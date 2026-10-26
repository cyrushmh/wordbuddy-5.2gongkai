"""压缩 / 归档格式只读接口层（7z · rar · tar · zip · gz · xz · bz2 · zst …）。

立项动机「帮用户省空间，也省内存」——两件事分开做，别混为一谈：

- **省储存**：找出**还能进一步压缩**的大文件，实测压缩率估算可回收空间；
  已压缩 / 有损媒体（zip、7z、rar、png、mp4、pdf…）再压几乎没收益，明确标出
  「别白压」，避免用户花几小时 CPU 换来 0.1% 的收获。
- **省运行内存**：读压缩包内部条目一律**流式**——tar 只过 header、gz/xz/bz2 分块
  读统计、扫描目录用 `heapq` 只留 Top N 而不是先把整棵目录树装进 list。
  全程不解压到磁盘、不整体载入内存。

依赖策略「不强求安装」（与 `tasks/lang.py` 同一套纪律）：
- 核心格式走**标准库**：tar / tar.gz / tar.xz / tar.bz2 / zip / gz / xz / bz2 → 零依赖，总可用。
- 进阶格式按需 `try-import` 降级：7z 需 `py7zr`；rar 需 `rarfile`（另需 unrar/unar/bsdtar
  后端）；zstd 需 `zstandard`。没装就在报告里写明「未安装，跳过」——**绝不报错、
  绝不假装支持**，与 storage 层「无该工具自动降级为跳过」一致。

设计原则：默认**只分析，不压缩、不解压、不删除**（与 `storage` 只读报告同款）。
真要归档，报告只给命令文本，由用户自己决定执行。
"""

from __future__ import annotations

import bz2
import gzip
import heapq
import lzma
import os
import shutil
import tarfile
import time
import zlib
import zipfile
from typing import Dict, List, Optional, Tuple

from ..i18n import _

# ---------------------------------------------------------------------------
# 扩展名分类：决定「这个文件还值不值得再压」
# ---------------------------------------------------------------------------

# 已压缩的归档/容器：再压基本无收益
_ARCHIVE_SUFFIX = {
    ".7z", ".zip", ".rar", ".gz", ".xz", ".bz2", ".zst", ".lz4", ".lzma", ".lzo",
    ".tgz", ".tbz", ".tbz2", ".txz", ".tzst", ".jar", ".whl", ".apk", ".deb",
    ".rpm", ".arj", ".lzh", ".cab", ".iso", ".dmg", ".pkg", ".xpi", ".crx",
    ".tar", ".zipx", ".z", ".zz", ".br",  # .tar 裸归档（未压，但下面按 stream 处理）
}

# 有损/已编码媒体：内部已经是压缩编码，再压无收益
_MEDIA_SUFFIX = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif", ".avif", ".bmp",
    ".tiff", ".mp3", ".flac", ".ogg", ".opus", ".aac", ".m4a", ".wma", ".aiff",
    ".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".mpg",
    ".mpeg", ".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".epub",
}

# 高可压的文本/结构化数据：压缩收益通常 60%~90%
_TEXT_SUFFIX = {
    ".txt", ".log", ".json", ".xml", ".csv", ".tsv", ".md", ".html", ".htm",
    ".css", ".js", ".mjs", ".ts", ".py", ".java", ".c", ".h", ".cpp", ".hpp",
    ".go", ".rb", ".rs", ".sql", ".yml", ".yaml", ".ini", ".conf", ".cfg",
    ".ndjson", ".svg", ".sh", ".bash", ".zsh", ".pl", ".lua", ".php", ".swift",
    ".kt", ".scala", ".toml", ".properties", ".tex", ".rst", ".org", ".dat",
    ".bak", ".old", ".out", ".err", ".trace", ".dump", ".pcap", ".cap",
}

# 单文件压缩流（用标准库分块流式统计内部大小）
_STREAM_OPENERS = {
    ".gz": gzip.open,
    ".xz": lzma.open,
    ".lzma": lzma.open,
    ".bz2": bz2.open,
}

_DEFAULT_KEEP = 64          # 只保留体积最大的 N 个文件（heapq，内存恒定）
_DEFAULT_MAX_FILES = 20000  # 遍历文件数上限（防拖慢）
_DEFAULT_BUDGET = 20.0      # 扫描时间预算（秒）
_SAMPLE_BYTES = 1 << 20     # 压缩率采样：只读前 1 MiB
_CHUNK = 1 << 20            # 流式统计块大小 1 MiB


