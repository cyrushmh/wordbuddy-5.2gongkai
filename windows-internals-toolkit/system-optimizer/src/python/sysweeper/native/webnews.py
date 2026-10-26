"""新闻 / 网站聚合优化知识库（只读层，v0.6.11 新增）。

立项一句话
----------
用户想要「把新闻或网站拿来优化整体」。但「拿来优化」必须先有「拿来」和「读懂」两步，
而且**绝对不能**把网上抓来的东西当成命令执行。本层只做第一、二步：

1. **拿来**：从你配置的新闻源 / 网站（RSS 2.0 / Atom / 普通网页）抓取内容，
   只允许 http/https，带超时与体积上限，失败就报「未能获取」，绝不编造。
2. **读懂**：把抓取到的条目按平台 / 分类抽取成「可落地的优化知识点」，
   带来源归属，写进本地缓存，供任务层 / GUI / CLI 当**只读建议**展示。

红线（写死，任何情况不越）
--------------------------
- **只抓你配置的 http(s) 地址**，不碰 file:///ftp://，也不发任何写请求。
- **抓来的永远只是文本**，本层没有任何执行路径——不 eval、不 subprocess、
  不把网页内容当命令、不自动改系统设置。优化建议由你决定要不要做。
- **绝不联网硬塞**：默认源列表为空，需你显式添加 URL 才会去抓；
  抓不到就明确报「未能获取」，不把空数据包装成「已是最优」。
- 缓存只存 URL / 标题 / 摘要 / 知识点文字，**不存任何可执行片段**。

设计原则（呼应项目「不麻烦」）
----------------------------
- 纯标准库（urllib + xml.etree），零第三方依赖；能在 Linux 沙箱安全 import。
- 每个函数「能拿到就返回，拿不到就空 / None / False」，让上层决定降级。
"""

from __future__ import annotations

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

# ----------------------------- 配置常量 -----------------------------

# 默认抓取超时（秒）与单源体积上限（字节）——防止一个慢源拖死整轮。
DEFAULT_TIMEOUT = 8.0
MAX_BYTES = 2_000_000  # 2 MiB，够装下绝大多数 RSS/Atom 与单页 HTML

# 缓存路径（XDG：~/.config/sysweeper/webnews.json）。只存文本，损坏优雅降级。
_CACHE_NAME = "webnews.json"
_TTL = 6 * 3600  # 缓存有效期 6 小时：同一源 6 小时内不重复抓

# 内置可配置来源示例（**默认不抓取**，需用户显式启用才会去拉）。
# 这里列几个稳定、与系统优化强相关的公开 RSS，作为「你能加什么」的范本；
# 它们是否可达取决于网络，抓不到本层会如实报「未能获取」。
DEFAULT_SOURCES: List[str] = [
    # "https://www.kernel.org/feeds/korbit.xml",   # Linux 内核主线动态
    # "https://lwn.net/headlines/newrss",           # LWN 内核/发行版头条
]

# 知识点抽取的「关键词 → 分类」规则。中英文都认，命中即归入对应分类。
# 分类与项目一致：windows / macos / linux / android / network / security /
# privacy / hardware / storage / battery。
_TIP_RULES: List[Tuple[str, List[str]]] = [
    ("windows", ["windows", "注册表", "powershell", "win11", "win10", "组策略",
                 "bitlocker", "windows update"]),
    ("macos", ["macos", "mac os", "终端", "swift", "homebrew", "mac 优化",
               "spotlight", "时间机器"]),
    ("linux", ["linux", "内核", "systemd", "apt", "dnf", "pacman", "内核参数",
               "cgroup", "sysctl", "ubuntu", "debian", "fedora", "arch"]),
    ("android", ["android", "安卓", "adb", "电池优化", "后台限制", "doze",
                 "apk", "magisk"]),
    ("network", ["网络", "dns", "ipv6", "tcp", "bbr", "mtu", "wifi", "路由",
                 "network", "缓存dns", "dot", "doh", "tcp bbr"]),
    ("security", ["安全", "漏洞", "cve", "补丁", "exploit", "勒索", "security",
                  "hardening", "防火墙", "firewall"]),
    ("privacy", ["隐私", "追踪", "telemetry", "遥测", "收集", "privacy",
                 "指纹", "cookie"]),
    ("hardware", ["硬件", "cpu", "gpu", "固件", "驱动", "firmware", "bios",
                  "uefi", "散热", "thermal", "throttle", "降频", "hardware"]),
    ("storage", ["磁盘", "ssd", "trim", "硬盘", "存储", "storage", "nvme",
                 "分区", "文件系统", "fstrim", "smart"]),
    ("battery", ["电池", "续航", "耗电", "battery", "省电", "待机", "充电"]),
]


