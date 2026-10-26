"""开源 Windows 分析学习应用只读诊断测试（v0.6.76 新建）。

守门同范式（与 test_radio / test_legacy / test_reverse 一致）：
- data/winternals_refs.json 的 13 条 items 须 schema 完整、官方源域名核验、存疑项挂 needs_verify；
- native/winternals.py 须真正消费 data 层（REFS=13、WINTERNALS_CHECKS 六维度全回链真实 key）；
- 五段只读报告 + 聚合报告须含红线 token；绝不启动任何工具、绝不 DMA；
- **跨系统先认系统与硬件**：目标环境判定须先于目录核验，判为 Windows 时不得摆 Linux 路径；
- 四任务在 registry 注册、native 动作可解析、subsystems 单一事实源登记。
"""

import json
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

from sysweeper.native import winternals as w  # noqa: E402
from sysweeper import registry  # noqa: E402

DATA = os.path.join(ROOT, "src", "python", "sysweeper", "data", "winternals_refs.json")

REQUIRED_FIELDS = ("key", "name", "org", "url", "protocols", "interfaces",
                   "docs", "summary", "advice", "evidence_status")

# 官方源域名白名单（OS 重实现 / 工具官网 / 微软官方文档 / 内核结构参考 / 许可文本 / 开发环境官网）
OFFICIAL_DOMAINS = ("github.com", "www.reactos.org", "www.winehq.org",
                    "ghidra-sre.org", "x64dbg.com", "www.radare.org",
                    "cutter.re", "learn.microsoft.com", "www.vergiliusproject.com",
                    "www.geoffchappell.com", "www.gnu.org", "www.aardio.com")


# ─────────────────────────────────────────────────────────────────────────── #
# 知识层 schema 守门                                                             #
# ─────────────────────────────────────────────────────────────────────────── #
def test_refs_schema_complete():
    """winternals_refs.json 的 13 条 items 须 schema 完整（十个字段非空）。"""
    with open(DATA, encoding="utf-8") as fh:
        doc = json.load(fh)
    items = doc.get("items") or []
    assert len(items) == 13, len(items)
    for it in items:
        for field in REQUIRED_FIELDS:
            assert it.get(field), (it.get("key"), field)
        assert isinstance(it["protocols"], list) and it["protocols"]
        assert isinstance(it["interfaces"], list) and it["interfaces"]
        assert isinstance(it["docs"], list) and it["docs"]


def test_refs_official_sources_and_needs_verify():
    """官方源域名须落在白名单内；不能逐条核实的条目须挂 needs_verify。"""
    with open(DATA, encoding="utf-8") as fh:
        doc = json.load(fh)
    urls = [ref.get("url", "") for ref in doc.get("references", [])]
    assert urls, "references 不能为空"
    for u in urls:
        assert any(d in u for d in OFFICIAL_DOMAINS), u
    nv = [it["key"] for it in doc["items"] if it.get("needs_verify")]
    assert nv, "至少应有 1 条 needs_verify"


def test_fs_and_runtime_dims_present():
    """用户要求的两条硬约束须在知识层有落点：文件系统/目录约定 + 运行语言环境。"""
    keys = {it["key"] for it in json.load(open(DATA, encoding="utf-8"))["items"]}
    assert "winternals-fs-layout" in keys
    assert "winternals-runtime-envs" in keys


# ─────────────────────────────────────────────────────────────────────────── #
# native 层消费 data 层                                                          #
# ─────────────────────────────────────────────────────────────────────────── #
def test_native_consumes_data_layer():
    """native/winternals.py 须真正消费 data 层（REFS=13，非孤儿）。"""
    assert len(w.REFS) == 13
    ref = w.reference("winternals-fs-layout")
    assert ref.get("org") and ref.get("url")
    assert w.reference("no-such-key") == {}


def test_checks_backlink_to_kb():
    """WINTERNALS_CHECKS 六维度回链的知识库 key 必须真实存在。"""
    assert set(w.WINTERNALS_CHECKS) == {
        "target_env", "fs_layout", "runtime_env",
        "toolchain", "anchors", "redline"}
    for _doc, _desc, keys in w.WINTERNALS_CHECKS.values():
        for k in keys:
            assert w.reference(k), k


def test_doc_list_lists_kb_items():
    """doc_list 须列出 13 条知识条目（带 [key] 标记）。"""
    lines = w.doc_list()
    assert len(lines) == 13
    assert all(ln.startswith("· [") for ln in lines)


# ─────────────────────────────────────────────────────────────────────────── #
# 跨系统第一原则：先定系统、再谈目录                                              #
# ─────────────────────────────────────────────────────────────────────────── #
def test_target_env_detection_precedes_dirs():
    """目标环境须先判定，且每种环境都有各自的文件系统与目录约定表。"""
    assert w.detect_target_env() in set(w.TARGET_FS), w.detect_target_env()
    for env, spec in w.TARGET_FS.items():
        assert spec.get("fs"), env          # 文件系统口径
        assert spec.get("dirs"), env        # 目录约定
        assert spec.get("sep"), env         # 路径分隔
    ok, msg = w.target_env_report()
    assert ok is True
    assert "判定结果" in msg and "路径分隔符" in msg
    assert "不挂载卸载" in msg              # 红线


