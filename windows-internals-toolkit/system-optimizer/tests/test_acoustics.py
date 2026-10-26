"""acoustics 子系统测试（v0.6.87）：知识库加载 + 纯函数换算/算律 + 只读不变量。"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import acoustics as na  # noqa: E402


# --------------------------------------------------------------------------- #
# 知识库四轴                                                                    #
# --------------------------------------------------------------------------- #

def test_refs_four_axes():
    refs = na.reference_all()
    assert set(refs) >= {"sound_basics", "chinese_pitch", "wireless_em", "audio_hardware"}
    for key, ref in refs.items():
        for field in ("name", "org", "url", "protocols", "interfaces",
                      "docs", "summary", "advice"):
            assert field in ref, f"{key} 缺字段 {field}"
        assert ref["protocols"] and ref["interfaces"] and ref["docs"]


def test_ism_bands_table():
    bands = na.reference("wireless_em")["ism_bands"]
    centers = {b["center"] for b in bands}
    assert "2450 MHz" in centers and "5800 MHz" in centers and "433.92 MHz" in centers
    # 每条都带 ITU 脚注出处
    assert all(b["footnote"].startswith("RR 5.") for b in bands)


def test_en50332_limits():
    lim = na.reference("audio_hardware")["en50332_limits"]
    assert lim["whole_system_max_spl_db"] == 100
    assert lim["player_max_output_voltage_mv"] == 150
    assert lim["headphone_wbcv_min_mv"] == 75
    assert lim["load_ohm"] == 32


# --------------------------------------------------------------------------- #
# 波动几何换算（纯函数）                                                        #
# --------------------------------------------------------------------------- #

def test_wavelength_air_20c():
    # 线性近似 c(20 °C) = 331.3 + 0.606×20 = 343.42 m/s（常四舍五入记 343）
    assert abs(na.speed_of_sound("air", 20.0) - 343.42) < 1e-6
    assert abs(na.wavelength(1000.0) - 0.34342) < 1e-4
    assert abs(na.wavelength(20.0) - 17.171) < 0.01
    assert abs(na.wavelength(20000.0) - 0.017171) < 1e-4


def test_speed_of_sound_temperature():
    assert abs(na.speed_of_sound("air", 0.0) - 331.3) < 1e-6
    assert abs(na.speed_of_sound("air", 20.0) - 343.42) < 1e-6
    assert na.speed_of_sound("steel") == 5960.0


def test_frequency_from_wavelength_roundtrip():
    f = na.frequency_from_wavelength(na.wavelength(440.0))
    assert abs(f - 440.0) < 1e-9


def test_em_wavelength_and_antenna():
    # 2.45 GHz → λ ≈ 12.24 cm；λ/4 ≈ 30.6 mm
    assert abs(na.em_wavelength(2.45e9) * 100 - 12.24) < 0.01
    assert abs(na.antenna_length(2.45e9) * 1000 - 30.6) < 0.05
    # 433.92 MHz → λ ≈ 69.09 cm
    assert abs(na.em_wavelength(433.92e6) * 100 - 69.09) < 0.01


def test_invalid_inputs_raise():
    import pytest
    with pytest.raises(ValueError):
        na.wavelength(0.0)
    with pytest.raises(ValueError):
        na.em_wavelength(-1.0)
    with pytest.raises(ValueError):
        na.speed_of_sound("unobtainium")


def test_db_sum():
    # 两个 60 dB 同源叠加 ≈ 63.01 dB
    assert abs(na.db_sum([60.0, 60.0]) - 63.01) < 0.01


def test_weighting_correction():
    # IEC 61672-1 标称值：A 计权 63 Hz = −26.2 dB，1 kHz = 0
    assert na.weighting_correction(63.0, "A") == -26.2
    assert na.weighting_correction(1000.0, "A") == 0.0
    # 非标称频率取对数轴最近邻：100 Hz 应取 125 Hz 档（−16.1）
    assert na.weighting_correction(100.0, "A") == -16.1
    # Z 计权全零
    assert na.weighting_correction(63.0, "Z") == 0.0


# --------------------------------------------------------------------------- #
# 三分损益十二律（算律正确性：对《吕氏春秋》口径的经典数值）                    #
# --------------------------------------------------------------------------- #

def test_sanfen_sunyi_lengths_match_classic_table():
    rows = {e["lvlv"]: e for e in na.sanfen_sunyi()}
    expect = {"黄钟": 81.0, "林钟": 54.0, "太簇": 72.0, "南吕": 48.0, "姑冼": 64.0,
              "应钟": 42.6667, "蕤宾": 56.8889, "大吕": 75.8519, "夷则": 50.5679,
              "夹钟": 67.4239, "无射": 44.9492, "中吕": 59.9323, "清黄钟": 39.9549}
    assert len(rows) == 13
    for name, length in expect.items():
        assert abs(rows[name]["length"] - length) < 1e-3, name


def test_sanfen_sunyi_freq_ratios():
    rows = {e["lvlv"]: e for e in na.sanfen_sunyi()}
    assert abs(rows["林钟"]["freq_ratio"] - 1.5) < 1e-9        # 3:2 五度
    assert abs(rows["太簇"]["freq_ratio"] - 1.125) < 1e-9       # 9:8
    assert abs(rows["大吕"]["freq_ratio"] - 2187 / 2048) < 1e-9  # 折回八度
    # 清黄钟不能还原：39.9549 ≠ 40.5
    assert rows["清黄钟"]["note"].startswith("管长 39.9549")


def test_sanfen_sunyi_cents_monotone_comma():
    rows = {e["lvlv"]: e for e in na.sanfen_sunyi()}
    # 自林钟起每律约 +1.96 音分（comma÷12），到大吕恰为 7×1.955 ≈ 13.69
    assert abs(rows["大吕"]["cents_vs_et"] - 13.69) < 0.01
    assert abs(rows["林钟"]["cents_vs_et"] - 1.96) < 0.01
    assert abs(rows["中吕"]["cents_vs_et"] - 21.51) < 0.01


def test_sanfen_sunyi_base_freq_scaling():
    rows = na.sanfen_sunyi(base_freq=110.0)
    assert abs(rows[0]["freq_hz"] - 110.0) < 1e-9
    assert abs(rows[1]["freq_hz"] - 165.0) < 1e-6   # 林钟 = 3/2


# --------------------------------------------------------------------------- #
# 只读探针与报告（不变量：可用性随环境，但永不抛异常）                          #
# --------------------------------------------------------------------------- #

def test_probes_never_raise():
    for fn_name, _label in na.PROBES:
        ok, msg = getattr(na, fn_name)()
        assert isinstance(ok, bool)
        assert msg is not None


def test_devices_and_conversion_and_lvlv_reports():
    for fn in ("devices_report", "conversion_report", "lvlv_report"):
        ok, msg = getattr(na, fn)()
        assert ok is True
        assert isinstance(msg, str) and msg


def test_hearing_guide_mentions_limits():
    ok, msg = na.hearing_protection_guide()
    assert ok is True
    assert "100" in msg and "150" in msg and "75" in msg


def test_acoustics_report_end_to_end():
    ok, rep = na.acoustics_report()
    assert ok is True
    for token in ("三分损益", "IEC 61672", "EN 50332", "ISM", "绝不"):
        assert token in rep


def test_no_write_paths_in_source():
    """安全不变量（AST 级）：模块唯一执行收口是 ``_run``，且其实参常量全在只读白名单。

    文档字符串里出现被禁命令名（用于声明禁止）不算数；这里只查**真实执行点**。
    """
    import ast
    src_path = os.path.join(os.path.dirname(na.__file__), "acoustics.py")
    tree = ast.parse(open(src_path, encoding="utf-8").read())

    exec_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in ("run", "_run", "system", "popen", "Popen", "check_output",
                        "check_call", "call", "spawnl", "spawnv", "execv"):
                exec_calls.append((name, node))

    # 1) 执行点只允许 _run（唯一收口）与其内部的 subprocess.run
    names = {n for n, _ in exec_calls}
    assert names <= {"_run", "run"}, f"存在收口之外的执行点: {sorted(names)}"
    assert "_run" in names, "未找到唯一执行收口 _run"

    # 2) _run 实参里的字符串常量必须全部属于只读清单命令
    safe_argv = {"aplay", "arecord", "pactl", "-l", "info"}
    for name, node in exec_calls:
        if name != "_run" or not node.args:
            continue
        arg0 = node.args[0]
        if isinstance(arg0, (ast.List, ast.Tuple)):
            argv = [ast.literal_eval(e) for e in arg0.elts
                    if isinstance(e, ast.Constant)]
            if argv:
                assert all(a in safe_argv for a in argv), \
                    f"可疑参数（疑似播放/调音量/录音/发射）: {argv}"
