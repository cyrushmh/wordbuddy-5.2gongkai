"""同人登录的多设备硬件资源共享（算力共享，数据不共享）。

用户要求：
> 如果同一个人登录的，那么所登录的设备、硬件资源、计算、GPU、NPU、TPU、CPU、
> 网络等共享共享，除了个人数据和关键资产数据，以防盗用他人网络互联互通能力。

因此本模块的三条硬边界：

1. **只共享算力与网络**：CPU / 内存 / GPU / NPU / TPU / 网络出口可被同一身份的
   其他设备借用；**个人数据与关键资产数据（凭据、密钥、钱包、通讯录、文档等）
   一律不共享**，任何对它们的访问请求都被 :func:`policy_check` 直接拒绝并记审计。
2. **先认定「同一人」再共享**：以 :mod:`sysweeper.native.netauth` 的跨设备**身份
   指纹**判定同一人（相同验证信息 + 相同共享口令 + 同一网络维度 => 同一指纹）。
   指纹是 PBKDF2 单向派生的，伪造者拿不到原始两项信息与口令就无法冒充，
   用于**防止他人盗用你的网络互联互通能力**（蹭算力 / 蹭网）。
3. **只落盘指纹与授权种类**，绝不落盘任何个人信息、文件清单或资产数据。

只读探测全部返回 ``(ok, msg)`` 或纯字典；无对应硬件/非对应平台一律优雅降级为
「未探测到」，永不报错中断。
"""

from __future__ import annotations

import json
import os
import platform
import socket
import time
from typing import Dict, List, Optional, Tuple

DEFAULT_PATH = os.path.expanduser("~/.config/sysweeper/reshare.json")
AUDIT_PATH = os.path.expanduser("~/.config/sysweeper/reshare-audit.log")
_AUDIT_MAX = 500

# --------------------------------------------------------------------------- #
# 共享域：可共享（算力/网络） vs 永不共享（个人数据/关键资产）                    #
# --------------------------------------------------------------------------- #

#: 可共享的资源种类 —— 只有「算力与网络」，不含任何数据本体。
SHAREABLE_KINDS: Tuple[str, ...] = (
    "cpu",        # CPU 算力（核心数 / 架构）
    "memory",     # 内存容量（作为算力配额，不含内存内容）
    "gpu",        # GPU 算力（渲染 / 通用计算）
    "npu",        # NPU 神经网络算力
    "tpu",        # TPU 张量算力（含边缘 TPU）
    "network",    # 网络出口与带宽（互联互通能力）
)

#: **永不共享** —— 个人数据与关键资产数据。任何请求一律拒绝。
NEVER_SHARE: Tuple[str, ...] = (
    "personal_data",     # 个人数据：文档、照片、聊天记录、浏览历史
    "contacts",          # 通讯录 / 社交关系
    "credentials",       # 账号口令、会话令牌、Cookie
    "crypto_keys",       # 私钥、密钥库、证书私钥
    "asset_data",        # 关键资产数据：钱包、交易记录、合同、财务账目
    "biometric",         # 生物特征
    "storage_content",   # 存储内容本体（只读算力可借，文件不借）
)

#: 每种可共享资源的说明（用于报告与授权确认）
KIND_LABELS: Dict[str, str] = {
    "cpu": "CPU 算力",
    "memory": "内存容量（配额，不含内容）",
    "gpu": "GPU 算力",
    "npu": "NPU 神经网络算力",
    "tpu": "TPU 张量算力",
    "network": "网络出口与带宽",
    "personal_data": "个人数据（永不共享）",
    "contacts": "通讯录（永不共享）",
    "credentials": "凭据令牌（永不共享）",
    "crypto_keys": "密钥私钥（永不共享）",
    "asset_data": "关键资产数据（永不共享）",
    "biometric": "生物特征（永不共享）",
    "storage_content": "存储内容（永不共享）",
}


