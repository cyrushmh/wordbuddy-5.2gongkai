"""证书与加密子系统（v0.6.31）只读审计验证。

对齐既有范式：文档完整 + 跨平台安全降级 + CLI/任务可注册 + 引擎纯函数可测。
红线：绝不读私钥、绝不解密、绝不改配置。
"""

import json
import sys

import pytest

sys.path.insert(0, "src/python")

from sysweeper.native import cert as c  # noqa: E402


def test_cert_doc_loaded():
    refs = c.reference_all()
    assert isinstance(refs, dict) and refs, "cert_docs.json 应已加载且非空"
    for key in ("openssl", "libressl", "boringssl", "gnutls", "x509",
                "acme", "tpm", "fido", "keystore", "device_cert"):
        assert key in refs, f"cert 知识库应含 {key}"
        r = refs[key]
        assert r.get("name") and r.get("url"), f"{key} 应有 name/url"
        assert isinstance(r.get("protocols"), list) and r["protocols"], f"{key} 应有 protocols"


def test_cert_reference_shape():
    # 文档层统一形态：name/org/url/protocols/interfaces/docs/summary/advice
    for key, ref in c.reference_all().items():
        for field in ("name", "org", "url", "summary", "advice"):
            assert field in ref, f"{key} 缺字段 {field}"
        assert isinstance(ref.get("interfaces"), list), f"{key}.interfaces 应为列表"
        assert isinstance(ref.get("docs"), list), f"{key}.docs 应为列表"


def test_cert_environment_report_runs():
    # 探针在任意平台都应优雅返回 list，不抛异常
    lines = c.environment_report()
    assert isinstance(lines, list) and lines
    # 探针清单项数与 PROBES 一致
    assert len(c.PROBES) == 6


def test_cert_audit_report_runs():
    ok, rep = c.cert_audit_report()
    assert ok is True
    assert isinstance(rep, str) and "证书与加密" in rep
    # 无障碍简述段应存在
    assert "无障碍简述" in rep


def test_cert_status_summary_shape():
    s = c.cert_status_summary()
    assert isinstance(s, dict)
    for k in ("openssl_version", "openssl_eol", "tpm_present",
              "keystore_present", "device_cert_present", "min_cert_days", "weak_crypto"):
        assert k in s, f"cert_status_summary 应含 {k}"
    # 布尔/None 字段类型正确
    assert s["tpm_present"] in (True, False)
    assert s["keystore_present"] in (True, False)


def test_cert_a11y_summary_accessible():
    lines = c.a11y_cert_summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    # 无障碍输出给出人话状态，不出现私钥/口令等敏感词
    assert "加密库" in joined and "硬件信任根" in joined


def test_cert_tune_list_nonempty():
    # 写操作仅指引：升级加密库/启用 TPM/硬件密钥库/续期证书
    lines = c.cert_tune_list()
    assert lines
    joined = "\n".join(lines)
    for kw in ("TPM", "密钥库", "ACME", "加密库"):
        assert kw in joined, f"cert 指引应覆盖 {kw}"


def test_cert_audit_openssl_safe():
    # 只读审计 OpenSSL 只取版本/判定 EOL，不读私钥、不改配置
    ao = c.audit_openssl()
    assert isinstance(ao, dict)
    assert ao["eol"] in (True, False, None)
    if ao["version"]:
        assert "OpenSSL" in ao["version"] or "LibreSSL" in ao["version"]


def test_cert_probe_degrade_no_crash():
    # 各探针在缺组件时都应降级返回 (ok, msg)，不抛
    for fn_name, _ in c.PROBES:
        ok, msg = getattr(c, fn_name)()
        assert isinstance(ok, bool)
        assert isinstance(msg, (str, dict))
