#!/usr/bin/env python3
# peview_qt.py — 基于 Qt6（PySide6）的 PE 查看器 GUI
#
# 解析逻辑复用纯标准库的 pe_inspect.py（与 C / Rust / Python / .NET / Java / Ruby
# 同源同义，字段口径一致），避免「界面一套、解析一套」。
# Qt6 为官方 LTS 路线；GUI 通过 PySide6（Qt 官方 Python 绑定）实现，跨平台一致。
#
# 用法:
#   python3 peview_qt.py                        # 弹出文件对话框选 PE
#   python3 peview_qt.py file.exe               # 直接打开指定 PE
#   python3 peview_qt.py file.exe --json        # 无头输出 JSON（不加载 Qt，纯标准库）
#   QT_QPA_PLATFORM=offscreen python3 peview_qt.py file.exe --smoke
#                                                  无显示冒烟测试（CI / 无桌面环境用）
import argparse
import json
import sys

import pe_inspect  # 纯标准库解析器（单一真源）


def run_headless(path, verbose=False):
    """无头模式：复用 pe_inspect 解析并打印 JSON，不依赖 Qt。"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        print(f"无法读取文件: {e}")
        return 1
    d, err = pe_inspect.parse(data)
    if err:
        print(err)
        return 1
    if verbose:
        d["verbose"] = True
    print(json.dumps(d, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="基于 Qt6 (PySide6) 的 PE 查看器")
    ap.add_argument("path", nargs="?", help="PE 文件路径；省略则弹出文件对话框")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印数据目录与节特征位（文本模式）")
    ap.add_argument("--json", action="store_true", help="无头输出 JSON（不加载 Qt）")
    ap.add_argument("--smoke", action="store_true", help="GUI 冒烟测试：构建窗口后退出，不进入事件循环")
    args = ap.parse_args()

    if args.json:
        if not args.path:
            print("错误：--json 模式需要指定 path")
            return 1
        return run_headless(args.path, args.verbose)

    # ---- GUI 模式：惰性加载 PySide6（避免无 Qt 环境下 --json 也变慢/失败）----
    from PySide6 import QtWidgets
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                                   QPlainTextEdit, QTabWidget)

    class PeViewWindow(QMainWindow):
        def __init__(self, path=None):
            super().__init__()
            self.setWindowTitle("PE Viewer (Qt6 / PySide6)")
            self.resize(820, 620)
            self._tabs = QTabWidget()
            self._txt = QPlainTextEdit()
            self._txt.setReadOnly(True)
            self._jsn = QPlainTextEdit()
            self._jsn.setReadOnly(True)
            self._tabs.addTab(self._txt, "文本")
            self._tabs.addTab(self._jsn, "JSON")
            self.setCentralWidget(self._tabs)

            open_act = QAction("打开 PE...", self)
            open_act.setShortcut("Ctrl+O")
            open_act.triggered.connect(self._open)
            self.menuBar().addMenu("文件").addAction(open_act)

            if path:
                self._load(path)

        def _open(self):
            p, _ = QFileDialog.getOpenFileName(self, "选择 PE 文件", "", "可执行文件 (*.exe *.dll);;所有文件 (*)")
            if p:
                self._load(p)

        def _load(self, path):
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                self.statusBar().showMessage(f"读取失败: {e}")
                return
            d, err = pe_inspect.parse(data)
            if err:
                self._txt.setPlainText(err)
                self._jsn.setPlainText("")
                self.statusBar().showMessage(f"非 PE: {path}")
                return
            if getattr(self, "_verbose", False):
                d["verbose"] = True
            self._txt.setPlainText(pe_inspect.to_text(d))
            self._jsn.setPlainText(json.dumps(d, ensure_ascii=False, indent=2))
            self.statusBar().showMessage(
                f"{path}  machine=0x{d['machine']:04X}  subsystem={d['optional']['subsystem']}  "
                f"节数={d['number_of_sections']}"
            )

    app = QApplication(sys.argv)
    win = PeViewWindow(args.path)
    if args.verbose:
        win._verbose = True
    win.show()
    if args.smoke:
        app.processEvents()  # 触发一次布局/绘制（offscreen），随后退出，不阻塞
        return 0
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
