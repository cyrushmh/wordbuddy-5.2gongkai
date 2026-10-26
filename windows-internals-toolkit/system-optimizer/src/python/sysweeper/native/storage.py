"""存储与文件系统（ext4 / Btrfs / XFS / ZFS / LVM / fstrim / SMART / swap）
的原生接口与文档引用。

「触类旁通、举一反三」：在系统软件、鸿蒙、小程序端、包管理器、容器运行时之后，本层把
同一模式推广到**存储与文件系统**。它们的接口彼此完全不同，逐个按**自身的协议与接口**核对，
绝不套用同一套路径：

- ext4   : extent 布局 + jbd2 日志；e2fsck -fn / tune2fs / e4defrag / resize2fs
- Btrfs  : COW + B-tree + 子卷/快照 + qgroup；btrfs filesystem df/usage / balance / scrub / defrag
- XFS    : AG 分配组 + B+tree；xfs_info / xfs_db -r -c frag / xfs_fsr / xfs_repair（离线）
- ZFS    : zpool + dataset/zvol + DMU/SPA + 校验和；zpool list/status/scrub/trim / zfs list/destroy
- LVM    : PV/VG/LV + device-mapper + thin pool；pvs/vgs/lvs / lvreduce / pvmove / thin_check
- fstrim : ATA TRIM / SCSI UNMAP / NVMe DSM + FITRIM ioctl；fstrim -v/-a / blkdiscard / lsblk ROTA
- SMART  : ATA/SCSI/NVMe 自检属性；smartctl -H / -A / -t（只读，不跑测试即看健康）
- swap   : 签名页 + swapon(2)；swapon --show / /proc/swaps / mkswap

所有探测只读：仅统计占用、碎片率、健康与可清理项，不做任何删除/修复/TRIM；未安装该工具
或文件系统未挂载时返回 (False, 说明)，由上层降级为指引。参考文档见 data/storage_docs.json。

存储协议标准族（v0.6.65 补全，逐条联网核实；详见 data/storage_docs.json 标准条目）：
- 物理接口：NVMe（NVM Express Base Spec Rev 2.1，2024）/ SATA（SATA-IO）/ SAS（INCITS T10，ISO/IEC 14776）/
  UFS（JEDEC JESD220G UFS 4.1）/ eMMC（JEDEC JESD84-B51）
- 文件系统标准：POSIX（IEEE 1003.1-2024 / ISO·IEC·IEEE 9945:2026）/ ISO 9660（1988）/ UDF（ISO/IEC 13346·ECMA-167）/
  exFAT（Microsoft 规范 2019，ECMA-382 / ISO/IEC 30122）/ NTFS（Microsoft 专有）
"""

from __future__ import annotations

import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "storage_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(fs_id: str) -> dict:
    """返回某文件系统的文档参考（含协议 protocols 与接口 interfaces）。"""
    return REFS.get(fs_id, {})


def reference_all() -> dict:
    """返回全部存储/文件系统文档参考。"""
    return REFS


def _common_run(cmd: str, timeout: int = 30):
    from . import common
    return common.run(cmd, timeout=timeout)


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024 / 1024 / 1024:.2f} TiB"
    if n >= 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024 / 1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MiB"
    if n >= 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n} B"


def _indent(text: str, prefix: str = "   ") -> str:
    return "\n".join(prefix + l if l else l for l in (text or "").splitlines())


def _mounts_by_fstype(fstype: str) -> list:
    """从 /proc/mounts 读出某文件系统的 (设备, 挂载点) 列表（只读）。"""
    res = []
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[2] == fstype:
                    res.append((parts[0], parts[1]))
    except OSError:
        pass
    return res


def _mount_usage(mp: str) -> str:
    try:
        st = shutil.disk_usage(mp)
        return (f"总 {_fmt_size(st.total)} / 已用 {_fmt_size(st.used)} "
                f"/ 可用 {_fmt_size(st.free)} "
                f"({st.used * 100 // max(st.total, 1)}%)")
    except OSError:
        return "（无法读取用量）"


def detect_storage() -> dict:
    """探测本机可用的存储/文件系统工具（按各自官方 CLI 是否可用判断，只读 which 查询）。"""
    return {
        "ext4": bool(shutil.which("e2fsck") or shutil.which("e4defrag")),
        "btrfs": bool(shutil.which("btrfs")),
        "xfs": bool(shutil.which("xfs_db") or shutil.which("xfs_fsr")),
        "zfs": bool(shutil.which("zpool")),
        "lvm": bool(shutil.which("lvs")),
        "fstrim": bool(shutil.which("fstrim")),
        "smart": bool(shutil.which("smartctl")),
        "swap": bool(shutil.which("swapon")),
    }