def test_fs_layout_follows_target_env(monkeypatch):
    """判为 Windows 时须摆 Windows 盘符目录，不得拿 Linux FHS 去套。"""
    monkeypatch.setattr(w, "detect_target_env", lambda: "windows")
    _ok, msg = w.fs_layout_report()
    assert r"C:\Windows" in msg
    assert "SysWOW64" in msg
    # Windows 目标下的**目录清单**必须是 Windows 盘符路径，不能混进 Linux FHS 目录
    listed = " ".join(ln for ln in msg.splitlines()
                      if ln.strip().startswith(("✓", "✗")))
    assert r"C:\Windows" in listed
    for linux_dir in ("/etc", "/proc", "/var", "/usr"):
        assert linux_dir not in listed, linux_dir
    assert "不挂载" in msg


def test_fs_layout_on_linux_uses_fhs(monkeypatch):
    """判为 Linux 时按 FHS 核验（沙箱实测：/etc·/usr·/var 等）。"""
    monkeypatch.setattr(w, "detect_target_env", lambda: "linux")
    _ok, msg = w.fs_layout_report()
    for d in ("/etc", "/usr", "/var", "/proc"):
        assert d in msg


def test_runtime_env_two_sides(monkeypatch):
    """运行语言环境两头都要看：目标 ABI + 工具链自身语言依赖。"""
    monkeypatch.setattr(w, "detect_target_env", lambda: "windows")
    ok, msg = w.runtime_env_report()
    assert ok is True
    assert "PE" in msg and "Win32" in msg   # 目标侧 ABI
    assert "JVM" in msg and "Python 3" in msg  # 工具链侧语言环境
    assert "不安装任何运行时" in msg         # 红线


# ─────────────────────────────────────────────────────────────────────────── #
# 工具链盘点 + 内核锚点 + 红线 token                                             #
# ─────────────────────────────────────────────────────────────────────────── #
def test_toolchain_report_never_launches():
    """工具链报告：只探测路径存在性；绝不出现任何启动行为。"""
    ok, msg = w.toolchain_report()
    assert "只 which" in msg and "绝不启动" in msg
    for tool in ("ghidraRun", "r2", "cutter", "x64dbg"):
        assert tool in msg
    # DMA / 内核写类工具只登记存在性
    assert "pcileech" in msg
    assert "不 DMA" in msg


def test_anchors_report_license_purity():
    """锚点报告须含可对读路径与许可纯度 + 诚实边界。"""
    ok, msg = w.internals_anchors_report()
    assert ok is True
    assert "ReactOS" in msg and "Wine" in msg and "Driver Samples" in msg
    assert "许可纯度" in msg
    assert "诚实边界" in msg


# ─────────────────────────────────────────────────────────────────────────── #
# 聚合报告与能力自检                                                            #
# ─────────────────────────────────────────────────────────────────────────── #
def test_winternals_report_five_sections():
    """聚合报告须含 5 段 + 红线（绝不驱动任何真实的写入与注入）。"""
    _ok, msg = w.winternals_report()
    for title in ("目标环境判定", "文件系统与目录约定", "运行语言环境",
                  "分析工具链存在性", "内核锚点与许可纯度"):
        assert title in msg, title
    assert "绝不驱动任何真实的写入与注入" in msg   # _SELF_POSITION 红线


def test_capabilities_report_lists_count():
    """能力自检须含 13 条知识回链计数 + 红线。"""
    ok, msg = w.capabilities_report()
    assert ok is True
    assert "知识条目回链：13 条" in msg


# ─────────────────────────────────────────────────────────────────────────── #
# 只读不变量：绝不执行 / 绝不联网                                                #
# ─────────────────────────────────────────────────────────────────────────── #
def test_no_execute_or_network_in_layer():
    """只读不变量：native 层不得出现执行/网络类调用（shutil.which 仅探测，允许）。"""
    src = open(w.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket.", "requests",
                "urllib", "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, bad


# ─────────────────────────────────────────────────────────────────────────── #
# 四入口接线                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #
def test_tasks_registered():
    """四任务须在 registry 注册。"""
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("winternals_target_env", "winternals_runtime_env",
                "winternals_toolchain", "winternals_anchors"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("winternals_")}) == 4


def test_task_native_actions_resolvable():
    """每个 native 动作须能解析到 winternals 模块的真实函数。"""
    for t in registry.all_tasks():
        if not t.id.startswith("winternals_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(w, fn_name), (t.id, fn_name)


def test_subsystem_registered():
    """subsystems 单一事实源须登记 winternals（fn=winternals_report）。"""
    from sysweeper.native.subsystems import BY_KEY
    sub = BY_KEY.get("winternals")
    assert sub is not None
    assert sub.fn == "winternals_report"
    assert sub.module == "winternals"
    _ok, rep = getattr(w, sub.fn)()
    assert "开源 Windows" in rep


def test_linkage_has_winternals_axes():
    """联动轴须接入 winternals（孤岛清零依赖此条）。"""
    from sysweeper.native import linkage
    ends = {ax.from_key for ax in linkage.all_axes()} | \
           {ax.to_key for ax in linkage.all_axes()}
    assert "winternals" in ends
    assert linkage.isolated() == []
