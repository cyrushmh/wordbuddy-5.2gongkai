"""GUI 轴型概念系统面板测试（show_quantum / show_comp / show_apilab /
show_baigong / show_datong）。

gui.py 在无图形环境优雅降级，Tk() 需 DISPLAY；这里用最小 mock 把 tkinter 替掉，
真实跑面板逻辑，覆盖新增胶水代码，不依赖真实显示：
  · show_quantum —— 分类轴八域 / 桥接 / 检索·待核实 / 标准登记册 四页；
  · show_comp    —— 分类轴五轴 / 桥接 / 检索·待核实 / 语言编译需要 四页；
  · show_apilab  —— 分类轴五轴 / 桥接 / 检索·待核实 / 仓库接口面 / RFC 五页；
  · show_baigong —— 分类轴四轴 / 桥接 / 检索·待核实 / 用户端面 四页（v0.6.61）；
  · show_datong  —— 分类轴五轴 / 桥接 / 检索·待核实 / 实测面 四页（v0.6.62）。
数据层由 test_quantum.py / test_comp.py / test_apilab.py / test_baigong.py /
test_datong.py 覆盖。
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


# ------------------------------- quantum ---------------------------------- #

def test_show_quantum_window(_gui):
    top = _open(_gui, "show_quantum")
    assert isinstance(top, _Toplevel)
    assert "量子理念" in (top._title or "")


def test_quantum_axis_tab_default(_gui):
    top = _open(_gui, "show_quantum")
    lbs = _by(_Listbox)
    # 页1 分类轴：默认 state 域 8 个概念（0031 增 qudit-multi-level / 0032 增 qudit-register）
    assert len(lbs[0]._data) == 8
    assert all(c["domain"] == "state" for c in lbs[0]._data)
    lbs[0].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[0].master)
    assert "量子比特" in text and "纲宗" in text and "所属轴" in text


def test_quantum_axis_switch_domain(_gui):
    _open(_gui, "show_quantum")
    # 第一个 StringVar 是轴选择器；切到 algorithm 域应有 10 个概念
    _by(_Var)[0].set("algorithm")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 10
    assert any(c["id"] == "shor" for c in lbs[0]._data)


def test_quantum_bridges_and_search(_gui):
    _open(_gui, "show_quantum")
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 56          # 桥接边（v0.6.78 qkern 域 4 条 / v0.6.79 qkern 补全 3 条 / v0.6.80 network 域 5 条 / v0.6.81 网络域补 5 条指向 netsys 架构·硬件模块 / v0.6.82 quantum-network-topology → netsys:sysmesh 接入系统互联协调基底 / 0031 qudit 三位元 4 条）
    lbs[1].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "→" in text and "关系" in text
    # 页3 检索
    _by(_Var)[1].set("纠错")                 # 页2 目标系统选择器
    _by(_Var)[2].set("纠错")                 # 页3 关键词
    btn = next(b for b in _by(_Button) if b._text == "检索")
    btn.invoke()
    assert len(lbs[2]._data) >= 1


def test_quantum_standards_tab(_gui):
    _open(_gui, "show_quantum")
    lbs = _by(_Listbox)
    assert len(lbs) >= 4                    # 标准登记册是第 4 个 Listbox
    std_lb = lbs[3]
    assert len(std_lb._data) == 11         # v0.6.79：IEEE 7130 草案已核实 + 4 条 kernel.org 参考
    std_lb.fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is std_lb.master)
    assert "needs_verify" in text or "状态" in text


def test_quantum_verify_tab(_gui):
    _open(_gui, "show_quantum")
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 0           # v0.6.79：needs_verify 清零（IEEE 7130 草案已核实 / QV 方法论已引）
    # 清零后 GUI 不渲染内容面板，按钮与空列表即在位即可


# -------------------------------- comp ------------------------------------ #

def test_show_comp_window(_gui):
    top = _open(_gui, "show_comp")
    assert isinstance(top, _Toplevel)
    assert "编译" in (top._title or "")


def test_comp_axis_tab_default(_gui):
    _open(_gui, "show_comp")
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 10          # pipeline 轴（含 v0.6.63 新增 kernel-fusion→aski-pipeline）
    lbs[0].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[0].master)
    assert "编译流水线总览" in text and "桥接" in text


def test_comp_needs_tab_evidence(_gui):
    _open(_gui, "show_comp")
    lbs = _by(_Listbox)
    need_lb = lbs[3]                        # 语言编译需要页
    assert len(need_lb._data) == 15
    need_lb.fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is need_lb.master)
    assert "驱动" in text and "实测" in text


def test_comp_verify_honesty(_gui):
    _open(_gui, "show_comp")
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 1
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "146" in text


def test_comp_search_entry_realtime(_gui):
    """概念页检索框：<KeyRelease> 实时过滤检索列表（覆盖所有概念页）。"""
    import sysweeper.concepts.comp as cm
    _open(_gui, "show_comp")
    total = sum(len(cm.concepts_of_domain(d["domain"])) for d in cm.domains())
    assert total > 1
    targets = [w for w in _by(_Entry) if "<KeyRelease>" in w._cb]
    assert targets, "检索框未绑定 <KeyRelease>"
    ent = targets[0]
    var = ent._kw.get("textvariable")
    assert isinstance(var, _Var)
    # 输入关键词，经 KeyRelease 实时过滤
    var.set("mlir")
    ent._cb["<KeyRelease>"]()
    # 检索列表框 = 含 mlir 结果的那个（其余页不变）
    slb = next(lb for lb in _by(_Listbox)
               if lb._data and any("mlir" in (c.get("id", "") + c.get("name", "") +
                                              c.get("gist", "") + c.get("detail", "")).lower()
                                   for c in lb._data))
    assert 0 < len(slb._data) < total
    # 清空（空查询）→ 列表实时清空，符合通用面板语义
    var.set("")
    ent._cb["<KeyRelease>"]()
    assert len(slb._data) == 0


# ------------------------------- apilab ----------------------------------- #

def test_show_apilab_window(_gui):
    top = _open(_gui, "show_apilab")
    assert isinstance(top, _Toplevel)
    assert "接口" in (top._title or "")


def test_apilab_axis_tab_default(_gui):
    _open(_gui, "show_apilab")
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) == 11          # style 轴（含 v0.6.63 新增 c-abi/guile-ffi）
    lbs[0].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[0].master)
    assert "REST" in text and "标准依据" in text and "9110" in text


def test_apilab_repo_and_rfc_tabs(_gui):
    _open(_gui, "show_apilab")
    lbs = _by(_Listbox)
    rfc_lb = lbs[3]                         # RFC 依据页（第 4 个 Listbox）
    assert len(rfc_lb._data) == 12
    rfc_lb.fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is rfc_lb.master)
    assert "9110" in text or "引用概念" in text
    # 仓库接口面页是纯文本页（ ScrolledText 直接填充）
    repo_texts = [s.content() for s in _by(_Scrolled)
                  if "webapi_actions" in s.content()]
    assert repo_texts and "29" in repo_texts[0] and str(
        _live_cli_count()) in repo_texts[0]


def _live_cli_count() -> int:
    from sysweeper.cli import build_parser
    n = 0
    for a in build_parser()._actions:
        if a.__class__.__name__ == "_SubParsersAction":
            n = len(a.choices)
    return n


def test_apilab_search_auth(_gui):
    _open(_gui, "show_apilab")
    lbs = _by(_Listbox)
    _by(_Var)[2].set("令牌")
    btn = next(b for b in _by(_Button) if b._text == "检索")
    btn.invoke()
    assert len(lbs[2]._data) >= 1


# --------------------------- concepts center ------------------------------ #

def test_show_concepts_center(_gui):
    top = _open(_gui, "show_concepts_center")
    assert isinstance(top, _Toplevel)
    assert "概念系统中心" in (top._title or "")


def test_concepts_center_lists_eleven(_gui):
    _open(_gui, "show_concepts_center")
    lbs = _by(_Listbox)
    assert lbs[0]._data == ["plang", "netsys", "daoxue", "quantum",
                            "comp", "apilab", "zhuangzi", "baigong", "datong",
                            "protec", "sciences"]
    texts = [s.content() for s in _by(_Scrolled)]
    assert any("81" in t and "quantum" in t for t in texts)
    assert any("63" in t and "datong" in t for t in texts)


def test_concepts_center_search_all(_gui):
    _open(_gui, "show_concepts_center")
    _by(_Var)[0].set("编译")
    btn = next(b for b in _by(_Button) if b._text == "跨系统检索")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[0]._data) >= 2
    assert any(h.get("system") in ("comp", "quantum") for h in lbs[0]._data)


# ------------------------------- baigong ---------------------------------- #

def test_show_baigong_window(_gui):
    """「百工理念」面板（v0.6.61）：四轴三页 + 实测面页，不崩即过。"""
    top = _open(_gui, "show_baigong")
    assert isinstance(top, _Toplevel)
    texts = [s.content() for s in _by(_Scrolled)]
    joined = "\n".join(texts)
    assert "墨子" in joined
    assert any("128" in t for t in texts)  # 用户端面实测（CLI 子命令，qarch 117→…→cnstd 125→protec/sciences 127→nettransfer 128）


def test_baigong_axis_switch(_gui):
    """轴下拉切换到 schools：三教九流条目应出现。"""
    _open(_gui, "show_baigong")
    var = next(v for v in _by(_Var) if v.get() in ("core", "craft", "schools", "scenes"))
    var.set("schools")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    texts = [s.content() for s in _by(_Scrolled)]
    assert any("三教" in t or "九流" in t for t in texts)


# ------------------------------- datong ----------------------------------- #

def test_show_datong_window(_gui):
    """「大同理念」面板（v0.6.62）：五轴三页 + 实测面页。"""
    top = _open(_gui, "show_datong")
    assert isinstance(top, _Toplevel)
    assert "大同" in (top._title or "")
    texts = [s.content() for s in _by(_Scrolled)]
    joined = "\n".join(texts)
    # 页1 默认落traditions 轴：文明传统 15 条
    assert "15 个概念" in joined and "文明传统" in joined
    # 页2 桥接 51 条
    assert "桥接边 51 条" in joined
    # 页4 实测面：六象尾注 + CLI 子命令实测值
    assert any("正道六象" in t for t in texts)
    assert any("128" in t for t in texts)  # 用户端面实测（CLI 子命令，qarch 117→…→cnstd 125→protec/sciences 127→nettransfer 128）


def test_datong_axis_switch(_gui):
    """轴下拉切换到 six：正道六象六条目应出现（固/液/气/电/磁/波）。"""
    _open(_gui, "show_datong")
    var = next(v for v in _by(_Var)
               if v.get() in ("traditions", "theses", "six", "practices", "ethics"))
    var.set("six")
    btn = next(b for b in _by(_Button) if b._text == "列出")
    btn.invoke()
    lbs = _by(_Listbox)
    assert [c["id"] for c in lbs[0]._data] == ["gu", "ye", "qi", "dian", "ci", "bo"]
    lbs[0].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[0].master)
    assert "元阳" in text or "元阴" in text


def test_datong_bridges(_gui):
    """桥接页列出 51 条边，目标系统均非悬空（构建期已校验）。"""
    _open(_gui, "show_datong")
    lbs = _by(_Listbox)
    assert len(lbs[1]._data) == 51
    lbs[1].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[1].master)
    assert "→" in text and "关系" in text


def test_datong_verify_note_rendered(_gui):
    """待核实页：7 项挂牌，说明文字必须渲染出来（datong 用 note 字段）。"""
    _open(_gui, "show_datong")
    btn = next(b for b in _by(_Button) if b._text == "待核实")
    btn.invoke()
    lbs = _by(_Listbox)
    assert len(lbs[2]._data) == 7
    lbs[2].fire()
    text = next(s.content() for s in _by(_Scrolled) if s.master is lbs[2].master)
    assert "通古斯" in text or "正名约定" in text or "原典" in text


# ------------------------- quantum VM（v0.6.68 面板） ----------------------- #

def test_show_quantum_vm_window(_gui):
    top = _open(_gui, "show_quantum_vm")
    assert isinstance(top, _Toplevel)
    assert "量子虚拟机" in (top._title or "")


def test_quantum_vm_runs_builtin(_gui):
    _open(_gui, "show_quantum_vm")
    box = _by(_Scrolled)[0]
    run_btn = next(b for b in _by(_Button) if b._text == "运行")
    run_btn.invoke()
    out = box.content()
    assert "内置程序 bell" in out
    assert "00:" in out and "11:" in out


def test_quantum_vm_runs_architecture_demo(_gui):
    _open(_gui, "show_quantum_vm")
    box = _by(_Scrolled)[0]
    arch_btn = next(b for b in _by(_Button) if b._text == "架构演示")
    arch_btn.invoke()
    out = box.content()
    assert "架构基座演示" in out
    assert "halt" in out and "链路统计" in out


def test_quantum_vm_runs_custom_ir(_gui):
    _open(_gui, "show_quantum_vm")
    boxes = _by(_Scrolled)
    custom_btn = next(b for b in _by(_Button) if b._text == "运行自定义程序")
    custom_btn.invoke()
    out = boxes[0].content()
    assert "自定义程序" in out
    assert "000:" in out and "111:" in out  # 默认 IR 是 GHZ


def test_quantum_vm_invalid_ir_reports_error(_gui):
    _open(_gui, "show_quantum_vm")
    boxes = _by(_Scrolled)
    ir_box = boxes[1]
    ir_box._buf = []
    ir_box.insert("end", "not_a_gate 0")
    custom_btn = next(b for b in _by(_Button) if b._text == "运行自定义程序")
    custom_btn.invoke()
    assert "[失败]" in boxes[0].content()
