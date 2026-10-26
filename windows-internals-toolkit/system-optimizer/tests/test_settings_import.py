"""v0.6.23：参数与阈值注册表 + 多来源导入（剪贴板/文件/二维码）的测试。

覆盖三类断言：

1. **注册表自洽**：key/label 唯一、默认值合法、越界与非法枚举被拒、损坏配置回退、
   每条参数都登记了生效点（**不允许出现只显示不生效的装饰参数**）。
2. **阈值真实生效**：改阈值后 ``common.run`` 的截断与超时、``large_dirs_report`` 的
   条数真的跟着变；**显式传参仍优先**（向后兼容既有调用）。
3. **导入层只读安全**：文本/二维码能读进来；缺文件、非图片、未知来源都不抛错；
   **导入的内容绝不自动写入配置**（除非用户显式要求载入）。

所有涉及落盘的用例都用 ``_isolated`` 把配置目录指到 tmp_path，绝不污染用户真实配置。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))

from sysweeper.native import common  # noqa: E402
from sysweeper.native import importio  # noqa: E402
from sysweeper.native import settings as st  # noqa: E402


@pytest.fixture
def _isolated(tmp_path, monkeypatch):
    """把 settings 的配置落点（含变更留痕）隔离到 tmp_path，并清空缓存与订阅者。"""
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(st, "CONFIG_DIR", str(cfg_dir), raising=True)
    monkeypatch.setattr(st, "CONFIG_PATH", str(cfg_dir / "settings.json"), raising=True)
    monkeypatch.setattr(st, "HISTORY_PATH", str(cfg_dir / "settings-history.json"),
                        raising=True)
    monkeypatch.setattr(st, "_LISTENERS", [], raising=True)
    st.reload()
    yield st.CONFIG_PATH
    st.reload()


# ─────────────────────────────────────────────────────────────────────────────
# 1) 注册表自洽
# ─────────────────────────────────────────────────────────────────────────────
def test_registry_keys_and_labels_unique():
    keys = [s.key for s in st.SETTINGS]
    labels = [s.label for s in st.SETTINGS]
    assert len(keys) == len(set(keys)), "参数 key 必须唯一"
    assert len(labels) == len(set(labels)), "参数 label 必须唯一"
    assert len(keys) >= 10


def test_every_setting_has_real_apply_point():
    """反装饰参数：每条都必须写明生效点，且不少于一句说明。"""
    for s in st.SETTINGS:
        assert s.apply.strip(), f"{s.key} 缺少生效点说明"
        assert s.desc.strip(), f"{s.key} 缺少说明"
        assert s.group in (st.GROUP_THRESHOLD, st.GROUP_RUNTIME, st.GROUP_IMPORT)


def test_defaults_are_valid():
    """每个默认值都必须能通过自身校验（否则一开机就是非法态）。"""
    for s in st.SETTINGS:
        ok, norm, why = st.validate(s.key, s.default)
        assert ok, f"{s.key} 默认值非法: {why}"
        assert norm == s.default


def test_validate_rejects_out_of_range_and_bad_enum():
    ok, val, why = st.validate("cmd.timeout", 10 ** 9)
    assert not ok and val == st.BY_KEY["cmd.timeout"].default and "不能大于" in why
    ok, _val, why = st.validate("scan.limit", 0)
    assert not ok and "不能小于" in why
    ok, _val, why = st.validate("arch", "sparc")
    assert not ok and "只能是" in why
    ok, _val, why = st.validate("不存在的键", 1)
    assert not ok and "未知参数" in why


def test_bool_and_str_coercion():
    ok, val, _ = st.validate("arch", "auto")
    assert ok and val == "auto"
    ok, val, _ = st.validate("report.path", None)
    assert ok and val == ""


def test_set_get_roundtrip(_isolated):
    ok, val, _why = st.set_value("cmd.timeout", 300)
    assert ok and val == 300
    assert st.get("cmd.timeout") == 300
    # 落盘后能被真实回读
    with open(_isolated, "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk["cmd.timeout"] == 300


def test_corrupted_config_falls_back_to_defaults(_isolated):
    with open(_isolated, "w", encoding="utf-8") as fh:
        fh.write("{ 这不是 JSON")
    vals = st.load()
    assert vals == st.defaults(), "配置损坏必须安全回退默认值，不抛异常"


def test_unknown_key_in_config_is_ignored(_isolated):
    with open(_isolated, "w", encoding="utf-8") as fh:
        json.dump({"cmd.timeout": 60, "未来才会有的键": 1}, fh)
    st.reload()
    assert st.get("cmd.timeout") == 60
    assert "未来才会有的键" not in st.load()


def test_reset_restores_defaults(_isolated):
    st.set_value("cmd.timeout", 300)
    st.reset()
    assert st.get("cmd.timeout") == st.BY_KEY["cmd.timeout"].default


def test_apply_updates_partial_success(_isolated):
    results = st.apply_updates({"cmd.timeout": 45, "arch": "sparc", "bogus": 1})
    good = {k for k, ok, _ in results if ok}
    assert "cmd.timeout" in good and "arch" not in good and "bogus" not in good
    assert st.get("cmd.timeout") == 45, "合法项不能被非法项连坐"


def test_list_settings_shape_and_groups():
    items = st.list_settings()
    assert len(items) == len(st.SETTINGS)
    for it in items:
        for field in ("key", "label", "kind", "group", "default", "value",
                      "unit", "min", "max", "choices", "desc", "apply"):
            assert field in it, f"{it['key']} 缺字段 {field}"
    assert st.GROUP_THRESHOLD in st.groups()


def test_settings_report_ok():
    ok, msg = st.settings_report()
    assert ok is True
    assert "cmd.timeout" in msg and "参数与阈值" in msg


# ─────────────────────────────────────────────────────────────────────────────
# 2) 阈值真实生效（不是装饰参数）
# ─────────────────────────────────────────────────────────────────────────────
def test_tail_threshold_really_truncates(_isolated):
    st.set_value("cmd.tail", 5)
    _rc, out = common.run("echo ABCDEFGHIJ")
    assert out == "FGHIJ", "输出截断阈值必须真的作用于 common.run"
    st.set_value("cmd.tail", 0)
    _rc, out = common.run("echo ABCDEFGHIJ")
    assert out == "ABCDEFGHIJ", "tail=0 表示不截断"


def test_explicit_args_still_win(_isolated):
    st.set_value("cmd.tail", 5)
    _rc, out = common.run("echo ABCDEFGHIJ", 120, 3)
    assert out == "HIJ", "显式传参必须优先于配置值（向后兼容）"


def test_timeout_threshold_really_applies(_isolated):
    st.set_value("cmd.timeout", 1)
    rc, _out = common.run("sleep 5")
    assert rc == -1, "超时阈值必须真的传给 subprocess"


def test_scan_limit_threshold_really_applies(_isolated, tmp_path):
    for i in range(4):
        d = tmp_path / f"d{i}"
        d.mkdir()
        (d / "f.bin").write_bytes(b"x" * (100 * (i + 1)))
    st.set_value("scan.limit", 2)
    ok, msg = common.large_dirs_report(str(tmp_path))
    assert ok and "前2" in msg
    assert msg.count(";") == 1, "只应列出 2 条"
    assert len(common.find_large_subdirs(str(tmp_path))) == 2


def test_scan_root_parameter_really_applies(_isolated, tmp_path):
    sub = tmp_path / "root"
    sub.mkdir()
    (sub / "a").mkdir()
    (sub / "a" / "big.bin").write_bytes(b"y" * 4096)
    st.set_value("scan.root", str(sub))
    ok, msg = common.large_dirs_report()
    assert ok and str(sub) in msg


# ─────────────────────────────────────────────────────────────────────────────
# 3) 导入层
# ─────────────────────────────────────────────────────────────────────────────
def test_read_text_file(_isolated, tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello 中文", encoding="utf-8")
    r = importio.read_text_file(str(p))
    assert r.ok and "hello 中文" in r.text and "a.txt" in r.note


def test_read_text_file_respects_max_bytes(_isolated, tmp_path):
    p = tmp_path / "big.txt"
    p.write_text("z" * 5000, encoding="utf-8")
    r = importio.read_text_file(str(p), max_bytes=100)
    assert r.ok and len(r.text) == 100 and "截断" in r.note


def test_read_text_file_missing_path(_isolated):
    r = importio.read_text_file("/definitely/not/here.txt")
    assert not r.ok and r.text == "" and "不存在" in r.note


def test_decode_qr_roundtrip(_isolated, tmp_path):
    """二维码往返：生成 → 从**图片文件**解码（用户点名的「通过文件读取图片」）。"""
    qrcode = pytest.importorskip("qrcode")
    if not importio.qr_backends():
        pytest.skip("无可用二维码解码后端（cv2 / pyzbar 均未安装）")
    payload = "sysweeper-qr-roundtrip-9527"
    img = tmp_path / "qr.png"
    qrcode.make(payload).save(str(img))
    r = importio.decode_qr_image(str(img))
    assert r.ok, r.note
    assert payload in r.text


def test_decode_qr_rejects_non_image_and_missing(_isolated, tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("not an image", encoding="utf-8")
    r = importio.decode_qr_image(str(p))
    assert not r.ok and "图片格式" in r.note
    r2 = importio.decode_qr_image(str(tmp_path / "nope.png"))
    assert not r2.ok and "不存在" in r2.note


def test_decode_qr_does_not_raise_without_backend(_isolated, tmp_path, monkeypatch):
    """没有解码库时必须给指引，绝不抛异常、绝不自动安装。"""
    monkeypatch.setattr(importio, "qr_backends", lambda: [])
    p = tmp_path / "qr.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    r = importio.decode_qr_image(str(p))
    assert not r.ok and "不会自动安装" in r.note


def test_import_from_unknown_source(_isolated):
    r = importio.import_from("telepathy")
    assert not r.ok and "未知导入来源" in r.note


def test_import_from_dispatches_to_file(_isolated, tmp_path):
    p = tmp_path / "b.txt"
    p.write_text("from-file", encoding="utf-8")
    r = importio.import_from("file", str(p))
    assert r.ok and "from-file" in r.text
    r2 = importio.import_from("file", "")
    assert not r2.ok and "需要提供路径" in r2.note


def test_parse_settings_json_variants(_isolated):
    ok, acc, rej, _hint = importio.parse_settings_json('{"cmd.timeout": 60}')
    assert ok and acc == {"cmd.timeout": 60} and not rej
    ok, _acc, _rej, hint = importio.parse_settings_json("不是 JSON")
    assert not ok and "不是合法 JSON" in hint
    ok, _acc, _rej, hint = importio.parse_settings_json("[1,2]")
    assert not ok and "顶层不是对象" in hint
    ok, acc, rej, _hint = importio.parse_settings_json('{"bogus": 1}')
    assert not ok and rej
    # 越界值被拒，不写入
    ok, acc, rej, _hint = importio.parse_settings_json('{"cmd.timeout": 99999999}')
    assert not ok and not acc


def test_decode_qr_pil_roundtrip(_isolated):
    """内存里的 PIL 图像（模拟剪贴板截图）也能解码，不必先落盘。"""
    qrcode = pytest.importorskip("qrcode")
    if not importio.qr_backends():
        pytest.skip("无可用二维码解码后端")
    payload = "clipboard-screenshot-QR-7788"
    r = importio.decode_qr_pil(qrcode.make(payload))
    assert r.ok and payload in r.text
    assert not importio.decode_qr_pil(None).ok


def test_decode_qr_pil_without_backend_gives_hint(_isolated, monkeypatch):
    monkeypatch.setattr(importio, "qr_backends", lambda: [])
    r = importio.decode_qr_pil(object())
    assert not r.ok and "不会自动安装" in r.note


def test_read_clipboard_image_never_raises(_isolated):
    """Linux 桌面取不到剪贴板图像是常态：必须优雅失败并说明，绝不抛异常。"""
    ok, data, note = importio.read_clipboard_image()
    assert isinstance(ok, bool) and note
    if not ok:
        assert data is None


def test_decode_qr_from_clipboard_never_raises(_isolated):
    r = importio.decode_qr_from_clipboard()
    assert isinstance(r.ok, bool) and (r.text or r.note)


def test_clipboard_source_falls_back_to_screenshot(_isolated, monkeypatch):
    """剪贴板没有纯文本时，应自动再试一次截图里的二维码。"""
    monkeypatch.setattr(importio, "read_clipboard",
                        lambda *a, **k: importio.ImportResult(False, "", "剪贴板读取失败（测试桩）"))
    monkeypatch.setattr(importio, "decode_qr_from_clipboard",
                        lambda: importio.ImportResult(False, "", "无图像（测试桩）"))
    r = importio.import_from("clipboard")
    assert not r.ok and "已尝试剪贴板截图扫码" in r.note

    monkeypatch.setattr(importio, "decode_qr_from_clipboard",
                        lambda: importio.ImportResult(True, "from-screenshot", "测试桩"))
    r2 = importio.import_from("clipboard")
    assert r2.ok and r2.text == "from-screenshot"


def test_import_never_writes_config_by_itself(_isolated, tmp_path):
    """红线：导入动作本身绝不写配置（无 --as-settings / 无确认就不落盘）。"""
    before = st.load()
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"cmd.timeout": 7}), encoding="utf-8")
    r = importio.import_from("file", str(p))
    assert r.ok
    assert st.load() == before, "导入内容不得自动写入配置"


def test_importio_reports_shape(_isolated):
    ok, msg = importio.capabilities_report()
    assert ok and "剪贴板" in msg and "图片二维码" in msg and "摄像头" in msg
    ok2, msg2 = importio.importio_report()
    assert ok2 and "红线" in msg2


def test_sources_list_complete(_isolated):
    keys = [k for k, _l, _d in importio.SOURCES]
    for need in (importio.SRC_CLIPBOARD, importio.SRC_FILE,
                 importio.SRC_QR, importio.SRC_CAMERA):
        assert need in keys


# ─────────────────────────────────────────────────────────────────────────────
# 4) 子系统嵌入与 CLI
# ─────────────────────────────────────────────────────────────────────────────
def test_settings_and_importio_registered_as_subsystems():
    from sysweeper.native import subsystems as subs
    keys = {s.key for s in subs.SUBSYSTEMS}
    assert "settings" in keys and "importio" in keys
    for s in subs.SUBSYSTEMS:
        if s.key in ("settings", "importio"):
            assert s.default_on is True


def test_cli_settings_and_import(tmp_path, _isolated):
    from sysweeper import cli

    p = cli.build_parser()
    a = p.parse_args(["settings", "--list"])
    assert a.func is cli.cmd_settings
    a2 = p.parse_args(["settings", "--set", "cmd.timeout=222"])
    cli.cmd_settings(a2)
    assert st.get("cmd.timeout") == 222

    a3 = p.parse_args(["settings", "--get", "cmd.timeout"])
    cli.cmd_settings(a3)

    txt = tmp_path / "x.txt"
    txt.write_text("cli-import-ok", encoding="utf-8")
    a4 = p.parse_args(["import", "--from", "file", "--path", str(txt)])
    cli.cmd_import(a4)  # 仅查看，应不写配置
    assert st.get("cmd.timeout") == 222, "仅查看不得写配置"

    a5 = p.parse_args(["import", "--from", "file", "--path", str(txt)])
    assert getattr(a5, "as_settings", False) is False


def test_cli_defaults_follow_runtime_settings(_isolated):
    """运行参数必须真的影响 CLI 默认值（反装饰参数），且命令行显式给出仍优先。"""
    from sysweeper import cli

    st.set_value("arch", "riscv")
    assert cli.build_parser().parse_args(["list"]).arch == "riscv"
    assert cli.build_parser().parse_args(["list", "--arch", "x86"]).arch == "x86"

    st.set_value("profile", "minimal")
    st.set_value("locale", "en")
    st.set_value("report.path", "/tmp/report.md")
    a = cli.build_parser().parse_args(["list"])
    assert a.profile == "minimal" and a.locale == "en" and a.report == "/tmp/report.md"


def test_cli_defaults_stay_sane_after_reset(_isolated):
    from sysweeper import cli

    st.reset()
    a = cli.build_parser().parse_args(["list"])
    assert a.arch == "auto" and a.profile == "" and a.locale is None and a.report == ""


# ─────────────────────────────────────────────────────────────────────────────
# 5) v0.6.24：变更留痕 + 实时联动
# ─────────────────────────────────────────────────────────────────────────────
def test_changed_keys_tracks_difference_from_default(_isolated):
    assert st.changed_keys() == []
    st.set_value("cmd.timeout", 300)
    assert st.changed_keys() == ["cmd.timeout"]
    st.set_value("cmd.timeout", 120)
    assert st.changed_keys() == []


def test_history_records_source_and_values(_isolated):
    st.set_value("cmd.timeout", 300, source="cli", origin="--set")
    st.apply_updates({"scan.limit": 5, "arch": "riscv"},
                     source="import", origin="/tmp/from-qr.json")
    rows = st.history()
    assert len(rows) == 2
    assert rows[0]["source"] == "cli" and rows[0]["origin"] == "--set"
    assert rows[0]["changes"]["cmd.timeout"] == {"from": 120, "to": 300}
    assert rows[1]["source"] == "import" and "/tmp/from-qr.json" in rows[1]["origin"]
    assert set(rows[1]["changes"]) == {"scan.limit", "arch"}
    assert rows[0]["ts"]  # 有时间


def test_history_skips_no_op_change(_isolated):
    """重复写入同一个值不该产生噪音记录。"""
    st.set_value("cmd.timeout", 300)
    st.set_value("cmd.timeout", 300)
    assert len(st.history()) == 1


def test_history_never_stores_imported_full_text(_isolated):
    """留痕只记参数键与值 + 来源标识，绝不把导入的整篇文本留在本地。"""
    secret = "SECRET-SHOULD-NOT-BE-LOGGED"
    text = json.dumps({"cmd.timeout": 90, "note": secret, "arch": "riscv"})
    ok, accepted, rejected, _hint = importio.parse_settings_json(text)
    assert ok and "note" not in accepted  # 未知键不进参数
    st.apply_updates(accepted, source="file", origin="/tmp/notes.txt",
                     note="由导入内容载入")
    raw = open(st.HISTORY_PATH, "r", encoding="utf-8").read()
    assert secret not in raw, "导入全文不得进入留痕"
    assert "cmd.timeout" in raw and "/tmp/notes.txt" in raw


def test_history_capped_and_clearable(_isolated):
    for i in range(st.HISTORY_LIMIT + 10):
        st.record_change({"cmd.timeout": (i, i + 1)}, source="loop")
    assert len(st.history(0)) == st.HISTORY_LIMIT, "留痕必须有上限，不能无限增长"
    assert len(st.history(5)) == 5
    st.clear_history()
    assert st.history(0) == []


def test_reset_is_recorded(_isolated):
    st.set_value("cmd.timeout", 300)
    st.reset(source="gui", origin="参数窗口")
    rows = st.history()
    assert rows[-1]["source"] == "gui"
    assert rows[-1]["changes"]["cmd.timeout"] == {"from": 300, "to": 120}


def test_history_report_shape(_isolated):
    ok, msg = st.history_report(20)
    assert ok and "暂无变更留痕" in msg
    st.set_value("scan.limit", 3, source="gui")
    ok2, msg2 = st.history_report(20)
    assert ok2 and "scan.limit: 10 → 3" in msg2


def test_on_change_notifies_and_survives_bad_listener(_isolated):
    seen = []

    def boom(_changes):
        raise RuntimeError("订阅方炸了也不该影响保存")

    cb = lambda ch: seen.append(ch)  # noqa: E731
    st.on_change(boom)
    st.on_change(cb)
    st.set_value("cmd.timeout", 300)  # 订阅方抛错不应影响保存
    assert len(seen) == 1 and seen[0]["cmd.timeout"] == (120, 300)
    st.on_change(cb)  # 同一个回调对象不会被重复注册
    assert len(st._LISTENERS) == 2


def test_cli_history_subcommand(_isolated, capsys):
    from sysweeper import cli

    st.set_value("cmd.timeout", 300, source="cli", origin="--set")
    a = cli.build_parser().parse_args(["settings", "--history"])
    cli.cmd_settings(a)
    out = capsys.readouterr().out
    assert "cmd.timeout" in out and "120 → 300" in out


def test_cli_import_as_settings(tmp_path, _isolated):
    from sysweeper import cli

    cfg = tmp_path / "s.json"
    cfg.write_text(json.dumps({"cmd.timeout": 33, "scan.limit": 4}), encoding="utf-8")
    p = cli.build_parser()
    a = p.parse_args(["import", "--from", "file", "--path", str(cfg), "--as-settings"])
    cli.cmd_import(a)
    assert st.get("cmd.timeout") == 33 and st.get("scan.limit") == 4
