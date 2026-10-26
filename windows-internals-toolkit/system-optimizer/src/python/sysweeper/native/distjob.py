"""跨机派活层（distjob）：把分布式计算真正接到组网通道上。

上一轮 `distcompute` 只做到"出调度计划"——计划再漂亮，不派出去就是纸上谈兵。
本层补上闭环：**经组网通信通道（IPMsg / 飞鸽传书 / iptux 兼容的文本通道）
把工作单元派出去，把结果收回来，校验后才接受。**

为什么走文本通道而不是新建一个协议
----------------------------------
组网通道已经有了（meshchat，UDP 2425），再为算力派活造一套协议纯属重复建设。
WU 描述与结果都是**短文本**（几百字节），塞进一条普通消息即可：

```
SW-WU1:{"job":"...","op":"mc_pi","i":0,"p":{...},"budget":2.0}
SW-RES1:{"job":"...","i":0,"r":{...},"ms":12.3}
```

网里已有的飞鸽 / iptux 客户端会把它显示成一条普通消息——**不会干扰它们**，
只是看不懂而已；而我们自己的节点看到前缀就知道该怎么处理。

信任模型（与 distcompute 一致，不因跨机而放宽）
------------------------------------------------
- **收到的 WU 只跑白名单算子**，`op` 不在 `distcompute.OPS` 里就直接丢弃。
  别人发一句"请执行 xxx"是发不进来的——**通道里传的是参数，不是代码**。
- **收到的结果必须复算校验**：校验通过才算数，不通过标"存疑"。
  **不信任任何节点的自述**，这才是冗余双投的意义。
- **有 CPU 与时间预算**：接活方按 WU 自带的预算跑，跑满即停。

默认不发包
----------
`dispatch()` 默认 `dry_run=True`——**只编码、只出计划，不出网**。
真派活得你显式传 `dry_run=False`。这条与全工程"默认只给计划不代劳"一致。
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Dict, List, Optional, Tuple

from ..i18n import _
from . import distcompute, meshchat

WU_MAGIC = "SW-WU1:"      # 工作单元派发
RES_MAGIC = "SW-RES1:"    # 结果回传
OFFER_MAGIC = "SW-OFFER1:"  # 能力通告（我能接活）

MAX_PAYLOAD = 4096        # 单条载荷上限（超过就拒绝，不拆包——拆包等于给自己挖坑）
MAX_JOBS = 64             # 本地保留的任务数上限

_PENDING: Dict[str, dict] = {}   # job_id -> {op, units: {i: {results: [], status}}, ts}
_ACCEPTED: List[dict] = []
_SUSPECT: List[dict] = []


# ---------------------------------------------------------------- 编解码

def encode_wu(job: str, op: str, index: int, params: dict,
              budget: float = distcompute.BUDGET_DEFAULT_S) -> str:
    payload = {"job": job, "op": op, "i": int(index), "p": params,
               "budget": float(budget)}
    return WU_MAGIC + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_wu(text: str) -> Optional[dict]:
    """解析一条 WU 消息；不是我们的前缀 / JSON 坏了 / 超长 → None（不抛异常）。"""
    if not text or not text.startswith(WU_MAGIC):
        return None
    body = text[len(WU_MAGIC):]
    if len(body) > MAX_PAYLOAD:
        return None
    try:
        d = json.loads(body)
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(d, dict) or d.get("op") not in distcompute.OPS:
        return None          # 白名单外的算子：连解析都不认
    return d


def encode_res(job: str, index: int, result: dict, elapsed_ms: float) -> str:
    payload = {"job": job, "i": int(index), "r": result, "ms": round(elapsed_ms, 1)}
    return RES_MAGIC + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_res(text: str) -> Optional[dict]:
    if not text or not text.startswith(RES_MAGIC):
        return None
    body = text[len(RES_MAGIC):]
    if len(body) > MAX_PAYLOAD:
        return None
    try:
        d = json.loads(body)
    except Exception:  # noqa: BLE001
        return None
    return d if isinstance(d, dict) else None


def offer_text() -> str:
    """广播"我能接活"：带上本机能力，让派活方知道该不该派给我。"""
    cap = distcompute.node_capabilities()
    payload = {"cores": cap.get("cores"), "score": distcompute.capability_score(cap),
               "gpu": len(cap.get("gpu") or [])}
    return OFFER_MAGIC + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def decode_offer(text: str) -> Optional[dict]:
    """解析一条能力通告（SW-OFFER1:）。前缀不对 / JSON 坏了 / 超长 → None。"""
    if not text or not text.startswith(OFFER_MAGIC):
        return None
    body = text[len(OFFER_MAGIC):]
    if len(body) > MAX_PAYLOAD:
        return None
    try:
        d = json.loads(body)
    except Exception:  # noqa: BLE001
        return None
    return d if isinstance(d, dict) else None


# ---------------------------------------------------------------- 派活

def dispatch(op: str, params: dict, n: int = 4, redundancy: int = 2,
             target: Optional[str] = None,
             budget: float = distcompute.BUDGET_DEFAULT_S,
             dry_run: bool = True) -> dict:
    """派一批工作单元出去。**默认 dry_run=True：只编码不出网。**

    target 为空 → 全体广播（wall 语义）；有值 → 单播到该地址。
    每个单元冗余 k 份，各自独立算，回来校验一致才接受。
    """
    if op not in distcompute.OPS:
        return {"ok": False, "reason": _("未知算子 %s：只派白名单内的活") % op}
    job = uuid.uuid4().hex[:12]
    wus = distcompute.wu_split(op, params, n=n)
    k = max(1, min(int(redundancy), 4))
    messages: List[str] = []
    for wu in wus:
        for _r in range(k):
            messages.append(encode_wu(job, op, wu["index"], wu["params"], budget))

    sent = 0
    errors: List[str] = []
    if not dry_run:
        for m in messages:
            if len(m) > MAX_PAYLOAD:
                errors.append(_("载荷超长，已跳过"))
                continue
            ok, msg = (meshchat.send_text(target, m) if target
                       else meshchat.wall_text(m))
            if ok:
                sent += 1
            else:
                errors.append(str(msg)[:120])

    _PENDING[job] = {"op": op, "ts": int(time.time()), "k": k,
                     "units": {w["index"]: {"params": w["params"], "results": [],
                                            "status": "pending"} for w in wus}}
    while len(_PENDING) > MAX_JOBS:
        _PENDING.pop(next(iter(_PENDING)))

    return {"ok": True, "job": job, "op": op, "wu_count": len(wus),
            "redundancy": k, "messages": len(messages), "sent": sent,
            "dry_run": dry_run, "errors": errors[:5],
            "note": _("只编码不出网（dry_run）") if dry_run else _("已发出")}


# ---------------------------------------------------------------- 接活

def serve_once(timeout: float = 3.0,
               budget: float = distcompute.BUDGET_DEFAULT_S) -> dict:
    """作为算力节点接一次活：听一个包 → 是 WU 就本地算 → 回发结果。

    **只跑白名单算子**；别人发"请执行 xxx"是发不进来的——通道里传的是参数不是代码。
    """
    ok, msg = meshchat.listen_once(timeout=timeout)
    if not ok:
        return {"ok": False, "reason": msg}
    entries = _scan(WU_MAGIC)
    if not entries:
        return {"ok": False, "reason": _("收到的不是工作单元，已忽略")}
    entry, wu = entries[-1]
    r = distcompute.wu_run_local(wu["op"], wu.get("p") or {},
                                 budget_s=min(float(wu.get("budget") or budget), budget))
    result = r.get("result") or {}
    src = (entry.get("source") or "").rsplit(":", 1)[0]
    reply = encode_res(wu.get("job", ""), wu.get("i", 0), result,
                       r.get("elapsed_s", 0.0) * 1000)
    sent = False
    if src:
        sok, _smsg = meshchat.send_text(src, reply)
        sent = bool(sok)
    return {"ok": True, "job": wu.get("job"), "index": wu.get("i"),
            "op": wu["op"], "verify": r.get("verify"),
            "elapsed_s": r.get("elapsed_s"), "replied": sent, "to": src or _("（无回发地址）")}


# ---------------------------------------------------------------- 收结果

def _scan(prefix: str) -> List[Tuple[dict, dict]]:
    """从收件箱里找出本层关心的消息（按前缀），返回 (条目, 解析结果)。"""
    out: List[Tuple[dict, dict]] = []
    for e in meshchat.inbox():
        text = e.get("text", "")
        d = decode_wu(text) if prefix == WU_MAGIC else decode_res(text)
        if d is not None:
            out.append((e, d))
    return out


def apply_result(entry: dict, res: dict) -> Tuple[str, str]:
    """处理一条回传结果（**纯逻辑，不碰网络**——测试与 collect 共用）。

    返回 (状态, 原因)：accepted / suspect / ignored。
    这一步是信任模型的落点：**复算校验通过才算数**。
    """
    if not isinstance(res, dict):
        return "ignored", _("结果格式不对")
    job = str(res.get("job", ""))
    rec = _PENDING.get(job)
    if not rec:
        _SUSPECT.append({"job": job, "index": res.get("i"),
                         "why": _("无对应任务（可能是别人的任务），已忽略")})
        return "ignored", _("无对应任务")
    idx = res.get("i")
    unit = rec["units"].get(idx)
    if not unit:
        _SUSPECT.append({"job": job, "index": idx, "why": _("单元号不存在")})
        return "ignored", _("单元号不存在")
    good, why = distcompute.wu_verify(rec["op"], unit["params"], res.get("r") or {})
    if not good:
        unit["status"] = "suspect"
        _SUSPECT.append({"job": job, "index": idx, "why": why,
                         "from": entry.get("source", "")})
        return "suspect", why
    unit["results"].append(res.get("r"))
    if len(unit["results"]) >= 2 or rec["k"] == 1:
        unit["status"] = "accepted"
        _ACCEPTED.append({"job": job, "index": idx, "op": rec["op"],
                          "from": entry.get("source", "")})
        distcompute.credit_add(entry.get("source") or _("未知节点"), 1)
        return "accepted", why
    return "accepted", _("已收一份，等待冗余第二份")


def collect(timeout: float = 3.0) -> dict:
    """收一次结果：解码 → 交给 apply_result 复算校验 → 一致才接受。"""
    ok, msg = meshchat.listen_once(timeout=timeout)
    if not ok:
        return {"ok": False, "reason": msg}
    got = _scan(RES_MAGIC)
    if not got:
        return {"ok": False, "reason": _("收到的不是结果消息，已忽略")}
    accepted = suspect = 0
    for entry, res in got:
        status, _why = apply_result(entry, res)
        if status == "accepted":
            accepted += 1
        elif status == "suspect":
            suspect += 1
    return {"ok": True, "accepted": accepted, "suspect": suspect,
            "total_accepted": len(_ACCEPTED), "total_suspect": len(_SUSPECT),
            "message": msg}


def jobs() -> Dict[str, dict]:
    return dict(_PENDING)


def job_clear() -> None:
    _PENDING.clear()
    _ACCEPTED.clear()
    _SUSPECT.clear()


# ---------------------------------------------------------------- 报告

def job_report() -> Tuple[bool, str]:
    """跨机派活状态报告：派了什么、收回多少、有多少存疑。"""
    L = [_("跨机派活（经组网文本通道）"), ""]
    L.append(_("载荷格式：%s 与 %s，走同一条组网消息通道（UDP 2425）")
             % (WU_MAGIC, RES_MAGIC))
    L.append(_("信任模型：只跑白名单算子；结果必须复算校验，不信任任何节点的自述。"))
    L.append("")
    if not _PENDING:
        L.append(_("当前没有派出的任务。"))
        L.append(_("派法：dispatch('mc_pi', {'samples': 200000}, dry_run=True) "
                   "先看计划，确认后再 dry_run=False 真发。"))
    else:
        for job, rec in _PENDING.items():
            done = sum(1 for u in rec["units"].values() if u["status"] == "accepted")
            bad = sum(1 for u in rec["units"].values() if u["status"] == "suspect")
            L.append(_("任务 %s：算子 %s，%d 个单元（已完成 %d，存疑 %d，冗余 k=%d）")
                     % (job, rec["op"], len(rec["units"]), done, bad, rec["k"]))
    L.append("")
    L.append(_("累计：接受 %d 个单元，存疑 %d 个") % (len(_ACCEPTED), len(_SUSPECT)))
    if _SUSPECT:
        L.append(_("存疑明细（前 5 条）："))
        for s in _SUSPECT[-5:]:
            L.append(f"  • {s.get('why', '')}")
    L.append("")
    L.append(_("接活：serve_once() 听一个包，是工作单元就本地算并回发结果（受预算约束）。"))
    return True, "\n".join(L)


def loopback_report() -> Tuple[bool, str]:
    """本地回环自检：**不通网**验证「编码 → 解码 → 计算 → 校验 → 记账」整条链。

    在没验证过的链路上派活，等于把问题放大 N 倍——所以先跑这个。
    """
    L = [_("跨机派活链路自检（本地回环，不通网）"), ""]
    job = uuid.uuid4().hex[:12]
    op, params = "mc_pi", {"samples": 20_000, "seed": 11}
    wu = distcompute.wu_split(op, params, n=1)[0]
    text = encode_wu(job, op, wu["index"], wu["params"], 2.0)
    L.append(_("① 编码：%s…") % text[:64])
    d = decode_wu(text)
    L.append(_("② 解码：op=%s，单元号 %s") % (d["op"], d["i"]) if d else _("② 解码失败"))
    if not d:
        return False, "\n".join(L)
    r = distcompute.wu_run_local(d["op"], d["p"], budget_s=2.0)
    L.append(_("③ 本地计算：耗时 %.3f 秒，自检校验 %s")
             % (r["elapsed_s"], _("通过") if r["verify"] else _("不通过")))
    reply = encode_res(job, d["i"], r["result"], r["elapsed_s"] * 1000)
    back = decode_res(reply)
    ok, why = distcompute.wu_verify(op, wu["params"], (back or {}).get("r") or {})
    L.append(_("④ 结果回传并复算校验：%s") % (_("一致，接受") if ok else _("不一致，存疑")))
    bad = encode_res(job, d["i"], {"inside": 1, "samples": 1, "pi": 9.9}, 1.0)
    ok2, _why2 = distcompute.wu_verify(op, wu["params"], decode_res(bad)["r"])
    L.append(_("⑤ 伪造结果能否混过校验：%s")
             % (_("能（这是漏洞！）") if ok2 else _("不能，被打回")))
    junk = decode_wu("SW-WU1:{not json")
    L.append(_("⑥ 坏包处理：%s") % (_("忽略，不抛异常") if junk is None else _("异常")))
    evil = decode_wu(encode_wu(job, "rm -rf /", 0, {}))
    L.append(_("⑦ 白名单外的算子：%s")
             % (_("被拒（通道里传的是参数不是代码）") if evil is None else _("被接受（漏洞！）")))
    return True, "\n".join(L)
