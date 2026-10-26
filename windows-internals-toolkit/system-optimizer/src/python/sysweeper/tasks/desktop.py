"""桌面环境（GNOME / KDE / XFCE）的清理与优化任务（跨 Linux 桌面，platform="linux"）。

按用户要求「桌面（GNOME、KDE、x fce 等）文档也要跟踪」：每一项的标准依据一律指向
桌面环境官方文档 / freedesktop.org 规范（见 data/desktop_docs.json）：

- GNOME   : dconf/gsettings 文档、GNOME HIG（developer.gnome.org）
- KDE     : KConfig 文档、KDE HIG（develop.kde.org）
- XFCE    : xfconf 文档（docs.xfce.org）
- 通用    : freedesktop.org XDG Base Directory / 图标主题 / 桌面项 / 缩略图规范

原生读取失败（无图形环境 / 未装 gsettings/kwriteconfig5/xfconf-query）时自动降级为
「指引」，不强求安装工具。删除类动作默认需 --apply 才落地。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    Task(
        id="desktop_gnome_cache",
        platform="linux",
        title="清理 GNOME 私有缓存",
        category="cleanup",
        risk="low",
        desc="清理 GNOME 软件中心 / gdm / dconf 等私有缓存（~/.cache 下），回收空间。",
        actions=[
            S('rm -rf "$HOME/.cache/gnome-software" "$HOME/.cache/gdm" '
              '"$HOME/.cache/dconf" 2>/dev/null',
              "清理 GNOME 私有缓存目录", rev=True),
        ],
        standards=[
            "[国际] GNOME dconf 文档（developer.gnome.org，键存储后端，dconf/gsettings 接口）",
        ],
        notes=["参考 GNOME dconf 文档：缓存位于 ~/.cache，删除不影响设置（设置存于 ~/.config/dconf/user）。",
               "下次启动对应组件会重建缓存。"],
        caveats=["仅删 ~/.cache 下内容；切勿删除 ~/.config（含全部 GNOME 设置）。"],
    ),
    Task(
        id="desktop_kde_cache",
        platform="linux",
        title="清理 KDE Plasma 私有缓存",
        category="cleanup",
        risk="low",
        desc="清理 KDE plasmashell / krunner / ksycoca 等私有缓存（~/.cache 下）。",
        actions=[
            S('rm -rf "$HOME/.cache/plasmashell" "$HOME/.cache/krunner" '
              '"$HOME/.cache/ksycoca5" 2>/dev/null',
              "清理 KDE 私有缓存目录", rev=True),
        ],
        standards=[
            "[国际] KDE KConfig 文档（develop.kde.org，配置后端，kwriteconfig5 接口）",
        ],
        notes=["参考 KDE KConfig 文档：缓存位于 ~/.cache；设置存于 ~/.config/*.rc（勿删）。",
               "清理后可 `kbuildsycoca5` 重建服务/菜单缓存。"],
        caveats=["仅删 ~/.cache 下内容；删除 ~/.config 的 .rc 会丢失 KDE 应用设置。"],
    ),
    Task(
        id="desktop_xfce_cache",
        platform="linux",
        title="清理 XFCE 私有缓存",
        category="cleanup",
        risk="low",
        desc="清理 XFCE Thunar / xfce4 等私有缓存（~/.cache 下），轻量桌面清理收益直接。",
        actions=[
            S('rm -rf "$HOME/.cache/Thunar" "$HOME/.cache/xfce4" '
              '"$HOME/.cache/xfce4-notifyd" 2>/dev/null',
              "清理 XFCE 私有缓存目录", rev=True),
        ],
        standards=[
            "[国际] XFCE xfconf 文档（docs.xfce.org，配置系统，xfconf-query 接口）",
        ],
        notes=["参考 XFCE xfconf 文档：缓存与配置散落 ~/.cache 与 ~/.config/xfce4；设置走 xfconf。"],
        caveats=["仅删 ~/.cache 下内容；xfconf 配置存于 ~/.config/xfce4，误删会丢失面板/窗口设置。"],
    ),
    Task(
        id="desktop_recent_docs",
        platform="linux",
        title="清理最近文档记录（隐私）",
        category="privacy",
        risk="low",
        desc="删除最近文档列表（~/.local/share/recently-used.xbel），去除使用痕迹。",
        actions=[
            S('rm -f "$HOME/.local/share/recently-used.xbel" 2>/dev/null',
              "删除最近文档记录（XDG 规范）", rev=True),
        ],
        standards=[
            "[国际] freedesktop.org 桌面项规范（recently-used.xbel 由 GTK 按规范写入）",
        ],
        notes=["参考 freedesktop.org 规范：recently-used.xbel 跨桌面共享最近文档，删除即去痕迹，不影响文件本身。"],
        caveats=["删除后文件管理器/应用的「最近」列表清空，属隐私清理，非删除真实文件。"],
    ),
    Task(
        id="desktop_startup_clean",
        platform="linux",
        title="清理失效的桌面启动项",
        category="cleanup",
        risk="medium",
        desc="检查 ~/.local/share/applications 下 .desktop 启动项是否指向已缺失的可执行文件。",
        actions=[
            S('for f in "$HOME/.local/share/applications"/*.desktop; do '
              '[ -f "$f" ] || continue; exe=$(grep -m1 "^Exec=" "$f" | cut -d= -f2 | cut -d" " -f1); '
              'case "$exe" in ~/.xsession*|*/*) :;; *) command -v "${exe##*/}" >/dev/null || '
              'echo "失效: $(basename "$f") -> $exe";; esac; done 2>/dev/null',
              "列出指向缺失程序的 .desktop 启动项（仅报告，不删）"),
        ],
        standards=[
            "[国际] freedesktop.org 桌面项规范（desktop-entry-spec，.desktop 启动项）",
        ],
        notes=["参考桌面项规范：.desktop 的 Exec= 指向程序；程序已卸载则该启动项失效。本任务仅列出，删除需手动确认。"],
        caveats=["本任务不直接删除 .desktop；确认失效后再手动移除对应文件。"],
    ),
    Task(
        id="desktop_dconf_reset",
        platform="linux",
        title="重置 GNOME 用户设置（dconf）",
        category="maintenance",
        risk="high",
        desc="将 GNOME dconf 用户键清空回到默认（可选：全清或仅某 Schema）。高影响，需确认。",
        actions=[
            M("如需重置全部 GNOME 设置：`dconf reset -f /`（清空当前用户所有键，回到系统默认）；"
              "或仅重置某 Schema：`dconf reset -f /org/gnome/desktop/`。参考 GNOME dconf 文档。",
              "重置 GNOME dconf 用户键（指引，需手动执行并确认）"),
        ],
        standards=[
            "[国际] GNOME dconf 文档（developer.gnome.org，dconf reset 接口）",
        ],
        notes=["参考 GNOME dconf 文档：dconf 以二进制库 ~/.config/dconf/user 存设置；reset -f / 清空全部用户键。",
               "仅影响当前用户，不影响系统级默认值。"],
        caveats=["高危：会清空全部 GNOME 个性化设置（壁纸/字体/快捷键/扩展），执行前务必确认；建议先备份 dconf dump。"],
    ),
    Task(
        id="desktop_kde_kcache",
        platform="linux",
        title="重建 KDE 服务/菜单缓存",
        category="maintenance",
        risk="low",
        desc="用 kbuildsycoca5 重建 KDE 服务(Sycoca)缓存，修复菜单/关联异常（只读重建，不改设置）。",
        actions=[
            S('if command -v kbuildsycoca5 >/dev/null; then kbuildsycoca5 --noincremental; '
              'else echo "未安装 kbuildsycoca5，跳过"; fi',
              "重建 KDE Sycoca 缓存（参考 KConfig 文档）"),
        ],
        standards=[
            "[国际] KDE KConfig 文档（develop.kde.org，kbuildsycoca5 重建服务缓存）",
        ],
        notes=["参考 KDE KConfig 文档：Sycoca 缓存影响菜单/文件关联；重建不改变用户设置，仅刷新索引。"],
        caveats=["无 KDE 环境时自动跳过——不强求安装。"],
    ),
    Task(
        id="desktop_xfconf_report",
        platform="linux",
        title="XFCE 配置核对（xfconf）",
        category="maintenance",
        risk="low",
        desc="用 xfconf-query 列出 XFCE 配置通道，供维护前确认窗口管理器/面板设置。",
        actions=[
            N("desktop.xfconf_report", "列出 XFCE xfconf 通道（参考 XFCE xfconf 文档）"),
        ],
        standards=[
            "[国际] XFCE xfconf 文档（docs.xfce.org，xfconf-query 接口）",
        ],
        notes=["参考 XFCE xfconf 文档：xfconf 以通道/属性模型存设置；`xfconf-query -c xfwm4 -l` 可看窗口管理器键。"],
        caveats=["无 XFCE 环境或未装 xfconf-query 时自动降级为说明。"],
    ),
    Task(
        id="desktop_theme_standard",
        platform="linux",
        title="桌面主题/字体规范核对（freedesktop）",
        category="optimize",
        risk="low",
        desc="按 freedesktop 图标主题规范与 GNOME/KDE HIG 核对当前主题/字体设置是否规范一致。",
        actions=[
            S('echo "图标主题: ${XDG_DATA_DIRS:-$HOME/.local/share}/icons"; '
              'command -v gsettings >/dev/null && gsettings get org.gnome.desktop.interface icon-theme 2>/dev/null; '
              'command -v kreadconfig5 >/dev/null && kreadconfig5 --group Icons --key Theme 2>/dev/null; '
              'true',
              "读取当前图标主题（对照 freedesktop 图标主题规范）"),
        ],
        standards=[
            "[国际] freedesktop.org 图标主题规范（icon-theme-spec，主题/缓存索引）",
            "[国际] GNOME HIG / KDE HIG（人机界面指南，主题与字体一致性）",
        ],
        notes=["参考 freedesktop 图标主题规范：主题须含 index.theme 并在 XDG_DATA_DIRS 下；不一致会导致图标缺失。"],
        caveats=["仅核对/读取设置，不改主题；修改主题请走桌面环境自身设置界面。"],
    ),
    Task(
        id="desktop_cache_report",
        platform="linux",
        title="桌面缓存可回收量只读核对（对比报告）",
        category="maintenance",
        risk="low",
        desc="估算 GNOME/KDE/XFCE 私有缓存与 XDG 通用缓存（缩略图/着色器/mozilla 等）的可回收空间，"
             "生成清理前对比报告。只读，不删除任何文件。",
        actions=[
            N("desktop.cache_report", "估算桌面缓存可回收量（只读对比，不删除，供清理前核对）"),
        ],
        standards=[
            "[国际] freedesktop.org XDG Base Directory 规范（缓存位于 $XDG_CACHE_HOME=~/.cache）",
            "[国际] freedesktop.org 缩略图管理规范（thumbnail 缓存位于 ~/.cache/thumbnails）",
            "[国际] GNOME/KDE/XFCE 文档：缓存为可重建的临时数据，清理不影响用户设置",
        ],
        notes=["参考 XDG 缓存规范：~/.cache 下为可重建临时数据；本任务只估算可回收量并生成对比报告，"
               "真正回收请执行 desktop_gnome_cache / desktop_kde_cache / desktop_xfce_cache（需 --apply）。",
               "配合 `desktop --report <path>` 可导出 Markdown/JSON 对比报告。"],
        caveats=["纯只读：绝不删除文件，也不修改任何设置；报告仅用于清理前决策。"],
    ),
]
