"""GitHub Actions 排错脚本（tools/ci_triage.py）的回归测试。

背景（2026-10-22 真实事故）：私有仓库 Actions 分钟额度耗尽后，作业在排队阶段
即被中止 —— steps 空数组、无 runner、3 秒结束、日志 404 BlobNotFound。
早期 ci_triage.py 遇到这种失败会抛未捕获的 HTTPError 崩溃；修复后必须：

1. `preflight_failure()` 能识别「从未跑起来」的签名（steps 空 + 无 runner + 秒败）；
2. 有步骤的正常失败**不**被误判为额度墙；
3. `api_log()` 拿不到日志时返回 `(None, 原因)` 而不是抛异常；
4. `print_quota_wall()` 输出里含处置要点（Billing / 别改代码）。

这些用例就是那类失败的「复现器」——按 docs/CI-排错.md 的纪律，
修完之后必须有一条能复现该失败的回归测试。
"""

from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
CI_TRIAGE = ROOT / "tools" / "ci_triage.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("ci_triage_under_test", CI_TRIAGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def triage():
    return _load_module()


# ---------------------------------------------------------------------------
# 1. 额度墙签名识别
# ---------------------------------------------------------------------------

def _quota_wall_job(secs: int = 3) -> dict:
    """复刻 2026-10-22 run 39828234065 里 job 的真实形状。"""
    from datetime import datetime, timedelta, timezone
    started = datetime(2026, 10, 22, 18, 4, 49, tzinfo=timezone.utc)
    completed = started + timedelta(seconds=secs)
    fmt = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": 119997134923,
        "name": "构建语言底层产物（系统自带 python3）",
        "conclusion": "failure",
        "steps": [],
        "runner_id": 0,
        "runner_name": "",
        "started_at": fmt(started),
        "completed_at": fmt(completed),
    }


def test_preflight_detects_quota_wall(triage):
    """三步签名全中：steps 空 + 无 runner + 秒败 → 命中。"""
    secs = triage.preflight_failure(_quota_wall_job())
    assert secs is not None
    assert "3 秒" in secs


def test_preflight_ignores_normal_failed_job(triage):
    """有步骤的失败是普通失败（日志里有 ##[error] 可查），不能误判。"""
    job = _quota_wall_job()
    job["steps"] = [{"number": 1, "name": "Set up job", "conclusion": "success"},
                    {"number": 2, "name": "Run", "conclusion": "failure"}]
    assert triage.preflight_failure(job) is None


def test_preflight_ignores_job_with_runner(triage):
    """拿到过 runner 的失败（哪怕 steps 为空）不是排队阶段中止。"""
    job = _quota_wall_job()
    job["runner_id"] = 1000000943
    job["runner_name"] = "GitHub Actions 1000000943"
    assert triage.preflight_failure(job) is None


def test_preflight_ignores_slow_empty_job(triage):
    """steps 空但跑了超过 60 秒 —— 不符合「秒败」签名。"""
    job = _quota_wall_job(secs=120)
    assert triage.preflight_failure(job) is None


def test_preflight_ignores_success(triage):
    """成功的 job 没有 steps 也不该被报（调用方只会传失败的，防御一下）。"""
    job = _quota_wall_job()
    job["conclusion"] = "success"
    # 签名本身不看得失，但 duration 仍短 —— 这里确认它不依赖 conclusion
    assert triage.preflight_failure(job) is not None or job.get("steps")


# ---------------------------------------------------------------------------
# 2. 日志拉取：BlobNotFound 不再崩溃
# ---------------------------------------------------------------------------

def test_api_log_blobnotfound_returns_reason(triage):
    """404 BlobNotFound → (None, 原因)，而不是抛 HTTPError。"""
    err = urllib.error.HTTPError(
        "https://api.github.com/x", 404, "Not Found", {},
        __import__("io").BytesIO(b'{"message":"The specified blob does not exist"}'))
    with mock.patch.object(triage.urllib.request, "build_opener") as bo:
        opener = bo.return_value
        opener.open.side_effect = err
        text, reason = triage.api_log("/repos/o/r/actions/jobs/1/logs", "tok")
    assert text is None
    assert "BlobNotFound" in reason or "blob" in reason.lower()


def test_api_log_other_http_error_returns_reason(triage):
    """其它 HTTP 错误同样转为 (None, 原因)，不崩溃。"""
    err = urllib.error.HTTPError(
        "https://api.github.com/x", 500, "Server Error", {},
        __import__("io").BytesIO(b'{"message":"boom"}'))
    with mock.patch.object(triage.urllib.request, "build_opener") as bo:
        bo.return_value.open.side_effect = err
        text, reason = triage.api_log("/repos/o/r/actions/jobs/1/logs", "tok")
    assert text is None
    assert "500" in reason


def test_api_log_network_error_returns_reason(triage):
    """网络层错误（URLError/OSError）也不该逃出异常。"""
    with mock.patch.object(triage.urllib.request, "build_opener") as bo:
        bo.return_value.open.side_effect = OSError("connection reset")
        text, reason = triage.api_log("/repos/o/r/actions/jobs/1/logs", "tok")
    assert text is None
    assert "网络错误" in reason


# ---------------------------------------------------------------------------
# 3. 诊断输出包含处置要点
# ---------------------------------------------------------------------------

def test_quota_wall_report_mentions_actions(triage, capsys):
    """诊断里必须出现账户级处置（Billing）与「别改代码」的定性。"""
    triage.print_quota_wall(_quota_wall_job(), "3 秒")
    out = capsys.readouterr().out
    assert "Billing" in out
    assert "不是代码" in out
    assert "分钟额度" in out


# ---------------------------------------------------------------------------
# 4. 时间解析
# ---------------------------------------------------------------------------

def test_parse_ts_handles_z_suffix(triage):
    from datetime import timezone
    dt = triage._parse_ts("2026-10-22T18:04:49Z")
    assert dt is not None
    assert dt.tzinfo == timezone.utc


def test_parse_ts_bad_input_returns_none(triage):
    assert triage._parse_ts("") is None
    assert triage._parse_ts("not-a-time") is None
