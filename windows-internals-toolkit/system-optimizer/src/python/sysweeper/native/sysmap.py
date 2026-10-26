"""系统统筹总览（v0.6.22）——「你中有我，我中有你」的关联诊断引擎。

v0.6.22 重构：从「硬编码零散子集」升级为「统一清单 + 可配置开关 + 全量嵌入」。

- 编排清单改为单一事实源 ``native.subsystems``：凡是 native 层里能嵌入整体系统的
  只读诊断——不论 firmware（固件）/ plugins（插件）/ modules（内核模块）/ kernel /
  storage / container / hardware / 跨平台 OS 探测等——都在清单登记，不再零散硬编码。
- 选项开关：每个子系统可在 ``~/.config/sysweeper/subsystems.json`` 关闭；本总览只枚举
  **已开启**的探测项（即调即求值、尊重开关），关闭的子系统既不诊断也不展示。
- 关联关系（RELATIONS）扩到全量，且仅在**两端都已启用**时才画出，避免指向已关闭节点。

红线（与全工具一致，且本层更严）：仅做**只读聚合与关联**——
  不启停任何服务、不改任何配置、不连控制端口写命令、不写入任何系统状态。
  某个子系统诊断异常时只标「异常」并跳过，不影响整体总览。

兼容：``PROBES`` / ``RELATIONS`` 仍作为模块级常量对外暴露（5 元组 / 3 元组），
供既有测试与调用方使用；两者均从 ``subsystems`` 登记派生，标签保持一致。
"""
from __future__ import annotations

import importlib
from typing import Dict, List, Tuple

from . import subsystems

