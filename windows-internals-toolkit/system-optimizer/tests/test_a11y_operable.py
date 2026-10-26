"""前端运动/肢体无障碍门禁测试（0000.0000.0000.0017.20261025）：WCAG 2.2 Operable 契约静态扫描。

契约来源：docs/66《前端运动/肢体无障碍规范（WCAG Operable 落地）》§二–§五；
验收方法：docs/66 §九「静态扫描」——对目标 HTML 全文计数 focus-visible / min-width / min-height /
tabindex / role= / aria- / skip link / landmark 模式，对照差距清单逐项销项。

架构口径：两页均为「生成器烘焙单文件」——DOM 由页面内 JS 于运行时构建
（el() setAttribute / innerHTML 模板），故静态扫描断言**源文件中的契约模式**
（属性设置串 / 模板串 / keydown 处理器），运行时人工键盘实测按 docs/66 §九第二项执行。

另含 JS 语法门禁（2026-10-25 修复 report_viewer base64url 转义 bug 后固化）：
提取两页内联 <script> 交 node --check，node 缺席时跳过。
"""

import os
import re
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONCEPT_GUI = os.path.join(ROOT, "concept_gui.html")
REPORT_VIEWER = os.path.join(ROOT, "report_viewer.html")
GEN_CONCEPT = os.path.join(ROOT, "tools", "gen_concept_gui.py")
GEN_VIEWER = os.path.join(ROOT, "src", "deno", "report_viewer.ts")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _css_rules(text):
    """去注释后的 CSS 规则行集合（跳过 /* */ 注释，防注释字样误伤）。"""
    lines = []
    for line in text.splitlines():
        if "/*" in line or "*/" in line:
            continue
        lines.append(line)
    return "\n".join(lines)


# ---------- 2.4.7 焦点可见：:focus-visible 兜底 ----------

def test_focus_visible_fallback_both_pages():
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        html = _read(p)
        assert ":focus-visible{outline:2px solid var(--acc)" in html, f"{os.path.basename(p)} 缺 :focus-visible 兜底（2.4.7）"


def test_no_bare_outline_none():
    """docs/66 §四红线：禁裸 outline:none 无替代（仅查 CSS 规则，注释字样不误伤）。"""
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        css = _css_rules(_read(p))
        for m in re.finditer(r"outline:\s*none\s*[;}]", css):
            ctx = css[max(0, m.start() - 120):m.start()]
            assert "outline-offset" in ctx or "outline:" in ctx.replace("outline:none", ""), \
                f"{os.path.basename(p)} 裸 outline:none 无替代"


# ---------- 2.5.8 目标尺寸 ≥24×24 CSS px ----------

def test_target_size_min_24px():
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        html = _read(p)
        assert "min-width:24px" in html and "min-height:24px" in html, f"{os.path.basename(p)} .btn 未达 24×24 CSS px（2.5.8）"


def test_matrix_cells_ge_24px():
    """矩阵格子命中区 36×26 CSS px（既有 .mx td 宽高），≥24×24 契约。"""
    html = _read(CONCEPT_GUI)
    assert "width:36px;height:26px" in html, "矩阵 td 尺寸非 36×26，需复核 2.5.8"


# ---------- 2.4.1 landmark / skip link ----------

def test_landmarks_and_skip_link():
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        html = _read(p)
        assert "<header" in html and "<main" in html, f"{os.path.basename(p)} 缺 header/main landmark（2.4.1）"
        assert 'class="skip" href="#main"' in html, f"{os.path.basename(p)} 缺 skip link（2.4.1）"


# ---------- 2.1.1 自定义控件键盘可达：SVG 节点 / 矩阵格 / 中心 ----------

def test_svg_nodes_keyboard_operable():
    """运行时 DOM：core + 9 系统节点经 el() setAttribute 置 tabindex/role/aria-label（各 2 处设置串）；
    矩阵有数格经 innerHTML 模板 tabindex='0' role='button'；三处 keydown 处理器（g/core/td）。"""
    html = _read(CONCEPT_GUI)
    assert html.count('tabindex:"0"') >= 2, f"SVG 可聚焦属性设置仅 {html.count(chr(34).join(['tabindex:', '0', '']))} 处（应 ≥2：中心 + 节点模板）"
    assert "tabindex='0' role='button'" in html, "有数矩阵格未键盘化（2.1.1）"
    assert html.count('role:"button"') >= 2, "SVG 控件缺 role=button（el() 属性设置串）"
    assert '"aria-label":"聚焦 ' in html, "SVG 节点缺 aria-label（el() 属性设置串）"
    assert html.count('e.key === "Enter"') >= 3, "Enter/Space 键控处理器少于 3 处（g/core/td）"


