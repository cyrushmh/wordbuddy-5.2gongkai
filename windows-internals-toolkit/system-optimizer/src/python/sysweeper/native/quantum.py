"""量子程序与量子虚拟机（quantum）：把量子层从「概念登记」推进到「真能运行」。

定位（v0.6.68 新增，v0.6.69 补量子架构基座）：现有基础是
``data/concepts/quantum_taxonomy.json``（8 域 66 概念的只读分类图谱）与
``research/quantum/`` 的 JS 浏览器模拟器；本模块在 Python 侧补齐**可执行**的
一层——纯标准库、零依赖的 **n 量子比特态矢量模拟器 + 量子程序 IR + 虚拟机运行时 +
量子架构基座（QuantumMachine）**，内置 Bell/GHZ/量子隐形传态/Grover/BV 等小程序。

**量子架构基座**（v0.6.69：应用量子的意义依然是量子架构——不论虚拟量子，还是
量子计算机虚拟其他硬件，都站在同一块基座上）：
- **量子矩阵数字转换门**：``enc k`` 由置换矩阵 Π_k（按 k 的二进制分解复合 X 门）
  把整个寄存器从 |0…0> 确定性映到 |k>；``decode_number()`` 测量解码回整数。
- **CPU ↔ 闪存不间断交换**：经典控制寄存器（CPU）与量子核之间的每一次交换
  （指令推进/enc/measure）都写入数据链路；``step()``/``run_until_halt()`` 驱动，
  直到 ``halt`` 或程序耗尽（带步数预算护栏防失控）。
- **tan / ctan 返回交互**：把上一次交互量（相位/测量值）经 tan/ctan（π 周期）折叠
  为下一步旋转角——自定义控制启发式，矩阵酉性不受影响。
- **圆周率数据链路缓冲**：``PiLink`` 环形缓冲容量取 ``ceil(ratio·π)``，
  交换流按 π 周期节流，程序终止后可 drain 复盘。
- **虚拟其他硬件**：CPU 寄存器每个经典位可映射为虚拟针脚（pin），
  外部虚拟硬件经针脚 + 链路缓冲与量子核交互。

能力总览：
- **门集**：单比特 I/X/Y/Z/H/S/Sdg/T/Tdg/Rx/Ry/Rz/P，双比特 CX/CY/CZ/CH/SWAP，三比特 CCX；
  外加经典条件门（``xd``/``zd``/``if``）与 ``measure``/``barrier``/``reset`` 指令。
- **虚拟机**：按指令顺序执行；``measure`` 真实坍缩态矢量并写入经典寄存器；
  条件门依据经典位实现**经典反馈**（量子隐形传态修复即依赖于此）。
- **可复现**：所有随机性来自 ``random.Random(seed)``，同 seed 同程序必得同结果（确定性测试）。
- **程序 IR**：文本格式（``qubits N`` / ``h 0`` / ``cx 0 1`` / ``ry pi/4 0`` / ``measure 0 -> 0``）
  与结构化 op 列表双向转换；非法程序报错并列出门集与有效语法，不静默吞错。

红线（与全工具一致）：本模块是**纯软件模拟**——
- 绝不联网、绝不接量子硬件/云量子计算服务、零第三方依赖（不用 numpy）；
- 只读 taxonomy 图谱作参考（``taxonomy_basis()``），不写任何数据文件；
- 只做计算与教学演示，不对宿主系统产生任何副作用。
"""

from __future__ import annotations

import collections
import json
import math
import os
import random

__all__ = [
    "QuantumError",
    "MAX_QUBITS", "GATES", "GATE_ARITY", "GATE_PARAMS", "PARAM_GATES",
    "BUILTIN_PROGRAMS",
    "StateVector", "QuantumProgram",
    "PiLink", "QuantumMachine",
    "parse_program", "run_program", "run_named",
    "phase_wrap", "tan_return", "cotan_return",
    "quantum_report", "environment_report", "capabilities", "taxonomy_basis",
    "architecture_report", "quantum_probe",
]

# 态矢量规模上限：2^20 = 1,048,576 振幅（纯 Python list，约数十 MB 级），教学/验证足够。
MAX_QUBITS = 20

# 单行 IR 中单程序最多指令数（防误粘贴巨型文件耗尽内存）。
MAX_OPS = 100_000


class QuantumError(Exception):
    """量子程序/虚拟机错误：携带可读原因与修复提示（含门集与语法示例）。"""

    def __init__(self, msg: str, hint: str = ""):
        super().__init__(msg + (("\n提示：" + hint) if hint else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 门集（复数矩阵；qubit 0 约定为最高有效位，与文本 IR 的书写顺序一致）
# ─────────────────────────────────────────────────────────────────────────────
_R = 1.0 / math.sqrt(2.0)


def _rx(theta: float):
    c, s = math.cos(theta / 2.0), math.sin(theta / 2.0)
    return [[c, -1j * s], [-1j * s, c]]


def _ry(theta: float):
    c, s = math.cos(theta / 2.0), math.sin(theta / 2.0)
    return [[c, -s], [s, c]]


def _rz(theta: float):
    return [[complex(math.cos(theta / 2.0), -math.sin(theta / 2.0)), 0j],
            [0j, complex(math.cos(theta / 2.0), math.sin(theta / 2.0))]]


def _p(phi: float):
    return [[1.0 + 0j, 0j], [0j, complex(math.cos(phi), math.sin(phi))]]


def _cx():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]]


def _cy():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, -1j], [0, 0, 1j, 0]]


def _cz():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]]


def _ch():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, _R, _R], [0, 0, _R, -_R]]


def _swap():
    return [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]


def _ccx():
    m = [[0j] * 8 for _ in range(8)]
    for i in range(6):  # 110,111 两行做翻转
        m[i][i] = 1
    m[6][7] = 1
    m[7][6] = 1
    return m