# --------------------------------------------------------------------------- #
# 各文件系统只读探测：返回 (ok: bool, msg: str)。ok 表示该项可用且探测成功。     #
# --------------------------------------------------------------------------- #

def ext4_report() -> tuple:
    mounts = _mounts_by_fstype("ext4")
    if not mounts:
        return False, "未发现已挂载的 ext4 文件系统（/proc/mounts 无 ext4 项）"
    lines = [f"ext4 挂载点（{len(mounts)} 个）："]
    for dev, mp in mounts[:8]:
        lines.append(f"   · {mp}  ({dev})  {_mount_usage(mp)}")
    lines.append("   · 碎片整理: e4defrag <dir>（仅 extent 文件有效）；一致性: e2fsck -fn <dev>（只读）")
    return True, "\n".join(lines)


def btrfs_report() -> tuple:
    if not shutil.which("btrfs"):
        return False, "未安装 btrfs-progs（btrfs CLI），跳过"
    mounts = _mounts_by_fstype("btrfs")
    if not mounts:
        return False, "未发现已挂载的 Btrfs 文件系统（/proc/mounts 无 btrfs 项）"
    lines = [f"Btrfs 挂载点（{len(mounts)} 个）："]
    for _dev, mp in mounts[:6]:
        rc, out = _common_run(f"btrfs filesystem df -h {mp!r} 2>/dev/null", timeout=30)
        usage = _mount_usage(mp)
        lines.append(f"   · {mp}  {usage}")
        if rc == 0 and (out or "").strip():
            # 仅展示 Data/Metadata/System 三行的已用占比，避免刷屏
            for l in out.splitlines():
                if any(k in l for k in ("Data,", "Metadata,", "System,")):
                    lines.append("       " + l.strip())
    lines.append("   · 回收未用 chunk: btrfs balance start -dusage=20 -musage=20 <mp>（控制幅度）")
    lines.append("   · 校验: btrfs scrub start <mp>；清旧快照: btrfs subvolume delete <snap>")
    return True, "\n".join(lines)


def xfs_report() -> tuple:
    if not shutil.which("xfs_db"):
        return False, "未安装 xfsprogs（xfs_db / xfs_fsr），跳过"
    mounts = _mounts_by_fstype("xfs")
    if not mounts:
        return False, "未发现已挂载的 XFS 文件系统（/proc/mounts 无 xfs 项）"
    lines = [f"XFS 挂载点（{len(mounts)} 个）："]
    for dev, mp in mounts[:6]:
        lines.append(f"   · {mp}  ({dev})  {_mount_usage(mp)}")
        # xfs_db -r 只读模式算碎片率（务必带 -r，禁止写挂载设备）
        rc, out = _common_run(f"xfs_db -r -c frag {dev!r} 2>/dev/null", timeout=30)
        if rc == 0 and (out or "").strip():
            for l in out.splitlines():
                if "fragmentation factor" in l or "fragments" in l:
                    lines.append("       " + l.strip())
        else:
            lines.append("       · 碎片率: 需 xfs_db -r -c frag <dev>（只读）")
    lines.append("   · 整理: xfs_fsr（仅真实碎片文件有效）；修复须先 umount 再 xfs_repair")
    return True, "\n".join(lines)


def zfs_report() -> tuple:
    if not shutil.which("zpool"):
        return False, "未安装 ZFS（zpool / zfs CLI），跳过"
    rc, out = _common_run("zpool list -H -o name,health,cap 2>/dev/null", timeout=30)
    if rc != 0 or not (out or "").strip():
        return False, "未发现 ZFS 存储池（zpool list 无输出；可能未建池或模块未加载）"
    lines = ["ZFS 存储池："]
    for l in out.splitlines():
        if l.strip():
            parts = l.split("\t")
            name = parts[0] if parts else l.strip()
            health = parts[1] if len(parts) > 1 else ""
            cap = parts[2] if len(parts) > 2 else ""
            lines.append(f"   · {name} 健康={health} 容量={cap}")
    rc2, out2 = _common_run("zfs list -H -o name,used,available 2>/dev/null", timeout=30)
    if rc2 == 0 and (out2 or "").strip():
        n = len([l for l in out2.splitlines() if l.strip()])
        lines.append(f"   · 数据集: {n} 个（zfs list 见 used/available）")
    lines.append("   · 回收: zfs destroy <pool>/<ds>@<snap>（快照）；SSD 池: zpool trim <pool>")
    lines.append("   · 校验: zpool scrub <pool>（COW+校验和，可修副本）")
    return True, "\n".join(lines)


