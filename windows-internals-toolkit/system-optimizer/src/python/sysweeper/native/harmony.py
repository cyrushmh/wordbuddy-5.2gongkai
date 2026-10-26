"""鸿蒙（HarmonyOS / OpenHarmony）原生接口与文档引用。

「触类旁通、举一反三」：内核、桌面、其余系统软件之后，把同一套「权威文档 + 只读探测 +
任务」模式推广到鸿蒙生态。与其他平台一样，**按鸿蒙自身的协议与接口**核对，而非套用
Linux/Android 那套：

- Stage 模型      : UIAbility / ExtensionAbility 生命周期 + Want 意图协议
- SystemCapability: @ohos.* 分层 API + canIUse() 运行期能力判定
- HiLog           : 域(domain) / 标签(tag) / 级别(level) 三维日志协议
- hdc             : HarmonyOS Device Connector（对标 adb，但命令不兼容）
- 应用包          : HAP / HSP / HAR + ohpm / Hvigor 构建
- 分布式          : @ohos.rpc（IPC/RPC）+ 分布式软总线
- uni-app 鸿蒙端  : HBuilderX 4.27+ 起支持，仅 vue3（DCloud 官方文档）

探测分两侧（均只读）：
- 设备侧：需 hdc（未安装/未连设备即降级为指引）
- 工程侧：扫描当前目录的鸿蒙工程（AppScope / build-profile.json5）与
  uni-app 工程（pages.json / manifest.json）

参考文档见 data/harmony_docs.json。所有探测惰性守卫，绝不修改系统或设备。
"""

from __future__ import annotations

import glob
import json
import os
import shutil


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "harmony_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某鸿蒙子系统/能力的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    return REFS


def _common_run(cmd: str):
    from . import common
    return common.run(cmd)


def _fmt_size(n: int) -> str:
    if n >= 1024 * 1024 * 1024:
        return f"{n/1024/1024/1024:.2f} GiB"
    if n >= 1024 * 1024:
        return f"{n/1024/1024:.1f} MiB"
    if n >= 1024:
        return f"{n/1024:.1f} KiB"
    return f"{n} B"


def _dir_size(path: str) -> int:
    total = 0
    if not os.path.isdir(path):
        return 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _scan_project(markers: tuple) -> str:
    """在当前目录及其一级子目录中查找含任一 marker 的工程根目录（只读、不深扫）。"""
    cwd = os.getcwd()
    roots = [cwd]
    try:
        roots += [os.path.join(cwd, d) for d in os.listdir(cwd)
                  if os.path.isdir(os.path.join(cwd, d))]
    except OSError:
        pass
    for r in roots:
        for m in markers:
            if os.path.exists(os.path.join(r, m)):
                return r
    return ""


def detect_harmony() -> dict:
    """探测本机鸿蒙工具链与工程（按官方接口判定）。"""
    return {
        "hdc": bool(shutil.which("hdc")),
        "hilogtool": bool(shutil.which("hilogtool")),
        "ohpm": bool(shutil.which("ohpm")),
        "hvigorw": bool(shutil.which("hvigorw") or shutil.which("hvigor")),
        "node": bool(shutil.which("node")),
        "harmony_project": bool(_scan_project(("AppScope", "build-profile.json5",
                                               "oh-package.json5"))),
        "uniapp_project": bool(_scan_project(("pages.json", "manifest.json",
                                              "src/manifest.json"))),
    }


# ---------------------------------------------------------------------------
# 各子系统只读探测（均返回 (ok, msg)）
# ---------------------------------------------------------------------------

