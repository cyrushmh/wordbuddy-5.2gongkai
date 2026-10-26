"""浏览器与引擎检测 + Web 兼容知识参考（只读）。

基于 mdn/browser-compat-data 的思路：把「Web 平台特性在各引擎的支持度」做成
可查询的数据集。本模块做两件只读的事：① 探测本机装了哪些浏览器/引擎及版本；
② 提供一个小型兼容知识参考（演示 BCD 的「特性→支持等级」结构，非完整数据集）。

红线：不下载 BCD 全量 JSON、不连校外网、不自动改浏览器配置。
"""
import shutil
from . import common

# 兼容知识参考（灵感来自 mdn/browser-compat-data 的「特性→支持等级」结构，
# 此处为极简静态子集，展示数据组织方式；完整数据请引用 @mdn/browser-compat-data）。
_COMPAT_NOTES = {
    "WebGPU": "Chromium 113+ / 近期 Firefox Nightly；Safari 技术预览。旧版不支持。",
    "Container queries": "Chromium 105+ / Firefox 110+ / Safari 16+。",
    ":has() 选择器": "Chromium 105+ / Safari 15.4+ / Firefox 121+。",
    "Top-level await": "主流引擎均已支持（2021+）。",
    "SharedArrayBuffer": "需跨源隔离（COOP+COEP）；部分历史版本因 Spectre 被默认关闭。",
}


def _browsers() -> list:
    found = []
    for name, cmd in (("chromium", "chromium --version"),
                      ("chromium-browser", "chromium-browser --version"),
                      ("google-chrome", "google-chrome --version"),
                      ("google-chrome-stable", "google-chrome-stable --version"),
                      ("firefox", "firefox --version")):
        exe = shutil.which(name) or shutil.which(cmd.split()[0])
        if exe:
            rc, out = common.run(f"{cmd} 2>/dev/null", timeout=8)
            if rc == 0 and out.strip():
                engine = "Blink" if "chrom" in name else "Gecko"
                first = out.strip().splitlines()[0]
                found.append((name, engine, first))
    return found


def capabilities_report() -> tuple:
    lines = [
        "浏览器/引擎检测 + Web 兼容知识参考 · 能力自检",
        "可诊断维度：",
        "  1. 已安装浏览器与版本（chromium / chrome / firefox）",
        "  2. 渲染引擎（Blink / Gecko）",
        "  3. Web 平台特性兼容知识参考（结构性子集，灵感来自 mdn/browser-compat-data）",
        "红线：不下载 BCD 全量 JSON、不连校外网、不自动改浏览器配置。",
    ]
    return (True, "\n".join(lines))


def browser_report() -> tuple:
    lines = []
    lines.append("==== 浏览器与引擎检测（只读）====")
    found = _browsers()
    if found:
        for name, engine, ver in found:
            lines.append(f"[{name}] 引擎={engine} | {ver}")
    else:
        lines.append("（未检测到常见浏览器：chromium / chrome / firefox）")
    lines.append("")
    lines.append("---- Web 兼容知识参考（结构性子集，灵感来自 mdn/browser-compat-data）----")
    for feat, note in _COMPAT_NOTES.items():
        lines.append(f"  · {feat}：{note}")
    lines.append("")
    lines.append("提示：完整跨浏览器特性支持矩阵请引用 @mdn/browser-compat-data 数据集。")
    return (True, "\n".join(lines))
