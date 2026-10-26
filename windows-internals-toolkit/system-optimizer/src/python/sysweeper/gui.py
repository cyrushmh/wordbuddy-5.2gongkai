"""图形界面（GUI）点选封装。

设计原则「不强求安装」：
- 默认用 **Python 自带的 tkinter**（标准库，零依赖、无需 pip install）。
- 同时探测其他语言「自带」的 GUI 后端（Java Swing / .NET WinForms / Qt），
  在界面与命令行里给出可用状态与替代方案——缺哪个都不报错，只是那条路不通。
- 无图形环境（SSH / 容器 / CI）时优雅降级，退回命令行并给出各后端状态。

界面能力：选平台与版本 → 勾选任务 → 扫描分析 / 执行清理（带确认） / 生成报告。
"""

from __future__ import annotations

import io
import queue
import shutil
import threading
from contextlib import redirect_stdout


def _tk():
    """惰性导入 tkinter（缺图形环境也不至于在 import 阶段就崩）。"""
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
    return tk, ttk, messagebox, scrolledtext


def _nv_note(v: dict) -> str:
    """needs_verify 条目的说明文字：各系统字段不统一（daoxue=why，
    zhuangzi/baigong/datong=note），这里取其一，避免待核实页渲染为空。"""
    return v.get("why") or v.get("note") or v.get("detail") or ""


def chart_rects(rep: dict, width: int = 600, height: int = 400) -> dict:
    """纯函数：把报告算成 Canvas 矩形表（GUI 绘制用，也可单测，不依赖 tkinter）。

    返回 {"disk":[...], "tasks":[...], "width","height","freed"}，
    每个矩形含 x/y/w/h/数值，show_chart 直接拿它来画。
    """
    from . import report as repmod
    d = repmod.chart_data(rep)
    out = {"disk": [], "tasks": [], "width": width, "height": height, "freed": None}
    if d["disk"]:
        b = d["disk"]["before"]
        total = b.get("total") or 1
        left = 90
        barw = max(10, width - left - 30)
        frac = max(0.0, min(1.0, b["used"] / total))
        out["disk"].append({"label": "处理前", "x": left, "y": 60, "w": barw * frac,
                            "h": 22, "frac": frac})
        if "after" in d["disk"]:
            a = d["disk"]["after"]
            frac2 = max(0.0, min(1.0, a["used"] / total))
            out["disk"].append({"label": "处理后", "x": left, "y": 95, "w": barw * frac2,
                                "h": 22, "frac": frac2})
        if rep.get("reclaimed_bytes"):
            out["freed"] = rep["reclaimed_bytes"]
    if d["tasks"]:
        n = len(d["tasks"])
        base_y = 200
        bx = 60
        bw = (width - bx - 30) / max(n, 1)
        mx = max(x["estimate"] for x in d["tasks"]) or 1
        maxh = 110
        for i, x in enumerate(d["tasks"]):
            h = max(2, int(round(x["estimate"] / mx * maxh)))
            out["tasks"].append({"x": bx + i * bw + 6, "y": base_y + (maxh - h),
                                 "w": max(8, bw - 12), "h": h, "value": x["estimate"],
                                 "title": x["title"]})
    return out


def detect_gui_backends() -> list:
    """探测本机可用的 GUI 后端，优先「语言自带」的那些。"""
    out = []

    # Python 自带 tkinter（标准库）
    try:
        import tkinter  # noqa: F401
        out.append({"id": "tkinter", "name": "Python tkinter（标准库自带）",
                    "available": True, "note": "零依赖，本项目 GUI 默认用它"})
    except Exception as e:  # noqa: BLE001
        out.append({"id": "tkinter", "name": "Python tkinter（标准库自带）",
                    "available": False, "note": f"不可用（{e}）；Linux 可装 python3-tk"})

    # Java 自带 Swing/AWT（装了 JDK 就有）
    java = shutil.which("javac") or shutil.which("java")
    out.append({"id": "java_swing", "name": "Java Swing/AWT（JDK 自带）",
                "available": bool(java),
                "note": "装了 JDK 就有，无需额外依赖" if java else "未检测到 JDK"})

    # .NET 自带 WinForms/WPF（装了 SDK 就有）
    dotnet = shutil.which("dotnet")
    out.append({"id": "dotnet_winforms", "name": ".NET WinForms/WPF（SDK 自带）",
                "available": bool(dotnet),
                "note": "装了 .NET SDK 就有（桌面端 Windows 可用）" if dotnet
                        else "未检测到 dotnet"})

    # Qt / PySide6（需 pip 安装，不强求）
    try:
        import PySide6  # noqa: F401
        out.append({"id": "pyside6", "name": "Qt 6 / PySide6（需 pip 安装）",
                    "available": True, "note": "已安装"})
    except Exception:  # noqa: BLE001
        out.append({"id": "pyside6", "name": "Qt 6 / PySide6（需 pip 安装）",
                    "available": False, "note": "未安装；不强求，可用 tkinter 代替"})
    return out


def confirm_risky(parent, title: str, consequence: str, rollback: str = "") -> bool:
    """破坏性操作的统一确认框（南华·养生主=不伤、大宗师=失败指路可回退）。

    确认语固定三段式：做什么 → 后果是什么 → 如何回退（无回退时明示不可逆）。
    无显示环境（tkinter/messagebox 不可用）时返回 False——保守：不确定即不执行。
    """
    head = title.rstrip("？?")
    msg = f"{head}？\n\n后果：{consequence}"
    if rollback:
        msg += f"\n\n回退：{rollback}"
    else:
        msg += "\n\n回退：此操作不可逆，请确认已知晓。"
    try:
        _tkmod, _ttk, messagebox, _st = _tk()
        return bool(messagebox.askyesno("请确认：" + title, msg, parent=parent))
    except Exception:  # noqa: BLE001
        return False


