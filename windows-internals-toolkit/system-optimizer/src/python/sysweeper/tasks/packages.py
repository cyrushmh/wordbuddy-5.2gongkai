"""软件包规范审计任务（platform=any，跨平台）。

按系统/硬件/相关软件包只读检测包管理器（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper），
审计「安装/卸载/配置/设置优化」四类操作是否符合包规范，并给出相应层级应对；
任何 install/uninstall/configure/optimize 的高危动作一律只给规范指引，不代执行
——严守本项目只读红线。

引擎（detect_pkgmgr / audit_operation / packages_report）是纯函数，由 packages_report
串联；GUI 可让用户选定包管理器与操作，即时看到层级应对与合规铁律。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="packages_report",
        platform="any",
        title="软件包规范审计（按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对）",
        category="maintenance",
        risk="low",
        desc="只读检测当前系统的包管理器（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper），"
             "审计安装/卸载/配置/设置优化四类操作是否符合包规范，并给出层级应对（一律指引不代执行）。",
        actions=[
            N("packages.packages_report", "端到端生成软件包规范审计报告（检测→四类操作层级应对）"),
        ],
        notes=["软件只读能力面：只审计、只出层级应对，不 install/uninstall/configure/optimize 任何包。"],
        standards=["[国际] Debian Policy Manual（APT/dpkg 控制字段与依赖）",
                  "[国际] Fedora Packaging Guidelines（DNF/RPM）",
                  "[国际] Arch PKGBUILD / Pacman（构建与安装规范）",
                  "[国际] Homebrew Formula（macOS/Linux 用户态包）",
                  "[国际] WinGet 清单 schema v1.x（Windows 包管理）",
                  "[国际] Alpine apk-tools（APKINDEX 与签名）"],
    ),
    Task(
        id="packages_install_guidance",
        platform="any",
        title="包安装规范（层级应对指引）",
        category="maintenance",
        risk="low",
        desc="给出在当前包管理器下安装软件包的规范与层级应对：走官方接口、禁止手工改包数据库、"
             "签名/GPG 校验失败即停。绝不自动安装。",
        actions=[
            M("安装一律走官方接口（apt-get/dnf/pacman/brew/winget…），禁止裸 dpkg -i / rpm -i 绕过依赖求解；"
              "从可信签名源安装，校验失败即停。",
              "包安装规范（不代执行）"),
            N("packages.guide_install", "输出包安装规范指引（只给步骤，不装包）"),
        ],
        notes=["安装属写操作，一律只给层级应对指引；是否施工由用户在系统包管理器确认。"],
        standards=["[国际] Debian Policy / Fedora Packaging / Arch PKGBUILD（安装接口规范）"],
    ),
    Task(
        id="packages_uninstall_guidance",
        platform="any",
        title="包卸载规范（层级应对指引）",
        category="maintenance",
        risk="low",
        desc="给出在当前包管理器下卸载软件包的规范与层级应对：走官方接口回收依赖、不手工删库。绝不自动卸载。",
        actions=[
            M("卸载优先用 autoremove/孤儿回收（apt autoremove / dnf autoremove / pacman -Rns / apk del），"
              "purge 才清配置；不手工改包数据库。",
              "包卸载规范（不代执行）"),
            N("packages.guide_uninstall", "输出包卸载规范指引（只给步骤，不卸包）"),
        ],
        notes=["卸载属写操作，一律只给层级应对指引；是否施工由用户确认。"],
        standards=["[国际] 各包管理器官方卸载接口（autoremove/孤儿回收）"],
    ),
    Task(
        id="packages_configure_guidance",
        platform="any",
        title="包配置规范（层级应对指引）",
        category="maintenance",
        risk="low",
        desc="给出在当前包管理器下配置软件包/源的规范与层级应对：源与钉版走 drop-in 片段、不内联改主文件。绝不自动改写。",
        actions=[
            M("仓库源与版本钉版走 drop-in 片段（sources.list.d / yum.repos.d / pacman.conf Include / "
              "apk repositories），不内联改主配置文件；冲突按包管理器提示处理。",
              "包配置规范（不代执行）"),
            N("packages.guide_configure", "输出包配置规范指引（只给步骤，不改配置）"),
        ],
        notes=["配置属写操作，一律只给层级应对指引；是否施工由用户确认。"],
        standards=["[国际] 各包管理器源/钉版声明规范（drop-in 片段）"],
    ),
    Task(
        id="packages_optimize_guidance",
        platform="any",
        title="包设置优化规范（层级应对指引）",
        category="maintenance",
        risk="low",
        desc="给出在当前包管理器下设置优化（缓存清理/升级）的规范与层级应对：缓存回收走官方 clean、"
             "升级逐包确认。绝不自动大版本跨跳。",
        actions=[
            M("缓存回收走官方接口（apt clean / dnf clean / paccache / brew cleanup / apk cache clean / "
              "scoop cleanup）；升级走 upgrade 且逐包确认，不自动跨大版本。",
              "包设置优化规范（不代执行）"),
            N("packages.guide_optimize", "输出包设置优化规范指引（只给步骤，不代执行）"),
        ],
        notes=["优化属写操作，一律只给层级应对指引；是否施工由用户确认。"],
        standards=["[国际] 各包管理器缓存清理/升级回滚接口"],
    ),
]
