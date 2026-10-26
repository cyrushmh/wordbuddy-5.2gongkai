"""概念系统中心（v0.6.62）：跨概念系统的统一注册表。

仓库内所有「概念系统」都遵循同一骨架：

    数据层  data/concepts/<系统>_taxonomy.json   （research/<系统>/build_*.py 构建）
    只读层  concepts/<系统>.py                    （本包的成员模块）
    入口    CLI `<系统>` 子命令 + GUI 面板         （与只读层同口径）

本模块提供注册表，使 CLI/GUI 可以一致地枚举、加载与跨系统检索，
而不必知道每个系统的内部轴结构。

当前已登记系统（按登记顺序）：

    plang   编程语言概念系统（执行模型→架构→能力域→底层标准，v0.6.61 全量字段补全）
    netsys  网络与组网概念系统（层次→形态→性质→标准，v0.6.57+ 深化补全 +5 模块）
    daoxue  道枢治理层概念系统（四层经典→治理原则→桥接，v0.6.58）
    quantum 量子理念概念系统（八域：态/线路/算法/硬件/纠错/网络/工具链/经典模拟与语义，v0.6.65）
    comp    编译与工具链概念系统（流水线→工具链→构建→产物→语言编译需要，v0.6.59）
    apilab  接口 API 概念系统（风格→规约→传输→认证→仓库接口面，v0.6.59）
    zhuangzi 南华用户端概念系统（核心理念三篇→内篇辅篇→外杂选篇→人体工程学原则，v0.6.60）
    baigong 百工概念系统（墨子/公输般/公孙策/鲁班→三教九流→匠作原则→工程场景，v0.6.61）
    datong  大同概念系统（文明一体·唯道独尊；正道六象固/液/气/电/磁/波，v0.6.62）
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List

from ._common import load_taxonomy

#: 系统名 → 数据文件名（登记表；新系统在此追加一行即完成注册）
REGISTRY: Dict[str, str] = {
    "plang": "plang_taxonomy.json",
    "netsys": "netsys_taxonomy.json",
    "daoxue": "daoxue_taxonomy.json",
    "quantum": "quantum_taxonomy.json",
    "comp": "comp_taxonomy.json",
    "apilab": "apilab_taxonomy.json",
    "zhuangzi": "zhuangzi_taxonomy.json",
    "baigong": "baigong_taxonomy.json",
    "datong": "datong_taxonomy.json",
    "protec": "protec_taxonomy.json",
    "sciences": "sciences_taxonomy.json",
}

#: 一句话定位（GUI 中心窗口与 CLI `concepts overview` 展示）
TAGLINES: Dict[str, str] = {
    "plang": "编程语言概念系统：执行模型→硬件架构→能力域→底层标准，161 条语言",
    "netsys": "网络与组网概念系统：层次→形态→性质→标准→道性/神性/人性三层，64 个模块（含架构/硬件/盖亚意识/集智体/系统互联协调基底 sysmesh·sysfed/Linux 内核源码实证 L4S·PTP·Wi-Fi HE-EHT），协议无关、覆盖全 9 概念系统组网协调",
    "daoxue": "道枢治理层概念系统：道德经 81 章为中心，早晚坛前后置，心经/论语二级",
    "quantum": "量子理念概念系统：态→线路→算法→硬件→纠错→网络→工具链→经典模拟与语义→量子架构内核九域，82 个概念（含多位元 qudit/同位能级散逸/log 值交换/多 qudit 寄存器）",
    "comp": "编译与工具链概念系统：流水线→工具链→构建→产物→语言编译需要，15 种语言实测",
    "apilab": "接口 API 概念系统：风格→规约→传输→认证→仓库接口面（128 CLI / 29 ACTIONS 实测）",
    "zhuangzi": "南华用户端概念系统：逍遥游/应帝王/大宗师三核心理念 → 八条人体工程学原则",
    "baigong": "百工概念系统：墨子·公输般·公孙策·鲁班 → 三教九流 → 七条匠作原则（无解/暂不允许/具体结构三场景）",
    "datong": "大同概念系统：人类一体·唯道独尊 → 正道六象（天罡元阳气电波/地煞元阴固液磁）→ 九条人间落法",
    "protec": "protec 产品保护概念系统：材料耐久/电气安全/环境标准/应急保护四域 → 七条基本保护原则（冗余/降额/隔离/监控/接地/防护/可维护），28 个概念",
    "sciences": "sciences 自然科学概念系统：材料/热/气候/环境/物理/化学/生物七门学科 + 科学方法，32 个概念；protec 工程保护的科学底座",
}

#: 概念系统整体指导（元理念）：因果记录·全息·感应。
#: 详细条目（8 源）落在 daoxue 概念系统的 `zhengti_zhida` 段
#: （数据层 daoxue_taxonomy.json 的顶层键），不在此重复承载内容数据。
OVERALL_GUIDANCE: Dict[str, Any] = {
    "framing": "因果记录·全息·感应",
    "sources": [
        "阿卡西记录", "宇宙全息论", "三世石", "望乡台",
        "三世因果经", "文昌帝君阴鸷文", "黄帝阴符经", "太上感应篇",
    ],
}


def systems() -> List[str]:
    """已登记概念系统名（登记顺序）。"""
    return list(REGISTRY)


def load(name: str) -> Dict[str, Any]:
    """按系统名加载数据层（未经加工的原始 taxonomy）。"""
    try:
        filename = REGISTRY[name]
    except KeyError:
        raise KeyError(f"未登记的概念系统: {name!r}（已登记: {systems()}") from None
    return load_taxonomy(filename)


def module(name: str):
    """按系统名导入只读层模块（``concepts.<name>``）。"""
    if name not in REGISTRY:
        raise KeyError(f"未登记的概念系统: {name!r}（已登记: {systems()}")
    return importlib.import_module(f".{name}", __name__)


def overview() -> List[Dict[str, Any]]:
    """各系统摘要（meta + stats），供中心窗口一次性展示。"""
    out: List[Dict[str, Any]] = []
    for name in systems():
        mod = module(name)
        stats = {}
        fn = getattr(mod, "stats", None)
        if callable(fn):
            try:
                stats = fn()
            except Exception:  # pragma: no cover - 防御：单系统失败不拖垮中心
                stats = {}
        out.append({
            "system": name,
            "tagline": TAGLINES.get(name, ""),
            "version": mod.info().get("version", ""),
            "title": mod.info().get("title", ""),
            "stats": stats,
        })
    return out


def search_all(term: str) -> List[Dict[str, Any]]:
    """跨系统检索（对暴露了 ``search`` 的系统逐一代问）。

    每条命中带 ``system`` 字段标明来源；某系统无 ``search`` 实现时跳过，
    不臆造命中。
    """
    term = (term or "").strip()
    if not term:
        return []
    hits: List[Dict[str, Any]] = []
    for name in systems():
        fn = getattr(module(name), "search", None)
        if not callable(fn):
            continue
        for h in fn(term):
            hits.append({"system": name, **h})
    return hits


def topo() -> Dict[str, Any]:
    """跨系统桥接拓扑（数据驱动，从各 taxonomy 的 bridges 实测统计）。

    桥接是有向边：每条 bridge 的 ``from`` 属本系统（``<系统>:<id>``），
    ``system`` 字段标出目标系统；据此分别累加出边 / 入边与 9×9 边矩阵。
    数字全部来自磁盘数据层，不硬编码、不臆造。

    返回：``systems``（登记顺序）、``out``/``in``（每系统出/入边数）、
    ``edge``（``(src, tgt) -> 边数`` 字典）、``external``（指向九系统之外
    的目标 system 及边数，如 llvm/langref）。
    """
    syss = systems()
    out: Dict[str, int] = {s: 0 for s in syss}
    inn: Dict[str, int] = {s: 0 for s in syss}
    edge: Dict[tuple, int] = {(s, t): 0 for s in syss for t in syss}
    external: Dict[str, int] = {}
    for s in syss:
        for b in load(s).get("bridges", []):
            t = b.get("system")
            if t is None:
                continue
            if t in out:
                out[s] += 1
                inn[t] += 1
                edge[(s, t)] += 1
            else:
                external[t] = external.get(t, 0) + 1
    return {
        "systems": syss,
        "out": out,
        "in": inn,
        "edge": edge,
        "external": external,
    }
