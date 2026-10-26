"""时空与全维度管理器子系统（chrono）：量子/计算机原理 + 时空理论 + 未来兼容的只读透镜。

本子系统把「量子理论及计算机原理」「时间理论」「空间理论」「施时空组合理论」「未来兼容」
沉淀为一套**只读观测框架**，并提供一个**全时空全维度循环往复管理器**：以 round-robin
的方式周而复始地观察每个维度，每维一视同仁（亦复如是），只读不写。

设计「只读、最小权限、不写任何系统态」：本工具**绝不**改系统时钟、绝不改时区、绝不分区/
格式化、绝不升级/替换组件、绝不执行任何量子写操作。它做的是：

1. **量子理论及计算机原理（观测透镜）**：叠加态（并行非破坏观测各维）/ 纠缠（时间维与
   空间维相互关联）/ 测量（只读探针即一次测量，观测不改态）/ 后量子密码（FIPS 203/204/205
   是未来兼容硬约束）。计算机原理给出「维度」本体论（时间/空间/未来兼容 + 量子透镜）。

2. **时间理论（时间维）**：时钟同步（NTP/PTP）、时区、生命周期阶段（provisioning→steady→
   aging→EOL）；只观测不改正。

3. **空间理论（空间维）**：存储层级/地址空间/挂载点/NUMA 拓扑；只盘点不整理。

4. **施时空组合理论**：把时间维事件（带时间戳日志）与空间维资源态配对成因果链，识别纠缠
   （某时刻负载高峰 ↔ 某磁盘写入放大/温度上升），只关联不阻断。

5. **未来兼容维**：标准 EOL 追踪、后量子迁移、前向兼容原则；只评估给迁移方向。

6. **全时空全维度循环往复管理器**：以上各维（及既有子系统维度）登记进统一维度注册表，
   `cycle_dimensions()` 以 itertools.cycle 周而复始 round-robin 观察，每轮遍历全部维度、
   每维只读——「循环往复，周而复始，亦复如是」。

所有写操作一律**只给官方/规范指引，不代执行**，严守本项目只读红线。
"""

from __future__ import annotations

import itertools
import json
import os
import re


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "chrono_theory_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 chrono 主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 chrono 主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 全维度注册表：时空框架统一观察的维度（chrono 自有 + 既有子系统维度）          #
# 每项：(维度id, 中文名, 所属层) —— 管理器以 round-robin 周而复始遍历之。       #
# --------------------------------------------------------------------------- #
DIMENSION_REGISTRY = (
    ("time", "时间维（时钟/时区/生命周期）", "chrono"),
    ("space", "空间维（存储/地址空间/NUMA）", "chrono"),
    ("spacetime", "施时空组合维（事件-资源因果链）", "chrono"),
    ("future_compat", "未来兼容维（标准 EOL / 后量子）", "chrono"),
    ("quantum_lens", "量子观测透镜（叠加/纠缠/测量）", "chrono"),
    ("electrical", "供电与环境安全维（回路质量/接地/负载）", "electrical"),
    ("durability", "设备长期保障维（电池/温度/SMART/uptime）", "durability"),
    ("peripheral", "外部设备连接与兼容维（星闪/触控/USB-C PD）", "peripheral"),
    ("remote", "远程接入维（连接保活/重连）", "remote"),
    ("network", "网络协议维（ITU/标准开关）", "network"),
    ("compat", "兼容层串联维（跨子系统印证）", "compat"),
)


def _norm_env(env_tags) -> set:
    return set(env_tags or [])


# --------------------------------------------------------------------------- #
# 只读探针（仅读本机可读信号，绝不改时钟/时区/分区/升级组件）                    #
# --------------------------------------------------------------------------- #

