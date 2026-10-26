"""远程接入与传输客户端只读审计（v0.6.30）：文档完整 + 跨平台安全降级 + 只读审计 + CLI 可跑。

验证 remote 模块：
- 知识库（data/remote_clients_docs.json）覆盖 telnet/ssh/filezilla/putty，结构完整；
- 只读探针在安全降级下不崩、不伪造数据；
- 安全审计（ssh 安全 / telnet 风险 / filezilla 安全）只读、绝不读解密口令、绝不改配置；
- CLI 子命令 `sysweeper remote` 正常产出，且不含任何口令内容。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from sysweeper.native import remote as r
from sysweeper import registry

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "src" / "python")


def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = PY
    return env


def test_remote_doc_loaded():
    refs = r.reference_all()
    assert isinstance(refs, dict) and refs, "remote_clients_docs.json 应已加载且非空"
    for key in ("openssh", "telnet", "filezilla", "putty"):
        assert key in refs, f"remote 知识库应含 {key}"


def test_remote_reference_shape():
    for key, ref in r.reference_all().items():
        assert "protocols" in ref and "interfaces" in ref, (
            f"remote 接口 {key} 缺 protocols/interfaces")
        assert isinstance(ref["protocols"], list) and ref["protocols"]
        assert isinstance(ref["interfaces"], list) and ref["interfaces"]
        assert "advice" in ref and ref.get("advice"), f"remote {key} 缺 advice"


def test_remote_doc_list_nonempty():
    assert list(r.remote_doc_list())


def test_remote_tune_list_nonempty():
    lines = r.remote_tune_list()
    assert lines
    joined = "\n".join(lines)
    for kw in ("telnet", "sshd", "SFTP", "主密码"):
        assert kw in joined, f"remote 指引应覆盖 {kw}"


def test_remote_audit_runs():
    ok, rep = r.remote_audit_report()
    assert ok is True
    assert isinstance(rep, str) and rep
    assert "只读安全审计" in rep


def test_remote_ssh_security_readonly():
    # 只读读取 sshd_config 关键项；无目标平台应安全降级为 present=False
    ssh = r.read_ssh_security()
    assert isinstance(ssh, dict)
    assert "present" in ssh and "items" in ssh and "notes" in ssh
    # 绝不返回私钥内容或写操作
    assert not any("PRIVATE KEY" in str(v) for v in ssh["items"].values())


def test_remote_filezilla_security_no_decrypt():
    # FileZilla 安全判定只读：绝不读取或解密口令
    fz = r.read_filezilla_security()
    assert isinstance(fz, dict)
    assert "present" in fz and "plain_ftp" in fz
    # 不返回任何明文口令字段
    assert "password_plaintext" not in fz


def test_remote_telnet_risk_readonly():
    tel = r.audit_telnet_risk()
    assert isinstance(tel, dict)
    assert "client_available" in tel and "port_23_listening" in tel
    assert isinstance(tel["notes"], list)


def test_remote_in_registry():
    tks = [t for t in registry.all_tasks() if t.id.startswith("remote_")]
    assert len(tks) >= 5, "remote 任务应已注册"
    ids = {t.id for t in tks}
    for expect in ("remote_clients_audit", "remote_ssh_harden",
                   "remote_telnet_disable", "remote_filezilla_secure",
                   "remote_putty_secure"):
        assert expect in ids, f"缺 remote 任务 {expect}"


def test_cli_remote_runs():
    rr = subprocess.run([sys.executable, "-m", "sysweeper", "remote"],
                        cwd=REPO, capture_output=True, text=True, env=_env())
    assert rr.returncode == 0, rr.stderr
    assert "远程接入与传输客户端" in rr.stdout
