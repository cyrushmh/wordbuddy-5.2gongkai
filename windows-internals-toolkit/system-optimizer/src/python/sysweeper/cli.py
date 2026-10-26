"""命令行入口。

用法示例：
  python -m sysweeper detect
  python -m sysweeper info --platform linux     # 用原生接口报告系统环境
  python -m sysweeper list --platform windows --version 10
  python -m sysweeper scan                      # 自动探测 + 分析（不修改）
  python -m sysweeper notes --platform ios --version 26
  python -m sysweeper clean --apply --risk low # 仅执行低风险清理
  python -m sysweeper clean --platform android --apply --yes --risk medium
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional
from importlib import resources

from . import registry
from . import __version__
from .detect import detect
from .models import CATEGORIES, RISK_ORDER
from .native import common
from .native import importio as _importio  # v0.6.23：多来源导入（剪贴板/文件/二维码）
from .native import settings as _settings  # v0.6.23：可调参数与阈值的默认值来源
from .runner import analyze, human, measure_disk
from .langdetect import detect_languages, available_languages  # noqa: E402
from .i18n import _, set_locale  # noqa: E402


def load_versions() -> dict:
    try:
        data = resources.files("sysweeper.data").joinpath("versions.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


def load_uniapp_api() -> dict:
    try:
        return json.loads(resources.files("sysweeper.data")
                          .joinpath("uniapp_api.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(args) -> tuple:
    """返回 (platform, version)。命令行优先，否则自动探测。"""
    platform = args.platform
    version = args.version
    if not platform:
        info = detect()
        platform = info["platform"]
        version = info["version"]
        print(f"自动探测: 平台={platform} 版本={version or '(未知)'}"
              + (f"  发行版={info['distro']}" if info.get("distro") else ""))
        if platform == "unknown":
            print("无法自动探测，请用 --platform / --version 指定。")
            sys.exit(2)
    if not version:
        version = "0"
    return platform, version


def _resolve_arch(args) -> Optional[str]:
    """返回用于过滤的架构键。

    - "auto"：按当前运行架构探测（arch.current_arch()），未识别返回 None（不过滤）；
    - "any" ：不按架构过滤，返回 None；
    - 其它   ：显式架构键（loongarch/mips/riscv/...）。
    applicable() 仅在 arch 非空且任务 arch 与之不同才过滤，所以返回 None 即「不过滤」。
    """
    sel = getattr(args, "arch", "auto") or "auto"
    if sel in ("auto", "any"):
        if sel == "any":
            return None
        try:
            from .arch import current_arch
            return current_arch() or None
        except Exception:  # noqa: BLE001
            return None
    return sel


def cmd_detect(args):
    info = detect()
    print("探测结果：")
    for k, v in info.items():
        print(f"  {k}: {v or '(空)'}")


def cmd_info(args):
    """用各平台原生接口报告系统环境（磁盘/版本/发行版等），不修改任何东西。"""
    platform, version = _resolve(args)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    print(f"\n==== {name} {version or ''} 系统信息（原生接口） ====")

    if platform == "windows":
        from .native import windows as nw
        v = nw.get_version()
        print(f"  版本(注册表): {v.get('product_name','')} "
              f"{v.get('display_version','') or v.get('release_id','')} (build {v.get('build','')})")
        du = nw.disk_usage()
        if du:
            print(f"  系统盘: 总 {human(du['total'])} / 可用 {human(du['free'])}")
        print(f"  临时目录: {', '.join(nw.get_temp_dirs()) or '(无法获取)'}")

    elif platform == "linux":
        from .native import linux as nl
        d = nl.detect_distro()
        print(f"  发行版(LSB): {d.get('pretty') or d.get('id') or '(未知)'} "
              f"(id={d.get('id','')}, version={d.get('version_id','')})")
        print(f"  包管理器: {nl.pkg_manager() or '(未识别)'}")
        js = nl.journal_size()
        if js:
            print(f"  systemd 日志: {js}")
        du = nl.disk_usage("/")
        if du:
            print(f"  根分区: 总 {human(du['total'])} / 可用 {human(du['free'])}")

    elif platform == "macos":
        from .native import macos as nm
        sv = nm.sw_vers()
        print(f"  版本: {sv.get('product','')} {sv.get('version','')} (build {sv.get('build','')})")
        model = nm.sysctl("hw.model")
        if model:
            print(f"  硬件型号: {model}")
        du = nm.disk_usage("/")
        if du:
            print(f"  根分区: 总 {human(du['total'])} / 可用 {human(du['free'])}")

    elif platform == "android":
        from .native import android as na
        if na.connected():
            print(f"  设备: {na.device_model()}  Android {na.version()}")
            print(f"  存储: {na.free_storage() or '(无法读取)'}")
        else:
            print("  adb 未连接设备；连接并开启 USB 调试后可读取设备信息。")

    elif platform == "ios":
        from .native import ios as ni
        if ni.available():
            info = ni.device_info()
            print(f"  设备: {info.get('devicename','')}  iOS {info.get('productversion','')}")
            print(f"  型号: {info.get('producttype','')}")
        else:
            print("  libimobiledevice 不可用或未连接；安装并信任设备后可读取信息。")

    elif platform == "bsd":
        from .native import bsd as nb
        d = nb.detect_distro()
        print(f"  发行版(sysctlbyname): {d.get('pretty') or d.get('id') or '(未知)'} "
              f"(id={d.get('id','')})")
        print(f"  包管理器: {d.get('pkg_manager') or '(未识别)'}")
        du = nb.disk_usage("/")
        if du:
            print(f"  根分区: 总 {human(du['total'])} / 可用 {human(du['free'])}")

    elif platform == "unix":
        from .native import unix as nu
        d = nu.detect_distro()
        print(f"  发行版(/etc/release): {d.get('pretty') or d.get('id') or '(未知)'}")
        print(f"  包管理器: {d.get('pkg_manager') or '(未识别)'}")
        du = nu.disk_usage("/")
        if du:
            print(f"  根分区: 总 {human(du['total'])} / 可用 {human(du['free'])}")


def cmd_versions(args):
    data = load_versions()
    if args.platform and args.platform not in data:
        print(f"未知平台：{args.platform}")
        return
    platforms = [args.platform] if args.platform else list(data.keys())
    for pf in platforms:
        print(f"\n{registry.PLATFORM_NAMES.get(pf, pf)} 可选版本：")
        for ver, meta in data.get(pf, {}).items():
            tags = []
            if meta.get("latest"):
                tags.append("最新")
            if meta.get("eol"):
                tags.append("已终止支持")
            tag = (" [" + "/".join(tags) + "]") if tags else ""
            print(f"  • {ver:<12} {meta.get('name','')}{tag}")
            if meta.get("note"):
                print(f"      注意: {meta['note']}")


def cmd_diag(args):
    """生成脱敏诊断报告：只写本地文件，绝不自动上传。

    移植自 DiPlay 的工程实践（见仓库根 docs/DiPlay-参考分析.md）：
    IP / MAC / 标识 / 家目录占位符化，命中凭据关键词的行整行丢弃。
    """
    from . import diagnostics
    import shutil

    info = detect()
    tools = ("adb", "fastboot", "smartctl", "lspci", "lsusb", "powershell",
             "system_profiler", "pkg", "apt-get", "dnf", "winget", "cmdkey")
    tool_lines = [f"{name}: {'有' if shutil.which(name) else '无'}" for name in tools]

    sections = {
        "探测结果": [f"{k}: {v or '(空)'}" for k, v in info.items()],
        "外部只读工具可用性": tool_lines,
    }
    if args.note:
        sections["补充说明"] = [args.note]

    out = args.out or diagnostics.default_report_path()
    text = diagnostics.build_report(
        version=__version__,
        platform_name=info.get("platform", ""),
        os_version=info.get("version", ""),
        extra_sections=sections,
    )
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        print(f"写入诊断报告失败：{exc}")
        return
    print(f"诊断报告已写入：{out}")
    print(f"  {len(text)} 字符；脱敏已开启（IP/MAC/标识/家目录已占位符化，"
          f"命中凭据关键词的行已丢弃）")
    print("  报告不会自动上传；分享前请自行检查一遍。")


def cmd_langs(args):
    """展示当前环境探测到的语言运行时，以及「按语言自动启用」的清理/优化功能。"""
    langs = detect_languages()
    print("\n==== 语言运行时探测（按系统环境自动启用对应功能，不强求安装） ====")
    avail = available_languages()
    print(f"已安装: {', '.join(avail) if avail else '(无)'}")
    on = off = 0
    for key, info in langs.items():
        mark = "✓ 已装" if info["available"] else "✗ 未装"
        print(f"  [{mark}] {info['name']:<10} {info['note']}")
        on, off = (on + 1, off) if info["available"] else (on, off + 1)
    for t in registry.by_lang_any():
        state = "启用" if t.requires_lang in avail else "隐藏(未安装该语言)"
        print(f"   · 语言功能 [{state}] {t.id}（需要 {t.requires_lang}）: {t.display_title()}")
    print(f"\n小结：{on} 种语言可用 → 对应功能自动启用；{off} 种未装 → 自动隐藏。")


def cmd_a11y(args):
    """无障碍环境报告（**多系统适配**）+ 适用任务。

    每个系统按**它自己的**无障碍协议与接口探测：
      - Linux   : ORCA + AT-SPI2（D-Bus org.a11y.Bus）
      - Windows : 讲述人 + UI Automation（UIA）/ MSAA
      - macOS   : VoiceOver + NSAccessibility（AX API）
      - Android : TalkBack + AccessibilityService（adb settings secure）
      - iOS     : VoiceOver（设备端设置）
      - 鸿蒙    : 屏幕朗读 + AccessibilityExtensionAbility
    ``--platform`` 可指定系统（默认 any = 全部概览）；非当前系统一律降级为指引。
    --speak 时朗读摘要。
    """
    from . import a11y as a11y_mod, registry

    plat = getattr(args, "platform", None) or None
    print(f"\n==== 无障碍环境（多系统适配，platform={plat or 'any'}） ====")
    for line in a11y_mod.environment_report(plat):
        print(line)

    if not plat or plat in ("any", "linux"):
        print("\n-- 多系统无障碍权威文档（协议与接口出处）--")
        for line in a11y_mod.a11y_doc_list():
            print(line)

    backend = a11y_mod.speak_backend()
    print("\n-- 语音输出 --")
    print(f"   可用后端: {backend or '（无——结果以纯文本呈现，便于复制给读屏器）'}")

    platform, version = _resolve(args)
    tasks = registry.applicable(platform, version, category="accessibility",
                                include_lang_missing=True)
    print(f"\n-- 适用无障碍任务（{registry.PLATFORM_NAMES.get(platform, platform)}，"
          f"{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<24} [{t.platform}/{t.risk}]  {t.display_title()}")
    if not tasks:
        print("   （当前平台暂无无障碍任务）")

    print("\n-- 标准引用（无障碍分类，三层）--")
    from .models import standards_for_audience
    for line in standards_for_audience("accessibility", getattr(args, "audience", "cn") or "cn"):
        print(f"   {line}")
    print("   切换受众: standards --audience cn|intl|regional")

    if getattr(args, "speak", False):
        summary = (f"无障碍报告：ORCA {'可用' if a11y_mod.orca_available() else '未安装'}；"
                   f"适用任务 {len(tasks)} 项。")
        ok, msg = a11y_mod.speak(summary)
        print(f"\n朗读: {'成功' if ok else '未执行'} — {msg}")


def cmd_rfc(args):
    """RFC 全量标准目录（v0.6.50）：list / search / show / citing /
    relations / current / series / topics / topic / refs / wgs / wg.

    数据来自 IETF 官方 RFC INDEX（本地解析、只读），使 sysweeper 任务里
    每一条 "RFC NNNN" 引用都可回溯到官方索引条目。输出为纯文本，
    一行一事实，屏幕阅读器可朗读（无障碍口径）。
    """
    from .native import rfc_catalog as cat

    action = getattr(args, "rfc_action", "overview") or "overview"
    if action == "list":
        status = (getattr(args, "status", "") or "").strip()
        limit = int(getattr(args, "limit", 30) or 30)
        if status:
            items = cat.by_status(status, limit)
            print(f"\n==== RFC 目录（状态={status.upper()}，最多 {limit} 条） ====")
        else:
            items = cat.latest(limit)
            print(f"\n==== RFC 目录（最新 {limit} 条） ====")
        if not items:
            print("没有匹配的条目。")
        for e in items:
            extra = f"（{e['also']}）" if e.get("also") else ""
            print(f"  RFC {e['n']:>5}  {e.get('s', '?'):<22} {e.get('d', '?'):<15}{extra}{e.get('t', '')}")
        print("\n查看详情: rfc show <编号>；按状态过滤: rfc list --status 'INTERNET STANDARD'")
        return

    if action == "search":
        term = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 20) or 20)
        if not term:
            print("请给出检索词：rfc search <关键词>（如 TLS、DNS、HTTP）")
            return
        items = cat.search(term, limit)
        print(f"\n==== RFC 检索：{term}（命中 {len(items)} 条，最多 {limit} 条） ====")
        for e in items:
            print(f"  RFC {e['n']:>5}  {e.get('s', '?'):<22} {e.get('d', '?'):<15}{e.get('t', '')}")
        return

    if action == "show":
        num = getattr(args, "number", None) or getattr(args, "term", None)
        e = cat.rfc_info(num)
        if e is None:
            print(f"\nRFC {num}：不在官方 RFC INDEX 中（该编号可能未分配，"
                  "或输入格式有误——可用 9846 / rfc09846 形态）。")
            return
        print(f"\n==== RFC {e['n']} ====")
        if not e.get("i"):
            print("状态：编号保留未发布（Not Issued）。")
            return
        print(f"标题：{e.get('t', '')}")
        if e.get("a"):
            print(f"作者：{e['a']}")
        print(f"日期：{e.get('d', '未知')}")
        print(f"状态：{e.get('s', '未知')}")
        if e.get("also"):
            print(f"子系列：{e['also']}")
        for k, label in (("obs", "废弃（被本 RFC 取代）"), ("oby", "被废弃（取代本 RFC）"),
                         ("upd", "更新"), ("udy", "被更新")):
            nums = e.get(k)
            if nums:
                print(f"{label}：{', '.join('RFC %d' % n for n in nums)}")
        if e.get("f"):
            print(f"格式：{', '.join(e['f'])}")
        if e.get("doi"):
            print(f"DOI：{e['doi']}")
        cites = cat.citing_tasks_for(e["n"])
        if cites:
            print(f"本系统引用它的任务（{len(cites)} 项）：{', '.join(cites)}")
        else:
            print("本系统暂无任务引用它。")
        tp = cat.topic_of(e["n"])
        if tp["classified"]:
            labels = {t["domain"]: t["label"] for t in cat.topics()}
            desc = "、".join("%s（%s）" % (d, labels.get(d, d))
                            for d in tp["domains"])
            print(f"主题域（heuristic）：{desc}")
        else:
            print("主题域（heuristic）：未命中规则（未分类）。")
        return

    if action == "citing":
        num = getattr(args, "number", None) or getattr(args, "term", None)
        cites = cat.citing_tasks_for(num)
        print(f"\n==== 引用 RFC {num} 的本系统任务（{len(cites)} 项） ====")
        for tid in cites:
            print(f"  {tid}")
        if not cites:
            print("（暂无任务引用；未引用不代表该标准不重要）")
        return

    if action == "relations":
        num = getattr(args, "number", None) or getattr(args, "term", None)
        rel = cat.rfc_relations(num)
        if rel is None:
            print(f"\nRFC {num}：不在官方 RFC INDEX 中。")
            return
        print(f"\n==== RFC {rel['n']} 关系视图：{rel.get('t', '')} ====")
        for k, label in (("obsoletes", "废弃（被本 RFC 取代）"),
                         ("obsoleted_by", "被废弃（取代本 RFC）"),
                         ("updates", "更新"), ("updated_by", "被更新")):
            items = rel.get(k) or []
            if not items:
                continue
            parts = []
            for it in items:
                if it.get("resolved"):
                    parts.append("RFC %d %s" % (it["n"], it.get("t") or ""))
                else:
                    parts.append("RFC %d（编号不在本索引，未解析）" % it["n"])
            print(f"{label}：{'；'.join(parts)}")
        if rel.get("also"):
            print(f"子系列：{rel['also']}")
        if not any(rel.get(k) for k in ("obsoletes", "obsoleted_by",
                                        "updates", "updated_by")):
            print("（无废止/更新关系记录）")
        print("\n沿链找现行版本：rfc current <编号>")
        return

    if action == "current":
        num = getattr(args, "number", None) or getattr(args, "term", None)
        cur = cat.rfc_current(num)
        print(f"\n==== RFC {num} 现行版本（obsoleted-by 链） ====")
        chain = " -> ".join(str(n) for n in cur.get("chain") or [])
        print(f"链：{chain or '（无记录）'}")
        st = cur.get("status")
        if st == "OK" and cur.get("current"):
            print(f"现行：RFC {cur['current']}  {cur.get('current_title') or ''}")
        else:
            print(f"状态：{st} —— {cur.get('note', '')}")
        return

    if action == "series":
        name = getattr(args, "term", "") or ""
        if not name:
            idx = cat.series_index()
            print(f"\n==== STD/BCP/FYI 系列（{len(idx)} 个） ====")
            for nk, nums in idx.items():
                print(f"  {nk:<9} {len(nums)} 条：{', '.join(str(n) for n in nums[:8])}"
                      + (" …" if len(nums) > 8 else ""))
            print("\n查看某系列成员：rfc series <名>（如 STD13 / bcp47）")
            return
        members = cat.series_members(name)
        print(f"\n==== 系列 {name.upper()} 成员（{len(members)} 条） ====")
        for e in members:
            print(f"  RFC {e['n']:>5}  {e.get('s', '?'):<22} {e.get('t', '')}")
        if not members:
            print("（无匹配系列或系列名格式有误：STD/BCP/FYI + 数字）")
        return

    if action == "topics":
        stats = cat.topic_stats()
        print("\n==== RFC 主题域索引（heuristic，非官方分类） ====")
        print(f"口径：{stats.get('method')}；范围：{stats.get('match_scope')}；"
              f"{stats.get('domain_count')} 个域 / {stats.get('rule_count')} 条规则")
        for t in cat.topics():
            print(f"  {t['domain']:<16} {t['label']:<12} {t['count']:>5} 条"
                  f"（{t['rule_count']} 条规则）")
        print(f"\n覆盖 {stats['classified']} / 9848 条已发布 RFC"
              f"（{stats['coverage']:.1%}），未分类 {stats['unclassified']} 条"
              f"（如实保留，不强行覆盖）")
        print("看某域成员：rfc topic <域名>")
        return

    if action == "topic":
        dom = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 30) or 30)
        if not dom:
            print("请给出主题域名：rfc topic <域名>（如 tls-pki / dns / ip-core）")
            return
        members = cat.topic_members(dom, limit)
        label = next((t["label"] for t in cat.topics()
                      if t["domain"] == dom.lower()), dom)
        print(f"\n==== 主题域 {dom}（{label}）成员（{len(members)} 条） ====")
        for e in members:
            print(f"  RFC {e['n']:>5}  {e.get('s', '?'):<22} {e.get('d', '?'):<15}"
                  f"{e.get('t', '')}")
        if not members:
            print("（无此域或域内暂无成员）")
        print("\n全部主题域：rfc topics；单条归属：rfc show <编号> 后见主题域")
        return

    if action == "refs":
        audit = cat.citation_audit()
        print("\n==== 任务侧 RFC 引用核验（应用对账） ====")
        print(f"被引用 RFC 总数：{audit['cited_total']}，"
              f"解析到官方索引 {audit['resolved']}，悬空 {audit['dangling_count']}")
        if audit["dangling"]:
            for k, tasks in audit["dangling"].items():
                print(f"  [悬空] {k} <- {', '.join(tasks)}")
        if audit["obsolete_cited"]:
            print(f"已废止仍被引用（真过期引用）：{audit['obsolete_cited_count']} 项")
            for k, info in audit["obsolete_cited"].items():
                print(f"  [过期] {k}（现行 RFC {info['current']} "
                      f"{info.get('current_title') or ''}）"
                      f" <- {', '.join(info['tasks'])}")
        else:
            print("已废止仍被引用（真过期引用）：0 项")
        if audit["obsolete_mention"]:
            print(f"废止说明性提及（同文本含现行编号，不算过期引用）："
                  f"{audit['obsolete_mention_count']} 项")
            for k, tasks in audit["obsolete_mention"].items():
                print(f"  [说明] {k} <- {', '.join(tasks)}")
        print("\n口径：只报告不改写；是否更新任务文本由维护者定夺。")
        return

    if action == "wgs":
        st = cat.wg_stats()
        rc = st.get("reconciliation") or {}
        print("\n==== RFC 官方 WG/RG 索引（rfc-index.xml + datatracker，第二索引源） ====")
        print(f"口径：{st.get('method')}；来源：{st.get('source')}")
        print(f"{st.get('wg_count')} 个工作组/研究组覆盖 {st.get('wg_covered')} 条已发布 RFC"
              f"（覆盖 {st.get('wg_coverage'):.1%}）；area 数 {st.get('area_count')}；"
              f"kind 分布 {st.get('kind_counts')}")
        print(f"与 heuristic 主题域层模态一致率 {rc.get('modal_agreement_rate_fmt')}%，"
              f"共同分类 {rc.get('modal_agreement')}/{rc.get('both_classified')}。")
        ov = cat.wgs(limit=0)
        print("\n--- IETF Area（按 RFC 数降序）---")
        for a in ov["areas"]:
            print(f"  {a['area']:<14} {a['name'] or ''}：{a['rfc_count']} 条"
                  f"（{a['wg_count']} 个 WG）")
        print("\n--- 产出 RFC 最多的 WG/RG（Top 15）---")
        for g in cat.wgs(limit=15)["top_wgs"]:
            print(f"  {g['wg']:<14} {g['name'] or ''}（{g.get('area') or g.get('kind') or ''}"
                  f"）{g['count']} 条")
        print("\n看某 WG/area 成员：rfc wg <名>（如 httpbis / tls / security / rtgwg）")
        return

    if action == "wg":
        name = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 50) or 50)
        wi = cat._wg_index()
        if not name:
            print("请给出 WG/RG/area 名：rfc wg <名>（如 httpbis / tls / security / rtgwg / routing）")
            return
        if name.lower() in wi.get("groups", {}):
            g = wi["groups"][name.lower()]
            print(f"\n==== WG/RG {g.get('name') or name}（{name}） ====")
            print(f"类型：{g.get('kind')}；area：{g.get('area')}；状态：{g.get('state')}；"
                  f"RFC 数：{g.get('count')}")
            members = cat.wg_members(name, limit)
            print(f"\n成员（最多 {limit} 条，按编号升序）：")
            for e in members:
                print(f"  RFC {e['n']:>5}  {e.get('s','?'):<22} {e.get('d','?'):<15}{e.get('t','')}")
            if len(members) >= limit:
                print(f"  …（仅显示前 {limit} 条，本组共 {g.get('count')} 条）")
        elif name.lower() in wi.get("areas", {}):
            a = wi["areas"][name.lower()]
            print(f"\n==== IETF Area {a.get('name') or name}（{name}） ====")
            print(f"WG 数：{a.get('wg_count')}；RFC 数：{a.get('rfc_count')}")
            members = cat.wg_members(name, limit)
            print(f"\n成员（最多 {limit} 条，按编号升序）：")
            for e in members:
                print(f"  RFC {e['n']:>5}  {e.get('s','?'):<22} {e.get('d','?'):<15}{e.get('t','')}")
            if len(members) >= limit:
                print(f"  …（仅显示前 {limit} 条，本组共 {a.get('rfc_count')} 条）")
        else:
            print(f"\n未找到名为 {name!r} 的 WG/RG/area。"
                  f"用 rfc wgs 浏览可用名称。")
        return

    # overview（默认）
    for line in cat.summary():
        print(line)
    print("\n子命令：list / search <词> / show <编号> / citing <编号> / "
          "relations <编号> / current <编号> / series [名] / "
          "topics / topic <域名> / refs / wgs / wg <名>")


def cmd_xiuzhen(args):
    """修真图谱（v0.6.46）：overview / list / search / show / edges / layers.

    数据来自 data/xiuzhen_map.json（build_xiuzhen_map.py 三源可复现 join），
    节点/边一律带 source，本命令只读不联网。输出纯文本，一行一事实，
    屏幕阅读器可朗读（无障碍口径，与 App 侧文本等价视图同一事实源）。
    """
    from .native import xiuzhen_catalog as xz

    action = getattr(args, "xiuzhen_action", "overview") or "overview"

    if action == "list":
        layer = (getattr(args, "layer", "") or "").strip()
        limit = int(getattr(args, "limit", 30) or 30)
        if layer:
            nodes = xz.by_layer(layer)
            print(f"\n==== 修真图谱 · {layer} 层（{len(nodes)} 个节点） ====")
        else:
            nodes = xz.map_data().get("nodes", [])
            print(f"\n==== 修真图谱 · 全量节点（{len(nodes)} 个，最多 {limit} 条） ====")
        if not nodes:
            print("没有匹配的节点（层名可用 layers 查看）。")
        for n in nodes[:limit]:
            title = xz.display_name(n)
            print(f"  {n['id']:<58} [{xz.TYPE_NAMES.get(n.get('type'), n.get('type'))}/{n.get('layer')}]  {title}")
        if layer:
            print(f"\n查看关联: xiuzhen edges <节点id>；示例: xiuzhen edges book:daodejing")
        else:
            print("\n按层过滤: xiuzhen list --layer classics；检索: xiuzhen search <词>")
        return

    if action == "search":
        term = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 20) or 20)
        if not term:
            print("请给出检索词：xiuzhen search <关键词>（如 黄庭、脏腑辨证、素问）")
            return
        hits = xz.search(term, limit)
        print(f"\n==== 修真图谱检索：{term}（命中 {len(hits)} 条，最多 {limit} 条） ====")
        for n in hits:
            title = xz.display_name(n)
            print(f"  {n['id']:<58} [{xz.TYPE_NAMES.get(n.get('type'), n.get('type'))}/{n.get('layer')}]  {title}")
        if not hits:
            print("没有匹配的节点（可换 title/标签/id 再试）。")
        return

    if action == "show":
        probe = getattr(args, "node", None) or getattr(args, "term", None)
        n = xz.node_info(probe)
        if n is None:
            print(f"\n节点 {probe}：不在图谱中（可用 layers/list/search 找节点 id）。")
            return
        title = xz.display_name(n)
        print(f"\n==== {n['id']} ====")
        print(f"名称：{title}")
        print(f"类型/层：{xz.TYPE_NAMES.get(n.get('type'), n.get('type'))} / {n.get('layer')}")
        detail = n.get("detail")
        if detail:
            print(f"说明：{detail}")
        elif n.get("intro"):
            print(f"简介：{n['intro']}")
        elif n.get("file"):
            print(f"语料文件：{n['file']}（账号：{n.get('account', '未知')}）")
        if n.get("daozang"):
            dz = n["daozang"]
            print(f"道藏编号：nid={dz.get('nid')}, id={dz.get('id')}")
        if n.get("onlineUrl"):
            print(f"在线原文：{n['onlineUrl']}")
        print(f"出处：{n.get('source', '未标注')}")
        rels = xz.neighbors(n["id"])
        print(f"关联关系：{len(rels)} 条（xiuzhen edges {n['id']} 查看全部）")
        return

    if action == "edges":
        probe = getattr(args, "node", None) or getattr(args, "term", None)
        if xz.node_info(probe) is None:
            print(f"\n节点 {probe}：不在图谱中（可用 layers/list/search 找节点 id）。")
            return
        rels = xz.neighbors(probe)
        print(f"\n==== {probe} 的关联关系（{len(rels)} 条） ====")
        for r in rels:
            arrow = "→" if r["dir"] == "out" else "←"
            print(f"  {arrow} {xz.relation_text(r)}")
        if not rels:
            print("（该节点暂无关联——宁缺毋滥，无出处不连边）")
        return

    if action == "layers":
        print("\n==== 修真图谱 · 分层 ====")
        for l in xz.layers():
            print(f"  {l['name']:<10}（{l['count']:>2} 节点）  {l['desc']}")
        print("\n按层浏览: xiuzhen list --layer daozang|classics|topics|external|corpus")
        return

    # overview（默认）
    for line in xz.summary():
        print(line)


def cmd_caudit(args):
    """WebTrust for CAs 审计图谱（v0.6.47）：overview / list / search / show /
    children / matters / locations / std / cpcps / domains.

    数据来自 data/ca_audit_standards.json（由 research/caaudit/ 事实底稿构建，
    源为用户投递的 GoDaddy/Starfield 2026 WebTrust 报告 PDF），每条记录带
    报告页码，只读不联网。标准引用可经 rfc_catalog 反查 RFC 5280。
    """
    from .native import ca_audit as ca

    action = getattr(args, "caudit_action", "overview") or "overview"

    if action == "list":
        kind = (getattr(args, "kind", "") or "").strip()
        limit = int(getattr(args, "limit", 30) or 30)
        cas = ca.cas_by_kind(kind) if kind else ca.map_data().get("cas", [])
        head = "按种类 %s" % ca.KIND_NAMES.get(kind, kind) if kind else "全量"
        print(f"\n==== WebTrust 审计图谱 · CA {head}（{len(cas)} 个，最多 {limit} 条） ====")
        if not cas and kind:
            print("该种类下没有 CA（可用 root/cross/issuing）。")
        for c in cas[:limit]:
            print(f"  {c['id']:<62} [{ca.KIND_NAMES.get(c.get('kind'), c.get('kind'))}]  "
                  f"{ca.display_name(c)}  p.{c.get('source_page')}")
        print("\n查看详情: caudit show <名称>；某根的下属: caudit children <根名称>")
        return

    if action == "search":
        term = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 20) or 20)
        if not term:
            print("请给出检索词：caudit search <关键词>（如 Starfield、TLS、DV、VMCR1）")
            return
        hits = ca.search(term, limit)
        print(f"\n==== CA 检索：{term}（命中 {len(hits)} 条，最多 {limit} 条） ====")
        for c in hits:
            print(f"  {c['id']:<62} [{ca.KIND_NAMES.get(c.get('kind'), c.get('kind'))}]  "
                  f"{ca.display_name(c)}")
        if not hits:
            print("没有匹配的 CA（可换名称/指纹前缀/id 再试）。")
        return

    if action == "show":
        probe = getattr(args, "node", None) or getattr(args, "term", None)
        c = ca.ca_info(probe)
        if c is None:
            print(f"\nCA {probe}：不在图谱中（可用 list/search 查找名称或指纹）。")
            return
        print(f"\n==== {ca.display_name(c)} ====")
        print(f"id/种类：{c['id']} / {ca.KIND_NAMES.get(c.get('kind'), c.get('kind'))}")
        print(f"SHA-256 指纹：{c['fingerprint']}")
        if c.get("root_id"):
            root = ca.ca_info(c["root_id"])
            print(f"上级根：{ca.display_name(root)}（{c['root_id']}）")
        print(f"出处：报告 Attachment A 第 {c.get('source_page')} 页")
        kids = ca.children(c["id"])
        if kids:
            print(f"下属 CA：{len(kids)} 个（caudit children '{ca.display_name(c)}' 查看）")
        return

    if action == "children":
        probe = getattr(args, "node", None) or getattr(args, "term", None)
        if ca.ca_info(probe) is None:
            print(f"\nCA {probe}：不在图谱中。")
            return
        kids = ca.children(probe)
        print(f"\n==== {ca.display_name(ca.ca_info(probe))} 的下属 CA（{len(kids)} 个） ====")
        for c in kids:
            print(f"  [{ca.KIND_NAMES.get(c.get('kind'))}] {ca.display_name(c)}")
            print(f"      {c['fingerprint']}  (p.{c.get('source_page')})")
        if not kids:
            print("（该 CA 下没有交叉签名或签发 CA）")
        return

    if action == "matters":
        bug = (getattr(args, "bug", "") or "").strip()
        if bug:
            m = ca.matter_by_bug(bug)
            mats = [m] if m else []
            if not mats:
                print(f"\nBugzilla #{bug}：不在 4 项事项中（可用 matters 查看全部）。")
                return
        else:
            mats = ca.matters()
        print(f"\n==== WebTrust 报告事项（{len(mats)} 项） ====")
        for m in mats:
            print(f"\n[{m.get('no')}] Bugzilla #{m.get('bug_id')}：{m.get('topic')}")
            print(f"    时间：{m.get('opened')} → {m.get('closed') or '未关闭'}"
                  f"（{ca.STATUS_NAMES.get(m.get('status'), m.get('status'))}）")
            print(f"    概况：{m.get('summary_cn', '')}")
            for r in m.get("refs", []):
                print(f"    违反条款：{r['std']} {r['clause']}（{r.get('topic', '')}）")
            for i, step in enumerate(m.get("remediation", []), 1):
                print(f"    整改{i}：{step}")
            print(f"    审计师核查：{ca.VERDICT_NAMES.get(m.get('schellman_verdict'), m.get('schellman_verdict', ''))}")
            print(f"    出处：报告第 {'/'.join(str(p) for p in m.get('source_pages', []))} 页")
        return

    if action == "locations":
        locs = ca.locations()
        print(f"\n==== 地点清单（{len(locs)} 个） ====")
        for l in locs:
            mark = "纳入物理环境测试" if l.get("physical_testing") else "未纳入物理测试"
            print(f"  {l['name']:<32} {l['type']:<32} {l['place']:<40} {mark}")
        return

    if action == "std":
        term = (getattr(args, "term", "") or "").strip()
        node = (getattr(args, "node", "") or "").strip()
        # 编号入口：'std rfc 5280'（term='rfc', node='5280'）或 'std 5280'
        parts = term.split()
        if parts and parts[0].lower() == "rfc" and (len(parts) > 1 or node):
            num = parts[1] if len(parts) > 1 else node
        elif term:
            num = term
        elif node:
            num = node
        else:
            num = ""
        if not num:
            refs = ca.standards_refs()
            print(f"\n==== 标准引用（{len(refs)} 项） ====")
            for s in refs:
                rfc = s.get("rfc_number")
                extra = ""
                if rfc:
                    info = ca.rfc_ref(rfc)
                    if info:
                        extra = f"  [RFC {info.get('n')}：{info.get('t')}]"
                    else:
                        extra = f"  [RFC {rfc}：rfc_catalog 查无]"
                print(f"  {s['id']:<28} {s['kind']:<22} {s['title']}{extra}")
            print("\n反查 RFC: caudit std rfc 5280")
            return
        info = ca.rfc_ref(num)
        if info is None:
            print(f"\nRFC {num}：rfc_catalog 查无该编号（或数据缺失）。")
            return
        print(f"\n==== RFC {info.get('n')} ====")
        print(f"标题：{info.get('t')}")
        print(f"状态：{info.get('s')}；日期：{info.get('d')}")
        print(f"作者：{info.get('a', '').rstrip('.')}")
        print(f"DOI：{info.get('doi', '未标注')}")
        print("\n注：本图谱事项引用 RFC 5280 §4.2.2.1（AIA 扩展）——见 caudit matters")
        return

    if action == "cpcps":
        docs = ca.map_data().get("cpcps_documents", [])
        print(f"\n==== CP/CPS 文档谱系（{len(docs)} 份） ====")
        for d in docs:
            print(f"  {d['doc']}")
            print(f"      {d['version']}（{d['dated']}）  范围：{d.get('scope', '?')}  p.{d.get('source_page')}")
        return

    if action == "domains":
        groups = ca.map_data().get("control_domains", [])
        print(f"\n==== WebTrust 控制域（{len(groups)} 组） ====")
        for g in groups:
            print(f"\n  {g['domain']}")
            for item in g.get("criteria", []):
                print(f"    - {item}")
        excl = ca.map_data().get("exclusions", [])
        if excl:
            print("\n明确排除项（审计未覆盖）：")
            for e in excl:
                print(f"  - {e}")
        return

    # overview（默认）
    for line in ca.summary():
        print(line)


def cmd_mongo(args):
    """MongoDB 权威指南（第2版）知识索引（v0.6.48）：overview / chapters / show /
    concepts / search / deploy / cross / book.

    数据来自 data/mongo_docs.json（由 research/mongodb/mongo_book_facts.json 可
    复现构建）：6 部分 / 23 章 / 43 概念 / 16 条系统调优。只读不联网；原书为
    商业出版物，PDF 原件不入库（版权页声明仅供个人使用），只留 SHA256 备核。
    `deploy` 与 `cross` 列出第 23 章的系统层调优项及其在 sysweeper 中的对账入口。
    """
    from .native import mongo_catalog as mg

    action = getattr(args, "mongo_action", "overview") or "overview"

    if action == "chapters":
        part = (getattr(args, "part", "") or "").strip()
        cs = mg.chapters(part)
        head = "（%s）" % part if part else ""
        print(f"\n==== 章节清单{head}（{len(cs)} 章） ====")
        if not cs:
            print("该部分下没有章节（可用 p1..p6）。")
        for c in cs:
            print(f"  第{c['no']:>2}章 {c['title']}  （{len(c.get('sections', []))} 节）")
        print("\n看某章的节: mongo show <章号>；示例: mongo show 23")
        return

    if action == "show":
        probe = getattr(args, "node", None) or getattr(args, "term", None)
        c = mg.chapter(probe)
        if c is None:
            print(f"\n第 {probe} 章：不在索引中（共 23 章，可用 chapters 查看）。")
            return
        print(f"\n==== 第{c['no']}章 {c['title']} ====")
        print(f"所属部分：{c.get('part')}；节数：{len(c.get('sections', []))}")
        for s in c.get("sections", []):
            print(f"  - {s}")
        related = [x for x in mg.concepts() if x.get("chapter") == c["no"]]
        if related:
            print(f"\n本章相关概念（{len(related)} 条）：")
            for x in related:
                print(f"  - {x['name']}：{x['desc']}")
        return

    if action == "concepts":
        cat = (getattr(args, "cat", "") or getattr(args, "category", "") or "").strip()
        names = mg.categories()
        if cat and cat not in names:
            print(f"\n类别 {cat} 不存在（可用：{'/'.join(sorted(names))}）。")
            return
        cs = mg.concepts(cat)
        head = "（%s %s）" % (cat, names.get(cat, "")) if cat else ""
        print(f"\n==== 概念条目{head}（{len(cs)} 条） ====")
        for c in cs:
            print(f"  [{c['category']}] {c['name']}  （第{c['chapter']}章）")
            print(f"      {c['desc']}")
        if not cs:
            print("没有匹配的概念。")
        return

    if action == "search":
        term = (getattr(args, "term", "") or "").strip()
        limit = int(getattr(args, "limit", 20) or 20)
        if not term:
            print("请给出检索词：mongo search <关键词>（如 副本集、索引、片键、journal）")
            return
        hits = mg.search(term, limit)
        print(f"\n==== 检索：{term}（命中 {len(hits)} 条，最多 {limit} 条） ====")
        for h in hits:
            it = h["item"]
            if h["kind"] == "concept":
                print(f"  [概念/{it['category']}] {it['name']}  （第{it['chapter']}章）")
                print(f"      {it['desc']}")
            else:
                print(f"  [调优/{it['section']}] {it['name']}")
                print(f"      {it['desc']}")
        if not hits:
            print("没有匹配的条目（可换关键词再试）。")
        return

    if action == "deploy":
        ops = mg.sysops()
        print(f"\n==== 第23章「部署MongoDB」系统层调优（{len(ops)} 条） ====")
        for s in ops:
            print(f"\n  [{s['section']}] {s['name']}")
            print(f"      {s['desc']}")
            tail = []
            if s.get("sysweeper_task"):
                tail.append("对应任务 sysweeper %s" % s["sysweeper_task"])
            if s.get("sysweeper_cmd"):
                tail.append("对应命令 sysweeper %s" % s["sysweeper_cmd"])
            if tail:
                print(f"      {'；'.join(tail)}")
        print("\n只列与 sysweeper 对得上的条目: mongo cross")
        return

    if action == "cross":
        refs = mg.cross_ref()
        print(f"\n==== 与 sysweeper 对账的系统调优条目（{len(refs)} 条） ====")
        for r in refs:
            marks = []
            if r.get("sysweeper_task"):
                marks.append("任务 %s：%s" % (
                    r["sysweeper_task"],
                    "存在" if r.get("task_exists") else "未找到"))
            if r.get("sysweeper_cmd"):
                marks.append("子命令 %s：%s" % (
                    r["sysweeper_cmd"],
                    "存在" if r.get("command_exists") else "未找到"))
            print(f"  {r['section']} {r['name']} —— {'；'.join(marks)}")
        if not refs:
            print("（没有可交叉引用的条目）")
        return

    if action == "book":
        bk = mg.book()
        b = bk.get("book", {})
        print("\n==== 书目与版权边界 ====")
        print(f"书名：{b.get('title')}（{b.get('publisher')}）")
        print(f"作者/译者：{b.get('author')} 著；{'、'.join(b.get('translators') or [])} 译")
        print(f"ISBN：{b.get('isbn')}；页数：{b.get('pages')}")
        print(f"原件 SHA256（备核验，原件不入库）：{b.get('pdf_sha256')}")
        print(f"\n版权声明：{bk.get('copyright_note', '')}")
        print(f"入库处置：{bk.get('archiving_note', '')}")
        return

    # overview（默认）
    for line in mg.summary():
        print(line)


def cmd_recert(args):
    """WCET 续证 PDU 计分方案（v0.6.51）：overview / cycles / areas / categories /
    show / rules / caps.

    数据来自 data/recert_docs.json（由用户投递的两个 .xls 续证跟踪表解析出的规则
    知识层）：IEEE WCET（无线通信工程技术）认证已于 2019 年停办，本库仅供继续教育 /
    PDU 跟踪方法论参考。只读不联网；不复制表内个人隐私字段。
    """
    from .native import recert as rc

    action = getattr(args, "recert_action", "overview") or "overview"

    if action == "cycles":
        cyc = rc.cycles()
        req = rc.requirements()
        print("\n==== 续证周期（WCET Recertification Cycles） ====")
        print(f"最小计量：{req.get('increment_hours')} 小时（"
              f"{req.get('increment_note', '')}）")
        print(f"须覆盖技术知识领域：至少 {req.get('min_technical_areas_addressed')} / "
              f"共 {req.get('technical_areas_total')} 个")
        print(f"活动须分布：至少 {req.get('min_distinct_years')} 个自然年")
        for k, v in cyc.items():
            print(f"  [{k}] {v.get('label')}：≥{v.get('min_pdus')} PDU；"
                  f"{v.get('span_requirement')}")
            print(f"        来源：{v.get('source')}")
        return

    if action == "areas":
        print("\n==== WCET 七大技术知识领域（Technical Areas of Knowledge） ====")
        for i, a in enumerate(rc.technical_areas(), 1):
            print(f"  {i}. {a}")
        print("\n注：领域由 WCET Candidate Handbook Appendix A 定义（原表引用未枚举）；"
              "第 7 类标注待核实，本库不臆造。")
        return

    if action == "categories":
        cats = rc.categories()
        print(f"\n==== 活动分类（{len(cats)} 类，PDU 计分与周期封顶） ====")
        for c in cats:
            cap3 = c.get("cycle_cap", {}).get("3year")
            cap5 = c.get("cycle_cap", {}).get("5year")
            print(f"  {c['key']:<16} {c['label']}")
            print(f"      规则：{c['rule']}")
            print(f"      计分：{c['pdu_per_unit'].get('3year')}（三年）"
                  f" / {c['pdu_per_unit'].get('5year')}（五年）")
            print(f"      周期封顶：{cap3}（三年） / {cap5}（五年）"
                  + (f"；每年封顶 {c['per_year_cap'].get('3year')}"
                     if c.get("per_year_cap") else ""))
        return

    if action == "show":
        key = (getattr(args, "term", "") or getattr(args, "node", "") or "").strip()
        c = rc.category(key)
        if c is None:
            print(f"\n活动分类 {key!r}：不存在。可用 recert categories 浏览。")
            return
        cap3 = c.get("cycle_cap", {}).get("3year")
        cap5 = c.get("cycle_cap", {}).get("5year")
        print(f"\n==== {c['label']}（{c['key']}，表页 {c['sheet'].strip()}） ====")
        print(f"规则：{c['rule']}")
        print(f"计分：{c['pdu_per_unit'].get('3year')}（三年）"
              f" / {c['pdu_per_unit'].get('5year')}（五年）")
        print(f"周期封顶：{cap3}（三年） / {cap5}（五年）"
              + (f"；每年封顶 {c['per_year_cap'].get('3year')}"
                 if c.get("per_year_cap") else ""))
        return

    if action == "rules":
        print("\n==== 续证合规校验清单（只报告，不改写） ====")
        for r in rc.validation_rules():
            print(f"  - {r}")
        return

    if action == "caps":
        for cyc in ("3year", "5year"):
            ma = rc.max_attainable(cyc)
            tot = sum(ma.values())
            label = "三年周期" if cyc == "3year" else "五年周期"
            req = rc.requirements()["cycles"][cyc]["min_pdus"]
            print(f"\n==== 各分类理论封顶合计（{label}，下限 {req}） ====")
            for k, v in sorted(ma.items(), key=lambda kv: -kv[1]):
                print(f"  {k:<16} {v}")
            print(f"  封顶合计 {tot}（已超过下限 {req}，仅作合规提示，非刷分建议）")
        return

    # overview（默认）
    info = rc.info()
    print(f"\n==== {info.get('title')} ====")
    print(f"认证：{info.get('certification')}（{info.get('certification_zh')}）")
    print(f"原作者：{info.get('author')}")
    print(f"项目状态：{info.get('program_status')}")
    for line in rc.summary():
        print(line)
    print("\n子命令：cycles / areas / categories / show <类> / rules / caps")


def cmd_radio(args):
    """无线电技术与标准只读诊断（v0.6.75 新建，CLI 子命令 `radio`）：overview / rf /
    wifi / bluetooth / rf_devices / sdr / regulation / capabilities。

    数据来自 data/radio_docs.json（法规与 SDR 事实均经官方源实检，只读知识消费）。
    只读盘点本机射频面（rfkill/iw/蓝牙/总线）与 SDR 工具链存在性，并核对法规口径；
    绝不驱动任何真实发射——不改 regdom/信道/txpower、不开 monitor 注入、不扫描不配对、
    不代申请许可；attack 类工具仅登记存在不提供操作入口。
    """
    from .native import radio as r

    action = getattr(args, "radio_action", "overview") or "overview"
    name = {
        "rf": "射频开关(rfkill)",
        "wifi": "Wi-Fi 物理能力与监管域(iw)",
        "bluetooth": "蓝牙控制器(bluetoothctl)",
        "rf_devices": "总线射频器件(lsusb/lspci)",
        "sdr": "SDR 与无线工具链存在性",
        "regulation": "无线电法规与频段合规口径",
        "capabilities": "无线能力总览",
    }

    if action == "rf":
        ok, msg = r.rf_switch_report()
    elif action == "wifi":
        ok, msg = r.wifi_phys_report()
    elif action == "bluetooth":
        ok, msg = r.bluetooth_report()
    elif action == "rf_devices":
        ok, msg = r.rf_devices_report()
    elif action == "sdr":
        ok, msg = r.sdr_toolchain_report()
    elif action == "regulation":
        ok, msg = r.regulation_report()
    elif action == "capabilities":
        ok, msg = r.capabilities_report()
    else:
        ok, msg = r.radio_report()

    label = name.get(action, "无线电技术与标准总览")
    print(f"\n==== {label}（只读） ====")
    print(msg)
    if action != "overview":
        print(f"\n子命令：rf / wifi / bluetooth / rf_devices / sdr / regulation / "
              f"capabilities / overview")


def cmd_winternals(args):
    """开源 Windows 分析学习应用只读诊断（v0.6.76 新建，CLI 子命令 `winternals`）：
    overview / env / fs / runtime / toolchain / anchors / capabilities。

    数据来自 data/winternals_refs.json（12 条，许可与版本口径经官方源检索，只读知识消费）。
    第一原则是**先定系统、再谈目录**：先判定目标所属环境（Windows 原生 / WSL / Linux /
    macOS / Android），再按那一套环境自身的文件系统、目录约定、路径分隔与运行语言标准
    去读数，绝不以本机 Linux 沙箱的习俗臆造目标结构。
    工具链只问在不在、绝不启动；PCILeech 等 DMA 写能力工具仅登记存在性与法律边界。
    """
    from .native import winternals as w

    action = getattr(args, "winternals_action", "overview") or "overview"
    name = {
        "env": "目标环境判定（先看是什么系统）",
        "fs": "文件系统与目录约定核验",
        "runtime": "运行语言环境与运行时依赖",
        "toolchain": "开源 Windows 分析工具链存在性",
        "anchors": "内核原理锚点与许可纯度",
        "capabilities": "能力总览",
    }

    if action == "env":
        ok, msg = w.target_env_report()
    elif action == "fs":
        ok, msg = w.fs_layout_report()
    elif action == "runtime":
        ok, msg = w.runtime_env_report()
    elif action == "toolchain":
        ok, msg = w.toolchain_report()
    elif action == "anchors":
        ok, msg = w.internals_anchors_report()
    elif action == "capabilities":
        ok, msg = w.capabilities_report()
    else:
        ok, msg = w.winternals_report()

    label = name.get(action, "开源 Windows 分析学习应用总览")
    print(f"\n==== {label}（只读） ====")
    print(msg)
    if action != "overview":
        print(f"\n子命令：env / fs / runtime / toolchain / anchors / "
              f"capabilities / overview")


def cmd_qstore(args):
    """量子存储交换只读诊断（v0.6.77 新建，CLI 子命令 `qstore`）：
    overview / endpoints / align / radix / pipeline / capabilities。

    数据来自 data/qstore_refs.json（10 条，官方源与仓内锚点，只读知识消费）。
    把「ext4 默认 4K 对齐 + GPU/NPU/TPU/CAN 异构端点缓冲交互 + 按程序要求做储存
    读取扫描索引 + 量子数字逻辑矩阵做进制转换」落成量子架构基座上的只读仿真。
    绝不执行写盘/格式化命令（只作文本建议）；CAN 绝不开套接字不发帧。
    """
    from .native import qstore as q

    action = getattr(args, "qstore_action", "overview") or "overview"
    name = {
        "endpoints": "异构端点存在性只读盘点",
        "align": "ext4 / 4K 对齐逐设备核验",
        "radix": "量子进制转换（Π_k 保真往返）",
        "pipeline": "储存读取扫描索引管线仿真",
        "capabilities": "能力总览",
    }

    if action == "endpoints":
        ok, msg = q.endpoint_probe_report()
    elif action == "align":
        ok, msg = q.alignment_report()
    elif action == "radix":
        ok, msg = q.radix_report()
    elif action == "pipeline":
        ok, msg = q.pipeline_report()
    elif action == "capabilities":
        ok, msg = q.capabilities_report()
    else:
        ok, msg = q.qstore_report()

    label = name.get(action, "量子存储交换总览")
    print(f"\n==== {label}（只读） ====")
    print(msg)
    if action != "overview":
        print(f"\n子命令：endpoints / align / radix / pipeline / "
              f"capabilities / overview")


def cmd_qarch(args):
    """量子架构内核只读诊断（v0.6.78 新建，CLI 子命令 `qarch`）：
    overview / tree / arch / qpu / dist / capabilities。

    盘点 quantum-kernel/ 内核树：Linux 6.18.57 LTS + arch/quantum 纯新增架构
    + QPU 模拟设备。纯只读，绝不执行内核构建/写树/加载模块。
    """
    from .native import qarch as q

    action = getattr(args, "qarch_action", "overview") or "overview"
    name = {
        "tree": "内核树在位与基线盘点",
        "arch": "架构覆盖与纯新增核验",
        "qpu": "QPU 设备与语义盘点",
        "dist": "补丁分发与重建路径盘点",
        "capabilities": "能力总览",
    }
    fns = {"tree": q.tree_report, "arch": q.arch_report, "qpu": q.qpu_report,
           "dist": q.dist_report, "capabilities": q.capabilities_report}
    ok, msg = fns.get(action, q.qarch_report)()
    label = name.get(action, "量子架构内核总览")
    print(f"\n==== {label}（只读） ====")
    print(msg)
    if action != "overview":
        print("\n子命令：tree / arch / qpu / dist / capabilities / overview")


def cmd_langref(args):
    """编程语言与编译器知识库（v0.6.53，CLI 子命令 `langref`）：overview / stats /
    window / search / show / category / origin / paradigms / verify。

    数据来自 data/langs_docs.json（精选代表性集合，以 2008–2026 新发语言为主体，
    补历史锚点(古今)与国内外代表，以及「其他计算机类」：查询/标记/数据/Shell/IR/
    排版/记号/验证）。结构化元数据，不复制教材；存疑项标 needs_verify。只读不联网。
    """
    from .native import langs as lg

    action = getattr(args, "langs_action", "overview") or "overview"

    if action == "stats":
        s = lg.stats()
        print("\n==== 编程语言知识库统计 ====")
        print(f"总条目：{s['total']}（窗口 2008–2026 内 {s['in_window']}，"
              f"窗口外历史锚点 {s['out_of_window']}）")
        print(f"待核实(needs_verify)条目：{s['needs_verify']}")
        print("按分类：", s["by_category"])
        print("按来源：", s["by_origin"])
        return

    if action == "window":
        print("\n==== 2008–2026 窗口内语言（首现年降序） ====")
        for e in lg.window(only=True):
            print(f"  {e['first_year']}  {e['name']:<22} [{e['category']}]  {e['origin']}  {e['designer']}")
        return

    if action == "search":
        q = (getattr(args, "term", "") or "").strip()
        if not q:
            print("\n用法：langs search <关键词>（名称/中文名/设计者/范式/备注）")
            return
        hits = lg.search(q)
        print(f"\n==== 检索 {q!r}：{len(hits)} 条 ====")
        for e in hits:
            print(f"  {e['first_year']}  {e['name']}（{e['name_zh']}）  {e['category']}  {e['origin']}")
        return

    if action == "show":
        key = (getattr(args, "term", "") or "").strip()
        e = lg.get(key)
        if e is None:
            print(f"\n语言 {key!r}：不存在。可用 langs search <词> 或 langs window 浏览。")
            return
        print(f"\n==== {e['name']}（{e['name_zh']}） ====")
        # first_release 本身已含年份与沿革，分开打印避免「1993（1993…）」重复
        print(f"首现年：{e['first_year']}")
        print(f"发布沿革：{e['first_release']}")
        print(f"范式：{', '.join(e['paradigms'])}")
        print(f"类型系统：{e['type_system']}")
        print(f"实现：{e['implementation']}")
        print(f"设计者：{e['designer']}（{e['origin']} / {e['region']}）")
        print(f"状态：{e['status']}    分类：{e['category']}    窗口内：{e['in_window']}")
        print(f"标准：{e['standard']}")
        print(f"备注：{e['notes']}")
        if e.get("needs_verify"):
            print(f"⚠ 待核实：{'；'.join(e['needs_verify'])}")
        return

    if action == "category":
        cat = (getattr(args, "term", "") or "").strip()
        if not cat:
            print("\n用法：langs category <分类>（compiled/interpreted/jit/transpiled/"
                  "query/markup/data/config/shell/ir/typesetting/notation/verification）")
            return
        es = lg.by_category(cat)
        print(f"\n==== 分类 {cat}：{len(es)} 条 ====")
        for e in es:
            print(f"  {e['first_year']}  {e['name']}（{e['name_zh']}）  {e['origin']}")
        return

    if action == "origin":
        o = (getattr(args, "term", "") or "").strip()
        if not o:
            print("\n用法：langs origin <来源>（国外/国内/国际）")
            return
        es = lg.by_origin(o)
        print(f"\n==== 来源 {o}：{len(es)} 条 ====")
        for e in es:
            print(f"  {e['first_year']}  {e['name']}（{e['name_zh']}）  [{e['category']}]")
        return

    if action == "paradigms":
        print("\n==== 范式分布（按数量降序） ====")
        for p in lg.paradigms():
            print(f"  {p['paradigm']:<12} {p['count']}")
        return

    if action == "verify":
        es = lg.needs_verify()
        print(f"\n==== 待核实条目（needs_verify）：{len(es)} 条（诚实边界，以官网为准） ====")
        for e in es:
            print(f"  {e['name']}：{'；'.join(e['needs_verify'])}")
        return

    # overview（默认）
    info = lg.info()
    s = lg.stats()
    print(f"\n==== {info.get('title')} ====")
    print(f"范围：{info.get('scope')}")
    print(f"窗口：{info.get('window')}    条目：{s['total']}（窗口内 {s['in_window']}）")
    print(f"诚实说明：{info.get('honesty_note')}")
    print(f"子命令：stats / window / search <词> / show <id> / category <分类> / "
          f"origin <来源> / paradigms / verify")


def cmd_plang(args):
    """编程语言「概念系统」分层分类（v0.6.56）：以仓库 wordbuddy-github 为主目录，
    按执行模型 → 硬件架构子分类 → 能力域 → 底层标准依据(RFC 等)组织 161 条语言。

    子命令：overview / archs / arch <架构> / models / model <模型> / of <id> /
    rfc [id] / probe / domains。只读不联网；RFC 编号均经 rfc_catalog 交叉验证。
    """
    from .concepts import plang as pg

    action = getattr(args, "plang_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "archs":
        print("\n==== 硬件架构子分类（一条语言可属多个架构）====")
        for a in pg.archs():
            print(f"  [{a['kind']:<14}] {a['arch']:<10} {a['count']:>3}  {a['label']}")
            print(f"         {a['note']}")
        return

    if action == "arch":
        if not term:
            print("\n用法：plang arch <架构>（x86-64 / arm64 / riscv / wasm / jvm / clr / "
                  "beam / evm / js / gpu-simt / fpga / host / n-a）")
            return
        ids = pg.langs_of_arch(term)
        if not ids:
            print(f"\n架构 {term!r}：无该分类或为空。可用 plang archs 浏览。")
            return
        print(f"\n==== 架构 {term}：{len(ids)} 条语言 ====")
        for lid in ids:
            v = pg.of(lid) or {}
            print(f"  {lid:<14} {v.get('name','')}")
        return

    if action == "models":
        print("\n==== 执行模型 ====")
        for m in pg.models():
            print(f"  {m['model']:<14} {m['count']:>3}  {m['label']}")
            print(f"         {m['note']}")
        return

    if action == "model":
        if not term:
            print("\n用法：plang model <模型>（native / bytecode-vm / interpreted / jit / "
                  "transpiled / ir / hdl / non-exec）")
            return
        ids = pg.langs_of_model(term)
        if not ids:
            print(f"\n执行模型 {term!r}：无该分类或为空。可用 plang models 浏览。")
            return
        print(f"\n==== 执行模型 {term}：{len(ids)} 条语言 ====")
        for lid in ids:
            v = pg.of(lid) or {}
            print(f"  {lid:<14} {v.get('name','')}")
        return

    if action == "of":
        if not term:
            print("\n用法：plang of <语言 id>（如 rust / wasm / verilog / solidity）")
            return
        v = pg.of(term)
        if not v:
            print(f"\n语言 {term!r}：不在概念系统中。可用 plang archs 或 langref search 浏览。")
            return
        print(f"\n==== {v['name']}（{term}）的分类 ====")
        print(f"执行模型：{v['model']}")
        print(f"目标架构：{', '.join(v['archs'])}")
        print(f"能力域：{', '.join(v['domains'])}")
        print(f"映射来源：{v['mapping_source']}（explicit=人工判定 / inferred=按分类推断）")
        print(f"自身标准：{v.get('own_standard') or '（无/未登记）'}")
        # v0.6.61 补全字段：概念卡片
        print(f"{_('首次出现：')}{v.get('first_appeared') or '？'}")
        print(f"{_('范式：')}{v.get('paradigm') or '—'}")
        print(f"{_('类型系统：')}{v.get('typing') or '—'}")
        print(f"{_('内存管理：')}{v.get('memory') or '—'}")
        print(f"{_('一句话定位：')}{v.get('gist') or '—'}")
        print(f"{_('工程落法：')}{v.get('engineering') or '—'}")
        if v.get("standards"):
            print("继承的底层标准依据（补足自身标准不足）：")
            for s in v["standards"]:
                ref = f"{s['kind']} {s['num']}" if s.get("num") else s["kind"]
                title = s.get("rfc_title") or s.get("why") or ""
                print(f"  - [{s['domain_label']}] {ref}  {title}")
                print(f"      {s['why']}")
        return

    if action == "rfc":
        if term:
            refs = pg.rfc_refs(term)
            print(f"\n==== {term} 继承的 RFC 依据：{len(refs)} 条 ====")
            for s in refs:
                print(f"  RFC {s['num']}  {s.get('rfc_title','')}")
                print(f"      域 {s['domain_label']}：{s['why']}")
            return
        print("\n==== 概念系统引用的全部 RFC（均经 rfc_catalog 交叉验证）====")
        seen = set()
        for d in pg.domains():
            for s in d.get("standards", []):
                if s.get("kind") != "RFC" or s["num"] in seen:
                    continue
                seen.add(s["num"])
                print(f"  RFC {s['num']:<6} [{d['domain']}] {s.get('rfc_title','')}")
        return

    if action == "probe":
        p = pg.probe()
        print("\n==== 「各语言尝试编程整体」实测 ====")
        if not p["results"]:
            print("（无实测记录）")
            return
        m = p["meta"] or {}
        print(f"契约：{', '.join(m.get('contract', []))}")
        print(f"通过 {m.get('passed')}/{m.get('total')}；"
              f"本机无工具链的一律标「未实测」，不臆造结果\n")
        for r in p["results"]:
            mark = "✓" if r["status"] == "实测通过" else "—"
            print(f"  {mark} {r['name']:<12} {r['status']}"
                  + (f"  {r.get('reason','')[:50]}" if r.get("reason") else ""))
            if r.get("kv"):
                kv = r["kv"]
                print(f"      能力面：OPS={kv.get('OPS','-')} "
                      f"CONTROL={kv.get('CONTROL','-')} FUNC={kv.get('FUNC','-')} "
                      f"CONCURRENCY={kv.get('CONCURRENCY','-')}")
        return

    if action == "domains":
        print("\n==== 能力域 → 底层标准依据 ====")
        for d in pg.domains():
            print(f"  [{d['domain']}] {d['label']}")
            for s in d.get("standards", []):
                ref = f"{s['kind']} {s['num']}" if s.get("num") else s["kind"]
                print(f"      {ref}  {s.get('rfc_title') or ''}")
                print(f"         {s['why']}")
        return

    # overview（默认）
    m = pg.info()
    s = pg.stats()
    print(f"\n==== {m.get('title')} ====")
    print(f"主目录（概念系统）：{m.get('system_root')}")
    print(f"说明：{m.get('system_note')}")
    print(f"语言总数：{s['lang_total']}    执行模型 {s['model_count']} 类"
          f"    硬件架构 {s['arch_count']} 类    能力域 {s['domain_count']} 个")
    print(f"分类轴：{', '.join(m.get('axes', []))}")
    print(f"架构口径：{m.get('arch_note')}")
    print(f"映射口径：{m.get('mapping_note')}")
    print(f"RFC 口径：{m.get('rfc_note')}")
    print("\n子命令：archs / arch <架构> / models / model <模型> / of <id> / "
          "rfc [id] / probe / domains")


def cmd_netsys(args):
    """网络与组网「概念系统」（v0.6.57）：以仓库 wordbuddy-github 为主目录，把散落的
    20+ 个网络/组网子系统按四轴重组，并显式登记依赖/互补关系与红线。

    子命令：overview / layers / layer <层次> / forms / form <形态> / natures /
    nature <性质> / of <id> / relations / rfc / redlines。只读不联网。
    """
    from .concepts import netsys as ns

    action = getattr(args, "netsys_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    def _list_ids(ids, title):
        print(f"\n==== {title}：{len(ids)} 个 ====")
        for mid in ids:
            m = ns.of(mid) or {}
            print(f"  {mid:<12} {m.get('name','')}  [{m.get('nature','')}]")
            print(f"       {m.get('redline','')}")

    if action == "layers":
        print("\n==== 网络层次轴 ====")
        for l in ns.layers():
            print(f"  {l['layer']:<7} {l['count']:>2}  {l['label']}")
            print(f"         {l['note']}")
        return

    if action == "layer":
        if not term:
            print("\n用法：netsys layer <层次>（L1/L2/L3/L4/L5-6/L7/overlay/mesh）")
            return
        ids = ns.by_layer(term)
        if not ids:
            print(f"\n层次 {term!r}：无该分类或为空。可用 netsys layers 浏览。")
            return
        _list_ids(ids, f"层次 {term}")
        return

    if action == "forms":
        print("\n==== 组网形态轴 ====")
        for f in ns.forms():
            print(f"  {f['form']:<12} {f['count']:>2}  {f['label']}")
            print(f"         {f['note']}")
        return

    if action == "form":
        if not term:
            print("\n用法：netsys form <形态>（standalone/lan/mesh/overlay/sdwan/"
                  "distributed/anonymous/wan）")
            return
        ids = ns.by_form(term)
        if not ids:
            print(f"\n形态 {term!r}：无该分类或为空。可用 netsys forms 浏览。")
            return
        _list_ids(ids, f"组网形态 {term}")
        return

    if action == "natures":
        print("\n==== 能力性质轴 ====")
        for n in ns.natures():
            print(f"  {n['nature']:<12} {n['count']:>2}  {n['label']}")
            print(f"         {n['note']}")
        return

    if action == "nature":
        if not term:
            print("\n用法：netsys nature <性质>（diagnose/tune/communicate/share/"
                  "audit/discover/reference）")
            return
        ids = ns.by_nature(term)
        if not ids:
            print(f"\n性质 {term!r}：无该分类或为空。可用 netsys natures 浏览。")
            return
        _list_ids(ids, f"能力性质 {term}")
        return

    if action == "of":
        if not term:
            print("\n用法：netsys of <模块 id>（如 osi / distjob / tor / ipp）")
            return
        m = ns.of(term)
        if not m:
            print(f"\n模块 {term!r}：不在概念系统中。可用 netsys layers 浏览。")
            return
        print(f"\n==== {m['name']}（{m['id']}） ====")
        print(f"网络层次：{', '.join(m['layers'])}")
        print(f"组网形态：{', '.join(m['forms'])}")
        print(f"能力性质：{m['nature']}")
        for d in m.get("depends_detail", []):
            print(f"依赖：{d['name']}（{d['id']}）")
        for c in m.get("complements_detail", []):
            print(f"互补：{c['name']}（{c['id']}）")
        if m.get("standards"):
            print("标准依据：")
            for s in m["standards"]:
                ref = f"{s['kind']} {s['num']}" if s.get("num") else f"{s['kind']} {s.get('name','')}"
                print(f"  - {ref}  {s.get('rfc_title','')}")
        print(f"红线：{m['redline']}")
        return

    if action == "relations":
        kind = term or None
        rs = ns.relations(kind)
        print(f"\n==== 关系边：{len(rs)} 条"
              + (f"（{kind}）" if kind else "（depends + complements）") + " ====")
        for r in rs:
            print(f"  {r['from']:<12} --{r['kind']}--> {r['to']}")
            print(f"       {r['note']}")
        return

    if action == "rfc":
        seen = set()
        print("\n==== 网络模块引用的 RFC（均经 rfc_catalog 交叉验证）====")
        for m in ns.modules():
            for s in m.get("standards", []):
                if s.get("kind") != "RFC" or s["num"] in seen:
                    continue
                seen.add(s["num"])
                print(f"  RFC {s['num']:<6} [{m['id']}] {s.get('rfc_title','')}")
        return

    if action == "redlines":
        print("\n==== 各模块红线（越界防线）====")
        for r in ns.redlines():
            print(f"  [{r['nature']}] {r['id']:<12} {r['name']}")
            print(f"      {r['redline']}")
        return

    # overview（默认）
    m = ns.info()
    s = ns.stats()
    print(f"\n==== {m.get('title')} ====")
    print(f"主目录（概念系统）：{m.get('system_root')}")
    print(f"模块 {s['module_total']} 个    层次 {s['layer_count']} · 形态 {s['form_count']}"
          f" · 性质 {s['nature_count']}")
    print(f"关系边 {s['relation_count']} 条（依赖 {s['depends_count']} · 互补 {s['complements_count']}）")
    print(f"分类轴：{', '.join(m.get('axes', []))}")
    print(f"重组说明：{m.get('reorg_note')}")
    print(f"红线口径：{m.get('redline_note')}")
    print("\n子命令：layers / layer <层次> / forms / form <形态> / natures / "
          "nature <性质> / of <id> / relations / rfc / redlines")


def cmd_daoxue(args):
    """「道枢」治理层概念系统（v0.6.58）：以仓库 wordbuddy-github 为主目录，
    中心指导理念《道德经》81 章；前置指导思想《太上玄门早坛功课经》；中间二级思想
    《般若波罗蜜多心经》+《论语》；后置指导思想《太上玄门晚坛功课经》。
    并把理念落成 15 条可审计的工程治理原则，桥接到 plang / netsys / langref。

    子命令：overview / center [章号] / pre / post / middle / fangshu [域|条目] /
    principles [id] / bridge [系统] / apply <系统> / search <词> / verify / stats。

    方术子层（tier=3）只登记文献、形制与仪轨结构：不录符图笔画与咒文全文，
    不主张任何超自然效力或医疗疗效；祝由一支只作文文献与官制沿革登记，
    不构成医疗建议。只读不联网；不复制经典全文，只登记章旨/节旨/纲宗与映射。
    """
    from .concepts import daoxue as dx

    action = getattr(args, "daoxue_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "center":
        c = dx.center()
        if term:
            try:
                no = int(term)
            except ValueError:
                print(f"\n用法：daoxue center [1–81]")
                return
            ch = dx.chapter(no)
            if not ch:
                print(f"\n无第 {no} 章（道德经 1–81）。")
                return
            p = dx.principle(ch["principle"]) or {}
            print(f"\n==== 道德经 第{ch['no']}章（{ch['part']}）====")
            print(f"章旨：{ch['theme']}")
            print(f"节旨：{ch['gist']}")
            print(f"归属治理原则：{p.get('name','')}（{ch['principle']}）")
            print(f"  义理：{p.get('gist','')}")
            print(f"  工程落法：{p.get('engineering','')}")
            print(f"  经典依据：{', '.join(p.get('canon_refs', []))}")
            return
        print(f"\n==== {c['canon']}（中心指导理念）====")
        print(f"别名：{', '.join(c.get('alias', []))}")
        for p in c.get("parts", []):
            print(f"  {p['part']}：{p['chapters']} 章（{p['count']}）")
        print(f"共 {len(c.get('chapters', []))} 章；用法：daoxue center <章号> 看单章，"
              f"daoxue principles <原则 id> 看落法")
        return

    if action in ("pre", "post"):
        o = dx.office(action)
        if not o:
            print(f"\n无 {action} 层。")
            return
        if term:  # 按课程序位过滤
            secs = dx.sections_of(action, term)
            if not secs:
                print(f"\n{o['canon']}：无课程序位 {term!r}。可用 daoxue {action} 看全部序位。")
                return
            print(f"\n==== {o['canon']}·{term}：{len(secs)} 节 ====")
        else:
            secs = o.get("sections", [])
            print(f"\n==== {o['canon']}（{'前置' if action=='pre' else '后置'}指导思想）====")
            print(f"课义：{o.get('sense','')}")
            print(f"工程映射：{o.get('engineering','')}")
            print("课程序位：" + " → ".join(
                f"{p['phase']}({p['count']})" for p in dx.phases_of(action)))
            print(f"共 {len(secs)} 节：")
        for s in secs:
            print(f"  {s['idx']:>2}. [{s['phase']}/{s['kind']}] {s['name']}")
            print(f"      {s['gist']}")
        return

    if action == "middle":
        print("\n==== 中间二级思想 ====")
        for m in dx.middle():
            print(f"\n-- {m['canon']}（tier {m['tier']}）--")
            print(f"   别名：{', '.join(m.get('alias', []))}")
            print(f"   位置：{m['position']}")
            print(f"   说明：{m['note']}")
            for s in m["sections"]:
                print(f"   {s['idx']:>2}. {s['name']}")
                print(f"      纲宗：{s['gist']}")
                print(f"      工程：{s['engineering']}")
        return

    if action == "fangshu":
        fs = dx.fangshu()
        if not fs:
            print("\n无方术子层。")
            return
        if term and dx.fangshu_item(term):
            x = dx.fangshu_item(term)
            dom = dx.fangshu_domain(x["domain"]) or {}
            p = dx.principle(x.get("principle", "")) or {}
            print(f"\n==== 方术·{dom.get('name','')}：{x['name']}（{x['id']}）====")
            print(f"纲宗：{x['gist']}")
            print(f"详述：{x['detail']}")
            print(f"工程落法：{x['engineering']}")
            print(f"归属治理原则：{p.get('name','')}（{x.get('principle','')}）")
            if x.get("needs_verify"):
                print(f"[存疑] {x['needs_verify']}")
            for b in dx.fangshu_bridges():
                if b.get("fangshu") == x["id"]:
                    print(f"  桥接 → {b['system']}:{b['target']} [{b['relation']}] {b['how']}")
            return
        if term and dx.fangshu_domain(term):
            d = dx.fangshu_domain(term)
            print(f"\n==== 方术·{d['name']}（{d['domain']}）：{d['count']} 条 ====")
            print(f"{d['sense']}")
            for x in d["items"]:
                print(f"  {x['id']:<16} {x['name']}"
                      + ("  [存疑]" if x.get("needs_verify") else ""))
                print(f"      纲宗：{x['gist']}")
                print(f"      工程：{x['engineering']}")
                if x.get("needs_verify"):
                    print(f"      存疑：{x['needs_verify']}")
            return
        if term:
            print(f"\n无方术域或条目 {term!r}。可用域："
                  f"{' / '.join(d['domain'] for d in dx.fangshu_domains())}")
            return
        print("\n==== 方术子层（tier=3：符箓·咒语·画符仪轨·祝由）====")
        print(f"说明：{fs.get('sense','')}")
        print(f"工程映射：{fs.get('engineering','')}")
        for d in dx.fangshu_domains():
            print(f"  {d['domain']:<6} {d['name']:<18} {d['count']} 条  {d['sense']}")
        print(f"共 {sum(len(d.get('items', [])) for d in dx.fangshu_domains())} 条"
              f"（其中 {sum(1 for x in dx.fangshu_items() if x.get('needs_verify'))} 条挂存疑）；"
              f"用法：daoxue fangshu <域>（fu/lu/zhou/fa/you）看条目，"
              f"daoxue fangshu <条目 id> 看单条")
        return

    if action == "principles":
        if term:
            p = dx.principle(term)
            if not p:
                print(f"\n无治理原则 {term!r}。可用 daoxue principles 浏览。")
                return
            chs = dx.chapters_of_principle(p["id"])
            print(f"\n==== {p['name']}（{p['id']}）====")
            print(f"义理纲宗：{p['gist']}")
            print(f"工程落法：{p['engineering']}")
            print(f"经典依据：{', '.join(p.get('canon_refs', []))}")
            if chs:
                print(f"道德经对应章（{len(chs)}）：" + "；".join(
                    f"{c['no']}·{c['theme']}" for c in chs))
            bs = [b for b in dx.bridges() if b["principle"] == p["id"]]
            if bs:
                print("桥接到既有概念系统：")
                for b in bs:
                    print(f"  - {b['system']}:{b['target']} [{b['relation']}] {b['how']}")
            return
        print("\n==== 工程治理原则（由理念落成，可审计）====")
        for p in dx.principles():
            print(f"  {p['id']:<22} {p['name']:<8} 依据 {', '.join(p['canon_refs'])}")
            print(f"      义理：{p['gist']}")
            print(f"      工程：{p['engineering']}")
        return

    if action == "bridge":
        bs = dx.bridges(term)
        print(f"\n==== 理念 → 既有概念系统 桥接边：{len(bs)} 条"
              + (f"（{term}）" if term else "") + " ====")
        for b in bs:
            print(f"  {b['principle']:<22} → {b['system']}:{b['target']}  [{b['relation']}]")
            print(f"      {b['how']}")
        return

    if action == "apply":
        if not term:
            print("\n用法：daoxue apply <系统>（plang / netsys / langref）")
            return
        items = dx.apply_to(term)
        if not items:
            print(f"\n系统 {term!r}：无桥接（可用 plang / netsys / langref）。")
            return
        print(f"\n==== {term} 适用的治理原则：{len(items)} 条 ====")
        for it in items:
            print(f"  {it['name']}（{it['principle']}） → {it['target']} [{it['relation']}]")
            print(f"      依据 {', '.join(it['canon_refs'])}")
            print(f"      {it['how']}")
        return

    if action == "search":
        if not term:
            print("\n用法：daoxue search <关键词>")
            return
        hits = dx.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}")
            print(f"      {h['text']}")
            if h.get("principle"):
                print(f"      落法：{h['principle']}")
        return

    if action == "verify":
        print("\n==== 诚实边界（需核实项）====")
        for v in dx.needs_verify():
            print(f"  - {v['item']}：{v['why']}")
        return

    if action == "stats":
        s = dx.stats()
        print("\n==== 「道枢」概念系统规模 ====")
        for k, v in s.items():
            print(f"  {k:<18} {v}")
        return

    # overview（默认）
    meta = dx.info()
    s = dx.stats()
    print(f"\n==== 「道枢」治理层概念系统（schema {meta.get('schema')}）====")
    print(f"主目录（概念系统）：{meta.get('main_root')}")
    for l in dx.layers():
        print(f"  [{l['role']:<6}] tier{l['tier']}  {l['canon']}  ({l['count']})")
        print(f"           {l['sense']}")
    print(f"\n道德经 {s.get('center_chapters')} 章 / 早坛 {s.get('pre_sections')} 节 / "
          f"晚坛 {s.get('post_sections')} 节 / 二级 {s.get('middle_canons')} 部"
          f"{s.get('middle_sections')} 段")
    print(f"治理原则 {s.get('principle_count')} 条 · 桥接边 {s.get('bridge_count')} 条"
          f"（plang/netsys/langref，构建期校验无悬空）")
    print("诚实边界：" + "；".join(meta.get("honesty", [])))
    print("\n子命令：center [章号] / pre / post / middle / principles [id] / "
          "bridge [系统] / apply <系统> / search <词> / verify / stats")


def _axis_overview(mod, title, subcmd_note):
    """轴型概念系统（quantum/comp/apilab）共用的 overview 输出。"""
    m = mod.info()
    s = mod.stats()
    print(f"\n==== {title}（schema {m.get('schema')}）====")
    print(f"主目录（概念系统）：{m.get('main_root')}")
    print(f"分类轴：{' → '.join(m.get('axes', []))}"
          f"（{s.get('domain_count')} 个分类）")
    for d in mod.domains():
        print(f"  [{d['domain']:<10}] {d['count']:>2}  {d['label']}")
        print(f"         {d.get('note', '')}")
    print(f"概念共 {s.get('concept_total')} 条 · 桥接边 {s.get('bridge_count')} 条"
          f"（构建期校验目标真实存在，无悬空）")
    if m.get("honesty"):
        print("诚实边界：" + m["honesty"])
    if subcmd_note:
        print(f"\n子命令：{subcmd_note}")


def _axis_concepts_of(mod, sysname, term):
    """轴型系统：列出某轴下概念或单概念详情（of <id> 走详情）。"""
    if not term:
        print(f"\n用法：{sysname} domain <轴>（可用 {sysname} domains 浏览）")
        return
    c = mod.of(term)
    if c:
        _print_concept(mod, c)
        return
    cs = mod.concepts_of_domain(term)
    if not cs:
        print(f"\n轴 {term!r}：无该分类或为空。可用 {sysname} domains 浏览。")
        return
    print(f"\n==== 轴 {term}：{len(cs)} 个概念 ====")
    for x in cs:
        print(f"  {x['id']:<22} {x['name']}")
        print(f"      {x['gist']}")


def _print_concept(mod, c):
    """轴型系统：单概念完整视图。"""
    print(f"\n==== {c['name']}（{c['id']}） ====")
    print(f"所属轴：{c.get('domain', '')}")
    print(f"纲宗：{c['gist']}")
    print(f"详述：{c.get('detail', '')}")
    if c.get("standards"):
        print("标准依据：")
        for s in c["standards"]:
            if isinstance(s, dict):
                ref = f"{s.get('kind', '')} {s.get('num', '')}".strip()
                print(f"  - {ref}  {s.get('rfc_title', '') or s.get('name', '')}")
            else:
                print(f"  - {s}")
    if c.get("evidence"):
        ev = c["evidence"]
        print(f"实测证据：{ev.get('source', '')} [{ev.get('status', '')}"
              f" rc={ev.get('returncode', '?')}]")
        kv = ev.get("contract_kv") or {}
        if kv:
            print("  能力契约：" + "，".join(f"{k}={v}" for k, v in kv.items()))
    if c.get("needs_verify"):
        print(f"诚实边界：{c['needs_verify']}")
    bs = mod.bridges_of(c["id"])
    if bs:
        print("桥接到既有概念系统：")
        for b in bs:
            print(f"  - {b['system']}:{b['target']} [{b['relation']}] {b['how']}")


def _axis_bridges(mod, term):
    bs = mod.bridges(term)
    print(f"\n==== 桥接边：{len(bs)} 条" + (f"（{term}）" if term else "") + " ====")
    for b in bs:
        print(f"  {b.get('from', '?'):<28} → {b['system']}:{b['target']}  [{b['relation']}]")
        print(f"      {b['how']}")


def _axis_search(mod, term):
    if not term:
        print("\n用法：search <关键词>")
        return
    hits = mod.search(term)
    print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
    for h in hits:
        print(f"  [{h['where']}] {h['name']}（{h['id']}）")
        print(f"      {h['text']}")


def _axis_verify(mod, title):
    print(f"\n==== {title}·诚实边界（需核实项）====")
    vs = mod.needs_verify()
    if not vs:
        print("  （无——需核实项已清零；已核实项的来源见 standards 子命令）")
        return
    for v in vs:
        print(f"  - {v['item']}：{v['why']}")


def _axis_stats(mod, title):
    s = mod.stats()
    print(f"\n==== {title}·规模统计 ====")
    for k, v in s.items():
        print(f"  {k:<20} {v}")


def cmd_guide(args):
    """一屏操作入口地图（南华真经·逍遥游：无待一步——入口唯一，一屏直达）。

    人体工程学口径（详见 `concepts zhuangzi` 子系统）：
      逍遥游=无待一步（本命令）/ 应帝王=默认即最佳 / 大宗师=意图宗师（失败指路可回退）/
      养生主=不伤（破坏性操作先 snapshot 留痕）。
    """
    from .ergonomics import render_guide, principles_brief
    print(render_guide())
    if getattr(args, "principles", False):
        print("\n用户端人体工程学七原则（南华真经理念 → 工程翻译）：")
        for p in principles_brief():
            print(f"  {p['name']}（{p['canon']}）：{p['gist']}")


def cmd_zhuangzi(args):
    """「南华」用户端概念系统（v0.6.60，CLI 子命令 `zhuangzi`）。

    《南华真经》（庄子 33 篇）为用户端设计的中心指导理念：核心理念三篇
    《逍遥游》（无待一步）/《应帝王》（顺性不抢）/《大宗师》（意图为宗师），
    内篇辅篇四篇补充，外杂选篇 5 条，落成八条可审计的人体工程学原则，
    桥接 daoxue 治理原则与 apilab 接口概念。只读不联网，不复制经典全文。
    """
    from .concepts import zhuangzi as z

    action = getattr(args, "zhuangzi_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "overview":
        info = z.info()
        print(f"\n==== {info.get('title')} ====")
        print(f"经典：{info.get('canon', '')}")
        print(f"诚实边界：{info.get('honesty', '')}")
        print("\n四轴结构：")
        for l in z.layers():
            print(f"  {l['role']:<12} {l['count']:>2}条  {l['canon']}——{l['sense']}")
        uf = z.user_face()
        print(f"\n用户端面实测：CLI 子命令 {uf.get('cli_subcommands')} / "
              f"GUI 窗口 {uf.get('gui_windows')} / webapi ACTIONS {uf.get('webapi_actions')} / "
              f"deno 控制台 v{uf.get('deno_console_version')}")
        print("操作入口：python -m sysweeper guide（一屏入口地图·逍遥游）")
        print("子动作：core / inner / outer / ergonomics / concept <id> / principles [id] / "
              "bridge / userface / verify / stats / search <词>")
        return

    if action in ("core", "inner", "outer", "ergonomics"):
        cs = z.concepts_of_domain(action)
        d = z.domain(action)
        print(f"\n==== {d['label']}（{len(cs)} 条）— {d['note']} ====")
        for c in cs:
            print(f"\n· {c['name']}（{c['id']}）")
            print(f"  篇旨：{c.get('gist', '')}")
            if c.get("detail"):
                print(f"  章旨：{c['detail']}")
            print(f"  落法：{c.get('engineering', '')}")
            if c.get("canon_refs"):
                print(f"  经典依据：{', '.join(c['canon_refs'])}")
        return

    if action == "concept":
        if not term:
            print("\n用法：zhuangzi concept <id>（篇目或工程原则 id）")
            return
        c = z.concept(term)
        if not c:
            print(f"\n无概念 {term!r}。可用 zhuangzi core/inner/outer/ergonomics 浏览。")
            return
        print(f"\n==== {c['name']}（{c['id']}） ====")
        print(f"篇旨：{c.get('gist', '')}")
        if c.get("detail"):
            print(f"章旨：{c['detail']}")
        print(f"落法：{c.get('engineering', '')}")
        bs = z.bridges_of(c["id"])
        if bs:
            print("桥接：")
            for b in bs:
                print(f"  → {b['system']}:{b['target']} [{b['relation']}] {b['how']}")
        return

    if action == "principles":
        if term:
            p = z.principle(term)
            if not p:
                print(f"\n无工程原则 {term!r}。可用 zhuangzi principles 浏览。")
                return
            print(f"\n==== {p['name']}（{p['id']}） ====")
            print(f"理念：{p['gist']}")
            print(f"工程落法：{p['engineering']}")
            print(f"经典依据：{', '.join(p.get('canon_refs', []))}")
            return
        print("\n==== 用户端人体工程学七原则 ====")
        for p in z.principles():
            print(f"\n· {p['name']}（{p['id']}，{', '.join(p.get('canon_refs', []))}）")
            print(f"  理念：{p['gist']}")
            print(f"  落法：{p['engineering']}")
        return

    if action == "bridge":
        bs = z.bridges(term)
        print(f"\n==== 桥接边（{len(bs)} 条{'，按 ' + term + ' 过滤' if term else ''}） ====")
        for b in bs:
            print(f"  {b['from']} → {b['system']}:{b['target']} [{b['relation']}] {b['how']}")
        return

    if action == "userface":
        uf = z.user_face()
        print("\n==== 本仓库用户端面（构建期实测） ====")
        for k, v in uf.items():
            print(f"  {k:<24} {v}")
        return

    if action == "verify":
        nv = z.needs_verify()
        print(f"\n==== 诚实边界（needs_verify：{len(nv)} 项） ====")
        for v in nv:
            print(f"  - [{v['status']}] {v['item']}：{v['note']}")
        return

    if action == "search":
        if not term:
            print("\n用法：zhuangzi search <关键词>")
            return
        hits = z.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}：{h['text']}")
            if h.get("engineering"):
                print(f"      落法：{h['engineering']}")
        return

    if action == "stats":
        _axis_stats(z, "南华")


def cmd_baigong(args):
    """「百工」匠作概念系统（v0.6.61，CLI 子命令 `baigong`）。

    用户指定：在编程语言、编译语言、汇编语言、api、lib、标准、算法等领域，
    凡「具体无解 / 暂时不允许 / 构建程序具体结构」之事，以**墨子、公输般、
    公孙策、鲁班**为理念，可扩大为三教九流。

    四轴：核心理念五偶（core）/ 匠作原则七条（craft）/ 三教九流 12 条
    （schools）/ 工程场景三条（scenes），桥接七个既有概念系统，构建期
    校验无悬空。只读不联网，不复制经典全文。
    """
    from .concepts import baigong as b

    action = getattr(args, "baigong_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "overview":
        info = b.info()
        print(f"\n==== {info.get('title')} ====")
        print(f"理念：{info.get('canon', '')}")
        print(f"诚实边界：{info.get('honesty', '')}")
        print("\n四轴结构：")
        for l in b.layers():
            print(f"  {l['role']:<12} {l['count']:>2}条  {l['canon']}——{l['sense']}")
        uf = b.user_face()
        print(f"\n用户端面实测：CLI 子命令 {uf.get('cli_subcommands')} / "
              f"GUI 窗口 {uf.get('gui_windows')} / webapi ACTIONS {uf.get('webapi_actions')} / "
              f"deno 控制台 v{uf.get('deno_console_version')}")
        print(f"语言面实测：plang {uf.get('lang_total')} 条语言 / probe 实测 "
              f"{uf.get('probe_verified')} 种 / comp 语言编译需要 {uf.get('comp_lang_needs')} 条")
        print("匠作原则七条见：baigong craft（理念 → 可审计工程原则）")
        print("子动作：core / craft / schools / scenes / concept <id> / principles [id] / "
              "bridge / userface / verify / stats / search <词>")
        return

    if action in ("core", "craft", "schools", "scenes"):
        cs = b.concepts_of_domain(action)
        d = b.domain(action)
        print(f"\n==== {d['label']}（{len(cs)} 条）— {d['note']} ====")
        for c in cs:
            print(f"\n· {c['name']}（{c['id']}）")
            print(f"  纲宗：{c.get('gist', '')}")
            if c.get("detail"):
                print(f"  详述：{c.get('detail', '')}")
            print(f"  落法：{c.get('engineering', '')}")
            if c.get("canon_refs"):
                print(f"  理念依据：{', '.join(c['canon_refs'])}")
        return

    if action == "concept":
        if not term:
            print("\n用法：baigong concept <id>（五偶 / 匠作原则 / 教派 / 场景 id）")
            return
        c = b.concept(term)
        if not c:
            print(f"\n无概念 {term!r}。可用 baigong core/craft/schools/scenes 浏览。")
            return
        print(f"\n==== {c['name']}（{c['id']}） ====")
        print(f"纲宗：{c.get('gist', '')}")
        if c.get("detail"):
            print(f"详述：{c.get('detail', '')}")
        print(f"落法：{c.get('engineering', '')}")
        bs = b.bridges_of(c["id"])
        if bs:
            print("桥接：")
            for br in bs:
                print(f"  → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "principles":
        if term:
            p = b.principle(term)
            if not p:
                print(f"\n无匠作原则 {term!r}。可用 baigong principles 浏览。")
                return
            print(f"\n==== {p['name']}（{p['id']}） ====")
            print(f"理念：{p['gist']}")
            print(f"工程落法：{p['engineering']}")
            print(f"理念依据：{', '.join(p.get('canon_refs', []))}")
            return
        print("\n==== 匠作工程七原则（墨子/公输般/公孙策/鲁班 → 工程翻译） ====")
        for p in b.principles():
            print(f"\n· {p['name']}（{p['id']}，{', '.join(p.get('canon_refs', []))}）")
            print(f"  理念：{p['gist']}")
            print(f"  落法：{p['engineering']}")
        return

    if action == "bridge":
        bs = b.bridges(term)
        print(f"\n==== 桥接边（{len(bs)} 条{'，按 ' + term + ' 过滤' if term else ''}） ====")
        for br in bs:
            print(f"  {br['from']} → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "userface":
        uf = b.user_face()
        print("\n==== 本仓库实测面（构建期实测） ====")
        for k, v in uf.items():
            print(f"  {k:<24} {v}")
        return

    if action == "verify":
        nv = b.needs_verify()
        print(f"\n==== 诚实边界（needs_verify：{len(nv)} 项） ====")
        for v in nv:
            print(f"  - [{v['status']}] {v['item']}：{v['note']}")
        return

    if action == "search":
        if not term:
            print("\n用法：baigong search <关键词>")
            return
        hits = b.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}：{h['text']}")
            if h.get("engineering"):
                print(f"      落法：{h['engineering']}")
        return

    if action == "stats":
        _axis_stats(b, "百工")


def cmd_datong(args):
    """「大同」人类文明一体概念系统（v0.6.62，CLI 子命令 `datong`）。

    用户立意：人类命运是一个的，古今中外的宗教哲学都融合进来；「虽然
    人类是一体的，但是想要人类健康科学有序的发展，还是要宣扬天罡元阳、
    地煞元阴的正道，类似科学的，把固液气、电磁波，这六样是正道」；
    「古来唯道独成尊」。

    五轴：文明传统 15（traditions）/ 核心命题 21（theses）/ 正道六象
    6（six）/ 实践形态 12（practices）/ 人间落法九原则（ethics =
    principles），桥接八个既有概念系统，构建期校验无悬空。只读不联网，
    不宣扬任何宗教为真理，不复制经典全文。
    """
    from .concepts import datong as d

    action = getattr(args, "datong_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "overview":
        info = d.info()
        print(f"\n==== {info.get('title')} ====")
        print(f"立意：{info.get('canon', '')}")
        print(f"诚实边界：{info.get('honesty', '')}")
        print("\n五轴结构：")
        for l in d.layers():
            print(f"  {l['role']:<12} {l['count']:>2}条  {l['canon']}——{l['sense']}")
        uf = d.user_face()
        print(f"\n用户端面实测：CLI 子命令 {uf.get('cli_subcommands')} / "
              f"GUI 窗口 {uf.get('gui_windows')} / webapi ACTIONS {uf.get('webapi_actions')} / "
              f"deno 控制台 v{uf.get('deno_console_version')}")
        print(f"语言面实测：plang {uf.get('lang_total')} 条语言 / probe 实测 "
              f"{uf.get('probe_verified')} 种 / comp 语言编译需要 {uf.get('comp_lang_needs')} 条")
        print("人间落法九原则见：datong principles（命题 → 可审计工程原则）")
        print("子动作：traditions / theses / six / practices / concept <id> / principles [id] / "
              "bridge / userface / verify / stats / search <词>")
        return

    if action in ("traditions", "theses", "six", "practices", "ethics"):
        cs = d.concepts_of_domain(action)
        dm = d.domain(action)
        print(f"\n==== {dm['label']}（{len(cs)} 条）— {dm['note']} ====")
        for c in cs:
            print(f"\n· {c['name']}（{c['id']}）")
            print(f"  纲宗：{c.get('gist', '')}")
            if c.get("detail"):
                print(f"  详述：{c.get('detail', '')}")
            print(f"  落法：{c.get('engineering', '')}")
            if c.get("canon_refs"):
                print(f"  理念依据：{', '.join(c['canon_refs'])}")
        return

    if action == "concept":
        if not term:
            print("\n用法：datong concept <id>（传统 / 命题 / 六象 / 实践 / 原则 id）")
            return
        c = d.concept(term)
        if not c:
            print(f"\n无概念 {term!r}。可用 datong traditions/theses/six/practices 浏览。")
            return
        print(f"\n==== {c['name']}（{c['id']}） ====")
        print(f"纲宗：{c.get('gist', '')}")
        if c.get("detail"):
            print(f"详述：{c.get('detail', '')}")
        print(f"落法：{c.get('engineering', '')}")
        bs = d.bridges_of(c["id"])
        if bs:
            print("桥接：")
            for br in bs:
                print(f"  → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "principles":
        if term:
            p = d.principle(term)
            if not p:
                print(f"\n无人间落法原则 {term!r}。可用 datong principles 浏览。")
                return
            print(f"\n==== {p['name']}（{p['id']}） ====")
            print(f"理念：{p['gist']}")
            print(f"工程落法：{p['engineering']}")
            print(f"理念依据：{', '.join(p.get('canon_refs', []))}")
            return
        print("\n==== 人间落法九原则（命题 → 工程翻译） ====")
        for p in d.principles():
            print(f"\n· {p['name']}（{p['id']}，{', '.join(p.get('canon_refs', []))}）")
            print(f"  理念：{p['gist']}")
            print(f"  落法：{p['engineering']}")
        return

    if action == "bridge":
        bs = d.bridges(term)
        print(f"\n==== 桥接边（{len(bs)} 条{'，按 ' + term + ' 过滤' if term else ''}） ====")
        for br in bs:
            print(f"  {br['from']} → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "userface":
        uf = d.user_face()
        print("\n==== 本仓库实测面（构建期实测） ====")
        for k, v in uf.items():
            print(f"  {k:<24} {v}")
        return

    if action == "verify":
        nv = d.needs_verify()
        print(f"\n==== 诚实边界（needs_verify：{len(nv)} 项） ====")
        for v in nv:
            print(f"  - [{v['status']}] {v['item']}：{v['note']}")
        return

    if action == "search":
        if not term:
            print("\n用法：datong search <关键词>")
            return
        hits = d.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}：{h['text']}")
            if h.get("engineering"):
                print(f"      落法：{h['engineering']}")
        return

    if action == "stats":
        _axis_stats(d, "大同")


def cmd_protec(args):
    """「protec」产品（设备设施）长期运行与基本保护概念系统（v0.6.66，CLI 子命令 `protec`）。

    立意（用户原话）：「材料学、热力学、气候学、环境学、物理、化学、生物等以及相关
    对产品（设备设施）长期运行和基本保护的协议和标准查看」。

    五轴：材料耐久(durability) 7 / 电气安全(electrical) 6 / 环境标准(environment) 4 /
    应急保护(emergency) 4 / 基本保护(protection) 7（= principles），桥接七个既有概念系统
    （netsys/datong/zhuangzi/baigong/apilab/comp/quantum），构建期校验无悬空。只读不联网。
    """
    from .concepts import protec as p

    action = getattr(args, "protec_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "overview":
        info = p.info()
        print(f"\n==== {info.get('title')} ====")
        print(f"立意：{info.get('canon', '')}")
        print(f"诚实边界：{info.get('honesty', '')}")
        print("\n五轴结构：")
        for l in p.layers():
            print(f"  {l['role']:<12} {l['count']:>2}条  {l['canon']}——{l['sense']}")
        uf = p.user_face()
        print(f"\n用户端面实测：CLI 子命令 {uf.get('cli_subcommands')} / "
              f"GUI 窗口 {uf.get('gui_windows')} / webapi ACTIONS {uf.get('webapi_actions')} / "
              f"deno 控制台 v{uf.get('deno_console_version')}")
        print(f"语言面实测：plang {uf.get('lang_total')} 条语言 / probe 实测 "
              f"{uf.get('probe_verified')} 种 / comp 语言编译需要 {uf.get('comp_lang_needs')} 条")
        print("子动作：durability / electrical / environment / emergency / protection / "
              "concept <id> / principles [id] / bridge [system] / userface / verify / "
              "stats / search <词>")
        return

    if action in ("durability", "electrical", "environment", "emergency", "protection"):
        cs = p.concepts_of_domain(action)
        dm = p.domain(action)
        print(f"\n==== {dm['label']}（{len(cs)} 条）— {dm['note']} ====")
        for c in cs:
            print(f"\n· {c['name']}（{c['id']}）")
            print(f"  纲宗：{c.get('gist', '')}")
            if c.get("detail"):
                print(f"  详述：{c.get('detail', '')}")
            print(f"  落法：{c.get('engineering', '')}")
            if c.get("canon_refs"):
                print(f"  理念依据：{', '.join(c['canon_refs'])}")
        return

    if action == "concept":
        if not term:
            print("\n用法：protec concept <id>（材料耐久/电气安全/环境标准/应急保护/保护原则 id）")
            return
        c = p.concept(term)
        if not c:
            print(f"\n无概念 {term!r}。可用 protec durability/electrical/environment/"
                  f"emergency/protection 浏览。")
            return
        print(f"\n==== {c['name']}（{c['id']}） ====")
        print(f"纲宗：{c.get('gist', '')}")
        if c.get("detail"):
            print(f"详述：{c.get('detail', '')}")
        print(f"落法：{c.get('engineering', '')}")
        bs = p.bridges_of(c["id"])
        if bs:
            print("桥接：")
            for br in bs:
                print(f"  → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "principles":
        if term:
            pr = p.principle(term)
            if not pr:
                print(f"\n无保护原则 {term!r}。可用 protec principles 浏览。")
                return
            print(f"\n==== {pr['name']}（{pr['id']}） ====")
            print(f"理念：{pr['gist']}")
            print(f"工程落法：{pr['engineering']}")
            print(f"理念依据：{', '.join(pr.get('canon_refs', []))}")
            return
        print("\n==== 七条基本保护工程原则（protection = principles） ====")
        for pr in p.principles():
            print(f"\n· {pr['name']}（{pr['id']}，{', '.join(pr.get('canon_refs', []))}）")
            print(f"  理念：{pr['gist']}")
            print(f"  落法：{pr['engineering']}")
        return

    if action == "bridge":
        bs = p.bridges(term)
        print(f"\n==== 桥接边（{len(bs)} 条"
              f"{'，按 ' + term + ' 过滤' if term else ''}） ====")
        for br in bs:
            print(f"  {br['from']} → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "userface":
        uf = p.user_face()
        print("\n==== 本仓库实测面（构建期实测） ====")
        for k, v in uf.items():
            print(f"  {k:<24} {v}")
        return

    if action == "verify":
        nv = p.needs_verify()
        print(f"\n==== 诚实边界（needs_verify：{len(nv)} 项） ====")
        for v in nv:
            print(f"  - [{v['status']}] {v['item']}：{v['note']}")
        return

    if action == "search":
        if not term:
            print("\n用法：protec search <关键词>")
            return
        hits = p.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}：{h['text']}")
            if h.get("engineering"):
                print(f"      落法：{h['engineering']}")
        return

    if action == "stats":
        _axis_stats(p, "protec")


def cmd_sciences(args):
    """「sciences」自然科学概念系统（v0.6.67，CLI 子命令 `sciences`）。

    八轴：材料学(materials) 4 / 热力学(thermodynamics) 4 / 气候学(climatology) 4 /
    环境学(environmental) 3 / 物理(physics) 3 / 化学(chemistry) 3 / 生物(biology) 4 /
    科学方法(methodology) 7（= principles），共 32 概念；作为 protec 工程保护的科学底座，
    桥接 protec/量子/编译/接口/百工/大同/组网七个既有概念系统，构建期校验无悬空。只读不联网。
    """
    from .concepts import sciences as sc

    action = getattr(args, "sciences_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "overview":
        info = sc.info()
        print(f"\n==== {info.get('title')} ====")
        print(f"立意：{info.get('canon', '')}")
        print(f"诚实边界：{info.get('honesty', '')}")
        print("\n八轴结构：")
        for l in sc.layers():
            print(f"  {l['role']:<12} {l['count']:>2}条  {l['canon']}——{l['sense']}")
        uf = sc.user_face()
        print(f"\n用户端面实测：CLI 子命令 {uf.get('cli_subcommands')} / "
              f"GUI 窗口 {uf.get('gui_windows')} / webapi ACTIONS {uf.get('webapi_actions')} / "
              f"deno 控制台 v{uf.get('deno_console_version')}")
        print(f"语言面实测：plang {uf.get('lang_total')} 条语言 / probe 实测 "
              f"{uf.get('probe_verified')} 种 / comp 语言编译需要 {uf.get('comp_lang_needs')} 条")
        print("子动作：materials / thermodynamics / climatology / environmental / physics / "
              "chemistry / biology / methodology / concept <id> / principles [id] / "
              "bridge [system] / userface / verify / stats / search <词>")
        return

    if action in ("materials", "thermodynamics", "climatology", "environmental",
                  "physics", "chemistry", "biology", "methodology"):
        cs = sc.concepts_of_domain(action)
        dm = sc.domain(action)
        print(f"\n==== {dm['label']}（{len(cs)} 条）— {dm['note']} ====")
        for c in cs:
            print(f"\n· {c['name']}（{c['id']}）")
            print(f"  纲宗：{c.get('gist', '')}")
            if c.get("detail"):
                print(f"  详述：{c.get('detail', '')}")
            print(f"  落法：{c.get('engineering', '')}")
            if c.get("canon_refs"):
                print(f"  理念依据：{', '.join(c['canon_refs'])}")
        return

    if action == "concept":
        if not term:
            print("\n用法：sciences concept <id>（各学概念 / 方法原则 id）")
            return
        c = sc.concept(term)
        if not c:
            print(f"\n无概念 {term!r}。可用 sciences materials/…/methodology 浏览。")
            return
        print(f"\n==== {c['name']}（{c['id']}） ====")
        print(f"纲宗：{c.get('gist', '')}")
        if c.get("detail"):
            print(f"详述：{c.get('detail', '')}")
        print(f"落法：{c.get('engineering', '')}")
        bs = sc.bridges_of(c["id"])
        if bs:
            print("桥接：")
            for br in bs:
                print(f"  → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "principles":
        if term:
            pr = sc.principle(term)
            if not pr:
                print(f"\n无方法原则 {term!r}。可用 sciences principles 浏览。")
                return
            print(f"\n==== {pr['name']}（{pr['id']}） ====")
            print(f"理念：{pr['gist']}")
            print(f"工程落法：{pr['engineering']}")
            print(f"理念依据：{', '.join(pr.get('canon_refs', []))}")
            return
        print("\n==== 科学方法七原则（methodology = principles） ====")
        for pr in sc.principles():
            print(f"\n· {pr['name']}（{pr['id']}，{', '.join(pr.get('canon_refs', []))}）")
            print(f"  理念：{pr['gist']}")
            print(f"  落法：{pr['engineering']}")
        return

    if action == "bridge":
        bs = sc.bridges(term)
        print(f"\n==== 桥接边（{len(bs)} 条"
              f"{'，按 ' + term + ' 过滤' if term else ''}） ====")
        for br in bs:
            print(f"  {br['from']} → {br['system']}:{br['target']} [{br['relation']}] {br['how']}")
        return

    if action == "userface":
        uf = sc.user_face()
        print("\n==== 本仓库实测面（构建期实测） ====")
        for k, v in uf.items():
            print(f"  {k:<24} {v}")
        return

    if action == "verify":
        nv = sc.needs_verify()
        print(f"\n==== 诚实边界（needs_verify：{len(nv)} 项） ====")
        for v in nv:
            print(f"  - [{v['status']}] {v['item']}：{v['note']}")
        return

    if action == "search":
        if not term:
            print("\n用法：sciences search <关键词>")
            return
        hits = sc.search(term)
        print(f"\n==== 检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['where']}] {h['name']}：{h['text']}")
            if h.get("engineering"):
                print(f"      落法：{h['engineering']}")
        return

    if action == "stats":
        _axis_stats(sc, "sciences")


def cmd_concepts(args):
    """概念系统中心（v0.6.62）：九个概念系统的统一入口。

    已登记：plang / netsys / daoxue / quantum / comp / apilab / zhuangzi /
    baigong / datong——同一骨架（数据层 data/concepts/*.json + 只读层
    concepts/*.py + CLI/GUI 入口）。

    子命令：overview（默认）/ search <词> / show <系统>。只读不联网。
    """
    from . import concepts as C

    action = getattr(args, "concepts_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "search":
        if not term:
            print("\n用法：concepts search <关键词>")
            return
        hits = C.search_all(term)
        print(f"\n==== 跨系统检索 {term!r}：{len(hits)} 条 ====")
        for h in hits:
            print(f"  [{h['system']}] {h.get('name', '')}"
                  + (f"（{h['where']}）" if h.get("where") else ""))
            print(f"      {h.get('text', '')}")
        return

    if action == "show":
        if not term:
            print(f"\n用法：concepts show <系统>（{' / '.join(C.systems())}）")
            return
        if term not in C.systems():
            print(f"\n系统 {term!r} 未登记。可用：{' / '.join(C.systems())}")
            return
        mod = C.module(term)
        meta = mod.info()
        st = mod.stats()
        print(f"\n==== {meta.get('title', term)} ====")
        print(f"主目录（概念系统）：{meta.get('main_root')}")
        print(f"定位：{C.TAGLINES.get(term, '')}")
        print(f"分类轴：{' → '.join(meta.get('axes', []))}")
        print(f"规模：{st}")
        print(f"诚实边界：{meta.get('honesty', '')}")
        print(f"\n进入该系统：CLI `{term}` / GUI「"
              + {"quantum": "量子理念", "comp": "编译工具链",
                 "apilab": "接口 API", "daoxue": "道枢治理观"}.get(term, term)
              + "」")
        return

    if action == "topo":
        t = C.topo()
        total_internal = sum(t["out"].values())
        total_external = sum(t["external"].values())
        print("\n==== 跨系统桥接拓扑（数据驱动，自各 taxonomy 实测）====")
        print(f"{len(t['systems'])} 个系统 / 共 {total_internal + total_external} 条桥接"
              f"（系统内部 {total_internal} + 外部 {total_external}："
              + "、".join(f"{k}×{v}" for k, v in sorted(t["external"].items()))
              + "）")
        print(f"\n{'系统':<9}{'出边':>5}{'入边':>5}  角色")
        role = {"netsys": "纯材料层（被引用，不主动桥接）",
                "plang": "纯材料层（被引用，不主动桥接）",
                "datong": "综摄叶节点（向外指，已获 6 系统 10 条回链）"}
        for s in t["systems"]:
            print(f"{s:<9}{t['out'][s]:>5}{t['in'][s]:>5}  {role.get(s, '')}")
        syss = t["systems"]
        print(f"\n桥接矩阵（行=源系统 → 列=目标系统，数字=边数）")
        print("        " + " ".join(f"{s[:4]:>4}" for s in syss))
        for s in syss:
            row = " ".join(f"{t['edge'][(s, d)]:>4}" for d in syss)
            print(f"  {s[:4]:<4} {row}")
        print("\n提示：concepts overview 看九系统总览；concepts show <系统> 看单系统")
        return

    # overview（默认）
    print("\n==== 概念系统中心（以仓库 wordbuddy-github 为主目录）====")
    for e in C.overview():
        print(f"\n· {e['system']}（{e['version']}）  {e['title']}")
        print(f"    {e['tagline']}")
        print(f"    规模：{e['stats']}")
    print(f"\n共 {len(C.systems())} 个系统；concepts search <词> 跨系统检索，"
          f"concepts show <系统> 看单系统")


def cmd_quantum(args):
    """量子理念概念系统（v0.6.65）：以仓库 wordbuddy-github 为主目录，
    按量子态表示→线路→算法→硬件→纠错→网络→工具链→经典模拟与语义八域登记 66 个概念，
    标准（OpenQASM 3 / QIR / ISO-IEC 4879 / IEEE 7130 / ITU-T Y.3800 /
    ETSI QKD 014 / FIPS PQC）逐条标注核实状态；31 条桥接边接到
    plang / netsys / daoxue / datong，构建期校验无悬空。

    本仓库为经典系统工程工具箱：不含量子硬件探针、不接入量子设备、
    不在真实量子硬件上执行量子线路，只做理念与标准登记（qsim 域为经典模拟器，
    O(2ⁿ) 墙内 ≤6 比特）。只读不联网。

    子命令：overview / domains / domain <域> / of <id> / standards / bridge [系统] /
    search <词> / verify / stats / vm <程序|arch> / qudit [d] [value]。
    vm 动作为量子虚拟机入口（native/quantum.py，v0.6.69）：态矢量模拟执行内置
    量子程序（bell/ghz/teleport/grover2q/bv2/superposition），arch 为量子架构
    基座演示（数字转换门 / CPU↔闪存不间断交换 / tan·ctan 返回 / π 数据链路缓冲）。
    qudit 动作为多位元 qudit 入口（native/qudit.py，0031 轮）：d 级系统
    log₂(d) 比特容量 + 同位能级散逸（T1 振幅阻尼 / T2 相位阻尼）+ log 值交换
    在散逸下的解码漂移表——经典数值模拟，不宣称量子优势。
    """
    from .concepts import quantum as qm

    action = getattr(args, "quantum_action", "overview") or "overview"
    raw_term = getattr(args, "term", "") or ""
    if isinstance(raw_term, list):
        term = " ".join(raw_term).strip()
    else:
        term = str(raw_term).strip()

    if action == "vm":
        # 量子虚拟机（native/quantum.py）：态矢量模拟 + 程序 IR + 架构基座演示
        from .native import quantum as qvm
        prog = term or "bell"
        if prog.lower() == "arch":
            ok, msg = qvm.architecture_report()
            print(("\n" + msg) if ok else ("\n[失败] " + (msg or "架构演示失败")))
            return
        try:
            res = qvm.run_named(prog, shots=int(getattr(args, "shots", 1024) or 1024),
                                seed=getattr(args, "seed", None))
        except qvm.QuantumError as e:
            print(f"\n[失败] {e}")
            if getattr(e, "hint", ""):
                print(f"提示：{e.hint}")
            return
        print("\n", res["program"])
        print("shots:", res["shots"], "seed:", res["seed"])
        for k, v in sorted(res["counts"].items()):
            print(f"  {k}: {v}  (P={res['probabilities'][k]:.4f})")
        return

    if action == "qudit":
        # 多位元 qudit 报告（native/qudit.py）：d 级系统 + 同位能级散逸 + log 值交换
        from .native import qudit as qd
        d = 5
        value = 6.0
        parts = term.split()
        if parts:
            try:
                d = int(parts[0])
            except ValueError:
                print(f"\n[失败] d 须为整数（收到 {parts[0]!r}）")
                return
        if len(parts) > 1:
            try:
                value = float(parts[1])
            except ValueError:
                print(f"\n[失败] value 须为实数（收到 {parts[1]!r}）")
                return
        if not 2 <= d <= qd.MAX_D:
            print(f"\n[失败] d 须在 [2, {qd.MAX_D}]（d×d 复矩阵，纯 Python 墙），收到 {d}")
            return
        vmax = 2.0 ** (d - 1)
        if not 1.0 <= value <= vmax:
            print(f"\n[失败] d={d} 时 value 须在 [1, {vmax:g}]（μ=log₂(value) 落在能级 "
                  f"[0,{d - 1}] 内，越界将被截断而失真），收到 {value}")
            return
        try:
            print("\n", qd.qudit_report(d, value))
        except qd.QuditError as exc:
            print(f"\n[失败] {exc}")
        return

    if action == "qudreg":
        # 多位元寄存器报告（native/qudit.py）：结合 PiLink 内存交换参数覆盖 8/16/64/128 位元
        from .native import qudit as qd
        width = 64
        d = 8
        gamma = 0.0
        parts = term.split()
        if parts:
            try:
                width = int(parts[0])
            except ValueError:
                print(f"\n[失败] width 须为整数（收到 {parts[0]!r}）")
                return
        if len(parts) > 1:
            try:
                d = int(parts[1])
            except ValueError:
                print(f"\n[失败] d 须为整数（收到 {parts[1]!r}）")
                return
        if len(parts) > 2:
            try:
                gamma = float(parts[2])
            except ValueError:
                print(f"\n[失败] gamma 须为实数（收到 {parts[2]!r}）")
                return
        try:
            print("\n", qd.register_report(width, d, gamma=gamma))
        except qd.QuditError as exc:
            print(f"\n[失败] {exc}")
        return

    if action == "qudexp":
        # 寄存器级多位元往返耗散实验（native/qudit.py）：BER 随 γ 扫描，可复现
        from .native import qudit as qd
        width = 64
        gamma = 0.0
        seed = 0
        samples = 24
        parts = term.split()
        if parts:
            try:
                width = int(parts[0])
            except ValueError:
                print(f"\n[失败] width 须为整数（收到 {parts[0]!r}）")
                return
        if len(parts) > 1:
            try:
                gamma = float(parts[1])
            except ValueError:
                print(f"\n[失败] gamma 须为实数（收到 {parts[1]!r}）")
                return
        if len(parts) > 2:
            try:
                seed = int(parts[2])
            except ValueError:
                print(f"\n[失败] seed 须为整数（收到 {parts[2]!r}）")
                return
        if len(parts) > 3:
            try:
                samples = int(parts[3])
            except ValueError:
                print(f"\n[失败] samples 须为正整数（收到 {parts[3]!r}）")
                return
        try:
            rows = qd.register_experiment(width, 8, seed=seed, n_samples=samples)
            print(f"\n== qudit 寄存器级耗散实验（{width} bit → {rows[0]['n_qudits']} 个 d=8 qudit，"
                  f"每 γ {samples} 样本）==")
            print(f"{'γ':>6} {'平均BER':>10} {'最大BER':>10}")
            for r in rows:
                print(f"{r['gamma']:>6.2f} {r['ber_mean']:>10.4f} {r['ber_max']:>10.4f}")
            plot_path = getattr(args, "plot", None)
            if plot_path:
                out = qd.register_experiment_plot(width, 8, seed=seed, n_samples=samples,
                                                 out_path=plot_path)
                print(f"\n✓ BER-γ 曲线已写入（纯标准库 SVG）：{out}")
        except qd.QuditError as exc:
            print(f"\n[失败] {exc}")
        return

    if action == "bitconv":
        # 降维升维位元转化（native/qudit.py）：W 位经典整数 → N 个 d 级 qudit 升维，
        # 再降维回位；精确离散升维↔降维同构 R∘E=I（γ=0 无损），γ>0 量化耗散损失。
        from .native import qudit as qd
        show_table = getattr(args, "table", False)
        if show_table:
            try:
                rows = qd.bit_convert_table()
                print("\n== 降维升维位元转化：全位宽维度画像（d=8，每 qudit 3 bit）==")
                print(f"{'位宽':>5} {'qudit数':>7} {'升维比':>7} {'降维比':>7} "
                      f"{'总容量bit':>10} {'余量bit':>7} {'联合态维数(不物化)':>26}")
                for r in rows:
                    jd = r["joint_dimension"]
                    jds = f"{jd:.3e}" if jd >= 1e15 else str(jd)
                    print(f"{r['width_bits']:>5} {r['n_qudits']:>7} "
                          f"{r['bits_per_carrier']:>7.3f} {r['reduction_factor']:>7.3f} "
                          f"{r['total_capacity_bits']:>10.1f} {r['waste_bits']:>7.1f} {jds:>26}")
                print("\n诚实边界：升维/降维精确部分同构无损；联合态维数仅声明、绝不物化；"
                      "不宣称量子优势。")
            except qd.QuditError as exc:
                print(f"\n[失败] {exc}")
            return
        width = 64
        value = 41
        gamma = 0.0
        d = 8
        parts = term.split()
        if parts:
            try:
                width = int(parts[0])
            except ValueError:
                print(f"\n[失败] width 须为整数（收到 {parts[0]!r}）")
                return
        if len(parts) > 1:
            try:
                value = int(parts[1])
            except ValueError:
                print(f"\n[失败] value 须为整数（收到 {parts[1]!r}）")
                return
        if len(parts) > 2:
            try:
                gamma = float(parts[2])
            except ValueError:
                print(f"\n[失败] gamma 须为实数（收到 {parts[2]!r}）")
                return
        if len(parts) > 3:
            try:
                d = int(parts[3])
            except ValueError:
                print(f"\n[失败] d 须为整数（收到 {parts[3]!r}）")
                return
        try:
            prof = qd.dimension_profile(width, d)
            print(f"\n== 降维升维位元转化（{width} bit → {prof['n_qudits']} 个 d={d} qudit）==")
            print(f"升维比 bits_per_carrier = log2({d}) = {prof['bits_per_carrier']:.4f} bit/qudit")
            print(f"降维比 reduction_factor = {width}/{prof['n_qudits']} = {prof['reduction_factor']:.4f} bit/qudit")
            print(f"总容量 = {prof['total_capacity_bits']:.3f} bit（≥ {width} bit）；余量 {prof['waste_bits']:.3f} bit")
            print(f"联合态维数 = {prof['joint_dimension']}（仅声明，不物化）")
            r = qd.bit_convert(value, width, d, gamma=gamma)
            print(f"\n输入 value = {r['value']}")
            print(f"升维 digits_in  = {r['digits_in']}")
            if gamma:
                print(f"降维 digits_out = {r['digits_out']}（γ={gamma} 耗散+测量）")
            else:
                print(f"降维 digits_out = {r['digits_out']}（γ=0 精确同构）")
            print(f"解码 decoded = {r['decoded']}；符号误码率 BER = {r['ber']:.4f}")
            print(f"R∘E == I（无损）: {r['lossless']}")
        except qd.QuditError as exc:
            print(f"\n[失败] {exc}")
        return

    if action == "domains":
        print("\n==== 量子理念八域 ====")
        for d in qm.domains():
            print(f"  {d['domain']:<10} {d['count']:>2}  {d['label']}")
            print(f"         {d['note']}")
        return

    if action == "domain":
        _axis_concepts_of(qm, "quantum", term)
        return

    if action == "of":
        if not term:
            print("\n用法：quantum of <概念 id>（如 qubit / shor / surface-code）")
            return
        c = qm.of(term)
        if not c:
            print(f"\n概念 {term!r}：不在概念系统中。可用 quantum domains 浏览。")
            return
        _print_concept(qm, c)
        return

    if action == "standards":
        print("\n==== 标准登记册（status: verified=本轮核实 / needs_verify=待核实）====")
        for s in qm.standards():
            print(f"  [{s['status']:<12}] {s['name']}（{s['id']}）[{s.get('kind', '')}]")
            print(f"      {s.get('note', '')}")
            if s.get("source"):
                print(f"      来源：{s['source']}")
        return

    if action == "bridge":
        _axis_bridges(qm, term)
        return

    if action == "search":
        _axis_search(qm, term)
        return

    if action == "verify":
        _axis_verify(qm, "量子理念")
        return

    if action == "stats":
        _axis_stats(qm, "量子理念")
        return

    # overview（默认）
    _axis_overview(
        qm, "量子理念概念系统",
        "domains / domain <域> / of <id> / standards / bridge [系统] / "
        "search <词> / verify / stats")


def cmd_comp(args):
    """编译与工具链概念系统（v0.6.59）：以仓库 wordbuddy-github 为主目录，
    把「公开的计算机编程语言和编译需要」按七轴组织——编译流水线(9)→
    工具链(12)→构建形态(9)→产物形态(8)→语言编译需要(16)→黑箱逆向(6)→
    位宽与寻址世代(6)，共 66 个概念，67 条桥接边接到 plang / daoxue /
    datong / netsys / llvm（工具与目标三元组矩阵）。

    诚实边界：语言编译需要仅对 plang probe 实测通过的 15 种语言逐条登记
    明细（驱动/产物/证据），其余 146 种汇总为一条 needs_verify，不臆造。
    本概念系统只读登记，不驱动任何真实编译。只读不联网。

    子命令：overview / domains / domain <轴> / of <id> / need <语言> / needs /
    bridge [系统] / search <词> / verify / stats。
    """
    from .concepts import comp as cp

    action = getattr(args, "comp_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "domains":
        print("\n==== 编译七轴 ====")
        for d in cp.domains():
            print(f"  {d['domain']:<10} {d['count']:>2}  {d['label']}")
            print(f"         {d['note']}")
        return

    if action == "domain":
        _axis_concepts_of(cp, "comp", term)
        return

    if action == "of":
        if not term:
            print("\n用法：comp of <概念 id>（如 pipeline-overview / need-python）")
            return
        c = cp.of(term)
        if not c:
            print(f"\n概念 {term!r}：不在概念系统中。可用 comp domains 浏览。")
            return
        _print_concept(cp, c)
        return

    if action == "need":
        if not term:
            print("\n用法：comp need <语言>（如 python / rust / makefile）")
            return
        c = cp.lang_need(term)
        if not c:
            print(f"\n语言 {term!r}：无编译需要登记（可用 comp needs 看已登记的）。")
            return
        _print_concept(cp, c)
        return

    if action == "needs":
        print("\n==== 语言编译需要（plang probe 实测通过的逐条登记）====")
        for c in cp.verified_lang_needs():
            print(f"  {c.get('lang', c['id']):<12} 驱动：{c.get('driver', '')}")
            print(f"  {'':<12} 产物：{c.get('artifact', '')}")
        nv = cp.needs_verify()
        for v in nv:
            print(f"\n  [待核实] {v['item']}：{v['why']}")
        return

    if action == "bridge":
        _axis_bridges(cp, term)
        return

    if action == "search":
        _axis_search(cp, term)
        return

    if action == "verify":
        _axis_verify(cp, "编译与工具链")
        return

    if action == "stats":
        _axis_stats(cp, "编译与工具链")
        return

    # overview（默认）
    _axis_overview(
        cp, "编译与工具链概念系统",
        "domains / domain <轴> / of <id> / need <语言> / needs / bridge [系统] / "
        "search <词> / verify / stats")


def cmd_apilab(args):
    """接口 API 概念系统（v0.6.59）：以仓库 wordbuddy-github 为主目录，
    按风格→规约→传输→认证→仓库接口面五轴登记 32 个概念；RFC 依据
    （5280/6455/6749/6750/7519/7617/9000/9110/9112/9113/9114/9293）经
    本仓库 rfc_catalog 交叉验证；repo-face 轴以当前仓库实测事实登记
    （103 个 CLI 子命令 / webapi 29 个 JSONL ACTIONS，构建时从源码读出）。

    红线：令牌禁入 URL/localStorage、私钥不明文、访问令牌短时效 + 服务端刷新。
    只读不联网。

    子命令：overview / domains / domain <轴> / of <id> / repo / rfc / bridge [系统] /
    search <词> / verify / stats。
    """
    from .concepts import apilab as ab

    action = getattr(args, "apilab_action", "overview") or "overview"
    term = (getattr(args, "term", "") or "").strip()

    if action == "domains":
        print("\n==== 接口 API 五轴 ====")
        for d in ab.domains():
            print(f"  {d['domain']:<10} {d['count']:>2}  {d['label']}")
            print(f"         {d['note']}")
        return

    if action == "domain":
        _axis_concepts_of(ab, "apilab", term)
        return

    if action == "of":
        if not term:
            print("\n用法：apilab of <概念 id>（如 rest / auth-oauth2 / repo-webapi）")
            return
        c = ab.of(term)
        if not c:
            print(f"\n概念 {term!r}：不在概念系统中。可用 apilab domains 浏览。")
            return
        _print_concept(ab, c)
        return

    if action == "repo":
        f = ab.repo_facts()
        print("\n==== 本仓库接口面（构建时实测，漂移时重建）====")
        for k, v in f.items():
            print(f"  {k}:")
            if isinstance(v, int):
                print(f"      {v}")
            else:
                print(f"      {v}")
        return

    if action == "rfc":
        print("\n==== 接口概念引用的 RFC（均经 rfc_catalog 交叉验证）====")
        for s in ab.standards():
            if s.get("kind") != "RFC":
                continue
            print(f"  RFC {s.get('num', '?'):<6} [{s.get('from', '')}] {s.get('rfc_title', '')}")
        return

    if action == "bridge":
        _axis_bridges(ab, term)
        return

    if action == "search":
        _axis_search(ab, term)
        return

    if action == "verify":
        _axis_verify(ab, "接口 API")
        return

    if action == "stats":
        _axis_stats(ab, "接口 API")
        return

    # overview（默认）
    _axis_overview(
        ab, "接口 API 概念系统",
        "domains / domain <轴> / of <id> / repo / rfc / bridge [系统] / "
        "search <词> / verify / stats")


def cmd_netlink(args):
    """多种网络链接协议 + 多设备自组网/人机交互 + 按网络隐私验证 + 同人资源共享。

    四个能力域，全部只读优先、默认非变更：
      list      : 链接协议注册表（TCP/UDP/RFCOMM/串口/BLE/802.15.4）与本机能力
      serve     : 启用本地自组网（>1 台设备自己通信；命令通道只有只读安全命令）
      discover  : 发现本网段内其他设备
      msg       : 设备间人机交互消息（仅回显）
      auth      : 按网络维度的隐私验证（两项以上个人信息，原始值不保存，可重连）
      reshare   : 同人登录的多设备资源共享（算力/网络共享，个人数据与资产不共享）
    """
    from . import registry
    from .native import netauth, netlink, reshare

    act = getattr(args, "netlink_action", None) or "list"

    if act == "list":
        ok, msg = netlink.link_report()
        print("\n==== 多种网络链接协议（按各自协议与接口引用权威文档） ====")
        print(msg)
        ok2, msg2 = netlink.mesh_report()
        print("\n-- 自组网就绪态 --")
        print(msg2)
        tasks = [t for t in registry.all_tasks()
                 if t.id in ("net_link_protocols", "net_mesh_serve",
                             "net_mesh_discover", "net_mesh_hci",
                             "net_auth_setup", "net_reshare")]
        print(f"\n-- 相关任务（{len(tasks)} 项）--")
        for t in tasks:
            print(f"   • {t.id:<20} [{t.platform}/{t.risk}]"
                  f"{'[opt-in] ' if t.opt_in else ''}{t.display_title()}")
        return

    if act == "serve":
        ok, msg = netlink.mesh_serve()
        print(f"\n自组网启动: {'成功' if ok else '未启动'} — {msg}")
        ok2, msg2 = netlink.mesh_discover()
        print(f"邻居发现: {msg2}")
        print("\n提示：命令通道只接受 info/ping/probe/msg，绝不执行对端发来的任意命令。")
        return

    if act == "discover":
        ok, msg = netlink.mesh_discover()
        print(f"\n设备发现（只读）: {msg}")
        return

    if act == "msg":
        text = getattr(args, "text", "") or "你好，来自 sysweeper 的人机交互消息"
        ok, msg = netlink.mesh_send_msg(text)
        print(f"\n消息通道: {'已送达' if ok else '未送达'} — {msg}")
        inbox = netlink.mesh_inbox()
        print(f"会话收件箱: {len(inbox)} 条（仅内存，不落盘）")
        for e in inbox[-5:]:
            print(f"   · {e}")
        return

    if act == "auth":
        ok, msg = netauth.netauth_report()
        print("\n==== 按网络维度的隐私验证 ====")
        print(msg)
        ok2, msg2 = netauth.netauth_demo()
        print(f"\n-- 往返演示（假数据，不落盘）--\n{msg2}")
        print("\n用法：netauth.store(path, net_id, {'name':..., 'id_number':...}) 设置；")
        print("      netauth.auto_reconnect(path, net_id, {...}) 下次启动重连；")
        print("      只落盘 salt+派生令牌+字段标签，原始个人信息绝不保存。")
        return

    if act == "reshare":
        ok, msg = reshare.reshare_report()
        print("\n==== 同人设备资源共享（算力共享，数据不共享） ====")
        print(msg)
        ok2, msg2 = reshare.reshare_demo()
        print(f"\n-- 边界演示（临时目录，不落盘真实数据）--\n{msg2}")
        print("\n边界：只共享 CPU/内存/GPU/NPU/TPU/网络；"
              "个人数据、凭据、密钥、钱包等永不共享，防他人盗用互联互通能力。")
        return

    print(f"未知动作 {act!r}（可选：list/serve/discover/msg/auth/reshare）")


def cmd_thirdparty(args):
    """导入的第三方网络互联互通 / 硬件优化 / 开源下载 引用（只读登记，不打包二进制）。

      list      : 全部第三方引用清单（名称/许可证/用途归类）
      interop   : 网络互联互通共享资源（p2wlan/dae/gfw-pac/v2rayN）
      hw        : 硬件优化（DLSS5-Swapper，由用户选择）
      download  : 开源下载软件（aria2）
      cdn-p2p   : CDN / P2P 开关说明（落地参考 aria2）
      licenses  : 第三方许可证引用来源汇总（详见仓库 licenses/ 文件夹）
    """
    from . import registry
    from .native import thirdparty

    act = getattr(args, "thirdparty_action", None) or "list"
    ok, msg = thirdparty.thirdparty_report(act)
    print(f"\n==== 第三方引用：{act} ====")
    print(msg)
    if act in ("list", "interop", "hw", "download", "licenses", "cdn-p2p"):
        ids = {
            "interop": ("net_interop_refs", "net_interop_cdn_p2p"),
            "hw": ("hw_dlss_swapper",),
            "download": ("hw_dl_open_download",),
            "licenses": ("any_interop_policy",),
            "cdn-p2p": ("net_interop_cdn_p2p", "hw_dl_open_download"),
            "list": ("net_interop_refs", "net_interop_cdn_p2p", "hw_dlss_swapper",
                     "hw_dl_open_download", "any_interop_policy"),
        }.get(act, ())
        tasks = [t for t in registry.all_tasks() if t.id in ids]
        if tasks:
            print(f"\n-- 相关任务（{len(tasks)} 项，默认关闭需 --yes）--")
            for t in tasks:
                print(f"   • {t.id:<22} [{t.platform}/{t.risk}]"
                      f"{'[opt-in] ' if t.opt_in else ''}{t.display_title()}")
    return


def cmd_openwrt(args):
    """OpenWrt 路由器系统只读接口（v0.5.20/0.5.21）：

      list     : 能力总览（探测 + UCI + 包 + 网络 + 服务 + 防火墙 + 无线 + DHCP + 存储 + 构建参考）
      detect   : 板型/固件识别
      uci      : UCI 配置只读审计（不打印 secret 明文）
      pkgs     : 已装软件包盘点（opkg/apk 自适应）
      network  : 网络接口只读报告
      firewall : 防火墙只读报告（/etc/config/firewall）
      wireless : 无线只读报告（/etc/config/wireless，不回显密码）
      dhcp     : DHCP/DNS 只读报告（/etc/config/dhcp）
      storage  : 存储只读报告（fstab + df）
      build    : 构建系统参考（ImageBuilder/SDK/feeds，仅文档）
      write    : 写操作安全指引（sysupgrade/包管理/uci set/服务启停；只预检+命令文本，绝不执行）
    非 OpenWrt 环境优雅降级为指引（说明需在路由器上运行）。
    """
    from . import registry
    from .native import openwrt, openwrt_write

    act = getattr(args, "openwrt_action", None) or "list"
    dispatch = {
        "list": openwrt.openwrt_report,
        "detect": openwrt.openwrt_detect_report,
        "uci": openwrt.openwrt_uci_report,
        "pkgs": openwrt.openwrt_pkgs_report,
        "network": openwrt.openwrt_network_report,
        "firewall": openwrt.openwrt_firewall_report,
        "wireless": openwrt.openwrt_wireless_report,
        "dhcp": openwrt.openwrt_dhcp_report,
        "storage": openwrt.openwrt_storage_report,
        "build": openwrt.openwrt_build_report,
        "write": openwrt_write.openwrt_write_report,
    }
    fn = dispatch.get(act, openwrt.openwrt_report)
    ok, msg = fn()
    print(f"\n==== OpenWrt · {act} ====")
    print(msg)
    if act == "write":
        ids = ("openwrt_sysupgrade_guide", "openwrt_pkg_write_guide",
               "openwrt_uci_write_guide", "openwrt_svc_write_guide")
        tasks = [t for t in registry.all_tasks() if t.id in ids]
        if tasks:
            print(f"\n-- 对应高危写指引任务（{len(tasks)} 项，risk=high · 默认关闭 opt_in）--")
            for t in tasks:
                print(f"   • {t.id:<24} [{t.platform}/{t.risk}][opt-in] {t.display_title()}")
        return
    if act in ("list", "detect", "uci", "pkgs", "network", "firewall",
               "wireless", "dhcp", "storage", "build"):
        ids = {
            "detect": ("openwrt_detect",),
            "uci": ("openwrt_uci_audit",),
            "pkgs": ("openwrt_pkgs",),
            "network": ("openwrt_network",),
            "firewall": ("openwrt_firewall",),
            "wireless": ("openwrt_wireless",),
            "dhcp": ("openwrt_dhcp",),
            "storage": ("openwrt_storage",),
            "build": ("openwrt_build",),
            "list": ("openwrt_detect", "openwrt_uci_audit", "openwrt_pkgs",
                     "openwrt_network", "openwrt_firewall", "openwrt_wireless",
                     "openwrt_dhcp", "openwrt_storage", "openwrt_build"),
        }.get(act, ())
        tasks = [t for t in registry.all_tasks() if t.id in ids]
        if tasks:
            print(f"\n-- 相关任务（{len(tasks)} 项，platform=openwrt）--")
            for t in tasks:
                print(f"   • {t.id:<18} [{t.platform}/{t.risk}]"
                      f"{'[opt-in] ' if t.opt_in else ''}{t.display_title()}")
    return


def cmd_plugins(args):
    """插件支持（v0.5.20）：列出/查看/只读运行已注册的安全插件。

      list      : 全部已注册插件（内置 + 用户 drop-in）清单
      show      : 查看某插件清单（--id）；含能力/原生入口/关联任务
      run       : 只读运行某插件声明的全部原生函数（--id）
      allowlist : 查看当前只读白名单（静态审读 + register_native 运行时登记）
    插件安全模型：native 入口仅限白名单内零参只读函数，绝不执行任意代码。
    """
    from .native import plugins

    act = getattr(args, "plugins_action", None) or "list"
    pid = getattr(args, "plugin_id", None)
    ok, msg = plugins.plugin_report(act, pid)
    label = {"list": "插件清单", "show": f"插件详情（{pid}）",
             "run": f"只读运行（{pid}）", "allowlist": "只读白名单"}.get(act, act)
    print(f"\n==== 插件 · {label} ====")
    print(msg)
    return


def cmd_hardware(args):
    """硬件标准参考 + 硬件优化（参考 Linux kernel 源码文档）。

    只读报告：S.M.A.R.T./ACPI/PCI/USB/CPU（参考 T13/ACPI/PCI-SIG/USB-IF），
    以及「硬件优化」任务——其标准依据一律指向 Linux kernel Documentation
    （kernel.org/...），用系统已暴露的 /sys、/proc 接口核对可调项，不修改系统。
    """
    from .native import hardware as nhw
    from . import registry
    platform, version = _resolve(args)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    print(f"\n==== 硬件标准参考（{name} {version or ''}）原生接口读取 + 标准文档 ====")
    print("-- S.M.A.R.T.（参考 T13/ATA8-ACS）--")
    ok, msg = nhw.smart_health()
    print(f"   健康自检: {'OK' if ok else '不可用'}  {msg}")
    print("-- ACPI（参考 UEFI Forum ACPI 规范）--")
    states = nhw.acpi_states()
    print(f"   内核支持睡眠态: {states or '(无法读取)'}")
    print("-- PCI/USB（参考 PCI-SIG / USB-IF 类代码）--")
    pci = nhw.pci_devices()
    usb = nhw.usb_devices()
    print(f"   PCI 设备: {len(pci)} 个" + (f"（{pci[0] if pci else ''} …）" if pci else "（无 lspci）"))
    print(f"   USB 设备: {len(usb)} 个" + (f"（{usb[0] if usb else ''} …）" if usb else "（无 lsusb）"))
    print("-- CPU --")
    cpu = nhw.cpu_info()
    print(f"   {cpu}")
    print("\n标准参考（data/hardware.json）：")
    for sid, ref in nhw.reference_all().items():
        print(f"   · {ref.get('name','')}  [{ref.get('standard','')} / {ref.get('org','')}]")

    print("\n-- 硬件优化（参考 Linux kernel 源码文档 kernel.org/Documentation）--")
    for line in nhw.kernel_doc_list():
        print(line)

    tasks = registry.applicable(platform, version, category="hardware",
                                include_lang_missing=True)
    print(f"\n-- 适用硬件优化任务（{name}，{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.platform}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
        if not tasks:
            print("   （当前平台暂无硬件优化任务——多为 Linux 内核接口相关）")


def cmd_kernel(args):
    """Linux kernel 源码文档参考（硬件 / 软件 / 网络）。

    软件子系统（scheduler/cgroup-v2/oom/psi/thp-compaction/vm-sysctl）与网络子系统
    （tcp/拥塞控制/net.core/rps）的优化依据一律指向 kernel.org/Documentation；只读核对
    系统已暴露的 /sys、/proc 接口，不修改系统。
    """
    from . import registry
    from .native import kernel as nk

    platform, version = _resolve(args)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    print(f"\n==== Linux kernel 源码文档参考（{name} {version or ''}）：硬件 / 软件 / 网络 ====")
    grouped = nk.kernel_doc_grouped()
    label = {"hardware": "硬件（hardware）", "software": "软件（software）",
             "network": "网络（network）"}
    for g in ("hardware", "software", "network"):
        items = grouped.get(g, {})
        print(f"\n-- {label[g]}（{len(items)} 项文档）--")
        for line in nk.kernel_doc_list(group=g):
            print(line)

    print("\n-- 本机内核子系统核对（只读 /sys、/proc，不修改）--")
    for fn_name, lab in (
        ("sched_report", "CFS 调度器"),
        ("cgroup_v2_report", "cgroups v2"),
        ("oom_report", "OOM 防护"),
        ("psi_report", "资源压力 PSI"),
        ("thp_compaction_report", "THP 规整"),
        ("vm_dirty_report", "vm 脏页/缓存"),
        ("tcp_report", "TCP 协议栈"),
        ("tcp_congestion_report", "TCP 拥塞控制"),
        ("net_core_report", "net.core"),
        ("rps_report", "RPS/RFS"),
    ):
        ok, msg = getattr(nk, fn_name)()
        print(f"   · {lab}: {'OK' if ok else '不适用'}  {msg}")

    tasks = [t for t in registry.all_tasks()
             if t.platform == "linux"
             and any("Linux kernel Documentation" in s for s in t.standards)]
    print(f"\n-- 引用内核文档的 Linux 优化任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")


def cmd_desktop(args):
    """桌面环境文档跟踪（GNOME / KDE / XFCE + freedesktop 规范）。

    只读探测当前桌面环境，并对照桌面环境官方文档（dconf/gsettings、KConfig、xfconf、
    freedesktop XDG 规范）列出清理/优化任务与文档出处。
    """
    from . import registry
    from .native import desktop as ndt

    print("\n==== 桌面环境文档跟踪（GNOME / KDE / XFCE） ====")
    for line in ndt.environment_report():
        print(line)

    print("\n-- 桌面环境/规范文档引用（data/desktop_docs.json）--")
    for sid, ref in ndt.reference_all().items():
        print(f"   · {ref.get('name','')}  [{ref.get('org','')} / {ref.get('url','')}]")
        for d in ref.get("docs", [])[:3]:
            print(f"       - {d}")

    tasks = registry.applicable("linux", args.version or "0",
                                include_lang_missing=True)
    dtasks = [t for t in tasks if t.id.startswith("desktop_")]
    print(f"\n-- 桌面清理/优化任务（{len(dtasks)} 项）--")
    for t in dtasks:
        print(f"   • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")

    # 只读缓存对比报告（不删除文件）
    if getattr(args, "report", ""):
        from .native import desktop as ndt
        rep = ndt.cache_report_dict()
        env_label = {"gnome": "GNOME", "kde": "KDE Plasma", "xfce": "XFCE",
                     "other": "其他桌面", "unknown": "未知桌面"}
        try:
            out = _emit_cache_report(args.report, rep, env_label, ndt._fmt_size)
            print(f"\n只读缓存对比报告已生成: {out}（合计 {ndt._fmt_size(rep['grand_total'])}，"
                  f"不删除任何文件）")
        except Exception as e:  # noqa: BLE001
            print(f"\n报告生成失败: {e}")


def cmd_syssoftware(args):
    """其他系统软件文档跟踪（systemd / D-Bus / NetworkManager / PipeWire / BlueZ / udev / polkit / Wayland）。

    「触类旁通、举一反三」：既然内核（硬件/软件/网络）与桌面（GNOME/KDE/XFCE）的优化
    都能各自引用权威文档，其余系统软件同样按**自身的协议与接口**核对——systemd 单元 +
    D-Bus org.freedesktop.systemd1、D-Bus Specification、NetworkManager 的
    org.freedesktop.NetworkManager、PipeWire 原生协议(SPA)、BlueZ 的 org.bluez、
    udev 规则(udev(7))、polkit 的 org.freedesktop.PolicyKit1、Wayland 的 wayland.xml /
    xdg-shell。全部只读，未安装该软件时自动降级为指引。
    """
    from . import registry
    from .native import syssoftware as nsw

    print("\n==== 其他系统软件文档跟踪（按各自协议与接口） ====")
    for line in nsw.environment_report():
        print(line)

    print("\n-- 系统软件文档引用（data/syssoftware_docs.json）--")
    for line in nsw.syssoftware_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nsw.PROBES:
        ok, msg = getattr(nsw, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("syssw_")]
    print(f"\n-- 系统软件核对/优化任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_pkgmgr(args):
    """包管理器文档跟踪（dpkg/APT · RPM/DNF · apk · pacman · Homebrew · winget · pip · npm · Snap/Flatpak）。

    「触类旁通、举一反三」：内核、桌面、其余系统软件、鸿蒙、各小程序端之后，轮到
    **包管理器**——它们的接口彼此完全不同，因此逐个按**自身的协议与接口**核对：
    deb(ar 归档)+Debian Policy 控制字段+apt-get clean/autoremove、RPM 标签化头+rpmdb+
    dnf clean all、.apk+APKINDEX+apk cache clean、.pkg.tar.zst+*.db+paccache、
    Formula/Cask Ruby DSL+brew cleanup、YAML 清单+WinGet REST 源、
    PEP 503 索引+wheel+pip cache purge、Registry API+_cacache+npm cache verify、
    snapd REST+OSTree refs/commit。全部只读，未安装者自动降级为指引。
    """
    from . import registry
    from .native import pkgmgr as npm_

    print("\n==== 包管理器文档跟踪（各自按自身协议与接口） ====")
    for line in npm_.environment_report():
        print(line)

    print("\n-- 包管理器文档引用（data/pkgmgr_docs.json）--")
    for line in npm_.pkgmgr_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in npm_.PROBES:
        ok, msg = getattr(npm_, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("pm_")]
    print(f"\n-- 包管理器清理/核对任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_container(args):
    """容器运行时文档跟踪（Docker / Podman / containerd / BuildKit / OCI / LXC-LXD / CRI）。

    「触类旁通、举一反三」：内核、桌面、其余系统软件、鸿蒙、各小程序端、包管理器之后，
    轮到**容器运行时**——它们的接口彼此完全不同，逐个按**自身的协议与接口**核对：
    Docker 的 OCI runtime-spec + Engine API + system prune、Podman 的 rootless OCI、
    containerd 的 content store / snapshotter + nerdctl / ctr、BuildKit 的内容寻址 build
    cache、OCI 的 image-spec / runtime-spec（digest 共享层）、LXC/LXD 的 liblxc + 存储池、
    CRI 的 gRPC + crictl。全部只读，未安装该运行时自动降级为指引。
    """
    from . import registry
    from .native import container as nct

    print("\n==== 容器运行时文档跟踪（各自按自身协议与接口） ====")
    for line in nct.environment_report():
        print(line)

    print("\n-- 容器运行时文档引用（data/container_docs.json）--")
    for line in nct.container_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nct.PROBES:
        ok, msg = getattr(nct, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("ct_")]
    print(f"\n-- 容器运行时清理/核对任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_storage(args):
    """存储与文件系统文档跟踪（ext4 / Btrfs / XFS / ZFS / LVM / fstrim / SMART / swap）。

    「触类旁通、举一反三」：内核、桌面、其余系统软件、鸿蒙、各小程序端、包管理器、容器运行时
    之后，轮到**存储与文件系统**——它们的接口彼此完全不同，逐个按**自身的协议与接口**核对：
    ext4 的 extent 布局 + jbd2 日志、Btrfs 的 COW B-tree + 子卷/快照 + qgroup、XFS 的 AG 分配组
    + B+tree、ZFS 的 zpool/dataset + DMU/SPA 校验和、LVM 的 PV/VG/LV + device-mapper、fstrim 的
    FITRIM ioctl + ATA TRIM/SCSI UNMAP/NVMe DSM、SMART 的 ATA/SCSI/NVMe 自检属性、swap 的签名页
    + swapon(2)。全部只读，未安装该工具或文件系统未挂载自动降级为指引。
    """
    from . import registry
    from .native import storage as nst

    print("\n==== 存储与文件系统文档跟踪（各自按自身协议与接口） ====")
    for line in nst.environment_report():
        print(line)

    print("\n-- 存储/文件系统文档引用（data/storage_docs.json）--")
    for line in nst.storage_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nst.PROBES:
        ok, msg = getattr(nst, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("fs_")]
    print(f"\n-- 存储/文件系统清理/核对任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_network(args):
    """网络栈深度调优文档跟踪（iproute2 / ethtool / eBPF / tc / conntrack / NM-resolved / 缩放）。

    「触类旁通、举一反三」：内核、桌面、其余系统软件、鸿蒙、各小程序端、包管理器、容器运行时、
    存储与文件系统之后，把同一模式推广到**网络栈运维与可观测性**——每个工具接口完全不同，
    逐个按**自身的协议与接口**核对（绝不套用协议层的 sysctl 写法）：
      - iproute2 : netlink/rtnetlink + sock_diag；ip -br addr / ss -tunlp / tc qdisc show
      - ethtool  : ETHTOOL ioctl/netlink；-k/-i/-l/-g/-c/-S 只读，-K/-C 写
      - eBPF     : bpf() 系统调用 + libbpf；bpftool prog/map/net list 只读检视
      - tc       : rtnetlink(TC) qdisc；show 只读，add/replace 写
      - conntrack: nf_conntrack；-S / /proc 只读，sysctl max 写
      - nm_resolved: NM D-Bus / networkd INI / resolved stub；nmcli/networkctl/resolvectl 只读
      - scaling  : RPS/RFS/XPS sysfs + net.core；cat/sysctl 只读，echo/sysctl 写
    全部只读探测；未装该工具自动降级为指引。调优项见 TASKS（net_* 深度任务，全 opt_in）。
    """
    from . import registry
    from .native import network as nnet

    print("\n==== 网络栈深度调优文档跟踪（各自按自身协议与接口） ====")
    for line in nnet.environment_report():
        print(line)

    print("\n-- 网络运维工具文档引用（data/network_docs.json）--")
    for line in nnet.network_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nnet.PROBES:
        ok, msg = getattr(nnet, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("net_")]
    print(f"\n-- 网络栈深度调优任务（net_*，{len(tasks)} 项，全 opt_in）--")
    for t in tasks:
        print(f"   • {t.id:<22} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --category network --opt-in --yes --apply")
    print("  python -m sysweeper clean --only net_tc_fq --opt-in --yes --apply")


def cmd_macos(args):
    """macOS 原生接口文档跟踪（launchd / sysctl / defaults / softwareupdate /
    diskutil / pmset / tmutil / spctl / networksetup）。

    「触类旁通、举一反三」：内核、桌面、系统软件、鸿蒙、小程序端、包管理器、容器运行时、
    存储与文件系统、网络栈之后，把同一模式推广到 **macOS 自身系统接口**——每个接口完全不同，
    逐个按**自身的协议与接口**核对（绝不套用 Linux 的 /proc/sys 或 systemd 写法）：
      - launchd : plist 作业 + 域层级（system/gui/<uid>）；launchctl list / disable 只读，bootout 卸载
      - sysctl  : XNU sysctlbyname；sysctl -a 只读，-w 写（root）
      - defaults: CFPreferences plist 后端；defaults read/domains 只读，write 需 killall 生效
      - softwareupdate: SUS catalog；-l 只读列出
      - diskutil: APFS 容器/宗卷/快照；apfs list / verifyVolume 只读
      - pmset   : 电源配置；-g 只读
      - tmutil  : APFS 本地快照；listlocalsnapshots 只读
      - spctl   : Gatekeeper；--status / --assess 只读评估
      - networksetup: 网络配置；-listallnetworkservices / -getdnsservers 只读
    全部只读探测；非 macOS 环境自动降级为文档指引。清理/优化任务见 mac_*（默认 --apply 才执行）；
    v0.5.12 起另有一组 **官方写接口深度调优**（macos_tune_*，全 opt_in）：
    pmset -a / sysctl -w / networksetup -setdnsservers / tmutil thinlocalsnapshots /
    defaults write / softwareupdate --schedule / spctl --master-enable / diskutil verifyVolume，
    只往安全方向写（如 Gatekeeper 只开不关），参数（机型/网络服务）自动探测。
    """
    from . import registry
    from .native import macos as nm

    print("\n==== macOS 原生接口文档跟踪（各自按自身协议与接口） ====")
    for line in nm.environment_report():
        print(line)

    print("\n-- macOS 系统接口文档引用（data/macos_docs.json）--")
    for line in nm.macos_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nm.PROBES:
        ok, msg = getattr(nm, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- macOS 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in nm.macos_tune_list():
        print(line)

    base = [t for t in registry.all_tasks()
            if t.id.startswith("mac") and not t.id.startswith("macos_tune_")]
    tune = [t for t in registry.all_tasks() if t.id.startswith("macos_tune_")]
    print(f"\n-- macOS 清理/优化任务（mac_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- macOS 官方接口深度调优（macos_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<34} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform macos --opt-in --yes --apply")
    print("  python -m sysweeper clean --only macos_tune_pmset_hibernatemode --opt-in --yes --apply")


def cmd_bsd(args):
    """BSD 原生接口文档跟踪（pkg / rc.conf / sysctl / pf / zfs / periodic /
    bsdconfig / ports）。

    「触类旁通、举一反三」：把同一模式推广到 **BSD 自身系统接口**（FreeBSD/OpenBSD/
    NetBSD/DragonFly）——每个接口完全不同，逐个按**自身的协议与接口**核对：
      - pkg     : SQLite 本地库 + pkg+https 仓库；pkg info/version/audit 只读，clean/autoremove 写
      - rc.conf : rc(8) xxx_enable 变量 + rcorder 依赖；service -e 只读，禁用改 rc.conf
      - sysctl  : BSD MIB；-a 只读，-w 写（root）
      - pf      : pf.conf 规则集/锚点/表；pfctl -s rules/info/state 只读
      - zfs     : OpenZFS zpool/dataset；zpool list/status、zfs list 只读
      - periodic: /etc/periodic/{daily,weekly,monthly,security} 脚本；cat 只读
      - bsdconfig: 文本配置向导；进入模块查看即只读
      - ports   : /usr/ports Makefile + distfiles；du 清点只读
    全部只读探测；非 BSD 环境自动降级为文档指引。清理/优化任务见 bsd_*（默认 --apply 才执行）；
    v0.5.12 起另有一组 **官方写接口深度调优**（bsd_tune_*，全 opt_in）：
    sysctl -w（net.inet.tcp.rfc1323 / recvspace / kern.maxfiles / vfs.zfs.arc_max）、
    zpool set autotrim=on、zpool scrub、pfctl -e -f、periodic，
    只往安全方向写（pf 只启用不停用、缓冲只上调不降低），池名与内存自动探测。
    """
    from . import registry
    from .native import bsd as nb

    print("\n==== BSD 原生接口文档跟踪（各自按自身协议与接口） ====")
    for line in nb.environment_report():
        print(line)

    print("\n-- BSD 系统接口文档引用（data/bsd_docs.json）--")
    for line in nb.bsd_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nb.PROBES:
        ok, msg = getattr(nb, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- BSD 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in nb.bsd_tune_list():
        print(line)

    base = [t for t in registry.all_tasks()
            if t.id.startswith("bsd") and not t.id.startswith("bsd_tune_")]
    tune = [t for t in registry.all_tasks() if t.id.startswith("bsd_tune_")]
    print(f"\n-- BSD 清理/优化任务（bsd_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- BSD 官方接口深度调优（bsd_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<34} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform bsd --opt-in --yes --apply")
    print("  python -m sysweeper clean --only bsd_tune_zfs_autotrim --opt-in --yes --apply")


def cmd_windows(args):
    """Windows 原生接口文档跟踪（Win32 API / 注册表 / WMI-CIM / powercfg / DISM /
    SFC / 存储感知 / 传递优化 / Windows Update）。

    「触类旁通、举一反三」：把同一模式补到 **Windows 自身系统接口**（此前唯独
    它缺文档层）——每个接口完全不同，逐个按**自身的协议与接口**核对，
    绝不套用 Linux 的 /proc/sys 或 sysctl 写法：
      - Win32 API : kernel32/shell32/advapi32（stdcall + UTF-16 宽字符 + GetLastError）
      - 注册表    : winreg 读 HKLM/HKCU（REG_SZ/REG_DWORD/REG_QWORD，Wow6432Node 双视图）
      - WMI/CIM   : DMTF CIM 模型 + WQL；Get-CimInstance 只读查询
      - powercfg  : 计划 GUID + subgroup/setting 两级；/list /getactivescheme 只读
      - DISM      : servicing stack + CBS 组件存储；/Get-CurrentEdition 只读
      - SFC       : WRP 资源保护；/verifyonly 只读校验，/scannow 写修复
      - 存储感知  : StoragePolicy 注册表策略（01/04/32/2048 等 DWORD）
      - 传递优化  : DO P2P 缓存；Get-DeliveryOptimizationStatus 只读
      - Windows 更新: UsoSvc + 注册表 Results\\Detect 只读核对（不用已弃用的 wuauclt）
    全部只读探测；非 Windows 环境自动降级为文档指引。清理/优化任务见 win_*，
    v0.5.13 起另有一组官方写接口深度调优（win_tune_*，全 opt_in）：
    fsutil behavior set / netsh int tcp set global / netsh advfirewall（只开不关）/
    powercfg /change|/h /type reduced / sfc /scannow。
    """
    from . import registry
    from .native import windows as nw

    print("\n==== Windows 原生接口文档跟踪（各自按自身协议与接口） ====")
    for line in nw.environment_report():
        print(line)

    print("\n-- Windows 系统接口文档引用（data/windows_docs.json）--")
    for line in nw.windows_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nw.PROBES:
        ok, msg = getattr(nw, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- Windows 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in nw.windows_tune_list():
        print(line)

    base = [t for t in registry.all_tasks()
            if t.id.startswith("win") and not t.id.startswith("win_tune_")]
    tune = [t for t in registry.all_tasks() if t.id.startswith("win_tune_")]
    print(f"\n-- Windows 清理/优化任务（win_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- Windows 官方接口深度调优（win_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform windows --opt-in --yes --apply")
    print("  python -m sysweeper clean --only win_tune_tcp_autotuning --opt-in --yes --apply")


def cmd_durability(args):
    """设备长期使用保护子系统（v0.6.30）。

    只读采集电池/温度/存储 SMART/运行时长/环境传感器，标出本机未提供项（不伪造）；
    依据使用量（light/moderate/heavy）、期望使用年限、环境标签（high_humidity/mobile/
    plugged_in/outdoor）由知识库（IEC 60529 / ASHRAE / 厂商电池指南 / NVMe SMART）
    推导充电上限/温度预算/湿度包络，并给出评分、保养清单与优化建议。

    所有写操作（充电阈值/热策略/TRIM/备份）一律只给 OEM 官方工具指引，不代执行——
    严守只读红线，也契合「个人行为在完全图形界面控制操作」：本命令出报告，用户在
    GUI / OEM 工具里确认执行。
    """
    from . import registry
    from .native import durability as nd

    usage = getattr(args, "usage", None) or "moderate"
    years = getattr(args, "years", None) or 4
    env = getattr(args, "env", None) or []

    print("\n==== 设备长期使用保护（只读采集 + 知识库驱动保养，不写设备） ====")
    print(f"   画像: 使用量={usage}  期望年限={years}年  环境={env or '默认'}")
    for line in nd.environment_report():
        print(line)

    print("\n-- 知识库引用（data/durability_docs.json：天气/气候/材料/耐久/保养/水汽异物）--")
    for line in nd.durability_doc_list():
        print(line)

    print("\n-- 本机传感器核对（只读，读不到即标记「本机未提供」）--")
    for fn_name, lab in nd.PROBES:
        ok, msg = getattr(nd, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, ensure_ascii=False)
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- 端到端保护报告（采集→目标包络→评分→建议+清单）--")
    ok, rep = nd.durability_report(usage, years, env)
    print(rep)

    print("\n-- OEM 官方工具指引（此处只展示不调用——调用即写设备寄存器）--")
    for line in nd.durability_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("durability_")]
    print(f"\n-- 设备长期使用保护任务（durability_*，{len(base)} 项，只读报告+指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：报告 ≠ 授权执行——任何写设备操作只给 OEM 工具指引；"
          "是否优化始终由用户确认。")


def cmd_electrical(args):
    """供电与环境安全子系统（v0.6.38）。

    把电气火灾科普（局部高阻发热 P=I²R / 铜铝原电池腐蚀 / 金属蠕变松脱 / 串联电弧
    AFDD / 木桶短板过载 / 接地+RCD / 接点老化 / 可燃底座）落成知识库，据用户声明的
    供电环境标签（old_wiring/copper_aluminum/no_ground/wood_base/loose_outlet/
    overload_risk/high_dust）+ 本机可读温度，识别「事故前兆链条」与风险级，并给出
    「设备长期保障运行」自适应建议。

    本工具**只读感知 + 出方案**：绝不测插座接触电阻、绝不碰配电箱、绝不下发电气写
    命令；电气改造由持证电工按规范执行，是否施工始终由用户确认。与「设备长期使用
    保护（durability）」并列，共同支撑「依据设备外部和内部环境自适应、保持长期保障运行」。
    """
    from . import registry
    from .native import electrical as ne

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 供电与环境安全（只读感知 + 知识库自适应，绝不碰配电箱） ====")
    print(f"   供电环境标签: {env or '未声明（默认低风险基线）'}")

    print("\n-- 本机可读信号（只读，绝不涉及接触电阻）--")
    for fn_name, lab in ne.PROBES:
        ok, msg = getattr(ne, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, ensure_ascii=False)
        if msg:
            print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- 知识库引用（data/electrical_safety_docs.json：8 类电气火灾隐患机理与标准）--")
    for line in ne.electrical_doc_list():
        print(line)

    print("\n-- 端到端供电与环境安全报告（识别隐患链→自适应建议）--")
    ok, rep = ne.electrical_safety_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即碰配电箱）--")
    for line in ne.electrical_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("electrical_")]
    print(f"\n-- 供电与环境安全任务（electrical_*，{len(base)} 项，只读报告+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读感知 ≠ 授权施工——任何测接触电阻/碰配电箱/换线/装 RCD 动作"
          "只给规范指引；是否施工始终由用户请持证电工确认。")


def cmd_sysbase(args):
    """系统基座（v0.6.88）：只读系统目录 + 包管理 + 网络仓库 + msf 检测 + 概念课。

    红线同 native/sysbase.py：绝不安装/卸载软件、绝不改动仓库源与密钥、
    绝不启动 msfconsole 跑任何模块、绝不写任何系统目录。
    """
    from . import registry
    from .native import sysbase as na

    print("\n==== 系统基座（只读 + 知识库驱动，绝不改动系统） ====")

    ok, msg = na.sysbase_report()
    print(msg)

    print("\n-- 系统基座任务（sysbase_*，执行需 --apply；全部 read-only）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("sysbase_")]
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本子系统只读——不安装/卸载软件、不动仓库源与密钥、"
          "不启动 msfconsole 跑任何模块、不写任何系统目录。")


def cmd_sysdev(args):
    """从零造系统学习应用（v0.6.89）：pepsipu 项目群 7 仓库模式 + 工具链 + malloc 体检。

    红线同 native/sysdev.py：绝不编译/运行被分析的第三方源码、绝不修改 malloc
    环境变量或任何进程环境、绝不 vendored 第三方源代码。
    """
    from . import registry
    from .native import sysdev as na

    print("\n==== 从零造系统学习应用（只读 + 知识库驱动，绝不代跑第三方源码） ====")

    ok, msg = na.sysdev_report()
    print(msg)

    print("\n-- 从零造系统任务（sysdev_*，执行需 --apply；全部 read-only）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("sysdev_")]
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本子系统只读——不编译/运行第三方源码、不改 malloc 环境变量、"
          "不 vendored 第三方源代码（MIT/BSD 学模式，无许可证只学思想）。")


def cmd_docs(args):
    """文档与概念联动（v0.6.88）：docs/ 文档层作为联动网格一等节点（只读统合整合）。

    红线同 native/docs.py：不写任何文件、不执行命令、不修改系统；仅枚举文档与交叉引用。
    """
    from . import registry
    from .native import docs as na

    print("\n==== 文档与概念联动（只读 + 文档驱动，绝不改动系统） ====")

    ok, msg = na.docs_report()
    print(msg)

    print("\n-- 文档联动任务（docs_*，执行需 --apply；全部 read-only）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("docs_")]
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本节点只读——不写任何文件、不执行命令、不修改系统；"
          "仅枚举文档与交叉引用，供 CLI/GUI 展示与联动体检。")


def cmd_acoustics(args):
    """声学与音律（v0.6.87）：只读设备面 + 波动换算 + 三分损益 + 知识库引用。

    红线同 native/acoustics.py：绝不播放声音、绝不调音量、绝不采集麦克风内容、
    无任何射频发射路径。
    """
    from . import registry
    from .native import acoustics as na

    print("\n==== 声学与音律（只读 + 知识库驱动，绝不发声/调音量/采集声音） ====")

    ok, msg = na.devices_report()
    print(msg)

    ok, msg = na.conversion_report()
    print(msg)

    ok, msg = na.lvlv_report()
    print(msg)

    print("\n-- 知识库引用（data/acoustics_docs.json：声学基础/中国音律/无线电磁/音频硬件）--")
    for line in na.acoustics_doc_list():
        print(line)

    print("\n-- 听力保护参照（EN 50332 限值）--")
    ok, msg = na.hearing_protection_guide()
    print(msg)
    base = [t for t in registry.all_tasks() if t.id.startswith("acoustics_")]
    print(f"\n-- 声学与音律任务（acoustics_*，{len(base)} 项，只读报告+规范参照，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本子系统只读设备存在性、只做数学换算——绝不播放任何声音、"
          "绝不调音量、绝不采集麦克风内容、无任何射频发射路径。")


def cmd_androidstd(args):
    """国内标准知识库：Android/App 隐私合规（v0.6.67）。

    把中国境内 App 运营的四层标准体系落成知识库（全部经官方源实检）：
    上位法 PIPL（告知-同意/最小必要）→ 国标 GB/T 35273/41391/42574/34975 →
    四部门《认定方法》/《39 类必要个人信息范围规定》/ App 信息服务管理规定 / 备案 →
    TC260 自评估与系统权限实践指南。

    本工具**只读知识库 + 出检查项**：不扫描任何 App、不代执法、不代申诉；
    判定与行动（App 内投诉/分发平台/12321/监管部门）始终留给用户。
    """
    from . import registry
    from .native import androidstd as na

    print("\n==== 国内标准 · Android/App 隐私合规（只读知识库，不扫描、不代执法） ====")

    print("\n-- 知识库引用（data/androidstd_domestic_standards.json：13 条，官方源实检）--")
    for line in na.androidstd_doc_list():
        print(line)

    print("\n-- 端到端总报告（四层体系 + App 合规检查清单）--")
    ok, rep = na.androidstd_compliance_report()
    print(rep)

    print("\n-- 涉及任务（androidstd_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("androidstd_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本清单帮助理解并对照国内标准，不是合规认证、不代执法；"
          "判定权始终在用户与监管部门。")


def cmd_cnstd(args):
    """国内标准资源知识库：官方平台/协议规范/第三方/概念四层（v0.6.90）。

    把 14 个国内标准资源链接（2026-10-25 逐只读抓取）落成知识库：
    官方源五平台（openstd 国标全文公开 6188 强标 + 61615 推标 / std.samr
    行标 88751·76 行业 + 地标 49114 / hbba 行标备案 / CCSA / 合同示范文本库）
    + 协议规范两组（Modbus 六规范 / MQTT）+ 第三方三家（spc 商业付费 /
    biaozhuns 分享站 / RFC 中文翻译）+ 概念科普三篇。规模数字为检索日实测。

    本工具**只读知识库 + 出索引**：不联网代查、不代下载、不破解任何
    付费/受限资源；第三方渠道仅登记存在性与风险，取用与判定留给用户。
    """
    from . import registry
    from .native import cnstd as nc

    print("\n==== 国内标准资源（只读知识库，不联网、不代查、不代下载） ====")

    print("\n-- 知识库引用（data/cnstd_domestic_standards.json：14 源全量，2026-10-25 实测）--")
    for line in nc.cnstd_doc_list():
        print(line)

    print("\n-- 端到端总报告（四层体系 + needs_verify 挂牌）--")
    ok, rep = nc.cnstd_report()
    print(rep)

    print("\n-- 涉及任务（cnstd_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("cnstd_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：官方源（openstd/std.samr/hbba）为权威口径，第三方渠道"
          "版权风险自担；本工具不代查、不代下载、不破解付费/受限资源。")


def cmd_gmsstd(args):
    """GMS 标准知识库：GMS 兼容与 Google Play 上架（v0.6.67）。

    把 GMS 兼容与 Play 上架标准落成知识库（除 STS 细节外全部经官方源实检）：
    兼容体系 CDD/CTS/VTS/STS → GMS 兼容与许可（CTS 兼容是 GMS 服务栈门槛）
    → Play 三件套（Play Integrity API / Play App Signing / targetSdk 门槛）
    → Play 数据安全披露 → Android 安全公告与补丁体系。

    本工具**只读知识库 + 出检查项**：不扫描、不联网、不代审、不代申诉；
    判定与行动（上架/整改/申诉）始终留给用户与 Google 官方。
    """
    from . import registry
    from .native import gmsstd as ng

    print("\n==== GMS 标准 · GMS 兼容与 Play 上架（只读知识库，不扫描、不代审） ====")

    print(f"\n-- 知识库引用（data/gmsstd_standards.json：{len(ng.REFS)} 条，"
          f"官方源实检；STS 细节社区整理标注）--")
    for line in ng.gmsstd_doc_list():
        print(line)

    print("\n-- 端到端总报告（兼容体系 + GMS/Play 上架自查清单）--")
    ok, rep = ng.gms_compliance_report()
    print(rep)

    print("\n-- 涉及任务（gmsstd_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("gmsstd_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本清单帮助理解并对照 GMS/Play 标准，不是认证、不代审；"
          "判定权始终在用户与 Google 官方。")


def cmd_hmos_ecosystem(args):
    """HarmonyOS/OpenHarmony 生态知识库（v0.6.71）。

    把鸿蒙侧工程事实落成只读知识库：HAP 工程与 deviceTypes 判定 → NEXT 侧载
    工具链 → 第三方生态版图（2026-10 快照 110 款）→ OpenHarmony/HarmonyOS 版本
    关系（NEXT 分水岭）→ 开发工具链（Deveco/方舟/ArkTS/仓颉）→ HiSpark 开发板
    与 HDF。来源分社区整理源（needs_verify）与华为官方公开文档两类。

    本工具**只读知识库 + 出检查项**：不扫描、不联网、不代执行任何安装/签名；
    判定与行动（迁移/侧载/选型）始终留给用户。
    """
    from . import registry
    from .native import hmos_ecosystem as nh

    print("\n==== HarmonyOS/OpenHarmony 生态知识库（只读，不扫描、不代执行） ====")

    print(f"\n-- 知识条目（data/hmos_ecosystem_docs.json：{len(nh.ENTRY_KEYS)} 条，"
          f"社区源 needs_verify + 官方公开文档）--")
    for line in nh.hmos_doc_list():
        print(line)

    print("\n-- 端到端总报告（生态知识 + 评估自检清单）--")
    ok, rep = nh.hmos_ecosystem_report()
    print(rep)

    print("\n-- 涉及任务（hmoseco_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("hmoseco_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本清单帮助理解鸿蒙生态并对照自查，不推荐任何具体应用、"
          "不代执行安装/签名；判定权始终在用户与各官方来源。")


def cmd_hmosstd(args):
    """HarmonyOS 标准与合规知识库（v0.6.72）。

    第四生态标准库（前三：androidstd 国内 / gmsstd GMS / fdroidstd 免 GMS）：
    PIPL 上位法 → AppGallery 上架 → App 备案 → 权限 APL 分级 → 隐私指示器
    → HUKS/TEE/加解密 → API 版本兼容 → 未成年人保护 → 后台与网络规范 →
    XTS/Acts 兼容测试。口径分法规原文（npc.gov.cn / beian.miit.gov.cn）与
    华为官方公开文档（developer.huawei.com）两类。

    本工具**只读知识库 + 出对照项**：不代审、不代申诉、不下合规结论；
    判定与行动（整改/上架/申诉）始终留给用户。
    """
    from . import registry
    from .native import hmosstd as nh

    print("\n==== HarmonyOS 标准与合规知识库（只读，不代审、不下结论） ====")

    print(f"\n-- 标准条目（data/hmosstd_standards.json：{len(nh.ENTRY_KEYS)} 条，"
          f"法规原文 + 官方源口径；社区整理 needs_verify）--")
    for line in nh.hmosstd_doc_list():
        print(line)

    print("\n-- 端到端总报告（标准清单 + 合规对照表）--")
    ok, rep = nh.hmosstd_compliance_report()
    print(rep)

    print("\n-- 涉及任务（hmosstd_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("hmosstd_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本清单只给对照口径，不代审、不代申诉、不下合规结论；"
          "判定权始终在用户与各官方来源。")


def cmd_reverse(args):
    """黑箱逆向与调试工具链知识库（v0.6.73）。

    UPX/GDB/MinGW 沙箱实战沉淀：UPX 壳三特征识别（UPX! marker + UPX0/1/2 节名
    + 节熵>7.5）→ PE/ELF 节区解剖 → 香农熵两级判据 → MinGW 自造可控样本 →
    GDB 黑箱四连（info functions/disassemble/mappings/break）→ strip 前后符号
    可见性 → 只读边界。全部结论来自沙箱实盘（minGW GCC 13、UPX 4.2.2、GDB 15）。

    本工具**只读分析**：不执行目标程序、不 patch 内存、不 hook 调用、
    不生成注册机/破解补丁；逆向目标限自己/己方/已授权产物。
    """
    from . import registry
    from .native import reverse as nr

    print("\n==== 黑箱逆向与调试工具链（只读，不执行、不绕过） ====")

    print(f"\n-- 知识条目（data/reverse_docs.json：{len(nr.ENTRY_KEYS)} 条，沙箱实测口径）--")
    for line in nr.reverse_doc_list():
        print(line)

    print("\n-- 端到端总报告（知识清单 + 黑箱对照表）--")
    ok, rep = nr.reverse_report()
    print(rep)

    print("\n-- 涉及任务（reverse_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("reverse_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本工具只做只读分析——不执行目标、不 patch、不 hook、"
          "不生成任何绕过手段；逆向目标限自己/己方/已授权产物。")


def cmd_fdroidstd(args):
    """F-Droid 标准知识库：免 GMS 自由软件分发（v0.6.67）。

    把 F-Droid 生态标准落成知识库（事实经 GitHub/GitLab API 与官方文档
    检索快照实检）：存储库模型（免账号/免 GMS，能下载即可安装）→ 收录政策
    （FLOSS 准入）→ 反特征体系（广告/追踪/非自由依赖透明标注）→ fdroiddata
    配方 → 可复现构建（服务器从源码构建签名）→ 仓库协议（index/指纹/特权
    扩展）→ F-Droid 与 Play 对照 → 签名信任模型。

    本工具**只读知识库 + 出检查项**：不扫描、不联网、不代审、不代分发；
    装什么、加哪个仓库的判定与行动始终留给用户。
    """
    from . import registry
    from .native import fdroidstd as nf

    print("\n==== F-Droid 标准 · 免 GMS 自由软件分发（只读知识库，不扫描、不代分发） ====")

    print("\n-- 知识库引用（data/fdroidstd_standards.json：10 条，官方/GitHub 实检）--")
    for line in nf.fdroidstd_doc_list():
        print(line)

    print("\n-- 端到端总报告（分发体系 + 收录自查清单）--")
    ok, rep = nf.fdroid_compliance_report()
    print(rep)

    print("\n-- 涉及任务（fdroidstd_*，执行需 --apply；均为指引类，只读知识消费）--")
    base = [t for t in registry.all_tasks() if t.id.startswith("fdroidstd_")]
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：本清单帮助理解并对照 F-Droid 标准，不是认证、不代分发；"
          "装什么、加哪个仓库的判定权始终在用户。")


def cmd_peripheral(args):
    """外部设备连接与兼容子系统（v0.6.39）。

    整体引入星闪(NearLink)标准：SLB（高速率/对标 Wi-Fi）+ SLE（低功耗/对标 BLE），
    微秒时延、一拖上千并发、Polar 码抗干扰；并把触控技术（多点触控/精确触控板）与
    外部设备支持与兼容（USB-C/USB4+PD 供电、HID 即插即用）落成只读识别与标准指引。

    本工具**只读识别 + 出方案**：绝不刷星闪/USB 固件、绝不装私有外设驱动、绝不挂钩
    输入流、绝不改写 PD 协商；外设改造由用户在图形界面或厂商工具确认。与「供电与环境
    安全（electrical）」「设备长期使用保护（durability）」并列，共同支撑「外部设备
    连接与设备长期保障运行」。
    """
    from . import registry
    from .native import peripheral as npf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 外部设备连接与兼容（只读识别 + 星闪标准引入，绝不刷固件/装驱动/挂钩输入） ====")
    print(f"   设备标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机可读信号（只读，绝不挂钩输入流）--")
    for fn_name, lab in npf.PROBES:
        ok, msg = getattr(npf, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, ensure_ascii=False)
        if msg:
            print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- 知识库引用（data/peripheral_standards_docs.json：星闪/触控/USB-C PD/HID）--")
    for line in npf.peripheral_doc_list():
        print(line)

    print("\n-- 端到端外部设备连接与兼容报告（星闪引入→触控→USB-C PD/HID）--")
    ok, rep = npf.peripheral_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即刷固件/装驱动/改 PD）--")
    for line in npf.peripheral_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("peripheral_")]
    print(f"\n-- 外部设备连接与兼容任务（peripheral_*，{len(base)} 项，只读报告+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读识别 ≠ 授权施工——任何刷固件/装私有驱动/改写 PD 协商只给规范指引；"
          "是否施工始终由用户在图形界面或厂商工具确认。")


def cmd_chrono(args):
    """时空与全维度管理器子系统（v0.6.40）。

    以量子理论及计算机原理为只读观测透镜，观察时间维（时钟/时区/生命周期）、空间维
    （存储/地址空间/NUMA）、施时空组合维（事件-资源因果链）、未来兼容维（标准 EOL/
    后量子），并跑全时空全维度循环往复管理器（round-robin 周而复始、每维一视同仁）。

    本工具**只读观测 + 出方案**：绝不改系统时钟/时区、绝不分区/格式化、绝不升级替换
    组件、绝不执行任何量子写操作；系统改造由用户在图形界面或厂商工具确认。
    """
    from . import registry
    from .native import chrono as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 时空与全维度管理器（量子/计算机原理 + 时间/空间/施时空组合/未来兼容，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机可读信号（只读，绝不改时钟/时区/分区/升级）--")
    for fn_name, lab in ncf.PROBES:
        ok, msg = getattr(ncf, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
        if isinstance(msg, (dict, list)):
            msg = json.dumps(msg, ensure_ascii=False)
        if msg:
            print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- 知识库引用（data/chrono_theory_docs.json：量子/计算机原理/时间/空间/施时空组合/未来兼容）--")
    for line in ncf.chrono_doc_list():
        print(line)

    print("\n-- 端到端时空与全维度报告（时间→空间→施时空组合→未来兼容→循环往复管理器）--")
    ok, rep = ncf.chrono_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即改时钟/分区/升级组件）--")
    for line in ncf.chrono_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("chrono_")]
    print(f"\n-- 时空与全维度任务（chrono_*，{len(base)} 项，只读报告+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读观测 ≠ 授权施工——任何改时钟/时区/分区/格式化/升级替换组件只给规范指引；"
          "是否施工始终由用户在图形界面或厂商工具确认。")


def cmd_virt(args):
    """虚拟机环境只读诊断（v0.6.41）。

    只读识别本工具自身运行在哪一层虚拟化（裸金属/KVM/VMware/VirtualBox/Hyper-V/Xen/WSL/
    容器），并给出「在不同虚拟机内优雅降级」的应对——确保整体只降级不崩溃。本工具只读识别
    与降级，绝不装增强工具/改 QEMU-crosvm 配置/加载内核模块。
    """
    from .native import virt as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 虚拟机环境（virt：识别虚拟化层 + 不同 VM 内优雅降级，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机虚拟化探测（只读，绝不装驱动/改配置/加载模块）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端虚拟机环境报告（识别层→退化计划→子系统影响）--")
    ok, rep = ncf.virt_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即装增强工具/改配置）--")
    for line in ncf.virt_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("virt_")]
    print(f"\n-- 虚拟机环境任务（virt_*，{len(base)} 项，只读报告+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读识别 ≠ 授权施工——任何装增强工具/改 QEMU-crosvm 配置/加载内核模块只给"
          "规范指引；是否施工始终由用户在 guest 内或厂商工具确认。")


def cmd_packages(args):
    """软件包规范审计（v0.6.41）。

    按系统/硬件/相关软件包只读检测包管理器（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper），
    审计「安装/卸载/配置/设置优化」四类操作是否符合包规范并给出层级应对。本工具只审计 + 出指引，
    绝不 install/uninstall/configure/optimize 任何包。
    """
    from .native import packages as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 软件包规范审计（packages：按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机包管理器探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端软件包规范审计报告（检测→四类操作层级应对）--")
    ok, rep = ncf.packages_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即 install/uninstall/configure/optimize）--")
    for line in ncf.packages_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("packages_")]
    print(f"\n-- 软件包规范审计任务（packages_*，{len(base)} 项，只读审计+层级应对指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<32} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只审计 ≠ 授权施工——install/uninstall/configure/optimize 一律只给层级应对指引；"
          "是否施工始终由用户在系统包管理器或厂商工具确认。")


def cmd_apctrl(args):
    """AP 集中控制器只读审计（v0.6.42）。

    只读审计本机/网内 AP 栈（hostapd / NetworkManager 共享热点 / dnsmasq / apcontroller 思路），
    给出集中下发 WiFi 配置的合规指引。绝不读解密口令、绝不改任何 AP 配置、绝不下发配置。
    """
    from .native import apctrl as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== AP 集中控制器（apctrl：hostapd/NetworkManager/dnsmasq/apcontroller 只读审计，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机 AP 栈探测（只读，绝不回显口令/密钥）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端 AP 集中控制器审计报告 --")
    ok, rep = ncf.apctrl_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即下发 AP Group 配置）--")
    for line in ncf.apctrl_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("apctrl_")]
    print(f"\n-- AP 集中控制器任务（apctrl_*，{len(base)} 项，只读审计+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读审计 ≠ 授权施工——改 hostapd/dnsmasq、用 apcontroller 下发 AP Group 配置一律只给"
          "规范指引；是否施工始终由用户在控制器或厂商工具确认。")


def cmd_llvm(args):
    """LLVM 工具链与交叉编译（v0.6.42）。

    只读探测 LLVM 工具链（clang/lld/mlir），并给出按时间序列逐步扩充的交叉编译目标矩阵。
    绝不编译、绝不下载 sysroot、绝不改写工具链配置。
    """
    from .native import llvm as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== LLVM 工具链（llvm：clang/lld/mlir 探测 + 交叉编译目标矩阵，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机 LLVM 工具链探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端 LLVM 工具链报告 --")
    ok, rep = ncf.llvm_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即交叉编译）--")
    for line in ncf.llvm_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("llvm_")]
    print(f"\n-- LLVM 任务（llvm_*，{len(base)} 项，只读探测+交叉编译指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只探测 ≠ 授权施工——编译/下载 sysroot/改写工具链配置一律只给规范指引；"
          "是否施工始终由用户在构建脚本确认。")


def cmd_toolchain(args):
    """工具链全景（0000.0000.0000.0004.20261024）。

    按「类别 × 目标架构 × 仓库目录」三维编目宿主工具链与仓库工具软件（catalog 数据层），
    并对本机工具链逐项 which + --version 实采。只读探测与编目；安装/构建/下载一律只给指引。
    """
    from .native import toolchain as ntc

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 工具链全景（toolchain：宿主工具链 × 仓库工具软件 × 目标架构矩阵，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 编目全景（分类别 × 目标架构 × 仓库目录）--")
    ok, rep = ntc.catalog_report()
    print(rep)

    print("\n-- 本机工具链实采（which + 版本实读，不装不卸）--")
    ok, rep = ntc.host_probe_report()
    print(rep)

    print("\n-- 仓库工具软件（分类别+目录+配置逻辑顺序+命令序列）--")
    ok, rep = ntc.repo_tools_report()
    print(rep)

    print("\n-- 端到端工具链全景报告 --")
    ok, rep = ntc.toolchain_report(env)
    print(rep)

    base = [t for t in registry.all_tasks() if t.id.startswith("toolchain_")]
    print(f"\n-- 工具链任务（toolchain_*，{len(base)} 项，只读探测+指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：toolchain 只探测与编目；绝不安装/卸载/构建/下载；"
          "catalog 的 setup_steps 与 commands 是给人看的逻辑顺序，不是自动执行队列。")


def cmd_asm(args):
    """汇编语言优化（v0.6.43）。

    只读探测汇编器（nasm/yasm/gas/llvm-mc/gcc -S），并给出优化要点
    （SIMD：SSE/AVX/NEON/SVE/RVV；对齐/寄存器/缓存/分支/指令/内联约束）与 LLVM 交叉编译汇编指引。
    绝不编译、绝不改源码、绝不写汇编文件。
    """
    from .native import asm as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 汇编语言优化（asm：汇编器探测 + 优化要点 + LLVM 交叉汇编指引，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机汇编器探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端汇编语言优化报告 --")
    ok, rep = ncf.asm_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即交叉汇编）--")
    for line in ncf.asm_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("asm_")]
    print(f"\n-- 汇编任务（asm_*，{len(base)} 项，只读探测+优化要点，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只探测 ≠ 授权施工——编译/改源码/写汇编文件一律只给规范指引；"
          "是否施工始终由用户在构建脚本确认。")


def cmd_nettransfer(args):
    """FTP + 目录服务为基础的传输 / 负载验证（v0.6.91）。

    把 docs/74 查阅的真实标准落成可用能力：以 FTP（RFC 959）/ FTPS（RFC 4217）为底座，
    经 FTP 的目录服务（MLSD/LIST）寻址，做上传/下载/断点续传/sha256 校验/受控速率负载验证。

    红线：密码只经 --passenv 从环境变量读，绝不进参数、绝不落盘、绝不硬编码；
    无显式目标不出网；失败带偏移与原因。凭据缺失即拒连（对齐 meshchat/distcompute 纪律）。
    """
    from .native import transfer as tr

    if not getattr(args, "host", ""):
        print("错误：必须指定 --host（FTP 目标主机）。")
        return
    passwd = ""
    if getattr(args, "passenv", ""):
        try:
            passwd = tr.resolve_passwd(args.passenv)
        except ValueError as exc:
            print(f"错误：{exc}")
            return
    cfg = tr.TransferConfig(
        host=args.host, port=getattr(args, "port", 21),
        user=getattr(args, "user", "anonymous"), tls=bool(getattr(args, "tls", False)),
        passwd=passwd,
    )
    rate_limit = float(getattr(args, "rate_limit", 0.0)) * (1 << 20)  # CLI 用 MB/s
    op = getattr(args, "op", "list")

    eng = tr.FtpTransfer(cfg)
    try:
        eng.connect()
        if op == "pwd":
            print(f"远程工作目录：{eng.pwd()}")
        elif op == "mkdir":
            eng.mkdir(getattr(args, "remote", "."))
            print(f"已建远程目录：{getattr(args, 'remote', '.')}")
        elif op == "list":
            path = getattr(args, "remote", ".")
            rows = eng.list_dir(path)
            print(f"远程目录 {path}（{len(rows)} 项）：")
            for r in rows:
                if "name" in r:
                    print(f"   {r.get('type','?'):<8} {r.get('size',0):>12}  {r.get('mtime',''):<15}  {r['name']}")
                else:
                    print(f"   {r.get('raw','')}")
        elif op == "upload":
            res = eng.upload(getattr(args, "local", ""), getattr(args, "remote", ""),
                             verify=not getattr(args, "no_verify", False),
                             resume=bool(getattr(args, "resume", False)), rate_limit=rate_limit)
            print(f"上传完成：{res['local']} -> {res['remote']}（偏移 {res['offset']}，"
                  f"本地 {res['local_size']} B，sha256={res['local_sha256'][:16]}…）")
            print(f"校验：{res.get('verify_detail','跳过')}")
        elif op == "download":
            res = eng.download(getattr(args, "remote", ""), getattr(args, "local", ""),
                               verify=not getattr(args, "no_verify", False),
                               resume=bool(getattr(args, "resume", False)), rate_limit=rate_limit,
                               expected_hash=getattr(args, "expected_hash", "") or "")
            print(f"下载完成：{res['remote']} -> {res['local']}（接收 {res['received']} B，"
                  f"吞吐 {res['throughput']/1024/1024:.2f} MiB/s）")
            print(f"校验：{res.get('verify_detail','跳过')}")
        elif op == "loadtest":
            size = int(getattr(args, "size", 1 << 24))
            dur = float(getattr(args, "duration", 5.0))
            res = eng.loadtest(size=size, duration=dur, rate_limit=rate_limit)
            print(f"负载验证：灌入 {res['sent']} B，耗时 {res['elapsed']:.2f}s，"
                  f"吞吐 {res['throughput']/1024/1024:.2f} MiB/s，"
                  f"限速自约束={'是' if res['rate_limited'] else '否'}")
        else:
            print(f"未知操作：{op}（支持 list/pwd/mkdir/upload/download/loadtest）")
    except tr.TransferError as exc:
        print(f"传输失败：{exc}")
    finally:
        eng.close()


def cmd_meshnet(args):
    """组网优化与设备协同（v0.6.42）。

    学习 Mullvad Meshnet 的 WireGuard P2P 网状组网思路，只读观测组网拓扑、设备能力适配与负载均衡/
    协同共享。绝不新增 peer、绝不改 wg 配置、绝不共享个人数据。
    """
    from .native import meshnet as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 组网优化与设备协同（meshnet：WireGuard P2P + 设备能力适配 + 负载均衡，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机组网探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端组网优化与设备协同报告 --")
    ok, rep = ncf.meshnet_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即 wg set 加 peer）--")
    for line in ncf.meshnet_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("meshnet_")]
    print(f"\n-- 组网与设备协同任务（meshnet_*，{len(base)} 项，只读观测+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读观测 ≠ 授权施工——wg set 加 peer / 改权限一律只给规范指引；个人数据与关键资产永不共享。")


def cmd_matrix(args):
    """数字矩阵冗余数据只读观测（v0.6.84）——周天星斗大阵。

    只读统计 allowlist 内冗余数据（缓存/临时/包管理缓存/回收站/日志轮转）的存在性与体积；
    denylist（个人数据与关键资产）完全不触碰。清理只给文本指引，由用户沿原路执行。
    """
    from .native import matrix as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 周天星斗大阵 · 数字矩阵冗余数据（matrix：缓存/临时/回收站/日志，只读不删） ====")
    print("   指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
    print(f"   维度标签: {env or '未声明（默认全量 allowlist）'}")

    print("\n-- 本机冗余数据环境（只读概览）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端只读观测报告 --")
    ok, rep = ncf.matrix_report(env)
    print(rep)

    base = [t for t in registry.all_tasks() if t.id.startswith("matrix_")]
    print(f"\n-- 数字矩阵任务（matrix_*，{len(base)} 项，只读观测+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读观测 ≠ 授权清理——本命令不删除、不移动、不改写任何数据；")
    print("           denylist（个人数据与关键资产）完全不扫描；清理由用户沿原路执行。")


def cmd_f2b(args):
    """fail2ban 学习应用只读咨询（v0.6.84）——十二都天神煞大阵。

    学习 fail2ban 架构模式与分级响应思想，只读探测安装状态、只读解析 jail 配置；
    fail2ban 为 GPL-2.0 项目，不 vendored 其源码。配置建议仅文本，绝不代写、绝不代行封禁。
    """
    from .native import f2b as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 十二都天神煞大阵 · fail2ban 学习应用（f2b：探测/解析/模式学习，只读不写） ====")
    print("   指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
    print(f"   维度标签: {env or '未声明（默认全部咨询模板）'}")

    print("\n-- 本机 fail2ban 环境（只读概览）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端只读咨询报告 --")
    ok, rep = ncf.f2b_report(env)
    print(rep)

    base = [t for t in registry.all_tasks() if t.id.startswith("f2b_")]
    print(f"\n-- fail2ban 学习应用任务（f2b_*，{len(base)} 项，只读咨询+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读学习 ≠ 授权施工——不代写 jail.local、不重启 fail2ban、不代行封禁/解封；")
    print("           fail2ban-client 仅调 status/version/get 只读子命令；不 vendored GPL-2.0 源码。")


def cmd_vdns(args):
    """虚拟根 DNS 与多 CDN（v0.6.42）。

    只读观测根 DNS（resolv.conf / DoH-DoT）、多 CDN 选择与健康。绝不改 resolv.conf、绝不切 DoH/DoT、绝不改 hosts。
    """
    from .native import vdns as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 虚拟根 DNS 与多 CDN（vdns：根 DNS / DoH-DoT / 多 CDN 选择·健康，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机根 DNS 与多 CDN 探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端虚拟根 DNS 与多 CDN 报告 --")
    ok, rep = ncf.vdns_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即改 DNS）--")
    for line in ncf.vdns_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("vdns_")]
    print(f"\n-- 虚拟根 DNS 与多 CDN 任务（vdns_*，{len(base)} 项，只读观测+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读观测 ≠ 授权施工——改 resolv.conf / 切 DoH-DoT / 改 hosts 一律只给规范指引；"
          "是否施工始终由用户在网络管理或厂商工具确认。")


def cmd_ipp(args):
    """IPP 打印协议发现（v0.6.42）。

    只读发现 IPP 打印设备（CUPS / Avahi mDNS / 本地管理页）。绝不 lpadmin 加打印机、绝不改 CUPS 配置、绝不发布 mDNS 服务。
    """
    from .native import ipp as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== IPP 打印协议发现（ipp：CUPS / mDNS / 本地管理页，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机 IPP 打印设备发现（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端 IPP 打印协议发现报告 --")
    ok, rep = ncf.ipp_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即 lpadmin 加打印机）--")
    for line in ncf.ipp_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("ipp_")]
    print(f"\n-- IPP 打印发现任务（ipp_*，{len(base)} 项，只读发现+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读发现 ≠ 授权施工——lpadmin 加打印机 / 改 CUPS 配置 / 发布 mDNS 服务一律只给规范指引；"
          "是否施工始终由用户在系统设置或 CUPS 管理页确认。")


def cmd_display(args):
    """现代设备显示与 GPU（v0.6.42）。

    只读观测显示服务器（X11/Wayland/Tty）、GPU 与渲染后端、当前分辨率，并显式保留控制台/终端/远程终端。
    绝不装 GPU 驱动、绝不切 Wayland、绝不改显示配置。
    """
    from .native import display as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 现代设备显示与 GPU（display：显示服务器/GPU/分辨率 + 终端保留，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机显示与 GPU 探测（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端现代设备显示与 GPU 报告 --")
    ok, rep = ncf.display_report(env)
    print(rep)

    print("\n-- 规范指引（此处只展示不调用——调用即装 GPU 驱动）--")
    for line in ncf.display_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("display_")]
    print(f"\n-- 现代显示与 GPU 任务（display_*，{len(base)} 项，只读观测+规范指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：只读观测 ≠ 授权施工——装 GPU 驱动 / 切 Wayland / 改显示配置一律只给规范指引；"
          "控制台/终端/远程终端始终保留。")


def cmd_retro(args):
    """常态化回头看、久久为功（v0.6.42）。

    只读汇总「该定期回头看什么」：维护节奏表、长期保障要点、易漂移维度复盘提示。本身不调用任何写接口。
    """
    from .native import retro as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 常态化回头看、久久为功（retro：维护节奏表 + 长期保障要点 + 易漂移维度复盘，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机回头看汇总（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端常态化回头看报告 --")
    ok, rep = ncf.retro_report(env)
    print(rep)

    base = [t for t in registry.all_tasks() if t.id.startswith("retro_")]
    print(f"\n-- 常态化回头看任务（retro_*，{len(base)} 项，只读汇总提醒）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：retro 只读汇总提醒——不替你做任何操作，只把「该回头看什么」说清楚。")


def cmd_restart(args):
    """人类文明重启计划场景透镜（v0.6.42 · 洪荒重启）。

    只读场景透镜：维度清单、保命优先级（不可再生优先）、知识库离线沉淀指引。只帮你想清楚「重启要保什么、按什么序」。
    """
    from .native import restart as ncf

    env = [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]

    print("\n==== 人类文明重启计划场景透镜（restart · 洪荒重启：维度清单 + 保命优先级 + 知识库沉淀，只读不写） ====")
    print(f"   维度标签: {env or '未声明（默认基线）'}")

    print("\n-- 本机场景透镜（只读）--")
    for line in ncf.environment_report():
        print("   " + line)

    print("\n-- 端到端人类文明重启计划场景透镜报告 --")
    ok, rep = ncf.restart_report(env)
    print(rep)

    base = [t for t in registry.all_tasks() if t.id.startswith("restart_")]
    print(f"\n-- 人类文明重启透镜任务（restart_*，{len(base)} 项，只读场景透镜）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：restart 只读场景透镜——只帮你想清楚「重启要保什么、按什么序」，不做任何施工/搬运。")


def cmd_remote(args):
    """远程接入与传输客户端只读审计（v0.6.30）。

    覆盖 telnet / ssh（OpenSSH）/ filezilla / putty：各自按**自身协议与接口**核对；
    只读探针 + 安全审计（telnet 明文 / ssh 口令登录与 root 直登 / filezilla 明文 FTP +
    弱口令存储），**绝不读解密口令、绝不改 sshd_config、不替你停 telnetd**。

    加固（停用 telnet / sshd 改公钥 / filezilla 用 SFTP + 主密码）一律只给官方指引，
    不代执行——严守只读红线，也契合「个人行为在完全图形界面控制操作」。
    """
    from . import registry
    from .native import remote as nr

    print("\n==== 远程接入与传输客户端（只读审计 + 加固指引，不写配置） ====")
    for line in nr.environment_report():
        print(line)

    print("\n-- 知识库引用（data/remote_clients_docs.json：SSH/Telnet/FileZilla/PuTTY）--")
    for line in nr.remote_doc_list():
        print(line)

    print("\n-- 端到端只读安全审计 --")
    ok, rep = nr.remote_audit_report()
    print(rep)

    print("\n-- 加固/安全指引（此处只展示不调用——调用即写配置）--")
    for line in nr.remote_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("remote_")]
    print(f"\n-- 远程接入与传输任务（remote_*，{len(base)} 项，只读审计+指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：审计 ≠ 授权执行——任何改 sshd_config / 停 telnetd / 改站点配置"
          "只给官方指引；是否操作始终由用户确认。")


def cmd_cert(args):
    """证书与加密开源整合（v0.6.31）：只读审计 + 硬件信任根 + 各种证书。

    整合 OpenSSL/LibreSSL/BoringSSL/GnuTLS 等开源加密栈与最低内置硬件证书（TPM / IDevID），
    做只读审计：EOL 加密库、未启用 TPM、临近过期证书、密钥库不可达。绝不读私钥、绝不解密、
    绝不改配置——加固只给官方指引，契合「个人行为在完全图形界面控制操作」。
    """
    from . import registry
    from .native import cert as nc

    print("\n==== 证书与加密 只读安全审计（无障碍文本，整合 OpenSSL 类开源 + 硬件信任根） ====")
    for line in nc.environment_report():
        print(line)

    print("\n-- 知识库引用（data/cert_docs.json：OpenSSL/LibreSSL/GnuTLS/TPM/X.509/ACME/Keystore…）--")
    for line in nc.cert_doc_list():
        print(line)

    print("\n-- 端到端只读安全审计 --")
    ok, rep = nc.cert_audit_report()
    print(rep)

    print("\n-- 加固/安全指引（此处只展示不调用——调用即写证书/改固件）--")
    for line in nc.cert_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.id.startswith("cert_")]
    print(f"\n-- 证书与加密任务（cert_*，{len(base)} 项，只读审计+指引，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n安全不变量：审计 ≠ 授权执行——升级加密库/启用 TPM/续期证书只给官方指引；"
          "绝不读私钥、绝不解密、绝不替你换证。与「设备长期使用保护(durability)」打通："
          "durability 报告会吸收本审计的证书状态，一并保护关键资产/个人数据/通信能力。")


def cmd_unix(args):
    """Unix（System V）原生接口文档跟踪（IPS pkg / SMF / ZFS / /etc/release /
    logadm / kstat / Zones / FMA / dladm-ipadm）。

    「触类旁通、举一反三」：Windows / macOS / BSD 之后，把同一模式补到
    **System V 自身系统接口**——每个接口完全不同，逐个按**自身的协议与接口**核对，
    绝不套用 Linux 的 /proc/sys、sysctl 或 systemd 写法：
      - IPS pkg  : FMRI + 镜像 + publisher 目录；pkg list/publisher/verify 只读
      - SMF      : svc:/... FMRI + XML manifest + svc.startd 依赖图；svcs -a/-x 只读
      - ZFS      : OpenZFS pool/dataset 属性与校验和；zpool list/status、zfs get 只读
      - /etc/release: System V 的发行信息（不是 /etc/os-release）；cat + uname 只读
      - logadm   : /etc/logadm.conf 集中规则；logadm -V 只校验、-v 只预演
      - kstat    : module:instance:name:class 四元组（Solaris 不从 /proc 读系统态）
      - Zones    : zoneadm list -cv / zonecfg info / zonestat 只读清点
      - FMA      : fmadm faulty / fmdump 只读看自愈状态
      - dladm/ipadm: Crossbow 链路与 IP 分层；show-link/show-addr/show-prop 只读
    全部只读探测；非 System V 环境自动降级为文档指引。清理/优化任务见 unix_*，
    v0.5.14 起另有一组官方写接口深度调优（unix_tune_*，全 opt_in）：
    pkg refresh|fix / svcadm enable|clear / zfs set atime|compression /
    zpool scrub / logadm -r / ipadm set-prop ecn，
    只往安全方向写（服务只开不关、只清 maintenance、ZFS 只改属性不删数据），
    池名与 FMRI 自动探测。
    """
    from . import registry
    from .native import unix as nu

    print("\n==== Unix（System V）原生接口文档跟踪（各自按自身协议与接口） ====")
    for line in nu.environment_report():
        print(line)

    print("\n-- Unix 系统接口文档引用（data/unix_docs.json）--")
    for line in nu.unix_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口）--")
    for fn_name, lab in nu.PROBES:
        ok, msg = getattr(nu, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- Unix 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in nu.unix_tune_list():
        print(line)

    base = [t for t in registry.all_tasks()
            if t.id.startswith("unix") and not t.id.startswith("unix_tune_")]
    tune = [t for t in registry.all_tasks() if t.id.startswith("unix_tune_")]
    print(f"\n-- Unix 清理/优化任务（unix_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- Unix 官方接口深度调优（unix_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform unix --opt-in --yes --apply")
    print("  python -m sysweeper clean --only unix_tune_zfs_atime --opt-in --yes --apply")


def cmd_jdk(args):
    """OpenJDK / JVM 只读体检（java / JPMS / GC / JIT / JFR / 诊断工具面）。

    「推进 openJDK」= 把 OpenJDK 当成被体检对象，而不是在工具里装 JDK。
    按它自己的规范逐项只读核对：
      - java -version / -XshowSettings:properties（**只输出白名单键**，口令类
        属性只报存在性、不回显值——属性表里混有代理密码与令牌）
      - java --list-modules / --describe-module（JPMS 模块系统，JDK 9+）
      - java -XX:+PrintFlagsFinal（只读打印各 GC/JIT 标志的**最终值**，不修改）
      - jcmd -l / jps -l（只列进程，不 attach、不 dump）
      - jfr（只查能力；**start/dump 属写操作，不做**）
    """
    from .native import jdk as nj

    print("\n==== OpenJDK / JVM 只读体检（参照 OpenJDK 官方工程与 JEP） ====")
    for line in nj.environment_report():
        print(line)

    print("\n-- OpenJDK 官方文档参考（data 层：jdk/jvm/jpms/gc/jit/jfr/diagnostics）--")
    for line in nj.jdk_doc_list():
        print(line)

    print("\n-- 明确不执行的高副作用命令（本工具只读，给指引不代跑）--")
    for c in nj.FORBIDDEN_SUBCOMMANDS:
        print("   · " + c)

    base = [t for t in registry.all_tasks() if t.id.startswith("jdk_")]
    print(f"\n-- OpenJDK 相关任务（jdk_*，{len(base)} 项）--")
    for t in base:
        print(f"   • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}"
              f"{'  (opt_in)' if t.opt_in else ''}")
        for s in t.standards:
            print(f"       {s}")


def cmd_kmod(args):
    """Linux 内核 module / firmware / plugin(s) 只读层（对照 kernel.org 源码）。

    用户的「引入/参考/模仿/进阶/超越 linux kernel 的 module(s)、firmware、
    plugin(s)」，在这里落地为**按内核自己的组织方式做只读体检**：

      - **module(s)**  ：/proc/modules、/sys/module（builtin vs live）、
        /sys/module/*/parameters（只读！写它=运行期改内核）、modinfo 元数据
      - **firmware**   ：/lib/firmware 固件库统计、/sys/class/firmware 已加载固件
      - **plugin(s)**  ：eBPF（现代 Linux 事实上的内核级可编程插件）——
        BTF / bpffs / 非特权开关 / kprobe 可挂函数面

    全部只读：不 insmod/rmmod/modprobe、不写 parameters、不替换固件、
    不 attach/load eBPF。高危动作一律以「指引文本」给出。
    """
    from .native import kmod as nk

    print("\n==== Linux 内核 module / firmware / eBPF 只读体检 ====")
    for line in nk.environment_report():
        print(line)

    print("\n-- 内核源码文档引用（对照 kernel.org Documentation）--")
    for line in nk.kmod_doc_list():
        print(line)

    print("\n-- 明确不执行的高危命令（只给指引）--")
    for c in nk.FORBIDDEN_COMMANDS:
        print("   · " + c)

    base = [t for t in registry.all_tasks() if t.id.startswith("kmod_")]
    print(f"\n-- 内核 module/firmware/eBPF 相关任务（kmod_*，{len(base)} 项）--")
    for t in base:
        print(f"   • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}"
              f"{'  (opt_in)' if t.opt_in else ''}")
        for s in t.standards:
            print(f"       {s}")


def _profile_arg(args, default: str = "") -> str:
    """取档位名：未给就用 default；给了但不认识就直接说清楚，不静默当空档位。

    同时接受场景档名（如 elderly-friendly），解析为其基础档位名。
    """
    from . import profiles as pf
    name = (getattr(args, "profile", "") or "").strip() or default
    if name in pf.PROFILES or name in pf.SCENARIOS:
        return name
    print(f"⚠ 未知档位 '{name}'；可选档位：{' / '.join(pf.PROFILE_ORDER)}")
    print(f"  可选场景档：{' / '.join(pf.SCENARIOS)}")
    return ""


def cmd_profiles(args):
    """任务档位（大而全 / 小而全）—— 选一个档位名，而不是手工挑 300 个项。"""
    from . import profiles as pf

    platform, version = _resolve(args)
    print(f"\n==== 任务档位（大而全 / 小而全）｜平台={platform} 版本={version} ====")

    action = getattr(args, "profile_action", "list") or "list"
    if action == "list":
        for line in pf.profile_list(platform, version):
            print(line)
        print("")
        for line in pf.scenario_list(platform):
            print(line)
        print("\n用法：")
        print("  python -m sysweeper profiles show --profile minimal")
        print("  python -m sysweeper profiles tasks --profile standard")
        print("  python -m sysweeper profiles compare --profile minimal --against full")
        print("\n在 clean / scan 中使用档位：")
        print("  python -m sysweeper clean --profile lite --apply --yes")
    elif action == "show":
        name = _profile_arg(args, "minimal")
        if not name:
            return
        print()
        print(pf.profile_detail(name, platform, version, arch=_resolve_arch(args)))
    elif action == "tasks":
        name = _profile_arg(args, "minimal")
        if not name:
            return
        tasks = pf.tasks_in_profile(name, platform, version, arch=_resolve_arch(args))
        print(f"\n档位 {name} 命中 {len(tasks)} 项（平台={platform} {version}）：")
        for t in tasks:
            flag = " [opt_in]" if t.opt_in else ""
            print(f"   • {t.id:<28} [{t.category}/{t.risk}]{flag}  {t.display_title()}")
    elif action == "compare":
        name = _profile_arg(args, "minimal")
        if not name:
            return
        against = (getattr(args, "against", "") or "").strip() or "full"
        if against not in pf.PROFILES:
            print(f"⚠ 未知对照档位 '{against}'；可选：{' / '.join(pf.PROFILE_ORDER)}")
            return
        r = pf.compare_profiles(name, against, platform, version)
        print(f"\n档位对比 {r['a']} vs {r['b']}（平台={platform}）：")
        print(f"   任务数: {r['a']}={r['count_a']}  {r['b']}={r['count_b']}")
        print(f"   Jaccard 重合度 = {r['jaccard']:.4f}"
              f"（|A∩B|/|A∪B|，1=完全相同）")
        print(f"   仅 {r['a']} 有: {len(r['only_a'])} 项"
              f"{'  例: ' + ', '.join(r['only_a'][:8]) if r['only_a'] else ''}")
        print(f"   仅 {r['b']} 有: {len(r['only_b'])} 项"
              f"{'  例: ' + ', '.join(r['only_b'][:8]) if r['only_b'] else ''}")
    else:
        print(f"未知动作: {action}（可选 list|show|tasks|compare）")
    print("\n安全不变量：选档位**不等于授权执行**——执行仍需 --apply；"
          "含 opt_in 的档位另需 --opt-in + --yes 双重确认。")


def cmd_channels(args):
    """版本通道（release channel）：常态稳定版 / 长期支持版 / 尝鲜版。

    通道只决定你接收更新的发布流；选定后仅写入 settings.json 作更新检查标记，
    **工具绝不自动切换或升级你的环境**——是否更新始终由你确认。
    """
    from . import profiles as pf
    from .native import settings as st

    action = getattr(args, "channel_action", "list") or "list"
    if action == "list":
        for line in pf.channel_list():
            print(line)
        print("\n当前已选通道（settings.json）:", st.get("channel", "stable"))
        print("用法：")
        print("  python -m sysweeper channels show --channel lts")
        print("  python -m sysweeper channels recommend --usage heavy --years 5 --env high_humidity,mobile")
        print("  python -m sysweeper channels select --channel lts   # 仅写偏好，不升级")
    elif action == "show":
        name = (getattr(args, "channel", "") or "").strip() or "stable"
        if name not in pf.CHANNELS:
            print(f"⚠ 未知通道 '{name}'；可选：{' / '.join(pf.CHANNEL_ORDER)}")
            return
        print()
        print(pf.channel_detail(name,
                                getattr(args, "usage", "moderate"),
                                int(getattr(args, "years", 4) or 4),
                                [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()]))
    elif action == "recommend":
        rec = pf.channel_recommend(getattr(args, "usage", "moderate"),
                                   int(getattr(args, "years", 4) or 4),
                                   [t.strip() for t in (getattr(args, "env", "") or "").split(",") if t.strip()])
        print(f"据画像（使用量={getattr(args,'usage','moderate')} 期望年限={getattr(args,'years',4)}年 "
              f"环境={getattr(args,'env','') or '默认'}）：")
        print(f"  → 推荐通道：{rec}（{pf.CHANNELS[rec]['title']}）")
    elif action == "select":
        name = (getattr(args, "channel", "") or "").strip() or "stable"
        if name not in pf.CHANNELS:
            print(f"⚠ 未知通道 '{name}'；可选：{' / '.join(pf.CHANNEL_ORDER)}")
            return
        ok, msg = st.set_value("channel", name)
        if ok:
            print(f"✔ 已将通道偏好写入 settings.json: {name}（{pf.CHANNELS[name]['title']}）")
            print("  注意：仅作更新检查标记，**不会自动切换或升级你的环境**；是否更新由你确认。")
        else:
            print(f"✘ 写入失败: {msg}")
    else:
        print(f"未知动作: {action}（可选 list|show|recommend|select）")


def cmd_score(args):
    """数学化量化评估：覆盖度评分（WSM）+ Shannon 熵分布 + 平台均衡度。

    借鉴 openai/math（LaTeX 数学宏集合）背后的「用数学把话说精确」理念，
    工程上落为可计算指标，而**不 vendor 任何 LaTeX 宏包**（那会让本工具
    从「零依赖系统优化器」变成排版工具，且与功能零增益）。

    指标口径：
      · 覆盖广度 breadth = 命中分类数 / 全部分类数
      · 分布均衡 entropy = 归一化 Shannon 熵 H/log₂n（1=不偏科）
      · 任务深度 depth   = 1 − e^(−n/40)
      · 安全性 safety    = 1 − 高危占比 − 0.5×中危占比
      · 总分 = Σ wᵢ·x̂ᵢ（权重 breadth .30 / entropy .25 / depth .25 / safety .20）
    """
    from .native import metrics as mt
    from . import profiles as pf

    platform, version = _resolve(args)
    action = getattr(args, "score_action", "overview") or "overview"

    print("\n==== 数学化量化评估（归一化 + 加权评分 + Shannon 熵） ====")
    print(f"平台={platform} 版本={version}；全库任务 {len(registry.all_tasks())} 项")

    if action == "overview" or action == "global":
        allt = registry.all_tasks()
        print()
        print(mt.score_report(allt, "全库覆盖度评分"))
        print()
        print(mt.entropy_report(mt.category_distribution(allt)))
        gaps = mt.coverage_gaps(allt)
        if gaps:
            print(f"   ⚠ 覆盖缺口（全库无任务的分类）: {gaps}")
        else:
            print("   ✓ 无覆盖缺口：每个分类都有任务")
    elif action == "platform":
        allt = [t for t in registry.all_tasks() if t.platform == platform]
        print()
        print(mt.score_report(allt, f"平台 {platform} 覆盖度评分"))
    elif action == "profile":
        name = _profile_arg(args, "minimal")
        if not name:
            return
        tasks = pf.tasks_in_profile(name, platform, version)
        if not tasks:
            print(f"   ⚠ 档位 {name} 在平台={platform} {version} 下未命中任何任务"
                  "（可能是版本不匹配或该平台任务较少）")
        print()
        print(mt.score_report(tasks, f"档位 {name} 覆盖度评分"))
        print()
        print(mt.entropy_report(mt.category_distribution(tasks)))
    elif action == "balance":
        by_plat: dict = {}
        for t in registry.all_tasks():
            by_plat.setdefault(t.platform, []).append(t)
        b = mt.platform_balance(by_plat)
        print()
        print("平台任务分布均衡度（Gini / 变异系数）：")
        print(f"   Gini = {b['gini']:.4f}（0=均分，1=极端集中）")
        print(f"   变异系数 CV = {b['cv']:.4f}（σ/μ，量纲无关）")
        print(f"   结论: {b['verdict']}")
        for k, v in sorted(b["detail"].items(), key=lambda kv: -kv[1]):
            print(f"     · {k:<12} {v} 项")
    else:
        print(f"未知动作: {action}（可选 overview|global|platform|profile|balance）")
    print("\n说明：本模块是纯标准库实现的量化评估（不 vendor openai/math 的 LaTeX 宏），"
          "目的是让「覆盖得够不够全」从主观感受变成可复现的数字。")


def cmd_android(args):
    """Android 原生接口文档跟踪（adb / settings_provider / pm / am / dumpsys /
    getprop / svc / wm / logcat）。

    「触类旁通、举一反三」：Windows / macOS / BSD / Unix 之后，把同一模式补到
    **Android 自身系统接口**——Android 是 managed OS，PC 端只能经官方 ADB 向设备
    发指令，每个接口都与桌面完全不同，逐个按**自身的协议与接口**核对，绝不套
    注册表/plist/sysctl 或手改系统分区：
      - adb          : client-server（-server :5037 + 设备 adbd），发指令经 framework 校验
      - settings_provider: global/system/secure 三表；settings get/put/list（Android 版「配置」）
      - pm           : PackageManager；pm list/trim-caches/clear/disable-user（缓存与数据分离）
      - am           : ActivityManager；am kill-all（只后台）/ force-stop
      - dumpsys      : 服务状态快照；batterystats/meminfo/netstats（--reset 只清计数）
      - getprop      : 系统属性（ro.build.* 即 Android 的「发行版标识」）
      - svc          : 无线开关；svc wifi/data/nfc enable（只开不关）
      - wm           : 显示尺寸/密度；wm size|density reset（恢复默认，修复性）
      - logcat       : logd 环形缓冲；logcat -d（读）/ -c（清，只清日志）
    全部只读探测（需设备已连且授权）；未连设备时自动降级为文档指引。清理/优化任务
    见 and_*，v0.5.15 起另有一组官方写接口深度调优（and_tune_*，全 opt_in）：
    settings put 关动画 / pm trim-caches / svc wifi enable / dumpsys * --reset /
    logcat -c / am kill-all / wm size|density reset，
    只往安全方向写（动画只关可恢复、缓存只放不删数据、无线只开不关、统计只清计数、
    日志只清缓冲、后台只收不影响前台、显示只 reset 回默认）。
    """
    from . import registry
    from .native import android as na

    print("\n==== Android 原生接口文档跟踪（各自按自身协议与接口） ====")
    for line in na.environment_report():
        print(line)

    print("\n-- Android 系统接口文档引用（data/android_docs.json）--")
    for line in na.android_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口；需设备已连且授权）--")
    for fn_name, lab in na.PROBES:
        ok, msg = getattr(na, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- Android 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in na.android_tune_list():
        print(line)

    # ------------------------------------------------------------------ #
    # v0.5.22 适老化（老年人 / 高龄用户）区块：只读体检 + 纯文字指引
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 68)
    print("适老化（老年人 / 高龄用户）无障碍体检 —— 全部只读，不代改任何开关")
    print("=" * 68)
    ok_a11y, msg_a11y = na.elderly_a11y_report()
    print(msg_a11y)
    print("\n-- 适老化调整建议清单（纯文字，可直接照着念给长辈）--")
    for line in na.elderly_a11y_advice():
        print(line)

    print("\n-- Android 8（API 26）向下兼容口径（各接口最低 API 与本机可用性）--")
    ok_compat, msg_compat = na.android_compat_report()
    print(msg_compat)

    base = [t for t in registry.all_tasks() if t.platform == "android" and not t.opt_in]
    tune = [t for t in registry.all_tasks() if t.platform == "android" and t.opt_in]
    print(f"\n-- Android 清理/优化任务（and_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- Android 官方接口深度调优（and_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform android --opt-in --yes --apply")
    print("  python -m sysweeper clean --only and_tune_trim_cache --opt-in --yes --apply")


def cmd_ios(args):
    """iOS 原生接口文档跟踪（libimobiledevice：ideviceinfo / ideviceinstaller /
    idevicesyslog / idevicecrashreport / idevicediagnostics / idevicebackup2 /
    idevicepair / idevicename / idevicedate / idevicesetlocation / ideviceimagemounter）。

    「触类旁通、举一反三」：Windows / macOS / BSD / Unix / Android 之后，把同一模式
    补到 **iOS 自身系统接口**——iOS 沙盒严格，PC 端只能经 libimobiledevice 向已配对
    设备发指令，每个接口都与桌面/Android 完全不同，逐个按**自身的协议与接口**核对，
    绝不套注册表/plist/sysctl，也绝不 remount 改系统分区（越权，本工具不做）：
      - libimobiledevice: usbmuxd + lockdown 套件；idevice_id -l 判定在线
      - lockdown  : 设备值（DeviceName/ProductVersion/BuildVersion…）；ideviceinfo 读
      - installation_proxy: ideviceinstaller -l（列）/ -a（归档，保留数据）/ -U（卸载，不做）
      - afc       : 容量只读（com.apple.disk_usage）；不挂载写系统目录
      - crashreport: idevicecrashreport -l（列）/ -e（拷贝+删日志，仅日志）
      - syslog_relay: idevicesyslog（只读，3 秒截断快照）
      - diagnostics: idevicediagnostics diagnostics all（读）/ restart（优雅重启）
      - mobilebackup2: idevicebackup2 backup（仅备份到本地，单向、安全）
      - mobile_image_mounter: ideviceimagemounter（挂开发者镜像，可逆）
    全部只读探测（需设备已连且信任）；未连设备时自动降级为文档指引。清理/优化任务
    见 ios_*，v0.5.16 起另有一组官方写接口深度调优（ios_tune_*，全 opt_in）：
    idevicebackup2 backup / ideviceinstaller -a / idevicecrashreport -e /
    idevicedate -s / idevicesetlocation clear / idevicename / idevicediagnostics restart /
    ideviceimagemounter，
    只往安全方向写（备份只进不出、归档只留数据、日志只清缓冲、时间只同步、定位只清、
    设备名只归一化、重启只释放内存、开发者镜像只挂可逆），绝不卸载 App / 绝不 restore。
    """
    from . import registry
    from .native import ios as ni

    print("\n==== iOS 原生接口文档跟踪（libimobiledevice，各自按自身协议与接口） ====")
    for line in ni.environment_report():
        print(line)

    print("\n-- iOS 系统接口文档引用（data/ios_docs.json）--")
    for line in ni.ios_doc_list():
        print(line)

    print("\n-- 本机核对（只读，按各自官方接口；需设备已连且信任）--")
    for fn_name, lab in ni.PROBES:
        ok, msg = getattr(ni, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    print("\n-- iOS 官方写接口（深度调优，此处只展示不调用——调用即写系统）--")
    for line in ni.ios_tune_list():
        print(line)

    base = [t for t in registry.all_tasks() if t.platform == "ios" and not t.opt_in]
    tune = [t for t in registry.all_tasks() if t.platform == "ios" and t.opt_in]
    print(f"\n-- iOS 指引/清理任务（ios_*，{len(base)} 项，执行需 --apply）--")
    for t in base:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print(f"\n-- iOS 官方接口深度调优（ios_tune_*，{len(tune)} 项，全 opt_in）--")
    for t in tune:
        print(f"   • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")
    print("\n开启方式（默认关闭，须显式选择+确认）：")
    print("  python -m sysweeper clean --platform ios --opt-in --yes --apply")
    print("  python -m sysweeper clean --only ios_tune_backup --opt-in --yes --apply")


def cmd_snapshot(args):
    """基线快照与差异对比（纯只读）：capture 生成快照、diff 对比两份、show 查看。

    把跨子系统的只读探测聚合成可归档的 JSON 快照，并在两次扫描间做可追溯对比，
    让「前后对比」不再只是屏幕上的一闪而过。全程只读，不修改系统、不跑清理命令。
    """
    from .native import snapshot as nsnap

    action = getattr(args, "snapshot_action", "capture")

    if action == "capture":
        snap = nsnap.capture_snapshot(include_probes=not getattr(args, "no_probes", False))
        out = args.out or f"sysweeper-snapshot-{snap['meta']['captured_at'][:10]}.json"
        nsnap.save_snapshot(out, snap)
        print(f"已生成基线快照：{out}")
        for line in nsnap.summarize(snap):
            print("  " + line)
        print(f"\n下次对比：python -m sysweeper snapshot diff --a {out} --b <新快照>")

    elif action == "show":
        if not args.file:
            print("请指定 --file <快照路径>")
            return
        snap = nsnap.load_snapshot(args.file)
        print(json.dumps(snap, ensure_ascii=False, indent=2))

    elif action == "diff":
        if not (args.a and args.b):
            print("请同时指定 --a 与 --b 两份快照路径")
            return
        a = nsnap.load_snapshot(args.a)
        b = nsnap.load_snapshot(args.b)
        d = nsnap.diff_snapshots(a, b)
        print(nsnap.format_diff(d))
    else:
        print(f"未知动作：{action}（应为 capture/diff/show）")


def cmd_miniapp(args):
    """uni-app 各小程序端文档跟踪（微信 / 支付宝 / 百度 / 抖音 / QQ / 快手）。

    「触类旁通、举一反三」：跨端框架的每个目标端都有**自己的 API 规范与运行架构**——
    微信 wx.*（双线程）、支付宝 my.*（域名白名单）、百度 swan.*、抖音 tt.*、QQ qq.*、
    快手 ks.*；uni-app 用 uni.* 统一映射，差异由条件编译 #ifdef MP-XXX 隔离。
    只读扫描当前目录的 uni-app 工程（manifest 的 mp-* 节点、产物目录、条件编译）。
    """
    from . import registry
    from .native import miniapp as nmp

    print("\n==== uni-app 各小程序端文档跟踪（按各端自身 API 规范） ====")
    for line in nmp.environment_report():
        print(line)

    print("\n-- 小程序端文档引用（data/miniapp_docs.json）--")
    for line in nmp.miniapp_doc_list():
        print(line)

    print("\n-- 本机核对（只读，扫描 uni-app 工程）--")
    for fn_name, lab in nmp.PROBES:
        ok, msg = getattr(nmp, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.id.startswith("mp_")]
    print(f"\n-- 小程序端核对/清理任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<22} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_harmony(args):
    """鸿蒙（HarmonyOS / OpenHarmony）与 uni-app 鸿蒙端文档跟踪。

    「触类旁通、举一反三」：同样按鸿蒙**自身的协议与接口**核对——Stage 模型（UIAbility /
    Want）、SystemCapability（@ohos.* + canIUse）、HiLog（域/标签/级别）、hdc 设备桥、
    HAP/HSP 应用包与 ohpm/Hvigor 构建、@ohos.rpc 与分布式软总线，以及 uni-app 鸿蒙端
    （HBuilderX 4.27+，仅 vue3，见 uniapp.dcloud.net.cn/tutorial/harmony/）。
    设备侧需 hdc，工程侧扫描当前目录；未安装/未发现一律降级为指引。
    """
    from . import registry
    from .native import harmony as nhm

    print("\n==== 鸿蒙（HarmonyOS / OpenHarmony）文档跟踪（按自身协议与接口） ====")
    for line in nhm.environment_report():
        print(line)

    print("\n-- 鸿蒙文档引用（data/harmony_docs.json）--")
    for line in nhm.harmony_doc_list():
        print(line)

    print("\n-- 本机 / 设备核对（只读）--")
    for fn_name, lab in nhm.PROBES:
        ok, msg = getattr(nhm, fn_name)()
        print(f"   · {lab}: {'✓ 可用' if ok else '不适用'}")
        print("       " + (msg or "").replace("\n", "\n       "))

    tasks = [t for t in registry.all_tasks() if t.platform == "harmony"]
    print(f"\n-- 鸿蒙核对/优化任务（{len(tasks)} 项）--")
    for t in tasks:
        print(f"   • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
        for s in t.standards:
            print(f"       {s}")


def cmd_kaihong(args):
    """KaihongOS 发行版只读识别（深开鸿 / 基于 OpenHarmony）。

    只读识别本机是否为 KaihongOS：版本、variant（Stan/Small/Lite/桌面）、安全基座
    （SELinux/可信应用）、调试工具（hdc/HiLog）。非 KaihongOS 主机降级为指引。
    绝不连设备、绝不改配置。
    """
    from .native import harmony as nhm
    ok, msg = nhm.kaihong_report()
    print("\n==== KaihongOS 发行版识别（深开鸿 / 基于 OpenHarmony） ====")
    print(msg)
    if not ok:
        print("\n（提示：KaihongOS 专有诊断仅在其宿主机/设备上适用；"
              "当前主机按自身发行版接口核对即可。）")


def cmd_media(args):
    """图像/媒体编解码与色彩能力只读诊断（吸收 storytold/photocraft 图像管线视角）。

    只读核验编解码工具链、格式支持矩阵、ICC 色彩管理与 Rust 创意套件就位情况；
    不解码、不转码、不写任何图像文件。
    """
    from .native import media
    ok, msg = media.image_capability_report()
    print("\n==== 图像/媒体编解码与色彩能力（只读） ====")
    print(msg)


def cmd_livemedia(args):
    """可启动介质制作能力只读诊断（吸收 livecd/dvd/bd/usb 制作技术，v0.6.20，只读）。

    只读核验 ISO 构建工具链/BIOS·UEFI 引导加载器/El Torito·混合镜像/压缩根系统/
    U 盘写入工具/本机固件模式/介质规格知识；可选 --iso 对给定镜像做只读可启动性校验。
    绝不 mkisofs/xorriso 构建、绝不 dd 到设备、绝不挂载/解包 ISO。
    """
    from .native import livemedia
    ok, msg = livemedia.livemedia_report(getattr(args, "iso", None))
    print("\n==== 可启动介质制作能力（只读） ====")
    print(msg)


def cmd_legacy(args):
    """遗留/嵌入式/兼容层只读诊断（DOS 3.1 等 · busybox · dosbox，v0.6.21，只读）。

    只读核验遗留 DOS 环境(FreeDOS/DOSEMU2)、busybox 嵌入式用户态、dosbox DOS 模拟兼容层；
    绝不写 DOS 镜像、不 dd、不运行 DOS/DOSEMU/DOSBox、不挂载/解包镜像。
    """
    from .native import legacy
    ok, msg = legacy.legacy_report()
    print("\n==== 遗留 / 嵌入式 / 兼容层（只读） ====")
    print(msg)


def cmd_arch(args):
    """架构/指令集（ISA）报告：龙芯 LoongArch / MIPS / RISC-V / 开源硬件。

    标准按受众分层（国家优先 / 国际给外人 / 地区按需），与 standards 命令同口径。
    """
    from . import arch
    audience = getattr(args, "audience", "cn") or "cn"
    print("\n".join(arch.environment_report(audience)))

    for fn_name, label in (("loongarch_report", "龙芯 LoongArch"),
                           ("mips_report", "MIPS"),
                           ("riscv_report", "RISC-V")):
        ok, msg = getattr(arch, fn_name)()
        print(f"\n-- {label} --")
        prefix = "   " if ok else "   （不适用）"
        print(prefix + (msg or "").replace("\n", "\n   "))

    print("\n-- 开源硬件（OSHWA / CERN OHL / DIN SPEC 3105）--")
    ok, msg = arch.open_hardware_report()
    print("   " + (msg or "").replace("\n", "\n   "))

    key = arch.current_arch()
    print(f"\n-- 构建 --")
    print(f"   工具链: {arch.toolchain_hint(key)}")
    print(f"   Go 交叉构建: {arch.go_build_command(key)}")


def cmd_code(args):
    """低层码制：机器码 / 编译码 / ASCII 等字符编码 / 通信码 / 逻辑转换码。

    五层各有独立动作，全部纯标准库、只读、不联网：

        bits     位与二进制（端序/位域/补码/格雷码/BCD/奇偶/IEEE 754）
        chars    字符编码（ASCII/Unicode/UTF-8/Base/转义/摩尔斯/字符集互转）
        comm     通信码（CRC/校验和/成帧/线路编码/汉明码/波特率）
        logic    逻辑转换码（真值表/范式/卡诺图/QM 化简/NAND/加法器）
        machine  机器码与字节码（Python 字节码/Java class/x86-64 与 RISC-V 指令）
    """
    from .lowcode import bits, chars, comm, logic, machine  # noqa: F401
    from .lowcode import summary as _lowcode_summary

    layer = (getattr(args, "layer", "") or "overview").lower()
    action = (getattr(args, "action", "") or "").lower()
    value = getattr(args, "value", "") or ""
    width = int(getattr(args, "width", 0) or 0)
    y_raw = getattr(args, "y", "") or ""
    baud = int(getattr(args, "baud", 9600) or 9600)
    clock = float(getattr(args, "clock", 16000000.0) or 16000000.0)
    path = getattr(args, "file", "") or ""
    do_sub = bool(getattr(args, "sub", False))

    def read_file():
        if not path:
            return None
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError as exc:
            print(f"（无法读取 {path}：{exc}）")
            return None

    def as_bytes():
        """--value → bytes：优先按十六进制解析，否则按 UTF-8 编码。"""
        s = value.strip().replace(" ", "").replace(":", "")
        if not s:
            return b""
        try:
            if len(s) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in s):
                return bytes.fromhex(s)
        except ValueError:
            pass
        return value.encode("utf-8", "replace")

    if layer in ("", "overview"):
        print(_("==== 低层码制（lowcode）：五层能力 ===="))
        for item in _lowcode_summary():
            print(f"  {item['key']:<8} {item['name']:<10} {item['desc']}")
            print(f"           能力 {item['items']} 项 / 标准出处 {item['standards']} 条")
        print("\n用法：sysweeper code <bits|chars|comm|logic|machine> --action <动作> --value <输入>")
        print("示例：sysweeper code bits --value -7 --width 8")
        print("      sysweeper code chars --value 中文 --action charset")
        print("      sysweeper code comm --value 010300000001 --action crc")
        print("      sysweeper code logic --value 'A & B | !C' --action simplify")
        print("      sysweeper code machine --action py --value 'x = 1 + 2'")
        return

    # ------------------------------------------------------------ bits
    if layer == "bits":
        if action in ("", "explain"):
            n = bits.from_base(value or "0", default_base=10)
            if n is None:
                print(f"（无法解析整数：{value!r}）")
                return
            print("\n".join(bits.explain(n, width or 32)))
            return
        if action == "endian":
            n = bits.from_base(value or "0", default_base=10)
            size = width or 4
            view = bits.endian_view(n, size)
            if "error" in view:
                print(view["error"])
                return
            print(f"数值 {view['value']}（{size} 字节）")
            print(f"  大端：{view['big']['msb_first']}")
            print(f"  小端：{view['little']['wire_order']}")
            print(f"  字节交换后读出的值：0x{view['swapped_value']:X}")
            print(f"  本机字节序：{bits.host_endian()}")
            return
        if action == "float":
            n = bits.from_base(value or "0", default_base=10)
            if n is None:
                print(f"（无法解析：{value!r}）")
                return
            w = width or 32
            if w not in bits.FLOAT_FORMATS:
                print(f"（不支持的浮点位宽 {w}，支持 16/32/64/128）")
                return
            info = bits.decode_float(n, w)
            print(f"位模式 0x{info['hex']}  →  {info['class']}  {info['value']!r}")
            print(f"  符号 {info['sign']}   指数 {info['exponent_raw']}（去偏置 {info['exponent_unbiased']}）"
                  f"   尾数 {info['mantissa_raw']}")
            print(f"  二进制：{info['bin']}")
            return
        if action == "bcd":
            n = bits.from_base(value or "0", default_base=10)
            if n is None:
                print(f"（无法解析：{value!r}）")
                return
            print(f"十进制 {n} → BCD 0x{bits.to_bcd(n):X}，压缩 BCD 字节 {bits.pack_bcd(n).hex()}")
            back = bits.from_bcd(bits.to_bcd(n))
            print(f"反向还原：{back}")
            return
        if action in ("gray", "parity", "popcount"):
            n = bits.from_base(value or "0", default_base=10)
            w = width or 32
            print(f"  格雷码 0x{bits.to_gray(n, w):X}   反格雷 {bits.from_gray(bits.to_gray(n, w), w)}")
            print(f"  popcount {bits.popcount(n)}   偶校验位 {bits.parity(n, True)}"
                  f"   奇校验位 {bits.parity(n, False)}")
            return
        if action == "bases":
            n = bits.from_base(value or "0", default_base=10)
            if n is None:
                print(f"（无法解析整数：{value!r}）")
                return
            print("\n".join(bits.render_bases(n, (2, 3, 8, 10, 16))))
            return
        if action == "base":
            # 把输入（默认按前缀识别进制）转成用户指定的进制，并附十进制可读值
            n = bits.from_base(value or "0", default_base=10)
            if n is None:
                print(f"（无法解析整数：{value!r}）")
                return
            b = args.base or 3
            if not (2 <= b <= 36):
                print("（目标进制需在 2-36 之间，例如 --base 3 表示三进制）")
                return
            print(f"十进制（人类可读）: {bits.human_int(n)}")
            digits = bits.to_base(n, b)
            if b == 2:
                digits = bits.group_bits(digits, 4)
            elif b in (3, 4, 8, 9, 12, 20, 24, 32, 36, 60):
                digits = bits._group_digits(digits, 3)
            print(f"{bits.base_name(b)} ({b}): {digits}")
            return
        print(f"（bits 层未知动作：{action}；可用 explain/endian/float/bcd/gray/bases/base）")
        return

    # ------------------------------------------------------------ chars
    if layer == "chars":
        if action == "charset":
            print("\n".join(chars.render_charset_matrix(value or "中文Abc")))
            return
        if action == "base":
            print("\n".join(chars.render_base_compare(as_bytes() or (value or "hello").encode())))
            return
        if action == "escape":
            print("\n".join(chars.render_escape_compare(value or "中文 a/b")))
            return
        if action == "morse":
            r = chars.morse_encode(value or "SOS")
            print(f"摩尔斯：{r['morse']}   （未知字符 {r['unknown']} 个，{r['standard']}）")
            print(f"反向解码：{chars.morse_decode(r['morse'])['text']}")
            return
        if action == "mojibake":
            data = as_bytes()
            if not data:
                print("（请给 --value，十六进制字节串，例如 d6d0cec4）")
                return
            print("\n".join(chars.render_mojibake(data)))
            return
        if action == "ascii":
            print("\n".join(chars.render_controls()))
            print()
            print("\n".join(chars.render_ascii_table(cols=4, start=32, end=128)))
            return
        # 默认：逐字符档案
        if not value:
            print("\n".join(chars.render_controls()))
            return
        print("\n".join(chars.render_text_bytes(value)))
        for ch in value[:8]:
            info = chars.char_info(ch)
            print(f"  {info['uplus']}  {info['name']}  "
                  f"UTF-8 {info['utf8']['hex_spaced']}（{info['utf8']['bytes']} 字节）"
                  f"  HTML {info['html']}")
        return

    # ------------------------------------------------------------ comm
    if layer == "comm":
        if action in ("", "crc"):
            data = as_bytes() or b"123456789"
            print("\n".join(comm.render_crc_catalog(data)))
            return
        if action == "checksum":
            print("\n".join(comm.render_checksums(as_bytes() or b"123456789")))
            return
        if action == "frame":
            print("\n".join(comm.render_framing(as_bytes() or bytes([0x7E, 0x00, 0x11]))))
            return
        if action == "line":
            bitstr = "".join(c for c in value if c in "01") or "10110010"
            print("\n".join(comm.render_line_compare(bitstr)))
            return
        if action == "hamming":
            print("\n".join(comm.render_hamming_table()))
            return
        if action == "uart":
            try:
                nbytes = int(value or 1024)
            except ValueError:
                nbytes = 1024
            r = comm.uart_time(nbytes, baud, width or 8)
            print(f"{r['bytes']} 字节 @ {r['baud']} bps：每帧 {r['bits_per_frame']} 位，"
                  f"共 {r['total_bits']:.0f} 位 → {r['ms']:.2f} ms")
            print(f"  有效吞吐 {r['throughput_Bps']:.0f} 字节/秒，"
                  f"帧效率 {r['frame']['efficiency'] * 100:.0f}%")
            return
        if action == "baud":
            print("\n".join(comm.render_baud_table(clock, 16)))
            return
        print(f"（comm 层未知动作：{action}；可用 crc/checksum/frame/line/hamming/uart/baud）")
        return

    # ------------------------------------------------------------ logic
    if layer == "logic":
        expr = value or "A & B | !C"
        if action == "table":
            print("\n".join(logic.render_truth_table(expr)))
            return
        if action in ("sop", "pos", "canonical"):
            forms = logic.canonical_forms(expr)
            print(f"变量：{', '.join(forms['variables'])}")
            print(f"最小项 Σm({','.join(str(m) for m in forms['minterms'])})")
            print(f"最大项 ΠM({','.join(str(m) for m in forms['maxterms'])})")
            print(f"SOP：{forms['sop']}")
            print(f"POS：{forms['pos']}")
            return
        if action == "kmap":
            t = logic.truth_table(expr)
            print("\n".join(logic.render_karnaugh(t["minterms"], len(t["variables"]),
                                                  t["variables"])))
            return
        if action == "qm":
            print("\n".join(logic.render_qm(expr)))
            return
        if action == "nand":
            r = logic.nand_report(expr)
            print(f"表达式：{r['expression']}")
            print(f"  门数：{r['gate_count']}")
            print(f"  仅用 NAND：{r['nand_expr']}（{r['nand_gates']} 个门）")
            print(f"  仅用 NOR ：{r['nor_expr']}（{r['nor_gates']} 个门）")
            return
        if action == "adder":
            try:
                x = int(value) if value else 0
            except ValueError:
                x = 0
            try:
                y = int(y_raw) if y_raw else 0
            except ValueError:
                y = 0
            print("\n".join(logic.render_adder(x, y, width or 8, do_sub)))
            return
        # 默认：化简 + 等价性校验
        try:
            r = logic.simplify(expr)
        except logic.ParseError as exc:
            print(f"（表达式解析失败：{exc}）")
            return
        print(f"原式  ：{r['original']}")
        print(f"最简式：{r['expression']}")
        print(f"等价性：{'通过（真值表逐行比对）' if r['equivalent'] else '不一致！'}")
        return

    # ------------------------------------------------------------ machine
    if layer == "machine":
        if action == "py":
            src = value or "x = 1 + 2 * 3\nprint(x)"
            print("\n".join(machine.render_python_bytecode(src)))
            return
        if action == "pyc":
            data = read_file()
            if data is None:
                magic = machine.pyc_magic()
                print(f"本机 .pyc 魔数：{magic['magic']}（Python {magic['python']}）")
                return
            head = machine.parse_pyc_header(data)
            if "error" in head:
                print(head["error"])
                return
            print(f"魔数 {head['magic']}（{'与本机一致' if head['matches_interpreter'] else '与本机不一致'}）")
            print(f"校验方式：{head['check']}   字段：{head['field1']} / {head['field2']}")
            return
        if action == "x86":
            data = read_file() or as_bytes()
            if not data:
                print("\n".join(machine.render_x86_samples()))
                return
            print("\n".join(machine.render_x86(data)))
            return
        if action == "riscv":
            data = read_file() or as_bytes()
            if not data:
                print("\n".join(machine.render_riscv64_samples()))
                return
            print("\n".join(machine.render_riscv64(data)))
            return
        if action == "java":
            data = read_file()
            if data is None:
                print("（请用 --file 指定 .class 文件）")
                return
            print("\n".join(machine.render_classfile(data)))
            print()
            print("\n".join(machine.render_java_bytecode(data, 0)))
            return
        if action == "ident":
            data = read_file() or as_bytes()
            if not data:
                print("（请用 --file 或 --value 给出字节）")
                return
            info = machine.identify(data)
            print(f"格式：{info['format']}   魔数：{info['magic']}   {info['size']} 字节")
            print(f"说明：{info['note']}")
            return
        # 默认：概览 + x86 样例
        magic = machine.pyc_magic()
        print(f"Python {magic['python']} 的 .pyc 魔数：{magic['magic']}")
        print()
        print("\n".join(machine.render_x86_samples()))
        print("\n用法：--action py|pyc|x86|riscv|java|ident（java/ident 需 --file）")
        return

    print(f"（未知层：{layer}）")


def cmd_fonts(args):
    """展示字体/字符标准参考（Unicode 18.0.0 最新稳定版 + 原生接口读取）。"""
    from . import registry
    from .native import fonts as nf
    print("\n==== 字体/字符标准参考（Unicode 18.0.0 最新稳定版 + 原生接口） ====")
    enc = nf.system_encoding()
    print("-- 系统文本编码（对照 Unicode / ISO-IEC 10646）--")
    print("   " + "  ".join(f"{k}={v}" for k, v in enc.items() if v))
    print(f"   UTF-8: {'是（符合 Unicode 推荐）' if nf.is_utf8() else '否（建议设为 UTF-8）'}")

    # 编码模式与 UTF-8 向下兼容判定
    mode = getattr(args, "encoding", "utf-8") or "utf-8"
    print(f"-- 编码模式：{mode} --")
    ok, msg = nf.encoding_backward_compatible_with_utf8(mode)
    print(f"   向下兼容 UTF-8: {'是' if ok else '否'}  {msg}")
    eok, eff, enote = nf.effective_encoding(mode)
    if eok and eff:
        print(f"   实际落盘编码: {eff}  {enote}")

    print("-- 已安装字体（按字体标准类）--")
    fonts = nf.list_fonts()
    if fonts:
        print(f"   共 {len(fonts)} 个（示例：{', '.join(fonts[:5])} …）")
        dups = nf.duplicate_fonts(fonts)
        if dups:
            print(f"   疑似冗余字体: {len(dups)} 组（{dups[0]['name']} …）")
    else:
        print("   （无 fontconfig / 系统字体目录不可读；装 fontconfig 后可见）")
    print("-- 文本 Unicode 规范化（UAX #15 NFC）--")
    nok, nmsg = nf.text_normalize_report()
    print(f"   {'OK' if nok else '需关注'}  {nmsg}")
    print("\n标准参考（data/fonts_standards.json）：")
    for sid, ref in nf.reference_all().items():
        if sid.startswith("_"):
            continue
        print(f"   · {ref.get('name','')}  [{ref.get('standard','')} / {ref.get('org','')}]")
    print("\n相关任务（python -m sysweeper list --category fonts）：")
    for t in registry.all_tasks():
        if t.category == "fonts":
            print(t.line())


def cmd_toggles(args):
    """列出网络协议 / ITU 标准的 opt-in 开关（默认关闭，需选择+确认）。"""
    tasks = registry.opt_in_tasks()
    print("\n==== 网络协议 / ITU 标准 开关（默认关闭，需选择 + 确认） ====")
    if not tasks:
        print("  （无 opt-in 开关）")
        return
    for t in tasks:
        std = t.display_notes()[0] if t.display_notes() else ""
        print(f"  ○ {t.id:<18} [{t.risk}] {t.display_title()}")
        if std:
            print(f"        {std}")
    print("\n开启方式（默认关闭，必须显式选择并确认）：")
    print("  python -m sysweeper clean --category network --opt-in --yes --apply")
    print("  python -m sysweeper clean --only net_ipv6_privacy --opt-in --yes --apply")
    print("\n联动：开启网络协议后，字体分类下的「网络字体（@font-face 拉取 WOFF2）」同步可用：")
    print("  python -m sysweeper list --category fonts --opt-in")


def cmd_standards(args):
    """展示「分类规范整体」：每个分类的标准出处（按受众分层）→ 任务计数 → 逐类任务。

    标准引用优先级由 --audience 决定：
      cn      国内优先：国家标准/国家平台 → 国际 → 地区
      intl    面向外国用户：国际标准 → 国家 → 地区
      regional 按地区执行：地区 → 国家 → 国际
    """
    from . import registry
    from .models import (CATEGORY_ORDER, CATEGORIES, category_standards,
                         standards_for_audience, task_standards_ordered,
                         STANDARD_TIERS, NATIONAL_STANDARD_PORTAL)

    audience = getattr(args, "audience", "cn") or "cn"
    audience_label = {"cn": "国内（优先国家平台/国家标准）",
                      "intl": "面向外国用户（优先国际标准）",
                      "regional": "按国家/地区执行（优先地区标准）",
                      "us": "美国（优先 NIST / Section 508 / ENERGY STAR）",
                      "jp": "日本（优先 JIS / APPI）",
                      "eu": "欧盟（优先 GDPR / EN 301 549 / ErP）",
                      "de": "德国（优先 DIN SPEC 3105 开放硬件）"}.get(audience, audience)
    print(f"\n==== 分类规范整体（分类 → 标准出处[受众:{audience_label}] → 覆盖 → 任务） ====")
    print(f"国家平台: {NATIONAL_STANDARD_PORTAL}")
    cat = registry.category_summary()
    grouped = registry.tasks_by_category()
    for c in CATEGORY_ORDER:
        label = CATEGORIES.get(c, c)
        st = category_standards(c)
        n = cat.get(c, 0)
        suffix = "（含在下方 opt-in 开关中）" if c == "network" and n == 0 else ""
        print(f"\n■ {label}（{c}）：任务 {n} 项{suffix}")
        if st.get("doc"):
            print(f"   标准文档: {st['doc']}")
        # 按受众优先级展示三层标准
        ordered = standards_for_audience(c, audience)
        tier_of = {}
        for tier, _ in STANDARD_TIERS:
            for s in st.get("standards", {}).get(tier, []):
                tier_of[s] = tier
        for s in ordered:
            tag = {"national": "国标", "international": "国际", "regional": "地区"}.get(
                tier_of.get(s, ""), "")
            mark = "①" if (audience == "cn" and tier_of.get(s) == "national") or \
                (audience == "intl" and tier_of.get(s) == "international") or \
                (audience == "regional" and tier_of.get(s) == "regional") else " "
            print(f"   {mark} [{tag}] {s}")
        items = grouped.get(c, [])
        if not items:
            print("   任务: （暂无——该分类可补）")
        else:
            for t in items:
                print(f"   • {t.id:<22} [{t.platform}/{t.risk}]  {t.display_title()}")
                for s in task_standards_ordered(t, audience):
                    print(f"       {s}")

    opt = grouped.get("(opt_in)", [])
    print(f"\n默认关闭的 opt-in 开关: {len(opt)} 项（网络/ITU 调优，需 --opt-in + --yes）")
    for t in opt:
        print(f"   • {t.id:<22} [{t.platform}/{t.risk}]  {t.display_title()}")
        for s in task_standards_ordered(t, audience):
            print(f"       {s}")

    # 平台覆盖矩阵
    print("\n平台任务分布：")
    ps = registry.platform_summary()
    names = ["windows", "macos", "linux", "bsd", "unix", "android", "ios", "uniapp", "any"]
    for pf in names:
        n = ps.get(pf, 0)
        if n:
            print(f"   {registry.PLATFORM_NAMES.get(pf, pf):<26} {n} 项")
    print("\n（标准引用分层见 models.STANDARD_TIERS / CATEGORY_STANDARDS；"
          "各标准详细条目见 data/*.json）")


def _ver_text(version: str) -> str:
    """版本文案：未指定（空或占位 0）时不显示，避免出现「Linux 0 适用任务」。"""
    v = (version or "").strip()
    return "" if (not v or v == "0") else f" {v}"


def cmd_list(args):
    platform, version = _resolve(args)
    arch = _resolve_arch(args)
    tasks = _select_tasks(args, platform, version, arch)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    arch_tag = f" / 架构={arch}" if arch else ""
    ptag = f" [档位 {args.profile}]" if getattr(args, "profile", "") else ""
    print(f"\n{name}{_ver_text(version)}{arch_tag}{ptag} 适用任务（共 {len(tasks)} 项）：")
    for t in tasks:
        print(t.line())
    if args.category:
        print(f"（已按分类过滤：{CATEGORIES.get(args.category, args.category)}）")
    if args.opt_in:
        print("（含默认关闭的网络/ITU 开关）")


def cmd_notes(args):
    platform, version = _resolve(args)
    tasks = registry.applicable(platform, version, include_opt_in=args.opt_in)
    if getattr(args, "profile", ""):
        from . import profiles as pf
        pn = args.profile
        tasks = (pf.scenario_tasks(pn, platform, version)
                 if pn in pf.SCENARIOS
                 else pf.tasks_in_profile(pn, platform, version))
    name = registry.PLATFORM_NAMES.get(platform, platform)
    ptag = f" [档位 {args.profile}]" if getattr(args, "profile", "") else ""
    print(f"\n{name}{_ver_text(version)}{ptag} 的注意事项与风险提示：")
    any_ = False
    for t in tasks:
        for c in t.display_caveats():
            any_ = True
            print(f"  ⚠ [{t.display_title()}] {c}")
        for n in t.display_notes():
            any_ = True
            print(f"  ★ [{t.display_title()}] {n}")
    if not any_:
        print("  （无特别注意事项）")


def _select_tasks(args, platform: str, version: str, arch):
    """按 --profile 档位（若有）选取任务，并叠加 --risk / --opt-in / --only 收窄。

    档位优先：`--profile minimal` 直接给出该档位的任务集合（已含风险与 opt_in
    语义），再按用户显式给的 --risk 上限 / --opt-in 开关 / --only 进一步收窄。
    未给 --profile 时走 registry.applicable 的原有行为（向后兼容）。
    """
    only = _split_ids(getattr(args, "only", ""))
    pname = (getattr(args, "profile", "") or "").strip()
    if pname:
        from . import profiles as pf
        if pname not in pf.PROFILES and pname not in pf.SCENARIOS:
            print(f"未知档位: {pname}（可选 {'/'.join(pf.PROFILE_ORDER)} "
                  f"或场景档 {'/'.join(pf.SCENARIOS)}）")
            sys.exit(2)
        if pname in pf.SCENARIOS:
            tasks = pf.scenario_tasks(pname, platform, version, arch=arch)
            label = f"场景档 {pname}（基于 {pf.SCENARIOS[pname]['base']}）"
        else:
            tasks = pf.tasks_in_profile(pname, platform, version, arch=arch)
            label = f"档位 {pname}"
        # 再按用户显式参数收窄（档位给基线，参数做减法）
        from .models import RISK_ORDER
        maxr = RISK_ORDER.get(args.risk, 2)
        tasks = [t for t in tasks if RISK_ORDER.get(t.risk, 0) <= maxr]
        if not args.opt_in:
            tasks = [t for t in tasks if not t.opt_in]
        if only:
            tasks = [t for t in tasks if t.id in only]
        print(f"（按{label}选取 {len(tasks)} 项；档位仅决定默认范围，"
              f"执行仍需 --apply/--yes/--opt-in 确认）")
        return tasks
    return registry.applicable(platform, version, args.category, args.risk,
                               include_opt_in=args.opt_in, only_ids=only, arch=arch)


def cmd_scan(args):
    platform, version = _resolve(args)
    arch = _resolve_arch(args)
    tasks = _select_tasks(args, platform, version, arch)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    arch_tag = f" / 架构={arch}" if arch else ""
    if args.opt_in:
        print("（已包含默认关闭的网络/ITU 开关，仅分析不修改）")
    print(f"\n扫描 {name} {version}{arch_tag}：以下为可执行的优化/清理项（分析模式，不会修改系统）")
    before = measure_disk(platform)
    results: list = []
    analyze(tasks, platform, apply=False, yes=False, risk_limit=args.risk,
            collector=results)
    if args.report:
        _emit_report(args.report, platform, version, "scan", results, before, None)


def cmd_clean(args):
    platform, version = _resolve(args)
    arch = _resolve_arch(args)
    tasks = _select_tasks(args, platform, version, arch)
    name = registry.PLATFORM_NAMES.get(platform, platform)
    arch_tag = f" / 架构={arch}" if arch else ""
    if args.opt_in and not args.yes:
        print("⚠ 含网络/ITU 开关：需再加 --yes 确认才会执行（默认关闭、需选择+确认）。")
    print(f"\n对 {name} {version}{arch_tag} 执行清理（apply={args.apply}, risk<={args.risk}, "
          f"yes={args.yes}, opt_in={args.opt_in}）")
    if not args.apply:
        print("（未加 --apply，仅展示；加 --apply 才会真正执行）\n")
    before = measure_disk(platform)
    results: list = []
    rc = analyze(tasks, platform, apply=args.apply, yes=args.yes, risk_limit=args.risk,
                 collector=results)
    after = measure_disk(platform) if args.apply else None
    if args.report:
        _emit_report(args.report, platform, version,
                     "clean" if args.apply else "scan", results, before, after)
    if rc:
        print(f"\n有 {rc} 个动作执行失败。")
        sys.exit(1)


def _emit_report(path, platform, version, mode, results, before, after):
    """生成并写出前后对比报告（.md 或 .json）。"""
    from . import report as repmod
    rep = repmod.generate(platform, version, mode, [], results, before, after)
    try:
        out = repmod.write_report(path, rep)
        print(f"\n报告已生成: {out}（模式={mode}，任务 {rep['task_count']} 项）")
    except Exception as e:  # noqa: BLE001
        print(f"\n报告生成失败: {e}")


def _emit_cache_report(path, rep: dict, env_label: dict, fmt) -> str:
    """写出桌面缓存只读对比报告（.json 写 JSON，否则写 Markdown）。"""
    import json
    from datetime import datetime, timezone
    if path.endswith(".json"):
        payload = dict(rep, generated_at=datetime.now(timezone.utc).isoformat())
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
    lines = []
    lines.append("# 桌面缓存只读对比报告（不删除任何文件）\n")
    lines.append(f"- 生成时间: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- 当前桌面环境: {env_label.get(rep.get('current', ''), rep.get('current', ''))}")
    lines.append("")
    lines.append("## 各桌面环境缓存估算\n")
    for e in rep.get("entries", []):
        mark = "  ◀当前桌面" if e.get("current") else ""
        lines.append(f"- **{env_label.get(e['env'], e['env'])}{mark}**: {fmt(e.get('total', 0))}")
        for d in e.get("dirs", []):
            if d.get("size"):
                lines.append(f"  - `{d['path']}` ({fmt(d['size'])})")
    xdg = rep.get("xdg") or []
    if xdg:
        lines.append(f"\n## XDG 通用缓存（缩略图/着色器/mozilla 等）: {fmt(sum(x['size'] for x in xdg))}\n")
        for x in xdg:
            lines.append(f"- `{x['path']}` ({fmt(x['size'])})")
    lines.append("")
    lines.append(f"## 合计可回收（只读估算，不删除）\n\n**{fmt(rep.get('grand_total', 0))}**\n")
    lines.append("说明：以上为 `~/.cache` 下已知缓存目录占用；"
                 "执行 `desktop_gnome_cache` / `desktop_kde_cache` / `desktop_xfce_cache` 等任务"
                 "（需 `--apply`）才会真正回收。")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def cmd_uniapp(args):
    """展示 uni-app 需要的原生能力与 API 清单，以及该目标端的清理/优化任务。"""
    from . import registry
    data = load_uniapp_api()
    print("\n==== uni-app 需要的原生能力与 API ====")
    for g in data.get("groups", []):
        print(f"\n-- {g.get('name','')} --")
        if g.get("note"):
            print(f"   {g['note']}")
        for a in g.get("apis", []):
            print(f"   • {a.get('name','')}")
            print(f"       {a.get('desc','')}")
            print(f"       端: {', '.join(a.get('platforms', []))}"
                  f"　标准: {a.get('standard','')}")
    version = args.version or "4"
    tasks = registry.applicable("uniapp", version)
    print(f"\n==== uni-app 目标端的清理/优化任务（{version}，共 {len(tasks)} 项）====")
    for t in tasks:
        print(t.line())
    print("\n用法：")
    print(f"  python -m sysweeper list  --platform uniapp --version {version}")
    print(f"  python -m sysweeper scan  --platform uniapp --version {version}")
    print("  python -m sysweeper clean --platform uniapp --version 4 --apply --risk low")
    print("\n说明：uni-app 不是操作系统，而是「一套代码编译到 App/H5/小程序」的跨端框架，"
          "因此作为目标端需手动指定 --platform uniapp。")


def cmd_gui(args):
    """启动图形界面（优先 Python 自带 tkinter，零依赖）。"""
    from .gui import launch_or_fallback
    rc = launch_or_fallback(args.platform, args.version or "")
    if rc:
        sys.exit(rc)


def cmd_chart(args):
    """读取一个 JSON 报告（由 --report xxx.json 生成），打印 ASCII 可视化对比。"""
    from . import report as repmod
    import json
    try:
        rep = json.load(open(args.file, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"无法读取报告 {args.file}: {e}")
        sys.exit(1)
    print(f"\n==== 可视化对比（来自 {args.file}） ====\n")
    print(repmod.render_bars(rep))


def cmd_genbat(args):
    """生成 Windows 自包含 .bat（分析/执行/注册计划任务三模式）。"""
    from .windows_bat import write_bat
    version = args.version or "11"
    risk = args.risk
    out = args.output or f"sysweeper_optimize_win{version}.bat"
    n = write_bat(out, version=version, risk_limit=risk, task_name=args.task_name,
                  encoding=args.encoding)
    encname = {"utf-8-sig": "UTF-8(BOM)", "utf-8": "UTF-8", "gbk": "GBK"}.get(
        args.encoding, args.encoding)
    print(f"已生成自包含 .bat：{out}  ({n} 字节, 编码 {encname})")
    print("用法（在 Windows 上以管理员运行）：")
    print(f"  {out}            分析模式（只显示，不修改）")
    print(f"  {out} apply      执行（低风险直接跑，中/高风险逐一确认）")
    print(f"  {out} schedule   注册为每周一 09:00 的计划任务")


def _split_ids(raw) -> list:
    if not raw:
        return None
    out = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            out.append(part)
    return out or None


def cmd_webnews(args):
    """新闻/网站聚合优化资讯（只读层，v0.6.11）。

    fetch     : 抓取你配置的 http(s) 来源 → 解析 → 抽取优化知识点（--source 可临时追加 URL；
                不填则只抓 DEFAULT_SOURCES，默认空 = 不联网）。
    knowledge : 仅展示已缓存的知识点（不重新联网）。
    sources   : 列出当前配置的来源与安全边界。
    caps      : 能力自检（能不能用、依赖缺不缺）。
    默认（无动作）= 总报告：能力 + 来源 + 知识点。

    红线：抓来的永远是文本，本层无执行路径——不 eval、不 subprocess、不自动改系统。
    """
    from .native import webnews as nw
    act = getattr(args, "webnews_action", None) or "report"
    if act == "fetch":
        sources = list(getattr(args, "source", []) or []) or list(nw.DEFAULT_SOURCES)
        res = nw.fetch_all(sources)
        print("\n==== 资讯抓取（只读；失败源如实报「未能获取」，不编造） ====")
        print(f"来源 {res['sources_total']} 个，成功 {res['fetched']} 个，"
              f"条目 {res['items']} 条，命中分类 {len(res['tips_by_cat'])} 个")
        if res["errors"]:
            print("抓取失败（已跳过，不影响其它源）：")
            for e in res["errors"]:
                print(f"  ✗ {e}")
        ok, msg = nw.knowledge_report()
        print()
        print(msg)
        return
    if act == "knowledge":
        ok, msg = nw.knowledge_report()
    elif act == "sources":
        ok, msg = nw.sources_report()
    elif act == "caps":
        ok, msg = nw.capabilities_report()
    else:  # report
        ok, msg = nw.webnews_report()
    print(msg)


def cmd_edge(args):
    """单板机/ARM SBC 只读探测与优化建议（新硬件，v0.6.11）。

    report（默认）：板型 + 温度 + 降频/欠压 + 启动盘类型，附只读建议。
    caps         ：能力自检（探测接口与红线）。

    非 SBC（x86 桌面/服务器）上 detect_board 读不到设备树型号，优雅降级为「未识别为单板机」。
    红线：只读。不改频率/电压、不写 sysfs、不装散热服务。
    """
    from .native import edge as ne
    act = getattr(args, "edge_action", None) or "report"
    ok, msg = (ne.capabilities_report() if act == "caps" else ne.edge_report())
    print(msg)


def cmd_mesh(args):
    """组网节点发现（能力通告 SW-OFFER1 注册表，v0.6.11）。

    nodes（默认）：已知在线节点（来自收到的能力通告；TTL 过期自动剔除）。
    announce     ：广播本机能力通告（SW-OFFER1: + JSON，仅声明能接什么活）。
    protocol     ：协议说明（只读安全命令白名单等）。

    节点注册表是本机内存态；收不到通告时为空属正常（说明当前网段没有在广播的节点）。
    """
    from .native import meshchat
    act = getattr(args, "mesh_action", None) or "nodes"
    if act == "announce":
        ok, msg = meshchat.announce_offer()
        print(f"\n能力通告广播: {'已发出' if ok else '未发出'} — {msg}")
        return
    if act == "protocol":
        ok, msg = meshchat.protocol_report()
    else:  # nodes
        ok, msg = meshchat.node_report()
    print(msg)


def cmd_osi(args):
    """OSI 七层网络诊断（v0.6.13「以 OSI 为基础整体补全」，只读）。

    report（默认）：L1 物理→L7 应用 整体只读诊断（每层附参照文档）。
    layer  N      ：只看第 N 层（1–7）。
    probe  --url U：外网可达性探测（仅 http/https + 短超时；显式、不默认开）。
    caps          ：能力自检（每层是否可诊断 + 红线）。

    红线：只读 /sys/class/net、ip/ss/ethtool/openssl 只读项、DNS 解析、显式 http(s)
    探测；不写地址/路由/防火墙，不连校外网做写操作。
    """
    from .native import osi
    act = getattr(args, "osi_action", None) or "report"
    if act == "caps":
        ok, msg = osi.capabilities_report()
    elif act == "layer":
        n = int(getattr(args, "layer", 0) or 0)
        ok, msg = osi.layer_report(n)
    elif act == "probe":
        url = getattr(args, "url", None)
        if not url:
            print("probe 需要 --url <http(s)>；仅支持 http:// 或 https://（红线）")
            return
        ok, msg = osi.probe_http(url)
    else:  # report
        ok, msg = osi.osi_report()
    print(msg)


def cmd_distro(args):
    """发行版识别与发行注记读取（v0.6.13，只读）。

    report（默认）：发行版身份 + 本机可用注记来源清单。
    notes  --pkg P：读包 P 的本地 NEWS.Debian / changelog（只读本地，不联网）。
    caps          ：能力自检（识别 + 本地注记路径存在性）。

    红线：不 apt-get changelog（联网）、不改源、不写文件。
    """
    from .native import distro
    act = getattr(args, "distro_action", None) or "report"
    if act == "notes":
        pkg = getattr(args, "pkg", None)
        ok, msg = distro.release_notes(pkg=pkg or "", limit=6000)
    elif act == "caps":
        ok, msg = distro.capabilities_report()
    else:  # report
        ok, msg = distro.distro_report()
    print(msg)


def cmd_proton(args):
    """游戏/应用兼容层诊断（v0.6.14，只读，基于 Proton/Wine 坐标系）。

    report（默认）：Vulkan 支撑栈 / 32 位 i386 / NT 同步原语(esync·fsync·NTSync) /
                   Steam Runtime 与 Proton-Wine 安装，逐项给结论与修复提示。
    caps          ：能力自检（各维度是否可诊断 + 红线）。

    红线：不装包、不写 Wine prefix、不改内核参数、不连校外网。
    """
    from .native import proton
    act = getattr(args, "proton_action", None) or "report"
    if act == "caps":
        ok, msg = proton.capabilities_report()
    else:  # report
        ok, msg = proton.proton_report()
    print(msg)


def cmd_wsl(args):
    """WSL 环境诊断（v0.6.15，只读，基于 microsoft/wsl2-linux-kernel）。

    红线：不写 wsl.conf/.wslconfig、不 wsl --shutdown、不连校外网。
    """
    from .native import wsl
    ok, msg = wsl.wsl_report()
    print(msg)


def cmd_virtgpu(args):
    """虚拟化与 GPU 虚拟化诊断（v0.6.15，只读，基于 arehnman/yttrium-virtio-gpu）。

    红线：不加载模块、不装驱动、不改 QEMU/crosvm、不连校外网。
    """
    from .native import virtgpu
    ok, msg = virtgpu.virtgpu_report()
    print(msg)


def cmd_browser(args):
    """浏览器与引擎检测 + Web 兼容知识参考（v0.6.15，只读，基于 mdn/browser-compat-data）。

    红线：不下载 BCD 全量 JSON、不连校外网、不自动改浏览器配置。
    """
    from .native import browser
    ok, msg = browser.browser_report()
    print(msg)


def cmd_dnshealth(args):
    """DNS 解析健康度诊断（v0.6.15，只读，基于 python-dnspython 打包视角）。

    默认不发起解析探测（零出网）；``--query`` 可开启一次良性 A 查询。
    红线：不写 resolv.conf、不改 DNS。
    """
    from .native import dnshealth
    query = getattr(args, "query", False)
    ok, msg = dnshealth.dnshealth_report(query=query)
    print(msg)


def cmd_tor(args):
    """Tor（洋葱路由）匿名/隐私网络只读诊断（v0.6.17，只读）。

    只读核验 tor 安装/版本/守护进程/torrc 配置/可插拔传输；不启停 tor、不改 torrc、
    不连控制端口、不打印密钥明文。
    """
    from .native import tor
    ok, msg = tor.tor_report()
    print(msg)


def cmd_zerotier(args):
    """ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断（v0.6.17，只读）。

    只读核验 zerotier-one 安装/版本/运行态/identity/已加入网络/控制器/moon；
    不启停 zerotier-one、不 join/leave、不读 identity.secret。
    """
    from .native import zerotier
    ok, msg = zerotier.zerotier_report()
    print(msg)


def cmd_sysmap(args):
    """系统统筹总览（v0.6.22，只读）：你中有我，我中有你；统筹系统与局部兼顾。

    只读编排**已开启**的子系统诊断（全量登记、可配置开关），输出「开关状态 + 整体健康汇总 +
    局部本征状态 + 关联关系图 + 有序深入建议」。不启停服务、不改配置、不连控制端口、不写状态。
    """
    from .native import sysmap
    ok, msg = sysmap.sysmap_report()
    print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# v0.6.33：联动连轴体检（有方向有性质的联通图 + 孤岛/悬空自检）
# ─────────────────────────────────────────────────────────────────────────────
def cmd_linkage(args):
    """联动连轴体检（v0.6.33，纯计算只读）。

    把「谁和谁有关系」升级为「谁喂给谁 / 谁管着谁」：每条联动轴标注
    供给 / 门控 / 印证 / 闭环，并给出孤岛（登记了却没接上的子系统）与
    悬空轴（端点写错会静默失效）两份待修清单。不调用任何诊断函数、不写状态。
    """
    from .native import linkage

    # 串联：沿联动轴走一遍，看两件东西之间怎么串起来
    if getattr(args, "path", None):
        if len(args.path) != 2:
            print("用法：linkage --path <起点KEY> <终点KEY>（KEY 用 subsystems --list 查）")
            return
        chain = linkage.path(args.path[0], args.path[1])
        name = {s.key: s.label for s in linkage.subsystems.SUBSYSTEMS}
        if not chain:
            print(f"{args.path[0]} → {args.path[1]}：走不通（两者之间没有串联关系）")
            return
        nodes = [name.get(chain[0].from_key, chain[0].from_key)]
        nodes += [name.get(ax.to_key, ax.to_key) for ax in chain]
        print(f"串联链：{' → '.join(nodes)}（{len(chain)} 跳）")
        for i, ax in enumerate(chain, 1):
            print(f"  {i}. [{ax.kind}] {name.get(ax.from_key, ax.from_key)} → "
                  f"{name.get(ax.to_key, ax.to_key)}")
            print(f"     {ax.desc}")
        return

    # 图形：ASCII 分层邻接图 / 导出 SVG
    if getattr(args, "graph", False):
        print(linkage.ascii_graph())
        return
    if getattr(args, "svg", None):
        data = linkage.svg()
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(data)
        print(f"联动图 SVG 已写到 {args.svg}（{len(data)} 字节，纯标准库生成、可离线看）")
        return
    if getattr(args, "chains", False):
        ok, msg = linkage.chains_report()
        print(msg)
        return

    ok, msg = linkage.linkage_report()
    print(msg)
    if getattr(args, "stats", False):
        st = linkage.linkage_stats()
        print("─" * 58)
        print("[结构化统计]")
        print(f"  登记 {st['subsystems']} 项 · 轴 {st['axes_total']} 条 · 生效 {st['axes_enabled']} 条")
        print(f"  孤岛 {len(st['isolated'])} 个 · 悬空轴 {len(st['dangling'])} 条")


def cmd_linux(args):
    """Linux 本机发行面（v0.6.33 登记、v0.6.35 补命令入口）。

    只读聚合：发行版（LSB /etc/os-release）／包管理器／systemd 日志体积／根分区用量。
    **只报告不清日志**——收缩 journal 只在任务层以命令文本给出，由你自己决定是否执行。
    """
    from .native import linux
    ok, msg = linux.linux_report()
    print(msg)


def cmd_compress(args):
    """压缩空间分析（v0.6.33 登记、v0.6.35 补命令入口）。

    caps（默认）：本机可读哪些压缩格式（核心格式走标准库永远可用，7z/rar/zstd 缺库明确跳过）。
    report     ：扫描目录估算「还能压出多少空间」，并标出「别白压」的已压格式。
    可选 --dir 指定扫描目录（默认 $HOME），--max-files 限制文件数。

    红线：只读——**不压缩、不解压、不删除**；归档命令只在任务里以文本给出。
    """
    from .native import compress
    action = (getattr(args, "action", "") or "caps").strip().lower()
    if action == "report":
        ok, msg = compress.compress_report(
            scan_dir=getattr(args, "dir", None),
            max_files=int(getattr(args, "max_files", 0) or 0) or compress._DEFAULT_MAX_FILES)
        print(msg)
    else:
        ok, msg = compress.compress_format_capabilities()
        print(msg)


def cmd_emergency(args):
    """预警应急定位（v0.6.35 补命令入口，GUI 面板此前已有）。

    report（默认）：只读汇总定位与预警能力面（网络 + 基站为首选基线）。
    position   ：定位可用性只读探测。
    alert      ：预警通道只读探测。

    红线：只读探测，不发任何预警、不上传任何位置。
    """
    from .native import emergency
    action = (getattr(args, "action", "") or "report").strip().lower()
    fn = {"position": emergency.position_report,
          "alert": emergency.alert_report}.get(action, emergency.emergency_report)
    ok, msg = fn()
    print(msg)


def cmd_omni(args):
    """全能全知自检（v0.6.35 边界 / v0.6.36 闭环）：我知道什么 / 我不知道什么 / 我不做什么。

    coverage（默认）：能力覆盖面 + 接线完整度（纯计算，秒回）。
    all          ：三层边界总览（含「本工具没有探针的域」声明）。
    blind N      ：列出缺 N 处入口以上的半截能力。
    gaps         ：补齐清单——把每个缺口分成「设计如此 / 真缺口」，真缺口给具体补法（v0.6.36）。
    gen-stub KEY ：为真缺口的 data 项生成知识库占位 JSON（默认 dry-run，--write 才落盘，不覆盖）。
    --deep       ：实跑各子系统报告，统计「这台机器探不到的」（秒级，默认不跑）。

    口径：全知不是宣称什么都知道，是能精确说出自己的边界；v0.6.36 进一步让边界可补齐。
    """
    from .native import omni
    action = (getattr(args, "action", "") or "coverage").strip().lower()

    if action == "blind":
        extra = getattr(args, "extra", []) or []
        try:
            n = int(extra[0]) if extra else 2
        except ValueError:
            n = 2
        bs = omni.blind_spots(n)
        print(f"半截能力（缺 {n} 处入口以上）：{len(bs)} 项")
        for b in bs:
            print(f"  · {b['label']}（{b['domain']}）缺 {'、'.join(b['missing'])}")
            for r in b["remedies"]:
                print(f"      补法：{r}")
        return

    if action == "gaps":
        ok, msg = omni.remediation_report()
        print(msg)
        return

    if action == "gen-stub":
        extra = getattr(args, "extra", []) or []
        key = (extra[0] if extra else "").strip()
        if not key:
            print("用法：python -m sysweeper omni gen-stub <KEY> [--write]")
            print("      KEY 用 `python -m sysweeper subsystems` 或 `omni gaps` 查看")
            return
        ok, msg = omni.gen_stub(key, write=getattr(args, "write", False))
        print(msg)
        return

    if action == "all":
        ok, msg = omni.omni_report(deep=getattr(args, "deep", False))
        print(msg)
        return

    ok, msg = omni.coverage_report()
    print(msg)
    if getattr(args, "deep", False):
        print("─" * 58)
        print("[本机探不到的（已知未知）]")
        for k in omni.known_unknowns()[:12]:
            tail = f"  — {k.get('brief', '')}" if k.get("brief") else ""
            print(f"  · {k['label']}（{k['domain']}）{k['reason']}{tail}")


def cmd_compat(args):
    """兼容层串联（v0.6.34，只读）：四层依赖模型 + 场景结论。

    把 proton / dosbox / wsl / virtgpu / legacy 串成一条链，回答
    「我这台机器能不能跑那个平台的软件、缺哪一层」。**不安装、不启用、不改配置**，
    缺什么只给官方路径。
    """
    from .native import compat
    ok, msg = compat.compat_report()
    print(msg)
    print("─" * 58)
    print("[能力自检]")
    _ok, cap = compat.capabilities_report()
    print(cap)


# ─────────────────────────────────────────────────────────────────────────────
# v0.6.22：嵌入整体系统(sysmap)的子系统开关（选项式开启/关闭）
# ─────────────────────────────────────────────────────────────────────────────
def _apply_toggles(subs, enable, disable):
    """批量应用开启/关闭，未知 key 给予警告但不中断。"""
    done, unknown = [], []
    for raw in (enable or []):
        for k in raw.split(","):
            k = k.strip()
            if not k:
                continue
            (done if subs.set_enabled(k, True) else unknown).append((k, "开启"))
    for raw in (disable or []):
        for k in raw.split(","):
            k = k.strip()
            if not k:
                continue
            (done if subs.set_enabled(k, False) else unknown).append((k, "关闭"))
    for k, act in done:
        print(f"  {act}: {k}")
    for k in unknown:
        print(f"  未知子系统 key（已忽略）：{k}")
    if unknown:
        print("  可用 key 见：sysweeper subsystems --list")


def _print_subsystems(subs):
    """以表格列出全部子系统及其开/关状态。"""
    items = subs.list_subsystems()
    on = sum(1 for it in items if it["enabled"])
    print(f"\n==== 嵌入整体系统(sysmap)的子系统开关（共 {len(items)} 项，已开启 {on}） ====")
    print(f"  配置落点: {subs.CONFIG_PATH}")
    print(f"  {'KEY':<16}{'LAYER':<16}{'启用':<5}标签")
    for it in items:
        mark = "✓" if it["enabled"] else "✗"
        print(f"  {it['key']:<16}{it['layer']:<16}{mark:<5}{it['label']}")
    print("\n操作：")
    print("  sysweeper subsystems --enable tor kmod        # 开启")
    print("  sysweeper subsystems --disable tor            # 关闭")
    print("  sysweeper subsystems --enable-all / --disable-all")
    print("  sysweeper --list-subsystems                    # 顶层快捷列出")


def cmd_subsystems(args):
    """管理嵌入整体系统(sysmap)的子系统开关：列出/开启/关闭（默认列出）。"""
    from .native import subsystems as subs
    if getattr(args, "enable_all", False):
        for s in subs.SUBSYSTEMS:
            subs.set_enabled(s.key, True)
        print(f"已开启全部 {len(subs.SUBSYSTEMS)} 个子系统")
        return
    if getattr(args, "disable_all", False):
        for s in subs.SUBSYSTEMS:
            subs.set_enabled(s.key, False)
        print(f"已关闭全部 {len(subs.SUBSYSTEMS)} 个子系统（sysmap 将不再嵌入任何子系统）")
        return
    enable = getattr(args, "enable", None) or []
    disable = getattr(args, "disable", None) or []
    if enable or disable:
        _apply_toggles(subs, enable, disable)
        print()
    _print_subsystems(subs)


def _print_settings(st):
    """以表格列出全部可调参数与阈值（含当前值、默认值、范围/可选）。"""
    items = st.list_settings()
    print(f"\n==== 参数与阈值（共 {len(items)} 项） ====")
    print(f"  配置落点: {st.CONFIG_PATH}")
    print(f"  {'KEY':<20}{'类型':<6}{'当前值':<12}{'默认':<12}标签 / 范围")
    for it in items:
        cur = "" if it["value"] is None else str(it["value"])
        dft = "" if it["default"] is None else str(it["default"])
        if it["kind"] == "int":
            rng = f"({it['min']}~{it['max']}{it['unit']})"
        elif it["choices"]:
            ch = list(it["choices"])
            shown = [c for c in ch if c][:4]
            rng = "(" + "/".join(shown) + ("…" if len(ch) > 4 else "") + ")"
        else:
            rng = ""
        print(f"  {it['key']:<20}{it['kind']:<6}{cur:<12}{dft:<12}{it['label']} {rng}")
    print("\n操作：")
    print("  sysweeper settings --get cmd.timeout          # 查一个")
    print("  sysweeper settings --set cmd.timeout=300      # 改一个（可多个，空格分隔）")
    print("  sysweeper settings --set scan.limit=20 arch=any")
    print("  sysweeper settings --reset                    # 全部恢复默认")
    print("  sysweeper settings --history                  # 变更留痕：谁改的、什么时候")
    print("  提示：图形界面「参数/阈值」窗口同样可调，保存即生效；已改动项会高亮。")


def cmd_settings(args):
    """查看与修改可调参数/阈值（默认列出全部）。"""
    from .native import settings as st

    if getattr(args, "history", False):
        _ok, msg = st.history_report(200)
        print("\n" + msg)
        return

    if getattr(args, "reset", False):
        st.reset(source="cli", origin="--reset")
        print(f"已恢复全部默认参数与阈值（{len(st.ALL_KEYS)} 项）\n")
        _print_settings(st)
        return

    gets = getattr(args, "get", None) or []
    if gets:
        for k in gets:
            v = st.get(k, None)
            if v is None:
                print(f"  {k}: 未知参数（可用 key 见 sysweeper settings --list）")
            else:
                print(f"  {k} = {v}")
        return

    sets = getattr(args, "set", None) or []
    if sets:
        updates = {}
        for raw in sets:
            if "=" not in raw:
                print(f"  格式不对（应为 KEY=VALUE）: {raw}")
                continue
            k, _, v = raw.partition("=")
            updates[k.strip()] = v.strip()
        results = st.apply_updates(updates, source="cli", origin="--set")
        for k, ok, why in results:
            if ok:
                print(f"  已设置: {k} = {st.get(k)}")
            else:
                print(f"  被拒绝: {k} — {why}（已回退默认值）")
        print()
    _print_settings(st)


def cmd_import(args):
    """从剪贴板 / 本地文件 / 图片二维码 / 摄像头 导入内容（默认只读取展示）。

    红线：导入的内容**绝不自动执行**；只有显式加 ``--as-settings`` 才会把
    可识别的设置 JSON 写入配置（命令行显式给出即视为确认）。
    """
    from .native import importio as io_
    from .native import settings as st

    src = (getattr(args, "source", "") or io_.SRC_CLIPBOARD).strip().lower()
    path = getattr(args, "path", "") or ""
    r = io_.import_from(src, path)
    print(f"\n==== 导入（来源: {src}） ====")
    if not r.ok:
        print(f"[失败] {r.note}")
        print("可用来源: " + "/".join(k for k, _l, _d in io_.SOURCES))
        return
    print(f"[成功] {r.note}　共 {len(r.text)} 字符")
    print("-" * 60)
    print(r.text)
    print("-" * 60)
    if not getattr(args, "as_settings", False):
        print("（仅查看，未写入任何配置；要把可识别的 JSON 载入为参数请加 --as-settings）")
        return
    ok, accepted, rejected, hint = io_.parse_settings_json(r.text)
    if not ok:
        print(f"未载入为参数: {hint}")
        return
    origin = path if src in (io_.SRC_FILE, io_.SRC_QR) else (
        f"camera#{st.get('qr.camera_index', 0)}" if src == io_.SRC_CAMERA else "剪贴板")
    results = st.apply_updates(accepted, source=src, origin=origin, note="由导入内容载入")
    n = sum(1 for _k, okk, _w in results if okk)
    print(f"已载入 {n} 项参数: " + ", ".join(f"{k}={v}" for k, v in accepted.items()))
    for line in rejected:
        print(f"  已忽略: {line}")


def cmd_webapi(args):
    """统一 JSON 接口（v0.6.25）：一行请求一行响应，给 Web 控制台/报告查看器当后端。

    - ``--once '{"action":"ping"}'`` 只处理一条，输出后退出（脚本/测试用）；
    - 不带 ``--once`` 则走 JSONL 长连接：从 stdin 一行行读请求，逐行回 JSON。
      Deno 控制台起一个本进程常驻，省掉每次调用的解释器冷启动。

    红线：只暴露**只读诊断 + 用户自己的配置文件读写**，动作白名单之外一律拒绝。
    """
    from .webapi import dispatch_text, run_loop
    import json as _json
    once = getattr(args, "once", "") or ""
    if once:
        resp = dispatch_text(once)
        if getattr(args, "pretty", False):
            try:
                resp = _json.dumps(_json.loads(resp), ensure_ascii=False, indent=2)
            except ValueError:
                pass
        print(resp)
        return
    return run_loop()


def cmd_web(args):
    """一键拉起本机 Web 控制台（v0.6.25，需要 Deno）。

    控制台本体是 ``src/deno/console.ts``（Deno HTTP 外壳），
    数据后端是本模块 ``webapi``。本命令只负责找到 deno 并把它拉起来。

    未装 Deno 时**不自动安装**，只给官方安装指引——装不装、怎么装由用户决定。
    """
    import shutil
    import subprocess
    from pathlib import Path

    port = getattr(args, "port", 8787)
    host = getattr(args, "host", "127.0.0.1")
    script = Path(__file__).resolve().parents[2] / "deno" / "console.ts"

    deno = shutil.which("deno")
    if not deno:
        cand = Path.home() / ".deno" / "bin" / "deno"
        if cand.is_file():
            deno = str(cand)
    if not deno:
        print("未找到 deno（Web 控制台的外壳需要它）。")
        print("安装（官方脚本，装到 ~/.deno）：")
        print("  curl -fsSL https://deno.land/install.sh | sh")
        print("装完后重开终端，或把 ~/.deno/bin 加进 PATH 再跑：")
        print("  sysweeper web")
        print("\n不想装 Deno？同等能力走命令行/GUI：")
        print("  sysweeper settings / subsystems / import / webapi   # 同一套后端动作")
        return
    if not script.is_file():
        print(f"找不到控制台脚本: {script}")
        print("sysweeper web 需在仓库内运行（pip 安装包不含 Deno 外壳）。")
        return

    flags = ["--allow-net", "--allow-read", "--allow-run"]
    argv = [deno, "run", *flags, str(script),
            "--port", str(port), "--host", host]
    if getattr(args, "no_open", False):
        argv.append("--no-open")
    print(f"正在拉起 Web 控制台（deno，监听 {host}:{port}，Ctrl+C 退出）…")
    try:
        raise SystemExit(subprocess.call(argv))
    except FileNotFoundError:
        print(f"无法执行 {deno}，请确认其可运行。")
        raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sysweeper",
        description="万能系统优化与清理（Windows / macOS / Linux / BSD / Unix / Android / iOS）",
    )
    p.add_argument("--platform",
                   help="指定平台: windows|macos|linux|bsd|unix|android|ios|harmony")
    p.add_argument("--version", help="指定系统版本号，如 10 / 11 / 26 / 17 / 24.04 / 14")
    p.add_argument("--category", choices=list(CATEGORIES.keys()),
                   help="仅处理某分类: " + "/".join(CATEGORIES.keys()))
    p.add_argument("--risk", default="high", choices=list(RISK_ORDER.keys()),
                   help="风险上限（默认 high；clean 时可降到 low/medium）")
    # v0.6.22：嵌入整体系统(sysmap)的子系统开关（全局快捷操作）
    p.add_argument("--list-subsystems", action="store_true",
                   help="列出所有可嵌入整体系统的子系统及其开/关状态")
    p.add_argument("--enable", nargs="*", metavar="KEY",
                   help="（全局）开启子系统开关 key（可多个/逗号分隔），立刻写入配置")
    p.add_argument("--disable", nargs="*", metavar="KEY",
                   help="（全局）关闭子系统开关 key（可多个/逗号分隔），立刻写入配置")

    # 公共参数同时注入每个子命令，使「子命令 --platform」也合法
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--platform",
                        help="指定平台: windows|macos|linux|bsd|unix|android|ios|harmony")
    common.add_argument("--version", help="指定系统版本号，如 10 / 11 / 26 / 17 / 24.04 / 14")
    common.add_argument("--category", choices=list(CATEGORIES.keys()),
                         help="仅处理某分类: " + "/".join(CATEGORIES.keys()))
    common.add_argument("--risk", default="high", choices=list(RISK_ORDER.keys()),
                         help="风险上限（默认 high；clean 时可降到 low/medium）")
    common.add_argument("--opt-in", action="store_true",
                         help="纳入默认关闭的网络/ITU 开关（需配合 --yes 确认）")
    common.add_argument("--only", default="",
                         help="仅选择指定任务 id（逗号分隔），用于精确启用某项")
    # v0.6.23：以下四项的默认值取自可调参数（sysweeper settings / GUI 参数窗口），
    # 命令行显式给出仍然优先——配置只是「没指定时用什么」的兜底。
    common.add_argument("--report", default=_settings.get("report.path", ""),
                         help="生成前后对比报告文件（路径；.json 写 JSON，否则写 Markdown）"
                              "（默认值取自参数 report.path）")
    common.add_argument("--arch", default=_settings.get("arch", "auto"),
                         choices=["auto", "any", "loongarch", "mips", "riscv",
                                  "openpower", "openrisc", "x86", "arm", "open_hardware"],
                         help="架构/指令集维度过滤（默认 auto=按当前运行架构；"
                              "any=不按架构过滤；其余=指定某架构仅显示其专属任务）"
                              "（默认值取自参数 arch）")
    common.add_argument("--profile", default=_settings.get("profile", ""),
                         help="按任务档位筛选（v0.5.22）：minimal=零风险只读体检（小而全）；"
                              "lite=保守可逆；standard=默认；full=全量含 opt-in（大而全）。"
                              "与 --risk/--opt-in 叠加时以档位为基线再按参数收窄"
                              "（默认值取自参数 profile）")
    common.add_argument("--locale", default=(_settings.get("locale", "") or None),
                         help="界面语言（i18n）：zh_CN=简体中文（默认）/ en=English；"
                              "也可用环境变量 SYSWEEPER_LOCALE 指定"
                              "（默认值取自参数 locale）")

    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("detect", parents=[common], help="自动探测当前平台与版本").set_defaults(func=cmd_detect)
    sub.add_parser("info", parents=[common], help="用原生接口报告系统信息（磁盘/版本/发行版）").set_defaults(func=cmd_info)
    sub.add_parser("versions", parents=[common], help="列出某平台可选版本与注意事项").set_defaults(func=cmd_versions)
    sub.add_parser("list", parents=[common], help="列出适用任务").set_defaults(func=cmd_list)
    sub.add_parser("notes", parents=[common], help="仅显示注意事项与风险提示").set_defaults(func=cmd_notes)
    sub.add_parser("langs", parents=[common], help="语言运行时探测与「按语言自动启用」的功能开关").set_defaults(func=cmd_langs)
    sub.add_parser("hardware", parents=[common], help="硬件标准参考（S.M.A.R.T./ACPI/PCI/USB 原生读取）").set_defaults(func=cmd_hardware)
    sub.add_parser("kernel", parents=[common], help="Linux kernel 源码文档参考（硬件/软件/网络子系统）").set_defaults(func=cmd_kernel)
    sp_desktop = sub.add_parser("desktop", parents=[common],
                                help="桌面环境文档跟踪（GNOME/KDE/XFCE + freedesktop 规范；--report 导出只读缓存对比报告）")
    sp_desktop.set_defaults(func=cmd_desktop)
    sub.add_parser("syssoftware", parents=[common],
                   help="其他系统软件文档跟踪（systemd/D-Bus/NetworkManager/PipeWire/"
                        "BlueZ/udev/polkit/Wayland，按各自协议与接口）"
                   ).set_defaults(func=cmd_syssoftware)
    sub.add_parser("pkgmgr", parents=[common],
                   help="包管理器文档跟踪（APT/RPM/apk/pacman/Homebrew/winget/pip/npm/"
                        "Snap-Flatpak，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_pkgmgr)
    sub.add_parser("container", parents=[common],
                   help="容器运行时文档跟踪（Docker/Podman/containerd/BuildKit/OCI/LXC-LXD/"
                        "CRI，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_container)
    sub.add_parser("storage", parents=[common],
                   help="存储与文件系统文档跟踪（ext4/Btrfs/XFS/ZFS/LVM/fstrim/SMART/swap，"
                        "各自按自身协议与接口）"
                   ).set_defaults(func=cmd_storage)
    sub.add_parser("network", parents=[common],
                   help="网络栈深度调优文档跟踪（iproute2/ethtool/eBPF/tc/conntrack/"
                        "NM-resolved/RPS-XPS，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_network)
    sub.add_parser("windows", parents=[common],
                   help="Windows 原生接口文档跟踪（Win32/注册表/WMI-CIM/powercfg/DISM/"
                        "SFC/存储感知/传递优化/Windows Update，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_windows)
    sub.add_parser("macos", parents=[common],
                   help="macOS 原生接口文档跟踪（launchd/sysctl/defaults/softwareupdate/"
                        "diskutil/pmset/tmutil/spctl/networksetup，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_macos)
    sub.add_parser("unix", parents=[common],
                   help="Unix（System V）原生接口文档跟踪（IPS pkg/SMF/ZFS//etc/release/"
                        "logadm/kstat/Zones/FMA/dladm-ipadm，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_unix)
    sub.add_parser("android", parents=[common],
                   help="Android 原生接口文档跟踪（adb/settings_provider/pm/am/dumpsys/"
                        "getprop/svc/wm/logcat，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_android)
    sub.add_parser("ios", parents=[common],
                   help="iOS 原生接口文档跟踪（libimobiledevice：ideviceinfo/ideviceinstaller/"
                        "idevicesyslog/idevicecrashreport/idevicediagnostics/idevicebackup2/"
                        "idevicepair/idevicename/idevicedate/idevicesetlocation/ideviceimagemounter）"
                   ).set_defaults(func=cmd_ios)
    sub.add_parser("bsd", parents=[common],
                   help="BSD 原生接口文档跟踪（pkg/rc.conf/sysctl/pf/zfs/periodic/"
                        "bsdconfig/ports，各自按自身协议与接口）"
                   ).set_defaults(func=cmd_bsd)
    sp_durability = sub.add_parser("durability", parents=[common],
                                   help="设备长期使用保护（只读采集电池/温度/SMART/uptime/环境 + "
                                        "知识库驱动保养，不写设备，v0.6.30）")
    sp_durability.add_argument("--usage", default="moderate",
                               choices=["light", "moderate", "heavy"],
                               help="设备使用量：light=轻度/moderate=常规/heavy=重度")
    sp_durability.add_argument("--years", default=4, type=int,
                               help="期望使用年限（年），影响充电上限与温度预算")
    sp_durability.add_argument("--env", default="",
                               help="环境标签，逗号分隔（如 high_humidity,mobile,plugged_in,outdoor）")
    sp_durability.set_defaults(func=cmd_durability)
    sp_electrical = sub.add_parser("electrical", parents=[common],
                                    help="供电与环境安全（只读感知供电环境标签+本机温度，识别电气火灾"
                                         "事故前兆链条并自适应；绝不碰配电箱，v0.6.38）")
    sp_electrical.add_argument("--env", default="",
                               help="供电环境标签，逗号分隔（如 old_wiring,copper_aluminum,"
                                    "no_ground,wood_base,loose_outlet,overload_risk,high_dust）")
    sp_electrical.set_defaults(func=cmd_electrical)
    sp_acoustics = sub.add_parser("acoustics", parents=[common],
                                   help="声学与音律（频率/波长/声速/共振/分贝 + 黄钟大吕三分损益"
                                        "十二律 + ISM 频段 + 喇叭耳机电声标准；只读枚举与工程换算，"
                                        "绝不发声/调音量/采集声音/发射射频，v0.6.87）")
    sp_acoustics.set_defaults(func=cmd_acoustics)
    sp_sysbase = sub.add_parser("sysbase", parents=[common],
                                   help="系统基座（FHS/LFS 系统界定+deb/rpm 包管理+apt/yum 仓库"
                                         "订阅+Metasploit 安装痕迹两路检测+路径命名空间概念课；"
                                         "只读，绝不改动系统，v0.6.88）")
    sp_sysbase.set_defaults(func=cmd_sysbase)
    sp_sysdev = sub.add_parser("sysdev", parents=[common],
                                   help="从零造系统学习应用（pepsipu 项目群：warpalloc 分配器/"
                                        "aski 编译器/xinOS·OSpaint 玩具 OS/ramenbox 6502 模拟器/"
                                        "cx 多账户/torus 工作区；模式+边界学习 + 工具链与 malloc "
                                        "只读体检；绝不代跑第三方源码，v0.6.89）")
    sp_sysdev.set_defaults(func=cmd_sysdev)
    sp_docs = sub.add_parser("docs", parents=[common],
                                   help="文档与概念联动（docs/ 文档层作为联动网格一等节点："
                                         "统合整合概念系统的联动连轴连动；只读枚举与交叉引用，"
                                         "绝不写文件/执行命令/改系统，v0.6.88）")
    sp_docs.set_defaults(func=cmd_docs)
    sp_androidstd = sub.add_parser("androidstd", parents=[common],
                                    help="国内标准：Android/App 隐私合规（PIPL/GB-T/四部门规定/"
                                         "TC260，官方源实检，只读知识库，v0.6.67）")
    sp_androidstd.set_defaults(func=cmd_androidstd)
    sp_cnstd = sub.add_parser("cnstd", parents=[common],
                              help="国内标准资源：官方平台/协议规范/第三方/概念四层"
                                   "（openstd/std.samr/hbba/CCSA + Modbus/MQTT，"
                                   "14 源全量导入，只读知识库，v0.6.90）")
    sp_cnstd.set_defaults(func=cmd_cnstd)
    sp_gmsstd = sub.add_parser("gmsstd", parents=[common],
                               help="GMS 标准：GMS 兼容与 Play 上架（CDD/CTS/VTS/STS→"
                                    "GMS 许可→Play 三件套→Data safety，官方源实检，只读知识库，v0.6.67）")
    sp_gmsstd.set_defaults(func=cmd_gmsstd)
    sp_hmoseco = sub.add_parser("hmoseco", parents=[common],
                                help="鸿蒙生态：HAP 工程/侧载工具链/NEXT 生态版图/版本线/"
                                     "开发工具链/IoT（社区源 needs_verify + 官方文档，只读知识库，v0.6.71）")
    sp_hmoseco.set_defaults(func=cmd_hmos_ecosystem)
    sp_hmosstd = sub.add_parser("hmosstd", parents=[common],
                                help="HarmonyOS 标准：PIPL→AppGallery 上架→App 备案→权限 APL/"
                                     "HUKS/TEE/国密→版本兼容→未成年人→XTS（法规原文+官方源，只读知识库，v0.6.72）")
    sp_hmosstd.set_defaults(func=cmd_hmosstd)
    sp_reverse = sub.add_parser("reverse", parents=[common],
                                help="黑箱逆向：UPX 壳识别(三特征)/PE·ELF 节区解剖/香农熵/"
                                     "MinGW 造样本/GDB 四连（沙箱实测，只读不绕过，v0.6.73）")
    sp_reverse.set_defaults(func=cmd_reverse)
    sp_fdroidstd = sub.add_parser("fdroidstd", parents=[common],
                                  help="F-Droid 标准：免 GMS 自由软件分发（收录政策/反特征/"
                                       "可复现构建/仓库协议，能下载即可安装，v0.6.67）")
    sp_fdroidstd.set_defaults(func=cmd_fdroidstd)
    sp_peripheral = sub.add_parser("peripheral", parents=[common],
                                    help="外部设备连接与兼容（整体引入星闪标准+触控技术+USB-C/PD/HID"
                                         "只读识别与兼容指引，绝不刷固件/装驱动，v0.6.39）")
    sp_peripheral.add_argument("--env", default="",
                               help="设备标签，逗号分隔（如 nearlink_desired,touchscreen,"
                                    "touchpad,stylus,usb_c_pd,legacy_usb,hid_device,external_env_sensor）")
    sp_peripheral.set_defaults(func=cmd_peripheral)
    sp_chrono = sub.add_parser("chrono", parents=[common],
                               help="时空与全维度管理器（量子/计算机原理 + 时间/空间/施时空组合/未来"
                                    "兼容只读透镜 + 全时空全维度循环往复管理器，v0.6.40）")
    sp_chrono.add_argument("--env", default="",
                           help="维度标签，逗号分隔（如 time,space,spacetime,future_compat,"
                                "quantum_lens；留空即用全维度注册表）")
    sp_chrono.set_defaults(func=cmd_chrono)
    sp_virt = sub.add_parser("virt", parents=[common],
                             help="虚拟机环境识别与优雅降级（裸金属/KVM/VMware/VirtualBox/Hyper-V/Xen/"
                                  "WSL/容器只读探测 + 不同 VM 内只降级不崩溃，v0.6.41）")
    sp_virt.add_argument("--env", default="",
                          help="环境标签，逗号分隔（如 kvm,vmware,hyperv,virtualbox,xen,wsl,container,baremetal；"
                               "留空即自动识别）")
    sp_virt.set_defaults(func=cmd_virt)
    sp_packages = sub.add_parser("packages", parents=[common],
                                 help="软件包规范审计（按系统/硬件/相关软件包检测包管理器 + 安装/卸载/配置/"
                                      "设置优化四类操作层级应对，只读指引，v0.6.41）")
    sp_packages.add_argument("--env", default="",
                              help="环境标签，逗号分隔（如 apt,dnf,pacman,brew,winget,choco,apk,scoop,zypper；"
                                   "留空即自动检测）")
    sp_packages.set_defaults(func=cmd_packages)
    sp_apctrl = sub.add_parser("apctrl", parents=[common],
                               help="AP 集中控制器只读审计（hostapd/NetworkManager/dnsmasq/apcontroller 思路，只读不写，v0.6.42）")
    sp_apctrl.add_argument("--env", default="",
                           help="环境标签，逗号分隔（如 hostapd,nm_ap,dnsmasq,apcontroller；留空即自动探测）")
    sp_apctrl.set_defaults(func=cmd_apctrl)
    sp_llvm = sub.add_parser("llvm", parents=[common],
                             help="LLVM 工具链与交叉编译（clang/lld/mlir 探测 + 交叉编译目标矩阵，只读不写，v0.6.42）")
    sp_llvm.add_argument("--env", default="",
                         help="环境标签，逗号分隔（如 clang,lld,mlir,targets；留空即自动探测）")
    sp_llvm.set_defaults(func=cmd_llvm)
    sp_toolchain = sub.add_parser("toolchain", parents=[common],
                                  help="工具链全景（宿主工具链×仓库工具软件×目标架构矩阵，只读不写，v0004）")
    sp_toolchain.add_argument("--env", default="",
                              help="维度标签，逗号分隔（如 cross-compile,native-build,mingw,ndk,ohos；留空即全量）")
    sp_toolchain.set_defaults(func=cmd_toolchain)
    sp_meshnet = sub.add_parser("meshnet", parents=[common],
                                help="组网优化与设备协同（WireGuard P2P + 设备能力适配 + 负载均衡/协同共享，只读不写，v0.6.42）")
    sp_meshnet.add_argument("--env", default="",
                            help="环境标签，逗号分隔（如 wg,capability,balance；留空即自动探测）")
    sp_meshnet.set_defaults(func=cmd_meshnet)
    sp_nettransfer = sub.add_parser("nettransfer", parents=[common],
                                    help="FTP+目录服务传输/负载验证（上传/下载/续传/校验/限速/"
                                         "目录列举，凭据经 --passenv 从环境变量读，绝不落盘，v0.6.91）")
    sp_nettransfer.add_argument("--op", default="list",
                                 choices=["list", "pwd", "mkdir", "upload", "download", "loadtest"],
                                 help="操作：list 目录列举 / pwd 工作目录 / mkdir 建目录 / "
                                      "upload 上传 / download 下载 / loadtest 受控速率负载验证")
    sp_nettransfer.add_argument("--host", default="", help="FTP 目标主机（必填）")
    sp_nettransfer.add_argument("--port", type=int, default=21, help="FTP 端口（默认 21）")
    sp_nettransfer.add_argument("--user", default="anonymous", help="登录用户名（默认 anonymous）")
    sp_nettransfer.add_argument("--passenv", default="",
                                 help="密码环境变量名；从该变量读密码，绝不进参数/落盘/硬编码")
    sp_nettransfer.add_argument("--tls", action="store_true", help="启用 FTPS（FTP over TLS）")
    sp_nettransfer.add_argument("--remote", default=".", help="远程路径（list/mkdir/upload 目标 / download 源）")
    sp_nettransfer.add_argument("--local", default="", help="本地路径（upload 源 / download 目标）")
    sp_nettransfer.add_argument("--resume", action="store_true", help="断点续传（REST 跳过已传部分）")
    sp_nettransfer.add_argument("--no-verify", action="store_true", help="关闭 sha256/大小校验")
    sp_nettransfer.add_argument("--rate-limit", type=float, default=0.0, help="限速（MiB/s，0=不限）")
    sp_nettransfer.add_argument("--expected-hash", default="", help="download 期望 sha256（校验用）")
    sp_nettransfer.add_argument("--algo", default="sha256", help="校验算法（默认 sha256）")
    sp_nettransfer.add_argument("--size", type=int, default=1 << 24, help="loadtest 灌入字节数")
    sp_nettransfer.add_argument("--duration", type=float, default=5.0, help="loadtest 时长（秒）")
    sp_nettransfer.set_defaults(func=cmd_nettransfer)
    sp_matrix = sub.add_parser("matrix", parents=[common],
                               help="周天星斗大阵 · 数字矩阵冗余数据只读观测（缓存/临时/回收站/日志，只读不删，v0.6.84）")
    sp_matrix.add_argument("--env", default="",
                           help="维度标签，逗号分隔（如 user-cache,tmp,pkg-cache,trash,log-rotate；留空即全量）")
    sp_matrix.set_defaults(func=cmd_matrix)
    sp_f2b = sub.add_parser("f2b", parents=[common],
                            help="十二都天神煞大阵 · fail2ban 学习应用只读咨询（探测/解析/模式学习，只读不写，v0.6.84）")
    sp_f2b.add_argument("--env", default="",
                        help="咨询模板标签，逗号分隔（如 sshd-basic,whitelist,graduated；留空即全部）")
    sp_f2b.set_defaults(func=cmd_f2b)
    sp_vdns = sub.add_parser("vdns", parents=[common],
                             help="虚拟根 DNS 与多 CDN（根 DNS/DoH-DoT/多 CDN 选择·健康，只读不写，v0.6.42）")
    sp_vdns.add_argument("--env", default="",
                         help="环境标签，逗号分隔（如 rootdns,cdn,health；留空即自动探测）")
    sp_vdns.set_defaults(func=cmd_vdns)
    sp_ipp = sub.add_parser("ipp", parents=[common],
                            help="IPP 打印协议发现（CUPS/mDNS/本地管理页，只读发现，v0.6.42）")
    sp_ipp.add_argument("--env", default="",
                        help="环境标签，逗号分隔（如 cups,mdns,localweb；留空即自动探测）")
    sp_ipp.set_defaults(func=cmd_ipp)
    sp_display = sub.add_parser("display", parents=[common],
                                help="现代设备显示与 GPU（显示服务器/GPU/分辨率 + 终端保留，只读不写，v0.6.42）")
    sp_display.add_argument("--env", default="",
                            help="环境标签，逗号分隔（如 server,gpu,resolution,terminal；留空即自动探测）")
    sp_display.set_defaults(func=cmd_display)
    sp_retro = sub.add_parser("retro", parents=[common],
                              help="常态化回头看、久久为功（维护节奏表 + 长期保障要点 + 易漂移维度复盘，只读不写，v0.6.42）")
    sp_retro.add_argument("--env", default="",
                          help="环境标签，逗号分隔（如 cadence,longevity,drift；留空即默认基线）")
    sp_retro.set_defaults(func=cmd_retro)
    sp_restart = sub.add_parser("restart", parents=[common],
                                 help="人类文明重启计划场景透镜（维度清单 + 保命优先级 + 知识库沉淀，只读不写，v0.6.42）")
    sp_restart.add_argument("--env", default="",
                            help="环境标签，逗号分隔（如 dimensions,priority,knowledge；留空即默认基线）")
    sp_restart.set_defaults(func=cmd_restart)
    sp_asm = sub.add_parser("asm", parents=[common],
                            help="汇编语言优化（nasm/yasm/gas/llvm-mc/gcc -S 探测 + SIMD 优化要点 + "
                                 "LLVM 交叉编译汇编指引，只读不写，v0.6.43）")
    sp_asm.add_argument("--env", default="",
                        help="环境标签，逗号分隔（如 nasm,yasm,gas,llvm_mc,gcc_s；留空即自动探测）")
    sp_asm.set_defaults(func=cmd_asm)
    sub.add_parser("remote", parents=[common],
                   help="远程接入与传输客户端只读审计（telnet/ssh/filezilla/putty，"
                        "各自按自身协议；加固只给指引不写配置，v0.6.30）"
                   ).set_defaults(func=cmd_remote)
    sub.add_parser("cert", parents=[common],
                   help="证书与加密开源整合（OpenSSL/LibreSSL/GnuTLS + 硬件信任根 TPM/IDevID "
                        "+ 各种证书 X.509/ACME/FIDO；只读审计，绝不读私钥，v0.6.31）"
                   ).set_defaults(func=cmd_cert)
    sub.add_parser("miniapp", parents=[common],
                   help="uni-app 各小程序端文档跟踪（微信/支付宝/百度/抖音/QQ/快手，"
                        "按各端自身 API 规范）").set_defaults(func=cmd_miniapp)
    sub.add_parser("harmony", parents=[common],
                   help="鸿蒙 HarmonyOS/OpenHarmony + uni-app 鸿蒙端文档跟踪"
                        "（hdc/HiLog/Stage模型/SysCap/HAP/分布式）"
                   ).set_defaults(func=cmd_harmony)
    sub.add_parser("kaihong", parents=[common],
                   help="KaihongOS 发行版识别（深开鸿/基于 OpenHarmony：版本/variant/"
                        "SELinux/hdc，只读）"
                   ).set_defaults(func=cmd_kaihong)
    sub.add_parser("media", parents=[common],
                   help="图像/媒体编解码与色彩能力只读诊断（编解码工具链/格式矩阵/ICC/"
                        "Rust 创意套件；吸收 photocraft 图像管线视角）"
                   ).set_defaults(func=cmd_media)
    sp_livemedia = sub.add_parser("livemedia", parents=[common],
                   help="可启动介质制作能力只读诊断（ISO构建/引导加载/El Torito·混合/"
                        "压缩根 squashfs·overlayfs·casper/U盘写入/固件模式；吸收 livecd/dvd/bd/usb）"
                   )
    sp_livemedia.add_argument("--iso", default=None,
                   help="可选：传入一个 ISO 路径，额外做只读可启动性校验（file/isoinfo/xorriso）")
    sp_livemedia.set_defaults(func=cmd_livemedia)
    sp_legacy = sub.add_parser("legacy", parents=[common],
                   help="遗留/嵌入式/兼容层只读诊断（DOS 3.1 等·FreeDOS·DOSEMU2 / "
                        "busybox 嵌入式用户态 / dosbox 模拟兼容层；嵌入整体系统关联）"
                   ).set_defaults(func=cmd_legacy)
    sp_fonts = sub.add_parser("fonts", parents=[common],
                               help="字体/字符标准参考（Unicode 18.0.0 + OpenType/WOFF 原生读取）")
    sp_fonts.add_argument("--encoding", default="utf-8", choices=["utf-8", "utf-128"],
                          help="编码模式（默认 utf-8；utf-128 为前瞻宽编码，声明时落盘规范化为 UTF-8 向下兼容）")
    sp_fonts.set_defaults(func=cmd_fonts)
    sub.add_parser("toggles", parents=[common], help="网络协议/ITU 标准开关（默认关闭，需选择+确认）").set_defaults(func=cmd_toggles)
    sp_snap = sub.add_parser("snapshot", parents=[common],
                             help="基线快照与差异对比（capture/diff/show，纯只读，把前后对比做成可追溯）")
    sp_snap.add_argument("snapshot_action", choices=["capture", "diff", "show"],
                         help="capture=生成快照；diff=对比两份；show=查看快照内容")
    sp_snap.add_argument("--out", default="", help="capture 输出路径（默认 sysweeper-snapshot-<日期>.json）")
    sp_snap.add_argument("--a", default="", help="diff 的基线快照路径（A）")
    sp_snap.add_argument("--b", default="", help="diff 的对比快照路径（B）")
    sp_snap.add_argument("--file", default="", help="show 的快照路径")
    sp_snap.add_argument("file", nargs="?", default="",
                         help="show 的快照路径（位置参数，等同 --file）")
    sp_snap.add_argument("--no-probes", action="store_true",
                         help="capture 时不包含各子系统只读探测（仅保留 meta + 磁盘/内存指标）")
    sp_snap.set_defaults(func=cmd_snapshot)
    sp_a11y = sub.add_parser("a11y", parents=[common],
                             help="无障碍环境报告（多系统适配：Windows 讲述人/macOS VoiceOver/"
                                  "Linux ORCA/Android TalkBack/iOS VoiceOver/鸿蒙屏幕朗读）")
    sp_a11y.add_argument("--speak", action="store_true",
                         help="用可用语音后端朗读报告摘要（无后端时降级为纯文本）")
    sp_a11y.set_defaults(func=cmd_a11y)
    sp_netlink = sub.add_parser("netlink", parents=[common],
                                help="多种网络链接协议 + 多设备自组网/人机交互 + 按网络隐私验证 + 同人资源共享")
    sp_netlink.add_argument("netlink_action", nargs="?", default="list",
                            choices=["list", "serve", "discover", "msg", "auth", "reshare"],
                            help="list=链接协议与能力；serve=启用自组网；discover=发现设备；"
                                 "msg=人机交互消息；auth=按网络隐私验证；reshare=同人资源共享")
    sp_netlink.add_argument("--text", default="", help="msg 的消息文本")
    sp_netlink.set_defaults(func=cmd_netlink)
    sp_thirdparty = sub.add_parser("thirdparty", parents=[common],
                                    help="导入的第三方网络互联互通/硬件优化/开源下载 引用（只读登记，不打包二进制）")
    sp_thirdparty.add_argument("thirdparty_action", nargs="?", default="list",
                               choices=["list", "interop", "hw", "download",
                                        "cdn-p2p", "licenses"],
                               help="list=全部引用；interop=网络互联互通；hw=硬件优化；"
                                    "download=开源下载；cdn-p2p=CDN/P2P 开关；licenses=许可证来源")
    sp_thirdparty.set_defaults(func=cmd_thirdparty)
    sp_openwrt = sub.add_parser("openwrt", parents=[common],
                                help="OpenWrt 路由器系统只读接口（UCI/包管理/网络/防火墙/无线/"
                                     "DHCP/存储/构建 + 写操作指引，v0.5.20/21）")
    sp_openwrt.add_argument("openwrt_action", nargs="?", default="list",
                            choices=["list", "detect", "uci", "pkgs", "network",
                                     "firewall", "wireless", "dhcp", "storage",
                                     "build", "write"],
                            help="list=能力总览；detect=板型/固件；uci=UCI 只读审计；"
                                 "pkgs=已装包盘点；network=网络接口；firewall=防火墙；"
                                 "wireless=无线；dhcp=DHCP/DNS；storage=存储；"
                                 "build=构建系统参考；write=写操作安全指引(只预检+命令文本,绝不执行)")
    sp_openwrt.set_defaults(func=cmd_openwrt)
    sp_plugins = sub.add_parser("plugins", parents=[common],
                                help="插件支持：列出/查看/只读运行已注册的安全插件（v0.5.20）")
    sp_plugins.add_argument("plugins_action", nargs="?", default="list",
                            choices=["list", "show", "run", "allowlist"],
                            help="list=插件清单；show=查看某插件（--id）；run=只读运行某插件（--id）；"
                                 "allowlist=查看只读白名单（静态+运行时登记）")
    sp_plugins.add_argument("--id", dest="plugin_id", default=None,
                            help="show/run 指定的插件 id（用 `plugins` 查看清单）")
    sp_plugins.set_defaults(func=cmd_plugins)
    sp_standards = sub.add_parser("standards", parents=[common],
                   help="分类规范整体：分类→标准出处(按受众分层)→覆盖矩阵")
    sp_standards.add_argument("--audience", choices=["cn", "intl", "regional",
                                                      "us", "jp", "eu", "de"],
                              default="cn", help="标准引用受众：cn=国内优先国标；"
                              "intl=面向外国用户用国际标准；regional=按地区执行；"
                              "us/jp/eu/de=按具体国家/地区优先")
    sp_standards.set_defaults(func=cmd_standards)
    sp_rfc = sub.add_parser("rfc", parents=[common],
                            help="RFC 全量标准目录（IETF 官方 RFC INDEX 本地解析："
                                 "list/search/show/citing/relations/current/series/"
                                 "topics/topic/refs，只读不联网，v0.6.50）")
    sp_rfc.add_argument("rfc_action", nargs="?", default="overview",
                        choices=["overview", "list", "search", "show", "citing",
                                 "relations", "current", "series", "topics",
                                 "topic", "refs", "wgs", "wg"],
                        help="overview=目录速览(默认)；list=最新/按状态列出；search=按标题作者检索；"
                             "show=单条详情(含引用任务)；citing=哪些任务引用了某 RFC；"
                             "relations=关系视图(obsoletes/updates/...)；current=沿废止链找现行版本；"
                             "series[名]=STD/BCP/FYI 系列；topics=主题域速览；topic=某主题域成员；"
                             "refs=任务侧引用全量核验(悬空/过期引用)")
    sp_rfc.add_argument("term", nargs="?", default="",
                        help="search 的检索词（如 TLS）；topic 的主题域名；series 的系列名；"
                             "wg 的工作组/研究组/area 名")
    sp_rfc.add_argument("number", nargs="?", default=None,
                        help="show/citing/relations/current 的 RFC 编号"
                             "（9846 / rfc09846 均可）")
    sp_rfc.add_argument("--status", default="",
                        help="list 按状态过滤（如 'INTERNET STANDARD'、HISTORIC）")
    sp_rfc.add_argument("--limit", type=int, default=30,
                        help="list/search/topic 的最大条数（默认 30）")
    sp_rfc.set_defaults(func=cmd_rfc)

    sp_xiuzhen = sub.add_parser("xiuzhen", parents=[common],
                                help="修真图谱（典籍/道藏部类/研修主题/旁参/语料 五层关系，"
                                     "数据带 source 只读不联网，v0.6.46）")
    sp_xiuzhen.add_argument("xiuzhen_action", nargs="?", default="overview",
                            choices=["overview", "list", "search", "show", "edges", "layers"],
                            help="overview=图谱速览(默认)；list=列出节点(可按层过滤)；"
                                 "search=按标题/标签检索；show=单节点详情；edges=某节点的全部关联关系；"
                                 "layers=分层清单")
    sp_xiuzhen.add_argument("term", nargs="?", default="",
                            help="search 的检索词（如 黄庭、脏腑辨证）")
    sp_xiuzhen.add_argument("node", nargs="?", default=None,
                            help="show/edges 的节点（id 或标题，如 book:daodejing / 道德经）")
    sp_xiuzhen.add_argument("--layer", default="",
                            help="list 按层过滤（daozang/classics/topics/external/corpus）")
    sp_xiuzhen.add_argument("--limit", type=int, default=30,
                            help="list/search 的最大条数（默认 30）")
    sp_xiuzhen.set_defaults(func=cmd_xiuzhen)

    sp_caudit = sub.add_parser("caudit", parents=[common],
                               help="WebTrust for CAs 审计图谱（GoDaddy/Starfield 2026："
                                    "35 CA/4 事项/12 地点，标准条款可反查 RFC，只读不联网，v0.6.47）")
    sp_caudit.add_argument("caudit_action", nargs="?", default="overview",
                           choices=["overview", "list", "search", "show", "children",
                                    "matters", "locations", "std", "cpcps", "domains"],
                           help="overview=审计图谱速览(默认)；list=按种类列 CA；search=按名称/指纹检索；"
                                "show=单 CA 详情；children=某根下的交叉/签发 CA；matters=Bugzilla 事项；"
                                "locations=地点清单；std=标准引用(可反查 RFC)；cpcps=CP/CPS 谱系；domains=控制域清单")
    sp_caudit.add_argument("term", nargs="?", default="",
                           help="search 的检索词（如 Starfield/TLS/DV）；std rfc <编号> 的编号")
    sp_caudit.add_argument("node", nargs="?", default=None,
                           help="show/children 的 CA（名称/指纹/id，如 'Starfield TLS Root CA – R1'）")
    sp_caudit.add_argument("--kind", default="",
                           help="list 按种类过滤（root/cross/issuing）")
    sp_caudit.add_argument("--bug", default="",
                           help="matters 按 Bugzilla 编号过滤（如 2007216）")
    sp_caudit.add_argument("--limit", type=int, default=30,
                           help="list/search 的最大条数（默认 30）")
    sp_caudit.set_defaults(func=cmd_caudit)

    sp_mongo = sub.add_parser("mongo", parents=[common],
                              help="MongoDB 权威指南（第2版）知识索引（6 部分/23 章/43 概念/"
                                   "16 条系统调优，与 sysweeper 任务交叉对账，只读不联网，v0.6.48）")
    sp_mongo.add_argument("mongo_action", nargs="?", default="overview",
                          choices=["overview", "chapters", "show", "concepts",
                                   "search", "deploy", "cross", "book"],
                          help="overview=书目与规模速览(默认)；chapters=章节清单(可按部分过滤)；"
                               "show <章号>=章的节清单与相关概念；concepts=概念条目(可按类别过滤)；"
                               "search=按名称/描述检索；deploy=第23章系统层调优项；"
                               "cross=只列与 sysweeper 对得上的调优项；book=书目与版权边界")
    sp_mongo.add_argument("term", nargs="?", default="",
                          help="search 的检索词；show 的章号兜底")
    sp_mongo.add_argument("node", nargs="?", default=None,
                          help="show 的章号（如 23）")
    sp_mongo.add_argument("--part", default="",
                          help="chapters 按部分过滤（p1 MongoDB介绍 / p2 设计应用 / p3 复制 / "
                               "p4 分片 / p5 应用管理 / p6 服务器管理）")
    sp_mongo.add_argument("--cat", default="",
                          help="concepts 按类别过滤（model/crud/query/index/aggregate/"
                               "design/replica/sharding/admin）")
    sp_mongo.add_argument("--limit", type=int, default=20,
                          help="search 的最大条数（默认 20）")
    sp_mongo.set_defaults(func=cmd_mongo)

    sp_recert = sub.add_parser("recert", parents=[common],
                               help="WCET 续证 PDU 计分方案（IEEE 无线通信工程技术认证，已停办；"
                                    "双周期≥60/100 PDU、10 活动分类计分与封顶、七大技术领域，"
                                    "由投递的 .xls 解析规则知识层，只读不联网，v0.6.51）")
    sp_recert.add_argument("recert_action", nargs="?", default="overview",
                          choices=["overview", "cycles", "areas", "categories",
                                   "show", "rules", "caps"],
                          help="overview=方案速览(默认)；cycles=两周期下限与跨度；"
                               "areas=七大技术知识领域；categories=活动分类计分与封顶；"
                               "show <类>=单类规则(如 work/teaching/conferences)；"
                               "rules=续证合规校验清单；caps=各分类理论封顶合计")
    sp_recert.add_argument("term", nargs="?", default="",
                          help="show 的活动分类 key（如 work / volunteering / teaching / "
                               "publications / training / self_study / license_cert / "
                               "conferences / wcet_support / member_rank）")
    sp_recert.set_defaults(func=cmd_recert)

    sp_radio = sub.add_parser("radio", parents=[common],
                              help="无线电技术与标准只读诊断（v0.6.75；射频开关/无线物理能力/蓝牙/总线"
                                   "器件 + SDR 工具链存在性盘点 + 法规口径核对：型号核准·微功率·ISM·"
                                   "业余·无线充电；法规结论只引官方源，只读不驱动任何真实发射）")
    sp_radio.add_argument("radio_action", nargs="?", default="overview",
                          choices=["overview", "rf", "wifi", "bluetooth", "rf_devices",
                                   "sdr", "regulation", "capabilities"],
                          help="overview=总览(默认)；rf=射频开关(rfkill)；wifi=Wi-Fi 物理能力与 regdom；"
                               "bluetooth=蓝牙控制器(只 show 不扫描)；rf_devices=总线射频器件；"
                               "sdr=SDR 与无线工具链存在性；regulation=法规与频段合规口径；"
                               "capabilities=无线能力总览")
    sp_radio.set_defaults(func=cmd_radio)

    sp_winternals = sub.add_parser("winternals", parents=[common],
                              help="开源 Windows 分析学习应用只读诊断（v0.6.76；先定系统再谈目录——"
                                   "判定目标环境后按其自身的文件系统/目录约定/运行语言标准核验，"
                                   "含 Ghidra·x64dbg·radare2·Volatility3·MemProcFS·ReactOS·Wine 等"
                                   "工具链存在性盘点与内核原理锚点；只问在不在，绝不启动任何工具）")
    sp_winternals.add_argument("winternals_action", nargs="?", default="overview",
                          choices=["overview", "env", "fs", "runtime", "toolchain",
                                   "anchors", "capabilities"],
                          help="overview=总览(默认)；env=目标环境判定；fs=文件系统与目录约定；"
                               "runtime=运行语言环境与工具链自身语言依赖；toolchain=分析工具链存在性；"
                               "anchors=内核原理锚点与许可纯度；capabilities=能力总览")
    sp_winternals.set_defaults(func=cmd_winternals)

    sp_qstore = sub.add_parser("qstore", parents=[common],
                              help="量子存储交换只读诊断（v0.6.77；ext4 默认 4K 对齐 + "
                                   "GPU/NPU/TPU/CAN 异构端点缓冲交互 + 量子数字逻辑矩阵"
                                   "（Π_k 置换矩阵）做进制转换 + 储存读取扫描索引管线仿真；"
                                   "绝不写盘，格式化命令只作文本建议）")
    sp_qstore.add_argument("qstore_action", nargs="?", default="overview",
                          choices=["overview", "endpoints", "align", "radix",
                                   "pipeline", "capabilities"],
                          help="overview=总览(默认)；endpoints=端点存在性盘点；"
                               "align=4K 对齐核验；radix=量子进制转换；"
                               "pipeline=管线仿真；capabilities=能力总览")
    sp_qstore.set_defaults(func=cmd_qstore)

    sp_qarch = sub.add_parser("qarch", parents=[common],
                              help="量子架构内核只读诊断（v0.6.78；Linux 6.18.57 LTS + "
                                   "arch/quantum 纯新增架构（不删不改其他架构）+ QPU 模拟"
                                   "设备 /dev/qpuN；纯只读盘点，绝不执行内核构建）")
    sp_qarch.add_argument("qarch_action", nargs="?", default="overview",
                          choices=["overview", "tree", "arch", "qpu", "dist",
                                   "capabilities"],
                          help="overview=总览(默认)；tree=内核树盘点；arch=架构覆盖；"
                               "qpu=QPU 设备语义；dist=补丁分发与重建；capabilities=能力总览")
    sp_qarch.set_defaults(func=cmd_qarch)

    sp_langs = sub.add_parser("langref", parents=[common],
                              help="编程语言与编译器知识库（v0.6.53；以 2008–2026 新发语言为主体，"
                                   "补历史锚点(古今)与国内外代表，及查询/标记/数据/Shell/IR/排版等"
                                   "「其他计算机类」；结构化元数据不复制教材，存疑项标 needs_verify，"
                                   "只读不联网；注：`langs` 已用于语言运行时探测子系统）")
    sp_langs.add_argument("langs_action", nargs="?", default="overview",
                          choices=["overview", "stats", "window", "search", "show",
                                   "category", "origin", "paradigms", "verify"],
                          help="overview=库速览(默认)；stats=统计；window=2008–2026 窗口内语言；"
                               "search <词>=检索；show <id>=单条详情；category <分类>=按分类；"
                               "origin <来源>=按来源(国外/国内/国际)；paradigms=范式分布；"
                               "verify=待核实条目")
    sp_langs.add_argument("term", nargs="?", default="",
                          help="search/show/category/origin 的参数（关键词/id/分类/来源）")
    sp_langs.set_defaults(func=cmd_langref)

    sp_plang = sub.add_parser("plang", parents=[common],
                              help="编程语言「概念系统」分层分类（v0.6.56；以仓库 wordbuddy-github 为主目录，"
                                   "按执行模型→硬件架构子分类(isa/vm/加速器/FPGA/宿主/非执行)→能力域→"
                                   "底层标准依据(RFC 等，经 rfc_catalog 交叉验证)组织 161 条语言；"
                                   "含「各语言尝试编程整体」实测，只读不联网）")
    sp_plang.add_argument("plang_action", nargs="?", default="overview",
                          choices=["overview", "archs", "arch", "models", "model",
                                   "of", "rfc", "probe", "domains"],
                          help="overview=概念系统速览(默认)；archs=硬件架构子分类清单；"
                               "arch <架构>=该架构下语言；models=执行模型；model <模型>=该模型下语言；"
                               "of <id>=单语言完整分类(含继承的底层标准)；rfc [id]=RFC 依据；"
                               "probe=各语言「编程整体」实测；domains=能力域与底层标准")
    sp_plang.add_argument("term", nargs="?", default="",
                          help="arch/model/of/rfc 的参数")
    sp_plang.set_defaults(func=cmd_plang)

    sp_netsys = sub.add_parser("netsys", parents=[common],
                               help="网络与组网「概念系统」（v0.6.57；以仓库 wordbuddy-github 为主目录，"
                                    "把散落的网络/组网子系统按网络层次→组网形态→能力性质→标准依据四轴重组，"
                                    "显式登记依赖/互补关系与红线；RFC 经 rfc_catalog 交叉验证，只读不联网）")
    sp_netsys.add_argument("netsys_action", nargs="?", default="overview",
                           choices=["overview", "layers", "layer", "forms", "form",
                                    "natures", "nature", "of", "relations", "rfc",
                                    "redlines"],
                           help="overview=概念系统速览(默认)；layers/layer <层次>=按网络层次；"
                                "forms/form <形态>=按组网形态；natures/nature <性质>=按能力性质；"
                                "of <id>=单模块视图(层次/形态/性质/依赖/互补/标准/红线)；"
                                "relations=依赖与互补关系图；rfc=引用的 RFC；redlines=各模块红线")
    sp_netsys.add_argument("term", nargs="?", default="",
                           help="layer/form/nature/of 的参数；relations 可给 depends/complements")
    sp_netsys.set_defaults(func=cmd_netsys)

    sp_daoxue = sub.add_parser("daoxue", parents=[common],
                               help="「道枢」概念系统（v0.6.58+；中心指导理念《道德经》81 章，"
                                    "前置指导思想《太上玄门早坛功课经》，中间二级《般若波罗蜜多心经》"
                                    "与《论语》，后置指导思想《太上玄门晚坛功课经》，"
                                    "方术子层符箓·咒语·画符仪轨·祝由；理念落成 15 条"
                                    "可审计的工程治理原则并桥接 plang/netsys/langref；"
                                    "不复制经典全文，只读不联网）")
    sp_daoxue.add_argument("daoxue_action", nargs="?", default="overview",
                           choices=["overview", "center", "pre", "post", "middle",
                                    "fangshu", "principles", "bridge", "apply",
                                    "search", "verify", "stats"],
                           help="overview=五层速览(默认)；center [1-81]=道德经全章或单章；"
                                "pre=早坛功课(可给课程序位过滤)；post=晚坛功课(同)；"
                                "middle=中间二级思想；fangshu [域|条目id]=方术子层"
                                "（fu 符/lu 箓/zhou 咒/fa 法/you 由）；"
                                "principles [id]=治理原则与工程落法；"
                                "bridge [系统]=理念→plang/netsys/langref 的桥接边；"
                                "apply <系统>=某系统适用的原则；search <词>=跨层检索；"
                                "verify=诚实边界；stats=规模统计")
    sp_daoxue.add_argument("term", nargs="?", default="",
                           help="center 的章号 / pre-post 的课程序位 / principles 的 id / "
                                "bridge-apply 的系统 / search 的关键词")
    sp_daoxue.set_defaults(func=cmd_daoxue)

    sp_quantum = sub.add_parser("quantum", parents=[common],
                                help="量子理念「概念系统」（v0.6.65；以仓库 wordbuddy-github 为主目录，"
                                     "按量子态表示→线路→算法→硬件→纠错→网络→工具链→经典模拟与语义八域登记 "
                                     "66 个概念；标准（OpenQASM 3/QIR/ISO-IEC 4879/IEEE 7130/"
                                     "ITU-T Y.3800/ETSI QKD 014/FIPS PQC）逐条标注核实状态；"
                                     "31 条桥接边接到 plang/netsys/daoxue/datong；本仓库不含量子硬件探针，"
                                     "只做理念与标准登记，只读不联网）")
    sp_quantum.add_argument("quantum_action", nargs="?", default="overview",
                            choices=["overview", "domains", "domain", "of",
                                     "standards", "bridge", "search", "verify",
                                     "stats", "vm", "qudit", "qudreg", "qudexp", "bitconv"],
                            help="overview=八域速览(默认)；domains=八域清单；"
                                 "domain <域>=该域概念；of <id>=单概念(标准/桥接)；"
                                 "standards=标准登记册(核实状态)；bridge [系统]=桥接边；"
                                 "search <词>=跨域检索；verify=诚实边界；stats=规模统计；"
                                 "vm <bell|ghz|teleport|grover2q|bv2|arch>=量子虚拟机(架构演示)；"
                                 "qudit [d] [value]=多位元 qudit 报告(d 级系统 log2(d) 比特容量+同位能级散逸+log 值交换)；"
                                 "qudreg [width] [d] [gamma]=多位元寄存器报告(结合 PiLink 内存交换参数覆盖 8/16/64/128 位元)；"
                                 "qudexp [width] [gamma] [seed] [samples]=寄存器级多位元往返耗散实验(BER 随 γ 扫描，可复现；samples 后接 --plot 生成 SVG)；"
                                 "bitconv [width] [value] [gamma] [d]=降维升维位元转化(精确升维↔降维 R∘E=I 无损；γ>0 量化耗散损失；加 --table 看 8/16/64/128 全宽维数比)")
    sp_quantum.add_argument("--plot", default=None, metavar="PATH",
                            help="qudexp 动作专用：把 BER-γ 曲线写成 SVG（纯标准库，无依赖）")
    sp_quantum.add_argument("--table", action="store_true",
                            help="bitconv 动作专用：打印 8/16/64/128 全位宽维度画像表（升维比/降维比/联合维数）")
    sp_quantum.add_argument("term", nargs="*", default=[],
                            help="domain 的轴名 / of 的概念 id / bridge 的系统 / search 的关键词 / vm 的程序名 / qudit 的 [d] [value]")
    sp_quantum.add_argument("--shots", type=int, default=1024,
                            help="vm 动作的测量枪数（默认 1024）")
    sp_quantum.add_argument("--seed", type=int, default=None,
                            help="vm 动作的随机种子（固定种子结果可复现）")
    sp_quantum.set_defaults(func=cmd_quantum)

    sp_comp = sub.add_parser("comp", parents=[common],
                             help="编译与工具链「概念系统」（v0.6.59；以仓库 wordbuddy-github 为主目录，"
                                  "    按 编译流水线→工具链→构建形态→产物形态→语言编译需要→黑箱逆向→位宽与寻址世代 七轴组织 "
                                  "60 个概念，57 条桥接边接到 plang / daoxue / datong / netsys / llvm;"
                                  "语言编译需要仅对 plang probe 实测通过的 "
                                  "15 种语言逐条登记(驱动/产物/证据)，其余 146 种汇总 needs_verify 不臆造；"
                                  "只读登记不驱动真实编译，只读不联网）")
    sp_comp.add_argument("comp_action", nargs="?", default="overview",
                         choices=["overview", "domains", "domain", "of", "need",
                                  "needs", "bridge", "search", "verify", "stats"],
                         help="overview=七轴速览(默认)；domains=七轴清单；"
                              "domain <轴>=该轴概念；of <id>=单概念；need <语言>=该语言编译需要；"
                              "needs=15 种实测语言的编译需要汇总；bridge [系统]=桥接边；"
                              "search <词>=跨轴检索；verify=诚实边界；stats=规模统计")
    sp_comp.add_argument("term", nargs="?", default="",
                         help="domain 的轴名 / of-need 的 id 或语言名 / bridge 的系统 / search 的关键词")
    sp_comp.set_defaults(func=cmd_comp)

    sp_apilab = sub.add_parser("apilab", parents=[common],
                               help="接口 API「概念系统」（v0.6.59；以仓库 wordbuddy-github 为主目录，"
                                    "按 风格→规约→传输→认证→仓库接口面 五轴登记 32 个概念；RFC 依据经 "
                                    "rfc_catalog 交叉验证；repo-face 轴以当前仓库实测事实登记"
                                    "（103 个 CLI 子命令 / webapi 29 个 JSONL ACTIONS）；"
                                    "红线：令牌禁入 URL/localStorage、私钥不明文、短时效+服务端刷新，只读不联网）")
    sp_apilab.add_argument("apilab_action", nargs="?", default="overview",
                           choices=["overview", "domains", "domain", "of", "repo",
                                    "rfc", "bridge", "search", "verify", "stats"],
                           help="overview=五轴速览(默认)；domains=五轴清单；"
                                "domain <轴>=该轴概念；of <id>=单概念(标准/桥接)；"
                                "repo=本仓库接口面实测事实；rfc=引用的 RFC；bridge [系统]=桥接边；"
                                "search <词>=跨轴检索；verify=诚实边界；stats=规模统计")
    sp_apilab.add_argument("term", nargs="?", default="",
                           help="domain 的轴名 / of 的概念 id / bridge 的系统 / search 的关键词")
    sp_apilab.set_defaults(func=cmd_apilab)

    sp_concepts = sub.add_parser("concepts", parents=[common],
                                 help="概念系统中心（v0.6.62）：plang/netsys/daoxue/quantum/"
                                      "comp/apilab/zhuangzi/baigong/datong 九个概念系统的统一入口——overview 总览、"
                                      "search 跨系统检索、show 看单系统；只读不联网")
    sp_concepts.add_argument("concepts_action", nargs="?", default="overview",
                             choices=["overview", "search", "show", "topo"],
                             help="overview=九系统总览(默认)；search <词>=跨系统检索；"
                                  "show <系统>=单系统摘要；topo=跨系统桥接拓扑矩阵")
    sp_concepts.add_argument("term", nargs="?", default="",
                             help="search 的关键词 / show 的系统名")
    sp_concepts.set_defaults(func=cmd_concepts)

    # ---------------- v0.6.60：用户端人体工程学入口（南华理念 · guide） ------- #
    sp_guide = sub.add_parser("guide", parents=[common],
                              help="一屏操作入口地图（南华·逍遥游：无待一步；"
                                   "全部子命令按场景分组，--principles 看七原则）")
    sp_guide.add_argument("--principles", action="store_true",
                          help="附用户端人体工程学七原则（南华真经→工程翻译）")
    sp_guide.set_defaults(func=cmd_guide)

    # ---------------- v0.6.60：南华用户端概念系统（zhuangzi） ---------------- #
    sp_zhuangzi = sub.add_parser("zhuangzi", parents=[common],
                                 help="「南华」用户端概念系统（v0.6.60；《南华真经》核心理念三篇："
                                      "逍遥游·无待一步 / 应帝王·顺性不抢 / 大宗师·意图为宗师；"
                                      "落成七条可审计的人体工程学原则，桥接 daoxue/apilab；"
                                      "只读不联网，不复制经典全文）")
    sp_zhuangzi.add_argument("zhuangzi_action", nargs="?", default="overview",
                             choices=["overview", "core", "inner", "outer", "ergonomics",
                                      "concept", "principles", "bridge", "userface",
                                      "verify", "stats", "search"],
                             help="overview=四轴速览(默认)；core=核心理念三篇；inner=内篇辅篇；"
                                  "outer=外杂选篇；ergonomics=七条工程原则；concept <id>=单条详情；"
                                  "principles [id]=原则与落法；bridge [system]=桥接边；"
                                  "userface=本仓库用户端面实测；verify=诚实边界；stats=规模统计")
    sp_zhuangzi.add_argument("term", nargs="?", default="",
                             help="concept/principles 的 id / bridge 的 system 过滤 / search 关键词")
    sp_zhuangzi.set_defaults(func=cmd_zhuangzi)

    # ---------------- v0.6.61：百工匠作概念系统（墨子/公输般/公孙策/鲁班） ---- #
    sp_baigong = sub.add_parser("baigong", parents=[common],
                                help="「百工」匠作概念系统（v0.6.61；墨子·非攻守御 / 公输般·九设九距 / "
                                     "鲁班·绳墨 / 公孙策·锦囊 / 三教九流；落成七条匠作原则，"
                                     "覆盖具体无解/暂时不允许/构建程序具体结构三场景；只读不联网）")
    sp_baigong.add_argument("baigong_action", nargs="?", default="overview",
                            choices=["overview", "core", "craft", "schools", "scenes",
                                     "concept", "principles", "bridge", "userface",
                                     "verify", "stats", "search"],
                            help="overview=四轴速览(默认)；core=核心理念五偶；craft=匠作七原则；"
                                 "schools=三教九流12条；scenes=工程场景三条；concept <id>=单条详情；"
                                 "principles [id]=原则与落法；bridge [system]=桥接边；"
                                 "userface=用户端面+语言面实测；verify=诚实边界；stats=规模统计")
    sp_baigong.add_argument("term", nargs="?", default="",
                            help="concept/principles 的 id / bridge 的 system 过滤 / search 关键词")
    sp_baigong.set_defaults(func=cmd_baigong)

    # ---------------- v0.6.62：大同人类文明一体概念系统（datong） ----------- #
    sp_datong = sub.add_parser("datong", parents=[common],
                               help="「大同」人类文明一体概念系统（v0.6.62；唯道独尊·万流殊涂同归 → "
                                    "正道六象：天罡元阳（气·电·波）/ 地煞元阴（固·液·磁）→ "
                                    "九条人间落法；桥接八个既有系统；只读不联网）")
    sp_datong.add_argument("datong_action", nargs="?", default="overview",
                           choices=["overview", "traditions", "theses", "six", "practices",
                                    "concept", "principles", "bridge", "userface",
                                    "verify", "stats", "search"],
                           help="overview=五轴速览(默认)；traditions=文明传统15条；theses=核心命题21条；"
                                "six=正道六象；practices=实践形态12条；concept <id>=单条详情；"
                                "principles [id]=人间落法九原则；bridge [system]=桥接边；"
                                "userface=用户端面+语言面实测；verify=诚实边界；stats=规模统计")
    sp_datong.add_argument("term", nargs="?", default="",
                           help="concept/principles 的 id / bridge 的 system 过滤 / search 关键词")
    sp_datong.set_defaults(func=cmd_datong)

    # ---------------- v0.6.66：产品（设备设施）长期运行与基本保护概念系统（protec） ---- #
    sp_protec = sub.add_parser("protec", parents=[common],
                               help="「protec」产品保护概念系统（v0.6.66；材料耐久/电气安全/环境标准/"
                                    "应急保护四域 → 七条基本保护原则：冗余/降额/隔离/监控/接地/防护/可维护；"
                                    "整合 IEC/ASHRAE/IP/GB 标准；桥接 netsys/datong/zhuangzi/baigong/"
                                    "apilab/comp/quantum；只读不联网）")
    sp_protec.add_argument("protec_action", nargs="?", default="overview",
                           choices=["overview", "durability", "electrical", "environment",
                                    "emergency", "protection", "concept", "principles", "bridge",
                                    "userface", "verify", "stats", "search"],
                           help="overview=五轴速览(默认)；durability=材料耐久7条；electrical=电气安全6条；"
                                "environment=环境标准4条；emergency=应急保护4条；protection=七条保护原则；"
                                "concept <id>=单条详情；principles [id]=保护原则；bridge [system]=桥接边；"
                                "userface=用户端面+语言面实测；verify=诚实边界；stats=规模统计")
    sp_protec.add_argument("term", nargs="?", default="",
                           help="concept/principles 的 id / bridge 的 system 过滤 / search 关键词")
    sp_protec.set_defaults(func=cmd_protec)

    # ---------------- v0.6.67：自然科学概念系统（sciences） ------------------- #
    sp_sciences = sub.add_parser("sciences", parents=[common],
                                 help="「sciences」自然科学概念系统（v0.6.67；材料/热/气候/环境/物理/"
                                      "化学/生物七门学科 + 科学方法，protec 工程保护的科学底座；"
                                      "桥接 protec/量子/编译/接口/百工/大同/组网；只读不联网）")
    sp_sciences.add_argument("sciences_action", nargs="?", default="overview",
                             choices=["overview", "materials", "thermodynamics", "climatology",
                                      "environmental", "physics", "chemistry", "biology",
                                      "methodology", "concept", "principles", "bridge",
                                      "userface", "verify", "stats", "search"],
                             help="overview=八轴速览(默认)；materials/thermodynamics/climatology/"
                                  "environmental/physics/chemistry/biology=各学概念；methodology=科学方法七原则；"
                                  "concept <id>=单条详情；principles [id]=方法原则；bridge [system]=桥接边；"
                                  "userface=用户端面+语言面实测；verify=诚实边界；stats=规模统计")
    sp_sciences.add_argument("term", nargs="?", default="",
                             help="concept/principles 的 id / bridge 的 system 过滤 / search 关键词")
    sp_sciences.set_defaults(func=cmd_sciences)

    # ---------------- v0.5.22：JDK / 内核 module+firmware / 档位 / 数学评分 ------- #
    sub.add_parser("jdk", parents=[common],
                   help="OpenJDK / JVM 只读体检（java 版本/属性白名单/JPMS 模块/GC/JIT 标志/"
                        "诊断工具面/JFR 能力/Gradle-Maven 缓存，v0.5.22）"
                   ).set_defaults(func=cmd_jdk)
    sub.add_parser("kmod", parents=[common],
                   help="Linux 内核 module/firmware/eBPF 只读层（/proc/modules、/sys/module、"
                        "模块参数只读、modinfo、/lib/firmware、firmware_class、BTF/bpffs、"
                        "kprobe 面、模块 sysctl、黑名单、电源/温控，v0.5.22）"
                   ).set_defaults(func=cmd_kmod)
    sp_profiles = sub.add_parser("profiles", parents=[common],
                                 help="任务档位（大而全 full / 小而全 minimal 等四档，v0.5.22）")
    sp_profiles.add_argument("profile_action", nargs="?", default="list",
                             choices=["list", "show", "tasks", "compare"],
                             help="list=档位清单与场景档；show=某档位详情（含数学评分）；"
                                  "tasks=列出某档位命中的任务；compare=两档位对比(Jaccard)")
    sp_profiles.add_argument("--against", default="full",
                             help="compare 动作的对照档位（默认 full）")
    # 注意：--profile 已由 parents=[common] 提供（全子命令通用），此处不可重复添加
    sp_profiles.set_defaults(func=cmd_profiles, profile_action="list")
    sp_channels = sub.add_parser("channels", parents=[common],
                                 help="版本通道（stable 常态稳定版 / lts 长期支持版 / fresh 尝鲜版；"
                                      "仅记偏好，绝不自动升级，v0.6.30）")
    sp_channels.add_argument("channel_action", nargs="?", default="list",
                             choices=["list", "show", "recommend", "select"],
                             help="list=通道清单；show=某通道详情(含画像推荐)；"
                                  "recommend=据使用量/年限/环境给推荐；select=写入偏好(不升级)")
    sp_channels.add_argument("--channel", default="stable", help="show/select 的目标通道")
    sp_channels.add_argument("--usage", default="moderate", choices=["light", "moderate", "heavy"],
                             help="recommend/show 的设备使用量")
    sp_channels.add_argument("--years", default=4, help="recommend/show 的期望使用年限（年）")
    sp_channels.add_argument("--env", default="", help="recommend/show 的环境标签，逗号分隔"
                             "（如 high_temp,high_humidity,dusty,mobile,plugged_in）")
    sp_channels.set_defaults(func=cmd_channels, channel_action="list")
    sp_score = sub.add_parser("score", parents=[common],
                              help="数学化量化评估（归一化加权 WSM 评分 / Shannon 熵分布 / "
                                   "Gini 平台均衡度，借鉴 openai/math 理念但不 vendor LaTeX，v0.5.22）")
    sp_score.add_argument("score_action", nargs="?", default="overview",
                          choices=["overview", "global", "platform", "profile", "balance"],
                          help="overview/global=全库评分与熵分布；platform=当前平台评分；"
                               "profile=某档位评分；balance=平台间均衡度(Gini/CV)")
    # 注意：--profile 已由 parents=[common] 提供
    sp_score.set_defaults(func=cmd_score, score_action="overview")
    sp_arch = sub.add_parser("arch", parents=[common],
                             help="架构/指令集：龙芯 LoongArch / MIPS / RISC-V / 开源硬件（OSHWA/CERN OHL）")
    sp_arch.add_argument("--audience", choices=["cn", "intl", "regional",
                                                  "us", "jp", "eu", "de"],
                         default="cn", help="标准引用受众：cn=国内优先国标；"
                         "intl=面向外国用户用国际标准；regional=按地区执行；"
                         "us/jp/eu/de=按具体国家/地区优先")
    sp_arch.set_defaults(func=cmd_arch)
    sub.add_parser("uniapp", parents=[common], help="uni-app 需要的 API 清单 + 该目标端的清理任务").set_defaults(func=cmd_uniapp)
    sub.add_parser("gui", parents=[common], help="图形界面点选（Python 自带 tkinter，零依赖）").set_defaults(func=cmd_gui)
    sp_diag = sub.add_parser("diag", parents=[common],
                             help="生成脱敏诊断报告（只写本地，绝不自动上传）")
    sp_diag.add_argument("--out", help="报告落点（默认 ~/Downloads/sysweeper-diagnostics-<时间>.txt）")
    sp_diag.add_argument("--note", help="附加一行说明（例如复现步骤）")
    sp_diag.set_defaults(func=cmd_diag)

    sp_code = sub.add_parser("code", parents=[common],
                             help=_("低层码制：机器码/编译码、ASCII 等字符编码、通信码、逻辑转换码"))
    sp_code.add_argument("layer", nargs="?", default="overview",
                         choices=["overview", "bits", "chars", "comm", "logic", "machine"],
                         help="层：bits=位与二进制 / chars=字符编码 / comm=通信码 / "
                              "logic=逻辑转换码 / machine=机器码与字节码")
    sp_code.add_argument("--action", default="",
                         help="子动作：bits(explain/endian/float/bcd/gray/bases/base)、"
                              "chars(charset/base/escape/morse/mojibake/ascii)、"
                              "comm(crc/checksum/frame/line/hamming/uart/baud)、"
                              "logic(table/sop/pos/kmap/qm/nand/adder)、"
                              "machine(py/pyc/x86/riscv/java/ident)")
    sp_code.add_argument("--value", default="", help="输入值：整数 / 文本 / 十六进制字节 / 表达式")
    sp_code.add_argument("--width", type=int, default=0,
                         help="位宽（bits 层，默认 32）/ 每字节位数（uart，默认 8）")
    sp_code.add_argument("--y", default="", help="第二个操作数（adder 的 y）")
    sp_code.add_argument("--baud", type=int, default=9600, help="波特率（comm/uart，默认 9600）")
    sp_code.add_argument("--clock", type=float, default=16000000.0,
                         help="时钟频率（comm/baud 分频表，默认 16 MHz）")
    sp_code.add_argument("--file", default="", help="读取文件字节（machine 的 java/ident/x86/pyc）")
    sp_code.add_argument("--base", type=int, default=0,
                         help="目标进制（bits 层 base 动作；默认 3 三进制；范围 2-36）")
    sp_code.add_argument("--sub", action="store_true", help="adder 动作改为做减法 x - y")
    sp_code.set_defaults(func=cmd_code)

    sp_chart = sub.add_parser("chart", parents=[common],
                              help="读取 JSON 报告（--report 生成）并打印 ASCII 可视化对比")
    sp_chart.add_argument("file", help="报告 JSON 文件路径")
    sp_chart.set_defaults(func=cmd_chart)

    sp_scan = sub.add_parser("scan", parents=[common], help="分析模式扫描（不改系统）")
    sp_scan.set_defaults(func=cmd_scan)

    sp_clean = sub.add_parser("clean", parents=[common], help="执行清理/优化")
    sp_clean.add_argument("--apply", action="store_true", help="真正执行（默认仅展示）")
    sp_clean.add_argument("--yes", action="store_true", help="确认执行中/高风险动作（含 opt-in 开关）")
    sp_clean.set_defaults(func=cmd_clean)

    sp_genbat = sub.add_parser("genbat", parents=[common],
                               help="生成 Windows 自包含 .bat（分析/执行/注册计划任务）")
    sp_genbat.add_argument("-o", "--output", default="", help="输出 .bat 路径（默认 sysweeper_optimize_win<版本>.bat）")
    sp_genbat.add_argument("--task-name", default="Sysweeper.Optimize", help="schedule 模式注册的计划任务名")
    sp_genbat.add_argument("--encoding", default="utf-8-sig", choices=["utf-8-sig", "utf-8", "gbk"],
                           help=".bat 文件编码（默认 utf-8-sig；中文 Windows 兼容性差时改 gbk）")
    sp_genbat.set_defaults(func=cmd_genbat)

    sp_webnews = sub.add_parser("webnews", parents=[common],
                                help="新闻/网站聚合优化资讯（只读：抓 http(s) RSS/网页→抽知识点→XDG 缓存）")
    sp_webnews.add_argument("webnews_action", nargs="?", default="report",
                            choices=["report", "fetch", "knowledge", "sources", "caps"],
                            help="report=能力+来源+知识点总览；fetch=抓取并抽取（--source 追加 URL）；"
                                 "knowledge=仅展示缓存知识点；sources=配置来源；caps=能力自检")
    sp_webnews.add_argument("--source", nargs="*", default=None,
                            help="fetch 时临时追加的 http(s) 来源 URL（可多个；不填则只抓默认来源）")
    sp_webnews.set_defaults(func=cmd_webnews)

    sp_edge = sub.add_parser("edge", parents=[common],
                             help="单板机/ARM SBC 只读探测与优化建议（板型/温度/降频欠压/启动盘，新硬件）")
    sp_edge.add_argument("edge_action", nargs="?", default="report",
                         choices=["report", "caps"],
                         help="report=板型+温度+降频/欠压+启动盘+只读建议；caps=能力自检")
    sp_edge.set_defaults(func=cmd_edge)

    sp_mesh = sub.add_parser("mesh", parents=[common],
                             help="组网节点发现（能力通告 SW-OFFER1 注册表：已知节点/广播通告/协议说明）")
    sp_mesh.add_argument("mesh_action", nargs="?", default="nodes",
                         choices=["nodes", "announce", "protocol"],
                         help="nodes=已知在线节点；announce=广播本机能力通告；protocol=协议说明")
    sp_mesh.set_defaults(func=cmd_mesh)

    sp_osi = sub.add_parser("osi", parents=[common],
                            help="OSI 七层网络诊断（L1 物理→L7 应用，只读；ISO/IEC 7498-1 / ITU-T X.200）")
    sp_osi.add_argument("osi_action", nargs="?", default="report",
                        choices=["report", "layer", "probe", "caps"],
                        help="report=七层整体诊断；layer=单层(N 用 --layer)；probe=外网可达性(--url)；caps=能力自检")
    sp_osi.add_argument("--layer", type=int, default=0, help="layer 动作的目标层数 1–7")
    sp_osi.add_argument("--url", default=None, help="probe 动作的外网地址（仅 http/https，红线）")
    sp_osi.set_defaults(func=cmd_osi)

    sp_distro = sub.add_parser("distro", parents=[common],
                               help="发行版识别与发行注记读取（只读本地 NEWS.Debian / changelog）")
    sp_distro.add_argument("distro_action", nargs="?", default="report",
                           choices=["report", "notes", "caps"],
                           help="report=身份+注记来源；notes=读某包注记(--pkg)；caps=能力自检")
    sp_distro.add_argument("--pkg", default=None, help="notes 动作的目标包名（读其本地 changelog/NEWS）")
    sp_distro.set_defaults(func=cmd_distro)
    sp_proton = sub.add_parser("proton", parents=[common],
                               help="游戏/应用兼容层诊断（Proton/Wine 前提核验：Vulkan/32位/同步/Steam）")
    sp_proton.add_argument("proton_action", nargs="?", default="report",
                           choices=["report", "caps"],
                           help="report=前提核验；caps=能力自检")
    sp_proton.set_defaults(func=cmd_proton)
    # v0.6.15 导入分析学习应用：wsl / virtgpu / browser / dnshealth
    sp_wsl = sub.add_parser("wsl", parents=[common],
                            help="WSL 环境只读诊断（wsl2-linux-kernel 坐标系：版本/内核/systemd）")
    sp_wsl.set_defaults(func=cmd_wsl)
    sp_virtgpu = sub.add_parser("virtgpu", parents=[common],
                                help="虚拟化与 GPU 虚拟化只读诊断（VirtIO-GPU / Venus 坐标系）")
    sp_virtgpu.set_defaults(func=cmd_virtgpu)
    sp_browser = sub.add_parser("browser", parents=[common],
                                help="浏览器/引擎检测 + Web 兼容知识参考（mdn/bcd 坐标系）")
    sp_browser.set_defaults(func=cmd_browser)
    sp_dnshealth = sub.add_parser("dnshealth", parents=[common],
                                  help="DNS 解析健康度只读诊断（聚焦解析链路，与 nm_resolved 互补）")
    sp_dnshealth.add_argument("--query", action="store_true",
                              help="发起一次良性 A 解析探测（默认不探测，零出网）")
    sp_dnshealth.set_defaults(func=cmd_dnshealth)
    # v0.6.17 优化网络模块：Tor / ZeroTier 只读诊断
    sp_tor = sub.add_parser("tor", parents=[common],
                            help="Tor（洋葱路由）匿名/隐私网络只读诊断（安装/版本/torrc/可插拔传输）")
    sp_tor.set_defaults(func=cmd_tor)
    sp_zt = sub.add_parser("zerotier", parents=[common],
                           help="ZeroTier 虚拟网络（SD-WAN/零信任组网）只读诊断（网络/控制器/moon）")
    sp_zt.set_defaults(func=cmd_zerotier)
    # v0.6.18 系统统筹总览：你中有我，我中有你（只读编排）
    sp_sysmap = sub.add_parser("sysmap", parents=[common],
                               help="系统统筹总览（只读编排 13 子系统：整体健康+局部状态+关联关系+有序深入）")
    sp_sysmap.set_defaults(func=cmd_sysmap)
    # v0.6.22：嵌入整体系统(sysmap)的子系统开关管理
    sp_subs = sub.add_parser("subsystems", parents=[common],
                             help="管理嵌入整体系统(sysmap)的子系统开关：列出/开启/关闭"
                                  "（全量登记，默认全开；firmware/plugins/modules 等均可单独开关）")
    sp_subs.add_argument("--list", action="store_true", help="列出全部子系统及开/关状态（默认）")
    sp_subs.add_argument("--enable", nargs="*", metavar="KEY", help="开启指定子系统 key（可多个/逗号分隔）")
    sp_subs.add_argument("--disable", nargs="*", metavar="KEY", help="关闭指定子系统 key（可多个/逗号分隔）")
    sp_subs.add_argument("--enable-all", action="store_true", help="开启全部子系统")
    sp_subs.add_argument("--disable-all", action="store_true", help="关闭全部子系统")
    sp_subs.set_defaults(func=cmd_subsystems)
    # v0.6.33：联动连轴体检（有方向有性质的联通图 + 孤岛/悬空自检）
    sp_link = sub.add_parser("linkage", parents=[common],
                             help="联动连轴体检（每条轴标注供给/门控/印证/闭环/串联，含孤岛与悬空轴自检）")
    sp_link.add_argument("--stats", action="store_true", help="额外打印结构化统计（轴数/孤岛数/联通度）")
    sp_link.add_argument("--chains", action="store_true", help="串联体检：最长串联链 + 串联深度 + 兼容层示范链")
    sp_link.add_argument("--path", nargs=2, metavar=("FROM", "TO"),
                         help="沿联动轴走一遍：看两个子系统之间怎么串起来（如 --path arch pkgmgr）")
    sp_link.add_argument("--graph", action="store_true", help="打印 ASCII 分层邻接图（按层分组列出出边）")
    sp_link.add_argument("--svg", metavar="PATH", help="导出联动图 SVG 到指定路径（纯标准库生成、可离线看）")
    sp_link.set_defaults(func=cmd_linkage)
    # v0.6.34：兼容层串联（四层依赖 + 场景结论）
    sp_compat = sub.add_parser("compat", parents=[common],
                               help="兼容层串联（四层依赖：底座/图形/运行时/供给；按场景给结论，只读不代装）")
    sp_compat.set_defaults(func=cmd_compat)
    # v0.6.35：补齐此前「登记了但没命令入口」的三项 + 全能全知自检
    sp_linux = sub.add_parser("linux", parents=[common],
                              help="Linux 本机发行面只读聚合（发行版/包管理/日志体积/根分区，只报告不清日志）")
    sp_linux.set_defaults(func=cmd_linux)
    sp_comp = sub.add_parser("compress", parents=[common],
                             help="压缩空间分析（只读：caps 看格式可读性 / report 估算还能压出多少，不压缩不解压不删除）")
    sp_comp.add_argument("action", nargs="?", default="caps", choices=["caps", "report"],
                         help="caps=格式可读性（默认） / report=空间分析")
    sp_comp.add_argument("--dir", help="指定扫描目录（默认 $HOME）")
    sp_comp.add_argument("--max-files", type=int, default=0, help="扫描文件数上限（0=用默认 2 万）")
    sp_comp.set_defaults(func=cmd_compress)
    sp_eme = sub.add_parser("emergency", parents=[common],
                            help="预警应急定位只读探测（report/position/alert，不发预警不上传位置）")
    sp_eme.add_argument("action", nargs="?", default="report",
                        choices=["report", "position", "alert"], help="默认 report")
    sp_eme.set_defaults(func=cmd_emergency)
    sp_omni = sub.add_parser("omni", parents=[common],
                             help="全能全知自检：我知道什么/我不知道什么/我不做什么（coverage 默认 / all / blind N / gaps / gen-stub KEY）")
    sp_omni.add_argument("action", nargs="?", default="coverage",
                         choices=["coverage", "all", "blind", "gaps", "gen-stub"],
                         help="默认 coverage；gaps=补齐清单；gen-stub=生成知识库占位")
    sp_omni.add_argument("extra", nargs="*", default=[],
                         help="blind 模式的 N（缺几处入口算半截能力）/ gen-stub 模式的 KEY")
    sp_omni.add_argument("--deep", action="store_true",
                         help="实跑各子系统报告，统计这台机器探不到的（秒级，默认不跑）")
    sp_omni.add_argument("--write", action="store_true",
                         help="gen-stub 模式下真正落盘（默认 dry-run，只回显内容）")
    sp_omni.set_defaults(func=cmd_omni)
    # v0.6.23：参数与阈值（GUI 同款可调项，命令行亦可改）
    sp_set = sub.add_parser("settings", parents=[common],
                            help="查看/修改可调参数与数值阈值（命令超时/输出截断/扫描条数/导入上限等）")
    sp_set.add_argument("--list", action="store_true", help="列出全部参数与阈值（默认）")
    sp_set.add_argument("--get", nargs="*", metavar="KEY", help="查询指定参数的当前值")
    sp_set.add_argument("--set", nargs="*", metavar="KEY=VALUE",
                        help="设置参数（可多个，如 cmd.timeout=300 arch=any）")
    sp_set.add_argument("--reset", action="store_true", help="全部恢复默认值")
    sp_set.add_argument("--history", action="store_true",
                        help="查看参数变更留痕（什么时候、从哪来、改了什么）")
    sp_set.set_defaults(func=cmd_settings)
    # v0.6.23：多来源导入（剪贴板 / 本地文件 / 图片二维码 / 摄像头扫码）
    sp_imp = sub.add_parser("import", parents=[common],
                            help="导入外部内容：剪贴板 / 本地文件 / 图片二维码 / 摄像头扫码（默认只查看）")
    sp_imp.add_argument("--from", dest="source", default=_importio.SRC_CLIPBOARD,
                        choices=[k for k, _l, _d in _importio.SOURCES],
                        help="导入来源（默认 clipboard；qr/camera 依赖可选库）")
    sp_imp.add_argument("--path", default="", help="file/qr 来源的路径（文本文件或图片文件）")
    sp_imp.add_argument("--as-settings", action="store_true",
                        help="把导入的 JSON 载入为参数（默认只查看，绝不自动写入）")
    sp_imp.set_defaults(func=cmd_import)
    # v0.6.25：统一 JSON 接口层（Deno Web 控制台 / 远端报告查看器的唯一后端）
    sp_api = sub.add_parser("webapi", parents=[common],
                            help="统一 JSON 接口：一行请求一行响应（只读诊断 + 用户配置读写；"
                                 "给 Web 控制台与报告查看器当后端）")
    sp_api.add_argument("--once", metavar="JSON", default="",
                        help="只处理这一条请求（JSON 文本），输出后退出；"
                             "不带此参数则走 JSONL 长连接（stdin 逐行读）")
    sp_api.add_argument("--pretty", action="store_true", help="缩进输出（调试用）")
    sp_api.set_defaults(func=cmd_webapi)
    # v0.6.25：一键拉起本机 Web 控制台（Deno 外壳 + webapi 后端）
    sp_web = sub.add_parser("web", parents=[common],
                            help="一键拉起本机 Web 控制台（需 Deno；未装则给安装指引，不自动装）")
    sp_web.add_argument("--port", type=int, default=8787, help="监听端口（默认 8787）")
    sp_web.add_argument("--host", default="127.0.0.1",
                        help="监听地址（默认 127.0.0.1 只本机可访问）")
    sp_web.add_argument("--no-open", action="store_true", help="启动后不自动开浏览器")
    sp_web.set_defaults(func=cmd_web)
    return p


def harden_streams() -> None:
    """把 stdout / stderr 收拾成「不会因为控制台编码而崩」的样子。

    为什么要这一段：Windows 上 Python 用控制台的 ANSI 代码页当 stdout 编码
    —— 英文系统是 cp1252，中文系统是 cp936/gbk。本 CLI 大量输出中文以及
    → ✓ 这类符号，在 cp1252 下第一次 print 就会抛
    ``UnicodeEncodeError: 'charmap' codec can't encode ...``，进程 exit 1。
    （GitHub Actions 的 windows-latest runner 实测如此，见 docs/VALIDATION.md。）

    处理顺序：优先整体切成 UTF-8；切不动（流被外部接管、或平台不支持
    reconfigure）就退一步只把 errors 改成 replace —— 宁可显示成问号，
    也不让整条命令挂掉。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # Python 3.6 及更早没有 TextIOWrapper.reconfigure
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            try:
                reconfigure(errors="replace")
            except Exception:
                pass


def _redirect_stdout_to_devnull() -> None:
    """把 fd 1 指向 devnull，让后续（含解释器退出时那次）flush 都写不炸。"""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except Exception:
        pass


def _flush_quietly() -> None:
    """退出前主动 flush 标准流，把 BrokenPipe 吞掉。

    为什么要显式 flush：stdout 被重定向到管道时是块缓冲，`print` 往往一路成功，
    错误只在**解释器退出阶段**那最后一次 flush 才冒出来 —— 那时已经跑出 main 的
    try 之外，抓不到，结果就是日志里那两行
    ``Exception ignored in: <_io.TextIOWrapper ...>`` / ``BrokenPipeError``
    和退出码 120。提前 flush 一遍，退出时缓冲区已空，就不会二次触发。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except BrokenPipeError:
            _redirect_stdout_to_devnull()
        except Exception:
            pass


def main(argv=None) -> int:
    harden_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    # v0.6.22：全局子系统开关（--list-subsystems/--enable/--disable）优先于子命令执行
    if (getattr(args, "list_subsystems", False)
            or getattr(args, "enable", None) or getattr(args, "disable", None)):
        from .native import subsystems as subs
        if getattr(args, "list_subsystems", False):
            _print_subsystems(subs)
        else:
            _apply_toggles(subs, getattr(args, "enable") or [], getattr(args, "disable") or [])
        return 0
    if not getattr(args, "func", None):
        # 默认等同于 scan（最安全）
        args = parser.parse_args(["scan"])
    # i18n：仅当用户显式指定 --locale 或 SYSWEEPER_LOCALE 时才切换；
    # 默认保持源语言 zh_CN（中文），不影响后台与测试断言。
    set_locale(getattr(args, "locale", None))
    try:
        args.func(args)
    except BrokenPipeError:
        # 下游提前把管道关了（最典型：sysweeper hardware | head -6）。
        # 这里必须先把 fd 1 挪走再返回，否则解释器退出时那次 flush 会再抛一次
        # BrokenPipeError，把退出码抬成 120 —— CI 里配上 `set -o pipefail`
        # 会把整步判成失败。
        _redirect_stdout_to_devnull()
        return 0
    except KeyboardInterrupt:
        return 130
    finally:
        _flush_quietly()
    return 0


if __name__ == "__main__":
    sys.exit(main())