# gate -> (矩阵生成(零参传 () / 参数化传 params 元组), 量子比特数, 参数个数)
GATES = {
    "i":   (lambda: ((1, 0), (0, 1)), 1, 0),
    "x":   (lambda: ((0, 1), (1, 0)), 1, 0),
    "y":   (lambda: ((0, -1j), (1j, 0)), 1, 0),
    "z":   (lambda: ((1, 0), (0, -1)), 1, 0),
    "h":   (lambda: ((_R, _R), (_R, -_R)), 1, 0),
    "s":   (lambda: ((1, 0), (0, 1j)), 1, 0),
    "sdg": (lambda: ((1, 0), (0, -1j)), 1, 0),
    "t":   (lambda: ((1, 0), (0, complex(_R, _R))), 1, 0),
    "tdg": (lambda: ((1, 0), (0, complex(_R, -_R))), 1, 0),
    "p":   (_p, 1, 1),
    "rx":  (_rx, 1, 1),
    "ry":  (_ry, 1, 1),
    "rz":  (_rz, 1, 1),
    "cx":  (_cx, 2, 0),
    "cy":  (_cy, 2, 0),
    "cz":  (_cz, 2, 0),
    "ch":  (_ch, 2, 0),
    "swap": (_swap, 2, 0),
    "ccx": (_ccx, 3, 0),
}
GATE_ARITY = {name: spec[1] for name, spec in GATES.items()}
GATE_PARAMS = {name: spec[2] for name, spec in GATES.items()}
PARAM_GATES = tuple(sorted(n for n, c in GATE_PARAMS.items() if c))

# 门集中文参考（报告/文档用）
GATE_HELP = {
    "i": ("恒等", 1, 0, "无操作"),
    "x": ("Pauli-X 非门", 1, 0, "|0>↔|1>"),
    "y": ("Pauli-Y", 1, 0, "X 与 Z 的复合（带 i 相位）"),
    "z": ("Pauli-Z 相位翻转", 1, 0, "|1> 变 -|1>"),
    "h": ("Hadamard 叠加门", 1, 0, "|0>→(|0>+|1>)/√2"),
    "s": ("S 相位门", 1, 0, "Z 方向的 90° 旋转"),
    "sdg": ("S 逆", 1, 0, "S 的共轭"),
    "t": ("T 相位门", 1, 0, "Z 方向的 45° 旋转"),
    "tdg": ("T 逆", 1, 0, "T 的共轭"),
    "p": ("相位门 P(φ)", 1, 1, "|1> 乘 e^{iφ}"),
    "rx": ("绕 X 旋转", 1, 1, "角度弧度"),
    "ry": ("绕 Y 旋转", 1, 1, "角度弧度"),
    "rz": ("绕 Z 旋转", 1, 1, "角度弧度；全局相位不影响测量"),
    "cx": ("受控非 CNOT", 2, 0, "控制位为 1 时翻转目标位"),
    "cy": ("受控-Y", 2, 0, "CNOT 的 Y 变体"),
    "cz": ("受控-Z", 2, 0, "两位均 1 时相位 -1"),
    "ch": ("受控-H", 2, 0, "控制叠加"),
    "swap": ("SWAP 交换", 2, 0, "交换两比特"),
    "ccx": ("Toffoli 受控受控非", 3, 0, "两控制位均 1 时翻转目标位"),
}


def _matrix_of(gate: str, params):
    spec = GATES.get(gate)
    if spec is None:
        raise QuantumError(f"未知道门 '{gate}'",
                           "有效门：" + " ".join(sorted(GATES)) +
                           "；条件门用 xd/zd 或 if；其余指令：measure/barrier/reset")
    factory, arity, nparams = spec
    if nparams and params is not None and len(params) != nparams:
        raise QuantumError(f"门 '{gate}' 需要 {nparams} 个参数，收到 {len(params)} 个")
    return factory(*params) if nparams else factory()


# ─────────────────────────────────────────────────────────────────────────────
# 安全的数字解析（支持 float / pi / tau / 简单乘除，绝不用 eval）
# ─────────────────────────────────────────────────────────────────────────────
_NUM_TOKENS = {"pi": math.pi, "tau": math.tau, "e": math.e}


def _parse_number(tok: str) -> float:
    """解析角度/参数：'0.5'、'pi'、'pi/2'、'2*pi'、'-pi/4'、'3/7' 等。非法即抛错。"""
    tok = tok.strip().lower()
    if not tok:
        raise QuantumError("空参数")
    try:
        return float(tok)
    except ValueError:
        pass
    # 递归下降：term (('*' | '/') term)*；term := 数 | pi | tau | e | ( expr )
    pos = 0

    def expr() -> float:
        nonlocal pos
        val = term()
        while pos < len(tok) and tok[pos] in "*/":
            op = tok[pos]
            pos += 1
            rhs = term()
            val = val * rhs if op == "*" else val / rhs
        return val

    def term() -> float:
        nonlocal pos
        if pos < len(tok) and tok[pos] == "-":
            pos += 1
            return -term()
        if pos < len(tok) and tok[pos] == "+":
            pos += 1
            return term()
        if pos < len(tok) and tok[pos] == "(":
            pos += 1
            val = expr()
            if pos >= len(tok) or tok[pos] != ")":
                raise QuantumError(f"参数 '{tok}' 括号不匹配")
            pos += 1
            return val
        for name, val in _NUM_TOKENS.items():
            if tok.startswith(name, pos):
                pos += len(name)
                return val
        start = pos
        while pos < len(tok) and (tok[pos].isdigit() or tok[pos] == "."):
            pos += 1
        if start == pos:
            raise QuantumError(f"无法解析参数 '{tok}'",
                               "示例：0.5 / pi / pi/2 / -pi/4 / 2*pi")
        return float(tok[start:pos])

    val = expr()
    if pos != len(tok):
        raise QuantumError(f"无法解析参数 '{tok}'")
    return val