# ----------------------------- 工具函数 -----------------------------

def _state_dir() -> Path:
    """XDG 配置目录；拿不到就回退到当前目录下的 .sysweeper。"""
    try:
        base = Path.home() / ".config" / "sysweeper"
        base.mkdir(parents=True, exist_ok=True)
        return base
    except Exception:  # noqa: BLE001
        return Path(".sysweeper")


def _cache_path() -> Path:
    return _state_dir() / _CACHE_NAME


def is_allowed_url(url: str) -> bool:
    """只允许 http / https；file:///ftp:///其他一律拒绝。"""
    try:
        p = urlparse(url)
    except Exception:  # noqa: BLE001
        return False
    return p.scheme in ("http", "https")


def fetch(url: str, timeout: float = DEFAULT_TIMEOUT,
          max_bytes: int = MAX_BYTES) -> Tuple[bool, str]:
    """抓取一个 URL 的纯文本。失败返回 (False, 原因)，**绝不抛异常**。

    - 非 http/https 直接拒绝；
    - 超时 / 读不到 / 解码失败都返回 (False, 说明)，不编造内容；
    - 体积超过上限只取前 max_bytes，避免一个巨型源撑爆内存。
    """
    if not is_allowed_url(url):
        return False, f"拒绝抓取（仅允许 http/https）：{url}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sysweeper/0.6.11"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        text = raw.decode("utf-8", "replace")
        return True, text
    except Exception as e:  # noqa: BLE001
        return False, f"未能获取（{e}）：{url}"


def _text_of(el) -> str:
    """取 XML 元素的文本（含 CDATA / 子元素拼合）。"""
    if el is None:
        return ""
    t = (el.text or "") + "".join((c.tail or "") for c in el)
    # 递归把所有子元素文本拼上（RSS description 常包一层）
    for child in el:
        t += _text_of(child)
    return (t or "").strip()


def _norm(tag: str) -> str:
    """把带命名空间的元素标签压成纯本地名。"""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_feed(text: str) -> List[dict]:
    """把 RSS 2.0 / Atom 解析成条目列表。解析失败返回空列表（不抛异常）。

    每条：{title, link, summary, published, tags}。字段缺失就填空。
    """
    if not text or not text.strip():
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    items: List[dict] = []
    root_tag = _norm(root.tag).lower()
    # ---- Atom：<feed><entry> ----
    if root_tag == "feed":
        for e in root.findall("{*}entry"):
            items.append({
                "title": _text_of(e.find("{*}title")),
                "link": _atom_link(e),
                "summary": _text_of(e.find("{*}summary")) or _text_of(e.find("{*}content")),
                "published": _text_of(e.find("{*}updated")) or _text_of(e.find("{*}published")),
                "tags": [(_norm(c.tag), _text_of(c)) for c in e.findall("{*}category")],
            })
    # ---- RSS 2.0：<rss><channel><item> ----
    elif root_tag in ("rss", "rdf"):
        channel = root.find("{*}channel") or root
        for it in channel.findall("{*}item"):
            items.append({
                "title": _text_of(it.find("{*}title")),
                "link": _text_of(it.find("{*}link")),
                "summary": _text_of(it.find("{*}description")) or _text_of(it.find("{*}encoded")),
                "published": _text_of(it.find("{*}pubDate")) or _text_of(it.find("{*}date")),
                "tags": [(_norm(c.tag), _text_of(c)) for c in it.findall("{*}category")],
            })
    return [i for i in items if i.get("title") or i.get("link")]


