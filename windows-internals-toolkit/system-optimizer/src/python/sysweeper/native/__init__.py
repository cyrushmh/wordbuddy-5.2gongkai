"""各平台原生接口层（native）。

把「系统本身提供的接口」封装成 Python 函数，供 detect / runner / tasks 调用：

- Windows : 用 ctypes 调 Win32 API（SHGetKnownFolderPath / GetTempPathW /
            GetDiskFreeSpaceEx / SHEmptyRecycleBin）+ winreg 读注册表版本。
- Linux   : 用 LSB 规范文件 /etc/os-release（与 `lsb_release` 命令一致）+ 标准库。
- macOS   : 用 libc sysctlbyname + 系统命令（sw_vers / launchctl / defaults）。
- BSD     : 用 libc sysctlbyname + /etc/os-release + 各 BSD 包管理（pkg/pkg_add/pkgin）。
- Unix    : System V（Solaris / illumos）：/etc/release + IPS pkg。
- Android : 用 adb（Android Debug Bridge）与设备通信；v0.5.22 起下探到 Android 8.0
            （API 26）并提供**适老化只读探针**（字体缩放/放大镜/读屏/移除动画/护眼），
            逐项按 API 引入版本门控。
- jdk     : OpenJDK / HotSpot JVM 只读接口（java -version、JPMS 模块清单、GC/JIT 标志、
            诊断工具面、JFR 能力、Gradle/Maven 缓存体积），参照 OpenJDK 官方工程与 JEP。
            只读：不改 JAVA_HOME、不改 JVM 标志、不录制 JFR、不 attach 进程、
            系统属性只输出白名单键（口令/令牌类只报存在性不回显）。
- kmod    : Linux 内核 **module / firmware / eBPF** 只读层（/proc/modules、/sys/module、
            modinfo、/lib/firmware 固件清单、bpftool、power/thermal 状态），
            参照 kernel.org Documentation 与内核源码组织方式。
- profiles: 顶层 sysweeper/profiles.py 任务档位（大而全 full / 小而全 minimal），
            按风险/分类/opt-in 选任务子集。
- metrics : native/metrics.py 数学化量化评估（归一化加权评分、Shannon 熵、覆盖率、
            Gini 集中度），借鉴 openai/math 的「数学即文档」思路，
            但工程上不 vendor LaTeX 宏包，而是把「可计算」落到代码里。
- iOS     : 用 libimobiledevice（ideviceinfo 等）读设备信息；无则降级为指引。
- netlink : 多种网络链接协议注册表（TCP/UDP/RFCOMM/串口/BLE/802.15.4）+ 本地
            mesh 自组网（UDP 广播发现 + TCP 可靠通道 + **只读安全命令白名单**）。
- netauth : 按网络维度的隐私验证 —— 两项以上个人信息派生令牌，只存 salt+令牌+
            字段标签，**原始信息绝不保存**，下次重输即可重连。
- reshare : 同人登录的多设备资源共享 —— 只共享算力与网络（CPU/GPU/NPU/TPU/内存/
            网络出口），**个人数据与关键资产数据永不共享**，防他人盗用互联互通能力。
- meshchat  : 组网通信层：IPMsg（飞鸽传书）/ iptux 协议兼容编解码（UDP 2425 消息 /
            TCP 2425 文件）+ wall 式全体广播；覆盖文字 / 图片 / 视频 / 文件 /
            emoji / 颜文字（载荷类型不同，通道同一条）。**收到的文件不自动落盘**，
            进待收清单由用户显式接受——自动接收等于让别人能往你机器里塞东西。
- distcompute : 分布式计算共享层，BOINC 式 WU / 冗余双投 / credit 记账，
            **但与 BOINC 的根本差异是：只跑内置可验证算子，绝不下载或执行任何外部代码**
            （BOINC 的信任链是「我信任项目方」，本层砍掉这条链）。
            含看门狗重启模式（E，导入 mihomo-kubernetes）：只说明模式与出重启计划文本，
            绝不自动重启任何进程，与 openwrt_write 同口径。
            调度按核心数 × 空闲度 × 供电 × 是否计量网络打分；有 CPU 与时间预算，跑满即停。
- distjob   : 跨机派活层：把 distcompute 的工作单元**经 meshchat 组网文本通道**派出去、
            把结果收回来。载荷是短文本（SW-WU1: / SW-RES1: 前缀 + JSON），
            **通道里传的是参数不是代码**——白名单外的算子连解析都不认；
            收回的结果必须**复算校验**通过才算数，不信任任何节点的自述。
            默认 dry_run（只编码不出网），真派活需显式 dry_run=False。
- emergency : 预警应急与定位融合只读层。**定位口径**：先网络 + 基站为首选基线
            （室内/省电模式也总有），检测到导航定位（GNSS）后与基线**共同综合**
            （逆方差加权 + 基线 5% 最低话语权）；两源偏差超阈值标「存疑」且两套都摆出。
            红线：不自动报警/拨号/发短信，SOS 只生成文本；订阅源默认关闭，
            拉不到就报「未能获取」，绝不编造预警。
- webnews  : 新闻/网站聚合优化知识库（只读）。抓你配置的 http(s) RSS/网页 → 解析条目
            → 按平台/分类抽取优化知识点 → XDG 缓存。**抓来的永远是文本，无执行路径**——
            不 eval、不 subprocess、不自动改系统；优化建议带「来源归属」，由你决定做不做。
- edge     : 单板机/ARM SBC 只读探针与建议（v0.6.11「新硬件」）。设备树板型、thermal
            温度、Broadcom throttled 降频/欠压位、启动盘类型（SD/eMMC/NVMe）。惰性守卫：
            非 SBC 上优雅降级，绝不因「没有设备树」而崩；只读，不改频率/电压/不装服务。
- osi      : OSI 七层网络诊断（v0.6.13「整体补全」）。以 ISO/IEC 7498-1 / ITU-T X.200
            为骨架，把本机网络栈按 L1 物理→L7 应用**只读**摸一遍；复用 network 只读报告，
            红线同 webnews/edge——不写地址/路由/防火墙，不连校外网做写。
- distro   : 发行版识别 + 发行注记/变更日志读取（v0.6.13）。复用 linux.detect_distro，
            并读本机 /usr/share/doc 的 NEWS.Debian / changelog（只读本地，不 apt-get changelog 联网）。
- proton   : 游戏/应用兼容层只读诊断（v0.6.14「导入分析学习应用 Proton」）。以 Valve
            Proton（Steam Play 兼容层 = Wine+DXVK+VKD3D-Proton+wine-mono+Steam Runtime）为
            坐标系，只读核验「机器能否跑 Windows 游戏/程序」的前提：Vulkan 支撑栈(loader+ICD)、
            32 位 i386 运行时、NT 同步原语(esync/fsync/NTSync)、Steam Runtime 与 Proton/Wine
            安装。吸收 microsoft/litebox 的「接口面削减/隔离」理念，兼容层运行原则定为
            最小权限、可审计、可接管；红线同前——不装包、不写 Wine prefix、不连校外网。
- wsl      : WSL 环境只读诊断（v0.6.15「导入 microsoft/wsl2-linux-kernel」）。只读核验
            是否处于 WSL、版本 1/2、内核版本（对照 wsl2-linux-kernel 主线）、根文件系统驱动
            (virtiofs/9p)、systemd 与 interop 配置。红线——不写 wsl.conf/.wslconfig、不
            wsl --shutdown、不连校外网。
- virtgpu  : 虚拟化与 GPU 虚拟化只读诊断（v0.6.15「导入 arehnman/yttrium-virtio-gpu」）。
            核验是否虚拟化(hypervisor 标志)、virtio 设备、virtio-gpu（Venus 协议后端、免 GPU
            直通加速）、DRM 显示卡后端。红线——不加载模块、不装驱动、不改 QEMU/crosvm。
- browser  : 浏览器与引擎检测 + Web 兼容知识参考（v0.6.15「导入 mdn/browser-compat-data」）。
            探测已装浏览器/引擎(Blink/Gecko)版本，并给小型兼容知识参考（演示 BCD 的
            「特性→支持等级」结构）。红线——不下载 BCD 全量 JSON、不连校外网、不改配置。
- dnshealth: DNS 解析健康度只读诊断（v0.6.15「导入 python-dnspython 打包视角」）。聚焦解析
            链路（nameserver 来源 / systemd-resolved stub / 一次良性解析延迟），与
            network.nm_resolved 互补。红线——不写 resolv.conf、不重启 resolved、不改 DNS。
- tor      : Tor（洋葱路由）匿名/隐私网络只读诊断（v0.6.17「优化网络模块」）。读 tor 安装/版本/
            守护进程状态/torrc 关键配置(SOCKS/控制端口/桥接/可插拔传输/中继-出口)/可插拔传输
            二进制。红线——不启停 tor、不改 torrc、不连控制端口、不打印密钥明文。
- zerotier : ZeroTier 虚拟网络（SD-WAN/零信任组网）只读诊断（v0.6.17「优化网络模块」）。读
            zerotier-one 安装/版本/运行态/identity.public(公钥)/已加入网络(networks.d)/
            控制器(controller.d)/moon(moons.d)。红线——不启停 zerotier-one、不 join/leave、
            不读 identity.secret(私钥)。
- sysmap   : 系统统筹总览（v0.6.18「统筹系统与局部、你中有我」）。只读编排 13 个子系统诊断，
            输出「整体健康汇总 + 局部本征状态 + 关联关系图 + 有序深入建议」，把分散模块
            织成系统地图。仅做只读聚合与关联，不启停服务/不改配置/不连控制端口/不写状态。
- livemedia : 可启动介质制作能力只读诊断（v0.6.20「导入分析学习应用 livecd/dvd/bd/usb 制作技术」）。
            只读核验「本机具备制作何种可启动介质的能力」：ISO 构建工具链(xorriso/mkisofs/
            genisoimage/grub-mkrescue/mtools/isohybrid)、BIOS·UEFI 引导加载器(ISOLINUX/GRUB/
            systemd-boot)、El Torito·混合镜像(isohybrid)、压缩根系统(squashfs/overlayfs/casper)、
            U 盘写入工具(dd/Ventoy)、本机固件启动模式(UEFI/BIOS)与介质规格知识(CD/DVD/BD/USB)。
            红线同前——绝不 mkisofs/xorriso 实际构建、绝不 dd 到设备、绝不挂载/解包 ISO、绝不 modprobe。
- thirdparty : 第三方网络互联互通 / 硬件优化 / 开源下载 引用注册表（只读登记，
            p2wlan/dae/gfw-pac/v2rayN/DLSS5-Swapper/aria2），不打包其二进制。
- legacy  : 遗留 / 嵌入式 / 兼容层只读诊断（v0.6.21「导入分析学习应用」）。把 DOS 3.1 等
            遗留 DOS 环境、busybox 嵌入式用户态、dosbox DOS 模拟兼容层结构化只读核验，
            并嵌入整体系统——经 sysmap 关联图与 livemedia / openwrt / proton / wsl 产生
            「你中有我」关系（busybox↔OpenWrt、dosbox↔Proton、DOS↔livemedia）。
- radio  : 无线电技术与标准只读诊断（v0.6.75 新建）。把射频开关/无线物理能力/蓝牙/
          总线射频器件/SDR 工具链/法规口径（型号核准·微功率·ISM·业余·无线充电）
          结构化只读核验，法规结论只引用官方源；红线——绝不驱动任何真实发射
          （不改 regdom/信道/txpower、不开 monitor 注入、不扫描不配对、不代申请许可）。
- winternals : 开源 Windows 分析学习应用只读诊断（v0.6.76 新建）。把 System Informer/
          ReactOS/Ghidra/x64dbg/radare2·Cutter/dnSpyEx/Volatility3/MemProcFS/Wine/
          Windows Driver Samples 这批应用登记为只读诊断能力。**第一原则是先定系统再谈
          目录**：读任何目标前先判定它属于哪一套环境（Windows/WSL/Linux/macOS/Android），
          再按那一套的文件系统、目录约定、路径分隔与运行语言标准读数，绝不以本机
          （Linux 沙箱）的习俗臆造目标结构；运行语言环境两头看（目标的 PE/ELF/Mach-O
          与 CRT·CLR，工具链自身的 JVM/Python 3/交叉编译器）。红线——工具链只问在不在
          不启动，PCILeech 等具备 DMA 写能力的工具仅登记存在性与法律边界。
- qstore : 量子存储交换只读诊断（v0.6.77 新建）。把「ext4 默认 4K 对齐 + GPU/NPU/TPU/CAN
          异构端点缓冲交互 + 按程序要求做储存读取扫描索引 + 量子数字逻辑矩阵（Π_k 置换
          矩阵）做进制转换」落成量子架构基座上的存储域消费者：端点存在性只读探测、
          sysfs→lsblk→statvfs 三级对齐核验、enc 门保真往返、4K 对齐块打包管线仿真。
          红线——绝不执行写盘/格式化/分区命令（只作文本建议）、绝不加载驱动或提交
          计算、CAN 绝不开套接字不发帧；量子层纯软件仿真，不改 quantum.py 任何语义。
- qarch : 量子架构内核只读诊断（v0.6.78 新建）。盘点 quantum-kernel/ 内核树：
          Linux 6.18.57 LTS 基线、arch/quantum 纯新增架构（零修改接入——arch/Kconfig
          动态 source + SRCARCH 默认映射，既有架构全部原封）、drivers/quantum QPU
          模拟设备（/dev/qpuN，Π_k 门翻转语义与用户态基座一致）、4KiB 页纪律、
          补丁分发与整树重建路径。红线——纯只读，绝不执行内核构建/写树/加载模块。
- subsystems : 统一子系统清单 + 开关管理器（v0.6.22）。单一事实源登记所有能嵌入整体系统的
            只读诊断——不论 firmware（固件）/ plugins（插件）/ modules（内核模块）/ kernel /
            storage / container / hardware / 跨平台 OS 探测——每项可在
            ~/.config/sysweeper/subsystems.json 单独开/关（默认全开）；sysmap 只枚举
            已开启项，关闭项不诊断、不展示，关联图也只画两端均已开启的耦合。
- settings : 参数与阈值注册表（v0.6.23「GUI 可调控参数与阈值」）。单一事实源登记所有
            可在 GUI/CLI 调控的**运行参数**与**数值阈值**（命令超时/输出截断/扫描条数/
            导入上限/架构档位/报告落点/二维码后端/剪贴板后端…），落
            ~/.config/sysweeper/settings.json；类型与范围校验、越界拒绝、损坏回退默认。
            每条都登记生效点，全部真实消费于 common/importio/cli——**无装饰性假参数**。
- importio : 多来源导入层（v0.6.23「GUI 可导入剪贴板/本地文件/二维码」）。四种来源统一
            返回 (ok, text, note)：剪贴板（xclip/xsel/wl-copy → osascript → powershell →
            tk 兜底）、本地文本文件（受 import.max_bytes 限制）、**图片文件二维码解码**
            （后端 auto=OpenCV→pyzbar 降级）、摄像头扫码（可选，受 qr.camera_timeout 限制）。
            红线——只读不写回、缺库只给安装指引绝不自动安装、**导入内容只校验绝不自动执行**。
- openwrt : OpenWrt 路由器系统只读接口（UCI/opkg-apk/procd/netifd/ubus/固件板型/构建）。
- openwrt_write : OpenWrt 写操作「安全指引」层（只读预检 + 命令文本，绝不执行写操作；
            sysupgrade/包管理/uci set/服务启停均为 opt-in 高危指引）。
- durability : 设备长期使用保护子系统（v0.6.30）。只读采集电池/温度/存储 SMART/运行时长/
            环境传感器，按「使用量 + 期望年限 + 环境标签」推导保养目标包络与健康评分，
            生成优化建议与保养清单，**每条回链知识库（IEC 60529 / ASHRAE / NVMe SMART /
            厂商电池指南）**。写操作（充电上限/清灰/拆机）一律只给 OEM 官方工具指引，
            不代执行——契合只读红线，也契合「用户在 GUI 控制」诉求。
- remote : 远程接入与传输客户端只读审计子系统（v0.6.30）。覆盖 telnet/ssh/filezilla/putty，
            各自按**自身协议与接口**核对（SSH=RFC 425x 加密；Telnet=RFC 854 明文；FileZilla=
            FTP/RFC959 明文 vs SFTP vs FTPS/RFC4217；PuTTY=Windows SSH 客户端）。只读探针 +
            安全审计（telnet 明文 / ssh 口令登录 / filezilla 明文 FTP + 弱口令存储），**绝不读
            解密口令、绝不改 sshd_config、不替你停 telnetd**；加固只给官方指引。
- cert : 证书与加密开源整合子系统（v0.6.31）。整合 OpenSSL/LibreSSL/BoringSSL/GnuTLS 等开源加密
            栈 + **最低内置硬件证书**（TPM 2.0 硬件信任根 / IEEE 802.1AR IDevID 设备身份证书，
            私钥不可导出）+ 平台密钥库（Keychain/Secure Enclave/CNG/Android Keystore）+ 各种证书
            （X.509/ACME/FIDO2）。只读审计到期/信任链/EOL 加密库，**绝不读私钥、绝不解密、绝不改
            配置**；输出无障碍纯文本，与 a11y 子系统统一口径。
- linkage : 联动连轴体检（v0.6.33「整合统合合并 + 联动连轴」）。把 sysmap 的「谁和谁有关系」
            升级为**有方向、有性质**的联通图：每条轴标注供给/门控/印证/闭环（含既有关系表
            归并的「关联」），并做两件体检——**孤岛检测**（登记进统一清单却一条边都没有的
            假嵌入，v0.6.33 首跑即抓出跨平台 OS 五面全部悬空，已补轴清零）与**悬空轴自检**
            （端点 key 写错会静默失效）。v0.6.34 再进一层：新增**串联性质**（同一条依赖链的
            上下游）与**路径搜索**（`path` 沿轴走最短链、`reachable` 影响范围、
            `longest_chain` 全图最深串联），并给图形化产物（`graph` 结构化图数据 /
            `svg` 纯标准库生成 SVG / `ascii_graph` 命令行分层邻接图）。
- compat : 兼容层串联（v0.6.34）。把 proton / dosbox / wsl / virtgpu / legacy 从四份各说各话的
            报告串成**一条四层依赖链**：宿主底座（arch/kmod/distro）→ 设备与图形（virtgpu）→
            兼容运行时（proton/dosbox/wsl/legacy）→ 供给（pkgmgr）。按**场景**给结论
            （跑 Windows 程序 / 跑 DOS 程序 / 在 Windows 上跑 Linux / 跑遗留嵌入式），
            缺任一层判「缺层」；**不适用 ≠ 已就绪**（本机 Linux 时 wsl 报告 ok 但正文是
            「未识别为 WSL」，必须判不适用而非已通）。只调既有零参只读报告，
            **不安装、不启用、不改配置**，缺什么只给官方指引。
- omni : 全能全知自检（v0.6.35）。让工具**自述自己的边界**，三层：① 我知道什么（登记能力 +
            接线完整度，61 项里四件套齐全几项）；② 我知道我不知道什么（本机探不到的，`--deep`
            实跑）；③ **我不知道我不知道什么**（本工具压根没有探针的域——生物识别、GNSS 定位、
            音视频内容、文件正文、通信内容…写成显式边界声明而非沉默）。接线判定按 key→module→
            入口别名三级回退，避免把共用入口（`netlink`/`mesh`/`kaihong`/`import`）误报成欠账。

设计原则「不麻烦」：
- 全程纯标准库，零第三方依赖；能在当前沙箱（Linux）安全 import，绝不因
  平台不匹配而在 import 阶段崩溃（所有平台专属调用都做惰性守卫）。
- 每个函数返回「能拿到就返回，拿不到就 None/空」的稳值，让上层决定降级。
"""