def lvm_report() -> tuple:
    if not shutil.which("lvs"):
        return False, "未安装 LVM（lvs / vgs / pvs），跳过"
    rc, out = _common_run(
        "lvs -H -o vg_name,lv_name,lv_size,data_percent,attr 2>/dev/null", timeout=30)
    if rc != 0 or not (out or "").strip():
        return False, "未发现 LVM 逻辑卷（lvs 无输出；可能未使用 LVM）"
    lines = ["LVM 逻辑卷（data_percent 为精简池已用占比）："]
    for l in out.splitlines():
        if l.strip() and "LV" not in l.split()[:1]:
            lines.append("   · " + "  ".join(x for x in l.split() if x))
    # 精简池超额提示
    rc2, out2 = _common_run(
        "lvs -H -o lv_name,data_percent --segments -S 'segtype=thin-pool' 2>/dev/null",
        timeout=30)
    if rc2 == 0 and (out2 or "").strip() and len(out2.splitlines()) > 1:
        lines.append("   · 精简池(thin-pool) 已用：")
        for l in out2.splitlines()[1:]:
            if l.strip():
                lines.append("       " + "  ".join(x for x in l.split() if x))
    lines.append("   · 释放 LV: 先缩文件系统再 lvreduce；thin 超额用 fstrim 在挂载点回收")
    return True, "\n".join(lines)


def fstrim_report() -> tuple:
    if not shutil.which("fstrim"):
        return False, "未安装 util-linux（fstrim），跳过"
    if not shutil.which("lsblk"):
        return False, "未安装 lsblk，无法判断磁盘类型，跳过"
    rc, out = _common_run(
        "lsblk -d -n -o NAME,ROTA,TRAN 2>/dev/null", timeout=30)
    lines = ["磁盘类型与 TRIM 支持（ATA TRIM / SCSI UNMAP / NVMe DSM）："]
    seen = False
    for l in (out or "").splitlines():
        parts = l.split()
        if len(parts) < 2:
            continue
        name, rota = parts[0], parts[1]
        tran = parts[2] if len(parts) > 2 else "?"
        disk = f"/dev/{name}"
        try:
            with open(f"/sys/block/{name}/queue/discard_max_bytes") as f:
                discard = int(f.read().strip() or "0")
        except OSError:
            discard = 0
        kind = "SSD/NVMe" if rota == "0" else "HDD(旋转)"
        sup = "支持 discard" if discard > 0 else "不支持 discard"
        lines.append(f"   · {disk}  {kind} 传输={tran}  {sup}")
        seen = True
    if not seen:
        return False, "未发现块设备（lsblk 无输出）"
    lines.append("   · 回收: fstrim -av（对所有支持 discard 的挂载点）；不要日用")
    lines.append("   · 切勿用 blkdiscard 做常规回收（整盘立即丢弃，不可恢复）")
    return True, "\n".join(lines)


def smart_report() -> tuple:
    if not shutil.which("smartctl"):
        return False, "未安装 smartmontools（smartctl），跳过"
    if not shutil.which("lsblk"):
        return False, "未安装 lsblk，无法枚举磁盘，跳过"
    rc, out = _common_run(
        "lsblk -d -n -o NAME,TYPE 2>/dev/null", timeout=30)
    disks = [l.split()[0] for l in (out or "").splitlines()
              if len(l.split()) >= 2 and l.split()[1] == "disk"]
    if not disks:
        return False, "未发现磁盘设备（lsblk 无 type=disk 项）"
    lines = [f"磁盘健康（smartctl -H，{len(disks)} 块）："]
    for name in disks[:8]:
        disk = f"/dev/{name}"
        rc2, h = _common_run(f"smartctl -H {disk!r} 2>/dev/null", timeout=20)
        health = "未知"
        if rc2 == 0 and (h or "").strip():
            if "PASSED" in h:
                health = "PASSED"
            elif "FAILED" in h:
                health = "FAILED"
        # 只读取重映射/待映射扇区原始值（不跑自检）
        rc3, a = _common_run(f"smartctl -A {disk!r} 2>/dev/null", timeout=20)
        extra = ""
        if rc3 == 0 and (a or "").strip():
            for l in a.splitlines():
                if any(k in l for k in
                       ("Reallocated", "Current_Pending", "Offline_Uncorrectable")):
                    cols = l.split()
                    if len(cols) >= 10:
                        extra += f" {cols[1]}={cols[9]}"
        lines.append(f"   · {disk}  健康={health}{extra}")
    lines.append("   · 后台自检: smartctl -t short <dev>（离线，不阻塞）；长测 -t long")
    lines.append("   · 重映射/待映射扇区增长 → 立即备份并计划换盘")
    return True, "\n".join(lines)


