# -*- coding: utf-8 -*-
"""量子存储交换（qstore）——只读诊断子系统（v0.6.77 新建）。

把用户需求「保持量子架构 + ext4 默认 4K 对齐 + GPU/NPU/TPU/CAN 异构端点缓冲交互 +
按程序要求做储存读取扫描索引 + 量子数字逻辑矩阵做进制转换」落成只读子系统：

1. **端点存在性只读探测**：gpu/npu/tpu/can 四类端点 + cpu 基线，绝不加载驱动、
   绝不提交计算任务、绝不收发任何总线帧；
2. **ext4 / 4K 对齐核验**：sysfs → lsblk → statvfs 三级降级链，输出逐设备对齐判定；
3. **量子进制转换**：复用 quantum 子系统的 Π_k 置换矩阵编码门做保真往返——
   每个数字先 ``load()`` 复位（enc 是翻转语义，不复位会得到旧值 XOR k）、
   ``encode_number`` 编码、``decode_number`` 测量还原并逐一校验相等；
4. **存储管线仿真**：「分块 → 端点握手缓冲 → 量子进制转换 → 4096 对齐块打包」
   全程在量子架构基座上跑通，PiLink 链路统计给出利用率与覆盖浪费率。

诚实边界：量子部分做的是**可逆编码与管线仿真**，不是真的把 GPU/NPU 变成磁盘
加速器；沙箱内通常没有真实加速器，端点只做存在性只读探测，测试用假根目录覆盖。

红线（比全项目更严，同 radio）：绝不执行任何写盘/格式化命令——``mkfs.ext4``、
``dd``、``wipefs``、``sgdisk``、``parted`` 等只以**文本建议**出现，绝不进入执行
路径；CAN 端点绝不打开套接字、绝不发帧；本模块不引入进程执行/网络/动态链接
设施，不联网，对宿主零副作用。
"""
from __future__ import annotations

import glob
import os
import shutil
from typing import Dict, List, Optional, Tuple