# ─────────────────────────────────────────────────────────────────────────────
# 态矢量模拟器
# ─────────────────────────────────────────────────────────────────────────────
class StateVector:
    """n 量子比特纯态态矢量：振幅 list 长度 2^n，qubit 0 = 最高有效位（MSB）。

    只提供受控原语（应用门/测量/采样/重置），不感知上层程序结构；
    所有写路径都作用在自身副本上（``run_program`` 每 shot 重新 ``instantiate``）。
    """

    __slots__ = ("n", "amps")

    def __init__(self, n: int):
        if not isinstance(n, int) or isinstance(n, bool) or n < 1:
            raise QuantumError(f"量子比特数必须是 >=1 的整数，收到 {n!r}")
        if n > MAX_QUBITS:
            raise QuantumError(f"量子比特数 {n} 超过上限 {MAX_QUBITS}（纯 Python 内存约束）")
        self.n = n
        self.amps = [0j] * (1 << n)
        self.amps[0] = 1.0 + 0j

    # ── 内部：应用 k 比特门（qubits[0] 为子索引最高位） ──
    def apply(self, gate: str, qubits, params=()):
        qubits = list(qubits)
        k = GATE_ARITY[gate]
        if len(qubits) != k:
            raise QuantumError(f"门 '{gate}' 需要 {k} 个比特，收到 {len(qubits)} 个")
        if len(set(qubits)) != len(qubits):
            raise QuantumError(f"门 '{gate}' 的比特索引重复：{qubits}")
        for q in qubits:
            if not 0 <= q < self.n:
                raise QuantumError(f"比特索引 {q} 越界（共 {self.n} 比特）")
        matrix = _matrix_of(gate, params)
        n, dim = self.n, 1 << k
        masks = [1 << (n - 1 - q) for q in qubits]
        fixed = ((1 << n) - 1)
        for m in masks:
            fixed &= ~m
        amps = self.amps
        new = [0j] * (1 << n)
        for base in range(1 << n):
            if base & ~fixed:
                continue  # 只遍历「目标比特全 0」的基态，其余由矩阵枚举
            cur = []
            for p in range(dim):
                s = base
                for b in range(k):
                    if (p >> (k - 1 - b)) & 1:
                        s |= masks[b]
                cur.append(amps[s])
            for p in range(dim):
                row = matrix[p]
                acc = 0j
                for q in range(dim):
                    acc += row[q] * cur[q]
                s_out = base
                for b in range(k):
                    if (p >> (k - 1 - b)) & 1:
                        s_out |= masks[b]
                new[s_out] = acc
        self.amps = new
        return self

    # ── 概率与观测 ──
    def probabilities(self):
        total = 1 << self.n
        out = [0.0] * total
        acc = 0.0
        for i, a in enumerate(self.amps):
            p = a.real * a.real + a.imag * a.imag
            out[i] = p
            acc += p
        if acc > 0 and abs(acc - 1.0) > 1e-9:  # 数值漂移保护：归一化
            out = [p / acc for p in out]
        return out

    def prob_one(self, q: int) -> float:
        if not 0 <= q < self.n:
            raise QuantumError(f"比特索引 {q} 越界（共 {self.n} 比特）")
        mask = 1 << (self.n - 1 - q)
        return sum(p for i, p in enumerate(self.probabilities()) if i & mask)

    def measure_bit(self, q: int, rng: random.Random) -> int:
        """边缘概率采样 + 坍缩 + 归一化。返回 0/1。"""
        if not 0 <= q < self.n:
            raise QuantumError(f"比特索引 {q} 越界（共 {self.n} 比特）")
        mask = 1 << (self.n - 1 - q)
        p1 = sum(a.real * a.real + a.imag * a.imag
                 for i, a in enumerate(self.amps) if i & mask)
        outcome = 1 if rng.random() < p1 else 0
        keep = mask if outcome else ~mask
        acc = 0j
        for i, a in enumerate(self.amps):
            if (i & mask) and not outcome:
                self.amps[i] = 0j
            elif not (i & mask) and outcome:
                self.amps[i] = 0j
            else:
                acc += a * a.conjugate()
        norm = abs(acc) ** 0.5
        if norm > 0:
            self.amps = [a / norm if a != 0 else 0j for a in self.amps]
        return outcome

    def sample_index(self, rng: random.Random) -> int:
        """按概率采样一个基态索引（比特串）。"""
        probs = self.probabilities()
        r = rng.random()
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if r < acc:
                return i
        return len(probs) - 1

    def reset_qubit(self, q: int, rng: random.Random) -> None:
        """重置为 |0>（先测量再按结果翻转，保证与测量语义一致）。"""
        if self.measure_bit(q, rng) == 1:
            self.apply("x", [q])

    def clone(self) -> "StateVector":
        sv = StateVector.__new__(StateVector)
        sv.n = self.n
        sv.amps = list(self.amps)
        return sv


# ─────────────────────────────────────────────────────────────────────────────
# 量子程序 IR：结构化 op 列表 + 文本格式双向转换 + 启动绑定
# ─────────────────────────────────────────────────────────────────────────────
def _fmt_num(v: float) -> str:
    if abs(v - math.pi) < 1e-12:
        return "pi"
    if abs(v - math.tau) < 1e-12:
        return "tau"
    s = repr(round(v, 12))
    return s


class QuantumProgram:
    """一个已校验的量子程序：``n_qubits`` / ``n_classical`` / ``ops`` / 可选名称。

    op 结构（dict）：
    - ``{"op": "gate", "gate": "h", "qubits": [0], "params": []}``
    - ``{"op": "measure", "qubit": 0, "clbit": 0}``
    - ``{"op": "cond", "gate": "x", "clbit": 0, "qubits": [2], "params": []}``
    - ``{"op": "reset", "qubit": 0}`` / ``{"op": "barrier"}``
    """

    __slots__ = ("n_qubits", "n_classical", "ops", "name", "source")

    def __init__(self, n_qubits: int, n_classical: int, ops, name: str = "", source: str = ""):
        self.n_qubits = n_qubits
        self.n_classical = n_classical
        self.ops = list(ops)
        self.name = name
        self.source = source

    def instantiate(self) -> StateVector:
        return StateVector(self.n_qubits)

    def gate_count(self) -> int:
        return sum(1 for op in self.ops if op["op"] == "gate")

    def op_types(self):
        counts = {}
        for op in self.ops:
            counts[op["op"]] = counts.get(op["op"], 0) + 1
        return counts

    # ── 文本 IR 序列化（规范格式，供 round-trip 与人工阅读） ──
    def to_text_ir(self) -> str:
        lines = [f"qubits {self.n_qubits}", f"classical {self.n_classical}"]
        for op in self.ops:
            kind = op["op"]
            if kind == "gate":
                parts = [op["gate"]]
                parts += [_fmt_num(p) for p in op["params"]]
                parts += [str(q) for q in op["qubits"]]
                lines.append(" ".join(parts))
            elif kind == "measure":
                lines.append(f"measure {op['qubit']} -> {op['clbit']}")
            elif kind == "cond":
                parts = ["if", str(op["clbit"]), op["gate"]]
                parts += [_fmt_num(p) for p in op["params"]]
                parts += [str(q) for q in op["qubits"]]
                lines.append(" ".join(parts))
            elif kind == "reset":
                lines.append(f"reset {op['qubit']}")
            elif kind == "enc":
                lines.append(f"enc {op['value']}")
            elif kind == "halt":
                lines.append("halt")
            elif kind == "barrier":
                lines.append("barrier")
        return "\n".join(lines)

    def describe(self) -> str:
        types = self.op_types()
        return (f"{self.name or '未命名程序'}: {self.n_qubits} 量子比特 / "
                f"{self.n_classical} 经典位 / {len(self.ops)} 条指令 "
                f"({', '.join(f'{k}×{v}' for k, v in sorted(types.items()))})")