def swap_report() -> tuple:
    if not shutil.which("swapon"):
        return False, "未安装 util-linux（swapon），跳过"
    rc, out = _common_run("swapon --show=NAME,SIZE,USED,PRIO --noheadings 2>/dev/null",
                          timeout=20)
    swaps = [l for l in (out or "").splitlines() if l.strip()]
    if not swaps:
        return False, "当前未启用任何交换空间（swapon --show 为空；/proc/swaps 仅含表头）"
    lines = [f"交换空间（{len(swaps)} 个）："]
    for l in swaps:
        parts = l.split()
        name = parts[0] if parts else "?"
        size = parts[1] if len(parts) > 1 else "?"
        used = parts[2] if len(parts) > 2 else "?"
        lines.append(f"   · {name}  大小={size} 已用={used}")
    lines.append("   · 重建碎片 swap: swapoff <dev> && mkswap <dev> && swapon <dev>（须内存足够）")
    return True, "\n".join(lines)


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("ext4_report", "ext4 挂载点与用量（e2fsck -fn 只读校验 + e4defrag 整理建议）"),
    ("btrfs_report", "Btrfs 用量与未用 chunk（btrfs filesystem df）"),
    ("xfs_report", "XFS 挂载点与碎片率（xfs_db -r -c frag 只读）"),
    ("zfs_report", "ZFS 存储池健康与容量（zpool list / zfs list）"),
    ("lvm_report", "LVM 逻辑卷与精简池占比（pvs/vgs/lvs）"),
    ("fstrim_report", "磁盘类型与 TRIM 支持（lsblk ROTA + discard_max_bytes）"),
    ("smart_report", "磁盘健康（smartctl -H，只读不跑自检）"),
    ("swap_report", "交换空间用量（swapon --show / /proc/swaps）"),
)


def environment_report() -> list:
    """返回本机存储/文件系统工具可用性概览（✓ 已装 / ✗ 未装）。"""
    det = detect_storage()
    lines = ["存储/文件系统工具可用性："]
    for key, label in (
        ("ext4", "ext4 (e2fsprogs)"), ("btrfs", "Btrfs (btrfs-progs)"),
        ("xfs", "XFS (xfsprogs)"), ("zfs", "ZFS (zpool)"),
        ("lvm", "LVM (lvs)"), ("fstrim", "fstrim (util-linux)"),
        ("smart", "SMART (smartctl)"), ("swap", "swap (swapon)"),
    ):
        mark = "✓" if det.get(key) else "✗"
        lines.append(f"   {mark} {label}")
    return lines


def storage_doc_list() -> list:
    """返回文档参考清单文本行（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    协议:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append("    接口:")
        for i in ref.get("interfaces", []):
            lines.append(f"      - {i}")
        lines.append(f"    建议: {ref.get('summary', '')}")
    return lines


def _agg_norm(r):
    """归一化报告返回：tuple→(ok,msg)；list→(True,拼接)；其它→(True,str)。"""
    if isinstance(r, tuple):
        ok = bool(r[0]) if r else False
        msg = str(r[1]) if len(r) > 1 else ""
        return ok, msg
    if isinstance(r, list):
        return True, "\n".join(str(x) for x in r)
    return True, str(r)


def storage_report() -> tuple:
    """存储/文件系统只读聚合：串联 Btrfs/XFS/ZFS/LVM/fstrim/SMART/swap + 环境探测。"""
    parts = []
    ok_any = False
    for fn in (btrfs_report, xfs_report, zfs_report, lvm_report, fstrim_report,
               smart_report, swap_report, environment_report):
        try:
            ok, msg = _agg_norm(fn())
        except Exception:  # noqa: BLE001
            continue
        ok_any = ok_any or ok
        if msg.strip():
            parts.append(msg.strip())
    if not parts:
        return False, "未检测到任何存储/文件系统（无可读接口）"
    return ok_any, "\n".join(parts)
