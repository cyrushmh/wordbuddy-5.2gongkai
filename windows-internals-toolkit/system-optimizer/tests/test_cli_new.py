"""v0.6.12 新 CLI 子命令冒烟测试：webnews / edge / mesh（无头命令，不依赖 GUI）。

运行：PYTHONPATH=src/python python -m pytest tests/test_cli_new.py -q
"""

import sys

import pytest

from sysweeper import cli


def _run(argv, capsys):
    """用同一套解析器解析并派发，返回捕获的 stdout。"""
    parser = cli.build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return capsys.readouterr().out


def test_webnews_report(capsys):
    out = _run(["webnews"], capsys)
    assert "新闻/网站优化资讯层" in out
    assert "配置的新闻/网站来源" in out


def test_webnews_caps(capsys):
    out = _run(["webnews", "caps"], capsys)
    assert "新闻/网站优化资讯层" in out
    assert "红线" in out


def test_webnews_sources(capsys):
    out = _run(["webnews", "sources"], capsys)
    assert "配置的新闻/网站来源" in out
    assert "http/https" in out


def test_webnews_knowledge_empty(capsys):
    out = _run(["webnews", "knowledge"], capsys)
    assert "优化资讯缓存为空" in out


def test_webnews_fetch_injected(monkeypatch, tmp_path, capsys):
    """注入假 RSS，验证 fetch → 解析 → 抽关键词链路（不碰真网络）。"""
    from sysweeper.native import webnews

    rss = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        '<item><title>linux 内核调优实践</title><link>http://x/1</link>'
        '<description>用 sysctl 调优 linux 网络栈</description></item>'
        '</channel></rss>'
    )
    monkeypatch.setattr(webnews, "fetch", lambda url, timeout=8.0: (True, rss))
    # 缓存重定向到临时文件，避免污染 XDG；fetch 写入后 knowledge 才读得到
    cache_file = tmp_path / "webnews.json"
    monkeypatch.setattr(webnews, "_cache_path", lambda: cache_file)

    out = _run(["webnews", "fetch", "--source", "http://example.com/feed.xml"], capsys)
    assert "资讯抓取" in out
    assert "linux" in out  # 命中关键词被抽成关注方向（经由缓存回显）


def test_edge_report_degrade(capsys):
    out = _run(["edge"], capsys)
    # x86/非 SBC 上应优雅降级，绝不抛异常
    assert ("单板机" in out) or ("未识别" in out)


def test_edge_caps(capsys):
    out = _run(["edge", "caps"], capsys)
    assert "SBC" in out
    assert "只读" in out


def test_mesh_nodes_empty(capsys):
    out = _run(["mesh"], capsys)
    assert "节点发现" in out
    # 没收到通告时为空属正常
    assert ("未登记" in out) or ("在线节点" in out)


def test_mesh_protocol(capsys):
    out = _run(["mesh", "protocol"], capsys)
    assert "协议" in out
    assert "SW-OFFER1" in out or "UDP 2425" in out


def test_new_subcommands_registered():
    parser = cli.build_parser()
    names = set(parser._subparsers._group_actions[0].choices.keys())
    assert {"webnews", "edge", "mesh"} <= names
