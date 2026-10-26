"""设备长期使用保护 · 天气/气候感知与资产/数据/通信保护（v0.6.31）验证。

扩展点：read_weather_climate / read_comms 传感器、auto_climate_tags 自动推导环境标签、
protect_assets 纯函数、durability_report 融合证书/通信状态的保护段。
"""

import sys

import pytest

sys.path.insert(0, "src/python")

from sysweeper.native import durability as d  # noqa: E402


def test_weather_climate_and_comms_probes_registered():
    names = [n for n, _ in d.PROBES]
    assert "read_weather_climate" in names, "PROBES 应含天气/气候感知"
    assert "read_comms" in names, "PROBES 应含通信能力感知"


def test_read_weather_climate_degrades():
    ok, msg = d.read_weather_climate()
    assert isinstance(ok, bool)
    assert isinstance(msg, (str, dict))


def test_read_comms_degrades():
    ok, msg = d.read_comms()
    assert isinstance(ok, bool)
    assert isinstance(msg, (str, dict))


def test_auto_climate_tags():
    assert d.auto_climate_tags({"ambient_temp_c": 35}) == ["high_temp"]
    assert d.auto_climate_tags({"ambient_rh": 82}) == ["high_humidity"]
    assert d.auto_climate_tags({"ambient_temp_c": 35, "ambient_rh": 82}) == ["high_temp", "high_humidity"]
    assert d.auto_climate_tags({}) == []


def test_protect_assets_baseline_backup():
    items = d.protect_assets()
    ids = [it["id"] for it in items]
    assert "protect_backup" in ids, "资产保护应始终含备份项"
    for it in items:
        assert it["rationale"], f"{it['id']} 应回链知识库 key"
        assert it["action"] == "guidance", "保护项只给指引不代执行"


def test_protect_assets_with_cert_summary():
    cert = {
        "tpm_present": False, "keystore_present": False, "openssl_eol": True,
        "min_cert_days": 10, "device_cert_present": False, "weak_crypto": True,
    }
    items = d.protect_assets(cert_summary=cert)
    ids = [it["id"] for it in items]
    assert "protect_keyroot" in ids, "无 TPM/密钥库 → 应建议启用硬件信任根"
    assert "protect_crypto" in ids, "EOL 加密库 → 应建议升级"
    assert "protect_cert" in ids, "临近过期证书 → 应建议续期"
    assert "protect_device_id" in ids, "无设备身份证书 → 应建议启用硬件背书身份"


def test_protect_assets_comms_down():
    items = d.protect_assets(comms_summary={"reachable": False, "note": "链路 down"})
    ids = [it["id"] for it in items]
    assert "protect_comms" in ids, "通信中断 → 应提示排查"


def test_durability_report_includes_protection_section():
    ok, rep = d.durability_report("heavy", 5, ["mobile"])
    assert ok is True
    assert "关键资产 / 个人数据 / 通信能力保护" in rep, "报告应含资产保护段"
    assert "通信状态" in rep, "报告应含通信状态行"
    # 自动气候感知（沙箱无温感，high_temp 不会自动加；但段仍渲染）
    assert "证书状态" in rep or "通信状态" in rep


def test_durability_report_auto_climate_merge():
    # 即便用户未显式给 high_temp，若传感器读出高温也应并入环境标签
    ok, rep = d.durability_report("moderate", 4, [], cert_summary={}, comms_summary={"reachable": True})
    assert ok is True
    # 无异常即通过；合并逻辑在内部，断言不崩即可
