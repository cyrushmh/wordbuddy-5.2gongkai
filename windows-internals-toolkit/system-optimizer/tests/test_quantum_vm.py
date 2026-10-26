"""quantum 量子虚拟机测试（v0.6.68）：态矢量正确性 / 测量坍缩 / 经典反馈 / IR round-trip /
可复现性 / 错误路径 / 冒烟报告。全测试固定种子，结果确定。

注：概念图谱测试在 test_quantum.py（v0.6.65）；本文件只覆盖 native/quantum.py 可执行虚拟机。
"""
from __future__ import annotations

import math
import re

import pytest

from sysweeper.native import quantum as q


# ── 态矢量与门正确性 ──

def test_initial_state_is_zero():
    sv = q.StateVector(3)
    assert sv.amps[0] == 1
    assert sum(abs(a) ** 2 for a in sv.amps) == pytest.approx(1.0)
    assert sv.probabilities()[0] == pytest.approx(1.0)


def test_x_flips_qubit_zero():
    sv = q.StateVector(2).apply("x", [0])
    assert sv.probabilities()[0b10] == pytest.approx(1.0)  # qubit0 是 MSB


def test_h_then_measure_collapses_deterministically():
    """H 后测量得某值，再测同一比特必得同值（坍缩性质）。"""
    for seed in range(20):
        rng = q.random.Random(seed)
        sv = q.StateVector(1).apply("h", [0])
        first = sv.measure_bit(0, rng)
        second = sv.measure_bit(0, rng)
        assert first == second


def test_bell_state_correlation():
    """Bell 态只出现 00/11，且近似等概率，两比特完全相关。"""
    res = q.run_named("bell", shots=2000, seed=20260101)
    assert set(res["counts"]) == {"00", "11"}
    p = res["probabilities"]
    assert 0.42 < p["00"] < 0.58 and 0.42 < p["11"] < 0.58


def test_ghz_state():
    res = q.run_named("ghz", shots=1000, seed=11)
    assert set(res["counts"]) == {"000", "111"}


def test_gates_unitary_and_probability_conservation():
    """所有门作用于 |0...0> 后总概率恒为 1（酉性粗检）。"""
    for gate in q.GATES:
        n = q.GATE_ARITY[gate]
        sv = q.StateVector(n)
        if q.GATE_PARAMS[gate]:
            sv.apply(gate, list(range(n)), [0.37])
        else:
            sv.apply(gate, list(range(n)))
        assert sum(sv.probabilities()) == pytest.approx(1.0), gate


def test_swap_exchanges_states():
    sv = q.StateVector(2)
    sv.apply("x", [0])          # |10>
    sv.apply("swap", [0, 1])    # → |01>
    assert sv.probabilities()[0b01] == pytest.approx(1.0)


def test_rotation_ry_gives_expected_amplitude():
    """ry(π/2)|0> = cos(π/4)|0> + sin(π/4)|1>。"""
    sv = q.StateVector(1).apply("ry", [0], [math.pi / 2])
    p = sv.probabilities()
    assert p[0] == pytest.approx(0.5, abs=1e-9)
    assert p[1] == pytest.approx(0.5, abs=1e-9)


def test_phase_gate_p():
    sv = q.StateVector(1)
    sv.apply("h", [0])
    sv.apply("p", [0], [math.pi])   # Z 等价
    p = sv.probabilities()
    assert p[1] == pytest.approx(0.5, abs=1e-9)


# ── 经典反馈：量子隐形传态 ──

def test_teleport_transfers_state_exactly():
    """传 |1>：两次 Bell 测量结果任意，Bob 端（qubit 2）修复后恒为 1。"""
    res = q.run_named("teleport", shots=1000, seed=4242)
    counts = res["counts"]
    assert set(counts) == {"001", "011", "101", "111"}
    for bitstring in counts:
        assert bitstring[2] == "1", "传态失败：Bob 端未得到 |1>"


def test_teleport_with_custom_rotation_state():
    """自定义程序：ry(0.5)|0> 传态后 Bob 端 P(1)=sin²(0.25)。"""
    base = q.parse_program("ry 0.5 0\nh 1\ncx 1 2\ncx 0 1\nh 0\n"
                           "measure 0 -> 0\nmeasure 1 -> 1\nxd 1 2\nzd 0 2")
    res = q.run_program(base, shots=2000, seed=99)
    p1 = sum(p for k, p in res["probabilities"].items() if k[2] == "1")
    assert p1 == pytest.approx(math.sin(0.25) ** 2, abs=0.03)


# ── 算法库 ──

def test_grover_finds_marked_state_with_probability_one():
    res = q.run_named("grover2q", shots=512, seed=5)
    assert res["counts"] == {"11": 512}


def test_bv2_recovers_first_bit():
    res = q.run_named("bv2", shots=1000, seed=6)
    for bitstring in res["counts"]:
        assert bitstring[0] == "1"  # 隐串最高位 = 1