def test_matrix_cells_keyboard_operable():
    html = _read(CONCEPT_GUI)
    assert "tabindex='0' role='button'" in html, "有数矩阵格未键盘化（2.1.1）"


def test_report_viewer_native_buttons():
    """report_viewer 交互均为原生 <button>/<input>（默认可达），无需 tabindex 补偿。"""
    html = _read(REPORT_VIEWER)
    assert html.count("<button") >= 5, "原生 button 少于 5 个"
    assert '<input type="file"' in html, "文件选择缺原生 input"


# ---------- 2.1.4 单字符快捷键：本页无单字符快捷键，自然满足 ----------

def test_no_character_key_shortcuts():
    """docs/66 §二：无单字符快捷键即自然满足 2.1.4；若未来新增须可关闭。"""
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        html = _read(p)
        assert "addEventListener(\"keypress\"" not in html, f"{os.path.basename(p)} 出现 keypress 单字符监听，需按 2.1.4 复核"


# ---------- 2.5.7 拖拽替代：本页无拖拽操作（click 聚焦模型），自然满足 ----------

def test_no_dragging_movements():
    """click 聚焦模型，无 dragstart/setPointerCapture 平移缩放——2.5.7 自然满足。"""
    html = _read(CONCEPT_GUI)
    assert "dragstart" not in html and "setPointerCapture" not in html, "出现拖拽实现，须按 2.5.7 补非拖拽替代"


# ---------- JS 语法门禁（node --check；node 缺席跳过） ----------

def test_inline_js_syntax_valid():
    """两页内联 <script> 须通过 node --check。

    2026-10-25 修复：report_viewer.ts page() 模板中 base64url 行写 `\\/` `\\+`，
    按模板字符串语义产出 `/` `+`（无效正则 / 行注释），整块 script 语法错误、
    页面全部 JS 功能瘫痪；改双重转义后固化本门禁。
    """
    node = shutil.which("node")
    if not node:
        import pytest
        pytest.skip("node 不在 PATH，跳过 JS 语法门禁")
    for p in (CONCEPT_GUI, REPORT_VIEWER):
        html = _read(p)
        js = "\n;\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))
        assert js.strip(), f"{os.path.basename(p)} 未提取到内联 script"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(js)
            tmp = f.name
        try:
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True, timeout=60)
            assert r.returncode == 0, f"{os.path.basename(p)} 内联 JS 语法错误：{r.stderr[:300]}"
        finally:
            os.unlink(tmp)


# ---------- 生成器源码防回退断言 ----------

def test_generators_source_sync():
    gen_c = _read(GEN_CONCEPT)
    gen_v = _read(GEN_VIEWER)
    assert ":focus-visible{outline:2px solid var(--acc)" in gen_c, "gen_concept_gui.py 回退：缺 focus-visible"
    assert "min-width:24px;min-height:24px" in gen_c, "gen_concept_gui.py 回退：缺 24px"
    assert 'class="skip" href="#main"' in gen_c, "gen_concept_gui.py 回退：缺 skip link"
    assert "<header class=\"top\">" in gen_c and "<main class=\"main\" id=\"main\">" in gen_c, "gen_concept_gui.py 回退：缺 landmark"
    assert gen_c.count('tabindex:"0"') >= 2 and "keydown" in gen_c, "gen_concept_gui.py 回退：缺键盘可达"
    assert ":focus-visible{outline:2px solid var(--acc)" in gen_v, "report_viewer.ts 回退：缺 focus-visible"
    assert "min-width:24px;min-height:24px" in gen_v, "report_viewer.ts 回退：缺 24px"
    assert 'class="skip" href="#main"' in gen_v, "report_viewer.ts 回退：缺 skip link"
    assert "<header class=\"top\">" in gen_v and "<main class=\"wrap\" id=\"main\">" in gen_v, "report_viewer.ts 回退：缺 landmark"
