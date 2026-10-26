"""基线快照与差异对比（纯只读，跨子系统复用现有探测）。

把各子系统的「只读探测」聚合成一份可序列化的 JSON 快照，并对两份快照做
跨时间对比，让「前后对比」变成可追溯、可归档的产物。

设计原则（与全盘一致）：
- 全程只读：只读取文件（/proc/meminfo）+ 调用本就存在的 *_report 只读探测，
  绝不写系统、绝不跑任何清理/调优命令。
- 复用而非另起：探测结果直接来自各原生模块的 PROBES 元组（与 CLI storage/
  container/pkgmgr/network 命令同一来源），不重复实现探测逻辑。
- 结构化优先：磁盘/内存给出可比对数值，探测给出 ok/msg，diff 时既能看数值
  也能看「某探测从可用变不可用」。
"""

from __future__ import annotations

import importlib
import json
import os
import platform as pplatform
import re
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import common


def tool_version() -> str:
    """取工具版本：优先 pyproject.toml，回退到包 __version__，再回退 unknown。"""
    try:
        p = Path(__file__).resolve().parents[4] / "pyproject.toml"
        txt = p.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', txt, re.M)
        if m:
            return m.group(1)
    except Exception:  # noqa: BLE001
        pass
    try:
        from .. import __version__
        return __version__
    except Exception:  # noqa: BLE001
        return "unknown"


# 带 PROBES 的原生子系统（与 CLI storage/container/pkgmgr/network 等命令同源）。
# 顺序即展示顺序；缺模块时自动跳过。
_PROBE_MODULES = ("container", "harmony", "miniapp", "network",
                  "pkgmgr", "storage", "syssoftware")


def _probe_modules() -> List[Tuple[str, object]]:
    """直接导入各含 PROBES 的原生子模块（避免与 native 包聚合器形成循环导入）。"""
    out = []
    for name in _PROBE_MODULES:
        try:
            mod = importlib.import_module(f".{name}", __package__)
        except Exception:  # noqa: BLE001
            mod = None
        if mod and hasattr(mod, "PROBES"):
            out.append((name, mod))
    return out


def _run_probe(mod, fn_name: str) -> Tuple[bool, str]:
    """以无参方式调用某只读探测（与 runner._run_native 同口径）。"""
    fn = getattr(mod, fn_name, None)
    if fn is None:
        return False, f"(探测函数缺失: {fn_name})"
    try:
        res = fn()
    except Exception as e:  # noqa: BLE001
        return False, f"(调用失败: {e})"
    if isinstance(res, tuple) and len(res) == 2:
        return bool(res[0]), str(res[1])
    return bool(res), f"{fn_name} -> {res}"


def _disk_metrics() -> Dict[str, dict]:
    """主盘（$HOME 与 / 或系统盘）用量，返回 {path: {total,used,free}}（字节）。"""
    paths = [os.path.expanduser("~")]
    if pplatform.system().lower() == "windows":
        from . import windows as nw
        d = nw.disk_usage()
        if d and d.get("total"):
            return {"system": {"total": d["total"],
                               "used": d["total"] - (d.get("free") or 0),
                               "free": d.get("free") or 0}}
    else:
        paths.append("/")
    out: Dict[str, dict] = {}
    for p in paths:
        u = common.disk_usage(p)
        if u:
            out[p] = u
    return out


def _memory_metrics() -> Dict[str, object]:
    """Linux 读 /proc/meminfo（只读），返回 {key: bytes}。其它平台标记不支持。"""
    if pplatform.system().lower() != "linux":
        return {"supported": False}
    mp = "/proc/meminfo"
    if not os.path.isfile(mp):
        return {"supported": False}
    try:
        out: Dict[str, int] = {}
        with open(mp, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"^(\w+):\s+(\d+)\s*kB", line)
                if m:
                    out[m.group(1)] = int(m.group(2)) * 1024
        return out
    except Exception:  # noqa: BLE001
        return {"supported": False}


def capture_snapshot(include_probes: bool = True) -> dict:
    """采集一份基线快照（纯只读）。返回可 JSON 序列化的 dict。"""
    from ..detect import detect  # 惰性导入：避免与 native 包初始化形成循环
    info = detect()
    snap: dict = {
        "meta": {
            "tool": "sysweeper",
            "tool_version": tool_version(),
            "schema": 1,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "hostname": socket.gethostname(),
            "platform": info.get("platform", "unknown"),
            "distro": info.get("distro", ""),
            "python": pplatform.python_version(),
        },
        "metrics": {
            "disk": _disk_metrics(),
            "memory": _memory_metrics(),
        },
        "probes": {},
    }
    if include_probes:
        for name, mod in _probe_modules():
            rows = []
            for fn_name, label in mod.PROBES:
                ok, msg = _run_probe(mod, fn_name)
                rows.append({"label": label, "ok": ok, "msg": msg})
            snap["probes"][name] = rows
    return snap


