"""前后对比报告生成器（支撑 --report）。

把一次 scan（分析模式）/ clean（真正执行）的结果渲染成 Markdown 或 JSON，
呈现处理前/后的磁盘占用、每项任务的预计可回收与执行结果，让「默认只分析不乱删」
的理念对用户在结果层面也一目了然。

纯标准库实现；跨平台（磁盘字段来自 runner.measure_disk 的归一化结果）。
"""

from __future__ import annotations

import datetime
import json
import os


def generate(platform: str, version: str, mode: str, tasks, results: list,
             before: dict | None, after: dict | None) -> dict:
    """汇总一次扫描/清理的结果，供渲染。

    - mode   : "scan"（分析，未修改系统）或 "clean"（已执行）
    - before : 执行前主盘用量 {total,used,free} 或 None
    - after  : 执行后主盘用量，仅 clean --apply 有；否则 None
    - results: analyze 收集的每项结构化结果列表
    """
    reclaimed = None
    if before and after:
        reclaimed = max(0, after["free"] - before["free"])
    return {
        "tool": "sysweeper",
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform,
        "version": version,
        "mode": mode,
        "before": before,
        "after": after,
        "reclaimed_bytes": reclaimed,
        "task_count": len(results),
        "executed_count": sum(1 for r in results if r.get("executed")),
        "skipped_count": sum(1 for r in results if r.get("skipped")),
        "failed_count": sum(1 for r in results if r.get("executed") and r.get("ok") is False),
        "tasks": results,
    }


def _h(n) -> str:
    from .runner import human
    return human(n) if isinstance(n, int) else "—"


def render_markdown(rep: dict) -> str:
    L: list[str] = []
    L.append(f"# 系统优化 / 清理报告 — {rep['platform']} {rep['version'] or ''}")
    L.append("")
    L.append(f"- 生成时间：{rep['generated_at']}")
    mode_desc = "分析模式（未修改系统）" if rep["mode"] == "scan" else "已执行清理/优化"
    L.append(f"- 模式：{rep['mode']}（{mode_desc}）")
    L.append(f"- 任务总数：{rep['task_count']}（执行 {rep['executed_count']} / "
             f"跳过 {rep['skipped_count']} / 失败 {rep['failed_count']}）")
    L.append("")

    if rep["before"]:
        b = rep["before"]
        L.append("## 处理前磁盘")
        L.append(f"- 总容量：{_h(b['total'])}　已用：{_h(b['used'])}　可用：{_h(b['free'])}")
    if rep["after"]:
        a = rep["after"]
        L.append("## 处理后磁盘")
        L.append(f"- 总容量：{_h(a['total'])}　已用：{_h(a['used'])}　可用：{_h(a['free'])}")
    if rep["reclaimed_bytes"] is not None:
        L.append(f"- **实际释放空间：{_h(rep['reclaimed_bytes'])}**")
    L.append("")

    L.append("## 可视化对比")
    L.append("")
    L.append(render_bars(rep))
    L.append("")

    L.append("## 任务明细")
    L.append("")
    L.append("| 任务 | 分类 | 风险 | 预计可回收 | 状态 | 结果 |")
    L.append("|------|------|------|-----------|------|------|")
    for r in rep["tasks"]:
        est = _h(r.get("estimate")) if r.get("estimate") else "—"
        if r.get("executed"):
            status = "已执行"
            ok = "成功" if r.get("ok") else "失败"
        elif r.get("skipped"):
            status = "跳过"
            ok = r["skipped"]
        else:
            status = "分析"
            ok = "未执行"
        title = r["title"].replace("|", "/")
        L.append(f"| {title} | {r['category']} | {r['risk']} | {est} | {status} | {ok} |")
    L.append("")
    L.append("---")
    L.append("本报告由 sysweeper 生成；默认只分析不乱删，清理需 `--apply` 才会真正执行，"
             "中/高风险与默认关闭的开关还需 `--yes` 确认。")
    return "\n".join(L)


def chart_data(rep: dict) -> dict:
    """从报告 dict 抽取可绘制的序列（纯数据，CLI/GUI 共用）。

    返回 {"disk": {"before": {...}, "after": {...}|None}, "tasks": [...]}
    - disk  : 处理前/后主盘用量（仅 when total 可读）
    - tasks : 各「预计可回收 > 0」的任务（title/estimate/risk），用于条形图
    """
    data: dict = {"disk": None, "tasks": []}
    before = rep.get("before")
    after = rep.get("after")
    if before and before.get("total"):
        series = {"before": before}
        if after and after.get("total"):
            series["after"] = after
        data["disk"] = series
    for t in rep.get("tasks", []):
        est = t.get("estimate") or 0
        if est > 0:
            data["tasks"].append(
                {"title": t.get("title", ""), "estimate": est, "risk": t.get("risk", "")})
    return data


def render_bars(rep: dict, width: int = 32) -> str:
    """把报告渲染成纯文本 ASCII 条形图（终端 / Markdown 都能显示，零依赖）。

    包含两段：磁盘占用「处理前 → 处理后」对比；各任务「预计可回收」对比。
    """
    L: list[str] = []
    d = chart_data(rep)
    if d["disk"]:
        b = d["disk"]["before"]
        total = b.get("total") or 1

        def bar(used, tot) -> str:
            frac = max(0.0, min(1.0, (used / tot) if tot else 0.0))
            filled = int(round(frac * width))
            return "█" * filled + "·" * (width - filled)

        L.append("## 磁盘占用对比（处理前 → 处理后）")
        L.append(f"- 处理前：[{bar(b['used'], total)}] {_h(b['used'])} / {_h(total)}")
        if "after" in d["disk"]:
            a = d["disk"]["after"]
            L.append(f"- 处理后：[{bar(a['used'], total)}] {_h(a['used'])} / {_h(total)}")
        if rep.get("reclaimed_bytes"):
            L.append(f"- **实际释放空间：{_h(rep['reclaimed_bytes'])}**")
    if d["tasks"]:
        L.append("")
        L.append("## 各任务预计可回收空间")
        mx = max(x["estimate"] for x in d["tasks"]) or 1
        for x in d["tasks"]:
            filled = int(round(x["estimate"] / mx * width))
            bar = "█" * filled + "·" * (width - filled)
            title = x["title"]
            if len(title) > 20:
                title = title[:19] + "…"
            L.append(f"- {title:<20} [{bar}] {_h(x['estimate'])}")
    return "\n".join(L) if L else "（无可绘制数据：未执行或无可估算任务）"


def write_report(path: str, rep: dict) -> str:
    """把报告写到 path。以 .json 结尾写 JSON，否则写 Markdown。返回实际路径。"""
    abspath = os.path.abspath(path)
    os.makedirs(os.path.dirname(abspath) or ".", exist_ok=True)
    if path.endswith(".json"):
        with open(abspath, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
    else:
        with open(abspath, "w", encoding="utf-8") as f:
            f.write(render_markdown(rep))
    return abspath
