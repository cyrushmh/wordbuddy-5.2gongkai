"""v0.5.18 新增能力测试：链接协议 / 自组网 / 隐私验证 / 同人资源共享 / 多系统无障碍。

全部测试**不修改系统**、不联网写、不落盘真实个人信息（用临时目录）。
安全底线在本文件里以断言形式固定：
- mesh 命令通道**绝不执行任意命令**（越权命令降级为 msg + error=forbidden）；
- 隐私验证**绝不落盘原始 PII**（只存 salt + 派生令牌 + 字段标签）；
- 同人资源共享**永不共享个人数据与关键资产数据**。
"""

import os
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src", "python"))

from sysweeper.native import netauth, netlink, reshare  # noqa: E402
from sysweeper import a11y  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 多种网络链接协议                                                          #
# --------------------------------------------------------------------------- #

def _protocol_ids():
    return [pid for pid, _layer, _fn in netlink.LINK_PROTOCOLS]


def test_link_protocols_registered():
    ids = _protocol_ids()
    for want in ("tcp", "udp", "rfcomm", "serial", "ble", "ieee802154"):
        assert want in ids, f"缺少链接协议 {want}"
    assert len(ids) == len(set(ids)), "协议 id 必须唯一"


def test_link_protocol_docs_have_protocol_and_interface():
    for pid in _protocol_ids():
        doc = netlink.protocol_doc(pid)
        assert doc.get("name"), f"{pid} 缺少 name"
        assert doc.get("org"), f"{pid} 缺少组织 org"
        assert doc.get("protocols"), f"{pid} 缺少 protocols"
        assert doc.get("interfaces"), f"{pid} 缺少 interfaces"
        assert doc.get("url"), f"{pid} 缺少文档 url"


def test_list_protocols_and_environment_report():
    lines = netlink.list_protocols()
    assert lines and any("tcp" in ln for ln in lines)
    env = netlink.environment_report()
    assert env and any("udp" in ln for ln in env)


def test_protocol_capable_returns_tuple():
    for pid in _protocol_ids():
        ok, msg = netlink.protocol_capable(pid)
        assert isinstance(ok, bool)
        assert isinstance(msg, str) and msg


# --------------------------------------------------------------------------- #
# 2. 本地自组网（mesh）：帧编解码与安全命令白名单                               #
# --------------------------------------------------------------------------- #

def test_frame_parse_roundtrip():
    raw = netlink.frame("info", {"a": 1, "b": "中文"})
    cmd, payload = netlink.parse(raw)
    assert cmd == "info"
    assert payload == {"a": 1, "b": "中文"}


def test_frame_rejects_outside_allowlist():
    """不在白名单的命令在**编码阶段**就被改写为 msg + 错误，绝不原样传输。"""
    cmd, payload = netlink.parse(netlink.frame("rm -rf /", {}))
    assert cmd == "msg"
    assert "不在白名单" in payload.get("msg", "") or "error" in payload


def test_mesh_command_never_executes_arbitrary():
    info = netlink._local_info()
    for bad in ("exec", "shell", "eval", "sudo", "delete"):
        res = netlink.handle_mesh_command(bad, {"cmd": "rm -rf /"}, info)
        assert res.get("error") == "forbidden", f"{bad} 必须被拒绝"
        assert "rm -rf /" not in str(res.get("msg", "")).replace("命令 '", "")


def test_mesh_safe_commands():
    info = netlink._local_info()
    assert netlink.handle_mesh_command("ping", {"text": "hi"}, info)["pong"] is True
    assert netlink.handle_mesh_command("info", {}, info)["info"]["name"]
    assert "probe" in netlink.handle_mesh_command("probe", {}, info)
    r = netlink.handle_mesh_command("msg", {"text": "你好"}, info)
    assert r["received"] is True and "不触发" in r["note"]


def test_local_info_declares_share_boundary():
    """握手信息必须同时声明「可共享算力」与「永不共享的数据」。"""
    info = netlink._local_info()
    assert "share" in info
    for k in info["share"]["offered"]:
        assert k in reshare.SHAREABLE_KINDS
    for k in info["share"]["blocked"]:
        assert k in reshare.NEVER_SHARE