class SysweeperGUI:
    """tkinter 主界面。"""

    def __init__(self, root, platform="linux", version=""):
        from . import registry  # 延迟，避免循环
        from . import guistate
        self.registry = registry
        self.guistate = guistate
        self.state = guistate.load()   # 上次会话的开关/启停选择（持久化，跨会话记住）
        self.root = root
        self.root.title("sysweeper — 万能系统优化与清理")
        self.root.geometry("960x680")
        self.tasks = []
        self.vars = []
        self.last_report = None  # 最近的报告 dict，供「可视化对比」使用
        self._scan_snaps = []    # 扫描流程自动记录的基线快照历史（供跨扫描对比）
        # 用户上次关掉了「跟随系统」，就沿用他手动选的平台/版本
        if not self.state.get("follow_system") and self.state.get("platform"):
            platform = self.state["platform"]
            version = self.state.get("version") or version
        self._platform_default = platform
        self._version_default = version
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 界面搭建 ----------
    def _build(self):
        tk, ttk, _, scrolledtext = _tk()

        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="平台:").grid(row=0, column=0, sticky="w")
        self.platform_cb = ttk.Combobox(
            top, values=list(self.registry.PLATFORM_NAMES.keys()),
            width=22, state="readonly")
        self.platform_cb.set(self._platform_default)
        self.platform_cb.grid(row=0, column=1, padx=2)

        ttk.Label(top, text="版本:").grid(row=0, column=2, sticky="w")
        self.version_var = tk.StringVar(value=self._version_default)
        ttk.Entry(top, textvariable=self.version_var, width=10).grid(row=0, column=3, padx=2)

        ttk.Label(top, text="分类:").grid(row=0, column=4, sticky="w")
        self.cat_cb = ttk.Combobox(top, values=["(全部)"] + list(
            {t.category for t in self.registry.all_tasks()}), width=12, state="readonly")
        _saved_cat = self.state.get("category") or "(全部)"
        self.cat_cb.set(_saved_cat if _saved_cat in (self.cat_cb["values"] or ()) else "(全部)")
        self.cat_cb.grid(row=0, column=5, padx=2)

        ttk.Label(top, text="风险上限:").grid(row=0, column=6, sticky="w")
        self.risk_cb = ttk.Combobox(top, values=["low", "medium", "high"],
                                    width=8, state="readonly")
        self.risk_cb.set(self.state.get("max_risk") or "high")
        self.risk_cb.grid(row=0, column=7, padx=2)

        ttk.Button(top, text="刷新任务", command=self.refresh_tasks).grid(row=0, column=8, padx=6)
        ttk.Button(top, text="适配当前系统",
                   command=self.adapt_to_system).grid(row=0, column=9, padx=4)
        ttk.Button(top, text="更新/检查",
                   command=self.show_update).grid(row=0, column=10, padx=4)
        ttk.Button(top, text="预警应急",
                   command=self.show_emergency).grid(row=0, column=11, padx=4)
        ttk.Button(top, text="组网与算力",
                   command=self.show_mesh_compute).grid(row=0, column=12, padx=4)
        ttk.Button(top, text="新闻与优化资讯",
                   command=self.show_webnews).grid(row=0, column=13, padx=4)
        ttk.Button(top, text="OSI 网络诊断",
                   command=self.show_osi).grid(row=0, column=14, padx=4)
        ttk.Button(top, text="发行版与注记",
                   command=self.show_distro).grid(row=0, column=15, padx=4)
        ttk.Button(top, text="兼容层诊断",
                   command=self.show_proton).grid(row=0, column=16, padx=4)
        ttk.Button(top, text="WSL 诊断",
                   command=self.show_wsl).grid(row=0, column=17, padx=4)
        ttk.Button(top, text="虚拟化/GPU",
                   command=self.show_virtgpu).grid(row=0, column=18, padx=4)
        ttk.Button(top, text="浏览器/引擎",
                   command=self.show_browser).grid(row=0, column=19, padx=4)
        ttk.Button(top, text="DNS 健康",
                   command=self.show_dnshealth).grid(row=0, column=20, padx=4)
        ttk.Button(top, text="Tor 诊断",
                   command=self.show_tor).grid(row=0, column=21, padx=4)
        ttk.Button(top, text="ZeroTier",
                   command=self.show_zerotier).grid(row=0, column=22, padx=4)
        ttk.Button(top, text="系统总览",
                   command=self.show_sysmap).grid(row=0, column=23, padx=4)
        ttk.Button(top, text="控制台",
                   command=self.show_console).grid(row=0, column=24, padx=4)
        ttk.Button(top, text="参数/阈值",
                   command=self.show_settings).grid(row=0, column=25, padx=4)
        ttk.Button(top, text="导入",
                   command=self.show_import).grid(row=0, column=26, padx=4)

        # 第二行：开关与动作
        row = ttk.Frame(self.root, padding=(8, 0))
        row.pack(fill="x")
        self.optin_var = tk.BooleanVar(value=bool(self.state.get("opt_in")))
        self.apply_var = tk.BooleanVar(value=False)
        self.yes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="含网络/ITU 开关(--opt-in)",
                        variable=self.optin_var).pack(side="left")
        ttk.Checkbutton(row, text="真正执行(--apply)",
                        variable=self.apply_var).pack(side="left")
        ttk.Checkbutton(row, text="已确认中高风险(--yes)",
                        variable=self.yes_var).pack(side="left")

        ttk.Label(row, text="报告路径:").pack(side="left", padx=(12, 2))
        self.report_var = tk.StringVar(value=self.state.get("report_path") or "sysweeper-report.md")
        ttk.Entry(row, textvariable=self.report_var, width=22).pack(side="left")

        # 任务勾选区（可滚动）
        mid = ttk.Frame(self.root, padding=(8, 6))
        mid.pack(fill="both", expand=True)
        btns = ttk.Frame(mid)
        btns.pack(fill="x")
        ttk.Label(btns, text="可执行的任务（勾选后作用）:").pack(side="left")
        ttk.Button(btns, text="全选", command=lambda: self._select_all(True)).pack(side="right")
        ttk.Button(btns, text="全不选", command=lambda: self._select_all(False)).pack(side="right")

        self.canvas = tk.Canvas(mid, height=210)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.task_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.task_frame, anchor="nw")
        self.task_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # 日志输出
        self.logbox = scrolledtext.ScrolledText(self.root, height=14, wrap="word")
        self.logbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # 底部动作按钮
        bottom = ttk.Frame(self.root, padding=(8, 0))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="扫描分析（不改系统）",
                   command=lambda: self.run(False)).pack(side="left", padx=2)
        ttk.Button(bottom, text="执行选中项",
                   command=lambda: self.run(True)).pack(side="left", padx=2)
        ttk.Button(bottom, text="生成报告",
                   command=self.gen_report).pack(side="left", padx=2)
        ttk.Button(bottom, text="可视化对比",
                   command=self.show_chart).pack(side="left", padx=2)
        ttk.Button(bottom, text="GUI 后端状态",
                   command=self.show_backends).pack(side="left", padx=2)
        ttk.Button(bottom, text="标准与分类",
                   command=self.show_standards).pack(side="left", padx=2)
        ttk.Button(bottom, text="RFC 知识库",
                   command=self.show_rfc).pack(side="left", padx=2)
        ttk.Button(bottom, text="编程语言库",
                   command=self.show_langref).pack(side="left", padx=2)
        ttk.Button(bottom, text="道枢治理观",
                   command=self.show_daoxue).pack(side="left", padx=2)
        ttk.Button(bottom, text="量子理念",
                   command=self.show_quantum).pack(side="left", padx=2)
        ttk.Button(bottom, text="量子虚拟机",
                   command=self.show_quantum_vm).pack(side="left", padx=2)
        ttk.Button(bottom, text="编译工具链",
                   command=self.show_comp).pack(side="left", padx=2)
        ttk.Button(bottom, text="接口 API",
                   command=self.show_apilab).pack(side="left", padx=2)
        ttk.Button(bottom, text="南华理念",
                   command=self.show_zhuangzi).pack(side="left", padx=2)
        ttk.Button(bottom, text="百工理念",
                   command=self.show_baigong).pack(side="left", padx=2)
        ttk.Button(bottom, text="大同理念",
                   command=self.show_datong).pack(side="left", padx=2)
        ttk.Button(bottom, text="概念系统中心",
                   command=self.show_concepts_center).pack(side="left", padx=2)
        ttk.Button(bottom, text="产品保护",
                   command=self.show_protec).pack(side="left", padx=2)
        ttk.Button(bottom, text="自然科学",
                   command=self.show_sciences).pack(side="left", padx=2)
        ttk.Button(bottom, text="Windows",
                   command=self.show_windows).pack(side="left", padx=2)
        ttk.Button(bottom, text="Unix(SysV)",
                   command=self.show_unix).pack(side="left", padx=2)
        ttk.Button(bottom, text="Android",
                   command=self.show_android).pack(side="left", padx=2)
        ttk.Button(bottom, text="iOS",
                   command=self.show_ios).pack(side="left", padx=2)
        ttk.Button(bottom, text="无障碍", command=self.show_a11y).pack(side="left", padx=2)
        ttk.Button(bottom, text="无障碍(多系统)",
                   command=self.show_a11y_multi).pack(side="left", padx=2)
        ttk.Button(bottom, text="架构/开源硬件",
                   command=self.show_arch).pack(side="left", padx=2)
        ttk.Button(bottom, text="硬件优化",
                   command=self.show_hardware).pack(side="left", padx=2)
        ttk.Button(bottom, text="内核文档",
                   command=self.show_kernel).pack(side="left", padx=2)
        ttk.Button(bottom, text="桌面环境",
                   command=self.show_desktop).pack(side="left", padx=2)
        ttk.Button(bottom, text="系统软件",
                   command=self.show_syssoftware).pack(side="left", padx=2)
        ttk.Button(bottom, text="包管理器",
                   command=self.show_pkgmgr).pack(side="left", padx=2)
        ttk.Button(bottom, text="容器运行时",
                   command=self.show_container).pack(side="left", padx=2)
        ttk.Button(bottom, text="存储/文件系统",
                   command=self.show_storage).pack(side="left", padx=2)
        ttk.Button(bottom, text="网络栈调优",
                   command=self.show_network).pack(side="left", padx=2)
        ttk.Button(bottom, text="网络链接/Mesh",
                   command=self.show_netlink).pack(side="left", padx=2)
        ttk.Button(bottom, text="第三方网络/硬件",
                   command=self.show_thirdparty).pack(side="left", padx=2)
        ttk.Button(bottom, text="OpenWrt",
                   command=self.show_openwrt).pack(side="left", padx=2)
        ttk.Button(bottom, text="插件",
                   command=self.show_plugins).pack(side="left", padx=2)
        ttk.Button(bottom, text="macOS",
                   command=self.show_macos).pack(side="left", padx=2)
        ttk.Button(bottom, text="BSD",
                   command=self.show_bsd).pack(side="left", padx=2)
        ttk.Button(bottom, text="快照/对比",
                   command=self.show_snapshot).pack(side="left", padx=2)
        ttk.Button(bottom, text="扫描快照对比",
                   command=self.show_scan_diff).pack(side="left", padx=2)
        ttk.Button(bottom, text="鸿蒙",
                   command=self.show_harmony).pack(side="left", padx=2)
        ttk.Button(bottom, text="KaihongOS",
                   command=self.show_kaihong).pack(side="left", padx=2)
        ttk.Button(bottom, text="图像能力",
                   command=self.show_media).pack(side="left", padx=2)
        ttk.Button(bottom, text="可启动介质",
                   command=self.show_livemedia).pack(side="left", padx=2)
        ttk.Button(bottom, text="遗留/嵌入式",
                   command=self.show_legacy).pack(side="left", padx=2)
        ttk.Button(bottom, text="无线电/射频",
                   command=self.show_radio).pack(side="left", padx=2)
        ttk.Button(bottom, text="Win分析/逆向",
                   command=self.show_winternals).pack(side="left", padx=2)
        ttk.Button(bottom, text="量子存储",
                   command=self.show_qstore).pack(side="left", padx=2)
        ttk.Button(bottom, text="量子内核",
                   command=self.show_qarch).pack(side="left", padx=2)
        ttk.Button(bottom, text="小程序端",
                   command=self.show_miniapp).pack(side="left", padx=2)
        ttk.Button(bottom, text="OpenJDK/JVM",
                   command=self.show_jdk).pack(side="left", padx=2)
        ttk.Button(bottom, text="内核模块/固件",
                   command=self.show_kmod).pack(side="left", padx=2)
        ttk.Button(bottom, text="档位(大而全/小而全)",
                   command=self.show_profiles).pack(side="left", padx=2)
        ttk.Button(bottom, text="版本通道",
                   command=self.show_channels).pack(side="left", padx=2)
        ttk.Button(bottom, text="设备长期使用保护",
                   command=self.show_durability).pack(side="left", padx=2)
        ttk.Button(bottom, text="供电与环境安全",
                   command=self.show_electrical).pack(side="left", padx=2)
        ttk.Button(bottom, text="声学与音律",
                   command=self.show_acoustics).pack(side="left", padx=2)
        ttk.Button(bottom, text="外部设备连接与兼容",
                   command=self.show_peripheral).pack(side="left", padx=2)
        ttk.Button(bottom, text="国内标准·App隐私合规",
                   command=self.show_androidstd).pack(side="left", padx=2)
        ttk.Button(bottom, text="GMS标准·Play上架",
                   command=self.show_gmsstd).pack(side="left", padx=2)
        ttk.Button(bottom, text="F-Droid标准·免GMS分发",
                   command=self.show_fdroidstd).pack(side="left", padx=2)
        ttk.Button(bottom, text="国内标准·资源/协议/第三方",
                   command=self.show_cnstd).pack(side="left", padx=2)
        ttk.Button(bottom, text="鸿蒙生态·HAP/侧载/版图",
                   command=self.show_hmos_ecosystem).pack(side="left", padx=2)
        ttk.Button(bottom, text="鸿蒙标准·权限/隐私/上架",
                   command=self.show_hmosstd).pack(side="left", padx=2)
        ttk.Button(bottom, text="黑箱逆向·UPX/GDB/熵",
                   command=self.show_reverse).pack(side="left", padx=2)
        ttk.Button(bottom, text="时空与全维度",
                   command=self.show_chrono).pack(side="left", padx=2)
        ttk.Button(bottom, text="虚拟机环境",
                   command=self.show_virt).pack(side="left", padx=2)
        ttk.Button(bottom, text="软件包规范审计",
                   command=self.show_packages).pack(side="left", padx=2)
        ttk.Button(bottom, text="AP 集中控制器",
                   command=self.show_apctrl).pack(side="left", padx=2)
        ttk.Button(bottom, text="LLVM 工具链",
                   command=self.show_llvm).pack(side="left", padx=2)
        ttk.Button(bottom, text="工具链全景",
                   command=self.show_toolchain).pack(side="left", padx=2)
        ttk.Button(bottom, text="组网与设备协同",
                   command=self.show_meshnet).pack(side="left", padx=2)
        ttk.Button(bottom, text="周天星斗大阵",
                   command=self.show_matrix).pack(side="left", padx=2)
        ttk.Button(bottom, text="十二都天神煞大阵",
                   command=self.show_f2b).pack(side="left", padx=2)
        ttk.Button(bottom, text="虚拟根DNS与多CDN",
                   command=self.show_vdns).pack(side="left", padx=2)
        ttk.Button(bottom, text="IPP 打印发现",
                   command=self.show_ipp).pack(side="left", padx=2)
        ttk.Button(bottom, text="现代显示与GPU",
                   command=self.show_display).pack(side="left", padx=2)
        ttk.Button(bottom, text="常态化回头看",
                   command=self.show_retro).pack(side="left", padx=2)
        ttk.Button(bottom, text="人类文明重启透镜",
                   command=self.show_restart).pack(side="left", padx=2)
        ttk.Button(bottom, text="汇编语言优化",
                   command=self.show_asm).pack(side="left", padx=2)
        ttk.Button(bottom, text="远程接入审计",
                   command=self.show_remote).pack(side="left", padx=2)
        ttk.Button(bottom, text="证书与加密",
                   command=self.show_cert).pack(side="left", padx=2)
        ttk.Button(bottom, text="联动连轴",
                   command=self.show_linkage).pack(side="left", padx=2)
        ttk.Button(bottom, text="文档与概念联动",
                   command=self.show_docs).pack(side="left", padx=2)
        ttk.Button(bottom, text="联动图",
                   command=self.show_linkage_graph).pack(side="left", padx=2)
        ttk.Button(bottom, text="兼容层串联",
                   command=self.show_compat).pack(side="left", padx=2)
        ttk.Button(bottom, text="Linux 发行面",
                   command=self.show_linux).pack(side="left", padx=2)
        ttk.Button(bottom, text="压缩空间分析",
                   command=self.show_compress).pack(side="left", padx=2)
        ttk.Button(bottom, text="单板机(SBC)",
                   command=self.show_edge).pack(side="left", padx=2)
        ttk.Button(bottom, text="字体与文本规范化",
                   command=self.show_fonts).pack(side="left", padx=2)
        ttk.Button(bottom, text="全能全知自检",
                   command=self.show_omni).pack(side="left", padx=2)
        ttk.Button(bottom, text="数学评分",
                   command=self.show_score).pack(side="left", padx=2)
        ttk.Button(bottom, text="控制台(全模块)",
                   command=self.show_console).pack(side="left", padx=2)
        ttk.Button(bottom, text="参数/阈值",
                   command=self.show_settings).pack(side="left", padx=2)
        ttk.Button(bottom, text="导入(剪贴板/文件/二维码)",
                   command=self.show_import).pack(side="left", padx=2)
        ttk.Button(bottom, text="退出", command=self._on_close).pack(side="right", padx=2)

        self.refresh_tasks()

    # ---------- 任务列表 ----------
    def refresh_tasks(self):
        tk, ttk, _, _ = _tk()
        for w in self.task_frame.winfo_children():
            w.destroy()
        self.vars = []
        platform = self.platform_cb.get()
        version = self.version_var.get().strip() or "0"
        category = self.cat_cb.get()
        category = None if category in ("", "(全部)") else category
        self.tasks = self.registry.applicable(
            platform, version, category, self.risk_cb.get(),
            include_opt_in=self.optin_var.get())
        if not self.tasks:
            ttk.Label(self.task_frame,
                      text="（无匹配任务；可换平台/版本，或勾选 --opt-in 纳入网络/ITU 开关）"
                      ).pack(anchor="w")
            return
        for t in self.tasks:
            # 勾选 = 启用。初值来自持久配置：上次关掉的项这次不再默认勾上。
            v = tk.IntVar(value=1 if self.guistate.is_task_enabled(self.state, t.id) else 0)
            ttk.Checkbutton(
                self.task_frame,
                text=f"{t.display_title()}   [{t.category}/{t.risk}]   (id={t.id})",
                variable=v,
                command=lambda tid=t.id, var=v: self._on_task_toggle(tid, var),
            ).pack(anchor="w")
            self.vars.append((t, v))

    def _select_all(self, on: bool):
        for _t, v in self.vars:
            v.set(1 if on else 0)

    def selected_tasks(self):
        return [t for t, v in self.vars if v.get()]

    def log(self, text: str):
        self.logbox.insert("end", text)
        self.logbox.see("end")

    # ---------- 开关持久化（跨会话记住「开了什么、关了什么」） ----------
    def _on_task_toggle(self, task_id: str, var):
        """优化项开关变动 → 立刻写入配置。

        关掉的项记进 disabled_tasks，下次打开界面不再默认勾上；
        重新勾上则从名单里移除。只存 id，不存命令、不执行任何东西。
        """
        self.guistate.set_task_enabled(self.state, task_id, bool(var.get()))
        self._save_state()

    def _on_plugin_toggle(self, plugin_id: str, var):
        """插件启停开关变动 → 写入配置（同理只存 id）。"""
        self.guistate.set_plugin_enabled(self.state, plugin_id, bool(var.get()))
        self._save_state()
        self.log(f"\n插件 {plugin_id}：{'启用' if var.get() else '停用'}（已记住）\n")

    def _save_state(self):
        """把界面当前选择写回配置文件（平台/版本/分类/风险/开关/报告路径）。"""
        try:
            self.state["platform"] = self.platform_cb.get()
            self.state["version"] = self.version_var.get().strip()
            self.state["category"] = self.cat_cb.get()
            self.state["max_risk"] = self.risk_cb.get()
            self.state["opt_in"] = bool(self.optin_var.get())
            self.state["report_path"] = self.report_var.get().strip()
            self.guistate.save(self.state)
        except Exception as e:  # noqa: BLE001 - 存不下配置不该影响使用
            self.log(f"\n（配置保存失败，本次会话有效：{e}）\n")

    def _on_close(self):
        """关闭窗口前保存开关状态——否则用户勾的东西白勾。"""
        self._save_state()
        self.root.destroy()

    # ---------- 适配当前系统 ----------
    def adapt_to_system(self):
        """探测当前系统，把平台/版本填进界面并刷新任务列表。

        「适配当前系统」= 不用用户手填平台版本，直接认出本机是什么系统。
        """
        from .detect import detect

        try:
            d = detect()
        except Exception as e:  # noqa: BLE001
            self.log(f"\n探测当前系统失败：{e}\n")
            return
        plat = d.get("platform") or "unknown"
        ver = d.get("version") or ""
        distro = d.get("distro") or ""
        self.platform_cb.set(plat if plat != "unknown" else "linux")
        self.version_var.set(ver)
        self.state["follow_system"] = True
        self._save_state()
        self.refresh_tasks()
        self.log("\n已适配当前系统"
                 f"：{plat} {ver}{(' / ' + distro) if distro else ''}\n")

    # ---------- 更新 ----------
    def show_emergency(self):
        """预警应急窗口（v0.6.8）：定位综合 → 预警评估 → 呼救文本 → 手动开关。

        定位口径按使用者定的：先网络 + 基站为首选基线，检测到导航定位再与基线
        **共同综合**。手动开关**真生效**（关掉的功能直接返回关闭提示，不偷偷跑）。
        红线：呼救只生成文本，绝不自动发送；订阅源默认关闭，不主动联网。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import emergency

        top = tk.Toplevel(self.root)
        top.title("预警应急（定位 · 预警 · 呼救 · 手动开关）")
        top.geometry("900x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 预警应急 ====")
        put("口径：先网络 + 基站为首选基线；检测到导航定位则与基线共同综合。")
        put("红线：不自动报警 / 不拨号 / 不发短信；呼救只生成文本，通道由你选。")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="定位与距离综合",
                   command=lambda: run("定位与距离综合",
                                       emergency.position_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="预警评估",
                   command=lambda: run("预警评估",
                                       emergency.alert_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("能力自检",
                                       emergency.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="生成呼救文本",
                   command=lambda: run("应急呼救文本（只生成，不发送）",
                                       lambda: (True, emergency.sos_text()))).pack(side="left", padx=2)
        ttk.Button(bar, text="总报告",
                   command=lambda: run("预警应急总报告",
                                       emergency.emergency_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

        # 手动开关：勾选 = 启用，立即落盘（只存布尔值，不存命令）
        en = ttk.LabelFrame(top, text="手动开关（勾选=启用，立即记住；关掉的功能不参与运行）")
        en.pack(fill="x", padx=8, pady=(0, 8))
        for name, (dflt, desc) in emergency.SWITCHES.items():
            var = tk.BooleanVar(value=emergency.switch_on(name))

            def make(nm=name, v=var):
                def _cb():
                    emergency.set_switch(nm, v.get())
                    self.log(f"\n预警应急开关 {nm} = {'开' if v.get() else '关'}\n")
                return _cb

            ttk.Checkbutton(en, text=f"{name} — {desc}",
                            variable=var, command=make()).pack(anchor="w")

    def show_mesh_compute(self):
        """组网通信 + 分布式计算窗口（v0.6.9）：看协议、看算力、看调度计划。

        只放只读报告：**不在这里发包、不在这里派活**——发包与跑批都是动作，
        走任务勾选区（需 --apply），不在只读窗口里偷偷执行。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import distjob, meshchat, distcompute

        top = tk.Toplevel(self.root)
        top.title("组网通信与分布式计算（只读报告）")
        top.geometry("900x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 组网通信（IPMsg / 飞鸽传书 / iptux 兼容）====")
        put("红线：收到的文件不自动落盘，进待收清单由你显式接受。")
        put("==== 分布式计算（BOINC 式，但绝不执行外部代码）====")
        put("红线：只跑内置可验证算子，不下载、不执行任何外部程序。")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="组网协议",
                   command=lambda: run("组网协议核对",
                                       meshchat.protocol_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="表情/颜文字",
                   command=lambda: run("emoji", meshchat.emoji_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="收件箱",
                   command=lambda: run("收件箱与待收文件",
                                       meshchat.inbox_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="本机算力",
                   command=lambda: run("本机算力画像",
                                       distcompute.capability_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="内置算子",
                   command=lambda: run("内置可验证算子",
                                       distcompute.ops_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="调度计划",
                   command=lambda: run("调度计划", distcompute.plan_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="派活自检",
                   command=lambda: run("跨机派活链路自检（本地回环，不通网）",
                                       distjob.loopback_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="派活状态",
                   command=lambda: run("跨机派活状态", distjob.job_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="总报告",
                   command=lambda: run("分布式计算总报告",
                                       distcompute.distcompute_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_webnews(self):
        """新闻与优化资讯窗口（v0.6.11）：看来源、抓资讯、看点子（只读）。

        只放只读报告与「抓取」按钮：**这里不自动改任何系统设置**——
        抓来的文本只是建议，落不落地由用户决定。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import webnews

        top = tk.Toplevel(self.root)
        top.title("新闻与优化资讯（只读）")
        top.geometry("900x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 新闻/网站优化资讯层（只读）====")
        put("红线：抓来的永远是文本，本层无执行路径——不自动改系统；"
            "优化建议要不要落地由你决定。")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("本层能力自检", webnews.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="配置来源",
                   command=lambda: run("当前配置的来源", webnews.sources_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="抓取资讯",
                   command=lambda: run("抓取并抽取知识点（可联网）",
                                       lambda: webnews.fetch_all())).pack(side="left", padx=2)
        ttk.Button(bar, text="知识点",
                   command=lambda: run("缓存里的优化知识点", webnews.knowledge_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_osi(self):
        """OSI 七层网络诊断窗口（v0.6.13）：L1–L7 整体只读诊断（只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import osi

        top = tk.Toplevel(self.root)
        top.title("OSI 七层网络诊断（只读）")
        top.geometry("900x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== OSI 七层网络诊断（ISO/IEC 7498-1 / ITU-T X.200，只读）====")
        put("红线：只读 /sys/class/net、ip/ss/ethtool/openssl 只读项、DNS 解析、显式 "
            "http(s) 探测；不写地址/路由/防火墙，不连校外网做写操作。")
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("本层能力自检", osi.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="七层总报告",
                   command=lambda: run("L1–L7 整体只读诊断", osi.osi_report)).pack(side="left", padx=2)
        for n in range(1, 8):
            ttk.Button(bar, text=f"L{n}",
                       command=lambda nn=n: run(f"第 {nn} 层", lambda: osi.layer_report(nn))).pack(side="left", padx=1)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_distro(self):
        """发行版与发行注记窗口（v0.6.13）：识别 + 读本地注记（只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import distro

        top = tk.Toplevel(self.root)
        top.title("发行版与发行注记（只读）")
        top.geometry("900x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 发行版与发行注记（只读本地 NEWS.Debian / changelog）====")
        put("红线：不 apt-get changelog（联网）、不改源、不写文件。")
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("本层能力自检", distro.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="发行版与注记",
                   command=lambda: run("发行版身份 + 注记来源", distro.distro_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_proton(self):
        """游戏/应用兼容层诊断窗口（v0.6.14）：Proton/Wine 前提核验（只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import proton

        top = tk.Toplevel(self.root)
        top.title("兼容层诊断（Proton/Wine，只读）")
        top.geometry("900x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 游戏/应用兼容层诊断（Proton/Wine 坐标系，只读）====")
        put("判断这台机器能否跑 Windows 游戏/程序：Vulkan / 32位 / 同步原语 / Steam Runtime。")
        put("运行原则（参照 microsoft/litebox）：兼容层应在最小权限、可审计、可接管环境运行。")
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("本层能力自检", proton.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="兼容层诊断",
                   command=lambda: run("Proton/Wine 前提核验", proton.proton_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def _readonly_window(self, title, mod, report_fn, intro, principle=None):
        """导入分析类只读窗口的通用骨架（v0.6.15）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        top = tk.Toplevel(self.root)
        top.title(title)
        top.geometry("900x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run(t, fn):
            put("")
            put(f"==== {t} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{t}: 已完成\n")

        put(intro)
        if principle:
            put(principle)
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="能力自检",
                   command=lambda: run("本层能力自检", mod.capabilities_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="诊断",
                   command=lambda: run("只读诊断", report_fn)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_wsl(self):
        """WSL 环境只读诊断窗口（v0.6.15）。"""
        from .native import wsl
        self._readonly_window(
            "WSL 环境诊断（只读）", wsl, wsl.wsl_report,
            "判断本机是否 WSL、版本 1/2、内核与微软主线差多远、systemd 配置。",
            "红线：不写 wsl.conf/.wslconfig、不 wsl --shutdown、不连校外网。")

    def show_virtgpu(self):
        """虚拟化与 GPU 虚拟化只读诊断窗口（v0.6.15）。"""
        from .native import virtgpu
        self._readonly_window(
            "虚拟化与 GPU 虚拟化诊断（只读）", virtgpu, virtgpu.virtgpu_report,
            "判断是否虚拟化、virtio 设备、virtio-gpu（Venus 协议免直通加速）、DRM 后端。",
            "红线：不加载模块、不装驱动、不改 QEMU/crosvm、不连校外网。")

    def show_browser(self):
        """浏览器与引擎检测窗口（v0.6.15）。"""
        from .native import browser
        self._readonly_window(
            "浏览器与引擎检测（只读）", browser, browser.browser_report,
            "探测已装浏览器/引擎(Blink/Gecko)版本 + Web 兼容知识参考（mdn/bcd 坐标系）。",
            "红线：不下载 BCD 全量 JSON、不连校外网、不自动改浏览器配置。")

    def show_dnshealth(self):
        """DNS 解析健康度只读诊断窗口（v0.6.15）。"""
        from .native import dnshealth
        self._readonly_window(
            "DNS 解析健康度诊断（只读）", dnshealth, dnshealth.dnshealth_report,
            "聚焦解析链路：nameserver 来源 / systemd-resolved stub / 一次良性解析延迟。",
            "红线：不写 resolv.conf、不重启 resolved、不改 DNS；解析探测只读不改状态。")

    def show_tor(self):
        """Tor（洋葱路由）匿名/隐私网络只读诊断窗口（v0.6.17）。"""
        from .native import tor
        self._readonly_window(
            "Tor 匿名/隐私网络诊断（只读）", tor, tor.tor_report,
            "洋葱路由覆盖网络：tor 安装/版本/守护进程/torrc（SOCKS·控制端口·桥接·可插拔传输·中继-出口）。",
            "红线：不启停 tor、不改 torrc、不连控制端口、不打印密钥明文。")

    def show_zerotier(self):
        """ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断窗口（v0.6.17）。"""
        from .native import zerotier
        self._readonly_window(
            "ZeroTier 虚拟网络诊断（只读）", zerotier, zerotier.zerotier_report,
            "虚拟二层网 VL1：zerotier-one 安装/版本/运行态/identity/已加入网络/控制器/moon。",
            "红线：不启停 zerotier-one、不 join/leave、不读 identity.secret（私钥）。")

    def show_sysmap(self):
        """系统统筹总览（你中有我，我中有你）只读窗口（v0.6.18）。"""
        from .native import sysmap
        self._readonly_window(
            "系统统筹总览（只读）", sysmap, sysmap.sysmap_report,
            "只读编排 13 个子系统：整体健康汇总 + 局部本征状态 + 关联关系图 + 有序深入建议。",
            "红线：不启停服务、不改配置、不连控制端口、不写入任何系统状态。")

    def show_subsystems(self):
        """兼容旧入口：等价于「系统控制台」（开关 + 操作合一）。"""
        self.show_console()

    def show_console(self):
        """完全图形界面控制与操作（v0.6.22）：左栏全模块开关 + 逐个操作，右栏输出。

        左栏按层分组列出**全部**已登记子系统（firmware / plugins / modules / kernel /
        storage / container / hardware / 跨平台 OS 探测…），每行三件事：
          勾开关（是否嵌入 sysmap 总览）、显示 key、点「诊断」就地执行该子系统的只读检查。
        右栏是输出区；底部一键全选 / 全不选 / 保存开关 / 系统总览 / 清空。

        红线：这里能操作的全是各子系统既有的**只读**报告函数，不改任何系统状态；
        真正会改系统的动作只在主窗口「执行选中项」里，且需显式勾选 --apply + --yes。
        """
        import importlib

        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import subsystems as subs

        top = tk.Toplevel(self.root)
        top.title("系统控制台（全模块：开关 + 操作）")
        top.geometry("1120x700")

        status = tk.StringVar(value="")
        ttk.Label(top,
                  text="左栏勾选 = 嵌入 sysmap 总览；点「诊断」= 就地执行该子系统的只读检查。"
                       "此处所有操作均为只读，不改系统状态。").pack(anchor="w", padx=8, pady=(6, 2))
        ttk.Label(top, textvariable=status).pack(anchor="w", padx=8)

        body = ttk.Frame(top)
        body.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # ── 左栏：按层分组的模块清单（可滚动）──
        left = ttk.Frame(body)
        left.pack(side="left", fill="y")
        canvas = tk.Canvas(left, width=430)
        canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # ── 右栏：输出 ──
        box = scrolledtext.ScrolledText(body, wrap="word")
        box.pack(side="left", fill="both", expand=True, padx=(8, 0))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def run_one(it):
            """就地执行某子系统的只读报告（tuple / list 两种返回都兼容）。"""
            put("")
            put(f"==== {it['label']}  [{it['key']} · {it['layer']}] ====")
            try:
                mod = importlib.import_module("sysweeper.native." + it["module"])
                fn = getattr(mod, it["fn"], None)
                if fn is None:
                    put("[失败] 报告函数不可用")
                    return
                r = fn()
                if isinstance(r, tuple):
                    ok = bool(r[0]) if r else False
                    msg = str(r[1]) if len(r) > 1 else ""
                    put(f"[{'成功' if ok else '未完成'}] {msg}")
                elif isinstance(r, list):
                    put("[成功] " + "\n".join(str(x) for x in r))
                else:
                    put(f"[成功] {r}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{it['label']}：诊断完成\n")

        items = subs.list_subsystems()
        vars_ = {}
        grouped = {}
        for it in items:
            grouped.setdefault(it["layer"], []).append(it)
        for layer in grouped:
            ttk.Label(inner, text=f"── {layer} ──").pack(anchor="w", pady=(6, 1))
            for it in grouped[layer]:
                row = ttk.Frame(inner)
                row.pack(fill="x")
                v = tk.BooleanVar(value=it["enabled"])
                vars_[it["key"]] = v
                ttk.Checkbutton(row, text=it["label"], variable=v,
                                width=20).pack(side="left")
                ttk.Label(row, text=it["key"], width=17).pack(side="left")
                ttk.Button(row, text="诊断", width=6,
                           command=lambda s=it: run_one(s)).pack(side="left", padx=2)

        def refresh_status():
            on = sum(1 for v in vars_.values() if v.get())
            status.set(f"已开启 {on}/{len(vars_)}　配置落点：{subs.CONFIG_PATH}")

        def do_all(val):
            for v in vars_.values():
                v.set(val)
            refresh_status()

        def do_save():
            states = {k: bool(v.get()) for k, v in vars_.items()}
            subs.save_states(states)
            on = sum(1 for v in states.values() if v)
            self.log(f"\n模块开关已保存：开启 {on}/{len(states)}"
                     f"（配置：{subs.CONFIG_PATH}）\n")
            refresh_status()
            try:
                messagebox.showinfo("已保存", f"已保存模块开关：开启 {on}/{len(states)}")
            except Exception:  # noqa: BLE001
                pass

        def do_clear():
            box.delete("1.0", "end")

        def _on_param_change(changes):
            """参数在他处被改时，控制台输出区实时看到（不必重开窗口）。"""
            try:
                if top.winfo_exists():
                    top.after(0, lambda: put(
                        "[参数已变更] " + ", ".join(
                            f"{k}: {v[0]} → {v[1]}" for k, v in changes.items())))
            except Exception:  # noqa: BLE001
                pass

        from .native import settings as _st
        _st.on_change(_on_param_change)

        refresh_status()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(6, 8))
        ttk.Button(bar, text="全选", command=lambda: do_all(True)).pack(side="left", padx=2)
        ttk.Button(bar, text="全不选", command=lambda: do_all(False)).pack(side="left", padx=2)
        ttk.Button(bar, text="保存开关", command=do_save).pack(side="left", padx=2)
        ttk.Button(bar, text="系统总览", command=self.show_sysmap).pack(side="left", padx=2)
        ttk.Button(bar, text="清空输出", command=do_clear).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right", padx=2)

    def show_settings(self):
        """参数与阈值窗口（v0.6.23）：图形界面直接调控**运行参数**与**数值阈值**。

        控件按类型自动生成：数值→Spinbox（带上下界）、枚举→下拉、路径→输入框+浏览、
        布尔→勾选。「保存」后写配置文件并立即生效（下次诊断即按新阈值跑）。

        透明性：每行都标出该参数的**生效点**（真实消费位置），
        越界/类型错会被拒绝并回退默认值，并逐项报告哪条没通过。
        """
        tk, ttk, messagebox, _st = _tk()
        from tkinter import filedialog
        from .native import settings as st

        top = tk.Toplevel(self.root)
        top.title("参数与阈值（可调控）")
        top.geometry("1000x700")
        status = tk.StringVar(value="")
        ttk.Label(top,
                  text="改完点「保存」即生效（数值类会在下次诊断时按新阈值跑）。"
                       "越界或类型不对的取值会被拒绝并回退默认值。").pack(
            anchor="w", padx=8, pady=(6, 2))
        ttk.Label(top, textvariable=status).pack(anchor="w", padx=8)

        body = ttk.Frame(top)
        body.pack(fill="both", expand=True, padx=8, pady=(4, 0))
        canvas = tk.Canvas(body)
        canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        rows = {}  # key -> (kind, var, widget)
        marks = {}  # key -> 标签控件（用于「已改动」高亮）
        reset_btns = {}  # key -> 单项复位按钮

        def add_row(s, cur):
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=2)
            changed = (cur != s["default"])
            mk = {"foreground": "#0a58ca"} if changed else {}
            mark = ttk.Label(row, text=s["label"] + ("  ●" if changed else ""),
                             width=20, **mk)
            mark.pack(side="left")
            marks[s["key"]] = mark
            if s["kind"] == "int":
                v = tk.StringVar(value=str(cur))
                lo = int(s["min"]) if s["min"] is not None else 0
                hi = int(s["max"]) if s["max"] is not None else 10 ** 9
                w = ttk.Spinbox(row, from_=lo, to=hi, textvariable=v, width=12)
                w.pack(side="left")
                ttk.Label(row, text=(s["unit"] or "") + f"  ({lo}~{hi})",
                          width=18).pack(side="left")
            elif s["kind"] == "enum":
                v = tk.StringVar(value=str(cur))
                w = ttk.Combobox(row, textvariable=v, width=16,
                                 values=list(s["choices"]), state="readonly")
                w.pack(side="left")
                ttk.Label(row, text="可选 " + str(len(s["choices"])) + " 项",
                          width=18).pack(side="left")
            elif s["kind"] == "bool":
                v = tk.BooleanVar(value=bool(cur))
                w = ttk.Checkbutton(row, variable=v)
                w.pack(side="left")
                ttk.Label(row, text="", width=18).pack(side="left")
            else:  # path / str
                v = tk.StringVar(value=str(cur))
                w = ttk.Entry(row, textvariable=v, width=28)
                w.pack(side="left")
                if s["kind"] == "path":
                    ttk.Button(row, text="浏览", width=5,
                               command=lambda: _pick_dir(v)).pack(side="left", padx=2)
                else:
                    ttk.Button(row, text="浏览", width=5,
                               command=lambda: _pick_file(v)).pack(side="left", padx=2)
                ttk.Label(row, text="", width=18).pack(side="left")
            ttk.Label(row, text=s["key"], width=16).pack(side="left")
            rows[s["key"]] = (s["kind"], v, w)
            rb = ttk.Button(row, text="复位", width=5,
                            command=lambda k=s["key"]: do_reset_one(k))
            rb.config(state=("normal" if changed else "disabled"))
            rb.pack(side="left", padx=2)
            reset_btns[s["key"]] = rb
            sub = ttk.Frame(inner)
            sub.pack(fill="x")
            ttk.Label(sub, text="　　" + s["desc"] + "　→ 生效: " + s["apply"],
                      foreground="#666666").pack(anchor="w")

        def _pick_dir(v):
            try:
                d = filedialog.askdirectory(parent=top)
                if d:
                    v.set(d)
            except Exception:  # noqa: BLE001
                pass

        def _pick_file(v):
            try:
                f = filedialog.asksaveasfilename(parent=top)
                if f:
                    v.set(f)
            except Exception:  # noqa: BLE001
                pass

        def fill():
            vals = st.load()
            for s in st.list_settings():
                kind, v, _w = rows[s["key"]]
                cur = vals.get(s["key"], s["default"])
                if kind == "bool":
                    v.set(bool(cur))
                else:
                    v.set("" if cur is None else str(cur))

        def render():
            for w in list(inner.winfo_children()):
                try:
                    w.destroy()
                except Exception:  # noqa: BLE001
                    pass
            marks.clear()
            reset_btns.clear()
            vals = st.load()
            for g in st.groups():
                ttk.Label(inner, text=f"── {g} ──").pack(anchor="w", pady=(8, 2))
                for s in st.list_settings():
                    if s["group"] == g:
                        add_row(s, vals.get(s["key"], s["default"]))

        def refresh_marks():
            """只刷新「已改动」高亮与状态行——不重建控件，避免打断正在输入的人。"""
            vals = st.load()
            for s in st.list_settings():
                k = s["key"]
                if k not in marks:
                    continue
                cur = vals.get(k, s["default"])
                changed = (cur != s["default"])
                marks[k].config(text=s["label"] + ("  ●" if changed else ""),
                                foreground=("#0a58ca" if changed else ""))
                if k in reset_btns:
                    reset_btns[k].config(state=("normal" if changed else "disabled"))
            refresh_status()

        def refresh_status():
            ch = st.changed_keys()
            if ch:
                tail = f"　已改动 {len(ch)} 项: " + "、".join(ch)
            else:
                tail = "　（全部为默认值）"
            status.set(f"共 {len(rows)} 项可调{tail}　配置落点：{st.CONFIG_PATH}")

        def do_reset_one(k):
            """把这一项恢复默认（留痕记为 gui 单项复位）。"""
            st.set_value(k, st.BY_KEY[k].default, source="gui", note="单项复位")
            fill()
            refresh_marks()
            self.log(f"\n参数 {k} 已复位为默认值\n")

        def do_save():
            vals = {}
            for k, (kind, v, _w) in rows.items():
                try:
                    raw = v.get()
                except Exception:  # noqa: BLE001
                    continue
                if kind == "int":
                    try:
                        vals[k] = int(str(raw).strip())
                    except ValueError:
                        vals[k] = str(raw)  # 交给校验去拒
                else:
                    vals[k] = raw
            results = st.apply_updates(vals, source="gui", note="参数窗口保存")
            bad = [(k, why) for k, ok, why in results if not ok]
            self.log(f"\n参数已保存：{len(results) - len(bad)}/{len(results)} 项生效"
                     f"（配置：{st.CONFIG_PATH}）\n")
            if bad:
                msg = "\n".join(f"· {k}：{why}（已回退默认值）" for k, why in bad)
                try:
                    messagebox.showwarning("部分参数未通过校验", msg)
                except Exception:  # noqa: BLE001
                    pass
                fill()
            refresh_marks()

        def do_reset():
            if not confirm_risky(
                    top, "恢复默认",
                    "全部参数与阈值恢复为默认值，当前自定义设置被覆盖。",
                    "恢复前可在参数窗口「导出」为 sysweeper-settings.json 备份；"
                    "变更留痕仍保留，可在「留痕」窗口对照还原。"):
                return
            st.reset(source="gui", origin="参数窗口")
            fill()
            refresh_marks()
            self.log("\n参数已恢复默认值\n")

        def _on_external_change(_changes):
            """他处（导入窗口 / 控制台 / 命令行）改了参数时，本窗口自动跟上。

            这就是「实时联动」：不用关掉重开，改动立刻反映在当前界面上。
            """
            try:
                if top.winfo_exists():
                    top.after(0, lambda: (fill(), refresh_marks()))
            except Exception:  # noqa: BLE001
                pass

        def do_export():
            try:
                p = filedialog.asksaveasfilename(
                    parent=top, defaultextension=".json",
                    initialfile="sysweeper-settings.json")
            except Exception:  # noqa: BLE001
                return
            if not p:
                return
            import json
            try:
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(st.load(), fh, ensure_ascii=False, indent=2)
                self.log(f"\n参数已导出：{p}\n")
            except OSError as e:
                try:
                    messagebox.showerror("导出失败", str(e))
                except Exception:  # noqa: BLE001
                    pass

        render()
        refresh_status()
        st.on_change(_on_external_change)  # 订阅：他处改动时本窗口自动刷新
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(6, 8))
        ttk.Button(bar, text="保存（立即生效）", command=do_save).pack(side="left", padx=2)
        ttk.Button(bar, text="恢复默认", command=do_reset).pack(side="left", padx=2)
        ttk.Button(bar, text="导出 JSON", command=do_export).pack(side="left", padx=2)
        ttk.Button(bar, text="变更历史", command=self.show_settings_history).pack(side="left", padx=2)
        ttk.Button(bar, text="导入", command=self.show_import).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right", padx=2)

    def show_settings_history(self):
        """参数变更留痕窗口（v0.6.24）：谁在什么时候、从哪来、改了什么。

        留痕只记**参数键与旧/新值**以及来源标识，**绝不记录导入的全文内容**——
        能回答「这项是谁改的」就够了，不需要把别人的整篇文本留在本地。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import settings as st

        top = tk.Toplevel(self.root)
        top.title("参数变更历史（留痕）")
        top.geometry("900x560")
        ttk.Label(top,
                  text="记录每一笔参数变更的来源与时间；只记参数键与值，不记导入全文。"
                       f"落点：{st.HISTORY_PATH}").pack(anchor="w", padx=8, pady=(6, 2))
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        def refresh():
            box.delete("1.0", "end")
            _ok, msg = st.history_report(200)
            box.insert("end", msg + "\n")
            box.see("end")

        def do_clear():
            if not confirm_risky(
                    top, "清空留痕",
                    "清空全部变更留痕（参数值本身不变，仅删除操作历史记录）。",
                    "此操作不可逆：留痕清空后无法还原；如需保留证据，先在参数"
                    "窗口「导出」当前设置。"):
                return
            st.clear_history()
            refresh()
            self.log("\n参数变更留痕已清空\n")

        refresh()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="刷新", command=refresh).pack(side="left", padx=2)
        ttk.Button(bar, text="清空留痕", command=do_clear).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right", padx=2)

    def show_import(self):
        """导入窗口（v0.6.23）：剪贴板 / 本地文件 / 图片二维码 / 摄像头扫码。

        四种来源统一读到文本区：
          · 剪贴板      —— 按平台自动挑后端，失败给兜底说明；
          · 本地文件    —— 文本文件，受 import.max_bytes 限制；
          · 图片二维码  —— 从 PNG/JPG/BMP 等**图片文件**解码二维码（用户点名能力）；
          · 摄像头扫码  —— 可选，受 qr.camera_timeout 限制，超时即停。

        红线：**导入的内容绝不自动执行**。只有当内容是可识别的设置 JSON 时，
        才提供「载入为参数」按钮，且必须用户二次确认后才写入——不确认就只是查看。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from tkinter import filedialog
        from .native import importio as io_
        from .native import settings as st

        top = tk.Toplevel(self.root)
        top.title("导入（剪贴板 / 本地文件 / 二维码）")
        top.geometry("900x640")
        src = tk.StringVar(value=io_.SRC_CLIPBOARD)
        path = tk.StringVar(value="")
        status = tk.StringVar(value="")
        last = {"text": ""}

        head = ttk.Frame(top, padding=(8, 6))
        head.pack(fill="x")
        ttk.Label(head, text="来源:").pack(side="left")
        for key, label, desc in io_.SOURCES:
            ttk.Radiobutton(head, text=label, value=key, variable=src,
                            command=lambda: _sync()).pack(side="left", padx=4)
        ttk.Label(top, textvariable=status, foreground="#666666").pack(anchor="w", padx=8)

        prow = ttk.Frame(top, padding=(8, 2))
        prow.pack(fill="x")
        ttk.Label(prow, text="路径:").pack(side="left")
        ttk.Entry(prow, textvariable=path).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(prow, text="选择文件", command=lambda: _pick()).pack(side="left", padx=2)

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=6)

        def _sync():
            s = src.get()
            note = dict((k, d) for k, _l, d in io_.SOURCES).get(s, "")
            status.set(note + "（导入内容只校验，绝不自动执行）")
            if s in (io_.SRC_CLIPBOARD, io_.SRC_CAMERA):
                prow.pack_forget()
            else:
                prow.pack(fill="x", padx=8, pady=2)

        def _pick():
            try:
                if src.get() == io_.SRC_QR:
                    f = filedialog.askopenfilename(
                        parent=top, title="选择含二维码的图片",
                        filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                                   ("所有文件", "*.*")])
                else:
                    f = filedialog.askopenfilename(
                        parent=top, title="选择文本文件",
                        filetypes=[("文本", "*.txt *.md *.json *.yaml *.yml *.ini *.conf"),
                                   ("所有文件", "*.*")])
                if f:
                    path.set(f)
            except Exception:  # noqa: BLE001
                pass

        def _show(r, s):
            box.delete("1.0", "end")
            last["text"] = r.text
            last["note"] = r.note
            box.insert("end", f"[{s}] " + ("成功" if r.ok else "失败") + "\n")
            box.insert("end", "-" * 60 + "\n")
            box.insert("end", (r.text if r.ok else r.note) + "\n")
            self.log(f"\n导入（{s}）：{'成功' if r.ok else '失败'}\n")

        _cam_q = queue.Queue()

        def _poll_camera(s):
            """主线程轮询扫码结果（每 100ms 一次），避免在子线程里操作 tkinter。"""
            try:
                r = _cam_q.get_nowait()
            except Exception:  # noqa: BLE001 - queue.Empty
                top.after(100, lambda: _poll_camera(s))
                return
            btn_read.config(state="normal")
            _show(r, s)

        def do_read():
            s = src.get()
            if s == io_.SRC_CAMERA:
                # 扫码最长 qr.camera_timeout 秒，必须在后台跑，否则界面会卡死。
                # 线程只负责把结果放进队列；界面更新一律由主线程轮询完成
                # （tkinter 不允许从工作线程直接碰控件）。
                box.delete("1.0", "end")
                box.insert("end", "正在调用摄像头扫码（后台进行，界面不卡）…\n")
                btn_read.config(state="disabled")
                threading.Thread(target=lambda: _cam_q.put(io_.scan_qr_camera()),
                                 daemon=True).start()
                _poll_camera(s)
                return
            _show(io_.import_from(s, path.get().strip()), s)

        def do_load_as_settings():
            """把导入文本当作设置 JSON 载入——**必须二次确认**，绝不自动执行。"""
            ok, accepted, rejected, hint = io_.parse_settings_json(last["text"])
            if not ok:
                try:
                    messagebox.showinfo("不能载入为参数", hint)
                except Exception:  # noqa: BLE001
                    pass
                return
            detail = "\n".join(f"· {k} = {v}" for k, v in accepted.items())
            if rejected:
                detail += "\n被忽略:\n" + "\n".join(f"· {r}" for r in rejected)
            if not confirm_risky(
                    top, "确认载入为参数",
                    f"{detail}\n\n导入的参数值将写入配置。",
                    "写入前随时可取消；写入后可在参数窗口「导出」备份，"
                    "留痕记录来源（导入内容 / 文件路径）可对照。"):
                return
            # 留痕：记下这批参数是从哪个来源进来的（只记来源标识，不记导入全文）
            s = src.get()
            if s == io_.SRC_QR:
                origin = f"{path.get().strip()}（{last.get('note', '')}）"
            elif s == io_.SRC_FILE:
                origin = path.get().strip()
            elif s == io_.SRC_CAMERA:
                origin = f"camera#{st.get('qr.camera_index', 0)}"
            else:
                origin = "剪贴板"
            results = st.apply_updates(accepted, source=s, origin=origin,
                                       note="由导入内容载入")
            n = sum(1 for _k, okk, _w in results if okk)
            self.log(f"\n由导入内容载入参数：{n} 项（来源: {s}）\n")
            try:
                messagebox.showinfo("已载入", f"{n} 项参数已写入并生效")
            except Exception:  # noqa: BLE001
                pass

        def do_caps():
            box.delete("1.0", "end")
            _ok, msg = io_.importio_report()
            box.insert("end", msg + "\n")

        def do_clear():
            box.delete("1.0", "end")
            last["text"] = ""

        _sync()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        btn_read = ttk.Button(bar, text="读取", command=do_read)
        btn_read.pack(side="left", padx=2)
        ttk.Button(bar, text="载入为参数（需确认）",
                   command=do_load_as_settings).pack(side="left", padx=2)
        ttk.Button(bar, text="导入能力自检", command=do_caps).pack(side="left", padx=2)
        ttk.Button(bar, text="清空", command=do_clear).pack(side="left", padx=2)
        ttk.Button(bar, text="参数/阈值", command=self.show_settings).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right", padx=2)

    def show_update(self):
        """「更新」窗口：**默认只检查**，不做任何改动。

        - 只读体检：版本、git 仓库状态、远端是否有新提交、插件与任务库规模。
        - 本地刷新：重新扫描插件目录、重算任务数（**不改代码**）。
        - 真正的代码更新**只给命令，不代劳**：自动改用户机器上的代码是越权，
          且失败会留下半吊子状态。
        """
        tk, ttk, _, scrolledtext = _tk()
        from . import updater

        top = tk.Toplevel(self.root)
        top.title("更新与检查")
        top.geometry("820x560")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str = ""):
            box.insert("end", text + "\n")
            box.see("end")

        def do_check():
            box.delete("1.0", "end")
            put(updater.render_check())

        def do_refresh():
            put("")
            put("==== 本地刷新（重新扫描插件 / 重算任务数，不改代码）====")
            r = updater.refresh()
            put(f"任务库：{r['tasks']} 项；插件：{r['plugins']} 个")
            for n in r["notes"]:
                put(f"· {n}")
            self.log("\n本地刷新完成\n")

        def do_cmds():
            put("")
            put("==== 真正更新时应执行的命令（本界面不会替你跑）====")
            for c in updater.update_commands():
                put(f"  {c}")

        put("正在检查（只读，不改动任何东西）…")
        top.update_idletasks()
        do_check()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="重新检查", command=do_check).pack(side="left", padx=2)
        ttk.Button(bar, text="本地刷新", command=do_refresh).pack(side="left", padx=2)
        ttk.Button(bar, text="显示更新命令", command=do_cmds).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        ttk.Label(top, text="纪律：界面只做只读检查与本地刷新；改代码 / 拉代码一律由你在终端确认后执行。",
                  foreground="#b00").pack(fill="x", padx=8, pady=(0, 8))
        box.see("1.0")
        return top

    # ---------- 动作 ----------
    def _ctx(self):
        return self.platform_cb.get(), (self.version_var.get().strip() or "0")

    def run(self, apply: bool):
        _, _, messagebox, _ = _tk()
        from .runner import analyze, human, measure_disk

        tasks = self.selected_tasks()
        if not tasks:
            messagebox.showinfo("提示", "请先勾选至少一项任务。")
            return
        yes = self.yes_var.get()
        if apply:
            risky = [t for t in tasks if t.risk != "low" or t.opt_in]
            if risky and not yes:
                if not confirm_risky(
                        top, "确认中/高风险项",
                        f"选中 {len(risky)} 项中/高风险或默认关闭的开关，"
                        "可能改变系统状态。",
                        "执行后可用 report 前后对比、snapshot capture 留迹核对；"
                        "或先勾选「已确认中高风险(--yes)」。"):
                    return
            if not confirm_risky(
                    top, "再次确认",
                    f"将对 {len(tasks)} 项任务执行操作（apply=True）。",
                    "执行前建议先 snapshot capture 建立基线，失败可对照回退。"):
                return
        platform, version = self._ctx()
        before = measure_disk(platform) if apply else None
        results = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            failures = analyze(tasks, platform, apply=apply, yes=yes,
                               risk_limit=self.risk_cb.get(), collector=results)
        self.log(buf.getvalue())
        from . import report as repmod
        after = measure_disk(platform) if apply else None
        self.last_report = repmod.generate(
            platform, version, "clean" if apply else "scan",
            tasks, results, before, after)
        if apply:
            self.log(f"\n执行完成；失败动作数: {failures}\n")
            if before and after:
                freed = after["free"] - before["free"]
                self.log(f"磁盘可用空间变化: {human(max(freed, 0))}"
                         f"（处理后可用 {human(after['free'])}）\n")
        else:
            self.log("\n（分析模式：未修改系统；勾选「真正执行」并确认后才会落地）\n")

        # 扫描流程内嵌基线快照：每次扫描/执行都记录，下次扫描自动展示与上次差异
        try:
            from .native import snapshot as nsnap
            snap = nsnap.capture_snapshot(include_probes=True)
            diff, self._scan_snaps = nsnap.record_scan(self._scan_snaps, snap)
            if diff is not None:
                self.log("\n[扫描快照对比] 与上次扫描的差异：\n")
                self.log(nsnap.format_diff(diff) + "\n")
            else:
                self.log(f"\n[扫描快照] 已记录本次基线（会话内第 {len(self._scan_snaps)} 份，"
                         f"下次扫描将自动对比）。\n")
            self.last_scan_snapshot = snap
        except Exception as e:  # noqa: BLE001
            self.log(f"\n[扫描快照] 记录失败（不影响本次分析）：{e}\n")

    def gen_report(self):
        _, _, messagebox, _ = _tk()
        from . import report as repmod
        from .runner import analyze, measure_disk

        path = self.report_var.get().strip()
        if not path:
            messagebox.showinfo("提示", "请填写报告路径，如 sysweeper-report.md")
            return
        tasks = self.selected_tasks()
        if not tasks:
            messagebox.showinfo("提示", "请先勾选至少一项任务。")
            return
        platform, version = self._ctx()
        before = measure_disk(platform)
        results = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            analyze(tasks, platform, apply=False, yes=False,
                    risk_limit=self.risk_cb.get(), collector=results)
        try:
            rep = repmod.generate(platform, version, "scan", tasks, results, before, None)
            self.last_report = rep
            out = repmod.write_report(path, rep)
            self.log(f"\n报告已生成: {out}（{rep['task_count']} 项任务）\n")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("报告失败", str(e))

    def show_chart(self):
        """弹出前后对比可视化窗口（tkinter Canvas 画条形图，纯标准库）。"""
        tk, ttk, messagebox, _ = _tk()
        from .runner import human
        if not self.last_report:
            messagebox.showinfo("提示", "暂无报告数据。请先「扫描分析」或「生成报告」。")
            return
        rep = self.last_report
        top = tk.Toplevel(self.root)
        top.title("前后对比可视化")
        top.geometry("640x440")
        cv = tk.Canvas(top, width=620, height=420, bg="#ffffff")
        cv.pack(fill="both", expand=True)
        r = chart_rects(rep, width=620, height=420)

        cv.create_text(20, 16, anchor="nw", text="磁盘占用对比", font=("Arial", 12, "bold"))
        for bar in r["disk"]:
            cv.create_rectangle(bar["x"], bar["y"], bar["x"] + bar["w"], bar["y"] + bar["h"],
                                fill="#007aff", outline="")
            cv.create_text(20, bar["y"] + 4, anchor="w", text=bar["label"], fill="#333")
            cv.create_text(bar["x"] + bar["w"] + 8, bar["y"] + bar["h"] / 2,
                           anchor="w", text=f"{int(bar['frac'] * 100)}%", fill="#007aff")
        if r["freed"] is not None:
            cv.create_text(20, 138, anchor="nw", text=f"实际释放：{human(r['freed'])}",
                           fill="#e54d42", font=("Arial", 11, "bold"))

        cv.create_text(20, 168, anchor="nw", text="各任务预计可回收空间",
                       font=("Arial", 12, "bold"))
        for t in r["tasks"]:
            cv.create_rectangle(t["x"], t["y"], t["x"] + t["w"], t["y"] + t["h"],
                                fill="#34c759", outline="")
            cv.create_text(t["x"] + t["w"] / 2, t["y"] - 6, anchor="s",
                           text=human(t["value"]), fill="#2a8f47", font=("Arial", 9))
        if not r["disk"] and not r["tasks"]:
            cv.create_text(20, 210, anchor="nw",
                           text="（无可绘制数据：未执行或无可估算任务）", fill="#999")

    def show_backends(self):
        info = ["GUI 后端可用性（优先用语言自带的）：\n"]
        for b in detect_gui_backends():
            mark = "✓ 可用" if b["available"] else "✗ 不可用"
            info.append(f"  [{mark}] {b['name']} — {b['note']}")
        info.append("\n本界面由 Python 自带 tkinter 绘制，无需额外安装。")
        self.log("\n".join(info) + "\n")

    def show_standards(self):
        """弹出「标准与分类」窗口：分类 → 标准出处（国家/国际/地区三层）→ 覆盖 → 任务。

        标准引用按受众分层展示：国内优先国家标准/国家平台，面向外国用户用国际
        标准，必要时按地区标准执行；opt-in 默认关闭的开关单列一组展示。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .models import (CATEGORY_ORDER, CATEGORIES, category_standards,
                             task_standards_ordered,
                             STANDARD_TIERS, NATIONAL_STANDARD_PORTAL)

        top = tk.Toplevel(self.root)
        top.title("标准与分类（分类规范整体）")
        top.geometry("760x560")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        grouped = registry.tasks_by_category()
        counts = registry.category_summary()
        total = sum(counts.get(c, 0) for c in CATEGORY_ORDER)
        put("=" * 72)
        put(f"分类规范整体：共 {total} 项普通任务 + "
            f"{counts.get('(opt_in)', 0)} 项默认关闭开关（opt-in）")
        put(f"标准引用优先级：国内优先国家平台/国标 → 国际(IEEE/RFC/ISO/ITU…) → 地区")
        put(f"国家平台: {NATIONAL_STANDARD_PORTAL}")
        put("=" * 72)

        for c in CATEGORY_ORDER:
            st = category_standards(c)
            label = CATEGORIES.get(c, c)
            put("")
            put(f"■ {label}（{c}）：{counts.get(c, 0)} 项")
            if st.get("doc"):
                put(f"    标准文档: {st['doc']}")
            # 三层标准：国家(优先) / 国际 / 地区
            tiers = st.get("standards", {})
            tier_tag = {"national": "国标", "international": "国际", "regional": "地区"}
            for tier, _desc in STANDARD_TIERS:
                for s in tiers.get(tier, []):
                    mark = "①" if tier == "national" else " "
                    put(f"    {mark} [{tier_tag.get(tier, tier)}] {s}")
            items = grouped.get(c, [])
            if not items:
                put("    （暂无任务——该分类可补）")
            else:
                for t in items:
                    put(f"    • {t.id:<22} [{t.platform}/{t.risk}]  {t.display_title()}")

        opt = grouped.get("(opt_in)", [])
        put("")
        put("-" * 72)
        put(f"默认关闭的 opt-in 开关：{len(opt)} 项"
            "（网络/ITU 调优，需 --opt-in + --yes）")
        for t in opt:
            put(f"    • {t.id:<22} [{t.platform}/{t.risk}]  {t.display_title()}")
            for s in task_standards_ordered(t, "cn"):
                put(f"        {s}")

        put("")
        put("=" * 72)
        put("说明：分类口径与标准出处见 models.CATEGORY_STANDARDS；"
            "逐分类任务可在 CLI 用 `python -m sysweeper standards` 查看。")
        box.see("1.0")
        return top

    def show_rfc(self):
        """弹出「RFC 知识库」窗口（v0.6.52）：只读浏览主题域 / 工作组(WG) / 单号查询。

        与 CLI `rfc topics / topic / wgs / wg` 口径一致，纯展示、不改动数据。
        三页：
          · 主题域   —— heuristic 13 主题域（按成员数降序），点选看成员 RFC；
          · 工作组   —— IETF area + Top WG（官方第二索引源），点选看成员 RFC；
          · 单号查询 —— 输入编号，同时给 heuristic 主题域归属与官方 WG 归属。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import rfc_catalog as cat

        top = tk.Toplevel(self.root)
        top.title("RFC 知识库（只读）")
        top.geometry("1000x680")

        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=8, pady=6)

        # ---- 页1：主题域（heuristic 层）----
        f_topic = ttk.Frame(nb)
        nb.add(f_topic, text="主题域")
        tl = tk.Listbox(f_topic, width=30)
        tl.pack(side="left", fill="y", padx=(6, 2), pady=6)
        tbox = scrolledtext.ScrolledText(f_topic, wrap="word")
        tbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        tl._data = []

        def _fill_topics():
            tl.delete(0, "end")
            tl._data = cat.topics()
            for d in tl._data:
                tl.insert("end", f"{d['label']}  ({d['count']})")

        def _on_topic(_ev=None):
            sel = tl.curselection()
            if not sel:
                return
            d = tl._data[sel[0]]
            members = cat.topic_members(d["domain"], limit=200)
            tbox.delete("1.0", "end")
            tbox.insert("end", f"主题域：{d['label']}  [{d['domain']}]\n")
            tbox.insert("end", f"规则数：{d['rule_count']}    成员 RFC：{d['count']}"
                        f"（本页最多列 200）\n")
            tbox.insert("end", "-" * 64 + "\n")
            for m in members:
                tbox.insert("end", f"RFC {m['n']}  {m.get('t', '')}\n")
            tbox.see("1.0")

        tl.bind("<<ListboxSelect>>", _on_topic)
        _fill_topics()

        # ---- 页2：工作组 / 研究组（官方第二索引源）----
        f_wg = ttk.Frame(nb)
        nb.add(f_wg, text="工作组(WG)")
        wl = tk.Listbox(f_wg, width=38)
        wl.pack(side="left", fill="y", padx=(6, 2), pady=6)
        wbox = scrolledtext.ScrolledText(f_wg, wrap="word")
        wbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        wl._data = []

        def _fill_wgs():
            wl.delete(0, "end")
            wl._data = []
            w = cat.wgs(100)
            for a in w["areas"]:
                wl.insert("end", f"[area] {a['name']}  ({a['rfc_count']})")
                wl._data.append(("area", a["area"]))
            for g in w["top_wgs"]:
                wl.insert("end", f"{g['name']}  ({g['count']})")
                wl._data.append(("wg", g["wg"]))

        def _on_wg(_ev=None):
            sel = wl.curselection()
            if not sel:
                return
            kind, key = wl._data[sel[0]]
            label = wl.get(sel[0])
            members = cat.wg_members(key, limit=200)
            wbox.delete("1.0", "end")
            wbox.insert("end", f"{label}\n")
            wbox.insert("end", f"成员 RFC：{len(members)}（本页最多列 200）\n")
            wbox.insert("end", "-" * 64 + "\n")
            for m in members:
                wbox.insert("end", f"RFC {m['n']}  {m.get('t', '')}\n")
            wbox.see("1.0")

        wl.bind("<<ListboxSelect>>", _on_wg)
        _fill_wgs()

        # ---- 页3：单号查询（两层归属并陈）----
        f_q = ttk.Frame(nb)
        nb.add(f_q, text="单号查询")
        qrow = ttk.Frame(f_q, padding=(8, 6))
        qrow.pack(fill="x")
        qvar = tk.StringVar(value="")
        ttk.Label(qrow, text="RFC 编号:").pack(side="left")
        ttk.Entry(qrow, textvariable=qvar, width=12).pack(side="left", padx=4)
        qbox = scrolledtext.ScrolledText(f_q, wrap="word")
        qbox.pack(fill="both", expand=True, padx=8, pady=6)

        def _do_query():
            raw = (qvar.get() or "").strip().lstrip("0") or "0"
            try:
                num = int(raw)
            except ValueError:
                qbox.delete("1.0", "end")
                qbox.insert("end", "请输入数字编号。\n")
                return
            e = cat.rfc_info(num)
            qbox.delete("1.0", "end")
            if not e:
                qbox.insert("end", f"RFC {num}：rfc_catalog 查无该编号（或数据缺失）。\n")
                return
            qbox.insert("end", f"RFC {num}\n")
            qbox.insert("end", f"标题：{e.get('t', '')}\n")
            qbox.insert("end", f"状态：{e.get('s', '')}    日期：{e.get('d', '')}\n")
            if e.get("a"):
                qbox.insert("end", f"作者：{e.get('a')}\n")
            if e.get("doi"):
                qbox.insert("end", f"DOI：{e.get('doi')}\n")
            to = cat.topic_of(num)
            qbox.insert("end", "-" * 64 + "\n")
            if to.get("classified"):
                qbox.insert("end", f"主题域(heuristic)：{', '.join(to['domains'])}\n"
                            f"命中规则：{', '.join(to['rules'])}\n")
            else:
                qbox.insert("end", "主题域(heuristic)：未归类（由官方 WG 层或独立投稿兜底）\n")
            wo = cat.wg_of(num)
            if wo.get("wg"):
                qbox.insert("end", f"官方 WG：{wo['wg_name']} [{wo['wg']}]\n"
                            f"类型：{wo['kind']}    area：{wo['area']}    stream：{wo['stream']}\n"
                            f"起草草案：{wo.get('draft')}\n")
            else:
                qbox.insert("end", f"官方 WG：无（kind={wo.get('kind')}，"
                            f"如为 IAB/独立投稿/Legacy 则无 WG 归属）\n")

        ttk.Button(qrow, text="查询", command=_do_query).pack(side="left", padx=4)
        ttk.Button(qrow, text="示例 8446",
                   command=lambda: (qvar.set("8446"), _do_query())).pack(side="left")

        nb.select(0)
        return top

    def show_langref(self):
        """弹出「编程语言库」窗口（v0.6.54）：只读浏览语言知识库。

        与 CLI `langref` 口径一致，纯展示、不改动数据。三页：
          · 窗口内   —— 2008–2026 首现语言（按年降序），点选看单条详情；
          · 分类/来源 —— 按分类（compiled/jit/…）或来源（国外/国内/国际）筛选成员；
          · 检索     —— 关键词检索，另有「待核实」按钮列出 needs_verify 条目。
        存疑条目在详情里以「待核实：」原样标出（诚实边界，不臆造）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import langs as lg

        top = tk.Toplevel(self.root)
        top.title("编程语言库（只读）")
        top.geometry("1000x680")

        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=8, pady=6)

        def _detail(e):
            """把单条语言格式化为详情文本（含 needs_verify 诚实标注）。"""
            lines = [
                f"{e['name']}（{e['name_zh']}）",
                # first_release 已含年份与沿革，分开写避免「1993（1993…）」重复
                f"首现年：{e['first_year']}",
                f"发布沿革：{e['first_release']}",
                f"范式：{', '.join(e['paradigms'])}",
                f"类型系统：{e['type_system']}",
                f"实现：{e['implementation']}",
                f"设计者：{e['designer']}（{e['origin']} / {e['region']}）",
                f"状态：{e['status']}    分类：{e['category']}"
                f"    窗口内：{e['in_window']}",
                f"标准：{e['standard']}",
                "-" * 64,
                f"备注：{e['notes']}",
            ]
            if e.get("needs_verify"):
                lines.append("⚠ 待核实：" + "；".join(e["needs_verify"]))
            return "\n".join(lines) + "\n"

        # ---- 页1：窗口内（2008–2026）----
        f_win = ttk.Frame(nb)
        nb.add(f_win, text="窗口内(2008–2026)")
        wlb = tk.Listbox(f_win, width=34)
        wlb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        wbox = scrolledtext.ScrolledText(f_win, wrap="word")
        wbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        wlb._data = []
        for e in lg.window(only=True):
            wlb.insert("end", f"{e['first_year']}  {e['name']}")
            wlb._data.append(e)

        def _on_win(_ev=None):
            sel = wlb.curselection()
            if not sel:
                return
            wbox.delete("1.0", "end")
            wbox.insert("end", _detail(wlb._data[sel[0]]))
            wbox.see("1.0")

        wlb.bind("<<ListboxSelect>>", _on_win)

        # ---- 页2：分类 / 来源 ----
        f_cat = ttk.Frame(nb)
        nb.add(f_cat, text="分类/来源")
        crow = ttk.Frame(f_cat, padding=(8, 6))
        crow.pack(fill="x")
        cats = sorted(lg.info().get("categories", []))
        origins = sorted(lg.info().get("origin_values", []))
        cat_v = tk.StringVar(value="compiled")
        org_v = tk.StringVar(value="国外")
        ttk.Label(crow, text="分类:").pack(side="left")
        ttk.Combobox(crow, textvariable=cat_v, values=cats, width=16,
                     state="readonly").pack(side="left", padx=2)
        ttk.Button(crow, text="按分类列出",
                   command=lambda: _fill(cat=True)).pack(side="left", padx=4)
        ttk.Label(crow, text="来源:").pack(side="left", padx=(12, 0))
        ttk.Combobox(crow, textvariable=org_v, values=origins, width=8,
                     state="readonly").pack(side="left", padx=2)
        ttk.Button(crow, text="按来源列出",
                   command=lambda: _fill(cat=False)).pack(side="left", padx=4)
        clb = tk.Listbox(f_cat, width=34)
        clb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        cbox = scrolledtext.ScrolledText(f_cat, wrap="word")
        cbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        clb._data = []

        def _fill(cat=True):
            es = lg.by_category(cat_v.get()) if cat else lg.by_origin(org_v.get())
            clb.delete(0, "end")
            clb._data = list(es)
            for e in es:
                clb.insert("end", f"{e['first_year']}  {e['name']}")
            cbox.delete("1.0", "end")
            cbox.insert("end", f"{'分类' if cat else '来源'} "
                        f"{cat_v.get() if cat else org_v.get()}：{len(es)} 条\n")

        def _on_cat(_ev=None):
            sel = clb.curselection()
            if not sel:
                return
            cbox.delete("1.0", "end")
            cbox.insert("end", _detail(clb._data[sel[0]]))
            cbox.see("1.0")

        clb.bind("<<ListboxSelect>>", _on_cat)
        _fill(cat=True)

        # ---- 页3：检索 / 待核实 ----
        f_s = ttk.Frame(nb)
        nb.add(f_s, text="检索/待核实")
        srow = ttk.Frame(f_s, padding=(8, 6))
        srow.pack(fill="x")
        sv = tk.StringVar(value="")
        ttk.Label(srow, text="关键词:").pack(side="left")
        ttk.Entry(srow, textvariable=sv, width=18).pack(side="left", padx=4)
        slb = tk.Listbox(f_s, width=34)
        slb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        sbox = scrolledtext.ScrolledText(f_s, wrap="word")
        sbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        slb._data = []

        def _do_search():
            q = (sv.get() or "").strip()
            es = lg.search(q) if q else []
            slb.delete(0, "end")
            slb._data = list(es)
            for e in es:
                slb.insert("end", f"{e['first_year']}  {e['name']}")
            sbox.delete("1.0", "end")
            sbox.insert("end", f"检索 {q!r}：{len(es)} 条\n")

        def _do_verify():
            es = lg.needs_verify()
            slb.delete(0, "end")
            slb._data = list(es)
            for e in es:
                slb.insert("end", f"{e['first_year']}  {e['name']}")
            sbox.delete("1.0", "end")
            sbox.insert("end", f"待核实(needs_verify)：{len(es)} 条"
                        "（以各语言官网为准）\n")

        def _on_s(_ev=None):
            sel = slb.curselection()
            if not sel:
                return
            sbox.delete("1.0", "end")
            sbox.insert("end", _detail(slb._data[sel[0]]))
            sbox.see("1.0")

        slb.bind("<<ListboxSelect>>", _on_s)
        ttk.Button(srow, text="检索", command=_do_search).pack(side="left", padx=4)
        ttk.Button(srow, text="待核实",
                   command=_do_verify).pack(side="left", padx=4)
        ttk.Button(srow, text="示例 rust",
                   command=lambda: (sv.set("rust"), _do_search())).pack(side="left")

        nb.select(0)
        return top

    def show_daoxue(self):
        """弹出「道枢」治理层概念系统窗口（v0.6.58）：只读浏览，与 CLI `daoxue` 同口径。

        四页：
          · 道德经中心 —— 81 章（章旨/节旨/归属治理原则及其工程落法）；
          · 早晚坛功课 —— 前置(早坛)/后置(晚坛) 的节次与课程序位（净坛→…→结行）；
          · 原则·桥接   —— 15 条工程治理原则与到 plang/netsys/langref 的桥接；
                            另有关键词检索与「待核实」诚实边界清单；
          · 方术子层   —— 符/箓/咒/法/由 五域（tier=3，与治理层「理—用」相对）；
                            只登记文献形制与仪轨结构，不录符图咒文、不主张效力。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .concepts import daoxue as dx

        top = tk.Toplevel(self.root)
        top.title("道枢·治理层概念系统（只读）")
        top.geometry("1000x680")

        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=8, pady=6)

        # ---- 页1：道德经中心（81 章）----
        f_c = ttk.Frame(nb)
        nb.add(f_c, text="道德经中心")
        clb = tk.Listbox(f_c, width=30)
        clb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        cbox = scrolledtext.ScrolledText(f_c, wrap="word")
        cbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        clb._data = []
        for ch in dx.chapters():
            clb.insert("end", f"{ch['no']:>2}  {ch['theme']}")
            clb._data.append(ch)

        def _ch_detail(c):
            p = dx.principle(c["principle"]) or {}
            lines = [
                f"第{c['no']}章（{c['part']}）",
                f"章旨：{c['theme']}",
                f"节旨：{c['gist']}",
                "-" * 60,
                f"治理原则：{p.get('name','')}（{c['principle']}）",
                f"  义理：{p.get('gist','')}",
                f"  工程落法：{p.get('engineering','')}",
                f"  经典依据：{', '.join(p.get('canon_refs', []))}",
            ]
            return "\n".join(lines) + "\n"

        def _on_ch(_ev=None):
            sel = clb.curselection()
            if not sel:
                return
            cbox.delete("1.0", "end")
            cbox.insert("end", _ch_detail(clb._data[sel[0]]))
            cbox.see("1.0")

        clb.bind("<<ListboxSelect>>", _on_ch)

        # ---- 页2：早晚坛功课（前置 / 后置）----
        f_o = ttk.Frame(nb)
        nb.add(f_o, text="早坛/晚坛")
        orow = ttk.Frame(f_o, padding=(8, 6))
        orow.pack(fill="x")
        role_v = tk.StringVar(value="pre")
        phase_v = tk.StringVar(value="全部")
        ttk.Label(orow, text="功课:").pack(side="left")
        ttk.Combobox(orow, textvariable=role_v, values=["pre", "post"], width=8,
                     state="readonly").pack(side="left", padx=2)
        ttk.Label(orow, text="序位:").pack(side="left", padx=(12, 0))
        ttk.Combobox(orow, textvariable=phase_v, values=["全部"], width=10,
                     state="readonly").pack(side="left", padx=2)
        olb = tk.Listbox(f_o, width=30)
        olb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        obox = scrolledtext.ScrolledText(f_o, wrap="word")
        obox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        olb._data = []

        def _fill_office():
            role = role_v.get() or "pre"
            ph = phase_v.get() or "全部"
            secs = (dx.sections_of(role) if ph == "全部"
                    else dx.sections_of(role, ph))
            olb.delete(0, "end")
            olb._data = list(secs)
            for s in secs:
                olb.insert("end", f"{s['idx']:>2}  {s['name']}")
            o = dx.office(role)
            obox.delete("1.0", "end")
            obox.insert("end",
                        f"{o.get('canon','')}（{'前置' if role=='pre' else '后置'}）："
                        f"{len(secs)} 节\n"
                        f"课义：{o.get('sense','')}\n"
                        f"工程映射：{o.get('engineering','')}\n")

        def _on_o(_ev=None):
            sel = olb.curselection()
            if not sel:
                return
            s = olb._data[sel[0]]
            obox.delete("1.0", "end")
            obox.insert("end",
                        f"{s['name']}（{s['phase']} / {s['kind']}）\n"
                        f"节旨：{s['gist']}\n")

        olb.bind("<<ListboxSelect>>", _on_o)
        ttk.Button(orow, text="列出", command=_fill_office).pack(side="left", padx=4)
        _fill_office()

        # ---- 页3：治理原则 / 桥接 / 检索 ----
        f_p = ttk.Frame(nb)
        nb.add(f_p, text="原则/桥接")
        prow = ttk.Frame(f_p, padding=(8, 6))
        prow.pack(fill="x")
        pv = tk.StringVar(value="")
        ttk.Label(prow, text="关键词:").pack(side="left")
        ttk.Entry(prow, textvariable=pv, width=16).pack(side="left", padx=4)
        plb = tk.Listbox(f_p, width=30)
        plb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        pbox = scrolledtext.ScrolledText(f_p, wrap="word")
        pbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        plb._data = []

        def _p_detail(p):
            lines = [
                f"{p['name']}（{p['id']}）",
                f"经典依据：{', '.join(p.get('canon_refs', []))}",
                f"义理：{p['gist']}",
                f"工程落法：{p['engineering']}",
                "-" * 60,
                "桥接到既有概念系统：",
            ]
            for b in dx.bridges():
                if b["principle"] == p["id"]:
                    lines.append(f"  · {b['system']}:{b['target']} [{b['relation']}]")
                    lines.append(f"      {b['how']}")
            return "\n".join(lines) + "\n"

        def _fill_principles():
            plb.delete(0, "end")
            plb._data = list(dx.principles())
            for p in plb._data:
                plb.insert("end", p["name"])
            pbox.delete("1.0", "end")
            pbox.insert("end", f"治理原则 {len(plb._data)} 条（由理念落成，可审计）\n")

        def _do_search():
            q = (pv.get() or "").strip()
            hits = dx.search(q) if q else []
            plb.delete(0, "end")
            plb._data = list(hits)
            for h in hits:
                plb.insert("end", f"{h['where']} {h['name']}")
            pbox.delete("1.0", "end")
            pbox.insert("end", f"检索 {q!r}：{len(hits)} 条\n")

        def _do_verify():
            vs = dx.needs_verify()
            plb.delete(0, "end")
            plb._data = list(vs)
            for v in vs:
                plb.insert("end", v["item"])
            pbox.delete("1.0", "end")
            pbox.insert("end", f"诚实边界（需核实）：{len(vs)} 项\n")

        def _on_p(_ev=None):
            sel = plb.curselection()
            if not sel:
                return
            item = plb._data[sel[0]]
            pbox.delete("1.0", "end")
            if isinstance(item, dict) and "id" in item:
                pbox.insert("end", _p_detail(item))
            else:
                pbox.insert("end", f"{item.get('item','')}：{item.get('why','')}\n"
                            if isinstance(item, dict) else "")

        plb.bind("<<ListboxSelect>>", _on_p)
        ttk.Button(prow, text="检索", command=_do_search).pack(side="left", padx=4)
        ttk.Button(prow, text="待核实",
                   command=_do_verify).pack(side="left", padx=4)
        ttk.Button(prow, text="原则", command=_fill_principles).pack(side="left")
        _fill_principles()

        # ---- 页4：方术子层（符/箓/咒/法/由，tier=3）----
        f_f = ttk.Frame(nb)
        nb.add(f_f, text="方术子层")
        fdoms = dx.fangshu_domains()
        # 检索行：实时过滤方术列表（联动 fangshu_search）
        frow = ttk.Frame(f_f, padding=(6, 4))
        frow.pack(fill="x")
        ttk.Label(frow, text="检索:").pack(side="left")
        fq = tk.StringVar(value="")
        fent = ttk.Entry(frow, textvariable=fq, width=20)
        fent.pack(side="left", padx=4)
        # 主体：列表 + 详情（独立 body 帧，避免与检索行在同一行并排）
        fbody = ttk.Frame(f_f)
        fbody.pack(fill="both", expand=True)
        flb = tk.Listbox(fbody, width=36)
        flb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        fbox = scrolledtext.ScrolledText(fbody, wrap="word")
        fbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        flb._data = []

        def _f_detail(x):
            p = dx.principle(x.get("principle", "")) or {}
            lines = [
                f"{x['name']}（{x['id']}）",
                f"所属域：{x.get('domain', '')}",
                f"纲宗：{x['gist']}",
                f"详述：{x.get('detail', '')}",
                "-" * 60,
                f"工程落法：{x.get('engineering', '')}",
                f"归属治理原则：{p.get('name', '')}（{x.get('principle', '')}）",
            ]
            if x.get("needs_verify"):
                lines.append("-" * 60)
                lines.append(f"[待核实] {x['needs_verify']}")
            bs = [b for b in dx.fangshu_bridges() if b.get("fangshu") == x["id"]]
            if bs:
                lines.append("-" * 60)
                lines.append("桥接到既有概念系统：")
                for b in bs:
                    lines.append(f"  · {b['system']}:{b['target']} [{b['relation']}]")
                    lines.append(f"      {b['how']}")
            return "\n".join(lines) + "\n"

        def _fill_f(q=""):
            q = (q or "").strip()
            items = dx.fangshu_search(q) if q else dx.fangshu_items()
            flb.delete(0, "end")
            flb._data = list(items)
            for x in items:
                flb.insert("end", f"[{x['domain']}] {x['name']}"
                           + ("  [存疑]" if x.get("needs_verify") else ""))
            fbox.delete("1.0", "end")
            fbox.insert("end",
                        "方术子层（tier=3：符箓·咒语·画符仪轨·祝由）："
                        f"{len(items)} 条"
                        + (f"（检索 {q!r}）" if q else "")
                        + "\n"
                        + "；".join(f"{d['domain']} {d['count']}" for d in fdoms)
                        + "\n只登记文献形制与仪轨结构；不录符图咒文、不主张效力。\n")

        def _on_f(_ev=None):
            sel = flb.curselection()
            if not sel:
                return
            fbox.delete("1.0", "end")
            fbox.insert("end", _f_detail(flb._data[sel[0]]))
            fbox.see("1.0")

        def _on_fsearch(_ev=None):
            _fill_f(fq.get())

        flb.bind("<<ListboxSelect>>", _on_f)
        fent.bind("<KeyRelease>", _on_fsearch)
        _fill_f()

        nb.select(0)
        return top

    # ---------------- v0.6.59：轴型概念系统通用窗口（quantum/comp/apilab）--------- #
    def _axis_concept_window(self, mod, sysname, title, extra_tab=None):
        """轴型概念系统通用面板：分类轴浏览 / 桥接边 / 检索与诚实边界。

        ``extra_tab(nb)`` 可追加系统特有页（quantum=标准登记册，comp=语言编译需要，
        apilab=仓库接口面实测 + RFC）。与 CLI ``<系统>`` 子命令同口径，只读。
        """
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title(f"{title}（只读）")
        top.geometry("1000x680")
        nb = ttk.Notebook(top)
        nb.pack(fill="both", expand=True, padx=8, pady=6)

        # ---- 页1：分类轴浏览 ----
        f_d = ttk.Frame(nb)
        nb.add(f_d, text="分类轴")
        drow = ttk.Frame(f_d, padding=(8, 6))
        drow.pack(fill="x")
        doms = mod.domains()
        ttk.Label(drow, text="轴:").pack(side="left")
        dom_v = tk.StringVar(value=doms[0]["domain"] if doms else "")
        ttk.Combobox(drow, textvariable=dom_v, state="readonly", width=14,
                     values=[d["domain"] for d in doms]).pack(side="left", padx=4)
        dlb = tk.Listbox(f_d, width=32)
        dlb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        dbox = scrolledtext.ScrolledText(f_d, wrap="word")
        dbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        dlb._data = []

        def _concept_detail(c):
            lines = [
                f"{c['name']}（{c['id']}）",
                f"所属轴：{c.get('domain', '')}",
                f"纲宗：{c['gist']}",
                f"详述：{c.get('detail', '')}",
            ]
            for s in c.get("standards", []):
                if isinstance(s, dict):
                    ref = f"{s.get('kind', '')} {s.get('num', '')}".strip()
                    lines.append(f"标准依据：{ref}  "
                                 f"{s.get('rfc_title', '') or s.get('name', '')}")
                else:
                    lines.append(f"标准依据：{s}")
            ev = c.get("evidence")
            if ev:
                lines.append("-" * 60)
                lines.append(f"实测证据：{ev.get('source', '')} "
                             f"[{ev.get('status', '')} rc={ev.get('returncode', '?')}]")
                for k, v in (ev.get("contract_kv") or {}).items():
                    lines.append(f"  {k} = {v}")
            if c.get("needs_verify"):
                lines.append(f"诚实边界：{c['needs_verify']}")
            bs = mod.bridges_of(c["id"])
            if bs:
                lines.append("-" * 60)
                lines.append("桥接到既有概念系统：")
                for b in bs:
                    lines.append(f"  · {b['system']}:{b['target']} [{b['relation']}]")
                    lines.append(f"      {b['how']}")
            return "\n".join(lines) + "\n"

        def _fill_domain(_ev=None):
            name = dom_v.get()
            cs = mod.concepts_of_domain(name)
            dlb.delete(0, "end")
            dlb._data = list(cs)
            for c in cs:
                dlb.insert("end", f"{c['id']:<24} {c['name']}")
            d = mod.domain(name) or {}
            dbox.delete("1.0", "end")
            dbox.insert("end",
                        f"轴 {name}（{d.get('label', '')}）：{len(cs)} 个概念\n"
                        f"{d.get('note', '')}\n")

        def _on_d(_ev=None):
            sel = dlb.curselection()
            if not sel:
                return
            dbox.delete("1.0", "end")
            dbox.insert("end", _concept_detail(dlb._data[sel[0]]))
            dbox.see("1.0")

        dlb.bind("<<ListboxSelect>>", _on_d)
        ttk.Button(drow, text="列出", command=_fill_domain).pack(side="left", padx=4)
        _fill_domain()

        # ---- 页2：桥接边 ----
        f_b = ttk.Frame(nb)
        nb.add(f_b, text="桥接")
        brow = ttk.Frame(f_b, padding=(8, 6))
        brow.pack(fill="x")
        sys_v = tk.StringVar(value="全部")
        ttk.Label(brow, text="目标系统:").pack(side="left")
        ttk.Combobox(brow, textvariable=sys_v, width=12, state="readonly",
                     values=["全部"]).pack(side="left", padx=4)
        blb = tk.Listbox(f_b, width=40)
        blb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        bbox = scrolledtext.ScrolledText(f_b, wrap="word")
        bbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        blb._data = []

        def _fill_bridges():
            sysname_v = sys_v.get()
            bs = mod.bridges("" if sysname_v == "全部" else sysname_v)
            blb.delete(0, "end")
            blb._data = list(bs)
            for b in bs:
                blb.insert("end", f"{b.get('from', '?')} → {b['system']}:{b['target']}")
            bbox.delete("1.0", "end")
            bbox.insert("end", f"桥接边 {len(bs)} 条（构建期校验目标真实存在，无悬空）\n")

        def _on_b(_ev=None):
            sel = blb.curselection()
            if not sel:
                return
            b = blb._data[sel[0]]
            bbox.delete("1.0", "end")
            bbox.insert("end",
                        f"{b.get('from', '?')} → {b['system']}:{b['target']}\n"
                        f"关系：{b['relation']}\n{b['how']}\n")

        blb.bind("<<ListboxSelect>>", _on_b)
        ttk.Button(brow, text="列出", command=_fill_bridges).pack(side="left", padx=4)
        _fill_bridges()

        # ---- 页3：检索 / 诚实边界 ----
        f_s = ttk.Frame(nb)
        nb.add(f_s, text="检索/待核实")
        srow = ttk.Frame(f_s, padding=(8, 6))
        srow.pack(fill="x")
        qv = tk.StringVar(value="")
        ttk.Label(srow, text="关键词:").pack(side="left")
        sq = ttk.Entry(srow, textvariable=qv, width=18)
        sq.pack(side="left", padx=4)
        slb = tk.Listbox(f_s, width=36)
        slb.pack(side="left", fill="y", padx=(6, 2), pady=6)
        sbox = scrolledtext.ScrolledText(f_s, wrap="word")
        sbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        slb._data = []

        def _do_search():
            q = (qv.get() or "").strip()
            hits = mod.search(q) if q else []
            slb.delete(0, "end")
            slb._data = list(hits)
            for h in hits:
                slb.insert("end", f"[{h['where']}] {h['name']}")
            sbox.delete("1.0", "end")
            sbox.insert("end", f"检索 {q!r}：{len(hits)} 条\n")

        # 实时检索：每次按键即过滤（与 daoxue 方术页同范式）
        sq.bind("<KeyRelease>", lambda _e=None: _do_search())

        def _do_verify():
            vs = mod.needs_verify()
            slb.delete(0, "end")
            slb._data = list(vs)
            for v in vs:
                slb.insert("end", v.get("item", ""))
            sbox.delete("1.0", "end")
            sbox.insert("end", f"诚实边界（需核实）：{len(vs)} 项\n")
            for v in vs:
                sbox.insert("end", f"  - {v.get('item', '')}：{_nv_note(v)}\n")

        def _on_s(_ev=None):
            sel = slb.curselection()
            if not sel:
                return
            item = slb._data[sel[0]]
            sbox.delete("1.0", "end")
            if isinstance(item, dict) and "name" in item and "gist" in item:
                sbox.insert("end", _concept_detail(item))
            else:
                sbox.insert("end", f"{item.get('item', '')}：{_nv_note(item)}\n")

        slb.bind("<<ListboxSelect>>", _on_s)
        ttk.Button(srow, text="检索", command=_do_search).pack(side="left", padx=4)
        ttk.Button(srow, text="待核实", command=_do_verify).pack(side="left")

        if extra_tab is not None:
            try:
                extra_tab(nb)
            except Exception as exc:  # pragma: no cover - 附加页失败不拖垮主面板
                self.log(f"\n[{sysname}] 附加页加载失败: {exc}\n")

        nb.select(0)
        return top

    def show_quantum(self):
        """弹出「量子理念」概念系统窗口（v0.6.65）：只读浏览，与 CLI `quantum` 同口径。

        四页：分类轴八域（态/线路/算法/硬件/纠错/网络/工具链/经典模拟与语义）/
        桥接边 / 检索与待核实 / 标准登记册（verified 与 needs_verify 逐条标注）。
        本仓库为经典系统工程工具箱：不含量子硬件探针，只做理念与标准登记
        （qsim 域为经典模拟器，O(2ⁿ) 墙内 ≤6 比特）。
        """
        from .concepts import quantum as qm
        tk, ttk, messagebox, scrolledtext = _tk()

        def _std_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="标准登记册")
            row = ttk.Frame(f, padding=(8, 6))
            row.pack(fill="x")
            slb = tk.Listbox(f, width=34)
            slb.pack(side="left", fill="y", padx=(6, 2), pady=6)
            sbox = scrolledtext.ScrolledText(f, wrap="word")
            sbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
            slb._data = []
            stds = qm.standards()

            def _fill():
                slb.delete(0, "end")
                slb._data = list(stds)
                for s in stds:
                    slb.insert("end", f"[{s['status']}] {s['name']}")
                sbox.delete("1.0", "end")
                sbox.insert("end",
                            f"标准登记 {len(stds)} 条（verified=本轮核实 / "
                            f"needs_verify=待核实，不臆造发布状态）\n")

            def _on(_ev=None):
                sel = slb.curselection()
                if not sel:
                    return
                s = slb._data[sel[0]]
                sbox.delete("1.0", "end")
                sbox.insert("end",
                            f"{s['name']}（{s['id']}）\n"
                            f"类别：{s.get('kind', '')}\n"
                            f"状态：{s['status']}\n"
                            f"说明：{s.get('note', '')}\n"
                            f"来源：{s.get('source', '')}\n"
                            + (f"待核实原因：{s.get('reason', '')}\n"
                               if s.get('reason') else ""))

            slb.bind("<<ListboxSelect>>", _on)
            ttk.Button(row, text="列出", command=_fill).pack(side="left", padx=4)
            _fill()

        return self._axis_concept_window(qm, "quantum", "量子理念概念系统", _std_tab)

    def show_quantum_vm(self):
        """弹出「量子虚拟机」窗口（v0.6.68 新增）：真能跑的量子程序模拟 + 架构基座演示。

        三块能力：
          · 内置程序（bell/ghz/teleport/grover2q/bv2/superposition）：选程序 + 枪数 + 种子 → 运行
          · 自定义 IR：文本框写文本量子程序 → 解析运行（非法程序报错并列有效语法）
          · 架构基座演示：CPU ↔ 闪存链路 ↔ 量子核 不间断交换
            （enc 数字转换门 / tan·ctan 返回交互 / 圆周率链路缓冲）
        红线：纯软件模拟——不联网、不接量子硬件/云量子服务，只读 taxonomy 作参考。
        """
        from .native import quantum as qmod
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title("量子虚拟机（量子程序模拟 + 架构基座）")
        top.geometry("980x700")

        box = scrolledtext.ScrolledText(top, wrap="word")

        # ── 内置程序区 ──
        row1 = ttk.Frame(top)
        row1.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Label(row1, text="内置程序:").pack(side="left")
        prog_var = tk.StringVar(value="bell")
        ttk.Combobox(row1, textvariable=prog_var, width=14,
                     values=sorted(qmod.BUILTIN_PROGRAMS),
                     state="readonly").pack(side="left", padx=4)
        ttk.Label(row1, text="枪数:").pack(side="left")
        shots_var = tk.StringVar(value="1024")
        ttk.Entry(row1, textvariable=shots_var, width=8).pack(side="left", padx=2)
        ttk.Label(row1, text="种子:").pack(side="left")
        seed_var = tk.StringVar(value="")
        ttk.Entry(row1, textvariable=seed_var, width=8).pack(side="left", padx=2)

        def _seed():
            txt = seed_var.get().strip()
            return int(txt) if txt else None

        def run_builtin():
            put("")
            put(f"==== 内置程序 {prog_var.get()} ====")
            try:
                res = qmod.run_named(prog_var.get(),
                                     shots=int(shots_var.get()), seed=_seed())
                put(res["program"])
                put(f"shots={res['shots']} seed={res['seed']}")
                for k, v in res["counts"].items():
                    put(f"  {k}: {v}  (P={res['probabilities'][k]:.4f})")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
                messagebox.showerror("量子虚拟机", str(e))

        ttk.Button(row1, text="运行", command=run_builtin).pack(side="left", padx=4)

        def run_arch():
            put("")
            put("==== 架构基座演示（CPU ↔ 闪存链路 ↔ 量子核 不间断交换）====")
            try:
                m = qmod.QuantumMachine(n_qubits=4, link_ratio=2.0, seed=7)
                m.define_pin("led", 0)
                m.load("qubits 4\nenc 5\nh 0\ncx 0 1\nmeasure 0 -> 0\nif 0 x 2\nhalt")
                for r in m.run_until_halt():
                    put(f"  step {r['pc']}: {r}")
                put(f"CPU: {m.cpu} | pin led={m.read_pin('led')} | "
                    f"next_angle(tan)={m.next_angle:.6f}")
                put(f"链路统计: {m.link.stats()}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
                messagebox.showerror("量子虚拟机", str(e))

        ttk.Button(row1, text="架构演示", command=run_arch).pack(side="left", padx=2)

        # ── 自定义 IR 区 ──
        ttk.Label(top, text="自定义量子程序（文本 IR；语法：qubits N / h 0 / cx 0 1 / "
                            "ry pi/4 0 / enc 5 / measure 0 -> 0 / if 0 x 2 / halt）"
                  ).pack(anchor="w", padx=8, pady=(8, 2))
        ir = scrolledtext.ScrolledText(top, wrap="word", height=9)
        ir.pack(fill="both", padx=8, pady=(0, 6))
        ir.insert("end", "qubits 3\nh 0\ncx 0 1\ncx 1 2\n"
                         "measure 0 -> 0\nmeasure 1 -> 1\nmeasure 2 -> 2\nhalt")

        def run_custom():
            put("")
            put("==== 自定义程序 ====")
            try:
                res = qmod.run_program(ir.get("1.0", "end"),
                                       shots=int(shots_var.get()), seed=_seed())
                put(res["program"])
                for k, v in res["counts"].items():
                    put(f"  {k}: {v}  (P={res['probabilities'][k]:.4f})")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
                messagebox.showerror("量子虚拟机", str(e))

        ttk.Button(top, text="运行自定义程序",
                   command=run_custom).pack(anchor="w", padx=8)

        # ── 输出区（最后 pack，占满剩余空间） ──
        def put(text: str = ""):
            box.insert("end", str(text) + "\n")
            box.see("end")

        box.pack(fill="both", expand=True, padx=8, pady=(6, 8))
        put("量子虚拟机就绪：纯标准库态矢量模拟（零依赖、不联网、不接量子硬件）。")
        put("门集：" + " ".join(sorted(qmod.GATES)))
        put("指令：qubits/classical/enc/measure/reset/barrier/halt/if/xd/zd")
        put("架构基座：enc 数字转换门 · CPU↔闪存不间断交换 · tan/ctan 返回交互 · 圆周率链路缓冲")
        try:
            self.log("\n量子虚拟机：面板已打开\n")
        except Exception:  # noqa: BLE001 —— 日志框缺失不阻断面板（GUI 降级）
            pass
        return top

    def show_comp(self):
        """弹出「编译与工具链」概念系统窗口（v0.6.59）：只读浏览，与 CLI `comp` 同口径。

        四页：分类轴五轴（流水线/工具链/构建/产物/语言编译需要）/ 桥接边 /
        检索与待核实 / 语言编译需要（plang probe 实测通过的 15 种逐条带证据，
        其余 146 种汇总 needs_verify）。
        """
        from .concepts import comp as cp
        tk, ttk, messagebox, scrolledtext = _tk()

        def _need_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="语言编译需要")
            row = ttk.Frame(f, padding=(8, 6))
            row.pack(fill="x")
            nlb = tk.Listbox(f, width=26)
            nlb.pack(side="left", fill="y", padx=(6, 2), pady=6)
            nbox = scrolledtext.ScrolledText(f, wrap="word")
            nbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
            nlb._data = []
            needs = cp.verified_lang_needs()

            def _fill():
                nlb.delete(0, "end")
                nlb._data = list(needs)
                for c in needs:
                    nlb.insert("end", f"{c.get('lang', c['id']):<14} {c.get('artifact', '')}")
                nbox.delete("1.0", "end")
                nbox.insert("end",
                            f"实测通过的 {len(needs)} 种语言（证据取自 "
                            f"plang probe_results）\n")

            def _on(_ev=None):
                sel = nlb.curselection()
                if not sel:
                    return
                c = nlb._data[sel[0]]
                ev = c.get("evidence") or {}
                nbox.delete("1.0", "end")
                nbox.insert("end",
                            f"{c.get('lang', c['id'])}（{c['id']}）\n"
                            f"驱动：{c.get('driver', '')}\n"
                            f"产物：{c.get('artifact', '')}\n"
                            f"说明：{c.get('detail', '')}\n"
                            f"证据：{ev.get('source', '')} "
                            f"[{ev.get('status', '')} rc={ev.get('returncode', '?')}]\n")
                for k, v in (ev.get("contract_kv") or {}).items():
                    nbox.insert("end", f"  {k} = {v}\n")

            nlb.bind("<<ListboxSelect>>", _on)
            ttk.Button(row, text="列出", command=_fill).pack(side="left", padx=4)
            _fill()

        return self._axis_concept_window(cp, "comp", "编译与工具链概念系统", _need_tab)

    def show_apilab(self):
        """弹出「接口 API」概念系统窗口（v0.6.59）：只读浏览，与 CLI `apilab` 同口径。

        五页：分类轴五轴（风格/规约/传输/认证/仓库接口面）/ 桥接边 /
        检索与待核实 / 仓库接口面实测（103 CLI 子命令、29 webapi ACTIONS 等，
        构建时从源码读出）/ RFC 依据（经 rfc_catalog 交叉验证）。
        """
        from .concepts import apilab as ab
        tk, ttk, messagebox, scrolledtext = _tk()

        def _repo_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="仓库接口面")
            rbox = scrolledtext.ScrolledText(f, wrap="word")
            rbox.pack(fill="both", expand=True, padx=8, pady=8)
            facts = ab.repo_facts()
            rbox.insert("end", "本仓库接口面（构建时实测；数字随代码演进，"
                               "漂移时以 build_apilab.py --check 检出）\n\n")
            for k, v in facts.items():
                rbox.insert("end", f"{k}:\n    {v}\n\n")

        def _rfc_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="RFC 依据")
            row = ttk.Frame(f, padding=(8, 6))
            row.pack(fill="x")
            rlb = tk.Listbox(f, width=30)
            rlb.pack(side="left", fill="y", padx=(6, 2), pady=6)
            rbox = scrolledtext.ScrolledText(f, wrap="word")
            rbox.pack(side="left", fill="both", expand=True, padx=2, pady=6)
            rlb._data = []
            stds = [s for s in ab.standards() if s.get("kind") == "RFC"]

            def _fill():
                rlb.delete(0, "end")
                rlb._data = list(stds)
                for s in stds:
                    rlb.insert("end", f"RFC {s.get('num', '?')}")
                rbox.delete("1.0", "end")
                rbox.insert("end",
                            f"RFC 依据 {len(stds)} 条（构建时经 rfc_catalog "
                            f"交叉验证存在性并回填标题）\n")

            def _on(_ev=None):
                sel = rlb.curselection()
                if not sel:
                    return
                s = rlb._data[sel[0]]
                rbox.delete("1.0", "end")
                rbox.insert("end",
                            f"RFC {s.get('num', '?')}  {s.get('rfc_title', '')}\n"
                            f"引用概念：{s.get('from', '')}\n")

            rlb.bind("<<ListboxSelect>>", _on)
            ttk.Button(row, text="列出", command=_fill).pack(side="left", padx=4)
            _fill()

        def _tabs(nb):
            _repo_tab(nb)
            _rfc_tab(nb)

        return self._axis_concept_window(ab, "apilab", "接口 API 概念系统", _tabs)

    def show_zhuangzi(self):
        """弹出「南华用户端」概念系统窗口（v0.6.60）：只读浏览，与 CLI `zhuangzi` 同口径。

        四轴：核心理念三篇（逍遥游/应帝王/大宗师）/ 内篇辅篇 / 外杂选篇 /
        七条人体工程学工程原则；额外页「用户端面实测」：CLI/GUI/webapi/deno
        四端事实（构建时从源码读出，漂移由 build_zhuangzi.py --check 检出）。
        """
        from .concepts import zhuangzi as z
        tk, ttk, messagebox, scrolledtext = _tk()

        def _userface_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="用户端面实测")
            box = scrolledtext.ScrolledText(f, wrap="word")
            box.pack(fill="both", expand=True, padx=8, pady=8)
            box.insert("end", "本仓库用户端面（构建时实测；数字随代码演进，"
                               "漂移时以 build_zhuangzi.py --check 检出）\n\n")
            for k, v in z.user_face().items():
                box.insert("end", f"{k}:\n    {v}\n\n")
            box.insert("end", "操作入口：python -m sysweeper guide（一屏入口地图）")

        return self._axis_concept_window(z, "zhuangzi", "南华用户端概念系统",
                                         _userface_tab)

    def show_baigong(self):
        """弹出「百工」匠作概念系统窗口（v0.6.61）：只读浏览，与 CLI `baigong` 同口径。

        四轴：核心理念五偶（墨子/公输般/公孙策/鲁班/三教九流总纲）/ 匠作七原则 /
        三教九流 12 条 / 工程场景三条（具体无解·暂时不允许·构建程序具体结构）；
        额外页「实测面」：CLI/GUI/webapi/deno 四端 + 语言面三项事实（构建时
        实测，漂移由 build_baigong.py --check 检出）。
        """
        from .concepts import baigong as b
        tk, ttk, messagebox, scrolledtext = _tk()

        def _userface_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="实测面")
            box = scrolledtext.ScrolledText(f, wrap="word")
            box.pack(fill="both", expand=True, padx=8, pady=8)
            box.insert("end", "本仓库实测面（构建时实测；数字随代码演进，"
                              "漂移时以 build_baigong.py --check 检出）\n\n")
            uf = b.user_face()
            for k, v in uf.items():
                box.insert("end", f"{k}:\n    {v}\n\n")
            box.insert("end", "三场景落地：具体无解（悬置+降级）/ 暂时不允许（守御 opt-in）/\n"
                              "构建程序具体结构（绳墨 + 九设九距）——详见 scenes 轴")

        return self._axis_concept_window(b, "baigong", "百工匠作概念系统",
                                         _userface_tab)

    def show_datong(self):
        """弹出「大同」人类文明一体概念系统窗口（v0.6.62）：只读浏览，与 CLI
        `datong` 同口径。

        五轴：文明传统 15（traditions）/ 核心命题 21（theses，唯道独尊为宗）/
        正道六象 6（six：天罡元阳气电波·地煞元阴固液磁）/ 实践形态 12
        （practices）/ 人间落法九原则（ethics）；额外页「实测面」：CLI/webapi/
        GUI/deno 四端 + 语言面三项事实（构建时实测，漂移由 build_datong.py
        --check 检出）。
        """
        from .concepts import datong as d
        tk, ttk, messagebox, scrolledtext = _tk()

        def _userface_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="实测面")
            box = scrolledtext.ScrolledText(f, wrap="word")
            box.pack(fill="both", expand=True, padx=8, pady=8)
            box.insert("end", "本仓库实测面（构建时实测；数字随代码演进，"
                              "漂移时以 build_datong.py --check 检出）\n\n")
            uf = d.user_face()
            for k, v in uf.items():
                box.insert("end", f"{k}:\n    {v}\n\n")
            box.insert("end", "正道六象：天罡元阳（气·电·波·外发）/ 地煞元阴（固·液·磁·内聚）"
                              "——类科学的自然正道，正名约定见 needs_verify")

        return self._axis_concept_window(d, "datong", "大同人类文明一体概念系统",
                                         _userface_tab)

    def show_protec(self):
        """弹出「protec」产品（设备设施）长期运行与基本保护概念系统窗口（v0.6.69）：
        只读浏览，与 CLI `protec` 同口径。

        八轴：材料耐久 7 / 电气安全 6 / 环境标准 4 / 应急保护 4 / 基本保护 7
        （= principles）/ 传输与可用性 8 / 接入与链路 7 / IPv6 与 ICMPv6 控制面 10；
        额外页「实测面」：CLI/webapi/GUI/deno 四端 + 语言面三项事实
        （构建时实测，漂移由 build_protec.py --check 检出）。
        """
        from .concepts import protec as p
        tk, ttk, messagebox, scrolledtext = _tk()

        def _userface_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="实测面")
            box = scrolledtext.ScrolledText(f, wrap="word")
            box.pack(fill="both", expand=True, padx=8, pady=8)
            box.insert("end", "本仓库实测面（构建时实测；数字随代码演进，"
                              "漂移时以 build_protec.py --check 检出）\n\n")
            uf = p.user_face()
            for k, v in uf.items():
                box.insert("end", f"{k}:\n    {v}\n\n")

        return self._axis_concept_window(p, "protec", "产品长期运行与基本保护概念系统",
                                         _userface_tab)

    def show_sciences(self):
        """弹出「sciences」自然科学概念系统窗口（v0.6.67）：只读浏览，与 CLI
        `sciences` 同口径。protec 工程保护的科学底座。

        八轴：材料 4 / 热力学 4 / 气候 4 / 环境 3 / 物理 3 / 化学 3 / 生物 4 /
        科学方法 7（= principles）；额外页「实测面」：CLI/webapi/GUI/deno 四端 +
        语言面三项事实（构建时实测，漂移由 build_sciences.py --check 检出）。
        """
        from .concepts import sciences as sc
        tk, ttk, messagebox, scrolledtext = _tk()

        def _userface_tab(nb):
            f = ttk.Frame(nb)
            nb.add(f, text="实测面")
            box = scrolledtext.ScrolledText(f, wrap="word")
            box.pack(fill="both", expand=True, padx=8, pady=8)
            box.insert("end", "本仓库实测面（构建时实测；数字随代码演进，"
                              "漂移时以 build_sciences.py --check 检出）\n\n")
            uf = sc.user_face()
            for k, v in uf.items():
                box.insert("end", f"{k}:\n    {v}\n\n")

        return self._axis_concept_window(sc, "sciences", "自然科学概念系统",
                                         _userface_tab)

    def show_concepts_center(self):
        """弹出「概念系统中心」窗口（v0.6.62）：九个概念系统的统一入口。

        汇总 concepts 注册表（plang/netsys/daoxue/quantum/comp/apilab/zhuangzi/
        baigong/datong）的一句话定位、版本与规模统计；双击某系统调用其专属面板。
        与 CLI ``concepts`` 子命令同口径，只读。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import concepts as C

        top = tk.Toplevel(self.root)
        top.title("概念系统中心（只读）")
        top.geometry("980x620")
        row = ttk.Frame(top, padding=(8, 6))
        row.pack(fill="x")
        ttk.Label(row, text="关键词:").pack(side="left")
        qv = tk.StringVar(value="")
        ttk.Entry(row, textvariable=qv, width=18).pack(side="left", padx=4)
        lb = tk.Listbox(top, width=34)
        lb.pack(side="left", fill="y", padx=(8, 2), pady=6)
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(side="left", fill="both", expand=True, padx=2, pady=6)
        lb._data = []

        def _overview_text():
            lines = ["==== 概念系统中心 ====", ""]
            for e in C.overview():
                lines.append(f"· {e['system']}（{e['version']}）  {e['title']}")
                lines.append(f"    {e['tagline']}")
                lines.append(f"    规模：{e.get('stats')}")
                lines.append("")
            return "\n".join(lines)

        def _open(_ev=None):
            sel = lb.curselection()
            if not sel:
                return
            name = lb._data[sel[0]]
            if not isinstance(name, str):
                return
            fn = getattr(self, f"show_{name}", None)
            if not callable(fn):
                if messagebox is not None:
                    messagebox.showinfo("概念系统中心",
                                        f"{name} 的专属面板请从底部按钮打开。")
                return
            fn()

        def _fill():
            lb.delete(0, "end")
            lb._data = list(C.systems())
            for s in lb._data:
                lb.insert("end", s)
            box.delete("1.0", "end")
            box.insert("end", _overview_text())

        def _do_search():
            q = (qv.get() or "").strip()
            hits = C.search_all(q) if q else []
            lb.delete(0, "end")
            lb._data = list(hits)
            for h in hits:
                lb.insert("end", f"[{h['system']}] {h.get('name', '')}")
            box.delete("1.0", "end")
            box.insert("end", f"跨系统检索 {q!r}：{len(hits)} 条\n")

        def _on(_ev=None):
            sel = lb.curselection()
            if not sel:
                return
            item = lb._data[sel[0]]
            if isinstance(item, dict) and item.get("system"):
                box.delete("1.0", "end")
                box.insert("end", f"[{item['system']}] {item.get('name', '')}\n"
                                  f"{item.get('text', '')}\n")

        lb.bind("<<ListboxSelect>>", _on)
        lb.bind("<Double-Button-1>", _open)
        ttk.Button(row, text="跨系统检索",
                   command=_do_search).pack(side="left", padx=4)
        ttk.Button(row, text="刷新", command=_fill).pack(side="left")
        ttk.Button(row, text="打开选中系统",
                   command=_open).pack(side="left", padx=4)
        _fill()
        return top

    def show_a11y(self):
        """弹出「无障碍」窗口：ORCA / AT-SPI2 环境报告 + 无障碍任务 + 朗读结果。

        面向 Linux ORCA 屏幕阅读器（经 AT-SPI2 D-Bus 总线 org.a11y.Bus 访问应用
        无障碍树）提供协议/接口自检；文本经 accessible_text 去装饰，便于朗读。
        有语音后端（spd-say / espeak / say）时可点「朗读结果」直接读屏。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import a11y as a11y_mod, registry

        top = tk.Toplevel(self.root)
        top.title("无障碍（ORCA / AT-SPI2）")
        top.geometry("720x520")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        for line in a11y_mod.environment_report():
            put(line)

        put("")
        put("-" * 68)
        tasks = registry.applicable(self.platform_cb.get(),
                                    self.version_var.get().strip() or "0",
                                    category="accessibility", include_lang_missing=True)
        put(f"适用无障碍任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<24} [{t.platform}/{t.risk}]  {t.display_title()}")
        put("")
        put("提示：结果文本已去除装饰字符，可直接复制给读屏器；"
            "也可点下方按钮用系统语音朗读。")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))

        def do_speak():
            ok, msg = a11y_mod.speak(a11y_mod.accessible_text(box.get("1.0", "end"))[:400])
            self.log(f"\n朗读: {'成功' if ok else '未执行'} — {msg}\n")

        ttk.Button(bar, text="朗读结果", command=do_speak).pack(side="left")
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        backend = a11y_mod.speak_backend()
        ttk.Label(bar, text=("语音后端: " + backend) if backend
                  else "无语音后端（纯文本呈现）").pack(side="left", padx=8)
        box.see("1.0")
        return top

    def show_a11y_multi(self):
        """弹出「无障碍（多系统适配）」窗口。

        按**各系统自己的**无障碍协议与接口只读探测：Windows 讲述人(UIA/MSAA)、
        macOS VoiceOver(NSAccessibility)、Linux ORCA(AT-SPI2)、
        Android TalkBack(AccessibilityService)、iOS VoiceOver、鸿蒙屏幕朗读
        (AccessibilityExtensionAbility)。可下拉切换系统；非当前系统降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import a11y as a11y_mod

        top = tk.Toplevel(self.root)
        top.title("无障碍（多系统适配）")
        top.geometry("760x560")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")

        def render(plat: str):
            box.delete("1.0", "end")
            put(f"==== 多系统无障碍适配（platform={plat}）====")
            for line in a11y_mod.environment_report(None if plat == "any" else plat):
                put(line)
            put("")
            put("-" * 68)
            put("权威文档（协议与接口出处）：")
            for line in a11y_mod.a11y_doc_list():
                put("  " + line)
            box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Label(bar, text="系统:").pack(side="left")
        plat_var = tk.StringVar(value="any")
        cb = ttk.Combobox(bar, textvariable=plat_var, width=12, state="readonly",
                          values=["any", "windows", "macos", "linux", "android",
                                  "ios", "harmony"])
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: render(plat_var.get()))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

        render("any")
        return top

    def show_netlink(self):
        """弹出「网络链接 / 自组网 / 隐私验证 / 资源共享」窗口。

        四个能力域，全部只读优先、默认非变更：
        - 链接协议：TCP/UDP/RFCOMM/串口/BLE/802.15.4 注册表与本机能力
        - 自组网  ：多于 1 台设备自己通信（UDP 发现 + TCP 可靠通道，
                    命令通道只有 info/ping/probe/msg，**绝不执行任意命令**）
        - 隐私验证：按网络维度用两项以上个人信息验证，原始值不保存，可重连
        - 资源共享：同人登录的多设备共享算力与网络，个人数据与资产永不共享
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import netauth, netlink, reshare

        top = tk.Toplevel(self.root)
        top.title("网络链接 / 自组网 / 隐私验证 / 资源共享")
        top.geometry("820x580")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 多种网络链接协议 + 本机能力 ====")
        ok, msg = netlink.link_report()
        put(msg)
        put("")
        ok2, msg2 = netlink.mesh_report()
        put(msg2)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="启动自组网",
                   command=lambda: run("启用本地自组网（多设备自通信）",
                                       netlink.mesh_serve)).pack(side="left", padx=2)
        ttk.Button(bar, text="发现设备",
                   command=lambda: run("发现本网段设备（只读）",
                                       netlink.mesh_discover)).pack(side="left", padx=2)
        ttk.Button(bar, text="本节点信息",
                   command=lambda: run("本节点信息", netlink.mesh_info)).pack(side="left", padx=2)
        ttk.Button(bar, text="隐私验证",
                   command=lambda: run("按网络维度的隐私验证（原始信息不保存）",
                                       netauth.netauth_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="资源共享",
                   command=lambda: run("同人设备资源共享（算力共享，数据不共享）",
                                       reshare.reshare_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        ttk.Label(top, text="命令通道白名单：info/ping/probe/msg —— "
                            "绝不执行对端发来的任意命令；个人数据与关键资产数据永不共享。",
                  foreground="#b00").pack(fill="x", padx=8, pady=(0, 8))

    def show_thirdparty(self):
        """弹出「第三方网络互联互通 / 硬件优化 / 开源下载」窗口（只读引用登记）。

        把用户导入的若干开源仓库作为可选方案登记：
        - 网络互联互通：p2wlan / dae / gfw-pac / v2rayN（合并到同人资源共享模型）
        - 硬件优化    ：DLSS5-Swapper（由用户选择）
        - 开源下载    ：aria2（含 CDN / P2P 开关）
        本工具不打包其二进制；安全护栏：同人共享只限本人授权网络与算力，
        绝不盗用他人网络互联、绝不共享个人数据与关键资产。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import thirdparty

        top = tk.Toplevel(self.root)
        top.title("第三方网络互联互通 / 硬件优化 / 开源下载")
        top.geometry("860x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 第三方引用清单（只读登记，本工具不打包其二进制） ====")
        ok, msg = thirdparty.thirdparty_report("list")
        put(msg)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="网络互联互通",
                   command=lambda: run("网络互联互通共享资源",
                                       thirdparty.interop_refs_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="硬件优化",
                   command=lambda: run("硬件优化（由用户选择）",
                                       thirdparty.hw_opt_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="开源下载",
                   command=lambda: run("开源下载软件",
                                       thirdparty.downloader_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="CDN/P2P 开关",
                   command=lambda: run("CDN / P2P 开关说明",
                                       thirdparty.cdn_p2p_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="许可证来源",
                   command=lambda: run("第三方许可证引用来源",
                                       thirdparty.licenses_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        ttk.Label(top, text="安全护栏：同人共享只限本人授权网络与算力；个人数据与关键资产数据"
                            "永不共享；绝不盗用他人网络互联互通能力。完整许可证见仓库 licenses/ 文件夹。",
                  foreground="#b00").pack(fill="x", padx=8, pady=(0, 8))
        box.see("1.0")
        return top

    def show_openwrt(self):
        """弹出「OpenWrt 路由器系统只读接口」窗口（v0.5.20/0.5.21）。

        只读优先：固件/板型识别、UCI 配置审计（不打印 secret 明文）、包管理盘点
        （opkg/apk）、网络接口、防火墙、无线（不回显密码）、DHCP/DNS、存储、构建系统参考。
        另提供「写操作指引」按钮：只做只读预检 + 给出命令文本，任何写操作
        （opkg install / uci set / sysupgrade / 服务重启）都绝不自动执行。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import openwrt, openwrt_write

        top = tk.Toplevel(self.root)
        top.title("OpenWrt 路由器系统只读接口")
        top.geometry("860x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== OpenWrt · 能力总览（只读） ====")
        ok, msg = openwrt.openwrt_report()
        put(msg)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="板型/固件",
                   command=lambda: run("OpenWrt 板型与固件识别",
                                       openwrt.openwrt_detect_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="UCI 审计",
                   command=lambda: run("UCI 配置只读审计（不打印 secret 明文）",
                                       openwrt.openwrt_uci_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="已装软件包",
                   command=lambda: run("已装软件包盘点（opkg/apk）",
                                       openwrt.openwrt_pkgs_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="网络接口",
                   command=lambda: run("网络接口只读报告",
                                       openwrt.openwrt_network_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="防火墙",
                   command=lambda: run("防火墙只读报告",
                                       openwrt.openwrt_firewall_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="无线",
                   command=lambda: run("无线只读报告（不回显密码）",
                                       openwrt.openwrt_wireless_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="DHCP/DNS",
                   command=lambda: run("DHCP/DNS 只读报告",
                                       openwrt.openwrt_dhcp_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="存储",
                   command=lambda: run("存储只读报告",
                                       openwrt.openwrt_storage_report)).pack(side="left", padx=2)
        ttk.Button(bar, text="构建系统参考",
                   command=lambda: run("OpenWrt 构建系统参考（仅文档）",
                                       openwrt.openwrt_build_report)).pack(side="left", padx=2)

        bar2 = ttk.Frame(top)
        bar2.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar2, text="⚠ 写操作指引（只预检+命令文本，绝不执行）",
                   command=lambda: run("OpenWrt 写操作安全指引（不执行）",
                                       openwrt_write.openwrt_write_report)).pack(side="left", padx=2)
        ttk.Button(bar2, text="关闭", command=top.destroy).pack(side="right")
        ttk.Label(top, text="安全底线：仅只读探测与文档引用；opkg install / uci set / "
                            "sysupgrade / make image 等写操作只给指引，绝不自动执行。",
                  foreground="#b00").pack(fill="x", padx=8, pady=(0, 8))
        box.see("1.0")
        return top

    def show_plugins(self):
        """弹出「插件支持」窗口（v0.5.20）：列出/查看/只读运行已注册的安全插件。

        插件 native 入口仅限白名单内零参只读函数，绝不执行任意代码；含命令注入或
        非白名单函数的清单会被 plugin_validate 直接拒绝注册。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import plugins

        top = tk.Toplevel(self.root)
        top.title("插件支持（安全只读插件注册表）")
        top.geometry("860x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def put(text: str):
            box.insert("end", text + "\n")
            box.see("end")

        def run(title: str, fn):
            put("")
            put(f"==== {title} ====")
            try:
                ok, msg = fn()
                put(f"[{'成功' if ok else '未完成'}] {msg}")
            except Exception as e:  # noqa: BLE001
                put(f"[失败] {e}")
            self.log(f"\n{title}: 已完成\n")

        put("==== 已注册插件（安全只读注册表） ====")
        ok, msg = plugins.plugin_report("list")
        put(msg)

        def run_plugin(pid: str):
            """运行前先查启用状态——停用就真不让跑，开关不做装饰。"""
            if not self.guistate.is_plugin_enabled(self.state, pid):
                put(f"[已停用] 插件 {pid} 当前为停用状态；先在下方勾选「启用」再运行。")
                return
            run(f"只读运行：{pid}", lambda: plugins.plugin_run(pid))

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(bar, text="查看 openwrt",
                   command=lambda: run("插件详情：openwrt",
                                       lambda: plugins.plugin_report("show", "openwrt"))).pack(side="left", padx=2)
        ttk.Button(bar, text="只读运行 openwrt",
                   command=lambda: run_plugin("openwrt")).pack(side="left", padx=2)
        ttk.Button(bar, text="查看 interop",
                   command=lambda: run("插件详情：interop",
                                       lambda: plugins.plugin_report("show", "interop"))).pack(side="left", padx=2)
        ttk.Button(bar, text="只读运行 interop",
                   command=lambda: run_plugin("interop")).pack(side="left", padx=2)
        ttk.Button(bar, text="只读白名单",
                   command=lambda: run("插件只读白名单（静态+运行时登记）",
                                       lambda: plugins.plugin_report("allowlist"))).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

        # 插件启停：勾选 = 启用，立即记进配置（只存 id，不存任何命令）
        try:
            reg = getattr(plugins, "PLUGINS", None) or {}
            ids = list(reg.keys()) if isinstance(reg, dict) else []
        except Exception:  # noqa: BLE001
            ids = []
        if not ids:
            ids = ["openwrt", "interop"]
        en = ttk.LabelFrame(top, text="插件启停（勾选=启用，立即记住；停用的插件不参与运行）")
        en.pack(fill="x", padx=8, pady=(0, 4))
        for pid in ids:
            v = tk.BooleanVar(value=self.guistate.is_plugin_enabled(self.state, pid))
            ttk.Checkbutton(en, text=pid, variable=v,
                            command=lambda p=pid, var=v: self._on_plugin_toggle(p, var)
                            ).pack(side="left", padx=6)
        ttk.Label(top, text="插件安全模型：native 入口仅限白名单内零参只读函数；含命令/路径/"
                            "shell 元字符或非白名单函数的清单直接拒绝注册（防注入）。",
                  foreground="#b00").pack(fill="x", padx=8, pady=(0, 8))
        box.see("1.0")
        return top

    def show_arch(self):
        """弹出「架构 / 开源硬件」窗口：ISA 探测 + 龙芯/MIPS/RISC-V + 开源硬件标准。

        架构维度独立于操作系统：龙芯 LoongArch（国产自主）、MIPS（含龙芯早期授权
        机型与嵌入式设备）、RISC-V（开源 ISA）、开源硬件（OSHWA / CERN OHL /
        DIN SPEC 3105）。标准按「国家优先 / 国际给外人 / 地区按需」三层呈现。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import arch as arch_mod, registry

        top = tk.Toplevel(self.root)
        top.title("架构 / 指令集 / 开源硬件")
        top.geometry("760x560")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        for line in arch_mod.environment_report("cn"):
            put(line)

        for fn_name, label in (("loongarch_report", "龙芯 LoongArch"),
                               ("mips_report", "MIPS"),
                               ("riscv_report", "RISC-V"),
                               ("open_hardware_report", "开源硬件")):
            ok, msg = getattr(arch_mod, fn_name)()
            put("")
            put(f"-- {label} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = registry.applicable(self.platform_cb.get(),
                                    self.version_var.get().strip() or "0",
                                    category="arch", include_lang_missing=True)
        put(f"适用架构任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<24} [{t.platform}/{t.risk}]  {t.display_title()}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        ttk.Label(bar, text=f"GOARCH: {arch_mod.goarch() or '（未收录）'}").pack(side="left", padx=8)
        box.see("1.0")
        return top

    def show_hardware(self):
        """弹出「硬件优化」窗口：内核文档引用 + 硬件可调项核对 + 适用任务。

        硬件优化的标准依据一律指向 Linux kernel 源码文档（kernel.org/Documentation）：
        CPUFreq/cpuidle/intel_pstate（admin-guide/pm/）、thermal、THP/zswap/NUMA/vm
        （admin-guide/mm/、sysctl/vm.rst）、block/bfq/nvme、watchdog、EAS（scheduler/）。
        只读核对系统已暴露的 /sys、/proc 接口，不修改系统。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import hardware as nhw

        top = tk.Toplevel(self.root)
        top.title("硬件优化（参考 Linux kernel 源码文档）")
        top.geometry("760x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("硬件优化：标准依据 = Linux kernel 源码文档（kernel.org/Documentation）")
        put("=" * 72)
        put("")
        put("-- 内核文档引用（data/hardware_kernel.json）--")
        for line in nhw.kernel_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机硬件可调项核对（只读 /sys、/proc，不修改）：")
        for fn_name, label in (("cpufreq_governor", "CPUFreq governor"),
                               ("cpuidle_report", "cpuidle 空闲态"),
                               ("intel_pstate_status", "Intel P-State"),
                               ("thermal_report", "温控热区"),
                               ("thp_enabled", "透明大页 THP"),
                               ("zswap_enabled", "zswap"),
                               ("zram_report", "zram"),
                               ("io_scheduler", "I/O 调度器"),
                               ("nvme_report", "NVMe"),
                               ("epb_read", "x86 EPB"),
                               ("numa_balancing", "NUMA 平衡"),
                               ("watchdog_report", "看门狗"),
                               ("vm_swappiness", "vm.swappiness"),
                               ("eas_available", "EAS")):
            ok, msg = getattr(nhw, fn_name)()
            put("")
            put(f"-- {label} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = registry.applicable(self.platform_cb.get(),
                                    self.version_var.get().strip() or "0",
                                    category="hardware", include_lang_missing=True)
        put(f"适用硬件优化任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.platform}/{t.risk}]  {t.display_title()}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_kernel(self):
        """弹出「内核文档」窗口：硬件/软件/网络子系统文档 + 本机核对 + 适用任务。

        Linux 整体优化的依据统一指向 kernel.org/Documentation：硬件（CPUFreq/thermal/
        THP/zswap/NUMA/block…）、软件（scheduler/cgroup-v2/oom/psi/vm-sysctl）、网络
        （tcp/拥塞控制/net.core/rps）。只读核对系统已暴露的 /sys、/proc 接口，不修改。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import kernel as nk

        top = tk.Toplevel(self.root)
        top.title("Linux kernel 源码文档参考（硬件/软件/网络）")
        top.geometry("780x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("Linux 整体优化依据 = Linux kernel 源码文档（kernel.org/Documentation）")
        put("=" * 72)
        grouped = nk.kernel_doc_grouped()
        label = {"hardware": "硬件（hardware）", "software": "软件（software）",
                 "network": "网络（network）"}
        for g in ("hardware", "software", "network"):
            put("")
            put(f"-- {label[g]}（{len(grouped.get(g, {}))} 项）--")
            for line in nk.kernel_doc_list(group=g):
                put(line)

        put("")
        put("-" * 68)
        put("本机内核子系统核对（只读 /sys、/proc，不修改）：")
        for fn_name, lab in (("sched_report", "CFS 调度器"),
                             ("cgroup_v2_report", "cgroups v2"),
                             ("oom_report", "OOM 防护"),
                             ("psi_report", "资源压力 PSI"),
                             ("thp_compaction_report", "THP 规整"),
                             ("vm_dirty_report", "vm 脏页/缓存"),
                             ("tcp_report", "TCP 协议栈"),
                             ("tcp_congestion_report", "TCP 拥塞控制"),
                             ("net_core_report", "net.core"),
                             ("rps_report", "RPS/RFS")):
            ok, msg = getattr(nk, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks()
                 if t.platform == "linux"
                 and any("Linux kernel Documentation" in s for s in t.standards)]
        put(f"引用内核文档的 Linux 优化任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_desktop(self):
        """弹出「桌面环境」窗口：当前桌面探测 + GNOME/KDE/XFCE/freedesktop 文档 + 任务。

        按用户要求跟踪桌面（GNOME、KDE、XFCE 等）文档：dconf/gsettings、KConfig、
        xfconf、freedesktop XDG 规范；只读探测当前桌面环境，列出清理/优化任务与文档出处。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import desktop as ndt

        top = tk.Toplevel(self.root)
        top.title("桌面环境文档跟踪（GNOME / KDE / XFCE）")
        top.geometry("760x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("桌面环境文档跟踪（GNOME / KDE / XFCE + freedesktop 规范）")
        put("=" * 72)
        for line in ndt.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("桌面环境/规范文档引用（data/desktop_docs.json）：")
        for sid, ref in ndt.reference_all().items():
            put(f"   · {ref.get('name','')}  [{ref.get('org','')} / {ref.get('url','')}]")
            for d in ref.get("docs", [])[:3]:
                put(f"       - {d}")

        put("")
        put("-" * 68)
        tasks = registry.applicable("linux", self.version_var.get().strip() or "0",
                                    include_lang_missing=True)
        dtasks = [t for t in tasks if t.id.startswith("desktop_")]
        put(f"桌面清理/优化任务：{len(dtasks)} 项")
        for t in dtasks:
            put(f"  • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))

        def do_cache_report():
            """把桌面缓存只读对比报告追加到文本框（不删除任何文件）。"""
            ok, msg = ndt.cache_report()
            put("")
            put("-" * 68)
            put("桌面缓存只读对比报告（不删除任何文件）：")
            for line in (msg or "").splitlines():
                put(line)
            box.see("end")

        ttk.Button(bar, text="缓存对比报告（只读）",
                   command=do_cache_report).pack(side="left", padx=4)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_syssoftware(self):
        """弹出「系统软件」窗口：各软件探测 + 协议/接口文档 + 本机核对 + 任务。

        「触类旁通、举一反三」：与内核、桌面同一模式，覆盖其余系统软件——systemd
        （单元/D-Bus/journal）、D-Bus（规范）、NetworkManager（org.freedesktop
        .NetworkManager）、PipeWire（SPA 协议）、BlueZ（org.bluez）、udev（规则/hwdb）、
        polkit（策略）、Wayland（wayland.xml/xdg-shell）。全部只读，未安装则降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import syssoftware as nsw

        top = tk.Toplevel(self.root)
        top.title("其他系统软件文档跟踪（按各自协议与接口）")
        top.geometry("780x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("其他系统软件：各自按自身协议与接口核对（延续内核/桌面文档跟踪模式）")
        put("=" * 72)
        for line in nsw.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("系统软件文档引用（data/syssoftware_docs.json）：协议 + 接口")
        for line in nsw.syssoftware_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nsw.PROBES:
            ok, msg = getattr(nsw, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("syssw_")]
        put(f"系统软件核对/优化任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_pkgmgr(self):
        """弹出「包管理器」窗口：各包管理器探测 + 协议/接口文档 + 本机核对 + 任务。

        「触类旁通、举一反三」：与内核、桌面、系统软件、鸿蒙、小程序端同一模式，
        覆盖包管理器——它们的接口彼此完全不同，故逐个按自身协议核对：APT（deb +
        Debian Policy 控制字段）、RPM/DNF（rpmdb + repomd.xml）、apk（APKINDEX）、
        pacman（.pkg.tar.zst + *.db）、Homebrew（Formula/Cask DSL）、winget（YAML
        清单 + REST 源）、pip（PEP 503 + wheel）、npm（Registry API + _cacache）、
        Snap/Flatpak（snapd REST + OSTree）。全部只读，未安装则降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import pkgmgr as npm_

        top = tk.Toplevel(self.root)
        top.title("包管理器文档跟踪（各自按自身协议与接口）")
        top.geometry("780x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("包管理器：各自按自身协议与接口核对（延续内核/桌面/系统软件文档跟踪模式）")
        put("=" * 72)
        for line in npm_.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("包管理器文档引用（data/pkgmgr_docs.json）：协议 + 接口")
        for line in npm_.pkgmgr_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in npm_.PROBES:
            ok, msg = getattr(npm_, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("pm_")]
        put(f"包管理器清理/核对任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_container(self):
        """弹出「容器运行时」窗口：各运行时探测 + 协议/接口文档 + 本机核对 + 任务。

        「触类旁通、举一反三」：延续内核/桌面/系统软件/鸿蒙/小程序端/包管理器同一模式，
        覆盖容器运行时——接口彼此完全不同，故逐个按自身协议核对：Docker（OCI runtime-spec
        + Engine API + system prune）、Podman（rootless OCI）、containerd（content store /
        snapshotter + nerdctl/ctr）、BuildKit（内容寻址 build cache）、OCI（image-spec /
        runtime-spec + digest 共享层）、LXC/LXD（liblxc + 存储池）、CRI（gRPC + crictl）。
        全部只读，未安装则降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import container as nct

        top = tk.Toplevel(self.root)
        top.title("容器运行时文档跟踪（各自按自身协议与接口）")
        top.geometry("780x640")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("容器运行时：各自按自身协议与接口核对（延续内核/桌面/系统软件文档跟踪模式）")
        put("=" * 72)
        for line in nct.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("容器运行时文档引用（data/container_docs.json）：协议 + 接口")
        for line in nct.container_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nct.PROBES:
            ok, msg = getattr(nct, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("ct_")]
        put(f"容器运行时清理/核对任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_storage(self):
        """弹出「存储与文件系统」窗口：各文件系统探测 + 协议/接口文档 + 本机核对 + 任务。

        「触类旁通、举一反三」：延续内核/桌面/系统软件/鸿蒙/小程序端/包管理器/容器运行时同一
        模式，覆盖存储与文件系统——接口彼此完全不同，故逐个按自身协议核对：ext4（extent/jbd2
        + e2fsck/e4defrag）、Btrfs（COW B-tree + balance/scrub）、XFS（AG + xfs_db -r/xfs_fsr）、
        ZFS（zpool/zfs + 校验和）、LVM（PV/VG/LV + thin）、fstrim（FITRIM + TRIM/UNMAP）、SMART
        （smartctl 健康）、swap（swapon/mkswap）。全部只读，未安装则降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import storage as nst

        top = tk.Toplevel(self.root)
        top.title("存储与文件系统文档跟踪（各自按自身协议与接口）")
        top.geometry("800x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("存储与文件系统：各自按自身协议与接口核对（延续文档跟踪模式）")
        put("=" * 72)
        for line in nst.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("存储/文件系统文档引用（data/storage_docs.json）：协议 + 接口")
        for line in nst.storage_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nst.PROBES:
            ok, msg = getattr(nst, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("fs_")]
        put(f"存储/文件系统清理/核对任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_network(self):
        """弹出「网络栈深度调优」窗口：各运维工具探测 + 协议/接口文档 + 本机核对 + 任务。

        「触类旁通、举一反三」：延续存储/容器/包管理器同一模式，覆盖网络栈运维与可观测性——
        接口彼此完全不同，故逐个按自身协议核对：iproute2（netlink/rtnetlink+sock_diag）、
        ethtool（ETHTOOL ioctl/netlink，-k/-K）、eBPF（bpf()+libbpf，bpftool list）、
        tc（rtnetlink TC qdisc）、conntrack（nf_conntrack）、NM-resolved（nmcli/resolvectl）、
        scaling（RPS/RFS/XPS sysfs）。全部只读，未安装则降级为指引。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import network as nnet

        top = tk.Toplevel(self.root)
        top.title("网络栈深度调优文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("网络栈深度调优：各自按自身协议与接口核对（延续文档跟踪模式）")
        put("=" * 72)
        for line in nnet.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("网络运维工具文档引用（data/network_docs.json）：协议 + 接口")
        for line in nnet.network_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nnet.PROBES:
            ok, msg = getattr(nnet, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("net_")]
        put(f"网络栈深度调优任务（net_*）：{len(tasks)} 项（全 opt_in）")
        for t in tasks:
            put(f"  • {t.id:<22} [{t.platform}/{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_snapshot(self):
        """弹出「快照/对比」窗口：生成只读基线快照、或对比两份快照（跨时间 diff）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from tkinter import filedialog
        from .native import snapshot as nsnap

        top = tk.Toplevel(self.root)
        top.title("基线快照与差异对比（纯只读）")
        top.geometry("820x640")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str = ""):
            box.insert("end", text + "\n")

        def do_capture():
            snap = nsnap.capture_snapshot(include_probes=True)
            path = filedialog.asksaveasfilename(
                title="保存快照为 JSON", defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("全部", "*.*")])
            if not path:
                return
            nsnap.save_snapshot(path, snap)
            box.delete("1.0", "end")
            put(f"已生成基线快照：{path}")
            for line in nsnap.summarize(snap):
                put("  " + line)

        def do_diff():
            a = filedialog.askopenfilename(title="选择基线快照（A）",
                                           filetypes=[("JSON", "*.json"), ("全部", "*.*")])
            if not a:
                return
            b = filedialog.askopenfilename(title="选择对比快照（B）",
                                           filetypes=[("JSON", "*.json"), ("全部", "*.*")])
            if not b:
                return
            try:
                sa = nsnap.load_snapshot(a)
                sb = nsnap.load_snapshot(b)
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("读取失败", str(e))
                return
            box.delete("1.0", "end")
            put(f"A: {a}")
            put(f"B: {b}")
            put("")
            put(nsnap.format_diff(nsnap.diff_snapshots(sa, sb)))

        put("基线快照与差异对比（纯只读）：")
        put("  · 生成快照：聚合各子系统只读探测 + 磁盘/内存指标，落盘为 JSON")
        put("  · 对比快照：选两份快照，输出跨时间的可追溯差异")
        put("  · 全程不修改系统、不跑清理命令")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="生成快照", command=do_capture).pack(side="left", padx=2)
        ttk.Button(bar, text="对比两份快照", command=do_diff).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_scan_diff(self):
        """弹出本会话内最近两次扫描快照的差异（扫描流程自动记录的基线）。

        与独立「快照/对比」窗口的区别：这里对比的是 GUI 扫描流程每次自动留下的
        会话内基线，无需手动选文件；不足两份时提示先扫描。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import snapshot as nsnap
        snaps = getattr(self, "_scan_snaps", [])
        if len(snaps) < 2:
            messagebox.showinfo(
                "提示",
                "会话内扫描快照不足两份。请先至少点「扫描分析」两次——"
                "系统会自动记录并对比基线快照。")
            return
        a, b = snaps[-2], snaps[-1]
        top = tk.Toplevel(self.root)
        top.title("扫描前后对比（本会话基线快照）")
        top.geometry("820x640")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)
        box.insert("end", f"A（上次扫描）: {a['meta'].get('captured_at', '?')}\n")
        box.insert("end", f"B（本次扫描）: {b['meta'].get('captured_at', '?')}\n\n")
        box.insert("end", nsnap.format_diff(nsnap.diff_snapshots(a, b)))
        box.see("1.0")
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_windows(self):
        """弹出「Windows」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：把同一文档跟踪模式补到 Windows 自身系统接口
        （此前唯独它缺文档层）——逐个按自身协议与接口核对：Win32 API
        （kernel32/shell32/advapi32）、注册表（winreg）、WMI/CIM（CIM 模型 + WQL）、
        powercfg、DISM/CBS、SFC/WRP、存储感知、传递优化、Windows Update。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import windows as nw

        top = tk.Toplevel(self.root)
        top.title("Windows 原生接口文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("Windows 原生接口文档跟踪：各自按自身协议与接口核对")
        put("=" * 72)
        for line in nw.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("Windows 系统接口文档引用（data/windows_docs.json）：协议 + 接口")
        for line in nw.windows_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nw.PROBES:
            ok, msg = getattr(nw, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("Windows 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in nw.windows_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks()
                if t.id.startswith("win") and not t.id.startswith("win_tune_")]
        tune = [t for t in registry.all_tasks() if t.id.startswith("win_tune_")]
        put(f"Windows 清理/优化任务（win_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"Windows 官方接口深度调优（win_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<30} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_unix(self):
        """弹出「Unix（System V）」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：Windows / macOS / BSD 之后，把同一文档跟踪模式补到
        System V 自身系统接口，逐个按自身协议与接口核对（绝不套 Linux 的 /proc/sys、
        sysctl 或 systemd 写法）：IPS pkg（FMRI + 镜像 + publisher）、SMF
        （svc:/... FMRI + XML manifest + svc.startd）、ZFS（pool/dataset 属性与
        校验和）、/etc/release、logadm、kstat（module:instance:name:class）、
        Zones、FMA（fmadm/fmdump 自愈）、dladm+ipadm（Crossbow 链路与 IP 分层）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import unix as nu

        top = tk.Toplevel(self.root)
        top.title("Unix（System V）原生接口文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("Unix（System V）原生接口文档跟踪：各自按自身协议与接口核对")
        put("=" * 72)
        for line in nu.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("Unix 系统接口文档引用（data/unix_docs.json）：协议 + 接口")
        for line in nu.unix_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nu.PROBES:
            ok, msg = getattr(nu, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("Unix 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in nu.unix_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks()
                if t.id.startswith("unix") and not t.id.startswith("unix_tune_")]
        tune = [t for t in registry.all_tasks() if t.id.startswith("unix_tune_")]
        put(f"Unix 清理/优化任务（unix_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"Unix 官方接口深度调优（unix_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_android(self):
        """弹出「Android」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：Windows / macOS / BSD / Unix 之后，把同一文档跟踪
        模式补到 Android 自身系统接口。Android 是 managed OS，PC 端只能经官方 ADB
        向设备发指令，每个接口都与桌面不同，逐个按自身协议与接口核对（绝不套
        注册表/plist/sysctl，也不 adb remount 后改系统分区）：adb（client-server
        调试桥）、settings_provider（global/system/secure 三表）、pm（PackageManager
        缓存与数据分离）、am（ActivityManager 只后台）、dumpsys（batterystats/
        meminfo/netstats 状态快照与 --reset 只清计数）、getprop（ro.build.* 即
        Android 的发行版标识）、svc（无线只开不关）、wm（显示 reset 回默认）、
        logcat（logd 环形缓冲只清日志）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import android as na

        top = tk.Toplevel(self.root)
        top.title("Android 原生接口文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("Android 原生接口文档跟踪：各自按自身协议与接口核对")
        put("=" * 72)
        for line in na.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("Android 系统接口文档引用（data/android_docs.json）：协议 + 接口")
        for line in na.android_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口；需设备已连且授权）：")
        for fn_name, lab in na.PROBES:
            ok, msg = getattr(na, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("Android 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in na.android_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks() if t.platform == "android" and not t.opt_in]
        tune = [t for t in registry.all_tasks() if t.platform == "android" and t.opt_in]
        put(f"Android 清理/优化任务（and_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"Android 官方接口深度调优（and_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        put("")
        put("=" * 68)
        put("适老化（老年人 / 高龄用户）无障碍体检 —— 全部只读，不代改任何开关")
        put("=" * 68)
        ok_a11y, msg_a11y = na.elderly_a11y_report()
        put(msg_a11y)
        put("")
        put("-- 适老化调整建议清单（纯文字，可直接照着念给长辈）--")
        for line in na.elderly_a11y_advice():
            put(line)
        put("")
        put("-- Android 8（API 26）向下兼容口径（各接口最低 API 与本机可用性）--")
        ok_compat, msg_compat = na.android_compat_report()
        put(msg_compat)

        put("")
        put("-" * 68)
        put("适老化任务（and_a11y_* / and_compat_audit，只读，无需 --apply 亦可查看）")
        from . import registry as _reg
        a11y_tasks = [t for t in _reg.all_tasks()
                      if t.platform == "android" and t.id.startswith(("and_a11y", "and_compat"))]
        for t in a11y_tasks:
            put(f"  • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_jdk(self):
        """弹出「OpenJDK / JVM」窗口：只读体检 + 官方文档参考 + 高危动作禁令 + 任务。

        把 OpenJDK 当成**被体检对象**而非「要装的依赖」：只跑 `java -version`、
        `--list-modules`、`PrintFlagsFinal`（只打印最终值）、`jps/jcmd -l`（只列进程）。
        系统属性只输出白名单键，口令/令牌类只报「存在」不回显值。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import jdk as nj

        top = tk.Toplevel(self.root)
        top.title("OpenJDK / JVM 只读体检（参照 OpenJDK 官方工程与 JEP）")
        top.geometry("860x700")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("OpenJDK / JVM 只读体检：只查状态，不改 JAVA_HOME、不设参数、不录制")
        put("=" * 72)
        for line in nj.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("OpenJDK 官方文档参考（jdk/jvm/jpms/gc/jit/jfr/diagnostics）：")
        for line in nj.jdk_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("明确不执行的高副作用命令（只给指引，不代跑）：")
        for c in nj.FORBIDDEN_SUBCOMMANDS:
            put("  · " + c)

        put("")
        put("-" * 68)
        put("OpenJDK 体检明细（逐项只读）：")
        for fn_name, label, _need in nj.JDK_PROBES:
            ok, msg = getattr(nj, fn_name)()
            put("")
            put(f"-- {label} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("jdk_")]
        put(f"OpenJDK 任务（jdk_*）：{len(tasks)} 项（无 JDK 时自动隐藏）")
        for t in tasks:
            put(f"  • {t.id:<20} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_kmod(self):
        """弹出「内核模块/固件/eBPF」窗口：按 kernel.org 源码组织方式的只读体检。

        用户的「引入/参考/模仿/进阶/超越 linux kernel 的 module(s)/firmware/plugin(s)」
        在这里落地为三层只读视图：
          1. **module(s)**  —— /proc/modules、/sys/module、模块参数（只读 sysfs）、modinfo
          2. **firmware**   —— /lib/firmware 统计、/sys/class/firmware 已加载固件
          3. **plugin(s)**  —— eBPF（现代 Linux 的内核级可编程插件）：BTF/bpffs/kprobe 面
        全部只读：不 insmod/rmmod、不写 parameters、不替换固件、不 load/attach eBPF。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import kmod as nk

        top = tk.Toplevel(self.root)
        top.title("Linux 内核 module / firmware / eBPF 只读体检")
        top.geometry("880x700")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("Linux 内核 module / firmware / eBPF：按 kernel.org 源码组织方式只读体检")
        put("=" * 72)
        for line in nk.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("内核源码文档引用（对照 kernel.org Documentation）：")
        for line in nk.kmod_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("明确不执行的高危命令（只给指引）：")
        for c in nk.FORBIDDEN_COMMANDS:
            put("  · " + c)

        put("")
        put("-" * 68)
        put("逐项体检明细（只读）：")
        for fn_name, label in nk.KMOD_PROBES:
            ok, msg = getattr(nk, fn_name)()
            put("")
            put(f"-- {label} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("kmod_")]
        put(f"内核 module/firmware/eBPF 任务（kmod_*）：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<20} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_profiles(self):
        """弹出「任务档位」窗口：大而全(full) / 小而全(minimal) 四档 + 场景档。

        档位只决定「默认列入哪些任务」，**不改变执行确认逻辑**——
        选 full 也仍需 --apply/--opt-in/--yes 三重确认。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import profiles as pf
        from .detect import detect

        top = tk.Toplevel(self.root)
        top.title("任务档位（大而全 / 小而全）")
        top.geometry("860x700")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        try:
            info = detect()
            plat, ver = info.get("platform", "any"), info.get("version") or "0"
        except Exception:  # noqa: BLE001
            plat, ver = "any", "0"

        put("=" * 72)
        put(f"任务档位｜当前平台={plat} 版本={ver}")
        put("=" * 72)
        put("档位只决定「默认列入哪些任务」；执行仍需 --apply，")
        put("含 opt_in 的档位另需 --opt-in + --yes —— 选档位 ≠ 授权执行。")
        put("")
        for line in pf.profile_list(plat, ver):
            put(line)
        put("")
        for line in pf.scenario_list(plat):
            put(line)

        put("")
        put("-" * 68)
        for name in pf.PROFILE_ORDER:
            s = pf.profile_summary(name, plat, ver)
            put("")
            put(f"【{name}】{s.get('title','')} — 命中 {s.get('count',0)} 项")
            if s.get("categories"):
                put("   分类分布: " + "  ".join(
                    f"{k}={v}" for k, v in sorted(s["categories"].items(),
                                                  key=lambda kv: -kv[1])))
            put(f"   含 opt_in: {'有' if s.get('has_opt_in') else '无'}；"
                f"含高危: {'有' if s.get('has_high_risk') else '无'}")

        put("")
        put("-" * 68)
        put("对比（minimal vs full 的 Jaccard 重合度）：")
        r = pf.compare_profiles("minimal", "full", plat, ver)
        put(f"   minimal={r['count_a']} 项，full={r['count_b']} 项，"
            f"Jaccard={r['jaccard']:.4f}")
        put(f"   仅 minimal 有: {len(r['only_a'])} 项（0 表示 minimal 是 full 的真子集）")
        put(f"   仅 full 有: {len(r['only_b'])} 项")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_channels(self):
        """弹出「版本通道」窗口：stable 常态稳定版 / lts 长期支持版 / fresh 尝鲜版。

        完全图形界面控制：用户在 GUI 里选通道并「选定」，仅写入 settings.json 作
        更新检查标记；**工具绝不自动切换或升级你的环境**——是否更新始终由用户确认。
        同时据「使用量 / 期望年限 / 环境」给个性化推荐（接入 durability 维度）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import profiles as pf
        from .native import settings as st

        top = tk.Toplevel(self.root)
        top.title("版本通道（发布流选择；选定仅记偏好，绝不自动升级）")
        top.geometry("880x760")

        # 上：控制区（使用量/年限/环境 → 推荐；通道单选 → 选定）
        ctl = ttk.LabelFrame(top, text="你的长期使用需求（决定推荐哪个通道）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="使用量:").pack(side="left")
        usage_var = tk.StringVar(value="moderate")
        ttk.OptionMenu(f1, usage_var, "moderate", "light", "moderate", "heavy").pack(side="left", padx=4)
        ttk.Label(f1, text="期望年限(年):").pack(side="left", padx=(10, 0))
        years_var = tk.StringVar(value="4")
        ttk.Spinbox(f1, from_=1, to=10, textvariable=years_var, width=5).pack(side="left", padx=4)
        ttk.Label(f1, text="环境(逗号分隔):").pack(side="left", padx=(10, 0))
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=26).pack(side="left", padx=4)

        f2 = ttk.Frame(ctl)
        f2.pack(fill="x", padx=6, pady=4)
        rec_var = tk.StringVar(value="")
        ttk.Button(f2, text="据画像推荐通道",
                   command=lambda: _do_recommend()).pack(side="left", padx=4)
        ttk.Label(f2, textvariable=rec_var, foreground="blue").pack(side="left", padx=8)

        def _do_recommend():
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            try:
                yrs = int(years_var.get() or 4)
            except ValueError:
                yrs = 4
            rec = pf.channel_recommend(usage_var.get(), yrs, envs)
            rec_var.set(f"→ 推荐：{rec}（{pf.CHANNELS[rec]['title']}）")
            ch_var.set(rec)

        # 通道单选
        ch_frame = ttk.LabelFrame(top, text="选择版本通道（选定仅写偏好，绝不自动升级）")
        ch_frame.pack(fill="x", padx=8, pady=6)
        ch_var = tk.StringVar(value=st.get("channel", "stable") or "stable")
        for name in pf.CHANNEL_ORDER:
            ch = pf.CHANNELS[name]
            ttk.Radiobutton(ch_frame, text=f"{name} — {ch['title']}",
                            variable=ch_var, value=name).pack(anchor="w", padx=8, pady=1)

        def _select():
            name = ch_var.get()
            if name not in pf.CHANNELS:
                messagebox.showwarning("未知通道", name)
                return
            ok, _, why = st.set_value("channel", name)
            if ok:
                messagebox.showinfo("已写入偏好",
                                    f"通道偏好已写入 settings.json：{name}（{pf.CHANNELS[name]['title']}）\n"
                                    "注意：仅作更新检查标记，不会自动切换或升级你的环境。")
            else:
                messagebox.showerror("写入失败", why)

        ttk.Button(ch_frame, text="选定此通道（仅写偏好）", command=_select).pack(anchor="w", padx=8, pady=4)

        # 下：详情文本框
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("版本通道（发布流选择）")
        put("=" * 72)
        put("通道只决定你接收更新的发布流；选定后写入 settings.json 仅作更新检查标记，")
        put("**工具绝不自动切换或升级你的环境**——是否更新始终由你确认。")
        put("")
        for line in pf.channel_list():
            put(line)
        put("")
        put("-" * 68)
        for name in pf.CHANNEL_ORDER:
            put("")
            put(pf.channel_detail(name))
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_durability(self):
        """弹出「设备长期使用保护」窗口（v0.6.30）。

        完全图形界面控制：用户在 GUI 里选使用量/期望年限/环境标签，即时看到个性化
        保护报告（传感器采集 → 知识库目标包络 → 健康评分 → 保养清单 + 优化建议）。
        所有写设备动作只给 OEM 官方工具指引，不代执行——严守只读红线。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import durability as nd

        top = tk.Toplevel(self.root)
        top.title("设备长期使用保护（只读采集 + 知识库保养，不写设备）")
        top.geometry("900x720")

        ctl = ttk.LabelFrame(top, text="你的设备与长期使用需求（决定保养方案）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="使用量:").pack(side="left")
        usage_var = tk.StringVar(value="moderate")
        ttk.OptionMenu(f1, usage_var, "moderate", "light", "moderate", "heavy").pack(side="left", padx=4)
        ttk.Label(f1, text="期望年限(年):").pack(side="left", padx=(10, 0))
        years_var = tk.StringVar(value="4")
        ttk.Spinbox(f1, from_=1, to=10, textvariable=years_var, width=5).pack(side="left", padx=4)
        ttk.Label(f1, text="环境(逗号分隔):").pack(side="left", padx=(10, 0))
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=26).pack(side="left", padx=4)

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            try:
                yrs = int(years_var.get() or 4)
            except ValueError:
                yrs = 4
            usage = usage_var.get() or "moderate"
            put("=" * 72)
            put(f"设备长期使用保护｜使用量={usage} 期望年限={yrs}年 环境={envs or '默认'}")
            put("=" * 72)
            put("只读采集传感器，读不到即标「本机未提供」（不伪造）；写设备只给 OEM 指引。")
            put("")
            put("-- 本机传感器可用项 --")
            for line in nd.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（天气/气候/材料/耐久/保养/水汽异物）--")
            for line in nd.durability_doc_list():
                put(line)
            put("")
            put("-- 本机传感器核对（只读）--")
            for fn_name, lab in nd.PROBES:
                ok, msg = getattr(nd, fn_name)()
                put(f"   · {lab}: {'✓ 可用' if ok else '✗ 不适用'}")
                if msg:
                    if isinstance(msg, (dict, list)):
                        import json as _json
                        msg = _json.dumps(msg, ensure_ascii=False)
                    put("       " + str(msg).replace("\n", "\n       "))
            put("")
            put("-- 端到端保护报告 --")
            ok, rep = nd.durability_report(usage, yrs, envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- OEM 官方工具指引（此处只展示不调用）--")
            for line in nd.durability_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成保护报告", command=_render).pack(side="left", padx=4)
        # 首次打开即渲染一份默认画像
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_electrical(self):
        """弹出「供电与环境安全」窗口（v0.6.38）。

        完全图形界面控制：用户在 GUI 里填写供电环境标签（旧线/铜铝/无接地/木座/
        松动插座/高发热负载/多尘），即时看到自适应安全报告（识别电气火灾事故前兆链条
        → 长期保障运行建议）。本工具只读感知 + 出方案，电气改造由持证电工按规范执行。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import electrical as ne

        top = tk.Toplevel(self.root)
        top.title("供电与环境安全（只读感知 + 知识库自适应，绝不碰配电箱）")
        top.geometry("900x720")

        ctl = ttk.LabelFrame(top, text="你的供电环境（决定风险识别与自适应方案）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="供电环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=48).pack(side="left", padx=4)
        ttk.Label(f1, text="例: old_wiring,copper_aluminum,no_ground,wood_base,loose_outlet,overload_risk,high_dust"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"供电与环境安全｜供电环境标签={envs or '未声明（默认低风险基线）'}")
            put("=" * 72)
            put("只读感知供电环境 + 本机温度，绝不测接触电阻、绝不碰配电箱；电气改造由持证电工执行。")
            put("")
            put("-- 本机可读信号（只读）--")
            for line in ne.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（8 类电气火灾隐患机理与标准）--")
            for line in ne.electrical_doc_list():
                put(line)
            put("")
            put("-- 端到端供电与环境安全报告 --")
            ok, rep = ne.electrical_safety_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ne.electrical_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成安全报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_acoustics(self):
        """弹出「声学与音律」窗口（v0.6.87）。

        四轴：声学基础（频率/波长/声速/共振/分贝，IEC 61672）→ 中国音律
        （黄钟大吕·三分损益十二律）→ 无线电磁（ITU ISM 频段与 λ/4 天线）→
        音频硬件（IEC 60268 / EN 50332 喇叭耳机标准）。只读枚举与工程换算，
        绝不播放声音、绝不调音量、绝不采集麦克风内容、无任何射频发射路径。
        """
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title("声学与音律（只读 + 工程换算，绝不发声/调音量/采集声音/发射射频）")
        top.geometry("920x760")

        ctl = ttk.LabelFrame(top, text="基准频率（Hz，仅作三分损益换算基准；不宣称复原古音高）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="黄钟基准频率:").pack(side="left")
        base_var = tk.StringVar(value="261.6256")
        ttk.Entry(f1, textvariable=base_var, width=14).pack(side="left", padx=4)
        ttk.Label(f1, text="默认 C4=261.6256 Hz；黄钟绝对音高各代不同（needs_verify）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            try:
                base = float(base_var.get().strip() or "261.6256")
            except ValueError:
                base = 261.6256
            from .native import acoustics as na
            put("=" * 74)
            put(f"声学与音律｜黄钟基准频率 = {base} Hz（仅换算基准）")
            put("=" * 74)
            put("红线：只读设备存在性、只做数学换算——绝不播放任何声音、绝不调音量、"
                "绝不采集麦克风内容、无任何射频发射路径。")
            put("")
            put("-- 本机音频设备（只读枚举，ALSA/PulseAudio 能力面）--")
            for line in na.devices_report()[1].splitlines():
                put(line)
            put("")
            put("-- 波动几何换算（c = f·λ；空气 331.3+0.606·T，20 °C 时 343 m/s）--")
            for line in na.conversion_report()[1].splitlines():
                put(line)
            put("")
            put("-- 三分损益十二律 --")
            put("   律名   阴阳   管长      频率(Hz)   偏离平均律")
            for e in na.sanfen_sunyi(base):
                cents = e.get("cents_vs_et")
                ctxt = f"{cents:+.2f} 音分" if cents is not None else "—"
                put(f"   {e['lvlv']:<4}  {e['yin_yang']}  {e['length']:<8}  "
                    f"{e['freq_hz']:<9.2f}  {ctxt}")
            put("   注：自林钟起每律约 +1.96 音分（comma÷12）；清黄钟管长 39.9549 ≠ 40.5，"
                "即「黄钟不能还原」。")
            put("")
            put("-- 知识库引用（data/acoustics_docs.json）--")
            for line in na.acoustics_doc_list():
                put(line)
            put("")
            put("-- 听力保护参照（EN 50332 限值）--")
            for line in na.hearing_protection_guide()[1].splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成声学报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_sysbase(self):
        """弹出「系统基座」窗口（v0.6.88）。

        五轴：系统目录（FHS/LFS）→ 软件包格式（deb/rpm）→ 网络包管理器（apt/yum 仓库）→
        Metasploit 分发与检测 → 路径与命名空间（相对路径机理 + 互联网即目录服务）。只读盘点，
        不安装/卸载、不动仓库源与密钥、不启动 msfconsole、不写任何系统目录。
        """
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title("系统基座（只读 + 知识库驱动，绝不改动系统）")
        top.geometry("920x760")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            from .native import sysbase as na
            put("=" * 74)
            put("系统基座｜只读：系统目录 · 包管理 · 网络仓库 · 安全检测")
            put("=" * 74)
            put("红线：只读感知——不安装/卸载软件、不动仓库源与密钥、"
                "不启动 msfconsole 跑任何模块、不写任何系统目录。")
            put("")
            for line in na.sysbase_report()[1].splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="生成系统基座报告", command=_render).pack(side="left", padx=8, pady=(0, 8))
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_sysdev(self):
        """弹出「从零造系统学习应用」窗口（v0.6.89）。

        pepsipu 项目群 7 仓库（warpalloc/aski/xinOS-old/OSpaint/ramenbox/cx/torus）的
        模式+边界学习 + 本机工具链与 glibc malloc 只读体检。绝不编译/运行被分析的
        第三方源码、绝不修改 malloc 环境变量、绝不 vendored 第三方源代码。
        """
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title("从零造系统学习应用（只读 + 知识库驱动，绝不代跑第三方源码）")
        top.geometry("920x760")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            from .native import sysdev as na
            put("=" * 74)
            put("从零造系统学习应用｜只读：分配器 · 编译器 · 玩具 OS · 模拟器")
            put("=" * 74)
            put("红线：学习不等于打包——不编译/运行第三方源码、不改 malloc 环境变量、"
                "不 vendored 第三方源代码（MIT/BSD 学模式，无许可证只学思想）。")
            put("")
            for line in na.sysdev_report()[1].splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="生成学习应用报告", command=_render).pack(side="left", padx=8, pady=(0, 8))
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_docs(self):
        """弹出「文档与概念联动」窗口（v0.6.88）。

        docs/ 文档层作为联动网格一等节点：枚举 docs/ 规范化文档清单，并把文档层
        接入联动网格（被 subsystems/linkage/sysbase 供给与印证）。只读枚举与交叉
        引用，不写任何文件、不执行命令、不修改系统。
        """
        tk, ttk, messagebox, scrolledtext = _tk()

        top = tk.Toplevel(self.root)
        top.title("文档与概念联动（只读 + 文档驱动，绝不改动系统）")
        top.geometry("920x760")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            from .native import docs as na
            put("=" * 74)
            put("文档与概念联动｜只读：docs/ 文档层 · 联动网格一等节点")
            put("=" * 74)
            put("红线：只读感知——不写任何文件、不执行命令、不修改系统；"
                "仅枚举文档与交叉引用。")
            put("")
            for line in na.docs_report()[1].splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="生成文档与概念联动报告", command=_render).pack(side="left", padx=8, pady=(0, 8))
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_androidstd(self):
        """弹出「国内标准 · Android/App 隐私合规」窗口（v0.6.67）。

        展示中国境内 App 隐私合规四层标准体系（PIPL 上位法 → GB/T 国标 →
        四部门规定 → TC260 实践指南，全部官方源实检），并给出用户视角的
        App 合规检查清单（每条回链知识库）。只读知识库：不扫描任何 App、
        不代执法、不代申诉；判定与行动（投诉/12321/监管渠道）留给用户。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import androidstd as na

        top = tk.Toplevel(self.root)
        top.title("国内标准 · Android/App 隐私合规（只读知识库，不扫描、不代执法）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("国内标准 · Android/App 隐私合规｜PIPL → GB/T 国标 → 四部门规定 → TC260")
        put("=" * 72)
        put("定位：只读知识库 + 出检查项；不是合规认证、不代执法。")
        put("")
        put("-- 标准/法规清单（数据经 openstd/cac/miit/gov/tc260 官方源实检）--")
        for line in na.androidstd_doc_list():
            put(line)
        put("")
        put("-- App 合规检查清单（用户视角，人工执行）--")
        for i, c in enumerate(na.app_compliance_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（androidstd_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("androidstd_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_cnstd(self):
        """弹出「国内标准资源」窗口（v0.6.90）。

        展示 14 个国内标准资源（2026-10-25 逐只读抓取）的四层体系：官方源
        五平台（openstd 国标全文公开 / std.samr 公共服务 / hbba 行标备案 /
        CCSA / 合同示范文本库）+ 协议规范两组（Modbus 六规范 / MQTT）+
        第三方三家（spc 商业付费 / biaozhuns 分享站 / RFC 中文翻译）+ 概念
        科普三篇。只读知识库：不联网代查、不代下载、不破解付费/受限资源。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import cnstd as nc

        top = tk.Toplevel(self.root)
        top.title("国内标准资源（官方平台/协议规范/第三方/概念，只读知识库）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("国内标准资源｜官方平台 → 协议规范 → 第三方渠道 → 概念科普（14 源，2026-10-25 实测）")
        put("=" * 72)
        put("定位：只读知识库 + 出索引；不代查、不代下载、不破解付费/受限资源。")
        put("")
        put("-- 资源清单（规模数字为官方源检索日实测）--")
        for line in nc.cnstd_doc_list():
            put(line)
        put("")
        put("-- 官方三平台检索路径（全文/状态/备案分工）--")
        ok, guide = nc.cnstd_lookup_guide()
        if ok:
            put(guide)
        put("")
        put("-- 协议规范选用（Modbus 六规范 + MQTT）--")
        ok, proto = nc.cnstd_protocol_guide()
        if ok:
            put(proto)
        put("")
        put("-- 涉及任务（cnstd_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("cnstd_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_gmsstd(self):
        """弹出「GMS 标准 · GMS 兼容与 Play 上架」窗口（v0.6.67）。

        展示 GMS 兼容与 Play 上架标准体系（CDD/CTS/VTS/STS → GMS 许可 →
        Play 三件套 → Data safety → 安全公告补丁，除 STS 细节外全部官方源
        实检），并给出上架自查清单（每条回链知识库）。只读知识库：不扫描、
        不联网、不代审；判定与行动留给用户与 Google 官方。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import gmsstd as ng

        top = tk.Toplevel(self.root)
        top.title("GMS 标准 · GMS 兼容与 Play 上架（只读知识库，不扫描、不代审）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("GMS 标准 · GMS 兼容与 Play 上架｜CDD/CTS/VTS/STS → GMS 许可 → Play 三件套")
        put("=" * 72)
        put("定位：只读知识库 + 出检查项；不是认证、不代审。")
        put("")
        put("-- 标准/规范清单（官方源实检；STS 细节为社区整理并标注）--")
        for line in ng.gmsstd_doc_list():
            put(line)
        put("")
        put("-- GMS/Play 上架自查清单（用户视角，人工执行）--")
        for i, c in enumerate(ng.gms_compliance_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（gmsstd_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("gmsstd_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_fdroidstd(self):
        """弹出「F-Droid 标准 · 免 GMS 自由软件分发」窗口（v0.6.67）。

        展示 F-Droid 分发标准体系（存储库模型 → 收录政策 → 反特征 → fdroiddata
        配方 → 可复现构建 → 仓库协议 → 免 GMS 国内分发，事实经 GitHub/GitLab
        API 与官方文档检索快照实检），并给出收录/分发自查清单（每条回链
        知识库）。只读知识库：不扫描、不联网、不代分发；装什么、加哪个仓库
        的判定与行动留给用户。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import fdroidstd as nf

        top = tk.Toplevel(self.root)
        top.title("F-Droid 标准 · 免 GMS 自由软件分发（只读知识库，能下载即可安装）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("F-Droid 标准 · 免 GMS 自由软件分发｜收录政策 → 反特征 → 可复现构建 → 仓库协议")
        put("=" * 72)
        put("定位：只读知识库 + 出检查项；不是认证、不代分发。")
        put("")
        put("-- 标准/规范清单（官方/GitHub/GitLab 实检）--")
        for line in nf.fdroidstd_doc_list():
            put(line)
        put("")
        put("-- F-Droid 收录/分发自查清单（用户视角，人工执行）--")
        for i, c in enumerate(nf.fdroid_compliance_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（fdroidstd_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("fdroidstd_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_hmos_ecosystem(self):
        """弹出「鸿蒙生态 · HAP/侧载/版图/版本/工具链」窗口（v0.6.71）。

        展示 HarmonyOS/OpenHarmony 生态知识库（HAP 工程 → 侧载工具链 →
        NEXT 生态版图 → 版本关系 → 开发工具链 → Codelabs 构建块图谱 → FA/Stage
        范式演进），并给出生态评估自检清单（每条回链知识库）。只读知识库：
        不扫描、不联网、不代执行安装/签名；判定与行动留给用户。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import hmos_ecosystem as nh

        top = tk.Toplevel(self.root)
        top.title("鸿蒙生态 · HarmonyOS/OpenHarmony（只读知识库，不扫描、不代执行）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("鸿蒙生态 · HAP 工程 → 侧载工具链 → NEXT 版图 → 版本线 → 工具链 → IoT")
        put("=" * 72)
        put("定位：只读知识库 + 出检查项；社区源 needs_verify，不代执行安装/签名。")
        put("")
        put("-- 知识条目（data/hmos_ecosystem_docs.json：8 条）--")
        for line in nh.hmos_doc_list():
            put(line)
        put("")
        put("-- 生态评估自检清单（用户视角，人工执行）--")
        for i, c in enumerate(nh.hmos_compliance_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（hmoseco_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("hmoseco_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_hmosstd(self):
        """弹出「HarmonyOS 标准 · 权限/隐私/上架/安全」窗口（v0.6.72）。

        展示 HarmonyOS NEXT 标准与合规知识库（PIPL → AppGallery 上架 →
        App 备案 → 权限 APL 分级 → 隐私指示器 → HUKS/TEE/加解密 → 版本兼容 →
        未成年人保护 → 后台与网络 → XTS 兼容测试），并给出合规对照清单
        （每条回链知识库）。只读知识库：不扫描、不联网、不代审、不下结论；
        判定与行动留给用户与官方来源。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import hmosstd as nh

        top = tk.Toplevel(self.root)
        top.title("HarmonyOS 标准 · 权限/隐私/上架/安全（只读知识库，不代审、不下结论）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("HarmonyOS 标准 · PIPL → AppGallery 上架 → App 备案 → 权限/隐私 → 安全 → 测试")
        put("=" * 72)
        put("定位：只读知识库 + 出对照项；不是认证、不代审、不下合规结论。")
        put("")
        put("-- 标准/法规清单（法规原文 + 官方源口径；社区整理 needs_verify）--")
        for line in nh.hmosstd_doc_list():
            put(line)
        put("")
        put("-- 鸿蒙 App 合规对照清单（用户视角，人工执行）--")
        for i, c in enumerate(nh.hmosstd_compliance_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（hmosstd_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("hmosstd_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_reverse(self):
        """弹出「黑箱逆向与调试工具链」窗口（v0.6.73）。

        展示 UPX/GDB/MinGW 沙箱实测沉淀（UPX 壳三特征/节区解剖/熵判据/
        GDB 四连/strip 前后对比/只读边界），并给出黑箱对照清单。只读：
        不执行目标、不 patch、不 hook、不生成绕过手段。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import reverse as nr

        top = tk.Toplevel(self.root)
        top.title("黑箱逆向与调试工具链（只读，不执行、不绕过）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("黑箱逆向 · UPX 壳识别 → 节区解剖 → 熵判据 → MinGW 造样本 → GDB 四连")
        put("=" * 72)
        put("定位：只读分析；不执行目标、不 patch、不 hook、不生成绕过手段。")
        put("")
        put("-- 知识条目（data/reverse_docs.json，沙箱实测口径）--")
        for line in nr.reverse_doc_list():
            put(line)
        put("")
        put("-- 黑箱对照清单（用户视角，人工执行）--")
        for i, c in enumerate(nr.reverse_checklist(), 1):
            put(f"  {i:>2}. [{c['severity']}] {c['title']}  ({c['rationale']})")
        put("")
        put("-- 涉及任务（reverse_*，执行需 --apply；均为指引类）--")
        for t in [t for t in registry.all_tasks() if t.id.startswith("reverse_")]:
            put(f"· {t.id} [{t.category}/{t.risk}] {t.display_title()}")
        box.see("1.0")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_peripheral(self):
        """弹出「外部设备连接与兼容」窗口（v0.6.39）。

        完全图形界面控制：用户在 GUI 里填写设备标签（星闪/触控屏/精确触控板/手写笔/
        USB-C PD/HID/外部温湿度计），即时看到兼容报告（整体引入星闪标准→触控技术支持→
        USB-C PD/HID 兼容）。本工具只读识别 + 出方案，绝刷固件/装私有驱动/挂钩输入流。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import peripheral as npf

        top = tk.Toplevel(self.root)
        top.title("外部设备连接与兼容（只读识别 + 星闪标准引入，绝不刷固件/装驱动）")
        top.geometry("900x720")

        ctl = ttk.LabelFrame(top, text="你的外部设备（决定标准引入与兼容方案）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="设备标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=52).pack(side="left", padx=4)
        ttk.Label(f1, text="例: nearlink_desired,touchscreen,touchpad,stylus,usb_c_pd,legacy_usb,hid_device,external_env_sensor"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"外部设备连接与兼容｜设备标签={envs or '未声明（默认基线）'}")
            put("=" * 72)
            put("只读识别触控/USB-C PD/HID 外设与多点触控协议，整体引入星闪标准；"
                "绝不刷固件、绝不装私有驱动、绝不挂钩输入流。")
            put("")
            put("-- 本机可读信号（只读）--")
            for line in npf.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（星闪/触控/USB-C PD/HID）--")
            for line in npf.peripheral_doc_list():
                put(line)
            put("")
            put("-- 端到端外部设备连接与兼容报告 --")
            ok, rep = npf.peripheral_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in npf.peripheral_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成兼容报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_chrono(self):
        """弹出「时空与全维度管理器」窗口（v0.6.40）。

        完全图形界面控制：用户在 GUI 里填写维度标签（time/space/spacetime/future_compat/
        quantum_lens），即时看到全时空全维度报告（量子/计算机原理透镜 → 时间维 → 空间维 →
        施时空组合维 → 未来兼容维 → 循环往复管理器）。本工具只读观测 + 出方案，绝不改时钟/
        时区/分区/升级组件。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import chrono as ncf

        top = tk.Toplevel(self.root)
        top.title("时空与全维度管理器（量子/计算机原理 + 时间/空间/施时空组合/未来兼容，只读不写）")
        top.geometry("920x760")

        ctl = ttk.LabelFrame(top, text="你的维度诉求（决定时空观测与循环往复观察范围）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="维度标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=52).pack(side="left", padx=4)
        ttk.Label(f1, text="例: time,space,spacetime,future_compat,quantum_lens（留空=全维度）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"时空与全维度管理器｜维度标签={envs or '未声明（默认全维度注册表）'}")
            put("=" * 72)
            put("以量子/计算机原理为只读观测透镜，观察时间/空间/施时空组合/未来兼容维；"
                "全时空全维度循环往复管理器（round-robin 周而复始、每维一视同仁）。只读不写。")
            put("")
            put("-- 本机可读信号（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（量子/计算机原理/时间/空间/施时空组合/未来兼容）--")
            for line in ncf.chrono_doc_list():
                put(line)
            put("")
            put("-- 端到端时空与全维度报告 --")
            ok, rep = ncf.chrono_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.chrono_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成全维度报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_virt(self):
        """弹出「虚拟机环境」窗口（v0.6.41）。

        完全图形界面控制：用户填写环境标签（kvm/vmware/hyperv/virtualbox/xen/wsl/container/
        baremetal）即时看到虚拟机环境报告（识别层→退化计划→子系统影响）。本工具只读识别与降级，
        绝不装增强工具/改 QEMU-crosvm 配置/加载内核模块。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import virt as ncf

        top = tk.Toplevel(self.root)
        top.title("虚拟机环境（识别虚拟化层 + 不同 VM 内优雅降级，只读不写）")
        top.geometry("920x720")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定虚拟化识别与退化范围）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: kvm,vmware,hyperv,virtualbox,xen,wsl,container,baremetal（留空=自动识别）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"虚拟机环境｜环境标签={envs or '未声明（自动识别）'}")
            put("=" * 72)
            put("只读识别虚拟化层；受限 VM 退化为概念观测、裸金属全开；绝不装增强工具/改配置/加载模块。")
            put("")
            put("-- 本机虚拟化探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端虚拟机环境报告 --")
            ok, rep = ncf.virt_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.virt_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成虚拟机环境报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_packages(self):
        """弹出「软件包规范审计」窗口（v0.6.41）。

        完全图形界面控制：用户填写环境标签（apt/dnf/pacman/brew/winget/choco/apk/scoop/zypper）
        即时看到软件包规范审计报告（检测→安装/卸载/配置/设置优化四类操作层级应对）。本工具只审计
        + 出指引，绝不 install/uninstall/configure/optimize 任何包。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import packages as ncf

        top = tk.Toplevel(self.root)
        top.title("软件包规范审计（按系统/硬件/相关软件包检测包管理器 + 四类操作层级应对，只读不写）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定包管理器与规范口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: apt,dnf,pacman,brew,winget,choco,apk,scoop,zypper（留空=自动检测）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"软件包规范审计｜环境标签={envs or '未声明（自动检测）'}")
            put("=" * 72)
            put("按系统/硬件/相关软件包检测包管理器；安装/卸载/配置/优化一律走官方接口、不手工改库。")
            put("")
            put("-- 本机包管理器探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端软件包规范审计报告 --")
            ok, rep = ncf.packages_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.packages_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成包规范审计报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_apctrl(self):
        """弹出「AP 集中控制器」窗口（v0.6.42，学习 apcontroller）。

        完全图形界面控制：用户填写环境标签（openwrt/hostapd/networkmanager/dnsmasq/apcontroller）
        即时看到 AP 控制器集中报告（控制面识别→AP Group 下发 WiFi→用户脚本）。本工具只读识别与下发
        指引，绝不下发 AP 配置/读私钥/改写现有 hostapd/dnsmasq。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import apctrl as ncf

        top = tk.Toplevel(self.root)
        top.title("AP 集中控制器（学习 apcontroller：只读识别 + AP Group 下发 WiFi，不写配置/不下发）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定 AP 控制面识别范围）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: openwrt,hostapd,networkmanager,dnsmasq,apcontroller（留空=自动识别）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"AP 集中控制器｜环境标签={envs or '未声明（自动识别）'}")
            put("=" * 72)
            put("只读识别 hostapd/NetworkManager/dnsmasq/apcontroller 控制面；AP Group 下发 WiFi 只给指引。")
            put("绝不读私钥/改 hostapd 配置/下发 AP 配置。")
            put("")
            put("-- 本机 AP 控制面探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端 AP 集中控制器报告 --")
            ok, rep = ncf.apctrl_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.apctrl_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成 AP 集中控制器报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_llvm(self):
        """弹出「LLVM 工具链」窗口（v0.6.42，新增编程语言与交叉编译）。

        完全图形界面控制：用户填写环境标签（clang/lld/mlir/aarch64/riscv64/wasm32/mingw...）即时看到
        LLVM 工具链报告（clang/lld/mlir 探针→已建目标→交叉编译指引）。本工具只读探测与 sysroot 指引，
        绝不编译/下载 sysroot/改写工具链。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import llvm as ncf

        top = tk.Toplevel(self.root)
        top.title("LLVM 工具链（v0.6.42：clang/lld/mlir 探测 + 8 交叉目标 + 交叉编译 sysroot 指引）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定交叉编译目标与工具链口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: clang,lld,mlir,aarch64,riscv64,wasm32,mingw（留空=自动探测）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"LLVM 工具链｜环境标签={envs or '未声明（自动探测）'}")
            put("=" * 72)
            put("只读探测 clang/lld/mlir 与已建交叉目标；交叉编译只给 sysroot 指引，绝不编译/下载 sysroot。")
            put("")
            put("-- 本机 LLVM 探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端 LLVM 工具链报告 --")
            ok, rep = ncf.llvm_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.llvm_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成 LLVM 工具链报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_asm(self):
        """弹出「汇编语言优化」窗口（v0.6.43，新增汇编语言优化）。

        完全图形界面控制：用户填写环境标签（nasm/yasm/gas/llvm_mc/gcc_s）即时看到
        汇编语言优化报告（汇编器探针→SIMD 矩阵→优化要点→LLVM 交叉汇编指引）。本工具只读探测与优化要点，
        绝不编译/改源码/写汇编文件。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import asm as ncf

        top = tk.Toplevel(self.root)
        top.title("汇编语言优化（v0.6.43：nasm/yasm/gas/llvm-mc/gcc -S 探测 + SIMD 优化要点 + 交叉汇编指引）")
        top.geometry("940x760")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定汇编器与 SIMD 口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: nasm,yasm,gas,llvm_mc,gcc_s（留空=自动探测）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"汇编语言优化｜环境标签={envs or '未声明（自动探测）'}")
            put("=" * 72)
            put("只读探测汇编器并给优化要点（向量化/对齐/寄存器/缓存/分支/指令/内联约束）；"
                "交叉汇编只给 clang -target=<triple> -S 指引，绝不编译/改源码/写汇编文件。")
            put("")
            put("-- 本机汇编器探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端汇编语言优化报告 --")
            ok, rep = ncf.asm_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.asm_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成汇编语言优化报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_toolchain(self):
        """弹出「工具链全景」窗口（0000.0000.0000.0004.20261024）。

        按「类别 × 目标架构 × 仓库目录」三维编目宿主工具链与仓库工具软件
        （data/toolchain_catalog.json），并对本机工具链逐项 which + --version 实采。
        只读探测与编目；安装/构建/下载一律只给指引，不代执行。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import toolchain as ntc

        top = tk.Toplevel(self.root)
        top.title("工具链全景（v0004：宿主工具链×仓库工具软件×目标架构矩阵，只读不写）")
        top.geometry("980x780")

        ctl = ttk.LabelFrame(top, text="维度标签（决定编目口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="维度标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: cross-compile,native-build,mingw,ndk,ohos（留空=全量）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"工具链全景｜维度标签={envs or '未声明（全量）'}")
            put("=" * 72)
            put("分类别（交叉编译/原生构建/仿真/打包/质量/安全检测/编辑器浏览器）× 目标架构 × 仓库目录；")
            put("只读探测与编目，安装/构建/下载一律只给指引。")
            put("")
            put("-- 编目全景 --")
            ok, rep = ntc.catalog_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 本机工具链实采（which + 版本实读）--")
            ok, rep = ntc.host_probe_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 仓库工具软件（目录+配置逻辑顺序+命令序列）--")
            ok, rep = ntc.repo_tools_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 目标架构矩阵 --")
            ok, rep = ntc.target_matrix_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 上游新鲜度 --")
            ok, rep = ntc.freshness_report()
            for line in rep.splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成工具链全景报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_meshnet(self):
        """弹出「组网与设备协同」窗口（v0.6.42，学习 Mullvad Meshnet）。

        完全图形界面控制：用户填写环境标签（wireguard/mullvad/zerotier/tailscale）即时看到组网报告
        （拓扑→设备能力适配→负载均衡与协同共享）。本工具只读 wg show 与能力适配建议，绝不配 VPN/
        改路由/下发 peer。来源缺口已显式标注。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import meshnet as ncf

        top = tk.Toplevel(self.root)
        top.title("组网与设备协同（v0.6.42：学习 Mullvad Meshnet 只读拓扑+能力适配+负载均衡）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定组网模型与设备协同口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: wireguard,mullvad,zerotier,tailscale（留空=自动识别）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"组网与设备协同｜环境标签={envs or '未声明（自动识别）'}")
            put("=" * 72)
            put("只读 wg show 拓扑 + 设备能力适配（算力/GPU/存储缓存）+ 负载均衡与协同共享建议。")
            put("绝不配 VPN/改路由/下发 peer；来源缺口已显式标注。")
            put("")
            put("-- 本机组网探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端组网与设备协同报告 --")
            ok, rep = ncf.meshnet_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.meshnet_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成组网与设备协同报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_matrix(self):
        """弹出「周天星斗大阵 · 数字矩阵冗余数据」窗口（v0.6.84）。

        完全图形界面控制：用户选择维度（缓存/临时/包管理缓存/回收站/日志）即时看到只读观测报告
        （星斗分布→合计→清理指引）。只读统计存在性与体积；denylist（个人数据与关键资产）完全不触碰；
        清理只给文本指引，由用户沿原路执行。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import matrix as ncf

        top = tk.Toplevel(self.root)
        top.title("周天星斗大阵 · 数字矩阵冗余数据（v0.6.84：缓存/临时/回收站/日志，只读不删）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="维度标签（决定只读统计的扫描面；denylist 永不涉足）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="维度标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: user-cache,tmp,pkg-cache,trash,log-rotate（留空=全量）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"周天星斗大阵｜维度标签={envs or '未声明（全量 allowlist）'}")
            put("=" * 72)
            put("指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
            put("只读统计冗余数据存在性与体积；denylist（个人数据与关键资产）完全不扫描、不统计、不清理。")
            put("")
            put("-- 本机冗余数据环境（只读概览）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端只读观测报告 --")
            ok, rep = ncf.matrix_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("安全不变量：只读观测 ≠ 授权清理——本面板不删除、不移动、不改写任何数据；")
            put("           清理由用户沿原路执行。")
            box.see("1.0")

        ttk.Button(ctl, text="生成只读观测报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_f2b(self):
        """弹出「十二都天神煞大阵 · fail2ban 学习应用」窗口（v0.6.84）。

        完全图形界面控制：用户选择咨询模板即时看到只读咨询报告（探测→jail 登记→模式学习→建议文本）。
        只读探测与解析；fail2ban 为 GPL-2.0 项目，不 vendored 其源码；配置建议仅文本，绝不代写、
        绝不代行封禁。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import f2b as ncf

        top = tk.Toplevel(self.root)
        top.title("十二都天神煞大阵 · fail2ban 学习应用（v0.6.84：探测/解析/模式学习，只读不写）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="咨询模板（配置建议仅文本——是否写入由用户沿原路执行）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="模板标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: sshd-basic,whitelist,graduated（留空=全部）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"十二都天神煞大阵｜模板标签={envs or '未声明（全部咨询模板）'}")
            put("=" * 72)
            put("指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
            put("只读探测安装状态、只读解析 jail 配置；不 vendored GPL-2.0 源码；不代写、不代行封禁。")
            put("")
            put("-- 本机 fail2ban 环境（只读概览）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端只读咨询报告 --")
            ok, rep = ncf.f2b_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("安全不变量：只读学习 ≠ 授权施工——不代写 jail.local、不重启 fail2ban、不代行封禁/解封。")
            box.see("1.0")

        ttk.Button(ctl, text="生成只读咨询报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_vdns(self):
        """弹出「虚拟根DNS与多CDN」窗口（v0.6.42）。

        完全图形界面控制：用户填写环境标签（resolved/stubby/cloudflared/doh/dot）即时看到虚拟根 DNS
        与多 CDN 报告（resolv.conf→DoH/DoT 识别→已知 CDN 命中→良性解析探测）。本工具只读配置与一次性
        良性解析，绝不改 resolv.conf/启用 DoH/切 DNS。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import vdns as ncf

        top = tk.Toplevel(self.root)
        top.title("虚拟根DNS与多CDN（v0.6.42：resolv.conf/DoH-DoT/已知CDN/良性解析探测，只读）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定 DNS 解析与 CDN 口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: resolved,stubby,cloudflared,doh,dot（留空=自动识别）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"虚拟根DNS与多CDN｜环境标签={envs or '未声明（自动识别）'}")
            put("=" * 72)
            put("只读 resolv.conf/DoH-DoT 配置 + 已知 CDN 命中 + 一次良性解析探测；绝不改 DNS/启用 DoH。")
            put("")
            put("-- 本机 DNS 探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端虚拟根DNS与多CDN报告 --")
            ok, rep = ncf.vdns_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.vdns_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成虚拟根DNS与多CDN报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_ipp(self):
        """弹出「IPP 打印发现」窗口（v0.6.42，RFC 8010/8011/IPP Everywhere）。

        完全图形界面控制：用户填写环境标签（cups/avahi/ipp-everywhere）即时看到 IPP 打印发现报告
        （CUPS 队列→mDNS IPP 服务→本机 631 控制台）。本工具只读队列与 mDNS 广播，绝不加打印机/改
        CUPS 配置/下发打印作业。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import ipp as ncf

        top = tk.Toplevel(self.root)
        top.title("IPP 打印发现（v0.6.42：CUPS/mDNS IPP/IPP Everywhere，只读发现不添加打印机）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定打印发现口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: cups,avahi,ipp-everywhere（留空=自动发现）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"IPP 打印发现｜环境标签={envs or '未声明（自动发现）'}")
            put("=" * 72)
            put("只读 CUPS 队列 + mDNS IPP 服务 + 本机 631 控制台；绝不添加打印机/改 CUPS/下发作业。")
            put("")
            put("-- 本机打印环境探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端 IPP 打印发现报告 --")
            ok, rep = ncf.ipp_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.ipp_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成 IPP 打印发现报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_display(self):
        """弹出「现代显示与GPU」窗口（v0.6.42，保留控制台/终端/远程终端）。

        完全图形界面控制：用户填写环境标签（x11/wayland/tty/nvidia/amd/intel/vulkan）即时看到现代显示
        与 GPU 报告（会话类型→GPU/vulkan/gl→分辨率→终端显式保留）。本工具只读显示拓扑，绝不装驱动/
        改 Xorg/Wayland 配置/切会话。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import display as ncf

        top = tk.Toplevel(self.root)
        top.title("现代显示与GPU（v0.6.42：会话/GPU/vulkan/分辨率，显式保留控制台与远程终端，只读）")
        top.geometry("940x740")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定显示与 GPU 口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: x11,wayland,tty,nvidia,amd,intel,vulkan（留空=自动识别）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"现代显示与GPU｜环境标签={envs or '未声明（自动识别）'}")
            put("=" * 72)
            put("只读会话类型/GPU/vulkan/分辨率；控制台/终端/SSH 远程终端显式保留；绝不装驱动/改会话。")
            put("")
            put("-- 本机显示环境探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端现代显示与GPU报告 --")
            ok, rep = ncf.display_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.display_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成现代显示与GPU报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_retro(self):
        """弹出「常态化回头看」窗口（v0.6.42，元能力/演进）。

        完全图形界面控制：用户填写环境标签（daily/weekly/monthly，决定维护节奏）即时看到常态化回头看
        报告（维护节奏→易漂移维度→长期使用只读汇总）。本工具只读汇总与提示，绝不改配置/跑写操作。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import retro as ncf

        top = tk.Toplevel(self.root)
        top.title("常态化回头看（v0.6.42：维护节奏表 + 易漂移维度 + 长期使用只读汇总，只读不写）")
        top.geometry("940x720")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定维护节奏口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: daily,weekly,monthly（留空=默认节奏）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"常态化回头看｜环境标签={envs or '未声明（默认节奏）'}")
            put("=" * 72)
            put("只读维护节奏表 + 易漂移维度 + 长期使用保护汇总；绝不改配置/跑写操作（久久为功）。")
            put("")
            put("-- 本机演进环境探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端常态化回头看报告 --")
            ok, rep = ncf.retro_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.retro_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成常态化回头看报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_restart(self):
        """弹出「人类文明重启透镜」窗口（v0.6.42，别名洪荒重启）。

        完全图形界面控制：用户填写环境标签（knowledge/manufacturing/talent/power，决定场景维度）即时
        看到人类文明重启透镜报告（六维场景→保命优先级→知识库离线沉淀）。本工具只读场景透镜与提示，
        绝不改配置/下发写操作。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import restart as ncf

        top = tk.Toplevel(self.root)
        top.title("人类文明重启透镜（v0.6.42 别名洪荒重启：六维场景+保命优先级+知识库离线，只读）")
        top.geometry("940x720")

        ctl = ttk.LabelFrame(top, text="你的环境标签（决定场景维度口径）")
        ctl.pack(fill="x", padx=8, pady=6)
        f1 = ttk.Frame(ctl)
        f1.pack(fill="x", padx=6, pady=4)
        ttk.Label(f1, text="环境标签(逗号分隔):").pack(side="left")
        env_var = tk.StringVar(value="")
        ttk.Entry(f1, textvariable=env_var, width=56).pack(side="left", padx=4)
        ttk.Label(f1, text="例: knowledge,manufacturing,talent,power（留空=全维度）"
                  ).pack(side="left", padx=(6, 0))

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            envs = [t.strip() for t in env_var.get().split(",") if t.strip()]
            put("=" * 72)
            put(f"人类文明重启透镜｜环境标签={envs or '未声明（全维度）'}")
            put("=" * 72)
            put("只读六维场景透镜 + 保命优先级 + 知识库离线沉淀提示；绝不改配置/下发写操作。")
            put("")
            put("-- 本机场景环境探测（只读）--")
            for line in ncf.environment_report():
                put(line)
            put("")
            put("-- 端到端人类文明重启透镜报告 --")
            ok, rep = ncf.restart_report(envs)
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 规范指引（此处只展示不调用）--")
            for line in ncf.restart_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(ctl, text="生成人类文明重启透镜报告", command=_render).pack(side="left", padx=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_remote(self):
        """弹出「远程接入与传输客户端」窗口（v0.6.30）。

        完全图形界面控制：用户在 GUI 里一键生成只读安全审计（telnet/ssh/filezilla/putty），
        看到明文风险与加固指引。**绝不读解密口令、绝不改 sshd_config、不替你停 telnetd**——
        是否操作始终由用户在 GUI/OEM 工具里确认。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import remote as nr

        top = tk.Toplevel(self.root)
        top.title("远程接入与传输客户端（只读审计 + 加固指引，不写配置）")
        top.geometry("900x700")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            put("=" * 72)
            put("远程接入与传输客户端｜只读安全审计（telnet/ssh/filezilla/putty）")
            put("=" * 72)
            put("各自按自身协议与接口核对；加固只给官方指引，绝不读解密口令/不改配置。")
            put("")
            put("-- 本机客户端可用项 --")
            for line in nr.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（SSH/Telnet/FileZilla/PuTTY）--")
            for line in nr.remote_doc_list():
                put(line)
            put("")
            put("-- 端到端只读安全审计 --")
            ok, rep = nr.remote_audit_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 加固/安全指引（此处只展示不调用）--")
            for line in nr.remote_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="生成只读审计", command=_render).pack(anchor="w", padx=8, pady=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_cert(self):
        """弹出「证书与加密」窗口（v0.6.31）。

        完全图形界面控制：用户在 GUI 里一键生成只读安全审计（OpenSSL 类开源加密栈 +
        硬件信任根 TPM/IDevID + 各种证书 X.509/ACME/FIDO）。**绝不读私钥、绝不解密、
        绝不改配置**——是否操作始终由用户在 GUI/OEM 工具里确认。输出为无障碍纯文本。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import cert as nc

        top = tk.Toplevel(self.root)
        top.title("证书与加密（只读审计 + 硬件信任根，不读私钥/不改配置）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            put("=" * 72)
            put("证书与加密｜只读安全审计（OpenSSL 类开源 + 硬件信任根 TPM/IDevID + 各种证书）")
            put("=" * 72)
            put("整合开源加密栈，只读审计；绝不读私钥、绝不解密、绝不改配置。")
            put("")
            put("-- 本机可用项 --")
            for line in nc.environment_report():
                put(line)
            put("")
            put("-- 知识库引用（OpenSSL/LibreSSL/GnuTLS/TPM/X.509/ACME/Keystore…）--")
            for line in nc.cert_doc_list():
                put(line)
            put("")
            put("-- 端到端只读安全审计 --")
            ok, rep = nc.cert_audit_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 加固/安全指引（此处只展示不调用）--")
            for line in nc.cert_tune_list():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="生成只读审计", command=_render).pack(anchor="w", padx=8, pady=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_linkage(self):
        """弹出「联动连轴」窗口（v0.6.33）：谁喂给谁 / 谁管着谁。

        完全图形界面控制：一键查看全部子系统之间的联动轴（每条标注供给 / 门控 /
        印证 / 闭环），以及两份待修清单——**孤岛**（登记进统一清单却一条边都没有，
        属「登记未嵌入」）与**悬空轴**（端点写错会静默失效）。
        纯计算只读：不跑任何诊断函数、不改任何状态。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import linkage

        top = tk.Toplevel(self.root)
        top.title("联动连轴体检（只读 · 纯计算，不跑诊断/不改状态）")
        top.geometry("900x720")

        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            put("=" * 72)
            put("联动连轴｜谁喂给谁 / 谁管着谁（供给 · 门控 · 印证 · 闭环）")
            put("=" * 72)
            put("纯计算只读：不跑任何诊断、不改任何系统状态，只看各子系统之间怎么联通。")
            put("")
            put("-- 能力自检 --")
            _ok, cap = linkage.capabilities_report()
            for line in cap.splitlines():
                put(line)
            put("")
            put("-- 联动轴全图 --")
            _ok2, rep = linkage.linkage_report()
            for line in rep.splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="重新体检", command=_render).pack(anchor="w", padx=8, pady=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_linkage_graph(self):
        """弹出「联动图」窗口（v0.6.34）：把 61 个子系统与近百条联动轴画成图。

        分层布局（按子系统所属层分列）、边按性质着色（供给绿 / 门控红 / 印证蓝 /
        闭环紫 / 串联橙 / 关联灰）、点越大表示联通度越高。**点节点看它的联动轴**
        （入边谁喂它、出边它喂谁），一键导出 SVG 留档。
        纯计算只读：不跑任何诊断、不改任何状态，画的只是清单与轴的关系。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from tkinter import filedialog
        from .native import linkage

        top = tk.Toplevel(self.root)
        top.title("联动图（只读 · 分层布局 · 点节点看联动轴）")
        top.geometry("1240x900")
        W, H = 1120, 720

        cv = tk.Canvas(top, width=W, height=H, bg="#ffffff", highlightthickness=1)
        cv.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        info = scrolledtext.ScrolledText(top, height=9, wrap="word")
        info.pack(fill="x", padx=8, pady=(0, 4))
        info.insert("end", "点图里的圆点看它的联动轴；上方按钮可导出 SVG。\n")
        info.configure(state="disabled")

        g = linkage.graph()
        pos = linkage.layout(g, W, H)

        def draw():
            cv.delete("all")
            # 图例
            lx, ly = 12, 14
            for kind in linkage.KINDS:
                cv.create_rectangle(lx, ly, lx + 11, ly + 11,
                                    fill=linkage.KIND_COLORS.get(kind, "#78909c"), outline="")
                cv.create_text(lx + 16, ly + 5, anchor="w", text=kind, fill="#444",
                               font=("Arial", 9))
                lx += 72
            cv.create_text(W - 12, 14, anchor="ne",
                           text=f"{len(g['nodes'])} 个子系统 · {len(g['edges'])} 条轴",
                           fill="#666", font=("Arial", 9))
            # 边
            for e in g["edges"]:
                a, b = pos.get(e["from"]), pos.get(e["to"])
                if not a or not b:
                    continue
                cv.create_line(a[0], a[1], b[0], b[1], fill=e["color"],
                               width=1, arrow="last", arrowshape=(6, 8, 3),
                               activewidth=2)
            # 节点
            for n in g["nodes"]:
                x, y = pos.get(n["key"], (0, 0))
                r = 3 + min(7, n["total"])
                cv.create_oval(x - r, y - r, x + r, y + r, fill="#37474f",
                               outline="", activefill="#c62828", tags=(n["key"],))
                cv.create_text(x + r + 3, y, anchor="w", text=n["label"],
                               fill="#333", font=("Arial", 8))

        def on_click(_ev):
            item = cv.find_withtag("current")
            if not item:
                return
            tags = cv.gettags(item[0])
            if not tags:
                return
            key = tags[0]
            name = {s.key: s.label for s in linkage.subsystems.SUBSYSTEMS}
            label = name.get(key, key)
            out_axes = [a for a in linkage.all_axes() if a.from_key == key]
            in_axes = [a for a in linkage.all_axes() if a.to_key == key]
            lines = [f"【{label}】（{key}）  入 {len(in_axes)} / 出 {len(out_axes)}",
                     ""]
            lines.append("—— 它喂给谁（出边）——")
            for a in out_axes:
                lines.append(f"  [{a.kind}] → {name.get(a.to_key, a.to_key)}：{a.desc}")
            if not out_axes:
                lines.append("  （无出边：串联收口点）")
            lines.append("")
            lines.append("—— 谁喂给它（入边）——")
            for a in in_axes:
                lines.append(f"  [{a.kind}] ← {name.get(a.from_key, a.from_key)}：{a.desc}")
            if not in_axes:
                lines.append("  （无入边：串联起点）")
            info.configure(state="normal")
            info.delete("1.0", "end")
            info.insert("end", "\n".join(lines))
            info.configure(state="disabled")

        cv.bind("<Button-1>", on_click)
        draw()

        def export_svg():
            path = filedialog.asksaveasfilename(
                parent=top, title="导出联动图 SVG",
                defaultextension=".svg",
                filetypes=[("SVG 图片", "*.svg"), ("所有文件", "*.*")],
                initialfile="sysweeper-linkage.svg")
            if not path:
                return
            try:
                data = linkage.svg()
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(data)
                messagebox.showinfo("已导出", f"联动图已写到：\n{path}\n（{len(data)} 字节）", parent=top)
                self.log(f"\n联动图 SVG 导出: {path}\n")
            except OSError as e:
                messagebox.showerror("导出失败", str(e), parent=top)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="重绘", command=draw).pack(side="left", padx=2)
        ttk.Button(bar, text="导出 SVG", command=export_svg).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_compat(self):
        """弹出「兼容层串联」窗口（v0.6.34）：四层依赖 + 场景结论。

        把 proton / dosbox / wsl / virtgpu / legacy 串成一条链，回答
        「能不能跑那个平台的软件、缺哪一层」。**不适用 ≠ 已就绪**（本机 Linux 时
        WSL 报告 ok 但正文是「未识别为 WSL」，判不适用）。只调既有零参只读报告，
        **不安装、不启用、不改配置**。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import compat

        top = tk.Toplevel(self.root)
        top.title("兼容层串联（只读 · 四层依赖 · 不安装不启用）")
        top.geometry("900x720")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        def _render():
            box.delete("1.0", "end")
            put("=" * 72)
            put("兼容层串联｜四层依赖：底座 → 设备与图形 → 兼容运行时 → 供给")
            put("=" * 72)
            put("上层能不能用，取决于下层给不给得了——缺一层，上层就是空转。")
            put("")
            _ok, rep = compat.compat_report()
            for line in rep.splitlines():
                put(line)
            put("")
            put("-- 能力自检 --")
            _ok2, cap = compat.capabilities_report()
            for line in cap.splitlines():
                put(line)
            box.see("1.0")

        ttk.Button(top, text="重新盘点", command=_render).pack(anchor="w", padx=8, pady=4)
        _render()

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_linux(self):
        """弹出「Linux 本机发行面」窗口（v0.6.35 补图形入口）。

        只读聚合：发行版（LSB /etc/os-release）／包管理器／systemd 日志体积／根分区用量。
        **只报告不清日志**——收缩 journal 只给命令文本，是否在终端执行由你决定。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import linux

        top = tk.Toplevel(self.root)
        top.title("Linux 本机发行面（只读聚合 · 只报告不清日志）")
        top.geometry("860x520")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def _render():
            box.delete("1.0", "end")
            put = lambda t: box.insert("end", t + "\n")
            put("=" * 68)
            put("Linux 本机发行面｜发行版 · 包管理 · 日志 · 根分区（全部只读）")
            put("=" * 68)
            ok, msg = linux.linux_report()
            for line in msg.splitlines():
                put(line)
            put("")
            put("提示：日志只报告不清。要收缩请自己在终端执行：")
            put("  journalctl --vacuum-size=200M")
            box.see("1.0")

        _render()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="刷新", command=_render).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_compress(self):
        """弹出「压缩空间分析」窗口（v0.6.35 补图形入口）。

        先列本机可读哪些压缩格式（caps），再按需扫描估算还能压出多少空间（report）。
        红线：**不压缩、不解压、不删除**，归档命令只以文本给出。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import compress

        top = tk.Toplevel(self.root)
        top.title("压缩空间分析（只读 · 不压缩不解压不删除）")
        top.geometry("900x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        box.insert("end", "点「格式可读性」看本机支持哪些压缩格式；"
                          "点「空间分析」估算还能压出多少（只读，不压缩不解压不删除）。\n")

        def _caps():
            box.delete("1.0", "end")
            ok, msg = compress.compress_format_capabilities()
            box.insert("end", msg + "\n")

        def _report():
            box.delete("1.0", "end")
            box.insert("end", "扫描中（有文件数上限与时间预算，达上限会标注「非全量」）…\n")
            box.update()
            ok, msg = compress.compress_report()
            box.delete("1.0", "end")
            box.insert("end", msg + "\n")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="格式可读性", command=_caps).pack(side="left", padx=2)
        ttk.Button(bar, text="空间分析", command=_report).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_edge(self):
        """弹出「单板机(SBC)」窗口（v0.6.35 补图形入口）。

        只读探测板型 / 温度 / 降频欠压 / 启动盘类型。非 SBC 优雅降级为「未识别为单板机」。
        红线：不改频率电压、不写 sysfs、不装散热服务。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import edge

        top = tk.Toplevel(self.root)
        top.title("单板机(SBC) 只读探测（不改频率电压、不写 sysfs）")
        top.geometry("860x560")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def _render():
            box.delete("1.0", "end")
            ok, msg = edge.edge_report()
            box.insert("end", msg + "\n")

        _render()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="重新探测", command=_render).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_omni(self):
        """弹出「全能全知自检」窗口（v0.6.35）：我知道什么 / 我不知道什么 / 我不做什么。

        三层边界：已登记能力（含接线完整度）／本机探不到的（已知未知，需点「实跑」）／
        **本工具压根没有探针的域**（第三层，也是最容易被人忽略的一层）。
        纯计算只读，不采集任何信息。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import omni

        top = tk.Toplevel(self.root)
        top.title("全能全知自检（我知道什么 / 我不知道什么 / 我不做什么）")
        top.geometry("960x720")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def _render(deep: bool = False):
            box.delete("1.0", "end")
            put = lambda t: box.insert("end", t + "\n")
            put("=" * 72)
            put("全能全知自检｜全知不是什么都知道，是能精确说出自己的边界")
            put("=" * 72)
            _ok, cap = omni.capabilities_report()
            for line in cap.splitlines():
                put(line)
            put("")
            ok, msg = omni.omni_report(deep=deep)
            for line in msg.splitlines():
                put(line)
            box.see("1.0")

        _render(False)
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="重新自检", command=lambda: _render(False)).pack(side="left", padx=2)
        ttk.Button(bar, text="实跑已知未知（慢）",
                   command=lambda: _render(True)).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_fonts(self):
        """弹出「字体与文本规范化」窗口（v0.6.36 补 GUI 入口：此前只差这一处）。

        只读：本机字体清单/重复项 + 文本规范化状态（UAX #15）。不改动任何字体与文件。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import fonts as nf

        top = tk.Toplevel(self.root)
        top.title("字体与文本规范化（只读 · 不改动字体与文件）")
        top.geometry("900x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        def _render():
            box.delete("1.0", "end")
            put = lambda t: box.insert("end", t + "\n")
            put("=" * 68)
            put("字体与文本规范化｜本机字体清单 / 重复项 / 文本规范化状态（全部只读）")
            put("=" * 68)
            ok, msg = nf.report_fonts()
            for line in msg.splitlines():
                put(line)
            put("")
            ok2, msg2 = nf.text_normalize_report()
            for line in msg2.splitlines():
                put(line)
            box.see("1.0")

        _render()
        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="刷新", command=_render).pack(side="left", padx=2)
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        return top

    def show_score(self):
        """弹出「数学评分」窗口：归一化加权评分 + Shannon 熵 + 平台均衡度。

        借鉴 openai/math（LaTeX 数学宏集合）背后「用数学把话说精确」的理念，
        工程上落为可复现的数字指标，**不 vendor LaTeX 宏包**。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from . import profiles as pf
        from .native import metrics as mt

        top = tk.Toplevel(self.root)
        top.title("数学化量化评估（归一化 / 加权评分 / Shannon 熵 / Gini）")
        top.geometry("860x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        allt = registry.all_tasks()
        put("=" * 72)
        put("数学化量化评估：把「覆盖得够不够全」变成可复现的数字")
        put("=" * 72)
        put(mt.score_report(allt, "全库覆盖度评分"))
        put("")
        put(mt.entropy_report(mt.category_distribution(allt)))
        gaps = mt.coverage_gaps(allt)
        put("")
        put("覆盖缺口（全库无任务的分类）：" + (", ".join(gaps) if gaps else "无 ✓"))

        put("")
        put("-" * 68)
        by_plat: dict = {}
        for t in allt:
            by_plat.setdefault(t.platform, []).append(t)
        b = mt.platform_balance(by_plat)
        put("平台任务分布均衡度：")
        put(f"   Gini = {b['gini']:.4f}（0=均分，1=极端集中）")
        put(f"   CV   = {b['cv']:.4f}（σ/μ）")
        put(f"   结论: {b['verdict']}")
        for k, v in sorted(b["detail"].items(), key=lambda kv: -kv[1]):
            put(f"     · {k:<12} {v} 项")

        put("")
        put("-" * 68)
        put("各档位评分对比：")
        for name in pf.PROFILE_ORDER:
            r = mt.coverage_score(pf.tasks_in_profile(name, "linux"))
            put(f"   {name:<9} score={r['score']:.4f}  {r['summary']}")

        put("")
        put("-" * 68)
        put("说明：本模块是纯标准库实现的量化评估（不 vendor openai/math 的 LaTeX 宏），")
        put("目的是让「覆盖得够不够全」从主观感受变成可复现的数字。")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_ios(self):
        """弹出「iOS」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：Windows / macOS / BSD / Unix / Android 之后，把同一
        文档跟踪模式补到 iOS 自身系统接口。iOS 沙盒严格，PC 端只能经 libimobiledevice
        向已配对设备发指令，每个接口都与其它平台不同，逐个按自身协议与接口核对
        （绝不套注册表/plist/sysctl，也绝不 remount 改系统分区）：libimobiledevice
        （usbmuxd+lockdown 套件）、lockdown（设备值）、installation_proxy（ideviceinstaller
        归档只留数据）、afc（容量只读）、crashreport（只清诊断日志）、syslog_relay
        （只读快照）、diagnostics（优雅重启）、mobilebackup2（只备份不恢复）、
        mobile_image_mounter（挂开发者镜像可逆）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import ios as ni

        top = tk.Toplevel(self.root)
        top.title("iOS 原生接口文档跟踪（libimobiledevice，各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("iOS 原生接口文档跟踪：各自按自身协议与接口核对（libimobiledevice）")
        put("=" * 72)
        for line in ni.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("iOS 系统接口文档引用（data/ios_docs.json）：协议 + 接口")
        for line in ni.ios_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口；需设备已连且信任）：")
        for fn_name, lab in ni.PROBES:
            ok, msg = getattr(ni, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("iOS 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in ni.ios_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks() if t.platform == "ios" and not t.opt_in]
        tune = [t for t in registry.all_tasks() if t.platform == "ios" and t.opt_in]
        put(f"iOS 指引/清理任务（ios_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"iOS 官方接口深度调优（ios_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<28} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_macos(self):
        """弹出「macOS」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：把同一文档跟踪模式推广到 macOS 自身系统接口，
        逐个按自身协议与接口核对（绝不套 Linux 的 /proc/sys、systemd 写法）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import macos as nm

        top = tk.Toplevel(self.root)
        top.title("macOS 原生接口文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("macOS 原生接口文档跟踪：各自按自身协议与接口核对")
        put("=" * 72)
        for line in nm.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("macOS 系统接口文档引用（data/macos_docs.json）：协议 + 接口")
        for line in nm.macos_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nm.PROBES:
            ok, msg = getattr(nm, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("macOS 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in nm.macos_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks()
                if t.id.startswith("mac") and not t.id.startswith("macos_tune_")]
        tune = [t for t in registry.all_tasks() if t.id.startswith("macos_tune_")]
        put(f"macOS 清理/优化任务（mac_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"macOS 官方接口深度调优（macos_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<34} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_bsd(self):
        """弹出「BSD」窗口：各系统接口探测 + 文档引用 + 本机核对 + 任务。

        「触类旁通、举一反三」：把同一文档跟踪模式推广到 BSD 自身系统接口，
        逐个按自身协议与接口核对（pkg/rc.conf/sysctl/pf/zfs/periodic/...）。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import bsd as nb

        top = tk.Toplevel(self.root)
        top.title("BSD 原生接口文档跟踪（各自按自身协议与接口）")
        top.geometry("800x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("BSD 原生接口文档跟踪：各自按自身协议与接口核对")
        put("=" * 72)
        for line in nb.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("BSD 系统接口文档引用（data/bsd_docs.json）：协议 + 接口")
        for line in nb.bsd_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，按各自官方接口）：")
        for fn_name, lab in nb.PROBES:
            ok, msg = getattr(nb, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        put("BSD 官方写接口（深度调优，只展示不调用——调用即写系统）：")
        for line in nb.bsd_tune_list():
            put(line)

        put("")
        put("-" * 68)
        base = [t for t in registry.all_tasks()
                if t.id.startswith("bsd") and not t.id.startswith("bsd_tune_")]
        tune = [t for t in registry.all_tasks() if t.id.startswith("bsd_tune_")]
        put(f"BSD 清理/优化任务（bsd_*）：{len(base)} 项")
        for t in base:
            put(f"  • {t.id:<24} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")
        put("")
        put(f"BSD 官方接口深度调优（bsd_tune_*）：{len(tune)} 项（全 opt_in，需选择+确认）")
        for t in tune:
            put(f"  • {t.id:<34} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_harmony(self):
        """弹出「鸿蒙」窗口：工具链/工程探测 + 协议接口文档 + 只读核对 + 任务。

        「触类旁通、举一反三」：按鸿蒙自身协议与接口核对——Stage 模型（UIAbility/Want）、
        SystemCapability（@ohos.* + canIUse）、HiLog（域/标签/级别）、hdc 设备桥、
        HAP/HSP 应用包与 ohpm/Hvigor 构建、@ohos.rpc 与分布式软总线，以及 uni-app
        鸿蒙端（HBuilderX 4.27+，仅 vue3）。设备侧需 hdc，工程侧扫描当前目录。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import harmony as nhm

        top = tk.Toplevel(self.root)
        top.title("鸿蒙 HarmonyOS / OpenHarmony 文档跟踪（含 uni-app 鸿蒙端）")
        top.geometry("780x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("鸿蒙：按自身协议与接口核对（延续内核/桌面/系统软件文档跟踪模式）")
        put("=" * 72)
        for line in nhm.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("鸿蒙文档引用（data/harmony_docs.json）：协议 + 接口")
        for line in nhm.harmony_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机 / 设备核对（只读）：")
        for fn_name, lab in nhm.PROBES:
            ok, msg = getattr(nhm, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.platform == "harmony"]
        put(f"鸿蒙核对/优化任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<26} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_kaihong(self):
        """弹出「KaihongOS」窗口：发行版只读识别（深开鸿 / 基于 OpenHarmony）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import harmony as nhm

        top = tk.Toplevel(self.root)
        top.title("KaihongOS 发行版识别（深开鸿 / 基于 OpenHarmony）")
        top.geometry("760x520")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("KaihongOS 发行版识别（深开鸿，基于 OpenHarmony；只读）")
        put("=" * 72)
        ok, msg = nhm.kaihong_report()
        if ok:
            for line in msg.splitlines():
                put(line)
        else:
            put("（当前不适用）" + msg)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_media(self):
        """弹出「图像能力」窗口：编解码/色彩能力只读诊断（吸收 photocraft 图像管线视角）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import media

        top = tk.Toplevel(self.root)
        top.title("图像/媒体编解码与色彩能力（只读诊断）")
        top.geometry("780x600")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("图像/媒体编解码与色彩能力（只读；吸收 storytold/photocraft 图像管线视角）")
        put("=" * 72)
        _ok, msg = media.image_capability_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_livemedia(self):
        """弹出「可启动介质制作能力」窗口（吸收 livecd/dvd/bd/usb 制作技术，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import livemedia

        top = tk.Toplevel(self.root)
        top.title("可启动介质制作能力（只读诊断）")
        top.geometry("820x640")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("可启动介质制作能力（只读；吸收 livecd/dvd/bd/usb 制作技术）")
        put("=" * 72)
        _ok, msg = livemedia.livemedia_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_legacy(self):
        """弹出「遗留/嵌入式/兼容层」窗口（DOS 3.1 等 · busybox · dosbox，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import legacy

        top = tk.Toplevel(self.root)
        top.title("遗留 / 嵌入式 / 兼容层（只读诊断）")
        top.geometry("820x640")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("遗留 / 嵌入式 / 兼容层（只读；DOS 3.1 等 · busybox · dosbox）")
        put("=" * 72)
        _ok, msg = legacy.legacy_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_radio(self):
        """弹出「无线电技术与标准」窗口（射频面 / SDR 工具链 / 法规口径，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import radio

        top = tk.Toplevel(self.root)
        top.title("无线电技术与标准（只读诊断）")
        top.geometry("840x660")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("无线电技术与标准（只读；射频面 · SDR 工具链 · 法规口径）")
        put("=" * 72)
        _ok, msg = radio.radio_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")

    def show_winternals(self):
        """弹出「开源 Windows 分析学习应用」窗口（先定系统再谈目录，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import winternals

        top = tk.Toplevel(self.root)
        top.title("开源 Windows 分析学习应用（只读诊断）")
        top.geometry("860x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("开源 Windows 分析学习应用（只读；目标环境 · 文件系统 · 运行时 · 工具链）")
        put("=" * 72)
        put("第一原则：先定系统，再谈目录——先判定目标所属环境，再按该环境自身的")
        put("文件系统、目录约定、路径分隔与运行语言标准去读数，不以本机习俗臆造。")
        put("")
        _ok, msg = winternals.winternals_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_qstore(self):
        """弹出「量子存储交换」窗口（ext4 4K 对齐 + 异构端点 + Π_k 进制转换，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import qstore

        top = tk.Toplevel(self.root)
        top.title("量子存储交换（只读诊断）")
        top.geometry("860x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("量子存储交换（只读；ext4 4K 对齐 · 异构端点缓冲 · Π_k 进制转换 · 管线仿真）")
        put("=" * 72)
        put("量子部分是可逆编码与仿真，不是真的把 GPU 变成磁盘加速器；")
        put("写盘/格式化命令只作文本建议，绝不执行。")
        put("")
        _ok, msg = qstore.qstore_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")

    def show_qarch(self):
        """弹出「量子架构内核」窗口（6.18.57 LTS + arch/quantum，只读）。"""
        tk, ttk, messagebox, scrolledtext = _tk()
        from .native import qarch

        top = tk.Toplevel(self.root)
        top.title("量子架构内核（只读诊断）")
        top.geometry("860x680")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("量子架构内核（只读；Linux 6.18.57 LTS · arch/quantum · QPU 设备）")
        put("=" * 72)
        put("纯新增架构：既有 21 个架构一个不动；纯只读盘点，绝不执行内核构建。")
        put("")
        _ok, msg = qarch.qarch_report()
        for line in msg.splitlines():
            put(line)

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top

    def show_miniapp(self):
        """弹出「小程序端」窗口：各端探测 + API 规范文档 + 只读核对 + 任务。

        「触类旁通、举一反三」：跨端框架的每个目标端都有自己的 API 规范——微信 wx.*
        （双线程）、支付宝 my.*（域名白名单）、百度 swan.*、抖音 tt.*、QQ qq.*、快手 ks.*；
        uni-app 用 uni.* 统一映射，差异由条件编译 #ifdef MP-XXX 隔离。
        """
        tk, ttk, messagebox, scrolledtext = _tk()
        from . import registry
        from .native import miniapp as nmp

        top = tk.Toplevel(self.root)
        top.title("uni-app 各小程序端文档跟踪（微信/支付宝/百度/抖音/QQ/快手）")
        top.geometry("780x620")
        box = scrolledtext.ScrolledText(top, wrap="word")
        box.pack(fill="both", expand=True, padx=8, pady=8)

        def put(text: str):
            box.insert("end", text + "\n")

        put("=" * 72)
        put("uni-app 各小程序端：按各端自身 API 规范核对（延续文档跟踪模式）")
        put("=" * 72)
        for line in nmp.environment_report():
            put(line)

        put("")
        put("-" * 68)
        put("小程序端文档引用（data/miniapp_docs.json）：协议 + 接口")
        for line in nmp.miniapp_doc_list():
            put(line)

        put("")
        put("-" * 68)
        put("本机核对（只读，扫描 uni-app 工程）：")
        for fn_name, lab in nmp.PROBES:
            ok, msg = getattr(nmp, fn_name)()
            put("")
            put(f"-- {lab} --")
            put(("  " + (msg or "").replace("\n", "\n  ")) if ok
                else f"  （当前不适用）{msg}")

        put("")
        put("-" * 68)
        tasks = [t for t in registry.all_tasks() if t.id.startswith("mp_")]
        put(f"小程序端核对/清理任务：{len(tasks)} 项")
        for t in tasks:
            put(f"  • {t.id:<22} [{t.category}/{t.risk}]  {t.display_title()}")
            for s in t.standards:
                put(f"       {s}")

        bar = ttk.Frame(top)
        bar.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text="关闭", command=top.destroy).pack(side="right")
        box.see("1.0")
        return top


def launch(platform: str = None, version: str = "") -> int:
    """启动 GUI。无图形环境时优雅降级，返回退出码。"""
    tk, ttk, messagebox, scrolledtext = _tk()  # 缺 tkinter 会在此抛出
    from .detect import detect

    if not platform:
        d = detect()
        platform = d["platform"] if d["platform"] != "unknown" else "linux"
        version = d.get("version", "") or version
    root = tk.Tk()  # 无 DISPLAY 时在此抛 TclError
    SysweeperGUI(root, platform=platform, version=version or "")
    root.mainloop()
    return 0


def launch_or_fallback(platform: str = None, version: str = "") -> int:
    """尝试启动 GUI；失败则打印各后端状态并退回命令行指引。"""
    try:
        return launch(platform, version)
    except Exception as e:  # noqa: BLE001
        print(f"无法启动图形界面：{e}")
        print("\n各 GUI 后端状态（优先「语言自带」的）：")
        for b in detect_gui_backends():
            mark = "✓ 可用" if b["available"] else "✗ 不可用"
            print(f"  [{mark}] {b['name']} — {b['note']}")
        print("\n替代方案（命令行，功能完全一致）：")
        print("  python -m sysweeper scan                     # 分析，不改系统")
        print("  python -m sysweeper clean --apply --risk low # 仅执行低风险清理")
        print("  python -m sysweeper scan --report report.md  # 生成前后对比报告")
        return 1