from . import (android, arch, bsd, common, compress, distcompute, distjob,  # noqa: F401
               durability, cert, remote, edge, emergency, fonts, hardware, ios, jdk, kmod, linux, macos,
               meshchat, metrics, netauth, netlink, network, openwrt, openwrt_write, plugins,
               reshare, snapshot, thirdparty, unix, webnews, windows, osi, distro, proton,
               wsl, virtgpu, browser, dnshealth, tor, zerotier, sysmap, subsystems,
               livemedia, legacy, settings, importio, remote, cert, linkage, compat, omni,
               apctrl, llvm, toolchain, meshnet, vdns, ipp, display, retro, restart, asm, recert, langs,
               quantum, qudit, radio, winternals, qstore, qarch, transfer)
# v0.6.90 派发缺口补齐：runner._run_native 经 getattr(native, mod) 派发任务
# 里的 N("mod.func") 动作——此前 27 个被任务引用的模块（kernel/acoustics/
# androidstd/storage/…）+ 5 个已存在未接线模块不在本包 import 面内，任务
# 一执行就报「找不到原生接口」。本次全量接线（含国内标准 cnstd）。
from . import (acoustics, androidstd, ca_audit, chrono, cnstd, container, desktop, docs,  # noqa: F401
               electrical, f2b, fdroidstd, gmsstd, harmony, hmos_ecosystem, hmosstd, kernel,
               matrix, media, miniapp, mongo_catalog, packages, peripheral, pkgmgr, reverse,
               rfc_catalog, storage, sysbase, sysdev, syssoftware, tls13, virt, xiuzhen_catalog)
