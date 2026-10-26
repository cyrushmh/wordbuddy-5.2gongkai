# -*- coding: utf-8 -*-
"""qarch 量子架构内核子系统测试（v0.6.78）。

守门范围：知识层 schema 与官方源、QARCH_CHECKS 回链、doc_list/reference、
内核树在位与降级双路径、纯新增核验（21 既有架构原封 + quantum 注册）、
镜像与内核树一致性、能量激发态模型与 idle=mwait 固化、vmlinux 诚实边界
（已链接事实与「非量子处理器指令」边界都不能退回过时表述）、四入口接线、
红线 token（禁执行禁网络）。

内核树不在位时（如 CI 从 git clone）树相关断言自动降级为「报告不崩」。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import qarch as q          # noqa: E402
from sysweeper.native import subsystems, linkage  # noqa: E402
from sysweeper import registry, ergonomics        # noqa: E402

DATA = os.path.join("src", "python", "sysweeper", "data", "qarch_refs.json")

# 官方源域名白名单（references + items.url）——qarch 只引 kernel.org 一手源
OFFICIAL_HOSTS = {"kernel.org", "docs.kernel.org"}

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
KERNEL_TREE = os.path.join(REPO_ROOT, "quantum-kernel", "linux-6.18.57")
TREE_PRESENT = os.path.isfile(os.path.join(KERNEL_TREE, "Makefile")) and \
    os.path.isdir(os.path.join(KERNEL_TREE, "arch", "quantum"))


@pytest.fixture(scope="module")
def refs_doc():
    with open(DATA, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── 知识层 schema 与官方源 ────────────────────────────────────────────────

def test_refs_schema_ten_fields(refs_doc):
    req = ("key", "name", "org", "url", "protocols", "interfaces",
           "docs", "summary", "advice", "evidence_status")
    items = refs_doc["items"]
    assert len(items) >= 6
    keys = [it["key"] for it in items]
    assert len(keys) == len(set(keys)), "items key 重复"
    for it in items:
        for f in req:
            assert it.get(f), f"{it.get('key')}.{f} 缺失"
        for f in ("protocols", "interfaces", "docs"):
            assert isinstance(it[f], list) and it[f], f"{it['key']}.{f} 需非空列表"


def test_refs_official_sources_only(refs_doc):
    from urllib.parse import urlparse
    urls = [r["url"] for r in refs_doc["references"]]
    urls += [it["url"] for it in refs_doc["items"] if it.get("url")]
    assert urls
    for u in urls:
        host = urlparse(u).netloc.lower()
        assert any(host == h or host.endswith("." + h) for h in OFFICIAL_HOSTS), \
            f"非官方源域名：{host}（{u}）"


def test_qarch_checks_backlinks_resolved():
    for name, (key, desc, links) in q.QARCH_CHECKS.items():
        for lk in links:
            assert q.reference(lk), f"{name} 回链悬空：{lk}"


def test_doc_list_and_reference(refs_doc):
    lst = q.doc_list()
    assert len(lst) == len(q.REFS) and all(l.startswith("· [") for l in lst)
    assert q.reference("qarch-lts-618")["name"]
    assert q.reference("qarch-build-honesty")["evidence_status"] == "repo_verified"
    assert q.reference("no-such-key") == {}


# ── 报告全量 OK（树在位与降级双路径） ─────────────────────────────────────

def test_all_reports_ok():
    for fn in (q.tree_report, q.arch_report, q.qpu_report, q.dist_report,
               q.qarch_report, q.capabilities_report):
        ok, msg = fn()
        assert ok and msg.strip(), fn.__name__


def test_reports_degrade_without_tree(monkeypatch):
    """内核树缺失时所有报告仍返回 ok（不崩、不谎报在位）。"""
    monkeypatch.setattr(q, "_kernel_root", lambda: "")
    for fn in (q.tree_report, q.arch_report, q.qpu_report, q.qarch_report):
        ok, msg = fn()
        assert ok and msg.strip(), fn.__name__
    assert "未找到" in q.tree_report()[1]
    assert "不在位" in q.arch_report()[1]


def test_capabilities_backlinks_all_resolved():
    ok, msg = q.capabilities_report()
    assert ok
    assert "缺失" not in msg, f"capabilities 回链缺失：{msg}"


# ── 内核树在位核验（树缺失时跳过） ─────────────────────────────────────────

@pytest.mark.skipif(not TREE_PRESENT, reason="quantum-kernel 内核树不在位")
class TestKernelTreeInPlace:
    def test_lts_baseline(self):
        ok, msg = q.tree_report()
        assert ok and "6.18.57" in msg

    def test_pure_additive_arch_coverage(self):
        ok, msg = q.arch_report()
        assert ok
        assert "quantum：✓ 已注册" in msg
        assert "既有架构缺失：无" in msg
        # 21 个既有架构一个不动
        assert len(q.EXISTING_ARCHS) == 21
        archdir = os.path.join(KERNEL_TREE, "arch")
        archs = {d for d in os.listdir(archdir)
                 if os.path.isdir(os.path.join(archdir, d))}
        assert set(q.EXISTING_ARCHS) <= archs, "既有架构清单与内核树不符"
        assert "quantum" in archs
        assert len(archs) == 22  # 21 既有 + quantum

    def test_only_three_existing_files_modified(self):
        """纯新增实证：既有文件仅 3 个变更（drivers 两处追加 + 文档索引一行）。"""
        base = os.path.join("/tmp", "kbase", "linux-6.18.57")
        if not os.path.isdir(base):
            pytest.skip("原始基线树 /tmp/kbase 不在位（本地重建后可跑）")
        import subprocess  # noqa: S404  # 仅本测试内 diff 只读命令
        out = subprocess.run(
            ["diff", "-rq", "--no-dereference", base, KERNEL_TREE],
            capture_output=True, text=True, timeout=300)
        changed = [ln for ln in out.stdout.splitlines()
                   if ln.startswith("Files ") and "differ"]
        # 过滤构建产物目录（build/）——仅算既有源码文件
        changed = [ln for ln in changed if "/build/" not in ln]
        assert len(changed) == 3, f"既有文件变更应为 3 个，实为 {changed}"
        joined = "\n".join(changed)
        assert "drivers/Kconfig" in joined
        assert "drivers/Makefile" in joined
        assert "Documentation/index.rst" in joined

    def test_mirror_matches_tree(self):
        """git 侧增量镜像与内核树一一对应（ arch/quantum、drivers/quantum、
        Documentation/quantum、uapi 头）。"""
        gk = os.path.join(REPO_ROOT, "quantum-kernel")
        pairs = [("arch/quantum", "arch/quantum"),
                 ("drivers/quantum", "drivers/quantum"),
                 ("Documentation/quantum", "Documentation/quantum")]
        for a, b in pairs:
            ta, tb = os.path.join(KERNEL_TREE, a), os.path.join(gk, b)
            fa = {os.path.relpath(os.path.join(r, f), ta)
                  for r, _, fs in os.walk(ta) for f in fs}
            fb = {os.path.relpath(os.path.join(r, f), tb)
                  for r, _, fs in os.walk(tb) for f in fs}
            assert fa == fb, f"镜像 {b} 与内核树 {a} 文件集不一致"
        assert os.path.isfile(os.path.join(
            gk, "include", "uapi", "linux", "quantum.h"))

    def test_energy_model_and_idle_mwait_frozen(self):
        """能量激发态模型与 idle=mwait 双引导配置在位（GRUB/LILO）。"""
        root = KERNEL_TREE
        e = open(os.path.join(root, "arch/quantum/kernel/quantum-energy.c"),
                 encoding="utf-8").read()
        for tok in ("quantum_excite", "quantum_relax", "quantum_phase_advance",
                    "quantum_decohere_tick", "quantum_interference",
                    "quantum_measure", "quantum_entangle", "qm_sin"):
            assert tok in e, f"能量模型缺符号：{tok}"
        for cfg in ("arch/quantum/boot/grub.cfg", "arch/quantum/boot/lilo.conf"):
            txt = open(os.path.join(root, cfg), encoding="utf-8").read()
            assert "idle=mwait" in txt, f"{cfg} 缺 idle=mwait"
        doc = open(os.path.join(root, "Documentation/quantum/energy-model.rst"),
                   encoding="utf-8").read()
        assert "idle=mwait" in doc

    def test_page_discipline_4k(self):
        txt = open(os.path.join(KERNEL_TREE, "arch/quantum/include/asm/page.h"),
                   encoding="utf-8").read()
        assert "PAGE_SHIFT\t12" in txt or "PAGE_SHIFT 12" in txt

    def test_patch_series_roundtrip_artifact(self):
        """补丁系列在位且非平凡（60 文件段量级）。

        仅核验基线补丁 `0001-quantum-architecture-v1.patch`（diff -ruN
        拼接，+++ 头为 `linux-6.18.57/...`）；各 LTS 版本补丁由
        gen_version_patch.py 生成、走 git-diff 格式（+++ b/...），不在
        本断言范围内。
        """
        pk = os.path.join(REPO_ROOT, "quantum-kernel", "patches")
        baseline = os.path.join(pk, "0001-quantum-architecture-v1.patch")
        assert os.path.isfile(baseline), "基线补丁缺失"
        size = os.path.getsize(baseline)
        assert size > 100_000, f"补丁体积异常：{size}"
        text = open(baseline, encoding="utf-8", errors="replace").read()
        # 补丁为逐路径组 diff --color -ruN 拼接（file-vs-file 无 diff 头行，
        # 以 unified hunk 与 +++ 行为准），可 patch -p1 回放
        assert "@@" in text and "arch/quantum" in text
        assert "+++ linux-6.18.57" in text

    def test_vmlinux_honesty_boundary_locked(self):
        """诚实边界锁定：vmlinux 已链接的事实与『非量子处理器指令』的边界
        都不能退回过时的『不可达』表述。"""
        vml = os.path.join(KERNEL_TREE, "build", "vmlinux")
        if not os.path.isfile(vml):
            pytest.skip("build/vmlinux 不在位（本地构建后可跑）")
        bh = q.reference("qarch-build-honesty")
        assert "vmlinux" in bh["summary"]
        # vmlinux 本身已链接，不得再称其不可达；但「真实量子硬件上运行
        # 不可达」是必须保留的诚实边界
        assert "vmlinux（不可达" not in bh["summary"]
        assert "vmlinux 不可达" not in bh["summary"]
        assert "整树编译并链接 vmlinux" in bh["summary"]
        assert "宿主" in bh["summary"], "必须保留宿主工具链诚实编译的边界表述"
        assert "不可达" in bh["summary"], "真实量子硬件运行的不可达边界必须保留"
        ok, msg = q.qpu_report()
        assert "vmlinux 产物：✓" in msg


# ── 四入口接线 ────────────────────────────────────────────────────────────

def test_subsystem_registered():
    ks = [s.key for s in subsystems.SUBSYSTEMS]
    assert "qarch" in ks
    sub = next(s for s in subsystems.SUBSYSTEMS if s.key == "qarch")
    assert sub.layer and "内核" in sub.layer  # omni 系统域归类条件


def test_linkage_not_isolated():
    assert linkage.isolated() == []
    assert linkage.dangling() == []
    deg = linkage.degrees()
    assert deg.get("qarch", {}).get("total", 0) >= 1


def test_tasks_registered():
    ids = [t.id for t in registry.all_tasks() if t.id.startswith("qarch_")]
    assert len(ids) == 2
    for t in registry.all_tasks():
        if t.id.startswith("qarch_"):
            assert t.platform == "any"
            assert t.category in ("arch", "hardware")
            assert t.risk == "low"


def test_ergonomics_grouped():
    st = ergonomics.stats()
    assert st["ungrouped"] == [] and st["phantom"] == []
    assert st["scenes"] == 12  # 场景数不变
    assert "qarch" in ergonomics.grouped_commands()  # 概念与知识场景已收录


def test_cli_subcommand_wired():
    from sysweeper import cli
    assert hasattr(cli, "cmd_qarch")
    import argparse
    p = cli.build_parser()
    ns = p.parse_args(["qarch", "arch"])
    assert ns.qarch_action == "arch"


def test_gui_method_wired():
    src = open(os.path.join("src", "python", "sysweeper", "gui.py"),
               encoding="utf-8").read()
    assert "def show_qarch" in src and "量子内核" in src


# ── 红线 ─────────────────────────────────────────────────────────────────

def test_redline_tokens_absent_from_source():
    src = open(q.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket", "requests", "urllib",
                "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, f"红线 token 出现在源码：{bad}"


def test_no_build_execution_in_source():
    """绝不执行内核构建/写树/加载模块的设施不存在。"""
    src = open(q.__file__, encoding="utf-8").read()
    for bad in ("make ", "modprobe", "insmod", "O=build"):
        assert bad not in src, f"构建执行 token 出现在源码：{bad}"