def _fmt(n: float) -> str:
    """字节 → 人类可读（B/KB/MB/GB/TB）。"""
    units = (_("B"), _("KB"), _("MB"), _("GB"), _("TB"))
    v = float(n)
    for u in units:
        if v < 1024.0 or u == units[-1]:
            return f"{v:.1f} {u}" if v < 100 else f"{v:.0f} {u}"
        v /= 1024.0
    return f"{v:.1f} {units[-1]}"


def _kind_of(path: str) -> str:
    """按扩展名判定：compressed（别白压）/ media / text（值得压）/ other。"""
    low = path.lower()
    for suf in (".tar.gz", ".tar.xz", ".tar.bz2", ".tar.zst"):
        if low.endswith(suf):
            return "compressed"
    dot = low.rfind(".")
    suf = low[dot:] if dot >= 0 else ""
    if suf in _ARCHIVE_SUFFIX:
        return "compressed"
    if suf in _MEDIA_SUFFIX:
        return "media"
    if suf in _TEXT_SUFFIX:
        return "text"
    return "other"


def _iter_files(root: str):
    """递归产出常规文件路径（生成器：不把整棵目录树装进内存）。"""
    try:
        it = os.scandir(root)
    except (PermissionError, OSError):
        return
    with it:
        for entry in it:
            try:
                if entry.is_dir(follow_symlinks=False):
                    yield from _iter_files(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    yield entry.path
            except (PermissionError, OSError):
                continue


def _sample_ratio(path: str, sample_bytes: int = _SAMPLE_BYTES) -> Optional[float]:
    """采样前 N 字节实测压缩率 → (压缩后/原始)。越小越省。

    只读前 1 MiB 就够估算，且**不把整个大文件读进内存**——省内存的关键之一。
    用 lzma（接近 7z 的 LZMA2），失败回退 zlib。
    """
    try:
        with open(path, "rb") as f:
            data = f.read(sample_bytes)
    except OSError:
        return None
    if not data:
        return None
    for fn in (lambda d: lzma.compress(d), lambda d: zlib.compress(d, 6)):
        try:
            return len(fn(data)) / len(data)
        except Exception:  # noqa: BLE001 - 单次采样失败不影响整体报告
            continue
    return None


def _inspect_archive(path: str) -> Tuple[str, int, int, str]:
    """流式读一个压缩包 → (格式, 条目数, 内部未压缩总字节, 说明)。

    全程**不解压到磁盘、不整体载入内存**：
    - tar：迭代 header（只过元数据，不读文件内容）
    - zip：读 central directory（只元数据）
    - gz/xz/bz2：分块读统计解压后字节数，读完即丢
    - 7z/rar/zst：按需 import，缺库则明确说明「跳过」
    """
    low = path.lower()

    # --- tar 系（含 tar.gz / tar.xz / tar.bz2）---
    if low.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz",
                     ".tar.bz2", ".tbz", ".tbz2")):
        try:
            n = 0
            total = 0
            with tarfile.open(path, "r:*") as tf:
                for m in tf:  # 流式迭代，只解析 header
                    n += 1
                    if m.isfile():
                        total += m.size
            return "tar", n, total, ""
        except Exception as e:  # noqa: BLE001
            return "tar", 0, 0, _("读取失败: %s") % e

    # --- zip ---
    if low.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as zf:
                infos = zf.infolist()
            return "zip", len(infos), sum(i.file_size for i in infos), ""
        except Exception as e:  # noqa: BLE001
            return "zip", 0, 0, _("读取失败: %s") % e

    # --- 7z（需 py7zr）---
    if low.endswith(".7z"):
        try:
            import py7zr  # type: ignore
        except ImportError:
            return "7z", 0, 0, _("未安装 py7zr，跳过 7z 内部分析")
        try:
            with py7zr.SevenZipFile(path) as z:
                lst = z.list()
            total = sum(getattr(i, "uncompressed", 0) or 0 for i in lst)
            return "7z", len(lst), total, ""
        except Exception as e:  # noqa: BLE001
            return "7z", 0, 0, _("读取失败: %s") % e

    # --- rar（需 rarfile + unrar/unar/bsdtar 后端）---
    if low.endswith(".rar"):
        try:
            import rarfile  # type: ignore
        except ImportError:
            return "rar", 0, 0, _("未安装 rarfile，跳过 rar 内部分析")
        try:
            with rarfile.RarFile(path) as rf:
                infos = rf.infolist()
            return "rar", len(infos), sum(i.file_size for i in infos), ""
        except Exception as e:  # noqa: BLE001
            return "rar", 0, 0, _("读取失败（rar 需 unrar/unar/bsdtar 后端）: %s") % e

    # --- zstd（需 zstandard）---
    if low.endswith((".zst", ".tzst")):
        return "zst", 0, 0, _("未安装 zstandard，跳过 zstd 内部分析")

    # --- 单文件压缩流：分块读统计内部大小（最典型的「流式省内存」）---
    dot = low.rfind(".")
    opener = _STREAM_OPENERS.get(low[dot:] if dot >= 0 else "")
    if opener:
        total = 0
        try:
            with opener(path, "rb") as f:
                while True:
                    chunk = f.read(_CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)  # 统计完就丢，不驻留内存
            return "stream", 1, total, ""
        except Exception as e:  # noqa: BLE001
            return "stream", 0, 0, _("读取失败: %s") % e

    return "other", 0, 0, ""