def policy_check(kind: str) -> Tuple[bool, str]:
    """访问策略：该资源种类是否允许共享。返回 (允许, 说明)。

    ``NEVER_SHARE`` 中的个人数据与关键资产数据**永远返回 False**，
    这是防数据被盗用的底线；被拒绝的请求会写入审计日志（不含任何个人信息）。
    """
    k = str(kind or "").strip().casefold()
    if k in NEVER_SHARE:
        audit("deny", k, "个人数据/关键资产数据永不共享")
        return False, f"{KIND_LABELS.get(k, k)}：属于个人数据或关键资产数据，永不共享"
    if k in SHAREABLE_KINDS:
        return True, f"{KIND_LABELS.get(k, k)}：属于算力/网络，可被同一身份的设备共享"
    return False, f"未知资源种类 {kind!r}（默认拒绝）"


# --------------------------------------------------------------------------- #
# 只读探测：本机可被共享的算力与网络清单                                          #
# --------------------------------------------------------------------------- #

def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _listdir(path: str) -> List[str]:
    try:
        return sorted(os.listdir(path))
    except OSError:
        return []


def _cpu_info() -> Dict[str, object]:
    cores = os.cpu_count() or 0
    model = ""
    txt = _read("/proc/cpuinfo")
    if txt:
        for line in txt.splitlines():
            if line.lower().startswith("model name"):
                model = line.split(":", 1)[1].strip()
                break
    if not model:
        model = platform.processor() or platform.machine() or "unknown"
    return {"kind": "cpu", "cores": cores, "model": model,
            "arch": platform.machine() or "unknown"}


def _memory_info() -> Dict[str, object]:
    total_mb = 0
    for line in _read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            try:
                total_mb = int(line.split()[1]) // 1024
            except (IndexError, ValueError):
                total_mb = 0
            break
    return {"kind": "memory", "total_mb": total_mb} if total_mb else {
        "kind": "memory", "total_mb": 0}


def _accel_info(kind: str, sysfs_dirs: Tuple[str, ...],
                dev_globs: Tuple[str, ...], vendor_hint: str) -> Dict[str, object]:
    """通用加速器探测：先看 sysfs 类目录，再看 /dev 下设备节点。"""
    names: List[str] = []
    for d in sysfs_dirs:
        for entry in _listdir(d):
            names.append(f"{d.rstrip('/').split('/')[-1]}/{entry}")
    for g in dev_globs:
        hits = [n for n in _listdir("/dev") if n.startswith(g)]
        names.extend(hits)
    if not names and vendor_hint:
        lspci = _read("/proc/bus/pci/devices")       # 非 Linux 上为空，自动降级
        if vendor_hint.casefold() in lspci.casefold():
            names.append(f"{vendor_hint}(pci)")
    return {"kind": kind, "count": len(names), "devices": names[:8]}


def resource_inventory() -> Dict[str, Dict[str, object]]:
    """只读探测本机可被共享的算力与网络资源。不读任何个人文件。

    返回 ``{kind: {...}}``；未探测到的种类不出现（调用方按缺省处理）。
    """
    inv: Dict[str, Dict[str, object]] = {}
    inv["cpu"] = _cpu_info()
    inv["memory"] = _memory_info()
    gpu = _accel_info("gpu", ("/sys/class/drm",), ("nvidia", "card"), "VGA")
    if gpu.get("count"):
        inv["gpu"] = gpu
    npu = _accel_info("npu", ("/sys/class/accel", "/sys/class/npu"), ("npu", "accel"), "")
    if npu.get("count"):
        inv["npu"] = npu
    tpu = _accel_info("tpu", ("/sys/class/apex",), ("apex_", "tpu"), "")
    if tpu.get("count"):
        inv["tpu"] = tpu
    ifaces = [i for i in _listdir("/sys/class/net") if i != "lo"]
    inv["network"] = {"kind": "network", "interfaces": ifaces,
                      "count": len(ifaces), "hostname": socket.gethostname()}
    return inv


