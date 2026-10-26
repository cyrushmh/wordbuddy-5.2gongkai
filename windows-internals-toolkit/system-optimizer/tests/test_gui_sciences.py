"""GUI 概念系统面板测试（show_sciences，v0.6.67）。

gui.py 在无图形环境优雅降级，Tk() 需 DISPLAY；这里用最小 mock 把 tkinter 替掉，
真实跑面板逻辑，覆盖新增胶水代码，不依赖真实显示：
  · show_sciences —— 分类轴八域（材料/热/气候/环境/物理/化学/生物/方法）/ 桥接 /
    检索·待核实 / 用户端面 四页（同 _axis_concept_window + _userface_tab）。
    是 protec 工程保护的科学底座。
数据层由 test_sciences.py 覆盖。
"""
from __future__ import annotations

import sys
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
    inst = g.SysweeperGUI.__new__(g.SysweeperGUI)
    inst.root = object()
    return g.SysweeperGUI, inst


def _open(_gui, name):
    _W._reg = []
    return getattr(_gui[1], name)()


# ------------------------------ sciences --------------------------------- #

def test_show_sciences_window(_gui):
    """「自然科学」面板（v0.6.67）：八轴三页 + 实测面页，不崩即过。"""
    top = _open(_gui, "show_sciences")
    assert isinstance(top, _Toplevel)
    assert "自然科学" in (top._title or "")
    texts = [s.content() for s in _by(_Scrolled)]
    joined = "\n".join(texts)
    # 页1 默认落 materials 轴：材料 4 个概念
    assert "4 个概念" in joined and "材料" in joined
    # 页2 桥接 18 条
    assert "桥接边 18 条" in joined
    # 页4 实测面：CLI 子命令实测值
    assert any("128" in t for t in texts)


def test_sciences_axis_switch(_gui):
    """轴下拉切换到 physics：物理 3 条目应出现。"""
    _open(_gui, "show_sciences")
    var = next(v for v in _by(_Var) if v.get() in (
        "materials", "thermodynamics", "climatology", "environmental",
        "physics", "chemistry", "biology", "methodology"))
    var.set("physics")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 3
    assert any(c["domain"] == "physics" for c in lbs[0]._data)


def test_sciences_bridges(_gui):
    """桥接页列出 18 条边，目标系统均非悬空（构建期已校验）。"""
    _open(_gui, "show_sciences")
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 18
    lbs[1].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "→" in text and "关系" in text


def test_sciences_verify_note_rendered(_gui):
    """待核实页：3 项挂牌，说明文字必须渲染出来（sciences 用 note 字段）。"""
    _open(_gui, "show_sciences")
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 3
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "标准" in text or "版本" in text
