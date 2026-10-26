"""多来源导入层（v0.6.23）：剪贴板 / 本地文件 / 二维码（图片文件 + 摄像头）。

对齐用户要求「能够导入剪贴板、本地文件、二维码的扫码和读取（支持通过文件读取图片）」。

四种来源，统一返回 ``(ok, text, note)``：

- **剪贴板**   : Linux(xclip/xsel/wl-copy) → macOS(osascript) → Windows(powershell)
                 → 都不行回退 tk；**取不到纯文本时再试剪贴板截图里的二维码**
                 （Windows/macOS 可用；Linux 桌面取不到剪贴板图像，会如实说明）。
                 全部只读，**不写回剪贴板**。
- **本地文件** : 文本文件按 UTF-8（容错 Latin-1）读入，受 ``import.max_bytes`` 限制。
- **图片二维码**: 从 PNG/JPG/BMP 等图片文件解码二维码（用户点名的「通过文件读取图片」）。
                 后端 ``qr.backend``：auto = OpenCV → pyzbar 依次降级。
- **摄像头扫码**: 可选能力，需 OpenCV；受 ``qr.camera_timeout`` 限制，超时即结束。

红线（与全工具一致）：

- **只读**：不写剪贴板、不改被导入的文件、不联网。
- **绝不自动安装依赖**：二维码/剪贴板后端缺失时只给安装指引，不碰 pip。
- **导入内容绝不自动执行**：JSON 只做结构校验，是否载入为设置必须由用户确认。
- **绝不因来源异常抛错**：一律降级为 ``(False, "", 说明)``。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from . import settings as _settings

__all__ = [
    "ImportResult", "SOURCES",
    "read_clipboard", "read_text_file", "decode_qr_image", "scan_qr_camera",
    "read_qr_from_image", "import_from", "clipboard_backends", "qr_backends",
    "read_clipboard_image", "decode_qr_from_clipboard", "decode_qr_pil",
    "parse_settings_json", "capabilities_report", "importio_report",
]

# 来源标识（GUI 单选 / CLI --from 均用此 key）
SRC_CLIPBOARD = "clipboard"
SRC_FILE = "file"
SRC_QR = "qr"
SRC_CAMERA = "camera"

SOURCES: List[Tuple[str, str, str]] = [
    (SRC_CLIPBOARD, "剪贴板", "读取剪贴板文本；无文本时自动尝试剪贴板截图里的二维码"),
    (SRC_FILE, "本地文件", "读取本地文本文件（UTF-8，受读入上限限制）"),
    (SRC_QR, "图片二维码", "从本地图片文件解码二维码（PNG/JPG/BMP 等）"),
    (SRC_CAMERA, "摄像头扫码", "调用摄像头实时扫码（需 OpenCV，受超时阈值限制）"),
]


class ImportResult:
    """导入结果容器（也提供元组式解包，兼容既有 (ok, msg) 报告风格）。"""

    __slots__ = ("ok", "text", "note")

    def __init__(self, ok: bool, text: str = "", note: str = "") -> None:
        self.ok = bool(ok)
        self.text = text or ""
        self.note = note or ""

    def as_tuple(self) -> Tuple[bool, str, str]:
        return (self.ok, self.text, self.note)

    def report(self) -> Tuple[bool, str]:
        """转成 (ok, 摘要) —— 供 GUI/控制台直接显示。"""
        head = "导入成功" if self.ok else "导入失败"
        body = self.text if self.ok else self.note
        if self.ok and self.note:
            body = f"{self.text}\n（{self.note}）"
        return self.ok, f"{head}: {body}" if body else head

    def __iter__(self):
        return iter(self.as_tuple())

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"ImportResult(ok={self.ok!r}, text={self.text[:40]!r}, note={self.note!r})"


def _max_bytes() -> int:
    try:
        return int(_settings.get("import.max_bytes", 1048576))
    except (TypeError, ValueError):
        return 1048576


def _opt(key: str, fallback: str = "auto") -> str:
    try:
        v = _settings.get(key, fallback)
        return fallback if v is None else str(v)
    except (TypeError, ValueError):
        return fallback


# ─────────────────────────────────────────────────────────────────────────────
# 1) 剪贴板
# ─────────────────────────────────────────────────────────────────────────────
def _clip_commands() -> List[Tuple[str, List[str], str]]:
    """候选剪贴板读取命令（平台相关，按优先级排列）。"""
    if sys.platform == "darwin":
        return [("osascript", ["osascript", "-e", "the clipboard as text"], "osascript")]
    if os.name == "nt" or sys.platform.startswith("win"):
        return [("powershell", ["powershell", "-NoProfile", "-Command", "Get-Clipboard"], "powershell")]
    out: List[Tuple[str, List[str], str]] = []
    for exe in ("wl-copy", "xclip", "xsel"):
        p = shutil.which(exe)
        if not p:
            continue
        if exe == "wl-copy":
            out.append((exe, [p, "--paste"], "wl-copy(Wayland)"))
        elif exe == "xclip":
            out.append((exe, [p, "-selection", "clipboard", "-o"], "xclip(X11)"))
        else:
            out.append((exe, [p, "--clipboard", "--output"], "xsel(X11)"))
    return out


def clipboard_backends() -> List[str]:
    """返回当前平台可用的剪贴板后端名（不含 tk 兜底）。"""
    return [name for name, _cmd, _label in _clip_commands()]


def _clip_via_tk() -> ImportResult:
    """tk 兜底：无图形会话时静默失败（不弹窗、不抛错）。"""
    try:
        import tkinter  # noqa: WPS433 - 可选依赖，按需导入
    except Exception:
        return ImportResult(False, "", "tkinter 不可用")
    try:
        root = tkinter.Tk()
        root.withdraw()
        try:
            data = root.clipboard_get()
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        if data:
            return ImportResult(True, str(data), "tkinter")
        return ImportResult(False, "", "剪贴板为空（tkinter）")
    except Exception as e:  # noqa: BLE001
        return ImportResult(False, "", f"tkinter 读取失败: {e}")


def read_clipboard(backend: str = None) -> ImportResult:
    """读取系统剪贴板文本。

    backend 不传时取运行参数 ``clipboard.backend``（默认 auto=按平台自动挑）。
    """
    want = (backend or _opt("clipboard.backend", "auto")).strip().lower()
    cands = _clip_commands()
    if want and want != "auto":
        cands = [c for c in cands if c[0] == want]
        if not cands and want == "tk":
            return _clip_via_tk()
        if not cands:
            return ImportResult(False, "", f"指定后端不可用: {want}（可选: auto/"
                                           + "/".join(clipboard_backends() or ["tk"]) + "）")
    if not cands:
        return _clip_via_tk()
    errs: List[str] = []
    for name, cmd, label in cands:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and r.stdout:
                return ImportResult(True, r.stdout, label)
            errs.append(f"{name}: rc={r.returncode}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{name}: {e}")
    tk = _clip_via_tk()
    if tk.ok:
        return tk
    return ImportResult(False, "", "剪贴板读取失败（" + "; ".join(errs) + "; tk 亦不可用）")


# ─────────────────────────────────────────────────────────────────────────────
# 2) 本地文本文件
# ─────────────────────────────────────────────────────────────────────────────
def read_text_file(path: str, max_bytes: int = None) -> ImportResult:
    """读取本地文本文件（UTF-8，失败回退 Latin-1；受读入上限约束）。"""
    path = os.path.expanduser(path or "")
    if not path or not os.path.isfile(path):
        return ImportResult(False, "", f"文件不存在: {path}")
    cap = _max_bytes() if max_bytes is None else int(max_bytes)
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            raw = fh.read(cap)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
        note = f"{os.path.basename(path)} · {size} 字节"
        if size > cap:
            note += f"（超过上限 {cap} 字节，已截断）"
        if not text.strip():
            return ImportResult(False, "", f"文件内容为空: {path}")
        return ImportResult(True, text, note)
    except OSError as e:
        return ImportResult(False, "", f"读取失败: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 3) 图片文件 → 二维码解码
# ─────────────────────────────────────────────────────────────────────────────
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp")


def qr_backends() -> List[str]:
    """返回当前可用的二维码解码后端（['cv2'] / ['pyzbar'] / 组合 / []）。"""
    out: List[str] = []
    try:
        import cv2  # noqa: F401
        out.append("cv2")
    except Exception:
        pass
    try:
        from pyzbar import pyzbar  # noqa: F401
        out.append("pyzbar")
    except Exception:
        pass
    return out


def _qr_hint() -> str:
    return ("未检测到二维码解码库；任选其一安装后即可用（工具不会自动安装）: "
            "pip install opencv-python-headless  或  pip install pyzbar pillow"
            "（pyzbar 还需系统库 libzbar0: apt install libzbar0）")


def _decode_via_cv2(path: str) -> ImportResult:
    try:
        import cv2
    except Exception as e:
        return ImportResult(False, "", f"cv2 不可用: {e}")
    try:
        img = cv2.imread(path)
        if img is None:
            return ImportResult(False, "", f"无法读取图片: {path}")
        data, _pts, _straight = cv2.QRCodeDetector().detectAndDecode(img)
        if data:
            return ImportResult(True, str(data), "cv2(OpenCV)")
        return ImportResult(False, "", "图中未识别到二维码（cv2）")
    except Exception as e:  # noqa: BLE001
        return ImportResult(False, "", f"cv2 解码失败: {e}")


def _decode_via_pyzbar(path: str) -> ImportResult:
    try:
        from PIL import Image
        from pyzbar import pyzbar
    except Exception as e:
        return ImportResult(False, "", f"pyzbar 不可用: {e}")
    try:
        with Image.open(path) as im:
            res = pyzbar.decode(im)
        if not res:
            return ImportResult(False, "", "图中未识别到二维码（pyzbar）")
        items = [r.data.decode("utf-8", errors="replace") for r in res if getattr(r, "data", None)]
        if not items:
            return ImportResult(False, "", "二维码无有效内容（pyzbar）")
        return ImportResult(True, "\n".join(items), f"pyzbar × {len(items)}")
    except Exception as e:  # noqa: BLE001
        return ImportResult(False, "", f"pyzbar 解码失败: {e}")


def decode_qr_image(path: str, backend: str = None) -> ImportResult:
    """从本地图片文件解码二维码（用户点名的「支持通过文件读取图片」）。

    backend 不传时取运行参数 ``qr.backend``（auto = cv2 → pyzbar 依次降级）。
    """
    path = os.path.expanduser(path or "")
    if not path or not os.path.isfile(path):
        return ImportResult(False, "", f"图片不存在: {path}")
    if os.path.splitext(path)[1].lower() not in _IMG_EXTS:
        return ImportResult(False, "", f"不是受支持的图片格式: {path}（支持 "
                                       + "/".join(_IMG_EXTS) + "）")
    cap = _max_bytes()
    try:
        if os.path.getsize(path) > cap:
            return ImportResult(False, "", f"图片超过读入上限 {cap} 字节（可调 import.max_bytes）")
    except OSError:
        pass

    want = (backend or _opt("qr.backend", "auto")).strip().lower()
    avail = qr_backends()
    if not avail:
        return ImportResult(False, "", _qr_hint())
    order = avail if want == "auto" else ([want] if want in avail else [])
    if not order:
        return ImportResult(False, "", f"指定后端不可用: {want}（当前可用: {'/'.join(avail)}）")

    notes: List[str] = []
    for b in order:
        r = _decode_via_cv2(path) if b == "cv2" else _decode_via_pyzbar(path)
        if r.ok:
            return r
        notes.append(r.note)
    return ImportResult(False, "", "；".join(notes))


# 兼容别名（ photographers 直觉命名）
read_qr_from_image = decode_qr_image


def decode_qr_pil(img) -> ImportResult:
    """直接解码一张 PIL Image 对象（不落盘，内存里解码）。

    供「剪贴板截图」场景使用：截图进的是内存图像，没必要先写临时文件。
    """
    if img is None:
        return ImportResult(False, "", "没有图像")
    want = _opt("qr.backend", "auto")
    avail = qr_backends()
    if not avail:
        return ImportResult(False, "", _qr_hint())
    order = avail if want == "auto" else ([want] if want in avail else [])
    notes: List[str] = []
    for b in order:
        if b == "cv2":
            try:
                import numpy as np
                import cv2
                arr = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
                data, _pts, _ = cv2.QRCodeDetector().detectAndDecode(arr)
                if data:
                    return ImportResult(True, str(data), "cv2(OpenCV)")
                notes.append("图中未识别到二维码（cv2）")
            except Exception as e:  # noqa: BLE001
                notes.append(f"cv2 解码失败: {e}")
        else:
            try:
                from pyzbar import pyzbar
                res = pyzbar.decode(img)
                items = [r.data.decode("utf-8", errors="replace")
                         for r in res if getattr(r, "data", None)]
                if items:
                    return ImportResult(True, "\n".join(items), f"pyzbar × {len(items)}")
                notes.append("图中未识别到二维码（pyzbar）")
            except Exception as e:  # noqa: BLE001
                notes.append(f"pyzbar 解码失败: {e}")
    return ImportResult(False, "", "；".join(notes))


def read_clipboard_image():
    """读剪贴板里的图像，返回 (ok, PIL Image 或图片路径列表, note)。

    平台差异（如实说明，不假装都能用）：
      · Windows / macOS —— pillow 的 ImageGrab 可取到剪贴板图像；
      · Linux —— X11/Wayland 剪贴板图像取不到，优雅失败并提示改用「图片文件」来源。
    本函数只读剪贴板，绝不写回。
    """
    try:
        from PIL import ImageGrab
    except Exception:
        return False, None, "读取剪贴板图像需要 pillow：pip install pillow（工具不会自动安装）"
    try:
        data = ImageGrab.grabclipboard()
    except Exception as e:  # noqa: BLE001
        return False, None, f"剪贴板图像读取失败（Linux 桌面通常不支持）: {e}"
    if data is None:
        return False, None, "剪贴板里没有图像（可能是纯文本或空）"
    return True, data, "剪贴板图像"


def decode_qr_from_clipboard() -> ImportResult:
    """把剪贴板里的**截图**当二维码解码——截个图就能导入，不必先存文件。

    剪贴板内容是文件路径列表时（macOS 常见行为）直接按图片文件解码；
    是图像对象时在内存里解码，不落临时文件。
    """
    ok, data, note = read_clipboard_image()
    if not ok:
        return ImportResult(False, "", note)
    # macOS：grabclipboard 可能返回文件路径列表
    if isinstance(data, list):
        for p in data:
            if isinstance(p, str) and os.path.isfile(p):
                r = decode_qr_image(p)
                if r.ok:
                    return r
        return ImportResult(False, "", "剪贴板中的文件不是含二维码的图片")
    try:
        from PIL import Image
        if not isinstance(data, Image.Image):
            return ImportResult(False, "", f"剪贴板内容不是图像: {type(data).__name__}")
    except Exception:
        return ImportResult(False, "", "pillow 不可用，无法处理剪贴板图像")
    return decode_qr_pil(data)


# ─────────────────────────────────────────────────────────────────────────────
# 4) 摄像头扫码（可选能力）
# ─────────────────────────────────────────────────────────────────────────────
def scan_qr_camera(index: int = None, timeout: int = None) -> ImportResult:
    """调用摄像头实时扫码，识别到立即返回；超时结束。

    需要 OpenCV。无摄像头/无权限/超时均返回失败说明，不抛错、不死等。
    """
    try:
        import cv2
    except Exception:
        return ImportResult(False, "", "摄像头扫码需要 OpenCV: pip install opencv-python-headless（工具不会自动安装）")
    if index is None:
        try:
            index = int(_settings.get("qr.camera_index", 0))
        except (TypeError, ValueError):
            index = 0
    if timeout is None:
        try:
            timeout = int(_settings.get("qr.camera_timeout", 20))
        except (TypeError, ValueError):
            timeout = 20

    import time
    cap = cv2.VideoCapture(int(index))
    if not cap or not cap.isOpened():
        return ImportResult(False, "", f"无法打开摄像头 #{index}（被占用/无权限/无设备）")
    det = cv2.QRCodeDetector()
    deadline = time.time() + max(1, int(timeout))
    try:
        while time.time() < deadline:
            ok, frame = cap.read()
            if not ok:
                break
            try:
                data, _pts, _ = det.detectAndDecode(frame)
            except Exception:
                data = ""
            if data:
                return ImportResult(True, str(data), f"摄像头 #{index}")
    finally:
        try:
            cap.release()
        except Exception:
            pass
    return ImportResult(False, "", f"{timeout} 秒内未识别到二维码（摄像头 #{index}）")


# ─────────────────────────────────────────────────────────────────────────────
# 统一入口
# ─────────────────────────────────────────────────────────────────────────────
def import_from(source: str, target: str = "") -> ImportResult:
    """按来源标识导入：clipboard / file / qr / camera。

    target: file 与 qr 需要路径；剪贴板与摄像头忽略该参数。
    """
    src = (source or "").strip().lower()
    if src == SRC_CLIPBOARD:
        r = read_clipboard()
        if r.ok:
            return r
        # 纯文本拿不到（或为空）时，再试一次「剪贴板截图里的二维码」
        r2 = decode_qr_from_clipboard()
        if r2.ok:
            return r2
        return ImportResult(False, "", f"{r.note}；已尝试剪贴板截图扫码: {r2.note}")
    if src == SRC_FILE:
        if not target:
            return ImportResult(False, "", "本地文件来源需要提供路径")
        return read_text_file(target)
    if src == SRC_QR:
        if not target:
            return ImportResult(False, "", "图片二维码来源需要提供图片路径")
        return decode_qr_image(target)
    if src == SRC_CAMERA:
        return scan_qr_camera()
    return ImportResult(False, "", f"未知导入来源: {source}（可选: "
                                   + "/".join(k for k, _l, _d in SOURCES) + "）")


# ─────────────────────────────────────────────────────────────────────────────
# 导入内容为 JSON 时：只校验结构，绝不自动执行/自动应用
# ─────────────────────────────────────────────────────────────────────────────
def parse_settings_json(text: str) -> Tuple[bool, Dict[str, object], List[str], str]:
    """把导入文本当作「设置 JSON」解析并校验。

    返回 (是否可载入, 可载入的键值对, 被拒绝项说明列表, 提示)。
    **本函数只做解析与校验，绝不写入配置、绝不执行内容** —— 是否应用由用户确认。
    """
    text = (text or "").strip()
    if not text:
        return False, {}, [], "内容为空"
    try:
        obj = json.loads(text)
    except ValueError as e:
        return False, {}, [], f"不是合法 JSON: {e}"
    if not isinstance(obj, dict):
        return False, {}, [], "JSON 顶层不是对象（应为 {\"参数key\": 值}）"

    from .settings import ALL_KEYS, validate  # 局部导入，保持本模块可独立使用

    accepted: Dict[str, object] = {}
    rejected: List[str] = []
    for k, v in obj.items():
        ok, norm, why = validate(k, v)
        if ok:
            accepted[k] = norm
        else:
            rejected.append(f"{k}: {why}")
    if not accepted:
        return False, {}, rejected, "没有可识别的参数键（已登记键: " + ", ".join(ALL_KEYS) + "）"
    hint = f"可载入 {len(accepted)} 项"
    if rejected:
        hint += f"，忽略 {len(rejected)} 项"
    return True, accepted, rejected, hint


# ─────────────────────────────────────────────────────────────────────────────
# 能力报告（供 sysmap 嵌入与控制台展示）
# ─────────────────────────────────────────────────────────────────────────────
def capabilities_report() -> Tuple[bool, str]:
    """导入层能力报告：四种来源分别是否可用（只读探测，不实际读取）。"""
    clips = clipboard_backends()
    qr = qr_backends()
    lines = [
        "导入来源:",
        f"  剪贴板      : {'可用（' + '/'.join(clips) + '）' if clips else '无命令行工具，仅 tk 兜底'}",
        f"  本地文件    : 可用（上限 {_max_bytes()} 字节）",
        f"  图片二维码  : {'可用（' + '/'.join(qr) + '）' if qr else '缺解码库'}",
        f"  摄像头扫码  : {'可用' if 'cv2' in qr else '需 OpenCV'}",
    ]
    if not qr:
        lines.append("  " + _qr_hint())
    return True, "\n".join(lines)


def importio_report() -> Tuple[bool, str]:
    """导入层总览（能力 + 当前参数），供 sysmap/控制台展示。"""
    ok, cap = capabilities_report()
    lines = [cap, "",
             f"当前参数: qr.backend={_opt('qr.backend')} · "
             f"clipboard.backend={_opt('clipboard.backend')} · "
             f"import.max_bytes={_max_bytes()} · "
             f"qr.camera_index={_opt('qr.camera_index', '0')} · "
             f"qr.camera_timeout={_opt('qr.camera_timeout', '20')}秒",
             "红线: 导入内容只校验不自动执行；是否载入为设置需你确认。"]
    return ok, "\n".join(lines)
