"""联动连轴（v0.6.33）：把「你中有我」从一张关系图升级为**可体检的联通图**。

sysmap 的 RELATIONS 回答的是「谁和谁有关系」，但不回答三个更要命的问题：

1. **这条边到底是什么性质**？A 给 B 喂数据（供给）／A 决定 B 成不成立（门控）／
   两者互相佐证（印证）／B 的结果回流给 A（闭环）——性质不同，断掉时的后果不同。
2. **有没有接不上的**？登记进统一清单却一条边都没有的子系统，是「登记了但没嵌入」
   的假嵌入，必须显式暴露出来（孤岛检测）。
3. **边有没有写错**？端点 key 拼错、指向已下线的子系统，会静默失效（悬空轴自检）。

本模块就干这三件事，全程**只读、纯计算**：不调用任何子系统的报告函数，
只读统一清单（subsystems）与既有关系表（sysmap.RELATIONS），因此开销恒为零。

四类联动（kind）：

| kind | 含义 | 断掉的后果 |
|---|---|---|
| 供给 | A 的产出直接喂给 B（数据/能力流） | B 拿不到输入，能力打折 |
| 门控 | A 决定 B 能否成立（约束/前提） | B 成立前提没了，结论不可信 |
| 印证 | A 与 B 交叉验证同一事实 | 少一面镜子，误判风险上升 |
| 闭环 | B 的结果回流 A，形成保护/优化回路 | 只剩单向诊断，没有闭合动作 |

红线：本模块**只计算与展示**，绝不调用任何报告函数、绝不写任何状态。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from . import subsystems

__all__ = [
    "Axis", "KINDS", "AXES_EXTRA", "all_axes", "enabled_axes",
    "degrees", "isolated", "dangling", "linkage_stats", "linkage_report",
    "capabilities_report",
    "path", "reachable", "longest_chain", "chains_report",
    "graph", "layout", "svg", "ascii_graph",
]


@dataclass(frozen=True)
class Axis:
    """一条联动轴。方向有意义：from_key 流向/约束 to_key。"""
    from_key: str
    to_key: str
    kind: str
    desc: str


# 联动性质（顺序即报告展示顺序）
# 「串联」= v0.6.34 新增：同一条依赖链上的上下游（如兼容层四层模型：底座→设备→运行时→供给）
KINDS: Tuple[str, ...] = ("供给", "门控", "印证", "闭环", "串联", "关联")


# ── v0.6.33 新增联动轴（带方向与性质）──
# 说明：既有 sysmap.RELATIONS 会自动并入（kind 归为「关联」），这里只写
# 需要标明方向与性质的轴，避免两套维护同一条边（同 (from,to) 以既有边优先）。
AXES_EXTRA: List[Axis] = [
    # ── Linux 本机发行面：新登记，把它接到既有主干 ──
    Axis("linux", "distro", "供给",
         "linux 实读 /etc/os-release 的发行版结论直接喂给发行版能力层，后者据此匹配版本专属建议"),
    Axis("linux", "pkgmgr", "供给",
         "linux 探测到的包管理器（apt/dnf/pacman…）决定包管理层走哪套命令口径"),
    Axis("linux", "storage", "供给",
         "linux 的根分区用量是存储层的本机实时输入（已用/总量/空闲）"),
    Axis("linux", "syssoftware", "供给",
         "linux 的 journal 体积来自 systemd-journald，与系统软件栈同源"),
    Axis("linux", "kernel", "门控",
         "内核版本与发行版捆绑供给，内核调优项是否成立由发行面先定档"),

    # ── 压缩 / 快照：新登记，接到存储与保护闭环 ──
    Axis("compress", "storage", "供给",
         "压缩分析算出的可回收空间直接落在存储余量上：省空间这一件事由两侧共同完成"),
    Axis("snapshot", "compress", "印证",
         "压缩清出空间后，用前后两份快照的磁盘差值验证真实回收量，避免只信估算"),
    Axis("snapshot", "hardware", "印证",
         "快照的磁盘/内存实测与硬件本征读数互为佐证，任一侧跳变都值得复核"),
    Axis("snapshot", "durability", "供给",
         "连续快照给出容量与负载的时间序列，是设备保养包络的衰减斜率来源"),
    Axis("durability", "storage", "闭环",
         "保养建议（留余量、少写入）回流到存储健康面，形成「诊断→建议→再诊断」的闭合"),

    # ── 证书 / 远程 / 保护的反向闭环（既有边是 cert→durability，这里补回流）──
    Axis("durability", "cert", "闭环",
         "证书临近到期被写进资产保护清单，由设备保护侧推动续期，保护才真的闭合"),
    Axis("remote", "durability", "闭环",
         "远程接入审计发现的明文通道风险并入设备保护清单，统一收口到「通信能力保护」"),

    # ── 供电与环境安全（v0.6.38）：设备长期保障运行的供电环境维度 ──
    Axis("electrical", "durability", "闭环",
         "electrical 看设备外部与内部供电环境（回路质量/接地/负载），durability 看设备自身"
         "（电池/温度/SMART）；二者共同支撑「依据设备外部和内部环境自适应、保持长期保障运行」"),
    Axis("durability", "electrical", "供给",
         "设备保护的健康评估吸收供电环境结论（木座/铜铝/无接地→降载与重拉指引），保护建议才完整闭合"),

    # ── 外部设备连接与兼容（v0.6.39）：星闪/触控/USB-C PD/HID 的只读识别层 ──
    Axis("peripheral", "electrical", "供给",
         "外部温湿度计等外部感知设备经 peripheral 识别后，其读数喂给 electrical 做供电环境"
         "自适应（高温降载/高湿防蚀），外设是电气环境的外部输入"),
    Axis("peripheral", "durability", "供给",
         "外设（星闪/触控/USB）的连接质量与兼容状态是设备长期使用保护的外部输入"
         "（接口老化/连接损耗/供电波动），与设备自身维度共同支撑长期保障运行"),
    Axis("peripheral", "compat", "印证",
         "外设经 HID/USB/驱动被系统识别，兼容层结论与外设识别互相印证，任一侧缺驱动都值得复核"),

    # ── 时空与全维度管理器（v0.6.40）：量子/计算机原理 + 时间/空间/施时空组合/未来兼容透镜 ──
    Axis("chrono", "electrical", "供给",
         "chrono 施时空组合识别「某时刻负载高峰 ↔ 该时刻电气温度升高/写入放大」的纠缠，"
         "electrical 的供电环境自适应吸收该时序结论，做同步降载/防蚀"),
    Axis("chrono", "durability", "闭环",
         "chrono 时间维生命周期（provisioning→steady→aging→EOL）× 空间维资源占用 = "
         "设备长期保障的扩容/迁移/退役决策；只读观察给设备保护闭环提供维度依据"),
    Axis("chrono", "compat", "印证",
         "chrono 未来兼容维（标准 EOL / 后量子）与 compat 层版本兼容结论互相印证，"
         "近 EOL 标准须在前向兼容迁移里优先处理"),

    # ── 声学与音律（v0.6.87）：声音/频率/振动/音调/黄钟大吕四轴 ──
    Axis("acoustics", "radio", "印证",
         "声学的频率-波长-天线尺寸换算（c=f·λ）与 radio 的射频能力盘点互为印证："
         "同一波动几何下，喇叭尺寸与无线天线遵循同一条物理定律"),
    Axis("acoustics", "peripheral", "供给",
         "音频设备（喇叭/耳机/声卡）经 acoustics 只读枚举后，其能力面是外设连接与"
         "兼容判断的输入（耳机接口/WBCV 口径/USB 音频设备识别）"),
    Axis("acoustics", "chrono", "印证",
         "三分损益十二律配十二月（《淮南子·天文训》）是 chrono 时空维度的古典算例："
         "音律比例与历法节气同为「以数定时」的早期标准化工程"),
    Axis("radio", "acoustics", "印证",
         "radio 的 ISM/微功率合规口径与 acoustics 的频段波长表互相对账，"
         "433.92/2450/5800 MHz 三段的天线与绕射特性由 acoustics 给出物理解释"),

    # ── 系统基座（v0.6.88）：目录/包/仓库/检测 + 路径命名空间概念课 ──
    Axis("sysbase", "packages", "印证",
         "sysbase 的 deb/rpm 包数据库（dpkg -l / rpm -qa）与 packages 包可用性盘点互相印证："
         "同一个 metasploit-framework 的包记录是「已用包管理器安装」的判据"),
    Axis("sysbase", "pkgmgr", "供给",
         "sysbase 的本地包管理器存在性与 pkgmgr 的包管理职责同属一层："
         "dpkg/rpm 记账、apt/yum/dnf 解依赖——二者共享 FHS 约定的安装落点"),
    Axis("sysbase", "network", "印证",
         "sysbase 盘点 apt/yum 第三方仓库订阅（源/pin/keyring），network 做连通性体检："
         "订阅了什么源、pin 多少、信任哪把钥匙，是系统可信边界的变更记录"),
    Axis("sysbase", "cert", "闭环",
         "sysbase 的仓库 GPG 信任锚（公钥认证）与 cert 的证书加密同属信任链："
         "apt 信任锚是公钥不是 HTTPS；公钥分发是投毒软肋，与证书信任互为印证"),

    # ── 文档与概念联动（v0.6.88）：docs 作为联动网格文档层一等节点 ──
    Axis("docs", "subsystems", "供给",
         "docs 文档层登记进统一子系统清单，成为可开关的文档节点："
         "文档是各子系统知识的检索与审计承载，喂给清单的覆盖与分组展示"),
    Axis("docs", "linkage", "印证",
         "docs（54_系统基座 / 55_兼容层common）与联动轴互相印证："
         "文档交叉验证联动体检的「接没接上」（孤岛）与「接线接全了没有」（半截能力）"),
    Axis("docs", "sysbase", "印证",
         "docs 文档层与系统基座只读诊断互相印证，把概念系统的「联动连轴连动」"
         "沉淀为可审计文档——文档即统合整合的一环"),

    # ── 从零造系统学习应用（v0.6.89）：pepsipu 七仓库导入的只读学习层 ──
    Axis("sysdev", "hardware", "印证",
         "学习对象是 x86-32 手写分配器与 i386 保护模式玩具 OS——位宽/指令集/中断控制器"
         "这些「从零造系统」的底层假设，须与本机 hardware 实测（架构/位宽/CPU）对账，"
         "学的是哪一级硬件一目了然"),
    Axis("sysdev", "asm", "供给",
         "warpalloc 是 NASM 手写、aski 的 # 前缀内联汇编、xinOS 的 bootloader.asm——"
         "汇编子系统是「从零造系统」的工具上游，asm 的能力面决定能读哪一层源码"),
    Axis("sysdev", "docs", "供给",
         "导入学习应用的方法论（浅克隆→逐文件读→知识层→只读层→回灌）沉淀为 docs "
         "文档层可审计内容：学了什么、边界在哪（MIT/BSD 可学模式，无许可证默认保留所有权利）"),
    Axis("sysdev", "compat", "印证",
         "aski 的 while/for 未实现如实标注、ramenbox 按字节反射分发——学习源码里的"
         "「未实现/半截能力」与 compat 的「不适用 ≠ 已就绪」是同一诚实口径"),
    # ── 字体 ──
    Axis("fonts", "desktop", "供给",
         "字体规范化与字形回退决定桌面渲染是否出现豆腐块/重影，字体是桌面的上游"),
    Axis("fonts", "imagefmt", "印证",
         "文字渲染与图像解码共享图形栈，字体缺字形与图像缺解码器同属渲染链路缺口"),

    # ── 鸿蒙两只新登记项：接到 KaihongOS 主干 ──
    Axis("harmony_hdc", "harmony_device", "门控",
         "hdc 桥不通就拿不到设备信息：设备信息面以 HDC 通道为前提"),
    Axis("harmony_device", "kaihong", "印证",
         "真机设备信息与 KaihongOS 发行版探测互相印证，确认跑的是哪一套系统"),
    Axis("harmony_hdc", "android", "印证",
         "鸿蒙与安卓共用同一套调试桥思路（hdc / adb），两侧能力可交叉核对"),

    # ── 跨层闭环：共享计算与应急 ──
    Axis("distcompute", "durability", "门控",
         "共享算力的持续时间受设备保养包络约束：长期高负载会吃掉设备寿命，先问设备答不答应"),
    Axis("emergency", "durability", "闭环",
         "应急定位与设备保护共用「关键资产」清单，出事时两边指向同一批要保的东西"),
    Axis("importio", "settings", "供给",
         "外部导入的参数/阈值经导入层校验后写进参数注册表，成为可调阈值的输入"),

    # ── 孤岛清零：跨平台 OS 五面此前一条边都没有（登记了但没嵌入）──
    Axis("android", "linux", "门控",
         "安卓跑在 Linux 内核之上，内核面决定它能用哪些调度/IO/省电手段"),
    Axis("ios", "macos", "印证",
         "iOS 与 macOS 同属 Apple 生态、共享 Darwin 底座，两侧结论应能对上"),
    Axis("ios", "android", "印证",
         "移动端两端互为对照：同一条优化结论在 iOS 与 Android 上都应站得住"),
    Axis("macos", "unix", "印证",
         "macOS 属 Unix 系（Darwin 派生），与 unix 面共用一套用户态口径"),
    Axis("macos", "bsd", "印证",
         "Darwin 与 BSD 同源，手册与命令行工具口径近似，可交叉核对"),
    Axis("unix", "bsd", "印证",
         "BSD 是 Unix 的直接后裔，历史与接口同源，诊断结论互相印证"),
    Axis("unix", "linux", "印证",
         "同为 POSIX 系：用户态、权限模型、文件系统布局可对照诊断"),
    Axis("windows", "desktop", "供给",
         "Windows 的桌面会话/登录项由 windows 面探测，喂给桌面环境层做展示与建议"),
    Axis("windows", "storage", "印证",
         "Windows 卷/分区与存储层的文件系统健康互为佐证（NTFS 侧与 Linux 侧同看）"),
    Axis("windows", "linux", "印证",
         "跨平台兼容口径对照：同一优化项在 Windows 与 Linux 上的结论应能对上"),

    # ── 孤岛清零：第三方互联 / 资讯 / 遗留总览 ──
    Axis("thirdparty", "network", "供给",
         "第三方互联与硬件引用文档是网络面兼容结论的出处，供网络诊断引用"),
    Axis("webnews", "durability", "供给",
         "保养与优化资讯持续喂进设备保护的建议库，让保养建议跟得上最新实践"),
    Axis("legacy", "dos", "供给",
         "遗留/嵌入式总览是 DOS 面的上层聚合：先看总览再决定钻哪一层"),
    Axis("legacy", "busybox", "供给",
         "总览涵盖 busybox 嵌入式用户态，是嵌入式面的收口视图"),

    # ── v0.6.34：兼容层串联（四层依赖模型，上层能不能用取决于下层给不给得了）──
    Axis("arch", "compat", "门控",
         "架构决定兼容层能不能成立：x86 才能原生跑 Win32，ARM 上 Wine/Proton 口径完全不同"),
    Axis("kmod", "compat", "门控",
         "NT 同步原语（esync/fsync/NTSync）与内核模块版本门控，决定 Proton 这一类翻译层跑不跑得动"),
    Axis("distro", "compat", "供给",
         "32 位 i386 运行时与 wine/proton 包由发行版供给，发行版不给就装不上"),
    Axis("virtgpu", "compat", "供给",
         "兼容层要画得出画面，得有图形通路：Vulkan/VirtIO-GPU（venus）是它的下游供给"),
    Axis("compat", "proton", "串联",
         "兼容层串联把 Proton/Wine 作为 Windows 侧运行时收纳，先问底座再问运行时"),
    Axis("compat", "dosbox", "串联",
         "兼容层串联把 dosbox 作为 DOS 侧运行时收纳，与 Proton 同属「翻译别人家的调用」"),
    Axis("compat", "wsl", "串联",
         "兼容层串联把 WSL 作为反向桥收纳：别人在 Windows 上跑 Linux，方向相反、思路同源"),
    Axis("compat", "legacy", "串联",
         "兼容层串联以遗留/嵌入式总览做收口，DOS 与 busybox 是这条链的老端"),
    Axis("compat", "pkgmgr", "串联",
         "缺的运行时由包管理补上：串联的最后一跳是「谁来装」"),
    Axis("dosbox", "proton", "印证",
         "两者都是「在现系统跑旧/异平台软件」的翻译层，一个 DOS 一个 Windows，能力可互相印证"),

    # ── v0.6.35：全能全知自检（元能力，把「自述边界」接进主干）──
    Axis("subsystems", "omni", "供给",
         "统一清单是自检的数据源：登记项与 layer 决定覆盖面与能力域划分，清单变则自检结论变"),
    Axis("omni", "linkage", "印证",
         "两种欠账视角互相印证：linkage 查「接没接上主干」（孤岛），omni 查「接线接全了没有」（半截能力）"),
    Axis("omni", "compat", "印证",
         "compat 说「这一层缺了」，omni 说「这项入口缺了」——前者是运行时依赖，后者是工程接线，同属欠账"),

    # ── 虚拟机环境（v0.6.41）：让整体在不同 VM 内优雅降级 ──
    Axis("virt", "linux", "门控",
         "virt 识别到的虚拟化层（裸金属/KVM/VMware/Hyper-V/Xen/容器/WSL）决定哪些只读探针可用、"
         "哪些退化为概念观测：受限 VM 硬件/传感器退化，裸金属全开"),
    Axis("virt", "durability", "印证",
         "virt 虚拟硬件（vCPU/虚拟磁盘/balloon）的资源读数喂给 durability 做长期保障评估；"
         "虚拟磁盘 I/O 与物理盘不同，SMART 多不可用"),
    Axis("virt", "compat", "供给",
         "virt 内的兼容层（virtio/增强工具）可用性决定兼容层串联能否成立：无 virtio 则图形/设备通路退化"),

    # ── 软件包规范审计（v0.6.41）：按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对 ──
    Axis("packages", "pkgmgr", "供给",
         "packages 的包规范审计以 pkgmgr 探测到的包管理器为准：apt/dnf/pacman/brew/winget…各走各的规范口径"),
    Axis("packages", "linux", "门控",
         "包规范审计的前提是确认发行版与包管理器（由 linux/pkgmgr 供给），否则无法判定 install/uninstall/configure 合规"),
    Axis("packages", "compat", "印证",
         "packages 发现的不合规安装/残留与 compat 的运行时供给互相印证：缺的运行时由合规包管理补上"),

    # ── v0.6.42：导入学习应用 + 网络/显示/元能力/场景透镜（全部接入主干）──
    Axis("apctrl", "network", "供给",
         "apctrl 审计的 hostapd/NetworkManager 共享热点/dnsmasq 都落在网络层：AP 栈是网络接入点，结论喂给网络面"),
    Axis("apctrl", "dnshealth", "印证",
         "apctrl 看 dnsmasq 的 DHCP/DNS、vdns 看根 DNS，二者互为佐证：AP 内 DNS 与全局根 DNS 同看"),
    Axis("apctrl", "openwrt", "关联",
         "apcontroller 思路集中管理轻量 AP，与 OpenWrt 路由器（嵌入式 AP）视角互补：一个管 AP 群、一个管路由"),
    Axis("llvm", "compat", "供给",
         "llvm 交叉编译目标矩阵是兼容层运行时的来源之一：缺的跨平台运行时由 clang --target 补上（与 compat 串联最后一跳同口径）"),
    # ── 0004.20261024 工具链全景（toolchain）接入：编目复用 llvm 矩阵 / 架构门控 /
    #    包管理供给 / 兼容层仿真 / 逆向工具面 / 从零造系统，六处性质各异 ──
    Axis("llvm", "toolchain", "供给",
         "llvm 的交叉编译目标矩阵与 clang/lld/mlir 探针是 toolchain 全景编目的基座："
         "宿主 clang 18.1.3 与 NDK/OHOS 的 clang wrapper 同属 LLVM 家族，一处探测两处受益"),
    Axis("toolchain", "arch", "门控",
         "目标架构矩阵（x86_64/i686/PE32+/bionic×3/ohos musl）第一维就是 arch："
         "架构不成立则三元组与 sysroot 指引无意义"),
    Axis("toolchain", "pkgmgr", "供给",
         "宿主工具链由包管理供给（apt 的 gcc/mingw-w64/wine/lintian…）："
         "catalog 的 setup_steps 只给逻辑顺序，真正安装由 pkgmgr 侧用户确认"),
    Axis("toolchain", "compat", "供给",
         "兼容层运行时的仿真类工具链（qemu-user 8.2.2 / wine 9.0）登记在 catalog："
         "bionic qemu 三连坎与 musl 实跑通过的口径即 compat 串联的运行时证据"),
    Axis("toolchain", "reverse", "供给",
         "黑箱逆向工具链（UPX/GDB/MinGW）是 catalog 仓库工具软件的组成："
         "reverse 的沙箱实测结论回灌 catalog 的 security-detect 类别口径"),
    Axis("toolchain", "sysdev", "供给",
         "从零造系统（LFS/BLFS 口径）第一步就是基础工具链：catalog 的"
         "「什么是系统/基础工具链/系统关键组件」维度给 sysdev 供工具链全景底账"),
    Axis("toolchain", "winternals", "关联",
         "winternals 的目标环境判定含工具链存在性盘点（交叉系统先认系统与硬件）："
         "catalog 的 host_probe 实采正是该盘点的宿主侧数据源"),
    Axis("llvm", "arch", "门控",
         "交叉编译目标三元组首要就是架构（aarch64/armv7/riscv64/loongarch64…），架构不成立则目标矩阵无意义"),
    Axis("llvm", "pkgmgr", "供给",
         "交叉 sysroot/交叉工具链由包管理供给（gcc-aarch64-linux-gnu/mingw-w64…），llvm 与 pkgmgr 同源"),
    Axis("meshnet", "network", "供给",
         "meshnet 的 WireGuard P2P 网状是网络层的设备间直连拓扑，组网结论喂给网络面"),
    Axis("meshnet", "zerotier", "印证",
         "meshnet 与 ZeroTier 同为虚拟组网（一个 P2P 网状、一个 SD-WAN），设备间连通结论互相印证"),
    Axis("meshnet", "reshare", "供给",
         "meshnet 的设备能力适配（算力/GPU/存储缓存）与 reshare 的算力/网络共享同源：只共享算力网络、不共享个人数据"),
    Axis("vdns", "dnshealth", "供给",
         "vdns 的虚拟根 DNS（resolv.conf/DoH-DoT）是 dnshealth 解析链路的上游：根 DNS 健康决定解析健康"),
    Axis("vdns", "network", "印证",
         "vdns 看根 DNS 与多 CDN、network 看接口路由，二者共同决定「出得去、解析得到、选得优」"),
    Axis("ipp", "peripheral", "门控",
         "ipp 发现的打印机属外部设备（peripheral 范畴），外设连接质量决定打印能力是否成立"),
    Axis("ipp", "desktop", "供给",
         "ipp 打印机由桌面环境/系统设置管理，发现结论喂给桌面面做展示与建议"),
    Axis("display", "desktop", "供给",
         "display 的显示服务器与分辨率是桌面渲染的上游：图形栈能否画得出画面由 display 定档"),
    Axis("display", "virtgpu", "印证",
         "display 看 GPU/渲染后端、virtgpu 看虚拟化 GPU，二者互为佐证：无 virtio-GPU 则显示退化"),
    Axis("display", "peripheral", "关联",
         "display 推进图形化、peripheral 管外部显示设备（触控/USB-C），二者同属「看得见的界面」维度"),
    Axis("retro", "omni", "印证",
         "retro 的常态化回头看与 omni 的自检同源：一个查工程接线欠账、一个查长期保障欠账，同属持续演进"),
    Axis("retro", "subsystems", "供给",
         "retro 的维护节奏表按已登记子系统编排，清单变则回头看清单变"),
    Axis("restart", "durability", "关联",
         "restart 场景透镜把「设备长期保障」升维成文明级资产保护：保养包络与可复制资产同属长期主义"),
    Axis("restart", "electrical", "门控",
         "restart 维度清单以供电为前置（无电一切停摆），电气环境是文明重启的第一道门槛"),
    Axis("restart", "storage", "关联",
         "restart 强调知识库（规范/源码/教材）离线沉淀，存储健康决定知识资产能否留得住"),
    Axis("restart", "chrono", "关联",
         "restart 的「按什么序保命」与 chrono 的时间维生命周期同源：不可再生资产优先于可替代设备"),

    # ── v0.6.43：虚拟机完整运行支持 + 汇编语言优化 ──
    Axis("virt", "arch", "门控",
         "virt 完整运行支持依赖 CPU 虚拟化标志（vmx/svm）与嵌套开关，架构/指令集成立才谈得上嵌套与运行配置"),
    Axis("virt", "llvm", "供给",
         "virt 运行配置模板的生成与交叉构建可借助 LLVM/clang 交叉编译（guest 内工具链由 clang --target 供给）"),
    Axis("asm", "llvm", "供给",
         "asm 的 LLVM 交叉编译汇编指引直接复用 llvm 的交叉编译目标矩阵：clang -target=<triple> -S 生成跨架构汇编"),
    Axis("asm", "arch", "门控",
         "asm 的 SIMD 矩阵按架构分列（x86_64 的 SSE/AVX、aarch64 的 NEON/SVE、riscv64 的 RVV）：架构决定可用向量扩展"),
    Axis("asm", "compat", "印证",
         "asm 手写 intrinsics/内联汇编与 compat 的运行时供给互相印证：缺的跨平台运行时由对应工具链补上"),
    # ── v0.6.67 三个标准知识库（androidstd 国内 / gmsstd GMS / fdroidstd 免 GMS）接入主干 ──
    Axis("androidstd", "android", "门控",
         "国内标准（PIPL/GB-T/备案）是 android 端只读探针口径的合规门控：零权限、零采集、"
         "读失败降级正是国内标准的工程化自评基线，端侧任何越界采集都直接触发标准违规"),
    Axis("gmsstd", "fdroidstd", "印证",
         "两条分发通道标准互为印证：同一 APK 在 GMS 生态（Play Integrity/App Signing/targetSdk）"
         "与免 GMS 生态（F-Droid 反特征/可复现构建）双口径体检；国内无 GMS 场景下 fdroidstd 是 gmsstd 的替代通道"),
    Axis("fdroidstd", "android", "供给",
         "F-Droid 通道标准给 android 端供给分发形态输入：可直装（能下载即可安装）、零 GMS 依赖、"
         "零反特征——android 端只读探针的产物形态以此为准，入库主仓库或自建仓库均可分发"),

    # ── v0.6.90 国内标准资源知识库（cnstd：14 源）接入：资源层 / 协议工具层 / 引用分层三处 ──
    Axis("cnstd", "androidstd", "供给",
         "资源层给应用层供检索入口：androidstd 引用的 GB/T 35273/41391 等标准号，"
         "全文与状态在 cnstd 登记的官方三平台（openstd 全文 / std.samr 状态 / hbba 备案）可查——"
         "标准引用从「记得号」变成「查得到」，两侧都只读登记、不代查不代下载"),
    Axis("cnstd", "network", "供给",
         "协议规范与网络工具给 network 只读诊断供参照系：Modbus 六规范 / MQTT 是工业与物联网"
         "协议的事实标准坐标，net-merge 多链路合并 / ddns-go 动态解析是网络面的应用实例——"
         "network 诊断结论（链路/路由/DNS）可对照这些规范与工具的口径解释"),
    Axis("cnstd", "docs", "印证",
         "引用分层互相印证：cnstd 的「官方源 > 规范转载 > 第三方 > 科普」四层与 docs 的"
         "文档网格同构——本轮导入的头条科普文章（Claude Code/防火墙双轨制等）在 cnstd 里"
         "明确挂科普层，正式引用仍回一手规范，与 docs 的「文档即节点」原则一致"),

    # ── v0.6.69 量子程序与虚拟机：接到时空透镜 / 虚拟化层 / 硬件参照三处 ──
    Axis("quantum", "chrono", "供给",
         "chrono 的「量子/计算机原理」透镜维度由 quantum 供材料：态矢量模拟与内置算法"
         "（bell/ghz/teleport/grover）是可执行的量子原理演示，chrono 只读观察它而不重复实现"),
    Axis("virt", "quantum", "门控",
         "virt 识别本工具运行在裸金属/VM/容器哪一层后门控量子模拟规模：态矢量是 O(2^n) 内存敏感"
         "结构（MAX_QUBITS=20 需约 16 MB），受限 VM/容器环境据此降档可用位宽，不假装能跑大程序"),
    Axis("quantum", "hardware", "关联",
         "量子概念系统的硬件平台域（超导/离子阱/光量子等）与硬件标准参考互为参照："
         "本仓库只读登记不含量子硬件探针，两侧都不接真实量子设备，仅概念层互相索引"),

    # ── v0.6.71 鸿蒙生态工程知识（四仓库导入）接入：hdc 桥 / KaihongOS 发行版 /
    #    GMS 交叉口径 / 发行版版图方法论，四侧性质各异 ──
    Axis("hmos_ecosystem", "harmony_hdc", "供给",
         "HAP/侧载/工具链生态知识给 HDC 设备桥供场景口径：装 HAP 走 hdc install，"
         "侧载（FAA/Release 签名）结论直接决定 hdc 通道的调试边界，工程结构按 FA/Stage 双范式解释"),
    Axis("hmos_ecosystem", "gmsstd", "关联",
         "装 GMS 是两库交叉口径：HarmonyOS 4.x（AOSP 兼容层）侧载 GMS 三件套的实战知识"
         "（FCM 保活、多用户管控、版本边界）是 gmsstd 的鸿蒙特例，gmsstd 给 hmos_ecosystem 兼容性判据"),
    Axis("hmos_ecosystem", "distro", "印证",
         "生态版图映射方法论互相印证：distro 的发行版生态位登记法与 hmos_ecosystem 的"
         "发行版版图（OpenHarmony 商业发行版谱系）同构，两侧都只读登记、均不装不刷"),
    Axis("kaihong", "hmos_ecosystem", "供给",
         "KaihongOS 发行版实践给生态知识供材料：harmony_vs_openharmony 条目覆盖的"
         "兼容 HarmonyOS 的发行版定位即由此反向登记，生态知识本身不探测任何设备"),

    # ── v0.6.72 鸿蒙标准库（hmosstd）接入：双通道合规 / 共同上位法 / 标准-生态分工 /
    #    证明链与信任锚，四处性质各异 ──
    Axis("hmosstd", "gmsstd", "关联",
         "双通道合规互为口径：同一 App 出海走 Play（Data safety/Play Integrity）与"
         "上 AppGallery（隐私政策/备案/软著）是两套并行的上架口径，核对同一数据清单"),
    Axis("hmosstd", "androidstd", "关联",
         "共同上位法 PIPL 的双侧落地：鸿蒙侧（权限 APL/隐私指示器）与国内 Android 侧"
         "（权限合规/备案）对同一法规各有一套工程化翻译，互为参照系"),
    Axis("hmosstd", "hmos_ecosystem", "供给",
         "标准口径给生态知识定边界：hmos_ecosystem 回答生态事实（HAP/侧载/版图），"
         "hmosstd 给判定基线（侧载分发不入市场审核，但 PIPL 隐私义务不因通道而豁免）"),
    Axis("hmosstd", "cert", "门控",
         "证明链同构互证：HUKS 密钥 Attestation 证书链（TEE 证明）与 cert 子系统的"
         "信任锚/证书链校验是同一套「链上可信」思想在端侧与传输侧的两个实例"),

    # ── v0.6.73 黑箱逆向（reverse）接入：工具链供给 / 指令证据 / 签名链门控 /
    #    完整性检测关联，四处性质各异 ──
    Axis("llvm", "reverse", "供给",
         "llvm 工具链给黑箱分析供工具面：clang/llvm-objdump 多目标产出与反汇编能力，"
         "把『想分析什么就先造什么』的闭环接到 MinGW/UPX 实战链上"),
    Axis("reverse", "asm", "供给",
         "黑箱反汇编给 asm 供给指令级实证：实测 add 函数三条指令（endbr64/lea/ret）"
         "即调用约定与优化产物的活教材，asm 的 SIMD/intrinsics 指引以此校准"),
    Axis("reverse", "cert", "门控",
         "发布链顺序纪律门控：先签名后加壳才是可验的——加壳会改变分发物字节面，"
         "签名校验前被套壳等于把校验对象换掉；cert 的信任链据此给黑箱扫描定位"),
    Axis("reverse", "gmsstd", "关联",
         "完整性与壳的两面：Play Integrity 的 device signals 检篡改/调试/加壳，"
         "reverse 的三特征识别（UPX!/节名/熵）是同一检测能力的本地侧自检映照"),
    # ── v0.6.75 无线电技术与标准（radio）接入：射频物理面喂给组网 / 印证路由射频 ──
    Axis("radio", "meshnet", "供给",
         "radio 的射频物理面（rfkill/iw/蓝牙/总线器件）直接喂给 meshnet 的自组网："
         "设备有没有无线能力、regdom 合法信道，决定 WireGuard P2P 能不能起"),
    Axis("network", "radio", "关联",
         "network 的网络层结论与 radio 的射频物理面同一块网卡：2.4/5GHz 信道与发射功率"
         "合法上限由 regdom 决定，射频面异常网络层也跟着异常"),
    Axis("openwrt", "radio", "印证",
         "openwrt 的路由射频与 radio 的无线诊断互相印证：同一台设备的 Wi-Fi 网卡，"
         "一端看路由配置、一端看物理能力，结论对得上才算靠谱"),
    Axis("radio", "legacy", "关联",
         "radio 的射频 MCU（AVR/ESP32/STM32WL）正是 legacy 的嵌入式底座："
         "裸机/RTOS 上的射频信号处理与 DOS·busybox 嵌入式同源"),
    # ── v0.6.76 开源 Windows 分析学习应用（winternals）接入：工具链生态喂给逆向 ————
    Axis("winternals", "reverse", "供给",
         "winternals 登记的开源工具链（Ghidra / radare2·Cutter / x64dbg / dnSpyEx）"
         "正是 reverse 静态能力的生态坐标：reverse 负责解剖 PE/ELF 节区与算熵，"
         "winternals 回答『这套活儿在开源世界里由谁来做、各自什么许可证』"),
    Axis("windows", "winternals", "关联",
         "windows 是本机的 Windows 只读面，winternals 是 Windows 的分析生态面："
         "同一个目标系统一端看本机状态、一端看可对读锚点与工具坐标，"
         "两者都以『先判定环境再看目录』为前提"),
    Axis("proton", "winternals", "印证",
         "proton 的兼容层（Wine 的 Valve 衍生）与 winternals 的 Wine 条目互相印证："
         "同一套 Win32-to-POSIX 翻译，一端核验机器能不能跑 Windows 程序，"
         "一端登记它作为 Win32 语义批注参考的许可口径（LGPL-2.1）"),
    Axis("compat", "winternals", "关联",
         "compat 把 proton / dosbox / wsl / legacy 串成四层依赖链，"
         "而 winternals 的 Wine 与 ReactOS 正是这条链上『兼容实现』的知识侧："
         "WSL 还让 Windows 与 Linux 两套文件系统与目录约定在同一台机器上并存"),
    # ── v0.6.77 量子存储交换（qstore）接入：存储域 × 量子基座 × 异构端点 ─———
    Axis("qstore", "quantum", "供给",
         "qstore 是量子架构基座的存储域消费者：进制转换用 Π_k 置换矩阵编码门、"
         "端点握手用经典针脚、缓冲水位用 PiLink 链路统计——全部复用 quantum 的语义，"
         "绝不改基座本身"),
    Axis("storage", "qstore", "供给",
         "storage 的磁盘/文件系统只读面供给 qstore 的对齐核验：ext4 的 4K 块与 GPT "
         "分区起点正是『储存读取扫描索引』落盘前的第一道门槛，storage 看现状、"
         "qstore 看对齐与管线"),
    Axis("qstore", "virtgpu", "关联",
         "qstore 的 GPU 端点与 virtgpu 的虚拟化 GPU 互为两极：一端是宿主真实显卡"
         "（吞吐型缓冲），一端是虚机里的 virtio-GPU；两者经同一套 PCI 类别码口径"
         "识别，共同支撑异构端点建模"),
    # ── v0.6.78 量子架构内核（qarch）接入：内核侧存储/量子语义贯通 ─———
    Axis("qarch", "qstore", "印证",
         "qarch 的 4KiB 页纪律与 qstore 的 4K 对齐数列同源互证：字节流→12 位重组"
         " 4096 进制→4K 页，存储域口径从内核页粒度到用户态打包两层印证"),
    Axis("qarch", "quantum", "闭环",
         "qarch 的 QPU 模拟设备把 quantum 的 Π_k 门、8q 寄存器与 PiLink 链路"
         "语义带进内核（/dev/qpuN + UAPI），用户态基座与内核侧设备一一对应成环"),
]


def _label2key() -> Dict[str, str]:
    return {s.label: s.key for s in subsystems.SUBSYSTEMS}


def all_axes() -> List[Axis]:
    """本模块标注轴（有方向有性质）+ 既有关系表（sysmap.RELATIONS，归为「关联」），
    按 (from,to) 去重。

    同向重复时以**标注轴优先**——它带方向与性质（供给/门控/印证/闭环），
    信息量高于「关联」这一兜底分类。反向的同一对（A→B 与 B→A）不算重复：
    方向不同，是两条不同的轴。
    """
    from . import sysmap  # 惰性：避免与 sysmap 形成导入环

    l2k = _label2key()
    axes: List[Axis] = []
    seen = set()
    for ax in AXES_EXTRA:
        axes.append(ax)
        seen.add((ax.from_key, ax.to_key))
    for a, b, desc in sysmap.RELATIONS:
        ka, kb = l2k.get(a), l2k.get(b)
        if not ka or not kb or (ka, kb) in seen:
            continue
        axes.append(Axis(ka, kb, "关联", desc))
        seen.add((ka, kb))
    return axes


def enabled_axes() -> List[Axis]:
    """只保留两端子系统都已开启的联动轴（关闭项不参与联通）。"""
    states = subsystems.load_states()
    return [ax for ax in all_axes()
            if states.get(ax.from_key, False) and states.get(ax.to_key, False)]


def degrees() -> Dict[str, Dict[str, int]]:
    """每个登记项的联通度：出度（流向别人）/ 入度（被别人喂）/ 总度。"""
    deg: Dict[str, Dict[str, int]] = {
        s.key: {"out": 0, "in": 0, "total": 0} for s in subsystems.SUBSYSTEMS
    }
    for ax in all_axes():
        if ax.from_key in deg:
            deg[ax.from_key]["out"] += 1
        if ax.to_key in deg:
            deg[ax.to_key]["in"] += 1
    for d in deg.values():
        d["total"] = d["out"] + d["in"]
    return deg


def isolated() -> List[str]:
    """孤岛：登记进清单却一条联动边都没有的 key（允许两端任意方向）。"""
    deg = degrees()
    return [k for k, d in deg.items() if d["total"] == 0]


def dangling() -> List[Axis]:
    """悬空轴：端点 key 不在统一清单里（写错即静默失效，这里显式抓出来）。"""
    known = set(subsystems.ALL_KEYS)
    return [ax for ax in all_axes()
            if ax.from_key not in known or ax.to_key not in known]


def linkage_stats() -> dict:
    """结构化统计，供测试与其它模块复用（纯计算，零副作用）。"""
    axes = all_axes()
    enabled = enabled_axes()
    deg = degrees()
    by_kind: Dict[str, int] = {k: 0 for k in KINDS}
    for ax in enabled:
        by_kind[ax.kind] = by_kind.get(ax.kind, 0) + 1
    top = sorted(deg.items(), key=lambda kv: (-kv[1]["total"], kv[0]))[:5]
    return {
        "subsystems": len(subsystems.SUBSYSTEMS),
        "axes_total": len(axes),
        "axes_enabled": len(enabled),
        "by_kind": by_kind,
        "isolated": isolated(),
        "dangling": [(a.from_key, a.to_key) for a in dangling()],
        "top": [(k, d["total"]) for k, d in top],
        "degrees": deg,
    }


def linkage_report() -> tuple:
    """联动连轴体检报告（只读、纯计算）。返回 (True, msg)。

    五段：联动概览 / 按性质分组的联动轴（仅两端均已开启）/ 联通度最高节点 /
    孤岛清单 / 悬空轴自检。孤岛与悬空轴非空即为待修欠账，明确写出。
    """
    st = linkage_stats()
    enabled = enabled_axes()
    name = {s.key: s.label for s in subsystems.SUBSYSTEMS}

    out = []
    out.append("联动连轴体检（sysweeper · 你中有我，我中有你）")
    out.append("口径：联动 = 有方向、有性质（供给/门控/印证/闭环）的数据或约束流动")
    out.append("─" * 58)
    out.append("[联动概览]")
    out.append(f"  登记子系统 {st['subsystems']} 项 · 联动轴 {st['axes_total']} 条"
               f" · 当前生效 {st['axes_enabled']} 条（两端均已开启）")
    kinds = "  ".join(f"{k} {st['by_kind'].get(k, 0)}" for k in KINDS)
    out.append(f"  生效轴按性质：{kinds}")
    out.append("─" * 58)
    out.append("[联动轴 · 谁喂给谁 / 谁管着谁]")
    for kind in KINDS:
        group = [ax for ax in enabled if ax.kind == kind]
        if not group:
            continue
        out.append(f"  ▸ {kind}（{len(group)} 条）")
        for ax in group:
            out.append(f"     · {name.get(ax.from_key, ax.from_key)} → "
                       f"{name.get(ax.to_key, ax.to_key)}")
            out.append(f"       {ax.desc}")
    out.append("─" * 58)
    out.append("[联通度最高的节点]（度越高越是枢纽，改动它影响面最大）")
    for k, total in st["top"]:
        d = st["degrees"][k]
        out.append(f"  · {name.get(k, k):<18}总度 {total}（出 {d['out']} / 入 {d['in']}）")
    out.append("─" * 58)
    out.append("[孤岛检测 · 登记了但没接上的]")
    if st["isolated"]:
        for k in st["isolated"]:
            out.append(f"  · {name.get(k, k)}（{k}）—— 无任何联动边，属「登记未嵌入」欠账")
        out.append("  处置：补一条接进主干的联动轴，或确认它本就该独立")
    else:
        out.append("  · 无孤岛：所有登记项都至少接入一条联动轴")
    out.append("─" * 58)
    out.append("[悬空轴自检 · 端点写错的]")
    if st["dangling"]:
        for a, b in st["dangling"]:
            out.append(f"  · {a} → {b} —— 端点不在统一清单，该轴静默失效，需修正")
    else:
        out.append("  · 无悬空轴：全部端点均在统一清单内")
    return True, "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 串联：从「有边」升级到「能沿边走」——路径 / 可达 / 最长链
# ─────────────────────────────────────────────────────────────────────────────
def _adjacency(axes: List[Axis] = None) -> Dict[str, List[Axis]]:
    """出边邻接表：key → 从它出发的轴列表。"""
    adj: Dict[str, List[Axis]] = {s.key: [] for s in subsystems.SUBSYSTEMS}
    for ax in (axes if axes is not None else all_axes()):
        if ax.from_key in adj:
            adj[ax.from_key].append(ax)
    return adj


def path(from_key: str, to_key: str) -> List[Axis]:
    """沿联动轴做 BFS，返回从 `from_key` 到 `to_key` 的**最短串联链**（轴序列）。

    走不到返回 []（说明这两者之间没有串联关系，是两块互不相干的能力）。
    同起终点返回 []（自己到自己不算链）。
    """
    known = set(subsystems.ALL_KEYS)
    if from_key not in known or to_key not in known or from_key == to_key:
        return []
    adj = _adjacency()
    # BFS：记录到达每个节点时所走的那条轴，回溯即得链路
    prev: Dict[str, Axis] = {}
    seen = {from_key}
    queue = [from_key]
    while queue:
        cur = queue.pop(0)
        for ax in adj.get(cur, []):
            nxt = ax.to_key
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = ax
            if nxt == to_key:
                chain, node = [], nxt
                while node != from_key:
                    ax2 = prev[node]
                    chain.append(ax2)
                    node = ax2.from_key
                return list(reversed(chain))
            queue.append(nxt)
    return []


def reachable(from_key: str) -> List[str]:
    """从某节点出发沿联动轴能走到哪些节点（它**影响得到**的范围）。"""
    if from_key not in subsystems.ALL_KEYS:
        return []
    adj = _adjacency()
    seen, queue = {from_key}, [from_key]
    while queue:
        cur = queue.pop(0)
        for ax in adj.get(cur, []):
            if ax.to_key not in seen:
                seen.add(ax.to_key)
                queue.append(ax.to_key)
    seen.discard(from_key)
    return sorted(seen)


def longest_chain() -> Tuple[List[Axis], int]:
    """全图最长串联链（对所有节点对做 BFS 取最长），返回 (轴序列, 跳数)。

    用来回答「这个系统最深的串联有多深」——链越长说明跨层协作越深，
    也意味着链上任何一环断掉，影响面越大。
    """
    keys = list(subsystems.ALL_KEYS)
    best: List[Axis] = []
    for a in keys:
        for b in keys:
            if a == b:
                continue
            chain = path(a, b)
            if len(chain) > len(best):
                best = chain
    return best, len(best)


def chains_report() -> tuple:
    """串联体检报告（纯计算）：最长链 + 每个节点的串联深度 + 一条示范链。

    「串联深度」= 从该节点出发最远能走几跳；深度为 0 即**终点节点**
    （只被别人喂、不喂别人），是串联的收口处。
    """
    chain, hops = longest_chain()
    name = {s.key: s.label for s in subsystems.SUBSYSTEMS}

    out = ["串联体检（沿联动轴走一遍：不是只画边，是要能沿边走通）"]
    out.append("─" * 58)
    out.append("[最长串联链]")
    if chain:
        nodes = [name.get(chain[0].from_key, chain[0].from_key)]
        out.append("  " + " → ".join(nodes + [name.get(ax.to_key, ax.to_key) for ax in chain]))
        out.append(f"  共 {hops} 跳；每跳的性质：")
        for i, ax in enumerate(chain, 1):
            out.append(f"    {i}. [{ax.kind}] {name.get(ax.from_key, ax.from_key)} → "
                       f"{name.get(ax.to_key, ax.to_key)}｜{ax.desc}")
    else:
        out.append("  · 无（图中不存在可走通的路径）")
    out.append("─" * 58)
    out.append("[串联深度 Top · 谁的影响面最深]")
    depth = {k: 0 for k in subsystems.ALL_KEYS}
    for k in subsystems.ALL_KEYS:
        # 深度 = 从该点出发的最远跳数（BFS 层数）
        adj = _adjacency()
        seen, frontier = {k}, [k]
        d = 0
        while frontier:
            nxt = []
            for cur in frontier:
                for ax in adj.get(cur, []):
                    if ax.to_key not in seen:
                        seen.add(ax.to_key)
                        nxt.append(ax.to_key)
            if not nxt:
                break
            d += 1
            frontier = nxt
        depth[k] = d
    top = sorted(depth.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    for k, d in top:
        out.append(f"  · {name.get(k, k):<22}深度 {d}（可达 {len(reachable(k))} 项）")
    out.append("─" * 58)
    out.append("[示范 · 兼容层四层串联]")
    demo = path("arch", "pkgmgr")
    if demo:
        out.append("  " + " → ".join([name.get(demo[0].from_key, demo[0].from_key)]
                                     + [name.get(ax.to_key, ax.to_key) for ax in demo]))
        out.append("  读法：装兼容运行时之前先看底座——箭头左边是右边能不能成立的前提。")
    else:
        out.append("  · 当前无 arch→pkgmgr 串联链")
    return True, "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 图形：把联通图交给 GUI 画 / 导出 SVG / 命令行 ASCII
# ─────────────────────────────────────────────────────────────────────────────
# 每种性质一个颜色（GUI 与 SVG 共用，保证两处观感一致）
KIND_COLORS: Dict[str, str] = {
    "供给": "#2e7d32",   # 绿：数据/能力流
    "门控": "#c62828",   # 红：前提约束，断了最要命
    "印证": "#1565c0",   # 蓝：交叉验证
    "闭环": "#6a1b9a",   # 紫：结果回流
    "串联": "#ef6c00",   # 橙：同一条依赖链的上下游
    "关联": "#78909c",   # 灰：既有关系表归并
}


def graph() -> dict:
    """结构化图数据（GUI 画 Canvas / 导出 SVG 共用，纯计算）。

    返回 {nodes:[{key,label,layer,out,in,total}], edges:[{from,to,kind,desc,color}],
          layers:[层名…]}。节点按 layer 分组，便于分层布局。
    """
    deg = degrees()
    name = {s.key: s.label for s in subsystems.SUBSYSTEMS}
    layer_of = {s.key: s.layer for s in subsystems.SUBSYSTEMS}
    layers: List[str] = []
    for s in subsystems.SUBSYSTEMS:
        if s.layer not in layers:
            layers.append(s.layer)
    nodes = [{"key": s.key, "label": s.label, "layer": s.layer,
              "out": deg[s.key]["out"], "in": deg[s.key]["in"],
              "total": deg[s.key]["total"]} for s in subsystems.SUBSYSTEMS]
    edges = [{"from": ax.from_key, "to": ax.to_key, "kind": ax.kind,
              "desc": ax.desc, "color": KIND_COLORS.get(ax.kind, "#78909c"),
              "from_label": name.get(ax.from_key, ax.from_key),
              "to_label": name.get(ax.to_key, ax.to_key)}
             for ax in all_axes()]
    return {"nodes": nodes, "edges": edges, "layers": layers}


def layout(g: dict, width: int, height: int) -> Dict[str, Tuple[float, float]]:
    """分层布局：每层占一列（层多则折行），层内节点等距竖排。纯函数，可单测。"""
    pos: Dict[str, Tuple[float, float]] = {}
    layers = g["layers"]
    cols = max(1, min(len(layers), 6))          # 最多 6 列，超出折行
    rows = (len(layers) + cols - 1) // cols
    cell_w = width / (cols + 0.5)
    cell_h = height / (rows + 0.5)
    for li, layer in enumerate(layers):
        members = [n for n in g["nodes"] if n["layer"] == layer]
        col, row = li % cols, li // cols
        x0 = cell_w * (col + 0.5)
        y0 = cell_h * (row + 0.5)
        span = cell_h * 0.86
        for i, n in enumerate(members):
            t = (i + 0.5) / max(1, len(members))
            pos[n["key"]] = (x0, y0 - span / 2 + span * t)
    return pos


def svg(width: int = 1280, height: int = 900) -> str:
    """把联动图渲染成**纯标准库生成**的 SVG 字符串（零依赖、可离线看、可直接贴网页）。

    分层布局 + 按性质着色的有向边。只返回字符串，**不写任何文件**——
    是否落盘、落到哪里由调用方（CLI `--svg PATH` 或 GUI 另存为）决定。
    """
    g = graph()
    pos = layout(g, width, height)
    esc = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           f'<text x="16" y="26" font-family="sans-serif" font-size="18" '
           f'font-weight="bold" fill="#222">sysweeper 联动连轴图</text>',
           f'<text x="16" y="46" font-family="sans-serif" font-size="12" fill="#666">'
           f'{len(g["nodes"])} 个子系统 · {len(g["edges"])} 条联动轴（颜色=性质）</text>']
    # 图例
    lx, ly = 16, 62
    for kind in KINDS:
        out.append(f'<rect x="{lx}" y="{ly - 9}" width="12" height="12" '
                   f'fill="{KIND_COLORS.get(kind, "#78909c")}"/>')
        out.append(f'<text x="{lx + 18}" y="{ly}" font-family="sans-serif" '
                   f'font-size="12" fill="#444">{esc(kind)}</text>')
        lx += 74
    # 边（带箭头）
    out.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" '
               'orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#888"/></marker></defs>')
    for e in g["edges"]:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b:
            continue
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" '
                   f'stroke="{e["color"]}" stroke-width="1.1" stroke-opacity="0.55" '
                   f'marker-end="url(#arrow)"><title>{esc(e["from_label"])} → '
                   f'{esc(e["to_label"])}［{esc(e["kind"])}］{esc(e["desc"])}</title></line>')
    # 节点
    for n in g["nodes"]:
        x, y = pos.get(n["key"], (0, 0))
        r = 4 + min(8, n["total"])  # 度越大点越大
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#37474f" '
                   f'fill-opacity="0.85"><title>{esc(n["label"])}（{esc(n["layer"])}）'
                   f'入 {n["in"]} / 出 {n["out"]}</title></circle>')
        out.append(f'<text x="{x + r + 3:.1f}" y="{y + 4:.1f}" font-family="sans-serif" '
                   f'font-size="9" fill="#333">{esc(n["label"])}</text>')
    out.append("</svg>")
    return "\n".join(out)


def ascii_graph(max_edges_per_node: int = 3) -> str:
    """命令行用的 ASCII 分层邻接图（按层分组，列出每个节点的出边目标）。"""
    g = graph()
    out = ["ASCII 联动图（按层分组 · 只列出边的前 %d 个目标）" % max_edges_per_node]
    for layer in g["layers"]:
        members = [n for n in g["nodes"] if n["layer"] == layer]
        if not members:
            continue
        out.append(f"▸ {layer}（{len(members)} 项）")
        for n in members:
            outs = [e for e in g["edges"] if e["from"] == n["key"]]
            if not outs:
                out.append(f"   · {n['label']}  （无出边，串联收口点）")
                continue
            shown = outs[:max_edges_per_node]
            tail = "" if len(outs) <= max_edges_per_node else f" …等 {len(outs)} 条"
            out.append(f"   · {n['label']} → " + "、".join(
                f"{e['to_label']}[{e['kind']}]" for e in shown) + tail)
    return "\n".join(out)


def capabilities_report() -> tuple:
    """本层能力自检（GUI/CLI 通用入口）：清单覆盖 / 轴覆盖 / 孤岛 / 悬空。

    返回 (ok, msg)：**无孤岛且无悬空轴才算 ok=True**——二者都是待修欠账，
    自检就该如实报「未完成」，而不是一律打勾糊过去。
    """
    st = linkage_stats()
    name = {s.key: s.label for s in subsystems.SUBSYSTEMS}
    out = ["联动连轴层能力自检（纯计算、零副作用）"]
    out.append(f"  · 统一清单登记项：{st['subsystems']} 项")
    out.append(f"  · 联动轴：{st['axes_total']} 条（当前生效 {st['axes_enabled']} 条）")
    out.append("  · 轴性质分类：" + "、".join(
        f"{k} {st['by_kind'].get(k, 0)}" for k in KINDS))
    covered = st["subsystems"] - len(st["isolated"])
    out.append(f"  · 联通覆盖率：{covered}/{st['subsystems']} 项至少接入一条轴")
    if st["isolated"]:
        out.append("  · 孤岛（登记了但没接上）："
                   + "、".join(name.get(k, k) for k in st["isolated"]))
    else:
        out.append("  · 孤岛：无")
    if st["dangling"]:
        out.append("  · 悬空轴（端点写错）："
                   + "、".join(f"{a}→{b}" for a, b in st["dangling"]))
    else:
        out.append("  · 悬空轴：无")
    ok = not st["isolated"] and not st["dangling"]
    out.append(f"  · 结论：{'全部登记项均已接入联动轴，无悬空' if ok else '存在待修项（见上）'}")
    return ok, "\n".join(out)
