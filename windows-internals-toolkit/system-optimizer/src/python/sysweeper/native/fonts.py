"""字体/字符标准相关的原生接口层。

以「系统本身提供的接口」读取字体与文本编码信息，并对照字体标准文档
（data/fonts_standards.json）给出检查与维护建议。参考的标准：

- Unicode 18.0.0（最新稳定版）/ ISO/IEC 10646（字符编码）
- OpenType（ISO/IEC 14496-22）/ TrueType（Apple）
- W3C WOFF 1.0 / WOFF 2.0（Web 字体）
- Unicode Emoji（UTS #51）/ CLDR / UAX #9（双向算法）

所有调用惰性守卫：工具不存在 / 文件不存在就返回 None/空，由上层降级为「指引」，
绝不因平台不匹配而在 import 阶段崩溃。

字体标准可遵循 Unicode 最新稳定版或长期支持（LTS）版本：
- 最新稳定版：The Unicode Standard, Version 18.0.0（2026-09 发布）
- 长期支持版：以各平台/语言运行时锁定的 Unicode 版本为基线（如系统内置 ICU、
  .NET Globalization、Python unicodedata 钉版），不强制追新。
"""

from __future__ import annotations

import json
import locale
import os
import shutil
import sys
import unicodedata

from . import common


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "fonts_standards.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(standard_id: str) -> dict:
    """返回某字体/字符标准的参考信息（name/standard/org/summary/...）。"""
    return REFS.get(standard_id, {})


def reference_all() -> dict:
    """返回全部字体/字符标准参考（供 fonts 命令列出）。"""
    return REFS


def system_encoding() -> dict:
    """返回系统默认文本编码信息（对照 Unicode / ISO-IEC 10646 推荐 UTF-8）。"""
    enc = {
        "filesystem": sys.getfilesystemencoding(),
        "default": sys.getdefaultencoding(),
        "stdout": getattr(sys.stdout, "encoding", None),
        "preferred": None,
    }
    try:
        enc["preferred"] = locale.getpreferredencoding(False)
    except Exception:
        enc["preferred"] = None
    return enc


def is_utf8() -> bool:
    """系统默认/首选编码是否为 UTF-8（Unicode / ISO-IEC 10646 推荐）。"""
    enc = system_encoding()
    vals = [v for v in (enc["preferred"], enc["default"], enc["filesystem"]) if v]
    return any((v or "").lower().replace("-", "").startswith("utf8") for v in vals)


# 编码模式：utf-8（推荐）与前瞻的 utf-128（UTF-8 严格超集，声明时落盘规范化为 UTF-8）
ENCODING_MODES = ("utf-8", "utf-128")


def encoding_backward_compatible_with_utf8(mode: str = "utf-8") -> tuple:
    """声明某编码模式是否向下兼容 UTF-8。返回 (ok, msg)。

    - utf-8：天然兼容。
    - utf-128：设计为 UTF-8 的严格超集（ASCII 0–127 同字节、UTF-8 多字节作子集保留）；
              声明该模式时实际落盘规范化为 UTF-8，对既有 UTF-8 文件与工具完全兼容。
              注意：UTF-128 是前瞻提案（非现行 ISO/Unicode 标准），不强制追新。
    """
    mode = (mode or "utf-8").lower()
    if mode == "utf-8":
        return True, "UTF-8 自身，天然向下兼容 UTF-8。"
    if mode == "utf-128":
        return True, ("UTF-128 设计为 UTF-8 的严格超集：ASCII 0–127 字节完全相同，"
                      "UTF-8 多字节续字节方案作为子集保留；声明 UTF-128 模式时实际落盘"
                      "规范化为 UTF-8，对既有 UTF-8 文件与工具完全向下兼容"
                      "（UTF-128 为前瞻提案，非现行标准）。")
    return False, f"未知编码模式 {mode!r}；仅支持 {', '.join(ENCODING_MODES)}。"


