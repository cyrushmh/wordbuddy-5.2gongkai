"""uni-app 各小程序端（微信 / 支付宝 / 百度 / 抖音 / QQ / 快手）原生接口与文档引用。

「触类旁通、举一反三」：内核、桌面、系统软件、鸿蒙之后，同一模式落到**跨端框架的各目标端**
——每个小程序平台都有**自己的 API 规范与运行架构**，不能混用：

- 微信 : wx.* API + 双线程架构（逻辑层 AppService / 视图层 WebView）
- 支付宝: my.* API + 域名白名单 + my.getAuthCode 授权
- 百度 : swan.* API
- 抖音 : tt.* API
- QQ   : qq.* API（与微信高度同源）
- 快手 : ks.* API
- uni-app: uni.* 统一 API → 各端映射，差异用条件编译（#ifdef MP-XXX）隔离

探测全部只读：扫描当前目录的 uni-app 工程（manifest.json / pages.json），
核对各端 manifest 的 mp-* 平台节点、构建产物目录与条件编译使用情况。
未发现工程时降级为指引，不强求安装任何工具。

参考文档见 data/miniapp_docs.json。
"""

from __future__ import annotations

import json
import os
import re
import shutil

# 端键 → (中文名, manifest 平台节点, 条件编译宏, API 前缀, 官方域名)
PLATFORMS = {
    "weixin": ("微信", "mp-weixin", "MP-WEIXIN", "wx.*",
               "https://developers.weixin.qq.com/miniprogram/dev/framework/"),
    "alipay": ("支付宝", "mp-alipay", "MP-ALIPAY", "my.*",
               "https://opendocs.alipay.com/mini/developer"),
    "baidu": ("百度", "mp-baidu", "MP-BAIDU", "swan.*",
              "https://smartprogram.baidu.com/docs/"),
    "douyin": ("抖音", "mp-toutiao", "MP-TOUTIAO", "tt.*",
               "https://developer.open-douyin.com/docs/"),
    "qq": ("QQ", "mp-qq", "MP-QQ", "qq.*", "https://q.qq.com/wiki/"),
    "kuaishou": ("快手", "mp-kuaishou", "MP-KUAISHOU", "ks.*",
                 "https://mp.kuaishou.com/docs"),
}

# 各端常见产物目录（相对工程根）
DIST_DIRS = ("unpackage/dist/build", "dist/build", "dist/dev", "unpackage/dist/dev")


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "miniapp_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    return REFS.get(key, {})


def reference_all() -> dict:
    return REFS


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024 * 1024:
        return f"{n/1024/1024/1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n/1024/1024:.1f} MiB"
    if n >= 1024:
        return f"{n/1024:.1f} KiB"
    return f"{n} B"


def _dir_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _scan_project() -> str:
    """在当前目录及其一级子目录中查找 uni-app 工程根目录（只读、不深扫）。"""
    cwd = os.getcwd()
    roots = [cwd]
    try:
        roots += [os.path.join(cwd, d) for d in os.listdir(cwd)
                  if os.path.isdir(os.path.join(cwd, d))]
    except OSError:
        pass
    for r in roots:
        for m in ("pages.json", "manifest.json", "src/manifest.json"):
            if os.path.exists(os.path.join(r, m)):
                return r
    return ""