def compress_format_capabilities() -> tuple:
    """本机可读压缩格式能力（只读探测，不解压任何文件）。

    返回 (True, 多行报告)。核心格式永远可用（标准库），进阶格式缺库就写明。
    """
    rows: List[Tuple[str, bool, str]] = [
        (_("tar / tar.gz / tar.xz / tar.bz2"), True, _("标准库 tarfile（流式过 header）")),
        (_("zip"), True, _("标准库 zipfile（只读 central directory）")),
        (_("gz / xz / bz2（单文件流）"), True, _("标准库 gzip/lzma/bz2 分块流式")),
    ]

    try:
        import py7zr  # noqa: F401
        rows.append((_("7z"), True, _("py7zr")))
    except ImportError:
        cmd = next((c for c in ("7z", "7za", "7zr") if shutil.which(c)), "")
        rows.append((_("7z"), False,
                     (_("命令行 %s（仅可读命令输出，内部条目分析需 py7zr）") % cmd)
                     if cmd else _("未安装 py7zr / 7z 命令行")))

    try:
        import rarfile  # noqa: F401
        backend = next((c for c in ("unrar", "unar", "bsdtar") if shutil.which(c)), "")
        rows.append((_("rar"), bool(backend),
                     (_("rarfile + %s 后端") % backend) if backend
                     else _("rarfile 已装，但缺 unrar/unar/bsdtar 后端")))
    except ImportError:
        rows.append((_("rar"), False, _("未安装 rarfile")))

    try:
        import zstandard  # noqa: F401
        rows.append((_("zst（zstd）"), True, _("zstandard")))
    except ImportError:
        rows.append((_("zst（zstd）"), bool(shutil.which("zstd")),
                     _("命令行 zstd（内部条目需 zstandard）") if shutil.which("zstd")
                     else _("未安装 zstandard / zstd 命令行")))

    lines = [_("本机压缩格式可读性（只读探测，不解压）：")]
    for name, ok, src in rows:
        mark = _("可用") if ok else _("跳过")
        lines.append(f"   · {name}  [{mark}]  {src}")
    lines.append(_("   · 说明：核心格式走标准库，永远可用；7z/rar/zstd 缺库时明确跳过，不强求安装。"))
    return True, "\n".join(lines)


