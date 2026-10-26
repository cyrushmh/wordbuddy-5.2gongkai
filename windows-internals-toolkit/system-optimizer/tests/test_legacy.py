"""遗留/嵌入式/兼容层只读诊断测试（吸收 DOS 3.1 等 · busybox · dosbox）。

红线：仅 shutil.which + 目录存在性 + 版本/包管理只读查询；绝不运行 DOS/DOSEMU/
DOSBox、不写镜像、不连校外网。版本/安装查询只取命令首行或只读元数据。
"""

import sys

import pytest

sys.path.insert(0, "src/python")
from sysweeper.native import legacy  # noqa: E402


def test_legacy_report_shape():
    ok, msg = legacy.legacy_report()
    # ok 反映本机是否检测到三项之一；干净沙箱上为 False 也合法，只校验形态
    assert isinstance(ok, bool)
    assert isinstance(msg, str) and msg
    for token in ("FreeDOS", "busybox", "dosbox", "红线", "sysmap"):
        assert token in msg


def test_dos_report_knowledge_present():
    ok, msg = legacy.dos_report()
    assert isinstance(ok, bool)  # 干净沙箱上无 FreeDOS 时 ok=False 合法
    assert "MS-DOS 3.1" in msg
    assert "livemedia" in msg  # 关联：DOS↔可启动介质


def test_busybox_detected_via_which(monkeypatch):
    """busybox 被 which 命中时，应判为已安装并取版本。"""
    real_which = legacy.shutil.which

    def fake_which(cmd):
        if cmd == "busybox":
            return "/bin/busybox"
        return real_which(cmd)

    monkeypatch.setattr(legacy.shutil, "which", fake_which)
    _ok, msg = legacy.busybox_report()
    assert "busybox 版本" in msg
    assert "✓" in msg


def test_missing_all_markers_no_crash(monkeypatch):
    """所有工具 which 均为 None、关键目录不存在时，三报告都不崩且标缺失。"""
    monkeypatch.setattr(legacy.shutil, "which", lambda _cmd: None)
    monkeypatch.setattr(legacy.os.path, "isdir", lambda _p: False)
    monkeypatch.setattr(legacy.os.path, "islink", lambda _p: False)
    monkeypatch.setattr(legacy.os.path, "exists", lambda _p: False)
    for fn in (legacy.dos_report, legacy.busybox_report, legacy.dosbox_report):
        ok, msg = fn()
        assert ok is False
        assert isinstance(msg, str) and msg


def test_sysmap_includes_legacy_probes():
    """sysmap 须把三项遗留/嵌入式/兼容层纳入编排（嵌入整体系统）。"""
    from sysweeper.native import sysmap
    keys = [p[0] for p in sysmap.PROBES]
    for k in ("dos", "busybox", "dosbox"):
        assert k in keys
    # 关联图须体现你中有我
    rel_pairs = [(a, b) for a, b, _ in sysmap.RELATIONS]
    assert ("busybox 嵌入式用户态", "KaihongOS 发行版") in rel_pairs
    assert ("dosbox 模拟兼容层", "Proton 兼容层") in rel_pairs
    assert ("遗留 DOS 环境", "可启动介质制作能力") in rel_pairs


# --------------------------------------------------------------------------- #
# v0.6.74：dos/busybox/dosbox 知识层消费 + 位宽世代 + PAE                          #
# --------------------------------------------------------------------------- #
def test_refs_schema_complete():
    """三个 data 层 items 的 schema 须完整（与 reverse/hmosstd 同范式）。"""
    import json
    for name, expect in (("dos", 5), ("busybox", 4), ("dosbox", 3)):
        path = ("src/python/sysweeper/data/%s.json" % name)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        items = doc.get("items") or []
        assert len(items) == expect, name
        for it in items:
            for field in ("key", "name", "org", "url", "protocols", "interfaces",
                          "docs", "summary", "advice", "evidence_status"):
                assert it.get(field), (name, it.get("key"), field)
            assert isinstance(it["protocols"], list) and it["protocols"]
            assert isinstance(it["interfaces"], list) and it["interfaces"]
            assert isinstance(it["docs"], list) and it["docs"]


def test_refs_official_sources_and_needs_verify():
    """官方源域名须核验过；不能逐条核实的条目须挂 needs_verify（诚实边界）。"""
    import json
    official = {
        "dos": ("freedos.org", "dosemu2.org", "wiki.osdev.org"),
        "busybox": ("busybox.net", "git.busybox.net"),
        "dosbox": ("dosbox.com", "dosbox-x.com"),
    }
    for name, domains in official.items():
        with open("src/python/sysweeper/data/%s.json" % name, encoding="utf-8") as fh:
            doc = json.load(fh)
        urls = [r.get("url", "") for r in doc.get("references", [])]
        assert urls, name
        for u in urls:
            assert any(d in u for d in domains), (name, u)
        # needs_verify 挂牌：每库至少一条（历史细节/版本线/衍生线未逐条核实）
        nv = [it["key"] for it in doc["items"] if it.get("needs_verify")]
        assert nv, name