# ── 兼容常量（派生自统一清单，标签与 subsystems 一致）──
# PROBES: (key, label, layer, module, fn)
PROBES: List[Tuple[str, str, str, str, str]] = [
    (s.key, s.label, s.layer, s.module, s.fn) for s in subsystems.SUBSYSTEMS
]
# RELATIONS: (A label, B label, 关系说明) —— 端点用 label，与 PROBES 标签一致
RELATIONS: List[Tuple[str, str, str]] = [
    # 原有耦合（v0.6.18 → v0.6.21）
    ("网络接口/路由", "DNS 解析", "网络连通以 DNS 解析为前提；dnshealth 与 nm_resolved 互补诊断"),
    ("DNS 解析", "Tor 覆盖层", "Tor 启用 DNSPort 时，应用解析经洋葱流转，解析隐私提升"),
    ("Tor 覆盖层", "ZeroTier 虚拟组网", "同为网络覆盖层：Tor 偏匿名、ZeroTier 偏组网，可叠加使用"),
    ("OSI 七层", "网络接口/路由", "OSI 七层以 network 的 L1-L4 本征为底座，逐层上探"),
    ("Proton 兼容层", "虚拟化/GPU", "游戏渲染依赖 Vulkan/VirtIO-GPU（venus）后端加速"),
    ("Proton 兼容层", "内核模块", "兼容依赖 NTSync/fsync 同步原语（内核版本门控）"),
    ("Proton 兼容层", "发行版能力", "32 位 i386 运行时供给由发行版包管理决定兼容前提"),
    ("浏览器引擎", "DNS 解析", "引擎兼容依赖解析链路健康"),
    ("ZeroTier 虚拟组网", "本地自组网", "跨网虚拟组网(ZeroTier) 与 近场自组网(meshchat) 是组网两端"),
    ("虚拟化/GPU", "内核模块", "GPU/虚拟化能力受内核模块与 CPU 虚拟化标志约束"),
    ("WSL 子系统", "网络接口/路由", "WSL2 经 virtio-net，可与宿主机网络/ZeroTier 叠加"),
    ("KaihongOS 发行版", "发行版能力", "KaihongOS 是深开鸿基于 OpenHarmony 的具体发行版；"
                               "发行版能力探测涵盖其系统栈，鸿蒙通用探测(hdc/HiLog/Stage/"
                               "SysCap/分布式)为其上层能力"),
    ("图像编解码能力", "浏览器引擎", "WebP/AVIF/HEIC 等格式渲染依赖同一编解码底座，"
                               "图像优化与网页渲染共享解码链路"),
    ("图像编解码能力", "发行版能力", "编解码工具链(libheif/libavif/libwebp/libjxl/ImageMagick)"
                               "由发行版包管理供给，缺失即图像优化链路受限"),
    ("遗留 DOS 环境", "可启动介质制作能力", "DOS 启动软盘复用 livemedia 的 mtools/syslinux 工具链"),
    ("busybox 嵌入式用户态", "KaihongOS 发行版", "busybox 与 OpenWrt 同源思路(单二进制撑起工具集)，"
                                    "嵌入式/路由器根用户态视角互补"),
    ("busybox 嵌入式用户态", "可启动介质制作能力", "多数发行版 live ISO 的 initramfs 早期用户态即 busybox"),
    ("dosbox 模拟兼容层", "Proton 兼容层", "二者都是「在现系统跑旧/异平台软件」的兼容层，"
                               "一个 DOS、一个 Windows"),
    ("dosbox 模拟兼容层", "WSL 子系统", "都是把旧运行环境搬到现系统的桥(模拟 vs 子系统)"),
    ("遗留 DOS 环境", "dosbox 模拟兼容层", "DOS 环境既可直接跑(DOSEMU2)也可模拟跑(dosbox)，两条路径互补"),
    # v0.6.22 全量嵌入新增耦合
    ("内核模块", "固件(firmware)", "内核模块与固件同源，驱动加载依赖对应固件镜像（kmod 与 firmware 同属内核资源面）"),
    ("内核模块", "已加载模块", "已加载模块即内核模块当前运行实例"),
    ("固件(firmware)", "硬件本征", "固件决定硬件能力边界（如 GPU/网卡/SSD 控制器固件）"),
    ("内核模块", "内核调优(sysctl)", "内核模块与内核 sysctl 调优同属内核面，互相影响"),
    ("已加载模块", "虚拟化/GPU", "VirtIO-GPU/venus 等虚拟化能力依赖对应内核模块"),
    ("包管理", "发行版能力", "包管理由发行版决定可用软件集合，是发行版能力的供给侧"),
    ("插件(plugins)", "系统软件栈", "插件运行于系统软件栈之上（浏览器扩展/systemd 单元/桌面组件等）"),
    ("插件白名单", "插件(plugins)", "白名单约束插件加载范围，是插件的安全闸门"),
    ("容器运行时", "内核模块", "容器依赖 namespace/cgroup 等内核能力（由模块/sysctl 提供）"),
    ("容器运行时", "存储/文件系统", "容器镜像与层存储依赖底层文件系统（overlayfs/btrfs/zfs）"),
    ("存储/文件系统", "硬件本征", "存储健康受硬件约束（SMART/NVMe/看门狗等）"),
    ("OpenWrt 路由器", "busybox 嵌入式用户态", "OpenWrt 根用户态即 busybox 同源，路由器与嵌入式视角互补"),
    ("OpenWrt 路由器", "网络接口/路由", "路由器本质是网络枢纽，承载接口/路由/防火墙"),
    ("分布式计算", "跨机派活", "distjob 经组网把 distcompute 的工作单元派出去、把结果收回来"),
    ("跨机派活", "本地自组网", "distjob 载荷经 meshchat 文本通道派发（通道里传参数不传代码）"),
    ("算力/网络共享", "分布式计算", "reshare 共享的算力/网络供给 distcompute 运行"),
    ("预警应急定位", "网络接口/路由", "定位以网络+基站为首选基线，网络异常会影响定位可用性"),
    ("网络隐私验证", "Tor 覆盖层", "netauth 按网络维度做隐私验证，与 Tor 匿名互相印证"),
    ("网络链接协议", "网络接口/路由", "netlink 是网络配置通道（L2-L3），与 iproute2 同源"),
    ("桌面环境", "浏览器引擎", "桌面环境承载浏览器，渲染依赖同一图形栈"),
    ("桌面环境", "系统软件栈", "桌面依赖 systemd/显示栈(pipewire/wayland) 等系统软件"),
    ("架构/指令集", "内核模块", "内核模块/固件受架构约束（x86/ARM/RISC-V/LoongArch）"),
    ("单板机(SBC)", "硬件本征", "SBC 是硬件本征的具象板型（设备树/thermal/降频位）"),
    ("单板机(SBC)", "固件(firmware)", "SBC 启动固件(UEFI/UBoot)决定能力边界"),
    ("KaihongOS 发行版", "硬件本征", "KaihongOS 适配具体硬件（板型/驱动/固件）"),
    ("小程序端映射", "浏览器引擎", "小程序运行于浏览器/引擎内核之上（渲染与 JS 引擎共用）"),
    ("OpenJDK-JVM", "发行版能力", "JDK/JVM 由发行版包管理供给（openjdk 包 + 缓存）"),
    ("网络隐私验证", "网络链接协议", "netauth 验证维度落在网络层，与 netlink 配置口径呼应"),
    # v0.6.30-31 新增耦合：设备保护 / 远程接入 / 证书加密 互相嵌入
    ("证书与加密", "远程接入审计", "SSH/SFTP 的强度即证书链与加密库：远程接入是否可信，取决于证书与算法是否受支持"),
    ("证书与加密", "设备长期使用保护", "durability 的资产保护段吸收 cert 的证书/TPM 状态，一并保护密钥与通信能力"),
    ("设备长期使用保护", "硬件本征", "保养包络由传感器读数推导，而读数（电池/温度/SMART）来自硬件本征"),
    ("设备长期使用保护", "网络接口/路由", "通信能力是设备长期可用的一环：链路 down 即进入资产保护清单"),
    ("供电与环境安全", "设备长期使用保护", "electrical 的供电环境维度与 durability 的设备自身维度共同支撑「长期保障运行」，互为输入"),
    ("外部设备连接与兼容", "供电与环境安全", "外部温湿度计等外部感知设备经 peripheral 识别后喂给 electrical 做环境自适应（温度降载/湿度防蚀）"),
    ("外部设备连接与兼容", "设备长期使用保护", "外设连接质量与兼容状态（接口老化/供电波动）是设备长期保护的外部输入，与设备自身维度共同支撑长期保障运行"),
    ("外部设备连接与兼容", "兼容层串联", "外设经 HID/USB/驱动被识别，兼容层结论与外设识别互相印证"),
    # v0.6.40 新增耦合：时空与全维度管理器把各维统一进观察框架
    ("时空与全维度管理器", "供电与环境安全", "chrono 施时空组合识别「某时刻负载高峰 ↔ 该时刻电气温度升高/写入放大」的纠缠，喂给 electrical 做同步降载防蚀"),
    ("时空与全维度管理器", "设备长期使用保护", "chrono 时间维生命周期 × 空间维资源占用 = 设备长期保障的扩容/迁移/退役决策依据"),
    ("时空与全维度管理器", "兼容层串联", "chrono 未来兼容维（标准 EOL/后量子）与 compat 版本兼容结论互相印证，近 EOL 标准优先前向迁移"),
    ("远程接入审计", "网络接口/路由", "telnet/明文 FTP 的风险只在不可信网络上成立，网络面决定暴露面"),
    # v0.6.33 新增耦合：补齐六个此前未登记模块 + 跨平台 OS 孤岛清零
    ("Linux 本机发行面", "发行版能力", "linux 实读 /etc/os-release 的发行版结论直接喂给发行版能力层"),
    ("Linux 本机发行面", "存储/文件系统", "根分区用量是存储层的本机实时输入（已用/总量/空闲）"),
    ("Linux 本机发行面", "内核调优(sysctl)", "内核版本由发行版捆绑供给，调优项先过发行面定档"),
    ("Linux 本机发行面", "包管理", "包管理器探测结果决定包管理层走哪套命令口径"),
    ("压缩空间分析", "存储/文件系统", "压缩算出的可回收空间直接落在存储余量上，省空间由两侧共同完成"),
    ("系统快照/对比", "硬件本征", "快照的磁盘/内存实测与硬件本征读数互为佐证"),
    ("系统快照/对比", "设备长期使用保护", "连续快照的时间序列给出设备保养包络的衰减斜率"),
    ("字体与文本规范化", "桌面环境", "字体规范化与字形回退决定桌面渲染会不会出现豆腐块/重影"),
    ("鸿蒙 HDC 设备桥", "鸿蒙设备信息", "hdc 桥不通就拿不到设备信息，前者是后者的前提"),
    ("鸿蒙设备信息", "KaihongOS 发行版", "真机设备信息与发行版探测互相印证，确认跑的是哪一套系统"),
    ("Android 设备", "Linux 本机发行面", "安卓跑在 Linux 内核之上，内核/发行面决定它能用哪些调度与省电手段"),
    ("iOS 设备", "macOS 系统", "iOS 与 macOS 同属 Apple 生态、共享 Darwin 底座，两侧结论应能对上"),
    ("iOS 设备", "Android 设备", "移动端两端互为对照：同一条优化结论在 iOS 与 Android 上都应站得住"),
    ("macOS 系统", "Unix/Solaris", "macOS 属 Unix 系（Darwin 派生），与 unix 面共用一套用户态口径"),
    ("macOS 系统", "BSD 系统", "Darwin 与 BSD 同源，手册与命令行工具口径近似，可交叉核对"),
    ("Unix/Solaris", "BSD 系统", "BSD 是 Unix 的直接后裔，历史与接口同源，诊断结论互相印证"),
    ("Unix/Solaris", "Linux 本机发行面", "同为 POSIX 系：用户态、权限模型、文件系统布局可对照诊断"),
    ("Windows 系统", "桌面环境", "Windows 的桌面会话/登录项由 windows 面探测，喂给桌面环境层"),
    ("Windows 系统", "存储/文件系统", "Windows 卷/分区与存储层文件系统健康互为佐证（NTFS 侧与 Linux 侧同看）"),
    ("Windows 系统", "Linux 本机发行面", "跨平台兼容口径对照：同一优化项在 Windows 与 Linux 上的结论应能对上"),
    ("第三方互联", "网络接口/路由", "第三方互联与硬件引用文档是网络面兼容结论的出处"),
    ("优化资讯知识库", "设备长期使用保护", "保养与优化资讯持续喂进设备保护的建议库，让建议跟得上最新实践"),
    ("遗留/嵌入式总览", "遗留 DOS 环境", "总览是 DOS 面的上层聚合：先看总览再决定钻哪一层"),
    ("遗留/嵌入式总览", "busybox 嵌入式用户态", "总览涵盖 busybox 嵌入式用户态，是嵌入式面的收口视图"),
    # v0.6.41 新增耦合：虚拟机环境（让整体在不同 VM 内优雅降级）
    ("虚拟机环境", "Linux 本机发行面", "virt 识别到的虚拟化层（裸金属/KVM/VMware/Hyper-V/Xen/容器/WSL）决定哪些只读探针可用、哪些退化为概念观测"),
    ("虚拟机环境", "设备长期使用保护", "virt 虚拟硬件（vCPU/虚拟磁盘/balloon）的资源读数喂给 durability 做长期保障评估；虚拟磁盘 SMART 多不可用"),
    ("虚拟机环境", "兼容层串联", "virt 内的兼容层（virtio/增强工具）可用性决定兼容层串联能否成立：无 virtio 则图形/设备通路退化"),
    # v0.6.41 新增耦合：软件包规范审计（按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对）
    ("软件包规范审计", "包管理", "packages 的包规范审计以 pkgmgr 探测到的包管理器为准：apt/dnf/pacman/brew/winget…各走各的规范口径"),
    ("软件包规范审计", "Linux 本机发行面", "包规范审计的前提是确认发行版与包管理器（由 linux/pkgmgr 供给），否则无法判定 install/uninstall/configure 合规"),
    ("软件包规范审计", "兼容层串联", "packages 发现的不合规安装/残留与 compat 的运行时供给互相印证：缺的运行时由合规包管理补上"),
    # v0.6.42 新增耦合：导入学习应用 + 网络/显示/元能力/场景透镜
    ("AP 集中控制器", "网络接口/路由", "apctrl 审计的 hostapd/NetworkManager 共享热点/dnsmasq 都落在网络层：AP 栈是网络接入点"),
    ("AP 集中控制器", "DNS 解析", "apctrl 看 dnsmasq 的 DHCP/DNS、vdns 看根 DNS，AP 内 DNS 与全局根 DNS 同看"),
    ("AP 集中控制器", "OpenWrt 路由器", "apcontroller 思路集中管理轻量 AP，与 OpenWrt 路由器（嵌入式 AP）视角互补"),
    ("LLVM 工具链", "兼容层串联", "llvm 交叉编译目标矩阵是兼容层跨平台运行时的来源之一，缺的运行时由 clang --target 补上"),
    ("LLVM 工具链", "架构/指令集", "交叉编译目标三元组首要就是架构（aarch64/armv7/riscv64/loongarch64…），架构不成立则目标矩阵无意义"),
    ("LLVM 工具链", "包管理", "交叉 sysroot/交叉工具链由包管理供给（gcc-aarch64-linux-gnu/mingw-w64…），llvm 与 pkgmgr 同源"),
    ("组网与设备协同", "网络接口/路由", "meshnet 的 WireGuard P2P 网状是网络层设备间直连拓扑，组网结论喂给网络面"),
    ("组网与设备协同", "ZeroTier 虚拟组网", "meshnet 与 ZeroTier 同为虚拟组网（一个 P2P 网状、一个 SD-WAN），设备间连通结论互相印证"),
    ("组网与设备协同", "算力/网络共享", "meshnet 设备能力适配（算力/GPU/存储缓存）与 reshare 算力/网络共享同源：只共享算力网络"),
    ("虚拟根DNS与多CDN", "DNS 解析", "vdns 虚拟根 DNS（resolv.conf/DoH-DoT）是 dnshealth 解析链路上游，根 DNS 健康决定解析健康"),
    ("虚拟根DNS与多CDN", "网络接口/路由", "vdns 看根 DNS 与多 CDN、network 看接口路由，共同决定出得去/解析得到/选得优"),
    ("IPP 打印发现", "外部设备连接与兼容", "ipp 发现的打印机属外部设备，外设连接质量决定打印能力是否成立"),
    ("IPP 打印发现", "桌面环境", "ipp 打印机由桌面环境/系统设置管理，发现结论喂给桌面面做展示与建议"),
    ("现代显示与GPU", "桌面环境", "display 显示服务器与分辨率是桌面渲染上游，图形栈能否画得出由 display 定档"),
    ("现代显示与GPU", "虚拟化/GPU", "display 看 GPU/渲染后端、virtgpu 看虚拟化 GPU，无 virtio-GPU 则显示退化"),
    ("常态化回头看", "全能全知自检", "retro 常态化回头看与 omni 自检同源：一个查工程接线欠账、一个查长期保障欠账"),
    ("常态化回头看", "统一子系统清单", "retro 维护节奏表按已登记子系统编排，清单变则回头看清单变"),
    ("人类文明重启透镜", "设备长期使用保护", "restart 把设备长期保障升维成文明级资产保护：保养包络与可复制资产同属长期主义"),
    ("人类文明重启透镜", "供电与环境安全", "restart 维度清单以供电为前置（无电一切停摆），电气环境是文明重启第一道门槛"),
    ("人类文明重启透镜", "存储/文件系统", "restart 强调知识库离线沉淀，存储健康决定知识资产能否留得住"),
    # v0.6.43 新增耦合：虚拟机完整运行支持 + 汇编语言优化
    ("虚拟机环境", "架构/指令集", "virt 完整运行支持依赖 CPU 虚拟化标志（vmx/svm）与嵌套开关，架构成立才谈得上嵌套与运行配置"),
    ("虚拟机环境", "LLVM 工具链", "virt 运行配置模板与 guest 内工具链可借助 LLVM/clang 交叉编译供给"),
    ("汇编语言优化", "LLVM 工具链", "asm 的 LLVM 交叉编译汇编指引直接复用 llvm 交叉编译目标矩阵（clang -target=<triple> -S）"),
    ("汇编语言优化", "架构/指令集", "asm 的 SIMD 矩阵按架构分列（SSE/AVX/NEON/SVE/RVV），架构决定可用向量扩展"),
    ("汇编语言优化", "兼容层串联", "asm 手写 intrinsics/内联汇编与兼容层运行时互相印证：缺的跨平台运行时由对应工具链补上"),
]

