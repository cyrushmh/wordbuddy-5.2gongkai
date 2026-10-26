"""qudit（d 级量子系统 / 多位元）的经典模拟：同位能级散逸 + log 值交换。

诚实定位（与 native/quantum.py 同一红线：纯软件模拟、零依赖、不接硬件）
----------------------------------------------------------------------
- **qudit = d 级量子系统**（d=2 即 qubit，d=3 即 qutrit，…）。单 qudit 的信息容量
  为 **log2(d) 比特**——这是真实的量子信息事实（Nielsen & Chuang §4/§8），不是臆造：
  d=3 → log2(3)≈1.585 bit，d=5 → log2(5)≈2.322 bit。
- **「同位能级散逸」= 同一物理位（同一 site）内相邻能级之间的耗散**：
  * 振幅阻尼（amplitude damping，对应 T1 能量弛豫）：|k> → |k-1> 逐级衰减，
    用 Kraus 算符在**密度矩阵**上演化（耗散非酉，纯态→混态，故必须用 ρ 而非态矢量）；
  * 相位阻尼（dephasing，对应 T2）：非对角元按 |i-j| 衰减。
  二者是标准开放量子系统通道（Nielsen & Chuang §8.3），此处为经典数值实现。
- **「log 值交换」= 以 log2(d) 比特/符号的容量承载经典值**：把值编码进 qudit 的能级
  分布（对数幅度编码，中心在 μ=log2(value)），经耗散信道「传输」后再解码。散逸侵蚀
  编码值（能量向低能级泄漏 → 解码值下漂），本模块**诚实量化**这种损失，不宣称量子优势。

不做 / 不臆造
-------------
- 不接真量子硬件、不联网、不调云量子服务；纯标准库（不用 numpy）。
- 不声称「量子位宽阶梯」：qudit 的「多位元」是 **log2(d) 比特容量**，与经典位宽是
  不同轴；不把 d 级系统硬说成「d 比特」（那会把 d 级当二进制，是对量子信息的误读）。
- 耗散为**简化的单步均匀衰减模型**，不建模真实器件的 T1/T2 频变、串扰与门误差谱。
"""

from __future__ import annotations

import cmath
import math
import random

__all__ = [
    "QuditError", "MAX_D", "MAX_QUDITS", "SUPPORTED_WIDTHS",
    "capacity_bits",
    "density_from_pure", "dft_matrix", "shift_matrix", "phase_matrix",
    "apply_unitary", "amplitude_damping", "dephasing",
    "purity", "fidelity_pure", "probabilities", "measure",
    "encode_log_amplitudes", "decode_log_value", "log_value_link",
    "dissipation_sweep", "exchange_integer",
    "QuditRegister", "register_report",
    "register_roundtrip", "register_experiment", "register_experiment_plot",
    "dimension_profile", "elevate_bits", "reduce_bits",
    "bit_convert", "bit_convert_table",
    "qudit_report", "qudit_probe", "capabilities",
]

# 单 qudit 能级数上限：d×d 复矩阵，纯 Python 足够（d=8 → 64 复数）。
MAX_D = 8
# 多 qudit 整数交换的 qudit 数上限（d**n 才不爆；d=3,n=12 → 3^12≈53 万，仅作值域说明）。
MAX_QUDITS = 12
# 多位元寄存器支持的经典位宽（结合 PiLink 内存交换参数后覆盖 8/16/64/128 位元）。
SUPPORTED_WIDTHS = (8, 16, 64, 128)


class QuditError(Exception):
    """qudit 模拟的输入/形状错误。"""


# ───────────────────────── 复数矩阵原语（纯 Python） ─────────────────────────

def _zeros(d):
    return [[0j] * d for _ in range(d)]


def _eye(d):
    return [[1 + 0j if i == j else 0j for j in range(d)] for i in range(d)]


def _dag(a):
    """共轭转置 a†。"""
    d = len(a)
    return [[a[j][i].conjugate() for j in range(d)] for i in range(d)]


def _mul(a, b):
    d = len(a)
    out = _zeros(d)
    for i in range(d):
        ai = a[i]
        oi = out[i]
        for k in range(d):
            aik = ai[k]
            if aik == 0:
                continue
            bk = b[k]
            for j in range(d):
                oi[j] += aik * bk[j]
    return out


def _clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def _check_d(d):
    if not isinstance(d, int) or d < 2:
        raise QuditError(f"能级数 d 必须为 >=2 的整数，收到 {d!r}")
    if d > MAX_D:
        raise QuditError(f"能级数 d={d} 超过上限 MAX_D={MAX_D}（d² 复矩阵，纯 Python）")


# ───────────────────────── 态与门 ─────────────────────────

def capacity_bits(d):
    """单 qudit 的信息容量（比特）= log2(d)。"""
    _check_d(d)
    return math.log2(d)


def density_from_pure(amps):
    """由纯态振幅 α（长度 d）构造密度矩阵 ρ=|ψ><ψ|，返回 d×d 复数矩阵。"""
    d = len(amps)
    _check_d(d)
    norm = math.sqrt(sum(abs(a) ** 2 for a in amps))
    if norm <= 0:
        raise QuditError("振幅全零，无法归一化")
    a = [complex(x) / norm for x in amps]
    return [[a[i] * a[j].conjugate() for j in range(d)] for i in range(d)]