from . import common
from . import quantum as qvm

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_refs() -> List[dict]:
    """只读加载 data/qstore_refs.json 的 items；失败返回空列表（不崩）。"""
    import json
    path = os.path.join(DATA_DIR, "qstore_refs.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return list(doc.get("items") or [])
    except Exception:  # noqa: BLE001 —— 知识库缺失不拖垮探测
        return []


REFS: List[dict] = _load_refs()

# 只读层自查项：每项回链知识库条目 key。
QSTORE_CHECKS: Dict[str, tuple] = {
    "endpoints": ("qstore", "GPU/NPU/TPU/CAN 端点存在性只读探测",
                  ["qstore-gpu-endpoint", "qstore-npu-endpoint",
                   "qstore-tpu-endpoint", "qstore-can-endpoint",
                   "qstore-pcisig-interconnect"]),
    "align": ("qstore", "ext4 / 4K 对齐逐设备核验（sysfs→lsblk→statvfs）",
              ["qstore-ext4-4k-align", "qstore-gpt-partition-align",
               "qstore-e2fsprogs"]),
    "radix": ("qstore", "Π_k 置换矩阵编码门的进制转换保真往返",
              ["qstore-quantum-matrix-anchor"]),
    "pipeline": ("qstore", "分块→端点缓冲→量子转换→4K 打包管线仿真",
                 ["qstore-block-layer", "qstore-quantum-matrix-anchor"]),
}

_SELF_POSITION = (
    "本层只读诊断：绝不执行写盘/格式化/分区命令（mkfs/dd/wipefs/sgdisk/parted 只作"
    "文本建议），绝不加载厂商内核模块或提交计算任务，CAN 绝不开套接字不发帧；"
    "对齐结论只来自 sysfs/lsblk/statvfs 只读读取；量子层纯软件仿真，对宿主零副作用。"
)

# ─────────────────────────────────────────────────────────────────────────────
# 端点表：cpu 基线 + 四类交互端点（每端点占 2 个经典位 req/ack 握手）
# ─────────────────────────────────────────────────────────────────────────────
N_QUBITS = 8        # 字节宽编码：0..255 经 Π_k 门严格可逆
N_CLASSICAL = 8     # 4 端点 × 2 位 req/ack，恰好占满

ENDPOINTS: Dict[str, dict] = {
    "cpu": {"label": "CPU（页缓存基线）", "kind": "baseline",
            "pins": (), "bits": (),
            "note": "页缓存命中→块层合并→调度器下发，是储存读取扫描索引的默认通路"},
    "gpu": {"label": "GPU（吞吐型）", "kind": "throughput",
            "pins": ("gpu_req", "gpu_ack"), "bits": (0, 1),
            "note": "批量宽粒度，承担缓冲与批量进制变换"},
    "npu": {"label": "NPU（推理型）", "kind": "inference",
            "pins": ("npu_req", "npu_ack"), "bits": (2, 3),
            "note": "粒度小、批间相关性弱，承担量化/变换型缓冲"},
    "tpu": {"label": "TPU（专化张量）", "kind": "tensor",
            "pins": ("tpu_req", "tpu_ack"), "bits": (4, 5),
            "note": "比 NPU 更窄但延迟可预期"},
    "can": {"label": "CAN（确定性控制面）", "kind": "control",
            "pins": ("can_req", "can_ack"), "bits": (6, 7),
            "note": "窄带宽、时延确定、帧格式标准——控制面握手，不承载数据面"},
}

_BLOCK = 4096  # 4K 对齐常量（ext4 默认块大小）


def _machine(seed: int = 2026) -> "qvm.QuantumMachine":
    """建一台 8q/8c 基座并定义全部端点针脚（超出宽度即清晰报错）。"""
    m = qvm.QuantumMachine(n_qubits=N_QUBITS, n_classical=N_CLASSICAL,
                           link_ratio=2.0, seed=seed)
    used = 0
    for key in ("gpu", "npu", "tpu", "can"):
        ep = ENDPOINTS[key]
        req, ack = ep["pins"]
        b0, b1 = ep["bits"]
        m.define_pin(req, b0)
        m.define_pin(ack, b1)
        used += 2
    if used > len(m.cpu):
        raise qvm.QuantumError(
            f"端点针脚共 {used} 位，超出经典寄存器 {len(m.cpu)} 位——"
            "请提高 n_classical 或减端点")
    return m


# 空程序：仅用于 load() 复位态矢量（enc 是翻转语义，编码新数字前必须归零）。
_RESET_IR = "qubits 8\nclassical 8\nbarrier"


def _quantum_roundtrip(m: "qvm.QuantumMachine", k: int) -> int:
    """量子进制转换单元：复位 → Π_k 编码 → 测量解码 → 校验相等。

    翻转语义契约：不复位直接编码 j 会得到 |旧值 XOR j> 而非 |j>；
    decode_number() 会真实坍缩态矢量，故解码后同样依赖下次 load() 复位。
    """
    if not 0 <= k < (1 << N_QUBITS):
        raise qvm.QuantumError(f"{k} 超出 {N_QUBITS} 位寄存器范围（0..{255}）")
    m.load(_RESET_IR)
    m.encode_number(k)
    got = m.decode_number()
    if got != k:
        raise qvm.QuantumError(f"保真往返失败：编码 {k} 解码得 {got}")
    return got


def _handshake(m: "qvm.QuantumMachine", key: str) -> bool:
    """端点 req/ack 两位握手（经典位，控制面，不入链）。"""
    ep = ENDPOINTS[key]
    if not ep["pins"]:
        return True  # cpu 基线无针脚
    req, ack = ep["pins"]
    m.set_pin(req, 1)
    m.set_pin(ack, 1)  # 仿真端点应答
    ok = m.read_pin(req) == 1 and m.read_pin(ack) == 1
    m.set_pin(req, 0)
    m.set_pin(ack, 0)
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# 报告一：端点存在性只读探测
# ─────────────────────────────────────────────────────────────────────────────
def _pci_class_lines() -> List[str]:
    """lspci 只读转储（缺失/失败返回空列表，不报错）。"""
    if not shutil.which("lspci"):
        return []
    _rc, out = common.run("lspci -nn", timeout=15)
    return [ln for ln in (out or "").splitlines() if ln.strip()]


def _endpoint_facts() -> Dict[str, List[str]]:
    """逐端点收集只读存在性证据（绝不触碰设备本身）。"""
    facts: Dict[str, List[str]] = {k: [] for k in ENDPOINTS}
    # GPU：DRM 节点 + lspci 显示控制器（类别 03xx）
    for card in sorted(glob.glob("/sys/class/drm/card*")):
        facts["gpu"].append("DRM 节点 " + os.path.basename(card))
    # NPU：内核 accel 子系统节点 + PCI 处理加速器（类别 12xx）
    for node in sorted(glob.glob("/dev/accel/*")):
        facts["npu"].append("accel 节点 " + node)
    # TPU：Edge TPU 传统 apex 节点 + Coral PCI 厂商 ID
    for node in sorted(glob.glob("/dev/apex_*")):
        facts["tpu"].append("apex 节点 " + node)
    # CAN：SocketCAN 网络接口
    for iface in sorted(glob.glob("/sys/class/net/can*")):
        facts["can"].append("SocketCAN 接口 " + os.path.basename(iface))
    # lspci 交叉核对（按类别名/厂商 ID 归类，只读配置空间）
    for ln in _pci_class_lines():
        low = ln.lower()
        if any(kw in low for kw in ("vga compatible", "3d controller", "display controller")):
            facts["gpu"].append("PCI " + ln.strip()[:60])
        elif "processing accelerator" in low:
            facts["npu"].append("PCI " + ln.strip()[:60])
        if "1ac1:" in low:  # Coral 的 PCI 厂商 ID
            facts["tpu"].append("PCI(Coral) " + ln.strip()[:60])
    return facts


def endpoint_probe_report() -> Tuple[bool, str]:
    """四类异构端点 + cpu 基线的存在性只读盘点。"""
    facts = _endpoint_facts()
    lines = [
        "◇ qstore 端点存在性只读盘点（绝不加载驱动/提交任务/收发帧）",
        "· cpu（基线）：页缓存通路总是可用（软件建模面）",
    ]
    found = 0
    for key in ("gpu", "npu", "tpu", "can"):
        ep = ENDPOINTS[key]
        hits = facts.get(key) or []
        if hits:
            found += 1
            lines.append(f"· {ep['label']}：检出 {len(hits)} 条证据")
            for h in hits[:4]:
                lines.append("    - " + h)
            if len(hits) > 4:
                lines.append(f"    - …共 {len(hits)} 条")
        else:
            lines.append(f"· {ep['label']}：未检出（不影响建模——测试/仿真用假证据覆盖）")
    lines.append(f"→ 结论：异构端点检出 {found}/4；缺失端点按「未检出」降级，不报错。")
    lines.append("  端点角色互补：" + "；".join(
        f"{ENDPOINTS[k]['label']}={ENDPOINTS[k]['kind']}" for k in ("gpu", "npu", "tpu", "can")))
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 报告二：ext4 / 4K 对齐逐设备核验（sysfs → lsblk → statvfs 降级链）
# ─────────────────────────────────────────────────────────────────────────────
def _read_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return int(fh.read().strip())
    except Exception:  # noqa: BLE001 —— 字段缺失按 0 降级（virtio 常见）
        return None


def _aligned(start_lba: int, ss: int, phys: int, align_off: int) -> Tuple[bool, str]:
    """4K 对齐判定：(start·ss)%4096==0 且 ss≤4096 且 (offset+start·ss)%max(phys,4096)==0。"""
    byte_off = start_lba * ss
    phys_eff = max(phys or ss, _BLOCK)
    c1 = byte_off % _BLOCK == 0
    c2 = (ss or 512) <= _BLOCK
    c3 = ((align_off or 0) + byte_off) % phys_eff == 0
    ok = c1 and c2 and c3
    why = (f"起始 {byte_off}B%4096={byte_off % _BLOCK}"
           f"｜ss={ss}｜offset={align_off or 0}%{phys_eff}={((align_off or 0) + byte_off) % phys_eff}")
    return ok, why


def alignment_report() -> Tuple[bool, str]:
    """sysfs 优先 → lsblk 校验 → statvfs 兜底，输出逐设备 4K 对齐判定。"""
    lines = ["◇ qstore ext4 / 4K 对齐核验（三级降级：sysfs→lsblk→statvfs）"]
    dev_rows = 0
    for dev in sorted(glob.glob("/sys/block/*")):
        name = os.path.basename(dev)
        q = os.path.join(dev, "queue")
        ss = _read_int(os.path.join(q, "logical_block_size")) or 512
        ps = _read_int(os.path.join(q, "physical_block_size")) or ss
        ao = _read_int(os.path.join(q, "alignment_offset")) or 0  # 字段缺失按 0
        parts = sorted(glob.glob(os.path.join(dev, name + "[0-9]*")))
        if not parts:
            lines.append(f"· {name}：ss={ss} ps={ps} offset={ao}（无分区，跳过起点判定）")
            continue
        for part in parts:
            pname = os.path.basename(part)
            start = _read_int(os.path.join(part, "start"))
            if start is None:
                continue
            ok, why = _aligned(start, ss, ps, ao)
            dev_rows += 1
            mark = "✓" if ok else "✗"
            lines.append(f"· {pname}: {mark} 4K 对齐（{why}）")
    if dev_rows == 0:
        lines.append("· sysfs 无块设备分区可读（容器常见）——降级 lsblk / statvfs：")
    # 校验层：lsblk
    if shutil.which("lsblk"):
        _rc, out = common.run(
            "lsblk -o NAME,PHY-SEC,LOG-SEC,ALIGNMENT", timeout=15)
        if out and out.strip():
            lines.append("· lsblk 交叉核对：")
            for ln in out.strip().splitlines()[:8]:
                lines.append("    " + ln)
    # 兜底层：statvfs
    try:
        st = os.statvfs("/")
        lines.append(f"· statvfs('/'): f_bsize={st.f_bsize} f_frsize={st.f_frsize}"
                     f" → {'4K ✓' if st.f_frsize % _BLOCK == 0 else '非 4K ✗'}（文件系统视角）")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"· statvfs 不可用：{exc}")
    lines.append("→ 建议（仅文本，绝不执行）：未对齐的分区用 parted/gdisk 重排起点；"
                 "新建 ext4 用 mkfs.ext4 -b 4096 并确认起始偏移整除 4096。")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 报告三：量子进制转换（Π_k 保真往返 + 翻转语义陷阱对照）