def test_mesh_end_to_end_localhost():
    """端到端：本机起 mesh 节点 → 发一条 msg → 收到回执 → 进会话收件箱。

    端口被占用（如并行环境）时跳过，不因环境差异失败。
    """
    import time
    ok, msg = netlink.mesh_serve()
    if not ok:
        pytest.skip(f"端口不可用，跳过端到端: {msg}")
    time.sleep(0.3)
    ok2, msg2 = netlink.mesh_send_msg("hello 人机交互")
    assert ok2 is True, msg2
    time.sleep(0.3)
    assert len(netlink.mesh_inbox()) >= 1, "消息应记入会话收件箱"


def test_mesh_reports_are_readonly_and_graceful():
    for fn in (netlink.link_report, netlink.mesh_report, netlink.mesh_info):
        ok, msg = fn()
        assert isinstance(ok, bool) and isinstance(msg, str) and msg


# --------------------------------------------------------------------------- #
# 3. 按网络维度的隐私验证（原始信息不保存，可重连）                             #
# --------------------------------------------------------------------------- #

def test_netauth_derive_verify_consistency():
    fields = {"name": "张三", "id_number": "110101000000000000"}
    salt, token = netauth.derive(fields)
    assert netauth.verify(fields, salt, token) is True
    # 大小写/空白差异应容忍
    assert netauth.verify({"name": " 张三 ", "ID_Number": "110101000000000000"},
                          salt, token) is True
    # 值不一致应拒绝
    assert netauth.verify({"name": "李四", "id_number": "110101000000000000"},
                          salt, token) is False


def test_netauth_requires_at_least_two_fields():
    with pytest.raises(ValueError):
        netauth.derive({"name": "张三"})


def test_netauth_never_stores_raw_pii(tmp_path):
    p = str(tmp_path / "netauth.json")
    fields = {"name": "张三", "id_number": "110101000000000000", "email": "a@b.cn"}
    ok, _ = netauth.store(p, "home_wifi", fields)
    assert ok is True
    raw = open(p, encoding="utf-8").read()
    for secret in ("张三", "110101000000000000", "a@b.cn"):
        assert secret not in raw, f"原始个人信息 {secret!r} 绝不能落盘"
    salt, token, labels = netauth.load(p, "home_wifi")
    assert sorted(labels) == ["email", "id_number", "name"]


def test_netauth_auto_reconnect(tmp_path):
    p = str(tmp_path / "netauth.json")
    fields = {"name": "张三", "id_number": "110101000000000000"}
    netauth.store(p, "home_wifi", fields)
    ok, _ = netauth.auto_reconnect(p, "home_wifi", fields)
    assert ok is True, "下次启动重输同样信息应能重连"
    bad, _ = netauth.auto_reconnect(p, "home_wifi",
                                    {"name": "李四", "id_number": "110101000000000000"})
    assert bad is False


def test_netauth_reconnect_missing_field_hints(tmp_path):
    p = str(tmp_path / "netauth.json")
    netauth.store(p, "home", {"name": "张三", "id_number": "110", "email": "a@b.cn"})
    ok, msg = netauth.auto_reconnect(p, "home", {"name": "张三", "id_number": "110"})
    assert ok is False and "请补充" in msg


def test_identity_fingerprint_cross_device():
    a = {"name": "张三", "id_number": "110101000000000000"}
    f1 = netauth.identity_fingerprint(a, "home", "shared-pass")
    f2 = netauth.identity_fingerprint({"name": " 张三 ", "ID_Number": "110101000000000000"},
                                      "home", "shared-pass")
    assert netauth.same_identity(f1, f2), "同一人同一网络同一口令应认定一致"
    f3 = netauth.identity_fingerprint(a, "home", "wrong-pass")
    assert not netauth.same_identity(f1, f3), "口令不同不应一致（防冒用）"
    f4 = netauth.identity_fingerprint({"name": "李四", "id_number": "110101000000000000"},
                                      "home", "shared-pass")
    assert not netauth.same_identity(f1, f4), "不同人不应一致"


# --------------------------------------------------------------------------- #
# 4. 同人设备资源共享：算力共享，数据与资产永不共享                             #
# --------------------------------------------------------------------------- #

def test_never_share_always_denied():
    for kind in reshare.NEVER_SHARE:
        ok, _ = reshare.policy_check(kind)
        assert ok is False, f"{kind} 属于个人数据/关键资产，必须永不共享"


def test_shareable_kinds_allowed():
    for kind in reshare.SHAREABLE_KINDS:
        ok, _ = reshare.policy_check(kind)
        assert ok is True, f"{kind} 属算力/网络，应可共享"


