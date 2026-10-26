"""发行版识别与发行注记读取任务（platform="any"，v0.6.13「发行版文档/发行注记」）。

立项：linux.detect_distro 只能「识别」发行版，但维护/排障常要看「这版到底改了什么」——
也就是发行注记与包变更日志。本任务把注记从「识别」推进到「可读」，且只读本地
已安装的 /usr/share/doc 内容，绝不 apt-get changelog（那会联网）。

参照（发行注记/文档体系）：
- systemd os-release(5)        —— 标准化身份字段（ID/VERSION_ID/PRETTY_NAME/VERSION_CODENAME）
- Debian Policy 4.4            —— changelog 与 NEWS 文件规范
- FHS 3.0 §4.11 /usr/share/doc —— 文档放置位置
- LSB Core                     —— /etc/os-release 字段语义
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

OSREL = ("[官方] systemd os-release(5) 标准化身份文件（/etc/os-release、/usr/lib/os-release）")
POLICY = ("[官方] Debian Policy Manual §4.4（changelog.Debian / NEWS.Debian 规范）")
FHS = ("[官方] Filesystem Hierarchy Standard 3.0 §4.11（/usr/share/doc 文档位置）")
LSB = ("[官方] Linux Standard Base Core（/etc/os-release 字段语义）")


TASKS = [
    Task(
        id="distro_notes",
        platform="any",
        title="发行版与发行注记（识别 + 读本地 NEWS/changelog，只读）",
        category="maintenance",
        risk="low",
        desc="识别本机发行版（LSB /etc/os-release），并读本机已安装的发行注记与包变更"
             "日志（NEWS.Debian、changelog.Debian.gz 等），把「这版改了什么」摆出来。",
        actions=[
            N("distro.capabilities_report", "能力自检：识别 + 本地注记路径存在性"),
            N("distro.distro_report", "输出发行版身份 + 本机可用注记来源清单"),
            M("读某包近期变更：distro notes --pkg <包名>（只读本地 /usr/share/doc/<pkg>）",
              "按包读注记（只读，由你决定）"),
        ],
        standards=[OSREL, POLICY, FHS, LSB],
        notes=[
            "识别复用 linux.detect_distro（/etc/os-release 优先，lsb_release 兜底）。",
            "注记读取只读本地 /usr/share/doc/* 下的 NEWS.Debian* / changelog.Debian* / "
            "changelog*（含 .gz，自动解压前若干字符）。",
            "包管理操作史（/var/log/apt/history.log、dnf.log、pacman.log）仅列存在性，"
            "不读全量、不联网。",
            "VERSION_CODENAME 等字段也一并读出，方便对照发行说明。",
        ],
        caveats=[
            "只读任务：不 apt-get changelog（联网）、不改源、不写文件。",
            "本机没装某包的本地注记时，会明确说「未安装该包本地注记」，并提示 "
            "apt-get changelog 会联网——本工具不替你联网。",
        ],
    ),
]
