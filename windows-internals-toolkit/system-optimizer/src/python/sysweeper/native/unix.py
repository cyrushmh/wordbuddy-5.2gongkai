"""Unix（System V）原生接口：覆盖 Solaris / illumos 等。

设计「不麻烦、靠系统本身」：
- 发行版识别：读 Solaris 传统的 /etc/release（含发行名与版本），再用 uname 补版本。
- 包管理：Oracle Solaris / illumos 用 IPS 的 pkg；也探测 pkgin（illumos 社区）。
- 清理：调 pkg 原生命令（history 清理等）。

v0.5.14 起补上「文档层 + 只读探测 + 官方写接口深度调优」三层，与前几轮的
Windows / macOS / BSD 同构、但**只按 System V 自身的协议与接口**实现：
- 文档层：data/unix_docs.json（IPS / SMF / ZFS / /etc/release / logadm /
  kstat / Zones / FMA / dladm-ipadm），各自记 protocols 与 interfaces。
- 只读探测 PROBES：读 /etc/release、pkg list/publisher、svcs、zpool list/status、
  kstat、logadm -V、zoneadm list、fmadm faulty、dladm/ipadm show。
- 官方写接口 TUNES：pkg refresh/fix、svcadm enable|clear、zfs set atime|compression、
  zpool scrub、logadm -r、ipadm set-prop ecn——只往安全方向写。

非 System V（非 SunOS）平台 import 不崩溃；专属调用检测不到就返回 None/False。
"""

from __future__ import annotations

import json
import re
import shutil
import sys

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "unix_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 Unix 接口的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 Unix 接口文档参考。"""
    return REFS


def _is_unix() -> bool:
    return sys.platform == "sunos"


def read_release(path: str = "/etc/release") -> dict:
    """解析 Solaris /etc/release。返回 {id, version_id, pretty, name}。"""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            first = f.readline().strip()
    except OSError:
        return {}
    if not first:
        return {}
    out["pretty"] = first
    # 形如 "Oracle Solaris 11.4 X86" / "OpenIndiana illumos ..." / "OmniOS ..."
    m = re.search(r"(Solaris|illumos|OmniOS|SmartOS|OpenIndiana)", first, re.I)
    out["id"] = m.group(1).lower() if m else "unix"
    out["name"] = m.group(1) if m else "Unix"
    mv = re.search(r"(\d+)\.(\d+)", first)
    if mv:
        out["version_id"] = f"{mv.group(1)}.{mv.group(2)}"
    return out


def _uname() -> dict:
    rc, out = common.run("uname -a 2>/dev/null")
    res = {}
    if rc == 0 and out:
        parts = out.split()
        if len(parts) >= 3:
            res["sysname"], res["nodename"], res["release"] = parts[0], parts[1], parts[2]
    return res


def detect_distro() -> dict:
    """综合探测 System V 发行版。"""
    if not _is_unix():
        # 非 System V 环境（如被 --platform unix 手动指定）：诚实降级
        return {"id": "unix", "version_id": "", "pretty": "(当前非 System V 环境，以下为通用信息)",
                "name": "Unix", "pkg_manager": pkg_manager()}
    rel = read_release()
    base = {
        "id": rel.get("id", "unix"),
        "version_id": rel.get("version_id", ""),
        "pretty": rel.get("pretty", ""),
        "name": rel.get("name", "Unix"),
    } or {"id": "unix", "version_id": "", "pretty": "", "name": "Unix"}
    if not base.get("version_id"):
        u = _uname()
        base["version_id"] = u.get("release", "")
    base["pkg_manager"] = pkg_manager()
    return base


def pkg_manager() -> str:
    """探测 System V 包管理器：pkg（IPS）/ pkgin。"""
    for pm in ("pkg", "pkgin"):
        if shutil.which(pm):
            return pm
    return ""


def disk_usage(path: str = "/") -> dict | None:
    return common.disk_usage(path)