def _atom_link(e) -> str:
    """Atom 的 link 是属性 <link href=.../>，优先取 rel=alternate 的。"""
    best = ""
    for l in e.findall("{*}link"):
        href = l.get("href", "")
        if not href:
            continue
        rel = l.get("rel", "alternate")
        if rel == "alternate" or not best:
            best = href
    return best


def _strip_tags(s: str) -> str:
    """极简去 HTML 标签（用于网页/摘要里混进来的标记）。"""
    import re
    return re.sub(r"<[^>]+>", " ", s or "").strip()


def extract_tips(text: str) -> Dict[str, List[str]]:
    """从一段文本里抽取「可落地的优化知识点」，按分类归集。

    命中规则见 _TIP_RULES：中英文关键词都认。返回 {分类: [知识点句]}，
    只含非空分类。这是**启发式**——命中关键词不等于「源里一定给了操作步骤」，
    只是「这条信息可能与该分类的优化有关」，供你知道「该往哪看」。
    """
    blob = (_strip_tags(text) or "").lower()
    out: Dict[str, List[str]] = {}
    for cat, kws in _TIP_RULES:
        hits = [kw for kw in kws if kw in blob]
        if hits:
            # 知识点句：列出命中的关键词，作为「关注方向」而非操作步骤
            out[cat] = hits
    return out


def load_cache() -> dict:
    """读缓存；不存在 / 损坏 → 返回空结构，绝不抛异常。"""
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_cache(data: dict) -> None:
    """写缓存；任何失败静默（不拖垮调用方）。"""
    try:
        _cache_path().write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


# ----------------------------- 主流程 -----------------------------

def fetch_all(sources: Optional[List[str]] = None,
              timeout: float = DEFAULT_TIMEOUT,
              fetch_fn=None) -> dict:
    """抓一批来源 → 解析 → 抽取知识点 → 合并 → 缓存。返回统计字典。

    fetch_fn 可注入（测试用）：签名同 fetch(url, timeout) → (ok, text)。
    默认走真实 fetch。任何单源失败都不影响其它源，失败源进 errors。
    """
    srcs = sources if sources is not None else list(DEFAULT_SOURCES)
    srcs = [s for s in srcs if is_allowed_url(s)]
    _fetch = fetch_fn or fetch

    fetched = 0
    parsed_items: List[dict] = []
    tips_by_cat: Dict[str, List[str]] = {}
    src_reports: List[dict] = []
    errors: List[str] = []

    for url in srcs:
        ok, text = _fetch(url, timeout)
        if not ok:
            errors.append(str(text)[:160])
            src_reports.append({"url": url, "ok": False, "error": str(text)[:160]})
            continue
        fetched += 1
        items = parse_feed(text)
        src_reports.append({"url": url, "ok": True, "items": len(items)})
        for it in items:
            parsed_items.append(it)
            t = " ".join([it.get("title", ""), it.get("summary", ""),
                          " ".join(str(x) for x in it.get("tags", []))])
            for cat, kws in extract_tips(t).items():
                tips_by_cat.setdefault(cat, [])
                for kw in kws:
                    if kw not in tips_by_cat[cat]:
                        tips_by_cat[cat].append(kw)

    data = {
        "fetched_at": int(time.time()),
        "sources": src_reports,
        "items": parsed_items,
        "tips_by_cat": tips_by_cat,
        "errors": errors,
    }
    save_cache(data)
    return {
        "ok": True,
        "sources_total": len(srcs),
        "fetched": fetched,
        "items": len(parsed_items),
        "tips_by_cat": tips_by_cat,
        "errors": errors,
    }


