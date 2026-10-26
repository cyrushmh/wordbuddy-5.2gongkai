"""图像 / 媒体编解码与色彩能力任务（吸收 storytold/photocraft 等纯 Rust 图像创作
应用的「图像管线」视角）。

只读核验本机编解码 / 色彩能力，作为图像优化（缩略图 / 转码 / EXIF 清理）的前提核对。
不解码、不转码、不写任何图像文件。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="media_image_capability",
        platform="any",
        title="图像/媒体编解码与色彩能力诊断",
        category="maintenance",
        risk="low",
        desc="只读核验本机图像编解码工具链、格式支持矩阵、ICC 色彩管理与 Rust 创意套件"
             "就位情况，作为图像优化（缩略图/转码/EXIF 清理）的前提核对。",
        standards=["storytold/photocraft 等纯 Rust clean-room 复刻 Adobe 全家桶："
                   "图像优化以本机编解码/色彩能力为前提——JPEG/PNG/WebP/HEIC/AVIF "
                   "等格式的读取与写入依赖对应工具链（ImageMagick/libheif/libavif/"
                   "libwebp/libjxl）与 ICC 色彩管理"],
        actions=[
            N("media.image_capability_report", "只读核验编解码工具链/格式矩阵/ICC/创意套件"),
        ],
        notes=["缺失读取能力的格式（如 HEIC/AVIF/JXL 未装对应工具）会导致图像优化链路"
               "无法处理这些文件，应优先补装。",
               "ImageMagick 或 ffmpeg 是批量图像优化的通用引擎；两者皆无时优化任务应降级为指引。"],
        caveats=["仅读工具存在性与 ICC 目录；不实际解码/转码任何文件，不改配置、不连网。"],
    ),
]
