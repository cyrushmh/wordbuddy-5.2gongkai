# wine-sni-bridge

> 把 Wine / Windows 系统托盘图标桥接到 Wayland 的 StatusNotifierItem（SNI）协议。
> 来源：[github.com/waliori/wine-sni-bridge](https://github.com/waliori/wine-sni-bridge)（MIT License）。
> 镜像入库时间：2026-10-15，归入 `windows-internals-toolkit` 系统工具集，作为「Windows 兼容层 / Wayland 桌面整合」互补工具。

## 解决什么问题

在 Wayland 上，Wine 的「最小化到托盘」程序（游戏、后台应用）依赖 X11 的 XEmbed 协议。
KDE 的 `xembedsniproxy` 能转成现代 SNI，但它在 wlroots 系合成器（Sway / Hyprland / dwl）上
会创建 `override_redirect`（非托管）X11 窗口，**抢走键盘焦点**——焦点被抢后无法打字/用快捷键，
直到打开关闭 `rofi` 之类重置焦点链。这是 [swaywm/sway#7130](https://github.com/swaywm/sway/issues/7130) 跨合成器的已知问题，上游无修复（Wine 原生 SNI 支持自 2023 年 pending）。

wine-sni-bridge 用**托管型** X11 窗口（`override_redirect=False`，`_NET_WM_WINDOW_TYPE_UTILITY`）
替代，永不请求键盘焦点，由合成器窗口规则完全隐藏，从而根治抢焦点。

## 原理

```
Wine App (minimize to tray)
   |  X11 XEmbed (Shell_NotifyIcon)
   v
wine-sni-bridge.py  (认领 _NET_SYSTEM_TRAY_S0)
   |  - 图标窗口嵌入离屏容器
   |  - CopyArea 抽取像素 / 读 _NET_WM_ICON
   |  - 裁剪 + 缩放 48x48，黑色背景透明化
   v
DBus StatusNotifierItem（每个 Wine 程序一条独立 DBus 连接）
   v
Waybar / 任意 SNI 状态栏
```

## 特性

- 不抢焦点（托管工具窗口，合成器可控）
- 多程序支持（每个 Wine 程序独立 SNI 项 + 独立 DBus 连接）
- 图标缓存（按 WM_CLASS 记忆，重新最小化无白闪）
- 点击转发（状态栏左/中/右键转发回 Wine）
- 抗状态栏重启（监听 StatusNotifierWatcher 重启，自动重新注册）
- 过期图标清理（X11 窗口销毁时自动 undock）
- systemd 用户服务（失败自动重启）
- 单文件 ~580 行 Python，无需构建系统

## 依赖

- Python 3.10+
- `python-xlib`（X11 协议）
- `dbus-python`（DBus 接口）
- `PyGObject`（GLib 主循环）

Debian/Ubuntu：`apt install python3-xlib python3-dbus python3-gi`

## 安装

```bash
cp wine-sni-bridge.py ~/.local/bin/
chmod +x ~/.local/bin/wine-sni-bridge.py
cp wine-sni-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now wine-sni-bridge
```

## 合成器配置（必需）

桥的 X11 容器窗口若不加窗口规则会显形。必须用 `WM_CLASS=wine-sni-bridge` 加规则：
**浮动 + 不聚焦 + 零透明度 + 无边框/无阴影/无模糊/无动画**。

各合成器（Hyprland `windowrulev2` / Sway `for_window` / dwl `windowrule`）示例见上游 README。

## 字节序说明

DBus SNI 规范写 `IconPixmap` 为「网络字节序（大端）ARGB32」，但实测所有已知 SNI 宿主
（waybar 的 Cairo、Quickshell、KDE Plasma 的 Qt `QImage::Format_ARGB32`、fcitx5）都按
**原生字节序**读取（x86_64 小端即 B,G,R,A）。故默认 `--byte-order native` 才渲染正确；
仅当遇到严格按规范的宿主出现颜色反转时改用 `--byte-order network`。

## 与本项目的关系

`windows-internals-toolkit` / `sysweeper` 主线是 Windows 内部机制与系统优化；
wine-sni-bridge 是 **Wine（Windows 兼容层）在 Wayland 上的托盘整合**工具，属互补的
跨平台桌面整合能力——镜像入库便于在 Linux 桌面前端统一管理系统托盘表现。
