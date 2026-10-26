"""诊断日志与脱敏测试（移植自 DiPlay 工程实践，见 docs/DiPlay-参考分析.md）。

重点验证三条底线：
1. 敏感信息不会被写进报告（凭据整行丢弃、IP/MAC/标识/家目录占位符化）；
2. 写入永远不阻塞调用方、不因为一次写失败而中断；
3. 报告只写本地，不上传（这里用「不产生任何网络调用」的结构性检查代替）。
"""

from __future__ import annotations

import os
import sys
import time

PKG_ROOT = __file__.rsplit("/tests/", 1)[0] + "/src/python"
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

from sysweeper.diagnostics import (  # noqa: E402
    BoundedWriter, DiagnosticLog, Redactor, build_report,
)


# ---------------------------------------------------------------- 脱敏


def test_redact_replaces_identifiers():
    r = Redactor()
    line = "peer 192.168.31.7 mac aa:bb:cc:dd:ee:ff id 3f2a1b0c9d8e7f6a5b4c3d2e"
    out = r.redact(line)
    assert "192.168.31.7" not in out and "[ip]" in out
    assert "aa:bb:cc:dd:ee:ff" not in out and "[address]" in out
    assert "3f2a1b0c9d8e7f6a5b4c3d2e" not in out and "[identifier]" in out


def test_redact_drops_credential_lines():
    r = Redactor()
    for bad in ("wifi password=hunter2", "Authorization: Bearer abcdef",
                "private key stored at /etc/ssl", "psk=12345678",
                "token: aaaabbbbcccc"):
        assert r.redact(bad) is None, bad
    # 正常内容不受影响
    assert r.redact("scan finished: 12 tasks") is not None


def test_redact_hides_home_directory():
    r = Redactor()
    out = r.redact(os.path.expanduser("~/Documents/report.txt"))
    assert os.path.basename(os.path.expanduser("~")) not in out
    assert out.startswith("~")


def test_redact_folds_newlines_and_truncates():
    r = Redactor(max_line=20)
    out = r.redact("第一行\n第二行\r\n第三行")
    assert "\n" not in out and "\r" not in out
    assert len(out) <= 20


def test_redact_block_keeps_only_safe_lines():
    r = Redactor()
    kept = r.redact_block(["ok line", "password=1234", "another ok"])
    assert kept == ["ok line", "another ok"]


# ---------------------------------------------------------------- 有界写入


def test_bounded_writer_never_blocks_and_drops_oldest():
    seen = []
    writer = BoundedWriter(lambda x: (time.sleep(0.002), seen.append(x)),
                           max_pending=4)
    for i in range(300):
        writer.enqueue(i)          # 调用方不应被阻塞
    assert writer.flush(timeout=5.0) is True
    writer.close()
    assert writer.dropped_count > 0, "队列必须触发丢弃"
    assert seen[-1] == 299, "超载时保留最新、丢弃最旧"


def test_bounded_writer_survives_write_failure():
    state = {"n": 0}

    def flaky(item):
        state["n"] += 1
        if state["n"] == 1:
            raise OSError("disk full")
        state.setdefault("ok", []).append(item)

    writer = BoundedWriter(flaky, max_pending=8)
    for i in range(5):
        writer.enqueue(i)
    assert writer.flush(timeout=5.0) is True
    writer.close()
    assert state["n"] == 5, "一次写失败不应中断后续写入"


def test_bounded_writer_rejects_after_close():
    writer = BoundedWriter(lambda x: None, max_pending=4)
    writer.close()
    assert writer.enqueue("late") is False


# ---------------------------------------------------------------- 日志文件


def test_diagnostic_log_writes_and_skips(tmp_path):
    path = tmp_path / "diag.txt"
    log = DiagnosticLog(path)
    assert log.append("scan finished: 3 tasks") is True
    assert log.append("password=letmein") is False      # 命中凭据 → 整行丢弃
    assert log.flush(timeout=5.0) is True
    log.close()

    text = path.read_text(encoding="utf-8")
    assert "scan finished" in text
    assert "letmein" not in text
    assert log.skipped_count == 1
    assert log.written_count == 1


def test_diagnostic_log_context_manager(tmp_path):
    path = tmp_path / "diag2.txt"
    with DiagnosticLog(path) as log:
        log.append("entry one")
    assert "entry one" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- 报告


def test_build_report_is_redacted_and_offline():
    text = build_report(version="0.5.22", extra_sections={
        "备注": ["router 10.0.0.1", "password=secret", "all good"],
    })
    assert "10.0.0.1" not in text and "[ip]" in text
    assert "secret" not in text
    assert "all good" in text
    # 结构上不含任何上传目标（不自动上传的底线）
    assert "http://" not in text and "https://" not in text