def read_time_domain() -> tuple:
    """只读观测时间维：时钟同步状态、时区、uptime→生命周期阶段（优雅降级）。

    读 /etc/adjtime / /etc/timezone / proc/uptime 等；非 Linux 或容器隔离即降级。
    绝不改时钟、绝不改时区。
    """
    info = {}
    # uptime → 生命周期阶段推导（只读，不写）
    up = "/proc/uptime"
    if os.path.isfile(up):
        try:
            with open(up, encoding="utf-8") as f:
                secs = float(f.read().split()[0])
            info["uptime_days"] = round(secs / 86400.0, 1)
            info["lifecycle"] = ("provisioning" if secs < 86400 * 7 else
                                 "steady" if secs < 86400 * 365 else
                                 "aging" if secs < 86400 * 365 * 3 else "eol_risk")
        except (OSError, ValueError):
            pass
    # 时区（只读）
    tz = os.environ.get("TZ")
    if tz:
        info["timezone_env"] = tz
    elif os.path.islink("/etc/localtime"):
        info["timezone_link"] = os.readlink("/etc/localtime")
    # 时钟同步残留（/etc/adjtime 只读）
    adj = "/etc/adjtime"
    if os.path.isfile(adj):
        info["has_adjtime"] = True
    if info:
        return True, info
    return False, "本机无 /proc/uptime 或容器隔离；时间维退化为概念观测（时钟同步/时区/生命周期只给指引）"


def read_space_domain() -> tuple:
    """只读盘点空间维：挂载点占用 / 内存容量 / NUMA 拓扑（优雅降级，绝不分区/格式化）。

    读 /proc/mounts / proc/meminfo / sys/devices/system/node；非 Linux 即降级。
    """
    info = {}
    mounts = "/proc/mounts"
    if os.path.isfile(mounts):
        try:
            with open(mounts, encoding="utf-8") as f:
                rows = [l for l in f if l.split()[2] in ("ext4", "xfs", "btrfs",
                        "apfs", "ntfs", "vfat", "tmpfs", "zfs")]
            info["mount_points"] = len(rows)
        except OSError:
            pass
    mi = "/proc/meminfo"
    if os.path.isfile(mi):
        try:
            with open(mi, encoding="utf-8") as f:
                for l in f:
                    if l.startswith("MemTotal:"):
                        info["mem_total_kb"] = int(l.split()[1])
                        break
        except (OSError, ValueError, IndexError):
            pass
    node_dir = "/sys/devices/system/node"
    if os.path.isdir(node_dir):
        try:
            nodes = [d for d in os.listdir(node_dir) if d.startswith("node")]
            info["numa_nodes"] = len(nodes)
        except OSError:
            pass
    if info:
        return True, info
    return False, "本机无 /proc/mounts 或容器隔离；空间维退化为概念观测（分区/地址空间/NUMA 只给指引）"


def read_future_compat() -> tuple:
    """只读评估未来兼容维：本机不可枚举真实组件 EOL，返回评估原则（只指引不升级）。

    标准知识库（data/*.json）即各维标准的版本事实源；真实 EOL 巡检可借 endoflife.date
    类数据源只读比对。绝不自动升级/替换组件。
    """
    return False, ("未来兼容维只做只读评估：依据 data/*.json 标准库与 endoflife.date 类"
                   "数据源比对各标准/组件的 EOL 与后量子迁移状态；任何升级/替换只给规范指引")


def read_quantum_lens() -> tuple:
    """量子观测透镜：本工具不模拟量子硬件，返回观测方法论（只读不写）。"""
    return True, {
        "superposition": "并行非破坏观测各维，不把任一维坍缩为改动作",
        "entanglement": "时间维与空间维相互关联（某时刻负载高峰 ↔ 该时刻资源占用）",
        "measurement": "只读探针即一次测量，观测不改系统态",
        "post_quantum": "涉及加密/会话安全的组件须向前向量子安全（FIPS 203/204/205）",
    }


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("read_time_domain", "时间维（时钟同步/时区/生命周期，只读观测）"),
    ("read_space_domain", "空间维（挂载点/内存/NUMA，只读盘点）"),
    ("read_future_compat", "未来兼容维（标准 EOL/后量子，只读评估）"),
    ("read_quantum_lens", "量子观测透镜（叠加/纠缠/测量，只读不写）"),
)