# ─────────────────────────────────────────────────────────────────────────────
def radix_report() -> Tuple[bool, str]:
    """Π_k 编码门保真往返演示：逐数字复位→编码→解码→校验。"""
    m = _machine()
    lines = [
        f"◇ qstore 量子进制转换（Π_k 置换矩阵，{N_QUBITS} 位字节宽寄存器）",
        "· 数学：enc k = ∏ X_i（k 置 1 位复合），酉矩阵严格可逆；解码即测量。",
    ]
    samples = [0, 1, 255, 77, 202, 128]
    for k in samples:
        got = _quantum_roundtrip(m, k)
        lines.append(f"· 往返 {k:>3} → Π_k 编码 → 解码 {got:>3} {'✓' if got == k else '✗'}")
    # 翻转语义陷阱对照：不复位连续编码 → XOR 干扰
    m.load(_RESET_IR)
    m.encode_number(202)
    m.encode_number(77)          # 未复位：得到 202 XOR 77
    m.decode_number()            # 坍缩，取 cpu 无关——直接用返回值
    # 重新演示干扰值：复位后先 202 再 77 不复位
    m.load(_RESET_IR)
    m.encode_number(202)
    m.encode_number(77)
    polluted = m.decode_number()
    lines.append(f"· 陷阱对照：不复位连编 202→77 得 {polluted}（=202⊕77），"
                 f"非 77 → 必须先 load() 复位（本模块 _quantum_roundtrip 已内建）。")
    # 4K 数列视角：字节流 → 12 位重组 → base-4096（「硬盘可接受的数列」）
    raw = [77, 202, 255, 1]                     # 4 字节样本
    bits12 = []
    acc, nbits = 0, 0
    for byte in raw:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= 12:
            bits12.append((acc >> (nbits - 12)) & 0xFFF)
            nbits -= 12
    if nbits:
        bits12.append((acc << (12 - nbits)) & 0xFFF)
    lines.append("· 4K 数列打包：字节流 " + " ".join(f"{b:02x}" for b in raw)
                 + " → 12 位重组 → 4096 进制数列 "
                 + " ".join(f"{d:03x}" for d in bits12)
                 + f"（每项 0..4095，{_BLOCK} 进制=4K 粒度）")
    lines.append("→ 诚实边界：量子层做的是可逆编码与校验，不提速；"
                 "进制/打包的进位取模由经典层完成，中间数字过量子寄存器校验。")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 报告四：存储管线仿真（分块→端点缓冲→量子转换→4K 打包）