def detect_kaihong() -> dict:
    """探测本机是否为 KaihongOS（深开鸿基于 OpenHarmony 的发行版）。

    只读：/etc/os-release（及 /etc/os-release.d/*）、/proc/version、
    /sys/fs/selinux/enforce、shutil.which("hdc")。绝不连设备、绝不改系统。
    """
    info = {"is_kaihong": False, "name": "", "version": "", "variant": "",
            "selinux": None, "hdc": bool(shutil.which("hdc")),
            "hilogtool": bool(shutil.which("hilogtool"))}
    fields: dict = {}
    candidates = ["/etc/os-release"]
    try:
        candidates += sorted(glob.glob("/etc/os-release.d/*"))
    except Exception:
        pass
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if "=" not in line or line.startswith("#"):
                        continue
                    k, _, v = line.partition("=")
                    fields[k] = v.strip().strip('"').strip("'")
        except OSError:
            continue
    combined = (fields.get("ID", "") + " " + fields.get("NAME", "") + " "
                + fields.get("PRETTY_NAME", "")).lower()
    if "kaihong" in combined:
        info["is_kaihong"] = True
        info["name"] = fields.get("NAME", "KaihongOS")
        info["version"] = fields.get("VERSION_ID", "") or fields.get("PRETTY_NAME", "")
        low = combined
        if "desktop" in low or "桌面" in low:
            info["variant"] = "桌面版（x86 / ARM）"
        elif "stan" in low:
            info["variant"] = "Stan（L2，RK3568 / RK3588）"
        elif "small" in low:
            info["variant"] = "Small（L1，Hi3519 / Hi3516）"
        elif "lite" in low:
            info["variant"] = "Lite（L0，ESP32 / Hi3863）"
        else:
            info["variant"] = "（未识别具体 variant）"
    try:
        with open("/sys/fs/selinux/enforce", encoding="utf-8") as fh:
            info["selinux"] = fh.read().strip()
    except OSError:
        info["selinux"] = None
    return info


def kaihong_report() -> tuple:
    """KaihongOS 发行版只读识别（深开鸿 / 基于 OpenHarmony）。

    只报「是什么版本、什么 variant、安全基座（SELinux / 可信应用）、调试工具（hdc / HiLog）」，
    不连设备、不读业务数据、不改配置。非 KaihongOS 主机降级为指引。
    """
    info = detect_kaihong()
    if not info["is_kaihong"]:
        return False, ("未检测到 KaihongOS（深开鸿基于 OpenHarmony 的发行版）。\n"
                       "  本机若为其它发行版，按该发行版自身接口核对；\n"
                       "  KaihongOS 专有诊断（Stan/Small/Lite、分布式软总线、HDC、SELinux）"
                       "仅在其宿主机 / 设备上适用。")
    lines = ["检测到 KaihongOS（深开鸿，基于 OpenHarmony）："]
    lines.append(f"  名称      : {info['name']}")
    lines.append(f"  版本      : {info['version']}")
    lines.append(f"  variant   : {info['variant']}")
    if info["selinux"] in ("1", "0"):
        lines.append(f"  SELinux   : {'强制(Enforcing)' if info['selinux'] == '1' else '宽松(Permissive)'} "
                     f"（KaihongOS 安全基座含 SELinux 策略配置 + 可信应用 + 端到端加密）")
    else:
        lines.append("  SELinux   : 未挂载 /sys/fs/selinux（可能未启用 MAC）")
    lines.append(f"  HDC 工具  : {'✓ 已安装' if info['hdc'] else '✗ 未安装（设备侧调试需用 hdc）'}")
    lines.append(f"  HiLog     : {'✓ 已安装' if info['hilogtool'] else '✗ 未安装（日志分析需用 hilogtool）'}")
    lines.append("  说明      : 多内核混合部署（集成 UniProton，任务时延≤3us）；"
                 "分布式软总线实现跨设备协同（响应 <50ms）。")
    return True, "\n".join(lines)


def hdc_report() -> tuple:
    """hdc 设备桥：已连接设备核对（只读）。"""
    if not shutil.which("hdc"):
        return False, "未安装 hdc（HarmonyOS Device Connector）；未装 DevEco/HarmonyOS SDK " \
                      "或未连设备时跳过。\n" \
                      "   装后核对: `hdc list targets`（注意：与 adb devices 不通用）。"
    _rc, out = _common_run("hdc list targets 2>/dev/null")
    targets = [l.strip() for l in (out or "").splitlines()
               if l.strip() and "Empty" not in l and "empty" not in l]
    lines = [f"已连接设备: {len(targets)} 个（hdc list targets）"]
    for t in targets[:5]:
        lines.append("   · " + t)
    if not targets:
        lines.append("   （无设备——开启 USB 调试并连接后可见）")
    lines.append("接口: hdc shell / hdc file recv|send / hdc install；"
                 "三端架构 client-server-daemon")
    return True, "\n".join(lines)