def environment_report() -> list:
    """返回本机 chrono 探针可用性概览（✓ 可用 / ✗ 降级）。"""
    lines = ["时空与全维度 · 本机可读信号："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def chrono_doc_list() -> list:
    """返回 chrono 主题文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构/标准: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    机理:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append(f"    建议: {ref.get('advice', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 引擎层（纯函数，不碰系统，便于单测）。每条建议回链知识库 key。                #
# --------------------------------------------------------------------------- #

def assess_time_domain(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由本机时间维读数给只读观测建议（纯函数）。action_type=guidance 不代执行。"""
    tags = _norm_env(env_tags)
    r = readings or {}
    sug = []
    td = r.get("time_domain")
    if isinstance(td, dict):
        if td.get("lifecycle") == "eol_risk":
            sug.append({
                "id": "time_eol",
                "title": f"系统 uptime 已达 {td.get('uptime_days')} 天（EOL 风险态），"
                         f"评估版本与组件退役/迁移路径",
                "severity": "warning", "action_type": "guidance", "rationale": "time_theory",
            })
        if "timezone_env" not in td and "timezone_link" not in td:
            sug.append({
                "id": "tz_unset",
                "title": "时区未显式确认；时区错配会导致日志/证书/排程全错位，"
                         "确认时区与时钟源一致",
                "severity": "notice", "action_type": "guidance", "rationale": "time_theory",
            })
    else:
        sug.append({
            "id": "time_readonly",
            "title": "时间维退化观测：确认 NTP/PTP 时钟同步、时区一致、生命周期阶段；"
                     "任何改时钟/时区只给规范指引",
            "severity": "info", "action_type": "guidance", "rationale": "time_theory",
        })
    return sug


def assess_space_domain(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由本机空间维读数给只读盘点建议（纯函数）。action_type=guidance 不代执行。"""
    tags = _norm_env(env_tags)
    r = readings or {}
    sug = []
    sd = r.get("space_domain")
    if isinstance(sd, dict):
        if sd.get("numa_nodes", 1) > 1:
            sug.append({
                "id": "numa_aware",
                "title": f"检测到 {sd['numa_nodes']} 个 NUMA 节点，内存近端/远端访问存在代价差；"
                         f"内存敏感负载按 NUMA 亲和排布",
                "severity": "info", "action_type": "guidance", "rationale": "space_theory",
            })
        if sd.get("mem_total_kb"):
            sug.append({
                "id": "mem_budget",
                "title": f"物理内存约 {sd['mem_total_kb']//1048576} GiB；按存储层级"
                         f"（寄存器→缓存→内存→NVMe→HDD）分别观测，避免 OOM（地址空间失衡）",
                "severity": "info", "action_type": "guidance", "rationale": "space_theory",
            })
    else:
        sug.append({
            "id": "space_readonly",
            "title": "空间维退化观测：盘点磁盘分区占用、内存容量、挂载点、地址空间是否失衡；"
                     "任何分区/格式化/清理只给规范指引",
            "severity": "info", "action_type": "guidance", "rationale": "space_theory",
        })
    return sug


def assess_future_compat(env_tags: list | None = None, readings: dict | None = None) -> list:
    """由未来兼容维给只读评估建议（纯函数）。action_type=guidance 不代执行。"""
    tags = _norm_env(env_tags)
    sug = [{
        "id": "eol_track",
        "title": "依据 data/*.json 标准库与 endoflife.date 类数据源只读比对各标准/组件 EOL；"
                 "达/近 EOL 即规划前向兼容迁移",
        "severity": "info", "action_type": "guidance", "rationale": "future_compat",
    }, {
        "id": "pq_migrate",
        "title": "涉及加密/会话安全的组件须向后量子算法（FIPS 203/204/205）演进；"
                 "属未来兼容硬约束",
        "severity": "notice", "action_type": "guidance", "rationale": "future_compat",
    }]
    return sug


def compose_spacetime(env_tags: list | None = None, readings: dict | None = None) -> list:
    """施时空组合：把时间维事件与空间维资源配对成因果链、识别纠缠（纯函数）。

    只读关联，不做任何阻断/回滚，只给观察结论与迁移建议。
    """
    r = readings or {}
    sug = []
    td = r.get("time_domain")
    sd = r.get("space_domain")
    if isinstance(td, dict) and isinstance(sd, dict):
        sug.append({
            "id": "causal_pair",
            "title": "可把带时间戳事件（journald/syslog）与当时空间资源态配对，"
                     "形成可追责因果链（何时发生 × 当时哪些资源改变）",
            "severity": "info", "action_type": "guidance", "rationale": "spacetime_theory",
        })
        sug.append({
            "id": "entangle_observe",
            "title": "时间维负载高峰与空间维写入放大/温度上升存在纠缠，须同时观测两维，"
                     "不可孤立判断",
            "severity": "info", "action_type": "guidance", "rationale": "spacetime_theory",
        })
    else:
        sug.append({
            "id": "spacetime_readonly",
            "title": "施时空组合退化观测：把时间维事件与空间维资源配对成因果链；"
                     "只读关联，不做阻断/回滚",
            "severity": "info", "action_type": "guidance", "rationale": "spacetime_theory",
        })
    return sug


def cycle_dimensions(dimensions: list | None = None, max_rounds: int = 3) -> dict:
    """全时空全维度循环往复管理器：round-robin 周而复始遍历全部维度，每维一视同仁（亦复如是）。

    纯函数，不碰系统。返回观察轮次表：
      - 用 itertools.cycle 实现「周而复始」——遍历完一轮即从首维重新开始；
      - 每轮覆盖全部维度，每个维度本轮只读、下一轮仍只读（循环往复）；
      - 「亦复如是」：所有维度适用同一只读观测透镜，无差别对待。

    :param dimensions: 维度注册表子集（默认全量 DIMENSION_REGISTRY）；
    :param max_rounds: 观察轮数（默认 3，演示循环往复；1 即单轮全维）。
    :return: 含 principle / dimensions / rounds / schedule（每轮维度序列）的字典。
    """
    if not dimensions:
        dimensions = DIMENSION_REGISTRY
    dim_ids = [d[0] for d in dimensions]
    cyc = itertools.cycle(dim_ids)
    schedule = []
    for _ in range(max_rounds):
        schedule.append(list(itertools.islice(cyc, len(dim_ids))))
    return {
        "principle": "循环往复，周而复始，亦复如是",
        "dimensions": [{"id": d[0], "name": d[1], "layer": d[2]} for d in dimensions],
        "rounds": max_rounds,
        "schedule": schedule,
        "note": "每轮以 round-robin 覆盖全部维度；首轮末维之后，次轮回到首维，周而复始。"
                "每个维度在每轮均只读观测，适用同一量子透镜（叠加/纠缠/测量），无差别对待。",
    }


def chrono_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    """端到端生成时空与全维度报告（无参可调用，供任务/CLI/GUI）。

    流程：量子/计算机原理透镜 → 时间维 → 空间维 → 施时空组合 → 未来兼容维 →
    全时空全维度循环往复管理器。每条建议/标准都回链知识库 key。只读不写。
    """
    readings = readings or {}
    # 注入本机探测读数（若未显式传入）
    if "time_domain" not in readings:
        readings["time_domain"] = read_time_domain()[1] if read_time_domain()[0] else {}
    if "space_domain" not in readings:
        readings["space_domain"] = read_space_domain()[1] if read_space_domain()[0] else {}

    time_s = assess_time_domain(env_tags, readings)
    space_s = assess_space_domain(env_tags, readings)
    st_s = compose_spacetime(env_tags, readings)
    fc_s = assess_future_compat(env_tags, readings)
    cyc = cycle_dimensions(DIMENSION_REGISTRY, max_rounds=3)

    lines = ["== 时空与全维度报告（量子/计算机原理 + 时间/空间/施时空组合/未来兼容，只读不写）=="]
    lines.append(f"维度标签: {sorted(_norm_env(env_tags)) or '未声明（默认基线）'}")

    lines.append("")
    lines.append("[① 量子观测透镜（叠加/纠缠/测量/后量子）]")
    lines.append("   并行非破坏观测各维（叠加态）；时间维与空间维相互关联（纠缠）；"
                 "只读探针即测量，观测不改态；加密组件向 FIPS 203/204/205 演进。")

    lines.append("")
    lines.append("[② 时间维（时间理论）]")
    for s in time_s:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("[③ 空间维（空间理论）]")
    for s in space_s:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("[④ 施时空组合维（事件-资源因果链）]")
    for s in st_s:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("[⑤ 未来兼容维（标准 EOL / 后量子）]")
    for s in fc_s:
        lines.append(f"  · [{s['severity']}] {s['title']}  ({s['rationale']})")

    lines.append("")
    lines.append("[⑥ 全时空全维度循环往复管理器]")
    lines.append(f"   原则：{cyc['principle']}")
    lines.append(f"   维度总数：{len(cyc['dimensions'])}；观察轮数：{cyc['rounds']}")
    for i, rnd in enumerate(cyc["schedule"], 1):
        lines.append(f"   第{i}轮（周而复始）：{' → '.join(rnd)}")
    lines.append(f"   {cyc['note']}")

    lines.append("")
    lines.append("安全不变量：本工具只读观测 + 出方案；改时钟/时区/分区/升级组件由用户在"
                 "图形界面或厂商工具确认；是否施工始终由用户决定。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）：返回官方/规范操作指引。                          #
# --------------------------------------------------------------------------- #

def _guidance(fn_name: str, title: str, steps: list, kb: str) -> tuple:
    lines = [f"{title}（规范指引，不代执行；依据 {kb}）:"] + [f"   {i+1}. {s}" for i, s in enumerate(steps)]
    return True, "\n".join(lines)


def guide_time_sync() -> tuple:
    """指引时钟同步与时区校准（不代执行）。"""
    return _guidance(
        "guide_time_sync", "时钟同步与时区校准",
        ["Linux：timedatectl set-ntp true 启用 NTP；工业/金融用 PTP(IEEE 1588) 微秒级同步",
         "Windows：w32time 服务同步；macOS：timed 守护",
         "统一时区（IANA tz database），避免日志/证书/排程错位"],
        "time_theory")


def guide_space_rebalance() -> tuple:
    """指引空间维盘点与扩容（不代执行）。"""
    return _guidance(
        "guide_space_rebalance", "空间维盘点与扩容",
        ["按 FHS 检查 / /usr /var /home /tmp 占用，避免日志/临时区被挤占",
         "OOM 即地址空间失衡：按存储层级（内存→NVMe→HDD）分别定位瓶颈",
         "NUMA 多节点：内存敏感负载按亲和排布；扩容/迁移由用户在图形界面确认"],
        "space_theory")


def guide_future_migrate() -> tuple:
    """指引未来兼容迁移（不代执行）。"""
    return _guidance(
        "guide_future_migrate", "未来兼容迁移（EOL / 后量子）",
        ["以 data/*.json 标准库与 endoflife.date 比对各标准/组件 EOL，规划前向兼容迁移",
         "加密/会话安全组件向 FIPS 203/204/205 后量子算法演进",
         "新标准须向后兼容既有（USB4 兼容 USB 3.2/2.0、星闪与 BLE/Wi-Fi 共存）"],
        "future_compat")


def guide_quantum_safe() -> tuple:
    """指引后量子安全（不代执行）。"""
    return _guidance(
        "guide_quantum_safe", "后量子安全就绪",
        ["涉及加密的组件核对 NIST FIPS 203(ML-KEM)/204(ML-DSA)/205(SLH-DSA)",
         "会话/密钥协商优先迁移到量子安全算法",
         "仅评估与规划，任何替换由用户/厂商工具执行"],
        "quantum_principles")


# 写指引清单（仅展示，调用也只回指引，不写系统）。
TUNES = (
    ("guide_time_sync", "时钟同步与时区校准（规范指引，不代执行）"),
    ("guide_space_rebalance", "空间维盘点与扩容（规范指引，不代执行）"),
    ("guide_future_migrate", "未来兼容迁移 EOL/后量子（规范指引，不代执行）"),
    ("guide_quantum_safe", "后量子安全就绪（规范指引，不代执行）"),
)


def chrono_tune_list() -> list:
    """返回 chrono 写指引清单，供 CLI/GUI 展示。只读展示，调用只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
