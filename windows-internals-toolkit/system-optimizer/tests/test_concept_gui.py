"""圆光术概念系统拓扑 GUI 测试（tools/gen_concept_gui.py → concept_gui.html）。

覆盖四件事：
  1. 生成器可产出合法单文件静态页（DOCTYPE / data-sha256 标记 / 无残留 token）；
  2. 数据忠实——页面烘焙的 11 系统、边矩阵、外部靶与 topo() 实时实测完全一致；
  3. 同步纪律——同数据多次生成摘要稳定；数据变了（或标记被篡改）--check 必须失败；
  4. 圆光术范式落地——中心 / 环 / 光晕 / 矩阵 / 图例齐备，且离线（不连外部资源）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "gen_concept_gui.py"
HTML = ROOT / "concept_gui.html"
sys.path.insert(0, str(ROOT / "src" / "python"))

from sysweeper import concepts as C  # noqa: E402

EXPECTED = ["plang", "netsys", "daoxue", "quantum", "comp",
            "apilab", "zhuangzi", "baigong", "datong", "protec", "sciences"]


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GEN), *args],
                          capture_output=True, text=True, timeout=180)


def _baked_data(html_text: str) -> dict:
    m = re.search(r"const DATA = (\{.*?\});\n", html_text, re.S)
    assert m, "页面缺少烘焙数据（const DATA = {...}）"
    return json.loads(m.group(1))


def test_generate_writes_synced_page(tmp_path):
    """生成器可运行，产物是完整单文件页且带 data-sha256 标记。"""
    out = tmp_path / "concept_gui.html"
    r = _run("--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert re.search(r"data-sha256:[0-9a-f]{64}", html)
    assert not re.search(r"__[A-Z_]+__", html), "存在未替换的模板 token"


def test_check_passes_on_fresh_generation(tmp_path):
    """刚生成的页面必须通过 --check（默认路径与 --out 路径两条都验）。"""
    out = tmp_path / "concept_gui.html"
    assert _run("--out", str(out)).returncode == 0
    assert _run("--check", "--out", str(out)).returncode == 0
    assert _run("--check").returncode == 0  # 仓库内已提交页面同步


def test_check_detects_tampered_marker(tmp_path):
    """标记被篡改（或概念数据已变而页面未重烘焙）时 --check 必须失败。"""
    out = tmp_path / "concept_gui.html"
    assert _run("--out", str(out)).returncode == 0
    tampered = re.sub(r"data-sha256:[0-9a-f]{64}", "data-sha256:" + "0" * 64,
                      out.read_text(encoding="utf-8"))
    out.write_text(tampered, encoding="utf-8")
    r = _run("--check", "--out", str(out))
    assert r.returncode == 1
    assert "不一致" in r.stdout or "缺少" in r.stdout


def test_data_digest_stable_across_runs(tmp_path):
    """同一数据多次生成，data-sha256 稳定（摘要剔除生成时间）。"""
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    assert _run("--out", str(a)).returncode == 0
    assert _run("--out", str(b)).returncode == 0
    da = re.search(r"data-sha256:([0-9a-f]{64})", a.read_text(encoding="utf-8")).group(1)
    db = re.search(r"data-sha256:([0-9a-f]{64})", b.read_text(encoding="utf-8")).group(1)
    assert da == db


def test_baked_data_matches_live_topo():
    """页面烘焙数据与 topo() 实时实测逐项一致（九系统 / 边矩阵 / 出入边 / 外部靶）。"""
    data = _baked_data(HTML.read_text(encoding="utf-8"))
    t = C.topo()
    assert [s["name"] for s in data["systems"]] == EXPECTED == t["systems"]
    live = {(a, b): w for (a, b), w in t["edge"].items() if w}
    baked = {(e[0], e[1]): e[2] for e in data["edges"]}
    assert baked == live, "烘焙边矩阵与 topo() 实测不一致"
    assert sum(e[2] for e in data["edges"]) == sum(live.values())
    for s in data["systems"]:
        assert s["out"] == t["out"][s["name"]]
        assert s["in"] == t["in"][s["name"]]
        assert s["volume"] > 0, f"{s['name']} 体量未取到"
    assert data["external"] == t["external"]
    # 外部靶按来源系统的分组也与逐系统 bridges 实测一致
    for name in EXPECTED:
        expect: dict = {}
        for b in C.load(name).get("bridges", []):
            tgt = b.get("system")
            if tgt and tgt not in t["out"]:
                expect[tgt] = expect.get(tgt, 0) + 1
        assert data["external_by_system"][name] == expect


def test_page_is_offline_and_yuanguang():
    """圆光术范式要素齐备，且纯离线（无外链 / 无 fetch / 无 XHR）。"""
    html = HTML.read_text(encoding="utf-8")
    # 圆：中心 + 环；光：径向渐变光晕；术：聚焦交互 + 9×9 矩阵（整体全息）
    assert "盖亚意识 · 集智体" in html and "道通为一" in html
    assert "radialGradient" in html and "radial-gradient" in html
    assert "9×9 桥接矩阵" in html and "回归整体" in html
    assert "圆光术" in html
    # 离线：不拉外部资源、不发请求
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert not re.search(r'(?:src|href)\s*=\s*"https?://', html)
    assert not re.search(r'url\(\s*["\']?https?://', html)
    assert "@import" not in html


def test_committed_page_is_in_sync():
    """仓库内已提交的 concept_gui.html 必须与实时 taxonomy 同步（CI 纪律）。"""
    r = _run("--check")
    assert r.returncode == 0, r.stdout
    assert "OK" in r.stdout
