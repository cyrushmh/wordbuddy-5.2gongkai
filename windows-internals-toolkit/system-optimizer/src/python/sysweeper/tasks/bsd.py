"""BSD 平台任务定义（FreeBSD / OpenBSD / NetBSD / DragonFly）。

版本按发行版内核大版本区分；包管理命令用 `shutil.which` 探测，未安装对应
包管理器的发行版该任务自动空转，不会报错。深度清理需 root。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="bsd_pkg_cache",
        platform="bsd",
        title="清理包管理器缓存",
        category="cleanup",
        risk="low",
        desc="清除 pkg / pkgin / pkg_add 的下载缓存。",
        actions=[
            Action("native", "bsd.pkg_clean", "清理下载缓存（各 BSD 包管理原生命令）"),
        ],
        notes=["仅删除已下载的安装包，不影响已装软件。"],
    ),
    Task(
        id="bsd_orphan",
        platform="bsd",
        title="移除孤立/无用依赖",
        category="maintenance",
        risk="medium",
        desc="卸载不再被需要的依赖包。",
        actions=[
            Action("native", "bsd.autoremove", "移除无依赖的孤包（pkg autoremove / pkgin autoremove）"),
        ],
        caveats=["可能顺带移除你手动装但无其他依赖的软件，执行前会列出。"],
    ),
    Task(
        id="bsd_swappiness",
        platform="bsd",
        title="优化交换倾向（vm.swappiness）",
        category="optimize",
        risk="medium",
        desc="桌面/大内存机器可降低换页倾向。",
        actions=[
            S('sysctl vm.swappiness=10 2>/dev/null || echo "该 BSD 无 vm.swappiness，跳过"',
              "设置 swappiness=10（不支持则跳过）"),
        ],
        caveats=["FreeBSD 用 vm.swappiness（近年版本）；OpenBSD/NetBSD 无此参数，会自动跳过。"],
        notes=["FreeBSD 可加进 /etc/sysctl.conf 持久化。"],
    ),
    Task(
        id="bsd_distro_report",
        platform="bsd",
        title="发行版信息报告（sysctlbyname）",
        category="maintenance",
        risk="low",
        desc="用 libc sysctlbyname 读取内核状态，供优化前确认环境。",
        actions=[Action("native", "bsd.detect_distro", "读取发行版（sysctlbyname / uname / /etc/os-release）")],
        notes=["BSD 用 sysctlbyname 内核接口获取系统信息，比解析文件更权威。"],
    ),
    Task(
        id="bsd_services_audit",
        platform="bsd",
        title="开机服务审查（rc 服务）",
        category="optimize",
        risk="low",
        desc="列出当前启用的 rc 服务（FreeBSD service -e），按需禁用不需要的服务以减负。",
        actions=[
            S('service -e 2>/dev/null | head -40', "列出已启用服务（供审查，FreeBSD）"),
            M("在 /etc/rc.conf 中将对应 service 设为 NO（如 nginx_enable=\"NO\"）以禁用。",
              "通过 rc.conf 禁用服务"),
        ],
        notes=["不要禁用不清楚来源的底层服务（如网络/ssh 守护），可能影响远程访问。"],
        caveats=["改动 rc.conf 后需重启或 `service <name> stop` 生效；谨慎操作。"],
    ),
    Task(
        id="bsd_pkg_autoremove",
        platform="bsd",
        title="清理孤立软件包依赖（pkg autoremove）",
        category="cleanup",
        risk="low",
        desc="用 pkg autoremove 删除不再被任何软件依赖的孤立包，回收空间（FreeBSD）。",
        actions=[S("pkg autoremove -y 2>/dev/null || echo '未安装 pkg 或非 FreeBSD，跳过'",
                   "清理孤立依赖（pkg autoremove）")],
        notes=["只删“无人依赖”的包，不碰仍在用的软件；建议先 `pkg autoremove -n` 预演。"],
        caveats=["极少数情况 A 依赖 B 但元数据缺失，autoremove 可能误删；预演确认更稳妥。"],
    ),

    Task(
        id="bsd_zfs_trim",
        platform="bsd",
        title="ZFS 存储池 TRIM（FreeBSD/OpenBSD）",
        category="maintenance",
        risk="low",
        desc="按 OpenZFS 规范对 zpool 执行 trim，或开启 autotrim 自动回收 SSD 空间。",
        actions=[S('if command -v zpool >/dev/null; then zpool trim $(zpool list -H -o name) 2>/dev/null || echo "无可用 pool"; else echo "无 zpool，跳过"; fi',
                   "对 zpool 执行 TRIM（OpenZFS 原生命令）")],
        standards=["[国际] OpenZFS（ZFS On-Disk Specification / zpool(8)）"],
        notes=["也可 `zpool set autotrim=on <pool>`；机械盘无需 TRIM。"],
        caveats=["TRIM 期间有 IO 开销，建议低峰执行。"],
    ),
    Task(
        id="bsd_ports_distfiles",
        platform="bsd",
        title="清理 Ports 下载缓存（distfiles）",
        category="cleanup",
        risk="low",
        desc="清理 /usr/ports/distfiles 中已下载的软件源码包缓存，可重新下载。",
        actions=[S('if [ -d /usr/ports/distfiles ]; then du -sh /usr/ports/distfiles; '
                   'find /usr/ports/distfiles -type f -atime +60 -print | head -20; '
                   'else echo "无 /usr/ports/distfiles，跳过"; fi',
                   "清点并列出 60 天未访问的 distfiles")],
        standards=["[国际] FreeBSD Ports Collection（ports(7) 框架规范）"],
        notes=["删除命令：make distclean（在 port 目录内）或直接删 distfiles 下文件。"],
        caveats=["删除后重新编译该 port 需再次下载源码。"],
    ),

    # --------------------------------------------------------------------- #
    # v0.5.12 BSD 官方接口深度调优（bsd_tune_*）：沿用「按自身协议与接口」模式。
    # 每个接口只用自己的官方写子命令（sysctl -w / zpool set|scrub / pfctl -e -f /
    # periodic），不套用 Linux 的 /proc/sys 写法，也绝不做 pkg delete -a、
    # pfctl -F all、zpool destroy 这类破坏性操作。
    # 全部 opt_in：默认不出现、需选择 + 确认才执行。
    # --------------------------------------------------------------------- #
    Task(
        id="bsd_tune_tcp_rfc1323",
        platform="bsd",
        title="启用 TCP 高性能扩展（sysctl net.inet.tcp.rfc1323）",
        category="network",
        risk="medium",
        opt_in=True,
        standards=["[国际] RFC 7323（TCP 高性能扩展：窗口缩放 + 时间戳 + PAWS）",
                   "[官方] sysctl(8) / tcp(4) man（net.inet.tcp.rfc1323 MIB）"],
        desc="开启 RFC 7323 的窗口缩放与时间戳，长肥管道（高带宽时延积）下显著提升吞吐。",
        actions=[N("bsd.tcp_rfc1323", "sysctl -w net.inet.tcp.rfc1323=1（RFC 7323 官方 MIB）")],
        notes=["参考：RFC 7323 / tcp(4)。FreeBSD 默认即为 1，已是目标值时不动。"],
        caveats=["个别老旧中间设备对时间戳/窗口缩放处理异常，遇问题可关回 0。"],
    ),
    Task(
        id="bsd_tune_tcp_buffers",
        platform="bsd",
        title="调大 TCP 收发缓冲（recvspace / sendspace）",
        category="network",
        risk="medium",
        opt_in=True,
        standards=["[官方] sysctl(8) / tcp(4) man（net.inet.tcp.recvspace / sendspace）",
                   "[国际] RFC 7323（窗口缩放前提下的大窗口缓冲）"],
        desc="把 TCP 收发缓冲上调到 64 KiB（仅当当前值更小才动），提升高带宽链路吞吐。",
        actions=[N("bsd.tcp_buffers", "sysctl -w net.inet.tcp.recvspace/sendspace=65536（只上调）")],
        notes=["参考：tcp(4)。持久化写 /etc/sysctl.conf。"],
        caveats=["只上调不降低，避免覆盖内核自动调优的结果；缓冲过大会多占内核内存。"],
    ),
    Task(
        id="bsd_tune_maxfiles",
        platform="bsd",
        title="提高文件描述符上限（kern.maxfiles）",
        category="optimize",
        risk="medium",
        opt_in=True,
        standards=["[官方] sysctl(8) man（kern.maxfiles / kern.maxfilesperproc）",
                   "[国际] FreeBSD Handbook: 内核参数调优（/etc/sysctl.conf 持久化）"],
        desc="把 kern.maxfiles / kern.maxfilesperproc 提到 65536 / 32768，避免高并发/构建场景撞到描述符上限。",
        actions=[N("bsd.maxfiles", "sysctl -w kern.maxfiles=65536 kern.maxfilesperproc=32768（只上调）")],
        notes=["参考：sysctl(8)。当前值已达标时不动；持久化写 /etc/sysctl.conf。"],
        caveats=["上限过高会略增内核内存占用；root 权限下才写成功。"],
    ),
    Task(
        id="bsd_tune_zfs_autotrim",
        platform="bsd",
        title="ZFS 池开启自动 TRIM（zpool set autotrim=on）",
        category="maintenance",
        risk="low",
        opt_in=True,
        standards=["[国际] OpenZFS（zpool(8) autotrim 属性：后台自动回收 SSD 空闲块）"],
        desc="按 OpenZFS 官方接口给每个存储池开 autotrim，让 SSD 空闲块在后台持续回收，无需定期手动 trim。",
        actions=[N("bsd.zfs_autotrim", "zpool set autotrim=on <pool>（OpenZFS 官方接口）")],
        notes=["参考：zpool(8)。池名由 zpool list -H -o name 自动探测；机械盘无需 TRIM。"],
        caveats=["后台 TRIM 有轻微 IO 开销；极老 SSD 固件慎用。"],
    ),
    Task(
        id="bsd_tune_zfs_scrub",
        platform="bsd",
        title="ZFS 池校验（zpool scrub）",
        category="maintenance",
        risk="medium",
        opt_in=True,
        standards=["[国际] OpenZFS（zpool(8) scrub：遍历校验校验和并在有冗余时自愈）"],
        desc="对每个存储池启动官方 scrub 校验，遍历校验所有数据块、在有冗余时自动修复静默损坏。",
        actions=[N("bsd.zfs_scrub", "zpool scrub <pool>（OpenZFS 官方校验接口）")],
        notes=["参考：zpool(8)。进度用 zpool status 查看；建议低峰期跑。"],
        caveats=["scrub 会遍历全部数据、IO 开销明显；本任务只启动校验，绝不 destroy 池或数据集。"],
    ),
    Task(
        id="bsd_tune_zfs_arcmax",
        platform="bsd",
        title="限制 ZFS ARC 上限（vfs.zfs.arc_max）",
        category="optimize",
        risk="medium",
        opt_in=True,
        standards=["[国际] OpenZFS（zfs(4) vfs.zfs.arc_max：ARC 缓存上限可调参数）"],
        desc="把 ZFS ARC 上限压到物理内存的 50%，把内存让给应用与页缓存（数据库/编译机常见诉求）。",
        actions=[N("bsd.zfs_arc_max", "sysctl -w vfs.zfs.arc_max=<物理内存×50%>（OpenZFS 官方参数）")],
        notes=["参考：zfs(4)。物理内存由 sysctl hw.physmem 自动探测；未加载 ZFS 则跳过。"],
        caveats=["ARC 变小会增加磁盘读放大；纯文件服务器不宜压太狠。"],
    ),
    Task(
        id="bsd_tune_pf_enable",
        platform="bsd",
        title="启用 pf 防火墙并加载规则集（pfctl -e -f）",
        category="network",
        risk="medium",
        opt_in=True,
        standards=["[国际] OpenBSD FAQ: Packet Filter（pf.conf 规则集 + pfctl -e -f 启用加载）",
                   "[官方] pf.conf(5) / pfctl(8) man"],
        desc="按官方接口启用 pf 并加载 /etc/pf.conf 规则集（只启用不停用），恢复未开启的防火墙。",
        actions=[N("bsd.pf_enable", "pfctl -e -f /etc/pf.conf（官方写接口，只启不停）")],
        notes=["参考：pfctl(8)。只读核对用 pfctl -s rules/info/state。"],
        caveats=["规则集不存在时拒绝启用（不盲目开防火墙把自己锁在外面）；"
                 "本工具绝不做 pfctl -d（停用）或 -F all（冲刷全部状态/规则）。"],
    ),
    Task(
        id="bsd_tune_periodic_run",
        platform="bsd",
        title="手动跑一遍 periodic 维护脚本",
        category="maintenance",
        risk="low",
        opt_in=True,
        standards=["[国际] FreeBSD Handbook: 周期性任务配置（/etc/periodic/{daily,weekly,monthly,security}）",
                   "[官方] periodic(8) man"],
        desc="按官方入口手动跑一遍 daily 周期脚本（清临时文件、轮转日志、安全报告等），补齐被跳过的例行维护。",
        actions=[N("bsd.periodic_run", "periodic daily（官方周期维护入口）")],
        notes=["参考：periodic(8)。只读核对用 ls /etc/periodic/*；输出进系统日志/邮件。"],
        caveats=["脚本内容由系统自带，不改任何脚本；个别脚本会轮转日志，属预期行为。"],
    ),
]