def share_manifest(inventory: Optional[Dict[str, Dict[str, object]]] = None,
                   allow: Optional[List[str]] = None) -> Dict[str, object]:
    """根据清单与允许列表生成**可共享清单**（自动剔除永不共享项）。

    ``allow`` 为 None 时表示全部 :data:`SHAREABLE_KINDS` 都允许。
    返回值中 ``blocked`` 恒为 :data:`NEVER_SHARE`，用于向用户明示数据不共享。
    """
    inv = inventory if inventory is not None else resource_inventory()
    wanted = [k for k in (allow or list(SHAREABLE_KINDS))] or list(SHAREABLE_KINDS)
    offered: List[str] = []
    for k in wanted:
        ok, _ = policy_check(k)
        if ok and k in inv:
            offered.append(k)
    return {
        "host": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
        "offered": sorted(set(offered)),
        "blocked": list(NEVER_SHARE),
        "inventory": inv,
        "note": "仅共享算力与网络；个人数据与关键资产数据永不共享",
    }


# --------------------------------------------------------------------------- #
# 身份认定与授权（只落盘指纹 + 种类，绝不落盘个人信息）                            #
# --------------------------------------------------------------------------- #

def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(path: str, data: dict) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def audit(action: str, target: str, note: str = "") -> None:
    """写审计日志（只记动作与资源种类，**绝不记任何个人信息**）。"""
    try:
        d = os.path.dirname(AUDIT_PATH)
        if d:
            os.makedirs(d, exist_ok=True)
        line = json.dumps({"t": int(time.time()), "action": action,
                           "target": target, "note": note}, ensure_ascii=False)
        try:
            with open(AUDIT_PATH, encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            lines = []
        lines.append(line)
        if len(lines) > _AUDIT_MAX:
            lines = lines[-_AUDIT_MAX:]
        tmp = AUDIT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, AUDIT_PATH)
    except OSError:
        pass


def grant(peer_fp: str, kinds: Optional[List[str]] = None,
          label: str = "", path: str = DEFAULT_PATH) -> Tuple[bool, str]:
    """给同一身份的指纹授权共享某些资源种类（只存指纹与种类）。

    返回 (ok, msg)。``kinds`` 为 None 时授权全部算力/网络种类。
    ``NEVER_SHARE`` 中的种类会被自动剔除并记录拒绝审计。
    """
    fp = str(peer_fp or "").strip()
    if len(fp) < 16:
        return False, "身份指纹无效（需先用 netauth 派生）"
    wanted = list(kinds or SHAREABLE_KINDS)
    allowed: List[str] = []
    for k in wanted:
        ok, _ = policy_check(k)
        if ok:
            allowed.append(k)
    if not allowed:
        return False, "没有可共享的资源种类（个人数据与关键资产数据永不共享）"
    data = _load(path)
    peers = data.get("peers") if isinstance(data.get("peers"), dict) else {}
    peers[fp] = {"kinds": sorted(set(allowed)), "label": label,
                 "granted_at": int(time.time())}
    data["peers"] = peers
    data["version"] = 1
    _save(path, data)
    audit("grant", ",".join(sorted(set(allowed))), f"peer={fp[:12]}…")
    return True, (f"已向该身份授权共享：{sorted(set(allowed))}；"
                  f"个人数据与关键资产数据不共享（未保存任何个人信息）")


def revoke(peer_fp: str, path: str = DEFAULT_PATH) -> Tuple[bool, str]:
    """撤销某身份的共享授权（立即收回其对本机算力/网络的使用）。"""
    data = _load(path)
    peers = data.get("peers") if isinstance(data.get("peers"), dict) else {}
    if str(peer_fp) not in peers:
        return False, "该身份没有授权记录"
    del peers[str(peer_fp)]
    data["peers"] = peers
    _save(path, data)
    audit("revoke", "-", f"peer={str(peer_fp)[:12]}…")
    return True, "已撤销该身份的共享授权（其不再能使用本机算力与网络）"


def grants(path: str = DEFAULT_PATH) -> Dict[str, dict]:
    """返回当前授权表（只含指纹与种类，不含任何个人信息）。"""
    data = _load(path)
    peers = data.get("peers")
    return dict(peers) if isinstance(peers, dict) else {}


