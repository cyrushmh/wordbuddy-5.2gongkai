"""压缩 / 归档格式的只读分析与归档指引任务（platform="any"）。

立项动机是两句大白话：**省用户的储存空间，也省运行内存**。

- **省储存**：找出「还能进一步压缩」的大文件——文本、日志、JSON、CSV、源码这类
  压缩率通常在 60%~90%；反过来，zip / 7z / rar / png / mp4 / pdf 这些**已经压过**
  或**已编码**的格式，再压收益接近 0，报告会明确标出「别白压」，省下白跑的 CPU。
- **省运行内存**：全程流式——扫目录用 `heapq` 只留体积 Top N（内存恒定，不把整棵
  目录树装进 list）；读包内部条目只过 header / 分块读统计，**绝不解压到磁盘、
  绝不整体载入内存**。

依赖「不强求安装」（与 `tasks/lang.py` 同款纪律）：
- 核心格式走标准库：tar / tar.gz / tar.xz / tar.bz2 / zip / gz / xz / bz2 → 零依赖，总可用。
- 7z 需 `py7zr`、rar 需 `rarfile`（另需 unrar/unar/bsdtar 后端）、zstd 需 `zstandard`；
  缺库就在报告里写明「跳过」，**绝不报错、绝不假装支持**。

处置纪律：默认**只分析不压缩、不解压、不删除**。归档命令只以文本形式给出，
由用户自己决定是否执行（与 storage 层「只读报告 + 需 --yes 才动作」一致）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

# 标准出处（与其余任务同款：带 [国际]/[官方] 前缀，进「标准与分类」视图）
TAR = ("[国际] POSIX pax / ustar 归档格式（IEEE Std 1003.1，tar 的标准化格式）")
GZIP = ("[国际] RFC 1952 gzip 文件格式 + RFC 1951 DEFLATE 压缩数据格式")
XZ = ("[国际] XZ / LZMA2 容器格式规范（tukaani xz format）")
ZSTD = ("[国际] RFC 8878 Zstandard 压缩格式与字典格式")
ZIP = ("[国际] ZIP APPNOTE（PKWARE 归档格式规范）")
SEVENZ = ("[国际] 7z 格式与 LZMA2（7-Zip 官方格式文档 / Igor Pavlov LZMA SDK）")
RAR = ("[国际] RAR 归档格式（RARLAB，RAR5）")


TASKS = [
    # ---- 只读：本机压缩格式能力 ----
    Task(
        id="compress_formats",
        platform="any",
        title="压缩格式可读性核对（tar/zip/gz/xz/bz2/7z/rar/zstd）",
        category="maintenance",
        risk="low",
        desc="只读探测本机可读哪些压缩格式：核心格式走标准库永远可用，7z/rar/zstd 缺库时明确标「跳过」，不强求安装。",
        actions=[
            N("compress.compress_format_capabilities",
              "列出本机压缩格式可读性（只读探测，不解压任何文件）"),
        ],
        standards=[TAR, GZIP, XZ, ZSTD, ZIP, SEVENZ, RAR],
        notes=[
            "核心格式（tar/tar.gz/tar.xz/tar.bz2/zip/gz/xz/bz2）用标准库，零依赖总可用。",
            "7z 需 py7zr、rar 需 rarfile 且另需 unrar/unar/bsdtar 后端、zstd 需 zstandard；"
            "缺哪个就明确跳过哪个，绝不假装支持。",
        ],
        caveats=["只读任务：仅探测，不解压、不读取任何文件内容。"],
    ),
    # ---- 只读：压缩空间分析（核心） ----
    Task(
        id="compress_report",
        platform="any",
        title="压缩空间分析（找出还能压出多少空间，只读）",
        category="maintenance",
        risk="low",
        desc="只读扫描目录，按「还值不值得再压」分类统计，对体积最大的可压缩文件实测 LZMA 压缩率并估算可回收空间；"
             "同时流式读取最大的几个压缩包内部条目（不解压、不驻留内存）。",
        actions=[
            N("compress.compress_report",
              "扫描并估算可回收空间 + 流式读包内部条目（只读）"),
        ],
        standards=[TAR, GZIP, XZ, SEVENZ, RAR],
        notes=[
            "分类口径：归档/已压缩（zip、7z、rar…）与图片音视频/PDF（已编码）**再压几乎无收益**，"
            "报告会标「别白压」，只压文本/日志/结构化数据这类真正有收益的。",
            "压缩率只对前 1 MiB 采样实测（LZMA，接近 7z 的 LZMA2）后按比例推算，"
            "属估算而非精确值——目的是排序优先级，不是给出承诺数字。",
            "省内存的三处关键实现：扫目录用 heapq 只留体积 Top N（内存恒定）；"
            "压测只读前 1 MiB 而不是整个文件；读包内部只过 header / 分块读统计。",
            "扫描带文件数上限（2 万）与时间预算（20 秒），达上限会标注「非全量」，避免拖慢机器。",
        ],
        caveats=[
            "只读任务：不压缩、不解压、不删除任何文件。",
            "采样估算有误差（文件前后段内容差异大时尤甚），仅用于判断「哪些值得先压」。",
        ],
    ),
    # ---- 指引：归档命令（manual，绝不自动执行） ----
    Task(
        id="compress_archive_guide",
        platform="any",
        title="归档命令指引（tar / 7z，只给命令不代劳）",
        category="maintenance",
        risk="low",
        desc="给出常见归档场景的命令文本与选型建议：兼容性优先用 tar，压缩率优先用 7z。"
             "本任务只输出指引，绝不自动执行任何压缩动作。",
        actions=[
            M("兼容性优先：tar czf 归档.tar.gz <目录>   "
              "（标准库/系统 tar 即可，跨平台最通用；gz 用 DEFLATE，见 RFC 1952）",
              "tar + gzip 归档（兼容性最好）"),
            M("压缩率优先：7z a -t7z -mx=9 -m0=LZMA2 归档.7z <目录>   "
              "（LZMA2，见 7-Zip 官方格式文档；需装 7z 或 py7zr）",
              "7z + LZMA2 归档（压缩率最高）"),
            M("更快的现代选择：zstd -19 归档.tar.zst（需 zstd，见 RFC 8878）",
              "zstd 归档（速度与压缩率均衡）"),
        ],
        standards=[TAR, GZIP, SEVENZ, XZ, ZSTD],
        notes=[
            "选型：要「谁都能解开」用 tar.gz；要「压到最小」用 7z -mx=9；"
            "要「压得快又不太差」用 zstd（-19 兼顾，压缩/解压都远快于 LZMA）。",
            "已经压过的（zip/7z/rar/mp4/png/pdf/office）别再压一遍：收益接近 0，纯浪费 CPU 与时间。",
            "归档前确认目标目录不再变动；归档后**先校验再删原件**（如 tar -tf 列一遍、7z t 测试）。",
        ],
        caveats=[
            "指引类任务：只打印命令文本，不自动执行——是否归档、归档哪些，由你决定。",
            "压缩大目录会占用 CPU 与 IO；高压缩级别（-mx=9 / -19）耗时会明显变长。",
        ],
    ),
]