def save_snapshot(path: str, snap: dict, indent: int = 2) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=indent)


def load_snapshot(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _delta_bytes(before: Optional[dict], after: Optional[dict]) -> dict:
    """对 {total,used,free} 计算 used/free 的增减（字节）。"""
    return {
        "before": before,
        "after": after,
        "used_delta": (after or {}).get("used", 0) - (before or {}).get("used", 0)
        if before is not None and after is not None else None,
        "free_delta": (after or {}).get("free", 0) - (before or {}).get("free", 0)
        if before is not None and after is not None else None,
    }


def _delta_int(before: Optional[int], after: Optional[int]) -> dict:
    return {
        "before": before,
        "after": after,
        "delta": (after - before) if (before is not None and after is not None) else None,
    }


def diff_snapshots(a: dict, b: dict) -> dict:
    """对比两份快照，返回结构化差异。

    - metrics.disk : 每路径 used/free 增减
    - metrics.memory: 每指标字节增减
    - probes        : 按 label 对比，状态为 unchanged/changed/added/removed
    """
    out: dict = {"metrics": {"disk": {}, "memory": {}}, "probes": {}}

    da = (a.get("metrics") or {}).get("disk") or {}
    db = (b.get("metrics") or {}).get("disk") or {}
    for k in sorted(set(da) | set(db)):
        out["metrics"]["disk"][k] = _delta_bytes(da.get(k), db.get(k))

    ma = (a.get("metrics") or {}).get("memory") or {}
    mb = (b.get("metrics") or {}).get("memory") or {}
    for k in sorted(set(ma) | set(mb)):
        if k == "supported":
            continue
        out["metrics"]["memory"][k] = _delta_int(ma.get(k), mb.get(k))

    pa = a.get("probes") or {}
    pb = b.get("probes") or {}
    for sub in sorted(set(pa) | set(pb)):
        rows_a = {r["label"]: r for r in (pa.get(sub) or [])}
        rows_b = {r["label"]: r for r in (pb.get(sub) or [])}
        changes = []
        for label in sorted(set(rows_a) | set(rows_b)):
            ra, rb = rows_a.get(label), rows_b.get(label)
            if ra and rb:
                if ra["ok"] != rb["ok"] or ra["msg"] != rb["msg"]:
                    changes.append({
                        "label": label, "status": "changed",
                        "before_ok": ra["ok"], "after_ok": rb["ok"],
                        "before_msg": ra["msg"], "after_msg": rb["msg"],
                    })
                else:
                    changes.append({"label": label, "status": "unchanged"})
            elif rb and not ra:
                changes.append({"label": label, "status": "added",
                                "after_ok": rb["ok"], "after_msg": rb["msg"]})
            else:
                changes.append({"label": label, "status": "removed",
                                "before_ok": ra["ok"], "before_msg": ra["msg"]})
        out["probes"][sub] = changes
    return out


def summarize(snap: dict) -> List[str]:
    """把一份快照压成几行可读摘要（capture 后打印 / GUI 展示）。"""
    lines = []
    meta = snap.get("meta", {})
    lines.append(f"工具 sysweeper {meta.get('tool_version','?')}  ·  "
                 f"平台 {meta.get('platform','?')} {meta.get('distro','')}")
    lines.append(f"采集时间 {meta.get('captured_at','?')}  ·  主机 {meta.get('hostname','?')}")
    disk = (snap.get("metrics") or {}).get("disk") or {}
    for p, u in disk.items():
        lines.append(f"  磁盘 {p}: 已用 {common.human(u.get('used',0))} / "
                     f"共 {common.human(u.get('total',0))}  "
                     f"(空闲 {common.human(u.get('free',0))})")
    mem = (snap.get("metrics") or {}).get("memory") or {}
    if mem.get("supported") and "MemAvailable" in mem:
        lines.append(f"  内存: 可用 {common.human(mem.get('MemAvailable',0))} / "
                     f"共 {common.human(mem.get('MemTotal',0))}")
    probes = snap.get("probes") or {}
    for sub, rows in probes.items():
        avail = sum(1 for r in rows if r["ok"])
        lines.append(f"  探测[{sub}]: {avail}/{len(rows)} 可用")
    return lines


def _fmt_delta_bytes(delta: Optional[int]) -> str:
    if delta is None:
        return "—"
    sign = "+" if delta >= 0 else "-"
    return f"{sign}{common.human(abs(delta))}"


def format_diff(d: dict) -> str:
    """把结构化 diff 渲染成可读文本（CLI / GUI 展示）。"""
    parts: List[str] = []
    parts.append("基线快照对比（A → B）")
    parts.append("=" * 56)

    disk = (d.get("metrics") or {}).get("disk") or {}
    if disk:
        parts.append("指标 · 磁盘")
        for k, v in disk.items():
            if v["before"] is None and v["after"] is None:
                parts.append(f"  {k:<14}: 缺失/不可读")
                continue
            if v["before"] is not None and v["after"] is not None:
                parts.append(
                    f"  {k:<14}: 已用 {common.human(v['before']['used'])} → "
                    f"{common.human(v['after']['used'])} "
                    f"({_fmt_delta_bytes(v['used_delta'])})")
            else:
                parts.append(f"  {k:<14}: 仅单侧有数据（新增或移除快照维度）")

    mem = (d.get("metrics") or {}).get("memory") or {}
    if mem:
        parts.append("指标 · 内存 (Linux)")
        headline = ("MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree")
        shown = set()
        for k in headline:
            v = mem.get(k)
            if not v:
                continue
            shown.add(k)
            if v["before"] is not None and v["after"] is not None:
                parts.append(f"  {k:<14}: {common.human(v['before'])} → "
                             f"{common.human(v['after'])} ({_fmt_delta_bytes(v['delta'])})")
            else:
                parts.append(f"  {k:<14}: 仅单侧有数据")
        changed_others = 0
        for k, v in mem.items():
            if k in shown or k == "supported":
                continue
            if v.get("delta"):
                changed_others += 1
                parts.append(f"  {k:<14}: {common.human(v['before'])} → "
                             f"{common.human(v['after'])} ({_fmt_delta_bytes(v['delta'])})")
        if changed_others == 0:
            parts.append("  （其余内存指标无变化）")

    probes = d.get("probes") or {}
    for sub, changes in probes.items():
        if not changes:
            continue
        parts.append(f"探测 · {sub}")
        for c in changes:
            if c["status"] == "unchanged":
                parts.append(f"  · {c['label']}: 无变化")
            elif c["status"] == "changed":
                mark = f"({'✓' if c['before_ok'] else '✗'} → "
                mark += f"{'✓' if c['after_ok'] else '✗'})"
                parts.append(f"  · {c['label']} {mark}: 变更")
                parts.append(f"      A: {c['before_msg']}")
                parts.append(f"      B: {c['after_msg']}")
            elif c["status"] == "added":
                parts.append(f"  · {c['label']} (新增): {c.get('after_msg','')}")
            else:
                parts.append(f"  · {c['label']} (移除): {c.get('before_msg','')}")
    return "\n".join(parts)


def record_scan(history, snap: dict, maxlen: int = 10) -> Tuple[Optional[dict], list]:
    """把一次扫描快照并入会话历史，返回 (与上一快照的 diff, 新历史)。

    纯函数、零 GUI 依赖，便于单元测试与 GUI 复用（把「快照对比」下沉为扫描
    流程的内建能力，而非只在独立窗口里手动操作）：
    - history 为 None 或空列表时，只记录、不对比（diff=None）；
    - history 非空时，与上一条（同主机同平台）做结构化 diff；
    - 历史超过 maxlen 时只保留最近 maxlen 条，避免无限增长。
    """
    if not isinstance(history, list):
        history = []
    diff = diff_snapshots(history[-1], snap) if history else None
    history = history + [snap]
    if len(history) > maxlen:
        history = history[-maxlen:]
    return diff, history


def snapshot_report() -> tuple:
    """零参只读快照摘要（供统一子系统清单嵌入整体）。

    只采 meta + 磁盘/内存指标，**不跑全量探针**——全量探针由各子系统自己的
    报告负责，这里避免重复与耗时。返回 (ok, msg)。

    全程只读：读 /proc/meminfo 与挂载点用量，不写任何文件（落盘只在 GUI/CLI
    显式 save 时发生）。
    """
    try:
        snap = capture_snapshot(include_probes=False)
    except Exception as e:  # noqa: BLE001 —— 只读采集异常只标异常，不外抛
        return False, f"快照采集失败：{e}"

    lines = summarize(snap)
    head = "系统快照（基线指标，只读）"
    if not lines:
        return False, "快照为空（未采到任何指标）"
    return True, head + "\n  " + "\n  ".join(lines)