# ─────────────────────────────────────────────────────────────────────────────
def pipeline_report(seed: int = 2026) -> Tuple[bool, str]:
    """在量子架构基座上跑通「按程序要求的储存读取扫描索引」管线。"""
    m = _machine(seed=seed)
    history: List[dict] = []          # 全量链路历史（snapshot() 只回最近 7 条，不能用它）
    data_endpoints = ("gpu", "npu", "tpu")
    sample = [77, 202, 255, 1, 0, 128, 64, 32]   # 样本字节流（按程序要求的读取序列）
    packed: List[int] = []            # 4096 对齐块的字节累计
    lines = [
        "◇ qstore 存储管线仿真：分块 → 端点握手缓冲 → 量子进制转换 → 4K 打包",
        f"· 样本读取序列（{len(sample)} 字节）：" + " ".join(str(b) for b in sample),
    ]
    for i, byte in enumerate(sample):
        ep = data_endpoints[i % len(data_endpoints)]
        hs = _handshake(m, ep)                      # 数据端点握手（控制面）
        got = _quantum_roundtrip(m, byte)           # 量子转换（编码+解码各入链一次）
        history.append({"step": i, "endpoint": ep, "handshake": hs,
                        "value": byte, "decoded": got})
        packed.append(got)
        if sum(packed) % _BLOCK == 0 and packed:
            _handshake(m, "can")                    # CAN 控制面：块完成确认
    # 链路统计：PiLink 环形缓冲的利用率与覆盖浪费
    st = m.link.stats()
    util = st["total_writes"] / max(1, st["total_writes"] + st["overwrites"])
    lines.append(f"· 管线记录 {len(history)} 条（每字节=握手+编码+解码），"
                 f"全部校验相等：{all(h['handshake'] and h['value'] == h['decoded'] for h in history)}")
    lines.append(f"· PiLink 链路：容量 {st['size']} 槽（ceil(2π)），"
                 f"总写入 {st['total_writes']}，覆盖 {st['overwrites']}，"
                 f"利用率 {util:.1%}（覆盖越少越无丢失）")
    lines.append(f"· snapshot() 只保留最近 {st['size']} 条 → 全量历史由本模块自累积"
                 f"（{len(history)} 条），与 total_writes 一致性校验："
                 f"{'✓' if st['total_writes'] >= len(history) * 2 else '✗'}")
    lines.append("· 4K 打包：累计 " + str(sum(packed)) + "B → 按 4096 对齐需 "
                 f"{max(1, -(-sum(packed) // _BLOCK))} 块（不足整块按一块计，尾部填充不写盘）")
    lines.append("→ 真实通路对应：CPU 页缓存命中→块层合并→调度器下发；本仿真把"
                 "「缓存」映射为 PiLink、「端点握手」映射为针脚、「进制转换」映射为 Π_k 门。")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 聚合报告与能力自检
