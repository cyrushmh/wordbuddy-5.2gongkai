"""软件包管理器的清理、核对与优化任务（按各包管理器**自身的协议与接口**）。

「触类旁通、举一反三」：既然内核、桌面、其余系统软件、鸿蒙、各小程序端都能各自引用
权威文档，包管理器同样按自己的接口处理——它们的做法彼此完全不同，因此这里逐个区分：

- dpkg/APT    : `apt-get clean`（.deb 缓存）+ `apt-get autoremove`（按 auto 标记判定）
- RPM/DNF     : `dnf clean all`（元数据+rpm 缓存），孤儿包用 `repoquery --unneeded`
- apk-tools   : `apk cache clean`（清 APKINDEX 与 .apk 缓存）
- pacman      : `paccache -rk2`（保留最近 2 版，仍可降级）优于 `pacman -Scc` 全清
- Homebrew    : `brew cleanup`（默认只删已装 formula 的旧版本下载，`-n` 可干跑）
- winget      : 清 %LOCALAPPDATA%\\Temp\\WinGet 下载缓存，升级走 `winget upgrade`
- pip         : `pip cache purge`（官方缓存接口，不影响已装包）
- npm         : `npm cache verify`（官方推荐，校验并回收损坏/过期条目，非破坏性）
- Snap/Flatpak: `snap set system refresh.retain=2` 减少保留版本；`flatpak uninstall --unused`

删除类动作默认需 --apply；中风险（会删包）还需 --yes。未安装该包管理器时命令自带
守卫，自动降级为「跳过」而不是报错。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

APT = "[国际] Debian Policy Manual（Debian Project：deb 控制字段 / 包关系）+ apt-get(8) / dpkg(1)"
RPM = "[国际] rpm.org 文档（RPM 包格式 / rpmdb / rpm(8)）+ dnf(8) clean|repoquery"
APK = "[国际] apk-tools 文档（Alpine：.apk 分段格式 / APKINDEX.tar.gz / apk(8)）"
PACMAN = "[国际] Arch Wiki pacman（.pkg.tar.zst / *.db 仓库归档 / paccache(8) / pacman(8)）"
BREW = "[国际] Homebrew 文档（docs.brew.sh：Formula / Cask Ruby DSL、bottle、brew(1) cleanup）"
WINGET = "[国际] Microsoft WinGet 文档（YAML 清单规范 schema v1.x / 源 REST 接口 / winget 命令参考）"
PIP = "[国际] PyPA pip 文档 + PEP 503（简单索引）/ PEP 427（wheel）/ pip cache(1)"
NPM = "[国际] npm 文档（Registry HTTP API / _cacache 内容寻址 / npm-cache(1) verify）"
UNIV = "[国际] snapd REST API 文档（Canonical）+ Flatpak 文档（OSTree refs/commit / uninstall --unused）"


TASKS = [
    Task(
        id="pm_apt_cache",
        platform="linux",
        title="清 APT 下载的 .deb 缓存（apt-get clean）",
        category="cleanup",
        risk="low",
        desc="用官方接口清空 /var/cache/apt/archives 下已下载的 .deb——重装时会重新下载，不影响已装包。",
        actions=[
            S('if command -v apt-get >/dev/null; then apt-get clean 2>/dev/null; echo "APT 缓存已清"; '
              'else echo "非 Debian 系（无 apt-get），跳过"; fi',
              "清空 /var/cache/apt/archives（官方 clean 接口，不动包数据库）", rev=True),
        ],
        standards=[APT],
        notes=["参考 apt-get(8)：clean 只清 /var/cache/apt/archives 与 partial 下的 .deb，"
               "不影响 /var/lib/dpkg/status 中的已装包记录；autoclean 只清无法再下载到的旧版本。",
               "缓存来自 Packages 索引（RFC822 段落式）解析后的下载，重新 apt-get install 会再次获取。"],
        caveats=["清缓存后若处于离线环境，重装同名包将无法从本地缓存取用，需要联网重新下载。"],
    ),
    Task(
        id="pm_apt_autoremove",
        platform="linux",
        title="移除不再被依赖的包（apt-get autoremove）",
        category="cleanup",
        risk="medium",
        desc="按 APT 的 auto 标记移除「当初作为依赖装进来、现已无人依赖」的包（含旧内核的对应模块包）。",
        actions=[
            S('if command -v apt-get >/dev/null; then apt-get -s autoremove 2>/dev/null | grep "^Remv" | head -20; '
              'else echo "非 Debian 系（无 apt-get），跳过"; fi',
              "先模拟列出将被移除的包（dry-run，不改系统）"),
            S('if command -v apt-get >/dev/null; then apt-get autoremove -y 2>/dev/null; '
              'else echo "非 Debian 系（无 apt-get），跳过"; fi',
              "实际移除（会删包，需 --apply 且 --yes）", rev=True),
        ],
        standards=[APT],
        notes=["参考 apt-mark(8)：包被标记为 auto（自动安装）还是 manual（手动安装）"
               "决定了 autoremove 是否移除它；误删可用 `apt-mark manual <pkg>` 提前保住。",
               "旧内核镜像多由 autoremove 处理（/boot 塞满的典型解法）；保留当前运行内核。"],
        caveats=["会真实删除软件包：若某包是你手动用但被标成 auto，会被一并移除；"
                 "执行前务必看 dry-run 列表，必要时先 apt-mark manual 固定。"],
    ),
    Task(
        id="pm_dnf_clean",
        platform="linux",
        title="清 DNF / YUM 仓库缓存（dnf clean all）",
        category="cleanup",
        risk="low",
        desc="清空 /var/cache/dnf（或 /var/cache/yum）中的仓库元数据与已下载 rpm，官方 clean 接口。",
        actions=[
            S('if command -v dnf >/dev/null; then dnf clean all 2>/dev/null; echo "dnf 缓存已清"; '
              'elif command -v yum >/dev/null; then yum clean all 2>/dev/null; echo "yum 缓存已清"; '
              'elif command -v zypper >/dev/null; then zypper clean 2>/dev/null; echo "zypper 缓存已清"; '
              'else echo "非 RPM 系（无 dnf/yum/zypper），跳过"; fi',
              "清空仓库元数据与 rpm 缓存（按 RPM 系各自的官方接口）", rev=True),
        ],
        standards=[RPM],
        notes=["参考 dnf(8)：clean all 清的是仓库元数据（repomd.xml / primary.xml 等）与下载的 rpm，"
               "不触碰 rpmdb（/usr/lib/sysimage/rpm）中的已装包记录。",
               "长期不想缓存可在 /etc/dnf/dnf.conf 设 keepcache=False（见 dnf.conf(5)）。"],
        caveats=["清后首次 dnf 操作需重新下载元数据（约几十 MB，取决于启用仓库数量）；"
                 "离线环境慎用。"],
    ),
    Task(
        id="pm_apk_cache",
        platform="linux",
        title="清 apk 包缓存（apk cache clean）",
        category="cleanup",
        risk="low",
        desc="用 Alpine 官方接口清理 /etc/apk/cache（或 /var/cache/apk）下的 .apk 与索引缓存。",
        actions=[
            S('if command -v apk >/dev/null; then apk cache clean 2>/dev/null; echo "apk 缓存已清"; '
              'else echo "非 Alpine（无 apk），跳过"; fi',
              "清空 .apk 与 APKINDEX 缓存（官方 cache 子命令）", rev=True),
        ],
        standards=[APK],
        notes=["参考 apk(8)：cache clean 清的是索引（APKINDEX.tar.gz）与已下载 .apk，"
               "不动 /lib/apk/db/installed 中的已装包记录。",
               "构建镜像时用 `apk add --no-cache` 可让缓存不落盘，是 Alpine 镜像瘦身的标准做法。"],
        caveats=["清缓存后离线重装同名包需重新下载；容器构建层内清理才真正减小镜像体积。"],
    ),
    Task(
        id="pm_pacman_cache",
        platform="linux",
        title="按保留版本清理 pacman 缓存（paccache -rk2）",
        category="cleanup",
        risk="low",
        desc="用 pacman-contrib 的 paccache 保留最近 2 个版本、清理更旧的包缓存，优于 -Scc 全清。",
        actions=[
            S('if command -v paccache >/dev/null; then paccache -rk2 2>/dev/null; '
              'elif command -v pacman >/dev/null; then echo "未装 pacman-contrib（无 paccache），'
              '可用 pacman -Sc 清未安装包的缓存"; pacman -Sc --noconfirm 2>/dev/null; '
              'else echo "非 Arch 系（无 pacman），跳过"; fi',
              "保留最近 2 版清理旧缓存（无 paccache 时降级为 pacman -Sc）", rev=True),
        ],
        standards=[PACMAN],
        notes=["参考 paccache(8)：-r 清理已安装包的旧版本缓存，-k2 表示每个包保留最近 2 个版本，"
               "比 `pacman -Scc`（清空全部缓存）稳健——留着旧版才能离线降级。",
               "pacman 包为 .pkg.tar.zst（zstd 压缩 tar，含 .PKGINFO），缓存目录 /var/cache/pacman/pkg。"],
        caveats=["若确实要腾出全部空间可用 pacman -Scc，但之后无法离线降级到旧版本；"
                 "本任务默认只保留 2 版。"],
    ),
    Task(
        id="pm_brew_cleanup",
        platform="macos",
        title="清 Homebrew 下载缓存（brew cleanup）",
        category="cleanup",
        risk="low",
        desc="按 Homebrew 保留策略回收 formula/cask 的旧版本下载缓存，默认不动已装包的当前版本。",
        actions=[
            S('if command -v brew >/dev/null; then brew cleanup -n 2>/dev/null | tail -15; '
              'else echo "未装 Homebrew（brew），跳过"; fi',
              "先干跑列出将清理的内容（brew cleanup -n，不删任何东西）"),
            S('if command -v brew >/dev/null; then brew cleanup 2>/dev/null; echo "brew 缓存已清"; '
              'else echo "未装 Homebrew（brew），跳过"; fi',
              "按官方保留策略清理旧版本下载缓存", rev=True),
        ],
        standards=[BREW],
        notes=["参考 brew(1) Manpage：cleanup 默认删除已安装 formula 的旧版本下载缓存；"
               "`--prune=<days>` 连未安装/更旧的缓存一并清，属更激进选项，先用 `-n` 干跑确认。",
               "Formula/Cask 用 Ruby DSL 声明（url / sha256 / depends_on），预编译产物是 bottle。"],
        caveats=["`brew cleanup --prune=0` 会清空全部缓存（含未安装包），后续安装需重新下载；"
                 "本任务只用默认行为，不使用 --prune。"],
    ),
    Task(
        id="pm_winget_cache",
        platform="windows",
        title="清 winget 下载缓存（%LOCALAPPDATA%\\Temp\\WinGet）",
        category="cleanup",
        risk="low",
        desc="删除 Windows Package Manager 的临时下载缓存；winget 再次安装时会重新下载。",
        actions=[
            S(r'powershell -NoProfile -Command "Remove-Item -Path \"$env:LOCALAPPDATA\Temp\WinGet\*\" '
              r'-Recurse -Force -ErrorAction SilentlyContinue; '
              r'if ($?) { Write-Output ''winget 下载缓存已清'' }"',
              "清空 %LOCALAPPDATA%\\Temp\\WinGet（临时下载目录）", rev=True),
            M("升级全部包用官方接口：`winget upgrade --all`（清单为 YAML，经 REST 源检索）"),
        ],
        standards=[WINGET],
        notes=["参考 WinGet 文档：下载缓存落在 %LOCALAPPDATA%\\Temp\\WinGet，属临时目录，"
               "删除后重新安装会再次拉取，不影响 %LOCALAPPDATA%\\Microsoft\\WinGet\\Packages 下已装内容。",
               "winget 以 YAML 清单（version / installer / locale，schema v1.x）描述包，源为 REST 接口。"],
        caveats=["不要手动删除或改动 WinGet\\Packages 下的安装目录（卸载应走 winget uninstall，"
                 "否则注册表 UninstallString 与实际文件不一致）。"],
    ),
    Task(
        id="pm_pip_cache",
        platform="any",
        title="清 pip 下载缓存（pip cache purge）",
        category="cleanup",
        risk="low",
        desc="用 PyPA 官方的 pip cache 接口回收 wheel 与 HTTP 响应缓存，不影响任何已安装的包。",
        actions=[
            S('for p in pip3 pip; do if command -v $p >/dev/null; then $p cache purge 2>/dev/null; '
              'echo "pip 缓存已清"; break; fi; done; '
              'if ! command -v pip3 >/dev/null && ! command -v pip >/dev/null; then '
              'echo "未装 pip，跳过"; fi',
              "回收 pip 下载缓存（官方 pip cache 接口，不动 site-packages）", rev=True),
        ],
        standards=[PIP],
        notes=["参考 pip cache 文档：purge 只清缓存目录（Linux ~/.cache/pip、"
               "macOS ~/Library/Caches/pip、Windows %LOCALAPPDATA%\\pip\\cache），"
               "已装包在 site-packages，完全不受影响。",
               "缓存内容按 PEP 427 wheel 与 HTTP 响应分层；想长期不缓存可安装时加 --no-cache-dir。"],
        caveats=["清缓存后离线安装同名包会失败（需重新下载）；CI 环境建议直接 --no-cache-dir。"],
    ),
    Task(
        id="pm_npm_verify",
        platform="any",
        title="校验并回收 npm 缓存（npm cache verify）",
        category="maintenance",
        risk="low",
        desc="按官方推荐用 verify 校验 _cacache 内容寻址缓存，回收损坏与过期条目（非破坏性）。",
        actions=[
            S('if command -v npm >/dev/null; then npm cache verify 2>/dev/null | tail -6; '
              'else echo "未装 npm，跳过"; fi',
              "校验缓存完整性并回收损坏/过期条目（官方推荐接口）"),
        ],
        standards=[NPM],
        notes=["参考 npm-cache 文档：verify 会遍历 _cacache（index-v5 索引 + content-v2 内容，"
               "按 sha512 完整性哈希寻址），回收损坏与过期条目并输出统计；"
               "官方明确把 `npm cache clean --force` 标注为破坏性操作。",
               "npm 元数据来自 Registry HTTP API 的 JSON packument，lockfileVersion 决定锁定语义。"],
        caveats=["本任务不用 `npm cache clean --force`——那会全清缓存，令后续每次安装都重新下载；"
                 "verify 只删无效内容。"],
    ),
    Task(
        id="pm_flatpak_unused",
        platform="linux",
        title="清 Flatpak 无引用的 runtime（flatpak uninstall --unused）",
        category="cleanup",
        risk="medium",
        desc="移除不再被任何应用引用的 Flatpak runtime 与扩展（OSTree 仓库中无 ref 指向者）。",
        actions=[
            S('if command -v flatpak >/dev/null; then flatpak uninstall --unused -y 2>/dev/null; '
              'else echo "未装 flatpak，跳过"; fi',
              "移除无引用的 runtime / 扩展（会删数据，需 --apply 且 --yes）", rev=True),
        ],
        standards=[UNIV],
        notes=["参考 flatpak(1) / flatpak-uninstall(1)：--unused 指「没有任何已安装应用引用的"
               "runtime / extension」；应用本体不会被动到。",
               "Flatpak 用 OSTree 仓库（refs + commit objects）去重共享，删除 runtime 可能释放数百 MB。"],
        caveats=["若之后要装回依赖该 runtime 的应用，需要重新下载；删应用数据请用 --delete-data（"
                 "本任务不使用，避免误删用户数据）。"],
    ),
    Task(
        id="pm_snap_retain",
        platform="linux",
        title="将 snap 保留版本数降为 2（refresh.retain）",
        category="optimize",
        risk="low",
        desc="设置 snapd 的 refresh.retain=2，减少每个 snap 保留的历史版本（默认 3），只改配置不删包。",
        actions=[
            S('if command -v snap >/dev/null; then snap set system refresh.retain=2 2>/dev/null; '
              'echo "已设 refresh.retain=2"; else echo "未装 snap，跳过"; fi',
              "设置 refresh.retain=2（只改 snapd 配置，不立即删除）"),
            M("存量旧版本可用 `snap remove --revision=<n>` 精确删除（见 snap(8)）"),
        ],
        standards=[UNIV],
        notes=["参考 snapcraft.io 文档：snapd 默认每个 snap 保留 3 个版本（含当前），"
               "refresh.retain 调整的是「刷新时保留的旧版本数」；snapd 经 Unix socket "
               "/run/snapd.socket 暴露 /v2/snaps 等 REST 端点。",
               "snap 是 squashfs 只读镜像，历史版本常是 /var/lib/snapd 变大的主因。"],
        caveats=["本任务只改配置、不删任何现存版本；存量旧版本需自行确认后按 revision 删除。"],
    ),
    Task(
        id="pm_orphans_report",
        platform="linux",
        title="孤儿/未引用包核对（各包管理器自身接口，只读）",
        category="maintenance",
        risk="low",
        desc="按各发行版自身的查询接口找出孤儿包：pacman -Qdt、dnf repoquery --unneeded、apt-get -s autoremove。",
        actions=[
            N("pkgmgr.pacman_report", "Arch：孤儿包与缓存占用（pacman -Qdt，只读）"),
            N("pkgmgr.dnf_report", "RHEL：未被引用的包与缓存（repoquery --unneeded，只读）"),
            N("pkgmgr.apt_report", "Debian：可 autoremove 数与 .deb 缓存（模拟，只读）"),
            N("pkgmgr.universal_report", "Snap / Flatpak：应用与 runtime 占用（只读）"),
        ],
        standards=[APT, RPM, PACMAN, UNIV],
        notes=["「孤儿包」的判定完全取决于各包管理器自己的记账：APT 看 auto/manual 标记"
               "（apt-mark(8)）、pacman 看是否被依赖（-Qdt）、DNF 看 repoquery --unneeded——"
               "不存在统一定义，因此这里逐个按其自身接口核对。",
               "只读核对，不删除任何包；确认后再用对应发行版的官方删除命令。"],
        caveats=["不同发行版结果不可互相套用；删除孤儿包前请逐个确认，尤其是驱动与内核相关包。"],
    ),
]