def is_allowed(peer_fp: str, kind: str, path: str = DEFAULT_PATH) -> Tuple[bool, str]:
    """判定某身份能否使用某资源：先查策略（数据类一律拒绝），再查授权表。"""
    ok, why = policy_check(kind)
    if not ok:
        return False, why
    peers = grants(path)
    rec = peers.get(str(peer_fp))
    if not rec:
        audit("deny", str(kind), "未授权身份（防他人盗用互联互通能力）")
        return False, "该身份未获授权（同一人需先用相同的两项验证信息+共享口令完成认定）"
    if str(kind) not in list(rec.get("kinds", [])):
        return False, f"该身份未被授权使用 {kind}"
    return True, f"允许使用 {KIND_LABELS.get(kind, kind)}"


# --------------------------------------------------------------------------- #
# 报告 / 任务派发无参包装                                                        #
# --------------------------------------------------------------------------- #

def reshare_report() -> Tuple[bool, str]:
    """报告本机可共享算力与网络 + 当前授权情况（只读）。"""
    try:
        inv = resource_inventory()
        man = share_manifest(inv)
        lines = [f"同人设备资源共享（{man['host']} / {man['platform']}）：",
                 "  · 可共享（算力与网络）："]
        for k in SHAREABLE_KINDS:
            info = inv.get(k)
            if not info:
                lines.append(f"      - {KIND_LABELS[k]}：未探测到")
                continue
            if k == "cpu":
                detail = f"{info.get('cores')} 核 / {info.get('arch')}"
            elif k == "memory":
                detail = f"{info.get('total_mb')} MB"
            elif k == "network":
                detail = f"{info.get('count')} 个接口 {list(info.get('interfaces', []))}"
            else:
                detail = f"{info.get('count')} 个设备"
            lines.append(f"      - {KIND_LABELS[k]}：{detail}")
        lines.append("  · 永不共享（个人数据与关键资产数据）：")
        for k in NEVER_SHARE:
            lines.append(f"      - {KIND_LABELS[k]}")
        peers = grants()
        lines.append(f"  · 当前授权身份：{len(peers)} 个（仅存指纹与种类）")
        for fp, rec in peers.items():
            lines.append(f"      - {fp[:12]}…  种类={list(rec.get('kinds', []))}")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"资源共享报告生成失败: {e}"


def reshare_demo() -> Tuple[bool, str]:
    """无参演示「同一人→共享算力 / 非同一人→拒绝；数据类一律拒绝」。

    **不落盘任何真实数据**（用临时目录），原始验证信息用完即弃。
    """
    try:
        import tempfile
        from . import netauth as _na
        tmp = os.path.join(tempfile.mkdtemp(), "reshare.json")
        me = {"name": "示例用户", "id_number": "110000000000000000"}
        fp_me = _na.identity_fingerprint(me, "demo_net", "demo-pass")
        fp_other = _na.identity_fingerprint(
            {"name": "他人", "id_number": "999"}, "demo_net", "demo-pass")
        ok_g, _ = grant(fp_me, ["cpu", "gpu", "network"], label="示例", path=tmp)
        a1, _ = is_allowed(fp_me, "cpu", path=tmp)
        a2, _ = is_allowed(fp_other, "cpu", path=tmp)
        d1, _ = is_allowed(fp_me, "personal_data", path=tmp)
        d2, _ = is_allowed(fp_me, "asset_data", path=tmp)
        ok_r, _ = revoke(fp_me, path=tmp)
        a3, _ = is_allowed(fp_me, "cpu", path=tmp)
        passed = ok_g and a1 and not a2 and not d1 and not d2 and ok_r and not a3
        return passed, ("同人资源共享演示（临时目录，未落盘真实数据）："
                        f"同一人用 CPU={a1}；他人={a2}（拒绝，防盗用）；"
                        f"个人数据={d1}、关键资产={d2}（拒绝，永不共享）；"
                        f"撤销后={a3}（已收回）。")
    except Exception as e:  # noqa: BLE001
        return False, f"演示失败: {e}"


__all__ = [
    "SHAREABLE_KINDS", "NEVER_SHARE", "KIND_LABELS", "DEFAULT_PATH", "AUDIT_PATH",
    "policy_check", "resource_inventory", "share_manifest",
    "grant", "revoke", "grants", "is_allowed", "audit",
    "reshare_report", "reshare_demo",
]