# ─────────────────────────────────────────────────────────────────────────────
def doc_list() -> List[str]:
    """知识条目清单（回链 data 层 key）。"""
    out: List[str] = []
    for ref in REFS:
        out.append(f"· [{ref.get('key', '?')}] {ref.get('name', '?')}"
                   f"（{ref.get('org', '未注明')}）")
    return out


def reference(key: str) -> dict:
    """按 key 取知识条目；无则空 dict。"""
    for ref in REFS:
        if ref.get("key") == key:
            return ref
    return {}


def qstore_report() -> Tuple[bool, str]:
    """聚合报告：知识层 + 四段只读报告各摘一段 + 自查回链。"""
    blocks: List[str] = []
    blocks.append("═══ qstore 量子存储交换 · 聚合报告（只读） ═══")
    blocks.append(f"知识层：{len(REFS)} 条目（data/qstore_refs.json）")
    for ln in doc_list():
        blocks.append("  " + ln)
    ok, msg = endpoint_probe_report()
    blocks.append("")
    blocks.append("【端点】" + msg.splitlines()[0])
    blocks.append("  " + next((l for l in msg.splitlines() if l.startswith("→")), ""))
    ok, msg = alignment_report()
    align_lines = [l for l in msg.splitlines() if l.startswith("· ")][:3]
    blocks.append("")
    blocks.append("【对齐】" + msg.splitlines()[0])
    for l in align_lines:
        blocks.append("  " + l)
    ok, msg = radix_report()
    blocks.append("")
    blocks.append("【进制】" + msg.splitlines()[0])
    blocks.append("  " + next((l for l in msg.splitlines() if l.startswith("· 4K 数列")), "  （见 radix 子命令）"))
    ok, msg = pipeline_report()
    blocks.append("")
    blocks.append("【管线】" + next((l for l in msg.splitlines() if l.startswith("· PiLink")), ""))
    blocks.append("")
    blocks.append(_SELF_POSITION)
    return True, "\n".join(blocks)


def capabilities_report() -> Tuple[bool, str]:
    """能力自检：端点表/知识条目回链/红线声明。"""
    lines = [
        "◇ qstore 能力自检",
        f"· 端点表：{len(ENDPOINTS)} 个（cpu 基线 + gpu/npu/tpu/can），"
        f"针脚共 {sum(len(v['pins']) for v in ENDPOINTS.values())} 位 / 经典寄存器 {N_CLASSICAL} 位",
        f"· 量子寄存器：{N_QUBITS} qubits（字节宽 Π_k 编码），链路 ratio=2.0",
        f"· 知识条目回链：{len(REFS)} 条；自查项 {len(QSTORE_CHECKS)} 组",
    ]
    for name, (key, desc, links) in QSTORE_CHECKS.items():
        missing = [k for k in links if not reference(k)]
        lines.append(f"    - {name}：{desc} → 回链 {len(links)} 条"
                     + (f"（缺失 {missing}）" if missing else " ✓"))
    lines.append("· 红线：" + _SELF_POSITION)
    return True, "\n".join(lines)