def hilog_report() -> tuple:
    """HiLog：设备侧日志核对（只读，按域/标签/级别协议）。"""
    if not shutil.which("hdc"):
        return False, "未安装 hdc；无法读取设备 HiLog（/data/log/hilog）。\n" \
                      "   连设备后: `hdc shell hilog -L E`（只看 Error 及以上）。"
    _rc, out = _common_run('hdc shell "ls /data/log/hilog 2>/dev/null | head -10"')
    files = [l.strip() for l in (out or "").splitlines() if l.strip()]
    lines = [f"设备日志目录 /data/log/hilog 条目: {len(files)} 个"]
    for f in files[:8]:
        lines.append("   · " + f)
    lines.append("协议: 级别 D/I/W/E/F、域(应用层 0xD000)、标签(tag)；"
                 "持久日志为编码 gz，需 hilogtool 解析")
    lines.append("回收: 走 hilog / hdc 官方接口，勿直接删 /data/log/hilog")
    return True, "\n".join(lines)


def stage_model_report() -> tuple:
    """Stage 模型：本地鸿蒙工程的组件与配置核对（只读）。"""
    root = _scan_project(("AppScope", "build-profile.json5", "module.json5",
                          "oh-package.json5"))
    if not root:
        return False, "当前目录未发现鸿蒙工程（无 AppScope / build-profile.json5 / " \
                      "module.json5）；在非工程目录运行时跳过。"
    lines = [f"鸿蒙工程: {root}"]
    for f in ("AppScope/app.json5", "build-profile.json5", "module.json5",
              "oh-package.json5"):
        if os.path.exists(os.path.join(root, f)):
            lines.append("   · " + f)
    lines.append("核对: UIAbility / ExtensionAbility 声明于 module.json5；"
                 "生命周期走官方 UIAbility 接口，组件间经 Want 调度")
    return True, "\n".join(lines)


def syscap_report() -> tuple:
    """系统能力：SysCap 声明与 canIUse 判定核对（只读）。"""
    root = _scan_project(("syscap.json", "module.json5", "oh-package.json5",
                          "AppScope"))
    if not root:
        return False, "当前目录未发现鸿蒙工程；无法核对 SysCap 声明。"
    lines = [f"鸿蒙工程: {root}"]
    if os.path.exists(os.path.join(root, "syscap.json")):
        lines.append("   · syscap.json 存在（构建期能力声明）")
    else:
        lines.append("   · 未发现 syscap.json（可在工程中显式声明所需 SysCap）")
    lines.append("运行期判定: canIUse()（官方推荐——调用 @ohos.* API 前先判定，"
                 "避免低能力设备崩溃）")
    return True, "\n".join(lines)


def package_report() -> tuple:
    """应用包与构建产物：生成目录占用核对（只读，不删除）。"""
    root = _scan_project(("build-profile.json5", "AppScope", "oh-package.json5"))
    if not root:
        return False, "当前目录未发现鸿蒙工程；无法核对构建产物。"
    lines = [f"鸿蒙工程: {root}", "可重建的生成目录（清理安全）："]
    total = 0
    for d in ("build", ".hvigor", "oh_modules", "node_modules", ".preview"):
        p = os.path.join(root, d)
        if os.path.isdir(p):
            s = _dir_size(p)
            total += s
            lines.append(f"   · {d}/  {_fmt_size(s)}")
    lines.append(f"   合计（只读估算，不删除）: {_fmt_size(total)}")
    lines.append("勿删: AppScope/app.json5、module.json5、签名文件(p12/cer/p7b)")
    return True, "\n".join(lines)