# label → key，用于按开关过滤关系两端
_LABEL2KEY: Dict[str, str] = {s.label: s.key for s in subsystems.SUBSYSTEMS}

# 惰性模块缓存（仅在枚举到对应子系统时拉起）
_MOD_CACHE: Dict[str, object] = {}


def _get_module(name: str):
    """按 native 子模块名惰性导入并缓存（避免一次性 import 全部模块）。"""
    if name not in _MOD_CACHE:
        _MOD_CACHE[name] = importlib.import_module(__name__.rsplit(".", 1)[0] + "." + name)
    return _MOD_CACHE[name]


def _norm(r) -> Tuple[bool, str]:
    """归一化报告返回：tuple→(ok,msg)；list→(True, 拼接)；其它→(True,str)。"""
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
        return ok, msg
    if isinstance(r, list):
        return True, "\n".join(str(x) for x in r)
    return True, str(r)


def _classify(ok: bool, msg: str) -> str:
    """把单子系统诊断结果归为 4 档状态之一。

    - 不适用：报告明示未安装/未运行/非本平台/无数据（无论 ok 与否）。
    - 提示：诊断正常但出现警告/缺失/风险类措辞，需关注。
    - 正常：诊断正常且无告警。
    - 异常：由调用方在捕获异常时填入（本函数不处理）。
    """
    na_markers = ("未安装", "未检测到", "未运行", "未启用", "未找到",
                  "不适用", "非 Windows", "非游戏平台", "无数据", "N/A", "n/d")
    if any(m in msg for m in na_markers):
        return "不适用"
    if not ok:
        return "不适用"
    if any(m in msg for m in ("警告", "注意", "需关注", "异常", "失败",
                              "缺失", "未配置", "未开启", "风险", "不可用")):
        return "提示"
    return "正常"


