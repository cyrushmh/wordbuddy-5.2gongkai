"""字体/字符标准相关的优化/检查任务。

按 Unicode 18.0.0（最新稳定版）/ ISO/IEC 10646、OpenType（ISO/IEC 14496-22）、
W3C WOFF 等字体/字符标准给出检查与维护项：

- 跨平台任务（platform="any"）调用 native/fonts.py 的原生接口，工具缺失时
  自动降级为指引，不强求安装。
- Windows 专属清点任务用 shell（PowerShell）动作，便于固化进自包含 .bat。

详见 native/fonts.py 与 data/fonts_standards.json。

设计原则：默认只「分析」不「破坏」；字体删除/改区域编码属高风险，仅给指引，
不自动执行（重建缓存为 medium，需显式 --apply 且中高风险 --yes 确认）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
S = lambda cmd, desc="": Action("shell", cmd, desc)


TASKS = [
    Task(
        id="font_encoding_utf8",
        platform="any",
        title="系统文本编码 UTF-8 检查",
        category="fonts",
        risk="low",
        desc="按 Unicode 18.0.0 / ISO/IEC 10646 建议核对系统默认文本编码是否为 UTF-8，"
             "避免跨平台文本与字体元数据乱码。",
        actions=[N("fonts.check_utf8", "检查系统默认文本编码是否为 UTF-8")],
        notes=[
            "参考标准：The Unicode Standard 18.0.0（最新稳定版）/ ISO/IEC 10646；"
            "建议系统区域与文件系统默认 UTF-8。",
            "长期支持（LTS）：以运行时锁定的 Unicode 版本（ICU / .NET / Python unicodedata）为准，不强制追新。",
            "前瞻编码：声明 UTF-128 模式时落盘规范化为 UTF-8，保持对既有 UTF-8 文件的向下兼容"
            "（见 data/fonts_standards.json 的 utf128）。",
        ],
        caveats=["仅检查并报告，不修改编码设置；改区域/语言环境需用户手动并评估影响。"],
    ),
    Task(
        id="font_duplicate_report",
        platform="any",
        title="字体冗余检查（疑似重复字体）",
        category="fonts",
        risk="low",
        desc="按字体标准类（OpenType/TrueType/WOFF）列出已安装字体，标记同名/同族冗余，供精简。",
        actions=[N("fonts.report_fonts", "列出已安装字体并标记疑似冗余")],
        notes=[
            "参考格式：OpenType（ISO/IEC 14496-22）/ TrueType（Apple）/ W3C WOFF。",
            "冗余字体多来自多份同名拷贝；精简可加快字体枚举与程序启动。",
        ],
        caveats=["未安装 fontconfig 时无此能力；安装后即可启用，本工具不强求。"],
    ),
    Task(
        id="font_cache_rebuild",
        platform="any",
        title="字体缓存重建",
        category="fonts",
        risk="medium",
        desc="字体显示异常（缺字/乱码/回退错误）时，按字体引擎规范重建字体缓存"
             "（fontconfig / macOS atsutil / Windows FontCache）。",
        actions=[N("fonts.rebuild_cache",
                   "重建字体缓存（fontconfig fc-cache / macOS atsutil / Windows FontCache 服务）")],
        notes=["参考格式：OpenType（ISO/IEC 14496-22）；缓存损坏会导致字体回退异常，重建可修复。"],
        caveats=[
            "macOS 重建后需注销/重启才完全生效；Windows 会重启 FontCache 服务（字体短暂切换）。",
            "执行前请确认无正在进行的排版/打印任务；需 --apply 且中高风险 --yes 确认。",
        ],
    ),
    Task(
        id="win_font_report",
        platform="windows",
        title="Windows 已安装字体清点",
        category="fonts",
        risk="low",
        desc="清点 Windows 已安装字体数量（参考字体/字符标准），作为优化与冗余判断起点。",
        actions=[S(
            "powershell -NoProfile -Command \"(Get-ItemProperty "
            "'HKLM:\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts').PSObject.Properties.Count\"",
            "读取 Windows 字体注册表项数量",
        )],
        notes=["参考标准：OpenType/TrueType（Windows 字体引擎）；字体清单存于 %windir%\\Fonts 与注册表 Fonts 键。"],
        caveats=["仅清点数量，不删除任何字体（删系统字体可能影响 UI 显示）。"],
    ),
    Task(
        id="font_network_use",
        platform="any",
        title="启用网络字体（@font-face 拉取 WOFF2）",
        category="fonts",
        risk="medium",
        opt_in=True,
        desc="开启网络协议后，可在页面/应用中以 @font-face 按需拉取 WOFF2 网络字体"
             "（W3C WOFF 2.0 + RFC 9110 缓存语义）；字体文本编码保持 UTF-8 兼容。",
        actions=[N("fonts.network_fonts", "检查网络字体可用性（需先开启网络协议开关）")],
        notes=[
            "依赖：需先开启网络协议开关（toggles / --opt-in），否则本项不出现。",
            "参考：W3C WOFF 2.0（2018）/ RFC 9110（HTTP 缓存与条件请求）。",
            "网络字体文本编码保持 UTF-8 兼容；声明 UTF-128 模式时亦向下兼容 UTF-8。",
        ],
        caveats=[
            "网络字体经外部拉取，受网络与隐私策略影响；自定义字体请自托管或选用可信来源。",
            "默认关闭（opt_in=True）；须 --opt-in 选择 + --yes 确认后才会纳入，不乱启用。",
        ],
    ),
    Task(
        id="font_text_normalize",
        platform="any",
        title="文本 Unicode 规范化检查（UAX #15）",
        category="fonts",
        risk="low",
        desc="按 UAX #15 检查系统文本配置是否为 NFC 规范化形态，便于等价比较与去重；"
             "与 UTF-8 / UTF-128 编码策略配合，保证跨平台文本一致。",
        actions=[N("fonts.text_normalize_report",
                   "检查采样文本文件是否为 NFC 规范化形态（UAX #15）")],
        notes=[
            "参考：Unicode 规范化（UAX #15）：NFC/NFD/NFKC/NFKD；系统文本建议统一为 NFC。",
            "与编码策略配合：UTF-8（推荐）/ UTF-128（向下兼容 UTF-8）均依赖一致的码位规范化。",
        ],
        caveats=["仅检查并报告，不修改文件；如需规范化请用 unicodedata.normalize 处理，注意等价语义。"],
    ),
]