def pkg_purge_history() -> tuple:
    """清理 IPS 包操作历史（Solaris）。返回 (ok, msg)。"""
    if not _is_unix():
        return False, "当前非 System V Unix，无法调用 pkg"
    pm = pkg_manager()
    if pm == "pkg":
        rc, out = common.run("pkg purge-history -n 2>&1 | tail -1")
        # -n 仅预览；真正执行需去掉 -n
        return rc == 0, out or "（预览：pkg purge-history 可清理 IPS 历史）"
    if pm == "pkgin":
        rc, out = common.run("pkgin clean")
        return rc == 0, out
    return False, "未识别的 Unix 包管理器"


# --------------------------------------------------------------------------- #
# 文档跟踪层：System V 各系统接口只读探测（返回 (ok, msg)）。                     #
# 全部只读：只读 /etc/release、只列包与服务与池、只读 kstat、只校验 logadm 配置、  #
# 只列区与故障、只查链路与地址——不写任何系统项。                                 #
# 非 System V 环境接口不存在，优雅返回 (False, 说明)，由上层降级为文档指引。      #
# --------------------------------------------------------------------------- #

def release_report() -> tuple:
    """读发行版信息（/etc/release + uname，只读；System V 不靠 /etc/os-release）。"""
    if not _is_unix():
        return False, "当前非 System V Unix（非 sunos），无 /etc/release（降级为文档指引）"
    rel = read_release()
    if not rel:
        return False, "未读到 /etc/release（文件缺失或不可读）"
    d = detect_distro()
    tail = f"  内核 {d.get('version_id', '')}" if d.get("version_id") else ""
    return True, (f"{rel.get('pretty', '')}{tail}（/etc/release + uname 只读；"
                  f"包管理器 {d.get('pkg_manager') or '未探测到'}）")


def pkg_report() -> tuple:
    """列 IPS 已装包与软件源（pkg list / pkg publisher，只读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，IPS 的 pkg 接口不可用（降级为文档指引）"
    if not shutil.which("pkg"):
        return False, "未找到 pkg（IPS 不可用，可能为非 IPS 发行版）"
    rc, out = common.run("pkg list -H 2>/dev/null | wc -l", timeout=180)
    if rc != 0 or not (out or "").strip():
        return False, "pkg list 无输出（非 IPS 镜像或需权限）"
    lines = [f"IPS 已装包：{out.strip().splitlines()[0].strip()} 个（pkg list -H 只读）"]
    rc2, pub = common.run("pkg publisher 2>/dev/null | grep -E '^ *[a-z0-9_-]+ +origin' | head -5",
                          timeout=120)
    if rc2 == 0 and (pub or "").strip():
        lines.append("   · publisher/origin：")
        for l in pub.splitlines()[:5]:
            if l.strip():
                lines.append("       " + l.strip())
    lines.append("   · 一致性校验（只读）：pkg verify；历史：pkg history")
    return True, "\n".join(lines)


def smf_report() -> tuple:
    """列 SMF 服务状态（svcs -a 统计 + svcs -x 故障，只读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，SMF（svcs/svcadm）不可用（降级为文档指引）"
    if not shutil.which("svcs"):
        return False, "未找到 svcs（SMF 不可用）"
    rc, out = common.run("svcs -a -H -o STATE 2>/dev/null | sort | uniq -c", timeout=180)
    if rc != 0 or not (out or "").strip():
        return False, "svcs -a 无输出（SMF 服务仓库不可用）"
    lines = ["SMF 服务状态分布（svcs -a 只读）："]
    for l in out.splitlines():
        if l.strip():
            lines.append("   · " + l.strip())
    rc2, x = common.run("svcs -x 2>/dev/null | head -12", timeout=120)
    if rc2 == 0 and (x or "").strip():
        lines.append("   · 故障明细（svcs -x，只读）：")
        for l in x.splitlines()[:12]:
            if l.strip():
                lines.append("       " + l.strip())
    else:
        lines.append("   · 无处于故障/maintenance 的服务（svcs -x 为空）")
    return True, "\n".join(lines)


