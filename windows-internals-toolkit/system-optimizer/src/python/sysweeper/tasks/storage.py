"""存储与文件系统的清理、核对与优化任务（按各文件系统**自身的协议与接口**）。

「触类旁通、举一反三」：在系统软件、鸿蒙、小程序端、包管理器、容器运行时之后，把同一模式
推广到**存储与文件系统**。它们的接口彼此完全不同，因此逐个按**自身的协议与接口**处理：

- ext4   : e2fsck -fn（只读校验）/ e4defrag（在线整理）/ resize2fs（扩缩容）
- Btrfs  : btrfs balance -dusage/-musage（回收未用 chunk）/ scrub（校验）/ defrag（整理）
- XFS    : xfs_db -r -c frag（只读碎片率）/ xfs_fsr（整理）/ xfs_repair（离线修复）
- ZFS    : zpool trim（SSD 回收）/ scrub（校验）/ zfs destroy（释放快照）
- LVM    : lvreduce（先缩文件系统）/ pvmove（迁移）/ thin_check（thin 元数据）
- fstrim : fstrim -av（FITRIM 回收）/ blkdiscard（整盘丢弃，禁用）
- SMART  : smartctl -H / -A / -t（只读健康与自检）
- swap   : swapoff + mkswap + swapon（重建碎片交换）

删除/修复类动作默认带 `command -v` 守卫：无该工具或文件系统未挂载自动降级为「跳过」而非报错；
中风险（整理/balance/重建 swap）还需 --yes。绝不直接 dd 改写 superblock、不对挂载设备跑
xfs_repair、不用 blkdiscard 做常规回收——这些会让文件系统损坏或数据不可恢复。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

EXT4 = ("[国际] ext4 文档（e2fsck -fn 只读校验 / e4defrag 在线整理 "
        "+ ext4 磁盘布局 extent/jbd2 日志）")
BTRFS = ("[国际] Btrfs 文档（btrfs balance/scrub/defrag + COW B-tree "
         "子卷/快照/qgroup 引用计数）")
XFS = ("[国际] XFS 文档（xfs_db -r -c frag 只读碎片率 / xfs_fsr 整理 "
       "+ AG 分配组 B+tree）")
ZFS = ("[国际] OpenZFS 文档（zpool scrub/trim + zfs destroy "
       "+ DMU/SPA 端到端校验和）")
LVM = ("[国际] LVM 文档（lvreduce/pvmove/thin_check + device-mapper "
       "+ 精简置备 thin pool）")
FSTRIM = ("[国际] util-linux fstrim 文档（FITRIM ioctl + ATA TRIM / "
          "SCSI UNMAP / NVMe DSM）")
SMART = ("[国际] smartmontools smartctl 文档（smartctl -H/-A/-t "
         "+ ATA/SCSI/NVMe SMART 属性）")
SWAP = ("[国际] util-linux swapon 文档（swapon/swapoff/mkswap "
        "+ swap 签名页 SWAPSPACE2）")


TASKS = [
    # ---- 只读核对（native 探测，不修改系统） ----
    Task(
        id="fs_ext4_report",
        platform="any",
        title="ext4 挂载点与一致性核对（e2fsck -fn 只读 + e4defrag 建议）",
        category="maintenance",
        risk="low",
        desc="只读列出本机 ext4 挂载点与用量，给出 e2fsck -fn（只读校验，不修复）与 e4defrag（仅 extent 文件）的整理建议。",
        actions=[
            N("storage.ext4_report",
              "列出 ext4 挂载点/用量，给出只读校验与整理建议（只读）"),
        ],
        standards=[EXT4],
        notes=["参考 ext4 文档：e2fsck -fn 仅检查不修复（-f 强制，-n 假定 no 不写）；"
               "e4defrag 只对 extent 文件有效，目录或已连续文件无意义。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    Task(
        id="fs_btrfs_report",
        platform="any",
        title="Btrfs 用量与未用 chunk 核对（btrfs filesystem df）",
        category="maintenance",
        risk="low",
        desc="只读列出本机 Btrfs 挂载点的 data/metadata/unallocated 占比，定位未回收 chunk 与旧快照空间杀手。",
        actions=[
            N("storage.btrfs_report",
              "列出 Btrfs 挂载点用量与未用 chunk（只读）"),
        ],
        standards=[BTRFS],
        notes=["参考 Btrfs 文档：空间杀手是未回收的 chunk（balance）与未清的旧快照/子卷；"
               "btrfs filesystem df 看已用占比，unallocated 为可回收空间。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    Task(
        id="fs_xfs_report",
        platform="any",
        title="XFS 挂载点与碎片率核对（xfs_db -r -c frag 只读）",
        category="maintenance",
        risk="low",
        desc="只读列出本机 XFS 挂载点，用 xfs_db -r -c frag 计算碎片率（-r 只读，禁止写挂载设备）。",
        actions=[
            N("storage.xfs_report",
              "列出 XFS 挂载点并算碎片率（xfs_db -r 只读）"),
        ],
        standards=[XFS],
        notes=["参考 XFS 文档：碎片主要来自大量小文件随机写；xfs_db -r -c frag 只读算碎片率，"
               "务必带 -r 否则可能写挂载设备。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    Task(
        id="fs_zfs_report",
        platform="any",
        title="ZFS 存储池健康与容量核对（zpool list / zfs list）",
        category="maintenance",
        risk="low",
        desc="只读列出本机 ZFS 存储池健康/容量与数据集占用，定位快照累积与未释放数据集。",
        actions=[
            N("storage.zfs_report",
              "列出 ZFS 存储池健康与数据集占用（只读）"),
        ],
        standards=[ZFS],
        notes=["参考 OpenZFS 文档：空间靠快照引用计数管理；zpool list 看健康(cap)，"
               "zfs list 看 used/available。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    Task(
        id="fs_lvm_report",
        platform="any",
        title="LVM 逻辑卷与精简池占比核对（pvs/vgs/lvs）",
        category="maintenance",
        risk="low",
        desc="只读列出本机 LVM 逻辑卷与精简池(thin-pool) 已用占比，定位超额置备与未释放 LV。",
        actions=[
            N("storage.lvm_report",
              "列出 LVM 逻辑卷与精简池占比（只读）"),
        ],
        standards=[LVM],
        notes=["参考 LVM 文档：精简池(thin-pool) 超额置备后元数据满是常见空间杀手；"
               "data_percent 即已用占比。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    Task(
        id="fs_fstrim_report",
        platform="any",
        title="磁盘类型与 TRIM 支持核对（lsblk ROTA + discard_max_bytes）",
        category="maintenance",
        risk="low",
        desc="只读判断每块磁盘是 SSD/NVMe 还是 HDD，以及是否支持 discard（TRIM/UNMAP），给出 fstrim 回收建议。",
        actions=[
            N("storage.fstrim_report",
              "判断磁盘类型与 TRIM 支持（只读，不发 FITRIM）"),
        ],
        standards=[FSTRIM],
        notes=["参考 fstrim 文档：SSD/NVMe 靠 TRIM 回收空闲页；/sys/block/<dev>/queue/"
               "discard_max_bytes > 0 表示设备支持 discard。"],
        caveats=["只读任务：仅核对，不修改系统（不发 FITRIM，不跑 blkdiscard）。"],
    ),
    Task(
        id="fs_smart_report",
        platform="any",
        title="磁盘健康核对（smartctl -H，只读不跑自检）",
        category="maintenance",
        risk="low",
        desc="只读读取每块磁盘 SMART 整体健康(PASSED/FAILED) 与重映射/待映射扇区原始值，预警坏盘。",
        actions=[
            N("storage.smart_report",
              "读取磁盘 SMART 健康与关键属性（smartctl -H/-A 只读）"),
        ],
        standards=[SMART],
        notes=["参考 smartctl 文档：05 Reallocated / 197 CurrentPending / 198 OfflineUncorrectable "
               "增长预示坏道；NVMe 看可用备件下降。"],
        caveats=["只读任务：仅核对，不修改系统（不跑 -t 自检）。"],
    ),
    Task(
        id="fs_swap_report",
        platform="any",
        title="交换空间用量核对（swapon --show / /proc/swaps）",
        category="maintenance",
        risk="low",
        desc="只读列出本机已启用交换空间的大小与已用量，判断是否需要重建碎片 swap。",
        actions=[
            N("storage.swap_report",
              "列出交换空间大小/已用（只读）"),
        ],
        standards=[SWAP],
        notes=["参考 swapon 文档：长期运行的 swap 可能碎片；重建须先 swapoff 再 mkswap 再 swapon。"],
        caveats=["只读任务：仅核对，不修改系统。"],
    ),
    # ---- 优化/维护动作（带 command -v 守卫，中风险需 --yes） ----
    Task(
        id="fs_ext4_defrag",
        platform="any",
        title="ext4 在线碎片整理（e4defrag 首个 ext4 挂载点）",
        category="optimize",
        risk="low",
        desc="对首个 ext4 挂载点跑 e4defrag——仅整理 extent 文件，目录或已连续文件无效果，安全低风险。",
        actions=[
            S('MP=$(findmnt -n -o TARGET -t ext4 2>/dev/null | head -1); '
              'if command -v e4defrag >/dev/null && [ -n "$MP" ]; then '
              'e4defrag "$MP" 2>/dev/null && echo "ext4 碎片整理完成: $MP"; '
              'elif command -v e4defrag >/dev/null; then echo "无 ext4 挂载点，跳过"; '
              'else echo "无 e4defrag，跳过"; fi',
              "e4defrag 在线整理（仅 extent 文件有效，低风险）", rev=True),
        ],
        standards=[EXT4],
        notes=["参考 ext4 文档：e4defrag 只对 extent 文件有效；挂载点用 findmnt 取首个 ext4。"],
        caveats=["仅整理 extent 文件，不影响数据；大目录可能耗时但不破坏。"],
    ),
    Task(
        id="fs_xfs_defrag",
        platform="any",
        title="XFS 在线碎片整理（xfs_fsr 全部已挂载）",
        category="optimize",
        risk="medium",
        desc="xfs_fsr 整理所有已挂载 XFS 文件系统的真实碎片文件；会重写 extent，对极少碎片文件无意义且耗 IO，需 --yes。",
        actions=[
            S('if command -v xfs_fsr >/dev/null; then xfs_fsr 2>/dev/null '
              '&& echo "XFS 碎片整理完成"; else echo "无 xfs_fsr，跳过"; fi',
              "xfs_fsr 在线整理（重写真实碎片文件，需 --yes）", rev=True),
        ],
        standards=[XFS],
        notes=["参考 XFS 文档：xfs_fsr 仅对真实碎片文件有效；无参整理全部已挂载 XFS。"],
        caveats=["会重写 extent 增加 IO；运行前确认无关键写入在进行（需 --apply 且 --yes）。"],
    ),
    Task(
        id="fs_btrfs_balance",
        platform="any",
        title="Btrfs 回收未用 chunk（btrfs balance -dusage/-musage 20）",
        category="maintenance",
        risk="medium",
        desc="对首个 Btrfs 挂载点跑 balance，仅搬动已用<20% 的 chunk 以回收未分配空间——控制幅度避免全量重写。",
        actions=[
            S('MP=$(findmnt -n -o TARGET -t btrfs 2>/dev/null | head -1); '
              'if command -v btrfs >/dev/null && [ -n "$MP" ]; then '
              'btrfs balance start -dusage=20 -musage=20 "$MP" 2>/dev/null '
              '&& echo "Btrfs balance 完成: $MP"; '
              'elif command -v btrfs >/dev/null; then echo "无 btrfs 挂载点，跳过"; '
              'else echo "无 btrfs，跳过"; fi',
              "btrfs balance 回收未用 chunk（控制 usage=20，需 --yes）", rev=True),
        ],
        standards=[BTRFS],
        notes=["参考 Btrfs 文档：裸 btrfs balance 全量重写极重 IO；-dusage/-musage=20 只搬动"
               "已用<20% 的 chunk，回收空间同时控制幅度。"],
        caveats=["balance 会重写数据增加 IO 与写放大；运行期间勿中断（需 --apply 且 --yes）。"],
    ),
    Task(
        id="fs_btrfs_scrub",
        platform="any",
        title="Btrfs 后台校验（btrfs scrub start）",
        category="maintenance",
        risk="low",
        desc="对首个 Btrfs 挂载点启动 scrub——后台按 checksum 校验并修复副本，只读验证不丢数据。",
        actions=[
            S('MP=$(findmnt -n -o TARGET -t btrfs 2>/dev/null | head -1); '
              'if command -v btrfs >/dev/null && [ -n "$MP" ]; then '
              'btrfs scrub start "$MP" 2>/dev/null && echo "Btrfs scrub 已启动: $MP"; '
              'elif command -v btrfs >/dev/null; then echo "无 btrfs 挂载点，跳过"; '
              'else echo "无 btrfs，跳过"; fi',
              "btrfs scrub 后台校验（COW+checksum，只读验证）", rev=True),
        ],
        standards=[BTRFS],
        notes=["参考 Btrfs 文档：scrub 按每数据块 checksum 校验，副本可自修复；"
               "后台运行，可用 btrfs scrub status 查看进度。"],
        caveats=["仅校验修复，不修改用户数据；大文件系统耗时但不阻断读写。"],
    ),
    Task(
        id="fs_zfs_trim",
        platform="any",
        title="ZFS SSD 池回收空闲块（zpool trim 全部池）",
        category="optimize",
        risk="low",
        desc="对所有 ZFS 存储池发 TRIM，回收 SSD 后备盘上被释放但设备仍占用的空闲块。",
        actions=[
            S('if command -v zpool >/dev/null; then for p in $(zpool list -H -o name 2>/dev/null); '
              'do zpool trim "$p" 2>/dev/null && echo "ZFS trim 已发: $p"; done; '
              'else echo "无 zpool，跳过"; fi',
              "zpool trim 回收 SSD 空闲块（官方接口）", rev=True),
        ],
        standards=[ZFS],
        notes=["参考 OpenZFS 文档：zpool trim 对 SSD 后备盘发 TRIM；"
               "也可用 zpool set autotrim=on 让其自动回收。"],
        caveats=["trim 为后台异步，不影响数据；HDD 池无需 trim。"],
    ),
    Task(
        id="fs_fstrim_ssd",
        platform="any",
        title="SSD/精简置备未用块回收（fstrim -av）",
        category="optimize",
        risk="low",
        desc="对所有支持 discard 的挂载点发 FITRIM，让 SSD 控制器回收空闲页、让 thin 存储释放后端空间。",
        actions=[
            S('if command -v fstrim >/dev/null; then fstrim -av 2>/dev/null '
              '&& echo "fstrim 完成"; else echo "无 fstrim，跳过"; fi',
              "fstrim -av 回收所有支持 discard 的挂载点（官方 FITRIM 接口）", rev=True),
        ],
        standards=[FSTRIM],
        notes=["参考 fstrim 文档：fstrim 对挂载文件系统发 FITRIM，不破坏数据；"
               "频率过高伤低质 SSD 寿命，一周一次足够。"],
        caveats=["切勿用 blkdiscard 做常规回收——整盘立即丢弃，不可恢复。"],
    ),
    Task(
        id="fs_swap_rebuild",
        platform="any",
        title="重建碎片交换空间（swapoff + mkswap + swapon）",
        category="maintenance",
        risk="medium",
        desc="对所有已启用交换区：先 swapoff（须剩余内存足够）、mkswap 重建签名、再 swapon 重新启用——全程交换暂停，整理碎片。",
        actions=[
            S('if command -v swapon >/dev/null; then for s in $(swapon --show=NAME -o NAME '
              '--noheadings 2>/dev/null); do swapoff "$s" && mkswap "$s" && swapon "$s" '
              '&& echo "swap 重建完成: $s"; done; else echo "无 swapon，跳过"; fi',
              "swapoff + mkswap + swapon 重建（全程交换暂停，需 --yes）", rev=True),
        ],
        standards=[SWAP],
        notes=["参考 swapon 文档：重建须先 swapoff（剩余内存须足够，否则 OOM）；"
               "Btrfs 上的 swap 文件须 mkswap --file（自动 nocow）。"],
        caveats=["swapoff 期间无交换空间，内存不足会 OOM；确保物理内存够用再执行（需 --apply 且 --yes）。"],
    ),
]