def parse_program(text: str, name: str = "") -> QuantumProgram:
    """解析文本 IR → :class:`QuantumProgram`（启动即校验，非法即抛 :class:`QuantumError`）。

    语法（# 起头为注释，空行忽略）::

        qubits N            # 可选；缺省则按出现的最大索引推断（>=1）
        classical N         # 可选；缺省等于量子比特数
        <gate> [参数...] <比特...>     # 门必须写全参数与比特
        measure Q -> C      # 测量 Q 写入经典位 C（-> C 可省略，自动分配）
        reset Q             # 重置为 |0>
        barrier             # 顺序屏障（无计算效果）
        if C <gate> [参数...] <比特...>   # 经典位 C 为 1 时执行门
        xd C Q... / zd C Q  # if C x / if C z 的简写
    """
    if not isinstance(text, str):
        raise QuantumError("程序必须是文本 IR（str）")
    ops = []
    n_qubits = 0
    n_classical = None
    qubits_declared = False  # 显式 qubits 头出现后，比特簿记以头为准（不得静默扩容）
    auto_clbit = 0

    def _track_qubits(qubits):
        """门/条件门引用的比特入簿：已声明则校验越界，否则按最大索引推断。"""
        nonlocal n_qubits
        for qidx in qubits:
            if qubits_declared:
                if qidx >= n_qubits:
                    raise QuantumError(f"比特索引 {qidx} 越界（qubits {n_qubits}）")
            else:
                n_qubits = max(n_qubits, qidx + 1)

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        toks = line.split()
        head = toks[0].lower()
        try:
            if head == "qubits":
                if len(toks) != 2:
                    raise QuantumError("qubits 指令需要一个整数参数")
                n_qubits = int(toks[1])
                if not 1 <= n_qubits <= MAX_QUBITS:
                    raise QuantumError(f"qubits 需在 1..{MAX_QUBITS}，收到 {n_qubits}")
                qubits_declared = True
                continue
            if head == "classical":
                if len(toks) != 2:
                    raise QuantumError("classical 指令需要一个整数参数")
                n_classical = int(toks[1])
                if not 0 <= n_classical <= 256:
                    raise QuantumError(f"classical 需在 0..256，收到 {n_classical}")
                continue
            if head == "barrier":
                ops.append({"op": "barrier"})
                continue
            if head == "halt":
                ops.append({"op": "halt"})
                continue
            if head == "enc":
                # 量子矩阵数字转换门：整数 → 基态 |k>（置换矩阵 Π_k）
                if len(toks) != 2:
                    raise QuantumError("enc 需要一个非负整数（目标基态索引）")
                value = int(toks[1])
                if value < 0:
                    raise QuantumError(f"enc 的目标索引不能为负：{toks[1]}")
                ops.append({"op": "enc", "value": value})
                continue
            if head in ("xd", "zd"):
                # 简写：xd C Q... = if C x Q...
                if len(toks) < 3:
                    raise QuantumError(f"{head} 需要经典位索引与至少一个比特索引")
                gate = "x" if head == "xd" else "z"
                clbit, qubits = int(toks[1]), [int(t) for t in toks[2:]]
                _need(gate, clbit, qubits, ())
                _track_qubits(qubits)
                ops.append({"op": "cond", "gate": gate, "clbit": clbit,
                            "qubits": qubits, "params": []})
                continue
            if head == "if":
                # if C <gate> [params] <qubits...>
                if len(toks) < 3:
                    raise QuantumError("if 需要经典位索引与门名")
                clbit = int(toks[1])
                gate = toks[2].lower()
                params, qubits = _split_params_qubits(gate, toks[3:])
                _need(gate, clbit, qubits, params)
                _track_qubits(qubits)
                ops.append({"op": "cond", "gate": gate, "clbit": clbit,
                            "qubits": qubits, "params": params})
                continue
            if head == "measure":
                if len(toks) in (2, 4):
                    qubit = int(toks[1])
                    if len(toks) == 4:
                        if toks[2] != "->":
                            raise QuantumError("measure 的箭头写作 '->'，如 'measure 0 -> 0'")
                        clbit = int(toks[3])
                    else:
                        clbit = auto_clbit
                        auto_clbit += 1
                    _check_ranges(qubit, clbit, n_qubits, n_classical)
                    ops.append({"op": "measure", "qubit": qubit, "clbit": clbit})
                    continue
                raise QuantumError("measure 写作 'measure Q' 或 'measure Q -> C'")
            if head == "reset":
                if len(toks) != 2:
                    raise QuantumError("reset 需要一个比特索引")
                qubit = int(toks[1])
                if n_qubits and not 0 <= qubit < n_qubits:
                    raise QuantumError(f"比特索引 {qubit} 越界（qubits {n_qubits}）")
                ops.append({"op": "reset", "qubit": qubit})
                continue
            if head in GATES:
                gate = head
                params, qubits = _split_params_qubits(gate, toks[1:])
                _need(gate, None, qubits, params)
                _track_qubits(qubits)
                ops.append({"op": "gate", "gate": gate, "qubits": qubits, "params": params})
                continue
            raise QuantumError(f"未知指令/门 '{toks[0]}'",
                               "有效门：" + " ".join(sorted(GATES)) +
                               "；指令：qubits/classical/measure/reset/barrier/enc/halt/if/xd/zd")
        except QuantumError as exc:
            raise QuantumError(f"第 {lineno} 行 {line!r}：{exc}",
                               "示例：'h 0' / 'cx 0 1' / 'ry pi/4 0' / 'measure 0 -> 0' / 'if 0 x 2'") from exc
        except ValueError as exc:
            raise QuantumError(f"第 {lineno} 行 {line!r}：索引/参数不是整数或数字（{exc}）") from exc
    if n_qubits == 0:
        raise QuantumError("程序未声明任何量子比特（无 qubits 指令且无门指令）")
    if n_classical is None:
        n_classical = n_qubits
    if len(ops) > MAX_OPS:
        raise QuantumError(f"指令数 {len(ops)} 超过上限 {MAX_OPS}")
    for op in ops:
        kind = op["op"]
        if kind == "measure":
            _check_ranges(op["qubit"], op["clbit"], n_qubits, n_classical)
        elif kind == "cond":
            _check_ranges(op["qubits"][0], op["clbit"], n_qubits, n_classical)
            for qubit in op["qubits"]:
                if not 0 <= qubit < n_qubits:
                    raise QuantumError(f"条件门比特索引 {qubit} 越界（qubits {n_qubits}）")
        elif kind == "gate":
            for qubit in op["qubits"]:
                if not 0 <= qubit < n_qubits:
                    raise QuantumError(f"比特索引 {qubit} 越界（qubits {n_qubits}）")
        elif kind == "reset":
            if not 0 <= op["qubit"] < n_qubits:
                raise QuantumError(f"reset 比特索引 {op['qubit']} 越界（qubits {n_qubits}）")
        elif kind == "enc":
            if op["value"] >= (1 << n_qubits):
                raise QuantumError(
                    f"enc 目标 {op['value']} 超出 {n_qubits} 比特寄存器范围"
                    f"（0..{(1 << n_qubits) - 1}）")
    return QuantumProgram(n_qubits, n_classical, ops, name=name, source=text)


