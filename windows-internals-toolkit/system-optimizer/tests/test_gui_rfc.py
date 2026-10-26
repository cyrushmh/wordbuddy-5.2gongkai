"""GUI 知识库面板测试（show_rfc v0.6.52 / show_langref v0.6.54）。

gui.py 在无图形环境优雅降级，Tk() 需 DISPLAY；这里用最小 mock 把 tkinter 替掉，
真实跑面板逻辑，覆盖新增胶水代码，不依赖真实显示：
  · show_rfc     —— 主题域 / 工作组 / 单号查询 三页；
  · show_langref —— 窗口内 / 分类·来源 / 检索·待核实 三页。
数据层分别由 test_rfc_catalog.py、test_langs.py 覆盖。
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
    pass


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


def _qbox():
    """单号查询页的文本框：其 master 帧不含任何 Listbox。"""
    lb_masters = {w.master for w in _by(_Listbox)}
    for s in _by(_Scrolled):
        if s.master not in lb_masters:
            return s
    return None


@pytest.fixture()
def _gui(monkeypatch):
    import sysweeper.gui as g

    _W._reg = []
    monkeypatch.setattr(g, "_tk", _fake_tk)
    stub = types.SimpleNamespace(root=object())
    top = g.SysweeperGUI.show_rfc(stub)
    return top


def test_show_rfc_opens_rfc_window(_gui):
    assert isinstance(_gui, _Toplevel)
    assert "RFC 知识库" in (_gui._title or "")


def test_topic_tab_shows_members(_gui):
    lbs = [w for w in _by(_Listbox) if w._data and isinstance(w._data[0], dict)]
    assert lbs, "主题域 Listbox 未填充"
    lb = lbs[0]
    lb.fire()  # 默认选中第 0 项
    box = _by(_Scrolled)[0]  # 主题域页文本框（与首个 listbox 同帧）
    text = next((s.content() for s in _by(_Scrolled)
                 if s.master is lb.master), "")
    assert "路由与交换" in text or "RFC" in text


def test_wg_tab_shows_members(_gui):
    lbs = [w for w in _by(_Listbox) if w._data and isinstance(w._data[0], tuple)]
    assert lbs, "工作组 Listbox 未填充"
    lb = lbs[0]
    lb.fire()
    # 该页文本框：master 与 wg listbox 相同
    text = next((s.content() for s in _by(_Scrolled)
                 if s.master is lb.master), "")
    assert "RFC" in text


def test_query_tab_reports_tls_attribution(_gui):
    qvar = _by(_Var)[0]
    qvar.set("8446")
    btn = next(b for b in _by(_Button) if b._text == "查询")
    btn.invoke()
    qbox = _qbox()
    assert qbox is not None
    out = qbox.content()
    assert "RFC 8446" in out
    assert "Transport Layer Security" in out  # 官方 WG 归属
    assert "tls-pki" in out                     # heuristic 主题域归属


# ---------------- show_langref（编程语言库，v0.6.54）---------------- #

@pytest.fixture()
def _langref(monkeypatch):
    import sysweeper.gui as g

    _W._reg = []
    monkeypatch.setattr(g, "_tk", _fake_tk)
    stub = types.SimpleNamespace(root=object())
    return g.SysweeperGUI.show_langref(stub)


def test_show_langref_opens_window(_langref):
    assert "编程语言库" in (_langref._title or "")


def test_langref_window_tab_lists_in_window(_langref):
    lbs = _by(_Listbox)
    assert lbs[0]._data, "窗口内 Listbox 未填充"
    assert len(lbs[0]._data) == 72        # 2008–2026 窗口内
    # 最新年份为 2024（同年有多条，排序稳定，不断言具体 id）
    assert lbs[0]._data[0]["first_year"] == 2024
    assert all(2008 <= e["first_year"] <= 2026 for e in lbs[0]._data)
    lbs[0].fire()
    box = _by(_Scrolled)[0]
    assert "首现年：2024" in box.content()
    assert "发布沿革" in box.content()


def test_langref_category_button_fills(_langref):
    btn = next(b for b in _by(_Button) if b._text == "按分类列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) >= 1         # compiled 分类
    assert all(e["category"] == "compiled" for e in lbs[1]._data)
    lbs[1].fire()
    assert "类型系统" in _by(_Scrolled)[1].content()


def test_langref_origin_button_domestic(_langref):
    _by(_Var)[1].set("国内")              # org_v
    btn = next(b for b in _by(_Button) if b._text == "按来源列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert all(e["origin"] == "国内" for e in lbs[1]._data)
    assert "wenyan" in {e["id"] for e in lbs[1]._data}


def test_langref_search_finds_rust(_langref):
    _by(_Var)[2].set("rust")              # sv
    btn = next(b for b in _by(_Button) if b._text == "检索")
    btn.invoke()
    lbs = _by(_Listbox)
    assert any(e["id"] == "rust" for e in lbs[2]._data)
    lbs[2].fire()
    assert "Rust" in _by(_Scrolled)[2].content()


def test_langref_verify_button_lists_needs_verify(_langref):
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 12
    lbs[2].fire()
    assert "待核实" in _by(_Scrolled)[2].content()
