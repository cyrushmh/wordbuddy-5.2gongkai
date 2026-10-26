"""统一子系统清单 + 开关管理器测试（v0.6.22）。

覆盖：清单全量登记（含用户点名的 firmware/plugins/modules）、默认全开、
选项式开/关、配置落盘与回读、sysmap 只枚举已开启项。

配置落点用 monkeypatch 指到 tmp_path，绝不污染用户真实
~/.config/sysweeper/subsystems.json。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import subsystems  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """把配置落点隔离到 tmp_path，避免读写真实用户配置。"""
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(subsystems, "CONFIG_DIR", str(cfg_dir))
    monkeypatch.setattr(subsystems, "CONFIG_PATH", str(cfg_dir / "subsystems.json"))
    yield


def test_registry_covers_named_dimensions():
    """用户点名的 firmware / plugins / modules 必须在清单里显式登记。"""
    keys = {s.key for s in subsystems.SUBSYSTEMS}
    for k in ("firmware", "plugins", "modules", "kmod", "kernel",
              "storage", "container", "hardware"):
        assert k in keys, f"清单缺少登记项：{k}"


def test_registry_keys_unique():
    """key 必须唯一（RELATIONS 与配置文件都按 key 定位）。"""
    keys = [s.key for s in subsystems.SUBSYSTEMS]
    assert len(keys) == len(set(keys)), "存在重复 key"


def test_registry_labels_unique():
    """label 必须唯一：sysmap 用 label 反查 key 来过滤关联关系两端。"""
    labels = [s.label for s in subsystems.SUBSYSTEMS]
    assert len(labels) == len(set(labels)), "存在重复 label"


def test_default_all_enabled():
    """默认全开（向后兼容「全量嵌入」行为）。"""
    states = subsystems.default_states()
    assert states and all(states.values()), "默认应全部开启"
    assert len(subsystems.enabled_probes()) == len(subsystems.SUBSYSTEMS)


def test_all_report_functions_exist():
    """每项登记都指向真实存在的只读函数（防「引用了不存在的函数」）。"""
    import importlib
    pkg = "sysweeper.native."
    for s in subsystems.SUBSYSTEMS:
        mod = importlib.import_module(pkg + s.module)
        fn = getattr(mod, s.fn, None)
        assert callable(fn), f"函数不可调用：{s.module}.{s.fn}"


def test_set_enabled_roundtrip():
    """选项式开/关：关掉后不再出现在 enabled_probes，重开后恢复。"""
    assert subsystems.set_enabled("tor", False) is True
    probes = subsystems.enabled_probes()
    assert all(p[0] != "tor" for p in probes), "tor 已关闭却仍被枚举"
    assert subsystems.is_enabled("tor") is False

    assert subsystems.set_enabled("tor", True) is True
    assert any(p[0] == "tor" for p in subsystems.enabled_probes())
    assert subsystems.is_enabled("tor") is True


def test_set_enabled_unknown_key_rejected():
    """未知 key 必须被拒，不静默接受。"""
    assert subsystems.set_enabled("no_such_subsystem", True) is False
    assert subsystems.is_enabled("no_such_subsystem") is False


def test_config_persisted_and_reloaded():
    """开关落盘后可回读（真实写文件 + 重新解析）。"""
    subsystems.set_enabled("firmware", False)
    subsystems.set_enabled("plugins", False)
    with open(subsystems.CONFIG_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw["firmware"] is False and raw["plugins"] is False
    # 回读一致
    states = subsystems.load_states()
    assert states["firmware"] is False and states["plugins"] is False
    assert states["network"] is True  # 未动过的仍是默认开


def test_corrupted_config_falls_back_to_default():
    """配置损坏时安全回退默认，绝不因配置问题阻断总览。"""
    with open(subsystems.CONFIG_PATH, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    states = subsystems.load_states()
    assert states == subsystems.default_states()


def test_list_subsystems_shape():
    """list_subsystems 供 CLI/GUI 展示，字段与开关态齐全。"""
    items = subsystems.list_subsystems()
    assert len(items) == len(subsystems.SUBSYSTEMS)
    for it in items:
        for field in ("key", "label", "layer", "module", "fn", "enabled"):
            assert field in it
    assert all(isinstance(it["enabled"], bool) for it in items)