# ── IR：解析 / round-trip / 错误路径 ──

def test_parse_and_roundtrip():
    prog = q.parse_program(q.BUILTIN_PROGRAMS["teleport"], name="t")
    again = q.parse_program(prog.to_text_ir(), name="t")
    assert prog.ops == again.ops
    assert (prog.n_qubits, prog.n_classical) == (again.n_qubits, again.n_classical)


def test_implicit_qubit_declaration():
    prog = q.parse_program("h 0\ncx 0 1")
    assert prog.n_qubits == 2 and prog.n_classical == 2


def test_comments_and_blank_lines_ignored():
    prog = q.parse_program("# 注释\n\nqubits 2\n\nh 0  # 叠加\ncx 0 1\n")
    assert prog.gate_count() == 2


@pytest.mark.parametrize("bad", [
    "foo 0",           # 未知道门
    "rx 0",            # 缺参数
    "cx 0",            # 缺比特
    "qubits 99\nh 0",  # 超比特上限
    "measure 0 ->",    # 语法错误
])
def test_invalid_programs_raise(bad):
    with pytest.raises(q.QuantumError):
        q.parse_program(bad)


def test_out_of_range_indices_raise():
    with pytest.raises(q.QuantumError):
        q.parse_program("qubits 2\nh 9")
    with pytest.raises(q.QuantumError):
        q.parse_program("qubits 2\nclassical 2\nmeasure 0 -> 5")
    with pytest.raises(q.QuantumError):
        q.parse_program("if 7 x 0")


def test_error_message_lists_valid_gates():
    with pytest.raises(q.QuantumError) as ei:
        q.parse_program("zzz 0")
    assert "cx" in str(ei.value) and "measure" in str(ei.value)


# ── 数字解析（安全，不用 eval） ──

@pytest.mark.parametrize("tok,val", [
    ("0.5", 0.5), ("pi", math.pi), ("pi/2", math.pi / 2),
    ("-pi/4", -math.pi / 4), ("2*pi", 2 * math.pi), ("3/7", 3 / 7), ("tau", math.tau),
])
def test_number_parser(tok, val):
    assert q._parse_number(tok) == pytest.approx(val)


def test_number_parser_rejects_junk():
    with pytest.raises(q.QuantumError):
        q._parse_number("__import__('os')")


# ── 可复现性与运行器 ──

def test_same_seed_same_result():
    a = q.run_named("bell", shots=128, seed=99)
    b = q.run_named("bell", shots=128, seed=99)
    assert a["counts"] == b["counts"] and a["samples"] == b["samples"]


def test_different_seed_usually_differs():
    a = q.run_named("bell", shots=128, seed=1)
    b = q.run_named("bell", shots=128, seed=2)
    assert a["samples"] != b["samples"]


def test_shots_validation():
    with pytest.raises(q.QuantumError):
        q.run_named("bell", shots=0)


def test_reset_op_restores_zero():
    prog = q.parse_program("qubits 1\nx 0\nreset 0")
    res = q.run_program(prog, shots=16, seed=1)
    assert res["counts"] == {"0": 16}


def test_qubit_count_cap():
    with pytest.raises(q.QuantumError):
        q.StateVector(q.MAX_QUBITS + 1)


# ── 报告 / 环境 / 能力 ──

def test_quantum_report_ok():
    ok, msg = q.quantum_report()
    assert ok and "量子虚拟机就绪" in msg


def test_environment_report_lines():
    lines = q.environment_report()
    assert isinstance(lines, list) and len(lines) >= 8
    assert any("门集" in ln for ln in lines)
    assert any("红线" in ln for ln in lines)


def test_capabilities_and_taxonomy_basis():
    caps = q.capabilities()
    assert caps["max_qubits"] == q.MAX_QUBITS
    assert "cx" in caps["gates"] and "ccx" in caps["gates"]
    assert "teleport" in caps["builtin_programs"]
    basis = q.taxonomy_basis()
    assert basis["domains"] == 9 and basis["concepts"] == 82
    assert basis["version"]  # _meta.version 非空


def test_module_pure_stdlib():
    """红线：源码无第三方依赖引用（import 仅限标准库）。"""
    src = open(q.__file__, encoding="utf-8").read()
    imports = re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_][\w.]*)", src, re.M)
    allowed = ("json", "math", "os", "random", "sys", "collections", "__future__")
    for mod in imports:
        root = mod.split(".")[0]
        assert root in allowed, f"发现非标准库依赖：{mod}"


# ── 量子架构基座：数字转换门 / π 链路 / tan·ctan / pin / 不间断交换 ──

