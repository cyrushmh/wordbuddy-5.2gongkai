"""任务与动作的数据模型。

一个 Task 描述「在某个平台、某段版本范围内」的一项系统优化/清理动作。
动作（Action）分为五种执行通道：

- shell : 本地 shell 命令（桌面端真正执行）
- adb   : 通过 adb 推送到安卓设备执行
- python: 用 Python 标准库直接完成的清理（跨平台、零依赖）
- manual: 无法自动执行，仅给出操作指引（如 iOS、需图形界面点选的项）
- native: 调用 sysweeper.native 下的「系统原生接口」函数（如 Windows API /
          LSB / libimobiledevice），command 字段写 "module.func" 形式

任务（Task）的额外维度：
- requires_lang: 该任务用某种语言实现（ruby/go/node...），仅在当前环境探测到
  该语言运行时才「自动启用」，未安装则自动隐藏——不强求用户安装。
- opt_in: 默认关闭的高风险/影响行为类开关（如网络协议、ITU 标准相关调优），
  必须用户显式选择（--opt-in / --only）并确认（--yes）才会纳入与执行。

设计原则：默认只「分析」不「破坏」。任何删除类动作都必须经过 risk 评估与
显式 --apply 才会真正落地。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# 风险等级，数值越大越危险
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

# 任务分类
CATEGORIES = {
    "cleanup": "清理垃圾",
    "optimize": "性能优化",
    "privacy": "隐私清理",
    "maintenance": "系统维护",
    "network": "网络/协议优化",
    "fonts": "字体/字符标准",
    "accessibility": "无障碍辅助",
    "arch": "架构/指令集标准",
    "hardware": "硬件优化",
    # v0.6.90 新增（国内标准资源知识库 cnstd：官方平台/协议规范/第三方/概念四层）
    "standards": "标准/规范资源",
}

# 分类展示顺序（报告/列表/标准视图按此排序，保证「分类规范整体」一致）
CATEGORY_ORDER = ["cleanup", "optimize", "privacy", "maintenance", "hardware",
                  "network", "fonts", "accessibility", "arch", "standards"]

# 标准引用分层（分类规范整体）：参考时按受众分层、按优先级引用。
#   national     国家标准 / 国家平台：国内优先引用（如 GB 系列、个人信息保护法、
#                全国标准信息公共服务平台 std.samr.gov.cn）。
#   international 国际标准：面向外国用户 / 跨国场景使用（ISO/IEC、IEEE、IETF(RFC)、
#                ITU-T、W3C、Unicode 等）。
#   regional     地区标准：必要时按国家或地区执行（如欧盟 GDPR、美国相关规范）。
# 引用策略：默认（国内）优先国家平台/国家标准；给外国人用则改用国际标准；
#          个别场景按所在国家/地区标准执行。详细条目见 data/*.json。
STANDARD_TIERS = (
    ("national", "国家标准 / 国家平台（国内优先）"),
    ("international", "国际标准（面向外国用户 / 跨国）"),
    ("regional", "地区标准（按需按国家 / 地区执行）"),
)
NATIONAL_STANDARD_PORTAL = "全国标准信息公共服务平台（std.samr.gov.cn，国家标准化管理委员会）"

# 各分类对应的「标准/规范」出处（分类规范整体）：映射到参考文档与分层标准清单，
# 使每一项清理/优化都有据可依。standards 为三层 dict（national/international/regional）。
CATEGORY_STANDARDS = {
    "cleanup": {
        "doc": "（各平台原生缓存/临时目录规范）",
        "standards": {
            "national": [],  # 国家层面无专门“清理”国标，以操作系统厂商规范为准
            "international": [
                "XDG Base Directory（~/.cache，freedesktop 事实规范）",
                "Apple 用户库规范（~/Library/Caches）",
                "Windows Temp / 回收站（Shell32）",
            ],
            "regional": [],
        },
    },
    "optimize": {
        "doc": "（ACPI P-state/C-state、调度与电源规范）",
        "standards": {
            "national": [
                "中国能效标识（GB 24850 等能效限定值 / 节能评价值；"
                f"国家平台：{NATIONAL_STANDARD_PORTAL}）",
            ],
            "international": [
                "ACPI Specification（UEFI Forum）",
                "IEEE 802.11 节能模式（WMM / Power Save）",
                "Linux kernel sysctl 调优",
            ],
            "regional": [
                "美国 ENERGY STAR 能效认证（EPA，地区标准）",
                "欧盟 ErP 生态设计指令（EU 2019/1781，地区标准）",
                "日本 JIS C 类能效标准（地区标准）",
            ],
        },
    },
    "privacy": {
        "doc": "（隐私 / 数据最小化原则）",
        "standards": {
            "national": [
                "《个人信息保护法》(PIPL，中国) — 数据最小化与本地优先；"
                f"国家平台：{NATIONAL_STANDARD_PORTAL}",
            ],
            "international": [
                "OWASP 隐私实践（Privacy Risks）",
                "RFC 7858 / RFC 8484（DoT / DoH，传输层隐私）",
                "ISO/IEC 27001（信息安全管理）",
            ],
            "regional": [
                "欧盟 GDPR（一般数据保护条例，地区标准）",
                "美国 NIST SP 800-53（隐私控制家族，地区标准）",
                "日本 個人情報保護法（APPI，地区标准）",
            ],
        },
    },
    "maintenance": {
        "doc": "data/hardware.json / data/versions.json",
        "standards": {
            "national": [],
            "international": [
                "T13 / ATA8-ACS（S.M.A.R.T.）",
                "ATA TRIM（DATA SET MANAGEMENT）",
                "LSB（/etc/os-release）",
            ],
            "regional": [
                "美国 NIST SP 800-53（配置/维护控制，地区标准）",
                "日本 JIS X 系列（IT 设备，地区标准）",
            ],
        },
    },
    "hardware": {
        "doc": "data/hardware.json + data/hardware_kernel.json"
               "（Linux kernel Documentation 硬件子系统权威源码文档）",
        "standards": {
            "national": [
                "中国能效标识（GB 24850 等能效限定值 / 节能评价值；"
                f"国家平台：{NATIONAL_STANDARD_PORTAL}）",
            ],
            "international": [
                "Linux kernel Documentation（kernel.org，硬件子系统权威源码文档："
                "admin-guide/pm/、admin-guide/thermal/、admin-guide/mm/、block/、"
                "nvme/、watchdog/、scheduler/）",
                "ACPI Specification（UEFI Forum，P-state / C-state 电源与睡眠）",
                "T13 / ATA8-ACS（S.M.A.R.T.、TRIM）",
                "PCI-SIG / USB-IF（设备类代码）",
            ],
            "regional": [
                "美国 ENERGY STAR 能效认证（EPA，地区标准）",
                "欧盟 ErP 生态设计指令（EU 2019/1781，地区标准）",
            ],
        },
    },
    "network": {
        "doc": "data/network_standards.json",
        "standards": {
            "national": [
                "中国通信行业标准 YD/T 系列（路由 / 接入；"
                f"国家平台：{NATIONAL_STANDARD_PORTAL}）",
            ],
            "international": [
                "RFC 4941 / RFC 8200 / RFC 3168 / RFC 9002（IETF）",
                "IEEE 802.11（Wi-Fi 节能 / 调度）",
                "ITU-T Y.1541 / G.992 / G.711",
            ],
            "regional": [
                "美国 NIST SP 800-119（IPv6 安全部署指南，地区标准）",
                "欧盟 EN 301 549（ICT 产品无障碍，含网络服务，地区标准）",
            ],
        },
    },
    "fonts": {
        "doc": "data/fonts_standards.json",
        "standards": {
            "national": [
                "GB 18030《信息技术 中文编码字符集》（强制国标，向下兼容 Unicode；"
                f"国家平台：{NATIONAL_STANDARD_PORTAL}）",
            ],
            "international": [
                "Unicode 18.0.0 / ISO-IEC 10646",
                "OpenType（ISO/IEC 14496-22）",
                "W3C WOFF 2.0",
                "UAX #15（Unicode 规范化）",
            ],
            "regional": [
                "日本 JIS X 0213（日本語文字集合，地区标准）",
            ],
        },
    },
    "accessibility": {
        "doc": "src/python/sysweeper/a11y.py（ORCA / AT-SPI2 协议与接口）",
        "standards": {
            "national": [
                "GB/T 37668《信息技术 无障碍 通用设计规范》"
                f"（国家平台：{NATIONAL_STANDARD_PORTAL}）",
                "GB/T 38652《信息技术 无障碍 网页设计无障碍要求》",
                "YD/T 系列无障碍通信标准（工信部，信息无障碍）",
            ],
            "international": [
                "AT-SPI2（GNOME at-spi2-core，D-Bus org.a11y.Bus 辅助技术总线）",
                "W3C WCAG 2.2（Web 内容无障碍指南，W3C 推荐标准）",
                "W3C WAI-ARIA 1.2（可访问富互联网应用）",
                "ITU-T F.790（电信无障碍指南，面向老年与残障用户）",
            ],
            "regional": [
                "欧盟 EN 301 549（ICT 产品与服务无障碍，地区标准）",
                "美国 Section 508（联邦无障碍，修订版对齐 WCAG，地区标准）",
                "日本 JIS X 8341（高齢者・障害者配慮設計指針，地区标准）",
            ],
        },
    },
    "arch": {
        "doc": "data/arch.json + src/python/sysweeper/arch.py"
               "（龙芯 LoongArch / MIPS / RISC-V / 开源硬件）",
        "standards": {
            "national": [
                "龙芯 LoongArch 指令集架构（国产自主架构，龙芯中科；"
                f"相关国家标准见国家平台：{NATIONAL_STANDARD_PORTAL}）",
                "国产处理器（飞腾/鲲鹏/兆芯/海光/申威）适配相关国家标准（GB/T 系列，国家平台检索）",
                "中国 RISC-V 产业联盟（CRVA）开放指令生态规范",
            ],
            "international": [
                "RISC-V ISA Specification（RISC-V International，RVA20/RVA22/RVA23 profiles）",
                "MIPS Architecture for Programmers（MIPS32/MIPS64 Release 6，MIPS Open）",
                "Power ISA（OpenPOWER Foundation，含 Microwatt 开源核）",
                "OSHWA 开源硬件定义与认证（oshwa.org）+ CERN Open Hardware Licence（OHL v2）",
                "CHIPS Alliance（开放芯片设计与互连标准）",
            ],
            "regional": [
                "DIN SPEC 3105（德国：开放硬件标准化要求，地区标准）",
                "欧盟开放硬件实践（EUPL / 开源硬件倡议，地区标准）",
            ],
        },
    },
    # v0.6.90 新增（国内标准资源知识库：14 源分层，全部 2026-10-25 官方源实测）
    "standards": {
        "doc": "data/cnstd_domestic_standards.json + src/python/sysweeper/native/cnstd.py"
               "（国内标准资源 14 源：官方平台/协议规范/第三方渠道/概念科普）",
        "standards": {
            "national": [
                f"国家标准全文公开系统（openstd.samr.gov.cn，GB 6188 条 / "
                f"GB/T 61615 条实测，{NATIONAL_STANDARD_PORTAL}）",
                "全国标准信息公共服务平台（std.samr.gov.cn，行标 88751/76 行业、地标 49114 实测）",
                "行业标准信息服务平台（hbba.sacinfo.org.cn，行标备案公示 + 备案月报）",
                "中国通信标准化协会（CCSA，ccsa.org.cn/bzcx，YD/T 行标协会侧）",
                "市场监管总局合同示范文本库（htsfwb.samr.gov.cn，示范文本非技术标准）",
            ],
            "international": [
                "IETF RFC（rfc-editor.org；本仓 rfc_catalog 内置官方索引 10036 条）",
                "OASIS MQTT 协议规范（mqtt.org.cn 中文站为规范转载）",
                "Modbus 六规范（Modbus Organization 维护，modbus.cn 中文网转载）",
                "ISO/IEC 标准化文件（ISO Online Browsing Platform）",
            ],
            "regional": [],  # 国内资源为主，地区层暂无专门出处
        },
    },
}


def category_standards(cat: str) -> dict:
    """返回某分类对应的标准出处（doc + 分层 standards）。

    standards 为三层 dict：{"national": [...], "international": [...], "regional": [...]}
    """
    empty = {"national": [], "international": [], "regional": []}
    return CATEGORY_STANDARDS.get(cat, {"doc": "", "standards": empty})


def tier_order(audience: str) -> list:
    """按受众返回三层的引用顺序（list of tier key，越靠前越优先）。

    - cn        : 国标 / 国家平台优先 → 国际 → 地区
    - intl      : 国际优先 → 国标 → 地区（面向外国用户 / 跨国场景）
    - regional  : 地区优先 → 国标 → 国际
    - us/jp/eu/de：该地区优先（地区层内该国家/地区的条目排最前）→ 国标 → 国际
    """
    if audience == "intl":
        return ["international", "national", "regional"]
    if audience in ("regional", "region"):
        return ["regional", "national", "international"]
    if audience in REGION_KEYWORDS:
        return ["regional", "national", "international"]
    return ["national", "international", "regional"]


def standards_for_audience(cat: str, audience: str = "cn") -> list:
    """按受众返回优先级排序的标准清单（flat list of str）。

    默认 "cn"：参考优先国家平台 / 国家标准；给外国人用改用国际标准（intl）；
    个别场景按所在国家 / 地区标准执行（regional，或 us/jp/eu/de 精确地区）。
    """
    st = category_standards(cat).get("standards", {})
    order = tier_order(audience)
    out: list = []
    for tier in order:
        items = list(st.get(tier, []))
        # 精确地区受众：该地区条目排到最前（如 EU → GDPR / EN 301 549 / ErP）
        if tier == "regional" and audience in REGION_KEYWORDS:
            items.sort(key=lambda x: region_rank(x, audience))
        out.extend(items)
    return out


def category_label(cat: str) -> str:
    """分类的中文名；未知分类原样返回。"""
    return CATEGORIES.get(cat, cat)


# 层级标签（与 STANDARD_TIERS 的 key 对应）：用于 Task.standards 条目的前缀，
# 例如 "[国际] RFC 4941" / "[国标] YD/T 系列" / "[地区] 欧盟 GDPR"。
TIER_TAGS = {"national": "国标", "international": "国际", "regional": "地区"}
_TAG_TO_TIER = {v: k for k, v in TIER_TAGS.items()}


def parse_standard_ref(ref: str) -> tuple:
    """把一条 Task.standards 条目解析为 (tier, text)。

    约定前缀 `[国标]|[国际]|[地区]`；无前缀默认按 international 处理。
    返回 (tier_key, 纯文本)。
    """
    s = (ref or "").strip()
    for tag, tier in _TAG_TO_TIER.items():
        prefix = f"[{tag}]"
        if s.startswith(prefix):
            return tier, s[len(prefix):].strip()
    return "international", s


def task_standards_ordered(task, audience: str = "cn") -> list:
    """返回某任务的标准条目，按受众优先级排序，结果为带层级标记的字符串列表。

    例如 audience="cn" 时国标排前：["① [国标] YD/T ...", "  [国际] RFC 4941"]。
    任务自身未声明 standards 时，回退到「分类默认 + 关键词细化」的派生归属，
    使每一个普通任务也能展示自己的标准出处（分类规范整体逐条可追溯）。
    """
    refs = list(getattr(task, "standards", None) or []) or task_standards(task)
    if not refs:
        return []
    order = tier_order(audience)
    parsed = [parse_standard_ref(r) for r in refs]
    # 同一层内：精确地区受众时该地区条目排前
    if audience in REGION_KEYWORDS:
        parsed.sort(key=lambda p: (order.index(p[0]), region_rank(p[1], audience)))
    else:
        parsed.sort(key=lambda p: order.index(p[0]))
    out = []
    for tier, text in parsed:
        mark = "①" if tier == order[0] else " "
        out.append(f"{mark} [{TIER_TAGS.get(tier, tier)}] {text}")
    return out


# ---------------------------------------------------------------------------
# 任务级标准归属的「派生」规则（分类规范整体：每个普通任务也能追溯标准出处）
#
# 任务可在定义里显式写 standards=[...]（带 [国标]/[国际]/[地区] 前缀，见 network/arch
# 任务）；未显式声明的普通任务，按下面的规则派生：分类默认 + 关键词细化。
# 这样既避免逐条硬编码的维护负担，又保证「每一项优化都有据可依」。
# ---------------------------------------------------------------------------

# 分类 → 该分类任务的默认标准归属（带层级标记）
CATEGORY_TASK_STANDARDS = {
    "cleanup": [
        "[国际] XDG Base Directory 规范（~/.cache，freedesktop 事实标准）",
        "[国际] Apple 用户库规范（~/Library/Caches）",
        "[国际] Windows Temp / 回收站（Shell32 / SHGetKnownFolderPath）",
    ],
    "optimize": [
        "[国标] 中国能效标识（GB 24850 等，国家平台 std.samr.gov.cn）",
        "[国际] ACPI Specification（UEFI Forum，P-state / C-state）",
    ],
    "privacy": [
        "[国标] 《个人信息保护法》PIPL（数据最小化与本地优先）",
        "[国际] RFC 7858 / RFC 8484（DoT / DoH，传输层隐私）",
        "[地区] 欧盟 GDPR（一般数据保护条例）",
    ],
    "maintenance": [
        "[国际] T13 / ATA8-ACS（S.M.A.R.T. 磁盘健康）",
        "[国际] ATA TRIM（DATA SET MANAGEMENT，SSD 维护）",
        "[国际] LSB（/etc/os-release，发行版识别）",
    ],
    "fonts": [
        "[国标] GB 18030《信息技术 中文编码字符集》（强制国标，向下兼容 Unicode）",
        "[国际] Unicode 18.0.0 / ISO-IEC 10646",
        "[国际] UAX #15（Unicode 规范化 NFC）",
    ],
    "accessibility": [
        "[国标] GB/T 37668《信息技术 无障碍 通用设计规范》",
        "[国际] AT-SPI2（org.a11y.Bus 辅助技术总线，GNOME at-spi2-core）",
        "[国际] W3C WCAG 2.2 / WAI-ARIA 1.2",
        "[地区] 欧盟 EN 301 549（ICT 无障碍）",
    ],
    "arch": [
        "[国标] 龙芯 LoongArch 指令集架构（国产自主，国家平台 std.samr.gov.cn）",
        "[国际] RISC-V ISA Specification（RISC-V International）",
        "[国际] MIPS Architecture for Programmers（MIPS32/MIPS64 Release 6）",
    ],
    "hardware": [
        "[国标] 中国能效标识（GB 24850 等，国家平台 std.samr.gov.cn）",
        "[国际] Linux kernel Documentation（kernel.org，硬件子系统权威源码文档）",
    ],
    "network": [
        "[国际] RFC 4941 / RFC 8200（IPv6 隐私扩展与协议规范，IETF）",
    ],
}

# 关键词 → 细化标准（命中则优先采用，覆盖分类默认）
KEYWORD_STANDARDS = (
    ("trim", ["[国际] ATA TRIM（DATA SET MANAGEMENT，T13）"]),
    ("ssd", ["[国际] ATA TRIM（DATA SET MANAGEMENT，T13）"]),
    ("smart", ["[国际] T13 / ATA8-ACS（S.M.A.R.T. 磁盘自检）"]),
    ("disk", ["[国际] T13 / ATA8-ACS（S.M.A.R.T.）"]),
    ("sleep", ["[国际] ACPI Specification（UEFI Forum，S3/S4 睡眠态）"]),
    ("hibernate", ["[国际] ACPI Specification（UEFI Forum，S4 休眠）"]),
    ("power", ["[国标] 中国能效标识（GB 24850 等，国家平台 std.samr.gov.cn）",
               "[国际] ACPI Specification（UEFI Forum，P-state / C-state）"]),
    ("dns", ["[国际] RFC 1035（DNS 域名系统）",
             "[国际] RFC 7858 / RFC 8484（DoT / DoH）"]),
    ("font", ["[国标] GB 18030《信息技术 中文编码字符集》",
              "[国际] Unicode 18.0.0 / ISO-IEC 10646"]),
    ("unicode", ["[国标] GB 18030《信息技术 中文编码字符集》",
                 "[国际] UAX #15（Unicode 规范化 NFC）"]),
    ("orca", ["[国际] AT-SPI2（org.a11y.Bus，GNOME at-spi2-core）",
              "[国标] GB/T 37668《信息技术 无障碍 通用设计规范》"]),
    ("atspi", ["[国际] AT-SPI2（org.a11y.Bus 辅助技术总线）"]),
    ("a11y", ["[国标] GB/T 37668《信息技术 无障碍 通用设计规范》",
              "[国际] W3C WCAG 2.2"]),
    ("loongarch", ["[国标] 龙芯 LoongArch 指令集架构（国产自主指令集）"]),
    ("mips", ["[国际] MIPS Architecture for Programmers（MIPS32/MIPS64 Release 6）"]),
    ("riscv", ["[国际] RISC-V ISA Specification（RISC-V International）"]),
    ("open_hardware", ["[国际] OSHWA 开源硬件定义 + CERN OHL v2 许可",
                       "[地区] DIN SPEC 3105（德国：开放硬件要求）"]),
    ("go", ["[国际] Go 官方构建规范（GOOS/GOARCH 交叉编译矩阵）"]),
    ("zfs", ["[国际] OpenZFS（ZFS On-Disk Specification）"]),
    ("cpufreq", ["[国际] Linux kernel Documentation/admin-guide/pm/cpufreq.rst（CPUFreq 调频）"]),
    ("governor", ["[国际] Linux kernel Documentation/admin-guide/pm/cpufreq.rst（调频 governor）"]),
    ("cpuidle", ["[国际] Linux kernel Documentation/admin-guide/pm/cpuidle.rst（CPU idle 状态）"]),
    ("intel_pstate", ["[国际] Linux kernel Documentation/admin-guide/pm/intel_pstate.rst（Intel P-State）"]),
    ("thermal", ["[国际] Linux kernel Documentation/admin-guide/thermal/sysfs-api.rst（温控 sysfs）"]),
    ("thp", ["[国际] Linux kernel Documentation/admin-guide/mm/transhuge.rst（透明大页）"]),
    ("transparent_hugepage", ["[国际] Linux kernel Documentation/admin-guide/mm/transhuge.rst（透明大页）"]),
    ("zswap", ["[国际] Linux kernel Documentation/mm/zswap.rst（压缩交换缓存）"]),
    ("zram", ["[国际] Linux kernel Documentation/admin-guide/blockdev/zram.rst（内存压缩块设备）"]),
    ("nvme", ["[国际] Linux kernel Documentation/nvme/index.rst（NVMe 子系统）"]),
    ("io_sched", ["[国际] Linux kernel Documentation/block/（I/O 调度器 BFQ / mq-deadline / kyber）"]),
    ("epb", ["[国际] Intel P-State / x86 能效（energy_perf_bias，kernel admin-guide/pm/intel_pstate.rst）"]),
    ("numa", ["[国际] Linux kernel Documentation/admin-guide/mm/numa_memory_policy.rst（NUMA 平衡）"]),
    ("watchdog", ["[国际] Linux kernel Documentation/watchdog/watchdog-api.rst（硬件看门狗）"]),
    ("swappiness", ["[国际] Linux kernel Documentation/admin-guide/sysctl/vm.rst（vm.swappiness）"]),
    ("scheduler", ["[国际] Linux kernel Documentation/scheduler/sched-energy.rst（能耗感知调度 EAS）"]),
    ("kernel", ["[国际] Linux kernel Documentation（kernel.org，硬件子系统权威源码文档）"]),
    ("scheduler", ["[国际] Linux kernel Documentation/scheduler/sched-design-CFS.rst（CFS 调度器）"]),
    ("cgroup", ["[国际] Linux kernel Documentation/admin-guide/cgroup-v2.rst（cgroups v2 统一层级）"]),
    ("oom", ["[国际] Linux kernel Documentation/mm/oom_kill.rst（OOM 防护与 oom_score_adj）"]),
    ("psi", ["[国际] Linux kernel Documentation/accounting/psi.rst（资源压力失忆 PSI）"]),
    ("tcp", ["[国际] Linux kernel Documentation/networking/ip-sysctl.rst（TCP 协议栈参数）"]),
    ("bbr", ["[国际] Linux kernel Documentation/networking/ip-sysctl.rst（拥塞控制含 BBR）"]),
    ("net_core", ["[国际] Linux kernel Documentation/networking/ip-sysctl.rst（net.core 参数）"]),
    ("rps", ["[国际] Linux kernel Documentation/networking/scaling.rst（RPS / RFS 接收侧缩放）"]),
    # 网络栈深度调优（v0.5.9）：每个工具按自身协议与接口引用官方文档，绝不套用协议层 sysctl 写法
    ("ethtool", ["[国际] Linux kernel ethtool-netlink 文档（网卡卸载 GRO/GSO/TSO/LRO / -K/-C 写接口）",
                 "[官方] ethtool(8) man（man7.org）"]),
    ("offload", ["[国际] Linux kernel ethtool-netlink 文档（网卡分段/校验和卸载 GRO/GSO/TSO）"]),
    ("coalesce", ["[国际] Linux kernel ethtool 文档（中断聚合 rx-usecs/tx-usecs，-C 写接口）"]),
    ("xps", ["[国际] Linux kernel Documentation/networking/scaling.rst（XPS 发送侧缩放）"]),
    ("scaling", ["[国际] Linux kernel Documentation/networking/scaling.rst（RPS / RFS / XPS 接收发送侧缩放）"]),
    ("smp_affinity", ["[国际] Linux kernel Documentation/core-api/irq/irq-affinity.rst（IRQ 亲和）"]),
    ("irq", ["[国际] Linux kernel Documentation/core-api/irq/irq-affinity.rst（网卡中断亲和）"]),
    ("fq_codel", ["[国际] RFC 8290（FQ-CoDel 主动队列管理）",
                  "[社区] bufferbloat.net Codel/CAKE 项目（tc qdisc 写接口）"]),
    ("tc", ["[国际] Linux kernel tc(8) / rtnetlink(TC) qdisc 文档（fq_codel/cake 抗缓冲膨胀）"]),
    ("bufferbloat", ["[社区] bufferbloat.net Codel/CAKE 项目（tc qdisc 写接口，主动队列管理）"]),
    ("conntrack", ["[官方] Netfilter nf_conntrack 文档（/proc/sys/net/netfilter 连接跟踪表）",
                   "[官方] conntrack(8) man（man7.org）"]),
    ("nf_conntrack", ["[官方] Netfilter nf_conntrack 文档（nf_conntrack_max / _count 连接跟踪表）"]),
    ("netdev_backlog", ["[国际] Linux kernel Documentation/networking/ip-sysctl.rst（net.core.netdev_max_backlog）"]),
    ("ebpf", ["[官方] Linux kernel BPF & XDP 文档（docs.kernel.org/bpf）",
              "[官方] bpftool 文档（bpftool.readthedocs.io，prog/map/net list 只读检视）"]),
    ("bpf", ["[官方] Linux kernel BPF & XDP 文档（docs.kernel.org/bpf，bpf() 系统调用 + libbpf）"]),
    ("xdp", ["[官方] Linux kernel Documentation/networking/af_xdp.rst（XDP 驱动层数据面加速）"]),
    ("iproute2", ["[国际] iproute2 文档（wiki.linuxfoundation.org/networking/iproute2，netlink/rtnetlink/sock_diag）"]),
    ("ss", ["[国际] iproute2 ss(8) man（sock_diag 套接字诊断，优于 netstat）"]),
    ("gnome", ["[国际] GNOME dconf 文档（developer.gnome.org，dconf/gsettings 接口）",
               "[国际] GNOME HIG（人机界面指南）"]),
    ("kde", ["[国际] KDE KConfig 文档（develop.kde.org，kwriteconfig5 接口）",
             "[国际] KDE HIG（人机界面指南）"]),
    ("xfce", ["[国际] XFCE xfconf 文档（docs.xfce.org，xfconf-query 接口）"]),
    ("dconf", ["[国际] GNOME dconf 文档（developer.gnome.org，dconf reset 接口）"]),
    ("xfconf", ["[国际] XFCE xfconf 文档（docs.xfce.org，xfconf-query 接口）"]),
    ("freedesktop", ["[国际] freedesktop.org XDG Base Directory 规范（~/.cache / ~/.config）",
                     "[国际] freedesktop.org 图标主题规范（icon-theme-spec）"]),
    ("thumbnail", ["[国际] freedesktop.org 缩略图管理规范（~/.cache/thumbnails）"]),
    # 其他系统软件：按各自协议与接口引用其官方文档（触类旁通内核/桌面模式）
    ("systemd", ["[国际] systemd 文档（systemd.unit(5) / systemd-analyze(1) /"
                 " systemd-journald.service(8) / org.freedesktop.systemd1）"]),
    ("journal", ["[国际] systemd 文档（systemd-journald.service(8)，journalctl --vacuum 回收接口）"]),
    ("dbus", ["[国际] D-Bus Specification（freedesktop.org：org.freedesktop.DBus"
              " / .Introspectable / .Properties）"]),
    ("networkmanager", ["[国际] NetworkManager 文档（nmcli(1) / nm-settings(5)"
                        " / org.freedesktop.NetworkManager）"]),
    ("nmcli", ["[国际] NetworkManager 文档（nmcli(1) / nm-settings(5)）"]),
    ("pipewire", ["[国际] PipeWire 文档（docs.pipewire.org：pipewire.conf(5) / SPA 协议"
                  " / org.pipewire）"]),
    ("bluez", ["[国际] BlueZ 文档（bluetoothd(8) / org.bluez.Adapter1(5)）"]),
    ("bluetooth", ["[国际] BlueZ 文档（bluetoothctl(1) / org.bluez）"]),
    ("udev", ["[国际] udev 文档（udev(7) 规则语法 / udevadm(8) / hwdb(7)）"]),
    ("polkit", ["[国际] polkit 文档（polkit(8) / pkaction(1) / org.freedesktop.PolicyKit1(5)）"]),
    ("wayland", ["[国际] Wayland 协议规范（wayland.xml 核心 / xdg-shell 扩展）"]),
    # 鸿蒙（HarmonyOS / OpenHarmony）与 uni-app 鸿蒙端：按自身协议与接口
    ("harmony", ["[国际] 鸿蒙文档（Stage 模型 / SystemCapability / HiLog / hdc / HAP，"
                 "HarmonyOS 开发者文档）"]),
    ("harmonyos", ["[国际] HarmonyOS 开发者指南与 API 参考（developer.huawei.com）"]),
    ("openharmony", ["[国际] OpenHarmony 文档（开源鸿蒙，docs.openharmony.cn）"]),
    ("arkts", ["[国际] 鸿蒙 ArkTS / ArkUI 文档（声明式开发范式与状态管理）"]),
    ("arkui", ["[国际] 鸿蒙 ArkUI 文档（声明式 UI 与组件体系）"]),
    ("hap", ["[国际] 鸿蒙应用包文档（HAP / HSP / HAR 结构 + ohpm / Hvigor 构建）"]),
    ("hdc", ["[国际] 鸿蒙 hdc 工具文档（HarmonyOS Device Connector）"]),
    ("hilog", ["[国际] 鸿蒙 HiLog 文档（域 / 标签 / 级别 + hilogtool 解析）"]),
    ("syscap", ["[国际] 鸿蒙 SystemCapability 文档（@ohos.* 分层 API + canIUse()）"]),
    ("ability", ["[国际] 鸿蒙 Stage 应用模型文档（UIAbility / ExtensionAbility / Want）"]),
    ("ohos", ["[国际] 鸿蒙 @ohos.* API 参考（SystemCapability 能力分层）"]),
    # uni-app 各小程序端：按各端自身 API 规范
    ("weixin", ["[国际] 微信小程序文档（wx.* API / 双线程架构 / app.json）"]),
    ("alipay", ["[国际] 支付宝小程序文档（my.* API / 域名白名单 / getAuthCode）"]),
    ("baidu", ["[国际] 百度智能小程序文档（swan.* API）"]),
    ("douyin", ["[国际] 抖音小程序文档（tt.* API）"]),
    ("toutiao", ["[国际] 抖音小程序文档（tt.* API，uni-app 平台节点 mp-toutiao）"]),
    ("kuaishou", ["[国际] 快手小程序文档（ks.* API）"]),
    ("miniprogram", ["[国际] 小程序平台规范（各端 wx.*/my.*/swan.*/tt.*/qq.*/ks.* API）"]),
    ("mp_", ["[国际] uni-app 跨平台文档（条件编译 #ifdef MP-XXX + manifest mp-* 节点）"]),
    # 包管理器：各自按自身协议与接口（deb/RPM/.apk/.pkg.tar.zst/Formula/清单/PEP/Registry/OSTree）
    ("apt", ["[国际] Debian Policy Manual（deb 控制字段 / 包关系）+ apt-get(8)"]),
    ("dpkg", ["[国际] Debian Policy Manual（deb 包格式 / dpkg 数据库）+ dpkg(1)"]),
    ("autoremove", ["[国际] apt-mark(8)（auto/manual 标记为 autoremove 判定依据）"]),
    ("rpm", ["[国际] rpm.org 文档（RPM 包格式 / rpmdb）+ rpm(8) / dnf(8)"]),
    ("dnf", ["[国际] dnf(8) / dnf.conf(5)（clean all、keepcache、repoquery）"]),
    ("yum", ["[国际] yum(8)（旧版 RPM 系仓库缓存接口 clean all）"]),
    ("zypper", ["[国际] zypper(8)（openSUSE libzypp 同层包管理接口）"]),
    ("apk", ["[国际] apk-tools 文档（Alpine：.apk 分段格式 / APKINDEX / apk(8)）"]),
    ("pacman", ["[国际] Arch Wiki pacman（.pkg.tar.zst / *.db / paccache(8)）"]),
    ("paccache", ["[国际] paccache(8)（pacman-contrib：按保留版本清理缓存）"]),
    ("brew", ["[国际] Homebrew 文档（docs.brew.sh：Formula/Cask DSL / brew(1) cleanup）"]),
    ("homebrew", ["[国际] Homebrew 文档（docs.brew.sh：bottle 预编译包 / tap 机制）"]),
    ("winget", ["[国际] Microsoft WinGet 文档（YAML 清单 schema / 源 REST 接口）"]),
    ("pip", ["[国际] PyPA pip 文档 + PEP 503（简单索引）/ PEP 427（wheel 格式）"]),
    ("npm", ["[国际] npm 文档（Registry HTTP API / _cacache / npm-cache(1) verify）"]),
    ("snap", ["[国际] snapd REST API 文档（/v2/snaps + refresh.retain 保留版本）"]),
    ("flatpak", ["[国际] Flatpak 文档（OSTree refs/commit / uninstall --unused）"]),
    ("ostree", ["[国际] Flatpak 文档（OSTree 仓库去重与 runtime 共享）"]),
    # 容器运行时：各自按自身协议与接口（OCI/Docker/Podman/containerd/BuildKit/OCI/LXC/CRI）
    ("docker", ["[国际] Docker 文档（docker system prune / system df + OCI runtime-spec + Engine API）"]),
    ("podman", ["[国际] Podman 文档（podman-system-prune / image-prune + rootless OCI crun）"]),
    ("containerd", ["[国际] containerd.io 文档 + nerdctl command-reference（content store / snapshotter / CRI）"]),
    ("nerdctl", ["[国际] nerdctl command-reference（nerdctl system prune 等 docker 语义接口）"]),
    ("buildkit", ["[国际] moby/buildkit 文档（LLB 构建图 + 内容寻址 build cache + docker builder prune）"]),
    ("buildx", ["[国际] Docker buildx 文档（多驱动构建缓存 + docker buildx prune）"]),
    ("oci", ["[国际] OCI image-spec / runtime-spec（manifest/config/layer + digest 内容寻址）"]),
    ("skopeo", ["[国际] OCI 文档（skopeo 镜像复制/检查 + umoci 解包 / runc 启动）"]),
    ("lxc", ["[国际] linuxcontainers.org lxc / lxd（liblxc + LXD REST/1.0 + 存储池）"]),
    ("lxd", ["[国际] LXD 文档（lxc image delete / lxc storage volume rm + 存储池后端）"]),
    ("crictl", ["[国际] Kubernetes crictl 文档（CRI gRPC RuntimeService/ImageService + Pod 沙箱）"]),
    ("cri", ["[国际] Kubernetes CRI 文档（kubelet 与 containerd/CRI-O 之间的标准接口）"]),
    # 存储与文件系统：各自按自身协议与接口（ext4/Btrfs/XFS/ZFS/LVM/fstrim/SMART/swap）
    ("ext4", ["[国际] ext4 文档（e2fsck -fn 只读校验 / e4defrag 在线整理 + extent/jbd2）"]),
    ("btrfs", ["[国际] Btrfs 文档（btrfs balance/scrub/defrag + COW B-tree 子卷/快照/qgroup）"]),
    ("xfs", ["[国际] XFS 文档（xfs_db -r -c frag 只读碎片率 / xfs_fsr 整理 + AG 分配组 B+tree）"]),
    ("zfs", ["[国际] OpenZFS 文档（zpool scrub/trim + zfs destroy + DMU/SPA 校验和）"]),
    ("lvm", ["[国际] LVM 文档（lvreduce/pvmove/thin_check + device-mapper + 精简置备）"]),
    ("fstrim", ["[国际] util-linux fstrim 文档（FITRIM ioctl + ATA TRIM/SCSI UNMAP/NVMe DSM）"]),
    ("smart", ["[国际] smartmontools smartctl 文档（smartctl -H/-A/-t + ATA/SCSI/NVMe SMART 属性）"]),
    ("swap", ["[国际] util-linux swapon 文档（swapon/swapoff/mkswap + swap 签名页 SWAPSPACE2）"]),
    ("e4defrag", ["[国际] ext4 文档（e4defrag 仅整理 extent 文件）"]),
    ("scrub", ["[国际] Btrfs/ZFS 文档（scrub 按 checksum 后台校验并修复副本）"]),
    ("balance", ["[国际] Btrfs 文档（btrfs balance 按 usage 回收未用 chunk）"]),
    ("defrag", ["[国际] ext4/Btrfs/XFS 文档（e4defrag/xfs_fsr/btrfs defrag 在线碎片整理）"]),
    ("zpool", ["[国际] OpenZFS 文档（zpool list/status/scrub/trim 管理存储池）"]),
    ("xfs_fsr", ["[国际] XFS 文档（xfs_fsr 在线碎片整理）"]),
    ("trim", ["[国际] fstrim/ZFS 文档（TRIM/UNMAP 回收 SSD 空闲块）"]),
    ("smartctl", ["[国际] smartmontools smartctl 文档（SMART 健康与属性读取）"]),
    # macOS 原生接口：各自按自身协议与接口（launchd/sysctl/defaults/softwareupdate/diskutil/pmset/tmutil/spctl/networksetup）
    ("launchd", ["[国际] Apple TN2083 Daemons and Agents（launchd 域层级 + plist 作业 + launchctl 接口）",
                 "[官方] launchd.plist(5) / launchctl(1) man"]),
    ("launchctl", ["[国际] Apple TN2083（launchctl bootstrap/bootout/list/disable 接口）"]),
    ("sysctl_macos", ["[国际] XNU sysctl 文档（sysctlbyname 内核运行时参数 kern./hw./net.）",
                      "[官方] sysctl(8) man（Darwin）"]),
    ("defaults", ["[国际] Apple CFPreferences 文档（defaults 读写为 ~/Library/Preferences plist 后端）",
                  "[官方] defaults(1) man"]),
    ("softwareupdate", ["[国际] Apple 软件更新文档（softwareupdate -l 列可用更新 + SUS catalog）"]),
    ("diskutil", ["[国际] Apple APFS 参考（diskutil apfs list/listSnapshots/verifyVolume 接口）",
                  "[官方] diskutil(8) man"]),
    ("apfs", ["[国际] Apple 文件系统 APFS 规范（容器/宗卷/快照机制）"]),
    ("pmset", ["[国际] Apple IOPMlib 电源管理文档（pmset -g 读休眠/节能配置）",
               "[官方] pmset(1) man"]),
    ("tmutil", ["[国际] Apple Time Machine 文档（tmutil listlocalsnapshots/deletelocalsnapshots 本地快照）"]),
    ("spctl", ["[国际] Apple Gatekeeper 文档（spctl --status/--assess 代码签名与公证评估）"]),
    ("gatekeeper", ["[国际] Apple Gatekeeper 文档（应用准入守门员，基于代码签名 + 公证）"]),
    ("networksetup", ["[国际] Apple System Configuration 文档（networksetup -listallnetworkservices/-getdnsservers 网络配置）"]),
    ("sw_vers", ["[官方] sw_vers(1) man（Apple 官方版本命令）"]),
    # macOS 官方写接口（v0.5.12 深度调优）：只往安全方向写，各自用官方子命令
    ("hibernatemode", ["[国际] Apple IOPMlib 电源管理文档（pmset -a hibernatemode 0/3/25 语义）",
                       "[官方] pmset(1) man"]),
    ("standbydelay", ["[国际] Apple IOPMlib 电源管理文档（standby / standbydelayhigh / standbydelaylow）",
                      "[官方] pmset(1) man"]),
    ("maxfiles", ["[官方] sysctl(8) man（kern.maxfiles / kern.maxfilesperproc 文件描述符上限，Darwin 与 BSD 同名 MIB）"]),
    ("setdnsservers", ["[国际] Apple System Configuration 文档（networksetup -setdnsservers <service> empty 交回 DHCP）",
                       "[国际] RFC 2132（DHCP 选项 6：DNS 服务器下发）"]),
    ("thinlocalsnapshots", ["[国际] Apple 文件系统 APFS 规范（本地快照 + 空间共享）",
                            "[官方] tmutil(8) man（thinlocalsnapshots 官方瘦身接口）"]),
    ("autohide", ["[国际] Apple CFPreferences 文档（defaults write com.apple.dock autohide，plist 后端）",
                  "[官方] defaults(1) man"]),
    ("masterenable", ["[国际] Apple Gatekeeper 文档（spctl --master-enable 启用准入评估）",
                      "[官方] spctl(8) man"]),
    ("verifyvolume", ["[国际] Apple APFS 参考（diskutil verifyVolume 一致性校验，只校验不修复）",
                      "[官方] diskutil(8) man"]),
    # BSD 原生接口：各自按自身协议与接口（pkg/rc.conf/sysctl/pf/zfs/periodic/bsdconfig/ports）
    ("pkg", ["[国际] FreeBSD Handbook: pkg（SQLite 本地库 + pkg+https 仓库 + autoremove 依赖图）",
             "[官方] pkg(8) man"]),
    ("rc_conf", ["[国际] FreeBSD Handbook: 配置（rc.conf xxx_enable 变量 + rcorder 依赖图）",
                 "[官方] rc.conf(5) / service(8) man"]),
    ("rcorder", ["[国际] FreeBSD rc(8)（PROVIDE/REQUIRE/KEYWORD 解析启动顺序）"]),
    ("sysctl_bsd", ["[国际] BSD sysctl 文档（kern./vm./hw./net. 内核运行时参数 + /etc/sysctl.conf 持久化）"]),
    ("pf", ["[国际] OpenBSD FAQ: Packet Filter（pf.conf 规则集/锚点/表 + pfctl -s 只读统计）",
            "[官方] pf.conf(5) / pfctl(8) man"]),
    ("zfs_bsd", ["[国际] OpenZFS 文档（zpool list/status/scrub/trim + zfs list/destroy 管理存储池）"]),
    ("periodic", ["[国际] FreeBSD Handbook: 周期性任务配置（/etc/periodic/{daily,weekly,monthly,security} 脚本）",
                  "[官方] periodic(8) man"]),
    ("bsdconfig", ["[国际] FreeBSD bsdconfig 文档（dialog 文本配置向导：network/timezone/services/security）"]),
    ("ports", ["[国际] FreeBSD Handbook: Ports Collection（/usr/ports Makefile + distinfo + distfiles 缓存）",
               "[官方] ports(7) / portsnap(8) man"]),
    ("pkgin", ["[国际] NetBSD pkgin 文档（pkgin clean/autoremove 包管理接口）"]),
    ("pkg_add", ["[国际] OpenBSD pkg_add/pkg_delete 文档（pkg_info -a 查看已装 / pkg_delete 删除）"]),
    # BSD 官方写接口（v0.5.12 深度调优）：sysctl -w / zpool set|scrub / pfctl -e -f / periodic
    ("rfc1323", ["[国际] RFC 7323（TCP 高性能扩展：窗口缩放 + 时间戳 + PAWS）",
                 "[官方] tcp(4) / sysctl(8) man（net.inet.tcp.rfc1323 MIB）"]),
    ("recvspace", ["[官方] tcp(4) / sysctl(8) man（net.inet.tcp.recvspace / sendspace 收发缓冲）"]),
    ("autotrim", ["[国际] OpenZFS（zpool(8) autotrim 属性：后台自动回收 SSD 空闲块）"]),
    ("scrub", ["[国际] OpenZFS（zpool(8) scrub：遍历校验校验和并在有冗余时自愈）"]),
    ("arcmax", ["[国际] OpenZFS（zfs(4) vfs.zfs.arc_max：ARC 缓存上限可调参数）"]),
    ("periodic_run", ["[国际] FreeBSD Handbook: 周期性任务配置（/etc/periodic/{daily,weekly,monthly,security}）",
                      "[官方] periodic(8) man"]),
    # Windows 原生接口（v0.5.13 文档跟踪 + 深度调优）：各自按自身协议与接口
    ("win32", ["[官方] Windows Win32 API 参考（kernel32 / shell32 / advapi32）"]),
    ("winreg", ["[官方] Windows Registry 参考（hive / 键 / 值类型 REG_DWORD 等）",
                "[官方] Python winreg 模块文档"]),
    ("wmi", ["[国际] DMTF CIM Schema（通用信息模型）",
             "[官方] WMI SDK / Get-CimInstance 参考"]),
    ("registry_report", ["[官方] Windows Registry 参考（HKLM/HKCU 查询，只读）"]),
    ("powercfg", ["[官方] powercfg command-line options（电源计划 GUID + /change + /h /type）",
                  "[国际] ACPI Specification（UEFI Forum，S0/S3/S4 电源态）"]),
    ("dism", ["[官方] DISM Image Management Command-Line Options（servicing stack + CBS 组件存储）"]),
    ("sfc", ["[官方] sfc 命令参考 + Windows Resource Protection（WRP）"]),
    ("storage_sense", ["[官方] 用存储感知管理驱动器空间（StoragePolicy 注册表策略 + MDM）"]),
    ("delivery_opt", ["[官方] Delivery Optimization 文档（P2P 缓存 + 下载模式策略）"]),
    ("fsutil", ["[官方] fsutil behavior（NTFS 文件系统行为设置）",
                "[国际] NTFS 文件系统规范（$MFT 元数据与时间戳属性）"]),
    ("8dot3", ["[官方] fsutil 8dot3name / behavior disable8dot3（NTFS 短名生成）"]),
    ("autotuning", ["[国际] RFC 7323（TCP 高性能扩展：窗口缩放 + 时间戳 + PAWS）",
                    "[官方] netsh int tcp set global（autotuninglevel）"]),
    ("rss", ["[官方] netsh int tcp set global（rss 接收侧缩放，多核分摊收包）"]),
    ("ecn", ["[国际] RFC 3168（显式拥塞通知 ECN）",
             "[官方] netsh int tcp set global（ecncapability）"]),
    ("advfirewall", ["[官方] netsh advfirewall set allprofiles state（Windows 防火墙三档配置）"]),
    ("dism_cleanup", ["[国际] Windows servicing stack / CBS（微软组件服务规范）"]),
    # Unix（System V）原生接口（v0.5.14 文档跟踪 + 深度调优）：各自按自身协议与接口
    ("ips", ["[官方] pkg(1) / pkg(5)（IPS 镜像打包系统：FMRI + image + publisher 目录）",
             "[国际] Oracle Solaris 11.4 文档：Adding and Updating Software Packages"]),
    ("fmri", ["[官方] smf(7)（FMRI svc:/<category>/<name>:<instance> 命名与解析）"]),
    ("svcs", ["[官方] svcs(1) / svc.startd(8)（SMF 服务状态与依赖，只读）"]),
    ("svcadm", ["[官方] svcadm(8)（SMF enable/disable/clear/refresh 官方写接口）",
                "[国际] smf(7)（服务状态机：online/degraded/maintenance/disabled）"]),
    ("svccfg", ["[官方] svccfg(8)（SMF 配置库：XML manifest + 属性导出/导入）"]),
    ("logadm", ["[官方] logadm(8) / logadm.conf(5)（Solaris 官方日志轮转：-V 校验 / -r 轮转）"]),
    ("kstat", ["[官方] kstat(1) / kstat(3KSTAT)（module:instance:name:class 内核统计，只读）"]),
    ("zoneadm", ["[官方] zones(7) / zoneadm(8)（Solaris Zones 生命周期与品牌区）"]),
    ("zonecfg", ["[官方] zonecfg(8)（非全局区配置：zonepath/net/capped-* 资源上限）"]),
    ("fmadm", ["[官方] fmadm(8) / fmdump(8)（FMA 故障管理：faulty/repair/acquit）"]),
    ("fmdump", ["[官方] fmdump(8)（FMA 故障与 ereport 历史回溯，只读）"]),
    ("dladm", ["[官方] dladm(8)（Crossbow 数据链路层：VNIC/aggr/etherstub，取代 ifconfig）"]),
    ("ipadm", ["[官方] ipadm(8)（Crossbow IP 层：show-prop/set-prop，取代 ndd 管 TCP 可调项）"]),
    ("atime", ["[国际] OpenZFS（zfs(8) atime 属性：关访问时间回写以减写放大）"]),
    ("compression", ["[国际] OpenZFS（zfs(8) compression 属性：lz4/gzip/zstd 压缩）"]),
    ("etc_release", ["[官方] release(5) / uname(1)（System V 用 /etc/release 而非 /etc/os-release）"]),
    # Android 原生接口（v0.5.15 文档跟踪 + 深度调优）：各自按自身协议与接口（经官方 ADB）
    ("adb", ["[官方] adb（Android Debug Bridge：client-server 调试桥，PC↔device 标准系统接口）",
             "[国际] AOSP system/core：adbd 与 adb protocol"]),
    ("settings_provider", ["[官方] settings 命令（SettingsProvider global/system/secure 三表）",
                           "[国际] AOSP frameworks/base：android.provider.Settings"]),
    ("pm", ["[官方] pm trim-caches / pm clear（PackageManager 缓存与数据分离，只清缓存不删数据）",
            "[国际] AOSP frameworks/base：PackageManagerService"]),
    ("am", ["[官方] am kill-all / force-stop（ActivityManager 杀后台进程，只后台）",
            "[国际] AOSP frameworks/base：ActivityManagerService"]),
    ("dumpsys", ["[官方] dumpsys batterystats/meminfo/netstats --reset（服务状态快照与统计复位）",
                 "[国际] AOSP frameworks/base：BatteryStats/NetworkStatsService"]),
    ("getprop", ["[官方] getprop（系统属性：ro.build.* 即 Android 的发行版标识）",
                 "[国际] AOSP system/core init 与 property_service"]),
    ("svc", ["[官方] svc wifi enable（WifiManager 官方开关，只启用不关断）",
             "[国际] AOSP frameworks/base：WifiManager/NfcManager"]),
    ("wm", ["[官方] wm size reset / wm density reset（WindowManager 显示恢复默认）",
            "[国际] AOSP frameworks/base：WindowManager"]),
    ("logcat", ["[官方] logcat -c（logd 环形缓冲清空，只清日志）",
                "[国际] AOSP system/core：logcat / logd"]),
    # —— v0.5.16：iOS（libimobiledevice）关键词，按各自协议与接口 —— #
    ("ios", ["[官方] libimobiledevice 套件（usbmuxd + lockdown 通道，PC 端不发越权指令）",
             "[国际] Apple lockdown 协议（com.apple.mobile.lockdown）逆向参考实现"]),
    ("ideviceinfo", ["[官方] ideviceinfo / ideviceinfo -q（lockdown 设备值只读）",
                     "[国际] Apple lockdown 服务（DeviceName/ProductVersion 等）"]),
    ("ideviceinstaller", ["[官方] ideviceinstaller -a（installation_proxy 归档，保留数据、可逆）",
                          "[国际] Apple com.apple.mobile.installation_proxy（归档≠卸载 -U）"]),
    ("idevicebackup2", ["[官方] idevicebackup2 backup（mobilebackup2 单向备份到本地，不 restore）",
                        "[国际] Apple com.apple.mobilebackup2（增量备份服务）"]),
    ("idevicecrashreport", ["[官方] idevicecrashreport -e（crashreportcopymobile 拷贝+删日志，仅日志）",
                            "[国际] Apple com.apple.crashreportcopymobile"]),
    ("idevicedate", ["[官方] idevicedate -s（设备时间同步为主机时间，可逆）",
                     "[国际] Apple lockdown 时间同步接口"]),
    ("idevicesetlocation", ["[官方] idevicesetlocation clear（清除模拟定位，恢复真实 GPS）",
                            "[国际] Apple 模拟定位调试接口"]),
    ("idevicename", ["[官方] idevicename（设备名归一化，设置中可随时改回）",
                     "[国际] Apple lockdown DeviceName 写接口"]),
    ("idevicediagnostics", ["[官方] idevicediagnostics restart（优雅重启释放内存，无数据丢失）",
                            "[国际] Apple com.apple.mobile.diagnostics（restart/sleep）"]),
    ("ideviceimagemounter", ["[官方] ideviceimagemounter（mobile_image_mounter 挂开发者镜像，可逆）",
                             "[国际] Apple com.apple.mobile.mobile_image_mounter"]),
    ("idevice_id", ["[官方] idevice_id -l（usbmuxd 枚举在线设备 UDID）",
                    "[国际] Apple usbmuxd 多路复用通道"]),
    ("idevicepair", ["[官方] idevicepair list（lockdown 配对状态只读校验）",
                     "[国际] Apple lockdown Pair 服务"]),
    # --- v0.5.18 链接协议 / 自组网 / 隐私验证 / 同人资源共享 / 多系统无障碍 ---
    ("netlink", ["[国际] IETF RFC 9293（TCP）/ RFC 768（UDP）",
                 "[国际] IEEE 802.15.1（蓝牙）/ IEEE 802.15.4（低速率无线个域网）"]),
    ("mesh", ["[国际] IETF RFC 1112（IP 组播）/ RFC 768（UDP 发现信标）",
              "[国际] IETF RFC 9293（TCP 可靠通道）"]),
    ("rfcomm", ["[国际] Bluetooth SIG RFCOMM v1.2（基于 ETSI TS 07.10 串口仿真）"]),
    ("bluetooth", ["[国际] IEEE 802.15.1（蓝牙）/ Bluetooth Core Specification"]),
    ("ble", ["[国际] Bluetooth SIG GATT/ATT（低功耗蓝牙属性协议）"]),
    ("802.15.4", ["[国际] IEEE 802.15.4（低速率无线个域网 PHY/MAC，Zigbee/Thread 底层）"]),
    ("serial", ["[国际] EIA/TIA-232（RS-232 串口）/ ETSI TS 07.10 多路复用"]),
    ("tcp", ["[国际] IETF RFC 9293（TCP 规范）/ RFC 7323（高性能扩展）"]),
    ("udp", ["[国际] IETF RFC 768（UDP 规范）"]),
    ("privacy_verify", ["[国标] GB/T 35273《个人信息安全规范》（数据最小化、去标识化）",
                        "[国际] IETF RFC 8018（PBKDF2 口令派生）"]),
    ("pii", ["[国标] GB/T 35273《个人信息安全规范》（个人信息最小化处理）",
             "[地区] GDPR Art.5（数据最小化，欧盟）"]),
    ("reshare", ["[国标] GB/T 35273《个人信息安全规范》（目的限定、最小共享）",
                 "[国际] ISO/IEC 27001（访问控制与资产保护）"]),
    ("npu", ["[国际] IEEE 802.15.4 之外：AI 加速器接口随厂商（本工具仅只读探测）"]),
    ("tpu", ["[国际] Edge TPU / 张量加速器（本工具仅只读探测设备节点）"]),
    ("narrator", ["[官方] Microsoft UI Automation（讲述人 Narrator）",
                  "[国标] GB/T 37668《信息技术 无障碍 通用设计规范》"]),
    ("uia", ["[官方] Microsoft UI Automation / MSAA（Windows 无障碍接口）"]),
    ("voiceover", ["[官方] Apple NSAccessibility（AX API，macOS/iOS VoiceOver）"]),
    ("talkback", ["[官方] Android AccessibilityService（TalkBack）",
                   "[国际] Google Android 无障碍服务框架"]),
    # v0.5.19 第三方导入（网络互联互通 / 硬件优化 / 开源下载 / 许可证）
    ("interop", ["[仓库] p2wlan(MIT)/dae(AGPL-3.0)/gfw-pac(Apache-2.0)/v2rayN(GPL-3.0)",
                 "[国标] GB/T 35273《个人信息安全规范》（目的限定、最小共享）"]),
    ("p2wlan", ["[仓库] yhan-sun/p2wlan（P2P 虚拟局域网，MIT）",
                "[国际] NAT 穿透(STUN/TURN)/IPv6 直连/房间组网"]),
    ("dae", ["[仓库] daeuniverse/dae（eBPF 透明代理，AGPL-3.0）",
             "[国际] Linux eBPF(kernel>=5.8) 透明代理与分流"]),
    ("gfw-pac", ["[仓库] zhiyi7/gfw-pac（PAC 生成器，Apache-2.0）",
                 "[国际] PAC(Proxy Auto-Config) 直连/代理域名分流"]),
    ("v2rayn", ["[仓库] 2dust/v2rayN（Xray/sing-box 客户端，GPL-3.0）",
                "[国际] VMess/VLESS/Trojan/Shadowsocks 协议族"]),
    ("dlss", ["[仓库] rakanki911/DLSS5-Swapper（DLSS5 调优，MIT）",
              "[国际] Microsoft DirectX 12 / DLSS 超分接口（仅能力说明）"]),
    ("dlss5", ["[仓库] rakanki911/DLSS5-Swapper（DLSS5/RenoDX/OptiScaler，MIT）"]),
    ("aria2", ["[仓库] aria2/aria2（多协议多源下载器，GPL-2.0）",
               "[国际] HTTP/FTP/BitTorrent/Metalink 多源下载"]),
    ("cdn", ["[国际] CDN（内容分发网络）镜像源多连接分片下载",
             "[仓库] aria2 --max-connection-per-server/--split（GPL-2.0）"]),
    ("p2p", ["[国际] BitTorrent / Metalink P2P 多源分发",
             "[仓库] aria2 --bt-enabled（GPL-2.0）"]),
    ("licenses", ["[仓库] 本工具 licenses/ 文件夹（MIT/Apache-2.0/GPL-2.0/GPL-3.0/AGPL-3.0 全文与引用来源）",
                  "[官方] SPDX License List（https://spdx.org/licenses/）"]),
    # v0.5.20 OpenWrt 路由器系统 + 插件支持（各自按官方文档引用，只读优先）
    ("openwrt", ["[官方] OpenWrt 文档（guide-user/ + techref/，路由器/嵌入式 Linux）",
                 "[仓库] OpenWrt（GPL-2.0，本工具仅只读引用）"]),
    ("router", ["[官方] OpenWrt 文档（面向路由器/嵌入式设备的 Linux 发行版）",
                "[国际] IETF RFC（路由器相关协议：DHCP/SLAAC/NAT/PD）"]),
    ("uci", ["[官方] OpenWrt UCI 文档（guide-user/base-system/uci + techref/uci）",
             "[官方] /etc/config/*（UCI 文件格式：config/option/list 块）"]),
    ("opkg", ["[官方] OpenWrt opkg 文档（guide-user/additional-software/opkg，23.05 及更早）",
              "[官方] /usr/lib/opkg/status（已装清单）"]),
    ("apk", ["[官方] OpenWrt opkg→apk 迁移文档（guide-user/additional-software/opkg-to-apk-migration，24.10 起默认）",
             "[官方] /usr/lib/apk/db/installed（已装清单）"]),
    ("procd", ["[官方] OpenWrt procd 文档（techref/procd，init 与进程管理）",
               "[官方] /etc/init.d/*（服务脚本）"]),
    ("ubus", ["[官方] OpenWrt ubus 文档（techref/ubus，微总线）",
              "[官方] ubus call <ns> <method>（只读方法可调用）"]),
    ("netifd", ["[官方] OpenWrt netifd 文档（techref/netifd，网络接口守护）",
                "[官方] /etc/config/network（UCI 网络配置）"]),
    ("rpcd", ["[官方] OpenWrt rpcd 文档（techref/rpcd，RPC 守护/LuCI 后端）",
              "[官方] /usr/share/rpcd/acl.d/*.json（ACL 定义）"]),
    ("luci", ["[官方] OpenWrt LuCI 文档（guide-user/luci/start + techref/luci，Web 管理界面）",
              "[官方] uhttpd + rpcd 后端（经 ubus 读写系统）"]),
    ("imagebuilder", ["[官方] OpenWrt ImageBuilder 文档（guide-user/additional-software/imagebuilder，预编译根文件挑包）"]),
    ("sdk", ["[官方] OpenWrt SDK 文档（guide-developer/toolchain/using_the_sdk，交叉编译软件包）"]),
    ("feeds", ["[官方] OpenWrt feeds 文档（guide-developer/feeds，软件源机制）"]),
    ("buildroot", ["[官方] OpenWrt 构建系统文档（guide-developer/build-system，完整源码编译）"]),
    ("sysupgrade", ["[官方] OpenWrt sysupgrade 文档（techref/sysupgrade，固件升级，写操作仅指引）"]),
    ("plugin", ["[官方] 插件安全模型：native 入口仅限白名单内零参只读函数，绝不执行任意代码",
                "[仓库] 内置插件 openwrt/interop（随工具发布，经 plugin_validate 校验）"]),
    ("plugins", ["[官方] 插件框架：内置 + 用户 plugins/ 目录 drop-in 清单（*.json，经 plugin_validate 校验）",
                 "[安全] 非白名单/含命令注入的插件清单直接拒绝注册"]),
    # v0.5.21 OpenWrt 子系统补全（防火墙/无线/DHCP/存储）+ 可扩展只读白名单
    ("firewall", ["[官方] OpenWrt 防火墙文档（guide-user/security/firewall，fw4/nftables）",
                  "[国际] IETF RFC 3022 / RFC 4787（NAT 行为）"]),
    ("fw4", ["[官方] OpenWrt 防火墙文档（fw4 → nftables；fw4 print 只读检视）"]),
    ("nftables", ["[国际] Linux kernel Documentation/networking/nf/nftables（nftables 子系统）",
                  "[官方] OpenWrt 防火墙文档（fw4/nftables）"]),
    ("wireless", ["[官方] OpenWrt 无线文档（guide-user/smart-wifi/start，hostapd/UCI wireless）",
                  "[国际] IEEE 802.11（Wi-Fi 频段/信道/加密）"]),
    ("wifi", ["[国际] IEEE 802.11（Wi-Fi 频段/信道/加密）",
              "[官方] OpenWrt 无线文档（guide-user/smart-wifi/start）"]),
    ("hostapd", ["[官方] hostapd 文档（IEEE 802.11 认证与接入点，UCI wireless 后端）"]),
    ("dhcp", ["[国际] IETF RFC 2131 / RFC 2132（DHCP）",
              "[官方] OpenWrt DHCP/DNS 文档（guide-user/network/dhcp，dnsmasq/odhcpd）"]),
    ("dnsmasq", ["[官方] OpenWrt DHCP/DNS 文档（dnsmasq：DNS 转发 + DHCP 地址分配）",
                 "[国际] IETF RFC 1035（DNS 域名系统）"]),
    ("odhcpd", ["[官方] OpenWrt DHCP/DNS 文档（odhcpd：DHCPv6 / SLAAC 路由器通告）"]),
    ("fstab", ["[官方] OpenWrt 存储文档（guide-user/storage，UCI fstab / block-mount / overlay）",
               "[国际] Linux kernel Documentation/filesystems（文件系统）"]),
    ("overlay", ["[官方] OpenWrt 存储文档（overlay 叠加根：squashfs + jffs2）"]),
    ("write_guide", ["[安全] OpenWrt 写操作指引：只读预检 + 命令文本，opt-in 高危任务，绝不自动执行",
                     "[官方] OpenWrt 各子系统文档（sysupgrade/opkg/uci/procd）"]),
    ("register_native", ["[安全] 插件白名单可扩展：register_native 仅登记本包内已存在的零参只读函数，"
                         "写指引层显式拒绝进入白名单"]),
    # ---------------------------------------------------------------- #
    # v0.5.22：Android 8 下探 + 适老化 / OpenJDK / 内核 module·firmware·eBPF
    #         / 任务档位 / 数学量化
    # ---------------------------------------------------------------- #
    ("适老", ["[国际] WCAG 2.1 / 2.2 可访问性指南（1.4.3 对比度、1.4.4 文字可放大、2.3.3 动画可关闭）",
              "[国家] GB/T 37668-2019《信息技术 互联网内容无障碍可访问性技术要求与测试方法》",
              "[国家] GB/T 35273《信息安全技术 个人信息安全规范》（不采集个人数据，只读设备偏好）"]),
    ("无障碍", ["[国际] WCAG 2.1 / 2.2（Web Content Accessibility Guidelines）",
                "[官方] Android Accessibility（AccessibilityManager / AccessibilityService）",
                "[国家] GB/T 37668-2019 互联网内容无障碍可访问性技术要求与测试方法"]),
    ("android8", ["[官方] AOSP 平台版本对照（Android 8.0 Oreo = API 26）",
                  "[官方] Android 各 framework 服务引入版本（magnification API 17+ / daltonizer API 26+ / "
                  "high_text_contrast API 29+）"]),
    ("talkback", ["[官方] Android Accessibility / TalkBack（屏幕阅读器，AccessibilityService）",
                  "[国际] WCAG 2.1 4.1.2 Name, Role, Value（界面元素需可被辅助技术识别）"]),
    ("font_scale", ["[国际] WCAG 2.1 1.4.4 Resize Text（文字可放大至 200% 而不损失内容）",
                    "[官方] settings get system font_scale（Configuration.fontScale 全局生效）"]),
    ("contrast", ["[国际] WCAG 2.1 1.4.3 Contrast (Minimum) / 1.4.11 Non-text Contrast",
                  "[官方] accessibility_high_text_contrast（API 29+）"]),
    ("jdk", ["[官方] OpenJDK：https://openjdk.org/（JDK 文档入口：docs.oracle.com/en/java/javase/）"]),
    ("jvm", ["[官方] Java SE 规范（JVMS / Java Language Spec，含运行时系统属性定义）",
             "[国际] OpenJDK 源码：https://github.com/openjdk/jdk"]),
    ("jpms", ["[官方] JEP 261: Module System（JPMS 模块系统总纲）",
              "[官方] JEP 277: JDK 内部模块化（--add-exports / --add-opens）"]),
    ("gc", ["[官方] Oracle GC Tuning Guide（gctuning，G1/Z/Shenandoah 选型）",
            "[官方] JEP 439: Generational ZGC / JEP 379: Shenandoah"]),
    ("jit", ["[官方] Java SE 规范第 7 章 Code Generation（分层编译与内联）",
             "[官方] JEP 165: Compiler Control"]),
    ("jfr", ["[官方] Java Flight Recorder（JFR API，jdk.jfr 模块）",
             "[官方] jcmd JFR.start（JFR 录制入口；本工具只查能力不录制）"]),
    ("hotspot", ["[官方] HotSpot JVM（解释器 + C1/C2 两级 JIT + 多代 GC）"]),
    ("lsmod", ["[官方] Linux kernel Documentation/admin-guide/modules.rst（可加载内核模块）",
                "[官方] /proc/modules（proc(5) 内核模块表，只读）"]),
    ("kmod", ["[官方] Linux kernel Documentation/admin-guide/modules.rst",
              "[官方] sysfs ABI：/sys/module/<name>/（initstate / refcnt / parameters）"]),
    ("modinfo", ["[官方] modinfo(8) / lsmod(8)（kmod 工具，只读元数据）",
                 "[国际] Linux kernel 源码：include/linux/module.h（MODULE_LICENSE 与 taint）"]),
    ("firmware", ["[官方] Linux kernel Documentation/driver-api/firmware/（request_firmware 固件框架）",
                  "[官方] /lib/firmware（固件库路径；错配固件=硬件不可用，绝不替换）"]),
    ("bpf", ["[官方] Linux kernel Documentation/bpf/（eBPF 与 BPF 工具链）",
             "[官方] /proc/sys/kernel/unprivileged_bpf_disabled（非特权 BPF 安全开关）"]),
    ("ebpf", ["[官方] Linux kernel Documentation/bpf/（verifier / BPF-CPU 布局 / CO-RE）",
              "[官方] /sys/kernel/btf/vmlinux（BTF：BPF CO 跨内核版本运行的基础）"]),
    ("btf", ["[官方] /sys/kernel/btf/vmlinux（内核 BTF，CONFIG_DEBUG_INFO_BTF）",
             "[官方] Linux kernel Documentation/bpf/（BPF CO-RE 重定位）"]),
    ("taint", ["[官方] /proc/sys/kernel/tainted（内核 taint 标记）",
               "[国际] Linux kernel 源码：kernel/tainted.c（taint 传播规则）"]),
    ("kparams", ["[官方] Linux kernel Documentation/admin-guide/quick-kparams.rst（模块参数）",
                 "[安全] 写 /sys/module/*/parameters/* = 运行期改内核行为，属高危操作"]),
    ("档位", ["[工程] 任务档位（minimal/lite/standard/full）：选档位 ≠ 授权执行，"
              "执行仍需 --apply/--opt-in/--yes 三重确认"]),
    ("profile", ["[工程] 任务档位（大而全 full / 小而全 minimal），按风险/分类/opt-in 正交筛选"]),
    ("评分", ["[数学] 多准则决策 WSM：S = Σ wᵢ·x̂ᵢ（权重和为 1，分项先归一化到 [0,1]）",
              "[数学] Shannon 熵 H = −Σ pᵢ log₂ pᵢ，归一化后 H/log₂n ∈ [0,1] 衡量分布均衡度"]),
    ("shannon", ["[数学] 香农熵 H = −Σ pᵢ·log₂ pᵢ（信息论，分布均衡度度量）"]),
    ("gini", ["[数学] 基尼系数 G = Σ(2i−n−1)·pᵢ /(n·Σpᵢ) ∈ [0,1]（不平等度/集中度）"]),
    ("jaccard", ["[数学] 杰卡德相似度 J(A,B) = |A∩B|/|A∪B| ∈ [0,1]（集合重合度）"]),
    # 设备长期使用保护（v0.6.30）：传感器采集 + 材料/气候/耐久知识库，只读体检 + 保养指引
    ("battery", ["[官方] Apple 电池服务（优化电池充电 / 80% 上限建议）",
                 "[官方] 厂商电池指南（循环计数与容量衰减：满充循环约 300–1000 次后容量降至 80%）",
                 "[国际] IEEE 1188（阀控铅酸电池维护与寿命评估，可借鉴的电芯衰减判定思路）"]),
    ("charge_ceiling", ["[官方] 厂商电池保养（长期插电设备把上限锁 80% 显著降低日历老化）",
                        "[国际] 锂电化学（高 SOC 长期保持加速正极/电解液副反应）"]),
    ("ip_rating", ["[国际] IEC 60529（外壳防护等级 IPxx：首位防尘 0–6、次位防水 0–9K，如 IP67/IP68）",
                   "[官方] 厂商防护规格（进水/进尘不在常规保修范围，依 IP 等级使用）"]),
    ("ashrae", ["[国际] ASHRAE TC 9.9（信息技术设备推荐环境温度 18–27℃、相对湿度 40–60% 免冷凝）",
                "[国际] 冷凝露点（相对湿度随温度下降、低于露点即结露，损害电路）"]),
    ("storage_life", ["[国际] smartmontools smartctl 文档（SMART 健康与属性读取）",
                      "[国际] 存储寿命（保留空闲空间 + 温度上限可延长 NAND/磁盘寿命）",
                      "[官方] 厂商 SSD/HDD 规格（工作温度与年写入量 TBW 上限）"]),
    ("moisture", ["[国际] IEC 60529（防水等级，水汽/液体侵入依 IP 等级判定）",
                  "[官方] 厂商维护（异物/液体进入导致腐蚀，需干燥存放、避免高湿环境）"]),
    ("maintenance", ["[国际] IEC 60529（依防护等级确定清洁/防潮方式）",
                     "[官方] 厂商保养手册（定期清洁散热孔、更新固件、避免高温高湿延长寿命）"]),
    ("durability", ["[工程] 设备长期使用保护：只读采集传感器（电量/温度/SMART/uptime/循环）"
                    "+ 知识库驱动保养，绝不自动写设备；是否优化始终由用户确认"]),
    # 供电与环境安全（v0.6.38）：电气火灾科普落地的供电环境维度自适应
    ("electrical", ["[工程] 供电与环境安全：只读感知供电环境标签（旧线/铜铝/无接地/木座/松动插座）+ "
                    "本机温度，识别电气火灾事故前兆链条并自适应；绝不测接触电阻、绝不碰配电箱",
                    "[国家] GB/T 16895（等同 IEC 60364）/ GB/T 2099.1（插头插座）/ GB 13955（RCD）"]),
    # 国内标准知识库（v0.6.67）：中国境内 App 隐私合规四层体系（PIPL 上位法 → 国标 → 部门规定 → TC260）
    ("androidstd", ["[法律] 《中华人民共和国个人信息保护法》（PIPL，2021-11-01 施行；告知-同意/最小必要/敏感信息单独同意）",
                    "[国家] GB/T 35273-2020（个人信息安全规范，现行，2020-10-01 实施）",
                    "[国家] GB/T 41391-2022（App 收集个人信息基本要求，2022-11-01 实施）",
                    "[国家] GB/T 42574-2023（告知和同意实施指南，2023-12-01 实施）",
                    "[部门规范性文件] 《App 违法违规收集使用个人信息行为认定方法》（四部门，2019 印发）",
                    "[部门规范性文件] 《常见类型移动互联网应用程序必要个人信息范围规定》（39 类，2021-05-01 施行）",
                    "[部门规范性文件] 《移动互联网应用程序信息服务管理规定》（国家网信办，2022-08-01 施行）",
                    "[规程] 网络安全标准实践指南：App 自评估 / 系统权限申请使用（TC260，2020）"]),
    # GMS 标准知识库（v0.6.67）：GMS 兼容与 Google Play 上架（CDD/CTS/VTS/STS → GMS 许可 → Play 三件套 → Data safety）
    ("gmsstd", ["[GMS] Android 兼容性定义文档 CDD（source.android.google.cn/compatibility/cdd）",
                "[GMS] 兼容性测试套件 CTS（source.android.google.cn/docs/compatibility/cts，免费+CTS-V 手工项）",
                "[GMS] 供应商测试套件 VTS（source.android.google.cn/docs/core/tests/vts，Kernel/HAL）",
                "[GMS] 安全测试套件 STS（社区整理待核；官方锚点：Android 安全公告体系）",
                "[GMS] Play Integrity API（verdict 三件套+风险信号；默认每日 10000 次上限）",
                "[GMS] Play 应用签名（上传密钥 RSA≥2048 / 应用签名密钥 4096/2048；2021-08-01 条款）",
                "[GMS] Google Play targetSdk 要求（2026-08-31 起 API 36；Wear/车机 API 35）",
                "[GMS] Play 数据安全 Data safety 表单（2021-05 上线；开发者对披露负全责）"]),
    # F-Droid 标准知识库（v0.6.67）：免 GMS 自由软件分发（收录政策/反特征/可复现构建/仓库协议）
    ("fdroidstd", ["[分发] F-Droid 存储库模型（免账号免 GMS，能下载即可安装；F-Droid Limited 非营利运营）",
                   "[分发] F-Droid 收录政策 Inclusion Policy（主仓库只收 FLOSS 自由软件）",
                   "[分发] Anti-Features 反特征（Ads/Tracking/NonFreeNet/NonFreeDep/KnownVuln/DisabledAlgorithm 等）",
                   "[分发] fdroiddata 构建元数据（github.com/f-droid/fdroiddata，一个应用一个 .yml 配方）",
                   "[分发] F-Droid 可复现构建（服务端从源码构建签名，承诺与源码 tarball 一致）",
                   "[分发] fdroidclient 客户端与仓库协议（GPL-3.0；GitHub/GitLab 双仓；索引签名+指纹信任）"]),
    # 声学与音律（v0.6.87）：声音/频率/振动/音调/声率/黄钟大吕四轴知识库
    ("acoustics", ["[工程] 声学与音律：频率↔波长/声速/天线尺寸工程换算（c=f·λ）+ 三分损益十二律"
                   "生成器 + ISM 频段参照 + 音频设备只读枚举；绝不播放声音、绝不调音量、绝不采集"
                   "麦克风内容、无任何射频发射路径",
                   "[国际] IEC 61672-1（声级计·A/C/Z 计权）/ IEC 61260-1（倍频程）/ ISO 226（等响曲线）",
                   "[典籍] 《吕氏春秋·古乐》《淮南子·天文训》、朱载堉《律历融通》（新法密率）",
                   "[国际] ITU 无线电规则第 5 条（ISM 脚注 5.138/5.150/5.280）",
                   "[国家] 工信部公告 2019 年第 52 号（微功率短距离无线电发射设备目录和技术要求）",
                   "[国际] IEC 60268 系列 / EN 50332-1/-2（耳机声压≤100dB、输出电压≤150mV、WBCV≥75mV）",
                   "[国家] GB/T 14471（头戴耳机通用规范）"]),
    # 系统基座（v0.6.88）：系统目录·包格式·网络仓库·安全检测 四轴 + 路径命名空间概念课
    ("sysbase", ["[工程] 系统基座：FHS/LFS 界定「系统/基础工具链/系统关键组件」，包数据库与"
                   "第三方仓库订阅（源/pin/keyring）盘点，Metasploit 安装痕迹两路检测；"
                   "绝不安装/卸载、绝不改动仓库源与密钥、绝不启动 msfconsole、绝不写系统目录",
                   "[国际] FHS 3.0（文件系统层次标准）/ LFS Book（Linux From Scratch）",
                   "[国际] Debian Repository Format（wiki.debian.org）/ apt-secure(8) / apt_preferences(5)",
                   "[国际] Debian Policy Manual 第 5 章（二进制包结构）/ RPM Package Manager（rpm.org）",
                   "[厂商] docs.metasploit.com Nightly Installers（Rapid7 官方）/ metasploit-omnibus（安装器源码）",
                   "[概念] 互联网的本质是目录服务（DNS/仓库/URL）+ 安全与隐私是其上横切面；"
                   "安装包引用均为相对路径（相对仓库基址/安装前缀/PATH 解析）"]),
    # 文档与概念联动（v0.6.88）：docs 文档层作为联动网格一等节点（只读统合整合）
    ("docs", ["[工程] 文档与概念联动：docs/ 文档层是概念系统「联动连轴连动」统合整合的文档承载，"
                   "docs 登记进统一子系统清单成为可开关的文档节点，并与 linkage/sysbase 互相印证",
                   "[工程] 统一子系统清单（native/subsystems.py）：全量登记、可开关、配置落盘",
                   "[工程] 联动连轴（native/linkage.py）：方向性轴 + 五类性质（供给/门控/印证/闭环/串联）",
                   "[工程] 防误判冗余三防线（tests/test_native_common_lib.py）：身份契约/实际被依赖/冗余侦测"]),
    # 从零造系统学习应用（v0.6.89）：pepsipu 项目群导入分析学习应用
    ("sysdev", ["[工程] 从零造系统学习应用（导入分析学习应用 pepsipu 项目群）：warpalloc 预分配+"
                   "单空闲链分配器（MIT）、aski 四段编译器管线、xinOS-old/OSpaint 玩具 OS 引导链、"
                   "ramenbox 表格驱动 6502 模拟器、cx 符号链接农场多账户隔离、torus pnpm 工作区；"
                   "本机从零构建工具链与 glibc malloc 只读体检",
                   "[工程] 导入分析学习应用五步法：浅克隆全景→README 建意图→读最小核心源→"
                   "模式+边界+反面三件→回灌六层（知识/只读/任务/接线/概念/测试）",
                   "[国际] MIT License（warpalloc，Copyright (c) 2019 Sammy Hajhamid）/ "
                   "BSD 风格声明（xinOS-old，Copyright (c) 2020）",
                   "[工程] 许可证边界：aski/OSpaint/ramenbox/torus/cx 仓库未见许可证文件，"
                   "默认保留所有权利——只学思想与工程模式，绝不 vendored 源代码",
                   "[工程] glibc malloc 环境变量（man mallopt：MALLOC_ARENA_MAX/TRIM/MMAP/PERTURB/CHECK）"
                   "只读展示，绝不代设"]),
    # 外部设备连接与兼容（v0.6.39）：整体引入星闪标准 + 触控技术 + USB-C/PD/HID 兼容
    ("peripheral", ["[工程] 外部设备连接与兼容：只读识别触控/USB-C PD/HID 外设与多点触控协议，"
                    "整体引入星闪(NearLink)标准；绝不刷固件、绝不装私有驱动、绝不挂钩输入流",
                    "[国标] 星闪联盟团体标准 T/SL 系列（通信/接入/基础/测试）",
                    "[国际] USB-IF USB4 / USB PD 3.1（usb.org）/ USB-IF HID",
                    "[地区] IEC 62680（欧盟 USB-C 强制充电接口标准）",
                    "[国际] Linux kernel input multitouch protocol / 微软 Precision Touchpad 规范"]),
    ("nearlink", ["[国标] 星闪联盟团体标准 T/SL 系列（SparkLink/NearLink，SLB+SLE 两空口）",
                  "[国际] 蓝牙 SIG（BLE）/ Wi-Fi Alliance（IEEE 802.11，对标参考）"]),
    ("星闪", ["[国标] 星闪联盟团体标准 T/SL 系列（国产短距无线标准，整体引入）"]),
    ("touch", ["[国际] Linux kernel Documentation/input/multi-touch-protocol.rst（MT-A/MT-B）",
               "[国际] USB-IF HID / 微软 Precision Touchpad 规范"]),
    ("触控", ["[国际] 多点触控协议（内核 input MT：Type A/B）/ USB-IF HID",
              "[官方] 微软 Precision Touchpad（HID over I2C）"]),
    ("usb_c_pd", ["[国际] USB-IF USB4（基于 Thunderbolt 3，40Gbps）/ USB PD 3.1（100W/240W EPR）",
                  "[地区] IEC 62680（欧盟 USB-C 强制充电接口标准）",
                  "[国际] USB BC 1.2（Battery Charging，传统充电端口）"]),
    ("usb4", ["[国际] USB-IF USB4 规范（基于 Thunderbolt 3 协议，40Gbps，向下兼容 USB 3.2/2.0）"]),
    ("hid", ["[国际] USB-IF Device Class Definition for HID（Report Descriptor 规范）",
             "[国际] Linux kernel Documentation/hid/（hid-generic / hid-multitouch）"]),
    ("pnp", ["[国际] 即插即用（PnP）：设备经枚举→匹配驱动→就绪；HID 类按描述符自动加载通用驱动"]),
    # 时空与全维度管理器（v0.6.40）：量子/计算机原理 + 时间/空间/施时空组合/未来兼容透镜
    ("chrono", ["[工程] 时空与全维度管理器：以量子/计算机原理为只读观测透镜，观察时间维/空间维/"
                "施时空组合维/未来兼容维，并提供全时空全维度循环往复管理器（round-robin 周而复始、每维一视同仁）；"
                "绝不改时钟时区、绝不分区格式化、绝不升级替换组件、绝不执行量子写操作",
                "[国际] IETF RFC 5905（NTPv4）/ IEEE 1588（PTP）",
                "[国际] Linux Foundation FHS 3.0 / POSIX 虚拟地址空间 / NUMA 拓扑",
                "[国际] NIST FIPS 203/204/205（后量子 ML-KEM/ML-DSA/SLH-DSA）",
                "[国际] IEEE 7130 / ISO·IEC 4879（量子技术词汇）",
                "[国际] endoflife.date（标准 EOL 事实源）"]),
    ("quantum", ["[国际] 量子理论及量子计算原理（叠加/纠缠/测量/后量子密码），仅作只读观测透镜",
                 "[国际] NIST FIPS 203/204/205（后量子密码：ML-KEM/ML-DSA/SLH-DSA）",
                 "[国际] IEEE 7130 / ISO·IEC 4879（量子技术词汇）"]),
    ("量子", ["[国际] 量子理论及计算机原理（叠加态并行观测/纠缠关联/测量不改态），仅作系统多维观测的方法论透镜"]),
    # 虚拟机环境（v0.6.41）：识别虚拟化层 + 不同 VM 内优雅降级
    ("virt", ["[工程] 虚拟机环境：只读识别本工具运行在裸金属/KVM/VMware/VirtualBox/Hyper-V/Xen/WSL/容器哪一层，"
              "并给出各只读探针的可用/退化结论，确保整体在不同虚拟机内只降级不崩溃；绝不装增强工具/改配置/加载内核模块",
              "[国际] systemd-detect-virt（跨 Hypervisor 统一用户态检测接口）",
              "[国际] DMTF SMBIOS / DMI（product_name/sys_vendor 暴露虚拟化层）",
              "[国际] DMTF Redfish（硬件/虚拟化资源管理事实标准）",
              "[国际] OCI 运行时规范（容器隔离：runc/crun）",
              "[国际] libvirt（统一虚拟化管理层）"]),
    ("虚拟机", ["[工程] 虚拟机环境：让整体在不同虚拟机（KVM/VMware/VirtualBox/Hyper-V/Xen/WSL/容器）内都能正常运行，"
                "受限 VM 退化为概念观测、裸金属全开"]),
    # 软件包规范审计（v0.6.41）：按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对
    ("packages", ["[工程] 软件包规范审计：按系统/硬件/相关软件包只读检测包管理器（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper），"
                  "审计安装/卸载/配置/设置优化四类操作是否符合包规范并给出层级应对；任何写操作只给规范指引不代执行",
                  "[国际] Debian Policy Manual（APT/dpkg 控制字段与依赖）",
                  "[国际] Fedora Packaging Guidelines（DNF/RPM）",
                  "[国际] Arch PKGBUILD / Pacman（构建与安装规范）",
                  "[国际] Homebrew Formula（macOS/Linux 用户态包）",
                  "[国际] WinGet 清单 schema v1.x（Windows 包管理）",
                  "[国际] Alpine apk-tools（APKINDEX 与签名）"]),
    ("包管理", ["[工程] 软件包规范审计：安装/卸载/配置/优化一律走官方接口（apt/dnf/pacman/brew/winget…），"
                "禁止手工改包数据库，签名/GPG 校验失败即停；任何写操作只给层级应对指引"]),
    # v0.6.42：导入学习应用 + 网络/显示/元能力/场景透镜（全部只读、出指引不代执行）
    ("apctrl", ["[工程] AP 集中控制器审计：只读审计 hostapd/NetworkManager 共享热点/dnsmasq/apcontroller 思路，"
                "绝不读解密口令、绝不改任何 AP 配置、绝不下发配置",
                "[学习] obsy/apcontroller：cron 轮询 + scp/ssh 取数 + 按 AP Group 下发 WiFi 配置 + "
                "known_hosts 防 MITM + key-based（dropbear）免密 + 用户脚本 #desc:/#warn:"]),
    ("ap控制器", ["[工程] AP 集中控制器：把轻量 AP 当被管节点集中审计与下发（apcontroller 思路），"
                  "本机只探测、只给规范指引"]),
    ("llvm", ["[国际] LLVM 项目（clang/lld/MLIR 工具链）",
              "[国际] LLVM Target Triple 规范（arch-vendor-os-abi）",
              "[工程] 交叉编译目标矩阵按时间序列逐步扩充，附 sysroot 指引与 CHANGELOG（常态化的回头看）"]),
    ("交叉编译", ["[国际] GNU/Mingw-w64 交叉编译 sysroot 约定",
                  "[工程] clang --target=<triple> -sysroot <path> -fuse-ld=lld 做交叉编译，绝不自动编译/下 sysroot"]),
    ("meshnet", ["[国际] WireGuard（现行规范见 wireguard.com 论文；截至 2026-10 IETF 无 "
                 "WireGuard RFC，所用原语为 RFC 7748/7693/8439/5869；wg show 拓扑 / wg set 配置）",
                 "[学习] Mullvad Meshnet（模型，来源缺口已标注）：WireGuard P2P 网状、设备链接权限、"
                 "设备能力适配（算力/GPU/存储缓存）、负载均衡与协同共享",
                 "[工程] 只读观测组网：绝不新增 peer、绝不改 wg 配置、绝不共享个人数据"]),
    ("组网", ["[工程] 组网与设备协同：设备间直连优先、跨网不通才走 Exit Node；算力按 compute 维度分摊、"
              "GPU 只在登记 gpu 的设备跑、storage_cache 不强制占用磁盘"]),
    ("vdns", ["[国际] RFC 1035（DNS）/ RFC 7858（DoT）/ RFC 8484（DoH）",
              "[工程] 虚拟根 DNS 与多 CDN：只读观测 resolv.conf/DoH-DoT、多 CDN 选择与健康，绝不改 DNS"]),
    ("虚拟根dns", ["[工程] 虚拟根 DNS：nameserver 顺序决定解析入口；DoT/DoH 经 systemd-resolved/stubby/cloudflared 落地"]),
    ("ipp", ["[国际] RFC 8010（IPP 编码）/ RFC 8011（IPP 模型与语义）/ IPP Everywhere（PWG 5100.14）",
             "[工程] IPP 打印协议发现：只读发现 CUPS/mDNS/本地管理页，绝不 lpadmin 加打印机、绝不改 CUPS 配置"]),
    ("打印", ["[国际] PWG 标准打印（AirPrint / IPP-over-USB 同源思路）；驱动无关用 IPP Everywhere -m everywhere"]),
    ("display", ["[国际] freedesktop XDG_SESSION_TYPE（会话类型：x11/wayland/tty）",
                 "[国际] Vulkan（Khronos）/ OpenGL（glxinfo）渲染后端 / RandR（xrandr）",
                 "[工程] 现代显示与 GPU 推进：只读观测、保留控制台/终端/远程终端，绝不装驱动/切 Wayland"]),
    ("显示", ["[工程] 现代设备显示：显示服务器 + GPU 渲染后端 + 分辨率，推进图形化不移除控制台/终端/远程终端入口"]),
    ("retro", ["[工程] 常态化回头看、久久为功：维护节奏表（各维按周期回头看）+ 长期保障要点 + 易漂移维度复盘",
               "[工程] 与 novel-framework「每卷末/每 20 章体检」同源思路——持续演进元能力"]),
    ("回头看", ["[工程] 常态化的回头看：不一次性扫完就丢，把「该定期回头看什么」汇总成只读清单"]),
    ("restart", ["[导入] 对话人类文明重启计划（别名「洪荒重启」）场景透镜",
                 "[工程] 维度清单（计算/网络/供电/存储与知识库/制造与供应链/人才与训练）+ 保命优先级"
                 "（不可再生优先）+ 知识库离线沉淀（与 sysweeper data/ 知识库同口径，开放许可优先）",
                 "[工程] 只读场景透镜：只帮你想清楚「重启要保什么、按什么序」，不做任何施工/搬运"]),
    ("重启", ["[工程] 人类文明重启透镜：知识库>制造>人才>供电>计算网络（不可再生优先），知识是可复制资产"]),
    ("time_theory", ["[国际] IETF RFC 5905（NTPv4）/ IEEE 1588（PTP 精确时间协议）",
                     "[国际] IANA tz database（时区事实源）"]),
    ("时间理论", ["[国际] 时钟同步（NTP/PTP）/ 时区（IANA tz database）/ 生命周期阶段（provisioning→steady→aging→EOL）"]),
    ("space_theory", ["[国际] Linux Foundation FHS 3.0（文件系统层次）/ POSIX 虚拟地址空间",
                      "[国际] NUMA 拓扑（sys/devices/system/node）"]),
    ("空间理论", ["[国际] 存储层次金字塔（寄存器→缓存→内存→NVMe/SSD→HDD）/ 虚拟地址空间 / 挂载命名空间 / NUMA 拓扑"]),
    ("spacetime", ["[工程] 施时空组合理论：把带时间戳事件与当时空间资源态配对成因果链，识别时间维与空间维的纠缠",
                   "[国际] freedesktop journald（带时间戳事件源）/ rsyslog"]),
    ("施时空", ["[工程] 施时空组合理论（事件-时间-空间关联）：时间维事件 × 空间维资源 = 可追责因果链与扩容/迁移/退役依据"]),
    ("future_compat", ["[国际] 标准 EOL 追踪（endoflife.date）/ 后量子迁移（NIST FIPS 203/204/205）",
                       "[工程] 前向兼容原则（USB4 兼容 USB 3.2/2.0、星闪与 BLE/Wi-Fi 共存）"]),
    ("未来兼容", ["[国际] 未来兼容维：标准 EOL 追踪、后量子算法迁移（FIPS 203/204/205）、前向兼容原则"]),
    ("cycle_dimensions", ["[工程] 全时空全维度循环往复管理器：以 round-robin 周而复始遍历全部维度，每维一视同仁只读（亦复如是）"]),
    ("全维度", ["[工程] 各维度管理器：统一维度注册表（时间/空间/施时空组合/未来兼容/量子透镜 + 既有子系统维度），循环往复观察"]),

    # v0.6.43：虚拟机完整运行支持 + 汇编语言优化（只读、出模板/指引不代执行）
    ("virt", ["[工程] 虚拟机完整运行支持：只读探测本机能否完整跑起一层虚拟化（/dev/kvm 可读性、CPU VT-x/AMD-V 标志、"
              "嵌套开关 kvm_intel.nested/kvm_amd.nested），生成各 Hypervisor 运行配置只读模板"
              "（libvirt XML / QEMU / VBox / VMware .vmx / WSL .wslconfig），列出可嵌入 initramfs 的半虚拟化驱动模块",
              "[国际] KVM /dev/kvm 与 nested 参数（Linux 内核 admin-guide/kernel-parameters）",
              "[国际] libvirt 域 XML（type='kvm' / virtio 设备总线）",
              "[国际] Hyper-V 嵌套虚拟化 ExposeVirtualizationExtensions / WSL .wslconfig",
              "[国际] VMware .vmx vhv.enable 嵌套虚拟化开关"]),
    ("虚拟机完整运行", ["[工程] 虚拟机完整运行：让整体在 KVM/QEMU/VMware/VirtualBox/Hyper-V/Xen/WSL/容器都能给出"
                       "「怎么跑起来」的规范路径——只探测/模板/指引，不加载内核模块/不启动 VM/不装驱动/不改配置"]),
    ("asm", ["[国际] NASM / YASM（x86/x86_64 汇编器）",
             "[国际] GNU Assembler（GAS，AT&T/Intel 语法，随 binutils）",
             "[国际] LLVM MachineCoder（llvm-mc）",
             "[国际] SIMD 指令集规范（Intel SSE/AVX、ARM NEON/SVE、RISC-V Vector RVV、龙芯 LSX/LASX）",
             "[工程] 汇编语言优化：只读探测汇编器 + 给优化要点（向量化/对齐/寄存器/缓存/分支/指令/内联约束）"
             "与 LLVM 交叉编译汇编指引（clang -target=<triple> -S）；绝不编译、绝不改源码、绝不写汇编文件"]),
    ("汇编", ["[工程] 汇编语言优化：向量化（SIMD）优先让编译器自动向量化再手写 intrinsics；内存对齐、寄存器分配、"
              "缓存友好、分支优化、内联汇编约束——只给要点与交叉汇编指引，不代编译"]),

    # 远程接入与传输客户端（v0.6.30）：telnet/ssh/filezilla/putty 文档跟踪 + 只读安全审计
    ("ssh", ["[国际] RFC 4251/4252/4253/4254（SSH-2 架构/认证/传输/连接，全程加密）",
             "[官方] sshd_config(5) / ssh_config(5) man（PermitRootLogin / PasswordAuthentication / PubkeyAuthentication）",
             "[官方] NIST SP 800-63B（公钥/口令认证强度）"]),
    ("telnet", ["[国际] RFC 854（Telnet 协议：明文 NVT，口令与数据全程不加密）",
                "[安全] telnet 在不可信网可被嗅探；现代环境一律用 SSH 替代、telnetd 应停用"]),
    ("sftp", ["[国际] SSH File Transfer Protocol（RFC 4254 子会话，走 22 端口加密，优先于 FTP）",
              "[官方] sftp-server(8)（经 Subsystem sftp 启动）"]),
    ("ftp_plaintext", ["[国际] RFC 959（FTP 明文文件传输，口令与数据均不加密）",
                       "[国际] RFC 4217（FTP over TLS，FTPS 加密替代）",
                       "[安全] 明文 FTP 仅限本地可信场景；跨网一律用 SFTP/FTPS"]),
    ("filezilla", ["[官方] FileZilla 文档（站点管理器 / 主密码对 sitemanager.xml 口令二次加密）",
                   "[安全] 站点协议选 SFTP（22 端口）；不把含口令的 sitemanager.xml 随意分发"]),
    ("putty", ["[官方] PuTTY 文档（Session 注册表 / ppk 密钥 / pageant 代理）",
               "[安全] 默认 SSH 连接类型 + ED25519 公钥；私钥放 pageant 而非明文落盘口令"]),
    ("remote", ["[工程] 远程接入与传输客户端审计：只读判定明文风险（telnet/明文 FTP/口令登录），"
                "加固只给官方指引，绝不读解密口令 / 不改 sshd_config / 不替你停服务"]),
    # 证书与加密开源整合（v0.6.31）：OpenSSL 类开源栈 + 硬件信任根 + 各种证书
    ("cert", ["[国际] RFC 5280（X.509 公钥证书：链校验/有效期/SAN/EKU/吊销）",
              "[国际] RFC 8555（ACME 自动证书管理，Let's Encrypt 免费签发+续期）",
              "[国际] TPM 2.0（TCG 硬件信任根：私钥不可导出、封装磁盘加密密钥）",
              "[国际] IEEE 802.1AR（IDevID/LEDevID 设备身份证书，出厂硬件背书）",
              "[国际] FIDO2 / WebAuthn（硬件/平台认证器，抗钓鱼通行密钥）",
              "[官方] OpenSSL/LibreSSL/BoringSSL/GnuTLS 文档（允许接入开源加密栈）",
              "[官方] 各平台密钥库（Keychain/Secure Enclave/CNG/Android Keystore）"]),
    # v0.6.34-35：兼容层串联 + 全能全知自检
    ("compat", ["[官方] Wine 官方文档（WineHQ：Win32/Win64 API 重实现与 winecfg）",
                "[官方] Proton Wiki（Valve：Wine + DXVK + VKD3D-Proton + Steam Runtime）",
                "[官方] DOSBox Wiki（x86/声卡/显卡模拟与 MOUNT、cycles）",
                "[官方] Microsoft Learn · WSL（安装、wslconfig 与 interop）",
                "[国际] Khronos Vulkan 规范（loader / ICD / SPIR-V，兼容层的下游依赖）",
                "[官方] busybox 官方文档（多调用二进制与 --list 能力清单）"]),
    ("omni", ["[国际] ISO/IEC 25010（系统与软件质量模型：功能性/可靠性/可维护性等特性）",
              "[国际] ISO/IEC 25023（系统与软件产品质量测量：覆盖率等度量）",
              "[国标] GB/T 25000.10（系统与软件质量模型，等同采用 ISO/IEC 25010）",
              "[国际] NIST SP 800-53 Rev.5（系统与信息完整性 SI：自我评估与边界声明）"]),
)


def task_standards(task) -> list:
    """派生某任务的标准归属（带 [国标]/[国际]/[地区] 标记的字符串列表）。

    规则：任务自带 standards 优先；否则按 id/title 中的关键词细化；
    再无命中则回退分类默认。保证每个任务都能展示自己的标准出处。

    关键词匹配采用**最长优先**（而非表内顺序先命中即返回）：表里存在
    `pm`（Android PackageManager）这类短关键词，若按顺序匹配会劫持
    `jpms`/`jpm`（Java 模块系统）这类更长更具体的关键词——「JPMS 模块系统」
    会被误判成「pm 包管理」。取最长命中即取最具体的语义。
    """
    own = list(getattr(task, "standards", None) or [])
    if own:
        return own
    hay = f"{getattr(task, 'id', '')} {getattr(task, 'title', '')}".lower()
    best_kw = ""
    for kw, _refs in KEYWORD_STANDARDS:
        k = kw.lower()
        if k in hay and len(k) > len(best_kw):
            best_kw = k
    if best_kw:
        for kw, refs in KEYWORD_STANDARDS:
            if kw.lower() == best_kw:
                return list(refs)
    return list(CATEGORY_TASK_STANDARDS.get(getattr(task, "category", ""), []))


# ---------------------------------------------------------------------------
# 地区子标签：按目标国家/地区精确展示（us / jp / eu / de …）
# ---------------------------------------------------------------------------

REGION_TAGS = {"us": "美国", "jp": "日本", "eu": "欧盟", "de": "德国", "cn": "中国"}

# 地区 → 该地区的判定关键词（命中即视为该地区条目）
REGION_KEYWORDS = {
    "us": ("美国", "NIST", "Section 508", "ENERGY STAR", "EPA"),
    "jp": ("日本", "JIS", "APPI", "個人情報"),
    "eu": ("欧盟", "GDPR", "EN 301 549", "ErP", "EUPL", "EU "),
    "de": ("德国", "DIN"),
}

ALL_AUDIENCES = ("cn", "intl", "regional", "us", "jp", "eu", "de")


def region_rank(item: str, region: str) -> int:
    """某标准条目属于指定地区的优先级：0=命中该地区，1=其他地区条目。"""
    kws = REGION_KEYWORDS.get(region, ())
    return 0 if any(k in item for k in kws) else 1


@dataclass
class Action:
    """单个可执行/可指引的子动作。"""

    kind: str            # shell | adb | python | manual | native
    command: str         # 具体命令或指引文本（native 时为 "module.func"）
    description: str = ""  # 人类可读说明
    reversible: bool = False  # 是否可撤销（仅供展示）

    def summarize(self) -> str:
        tag = {"shell": "本地", "adb": "ADB", "python": "内建",
               "manual": "手动", "native": "原生接口"}[self.kind]
        return f"[{tag}] {self.description or self.command}"


@dataclass
class Task:
    """一项系统优化/清理任务。"""

    id: str
    platform: str        # windows|macos|linux|android|ios|bsd|unix|any
    title: str
    category: str        # cleanup|optimize|privacy|maintenance|network
    risk: str            # low|medium|high
    actions: List[Action] = field(default_factory=list)
    desc: str = ""
    min_ver: str = "0"    # 适用最低版本（数值比较）
    max_ver: str = "999"  # 适用最高版本
    caveats: List[str] = field(default_factory=list)   # 风险提示
    notes: List[str] = field(default_factory=list)     # 注意事项提醒
    requires_lang: str = ""  # 非空时仅当环境探测到该语言运行时才自动启用（不强求安装）
    opt_in: bool = False     # 默认关闭的高影响开关（网络/ITU 调优），需选择+确认
    standards: List[str] = field(default_factory=list)  # 本任务直接依据的标准条目（分类规范整体）
    arch: str = ""           # 架构/指令集维度（跨平台之上另一维度）：非空时仅当当前架构
                           # 匹配才适用（loongarch/mips/riscv/openpower/openrisc/x86/arm/
                           # open_hardware）；空=任意架构均适用。架构维度接入 scan/list/clean。

    # ---------------- 显示层（过 i18n） ----------------
    #
    # 为什么用方法而不是直接用字段：Task 的 title/desc/caveats/notes 是以**源语言
    # （简体中文）**书写的，也正是 gettext 的 msgid。字段本身保持原样（后台不变、
    # 可被 id 反查、可被测试按原文断言），只在**要显示给人看**的时候过一次 `_()`。
    # 于是：未翻译的语言自动回退中文，已翻译的语言显示译文，后台逻辑一行不改。

    def display_title(self) -> str:
        """显示用标题（过翻译；无译文时回退源语言原文）。"""
        from .i18n import _
        return _(self.title)

    def display_desc(self) -> str:
        from .i18n import _
        return _(self.desc) if self.desc else ""

    def display_caveats(self) -> List[str]:
        from .i18n import _
        return [_(c) for c in (self.caveats or [])]

    def display_notes(self) -> List[str]:
        from .i18n import _
        return [_(n) for n in (self.notes or [])]

    def risk_level(self) -> int:
        return RISK_ORDER.get(self.risk, 0)

    def matches(self, platform: str, version: str) -> bool:
        # 完全匹配平台
        if self.platform == platform:
            return _ver_ge(version, self.min_ver) and _ver_le(version, self.max_ver)
        # 跨平台任务：适用于所有「操作系统」平台，但不适用于 uni-app 这类目标端
        if self.platform == "any":
            if platform in NON_OS_PLATFORMS:
                return False
            return _ver_ge(version, self.min_ver) and _ver_le(version, self.max_ver)
        return False

    def line(self) -> str:
        cat = CATEGORIES.get(self.category, self.category)
        return f"  • {self.display_title()}  [{cat}/{self.risk}]  (id={self.id})"


# 非操作系统类的「目标端」（如 uni-app 跨端框架）。
# 跨平台任务（platform="any"）默认不适用于它们，否则查询某目标端时
# 会混入与其无关的通用任务（例如问 uni-app 却列出 S.M.A.R.T. 检查）。
NON_OS_PLATFORMS = {"uniapp"}


def _vt(v: str):
    """把版本字符串解析成可比较的整数元组。"""
    import re
    nums = re.findall(r"\d+", str(v))
    return tuple(int(x) for x in nums) if nums else (0,)


def _ver_ge(a: str, b: str) -> bool:
    return _vt(a) >= _vt(b)


def _ver_le(a: str, b: str) -> bool:
    return _vt(a) <= _vt(b)