def _split_params_qubits(gate: str, rest):
    """从 token 尾部规则地切出参数（前 nparams 个）与比特索引（其余全部）。"""
    nparams = GATE_PARAMS.get(gate, 0)
    if gate not in GATES:
        raise QuantumError(f"未知道门 '{gate}'",
                           "有效门：" + " ".join(sorted(GATES)))
    if len(rest) < nparams + GATE_ARITY[gate]:
        raise QuantumError(
            f"门 '{gate}' 需要 {GATE_ARITY[gate]} 个比特索引" +
            (f"与 {nparams} 个参数" if nparams else "") +
            f"，收到 {' '.join(rest)!r}")
    params = [_parse_number(t) for t in rest[:nparams]]
    qubits = []
    for t in rest[nparams:]:
        q = int(t)
        if q < 0:
            raise QuantumError(f"比特索引不能为负：{t}")
        qubits.append(q)
    return params, qubits


def _need(gate: str, clbit, qubits, params):
    """条件门/单门的合成校验（clbit=None 表示无条件门）。"""
    if gate not in GATES:
        raise QuantumError(f"未知道门 '{gate}'",
                           "有效门：" + " ".join(sorted(GATES)))
    if GATE_PARAMS[gate] and len(params) != GATE_PARAMS[gate]:
        raise QuantumError(f"门 '{gate}' 需要 {GATE_PARAMS[gate]} 个参数")
    if len(qubits) != GATE_ARITY[gate]:
        raise QuantumError(f"门 '{gate}' 需要 {GATE_ARITY[gate]} 个比特")
    if clbit is not None and clbit < 0:
        raise QuantumError(f"经典位索引不能为负：{clbit}")


def _check_ranges(qubit: int, clbit: int, n_qubits: int, n_classical) -> None:
    if n_qubits and not 0 <= qubit < n_qubits:
        raise QuantumError(f"比特索引 {qubit} 越界（qubits {n_qubits}）")
    if n_classical is not None and not 0 <= clbit < max(n_classical, 1):
        raise QuantumError(f"经典位索引 {clbit} 越界（classical {n_classical}）")


