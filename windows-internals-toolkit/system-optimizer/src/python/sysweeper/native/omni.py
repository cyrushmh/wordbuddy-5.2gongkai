"""全能全知自检层（v0.6.35）：让工具能**自述自己的边界**。

「全能全知」不是宣称什么都知道——那叫吹牛。真正的全知是三层：

| 层 | 问题 | 本模块怎么答 |
|---|---|---|
| **我知道什么** | 已登记的能力，接线接全了没有 | `wiring()`：每项在 CLI/GUI/任务/知识库四处的接线状态 |
| **我知道我不知道什么** | 有探针，但**这台机器**探不到 | `known_unknowns()`（`--deep` 实跑）：不适用 / 工具缺失 / 需权限 |
| **我不知道我不知道什么** | 这个能力域**压根没有探针** | `unknown_domains()`：显式列出本工具不覆盖的域 |

第三层最容易被人忽略，也最要命：一个只会报「已处理 61 项」的工具，永远不会告诉你
「生物识别、GNSS 定位、摄像头内容、文件正文这些维度我一行都没探」。本模块把它写成
**显式清单**，把「沉默的盲区」变成「声明过的边界」。

顺带暴露**接线欠账**：登记进统一清单 ≠ 真的接全了。61 项里四件套齐全的只有 22 项，
其余缺 CLI 入口 / 缺 GUI 面板 / 缺任务 / 缺知识库——这些是「半截能力」，用户点了
总看得见，但总览里看不出来。本模块让它自己说出来。

红线：全程**只读、纯计算**（接线盘点只读本仓库源码文本，不 import 执行）；
`--deep` 实跑时只调各子系统既有的零参只读报告。
"""

from __future__ import annotations

import importlib
import pathlib
from typing import Dict, List, Tuple

from . import subsystems

__all__ = [
    "WIRING_KINDS", "DOMAIN_PREFIXES", "UNKNOWN_DOMAINS", "BY_DESIGN_KEYS",
    "wiring", "domains", "blind_spots", "known_unknowns", "unknown_domains",
    "remediation_plan", "real_gaps", "remediation_report", "gen_stub",
    "coverage_report", "omni_report", "capabilities_report",
]

# 接线的四处落点（顺序即报告展示顺序）
WIRING_KINDS: Tuple[str, ...] = ("cli", "gui", "task", "data")

# ── 入口别名：登记项的 key 与它实际走的命令/面板名不一致时的对照 ──────────
# 不写这张表，共用入口就会被误报成欠账：比如 netauth / reshare 都走 `netlink`
# 命令、meshchat / distcompute / distjob 都走 `mesh` 命令、importio 走 `import`。
# 「全知」不能自己报错，所以这张表本身就是边界知识的一部分。
ENTRY_ALIASES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "importio": {"cli": ("import",), "gui": ("import",)},
    "netauth": {"cli": ("netlink",), "gui": ("netlink",)},
    "reshare": {"cli": ("netlink",), "gui": ("netlink",)},
    "meshchat": {"cli": ("mesh",), "gui": ("mesh_compute",)},
    "distcompute": {"cli": ("mesh",), "gui": ("mesh_compute",)},
    "distjob": {"cli": ("mesh",), "gui": ("mesh_compute",)},
    "harmony": {"cli": ("kaihong",), "gui": ("kaihong",)},
    "harmony_hdc": {"cli": ("kaihong",), "gui": ("kaihong",)},
    "harmony_device": {"cli": ("kaihong",), "gui": ("kaihong",)},
}

# ── data 文件别名：native 模块实际加载的**语义命名**知识库（不按 key 前缀起名）──
# 接线盘点若只用 `<key>*.json` 前缀猜，会漏掉这些（`netlink`→link_protocols.json、
# `thirdparty`→net_interop_refs.json），反把真有知识的项报成「缺 data」。
# harmony 三子项共用 harmony_docs.json，显式别名让它正确判成「有 data」。
DATA_FILE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "netlink": ("link_protocols.json",),
    "thirdparty": ("net_interop_refs.json",),
    "kaihong": ("harmony_docs.json",),
    "harmony_hdc": ("harmony_docs.json",),
    "harmony_device": ("harmony_docs.json",),
}