def ipc_distributed_report() -> tuple:
    """IPC/RPC 与分布式软总线核对（只读；需设备才展开）。"""
    if not shutil.which("hdc"):
        return False, "未安装 hdc；跨设备 RPC / 分布式软总线需连设备核对" \
                      "（@ohos.rpc、@ohos.distributedDeviceManager）。"
    return True, ("IPC/RPC: @ohos.rpc（MessageSequence / RemoteObject）；\n"
                  "分布式: @ohos.distributedDeviceManager（设备需先发现与认证组网）；\n"
                  "连设备后可用 `hdc shell` 核对设备侧分布式状态。")


def uniapp_harmony_report() -> tuple:
    """uni-app 鸿蒙端：工程与鸿蒙配置核对（只读，按 DCloud 官方文档）。"""
    root = _scan_project(("pages.json", "manifest.json", "src/manifest.json"))
    if not root:
        return False, "当前目录未发现 uni-app 工程（无 pages.json / manifest.json）；" \
                      "在非 uni-app 目录运行时跳过。\n" \
                      "   鸿蒙端要求: HBuilderX 4.27+，且仅支持 vue3 项目（vue2 需先迁移）。"
    lines = [f"uni-app 工程: {root}"]
    mj = os.path.join(root, "manifest.json")
    if not os.path.exists(mj):
        mj = os.path.join(root, "src", "manifest.json")
    if os.path.exists(mj):
        try:
            with open(mj, encoding="utf-8") as f:
                txt = f.read()
        except OSError:
            txt = ""
        if "harmony" in txt.lower():
            lines.append("   · manifest.json 已含鸿蒙(harmony)配置")
        else:
            lines.append("   · manifest.json 未发现鸿蒙配置"
                         "（需在 HBuilderX 4.27+ 中启用 Harmony Next）")
    for f in ("main.ts", "main.js", "src/main.ts", "src/main.js",
              "vite.config.ts", "vite.config.js"):
        if os.path.exists(os.path.join(root, f)):
            lines.append("   · " + f)
    lines.append("要求: 仅 vue3 可编译到鸿蒙；vue2 需先迁移（uni-app migration-to-vue3 文档）")
    lines.append("差异隔离: 用条件编译，勿假设与 Android/iOS 端 API 一致")
    return True, "\n".join(lines)


def connected() -> bool:
    """hdc 可用且至少连上一台鸿蒙设备（供 detect 自动识别平台）。"""
    if not shutil.which("hdc"):
        return False
    rc, out = _common_run("hdc list targets 2>/dev/null")
    if rc != 0:
        return False
    for l in (out or "").splitlines():
        s = l.strip()
        if s and "Empty" not in s and "empty" not in s:
            return True
    return False


def _param(name: str) -> str:
    """读取设备参数（param get，只读）。失败返回空串。"""
    rc, out = _common_run(f"hdc shell param get {name} 2>/dev/null")
    if rc != 0:
        return ""
    for l in (out or "").splitlines():
        s = l.strip()
        if s and "not found" not in s.lower():
            return s
    return ""


def device_model() -> str:
    """设备型号（const.product.model）。"""
    return _param("const.product.model") if connected() else ""


def version() -> str:
    """鸿蒙 API 版本（const.ohos.apiversion），回退系统版本。"""
    if not connected():
        return ""
    return (_param("const.ohos.apiversion")
            or _param("const.product.software.version"))


def device_report() -> tuple:
    """设备信息：型号 / 系统版本 / API 版本 / 存储占用（只读）。"""
    if not shutil.which("hdc"):
        return False, "未安装 hdc；无法读取鸿蒙设备信息。装后 `hdc list targets` 核对连接。"
    if not connected():
        return False, "hdc 已安装但无已连接设备；开启 USB 调试并连接后可见（hdc list targets）。"
    lines = []
    for label, name in (("设备型号", "const.product.model"),
                        ("系统版本", "const.product.software.version"),
                        ("API 版本", "const.ohos.apiversion")):
        v = _param(name)
        if v:
            lines.append(f"{label}: {v}")
    _rc, out = _common_run("hdc shell df -h /data 2>/dev/null")
    rows = [l.strip() for l in (out or "").splitlines() if l.strip()]
    if rows:
        lines.append("存储(/data): " + " | ".join(rows[-1].split()[:5]))
    if not lines:
        return False, "已连接设备但读取参数失败（可能权限受限或 param 命令不可用）。"
    lines.append("接口: hdc shell param get（系统参数只读查询）")
    return True, "\n".join(lines)