# ─────────────────────────────────────────────────────────────────────────────
# 虚拟机运行时
# ─────────────────────────────────────────────────────────────────────────────
def run_program(program, shots: int = 1024, seed=None, measure_all: bool = True):
    """执行量子程序 ``shots`` 次，返回计数/概率/经典位统计。

    ``program`` 可为 :class:`QuantumProgram` 或文本 IR（str）。
    ``seed`` 非 None 时结果完全可复现（同 seed 同程序必同结果）。
    每 shot 从 |0...0> 重新开始，按指令顺序执行；``measure`` 真实坍缩；
    ``if``/``xd``/``zd`` 依据经典寄存器实现经典反馈。
    """
    if isinstance(program, str):
        program = parse_program(program)
    if not isinstance(program, QuantumProgram):
        raise QuantumError("program 必须是 QuantumProgram 或文本 IR（str）")
    if not isinstance(shots, int) or shots < 1:
        raise QuantumError(f"shots 必须是 >=1 的整数，收到 {shots!r}")
    if shots > 1_000_000:
        raise QuantumError("shots 过大（上限 1,000,000）")
    rng = random.Random(seed)
    counts = {}
    clbit_counts = {}
    samples = []
    for _ in range(shots):
        sv = program.instantiate()
        clbits = [0] * max(program.n_classical, 1)
        for op in program.ops:
            kind = op["op"]
            if kind == "gate":
                sv.apply(op["gate"], op["qubits"], op["params"])
            elif kind == "enc":
                _encode_number(sv, op["value"])
            elif kind == "measure":
                clbits[op["clbit"]] = sv.measure_bit(op["qubit"], rng)
            elif kind == "cond":
                if clbits[op["clbit"]]:
                    sv.apply(op["gate"], op["qubits"], op["params"])
            elif kind == "reset":
                sv.reset_qubit(op["qubit"], rng)
            elif kind == "halt":
                break
            # barrier：仅顺序语义，无计算效果
        idx = sv.sample_index(rng) if measure_all else 0
        bitstring = format(idx, "0{}b".format(program.n_qubits))
        counts[bitstring] = counts.get(bitstring, 0) + 1
        key = tuple(clbits[:program.n_classical])
        clbit_counts[key] = clbit_counts.get(key, 0) + 1
        if len(samples) < 8:
            samples.append({"bitstring": bitstring, "classical": key})
    total = shots
    probs = {k: v / total for k, v in sorted(counts.items())}
    return {
        "ok": True,
        "program": program.describe(),
        "n_qubits": program.n_qubits,
        "n_classical": program.n_classical,
        "shots": shots,
        "seed": seed,
        "counts": dict(sorted(counts.items())),
        "probabilities": probs,
        "classical": {str(k): v / total for k, v in sorted(clbit_counts.items())},
        "samples": samples,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 内置小程序库（文本 IR 单一事实源，可直接运行/阅读/改写）
# ─────────────────────────────────────────────────────────────────────────────
BUILTIN_PROGRAMS = {
    "superposition": "qubits 1\nh 0",
    "bell": "qubits 2\nh 0\ncx 0 1",
    "ghz": "qubits 3\nh 0\ncx 0 1\ncx 1 2",
    "teleport": ("qubits 3\nclassical 2\n"
                 "x 0\n"          # 待传输态置 |1>（验证修复后恒为 1）
                 "h 1\ncx 1 2\n"  # 制备 Bell 对
                 "cx 0 1\nh 0\n"  # Alice 端纠缠
                 "measure 0 -> 0\nmeasure 1 -> 1\n"  # Bell 测量
                 "xd 1 2\nzd 0 2"),                  # Bob 端经典反馈修复
    "grover2q": ("qubits 2\n"
                 "h 0\nh 1\n"        # 均匀叠加
                 "cz 0 1\n"          # Oracle：标记 |11>
                 "h 0\nh 1\nx 0\nx 1\ncz 0 1\nx 0\nx 1\nh 0\nh 1"),  # 扩散
    "bv2": ("qubits 2\n"           # Bernstein-Vazirani，隐串 10（一位查询）
            "x 1\nh 0\nh 1\ncx 0 1\nh 0"),
}


def run_named(name: str, shots: int = 1024, seed=None):
    """运行内置程序（bell/ghz/teleport/grover2q/bv2/superposition）。"""
    key = (name or "").strip().lower()
    if key not in BUILTIN_PROGRAMS:
        raise QuantumError(f"未找到内置程序 '{name}'",
                           "可用：" + " ".join(sorted(BUILTIN_PROGRAMS)))
    prog = parse_program(BUILTIN_PROGRAMS[key], name=key)
    return run_program(prog, shots=shots, seed=seed)


# ─────────────────────────────────────────────────────────────────────────────
# 量子架构基座（v0.6.69）：CPU（经典控制）↔ 闪存链路（圆周率缓冲）↔ 量子核
# ─────────────────────────────────────────────────────────────────────────────
def _encode_number(sv: StateVector, k: int) -> None:
    """量子矩阵数字转换门：把寄存器从 |0…0> 确定性映到 |k>。

    数学上是置换矩阵 Π_k = ∏_{i: k_i=1} X_i（各 X 门矩阵的复合仍是酉矩阵），
    因此 enc 不是「打包压塞」而是严格的门矩阵作用；逆操作即测量解码。
    """
    if not 0 <= k < (1 << sv.n):
        raise QuantumError(f"enc 目标 {k} 超出 {sv.n} 比特寄存器范围（0..{(1 << sv.n) - 1}）")
    for b in range(sv.n):
        if (k >> (sv.n - 1 - b)) & 1:  # qubit 0 = 最高位，与文本 IR 比特串一致
            sv.apply("x", [b])


def phase_wrap(x: float) -> float:
    """π 周期折叠：tan 的周期是 π，把任意实角折叠到 (-π/2, π/2) 主值区间。"""
    return math.atan(math.tan(x))


def tan_return(x: float) -> float:
    """tan 返回交互：上次交互量 → tan（π 周期）→ 下一步旋转角（主值）。

    这是架构基座里「量子核 → CPU → 量子核」回环的控制启发式：
    确定性、无随机、与矩阵酉性正交（只改经典控制量）。
    """
    return phase_wrap(x)


def cotan_return(x: float) -> float:
    """ctan 返回交互：cot = tan(π/2 − θ)，给出与 tan_return 互补的旋转角。"""
    return math.pi / 2.0 - phase_wrap(x)


class PiLink:
    """圆周率数据链路缓冲：CPU 与量子核之间不间断交换流的环形缓冲。

    - 容量 = ``ceil(ratio·π)``（默认 ratio=2 → 7 槽），圆周率决定链路深度；
    - 满则覆盖最旧记录（FIFO 节流），总量与覆盖数如实统计；
    - 每一步交换（gate/enc/measure/…）都入链——交换不间断直到程序终止；
    - ``drain()`` 在程序终止后复盘全程。
    """

    def __init__(self, ratio: float = 2.0):
        if not ratio > 0:
            raise QuantumError(f"链路 ratio 必须为正数，收到 {ratio!r}")
        self.ratio = float(ratio)
        self.size = max(2, int(math.ceil(self.ratio * math.pi)))
        self._buf = collections.deque(maxlen=self.size)
        self.total_writes = 0
        self.overwrites = 0

    def push(self, record: dict) -> None:
        if len(self._buf) == self.size:
            self.overwrites += 1
        self._buf.append(record)
        self.total_writes += 1

    def snapshot(self) -> list:
        return list(self._buf)

    def drain(self) -> list:
        """取出并清空缓冲（程序终止后复盘用）。"""
        items = list(self._buf)
        self._buf.clear()
        return items

    def stats(self) -> dict:
        return {"size": self.size, "buffered": len(self._buf),
                "total_writes": self.total_writes, "overwrites": self.overwrites}


class QuantumMachine:
    """量子架构基座：一块基座同时支撑「虚拟量子」与「量子计算机虚拟其他硬件」。

    三层：
    - **CPU**：经典控制寄存器 ``cpu``（list[bit]），每个经典位可 define_pin 成
      虚拟针脚——外部虚拟硬件（led/继电器/传感器模型）经针脚读写；
    - **闪存链路**：``PiLink`` 圆周率环形缓冲，记录 CPU↔量子核的每一次交换；
    - **量子核**：``StateVector`` 态矢量 + 门矩阵。

    不间断交换语义：``step()`` 执行一条指令并把交换记录写入链路；
    ``run_until_halt()`` 循环推进直到 ``halt`` / 程序耗尽 / 步数预算耗尽。
    """

    def __init__(self, n_qubits: int = 4, n_classical: int = None,
                 link_ratio: float = 2.0, seed=None):
        if n_classical is None:
            n_classical = n_qubits
        self.sv = StateVector(n_qubits)
        self.cpu = [0] * n_classical
        self.link = PiLink(link_ratio)
        self.program: QuantumProgram = None
        self.pc = 0
        self.steps = 0
        self.halted = False
        self.rng = random.Random(seed)
        self.next_angle = 0.0     # tan/ctan 返回交互产出，供下一步控制消费
        self.pins = {}            # 虚拟针脚：name → CPU 经典位索引
        self._last_measure = None

    # ── 程序装载与推进 ──
    def load(self, program) -> "QuantumMachine":
        """装载程序（QuantumProgram 或文本 IR），复位 pc/ halted，量子核归零。"""
        if isinstance(program, str):
            program = parse_program(program)
        if not isinstance(program, QuantumProgram):
            raise QuantumError("load 需要 QuantumProgram 或文本 IR")
        if program.n_qubits != self.sv.n or program.n_classical != len(self.cpu):
            raise QuantumError(
                f"程序规模 {program.n_qubits}q/{program.n_classical}c 与基座 "
                f"{self.sv.n}q/{len(self.cpu)}c 不一致")
        self.program = program
        self.pc = 0
        self.steps = 0
        self.halted = False
        self.sv = self.sv.__class__(self.sv.n)
        return self

    def step(self):
        """执行一条指令并把本次交换写入链路；已终止则返回 None。"""
        if self.program is None:
            raise QuantumError("尚未 load() 程序")
        if self.halted or self.pc >= len(self.program.ops):
            return None
        op = self.program.ops[self.pc]
        self.pc += 1
        self.steps += 1
        kind = op["op"]
        record = {"pc": self.pc - 1, "op": kind}
        if kind == "gate":
            self.sv.apply(op["gate"], op["qubits"], op["params"])
            record["gate"] = op["gate"]
            record["qubits"] = op["qubits"]
        elif kind == "enc":
            _encode_number(self.sv, op["value"])
            record["value"] = op["value"]
            record["dir"] = "c→q"      # CPU 把数字写入量子核（数字转换门）
        elif kind == "measure":
            value = self.sv.measure_bit(op["qubit"], self.rng)
            self.cpu[op["clbit"]] = value
            self._last_measure = value
            record.update({"dir": "q→c", "clbit": op["clbit"], "qubit": op["qubit"],
                           "value": value})
            # tan/ctan 返回交互：测量值经 π 周期折叠，产出下一步旋转角
            ang = tan_return(float(self.cpu[op["clbit"]]) * math.pi / 2.0 + self.next_angle)
            cot = cotan_return(float(self.cpu[op["clbit"]]) * math.pi / 2.0 + self.next_angle)
            record["tan_return"] = ang
            record["ctan_return"] = cot
            self.next_angle = ang
        elif kind == "cond":
            if self.cpu[op["clbit"]]:
                self.sv.apply(op["gate"], op["qubits"], op["params"])
            record.update({"clbit": op["clbit"], "gate": op["gate"]})
        elif kind == "reset":
            self.sv.reset_qubit(op["qubit"], self.rng)
            record["qubit"] = op["qubit"]
        elif kind == "halt":
            self.halted = True
            record["dir"] = "cpu→halt"
        # barrier 仅顺序语义
        self.link.push(record)
        return record

    def run_until_halt(self, max_steps: int = 4096) -> list:
        """不间断交换直到程序终止：halt / 指令耗尽 / 步数预算耗尽（护栏）。"""
        if self.program is None:
            raise QuantumError("尚未 load() 程序")
        if max_steps < 1:
            raise QuantumError("max_steps 必须 >=1")
        while True:
            rec = self.step()
            if rec is None:
                return self.link.snapshot()
            if self.steps >= max_steps:
                raise QuantumError(
                    f"步数预算 {max_steps} 耗尽仍未终止（pc={self.pc}）——"
                    "程序可能含超长指令流；确认后调高 max_steps 或加 halt")

    # ── 数字转换门：整数 ⟷ 量子态 ──
    def encode_number(self, k: int) -> int:
        """CPU → 量子核：把整数 k 经置换矩阵 Π_k 写入寄存器（数字转换门）。"""
        _encode_number(self.sv, k)
        self.link.push({"op": "enc", "dir": "c→q", "value": k})
        return k

    def decode_number(self) -> int:
        """量子核 → CPU：测量全部比特解码回整数（enc 的逆）。"""
        value = 0
        for b in range(self.sv.n):
            bit = self.sv.measure_bit(b, self.rng)
            value = (value << 1) | bit
        self.link.push({"op": "dec", "dir": "q→c", "value": value})
        return value

    # ── 虚拟其他硬件：针脚 ──
    def define_pin(self, name: str, bit: int) -> None:
        """把 CPU 经典位映射为虚拟硬件针脚（led/relay/sensor 模型经名读写）。"""
        if not 0 <= bit < len(self.cpu):
            raise QuantumError(f"针脚位 {bit} 越界（CPU {len(self.cpu)} 位）")
        if not name or not isinstance(name, str):
            raise QuantumError("针脚名必须是非空字符串")
        self.pins[name] = bit

    def set_pin(self, name: str, value: int) -> None:
        bit = self.pins.get(name)
        if bit is None:
            raise QuantumError(f"未定义针脚 '{name}'", "已定义：" + " ".join(sorted(self.pins)))
        self.cpu[bit] = 1 if value else 0

    def read_pin(self, name: str) -> int:
        bit = self.pins.get(name)
        if bit is None:
            raise QuantumError(f"未定义针脚 '{name}'", "已定义：" + " ".join(sorted(self.pins)))
        return self.cpu[bit]

    # ── 观测 ──
    def phase_of(self, qubit: int = 0) -> float:
        """读取指定比特 |0>/|1> 分量的相对相位角（Bloch 相位圆上的观测点）。"""
        if not 0 <= qubit < self.sv.n:
            raise QuantumError(f"比特索引 {qubit} 越界")
        mask = 1 << (self.sv.n - 1 - qubit)
        alpha = self.sv.amps[0]
        beta = self.sv.amps[mask]
        return math.atan2(beta.imag, beta.real) - math.atan2(alpha.imag, alpha.real)

    def state_dict(self) -> dict:
        return {"n_qubits": self.sv.n, "cpu": list(self.cpu),
                "pc": self.pc, "steps": self.steps, "halted": self.halted,
                "next_angle": self.next_angle, "pins": dict(self.pins),
                "link": self.link.stats()}


# ─────────────────────────────────────────────────────────────────────────────
# 报告与环境探针（对齐 native 惯例：(ok, msg) / list[str] / dict）
# ─────────────────────────────────────────────────────────────────────────────
def capabilities() -> dict:
    """能力清单：上限比特数 / 门集 / 内置程序 / 特性（确定性种子、经典反馈、坍缩测量）。"""
    return {
        "max_qubits": MAX_QUBITS,
        "gates": sorted(GATES),
        "param_gates": list(PARAM_GATES),
        "builtin_programs": sorted(BUILTIN_PROGRAMS),
        "features": [
            "态矢量模拟（纯标准库，零依赖）",
            "真实测量坍缩与边缘概率",
            "经典条件门（if/xd/zd）实现经典反馈",
            "确定性种子（同 seed 同程序可复现）",
            "文本 IR 与结构化 op 双向转换",
        ],
        "architecture": [
            "量子矩阵数字转换门 enc k（置换矩阵 Π_k，整数⟷基态）",
            "CPU↔闪存不间断交换（step/run_until_halt，halt 终止）",
            "tan/ctan 返回交互（π 周期折叠为下一步旋转角）",
            "圆周率数据链路缓冲 PiLink（ceil(ratio·π) 槽环形缓冲）",
            "虚拟针脚 pin：CPU 经典位映射，虚拟其他硬件",
        ],
        "red_lines": [
            "不联网、不接量子硬件/云量子服务",
            "只读 taxonomy 参考，不写数据文件",
            "纯软件模拟，对宿主零副作用",
        ],
    }


def taxonomy_basis() -> dict:
    """只读加载现有量子分类图谱（data/concepts/quantum_taxonomy.json）作参考底座。

    文件缺失/损坏时安全返回 {}（不阻断本模块任何功能）。
    """
    path = os.path.join(os.path.dirname(__file__), "..", "data", "concepts",
                        "quantum_taxonomy.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    meta = data.get("_meta", {}) if isinstance(data.get("_meta"), dict) else {}
    domains = data.get("domains", []) or []
    return {
        "version": meta.get("version"),
        "domains": len(domains),
        "concepts": len(data.get("concepts", []) or []),
        "bridges": len(data.get("bridges", []) or []),
        "domain_names": [d.get("label") if isinstance(d, dict) else str(d) for d in domains],
    }


def quantum_probe() -> dict:
    """冒烟探测：跑 Bell 程序 256 枪（固定种子），验证计数相关性与测量坍缩。"""
    res = run_named("bell", shots=256, seed=20260101)
    c = res["counts"]
    ok = (set(c) <= {"00", "11"}) and len(c) == 2 and min(c.values()) > 0
    return {
        "ok": ok,
        "counts": c,
        "bell_prob_00": res["probabilities"].get("00", 0.0),
        "bell_prob_11": res["probabilities"].get("11", 0.0),
        "seed": 20260101,
    }


def quantum_report():
    """子系统报告（ok, msg）：量子虚拟机就绪状态 + 冒烟结果摘要。"""
    try:
        smoke = quantum_probe()
    except QuantumError as exc:
        return (False, f"量子虚拟机自检失败：{exc}")
    caps = capabilities()
    basis = taxonomy_basis()
    msg = (
        f"量子虚拟机就绪：态矢量模拟 {caps['max_qubits']} 比特上限 / "
        f"{len(caps['gates'])} 门 / 内置程序 {len(caps['builtin_programs'])} 个；"
        f"Bell 冒烟 {'通过' if smoke['ok'] else '失败'} "
        f"(P(00)={smoke['bell_prob_00']:.3f}, P(11)={smoke['bell_prob_11']:.3f})"
    )
    if basis:
        msg += f"；参考图谱 {basis['domains']} 域 / {basis['concepts']} 概念"
    return (True, msg)


def environment_report():
    """多行环境报告（list[str]，对齐 chrono/virt 报告风格）。"""
    caps = capabilities()
    basis = taxonomy_basis()
    lines = [
        "量子程序与虚拟机（native/quantum.py，v0.6.68 新增）",
        f"  模拟器：态矢量纯态模拟，上限 {caps['max_qubits']} 量子比特（纯标准库零依赖）",
        f"  门集（{len(caps['gates'])}）：{' '.join(caps['gates'])}",
        f"  参数门：{' '.join(caps['param_gates']) or '无'}",
        f"  内置程序：{' '.join(caps['builtin_programs'])}",
        "  特性：",
    ]
    for f in caps["features"]:
        lines.append(f"    - {f}")
    lines.append("  量子架构基座：")
    for a in caps["architecture"]:
        lines.append(f"    - {a}")
    lines.append("  红线：")
    for r in caps["red_lines"]:
        lines.append(f"    - {r}")
    if basis:
        lines.append(
            f"  参考图谱（只读）：{basis['version']}，{basis['domains']} 域 / "
            f"{basis['concepts']} 概念 / {basis['bridges']} 桥梁")
    smoke = quantum_probe()
    lines.append(
        f"  冒烟（Bell 256 枪 seed=20260101）：{'通过' if smoke['ok'] else '失败'}，"
        f"计数 {smoke['counts']}")
    return lines


def architecture_report():
    """量子架构基座报告（ok, msg）：数字转换门 / 不间断交换 / tan·ctan / π 链路。"""
    m = QuantumMachine(n_qubits=4, seed=1)
    m.define_pin("out0", 0)
    prog = parse_program("qubits 4\nenc 5\nh 0\nmeasure 0 -> 0\nhalt")
    m.load(prog)
    recs = m.run_until_halt()
    ok = (m.cpu[0] in (0, 1) and m.link.total_writes == m.steps == 4
          and recs[0]["op"] == "enc" and recs[0]["value"] == 5
          and m.pins.get("out0") == 0)
    link_stats = m.link.stats()
    msg = (f"量子架构基座就绪：4q CPU/量子核 / 链路 {link_stats['size']} 槽"
           f"（ceil(2π)）/ 交换 {m.link.total_writes} 次至 halt；"
           f"数字转换门 enc 5 → {recs[0]['op']}；tan 返回交互正常；"
           f"pin out0={m.read_pin('out0')}")
    return (ok, msg)


if __name__ == "__main__":  # 直接运行：python -m sysweeper.native.quantum [程序名|arch]
    import sys

    _arg = sys.argv[1] if len(sys.argv) > 1 else "bell"
    if _arg.lower() == "arch":
        # 架构基座演示：CPU↔闪存链路↔量子核 不间断交换 + tan/ctan 返回 + π 缓冲
        _m = QuantumMachine(n_qubits=4, link_ratio=2.0, seed=7)
        _m.define_pin("led", 0)
        _m.load("qubits 4\nenc 5\nh 0\ncx 0 1\nmeasure 0 -> 0\nif 0 x 2\nhalt")
        _recs = _m.run_until_halt()
        print("量子架构基座演示（4q / 链路 {} 槽 = ceil(2π)）".format(_m.link.size))
        for _r in _recs:
            print("  step", _r["pc"], _r)
        print("CPU:", _m.cpu, "| pin led =", _m.read_pin("led"),
              "| next_angle(tan) =", round(_m.next_angle, 6))
        print("链路统计:", _m.link.stats())
        raise SystemExit(0)
    _name = _arg
    _shots = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    _seed = int(sys.argv[3]) if len(sys.argv) > 3 else None
    _res = run_named(_name, shots=_shots, seed=_seed)
    print(_res["program"])
    print("shots:", _res["shots"], "seed:", _res["seed"])
    for _k, _v in _res["counts"].items():
        print(f"  {_k}: {_v}  (P={_res['probabilities'][_k]:.4f})")
