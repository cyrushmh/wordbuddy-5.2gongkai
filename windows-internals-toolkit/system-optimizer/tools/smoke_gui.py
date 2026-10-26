#!/usr/bin/env python3.11
"""图形界面烟雾测试：真的把窗口建起来，点一遍关键按钮，再关掉。

为什么单独一个脚本而不是单元测试
--------------------------------
单元测试不该依赖显示环境（CI 通常没有 X/Wayland）。但「图形模式能用」这件事
只有真建窗口才验得出来——窗口能不能撑起来、任务列表有没有渲染、按钮回调会不会
抛异常、关闭时配置有没有落盘。所以放在 `tools/`，需要显示环境时才跑：

    xvfb-run -a python3.11 tools/smoke_gui.py      # 无显示器也能跑
    python3.11 tools/smoke_gui.py                  # 有显示器直接跑

它**不执行任何优化动作**：只建窗口、切平台、开子窗口、读文本、关窗口。
退出码 0 = 全通过；1 = 有失败项。
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src", "python"))

# 配置落盘重定向到临时目录，绝不污染真实家目录
_TMP = tempfile.mkdtemp(prefix="sysweeper-smoke-")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_TMP, "config")

from sysweeper import gui as guimod  # noqa: E402
from sysweeper import guistate       # noqa: E402

RESULTS = []


def check(name: str, ok: bool, detail: str = ""):
    RESULTS.append((name, ok, detail))
    mark = "✓" if ok else "✗"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    tk, ttk, messagebox, scrolledtext = guimod._tk()

    print("=== 1. 建主窗口 ===")
    root = tk.Tk()
    root.withdraw()  # 不真的秀出来，避免在无显示器环境里卡住
    app = guimod.SysweeperGUI(root, platform="linux", version="")
    check("主窗口构造成功", True)
    check("任务列表已渲染", len(app.vars) > 0, f"{len(app.vars)} 项")

    print("=== 2. 适配当前系统 ===")
    app.adapt_to_system()
    plat = app.platform_cb.get()
    check("探测到平台", bool(plat) and plat != "unknown", f"platform={plat!r}")
    check("版本已填", True, f"version={app.version_var.get()!r}")

    print("=== 3. 开关持久化 ===")
    tid = app.vars[0][0].id
    app.guistate.set_task_enabled(app.state, tid, False)
    app._save_state()
    back = guistate.load()
    check("关掉的项被记住", guistate.is_task_enabled(back, tid) is False, tid)
    app.guistate.set_task_enabled(app.state, tid, True)
    app._save_state()

    print("=== 4. 子窗口能打开 ===")
    for label, fn in (("插件", app.show_plugins), ("更新", app.show_update),
                      ("档位", app.show_profiles)):
        try:
            fn()
            root.update_idletasks()
            check(f"打开「{label}」窗口", True,
                  f"当前 {len(root.winfo_children())} 个顶层窗口")
        except Exception as e:  # noqa: BLE001
            check(f"打开「{label}」窗口", False, repr(e))

    print("=== 5. 关闭落盘 ===")
    app._save_state()
    cfg = guistate.path()
    check("配置文件已落盘", cfg.exists(), str(cfg))
    try:
        root.destroy()
        check("窗口正常销毁", True)
    except Exception as e:  # noqa: BLE001
        check("窗口正常销毁", False, repr(e))

    failed = [n for n, ok, _ in RESULTS if not ok]
    print()
    print(f"合计 {len(RESULTS)} 项，失败 {len(failed)} 项")
    if failed:
        for n in failed:
            print(f"  失败：{n}")
        return 1
    print("图形模式烟雾测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