def dft_matrix(d):
    """d 级广义 Hadamard（离散傅里叶）：U_jk = ω^{jk}/√d，ω=e^{2πi/d}（酉）。"""
    _check_d(d)
    w = cmath.exp(2j * math.pi / d)
    s = 1.0 / math.sqrt(d)
    return [[s * (w ** ((j * k) % d)) for k in range(d)] for j in range(d)]


def shift_matrix(d):
    """循环移位门 X_d：|k> → |(k+1) mod d>（酉，置换）。"""
    _check_d(d)
    m = _zeros(d)
    for k in range(d):
        m[(k + 1) % d][k] = 1 + 0j
    return m


def phase_matrix(d):
    """广义 Z_d = diag(1, ω, ω², …, ω^{d-1})，ω=e^{2πi/d}（酉）。"""
    _check_d(d)
    w = cmath.exp(2j * math.pi / d)
    m = _zeros(d)
    for k in range(d):
        m[k][k] = w ** k
    return m


def apply_unitary(rho, u):
    """ρ → U ρ U†。"""
    return _mul(_mul(u, rho), _dag(u))


# ───────────────────────── 同位能级散逸（Kraus 通道） ─────────────────────────

def _apply_kraus(rho, kops):
    d = len(rho)
    out = _zeros(d)
    for k in kops:
        t = _mul(_mul(k, rho), _dag(k))
        for i in range(d):
            oi = out[i]
            ti = t[i]
            for j in range(d):
                oi[j] += ti[j]
    return out


def amplitude_damping(rho, gamma):
    """振幅阻尼（T1 能量弛豫）：相邻能级 |k>→|k-1> 以概率 γ 均匀衰减。

    Kraus：K0 = |0><0| + √(1-γ)Σ_{k≥1}|k><k|；A_k = √γ |k-1><k|（k=1..d-1）。
    Σ K†K = I（严格 CPTP），迹保持。
    """
    d = len(rho)
    _check_d(d)
    g = _check_prob(gamma, "gamma")
    k0 = _zeros(d)
    k0[0][0] = 1 + 0j
    for k in range(1, d):
        k0[k][k] = math.sqrt(1 - g)
    kops = [k0]
    for k in range(1, d):
        a = _zeros(d)
        a[k - 1][k] = math.sqrt(g)
        kops.append(a)
    return _apply_kraus(rho, kops)


def dephasing(rho, lam):
    """广义相位阻尼（T2）：ρ' = (1-λ)ρ + λ Z_d ρ Z_d†，非对角元按 |i-j| 衰减。"""
    d = len(rho)
    _check_d(d)
    lam = _check_prob(lam, "lambda")
    k0 = [[math.sqrt(1 - lam) if i == j else 0j for j in range(d)] for i in range(d)]
    z = phase_matrix(d)
    k1 = [[math.sqrt(lam) * z[i][j] for j in range(d)] for i in range(d)]
    return _apply_kraus(rho, [k0, k1])


def _check_prob(x, name):
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise QuditError(f"{name} 必须为 [0,1] 实数，收到 {x!r}")
    if v < 0 or v > 1:
        raise QuditError(f"{name} 必须在 [0,1]，收到 {v}")
    return v


# ───────────────────────── 观测量 ─────────────────────────

def purity(rho):
    """纯度 Tr(ρ²) ∈ (0,1]：纯态=1，完全混态=1/d。"""
    return abs(sum(rho[i][j] * rho[j][i] for i in range(len(rho)) for j in range(len(rho)))).real


def probabilities(rho):
    """各能级占据概率（对角元实部，已归一）。"""
    return [max(0.0, rho[k][k].real) for k in range(len(rho))]


def fidelity_pure(rho, amps):
    """纯态 |ψ> 与 ρ 的保真度 <ψ|ρ|ψ>（∈[0,1]）。"""
    d = len(rho)
    norm = math.sqrt(sum(abs(a) ** 2 for a in amps))
    a = [complex(x) / norm for x in amps]
    s = 0j
    for i in range(d):
        for j in range(d):
            s += a[i].conjugate() * rho[i][j] * a[j]
    return max(0.0, min(1.0, s.real))


def measure(rho, rng):
    """按 Born 规则采样能级 k（概率=对角元），并塌缩为 |k><k|；返回 k。

    就地修改 rho（塌缩）。随机源须为 random.Random 以便复现。
    """
    p = probabilities(rho)
    tot = sum(p)
    if tot <= 0:
        raise QuditError("概率全零，无法测量")
    r = rng.random() * tot
    acc = 0.0
    k = len(p) - 1
    for i, pi in enumerate(p):
        acc += pi
        if r <= acc:
            k = i
            break
    # 塌缩
    d = len(rho)
    for i in range(d):
        for j in range(d):
            rho[i][j] = 1 + 0j if (i == k and j == k) else 0j
    return k


# ───────────────────────── log 值交换 ─────────────────────────

def encode_log_amplitudes(value, d, sigma=0.6):
    """把正实数 value 编成 d 级对数幅度态：α_k ∝ exp(-(k-μ)²/(2σ²))，μ=log2(value)。

    value 的有效范围约 [1, 2^(d-1)]（μ∈[0,d-1]，越界截断）。
    """
    _check_d(d)
    if value <= 0:
        raise QuditError("log 值交换要求 value > 0")
    s = float(sigma)
    if s <= 0:
        raise QuditError("sigma 必须 > 0")
    mu = math.log2(value)
    mu = 0.0 if mu < 0 else (float(d - 1) if mu > d - 1 else mu)
    amps = [math.exp(-((k - mu) ** 2) / (2 * s * s)) for k in range(d)]
    n = math.sqrt(sum(x * x for x in amps))
    return [complex(x / n) for x in amps]