def test_encode_decode_number_roundtrip():
    """数字转换门 enc→dec 对 0..15 全部保真（置换矩阵 Π_k 的确定性）。"""
    m = q.QuantumMachine(n_qubits=4, seed=3)
    for k in range(16):
        m.sv = q.StateVector(4)
        m.encode_number(k)
        assert m.decode_number() == k, f"enc/dec 往返失败：{k}"


def test_enc_in_text_ir_deterministic():
    """IR 层 enc 5（4 比特）→ 测量恒得 0101。"""
    res = q.run_program(q.parse_program("qubits 4\nenc 5"), shots=32, seed=1)
    assert res["counts"] == {"0101": 32}


def test_enc_out_of_range_raises():
    with pytest.raises(q.QuantumError):
        q.parse_program("qubits 2\nenc 4")
    m = q.QuantumMachine(n_qubits=2)
    with pytest.raises(q.QuantumError):
        m.encode_number(4)


def test_pi_link_geometry_and_overwrite():
    """链路容量 = ceil(ratio·π)；超出覆盖最旧记录并如实计数。"""
    link = q.PiLink(2.0)
    assert link.size == 7  # ceil(2π)=7
    for i in range(10):
        link.push({"i": i})
    assert link.stats()["total_writes"] == 10
    assert link.stats()["overwrites"] == 3
    snap = link.snapshot()
    assert snap[0]["i"] == 3 and snap[-1]["i"] == 9  # 最旧的 0/1/2 被覆盖
    drained = link.drain()
    assert len(drained) == 7 and link.stats()["buffered"] == 0


def test_link_records_every_step_until_halt():
    """不间断交换：每条指令都入链；halt 提前终止，steps=入链数。"""
    m = q.QuantumMachine(n_qubits=4, seed=7)
    m.define_pin("led", 0)
    m.load("qubits 4\nenc 5\nh 0\ncx 0 1\nmeasure 0 -> 0\nif 0 x 2\nhalt\nh 3")
    recs = m.run_until_halt()
    assert m.halted and m.steps == 6  # halt 之后的 h 3 不执行
    assert m.link.total_writes == 6
    assert [r["op"] for r in recs] == ["enc", "gate", "gate", "measure", "cond", "halt"]
    # halt 后 step() 返回 None
    assert m.step() is None


def test_step_budget_guard():
    """步数预算护栏：未终止则报错而不是死循环。"""
    m = q.QuantumMachine(n_qubits=2, seed=1)
    m.load("qubits 2\nh 0\ncx 0 1\nh 1\nh 0")
    with pytest.raises(q.QuantumError):
        m.run_until_halt(max_steps=3)


def test_tan_return_pi_periodicity():
    """圆周率：tan 以 π 为周期，tan_return(x) == tan_return(x + kπ)。"""
    for x in (0.3, -1.2, 2.9, 5.5):
        assert q.tan_return(x) == pytest.approx(q.tan_return(x + math.pi))
        assert q.tan_return(x) == pytest.approx(q.tan_return(x + 3 * math.pi))
    assert q.tan_return(0.0) == pytest.approx(0.0)
    assert abs(q.tan_return(math.pi / 3)) < math.pi / 2 + 1e-9  # 主值区间


def test_cotan_complements_tan():
    """ctan = tan(π/2 − θ)：两路返回交互互补成直角。"""
    for x in (0.1, 0.9, -2.4):
        assert q.tan_return(x) + q.cotan_return(x) == pytest.approx(math.pi / 2)


def test_phase_of_reads_relative_phase():
    """相位观测：ry(π/2) 后加 p(π/2)，相对相位应为 π/2。"""
    m = q.QuantumMachine(n_qubits=1, seed=1)
    m.sv.apply("ry", [0], [math.pi / 2])
    m.sv.apply("p", [0], [math.pi / 2])
    assert m.phase_of(0) == pytest.approx(math.pi / 2, abs=1e-9)


def test_pins_virtual_hardware():
    """虚拟其他硬件：针脚定义/写/读/越界报错。"""
    m = q.QuantumMachine(n_qubits=2)
    m.define_pin("led", 0)
    m.define_pin("relay", 1)
    m.set_pin("led", 1)
    m.set_pin("relay", 0)
    assert m.read_pin("led") == 1 and m.read_pin("relay") == 0
    with pytest.raises(q.QuantumError):
        m.read_pin("nope")
    with pytest.raises(q.QuantumError):
        m.define_pin("bad", 9)


def test_measure_writes_tan_return_records():
    """measure 交换记录带 tan/ctan 返回交互字段（π 折叠角）。"""
    m = q.QuantumMachine(n_qubits=1, seed=2)
    m.load("qubits 1\nh 0\nmeasure 0 -> 0\nhalt")
    recs = m.run_until_halt()
    measure_rec = recs[1]
    assert measure_rec["op"] == "measure" and measure_rec["dir"] == "q→c"
    assert "tan_return" in measure_rec and "ctan_return" in measure_rec
    assert measure_rec["tan_return"] + measure_rec["ctan_return"] == pytest.approx(math.pi / 2)
    assert m.cpu[0] == measure_rec["value"]