def compress_report(scan_dir: Optional[str] = None,
                    max_files: int = _DEFAULT_MAX_FILES,
                    top_n: int = 8,
                    time_budget: float = _DEFAULT_BUDGET) -> tuple:
    """只读扫描目录，估算「还能压出多少空间」+ 流式读大压缩包内部条目。

    scan_dir 默认 $HOME。全程只读：**不压缩、不解压、不删除**。
    返回 (ok, 多行报告)。
    """
    root = scan_dir or os.path.expanduser("~")
    if not os.path.isdir(root):
        return False, _("目录不存在: %s") % root

    deadline = time.time() + time_budget
    keep = max(top_n, _DEFAULT_KEEP)
    heap: List[Tuple[int, str]] = []           # 只留体积最大的 keep 个（内存恒定）
    stats: Dict[str, List[int]] = {           # kind -> [文件数, 总字节]
        "compressed": [0, 0], "media": [0, 0], "text": [0, 0], "other": [0, 0],
    }
    scanned = 0
    total_bytes = 0
    truncated = False

    for path in _iter_files(root):
        scanned += 1
        if scanned > max_files or time.time() > deadline:
            truncated = True
            break
        try:
            size = os.stat(path).st_size
        except OSError:
            continue
        total_bytes += size
        st = stats[_kind_of(path)]
        st[0] += 1
        st[1] += size
        if len(heap) < keep:
            heapq.heappush(heap, (size, path))
        elif size > heap[0][0]:
            heapq.heapreplace(heap, (size, path))

    if not scanned:
        return False, _("未扫描到任何文件（目录为空或权限不足）: %s") % root

    top = sorted(heap, reverse=True)  # 大到小
    lines = [
        _("压缩空间分析报告（扫描目录 = %s）") % root,
        _("   · 已扫文件 %d 个，合计 %s%s") % (
            scanned, _fmt(total_bytes),
            _("（达上限/超时，非全量）") if truncated else ""),
    ]

    # ---- 分类占比 ----
    lines.append(_("   · 按「还值不值得再压」分类："))
    for kind, label in (("compressed", _("归档/已压缩（再压几乎无收益）")),
                        ("media", _("图片音视频/PDF（已编码，别白压）")),
                        ("text", _("文本/日志/结构化数据（压缩收益最高）")),
                        ("other", _("其他（视内容而定）"))):
        cnt, byts = stats[kind]
        if cnt:
            pct = (byts / total_bytes * 100) if total_bytes else 0.0
            lines.append(f"       - {label}: {cnt} 个 / {_fmt(byts)}（{pct:.1f}%）")

    # ---- 实测压缩率，估算可回收 ----
    lines.append("")
    lines.append(_("   · 体积最大的可压缩文件（采样前 1 MiB 实测 LZMA 压缩率）："))
    shown = 0
    savable_total = 0
    for size, path in top:
        if shown >= top_n:
            break
        kind = _kind_of(path)
        if kind in ("compressed", "media"):
            continue  # 已压缩/已编码：跳过压测，避免误导
        ratio = _sample_ratio(path)
        if ratio is None:
            continue
        savable = int(size * (1.0 - ratio))
        if savable <= 0:
            continue
        savable_total += savable
        shown += 1
        # 注意措辞：ratio 是「压后占原始的比例」，越小越省；
        # 直接写「压缩率」会被读成「压了多少」，故写明「压后占比 + 可省百分比」。
        lines.append(f"       - {_fmt(size)} → 约 {_fmt(savable)} 可省"
                     f"（压后占比 {ratio*100:.1f}%，可省 {(1.0-ratio)*100:.0f}%）"
                     f"  {os.path.basename(path)}")
    if shown == 0:
        lines.append(_("       - 未发现值得压缩的大文件（多数已是已压缩/已编码格式）"))
    else:
        lines.append(_("       · 仅这 %d 个文件归档，预计可回收约 %s") % (shown, _fmt(savable_total)))

    # ---- 流式读最大的几个压缩包内部条目（省内存的最佳例证）----
    lines.append("")
    lines.append(_("   · 大压缩包内部条目（流式读取，不解压、不驻留内存）："))
    packs = [(s, p) for s, p in top if _kind_of(p) == "compressed"][:3]
    if not packs:
        lines.append(_("       - 未发现归档/压缩包"))
    for size, path in packs:
        kind, entries, inner, note = _inspect_archive(path)
        if note:
            lines.append(f"       - {os.path.basename(path)}（{_fmt(size)}）: {note}")
            continue
        rate = (1 - size / inner) if inner else 0.0
        # stored（未压缩）的 zip / 已压过的内容，rate 接近 0 甚至为负，别显示成「省了 -0%」
        tail = (_("省了 %d%%") % round(rate * 100)) if rate > 0.02 else _("几乎未压缩（stored / 已压过）")
        lines.append(f"       - {os.path.basename(path)}: {entries} 个条目，"
                     f"内部 {_fmt(inner)} → 已压到 {_fmt(size)}（{tail}）")

    # ---- 建议（只给命令文本，不自动执行）----
    lines.append("")
    lines.append(_("   · 归档建议（只会打印命令，不自动执行）："))
    lines.append(_("       - 纯文本/日志：tar czf 归档.tar.gz <目录>   （标准库可用，兼容性最好）"))
    lines.append(_("       - 追求高压缩率：7z a -t7z -mx=9 归档.7z <目录>   （需装 7z 或 py7zr）"))
    lines.append(_("       - 已压过的（zip/7z/rar/mp4/png/pdf）别再压：收益接近 0，白费 CPU。"))
    lines.append(_("   · 本报告只读：未压缩、未解压、未删除任何文件。"))
    return True, "\n".join(lines)