def test_legacy_native_consumes_data_layer():
    """native/legacy.py 须真正消费 data 层（_load_refs 范式，非孤儿）。"""
    assert len(legacy.DOS_REFS) == 5
    assert len(legacy.BUSYBOX_REFS) == 4
    assert len(legacy.DOSBOX_REFS) == 3
    assert len(legacy.COMPAT_REFS) == 2  # compat_docs 的 bitwidth/pae
    assert len(legacy.LEGACY_REFS) == 14
    # reference() 命中与未命中
    freedos = legacy.reference("freedos-1.4")
    assert freedos.get("org") and freedos.get("url")
    # compat 主题（bitwidth/pae）也能回链
    for k in ("bitwidth", "pae"):
        ref = legacy.reference(k)
        assert ref.get("name") and ref.get("org"), k
    assert legacy.reference("no-such-key") == {}


def test_legacy_checks_backlink_to_kb():
    """LEGACY_CHECKS 每项回链的知识库 key 必须真实存在（5 个只读维度）。"""
    assert set(legacy.LEGACY_CHECKS) == {
        "dos_env", "busybox_env", "dosbox_env", "bitwidth_cap", "pae_support"}
    for ck, (_doc, _desc, keys) in legacy.LEGACY_CHECKS.items():
        for k in keys:
            assert legacy.reference(k), (ck, k)


def test_doc_list_lists_kb_items():
    lines = legacy.doc_list()
    assert len(lines) == 14
    assert any("[freedos-1.4]" in ln for ln in lines)
    assert any("[bitwidth]" in ln for ln in lines)


def test_bitwidth_report_matrix():
    """位宽世代能力矩阵：8/16/32/64 五行 + 本机 flags + 红线，全部只读。"""
    ok, msg = legacy.bitwidth_report()
    assert isinstance(ok, bool)
    for token in ("8 位世代", "16 位实模式", "32 位保护模式",
                  "32 位+PAE", "64 位长模式",
                  "MAME", "dosbox", "qemu-i386", "红线", "不启动任何模拟器"):
        assert token in msg, token


def test_bitwidth_reads_cpuinfo_flags(monkeypatch):
    """monkeypatch cpuinfo 后，矩阵须从 flags 读 lm/pae（不写任何东西）。"""
    fake = {"flags": "fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov "
                     "pat pse36 clflush mmx fxsr sse sse2 lm"}
    monkeypatch.setattr(legacy, "_cpuinfo", lambda: fake)
    ok, msg = legacy.bitwidth_report()
    assert "lm 标志" in msg or "lm" in msg
    assert "pae 标志=✓" in msg


def test_pae_report_windows_and_honesty():
    """PAE 报告：Windows 32 位官方命令文本 + XP 4GB 诚实边界 + 红线。"""
    _ok, msg = legacy.pae_report()
    for token in ("boot.ini", "/PAE", "bcdedit", "pae ForceEnable",
                  "4GB", "诚实边界", "红线", "不代改"):
        assert token in msg, token
    # 微软官方口径：XP 全版本上限即 4GB，开 PAE 不为突破 4GB
    assert "不是突破 4GB" in msg


def test_pae_report_conclusion_by_kernel(monkeypatch):
    """按内核位宽给结论：64 位不需 PAE；32 位 x86 须自查 HIGHMEM/X86_PAE。"""
    monkeypatch.setattr(legacy, "_kernel_bits", lambda: ("x86_64", "64 位"))
    _ok, msg = legacy.pae_report()
    assert "64 位内核原生全寻址，不需要也不支持 PAE" in msg
    monkeypatch.setattr(legacy, "_kernel_bits", lambda: ("i686", "32 位"))
    monkeypatch.setattr(legacy, "_cpuinfo",
                        lambda: {"flags": "fpu de pse tsc msr pae mce cx8 apic"})
    _ok, msg = legacy.pae_report()
    assert "HIGHMEM64G" in msg and "X86_PAE" in msg


def test_pae_report_no_flags_no_crash(monkeypatch):
    """读不到 cpuinfo（非 Linux）时不崩，结论落「不适用」。"""
    monkeypatch.setattr(legacy, "_cpuinfo", lambda: {})
    monkeypatch.setattr(legacy, "_kernel_bits", lambda: ("s390x", "64 位"))
    _ok, msg = legacy.pae_report()
    assert "64 位内核原生全寻址" in msg


def test_legacy_report_covers_five_sections():
    """聚合报告须含 5 段（dos/busybox/dosbox/位宽/PAE）+ 红线。"""
    _ok, msg = legacy.legacy_report()
    for title in ("遗留 DOS 环境", "busybox 嵌入式用户态", "dosbox DOS 模拟兼容层",
                  "位宽世代能力矩阵", "PAE 现状与开启指引"):
        assert title in msg, title
    assert "不代改任何引导配置" in msg


def test_capabilities_report_lists_five():
    ok, msg = legacy.capabilities_report()
    assert ok is True
    assert "知识条目回链：14 条" in msg


def test_no_execute_or_network_in_layer():
    """只读不变量：native 层不得出现执行/网络类调用。"""
    src = open(legacy.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket.", "requests", "urllib",
                "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, bad


def test_tasks_registered_bitwidth_pae():
    from sysweeper import registry
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("legacy_bitwidth", "legacy_pae"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("legacy_")}) == 5