# 注：概念系统（plang/netsys/daoxue…）自 v0.6.59 起迁入 sysweeper.concepts 包，
# 统一注册表见 sysweeper/concepts/__init__.py（systems/load/module/search_all）。

__all__ = ["common", "compress", "windows", "linux", "macos", "bsd", "unix", "android", "ios",
           "hardware", "network", "netlink", "netauth", "reshare", "thirdparty",
           "openwrt", "openwrt_write", "plugins", "fonts", "arch", "snapshot",
           # v0.5.22 新增
           "jdk", "kmod", "metrics",
           # v0.6.8 新增
           "emergency", "meshchat", "distcompute", "distjob",
           # v0.6.11 新增
           "webnews", "edge", "osi", "distro",
           # v0.6.14 新增
           "proton",
           # v0.6.15 新增（导入分析学习应用）
           "wsl", "virtgpu", "browser", "dnshealth",
           # v0.6.17 新增（优化网络模块：Tor / ZeroTier 只读诊断）
           "tor", "zerotier",
           # v0.6.18 新增（系统统筹总览：你中有我，我中有你）
           "sysmap",
           # v0.6.19 新增（导入分析：深开鸿 KaihongOS 识别并入 harmony；storytold/photocraft 图像管线）
           "media",
           # v0.6.20 新增（导入分析学习应用：可启动介质制作 livecd/dvd/bd/usb 只读诊断）
           "livemedia",
           # v0.6.21 新增（导入分析学习应用：遗留/嵌入式/兼容层 DOS·busybox·dosbox 只读诊断）
           "legacy",
           # v0.6.22 新增（统一子系统清单 + 开关管理器：全量嵌入整体系统，可选项开/关）
           "subsystems",
           # v0.6.23 新增（GUI 可调控参数与阈值 + 多来源导入：剪贴板/文件/二维码）
           "settings", "importio",
           # v0.6.30 新增（设备长期使用保护：传感器采集 + 保养/优化引擎，写操作仅指引）
           "durability",
           # v0.6.30 新增（远程接入与传输客户端只读审计：telnet/ssh/filezilla/putty）
           "remote",
           # v0.6.31 新增（证书与加密开源整合：硬件信任根 + 各种证书，只读审计）
           "cert",
           # v0.6.33 新增（联动连轴：有方向有性质的联通图 + 孤岛/悬空体检）
           "linkage",
           # v0.6.34 新增（兼容层串联：四层依赖模型 + 场景结论，只读不代装）
           "compat",
           # v0.6.35 新增（全能全知自检：覆盖面 / 已知未知 / 无探针域边界声明）
           "omni",
           # v0.6.42 新增（导入学习应用 + 网络/显示/元能力/场景透镜）
           "apctrl", "llvm", "toolchain", "meshnet", "vdns", "ipp", "display", "retro", "restart", "asm",
           "recert", "langs",
           # v0.6.68 新增（量子程序与量子虚拟机：可执行态矢量模拟 + 程序 IR + 内置算法）
           "quantum",
           # v0.6.92 新增（qudit 多位元：d 级量子系统 + 同位能级散逸 T1/T2 + log 值交换）
           "qudit",
           # v0.6.75 新增（无线电技术与标准：射频面/SDR 工具链只读盘点 + 法规口径核对，
           # 绝不驱动任何真实发射）
           "radio",
           # v0.6.76 新增（开源 Windows 分析学习应用：目标环境判定 + 文件系统/目录约定 +
           # 运行语言环境核验 + 工具链存在性盘点 + 内核锚点；跨系统先认系统与硬件）
           "winternals",
           # v0.6.77 新增（量子存储交换：ext4 4K 对齐 + 异构端点缓冲 + Π_k 进制转换 +
           # 4K 打包管线仿真；绝不写盘，格式化命令只作文本建议）
           "qstore",
           # v0.6.78 新增（量子架构内核：Linux 6.18.57 LTS + arch/quantum 纯新增架构
           # + QPU 模拟设备盘点；纯只读，绝不执行内核构建/写树/加载模块）
           "qarch",
           # v0.6.91 新增（FTP + 目录服务为基础的传输/负载验证：上传/下载/续传/校验/限速，凭据不落盘）
           "transfer",
           # v0.6.90 新增（派发缺口补齐：上列 27 个任务引用模块 + 5 个未接线模块
           # 全量进入 import 面与 __all__，runner getattr 派发修复；含 cnstd）
           "acoustics", "androidstd", "ca_audit", "chrono", "cnstd", "container",
           "desktop", "docs", "electrical", "f2b", "fdroidstd", "gmsstd", "harmony",
           "hmos_ecosystem", "hmosstd", "kernel", "matrix", "media", "miniapp",
           "mongo_catalog", "packages", "peripheral", "pkgmgr", "reverse",
           "rfc_catalog", "storage", "sysbase", "sysdev", "syssoftware", "tls13",
           "virt", "xiuzhen_catalog"]
