"""GUI 概念系统面板测试（show_protec，v0.6.68）。

gui.py 在无图形环境优雅降级，Tk() 需 DISPLAY；这里用最小 mock 把 tkinter 替掉，
真实跑面板逻辑，覆盖新增胶水代码，不依赖真实显示：
  · show_protec —— 分类轴七域（耐久/电气/环境/应急/保护/传输与可用性/接入与链路）/ 桥接 /
    检索·待核实 / 用户端面 四页（同 _axis_concept_window + _userface_tab）。
数据层由 test_protec.py 覆盖。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "python"))


class _Var:
    def __init__(self, value=""):
        self._v = value
        _W._reg.append(self)

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class _W:
    _reg: list = []

    def __init__(self, master=None, **kw):
        self.master = master
        self._kw = kw
        self._cb = {}
        _W._reg.append(self)

    def pack(self, *a, **k):
        pass

    def grid(self, *a, **k):
        pass

    def config(self, **k):
        self._kw.update(k)

    def destroy(self):
        pass


class _Toplevel(_W):
    def title(self, s):
        self._title = s

    def geometry(self, s):
        self._geom = s


class _Frame(_W):
    pass


class _Notebook(_W):
    def add(self, child, text=None, **k):
        tabs = getattr(self, "_tabs", [])
        tabs.append((child, text))
        self._tabs = tabs

    def select(self, i):
        pass


class _Listbox(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._items = []
        self._sel = (0,)
        self._data = []

    def delete(self, a, b=None):
        self._items = []

    def insert(self, i, s):
        self._items.append(s)

    def get(self, i):
        return self._items[i]

    def curselection(self):
        return self._sel

    def bind(self, ev, cb):
        self._cb[ev] = cb

    def fire(self, ev="<<ListboxSelect>>"):
        if ev in self._cb:
            self._cb[ev]()


class _Scrolled(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._buf = []

    def delete(self, a, b=None):
        self._buf = []

    def insert(self, a, s):
        self._buf.append(s)

    def see(self, a):
        pass

    def get(self, a, b=None):
        return "".join(self._buf)

    def content(self):
        return "".join(self._buf)


class _Label(_W):
    pass


class _Entry(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._cb = {}

    def bind(self, ev, cb):
        self._cb[ev] = cb

    def fire(self, ev="<KeyRelease>"):
        if ev in self._cb:
            self._cb[ev]()


class _Button(_W):
    def __init__(self, master=None, text=None, command=None, **kw):
        super().__init__(master, **kw)
        self._text = text
        self._cmd = command

    def invoke(self):
        if self._cmd:
            self._cmd()


class _Tk:
    Toplevel = _Toplevel
    Listbox = _Listbox
    StringVar = _Var


class _Ttk:
    Frame = _Frame
    Notebook = _Notebook
    Label = _Label
    Entry = _Entry
    Button = _Button
    Combobox = _Entry


class _ScrolledMod:
    ScrolledText = _Scrolled


class _Msg:
    """messagebox 替身：记录错误调用，绝不抛异常。"""

    errors = []

    @classmethod
    def showerror(cls, title, msg):
        cls.errors.append((title, msg))


def _fake_tk():
    _Msg.errors = []
    return _Tk(), _Ttk(), _Msg, _ScrolledMod()


def _by(cls):
    return [w for w in _W._reg if isinstance(w, cls)]


@pytest.fixture()
def _gui(monkeypatch):
    import sysweeper.gui as g

    _W._reg = []
    monkeypatch.setattr(g, "_tk", _fake_tk)
    inst = g.SysweeperGUI.__new__(g.SysweeperGUI)   # 跳过 __init__，只跑面板逻辑
    inst.root = object()
    return g.SysweeperGUI, inst


def _open(_gui, name):
    _W._reg = []
    return getattr(_gui[1], name)()


# ------------------------------- protec ---------------------------------- #

def test_show_protec_window(_gui):
    """「产品保护」面板（v0.6.69）：八轴三页 + 实测面页，不崩即过。"""
    top = _open(_gui, "show_protec")
    assert isinstance(top, _Toplevel)
    assert "产品" in (top._title or "") and "保护" in (top._title or "")
    texts = [s.content() for s in _by(_Scrolled)]
    joined = "\n".join(texts)
    # 页1 默认落 durability 轴：耐久 7 个概念
    assert "7 个概念" in joined and "耐久" in joined
    # 页2 桥接 34 条（v0.6.67 transfer +5、v0.6.68 access +5、v0.6.69 ipv6 +10）
    assert "桥接边 34 条" in joined
    # 页4 实测面：CLI 子命令实测值
    assert any("128" in t for t in texts)


def test_protec_axis_switch(_gui):
    """轴下拉切换到 electrical：电气 6 条目应出现。"""
    _open(_gui, "show_protec")
    var = next(v for v in _by(_Var) if v.get() in (
        "durability", "electrical", "environment", "emergency", "protection",
        "transfer", "access", "ipv6"))
    var.set("electrical")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 6
    assert any(c["domain"] == "electrical" for c in lbs[0]._data)


def test_protec_bridges(_gui):
    """桥接页列出 34 条边，目标系统均非悬空（构建期已校验）。"""
    _open(_gui, "show_protec")
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 34
    lbs[1].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "→" in text and "关系" in text


def test_protec_verify_note_rendered(_gui):
    """待核实页：8 项挂牌，说明文字必须渲染出来（protec 用 note 字段）。"""
    _open(_gui, "show_protec")
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 8
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "标准" in text or "口径" in text or "版本" in text


def test_protec_transfer_axis(_gui):
    """轴下拉切换到 transfer：传输与可用性 8 条目应出现（v0.6.67 新增）。"""
    _open(_gui, "show_protec")
    var = next(v for v in _by(_Var) if v.get() == "durability")
    var.set("transfer")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 8
    assert any(c["domain"] == "transfer" for c in lbs[0]._data)


def test_protec_access_axis(_gui):
    """轴下拉切换到 access：接入与链路层 7 条目应出现（v0.6.68 新增，v0.6.69 补星闪）。"""
    _open(_gui, "show_protec")
    var = next(v for v in _by(_Var) if v.get() == "durability")
    var.set("access")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 7
    assert any(c["domain"] == "access" for c in lbs[0]._data)


def test_protec_ipv6_axis(_gui):
    """轴下拉切换到 ipv6：IPv6 与 ICMPv6 控制面 10 条目应出现（v0.6.69 新增）。"""
    _open(_gui, "show_protec")
    var = next(v for v in _by(_Var) if v.get() == "durability")
    var.set("ipv6")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 10
    assert any(c["domain"] == "ipv6" for c in lbs[0]._data)
