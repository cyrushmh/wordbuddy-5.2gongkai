"""无线电技术与标准只读诊断测试（v0.6.75 新建）。

守门同范式（与 test_legacy / test_reverse 一致）：
- data/radio_docs.json 的 12 条 items 须 schema 完整、官方源域名核验、存疑项挂 needs_verify；
- native/radio.py 须真正消费 data 层（REFS=12、RADIO_CHECKS 六维度全回链真实 key）；
- 六段只读报告 + 聚合报告须含红线 token；绝不驱动发射；
- 三任务在 registry 注册、native 动作可解析、subsystems 单一事实源登记。
"""

import json

import pytest

from sysweeper.native import radio as r
from sysweeper import registry

DATA = "src/python/sysweeper/data/radio_docs.json"

REQUIRED_FIELDS = ("key", "name", "org", "url", "protocols", "interfaces",
                   "docs", "summary", "advice", "evidence_status")

# 法规口径官方源域名白名单（gov.cn/miit.gov.cn 为法规；gnuradio.org/hamlib.github.io
# 为开源工具链；ieee802.org/lora-alliance.org/3gpp.org/itu.int 为链路/蜂窝/国际口径）
OFFICIAL_DOMAINS = ("www.gov.cn", "www.miit.gov.cn", "gnuradio.org",
                    "hamlib.github.io", "www.ieee802.org", "lora-alliance.org",
                    "www.3gpp.org", "www.itu.int")


# ─────────────────────────────────────────────────────────────────────────── #
# 知识层 schema 守门                                                             #
# ─────────────────────────────────────────────────────────────────────────── #
def test_refs_schema_complete():
    """radio_docs.json 的 12 条 items 须 schema 完整（十个字段非空）。"""
    with open(DATA, encoding="utf-8") as fh:
        doc = json.load(fh)
    items = doc.get("items") or []
    assert len(items) == 12, len(items)
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
    # 存疑项挂牌：至少一条（如证书有效期/版本线/国际口径未逐条核实）
    nv = [it["key"] for it in doc["items"] if it.get("needs_verify")]
    assert nv, "至少应有 1 条 needs_verify"


# ─────────────────────────────────────────────────────────────────────────── #
# native 层消费 data 层                                                          #
# ─────────────────────────────────────────────────────────────────────────── #
def test_native_consumes_data_layer():
    """native/radio.py 须真正消费 data 层（REFS=12，非孤儿）。"""
    assert len(r.REFS) == 12
    freedos = r.reference("radio-regulation-cn")
    assert freedos.get("org") and freedos.get("url")
    assert r.reference("no-such-key") == {}


def test_checks_backlink_to_kb():
    """RADIO_CHECKS 六维度回链的知识库 key 必须真实存在。"""
    assert set(r.RADIO_CHECKS) == {
        "rf_switches", "wifi_phys", "bluetooth_ctl",
        "rf_devices", "sdr_toolchain", "regulation_kb"}
    for _doc, _desc, keys in r.RADIO_CHECKS.values():
        for k in keys:
            assert r.reference(k), k


def test_doc_list_lists_kb_items():
    """doc_list 须列出 12 条知识条目（带 [key] 标记）。"""
    lines = r.doc_list()
    assert len(lines) == 12
    assert all(ln.startswith("· [") for ln in lines)


# ─────────────────────────────────────────────────────────────────────────── #
# 六段只读报告 + 红线 token                                                      #
# ─────────────────────────────────────────────────────────────────────────── #
def test_rf_switch_report_redline(monkeypatch):
    """射频开关报告：rfkill 命中时只读探查 + 红线『不代切换』。"""
    monkeypatch.setattr(r.shutil, "which", lambda c: c == "rfkill")
    monkeypatch.setattr(r.common, "run",
                        lambda *a, **k: (0, "0: phy0: Wireless LAN\n"
                                         "\tSoft blocked: no\n\tHard blocked: no\n"))
    ok, msg = r.rf_switch_report()
    assert ok is True
    assert "rfkill" in msg
    assert "不代切换" in msg


def test_wifi_phys_report_redline(monkeypatch):
    """Wi-Fi 物理能力报告：含 regdom 读法 + 红线『不改 regdom/信道/txpower』。"""
    monkeypatch.setattr(r.shutil, "which", lambda c: c == "iw")
    monkeypatch.setattr(r.common, "run",
                        lambda *a, **k: (0, "Wiphy phy0\n"))
    ok, msg = r.wifi_phys_report()
    assert ok is True
    assert "regdom" in msg
    assert "不改 regdom/信道/txpower" in msg


