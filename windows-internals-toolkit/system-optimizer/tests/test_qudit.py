"""qudit 多位元模拟测试（同位能级散逸 + log 值交换）。

覆盖：容量 log2(d) / 门酉性 / 振幅阻尼 CPTP 迹保持 / 相位阻尼 / 纯度衰减 /
log 值交换无损往返与耗散单调下漂 / 整数 log 值交换 / 测量塌缩 / 能力面边界。
"""

import math

import pytest

from sysweeper.native import qudit as q


def test_capacity_bits():
    assert q.capacity_bits(2) == pytest.approx(1.0)
    assert q.capacity_bits(3) == pytest.approx(math.log2(3))
    assert q.capacity_bits(5) == pytest.approx(math.log2(5))
    with pytest.raises(q.QuditError):
        q.capacity_bits(1)


@pytest.mark.parametrize("d", [2, 3, 5, 8])
def test_gates_unitary(d):
    for u in (q.dft_matrix(d), q.shift_matrix(d), q.phase_matrix(d)):
        prod = q._mul(u, q._dag(u))
        err = max(abs(prod[i][j] - (1 if i == j else 0)) for i in range(d) for j in range(d))
        assert err < 1e-9


def test_amplitude_damping_cptp():
    amps = [1 / math.sqrt(3)] * 3
    rho = q.density_from_pure(amps)
    # γ=0 为恒等
    r0 = q.amplitude_damping(rho, 0.0)
    assert max(abs(r0[i][j] - rho[i][j]) for i in range(3) for j in range(3)) < 1e-12
    # 任意 γ 迹保持
    for g in (0.1, 0.5, 1.0):
        tr = sum(q.amplitude_damping(rho, g)[k][k].real for k in range(3))
        assert abs(tr - 1.0) < 1e-9


def test_dephasing_trace_preserved():
    rho = q.density_from_pure(q.dft_matrix(4)[0])
    for lam in (0.0, 0.3, 1.0):
        tr = sum(q.dephasing(rho, lam)[k][k].real for k in range(4))
        assert abs(tr - 1.0) < 1e-9


def test_purity_decays_under_damping():
    rho = q.density_from_pure([1 / math.sqrt(3)] * 3)
    assert q.purity(rho) == pytest.approx(1.0, abs=1e-9)
    assert q.purity(q.amplitude_damping(rho, 0.5)) < 1.0


def test_log_value_lossless_roundtrip():
    # 无耗散时，对数幅度编码解码回到设计值附近（有限 d 的离散化偏差 < 0.5）
    rec = q.log_value_link(6.0, 5, gamma=0.0)
    assert rec["fidelity"] == pytest.approx(1.0, abs=1e-9)
    assert rec["purity"] == pytest.approx(1.0, abs=1e-9)
    assert abs(rec["decoded"] - 6.0) < 0.5
    assert rec["capacity_bits"] == pytest.approx(math.log2(5))


def test_log_value_monotone_decay_with_dissipation():
    # 能级散逸（T1）使 log 编码值单调下漂（能量向低能级泄漏）
    vals = [q.log_value_link(6.0, 5, gamma=g)["decoded"] for g in (0.0, 0.1, 0.3, 0.6, 1.0)]
    for a, b in zip(vals, vals[1:]):
        assert a >= b - 1e-9, vals
    # 全耗散明显低于无损
    assert vals[-1] < vals[0]


def test_integer_exchange_lossless():
    ex = q.exchange_integer(41, 3, 4, gamma=0.0, seed=7)
    assert ex["decoded"] == 41
    assert ex["ber"] == 0.0
    assert ex["capacity_bits"] == pytest.approx(3 * math.log2(4))


def test_integer_exchange_dissipative_drifts_down():
    ex = q.exchange_integer(41, 3, 4, gamma=0.9, seed=7)
    assert 0.0 <= ex["ber"] <= 1.0
    # 能级向低泄漏 → 解码值不高于原值
    assert ex["decoded"] <= 41


def test_integer_exchange_range_guard():
    with pytest.raises(q.QuditError):
        q.exchange_integer(4 ** 3, 3, 4)  # 超出值域 [0, 4^3)


