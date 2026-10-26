"""TLS 1.3 态势审计子系统（v0.6.33）最小冒烟验证。

覆盖用户三条硬要求：适老化/无障碍留存、老旧设备兼容（保留硬化 TLS1.2）、进入整体（引擎友好渲染+可注册）。
红线：绝不读私钥、绝不改配置；不联网、不碰注册表写权限。
"""

import sys

import pytest

sys.path.insert(0, "src/python")

from sysweeper.data import rfc9846_spec as SPEC  # noqa: E402
from sysweeper.native import tls13 as t  # noqa: E402


def test_spec_constants_present():
    assert SPEC.TLS_LEGACY_RECORD_VERSION == 0x0303, "TLS 1.3 legacy_version 必须 0x0303"
    assert SPEC.TLS_1_3_WIRE == 0x0304
    assert SPEC.CIPHER_SUITES[SPEC.MANDATORY_CIPHER_SUITE]["name"] == "TLS_AES_128_GCM_SHA256"
    assert SPEC.DEPRECATED_PROTOCOLS == ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"]


def test_compatibility_tiers_legacy_devices():
    """老旧设备/设施仍能用：只淘汰死的，保留并硬化 TLS 1.2 作兼容桥。"""
    rep = t.tls13_posture_report()
    comp = rep["compatibility"]
    assert comp["retire_must_disable"] == ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"]
    assert comp["bridge_keep_for_legacy"] == "TLS 1.2", "TLS 1.2 必须作兼容桥保留"
    assert comp["primary"] == "TLS 1.3"
    # 分级表一致
    assert t.PROTOCOL_TIERS["TLS 1.2"]["tier"] == "bridge_keep"
    assert t.PROTOCOL_TIERS["TLS 1.0"]["tier"] == "retire"


def test_a11y_summary_plain_text():
    """无障碍/适老化必须留存：人话纯文本、屏幕阅读器可朗读。"""
    lines = t.a11y_tls13_summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    assert "无障碍" in joined and "人话" in joined  # 统一口径 + 适老表达
    assert "屏幕阅读器" in joined
    assert "本工具" in joined  # 打算只读、不代改的口吻（适老化：明示不擅自改动）
    # 不当给矛盾标签（如『必须处理……请放心』）
    assert "请放心。" not in joined


def test_audit_report_engine_friendly():
    """进入整体：动作 op 期望 (bool, text)，含 无障碍简述 与 兼容段。"""
    ok, text = t.tls13_audit_report()
    assert ok is True and isinstance(text, str)
    assert "无障碍简述" in text
    assert "兼容" in text  # 老旧设备/兼容桥


def test_task_registered():
    sys.path.insert(0, "src/python")
    from sysweeper.registry import by_id  # noqa: E402
    assert by_id("tls13_posture_audit") is not None
    assert by_id("tls13_legacy_device_coexistence_guidance") is not None
    # 动作应指向可被引擎 (bool,text) 渲染 audit，而非 dict
    task = by_id("tls13_posture_audit")
    assert task.actions[0].command == "tls13.tls13_audit_report"