def zpool_report() -> tuple:
    """列 ZFS 存储池与健康（zpool list + zpool status -x，只读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，ZFS 接口不可用（降级为文档指引）"
    if not shutil.which("zpool"):
        return False, "未找到 zpool（本机未使用 ZFS 或无该命令）"
    rc, out = common.run("zpool list -H -o name,size,alloc,free,cap 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "zpool list 无输出（无存储池或需权限）"
    lines = ["ZFS 存储池（zpool list 只读）："]
    for l in out.splitlines():
        if l.strip():
            name, *rest = l.split("\t")
            lines.append(f"   · {name}  " + "  ".join(rest))
    rc2, health = common.run("zpool status -x 2>/dev/null | head -3", timeout=120)
    if rc2 == 0 and (health or "").strip():
        lines.append("   · 健康（zpool status -x，只读）：" + health.splitlines()[0].strip())
    return True, "\n".join(lines)


def kstat_report() -> tuple:
    """读内核统计（kstat unix:0:system_pages:physmem，只读；Solaris 不从 /proc 读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，kstat 不可用（降级为文档指引）"
    if not shutil.which("kstat"):
        return False, "未找到 kstat（非 Solaris/illumos 内核）"
    rc, out = common.run("kstat -p -m unix -n system_pages -s physmem,availrmem 2>/dev/null",
                         timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "kstat system_pages 无输出（内核统计模块名不同或无权限）"
    lines = ["kstat 内核统计（只读，module:instance:name:stat 四元组）："]
    for l in out.splitlines():
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · physmem=物理内存页数；看 CPU 用 psrinfo -v，看进程用 prstat -a")
    return True, "\n".join(lines)


def logadm_report() -> tuple:
    """校验日志轮转配置（logadm -V，只读；失败则列 /etc/logadm.conf）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，logadm 不可用（降级为文档指引）"
    if not shutil.which("logadm"):
        return False, "未找到 logadm（日志轮转由其他机制管理）"
    rc, out = common.run("logadm -V 2>&1 | head -6", timeout=120)
    if rc == 0 and not (out or "").strip():
        # -V 校验通过时通常静默
        rc2, cnt = common.run("grep -cE '^[^-]' /etc/logadm.conf 2>/dev/null", timeout=60)
        n = (cnt or "?").strip().splitlines()[0] if (cnt or "").strip() else "?"
        return True, (f"logadm 配置校验通过（-V 无报错），/etc/logadm.conf 规则约 {n} 条"
                      "（只读校验；立即轮转用 logadm -r）")
    if rc == 0 and (out or "").strip():
        return True, "logadm -V 输出（只读校验）：" + "; ".join(
            l.strip() for l in out.splitlines()[:6] if l.strip())
    return False, (out or "logadm -V 校验未通过（配置可能有语法错误，请查 /etc/logadm.conf）")


def zones_report() -> tuple:
    """列 Solaris Zones（zoneadm list -cv，只读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，Zones（zoneadm）不可用（降级为文档指引）"
    if not shutil.which("zoneadm"):
        return False, "未找到 zoneadm（本机未启用 Zones 虚拟化）"
    rc, out = common.run("zoneadm list -cv 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "zoneadm list 无输出（无 zone 或无权限，非全局区无法列出）"
    lines = ["Solaris Zones（zoneadm list -cv 只读）："]
    for l in out.splitlines()[:12]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 看配置：zonecfg -z <zone> info；看资源占用：zonestat")
    return True, "\n".join(lines)


def fma_report() -> tuple:
    """列未处理硬件故障（fmadm faulty，只读；FMA 预测式自愈）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，FMA（fmadm/fmd）不可用（降级为文档指引）"
    if not shutil.which("fmadm"):
        return False, "未找到 fmadm（FMA 不可用）"
    rc, out = common.run("fmadm faulty 2>&1 | head -12", timeout=180)
    if rc != 0:
        return False, out or "fmadm faulty 执行失败（需 root 或 fmd 未运行）"
    if not (out or "").strip():
        return True, "无未处理硬件故障（fmadm faulty 为空，FMA 自愈状态良好）"
    lines = ["FMA 未处理故障（fmadm faulty 只读）："]
    for l in out.splitlines()[:12]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 修好硬件后再 fmadm repair <fmri>；勿用 acquit 掩盖未修故障")
    return True, "\n".join(lines)


def network_report() -> tuple:
    """列 Crossbow 网络栈（dladm show-link + ipadm show-addr，只读）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，dladm/ipadm 不可用（降级为文档指引）"
    if not shutil.which("dladm") and not shutil.which("ipadm"):
        return False, "未找到 dladm/ipadm（Solaris 11 Crossbow 网络栈不可用）"
    lines = ["Crossbow 网络栈（dladm/ipadm 只读）："]
    if shutil.which("dladm"):
        rc, out = common.run("dladm show-link 2>/dev/null | head -8", timeout=120)
        if rc == 0 and (out or "").strip():
            for l in out.splitlines()[:8]:
                if l.strip():
                    lines.append("   · link: " + l.strip())
    if shutil.which("ipadm"):
        rc2, addr = common.run("ipadm show-addr 2>/dev/null | head -8", timeout=120)
        if rc2 == 0 and (addr or "").strip():
            for l in addr.splitlines()[:8]:
                if l.strip():
                    lines.append("   · addr: " + l.strip())
    if len(lines) == 1:
        return False, "dladm show-link / ipadm show-addr 均无输出（无链路或无权限）"
    lines.append("   · TCP 可调项（只读）：ipadm show-prop tcp")
    return True, "\n".join(lines)


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("release_report", "发行版信息（/etc/release + uname，只读）"),
    ("pkg_report", "IPS 已装包与软件源（pkg list / pkg publisher，只读）"),
    ("smf_report", "SMF 服务状态（svcs -a / svcs -x，只读）"),
    ("zpool_report", "ZFS 存储池与健康（zpool list / status -x，只读）"),
    ("kstat_report", "内核统计（kstat unix:0:system_pages，只读）"),
    ("logadm_report", "日志轮转配置（logadm -V 校验，只读）"),
    ("zones_report", "Solaris Zones（zoneadm list -cv，只读）"),
    ("fma_report", "FMA 未处理故障（fmadm faulty，只读）"),
    ("network_report", "Crossbow 网络栈（dladm show-link / ipadm show-addr，只读）"),
)


def environment_report() -> list:
    """返回本机 System V 系统接口可用性概览（✓ 可用 / ✗ 未装/非 System V）。"""
    lines = ["Unix（System V）系统接口可用性（文档跟踪层）："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def unix_doc_list() -> list:
    """返回 Unix 接口文档参考清单（供 CLI/GUI 展示）。"""
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


# --------------------------------------------------------------------------- #
# 官方写接口（深度调优）：只往「安全方向」写，且只用各工具自己的官方子命令。       #
#   · pkg     : pkg refresh / pkg fix（按 IPS 官方清单刷新与修复）              #
#   · svcadm  : enable（只开不关）/ clear（清 maintenance，官方恢复接口）         #
#   · zfs     : zfs set atime=off|compression=lz4（只作用于新写入，安全方向）     #
#   · zpool   : scrub（官方校验，有冗余时自愈，不删数据）                        #
#   · logadm  : -r（按配置轮转，官方接口，不删日志）                             #
#   · ipadm   : set-prop -p ecn=active tcp（RFC 3168，官方协议属性接口）          #
# 关键约束：runner 以 fn() 无参派发，故参数一律内置自动探测（池名/FMRI 自动取）。   #
# --------------------------------------------------------------------------- #

def _zpool_names() -> list:
    """自动探测本机 zpool 名称列表（zpool list -H -o name）。"""
    if not shutil.which("zpool"):
        return []
    rc, out = common.run("zpool list -H -o name 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def _maintenance_fmris() -> list:
    """自动探测处于 maintenance 状态的服务 FMRI 列表（svcs -a -H -o STATE,FMRI）。"""
    if not shutil.which("svcs"):
        return []
    rc, out = common.run("svcs -a -H -o STATE,FMRI 2>/dev/null | awk '$1==\"maintenance\"{print $2}'",
                         timeout=180)
    if rc != 0 or not (out or "").strip():
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def ips_pkg_refresh() -> tuple:
    """刷新 IPS publisher 目录（pkg refresh，官方；只更新本地元数据）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，IPS 写接口不可用（降级为文档指引）"
    if not shutil.which("pkg"):
        return False, "未找到 pkg（IPS 不可用），跳过"
    rc, out = common.run("pkg refresh", timeout=600)
    if rc != 0:
        return False, out or "pkg refresh 失败（需 root 或网络不可达）"
    return True, ("pkg refresh 已完成（IPS 官方接口；只刷新 publisher 目录与本地元数据，"
                  "不装不卸任何包；只读核对 pkg publisher）")


def ips_pkg_fix() -> tuple:
    """按 IPS 官方清单校验并修复不一致文件（pkg fix，官方）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，IPS 写接口不可用（降级为文档指引）"
    if not shutil.which("pkg"):
        return False, "未找到 pkg（IPS 不可用），跳过"
    rc, vout = common.run("pkg verify 2>/dev/null | tail -3", timeout=900)
    rc2, out = common.run("pkg fix", timeout=1800)
    if rc2 != 0:
        return False, out or "pkg fix 失败（需 root；无不一致时也会正常返回）"
    tail = (vout or "").strip()
    return True, (f"pkg fix 已完成（IPS 官方接口；按 manifest 还原被改动的文件，"
                  f"不删用户数据）" + (f"｜verify 提示：{tail}" if tail else ""))


def smf_enable_fmd() -> tuple:
    """开启故障管理守护（svcadm enable svc:/system/fmd:default，只开不关）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，SMF 写接口不可用（降级为文档指引）"
    if not shutil.which("svcadm"):
        return False, "未找到 svcadm（SMF 不可用），跳过"
    fmri = "svc:/system/fmd:default"
    rc, out = common.run(f"svcadm enable {fmri}", timeout=180)
    if rc != 0:
        return False, out or f"svcadm enable {fmri} 失败（需 root）"
    return True, (f"已启用 {fmri}（SMF 官方接口；FMA 预测式自愈守护，"
                  "本工具只 enable 不 disable，绝不关关键服务）")


def smf_clear_maintenance() -> tuple:
    """清除 maintenance 状态（svcadm clear，官方恢复接口；FMRI 自动探测）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，SMF 写接口不可用（降级为文档指引）"
    if not shutil.which("svcadm"):
        return False, "未找到 svcadm（SMF 不可用），跳过"
    fmris = _maintenance_fmris()
    if not fmris:
        return True, "无处于 maintenance 状态的服务（svcs -a 未见 maintenance），无需清理"
    done, failed = [], []
    for f in fmris[:5]:
        rc, out = common.run(f"svcadm clear {f}", timeout=180)
        (done if rc == 0 else failed).append(f)
    if not done:
        return False, "svcadm clear 全部失败（需 root）：" + ", ".join(failed)
    tail = f"；失败 {len(failed)} 个" if failed else ""
    return True, (f"已清 maintenance：{', '.join(done)}（SMF 官方恢复接口，"
                  f"只清状态、不做启停{tail}；原因仍看 svcs -x）")


def zfs_atime_off() -> tuple:
    """关闭 atime 更新（zfs set atime=off，官方；少写元数据、减写放大）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，ZFS 写接口不可用（降级为文档指引）"
    if not shutil.which("zfs"):
        return False, "未找到 zfs（本机未使用 ZFS），跳过"
    pools = _zpool_names()
    if not pools:
        return False, "未探测到 zpool（zpool list 无输出），跳过"
    done = []
    for p in pools:
        rc, _ = common.run(f"zfs set atime=off {p}", timeout=300)
        if rc == 0:
            done.append(p)
    if not done:
        return False, "zfs set atime=off 失败（需 root 或池只读）"
    return True, (f"atime=off 已设于：{', '.join(done)}（ZFS 官方属性；"
                  "读文件不再回写访问时间戳，减写放大；只作用于设置后的新访问）")


def zfs_compression_lz4() -> tuple:
    """开启 LZ4 压缩（zfs set compression=lz4，官方；低 CPU 换空间）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，ZFS 写接口不可用（降级为文档指引）"
    if not shutil.which("zfs"):
        return False, "未找到 zfs（本机未使用 ZFS），跳过"
    pools = _zpool_names()
    if not pools:
        return False, "未探测到 zpool（zpool list 无输出），跳过"
    done = []
    for p in pools:
        rc, _ = common.run(f"zfs set compression=lz4 {p}", timeout=300)
        if rc == 0:
            done.append(p)
    if not done:
        return False, "zfs set compression=lz4 失败（需 root、或内核不支持 lz4）"
    return True, (f"compression=lz4 已设于：{', '.join(done)}（ZFS 官方属性；"
                  "只压缩新写入块，不重写已有数据，可随时改回 off）")


def zpool_scrub() -> tuple:
    """发起 ZFS 池校验（zpool scrub，官方；按校验和校验并在有冗余时自愈）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，ZFS 写接口不可用（降级为文档指引）"
    if not shutil.which("zpool"):
        return False, "未找到 zpool（本机未使用 ZFS），跳过"
    pools = _zpool_names()
    if not pools:
        return False, "未探测到 zpool（zpool list 无输出），跳过"
    done = []
    for p in pools:
        rc, _ = common.run(f"zpool scrub {p}", timeout=300)
        if rc == 0:
            done.append(p)
    if not done:
        return False, "zpool scrub 启动失败（需 root，或池正在 scrub）"
    return True, (f"已发起 scrub：{', '.join(done)}（OpenZFS 官方接口；后台按校验和校验、"
                  "有冗余时自愈；进度看 zpool status）")


def logadm_rotate_now() -> tuple:
    """按官方配置立即轮转一次日志（logadm -r，官方；只轮转不删历史）。"""
    if not _is_unix():
        return False, "当前非 System V Unix，logadm 写接口不可用（降级为文档指引）"
    if not shutil.which("logadm"):
        return False, "未找到 logadm（日志轮转由其他机制管理），跳过"
    rc, out = common.run("logadm -r", timeout=600)
    if rc != 0:
        return False, out or "logadm -r 失败（需 root；或配置有语法错误，先 logadm -V）"
    return True, ("logadm -r 已按 /etc/logadm.conf 轮转一次（官方接口；"
                  "改名归档、按 -C 淘汰最旧档，不删正在写的日志）")


def ipadm_tcp_ecn(enable: bool = True) -> tuple:
    """TCP 开/关 ECN（ipadm set-prop -p ecn=active tcp，官方 + RFC 3168）。

    Solaris 11 起 TCP 可调项由 ipadm 管（取代 ndd）；active 即主动发起 ECN 协商，
    拥塞链路下比丢包降速更稳。本工具只开不关（passive/off 时不改）。
    """
    if not _is_unix():
        return False, "当前非 System V Unix，ipadm 写接口不可用（降级为文档指引）"
    if not shutil.which("ipadm"):
        return False, "未找到 ipadm（非 Solaris 11+ Crossbow 网络栈），跳过"
    if not enable:
        return False, "本工具只往安全方向写：不做 ecn 的关闭（active→passive/off）"
    rc, out = common.run("ipadm set-prop -p ecn=active tcp", timeout=180)
    if rc != 0:
        return False, out or "ipadm set-prop ecn 失败（需 root 或该属性不被支持）"
    return True, ("ecn=active（ipadm 官方接口 + RFC 3168；拥塞时用标记代替丢包降速；"
                  "只读核对 ipadm show-prop tcp，属性随接口配置持久化）")


# 官方写接口清单（仅用于展示，**不在展示时调用**——调用即写系统）。
# 每项：(函数名, 官方写子命令说明)
TUNES = (
    ("ips_pkg_refresh", "pkg refresh（刷新 IPS publisher 目录与本地元数据，不装不卸）"),
    ("ips_pkg_fix", "pkg fix（按 IPS 官方清单校验并还原被改动的文件）"),
    ("smf_enable_fmd", "svcadm enable svc:/system/fmd:default（开 FMA 自愈守护，只开不关）"),
    ("smf_clear_maintenance", "svcadm clear <fmri>（清 maintenance，FMRI 自动探测）"),
    ("zfs_atime_off", "zfs set atime=off <pool>（关访问时间回写，减写放大）"),
    ("zfs_compression_lz4", "zfs set compression=lz4 <pool>（低 CPU 换空间，只压新写入）"),
    ("zpool_scrub", "zpool scrub <pool>（OpenZFS 官方校验，有冗余时自愈）"),
    ("logadm_rotate_now", "logadm -r（按官方配置立即轮转一次，不删历史）"),
    ("ipadm_tcp_ecn", "ipadm set-prop -p ecn=active tcp（RFC 3168 ECN，官方协议属性接口）"),
)


def unix_tune_list() -> list:
    """返回 Unix 官方写接口（深度调优）清单，供 CLI/GUI 展示。只读展示，不执行。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