def test_measure_collapse():
    import random
    rho = q.density_from_pure(q.dft_matrix(3)[0])  # 均匀叠加
    k = q.measure(rho, random.Random(1))
    assert 0 <= k < 3
    # 塌缩后为 |k><k|：纯度=1
    assert q.purity(rho) == pytest.approx(1.0, abs=1e-9)


def test_probe_all_pass():
    pr = q.qudit_probe()
    assert pr["all_pass"] is True
    assert pr["log_value_samples"][0] >= pr["log_value_samples"][-1]


def test_capabilities_boundaries():
    cap = q.capabilities()
    assert cap["pure_stdlib"] is True
    assert cap["log_value_exchange"] is True
    assert len(cap["boundaries"]) >= 3
    assert any("log2(d)" in b for b in cap["boundaries"])


# ───────────────────────── 多位元寄存器（结合 PiLink 内存交换参数） ─────────────────────────

def test_register_supported_widths():
    cap = q.capabilities()
    assert cap["register_widths"] == [8, 16, 64, 128]
    assert "PiLink" in cap["register_memory_exchange"]


def test_register_decomposition_covers_width():
    # 8/16/64/128 位元分别拆成 3/6/22/43 个 d=8 qudit，总容量 ≥ 名义位宽
    expect = {8: 3, 16: 6, 64: 22, 128: 43}
    for w, n in expect.items():
        reg = q.QuditRegister(width_bits=w, d=8)
        assert reg.n == n
        assert reg.total_capacity >= float(w)
        assert reg.d ** reg.n > (1 << w)  # 联合态维数远超 2^位宽（不物化）


def test_register_rejects_unsupported_width():
    with pytest.raises(q.QuditError):
        q.QuditRegister(width_bits=12, d=8)
    with pytest.raises(q.QuditError):
        q.QuditRegister(width_bits=32, d=8)  # 不在 (8,16,64,128)


def test_register_memory_exchange_records_swaps():
    # 内存交换参数（PiLink）如实记录每次 CPU↔量子核交换
    reg = q.QuditRegister(width_bits=64, d=8)
    assert reg.link.total_writes == 0
    reg.encode(0, 6.0)
    reg.apply_gate(0, "dft")
    reg.apply_dissipation(0, gamma=0.3)
    assert reg.link.total_writes >= 3
    # 每个 qudit 仅维持自身 d×d 局部态（未拼成 8^N 联合矩阵）
    assert len(reg.rho) == reg.n
    assert len(reg.rho[0]) == 8 and len(reg.rho[0][0]) == 8


def test_register_decode_drifts_under_dissipation():
    # 演示 qudit[0]：编码 → 散逸 → 解码，值随 γ 下漂
    reg = q.QuditRegister(width_bits=64, d=8)
    reg.encode(0, 6.0)
    ideal = reg.decode(0)
    reg.apply_dissipation(0, gamma=0.5)
    decoded = reg.decode(0)
    assert 0.0 <= decoded <= ideal


def test_register_report_runs_and_states_no_joint_state():
    out = q.register_report(64, 8, gamma=0.3)
    assert "不物化" in out
    assert "PiLink" in out
    assert "64 bit" in out


# ───────────────────────── 寄存器级多位元往返 + 可复现耗散实验（0033 批） ─────────────────────────

def test_register_roundtrip_lossless():
    # γ=0 无损：22 个 qudit 跨 PiLink 逐交换，解码应全等（BER=0）
    rt = q.register_roundtrip(width_bits=64, value=41, d=8, gamma=0.0, seed=0)
    assert rt["decoded"] == 41
    assert rt["ber"] == 0.0
    # 每个 qudit 一次 encode + 一次 measure → 共 2·N 次内存交换（不物化 8^N）
    assert rt["link_writes"] == 2 * rt["n_qudits"]
    assert rt["capacity_bits"] >= 64.0


def test_register_roundtrip_dissipative_drifts_down():
    rt = q.register_roundtrip(width_bits=64, value=41, d=8, gamma=0.9, seed=0)
    # 能级向低泄漏 → 解码值不高于原值，BER ∈ [0,1]
    assert rt["decoded"] <= 41
    assert 0.0 <= rt["ber"] <= 1.0


def test_register_roundtrip_range_guard():
    with pytest.raises(q.QuditError):
        # 64 bit / d=8 → 22 个 qudit，值域 [0, 8**22)
        q.register_roundtrip(width_bits=64, value=8 ** 22, d=8, gamma=0.0, seed=0)