def _oneline(msg: str, limit: int = 48) -> str:
    """从报告正文抽第一行实质内容，截断成紧凑状态串；优先跳过分隔线。"""
    skip = set("─═━┄┅│+-=· ")
    raw = [l.strip() for l in msg.splitlines() if l.strip()]
    if not raw:
        return ""
    nonbox = [l for l in raw if set(l) > skip]
    return (nonbox[0] if nonbox else raw[0])[:limit]


def sysmap_report() -> tuple:
    """按统一清单编排**已开启**的只读子系统，输出系统统筹总览。

    返回 (True, msg)：msg 含五段——开关状态 / 整体健康汇总 / 局部本征状态 /
    关联关系图（你中有我）/ 有序深入建议。本层只读聚合，永不写入。关闭的子系统
    既不诊断也不展示；某个子系统异常只标「异常」并跳过。
    """
    probes = subsystems.enabled_probes()  # 即调即求值、尊重开关
    enabled_keys = {p[0] for p in probes}

    rows = []
    counts = {"正常": 0, "提示": 0, "不适用": 0, "异常": 0}

    for key, label, layer, mod_name, fn_name in probes:
        mod = _get_module(mod_name)
        fn = getattr(mod, fn_name, None)
        status, line = "异常", "模块/函数不可用"
        if fn is not None:
            try:
                ok, msg = _norm(fn())
                status = _classify(bool(ok), str(msg))
                line = _oneline(str(msg))
            except Exception as e:  # noqa: BLE001
                status, line = "异常", f"诊断异常（已跳过）：{e}"
        counts[status] += 1
        rows.append((label, layer, status, line))

    total = len(subsystems.SUBSYSTEMS)
    on = len(enabled_keys)
    off = total - on

    out = []
    out.append("系统统筹总览（sysweeper · 你中有我，我中有你）")
    out.append("原则：统筹系统与局部兼顾 · 整体健康有序 · 全面科学发展")
    out.append("─" * 58)
    out.append("[模块开关状态]")
    out.append(f"  已登记子系统 {total} 项 · 已开启 {on} · 已关闭 {off}"
               + ("（关闭项不诊断、不展示）" if off else "（全量嵌入）"))
    out.append("─" * 58)
    out.append("[整体健康汇总]")
    out.append(f"  本次探测 {on} 项 · 正常 {counts['正常']} · 提示 "
               f"{counts['提示']} · 不适用 {counts['不适用']} · 异常 {counts['异常']}")
    out.append("─" * 58)
    out.append("[局部本征状态]（每个子系统只看状态；深入请钻取子命令）")
    for label, layer, status, line in rows:
        extra = f"  — {line}" if line else ""
        out.append(f"  · {label:<18}[{status}]{extra}")
    out.append("─" * 58)
    out.append("[关联关系 · 你中有我，我中有你]（仅显示两端均已开启的耦合）")
    shown = 0
    for a, b, r in RELATIONS:
        ka, kb = _LABEL2KEY.get(a), _LABEL2KEY.get(b)
        if ka in enabled_keys and kb in enabled_keys:
            out.append(f"  · {a} ↔ {b}：{r}")
            shown += 1
    if shown == 0:
        out.append("  · （当前开启的子系统间暂无可绘制的耦合关系）")
    out.append("─" * 58)
    out.append("[统筹建议 · 有序深入]（全面健康、科学排序）")
    out.append("  1. 网络异常排查顺序：硬件/网卡 → 发行版网络管理 → OSI(L1-L3) → "
               "网络(L4+/路由) → DNS → 覆盖层(Tor) → 虚拟组网(ZeroTier) → 本地自组网")
    out.append("  2. 兼容/游戏异常：内核(NTSync/fsync) → GPU(Vulkan/VirtIO) → "
               "发行版(i386) → Proton")
    out.append("  3. Web/应用兼容：DNS → 字符标准 → 浏览器引擎")
    out.append("  4. 内核/存储/容器：内核模块/固件 → 内核 sysctl 调优 → 存储健康 → 容器运行时")
    out.append("  5. 想看某子系统细节：sysweeper <子命令>"
               "（tor/zerotier/dnshealth/proton/wsl/virtgpu/browser/...）")
    out.append("  6. 管理嵌入项：sysweeper subsystems --list / --disable <key> / --enable <key>")
    out.append("─" * 58)
    out.append("红线：本总览仅做只读聚合与关联，不启停服务、不改配置、"
               "不连控制端口、不写入任何状态。")
    return (True, "\n".join(out))


def capabilities_report() -> tuple:
    """能力自检：列出可编排的只读子系统（全量登记）与红线声明。"""
    out = ["系统统筹总览 · 能力自检", "可编排的只读子系统（你中有我，我中有你，全量登记）："]
    for key, label, layer, *_ in PROBES:
        out.append(f"  · {label}（{layer}）")
    out.append("关联关系维度（示例）：")
    for a, b, r in RELATIONS[:6]:
        out.append(f"  · {a} ↔ {b}：{r}")
    out.append("红线：本总览仅做只读聚合与关联；")
    out.append("  不启停服务、不改配置、不连控制端口、不写入任何系统状态。")
    return (True, "\n".join(out))
