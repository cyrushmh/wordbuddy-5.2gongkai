"""CLI `rfc` 子命令组冒烟验证（v0.6.33）。

用真实子进程跑 python -m sysweeper rfc，确保参数解析、输出形态、
边界情况（未分配编号 / Not Issued / 空检索）全部诚实可读。
"""

import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(REPO, "src", "python")


def run_rfc(*argv):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    return subprocess.run([sys.executable, "-m", "sysweeper", "rfc", *argv],
                          capture_output=True, text=True, env=env, timeout=120)


def test_rfc_overview():
    r = run_rfc()
    assert r.returncode == 0, r.stderr
    assert "10036" in r.stdout and "只读" in r.stdout


def test_rfc_show_with_citing_tasks():
    r = run_rfc("show", "9846")
    assert r.returncode == 0, r.stderr
    assert "RFC 9846" in r.stdout
    assert "Transport Layer Security" in r.stdout
    assert "tls13_posture_audit" in r.stdout  # 反向引用视图


def test_rfc_show_unassigned_and_not_issued():
    r = run_rfc("show", "10544")
    assert r.returncode == 0
    assert "未分配" in r.stdout  # 诚实：不在索引即未分配，不臆造
    r = run_rfc("show", "14")
    assert r.returncode == 0
    assert "Not Issued" in r.stdout


def test_rfc_search_and_list_status():
    r = run_rfc("search", "TLS", "--limit", "3")
    assert r.returncode == 0
    assert "命中 3 条" in r.stdout and "TLS" in r.stdout
    r = run_rfc("list", "--status", "HISTORIC", "--limit", "2")
    assert r.returncode == 0
    assert "HISTORIC" in r.stdout
    r = run_rfc("search")
    assert r.returncode == 0 and "请给出检索词" in r.stdout


def test_rfc_citing():
    r = run_rfc("citing", "rfc08996")
    assert r.returncode == 0
    assert "tls13_posture_audit" in r.stdout
