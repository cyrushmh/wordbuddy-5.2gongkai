"""发行版识别与发行注记读取（只读）。

把「发行版文档 / 发行注记」从「识别」推进到「可读」：
- 识别：复用 linux.detect_distro（LSB /etc/os-release + lsb_release）。
- 发行注记：读本机已安装的发行注记/变更日志，而非联网拉取。
  权威落点（只读、普遍存在于主流发行版）：
    - /etc/os-release、/usr/lib/os-release        （LSB 标准身份文件）
    - /usr/share/doc/<pkg>/changelog.Debian.gz     （Debian/Ubuntu 包变更日志）
    - /usr/share/doc/<pkg>/NEWS.Debian.gz          （Debian/Ubuntu 重要变更通告）
    - /usr/share/doc/<pkg>/changelog.gz            （RPM 系/上游 changelog）
    - /usr/share/doc/*/README.* / FIXME / TODO      （上游附带的发布说明碎件）
    - /var/log/apt/history.log、dnf.log、pacman 日志（包管理操作史，只读尾行）

参照（发行注记/文档体系）：
- systemd os-release(5) —— 标准化身份字段（ID/VERSION_ID/PRETTY_NAME/VERSION_CODENAME）
- Debian Policy 4.4「Changes to the upstream changelog / NEWS」—— changelog 与 NEWS 规范
- FHS 3.0 §4.11 /usr/share/doc —— 文档放置位置
- LSB Core —— /etc/os-release 字段语义

红线：只读。不 apt-get changelog（那会联网）、不改源、不写文件。
"""

from __future__ import annotations

import glob
import gzip
import os
import shutil
from typing import Dict, List, Tuple

from . import common
from . import linux


def detect() -> Dict[str, str]:
    """识别发行版（复用 linux.detect_distro；只读）。"""
    return linux.detect_distro()


def _read_text_maybe_gz(path: str, limit: int = 4000) -> str:
    """读文本或 .gz；返回前 limit 字符。读不到返回 ''。"""
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
                return f.read(limit)
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except (OSError, EOFError):
        return ""


def release_notes(pkg: str = "", limit: int = 6000) -> Tuple[bool, str]:
    """读本机发行注记/变更日志（只读）。

    - pkg 为空：汇报本机发行版身份 + 能找到的注记来源清单（不dump全文）。
    - pkg 非空：尝试读该包的 changelog/NEWS（本地已装的，不联网）。
    返回 (ok, 文本)。
    """
    rel = detect()
    if not rel.get("id"):
        return False, "未能识别发行版（无 /etc/os-release 且 lsb_release 不可用）"

    lines = [f"发行版：{rel.get('pretty') or rel.get('name') or '未知'}"
             f"  (id={rel.get('id')}, ver={rel.get('version_id')}, "
             f"codename={rel.get('version_codename', '?')})"]
    lines.append(f"   · os-release: ID={rel.get('id')} VERSION_ID={rel.get('version_id')}"
                 f" BUILD_ID={rel.get('build_id', '?')}")

    if pkg:
        # 找该包本地 changelog / NEWS
        hits: List[str] = []
        for pat in (f"/usr/share/doc/{pkg}/changelog.Debian.gz",
                    f"/usr/share/doc/{pkg}/changelog.Debian",
                    f"/usr/share/doc/{pkg}/NEWS.Debian.gz",
                    f"/usr/share/doc/{pkg}/NEWS.Debian",
                    f"/usr/share/doc/{pkg}/changelog.gz",
                    f"/usr/share/doc/{pkg}/changelog"):
            if os.path.exists(pat):
                hits.append(pat)
        if not hits:
            return False, (f"本机未安装 {pkg} 的本地注记（/usr/share/doc/{pkg} 无 "
                           f"changelog/NEWS）。提示：apt-get changelog 会联网，本工具只读本地。")
        blocks = [f"{pkg} 本地注记（只读，前 {limit} 字符）："]
        for h in hits[:3]:
            blocks.append(f"── {h}")
            blocks.append(_read_text_maybe_gz(h, limit))
        return True, "\n".join(blocks)

    # 无 pkg：列出本机可用的注记来源
    doc_root = "/usr/share/doc"
    if os.path.isdir(doc_root):
        news_files = glob.glob(f"{doc_root}/*/NEWS.Debian*")[:8]
        changelog_files = glob.glob(f"{doc_root}/*/changelog.Debian*")[:8]
        lines.append(f"   · NEWS.Debian（重要变更通告）样本：{len(news_files)} 个在 {doc_root}/*/")
        for nf in news_files:
            lines.append(f"       - {os.path.basename(os.path.dirname(nf))}")
        lines.append(f"   · changelog.Debian（包变更日志）样本：{len(changelog_files)} 个在 {doc_root}/*/")
    # 包管理操作史（只读尾行）
    for log, pm in (("/var/log/apt/history.log", "apt"),
                    ("/var/log/dnf.log", "dnf"),
                    ("/var/log/pacman.log", "pacman")):
        if os.path.exists(log):
            lines.append(f"   · 包管理日志({pm})：{log} 存在（可读尾行看近期变更）")
    lines.append("   · 读某包注记用 `distro notes --pkg <包名>`（只读本地，不联网）")
    return True, "\n".join(lines)


def distro_report() -> Tuple[bool, str]:
    """发行版 + 注记来源总览（只读）。"""
    return release_notes(pkg="", limit=6000)


def capabilities_report() -> Tuple[bool, str]:
    """能力自检（只读）：发行版识别 + 注记可读路径存在性。"""
    rel = detect()
    lines = ["发行版与发行注记能力自检（只读）："]
    lines.append(f"   · 识别：{'可用' if rel.get('id') else '不可用'}"
                 f"（linux.detect_distro → {rel.get('pretty') or '?'}）")
    doc_root = "/usr/share/doc"
    lines.append(f"   · 注记目录 {doc_root}：{'存在' if os.path.isdir(doc_root) else '不存在'}")
    lines.append(f"   · NEWS.Debian 样本：{len(glob.glob(doc_root + '/*/NEWS.Debian*')) if os.path.isdir(doc_root) else 0} 个")
    lines.append(f"   · changelog.Debian 样本：{len(glob.glob(doc_root + '/*/changelog.Debian*')) if os.path.isdir(doc_root) else 0} 个")
    lines.append("红线：只读本地 /usr/share/doc 与 /etc/os-release；不 apt-get changelog（联网）、不改源。")
    return True, "\n".join(lines)
