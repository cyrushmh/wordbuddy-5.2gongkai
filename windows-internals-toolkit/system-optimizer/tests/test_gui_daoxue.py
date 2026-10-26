"""GUI「道枢」治理层面板测试（show_daoxue，v0.6.58）。

gui.py 在无图形环境优雅降级，Tk() 需 DISPLAY；这里用最小 mock 把 tkinter 替掉，
真实跑面板逻辑，覆盖新增胶水代码，不依赖真实显示：
  · show_daoxue —— 道德经中心(81 章) / 早坛·晚坛功课 / 治理原则·桥接·检索 三页。
数据层由 test_daoxue.py 覆盖。
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
    Combobox = _Entry  # 只读下拉：值经 StringVar 读取，构造签名与 Entry 一致


class _ScrolledMod:
    ScrolledText = _Scrolled


def _fake_tk():
    return _Tk(), _Ttk(), None, _ScrolledMod()


def _by(cls):
    return [w for w in _W._reg if isinstance(w, cls)]


@pytest.fixture()
def _dxgui(monkeypatch):
    import sysweeper.gui as g

    _W._reg = []
    monkeypatch.setattr(g, "_tk", _fake_tk)
    stub = types.SimpleNamespace(root=object())
    return g.SysweeperGUI.show_daoxue(stub)


def test_show_daoxue_opens_window(_dxgui):
    assert isinstance(_dxgui, _Toplevel)
    assert "道枢" in (_dxgui._title or "")


def test_center_tab_lists_81_chapters(_dxgui):
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 81          # 道德经 81 章
    assert lbs[0]._data[25]["no"] == 26     # 第 26 章「重为轻根·静为躁君」
    lbs[0].fire()                           # 默认选中第 0 项（第 1 章）
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[0].master)
    assert "第1章（道经）" in text
    assert "治理原则" in text and "工程落法" in text


def test_office_tab_pre_default(_dxgui):
    menus = _by(_Var)
    assert menus[0].get() == "pre"          # 默认前置（早坛）
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 44          # 早坛节次
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "太上玄门早坛功课经" in text and "课义" in text
    lbs[1].fire()
    text2 = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "节旨" in text2


def test_office_tab_post_and_phase_filter(_dxgui):
    _by(_Var)[0].set("post")               # role_v → 晚坛
    _by(_Var)[1].set("结行")                # phase_v → 结行
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 3           # 晚坛·结行 3 节
    assert all(s["phase"] == "结行" for s in lbs[1]._data)


def test_principles_tab_and_search(_dxgui):
    # 原则页初始填充 15 条
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 15
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "桥接到既有概念系统" in text
    # 检索「水」应跨层命中（道德经/原则/二级）
    _by(_Var)[2].set("水")
    btn = next(b for b in _by(_Button) if b._text == "检索")
    btn.invoke()
    assert len(lbs[2]._data) >= 2
    assert any("道德经" in h["where"] for h in lbs[2]._data)


def test_principles_tab_verify_honesty(_dxgui):
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    # 3（心经/论语/道德经原文）+ 2（符图咒文不录、祝由疗效不采录）+ 28（方术存疑，含阵域 3 条）
    assert len(lbs[2]._data) == 33
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "心经" in text and "未提供原典" in text
    # 方术子层的存疑项也必须出现在待核实面板（民间口传一律挂牌）
    assert any("方术·" in d["item"] for d in lbs[2]._data)


def test_fangshu_tab_lists_items(_dxgui):
    """方术子层页（第四页）：59 条全列，选中显示工程落法与存疑挂牌。"""
    lbs = _by(_Listbox)
    assert len(lbs) == 4  # 道德经 / 早晚坛 / 原则桥接 / 方术 四页各一个
    flb = lbs[3]
    assert len(flb._data) == 59
    flb.fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is flb.master)
    assert "工程落法" in text and "归属治理原则" in text
    # 祝由一支的诚实红线在详情里可见
    hx = next(x for x in flb._data if x["id"] == "you-hongxian")
    assert "不主张" in hx["gist"]


def test_fangshu_search_entry_filters(_dxgui):
    """方术页检索框：输入关键词经 <KeyRelease> 实时过滤列表（联动 fangshu_search）。"""
    lbs = _by(_Listbox)
    flb = lbs[3]
    assert len(flb._data) == 59
    # 找方术页检索 Entry：逐个尝试，谁能让 flb 收缩即为目标
    targets = [w for w in _by(_Entry) if "<KeyRelease>" in w._cb]
    assert targets, "方术检索框未绑定 <KeyRelease>"
    found = None
    for e in targets:
        var = e._kw.get("textvariable")
        if not isinstance(var, _Var):
            continue
        var.set("符胆")
        e._cb["<KeyRelease>"]()
        if len(flb._data) < 59:
            found = e
            break
    assert found is not None, "检索框未能过滤方术列表"
    ids = [x["id"] for x in flb._data]
    assert len(ids) >= 1 and "fu-dan" in ids and "符胆" in flb._data[0]["gist"]
    # 清空恢复全量
    found._kw["textvariable"].set("")
    found._cb["<KeyRelease>"]()
    assert len(flb._data) == 59