def decode_log_value(rho):
    """解码：v̂ = 2^{平均能级}，平均能级 = Σ k·p_k。"""
    p = probabilities(rho)
    mean_k = sum(k * p[k] for k in range(len(p)))
    return 2.0 ** mean_k


def log_value_link(value, d, gamma=0.0, lam=0.0, sigma=0.6):
    """log 值交换单链路：编码 → 经同位能级散逸（T1 γ + T2 λ）→ 解码。

    返回 dict：value / encoded(d=2 理想解码值) / decoded / fidelity / purity /
    capacity_bits / levels。
    """
    amps = encode_log_amplitudes(value, d, sigma)
    rho = density_from_pure(amps)
    ideal = decode_log_value(rho)  # γ=λ=0 时的理想解码
    if gamma:
        rho = amplitude_damping(rho, gamma)
    if lam:
        rho = dephasing(rho, lam)
    return {
        "value": float(value),
        "ideal": ideal,
        "decoded": decode_log_value(rho),
        "fidelity": fidelity_pure(rho, amps),
        "purity": purity(rho),
        "capacity_bits": capacity_bits(d),
        "levels": d,
        "gamma": float(gamma),
        "lambda": float(lam),
    }


def dissipation_sweep(d=5, value=6.0, gammas=None, lam=0.0, sigma=0.6):
    """固定 value、扫 γ（T1）的解码值/保真度/纯度曲线（展示散逸侵蚀 log 值）。"""
    if gammas is None:
        gammas = [0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
    return [log_value_link(value, d, gamma=g, lam=lam, sigma=sigma) for g in gammas]


def exchange_integer(value, n_qudits, d, gamma=0.0, seed=0):
    """把整数 value 以 n_qudits 个 d 级 qudit（每个 log2(d) 比特）编码、经散逸、测量解码。

    返回 dict：value / decoded / capacity_bits / digit_errors / ber（按符号误码率）。
    诚实说明：散逸使能级向低泄漏 → 解码下漂；ber 反映「log 值交换」在耗散信道下的损失。
    """
    _check_d(d)
    if not isinstance(n_qudits, int) or n_qudits < 1:
        raise QuditError("n_qudits 必须为 >=1 的整数")
    if n_qudits > MAX_QUDITS:
        raise QuditError(f"n_qudits={n_qudits} 超过上限 MAX_QUDITS={MAX_QUDITS}")
    cap = d ** n_qudits
    if not (0 <= value < cap):
        raise QuditError(f"value={value} 超出 {n_qudits} 个 {d} 级 qudit 的值域 [0,{cap})")
    rng = random.Random(seed)
    # 分解为 d 进制各位（高位在前）
    digits = []
    v = value
    for _ in range(n_qudits):
        digits.append(v % d)
        v //= d
    digits.reverse()
    out_digits = []
    for dig in digits:
        amps = [0j] * d
        amps[dig] = 1 + 0j
        rho = density_from_pure(amps)
        if gamma:
            rho = amplitude_damping(rho, gamma)
        out_digits.append(measure(rho, rng))
    decoded = 0
    for od in out_digits:
        decoded = decoded * d + od
    errs = sum(1 for a, b in zip(digits, out_digits) if a != b)
    return {
        "value": int(value),
        "decoded": int(decoded),
        "digits_in": digits,
        "digits_out": out_digits,
        "n_qudits": n_qudits,
        "levels": d,
        "capacity_bits": n_qudits * math.log2(d),
        "digit_errors": errs,
        "ber": errs / n_qudits,
        "gamma": float(gamma),
    }


# ───────────────────────── 降维升维位元转化 ─────────────────────────
#
# 把 W 位经典整数（每符号 2 维 = 1 比特）**升维**成 N 个 d 级 qudit（每符号 d 维），
# 再**降维**回位元。两条主干：
#   * 精确离散升维（exact）：value → base-d 按位展开（digit 升维）↔ 测量解码。
#     这是同构映射 R∘E = I，γ=0 时严格无损、可互逆；
#   * 量化升维（quantized）：每符号以 |dig> 纯态经同位能级散逸（T1 γ）+ 测量塌缩，
#     诚实量化「升维后再降维」在耗散信道下的符号损失（与 register_roundtrip 同口径）。
#
# 维度画像的诚实指标：
#   * bits_per_carrier = log2(d)        —— 升维比：每 qudit 承载的经典比特数；
#   * reduction_factor = W / N          —— 降维比：实际每 qudit 摊到的经典比特（≤ bits_per_carrier）；
#   * joint_dimension  = d**N           —— 联合态维数，仅作诚实声明，**绝不物化**。

def dimension_profile(width_bits, d=8):
    """W 位经典整数 → N 个 d 级 qudit 的维度画像（升维/降维的量化指标）。

    返回 dict：width_bits / levels(d) / n_qudits(N) / per_carrier_bits(log2(d)) /
    total_capacity(N·log2(d)) / bits_per_carrier(升维比) / reduction_factor(降维比) /
    joint_dimension(d**N, 不物化) / waste_bits(余量) / supported。
    """
    _check_d(d)
    if not isinstance(width_bits, int) or width_bits < 1:
        raise QuditError(f"位宽须为 >=1 的整数，收到 {width_bits!r}")
    per = capacity_bits(d)                              # log2(d) bit/qudit
    n = max(1, math.ceil(width_bits / per))
    total = n * per
    return {
        "width_bits": int(width_bits),
        "levels": int(d),
        "n_qudits": n,
        "per_carrier_bits": per,
        "total_capacity_bits": total,
        "bits_per_carrier": per,                        # 升维比：每符号承载比特
        "reduction_factor": width_bits / n,             # 降维比：实际每符号摊到比特
        "joint_dimension": d ** n,                      # 仅声明，不物化
        "waste_bits": total - width_bits,               # ceil 余量
        "supported": width_bits in SUPPORTED_WIDTHS,
    }


def elevate_bits(value, n_qudits, d):
    """精确离散升维：把整数 value 以 base-d 按位展开成 N 个 d 级符号（高位在前）。

    value 须 ∈ [0, d**N)；返回长度 N 的 digit 列表。这是「低维位串 → 高维符号」的
    升维：W 个比特被重新表达为 N 个 d 级 qudit（每符号载 log2(d) 比特）。
    """
    _check_d(d)
    if not isinstance(n_qudits, int) or n_qudits < 1:
        raise QuditError("n_qudits 必须为 >=1 的整数")
    cap = d ** n_qudits
    if not (0 <= int(value) < cap):
        raise QuditError(f"value={value} 超出 {n_qudits} 个 d={d} qudit 的值域 [0,{cap})")
    v = int(value)
    digits = []
    for _ in range(n_qudits):
        digits.append(v % d)
        v //= d
    digits.reverse()
    return digits


def reduce_bits(digits, d):
    """精确降维：把 N 个 d 级符号按 base-d 解码回整数（测量解码的同构逆）。

    R∘E = I：reduce_bits(elevate_bits(value)) == value（γ=0 严格成立）。
    """
    _check_d(d)
    out = 0
    for dig in digits:
        if not isinstance(dig, int) or not (0 <= dig < d):
            raise QuditError(f"digit {dig!r} 须为 [0,{d}) 整数")
        out = out * d + dig
    return out


def bit_convert(value, width_bits, d=8, gamma=0.0, lam=0.0, seed=0):
    """降维升维位元转化的端到端封装：升维 →（可选耗散+测量）→ 降维。

    - γ=λ=0：精确离散升维 ↔ 降维，R∘E=I 严格无损（decoded==value, ber==0）。
    - γ>0：每符号 |dig> 纯态经同位能级散逸 + 测量塌缩，诚实量化符号损失
      （解码不高于原值、ber≥0），与 register_roundtrip 同口径。

    返回 dict：value / decoded / n_qudits / digits_in / digits_out / digit_errors /
    ber / capacity_bits / bits_per_carrier / reduction_factor / joint_dimension /
    levels / gamma / lambda / lossless(R∘E==I 标志)。

    诚实边界：升维/降维的精确部分是同构，无信息增益；耗散路径仅量化损失，
    不宣称量子优势；joint_dimension 仅声明、不物化。
    """
    _check_d(d)
    prof = dimension_profile(width_bits, d)
    n = prof["n_qudits"]
    digits = elevate_bits(value, n, d)
    rng = random.Random(seed)
    if gamma or lam:
        out_digits = []
        for dig in digits:
            rho = density_from_pure([1 + 0j if k == dig else 0j for k in range(d)])
            if gamma:
                rho = amplitude_damping(rho, gamma)
            if lam:
                rho = dephasing(rho, lam)
            out_digits.append(measure(rho, rng))
    else:
        out_digits = list(digits)                       # 精确降维：符号原样
    decoded = reduce_bits(out_digits, d)
    errs = sum(1 for a, b in zip(digits, out_digits) if a != b)
    return {
        "value": int(value),
        "decoded": int(decoded),
        "n_qudits": n,
        "digits_in": digits,
        "digits_out": out_digits,
        "digit_errors": errs,
        "ber": errs / n,
        "capacity_bits": prof["total_capacity_bits"],
        "bits_per_carrier": prof["bits_per_carrier"],
        "reduction_factor": prof["reduction_factor"],
        "joint_dimension": prof["joint_dimension"],
        "levels": d,
        "gamma": float(gamma),
        "lambda": float(lam),
        "lossless": (errs == 0 and decoded == int(value)),
    }


def bit_convert_table(widths=None, d=8):
    """全位宽维度画像表：对每个位宽给出升维/降维的量化指标（供 CLI --table）。

    返回 list[dict]：width_bits / n_qudits / per_carrier_bits / total_capacity_bits /
    bits_per_carrier / reduction_factor / joint_dimension / waste_bits。
    """
    if widths is None:
        widths = SUPPORTED_WIDTHS
    rows = []
    for w in widths:
        p = dimension_profile(w, d)
        rows.append({
            "width_bits": p["width_bits"],
            "n_qudits": p["n_qudits"],
            "per_carrier_bits": p["per_carrier_bits"],
            "total_capacity_bits": p["total_capacity_bits"],
            "bits_per_carrier": p["bits_per_carrier"],
            "reduction_factor": p["reduction_factor"],
            "joint_dimension": p["joint_dimension"],
            "waste_bits": p["waste_bits"],
            "supported": p["supported"],
        })
    return rows


# ───────────────────────── 自检报告 / 能力面 ─────────────────────────

def capabilities():
    """返回本模块的能力面与诚实边界（供 GUI/CLI/报告消费）。"""
    return {
        "module": "native/qudit.py",
        "levels_max": MAX_D,
        "qudits_max": MAX_QUDITS,
        "capacity_formula": "log2(d) bits/qudit",
        "gates": ["DFT_d", "X_d(shift)", "Z_d(phase)"],
        "channels": ["amplitude_damping(T1,γ)", "dephasing(T2,λ)"],
        "log_value_exchange": True,
        "register_widths": list(SUPPORTED_WIDTHS),
        "register_memory_exchange": "PiLink(CPU↔量子核 π 链路缓冲，native/quantum.py)",
        "register_roundtrip": True,
        "register_experiment": True,
        "bit_conversion": True,
        "pure_stdlib": True,
        "boundaries": [
            "经典数值模拟 qudit（d 级），非真实量子硬件",
            "多位元=log2(d) 比特容量，非 d 比特（不混同经典位宽）",
            "耗散为单步均匀衰减模型，不含真实 T1/T2 频变与串扰",
            "log 值交换为对数幅度编码 + 散散信道，不宣称量子优势",
            "多位元寄存器不物化 d**N 联合态；经 PiLink 内存交换参数逐 qudit 交换",
        ],
    }


def qudit_probe(seed=0):
    """紧凑数值自检：酉性 / CPTP 迹保持 / 散逸纯度衰减 / log 值单调下漂。"""
    out = {}
    # 1) 酉性：DFT_d · DFT_d† = I
    for d in (2, 3, 5):
        u = dft_matrix(d)
        prod = _mul(u, _dag(u))
        err = max(abs(prod[i][j] - (1 if i == j else 0)) for i in range(d) for j in range(d))
        out[f"dft_unitary_d{d}"] = err < 1e-9
    # 2) 振幅阻尼迹保持（CPTP）
    rho = density_from_pure([1 / math.sqrt(3), 1 / math.sqrt(3), 1 / math.sqrt(3)])
    tr = sum(amplitude_damping(rho, 0.3)[k][k].real for k in range(3))
    out["ad_trace_preserved"] = abs(tr - 1.0) < 1e-9
    # 3) 散逸使纯度下降
    pure0 = purity(rho)
    pure1 = purity(amplitude_damping(rho, 0.5))
    out["purity_decays"] = pure1 < pure0 + 1e-12
    # 4) log 值随 γ 单调下漂（0→1 全幅）
    vals = [log_value_link(6.0, 5, gamma=g)["decoded"] for g in (0.0, 0.25, 0.5, 1.0)]
    out["log_value_monotone_decay"] = all(vals[i] >= vals[i + 1] - 1e-9 for i in range(len(vals) - 1))
    out["log_value_samples"] = [round(v, 4) for v in vals]
    # 5) 无耗散时 log 值往返精度
    lv = log_value_link(6.0, 5, gamma=0.0)
    out["lossless_roundtrip_err"] = abs(lv["decoded"] - 6.0)
    # 6) 整数交换无损时全对
    ex = exchange_integer(41, 3, 4, gamma=0.0, seed=seed)
    out["integer_lossless_exact"] = ex["decoded"] == 41 and ex["ber"] == 0.0
    # 7) 多位元寄存器：分解覆盖名义位宽 + 内存交换参数记录交换
    reg = QuditRegister(width_bits=64, d=8)
    reg.encode(0, 6.0)
    reg.apply_gate(0, "dft")
    reg.apply_dissipation(0, gamma=0.3)
    reg.decode(0)
    out["register_width_supported"] = (
        reg.total_capacity >= 64.0
        and reg.link.total_writes >= 3
        and all(QuditRegister(width_bits=w, d=8).total_capacity >= float(w) for w in SUPPORTED_WIDTHS))
    # 8) 寄存器级多位元往返：γ=0 无损时应全等（覆盖 N 个 qudit 经 PiLink 逐交换）
    rt = register_roundtrip(width_bits=64, value=41, d=8, gamma=0.0, seed=seed)
    out["register_roundtrip_lossless"] = (
        rt["ber"] == 0.0 and rt["decoded"] == 41
        and rt["link_writes"] == 2 * rt["n_qudits"])
    # 9) 降维升维位元转化：精确离散升维↔降维同构（R∘E=I，γ=0 无损）
    invertible = True
    for n, dd in ((3, 2), (4, 3), (2, 5), (2, 8)):
        cap = dd ** n
        for v in range(cap):
            if reduce_bits(elevate_bits(v, n, dd), dd) != v:
                invertible = False
                break
        if not invertible:
            break
    out["dim_reduce_elevate_invertible"] = invertible
    # 10) 维度画像不变量：降维比 ≤ 升维比；总容量 ≥ 名义位宽；联合态维数一致（不物化）
    invariant = True
    for w in SUPPORTED_WIDTHS:
        p = dimension_profile(w, 8)
        if not (p["reduction_factor"] <= p["bits_per_carrier"] + 1e-12):
            invariant = False
            break
        if not (p["total_capacity_bits"] >= w - 1e-12):
            invariant = False
            break
        if p["joint_dimension"] != 8 ** p["n_qudits"]:
            invariant = False
            break
        # 边界值（最大值）升维降维往返
        top = (8 ** p["n_qudits"]) - 1
        if reduce_bits(elevate_bits(top, p["n_qudits"], 8), 8) != top:
            invariant = False
            break
    out["dim_profile_invariant"] = invariant
    out["all_pass"] = all(v is True for k, v in out.items() if k.endswith(("_unitary_d2", "_unitary_d3", "_unitary_d5")) or k in (
        "ad_trace_preserved", "purity_decays", "log_value_monotone_decay",
        "integer_lossless_exact", "register_width_supported", "register_roundtrip_lossless",
        "dim_reduce_elevate_invertible", "dim_profile_invariant"))
    return out


def qudit_report(d=5, value=6.0):
    """文本化的只读报告：能力面 + log 值交换在散逸下的漂移表。"""
    lines = []
    cap = capabilities()
    lines.append("== qudit 多位元模拟（同位能级散逸 + log 值交换）==")
    lines.append(f"单 qudit 容量：log2(d) 比特；d 上限 {cap['levels_max']}，qudit 数上限 {cap['qudits_max']}")
    lines.append(f"门：{', '.join(cap['gates'])}；通道：{', '.join(cap['channels'])}")
    lines.append(f"log 值交换（d={d}，理想值 {value}）：γ(T1) 越大解码值越下漂——")
    lines.append(f"{'γ':>6} {'解码值':>10} {'保真度':>8} {'纯度':>8}")
    for rec in dissipation_sweep(d=d, value=value):
        lines.append(f"{rec['gamma']:>6.2f} {rec['decoded']:>10.4f} "
                     f"{rec['fidelity']:>8.4f} {rec['purity']:>8.4f}")
    lines.append("诚实边界：经典数值模拟 qudit，非量子硬件；多位元=log2(d) 比特容量而非 d 比特；"
                 "耗散为单步均匀衰减模型。")
    return "\n".join(lines)


# ───────────────────────── 多位元寄存器（结合内存交换参数 PiLink） ─────────────────────────

class QuditRegister:
    """多位元 qudit 寄存器：N 个 d 级 qudit 经 π 链路（内存交换参数）不间断交换。

    这是「量子架构多位元支持」的扩展：单 qudit 容量 log2(d) 比特，N 个并联即
    N·log2(d) 比特。为覆盖经典位宽 8/16/64/128，取 d=8（3 bit/qudit），
    N = ceil(位宽 / 3)。

    **为什么必须结合「内存交换参数」**：N 个 qudit 的联合态维数 = d**N
    （128 位 → 8**43 ≈ 2**129），绝不可物化为单一密度矩阵。本寄存器每个 qudit
    仅维持自身 d×d 局部态，CPU↔量子核的每一次交换（encode/gate/dissipation/measure）
    都经 ``PiLink`` 环形缓冲记录——这正是 ``native/quantum.py`` 的「内存交换参数」
    落点：状态以分块方式经链路交换，而非一次性铺满内存。

    诚实边界：不物化联合态（仅逐 qudit 局部态）；寄存器容量为分解后总容量；
    散逸按单 qudit 局部施加；不声称量子优势。
    """

    def __init__(self, width_bits=64, d=8, link_ratio=2.0):
        if d < 2 or d > MAX_D:
            raise QuditError(f"能级数 d 须 ∈[2,{MAX_D}]，收到 {d}")
        if width_bits not in SUPPORTED_WIDTHS:
            raise QuditError(f"位宽须为 {SUPPORTED_WIDTHS} 之一，收到 {width_bits}")
        self.d = d
        self.width_bits = int(width_bits)
        self.per = capacity_bits(d)                       # 每 qudit log2(d) 比特
        self.n = max(1, math.ceil(self.width_bits / self.per))
        self.total_capacity = self.n * self.per           # 总容量（比特）
        zero = [1 + 0j if k == 0 else 0j for k in range(d)]
        # 每个 qudit 维持自身 d×d 局部密度矩阵（从不拼成 d**N 联合矩阵）
        self.rho = [density_from_pure(zero) for _ in range(self.n)]
        self.cpu = [0] * self.n                           # 经典控制寄存器（每 qudit 一 bit）
        from .quantum import PiLink                        # 内存交换参数：CPU↔量子核链路缓冲
        self.link = PiLink(link_ratio)

    def _qi(self, qidx):
        if not isinstance(qidx, int) or not (0 <= qidx < self.n):
            raise QuditError(f"qudit 索引须 ∈[0,{self.n})，收到 {qidx!r}")
        return qidx

    def exchange(self, qidx, kind, payload=None):
        """把一次 CPU↔量子核交换写入 π 链路缓冲（内存交换参数的落点）。"""
        rec = {"qudit": int(qidx), "op": kind}
        if payload:
            for k, v in payload.items():
                if k not in ("qudit", "op"):
                    rec[k] = v
        self.link.push(rec)

    def apply_gate(self, qidx, gate):
        idx = self._qi(qidx)
        g = {"dft": dft_matrix, "shift": shift_matrix, "phase": phase_matrix}.get(gate)
        if g is None:
            raise QuditError(f"未知门 {gate!r}（可选 dft/shift/phase）")
        self.rho[idx] = apply_unitary(self.rho[idx], g(self.d))
        self.exchange(idx, "gate", {"gate": gate})

    def apply_dissipation(self, qidx, gamma=0.0, lam=0.0):
        idx = self._qi(qidx)
        r = self.rho[idx]
        if gamma:
            r = amplitude_damping(r, gamma)
        if lam:
            r = dephasing(r, lam)
        self.rho[idx] = r
        self.exchange(idx, "dissipation", {"gamma": float(gamma), "lambda": float(lam)})

    def encode(self, qidx, value):
        idx = self._qi(qidx)
        self.rho[idx] = density_from_pure(encode_log_amplitudes(value, self.d))
        self.exchange(idx, "encode", {"value": float(value)})

    def decode(self, qidx):
        return decode_log_value(self.rho[self._qi(qidx)])

    def purity(self, qidx):
        return purity(self.rho[self._qi(qidx)])

    def measure(self, qidx, rng):
        """按 Born 规则测量并塌缩 qudit[qidx]，经 π 链路记录交换（内存交换参数落点）。

        rng 须为 random.Random 以便复现；就地修改 ρ（塌缩为 |k><k|）。
        """
        idx = self._qi(qidx)
        k = measure(self.rho[idx], rng)
        self.exchange(idx, "measure", {"outcome": int(k)})
        return k

    def report(self):
        ls = []
        ls.append("== qudit 多位元寄存器（结合 PiLink 内存交换参数）==")
        ls.append(f"名义位宽：{self.width_bits} bit")
        ls.append(f"分解：{self.n} 个 d={self.d} 级 qudit × log2(d)={self.per:.3f} bit/qudit")
        ls.append(f"寄存器总容量 = {self.total_capacity:.3f} bit（≥ 名义位宽 {self.width_bits} bit）")
        ls.append(f"内存交换参数：PiLink(size={self.link.size}) 缓冲 CPU↔量子核每次交换；"
                  f"联合态维数 = {self.d ** self.n}（不物化为单一矩阵）")
        ls.append(f"当前链路：写入 {self.link.total_writes} 次（覆盖 {self.link.overwrites} 次）")
        return "\n".join(ls)


def register_report(width_bits=64, d=8, gamma=0.0, lam=0.0, link_ratio=2.0, demo_value=6.0):
    """多位元寄存器报告：位宽分解 + 内存交换参数 + 一个 qudit 的 log 值交换演示（散逸下漂）。

    演示项把经典值编进 0 号 qudit，经同位能级散逸（γ/λ），再解码——量化
    「内存交换承载的 log 值」在耗散信道下的损失；链路统计如实记录交换次数。
    """
    reg = QuditRegister(width_bits=width_bits, d=d, link_ratio=link_ratio)
    ls = [reg.report()]
    reg.encode(0, demo_value)
    ideal = reg.decode(0)
    reg.apply_dissipation(0, gamma=gamma, lam=lam)
    decoded = reg.decode(0)
    ls.append(f"演示 qudit[0]：编码值 {demo_value} → 理想解码 {ideal:.4f} → "
              f"γ={gamma},λ={lam} 散逸后解码 {decoded:.4f}（下漂 {ideal - decoded:.4f}）")
    ls.append(f"链路统计：{reg.link.stats()}")
    ls.append("诚实边界：经典数值模拟；不物化 {0}**{1} 联合态；多位元=log2(d) 比特容量；"
              "耗散为单步均匀衰减模型。".format(reg.d, reg.n))
    return "\n".join(ls)


# ───────────────────────── 寄存器级多位元往返 + 可复现耗散实验 ─────────────────────────

def register_roundtrip(width_bits=64, value=0, d=8, gamma=0.0, lam=0.0, seed=0):
    """寄存器级多位元往返：用 QuditRegister 把整数 value 跨 N 个 d 级 qudit 做 digit 编码，
    经 PiLink 内存交换参数（每 qudit 一次 encode 交换）+ 可选「同位能级散逸（T1 γ / T2 λ）」
    + 测量塌缩，再按 d 进制解码回整数。

    这是把 0032 批的「多位元寄存器」抽象真正跑通端到端：值铺到全部 N 个 qudit，
    CPU↔量子核的每一次交换都经 π 链路缓冲记录（status 如实），而非一次性物化 8^N 联合态。

    返回 dict：value / decoded / n_qudits / digits_in / digits_out / digit_errors /
    ber / capacity_bits / link_writes / levels / gamma / lambda。

    诚实说明：散逸 + 测量使符号向低能级泄漏 → 解码值不高于原值、ber≥0；γ=λ=0 且无测量
    扰动时（measure 在 γ=0 仍按 Born 规则采样，但纯态 |dig> 测量恒得 dig）应全等 ber=0。
    随机源须可复现（seed）。
    """
    reg = QuditRegister(width_bits=width_bits, d=d)
    cap = d ** reg.n
    if not (0 <= int(value) < cap):
        raise QuditError(f"value={value} 超出 {reg.n} 个 d={d} qudit 的值域 [0,{cap})")
    rng = random.Random(seed)
    v = int(value)
    digits = []
    for _ in range(reg.n):
        digits.append(v % d)
        v //= d
    digits.reverse()
    out_digits = []
    for i, dig in enumerate(digits):
        reg.rho[i] = density_from_pure([1 + 0j if k == dig else 0j for k in range(d)])
        reg.exchange(i, "encode", {"value": int(dig)})
        if gamma:
            reg.apply_dissipation(i, gamma=gamma, lam=lam)
        out_digits.append(reg.measure(i, rng))
    decoded = 0
    for od in out_digits:
        decoded = decoded * d + od
    errs = sum(1 for a, b in zip(digits, out_digits) if a != b)
    return {
        "value": int(value),
        "decoded": int(decoded),
        "n_qudits": reg.n,
        "digits_in": digits,
        "digits_out": out_digits,
        "digit_errors": errs,
        "ber": errs / reg.n,
        "capacity_bits": reg.total_capacity,
        "link_writes": reg.link.total_writes,
        "levels": d,
        "gamma": float(gamma),
        "lambda": float(lam),
    }


def register_experiment(width_bits=64, d=8, gammas=None, seed=0, n_samples=24):
    """可复现的寄存器级耗散实验：固定位宽，扫 γ（T1 振幅阻尼），每个 γ 跑 n_samples 次
    随机值，统计平均 / 最大符号误码率（BER）。固定 seed → 结果可复现，用于诚实量化
    「多位元寄存器在耗散信道下的损失」。

    返回 list[dict]：gamma / ber_mean / ber_max / n_samples / width_bits / levels / n_qudits。
    """
    if gammas is None:
        gammas = [0.0, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0]
    reg = QuditRegister(width_bits=width_bits, d=d)
    cap = d ** reg.n
    rows = []
    for g in gammas:
        bers = []
        for s in range(n_samples):
            rs = random.Random((seed * 1000003 + s) & 0x7fffffff)
            val = rs.randint(0, cap - 1)
            rt = register_roundtrip(width_bits, val, d=d, gamma=g,
                                   seed=(seed * 7919 + s) & 0x7fffffff)
            bers.append(rt["ber"])
        rows.append({
            "gamma": float(g),
            "ber_mean": sum(bers) / len(bers),
            "ber_max": max(bers),
            "n_samples": n_samples,
            "width_bits": width_bits,
            "levels": d,
            "n_qudits": reg.n,
        })
    return rows


def register_experiment_plot(width_bits=64, d=8, gammas=None, seed=0, n_samples=24,
                            out_path="register_dissipation.svg"):
    """把 register_experiment 的 BER-γ 曲线画成 **纯标准库 SVG**（无第三方依赖，不污染
    核心的 pure_stdlib 边界）。返回输出路径。

    注：刻意不依赖 matplotlib——核心 qudit 模拟保持零依赖，绘图同样零依赖。
    """
    rows = register_experiment(width_bits=width_bits, d=d, gammas=gammas,
                              seed=seed, n_samples=n_samples)
    nq = rows[0]["n_qudits"]
    W, H = 720, 420
    ml, mr, mt, mb = 64, 24, 36, 48          #  margins
    x0, y0 = ml, H - mb
    x1, y1 = W - mr, mt
    def sx(g):  # γ∈[0,1] → x
        return x0 + (x1 - x0) * (g / 1.0)
    def sy(b):  # BER∈[0,1] → y
        return y0 - (y0 - y1) * b
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="system-ui,Segoe UI,Helvetica,Arial" '
        f'font-size="12">',
        f'<rect width="{W}" height="{H}" fill="#0f1420"/>',
        f'<text x="{W / 2}" y="22" fill="#e6edf3" text-anchor="middle" '
        f'font-size="14">qudit 寄存器耗散实验（{width_bits} bit → {nq} 个 d={d} qudit）</text>',
    ]
    # 网格 + 轴
    for i in range(11):
        gy = y1 + (y0 - y1) * i / 10
        parts.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" '
                     f'stroke="#26303f" stroke-width="1"/>')
        parts.append(f'<text x="{x0 - 8}" y="{gy + 4:.1f}" fill="#8b98a9" '
                     f'text-anchor="end">{i / 10:.1f}</text>')
    for i in range(11):
        gx = x0 + (x1 - x0) * i / 10
        parts.append(f'<text x="{gx:.1f}" y="{y0 + 20}" fill="#8b98a9" '
                     f'text-anchor="middle">{i / 10:.1f}</text>')
    parts.append(f'<line x1="{x0}" y1="{y1}" x2="{x0}" y2="{y0}" stroke="#5a6b7f" '
                 f'stroke-width="1.5"/>')
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" stroke="#5a6b7f" '
                 f'stroke-width="1.5"/>')
    parts.append(f'<text x="{(x0 + x1) / 2}" y="{H - 10}" fill="#e6edf3" '
                 f'text-anchor="middle">γ (T1 振幅阻尼)</text>')
    parts.append(f'<text x="16" y="{(y0 + y1) / 2}" fill="#e6edf3" '
                 f'text-anchor="middle" transform="rotate(-90 16 {(y0 + y1) / 2})">'
                 f'符号误码率 BER</text>')

    def poly(vals, color, dash=""):
        pts = " ".join(f"{sx(r['gamma']):.1f},{sy(v):.1f}" for r, v in zip(rows, vals))
        sw = ' stroke-dasharray="6 4"' if dash else ""
        return (f'<polyline fill="none" stroke="{color}" stroke-width="2.5"{sw} '
                f'points="{pts}"/>'
                + "".join(f'<circle cx="{sx(r["gamma"]):.1f}" cy="{sy(v):.1f}" '
                          f'r="3" fill="{color}"/>' for r, v in zip(rows, vals)))

    parts.append(poly([r["ber_mean"] for r in rows], "#4cc9f0"))
    parts.append(poly([r["ber_max"] for r in rows], "#f72585", dash=True))
    parts.append(f'<text x="{x1 - 6}" y="{y1 + 16}" fill="#4cc9f0" text-anchor="end">'
                 f'平均 BER</text>')
    parts.append(f'<text x="{x1 - 6}" y="{y1 + 34}" fill="#f72585" text-anchor="end">'
                 f'最大 BER</text>')
    parts.append("</svg>")
    data = "\n".join(parts) + "\n"
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(data)
    return out_path

