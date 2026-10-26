"""Unix（System V）平台任务定义（Solaris / illumos / OmniOS 等）。

用 IPS 的 pkg 做清理；读 /etc/release 识别发行版。深度清理需 root。
v0.5.14 起补上 unix_tune_*：与 Windows/macOS/BSD 同构的「官方接口深度调优」，
但只调 System V 自己的官方子命令（pkg / svcadm / zfs / zpool / logadm / ipadm）。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="unix_pkg_history",
        platform="unix",
        title="清理 IPS 包历史",
        category="maintenance",
        risk="low",
        desc="清理 Solaris/illumos IPS 的包操作历史（pkg purge-history）。",
        actions=[Action("native", "unix.pkg_purge_history", "清理 IPS 包历史（pkg 原生命令）")],
        notes=["历史清理不影响已装软件，仅释放元数据空间。"],
    ),
    Task(
        id="unix_distro_report",
        platform="unix",
        title="发行版信息报告（/etc/release）",
        category="maintenance",
        risk="low",
        desc="读 Solaris /etc/release 与 uname，供优化前确认环境。",
        actions=[Action("native", "unix.detect_distro", "读取发行版（/etc/release + uname）")],
        notes=["System V 系列用 /etc/release 而非 /etc/os-release 记录发行信息。"],
    ),
    Task(
        id="unix_log_archive",
        platform="unix",
        title="归档旧系统日志",
        category="maintenance",
        risk="low",
        desc="压缩 30 天前的已轮转日志（/var/log、/var/adm），回收空间（需 root，仅压缩不改内容）。",
        actions=[S(
            'find /var/log /var/adm -type f -mtime +30 ! -name "*.gz" '
            '\\( -name "*.log.*[0-9]" -o -name "*.0" -o -name "*.old" \\) -exec gzip -q {} \\; 2>/dev/null',
            "压缩 30 天前的已轮转日志（仅压缩，保留原意）", rev=True)],
        notes=[
            "仅处理已轮转、非当前写入的日志；压缩即归档，不影响日志可读性（gunzip 还原）。",
            "更稳妥做法是用系统 logadm / logrotate 统一轮转与压缩。",
        ],
        caveats=["勿压缩正在写入的当前日志（*.log 本身）；本任务已用后缀/轮转名过滤规避。"],
    ),

    Task(
        id="unix_zfs_scrub",
        platform="unix",
        title="ZFS 存储池校验（zpool scrub）",
        category="maintenance",
        risk="low",
        desc="按 OpenZFS 规范对 zpool 发起 scrub 校验，检测并修复数据校验和错误。",
        actions=[S('if command -v zpool >/dev/null; then zpool status -x; zpool scrub $(zpool list -H -o name) 2>/dev/null || echo "无可用 pool"; else echo "无 zpool，跳过"; fi',
                   "查询健康并发起 scrub（OpenZFS 原生命令）")],
        standards=["[国际] OpenZFS（ZFS On-Disk Specification / zpool(8)）"],
        notes=["scrub 在后台进行，可用 zpool status 查看进度。"],
        caveats=["大容量池 scrub 耗时长且占 IO，建议维护窗口执行。"],
    ),

    # --------------------------------------------------------------------- #
    # v0.5.14 Unix（System V）官方接口深度调优（unix_tune_*）：
    # 沿用「按自身协议与接口」模式——只调 Solaris/illumos 自己的官方子命令
    # （pkg / svcadm / zfs / zpool / logadm / ipadm），绝不套用 Linux 的
    # sysctl、也不手工改 /etc/system 绕过官方工具。全部 opt_in：默认不出现、
    # 需显式选择 + 确认。只往安全方向写：服务只开不关、只清 maintenance 不做
    # disable、ZFS 只改属性不改数据、scrub 只校验不删、ECN 只开不关。
    # --------------------------------------------------------------------- #
    Task(
        id="unix_tune_ips_refresh",
        platform="unix",
        title="刷新 IPS 软件源目录（pkg refresh）",
        category="maintenance",
        risk="low",
        opt_in=True,
        standards=["[官方] pkg(1) / pkg(5)（IPS 镜像打包系统：publisher 与 catalog）",
                   "[国际] Oracle Solaris 11.4 文档：Adding and Updating Software Packages"],
        desc="用 IPS 官方接口刷新 publisher 目录与本地元数据，让后续 pkg list/verify 基于最新清单。",
        actions=[N("unix.ips_pkg_refresh", "pkg refresh（IPS 官方 refresh 接口）")],
        notes=["只读核对：pkg publisher、pkg list -u（列可更新包）。"],
        caveats=["需 root 且要能连到软件源；只更新元数据，不安装也不卸载任何包。"],
    ),
    Task(
        id="unix_tune_ips_fix",
        platform="unix",
        title="按 IPS 清单校验修复不一致（pkg fix）",
        category="maintenance",
        risk="medium",
        opt_in=True,
        standards=["[官方] pkg(1) fix / verify（IPS 按 manifest 校验与修复）",
                   "[国际] Oracle Solaris 11.4 文档：Verifying and Fixing Packages"],
        desc="先用 pkg verify 比对已装文件与 IPS 清单，再用官方 pkg fix 还原被改动/缺失的文件。",
        actions=[N("unix.ips_pkg_fix", "pkg fix（IPS 官方修复接口，按 manifest 还原）")],
        notes=["只读核对：pkg verify（列出不一致文件，不改任何东西）。"],
        caveats=["需 root；会按官方清单覆盖被改动的系统文件（本地手工改过的文件可能被还原），"
                 "属『恢复一致性』方向，不动用户数据。"],
    ),
    Task(
        id="unix_tune_smf_fmd",
        platform="unix",
        title="开启 FMA 故障管理守护（svcadm enable）",
        category="maintenance",
        risk="low",
        opt_in=True,
        standards=["[官方] smf(7) / svcadm(8)（SMF 服务管理框架）",
                   "[国际] Oracle Solaris 文档：Fault Management（fmd 预测式自愈）"],
        desc="启用 svc:/system/fmd:default，让 FMA 收集故障遥测并在硬件出问题时自动隔离（只开不关）。",
        actions=[N("unix.smf_enable_fmd", "svcadm enable svc:/system/fmd:default（只开不关）")],
        notes=["只读核对：svcs -a | grep fmd；故障看 fmadm faulty / fmdump -v。"],
        caveats=["本工具只做 enable——绝不对 fmd/ssh/svc.startd 等关键服务做 disable。"],
    ),
    Task(
        id="unix_tune_smf_clear",
        platform="unix",
        title="清除服务 maintenance 状态（svcadm clear）",
        category="maintenance",
        risk="medium",
        opt_in=True,
        standards=["[官方] svcadm(8) clear（SMF 官方状态恢复接口）",
                   "[国际] smf(7)（服务状态：online/degraded/maintenance/disabled）"],
        desc="自动探测处于 maintenance 的服务 FMRI，用官方 svcadm clear 清状态，让服务重新受管。",
        actions=[N("unix.smf_clear_maintenance", "svcadm clear <fmri>（FMRI 自动探测）")],
        notes=["只读核对：svcs -x（看故障原因）；原因未除前清状态可能再次进入 maintenance。"],
        caveats=["只清状态、不做启停；真正的故障原因请先按 svcs -x 输出处理。"],
    ),
    Task(
        id="unix_tune_zfs_atime",
        platform="unix",
        title="ZFS 关闭访问时间更新（zfs set atime=off）",
        category="optimize",
        risk="low",
        opt_in=True,
        standards=["[国际] OpenZFS（zfs(8) atime 属性：文件访问时间回写）",
                   "[国际] OpenZFS 文档（openzfs.github.io）"],
        desc="关掉 ZFS 的 atime 回写：读文件不再写元数据，减少写放大，与 NTFS 关最后访问时间同思路。",
        actions=[N("unix.zfs_atime_off", "zfs set atime=off <pool>（池名自动探测）")],
        notes=["只读核对：zfs get atime <pool>；只作用于设置后的新访问，不重写已有数据。"],
        caveats=["依赖 atime 做审计/归档判断的软件需先确认；可随时 zfs set atime=on 改回。"],
    ),
    Task(
        id="unix_tune_zfs_compression",
        platform="unix",
        title="ZFS 开启 LZ4 压缩（zfs set compression=lz4）",
        category="optimize",
        risk="low",
        opt_in=True,
        standards=["[国际] OpenZFS（zfs(8) compression 属性：lz4/gzip/zstd）",
                   "[国际] OpenZFS 文档（openzfs.github.io）"],
        desc="给池开 LZ4 压缩：CPU 开销极低、压缩解压快，通常能用很小的代价换明显空间。",
        actions=[N("unix.zfs_compression_lz4", "zfs set compression=lz4 <pool>（池名自动探测）")],
        notes=["只读核对：zfs get compression <pool>；LZ4 在多数负载下接近零成本。"],
        caveats=["只压缩设置后新写入的块，已有数据不会被重写（想重写需 zfs send/recv 或 rewrite）；"
                 "已压缩数据改回 off 不会展开。"],
    ),
    Task(
        id="unix_tune_logadm_rotate",
        platform="unix",
        title="按官方配置轮转日志（logadm -r）",
        category="maintenance",
        risk="low",
        opt_in=True,
        standards=["[官方] logadm(8) / logadm.conf(5)（Solaris 官方日志轮转）",
                   "[国际] Oracle Solaris 11.4 文档：Managing Log Files"],
        desc="用官方 logadm 按 /etc/logadm.conf 立即轮转一次：归档改名、按保留份数淘汰最旧档。",
        actions=[N("unix.logadm_rotate_now", "logadm -r（官方轮转接口，不删历史）")],
        notes=["只读核对：logadm -V（校验配置语法）、logadm -v（预演）。"],
        caveats=["需 root；轮转不删正在写入的日志，历史档按 -C 份数淘汰。"],
    ),
    Task(
        id="unix_tune_ipadm_ecn",
        platform="unix",
        title="TCP 开启 ECN（ipadm set-prop，RFC 3168）",
        category="network",
        risk="medium",
        opt_in=True,
        standards=["[国际] RFC 3168（显式拥塞通知 ECN）",
                   "[官方] ipadm(8) set-prop（Solaris 11+ TCP 协议属性，取代 ndd）"],
        desc="用官方 ipadm 把 TCP 的 ecn 设为 active：拥塞时用报头标记代替丢包降速，吞吐更稳、延迟更低。",
        actions=[N("unix.ipadm_tcp_ecn", "ipadm set-prop -p ecn=active tcp（官方写接口）")],
        notes=["参考：RFC 3168 / ipadm(8) man。只读核对：ipadm show-prop tcp。"],
        caveats=["个别老旧或错误配置的中间设备会丢弃带 ECN 标记的报文，遇连通性异常请用 "
                 "ipadm set-prop -p ecn=passive tcp 退回（本工具只开不关）。"],
    ),

]