# 能力域归组：layer 里含哪个前缀就归到哪个域（从上往下先匹配先归）
DOMAIN_PREFIXES: List[Tuple[str, str]] = [
    ("网络", "网络"), ("硬件", "硬件"), ("内核", "内核"), ("存储", "存储"),
    ("容器", "系统"), ("系统", "系统"), ("应用", "应用"), ("兼容", "兼容"),
    ("嵌入式", "兼容"), ("安全", "安全"), ("共享", "共享计算"),
    ("设备", "设备保护"), ("快照", "元能力"), ("配置", "元能力"),
    ("导入", "元能力"), ("资讯", "元能力"),
]
_DEFAULT_DOMAIN = "其他"

# ── 第三层：本工具**压根没有探针**的能力域（未知未知 / 刻意不做）──
# 这不是 TODO 清单，是**边界声明**：写在这里的意思是「本工具不打算覆盖，且理由充分」。
UNKNOWN_DOMAINS: List[dict] = [
    {"domain": "生物识别（指纹 / 人脸 / 虹膜）", "state": "刻意不采集",
     "reason": "生物特征是不可更换的敏感个人信息，一旦泄露无法重置",
     "remedy": "由系统自带设置与厂商工具管理；本工具不提供任何采集入口"},
    {"domain": "GNSS 卫星定位原始坐标", "state": "仅粗粒度",
     "reason": "精确定位属行踪轨迹，属敏感个人信息",
     "remedy": "应急场景只用「网络 + 基站」粗粒度基线，不读 GPS 芯片原始坐标"},
    {"domain": "摄像头 / 麦克风采集内容", "state": "刻意不采集",
     "reason": "音视频内容直接涉及通信秘密与隐私",
     "remedy": "只探设备是否存在与驱动状态，绝不采集任何一帧画面、一段声音"},
    {"domain": "文件与文档正文", "state": "刻意不读",
     "reason": "用户文件内容不属于系统诊断范畴",
     "remedy": "清理类任务只按路径/体积/时间归类，绝不打开读取正文"},
    {"domain": "浏览器历史 / 网页内容", "state": "刻意不读",
     "reason": "浏览记录等同行为画像",
     "remedy": "只探浏览器与引擎版本（兼容性用），不碰历史与缓存内容"},
    {"domain": "通讯录 / 短信 / 邮件内容", "state": "刻意不读",
     "reason": "通信内容与社交关系属高度敏感个人信息",
     "remedy": "本工具无此类探针；如需清理请用户自己在对应 App 操作"},
    {"domain": "键盘按键与输入内容", "state": "刻意不记录",
     "reason": "按键记录等同键盘记录器，风险极高",
     "remedy": "只探输入设备是否存在与驱动版本，绝不挂钩输入流"},
    {"domain": "蜂窝基带 / SIM / eSIM", "state": "仅能力面",
     "reason": "基带固件与 SIM 数据涉及运营商与身份信息",
     "remedy": "只在「架构/指令集」与「应急定位」里间接涉及，不读 SIM 数据"},
    {"domain": "打印机 / 扫描仪等外设", "state": "无探针",
     "reason": "外设型号与耗材不属于系统优化主线",
     "remedy": "由系统设置与厂商工具管理"},
    {"domain": "云账号与计费 / 配额", "state": "刻意不接",
     "reason": "接入云账号等于要凭证，与「最小权限」红线冲突",
     "remedy": "本工具不保存任何账号凭证；云侧开销请到对应控制台查看"},
    {"domain": "固件刷写 / 超频 / 破解", "state": "刻意不做",
     "reason": "不可逆操作，一旦失败设备变砖",
     "remedy": "只给 OEM 官方工具指引，本工具绝不刷写任何固件"},
    {"domain": "医疗与生物传感器读数", "state": "无探针",
     "reason": "健康数据属敏感个人信息，且超出系统优化范畴",
     "remedy": "由健康类 App 与设备厂商管理"},
]