def test_architecture_report():
    ok, msg = q.architecture_report()
    assert ok and "量子架构基座就绪" in msg


def test_state_dict_snapshot():
    m = q.QuantumMachine(n_qubits=3, seed=1)
    m.load("qubits 3\nenc 3\nh 0\nhalt")
    m.run_until_halt()
    d = m.state_dict()
    assert d["steps"] == 3 and d["halted"] is True and d["link"]["size"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# CLI 接线：sysweeper quantum vm <程序|arch>（v0.6.69）
# ─────────────────────────────────────────────────────────────────────────────
def _run_cli(argv, capsys):
    from sysweeper import cli
    parser = cli.build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return capsys.readouterr().out


def test_cli_vm_bell(capsys):
    out = _run_cli(["quantum", "vm", "bell", "--shots", "256", "--seed", "42"], capsys)
    assert "bell" in out and "shots: 256" in out and "00:" in out and "11:" in out


def test_cli_vm_arch(capsys):
    out = _run_cli(["quantum", "vm", "arch"], capsys)
    assert "量子架构基座就绪" in out
    assert "链路 7 槽" in out and "tan" in out and "halt" in out


def test_cli_vm_unknown_program(capsys):
    out = _run_cli(["quantum", "vm", "nosuch"], capsys)
    assert "[失败]" in out and "bell" in out  # 提示里列出可用程序


def test_cli_vm_grover_and_superposition(capsys):
    out = _run_cli(["quantum", "vm", "grover2q", "--shots", "64"], capsys)
    assert "11:" in out
    out2 = _run_cli(["quantum", "vm", "superposition"], capsys)
    assert "0:" in out2 and "1:" in out2


# ─────────────────────────────────────────────────────────────────────────────
# omni 四件套接线：tasks/quantum.py + data/quantum.json（v0.6.70）
# 「登记进统一清单 ≠ 真的接全了」——本组守住 quantum 不再有半截能力。
# ─────────────────────────────────────────────────────────────────────────────
def test_quantum_task_registered():
    from sysweeper import registry
    ts = [t for t in registry.all_tasks() if t.id.startswith("quantum_")]
    assert len(ts) == 1
    t = ts[0]
    assert t.platform == "any" and t.risk == "low"
    # 只读任务：动作只能是 native 接口或手动指引，绝不 shell 代执行
    assert t.actions and all(a.kind in ("native", "manual") for a in t.actions)
    # 任务默认参与扫描（非 opt-in），否则「进了注册表却永远不跑」
    assert t.opt_in is False


def test_quantum_task_native_actions_resolve():
    """任务里引用的 native 接口必须真实存在且零参可调（防注册表与实现漂移）。"""
    from sysweeper import registry, runner
    t = next(t for t in registry.all_tasks() if t.id == "quantum_vm_report")
    native_ops = [a for a in t.actions if a.kind == "native"]
    assert native_ops, "至少应有 native 自检动作"
    for a in native_ops:
        ok, msg = runner.run_action(a)
        assert ok, f"{a.command} 未通过：{msg}"


def test_quantum_wiring_complete_in_omni():
    """omni 自检视角：quantum 的 cli/gui/task/data 四处接线必须齐全。"""
    from sysweeper.native import omni
    row = next(r for r in omni.wiring() if r["key"] == "quantum")
    assert row["wiring"] == {"cli": True, "gui": True, "task": True, "data": True}
    assert row["complete"] is True
    assert row["missing"] == []


def test_quantum_not_in_real_gaps():
    """真缺口清单里不允许再出现 quantum（半截能力已补齐）。"""
    from sysweeper.native import omni
    assert "quantum" not in {p["key"] for p in omni.real_gaps()}
    # 全量口径：当前应无任何真缺口（设计如此项单列，不算欠账）
    assert omni.real_gaps() == []


def test_quantum_kb_has_standards():
    """data/quantum.json 知识库：条目带 name/standard/org/summary 四字段。"""
    import importlib
    import json
    import pathlib
    pkg = pathlib.Path(importlib.import_module("sysweeper").__file__).parent
    kb = json.loads((pkg / "data" / "quantum.json").read_text(encoding="utf-8"))
    assert len(kb) > 10
    for key, entry in kb.items():
        if key == "_note":
            continue
        for f in ("name", "standard", "org", "summary"):
            assert entry.get(f), f"{key} 缺字段 {f}"
    # 内置程序各有原始文献出处：bell/ghz/teleport/grover/bv
    for key in ("bell1964", "greenberger1989", "teleport1993",
                "grover1996", "bernstein_vazirani1993"):
        assert key in kb, f"内置程序的出处 {key} 未登记"