def test_bluetooth_report_redline(monkeypatch):
    """蓝牙报告：含『不扫描、不配对』红线（只读 show）。"""
    monkeypatch.setattr(r.shutil, "which", lambda c: c == "bluetoothctl")
    monkeypatch.setattr(r.common, "run",
                        lambda *a, **k: (0, "Controller AA:BB:CC:DD:EE:FF pc\n"))
    ok, msg = r.bluetooth_report()
    assert ok is True
    assert "不扫描、不配对" in msg


def test_rf_devices_report_redline(monkeypatch):
    """总线射频器件报告：含『不绑定/解绑驱动』红线。"""
    monkeypatch.setattr(r.shutil, "which", lambda c: c == "lspci")
    monkeypatch.setattr(r.common, "run",
                        lambda *a, **k: (0, "02:00.0 Network controller: Intel Wi-Fi 6\n"))
    ok, msg = r.rf_devices_report()
    assert ok is True
    assert "不绑定/解绑驱动" in msg


def test_sdr_toolchain_report_never_launches():
    """SDR 工具链报告：只 which 盘点存在性；绝不出现任何启动行为。"""
    ok, msg = r.sdr_toolchain_report()
    assert "只 which" in msg or "绝不启动" in msg
    assert "GNU Radio" in msg and "rtl_sdr" in msg
    # 沙箱无 SDR 工具：全 ✗ 不崩
    assert "✗" in msg


def test_regulation_report_ism_and_redline():
    """法规报告：含中国 ISM 频段口径 + 诚实边界 + 红线 token。"""
    ok, msg = r.regulation_report()
    assert ok is True
    assert "2400-2500MHz" in msg          # 中国 ISM 常规频段之一
    assert "第三区" in msg                 # 中国所在第三区口径
    assert "型号核准" in msg
    assert "诚实边界" in msg


# ─────────────────────────────────────────────────────────────────────────── #
# 聚合报告与能力自检                                                            #
# ─────────────────────────────────────────────────────────────────────────── #
def test_radio_report_six_sections():
    """聚合报告须含 6 段 + 红线（绝不驱动任何真实发射）。"""
    _ok, msg = r.radio_report()
    for title in ("射频开关（rfkill）", "Wi-Fi 物理能力", "蓝牙控制器",
                  "总线射频器件", "SDR 与无线工具链", "法规与频段口径"):
        assert title in msg, title
    assert "绝不驱动任何真实发射" in msg
    assert "sysmap" in msg  # 嵌入整体系统关联图


def test_capabilities_report_lists_count():
    """能力自检须含 12 条知识回链计数 + 红线。"""
    ok, msg = r.capabilities_report()
    assert ok is True
    assert "知识条目回链：12 条" in msg


# ─────────────────────────────────────────────────────────────────────────── #
# 只读不变量：绝不执行 / 绝不联网                                                #
# ─────────────────────────────────────────────────────────────────────────── #
def test_no_execute_or_network_in_layer():
    """只读不变量：native 层不得出现执行/网络类调用（shutil.which 仅探测，允许）。"""
    src = open(r.__file__, encoding="utf-8").read()
    for bad in ("subprocess", "os.system", "socket.", "requests",
                "urllib", "eval(", "exec(", "pty", "ctypes"):
        assert bad not in src, bad


# ─────────────────────────────────────────────────────────────────────────── #
# 四入口接线                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #
def test_tasks_registered():
    """三任务须在 registry 注册。"""
    ids = {t.id for t in registry.all_tasks()}
    for tid in ("radio_rf_capability", "radio_sdr_toolchain", "radio_regulation_check"):
        assert tid in ids, tid
    assert len({t for t in ids if t.startswith("radio_")}) == 3


def test_task_native_actions_resolvable():
    """每个 native 动作须能解析到 radio 模块的真实函数。"""
    for t in registry.all_tasks():
        if not t.id.startswith("radio_"):
            continue
        for a in t.actions:
            if a.kind == "native":
                fn_name = a.command.split(".", 1)[1]
                assert hasattr(r, fn_name), (t.id, fn_name)


def test_subsystem_registered():
    """subsystems 单一事实源须登记 radio（fn=radio_report）。"""
    from sysweeper.native.subsystems import BY_KEY
    sub = BY_KEY.get("radio")
    assert sub is not None
    assert sub.fn == "radio_report"
    assert sub.module == "radio"
    _ok, rep = getattr(r, sub.fn)()
    assert "无线电" in rep
