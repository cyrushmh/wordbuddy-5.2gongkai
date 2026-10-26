"""v0.5.19 第三方网络互联互通/硬件优化/开源下载 引用 + 许可证归档 + 安全护栏 测试。

设计要点（与全局一致）：纯 stdlib、离线、只读引用、不打包第三方二进制；
第三方引用只作可选方案登记到「网络互联互通共享资源 / 硬件优化 / 开源下载」，
安全护栏：同人共享只限本人授权网络与算力，绝不盗用他人网络互联、绝不共享个人数据与关键资产。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 让 tests/ 能 import src/python 下的包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

# 仓库根（tests/ 的上一级）
REPO_ROOT = Path(__file__).resolve().parent.parent
LICENSES_DIR = REPO_ROOT / "licenses"

ALL_REFS = {
    "p2wlan": ("MIT", "network-interop"),
    "dae": ("AGPL-3.0", "network-interop"),
    "gfw-pac": ("Apache-2.0", "network-interop"),
    "v2rayn": ("GPL-3.0", "network-interop"),
    "dlss5-swapper": ("MIT", "hardware-opt"),
    "aria2": ("GPL-2.0", "downloader"),
}
LICENSE_FILES = {
    "MIT.txt", "Apache-2.0.txt", "GPL-2.0.txt", "GPL-3.0.txt", "AGPL-3.0.txt",
}


@pytest.fixture
def thirdparty():
    from sysweeper.native import thirdparty as T
    return T


def test_thirdparty_refs_loaded(thirdparty):
    """数据文件全部 6 个引用载入，且 license/role 正确。"""
    for rid, (lic, role) in ALL_REFS.items():
        d = thirdparty.reference(rid)
        assert d, f"缺少引用 {rid}"
        assert d.get("license") == lic, f"{rid} 许可证应为 {lic}，实际 {d.get('license')}"
        assert d.get("role") == role, f"{rid} 用途应为 {role}"
        assert d.get("url", "").startswith("https://github.com/"), f"{rid} 缺仓库链接"
        assert d.get("license_url", "").startswith("http"), f"{rid} 缺许可证全文链接"


def test_thirdparty_roles(thirdparty):
    """按 role 过滤正确。"""
    assert set(thirdparty.list_interop()) == {"p2wlan", "dae", "gfw-pac", "v2rayn"}
    assert set(thirdparty.list_hw_opt()) == {"dlss5-swapper"}
    assert set(thirdparty.list_downloaders()) == {"aria2"}


def test_thirdparty_cdn_p2p_switches(thirdparty):
    """CDN / P2P 开关均存在且语义正确。"""
    sw = thirdparty.cdn_p2p_switches()
    assert set(sw) == {"cdn", "p2p"}
    assert "HTTP" in ", ".join(sw["cdn"]["protocols"])
    assert "BitTorrent" in ", ".join(sw["p2p"]["protocols"])
    ok, msg = thirdparty.cdn_p2p_report()
    assert ok and "CDN" in msg and "P2P" in msg


def test_thirdparty_reports_return_tuple(thirdparty):
    """各报告函数返回 (bool, str) 且非空。"""
    for fn in (thirdparty.interop_refs_report, thirdparty.hw_opt_report,
               thirdparty.downloader_report, thirdparty.licenses_report,
               thirdparty.cdn_p2p_report):
        ok, msg = fn()
        assert isinstance(ok, bool) and isinstance(msg, str) and msg, fn


def test_thirdparty_licenses_folder_present():
    """licenses/ 文件夹存在，且含全部许可证文件与索引 README。"""
    assert LICENSES_DIR.is_dir(), "缺少 licenses/ 文件夹"
    present = set(os.listdir(LICENSES_DIR))
    for f in LICENSE_FILES:
        assert f in present, f"licenses/ 缺少 {f}"
    assert "README.md" in present, "licenses/ 缺少 README.md 索引"
    # 各许可证文件内含官方全文链接
    for f in LICENSE_FILES:
        text = (LICENSES_DIR / f).read_text(encoding="utf-8")
        assert "http" in text, f"{f} 应含官方全文链接"


def test_thirdparty_licenses_index_covers_all_repos(thirdparty):
    """licenses/README.md 索引覆盖全部导入仓库链接。"""
    idx = (LICENSES_DIR / "README.md").read_text(encoding="utf-8")
    for rid in ALL_REFS:
        url = thirdparty.reference(rid).get("url", "")
        assert url and url in idx, f"索引未覆盖 {rid}（{url}）"


def test_thirdparty_tasks_registered_and_opt_in():
    """任务全部注册；第三方网络/硬件任务默认关闭（opt_in），安全护栏默认非 opt_in。"""
    from sysweeper.registry import all_tasks
    by = {t.id: t for t in all_tasks()}
    for tid in ("net_interop_refs", "net_interop_cdn_p2p", "hw_dlss_swapper",
                "hw_dl_open_download"):
        assert tid in by, f"缺少任务 {tid}"
        assert by[tid].opt_in is True, f"{tid} 应为默认关闭"
        assert by[tid].standards, f"{tid} 应标注标准"
    assert by["any_interop_policy"].opt_in is False
    assert "绝不盗用" in by["any_interop_policy"].desc


def test_thirdparty_native_dispatchable():
    """任务里声明的 native 操作能被 runner 真正派发（零参、返回 (ok, msg)）。"""
    from sysweeper import runner
    for op in ("thirdparty.interop_refs_report", "thirdparty.hw_opt_report",
               "thirdparty.downloader_report", "thirdparty.cdn_p2p_report",
               "thirdparty.licenses_report"):
        ok, msg = runner._run_native(op)
        assert isinstance(ok, bool) and isinstance(msg, str) and msg, op
