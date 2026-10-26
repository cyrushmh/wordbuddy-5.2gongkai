"""统一子系统清单 + 开关管理器（v0.6.22）。

本模块是「所有已导入/自研、可嵌入整体系统（sysmap 关联总览）的只读诊断」
的**单一事实源**：每一条登记项即一个可独立开/关的子系统。

设计要点（对齐用户要求「利用选项开启关闭 + 所有能嵌入整体的必须嵌入」）：

- **全量登记**：凡是 native 层里能嵌入整体系统的只读诊断——不论 firmware（固件）/
  plugins（插件）/ modules（内核模块）/ kernel / storage / container / hardware /
  跨平台 OS 探测等——都在此登记，不再由 sysmap 硬编码零散子集。
- **可配置开关**：每项带 ``default_on``（默认 True，向后兼容当前「全嵌入」行为）；
  用户可在配置文件中关闭任一子系统，sysmap 只枚举已开启项。
- **配置落地**：``~/.config/sysweeper/subsystems.json``，键为子系统 key、值为 bool。
  读配置时与默认值合并，未知 key 自动忽略，保证旧配置不崩。

红线（与全工具一致）：本模块只登记与开关，**绝不**调用任何写/执行路径；
具体诊断仍由各 native 子模块的只读函数负责。

返回类型兼容：多数报告返回 ``(ok: bool, msg: str)``，部分环境类报告返回 ``list``；
sysmap 在调用处统一归一化（见 ``native/sysmap.py``）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

__all__ = [
    "Subsystem", "SUBSYSTEMS", "BY_KEY", "ALL_KEYS",
    "CONFIG_PATH", "default_states", "load_states", "save_states",
    "set_enabled", "is_enabled", "enabled_subsystems", "enabled_probes",
    "list_subsystems",
]

# 配置落点：~/.config/sysweeper/subsystems.json
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "sysweeper")
CONFIG_PATH = os.path.join(CONFIG_DIR, "subsystems.json")


@dataclass(frozen=True)
class Subsystem:
    """一个可独立开/关、可嵌入整体系统的只读诊断子系统。

    key    : 唯一标识（RELATIONS 与配置文件均用 key，不用 label，避免重名歧义）。
    label  : sysmap 展示标签（中文）。
    layer  : 所属层（用于 sysmap 分组展示）。
    module : native 子模块名（不含 .py，``from . import <module>``）。
    fn     : 报告函数名（零参可调用，返回 (bool,str) 或 list）。
    default_on : 默认是否开启（默认 True）。
    """
    key: str
    label: str
    layer: str
    module: str
    fn: str
    default_on: bool = True
    # 去中心化版本：每个子系统各自持有独立版本号（默认基值“没有后面”）；
    # 子系统独立推进只 bump 自己，不影响整体包/兼容层/概念系统。
    version: str = "0000.0000.0000.0000"


# ─────────────────────────────────────────────────────────────────────────────
# 单一事实源：所有可嵌入整体系统的只读诊断子系统（firmware/plugins/modules 等全量覆盖）
# ─────────────────────────────────────────────────────────────────────────────
SUBSYSTEMS: List[Subsystem] = [
    # ── 网络层 ──
    Subsystem("network", "网络接口/路由", "网络", "network", "iproute2_report"),
    Subsystem("osi", "OSI 七层", "网络", "osi", "osi_report"),
    Subsystem("dnshealth", "DNS 解析", "网络", "dnshealth", "dnshealth_report"),
    Subsystem("tor", "Tor 覆盖层", "网络/隐私", "tor", "tor_report"),
    Subsystem("zerotier", "ZeroTier 虚拟组网", "网络", "zerotier", "zerotier_report"),
    Subsystem("netlink", "网络链接协议", "网络", "netlink", "link_report"),
    Subsystem("netauth", "网络隐私验证", "网络/隐私", "netauth", "netauth_report"),
    Subsystem("meshchat", "本地自组网", "网络", "meshchat", "node_report"),
    Subsystem("reshare", "算力/网络共享", "网络/共享", "reshare", "reshare_report"),
    Subsystem("openwrt", "OpenWrt 路由器", "网络/嵌入式", "openwrt", "openwrt_report"),

    # ── 兼容 / 子系统层 ──
    Subsystem("wsl", "WSL 子系统", "兼容/子系统", "wsl", "wsl_report"),
    Subsystem("proton", "Proton 兼容层", "兼容", "proton", "proton_report"),
    Subsystem("virtgpu", "虚拟化/GPU", "硬件/虚拟化", "virtgpu", "virtgpu_report"),
    Subsystem("browser", "浏览器引擎", "应用", "browser", "browser_report"),
    Subsystem("jdk", "OpenJDK-JVM", "应用/JVM", "jdk", "jdk_report"),
    Subsystem("miniapp", "小程序端映射", "应用", "miniapp", "mapping_report"),

    # ── 跨平台 OS 探测（导入分析学习，可嵌入整体系统）──
    Subsystem("ios", "iOS 设备", "移动/OS", "ios", "environment_report"),
    Subsystem("android", "Android 设备", "移动/OS", "android", "environment_report"),
    Subsystem("macos", "macOS 系统", "OS", "macos", "environment_report"),
    Subsystem("bsd", "BSD 系统", "OS", "bsd", "environment_report"),
    Subsystem("unix", "Unix/Solaris", "OS", "unix", "environment_report"),
    Subsystem("windows", "Windows 系统", "OS", "windows", "environment_report"),

    # ── 内核 / 固件 / 模块（用户点名：firmware、modules）──
    Subsystem("kernel", "内核调优(sysctl)", "内核", "kernel", "kernel_report"),  # v0.6.22 新增聚合
    Subsystem("kmod", "内核模块", "内核", "kmod", "kmod_report"),
    Subsystem("firmware", "固件(firmware)", "硬件/固件", "kmod", "firmware_report"),
    Subsystem("modules", "已加载模块", "内核", "kmod", "loaded_modules_report"),

    # ── 硬件 / 存储 / 容器（v0.6.22 新增聚合）──
    Subsystem("hardware", "硬件本征", "硬件", "hardware", "hardware_report"),
    Subsystem("storage", "存储/文件系统", "存储", "storage", "storage_report"),
    Subsystem("container", "容器运行时", "容器", "container", "container_report"),

    # ── 系统 / 系统软件 / 插件（用户点名：plugins）──
    Subsystem("distro", "发行版能力", "系统", "distro", "distro_report"),
    Subsystem("syssoftware", "系统软件栈", "系统", "syssoftware", "systemd_report"),
    Subsystem("pkgmgr", "包管理", "系统", "pkgmgr", "universal_report"),
    Subsystem("plugins", "插件(plugins)", "系统/插件", "plugins", "plugin_report"),
    Subsystem("plugins_allowlist", "插件白名单", "系统/插件", "plugins", "allowlist_report"),
    Subsystem("thirdparty", "第三方互联", "系统", "thirdparty", "thirdparty_report"),
    Subsystem("arch", "架构/指令集", "硬件", "arch", "arch_report"),
    Subsystem("edge", "单板机(SBC)", "硬件", "edge", "edge_report"),
    Subsystem("desktop", "桌面环境", "应用", "desktop", "environment_report"),

    # ── 应用 / 媒体 / 资讯 ──
    Subsystem("imagefmt", "图像编解码能力", "应用/媒体", "media", "image_capability_report"),
    Subsystem("webnews", "优化资讯知识库", "资讯", "webnews", "webnews_report"),

    # ── 鸿蒙 / 遗留 / 介质 / 安全 / 共享计算 ──
    Subsystem("kaihong", "KaihongOS 发行版", "系统/OS", "harmony", "kaihong_report"),
    Subsystem("dos", "遗留 DOS 环境", "兼容/遗留", "legacy", "dos_report"),
    Subsystem("legacy", "遗留/嵌入式总览", "兼容/遗留", "legacy", "legacy_report"),
    Subsystem("busybox", "busybox 嵌入式用户态", "嵌入式", "legacy", "busybox_report"),
    Subsystem("dosbox", "dosbox 模拟兼容层", "兼容", "legacy", "dosbox_report"),
    Subsystem("livemedia", "可启动介质制作能力", "媒体/制作", "livemedia", "livemedia_report"),
    Subsystem("emergency", "预警应急定位", "安全", "emergency", "emergency_report"),
    Subsystem("distcompute", "分布式计算", "共享/计算", "distcompute", "distcompute_report"),
    Subsystem("distjob", "跨机派活", "共享/计算", "distjob", "job_report"),

    # ── 参数 / 阈值 / 导入（v0.6.23 新增，GUI 可调控与导入的入口）──
    Subsystem("settings", "参数与阈值", "配置/参数", "settings", "settings_report"),
    Subsystem("importio", "多来源导入(剪贴板/文件/二维码)", "导入", "importio", "importio_report"),

    # ── 设备保护 / 远程接入 / 证书加密（v0.6.30-31 新增，全量嵌入整体）──
    Subsystem("durability", "设备长期使用保护", "设备保护", "durability", "durability_report"),
    Subsystem("electrical", "供电与环境安全", "设备保护", "electrical", "electrical_safety_report"),
    Subsystem("peripheral", "外部设备连接与兼容", "设备/外设", "peripheral", "peripheral_report"),
    Subsystem("acoustics", "声学与音律", "设备/声学", "acoustics", "acoustics_report"),
    Subsystem("sysbase", "系统基座", "系统/基座", "sysbase", "sysbase_report"),
    # ── v0.6.89：从零造系统学习应用（pepsipu 项目群导入，只读知识+体检）──
    Subsystem("sysdev", "从零造系统学习应用", "系统/学习", "sysdev", "sysdev_report",
              version="0000.0000.0000.0001.20261023"),
    Subsystem("chrono", "时空与全维度管理器", "系统/理论", "chrono", "chrono_report"),
    Subsystem("remote", "远程接入审计", "网络/远程", "remote", "remote_audit_report"),
    Subsystem("cert", "证书与加密", "安全/证书", "cert", "cert_audit_report"),

    # ── v0.6.67：国内标准与 GMS 标准知识库（均经官方源实检，只读知识消费）──
    Subsystem("androidstd", "国内 App 隐私合规标准", "隐私/合规", "androidstd", "androidstd_compliance_report"),
    Subsystem("gmsstd", "GMS 兼容与 Play 标准", "隐私/合规", "gmsstd", "gms_compliance_report"),
    Subsystem("fdroidstd", "F-Droid 免 GMS 分发标准", "隐私/合规", "fdroidstd", "fdroid_compliance_report"),

    # ── v0.6.90：国内标准资源知识库（14 源：官方平台/协议规范/第三方/概念，只读知识消费）──
    Subsystem("cnstd", "国内标准资源（官方平台/协议规范/第三方/概念）", "标准/资源", "cnstd", "cnstd_report"),

    # ── v0.6.71：HarmonyOS/OpenHarmony 生态知识库（社区源 needs_verify，只读知识消费）──
    Subsystem("hmos_ecosystem", "鸿蒙生态工程知识（HAP/侧载/版图/版本/工具链）", "生态/鸿蒙", "hmos_ecosystem", "hmos_ecosystem_report"),

    # ── v0.6.72：HarmonyOS NEXT 标准与合规知识库（法规+官方+市场口径，只读知识消费）──
    Subsystem("hmosstd", "HarmonyOS 标准与合规（权限/隐私/上架/安全）", "隐私/合规", "hmosstd", "hmosstd_compliance_report"),

    # ── v0.6.73：黑箱逆向与调试工具链（UPX/GDB/MinGW 沙箱实测，只读不绕过）──
    Subsystem("reverse", "黑箱逆向与调试工具链（加壳识别/熵/节区/GDB）", "安全/逆向", "reverse", "reverse_report"),

    # ── v0.6.33 补齐：此前有模块、无登记，没能进统一开关与总览的六项 ──
    Subsystem("linux", "Linux 本机发行面", "系统/OS", "linux", "linux_report"),
    Subsystem("snapshot", "系统快照/对比", "快照", "snapshot", "snapshot_report"),
    Subsystem("compress", "压缩空间分析", "存储/压缩", "compress", "compress_report"),
    Subsystem("fonts", "字体与文本规范化", "应用/字体", "fonts", "text_normalize_report"),
    Subsystem("harmony_hdc", "鸿蒙 HDC 设备桥", "系统/OS", "harmony", "hdc_report"),
    Subsystem("harmony_device", "鸿蒙设备信息", "系统/OS", "harmony", "device_report"),

    # ── v0.6.34：兼容层串联（四层依赖模型，把 proton/dosbox/wsl/virtgpu 串成一条链）──
    Subsystem("compat", "兼容层串联", "兼容/串联", "compat", "compat_report"),

    # ── v0.6.35：元能力三项（清单自身 / 自检 / 边界声明，彼此联动）──
    Subsystem("subsystems", "统一子系统清单", "元能力", "subsystems", "list_subsystems"),
    Subsystem("linkage", "联动连轴", "元能力", "linkage", "linkage_report"),
    Subsystem("omni", "全能全知自检", "元能力", "omni", "omni_report"),
    Subsystem("docs", "文档与概念联动", "元能力/文档", "docs", "docs_report"),
    Subsystem("virt", "虚拟机环境", "系统/虚拟化", "virt", "virt_report"),
    Subsystem("packages", "软件包规范审计", "系统/包", "packages", "packages_report"),

    # ── v0.6.42：导入学习应用 + 网络/显示/元能力/场景透镜（全部只读、四入口接线）──
    Subsystem("apctrl", "AP 集中控制器", "网络/AP", "apctrl", "apctrl_report"),
    Subsystem("llvm", "LLVM 工具链", "语言/编译", "llvm", "llvm_report"),
    # ── 0000.0000.0000.0004.20261024：工具链全景（宿主工具链×仓库工具软件×目标架构矩阵，
    #    数据层 data/toolchain_catalog.json，只读实采；安装/构建/下载一律只给指引；
    #    #603 补全：10 类别 / 42 宿主条目 / 14 仓库工具 / 探针全覆盖 / 27 条新鲜度核实）──
    Subsystem("toolchain", "工具链全景", "语言/编译", "toolchain", "toolchain_report",
              version="0000.0000.0000.0002.20261024"),
    Subsystem("meshnet", "组网与设备协同", "网络/组网", "meshnet", "meshnet_report"),
    Subsystem("vdns", "虚拟根DNS与多CDN", "网络/DNS", "vdns", "vdns_report"),
    Subsystem("ipp", "IPP 打印发现", "应用/打印", "ipp", "ipp_report"),
    Subsystem("display", "现代显示与GPU", "硬件/显示", "display", "display_report"),
    Subsystem("retro", "常态化回头看", "元能力/演进", "retro", "retro_report"),
    Subsystem("restart", "人类文明重启透镜", "元能力/场景", "restart", "restart_report"),

    # ── v0.6.75：无线电技术与标准只读诊断（射频面/SDR 工具链/法规口径，绝不驱动发射）──
    Subsystem("radio", "无线电技术与标准（射频/SDR/法规）", "网络/射频", "radio", "radio_report"),
    # ── v0.6.76：开源 Windows 分析学习应用（目标环境/文件系统/运行时/工具链，只读不启动）──
    Subsystem("winternals", "开源 Windows 分析学习应用（工具链/内核锚点）", "系统/逆向", "winternals", "winternals_report"),
    Subsystem("qstore", "量子存储交换（ext4 4K 对齐/异构缓存管线）", "存储/量子", "qstore", "qstore_report"),
    Subsystem("qarch", "量子架构内核（Linux 6.18.57 LTS + arch/quantum）", "系统/内核", "qarch", "qarch_report"),
    Subsystem("asm", "汇编语言优化", "语言/汇编", "asm", "asm_report"),
    Subsystem("quantum", "量子程序与虚拟机", "计算/量子", "quantum", "quantum_report"),
]

BY_KEY: Dict[str, Subsystem] = {s.key: s for s in SUBSYSTEMS}
ALL_KEYS: List[str] = [s.key for s in SUBSYSTEMS]


# ─────────────────────────────────────────────────────────────────────────────
# 开关管理：默认态 / 读配置 / 写配置 / 单键置位
# ─────────────────────────────────────────────────────────────────────────────
def default_states() -> Dict[str, bool]:
    """返回默认开关态：所有子系统 default_on。"""
    return {s.key: s.default_on for s in SUBSYSTEMS}


def load_states() -> Dict[str, bool]:
    """读配置并与默认态合并；未知 key 忽略、缺文件回退默认。"""
    states = default_states()
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                user = json.load(fh)
            if isinstance(user, dict):
                for k, v in user.items():
                    if k in states and isinstance(v, bool):
                        states[k] = v
    except (OSError, ValueError):
        # 配置损坏：安全回退默认，不抛异常（绝不因配置问题阻断总览）
        pass
    return states


def save_states(states: Dict[str, bool]) -> None:
    """把开关态写入配置文件（仅写已知 key）。"""
    data = {k: bool(states.get(k, default_states().get(k, True))) for k in ALL_KEYS}
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError:
        # 写失败（无权限/只读家目录）不致命：开关仅当前进程生效
        pass


def set_enabled(key: str, on: bool) -> bool:
    """单键置位并落盘；key 不存在返回 False（不静默接受未知 key）。"""
    if key not in BY_KEY:
        return False
    states = load_states()
    states[key] = bool(on)
    save_states(states)
    return True


def is_enabled(key: str) -> bool:
    """查询某子系统当前是否开启（未知 key 视为关闭）。"""
    if key not in BY_KEY:
        return False
    return load_states().get(key, True)


# ─────────────────────────────────────────────────────────────────────────────
# 供 sysmap / CLI / GUI 消费的查询接口
# ─────────────────────────────────────────────────────────────────────────────
def enabled_subsystems() -> List[Subsystem]:
    """返回当前已开启的子系统（按登记顺序）。"""
    states = load_states()
    return [s for s in SUBSYSTEMS if states.get(s.key, True)]


def enabled_probes() -> List[Tuple[str, str, str, str, str]]:
    """返回已开启子系统的探测项元组：(key, label, layer, module, fn)。

    sysmap 按此枚举即调即求值，自动尊重开关。
    """
    return [(s.key, s.label, s.layer, s.module, s.fn) for s in enabled_subsystems()]


def list_subsystems() -> List[Dict[str, object]]:
    """返回全量子系统信息（含当前开/关），供 CLI `subsystems` 子命令与 GUI 面板展示。"""
    states = load_states()
    return [
        {
            "key": s.key,
            "label": s.label,
            "layer": s.layer,
            "module": s.module,
            "fn": s.fn,
            "enabled": states.get(s.key, True),
        }
        for s in SUBSYSTEMS
    ]
