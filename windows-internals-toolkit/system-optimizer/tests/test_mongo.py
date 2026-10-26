"""MongoDB 权威指南（第2版）知识索引（mongo + CLI）最小冒烟验证。

覆盖：数据完整性（23 章连续/43 概念/16 调优、概念 chapter 引用非悬空）、
章节与概念查询（查无返回 None）、按类别过滤、检索、第 23 章系统调优条目
与 sysweeper 任务/子命令的交叉对账（必须真实存在）、版权边界说明、CLI 子命令。
"""

import subprocess
import sys

sys.path.insert(0, "src/python")

from sysweeper.native import mongo_catalog as mg  # noqa: E402


def test_data_completeness():
    data = mg.map_data()
    counts = data["meta"]["counts"]
    assert counts == {"parts": 6, "chapters": 23, "appendixes": 2,
                      "concepts": 43, "sysops": 16, "concept_categories": 9}, counts
    nos = [c["no"] for c in data["chapters"]]
    assert nos == list(range(1, 24)), "章节号必须 1..23 连续"
    # 概念/调优的 chapter 引用非悬空
    chapter_set = set(nos)
    assert all(c["chapter"] in chapter_set for c in data["concepts"])
    assert all(s["chapter"] in chapter_set for s in data["sysops"])
    # 每个概念的类别都已登记
    assert all(c["category"] in mg.categories() for c in data["concepts"])


def test_chapter_and_concepts():
    c = mg.chapter(23)
    assert c is not None and c["title"] == "部署MongoDB"
    assert len(c["sections"]) == 24
    assert "23.3.3 禁用大内存页面" in c["sections"]
    # 部分过滤
    assert len(mg.chapters("p3")) == 4, "第三部分为复制（9-12 章）"
    assert [c["no"] for c in mg.chapters("p4")] == [13, 14, 15, 16]
    # 查无
    assert mg.chapter(99) is None
    assert mg.chapter("x") is None
    assert mg.chapter(None) is None
    # 类别过滤
    idx = mg.concepts("index")
    assert idx and all(c["category"] == "index" for c in idx)
    assert len(mg.concepts()) == 43


def test_search():
    hits = mg.search("副本集")
    assert hits and any(h["kind"] == "concept" for h in hits)
    assert mg.search("") == []
    # 调优条目也可被检索到
    assert any(h["kind"] == "sysop" for h in mg.search("NUMA"))


def test_sysops_and_cross_ref():
    ops = mg.sysops()
    assert len(ops) == 16
    assert all(o["chapter"] == 23 for o in ops)
    # 三条带任务 id 的引用，运行期必须都能在 registry 中找到（不臆造引用）
    refs = {r["sysweeper_task"]: r for r in mg.cross_ref() if r.get("sysweeper_task")}
    assert set(refs) == {"linux_swappiness", "linux_thp_compaction", "linux_io_scheduler"}
    for tid, r in refs.items():
        assert r["task_exists"] is True, "任务不存在: %s" % tid
        assert r["command_exists"] is True, "子命令不存在: %s" % r["sysweeper_cmd"]


def test_copyright_note_present():
    bk = mg.book()
    assert "仅供您个人使用" in bk.get("copyright_note", "")
    assert "不入库" in bk.get("archiving_note", "")
    assert bk["book"]["isbn"] == "978-7-115-34108-2"
    assert len(bk["book"]["pdf_sha256"]) == 64  # 原件哈希留档备核


def test_summary_plain_text():
    lines = mg.summary()
    assert isinstance(lines, list) and lines
    joined = "\n".join(lines)
    assert "23 章" in joined and "43 概念" in joined
    assert "版权边界" in joined
    assert "mongo deploy" in joined  # CLI 路径提示


def _run_cli(*argv):
    return subprocess.run(
        [sys.executable, "-m", "sysweeper", "mongo", *argv],
        capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": "src/python", "PATH": "/usr/bin:/bin"},
    )


def test_cli_actions():
    r = _run_cli()
    assert r.returncode == 0 and "23 章" in r.stdout
    r = _run_cli("show", "23")
    assert r.returncode == 0 and "禁用大内存页面" in r.stdout
    r = _run_cli("show", "99")
    assert r.returncode == 0 and "不在索引中" in r.stdout, "查无必须诚实说明"
    r = _run_cli("chapters", "--part", "p3")
    assert r.returncode == 0 and "创建副本集" in r.stdout
    r = _run_cli("concepts", "--cat", "sharding")
    assert r.returncode == 0 and "片键" in r.stdout
    r = _run_cli("search", "journal")
    assert r.returncode == 0 and "持久性" in r.stdout
    r = _run_cli("deploy")
    assert r.returncode == 0 and "sysweeper" in r.stdout
    r = _run_cli("cross")
    assert r.returncode == 0 and "存在" in r.stdout
    r = _run_cli("book")
    assert r.returncode == 0 and "ISBN" in r.stdout and "版权" in r.stdout