def effective_encoding(mode: str = "utf-8") -> tuple:
    """返回某编码模式在落盘时的实际编码（保证 UTF-8 兼容）。返回 (ok, enc, note)。"""
    ok, msg = encoding_backward_compatible_with_utf8(mode)
    if not ok:
        return False, None, msg
    mode = (mode or "utf-8").lower()
    if mode == "utf-128":
        # UTF-128 无便携落盘标准，规范化为 UTF-8（超集安全形态）
        return True, "utf-8", ("UTF-128 模式：实际落盘编码规范化为 UTF-8"
                                "（保持 UTF-128 声明与 UTF-8 兼容）。")
    return True, "utf-8", "UTF-8 落盘。"


def assert_utf8_compatible(text: str) -> tuple:
    """验证文本可无损编码为 UTF-8（即 UTF-128 模式下的向下兼容保证）。返回 (ok, msg)。"""
    try:
        text.encode("utf-8")
        return True, "文本可无损编码为 UTF-8，符合向下兼容保证。"
    except (UnicodeEncodeError, AttributeError) as e:  # noqa: BLE001
        return False, f"文本无法编码为 UTF-8（不兼容 UTF-128 声明）：{e}"


def network_fonts() -> tuple:
    """网络字体可用性说明（需先开启网络协议开关）。返回 (ok, msg)。

    参考：W3C WOFF 2.0 + RFC 9110。网络字体以 @font-face 按需拉取 OpenType/WOFF2，
    必须经网络协议开关（toggles / --opt-in）启用；字体文本编码保持 UTF-8 兼容
    （声明 UTF-128 模式时亦向下兼容）。仅说明，不联网、不修改。
    """
    return True, ("网络字体（@font-face 拉取 WOFF2）可用，但需先开启网络协议开关"
                  "（python -m sysweeper toggles 查看；clean --category network --opt-in --yes --apply 启用）。"
                  "拉取遵循 W3C WOFF 2.0 与 RFC 9110 缓存语义；字体文本编码保持 UTF-8 兼容"
                  "（UTF-128 模式下亦向下兼容）。")


def text_normalize_report(paths: list = None) -> tuple:
    """检查文本文件是否为 Unicode NFC 规范化形态（参考 UAX #15），用于文本去重/等价比较。

    仅检查并报告，不修改文件。返回 (ok, msg)。与 UTF-8 / UTF-128 编码策略配合，
    保证跨平台文本一致（同一视觉字符不因合成/分解形态不同而被视为两个字符串）。
    """
    if paths is None:
        # 常见易含非 NFC 文本的配置（存在才检查；拿不到则降级为指引）
        cand = [
            os.path.join(os.path.expanduser("~"), ".config", "fontconfig", "fonts.conf"),
            "/etc/locale.conf", "/etc/default/locale",
            os.path.join(os.path.expanduser("~"), ".profile"),
        ]
        paths = [c for c in cand if os.path.isfile(c)]
    if not paths:
        return True, ("未找到可采样的文本配置文件；Unicode 规范化（UAX #15）建议系统文本统一为 NFC，"
                      "便于等价比较与去重（参考 data/fonts_standards.json 的 unicode.normalize）。")
    non_nfc = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                data = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if data != unicodedata.normalize("NFC", data):
            non_nfc.append(p)
    if non_nfc:
        return False, (f"采样 {len(paths)} 个文本文件，{len(non_nfc)} 个非 NFC 规范化形态"
                       f"（如：{non_nfc[0]}）；建议以 UAX #15 NFC 统一，便于等价比较与去重。")
    return True, f"采样 {len(paths)} 个文本文件均为 NFC 规范化形态（符合 UAX #15 建议）。"