def _pkg_dir() -> pathlib.Path:
    """sysweeper 包目录（接线盘点要读本仓库源码文本，纯读不执行）。"""
    mod = importlib.import_module("sysweeper")
    return pathlib.Path(mod.__file__).parent


def _res_files(pkg: str):
    """取包资源的 Traversable 视图。

    为什么不能只用 pathlib：本工具的分发形态之一是 zipapp（.pyz），
    zipapp 里 `sysweeper.__file__` 指向 **zip 内部路径**，pathlib 的
    read_text/glob/is_file 全部失效——于是 `wiring()` 会把每一项都误报成
    「缺 cli/gui/task/data」（实测：.pyz 内 omni gaps 谎报 69 项真缺口，
    而源码树同一版本实为 0 项）。「全知」层绝不能自己误报，故读包内
    文本/判存在一律走 importlib.resources（zip 与磁盘通吃）。

    Python 3.8 无 `files()` API：返回 None，调用方回退磁盘路径
    （3.8 用户实际都跑源码检出树或 wheel，不跑 pyz，可接受）。
    """
    try:
        from importlib.resources import files
    except ImportError:  # Python 3.8 兜底
        return None
    try:
        return files(pkg)
    except (ModuleNotFoundError, OSError, ValueError):
        return None


def _read(name: str) -> str:
    """读包内文本文件（如 cli.py / gui.py）——zipapp 内也必须读得到。"""
    root = _res_files("sysweeper")
    if root is not None:
        try:
            return root.joinpath(name).read_text(encoding="utf-8")
        except (OSError, FileNotFoundError, ValueError):
            return ""
    try:
        return (_pkg_dir() / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def _has_file(rel: str) -> bool:
    """判包内相对路径文件是否存在（如 tasks/osi.py、data/fonts.json）。"""
    root = _res_files("sysweeper")
    if root is not None:
        try:
            return root.joinpath(rel).is_file()
        except (OSError, FileNotFoundError, ValueError):
            return False
    return (_pkg_dir() / rel).is_file()


def _data_files(key: str) -> List[str]:
    """列 data/ 下以 key 前缀命名的 JSON 名（只回名字，不读内容）。"""
    root = _res_files("sysweeper")
    if root is not None:
        try:
            entries = root.joinpath("data").iterdir()
        except (OSError, FileNotFoundError, ValueError):
            return []
        return sorted(p.name for p in entries
                      if p.name.startswith(key) and p.name.endswith(".json"))
    return sorted(p.name for p in (_pkg_dir() / "data").glob(f"{key}*.json"))


def wiring() -> List[dict]:
    """盘点每项子系统在**四处入口**的接线状态（纯计算，只读源码文本）。

    判定按 `key` → `module` 回退：多个登记项常共用同一个 native 模块与入口
    （如 `firmware` / `modules` 都走 `kmod` 的 CLI 与面板），按 key 判会把共用入口
    误报成欠账，因此先看 key、再看 module。

    包内文本与存在性一律走 `_read`/`_has_file`/`_data_files`（importlib.resources），
    使 zipapp（.pyz）分发形态下的盘点结果与源码树一致——否则 pyz 内会把全部
    82 项都误报成半截能力（v0.6.70 修）。
    """
    cli_src = _read("cli.py")
    gui_src = _read("gui.py")

    def has(kind: str, names: List[str]) -> bool:
        for n in names:
            if kind == "cli" and f"def cmd_{n}" in cli_src:
                return True
            if kind == "gui" and f"def show_{n}" in gui_src:
                return True
            if kind == "task" and _has_file(f"tasks/{n}.py"):
                return True
        return False

    def has_data(key: str) -> bool:
        # 显式别名优先：native 模块实际加载的语义命名 data 文件
        for fn in DATA_FILE_ALIASES.get(key, ()):
            if _has_file(f"data/{fn}"):
                return True
        # 回退：<key>*.json 前缀（绝大多数知识库按 key 前缀命名）
        return bool(_data_files(key))

    rows: List[dict] = []
    for s in subsystems.SUBSYSTEMS:
        alias = ENTRY_ALIASES.get(s.key, {})
        malias = ENTRY_ALIASES.get(s.module, {})
        state = {}
        for k in WIRING_KINDS:
            if k == "data":
                # data 只按本项 key（别名 / 前缀）判，不借 module 名继承，
                # 否则 harmony 三子项会误借 harmony_docs.json 判成「有 data」
                state[k] = has_data(s.key)
            else:
                names = [s.key, s.module] + list(alias.get(k, ())) + list(malias.get(k, ()))
                state[k] = has(k, names)
        rows.append({
            "key": s.key, "label": s.label, "layer": s.layer, "module": s.module,
            "domain": _domain_of(s.layer), "wiring": state,
            "missing": [k for k in WIRING_KINDS if not state[k]],
            "complete": all(state.values()),
        })
    return rows


def _domain_of(layer: str) -> str:
    for prefix, domain in DOMAIN_PREFIXES:
        if prefix in layer:
            return domain
    return _DEFAULT_DOMAIN


def domains() -> Dict[str, List[dict]]:
    """按能力域分组（保持清单登记顺序，便于报告稳定输出）。"""
    out: Dict[str, List[dict]] = {}
    for row in wiring():
        out.setdefault(row["domain"], []).append(row)
    return out


def blind_spots(min_missing: int = 2) -> List[dict]:
    """接线欠账清单：缺 `min_missing` 处以上的登记项（半截能力）。

    补齐建议按缺的具体落点给——缺 `task` 说明进不了「扫描/执行」，
    缺 `data` 说明没有权威文档/知识库出处，二者性质不同。
    """
    remedy = {
        "cli": "补一个 CLI 子命令入口（命令行用户要用）",
        "gui": "补一个 GUI 面板（图形界面用户要用）",
        "task": "补任务定义（否则进不了扫描与执行流程）",
        "data": "补知识库 JSON（否则该维度没有权威出处可引用）",
    }
    out = []
    for row in wiring():
        if len(row["missing"]) >= min_missing:
            out.append({
                "key": row["key"], "label": row["label"], "domain": row["domain"],
                "missing": row["missing"],
                "remedies": [remedy[m] for m in row["missing"]],
            })
    return out


def unknown_domains() -> List[dict]:
    """本工具**压根没有探针**的能力域（第三层：我不知道我不知道什么）。"""
    return list(UNKNOWN_DOMAINS)


# ── 设计如此：这些是元能力/机制类项，四件套里的 task/data 本就不适用 ──
# 不把它们标成「半截能力」，否则「四件套齐全」比例会被元能力拉低、误导读者。
# 它们是工具自身的骨架（清单/联动/自检/设置/导入/快照/派活），不是诊断探针。
BY_DESIGN_KEYS: Tuple[str, ...] = (
    "subsystems", "linkage", "omni", "docs", "settings", "importio", "snapshot", "distjob",
    # 以下为运行时数据/机制类：data 是运行期生成（peer/offer/审计/资讯聚合/插件白名单），
    # 不是包内静态知识库，故「缺 data」属设计如此，不应算半截能力
    "webnews", "plugins", "plugins_allowlist", "distcompute", "reshare", "meshchat",
)
_BY_DESIGN_REASON: Dict[str, str] = {
    "subsystems": "它是统一清单本身，没有独立的任务/知识库",
    "linkage": "它是联动轴体检，不是诊断探针",
    "docs": "它是文档层本身，已是联动网格的文档承载，无需再建 data 知识库",
    "omni": "它是自检层本身",
    "settings": "参数与阈值注册表即其数据来源",
    "importio": "多来源导入是机制，不是诊断维度",
    "snapshot": "快照/对比是基线采集机制",
    "distjob": "跨机派活是调度机制",
    "webnews": "资讯聚合是运行期抓取，本身即知识源，无包内静态知识库",
    "plugins": "插件框架是机制，白名单即其数据，非诊断维度",
    "plugins_allowlist": "插件白名单是代码侧安全配置，非知识库",
    "distcompute": "算力共享是运行期 peer/offer 状态，非包内静态知识库",
    "reshare": "算力/网络共享是运行期配置与审计日志，非包内静态知识库",
    "meshchat": "本地自组网是运行期节点发现，非包内静态知识库",
}


def _is_by_design(key: str) -> bool:
    return key in BY_DESIGN_KEYS


def remediation_plan() -> List[dict]:
    """把每个接线缺口变成**可执行的补齐清单**（v0.6.36 闭环）。

    分两类：
    - by_design：元能力/机制类，task/data 本就不适用（subsystems/linkage/omni/…）。
    - real：诊断类能力真的缺入口，给出具体补哪个文件、加哪个入口。

    让 v0.6.35 的「全知」从「能说出缺什么」前进到「能说出怎么补」。
    """
    action_for = {
        "cli": "cli.py 加 `def cmd_{key}(args)` 并注册 sub parser",
        "gui": "gui.py 加 `def show_{key}(args)` 面板并在底部按钮行登记",
        "task": "tasks/{key}.py 加任务定义并注册到 TASKS",
        "data": "data/{key}.json 加知识库（可 `omni gen-stub {key}` 生成占位）",
    }
    out: List[dict] = []
    for row in wiring():
        if not row["missing"]:
            continue
        if _is_by_design(row["key"]):
            out.append({
                "key": row["key"], "label": row["label"], "domain": row["domain"],
                "missing": row["missing"], "by_design": True,
                "action": "设计如此：" + _BY_DESIGN_REASON.get(
                    row["key"], "元能力/机制类，四件套中 task/data 本就不适用"),
            })
            continue
        acts = [action_for[m].format(key=row["key"]) for m in row["missing"]]
        out.append({
            "key": row["key"], "label": row["label"], "domain": row["domain"],
            "missing": row["missing"], "by_design": False,
            "action": "；".join(acts),
        })
    return out


def real_gaps() -> List[dict]:
    """真缺口（诊断类能力，应补齐），排除设计如此的元能力项。"""
    return [p for p in remediation_plan() if not p["by_design"]]


def remediation_report() -> tuple:
    """补齐清单（纯计算，只读）：真缺口给具体补法，设计如此项单列说明。"""
    plan = remediation_plan()
    real = [p for p in plan if not p["by_design"]]
    bd = [p for p in plan if p["by_design"]]
    out = ["全能全知自检 · 补齐清单（把缺口变成可执行动作）"]
    out.append("─" * 58)
    out.append(f"[真缺口 · {len(real)} 项]  （诊断类能力，应补齐）")
    for p in real:
        out.append(f"  · {p['label']}（{p['domain']}）缺 {'、'.join(p['missing'])}")
        out.append(f"      补法：{p['action']}")
    out.append("─" * 58)
    out.append(f"[设计如此 · {len(bd)} 项]  （元能力/机制，task/data 本不适用）")
    for p in bd:
        out.append(f"  · {p['label']}：{p['action']}")
    return True, "\n".join(out)


def gen_stub(key: str, write: bool = False) -> tuple:
    """为「缺 data 的真缺口」生成**知识库占位 JSON**（纯数据，不碰代码）。

    - 不覆盖：data/{key}.json 已存在则跳过。
    - 默认 dry-run：只回显将写入的内容，不落盘。
    - --write：真正创建占位文件，待人工补全权威来源。

    红线：只读诊断，不自动填充任何正文内容、不引用未核实来源——
    生成的只是带 `_note` 的空壳，references/items 留给你填。
    """
    import json
    from . import subsystems as _sb

    sub = next((s for s in _sb.SUBSYSTEMS if s.key == key), None)
    if sub is None:
        return False, f"未知子系统 key：{key}（用 `python -m sysweeper subsystems` 查看）"
    if _is_by_design(key):
        return False, (f"{sub.label} 是设计如此"
                       f"（{_BY_DESIGN_REASON.get(key, '元能力/机制类')}），无需 data 知识库")
    rows = {r["key"]: r for r in wiring()}
    row = rows.get(key)
    if row is None or "data" not in row["missing"]:
        miss = row["missing"] if row else []
        return False, (f"{sub.label} 未缺 data 入口，无需生成占位"
                       f"（当前缺：{miss or '无'}；或已存在 data/{key}*.json 但未以 {key} 前缀命名）")
    data_dir = _pkg_dir() / "data"
    target = data_dir / f"{key}.json"
    if _has_file(f"data/{key}.json"):
        return False, f"已存在，跳过（不覆盖）：{target.name}"
    if not data_dir.is_dir():
        # zipapp（.pyz）内 data_dir 不是真实目录：写不进去，如实告知
        return False, ("当前运行在 zipapp（.pyz）内，包体只读不可写；"
                       "gen-stub --write 请在源码检出树或已解包安装里运行")
    content = {
        "_note": (f"知识库占位（v0.6.36 gen-stub 生成）：{sub.label}。"
                  f"待你补全权威参考来源与条目。本工具只读引用，不自动填充正文。"),
        "key": key,
        "label": sub.label,
        "domain": _domain_of(sub.layer),
        "references": [],
        "items": [],
    }
    text = json.dumps(content, ensure_ascii=False, indent=2)
    if not write:
        return True, (f"[dry-run] 将创建 {target.name}（用 `omni gen-stub {key} --write` 真正落盘）：\n"
                      + text)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
    except OSError as e:  # noqa: BLE001
        return False, f"写入失败：{e}"
    return True, f"已创建 {target.name}（占位，待你填权威来源）。路径：{target}"


_NA_MARKERS = ("未安装", "未检测到", "未运行", "未启用", "未找到", "不适用",
               "非 Windows", "非游戏平台", "无数据", "N/A", "n/d", "未识别")


def known_unknowns() -> List[dict]:
    """**已知未知**：有探针，但这台机器探不到（`--deep` 才实跑，默认不跑）。

    逐项调各子系统既有的零参只读报告，按「不适用标记」判定。耗秒级，
    因此只在显式 `--deep` 时调用，不做默认路径。
    """
    out: List[dict] = []
    for s in subsystems.SUBSYSTEMS:
        try:
            mod = importlib.import_module(f"{__name__.rsplit('.', 1)[0]}.{s.module}")
            fn = getattr(mod, s.fn, None)
            if fn is None:
                out.append({"key": s.key, "label": s.label, "domain": _domain_of(s.layer),
                            "reason": "报告函数不可用"})
                continue
            r = fn()
            msg = (r[1] if isinstance(r, tuple) and len(r) > 1
                   else "\n".join(str(x) for x in r) if isinstance(r, list) else str(r))
            ok = bool(r[0]) if isinstance(r, tuple) else True
            if not ok or any(m in msg for m in _NA_MARKERS):
                head = next((l.strip() for l in msg.splitlines()
                             if l.strip() and not set(l.strip()) <= set("─═━┄┅│+-=· ")),
                            "")
                out.append({"key": s.key, "label": s.label, "domain": _domain_of(s.layer),
                            "reason": "本机不适用/未安装", "brief": head[:60]})
        except Exception as e:  # noqa: BLE001
            out.append({"key": s.key, "label": s.label, "domain": _domain_of(s.layer),
                        "reason": f"诊断异常（已跳过）：{e}"})
    return out


def coverage_report() -> tuple:
    """能力覆盖面 + 接线完整度（纯计算）。返回 (ok, msg)。"""
    rows = wiring()
    doms = domains()
    complete = sum(1 for r in rows if r["complete"])
    out = ["全能全知自检 · 覆盖面与接线完整度（纯计算，只读）"]
    out.append("─" * 58)
    out.append("[一 · 能力覆盖面]")
    out.append(f"  登记 {len(rows)} 项 · 分属 {len(doms)} 个能力域 · "
               f"四件套齐全 {complete} 项（{complete * 100 // max(1, len(rows))}%）")
    for dom, items in doms.items():
        c = sum(1 for i in items if i["complete"])
        out.append(f"  · {dom:<8}{len(items):>2} 项（齐全 {c}）  "
                   + "、".join(i["label"] for i in items[:4])
                   + ("…" if len(items) > 4 else ""))
    out.append("─" * 58)
    out.append("[二 · 接线完整度 · 每项在四处的入口]")
    for kind, name in (("cli", "CLI 子命令"), ("gui", "GUI 面板"),
                       ("task", "任务定义"), ("data", "知识库")):
        n = sum(1 for r in rows if r["wiring"][kind])
        out.append(f"  · {name:<10}{n}/{len(rows)} 项已接")
    out.append("─" * 58)
    bs = blind_spots()
    out.append(f"[三 · 半截能力 · 缺 2 处入口以上的 {len(bs)} 项]")
    if bs:
        for b in bs:
            out.append(f"  · {b['label']}（{b['domain']}）缺 {'、'.join(b['missing'])}")
    else:
        out.append("  · 无：所有登记项的四处入口都已接全")
    return True, "\n".join(out)


def omni_report(deep: bool = False, min_missing: int = 2) -> tuple:
    """全能全知总览（三层边界）。返回 (ok, msg)。

    `deep=True` 时才实跑各子系统报告以统计「已知未知」（秒级，默认不跑）。
    """
    rows = wiring()
    doms = domains()
    complete = sum(1 for r in rows if r["complete"])

    out = ["全能全知自检（sysweeper · 我知道什么 / 我不知道什么 / 我不做什么）",
           "口径：全知不是什么都知道，是能精确说出自己的边界在哪。",
           "─" * 58]
    out.append("[第一层 · 我知道什么]")
    out.append(f"  登记 {len(rows)} 项能力 · 分属 {len(doms)} 个域 · "
               f"四件套齐全 {complete} 项（{complete * 100 // max(1, len(rows))}%）")
    for dom, items in doms.items():
        out.append(f"    · {dom:<8}{len(items):>2} 项")
    out.append("─" * 58)
    out.append("[第二层 · 我知道我不知道什么 · 本机探不到的]")
    if deep:
        ku = known_unknowns()
        out.append(f"  实跑 {len(rows)} 项，本机探不到 {len(ku)} 项：")
        for k in ku[:12]:
            tail = f"  — {k['brief']}" if k.get("brief") else ""
            out.append(f"    · {k['label']}（{k['domain']}）{k['reason']}{tail}")
        if len(ku) > 12:
            out.append(f"    …另有 {len(ku) - 12} 项（多为非本平台/未安装，属正常）")
    else:
        out.append("  未实跑（省时间）。要看本机真实盲区请用 --deep。")
    out.append("─" * 58)
    out.append("[第三层 · 我不知道我不知道什么 · 本工具没有探针的域]")
    for u in unknown_domains():
        out.append(f"  · {u['domain']}：{u['state']}")
        out.append(f"      理由：{u['reason']}")
        out.append(f"      怎么办：{u['remedy']}")
    out.append("─" * 58)
    bs = blind_spots(min_missing)
    out.append(f"[半截能力 · 缺 {min_missing} 处入口以上的 {len(bs)} 项]")
    for b in bs:
        out.append(f"  · {b['label']}（{b['domain']}）缺 {'、'.join(b['missing'])}"
                   f" — {b['remedies'][0]}")
    out.append("─" * 58)
    out.append("[边界声明]")
    out.append("  本工具只读诊断：不删系统文件、不改系统配置、不启停服务、不刷固件、")
    out.append("  不采集生物特征/定位/音视频/文件正文/通信内容，不保存任何账号凭证。")
    return True, "\n".join(out)


def capabilities_report() -> tuple:
    """本层能力自检（GUI/CLI 通用）：三层边界各自有多少条。"""
    rows = wiring()
    complete = sum(1 for r in rows if r["complete"])
    out = ["全能全知自检层能力自检（纯计算只读）"]
    out.append(f"  · 登记能力：{len(rows)} 项，分属 {len(domains())} 个域")
    out.append(f"  · 接线齐全：{complete}/{len(rows)} 项")
    out.append(f"  · 半截能力（缺 ≥2 处入口）：{len(blind_spots())} 项")
    out.append(f"  · 无探针域（边界声明）：{len(unknown_domains())} 个")
    out.append("  · 已知未知需 --deep 实跑（默认不跑，省时间）")
    out.append("  · 红线：只盘点与声明，不采集、不修改任何东西")
    return True, "\n".join(out)
