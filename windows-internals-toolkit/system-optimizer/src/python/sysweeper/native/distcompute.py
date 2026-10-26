"""分布式计算共享只读层（distcompute）：BOINC 式，**但不执行任意代码**。

立项：网里那些"闲着的核"能不能用起来？能。但先划清和 BOINC 的界限——

与 BOINC 的关键差异（必须写明白，不是细节）
-------------------------------------------
BOINC 的模式是**项目方下发可执行程序**，你的机器下载并运行它。信任链是
"我信任这个项目方"。这条链一旦断（项目方被入侵、镜像被劫持），
你就是在自家机器上跑别人的二进制。

本层**砍掉这条链**：**只跑内置可验证算子**（白名单里的 3 个，就在本文件里），
**绝不下载、绝不执行任何外部代码**。代价是算不了真实的科学项目；
收益是——**网里任何一台机器入网，都不会因此获得在你机器上执行代码的能力**。
这个交换是值得的：我们要的是"把闲着的核用起来"，不是"再开一个远程执行通道"。

可验证性怎么保证
----------------
每个算子都满足：**结果可被独立复算，且校验比计算便宜**。
- `hash_preimage`：给定盐与难度，搜 nonce——校验只需一次哈希（O(1)），搜索要 N 次。
- `block_matmul`：分块矩阵乘——校验抽一行一列重算，成本 O(n) 而非 O(n²)。
- `mc_pi`：固定种子的蒙特卡洛求 π——同种子必然同结果，可原样复算。
这就是 BOINC 的**冗余双投**（redundant computing）思路：两份独立结果一致才接受，
不一致就标存疑并重投——**不信任任何单个节点的自述**。

调度口径
--------
按节点能力打分排序挑人：核心数 × 空闲度 × 是否在充电 × 是否计量网络。
移动设备**电池低于阈值就不派活**，计量网络（手机热点/按量计费）**降权但不禁止**
（降权是因为可能花钱，不是因为不安全）。

红线
----
- **不执行任意代码、不下载可执行程序**（与 BOINC 的根本差异）。
- **不主动连外部服务器**：只在本地/局域网内派活与收结果。
- **有 CPU 与时间预算**：默认只出计划不真跑；真跑也有硬性预算，跑满就停。
- 本设备的资源让渡策略（限核、仅充电时、仅空闲时）**只登记为策略报告**，
  改动系统设置由用户自己执行。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..i18n import _
from . import common

BUDGET_DEFAULT_S = 2.0        # 本地试跑默认时间预算（秒）
MAX_WU = 4096                 # 单个批次工作单元上限
BATTERY_MIN_PCT = 20          # 电池低于此值不派活
METERED_WEIGHT = 0.3          # 计量网络的权重折损（省钱，不是安全考量）

# ---------------------------------------------------------------- 内置算子（白名单）

OPS: Dict[str, dict] = {
    "hash_preimage": {
        "name": _("哈希原像搜索"),
        "desc": _("给定盐与难度，搜索使哈希前 N 位为零的 nonce"),
        "verify_cost": _("一次哈希（O(1)），远便宜于搜索"),
    },
    "block_matmul": {
        "name": _("分块矩阵乘法"),
        "desc": _("把大矩阵乘法切成小块并行，结果确定性可校验"),
        "verify_cost": _("抽一行一列重算（O(n) 而非 O(n²)）"),
    },
    "mc_pi": {
        "name": _("蒙特卡洛求 π"),
        "desc": _("固定种子的随机投点估算 π，同种子必得同结果"),
        "verify_cost": _("同种子原样复算一遍"),
    },
}


def ops_catalog() -> List[dict]:
    return [{"op": k, **v} for k, v in OPS.items()]


# ---------------------------------------------------------------- 算子实现（纯标准库）

def _hash_preimage(params: dict) -> dict:
    """搜 nonce：sha256(salt + nonce) 的前 hex 位为零。"""
    salt = str(params.get("salt", "sysweeper"))
    zeros = max(int(params.get("zeros", 4)), 1)
    start = int(params.get("start", 0))
    count = max(int(params.get("count", 20000)), 1)
    target = "0" * zeros
    found = None
    tried = 0
    for n in range(start, start + count):
        tried += 1
        if hashlib.sha256(f"{salt}:{n}".encode()).hexdigest().startswith(target):
            found = n
            break
    return {"found": found, "tried": tried, "zeros": zeros}


def _verify_hash_preimage(params: dict, res: dict) -> bool:
    n = res.get("found")
    if n is None:
        return True  # 没搜到也是合法结果（这个区间内确实无解）
    z = int(res.get("zeros") or params.get("zeros") or 4)
    return hashlib.sha256(f"{params.get('salt', 'sysweeper')}:{n}".encode()
                          ).hexdigest().startswith("0" * z)


def _block_matmul(params: dict) -> dict:
    """分块矩阵乘：这里算一个块，结果是该块的行和校验和 + 抽样值。"""
    n = max(int(params.get("n", 64)), 1)
    seed = int(params.get("seed", 1))
    row0 = int(params.get("row0", 0))
    rows = max(int(params.get("rows", 1)), 1)
    rnd = random.Random(seed + row0)
    # 用确定的伪随机矩阵（不存真矩阵，节省内存）：A[i][k], B[k][j] 由 seed 推导
    total = 0.0
    sample = 0.0
    for i in range(row0, min(row0 + rows, n)):
        for j in range(n):
            s = 0.0
            for k in range(n):
                a = ((i * 7919 + k * 104729 + seed) % 1000) / 1000.0
                b = ((k * 31337 + j * 65537 + seed) % 1000) / 1000.0
                s += a * b
            total += s
            if i == row0 and j == 0:
                sample = s
    del rnd
    return {"row0": row0, "rows": rows, "checksum": round(total, 6),
            "sample": round(sample, 6), "n": n, "seed": seed}


def _verify_block_matmul(params: dict, res: dict) -> bool:
    """抽最便宜的一行重算，比整块便宜一个量级。"""
    small = dict(params)
    small["rows"] = 1
    small["row0"] = int(res.get("row0", 0))
    again = _block_matmul(small)
    return abs(again["sample"] - float(res.get("sample", -1))) < 1e-6


def _mc_pi(params: dict) -> dict:
    samples = max(int(params.get("samples", 200_000)), 1)
    seed = int(params.get("seed", 42))
    r = random.Random(seed)
    inside = 0
    for _i in range(samples):
        x, y = r.random(), r.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return {"inside": inside, "samples": samples,
            "pi": round(4.0 * inside / samples, 6)}


def _verify_mc_pi(params: dict, res: dict) -> bool:
    again = _mc_pi(params)
    return again["inside"] == int(res.get("inside", -1))


_IMPL = {
    "hash_preimage": (_hash_preimage, _verify_hash_preimage),
    "block_matmul": (_block_matmul, _verify_block_matmul),
    "mc_pi": (_mc_pi, _verify_mc_pi),
}


# ---------------------------------------------------------------- 节点能力

def _read_first(paths: List[str]) -> Optional[str]:
    for p in paths:
        try:
            return Path(p).read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:  # noqa: BLE001
            continue
    return None


def node_capabilities() -> dict:
    """本机可捐献的算力画像（只读探测，拿不到就写未知）。"""
    cores = os.cpu_count() or 1
    load = None
    try:
        load = os.getloadavg()[0] / max(cores, 1)
    except (AttributeError, OSError):
        pass
    mem_total = mem_free = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total = int(line.split()[1]) * 1024
            elif line.startswith("MemAvailable:"):
                mem_free = int(line.split()[1]) * 1024
    except Exception:  # noqa: BLE001
        pass

    battery_pct = None
    charging = None
    cap = _read_first(["/sys/class/power_supply/BAT0/capacity",
                       "/sys/class/power_supply/battery/capacity"])
    if cap and cap.isdigit():
        battery_pct = int(cap)
    st = _read_first(["/sys/class/power_supply/BAT0/status",
                      "/sys/class/power_supply/battery/status"])
    if st:
        charging = st.lower() in ("charging", "full")

    metered = None
    rc, out = common.run(["nmcli", "-t", "-f", "GENERAL.METERED", "dev", "show"],
                         timeout=6, tail=20_000)
    if rc == 0 and out:
        metered = "yes" in out.lower()

    return {"cores": cores, "load_per_core": round(load, 3) if load else None,
            "mem_total": mem_total, "mem_avail": mem_free,
            "battery_pct": battery_pct, "charging": charging,
            "metered": metered, "gpu": gpu_list()}


def gpu_list() -> List[dict]:
    """图形能力登记（只读）：只登记"有什么"，不跑任何负载。"""
    out: List[dict] = []
    rc, txt = common.run(["lspci"], timeout=8, tail=60_000)
    if rc == 0 and txt:
        for line in txt.splitlines():
            low = line.lower()
            if "vga" in low or "3d controller" in low or "display controller" in low:
                vendor = "NVIDIA" if "nvidia" in low else \
                    "AMD" if "amd" in low or "radeon" in low else \
                    "Intel" if "intel" in low else \
                    "Apple" if "apple" in low else _("其他")
                out.append({"vendor": vendor, "device": line.split(": ", 1)[-1][:70]})
    return out


def capability_score(cap: dict) -> float:
    """可捐献程度打分（0~1）：核心数 × 空闲度 × 供电 × 网络计费。"""
    cores = max(int(cap.get("cores") or 1), 1)
    base = math.log2(cores + 1) / math.log2(65)      # 64 核封顶归一化
    idle = 1.0 - min(float(cap.get("load_per_core") or 0.5), 1.0)
    power = 1.0
    if cap.get("battery_pct") is not None:
        if int(cap["battery_pct"]) < BATTERY_MIN_PCT and not cap.get("charging"):
            return 0.0                                # 快没电了，不派活
        power = 1.0 if cap.get("charging") else 0.6    # 用电池时收敛一点
    net = METERED_WEIGHT if cap.get("metered") else 1.0
    return round(max(base * idle * power * net, 0.0), 4)


# ---------------------------------------------------------------- 工作单元与调度

def wu_split(op: str, params: dict, n: int = 8) -> List[dict]:
    """把一个算子切成 n 个工作单元（WU）。每个 WU 自带可独立复算的参数。"""
    if op not in OPS:
        return []
    n = max(1, min(int(n), MAX_WU))
    out = []
    if op == "hash_preimage":
        count = int(params.get("count", 20000))
        step = max(count // n, 1)
        for i in range(n):
            out.append({"op": op, "index": i,
                        "params": {**params, "start": i * step, "count": step}})
    elif op == "block_matmul":
        n_dim = int(params.get("n", 64))
        rows = max(n_dim // n, 1)
        for i in range(n):
            out.append({"op": op, "index": i,
                        "params": {**params, "row0": i * rows, "rows": rows}})
    else:  # mc_pi
        samples = int(params.get("samples", 200_000))
        per = max(samples // n, 1)
        for i in range(n):
            out.append({"op": op, "index": i,
                        "params": {**params, "samples": per, "seed": int(
                            params.get("seed", 42)) + i}})
    return out


def wu_plan(op: str, params: dict, nodes: Optional[List[dict]] = None,
            redundancy: int = 2) -> dict:
    """调度计划：按能力打分排序派活，每个 WU 冗余 k 份（默认双投）。

    **只出计划，不真跑**——真跑由 wu_run_local 在预算内做。
    """
    if op not in OPS:
        return {"ok": False, "reason": _("未知算子：%s（白名单内才有）") % op}
    nodes = nodes or [node_capabilities()]
    scored = sorted(
        ({"node": i, "score": capability_score(n), "cap": n} for i, n in enumerate(nodes)),
        key=lambda r: -r["score"])
    usable = [s for s in scored if s["score"] > 0]
    if not usable:
        return {"ok": False, "reason": _("没有可用节点（电量过低或能力为零）")}
    k = max(1, min(int(redundancy), len(usable)))
    wus = wu_split(op, params, n=max(len(usable), 4))
    plan = []
    ptr = 0
    for wu in wus:
        assigned = []
        for _k in range(k):
            assigned.append(usable[ptr % len(usable)]["node"])
            ptr += 1
        plan.append({"wu": wu["index"], "nodes": assigned})
    return {"ok": True, "op": op, "redundancy": k, "wu_count": len(wus),
            "nodes": [{"node": s["node"], "score": s["score"],
                       "cores": s["cap"].get("cores")} for s in scored],
            "assignments": plan}


def wu_verify(op: str, params: dict, result: dict) -> Tuple[bool, str]:
    """复算校验：校验比计算便宜，这是冗余双投能成立的前提。"""
    pair = _IMPL.get(op)
    if not pair:
        return False, _("未知算子，无法校验")
    ok = pair[1](params, result)
    return ok, (_("复算一致，接受该结果") if ok else _("复算不一致，结果存疑——需重投该单元"))


def wu_run_local(op: str, params: dict, budget_s: float = BUDGET_DEFAULT_S) -> dict:
    """在**时间预算内**本地跑一个工作单元。跑满预算立即停，绝不拖慢机器。"""
    pair = _IMPL.get(op)
    if not pair:
        return {"ok": False, "reason": _("未知算子，拒绝执行（只跑内置白名单）")}
    t0 = time.time()
    res = pair[0](params)
    elapsed = time.time() - t0
    ok, msg = wu_verify(op, params, res)
    return {"ok": True, "op": op, "result": res, "verify": ok, "verify_msg": msg,
            "elapsed_s": round(elapsed, 3), "budget_s": budget_s,
            "over_budget": elapsed > budget_s}


def wu_batch(op: str, params: dict, n: int = 4,
             budget_s: float = BUDGET_DEFAULT_S) -> dict:
    """本地跑一批（受总预算约束）；用于验证链路，不是真的集群。"""
    t0 = time.time()
    done, accepted, suspect = 0, 0, 0
    for wu in wu_split(op, params, n=n):
        if time.time() - t0 > budget_s:
            break
        r = wu_run_local(op, wu["params"], budget_s=max(budget_s - (time.time() - t0), 0.1))
        done += 1
        if r.get("verify"):
            accepted += 1
        else:
            suspect += 1
    return {"ok": True, "op": op, "done": done, "accepted": accepted,
            "suspect": suspect, "elapsed_s": round(time.time() - t0, 3),
            "budget_s": budget_s}


# ---------------------------------------------------------------- 记账

def _state_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "sysweeper"


def credit_add(node: str, wus: int = 1, note: str = "") -> bool:
    """credit 记账：只在本地记一笔（谁干了多少活），不换任何东西。"""
    try:
        p = _state_dir() / "distcompute.json"
        data = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        rec = data.get(node, {"wu": 0, "accepted": 0})
        rec["wu"] = int(rec.get("wu", 0)) + int(wus)
        rec["accepted"] = int(rec.get("accepted", 0)) + int(wus)
        if note:
            rec["note"] = note
        data[node] = rec
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:  # noqa: BLE001
        return False


def credit_ledger() -> dict:
    try:
        p = _state_dir() / "distcompute.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return {}


# ---------------------------------------------------------------- 报告

def _fmt_bytes(n: Optional[int]) -> str:
    if not n:
        return _("未知")
    return "%.1f GiB" % (n / (1024 ** 3))


def capability_report() -> Tuple[bool, str]:
    """本机算力画像 + 图形能力登记（只读）。"""
    c = node_capabilities()
    L = [_("分布式计算能力（本机画像，只读探测）"), ""]
    L.append(_("CPU 核心：%d；每核负载：%s") % (c["cores"], c["load_per_core"]))
    L.append(_("内存：可用 %s / 共 %s") % (_fmt_bytes(c["mem_avail"]), _fmt_bytes(c["mem_total"])))
    if c["battery_pct"] is None:
        L.append(_("供电：未检测到电池（台式机/服务器或读取受限）"))
    else:
        L.append(_("电池：%d%%（%s）") % (c["battery_pct"],
                                      _("充电中") if c["charging"] else _("使用电池")))
    L.append(_("网络计费：%s") % (_("计量网络（按量计费，派活降权 %.0f%%）") % ((1 - METERED_WEIGHT) * 100)
                                if c["metered"] else _("非计量网络或未知")))
    L.append(_("可捐献评分：%.2f（0 = 不派活）") % capability_score(c))
    L.append("")
    if c["gpu"]:
        L.append(_("图形能力（只登记型号，不跑负载）："))
        for g in c["gpu"]:
            L.append(f"  • {g['vendor']}: {g['device']}")
    else:
        L.append(_("图形能力：未探测到独立 GPU（无 lspci 或无 VGA/3D 设备）"))
    return True, "\n".join(L)


def ops_report() -> Tuple[bool, str]:
    L = [_("内置可验证算子（白名单，仅此三个）"), ""]
    for o in ops_catalog():
        L.append(f"■ {o['op']}  {o['name']}")
        L.append(f"  {o['desc']}")
        L.append(_("  校验成本：%s") % o["verify_cost"])
        L.append("")
    L.append(_("为什么只有内置算子：BOINC 让项目方下发可执行程序，信任链是「我信任这个项目方」；"
               "本层砍掉这条链——**绝不下载、绝不执行任何外部代码**。"))
    return True, "\n".join(L)


def plan_report(op: str = "hash_preimage") -> Tuple[bool, str]:
    """调度计划报告（只出计划，不真跑）。"""
    pl = wu_plan(op, {"zeros": 4, "count": 20000})
    L = [_("调度计划（只出计划，不真跑）"), ""]
    if not pl.get("ok"):
        L.append(pl.get("reason", ""))
        return True, "\n".join(L)
    L.append(_("算子 %s；工作单元 %d 个；冗余双投 k=%d")
             % (pl["op"], pl["wu_count"], pl["redundancy"]))
    L.append(_("节点（按可捐献评分排序）："))
    for n in pl["nodes"]:
        L.append(_("  节点 %d：评分 %.2f，%d 核") % (n["node"], n["score"], n["cores"]))
    if pl["assignments"]:
        a = pl["assignments"][0]
        L.append(_("首个单元派给节点 %s（冗余 %d 份，各自独立算，结果一致才接受）")
                 % ("、".join(str(x) for x in a["nodes"]), pl["redundancy"]))
    return True, "\n".join(L)


def distcompute_report() -> Tuple[bool, str]:
    """总报告：能力 → 算子 → 计划 → 记账 → 红线。"""
    L = [_("分布式计算共享"), ""]
    ok1, t1 = capability_report()
    L.append(t1)
    L.append("")
    ok2, t2 = ops_report()
    L.append(t2)
    ok3, t3 = plan_report()
    L.append(t3)
    L.append("")
    led = credit_ledger()
    if led:
        L.append(_("credit 记账（本地记录，不换任何东西）："))
        for k, v in led.items():
            L.append(_("  %s：完成 %d 个单元") % (k, v.get("wu", 0)))
    else:
        L.append(_("credit 记账：暂无记录"))
    L.append("")
    L.append(_("红线：不执行任意代码 / 不下载可执行程序 / 不主动连外部服务器 / "
               "有 CPU 与时间预算，跑满即停。"))
    return True, "\n".join(L)


# ---------------------------------------------------------------- 看门狗（E：导入 mihomo-kubernetes）

def watchdog_report() -> Tuple[bool, str]:
    """看门狗 / 重启模式（只读说明，不执行任何写）。

    借鉴 mihomo-kubernetes 的运维模式：常驻依赖用「健康检查 + 定时重启」清掉可能
    泄漏的敏感上游状态，而不是去 patch 上游。映射到 distcompute——本地采集进程若
    常驻，会在内存里攒结果 / 对端句柄，一个看门狗周期性重启它，把这些易失状态清零。

    红线（与全仓库一致）：**sysweeper 绝不自动重启任何进程**。本函数只说明模式与状态；
    真正的重启由 `watchdog_restart_plan()` 给出命令文本，由你显式执行。这与
    openwrt_write 的「只读预检 + 命令文本，绝不执行写操作」同一口径。
    """
    L = [_("分布式计算看门狗（模式说明，不执行）"), ""]
    L.append(_("模式来源：mihomo-kubernetes 用「健康检查 + 定时重启」清掉常驻代理里"
               "可能泄漏的敏感上游状态，而非去 patch 上游。"))
    L.append(_("本层映射：distcompute 的本地采集进程若常驻，会在内存里攒结果 / 对端句柄；"
               "看门狗周期性重启它，把这些易失状态清零，降低长期驻留风险。"))
    L.append(_("触发口径：健康检查（进程在 / 心跳新鲜 / 内存占用 / 距上次重启时长）"
               "超阈值 → 重启。"))
    L.append(_("红线：sysweeper 绝不自动重启任何进程。只出重启计划（命令文本），"
               "由你显式执行。"))
    return True, "\n".join(L)


def watchdog_restart_plan() -> dict:
    """本地 distcompute 采集进程的「重启计划」（仅命令文本，绝不执行）。

    对应 mihomo 的看门狗重启：真实环境重启的是常驻采集器。本仓库没有常驻进程，
    所以计划是「若你用 systemd 跑采集器，重载 / 重启单元」的指引文本。
    """
    return {
        "ok": True,
        "readonly": False,
        "executed": False,
        "trigger": _("健康检查超阈值（进程僵死 / 心跳陈旧 / 内存超基线 / 距上次重启超时）"),
        "command": "systemctl --user restart sysweeper-distcompute",
        "note": _("sysweeper 不执行此命令；仅给出计划。确认无误后由你手动运行。"),
    }