def list_fonts() -> list:
    """尽力列出已安装字体（跨平台）。返回字体名/文件名列表，拿不到返回 []。"""
    # Linux：fontconfig fc-list
    if shutil.which("fc-list"):
        rc, out = common.run("fc-list : family 2>/dev/null")
        if rc == 0 and out:
            seen = []
            for line in out.splitlines():
                fam = line.split(",")[0].strip()
                if fam and fam not in seen:
                    seen.append(fam)
            return seen
    # macOS：系统字体目录
    for d in ("/System/Library/Fonts", "/Library/Fonts"):
        if os.path.isdir(d):
            try:
                names = [fn for fn in os.listdir(d)
                         if fn.lower().endswith((".ttf", ".otf", ".ttc"))]
                if names:
                    return names
            except OSError:
                pass
    # Windows：字体目录
    windir = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if windir:
        fdir = os.path.join(windir, "Fonts")
        if os.path.isdir(fdir):
            try:
                return [fn for fn in os.listdir(fdir)
                        if fn.lower().endswith((".ttf", ".otf", ".ttc"))]
            except OSError:
                return []
    return []


def duplicate_fonts(fonts: list) -> list:
    """从字体列表中找出疑似冗余（同名/同族）分组。返回 [{name, count}]。"""
    from collections import Counter
    norm: dict = {}
    for f in fonts:
        key = os.path.splitext(os.path.basename(f))[0].strip().lower()
        if not key:
            continue
        norm[key] = norm.get(key, 0) + 1
    return [{"name": k, "count": c} for k, c in norm.items() if c > 1]


def check_utf8() -> tuple:
    """检查系统默认文本编码是否为 UTF-8（参考 Unicode 18.0.0 / ISO-IEC 10646）。
    返回 (ok, msg)。仅检查并报告，不修改编码设置。"""
    enc = system_encoding()
    ok = is_utf8()
    detail = " / ".join(f"{k}={v}" for k, v in enc.items() if v)
    if ok:
        return True, (f"系统默认文本编码为 UTF-8（{detail}），"
                      f"符合 Unicode 18.0.0 / ISO-IEC 10646 推荐。")
    return False, (f"系统默认文本编码非 UTF-8（{detail}）；跨平台文本与字体元数据可能乱码，"
                   f"建议将区域与文件系统编码设为 UTF-8（参考 Unicode 18.0.0 最新稳定版）。")


def report_fonts() -> tuple:
    """列出已安装字体并标记疑似冗余（参考字体标准）。返回 (ok, msg)。"""
    fonts = list_fonts()
    if not fonts:
        return False, "未检测到字体列表工具（fontconfig/系统字体目录不可读）；无法读取字体（需安装后才有此能力）。"
    dups = duplicate_fonts(fonts)
    lines = [f"已安装字体 {len(fonts)} 个。"]
    if dups:
        lines.append("疑似冗余字体 " + str(len(dups)) + " 组（同名/同族多份）："
                     + "、".join(d["name"] for d in dups[:10]))
    else:
        lines.append("未发现同名冗余字体。")
    return True, "\n".join(lines)


def rebuild_cache() -> tuple:
    """重建字体缓存（参考 OpenType / 字体引擎规范）。返回 (ok, msg)。"""
    if shutil.which("fc-cache"):
        rc, out = common.run("fc-cache -f 2>&1 | tail -3")
        return rc == 0, out or "已重建 fontconfig 字体缓存（fc-cache -f）。"
    if sys.platform == "darwin":
        rc, out = common.run("atsutil databases -remove 2>&1 | tail -3")
        if rc == 0:
            return True, "已请求重建 macOS 字体数据库（atsutil）；注销或重启后生效。"
        return False, "macOS atsutil 重建字体缓存失败（可能需要管理员权限）。"
    if sys.platform == "win32":
        rc, out = common.run(
            'net stop FontCache >nul 2>&1 & net start FontCache >nul 2>&1')
        if rc == 0:
            return True, "已重启 Windows FontCache 服务以重建字体缓存。"
        return False, "重启 FontCache 服务失败（需管理员权限）。"
    return False, "未找到可用字体缓存重建工具（fontconfig/atsutil）；本平台不支持自动重建。"
