"""系统基座任务（platform=any，跨平台）：目录·包管理·网络仓库·安全检测。

用户指令三问：「你应该了解系统目录、包管理器和网络包管理器的工作，软件包
类似 deb 和 rpm 等是软件包，还有把 msf 给我安装了，如果使用 git 或二进制包
就整合到概念系统」。五轴落法（data/sysbase_docs.json）：

1. 系统目录（FHS/LFS）：什么是系统、什么是基础工具链、什么是系统关键组件；
2. 软件包格式（deb/rpm）：本地包管理器职责与包数据库；
3. 网络包管理器：apt/yum 仓库、GPG 签名链、pin 优先级；
4. Metasploit 分发与检测：官方渠道、安装路径（二进制包 vs git）、检测面；
5. 路径与命名空间：安装包的相对路径机理、互联网的本质是目录服务。

全部只读：不安装/卸载软件、不动仓库源与密钥、不启动 msfconsole 跑任何模块、
不写任何系统目录。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="sysbase_report",
        platform="any",
        title="系统基座总报告（只读：目录 + 包管理 + 仓库 + msf 检测）",
        category="maintenance",
        risk="low",
        desc="端到端系统基座报告：FHS 目录布局与 usrmerge、本地包管理器与包记录、"
             "第三方仓库订阅（源/pin/keyring）、Metasploit 安装痕迹检测、五轴知识库引用。",
        actions=[
            N("sysbase.sysbase_report", "端到端生成系统基座报告（只读+知识库驱动）"),
        ],
        notes=["本子系统只读——不安装/卸载软件、不动仓库源与密钥、不启动 msfconsole、不写任何系统目录。"],
        standards=["[国际] FHS 3.0（文件系统层次标准）",
                  "[国际] Debian Repository Format / apt-secure(8)"],
    ),
    Task(
        id="sysbase_layout",
        platform="any",
        title="系统目录与「什么是系统」体检（FHS/LFS 口径，只读）",
        category="maintenance",
        risk="low",
        desc="按 FHS 3.0 盘点关键目录在位性、usrmerge 合并状态与 /opt 附加软件；"
             "对照 LFS 口径回答三问：什么是系统（引导器+内核+init+shell+coreutils+C 库）、"
             "什么是基础工具链（binutils/gcc/glibc/linux-api-headers）、"
             "什么是系统关键组件（内核/init/udev/journald/shell/包管理器/C 库）。",
        actions=[
            N("sysbase.probe_system_layout", "只读探测 FHS 目录布局、usrmerge 与 /opt 清点"),
            M("LFS 临时工具链顺序：binutils → gcc → glibc → linux-api-headers，"
              "先在宿主交叉编译出自持工具，再 chroot 进目标系统自举（LFS Book 第 5 章）。",
              "LFS 工具链自举顺序"),
        ],
        notes=["目录结构是「系统/工具链/组件」三者的共同契约：工具链按 FHS 找库，组件按 FHS 找配置与数据。",
               "/opt 与 /usr/local 是发行版包管理器管辖之外的两个自建软件落点，检测面必须覆盖。"],
        standards=["[国际] FHS 3.0（Filesystem Hierarchy Standard）",
                  "[国际] LFS Book（Linux From Scratch）",
                  "systemd file-hierarchy(7)"],
    ),
    Task(
        id="sysbase_pkgmgr",
        platform="any",
        title="软件包格式与本地包管理器盘点（deb/rpm，只读）",
        category="maintenance",
        risk="low",
        desc="探测本机包管理器（dpkg/apt、rpm/yum/dnf、pacman/apk）存在性，查询关键包的"
             "数据库记录（dpkg -l / rpm -q），并演示 deb 版本串解析（以 metasploit-framework "
             "6.5.3~20260818061200~1rapid7-1 为例拆 upstream/nightly 时间戳/打包者/修订号）。",
        actions=[
            N("sysbase.probe_package_managers", "只读探测包管理器存在性与 metasploit 包记录"),
            M("包数据库是清点的事实源：dpkg -l / rpm -qa 查已安装，dpkg -L / rpm -ql 查文件清单；"
              "git 源码安装的软件在数据库里没有记录——所以检测必须「数据库 + 文件系统」两路都查。",
              "为什么检测要两路都查"),
        ],
        notes=["deb = ar 归档（control + data 两段）；rpm = 带头签名的 cpio payload；底层工具记账，高层工具解依赖。",
               "deb 版本序中 ~ 表示「低于空」：6.5.3~20260818... < 6.5.3，nightly 因此排在正式版之前。"],
        standards=["[国际] Debian Policy Manual 第 5 章（二进制包结构）",
                  "[国际] RPM Package Manager（rpm.org）",
                  "dpkg(1) / apt(8) / rpm(8) man pages"],
    ),
    Task(
        id="sysbase_netrepo",
        platform="any",
        title="网络包管理器与第三方仓库订阅盘点（apt/yum 源·GPG·pin，只读）",
        category="network",
        risk="low",
        desc="盘点本机订阅的第三方仓库：/etc/apt/sources.list.d 源定义（含 signed-by 精确绑定）、"
             "/etc/apt/preferences.d pin 优先级、/usr/share/keyrings 签名密钥、/etc/yum.repos.d；"
             "讲清 apt 信任链四步（公钥验 Release → SHA256 验索引 → 校验和验包体，信任锚是公钥不是 HTTPS）。",
        actions=[
            N("sysbase.probe_network_repos", "只读盘点第三方仓库订阅（源/pin/keyring/yum repo）"),
            M("第三方仓库订阅是系统可信边界的变更：订阅了什么源、pin 优先级多少、信任了哪把钥匙，"
              "都应作为安全事件记录。实测 apt.metasploit.com 的 pin 为 1000（即使降级也装该源）。",
              "仓库订阅即可信边界变更"),
        ],
        notes=["仓库不校验客户端发行版：apt 源写 lucid 在 noble 上照样装（suite 名只是索引路径）。",
               "HTTPS 只保密不认证；认证全靠登记的 GPG 公钥——公钥分发（curl 拿 .gpg.key）是信任锚软肋。"],
        standards=["[国际] Debian Repository Format（wiki.debian.org）",
                  "[国际] apt-secure(8) / apt_preferences(5)",
                  "[国际] RFC 3986（URI：绝对 URL = 基址 + 相对路径）"],
    ),
    Task(
        id="sysbase_msf_detect",
        platform="any",
        title="Metasploit 安装痕迹检测（安全与检测，只读两路都查）",
        category="privacy",
        risk="low",
        desc="只读检测本机 Metasploit 痕迹：PATH 中 12 个命令（msfconsole/msfvenom/msfupdate 等）、"
             "dpkg/rpm 包记录、apt 四类痕迹（sources.list.d/pin/keyring/yum.repo）、/opt 安装目录、"
             "git 克隆目录；判定安装路径（二进制包 vs git 源码）并解析版本串。",
        actions=[
            N("sysbase.msf_version_report", "输出 msf 检测报告（命令/包记录/痕迹/路径判定/版本解析）"),
            M("本机实录：官方 msfinstall 装的 6.5.3~20260818061200~1rapid7-1（deb/apt 路径）。"
              "检测规则：包数据库（dpkg/rpm）+ 文件系统（/opt、PATH、工作目录）+ 仓库订阅（源/pin/keyring）"
              "三路都查——git 安装的没有包记录，只查数据库会漏。",
              "msf 检测三路覆盖规则"),
        ],
        notes=["绝不启动 msfconsole 跑任何模块、不生成载荷、不做任何扫描/利用动作——只查安装痕迹。",
               "未授权环境出现 msfconsole/msfvenom 痕迹即高信号；授权团队应能自证安装路径留痕。"],
        standards=["[厂商] docs.metasploit.com Nightly Installers（Rapid7 官方）",
                  "[厂商] metasploit-omnibus（GitHub 官方安装器源码）",
                  "[厂商] apt.metasploit.com 仓库实测（2026-10-23）"],
    ),
    Task(
        id="sysbase_path_concept",
        platform="any",
        title="路径与命名空间概念课（相对路径机理 + 互联网即目录服务）",
        category="maintenance",
        risk="low",
        desc="讲清两件事：① 为什么安装包都是相对路径——包内清单相对安装前缀记录（./opt/...）、"
             "仓库索引 Filename 相对仓库根（pool/main/...）、包装脚本以 $0 相对的 ../ 定位真身、"
             "update-alternatives 两跳符号链；② 互联网的本质是目录服务——DNS 是名字目录、URL 是路径、"
             "apt 仓库是包目录，安全（投毒与信任锚）与隐私（查询日志）是衍生问题，需求是扩展方向。",
        actions=[
            M("相对路径三实例（msf 实录）：deb data.tar 条目 ./opt/metasploit-framework/bin/msfconsole；"
              "Packages 索引 Filename: pool/main/m/metasploit-framework/xxx.deb；"
              "msfvenom 用法行 bin/../embedded/framework/msfvenom（$0 相对定位）。"
              "绝对地址 = 基址 + 相对路径，包因此可重定位（chroot/容器/自定义前缀）。",
              "安装包相对路径三实例"),
            M("目录服务栈：DNS（名字→地址，层级域名+委派）→ URL（路径定位）→ apt 仓库"
              "（suite/component/arch + Packages 索引）→ 搜索引擎（倒排索引）。"
              "安全衍生：目录投毒（DNS 劫持/伪造索引）对信任锚（DNSSEC/GPG）；"
              "隐私衍生：查询日志泄露兴趣，故有 DoH/DoT；需求扩展：算力/实时/身份仍是在命名空间里定位资源。",
              "互联网目录服务栈与衍生问题"),
        ],
        notes=["同一套目录思维的三层落地：系统目录（FHS）→ 包仓库（apt/yum）→ 互联网（DNS/URL）。",
               "本轴是概念层供料：把「目录服务」提升为系统/网络/安全三轴共通的根概念。"],
        standards=["[国际] RFC 3986（URI 通用语法）",
                  "[国际] RFC 1034/1035（域名系统）",
                  "[国际] POSIX 路径解析（dirname/realpath）"],
    ),
]