def _manifest_text(root: str) -> str:
    """读取 manifest.json 文本（兼容 src/manifest.json），失败返回空串。"""
    p = os.path.join(root, "manifest.json")
    if not os.path.exists(p):
        p = os.path.join(root, "src", "manifest.json")
    if not os.path.exists(p):
        return ""
    try:
        with open(p, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _count_macro(root: str, macro: str) -> int:
    """统计源码中该端条件编译宏的使用次数（只读，最多扫 300 个文件）。"""
    n = 0
    scanned = 0
    for base in ("pages", "src/pages", "components", "src/components"):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for cur, _dirs, files in os.walk(d):
            for f in files:
                if scanned >= 300:
                    return n
                if not f.endswith((".vue", ".js", ".ts", ".nvue", ".uts")):
                    continue
                scanned += 1
                try:
                    with open(os.path.join(cur, f), encoding="utf-8",
                              errors="ignore") as fh:
                        n += fh.read().count(macro)
                except OSError:
                    pass
    return n


def _mp_report(key: str) -> tuple:
    """某小程序端的核对（只读）：manifest 平台节点 + 产物目录 + 条件编译。"""
    label, node, macro, prefix, url = PLATFORMS[key]
    root = _scan_project()
    if not root:
        return False, (f"当前目录未发现 uni-app 工程（无 pages.json / manifest.json）；"
                       f"在非工程目录运行时跳过。\n"
                       f"   {label}端要点: API 前缀 {prefix}，条件编译宏 {macro}，"
                       f"官方 {url}")
    lines = [f"uni-app 工程: {root}"]
    txt = _manifest_text(root)
    if txt:
        lines.append(f"   manifest 平台节点 {node}: "
                     f"{'已配置' if node in txt else '未配置'}")
    else:
        lines.append("   manifest.json: 未读取到")
    built = []
    for base in DIST_DIRS:
        p = os.path.join(root, base, node)
        if os.path.isdir(p):
            built.append(f"{base}/{node}（{_fmt_size(_dir_size(p))}）")
    lines.append(f"   构建产物: {'; '.join(built) if built else '未发现'}")
    cnt = _count_macro(root, macro)
    lines.append(f"   条件编译 {macro} 使用: {cnt} 处")
    lines.append(f"   该端 API 前缀: {prefix}（uni.* 统一 API 会映射到此）")
    return True, "\n".join(lines)


def weixin_report() -> tuple:
    return _mp_report("weixin")


def alipay_report() -> tuple:
    return _mp_report("alipay")


def baidu_report() -> tuple:
    return _mp_report("baidu")


def douyin_report() -> tuple:
    return _mp_report("douyin")


def qq_report() -> tuple:
    return _mp_report("qq")


def kuaishou_report() -> tuple:
    return _mp_report("kuaishou")


def mapping_report() -> tuple:
    """uni-app 跨端映射核对：已启用端数 + 各端条件编译覆盖（只读）。"""
    root = _scan_project()
    if not root:
        return False, "当前目录未发现 uni-app 工程；无法核对跨端映射与条件编译覆盖。"
    txt = _manifest_text(root)
    enabled = []
    for key, (_label, node, macro, _prefix, _url) in PLATFORMS.items():
        if txt and node in txt:
            cnt = _count_macro(root, macro)
            enabled.append(f"{_label}({node}) 条件编译 {cnt} 处")
    lines = [f"uni-app 工程: {root}",
             f"manifest 中已配置的小程序端: {len(enabled)} 个"]
    for e in enabled:
        lines.append("   · " + e)
    if not enabled:
        lines.append("   （未发现 mp-* 平台节点——发行前需在 manifest.json 中逐端配置）")
    lines.append("差异隔离: 用 #ifdef MP-XXX 条件编译，勿运行时猜平台")
    return True, "\n".join(lines)


# 前缀 → 端键（用于跨端静态检查）
PREFIX_TO_KEY = {"wx": "weixin", "my": "alipay", "swan": "baidu",
                 "tt": "douyin", "qq": "qq", "ks": "kuaishou"}

# 常见跨端 API 名（用于降低「变量名恰好叫 my」之类的误报）
COMMON_APIS = (
    "request", "getStorage", "setStorage", "removeStorage", "getStorageSync",
    "setStorageSync", "login", "getAuthCode", "getUserProfile", "navigateTo",
    "redirectTo", "switchTab", "showToast", "showModal", "getSystemInfo",
    "uploadFile", "downloadFile", "connectSocket", "scanCode",
    "makePhoneCall", "getLocation", "chooseImage", "setNavigationBarTitle",
)

_API_RE = re.compile(r"\b(wx|my|swan|tt|qq|ks)\.(" + "|".join(COMMON_APIS) + r")\b")


def cross_platform_lint() -> tuple:
    """跨端静态检查（只读）：找出「直接调某端原生 API 却无该端条件编译保护」的位置。

    典型错误：源码里直接写 `wx.request(...)`，却在支付宝端运行——支付宝端没有 wx 对象，
    直接报错。正确做法是优先用 uni.* 统一 API；无法避免时用 #ifdef MP-WEIXIN 包裹。
    本函数只做静态扫描，不修改任何文件。
    """
    root = _scan_project()
    if not root:
        return False, ("当前目录未发现 uni-app 工程（无 pages.json / manifest.json）；"
                       "无法做跨端静态检查。\n"
                       "   跨端要点：优先用 uni.* 统一 API，差异用 #ifdef MP-XXX 隔离。")

    issues = []
    files = 0
    scanned = 0
    bases = ("pages", "src/pages", "components", "src/components", "src", "utils",
             "src/utils", "common", "src/common")
    for base in bases:
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for cur, _dirs, fnames in os.walk(d):
            for fn in fnames:
                if scanned >= 500:
                    break
                if not fn.endswith((".vue", ".js", ".ts", ".nvue", ".uts")):
                    continue
                path = os.path.join(cur, fn)
                scanned += 1
                try:
                    with open(path, encoding="utf-8", errors="ignore") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                files += 1
                stack = []  # 条件编译上下文栈（#ifdef / #ifndef / #endif）
                for i, line in enumerate(lines, 1):
                    s = line.strip()
                    # 条件编译在 .vue/.js 里写作注释（// #ifdef MP-XXX、<!-- #ifdef -->），
                    # 故用「包含」判断，不能按行首匹配
                    if "#ifdef" in s or "#ifndef" in s:
                        stack.append(s)
                        continue
                    if "#endif" in s:
                        if stack:
                            stack.pop()
                        continue
                    for m in _API_RE.finditer(line):
                        prefix = m.group(1)
                        key = PREFIX_TO_KEY.get(prefix)
                        if not key:
                            continue
                        needed = PLATFORMS[key][2]  # 该端条件编译宏，如 MP-WEIXIN
                        ctx = set()
                        for frame in stack:
                            ctx.update(re.findall(r"MP-[A-Z]+", frame))
                        if needed not in ctx:
                            rel = os.path.relpath(path, root)
                            issues.append(
                                f"{rel}:{i}  直接调用 {prefix}.{m.group(2)} "
                                f"→ 建议用 #ifdef {needed} 包裹，或改用 uni.{m.group(2)}")

    lines_out = [f"uni-app 工程: {root}",
                 f"扫描源码文件: {files} 个（上限 500）",
                 f"跨端风险: {len(issues)} 处"]
    for it in issues[:15]:
        lines_out.append("   · " + it)
    if len(issues) > 15:
        lines_out.append(f"   …（共 {len(issues)} 处）")
    if not issues:
        lines_out.append("   未发现跨端风险（已全部用条件编译隔离，或统一使用 uni.* API）")
    lines_out.append("原则：优先 uni.* 统一 API；无法抹平的差异用 #ifdef MP-XXX 隔离，"
                     "勿运行时猜平台")
    return True, "\n".join(lines_out)


def detect_miniapp() -> dict:
    """探测本地 uni-app 工程与各端启用情况。"""
    root = _scan_project()
    txt = _manifest_text(root) if root else ""
    det = {"uniapp_project": bool(root),
           "hbuilderx": bool(shutil.which("HBuilderX")),
           "node": bool(shutil.which("node"))}
    for key, (_label, node, _macro, _prefix, _url) in PLATFORMS.items():
        det[key] = bool(txt and node in txt)
    return det


# 探测函数 → 展示标签（CLI/GUI 统一遍历）
PROBES = (
    ("cross_platform_lint", "跨端静态检查（直调某端原生 API 未加该端条件编译保护）"),
    ("mapping_report", "uni-app 跨端映射（uni.* → 各端原生 API + 条件编译）"),
    ("weixin_report", "微信小程序（wx.* / 双线程架构）"),
    ("alipay_report", "支付宝小程序（my.* / 域名白名单）"),
    ("baidu_report", "百度智能小程序（swan.*）"),
    ("douyin_report", "抖音小程序（tt.*）"),
    ("qq_report", "QQ 小程序（qq.*）"),
    ("kuaishou_report", "快手小程序（ks.*）"),
)


def environment_report() -> list:
    """返回小程序端环境跟踪报告（多行文本），供 CLI/GUI 展示。"""
    det = detect_miniapp()
    lines = ["本机 uni-app / 小程序端探测（按各自官方接口）："]
    lines.append(f"   {'uni-app 工程':<16} : {'✓ 已发现' if det['uniapp_project'] else '✗ 未发现'}")
    for key, (label, node, _macro, _prefix, _url) in PLATFORMS.items():
        lines.append(f"   {label + '(' + node + ')':<16} : "
                     f"{'✓ 已配置' if det.get(key) else '— 未配置'}")
    lines.append("（未发现工程/未配置端不强求配置——对应任务自动降级为指引）")
    return lines


def miniapp_doc_list(key: str = None) -> list:
    """返回文档引用行（含协议 protocols 与接口 interfaces），供 CLI/GUI 展示。"""
    items = {key: REFS[key]} if (key and key in REFS) else REFS
    lines = []
    for _k, ref in items.items():
        lines.append(f"   · {ref.get('name','')}  [{ref.get('org','')}]")
        lines.append(f"       文档: {ref.get('url','')}")
        for p in ref.get("protocols", [])[:2]:
            lines.append(f"       协议: {p}")
        for i in ref.get("interfaces", [])[:2]:
            lines.append(f"       接口: {i}")
    return lines