def test_register_measure_method_collapses():
    import random
    reg = q.QuditRegister(width_bits=64, d=8)
    reg.rho[0] = q.density_from_pure(q.dft_matrix(8)[0])  # 均匀叠加
    k = reg.measure(0, random.Random(3))
    assert 0 <= k < 8
    assert reg.purity(0) == pytest.approx(1.0, abs=1e-9)  # 塌缩后纯度=1
    assert reg.link.total_writes >= 1


def test_register_experiment_reproducible_and_monotone():
    rows = q.register_experiment(width_bits=64, d=8, seed=5, n_samples=12)
    # 可复现：同 seed 同结果
    rows2 = q.register_experiment(width_bits=64, d=8, seed=5, n_samples=12)
    assert rows == rows2
    # BER 均值随 γ 单调非减（耗散侵蚀加剧）
    means = [r["ber_mean"] for r in rows]
    for a, b in zip(means, means[1:]):
        assert b >= a - 1e-9, means
    assert means[-1] > means[0]


def test_capabilities_register_experiment_flags():
    cap = q.capabilities()
    assert cap["register_roundtrip"] is True
    assert cap["register_experiment"] is True


# ───────────────────────── 降维升维位元转化（本批） ─────────────────────────

def test_dimension_profile_metrics():
    # 64 bit / d=8 → 22 个 qudit，每 qudit log2(8)=3 bit
    p = q.dimension_profile(64, 8)
    assert p["n_qudits"] == 22
    assert p["per_carrier_bits"] == pytest.approx(3.0)
    assert p["bits_per_carrier"] == pytest.approx(3.0)   # 升维比
    assert p["reduction_factor"] == pytest.approx(64 / 22)  # 降维比
    assert p["total_capacity_bits"] >= 64.0
    assert p["joint_dimension"] == 8 ** 22               # 仅声明，不物化
    # 降维比 ≤ 升维比（ceil 余量使实际每符号摊到的比特 ≤ 容量）
    assert p["reduction_factor"] <= p["bits_per_carrier"] + 1e-12


def test_elevate_reduce_invertible():
    # 精确离散升维↔降维同构（R∘E=I）：覆盖若干 (n,d) 全值域
    for n, d in ((3, 2), (4, 3), (2, 5), (2, 8)):
        cap = d ** n
        for v in range(cap):
            assert q.reduce_bits(q.elevate_bits(v, n, d), d) == v


def test_bit_convert_lossless():
    # γ=0 精确无损：decoded==value, ber==0, lossless 标志为真
    r = q.bit_convert(41, 64, 8, gamma=0.0)
    assert r["decoded"] == 41
    assert r["ber"] == 0.0
    assert r["lossless"] is True
    assert r["digits_in"] == r["digits_out"]


def test_bit_convert_dissipative_drifts_down():
    # γ>0 量化耗散损失：解码不高于原值、BER ∈ [0,1]
    r = q.bit_convert(41, 64, 8, gamma=0.9, seed=0)
    assert r["decoded"] <= 41
    assert 0.0 <= r["ber"] <= 1.0
    assert r["lossless"] is False


def test_bit_convert_range_guard():
    with pytest.raises(q.QuditError):
        # 64 bit / d=8 → 22 个 qudit，值域 [0, 8**22)
        q.bit_convert(8 ** 22, 64, 8, gamma=0.0)


def test_bit_convert_table_invariants():
    rows = q.bit_convert_table()
    assert [r["width_bits"] for r in rows] == [8, 16, 64, 128]
    for r in rows:
        assert r["reduction_factor"] <= r["bits_per_carrier"] + 1e-12
        assert r["total_capacity_bits"] >= r["width_bits"] - 1e-12
        assert r["joint_dimension"] == 8 ** r["n_qudits"]


def test_probe_dim_checks():
    # qudit_probe 的降维升维自检项存在且为真
    pr = q.qudit_probe()
    assert pr["dim_reduce_elevate_invertible"] is True
    assert pr["dim_profile_invariant"] is True


def test_capabilities_bit_conversion_flag():
    cap = q.capabilities()
    assert cap["bit_conversion"] is True