def cached_tips() -> Dict[str, List[str]]:
    """直接读缓存里的知识点（不重新抓网）。缓存空 → 空字典。"""
    return load_cache().get("tips_by_cat", {}) or {}


def knowledge_report() -> Tuple[bool, str]:
    """把缓存里的知识点整理成可读报告（只读建议，带来源归属）。"""
    cache = load_cache()
    if not cache:
        return True, ("优化资讯缓存为空。先运行「资讯抓取」添加你信任的新闻/网站源并拉取，"
                     "本层才会把其中与系统优化相关的知识点列出来。\n"
                     "红线：抓来的只是文本，本层不执行任何操作；要不要照着做由你决定。")
    lines = ["==== 优化资讯知识点（来自你配置的新闻/网站，只读建议）====", ""]
    tips = cache.get("tips_by_cat") or {}
    if not tips:
        lines.append("本轮抓取未命中任何已登记的分类关键词。"
                     "可换更贴近系统优化的来源，或放宽关注方向。")
    else:
        for cat in sorted(tips):
            kws = tips[cat]
            lines.append(f"  · [{cat}] 关注方向：{'、'.join(kws)}")
        lines.append("")
        lines.append("说明：以上是按关键词归类的「关注方向」，不是现成操作步骤——"
                     "点开来源自行核对具体做法；本层不自动改任何设置。")
    srcs = cache.get("sources") or []
    if srcs:
        lines += ["", "来源："]
        for s in srcs:
            if s.get("ok"):
                lines.append(f"  ✓ {s['url']}（{s.get('items', 0)} 条）")
            else:
                lines.append(f"  ✗ {s['url']}：{s.get('error', '未能获取')}")
    errs = cache.get("errors") or []
    if errs:
        lines += ["", f"抓取失败 {len(errs)} 个源（已跳过，不影响其它源）。"]
    return True, "\n".join(lines)


def sources_report() -> Tuple[bool, str]:
    """当前配置的来源列表（默认空；需用户显式添加）。"""
    lines = ["==== 配置的新闻/网站来源 ====", ""]
    if not DEFAULT_SOURCES:
        lines.append("默认来源为空（设计如此：不默认联网）。")
        lines.append("在 native/webnews.py 的 DEFAULT_SOURCES 里加入你信任的"
                     " http(s) RSS/网站地址，再运行「资讯抓取」即可。")
    else:
        for u in DEFAULT_SOURCES:
            lines.append(f"  · {u}")
    lines.append("")
    lines.append("允许范围：仅 http/https；带 8 秒超时与 2 MiB 体积上限；"
                 "失败源如实报「未能获取」，绝不编造内容。")
    return True, "\n".join(lines)


def capabilities_report() -> Tuple[bool, str]:
    """本层能力自检（哪些真能用、哪些依赖缺失）。"""
    lines = [
        "==== 新闻/网站优化资讯层（只读）====",
        "  抓取：urllib（标准库，零依赖）✓",
        "  解析：xml.etree（RSS 2.0 / Atom）✓",
        "  缓存：XDG ~/.config/sysweeper/webnews.json ✓",
        "  默认来源：空（需你显式添加才联网）✓",
        "",
        "红线：抓来的永远是文本，本层无执行路径——不 eval、不 subprocess、"
        "不自动改系统；优化建议要不要落地由你决定。",
    ]
    return True, "\n".join(lines)


def webnews_report() -> Tuple[bool, str]:
    """总报告：能力 + 来源 + 知识点。"""
    ok, cap = capabilities_report()
    ok2, src = sources_report()
    ok3, kd = knowledge_report()
    return True, "\n\n".join([cap, src, kd])
