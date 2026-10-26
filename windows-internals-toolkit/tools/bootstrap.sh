#!/bin/sh
# sysweeper 引导脚本 —— 语言底层：Python 3（多数 Linux / macOS / BSD 自带）
#
#   sh bootstrap.sh detect          # 探测当前系统
#   sh bootstrap.sh list            # 列出适用任务
#   sh bootstrap.sh android         # Android 只读审计（设备需 adb）
#
# 只做两件事：找一个能用的 python3，然后把参数交给它。不改任何系统设置。
# 若机器上没有 Python，只打印各系统的安装命令，绝不自作主张下载安装。

set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/.." && pwd)

PY=""
for c in python3 py python; do
    if command -v "$c" >/dev/null 2>&1; then
        PY=$c
        break
    fi
done

if [ -z "$PY" ]; then
    echo "未找到 Python 3（sysweeper 的语言底层）。请先安装："
    case "$(uname -s 2>/dev/null || echo unknown)" in
        Darwin)
            echo "  macOS : xcode-select --install   或   brew install python3"
            ;;
        Linux)
            echo "  Debian/Ubuntu : sudo apt-get install -y python3"
            echo "  RHEL/Fedora   : sudo dnf install -y python3"
            echo "  Arch          : sudo pacman -S python"
            echo "  Alpine        : apk add python3"
            echo "  openSUSE      : sudo zypper install python3"
            ;;
        FreeBSD)
            echo "  FreeBSD : pkg install python3   或   cd /usr/ports/lang/python3 && make install"
            ;;
        OpenBSD)
            echo "  OpenBSD : pkg_add python3"
            ;;
        NetBSD)
            echo "  NetBSD  : pkgin install python3"
            ;;
        *)
            echo "  Windows : winget install Python.Python.3.12   （或用 tools/bootstrap.ps1）"
            echo "  其它    : https://www.python.org/downloads/"
            ;;
    esac
    exit 1
fi

# 优先单文件 .pyz（zipapp，零依赖），其次仓库源码
APP=""
for f in "$root/dist"/sysweeper-*.pyz "$root"/sysweeper-*.pyz; do
    if [ -f "$f" ]; then
        APP=$f
        break
    fi
done

if [ -n "$APP" ]; then
    exec "$PY" "$APP" "$@"
fi

if [ -d "$root/system-optimizer/src/python" ]; then
    PYTHONPATH="$root/system-optimizer/src/python"
    export PYTHONPATH
    exec "$PY" -m sysweeper "$@"
fi

echo "未找到可运行入口：请把 sysweeper-*.pyz 放到 dist/，或保留仓库源码目录。"
exit 1
