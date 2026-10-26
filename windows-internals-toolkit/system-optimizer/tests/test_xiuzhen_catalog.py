"""修真图谱（xiuzhen_catalog + CLI）最小冒烟验证。

覆盖：数据层完整性（75 节点/77 边、全部带 source）、节点解析三种入口
（精确 id / 标题 / 前缀优先级——「道德经」应命中典籍而非旁参）、双向邻接、
关系文案、检索、分层统计、CLI 子命令（overview/list/search/show/edges/layers）。
"""

import subprocess
import sys

sys.path.insert(0, "src/python")

from sysweeper.native import xiuzhen_catalog as xz  # noqa: E402


def test_data_completeness():
    data = xz.map_data()
    assert len(data["nodes"]) == 75
    assert len(data["edges"]) == 77
    # 纪律：节点/边一律带 source，无出处不建
    assert all(n.get("source") for n in data["nodes"]), "存在无出处的节点"
    assert all(e.get("source") for e in data["edges"]), "存在无出处的边"
    # 悬空边 = 0（端点都必须在节点表中）
    ids = {n["id"] for n in data["nodes"]}
    assert all(e["from"] in ids and e["to"] in ids for e in data["edges"])


def test_node_resolution():
    # 精确 id
    assert xz.node_info("book:daodejing")["id"] == "book:daodejing"
    # 标题/名称
    assert xz.node_info("脏腑辨证")["id"] == "topic:脏腑辨证"
    # 前缀优先级：书名带括注，「道德经」应命中典籍而非旁参节点
    assert xz.node_info("道德经")["id"] == "book:daodejing"
    # 查无：None 而非臆造
    assert xz.node_info("不存在的节点") is None
    assert xz.node_info("") is None
    assert xz.node_info(None) is None


def test_neighbors_and_relation_text():
    rels = xz.neighbors("book:daodejing")
    assert len(rels) == 5
    dirs = {r["dir"] for r in rels}
    assert dirs == {"out", "in"}, "双向邻接缺方向"
    texts = [xz.relation_text(r) for r in rels]
    assert any(t == "道德经（老子） 属于 道德真经" for t in texts), texts
    assert any("同传统" in t for t in texts)
    assert xz.neighbors("查无此节点") == []
    # 权重后缀规则
    topic_rel = [r for r in xz.neighbors("art:2025-11-02_脾好不好看大便，肾强不强看小便，身体的“诚实报告”")
                 if r["edge"]["type"] == "has_topic" and r["edge"]["to"] == "topic:脏腑辨证"][0]
    assert xz.relation_text(topic_rel).endswith("（命中 135 次）")


def test_search():
    hits = xz.search("黄庭")
    assert len(hits) == 3 and all("huangting" in h["id"] for h in hits)
    assert xz.search("") == []
    assert xz.search("脏腑")[0]["id"] == "topic:脏腑辨证"


def test_layers():
    ls = xz.layers()
    assert len(ls) == 6
    counts = {l["id"]: l["count"] for l in ls}
    assert counts == {"daozang": 23, "classics": 12, "topics": 7,
                      "external": 10, "corpus": 15, "guidance": 8}
    assert len(xz.by_layer("classics")) == 12


def test_summary_plain_text():
    lines = xz.summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    assert "75 节点 / 77 关系" in joined
    assert "无出处不建" in joined  # 纪律口径
    assert "xiuzhen edges" in joined  # CLI 路径提示


def _run_cli(*argv):
    return subprocess.run(
        [sys.executable, "-m", "sysweeper", "xiuzhen", *argv],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": "src/python", "PATH": "/usr/bin:/bin"},
    )


def test_cli_actions():
    r = _run_cli()
    assert r.returncode == 0 and "75 节点 / 77 关系" in r.stdout
    r = _run_cli("edges", "book:daodejing")
    assert r.returncode == 0 and "道德经（老子） 属于 道德真经" in r.stdout
    r = _run_cli("search", "黄庭")
    assert r.returncode == 0 and "book:huangting-neijing" in r.stdout
    r = _run_cli("show", "道德经")
    assert r.returncode == 0 and "典籍 / classics" in r.stdout
    r = _run_cli("show", "查无")
    assert r.returncode == 0 and "不在图谱中" in r.stdout, "查无必须诚实说明"
    r = _run_cli("layers")
    assert r.returncode == 0 and "采集层" in r.stdout
    r = _run_cli("list", "--layer", "classics")
    assert r.returncode == 0 and "book:cantongqi" in r.stdout
