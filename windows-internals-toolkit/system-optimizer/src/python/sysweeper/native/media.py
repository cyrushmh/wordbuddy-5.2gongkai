"""图像 / 媒体编解码与色彩能力只读诊断（吸收 storytold/photocraft 等纯 Rust
clean-room 复刻 Adobe 全家桶的「图像管线」视角）。

「你中有我、系统的看待一切」：图像优化（清理 / 性能优化）的前提是本机具备对应编解码
与色彩管理能力。本模块只读核验：

- 编解码工具链 : ImageMagick(identify/convert/magick)/exiftool/ffmpeg、
  libheif(heif-convert/enc)、libavif(avifdec/enc)、libwebp(cwebp/dwebp)、
  libjxl(cjxl/djxl) 等
- 格式支持矩阵 : JPEG/PNG/WebP/HEIC/AVIF/JPEG XL/JPEG 2000/TIFF/BMP/GIF 的
  读取 / 写入能力（依据已装工具推断，不实际解码文件）
- 色彩管理     : ICC 配置目录(/usr/share/color/icc)、colord(colormgr)
- Rust 创意套件 : storytold 系纯 Rust 应用（photocraft/artcraft/lightcraft/
  filmcraft/vectorcraft/pdfcraft/effectcraft/cadcraft/soundcraft/deckcraft/
  gridcraft）是否就位——它们决定「本机能否跑起 Adobe 级创作 / 优化工作流」

红线：不解码 / 不转码 / 不写任何图像文件、不连网、不改配置；仅 shutil.which + 目录存在性。
"""

from __future__ import annotations

import os
import shutil


# 格式 -> (读取依赖工具, 写入依赖工具)；任一存在即判支持
_FORMATS = (
    ("JPEG",        ("convert", "magick", "jpegtran"), ("convert", "magick", "jpegtran")),
    ("PNG",         ("convert", "magick", "pngcheck"), ("convert", "magick")),
    ("WebP",        ("cwebp", "dwebp", "convert", "magick"), ("cwebp", "convert", "magick")),
    ("HEIC/HEIF",   ("heif-convert",), ("heif-enc",)),
    ("AVIF",        ("avifdec",), ("avifenc",)),
    ("JPEG XL",     ("djxl",), ("cjxl",)),
    ("JPEG 2000",   ("convert", "magick"), ("convert", "magick")),
    ("TIFF",        ("convert", "magick"), ("convert", "magick")),
    ("BMP",         ("convert", "magick"), ("convert", "magick")),
    ("GIF",         ("convert", "magick"), ("convert", "magick")),
)

# storytold 纯 Rust clean-room 复刻 Adobe 全家桶
_RUST_CREATIVE = (
    ("photocraft", "Adobe Photoshop (纯 Rust)"),
    ("artcraft", "ArtCraft 创作引擎"),
    ("lightcraft", "Adobe Lightroom (纯 Rust)"),
    ("filmcraft", "Adobe Premiere Pro (纯 Rust)"),
    ("vectorcraft", "Adobe Illustrator (纯 Rust)"),
    ("pdfcraft", "Adobe Acrobat (纯 Rust)"),
    ("effectcraft", "特效合成"),
    ("cadcraft", "AutoCAD (纯 Rust)"),
    ("soundcraft", "Avid Pro Tools (纯 Rust)"),
    ("deckcraft", "Microsoft PowerPoint (纯 Rust)"),
    ("gridcraft", "Microsoft Excel (纯 Rust)"),
)


def image_capability_report() -> tuple:
    """图像 / 媒体编解码与色彩能力只读诊断。

    返回 (ok, msg)：ok 恒为 True（任意主机都可诊断）；报告列出已支持 / 缺失的编解码与
    色彩能力，以及 Rust 创意套件就位情况。缺失项标注为建议补充，供「图像优化」任务参考。
    """
    lines = ["图像 / 媒体编解码与色彩能力（只读诊断）："]

    # 1) 工具链
    tools = {
        "ImageMagick": bool(shutil.which("convert") or shutil.which("magick")),
        "identify": bool(shutil.which("identify")),
        "exiftool": bool(shutil.which("exiftool")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "libheif(HEIC)": bool(shutil.which("heif-convert") or shutil.which("heif-enc")),
        "libavif(AVIF)": bool(shutil.which("avifdec") or shutil.which("avifenc")),
        "libwebp(WebP)": bool(shutil.which("cwebp") or shutil.which("dwebp")),
        "libjxl(JXL)": bool(shutil.which("cjxl") or shutil.which("djxl")),
    }
    lines.append("  编解码工具链：")
    for name, ok in tools.items():
        lines.append(f"    {name:<18} : {'✓ 已安装' if ok else '✗ 未安装（缺失）'}")

    # 2) 格式支持矩阵
    lines.append("  格式支持矩阵（依据已装工具推断，未实际解码）：")
    missing_read = []
    for fmt, r_deps, w_deps in _FORMATS:
        r_ok = any(shutil.which(d) for d in r_deps)
        w_ok = any(shutil.which(d) for d in w_deps)
        rd = "读✓" if r_ok else "读✗"
        wr = "写✓" if w_ok else "写✗"
        if not r_ok:
            missing_read.append(fmt)
        lines.append(f"    {fmt:<12} : {rd}  {wr}")

    # 3) 色彩管理
    icc_dir = "/usr/share/color/icc"
    icc_count = 0
    if os.path.isdir(icc_dir):
        try:
            icc_count = sum(1 for _ in os.listdir(icc_dir))
        except OSError:
            icc_count = 0
    colord = bool(shutil.which("colormgr"))
    lines.append("  色彩管理：")
    lines.append(f"    ICC 配置目录        : {'✓ 存在' if icc_count else '✗ 不存在'} "
                 f"（/usr/share/color/icc，共 {icc_count} 项）")
    lines.append(f"    colord(colormgr)    : {'✓ 已安装' if colord else '✗ 未安装'}")

    # 4) Rust 创意套件
    lines.append("  Rust 创意套件（storytold 纯 Rust clean-room 复刻 Adobe）：")
    present = []
    for bin_name, desc in _RUST_CREATIVE:
        if shutil.which(bin_name):
            present.append((bin_name, desc))
            lines.append(f"    {bin_name:<14} : ✓ 已就位（{desc}）")
    if not present:
        lines.append("    （均未检测到二进制——可为图像 / 创作优化工作流补充，非必需）")

    # 汇总提示
    if missing_read:
        lines.append(f"  建议补充（缺失读取能力）: {', '.join(missing_read)}")
    if not (tools["ImageMagick"] or tools["ffmpeg"]):
        lines.append("  提示：未装 ImageMagick / ffmpeg，批量图像优化（缩略图 / 转码 / EXIF 清理）"
                     "缺乏通用引擎，建议补装其一。")
    return True, "\n".join(lines)