def test_share_manifest_excludes_data():
    man = reshare.share_manifest()
    assert all(k not in reshare.NEVER_SHARE for k in man["offered"])
    assert man["blocked"] == list(reshare.NEVER_SHARE)
    assert "cpu" in man["inventory"] and "network" in man["inventory"]


def test_grant_only_same_identity(tmp_path):
    p = str(tmp_path / "reshare.json")
    me = {"name": "张三", "id_number": "110101000000000000"}
    fp_me = netauth.identity_fingerprint(me, "home", "pw")
    fp_other = netauth.identity_fingerprint({"name": "他人", "id_number": "999"},
                                            "home", "pw")
    ok, _ = reshare.grant(fp_me, ["cpu", "gpu", "network"], path=p)
    assert ok is True
    assert reshare.is_allowed(fp_me, "cpu", path=p)[0] is True
    assert reshare.is_allowed(fp_other, "cpu", path=p)[0] is False, "他人必须被拒绝"


def test_data_and_assets_never_shared_even_for_owner(tmp_path):
    p = str(tmp_path / "reshare.json")
    me = {"name": "张三", "id_number": "110101000000000000"}
    fp_me = netauth.identity_fingerprint(me, "home", "pw")
    reshare.grant(fp_me, list(reshare.SHAREABLE_KINDS), path=p)
    for kind in reshare.NEVER_SHARE:
        ok, _ = reshare.is_allowed(fp_me, kind, path=p)
        assert ok is False, f"即使本人也绝不共享 {kind}"


def test_revoke_withdraws_access(tmp_path):
    p = str(tmp_path / "reshare.json")
    fp = netauth.identity_fingerprint({"name": "张三", "id_number": "110"}, "home", "pw")
    reshare.grant(fp, ["cpu"], path=p)
    assert reshare.is_allowed(fp, "cpu", path=p)[0] is True
    ok, _ = reshare.revoke(fp, path=p)
    assert ok is True
    assert reshare.is_allowed(fp, "cpu", path=p)[0] is False


def test_reshare_stores_no_personal_info(tmp_path):
    p = str(tmp_path / "reshare.json")
    me = {"name": "张三", "id_number": "110101000000000000"}
    fp = netauth.identity_fingerprint(me, "home", "pw")
    reshare.grant(fp, ["cpu"], label="我的笔记本", path=p)
    raw = open(p, encoding="utf-8").read()
    assert "张三" not in raw and "110101000000000000" not in raw


def test_reshare_reports_graceful():
    ok, msg = reshare.reshare_report()
    assert ok is True and "永不共享" in msg
    ok2, msg2 = reshare.reshare_demo()
    assert ok2 is True and "拒绝" in msg2


# --------------------------------------------------------------------------- #
# 5. 无障碍多系统适配                                                          #
# --------------------------------------------------------------------------- #

def test_a11y_multi_platform_probe_covers_all():
    lines = a11y.a11y_probe_all("any")
    text = "\n".join(lines)
    for pf in ("windows", "macos", "linux", "android", "ios", "harmony"):
        assert pf in text, f"多系统无障碍缺少 {pf}"


def test_a11y_enable_commands_per_platform():
    for pf in ("windows", "macos", "linux", "android", "ios", "harmony"):
        cmds = a11y.a11y_enable_commands(pf)
        assert cmds, f"{pf} 缺少启用指引"
        assert all(isinstance(c, str) for c in cmds)


def test_a11y_platform_status_graceful():
    for pf in ("windows", "macos", "android", "ios", "harmony"):
        ok, msg = a11y.screen_reader_status(pf)
        assert isinstance(ok, bool)
        assert isinstance(msg, str) and msg
        assert "Traceback" not in msg


def test_a11y_docs_have_protocol_and_interface():
    refs = a11y.a11y_reference_all()
    assert len(refs) >= 6
    for did, ref in refs.items():
        assert ref.get("protocols"), f"{did} 缺少 protocols"
        assert ref.get("interfaces"), f"{did} 缺少 interfaces"
        assert ref.get("url"), f"{did} 缺少 url"


def test_a11y_environment_report_platform_switch():
    for pf in ("windows", "harmony"):
        lines = a11y.environment_report(pf)
        assert any(pf in ln for ln in lines), f"指定 {pf} 时报告未体现该系统"