def app_report() -> tuple:
    """已安装应用核对（bm dump -a，只读）。"""
    if not shutil.which("hdc"):
        return False, "未安装 hdc；无法列出设备应用。"
    if not connected():
        return False, "无已连接鸿蒙设备；连上后可 `hdc shell bm dump -a` 列出应用。"
    _rc, out = _common_run("hdc shell bm dump -a 2>/dev/null")
    rows = [l.strip() for l in (out or "").splitlines() if l.strip()]
    apps = [r for r in rows if "bundleName" in r or r.startswith(("com.", "ohos."))]
    if not apps:
        return False, ("设备已连接但 bm dump -a 未返回结果（部分系统版本需 root 或 bm 不可用）；"
                       "可改用 `hdc shell ls /data/app` 粗略核对。")
    lines = [f"已安装应用: {len(apps)} 个（bm dump -a）"]
    for a in apps[:10]:
        lines.append("   · " + a)
    if len(apps) > 10:
        lines.append(f"   …（共 {len(apps)} 个）")
    lines.append("接口: bm（Bundle Manager，应用包管理）；只读列出，不卸载")
    return True, "\n".join(lines)


# 探测函数 → 展示标签（CLI/GUI 统一遍历）
PROBES = (
    ("hdc_report", "hdc 设备连接桥（HarmonyOS Device Connector）"),
    ("device_report", "设备信息（型号 / 系统版本 / API 版本 / 存储）"),
    ("app_report", "已安装应用（bm dump -a）"),
    ("hilog_report", "HiLog 日志（域 / 标签 / 级别）"),
    ("stage_model_report", "Stage 应用模型（UIAbility / module.json5）"),
    ("syscap_report", "系统能力 SystemCapability（@ohos.* / canIUse）"),
    ("package_report", "HAP/HSP 应用包与 ohpm/Hvigor 构建产物"),
    ("ipc_distributed_report", "IPC/RPC 与分布式软总线"),
    ("uniapp_harmony_report", "uni-app 鸿蒙端（Harmony Next，vue3）"),
    ("kaihong_report", "KaihongOS 发行版识别（深开鸿 / 基于 OpenHarmony）"),
)


def environment_report() -> list:
    """返回鸿蒙环境跟踪报告（多行文本），供 CLI/GUI 展示。"""
    det = detect_harmony()
    labels = (("hdc", "hdc 设备桥"),
              ("hilogtool", "hilogtool 解析"),
              ("ohpm", "ohpm 包管理"),
              ("hvigorw", "Hvigor 构建"),
              ("node", "Node 运行时"),
              ("harmony_project", "鸿蒙工程"),
              ("uniapp_project", "uni-app 工程"))
    lines = ["本机鸿蒙 / uni-app 鸿蒙端探测（按各自官方接口）："]
    for key, label in labels:
        lines.append(f"   {label:<18} : {'✓ 可用/已发现' if det.get(key) else '✗ 未安装/未发现'}")
    lines.append("（未安装者不强求安装——对应任务自动降级为指引）")
    ki = detect_kaihong()
    if ki["is_kaihong"]:
        lines.append(f"  KaihongOS        : ✓ 检测到 {ki['variant']}（深开鸿，基于 OpenHarmony）")
    else:
        lines.append("  KaihongOS        : ✗ 未检测到（深开鸿发行版；非其宿主机/设备即不适用）")
    return lines


def harmony_doc_list(key: str = None) -> list:
    """返回文档引用行（含协议 protocols 与接口 interfaces），供 CLI/GUI 展示。"""
    items = {key: REFS[key]} if (key and key in REFS) else REFS
    lines = []
    for _k, ref in items.items():
        lines.append(f"   · {ref.get('name','')}  [{ref.get('org','')}]")
        lines.append(f"       文档: {ref.get('url','')}")
        for p in ref.get("protocols", [])[:2]:
            lines.append(f"       协议: {p}")
        for i in ref.get("interfaces", [])[:2]:
            lines.append(f"       接口: {i}")
    return lines
