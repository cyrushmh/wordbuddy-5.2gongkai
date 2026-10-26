"""Windows 原生接口：用 Win32 API（ctypes）与注册表（winreg）解决路径/版本/磁盘。

所有 win32 调用都惰性加载（在 Windows 上才有 windll），在 Linux/macOS 导入本
模块不会崩溃——函数内部检测不到 API 就返回 None，由上层降级到指引。"""

from __future__ import annotations

import json
import os
import shutil
import sys

from . import common

# winreg 仅 Windows 有；其他平台用 try 保护，import 不挂
try:
    import winreg  # type: ignore
except Exception:  # noqa: BLE001
    winreg = None


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "windows_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 Windows 接口的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 Windows 接口文档参考。"""
    return REFS


def _is_windows() -> bool:
    return sys.platform == "win32"


def _kernel32():
    if sys.platform != "win32":
        return None
    try:
        return __import__("ctypes").windll.kernel32
    except Exception:  # noqa: BLE001
        return None


def _shell32():
    if sys.platform != "win32":
        return None
    try:
        return __import__("ctypes").windll.shell32
    except Exception:  # noqa: BLE001
        return None


def get_temp_dirs() -> list:
    """返回本机临时目录列表（真实 API 解析）：
    - 当前用户 TEMP（GetTempPathW）
    - 系统 Windows\\Temp（以系统盘根 + 已知约定）
    - 用户 LocalAppData\\Temp
    拿不到的返回空列表。"""
    dirs = []
    ctypes = __import__("ctypes") if sys.platform == "win32" else None
    if ctypes is not None:
        k32 = _kernel32()
        if k32 is not None:
            buf = ctypes.create_unicode_buffer(1024)
            n = k32.GetTempPathW(1024, buf)
            if n:
                dirs.append(buf.value.rstrip("\\/"))
    # LocalAppData\\Temp 是 UWP/桌面应用最常用的临时根
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "Temp"))
    sysroot = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if sysroot:
        dirs.append(os.path.join(sysroot, "Temp"))
    # 去重保序
    seen, out = set(), []
    for d in dirs:
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def disk_usage(path: str = None) -> dict | None:
    """用 GetDiskFreeSpaceEx 取磁盘总/可用空间（字节）。拿不到返回 None。"""
    if sys.platform != "win32":
        return None
    ctypes = __import__("ctypes")
    k32 = _kernel32()
    if k32 is None:
        return None
    path = path or os.environ.get("SystemDrive", "C:\\")
    free = ctypes.c_ulonglong(0)
    total = ctypes.c_ulonglong(0)
    ok = k32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(path),
        ctypes.byref(free), ctypes.byref(total), None)
    if not ok:
        return None
    return {"total": total.value, "free": free.value, "used": total.value - free.value}


def empty_recycle_bin(drive: str = None) -> tuple:
    """调用 Shell32.SHEmptyRecycleBinW 清空回收站。返回 (ok, msg)。"""
    ctypes = __import__("ctypes")
    sh = _shell32()
    if sh is None:
        return False, "当前非 Windows，无法调用回收站 API"
    SHEB_NOCONFIRMATION = 0x1
    SHEB_NOPROGRESSUI = 0x2
    flags = SHEB_NOCONFIRMATION | SHEB_NOPROGRESSUI
    try:
        sh.SHEmptyRecycleBinW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
        sh.SHEmptyRecycleBinW.restype = ctypes.c_long
        rc = sh.SHEmptyRecycleBinW(None, drive, flags)
        return rc == 0, f"SHEmptyRecycleBin 返回 {rc}"
    except Exception as e:  # noqa: BLE001
        return False, f"调用失败: {e}"


def get_version() -> dict:
    """从注册表读 Windows 真实版本信息（Win32_OperatingSystem 的权威来源）。

    返回 {product_name, display_version, build, release_id}；非 Windows 返回 {}。"""
    if winreg is None:
        return {}
    key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    out = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as hk:
            for name in ("ProductName", "DisplayVersion", "CurrentBuild",
                         "ReleaseId", "UBR"):
                try:
                    val, _ = winreg.QueryValueEx(hk, name)
                    out[name.lower()] = val
                except OSError:
                    pass
    except OSError:
        return {}
    # 兼容：旧系统用 ReleaseId；新系统用 DisplayVersion
    out["version"] = str(out.get("display_version") or out.get("release_id") or "")
    return out


# --------------------------------------------------------------------------- #
# 文档跟踪层：Windows 各系统接口只读探测（返回 (ok, msg)）。                     #
# 全部只读：仅读注册表 / 查 CIM / 列电源计划 / 统计缓存占用，不写任何系统项。     #
# 非 Windows 环境接口不存在，优雅返回 (False, 说明)，由上层降级为文档指引。       #
# --------------------------------------------------------------------------- #

def version_report() -> tuple:
    """读 Windows 版本（注册表 HKLM\\...\\CurrentVersion，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，注册表版本接口不可用（降级为文档指引）"
    v = get_version()
    if not v:
        return False, "未读到版本信息（HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion 不可读）"
    name = v.get("productname") or "Windows"
    ver = v.get("version") or ""
    build = str(v.get("currentbuild") or "")
    ubr = str(v.get("ubr") or "")
    tail = f"  (build {build}.{ubr})" if build else ""
    return True, f"{name}  {ver}{tail}（winreg 只读）"


def disk_report() -> tuple:
    """读系统盘空间（Win32 GetDiskFreeSpaceExW，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，GetDiskFreeSpaceExW 不可用（降级为文档指引）"
    d = disk_usage()
    if not d or d.get("total") is None:
        return False, "GetDiskFreeSpaceExW 调用失败"
    total, free = d["total"], d.get("free") or 0
    pct = (d.get("used", 0) / total * 100) if total else 0
    return True, (f"系统盘 总 {common.human(total)}  可用 {common.human(free)}  "
                  f"已用 {pct:.1f}%（GetDiskFreeSpaceExW 只读）")


def registry_report() -> tuple:
    """读界面/性能相关注册表键值（HKCU\\...\\Explorer\\Advanced，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，winreg 不可用（降级为文档指引）"
    if winreg is None:
        return False, "未加载 winreg（非 Windows），跳过"
    key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
    vals = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as hk:
            for name in ("VisualFXSetting", "TaskbarAl", "HideFileExt",
                         "ShowTaskViewButton", "LaunchTo"):
                try:
                    vals[name] = winreg.QueryValueEx(hk, name)[0]
                except OSError:
                    pass
    except OSError:
        return False, f"读取 HKCU\\{key} 失败（键不存在或无权限）"
    if not vals:
        return False, f"HKCU\\{key} 下无可读设置值"
    return True, ("Explorer 高级设置（winreg 只读）："
                  + "; ".join(f"{k}={v}" for k, v in vals.items()))


def wmi_report() -> tuple:
    """查 CIM/WMI 系统信息（Get-CimInstance Win32_OperatingSystem，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，CIM/WMI 不可用（降级为文档指引）"
    if not shutil.which("powershell"):
        return False, "未找到 powershell，无法查询 CIM/WMI"
    rc, out = common.run(
        'powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | '
        'Select-Object Caption,Version,LastBootUpTime | Format-List"', timeout=60)
    if rc != 0 or not (out or "").strip():
        return False, "Get-CimInstance 无输出（PowerShell 不可用或 WMI 服务未运行）"
    lines = ["CIM/WMI（Get-CimInstance 只读）："]
    for l in (out or "").splitlines()[:8]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def powercfg_report() -> tuple:
    """读当前电源计划（powercfg /getactivescheme + /list，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，powercfg 不可用（降级为文档指引）"
    if not shutil.which("powercfg"):
        return False, "未找到 powercfg（Windows 应自带），跳过"
    rc, out = common.run("powercfg /getactivescheme", timeout=60)
    if rc != 0 or not (out or "").strip():
        return False, "powercfg /getactivescheme 无输出"
    lines = ["电源计划（powercfg 只读）："]
    for l in (out or "").splitlines()[:4]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 全部计划：powercfg /list；展开设置项：powercfg /query")
    return True, "\n".join(lines)


def dism_report() -> tuple:
    """读当前 Windows 版本（DISM /Online /Get-CurrentEdition，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，DISM 不可用（降级为文档指引）"
    if not shutil.which("DISM") and not shutil.which("dism"):
        return False, "未找到 DISM（Windows 应自带），跳过"
    rc, out = common.run("DISM /Online /Get-CurrentEdition", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "DISM /Online /Get-CurrentEdition 无输出（需管理员权限）"
    lines = ["组件服务（DISM 只读）："]
    for l in (out or "").splitlines()[-6:]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 组件存储可回收量分析：DISM /Online /Cleanup-Image /AnalyzeComponentStore（只读但较慢）")
    return True, "\n".join(lines)


def storage_sense_report() -> tuple:
    """读存储感知策略（HKCU\\...\\StorageSense\\Parameters\\StoragePolicy，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，存储感知策略不可用（降级为文档指引）"
    if winreg is None:
        return False, "未加载 winreg（非 Windows），跳过"
    key = (r"Software\Microsoft\Windows\CurrentVersion\StorageSense"
           r"\Parameters\StoragePolicy")
    vals = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as hk:
            for name in ("01", "04", "32", "2048", "256"):
                try:
                    vals[name] = winreg.QueryValueEx(hk, name)[0]
                except OSError:
                    pass
    except OSError:
        return False, f"读取 HKCU\\{key} 失败（未开启过存储感知时该键不存在）"
    if not vals:
        return False, "未配置存储感知策略（StoragePolicy 键值为空）"
    return True, ("存储感知策略（winreg 只读）："
                  + "; ".join(f"{k}={v}" for k, v in vals.items())
                  + "（01=启用 / 04=Downloads / 32=临时文件 / 2048=回收站周期）")


def delivery_opt_report() -> tuple:
    """统计传递优化缓存占用（DO Cache 目录，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，传递优化缓存不可用（降级为文档指引）"
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not root:
        return False, "未取到 SystemRoot，无法定位传递优化缓存"
    path = os.path.join(root, "SoftwareDistribution", "DeliveryOptimization",
                        "Cache")
    if not os.path.isdir(path):
        return False, "无传递优化缓存目录（DO 未启用或尚未下载）"
    sz = common.list_dir_size(path)
    if not sz:
        return False, "传递优化缓存为空"
    return True, (f"传递优化缓存：{common.human(sz)}（{path}，只读统计；"
                  "清理会重新下载，不影响已装更新）")


def windows_update_report() -> tuple:
    """读上次更新检测时间（HKLM\\...\\WindowsUpdate\\Auto Update\\Results\\Detect，只读）。"""
    if not _is_windows():
        return False, "非 Windows 环境，Windows 更新注册表接口不可用（降级为文档指引）"
    if winreg is None:
        return False, "未加载 winreg（非 Windows），跳过"
    key = (r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate"
           r"\Auto Update\Results\Detect")
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as hk:
            try:
                last = winreg.QueryValueEx(hk, "LastSuccessTime")[0]
            except OSError:
                return False, "未读到上次成功检测时间（Results\\Detect 无值）"
    except OSError:
        return False, f"读取 HKLM\\{key} 失败"
    return True, f"上次成功检测更新：{last}（winreg 只读；装更新请用官方图形入口）"


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("version_report", "Windows 版本（注册表 HKLM\\...\\CurrentVersion，只读）"),
    ("disk_report", "系统盘空间（Win32 GetDiskFreeSpaceExW，只读）"),
    ("registry_report", "Explorer 高级设置（winreg 读 HKCU，只读）"),
    ("wmi_report", "CIM/WMI 系统信息（Get-CimInstance 只读查询）"),
    ("powercfg_report", "电源计划（powercfg /getactivescheme 只读）"),
    ("dism_report", "组件服务 DISM（/Online /Get-CurrentEdition 只读）"),
    ("storage_sense_report", "存储感知策略（winreg 读 StoragePolicy 只读）"),
    ("delivery_opt_report", "传递优化缓存（DO Cache 占用统计，只读）"),
    ("windows_update_report", "Windows 更新检测时间（winreg 只读）"),
)


def environment_report() -> list:
    """返回本机 Windows 系统接口可用性概览（✓ 可用 / ✗ 未装/非 Windows）。"""
    lines = ["Windows 系统接口可用性（文档跟踪层）："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def windows_doc_list() -> list:
    """返回 Windows 接口文档参考清单（供 CLI/GUI 展示）。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
        lines.append("    协议:")
        for p in ref.get("protocols", []):
            lines.append(f"      - {p}")
        lines.append("    接口:")
        for i in ref.get("interfaces", []):
            lines.append(f"      - {i}")
        lines.append(f"    建议: {ref.get('summary', '')}")
    return lines


# --------------------------------------------------------------------------- #
# 官方写接口（深度调优）：只往「安全方向」写，且只用各工具自己的官方子命令。       #
#   · fsutil   : fsutil behavior set（NTFS 元数据写行为，官方）                  #
#   · netsh    : netsh int tcp set global（TCP 全局参数）+ advfirewall（只开不关）#
#   · powercfg : /change（超时）、/h /type reduced（缩减休眠文件，不彻底关闭）     #
#   · sfc      : /scannow（官方校验并还原受保护系统文件，不动用户数据）           #
# 关键约束：runner 以 fn() 无参派发，故参数一律内置自动探测。                     #
# --------------------------------------------------------------------------- #

def fsutil_disable_last_access(on: bool = True) -> tuple:
    """NTFS 关闭「最后访问时间」更新（fsutil behavior set DisableLastAccess，官方）。

    关掉后 NTFS 不再为每次读取回写元数据时间戳，减少写放大（SSD 更明显）。
    """
    if not _is_windows():
        return False, "非 Windows 环境，fsutil 写接口不可用（降级为文档指引）"
    if not shutil.which("fsutil"):
        return False, "未找到 fsutil（Windows 应自带），跳过"
    val = "1" if on else "0"
    rc, out = common.run(f"fsutil behavior set DisableLastAccess {val}")
    if rc != 0:
        return False, out or "fsutil behavior set 失败（需管理员权限）"
    return True, (f"DisableLastAccess={val}（fsutil 官方接口；NTFS 少写元数据、"
                  "减少 SSD 写放大；需重启生效）")


def fsutil_disable_8dot3(on: bool = True) -> tuple:
    """关闭 NTFS 8.3 短文件名生成（fsutil behavior set disable8dot3，官方）。"""
    if not _is_windows():
        return False, "非 Windows 环境，fsutil 写接口不可用（降级为文档指引）"
    if not shutil.which("fsutil"):
        return False, "未找到 fsutil（Windows 应自带），跳过"
    val = "1" if on else "0"
    rc, out = common.run(f"fsutil behavior set disable8dot3 {val}")
    if rc != 0:
        return False, out or "fsutil behavior set disable8dot3 失败（需管理员权限）"
    return True, (f"disable8dot3={val}（fsutil 官方接口；新建文件不再生成 8.3 短名，"
                  "减少目录元数据写入）")


def netsh_tcp_autotuning() -> tuple:
    """TCP 接收窗口自动调为 normal（netsh int tcp set global，官方 + RFC 7323）。

    autotuninglevel=normal 让 Windows 按带宽时延积自动缩放接收窗口（RFC 7323），
    这是长肥管道下的推荐值；本工具只调到 normal，**不禁用**自动调优。
    """
    if not _is_windows():
        return False, "非 Windows 环境，netsh 写接口不可用（降级为文档指引）"
    if not shutil.which("netsh"):
        return False, "未找到 netsh（Windows 应自带），跳过"
    rc, out = common.run("netsh int tcp set global autotuninglevel=normal")
    if rc != 0:
        return False, out or "netsh int tcp set global 失败（需管理员权限）"
    return True, ("autotuninglevel=normal（netsh 官方接口 + RFC 7323 窗口缩放；"
                  "只读核对 netsh int tcp show global）")


def netsh_tcp_rss() -> tuple:
    """开启接收侧缩放 RSS（netsh int tcp set global rss=enabled，官方）。"""
    if not _is_windows():
        return False, "非 Windows 环境，netsh 写接口不可用（降级为文档指引）"
    if not shutil.which("netsh"):
        return False, "未找到 netsh（Windows 应自带），跳过"
    rc, out = common.run("netsh int tcp set global rss=enabled")
    if rc != 0:
        return False, out or "netsh int tcp set global rss 失败（需管理员权限）"
    return True, ("rss=enabled（netsh 官方接口；收包中断散到多 CPU，"
                  "与 Linux RPS 同一思路）")


def netsh_tcp_ecn() -> tuple:
    """开启 ECN 显式拥塞通知（netsh int tcp set global ecncapability，RFC 3168）。"""
    if not _is_windows():
        return False, "非 Windows 环境，netsh 写接口不可用（降级为文档指引）"
    if not shutil.which("netsh"):
        return False, "未找到 netsh（Windows 应自带），跳过"
    rc, out = common.run("netsh int tcp set global ecncapability=enabled")
    if rc != 0:
        return False, out or "netsh int tcp set global ecncapability 失败（需管理员权限）"
    return True, ("ecncapability=enabled（netsh 官方接口 + RFC 3168；"
                  "个别老旧设备不兼容时可关回 disabled）")


def netsh_firewall_on() -> tuple:
    """开启 Windows 防火墙全部配置档（netsh advfirewall set allprofiles state on）。

    官方接口，**只开不关**——绝不做 `state off`（关防火墙会把机器暴露在网络上）。
    """
    if not _is_windows():
        return False, "非 Windows 环境，netsh advfirewall 不可用（降级为文档指引）"
    if not shutil.which("netsh"):
        return False, "未找到 netsh（Windows 应自带），跳过"
    rc, out = common.run("netsh advfirewall set allprofiles state on")
    if rc != 0:
        return False, out or "netsh advfirewall set 失败（需管理员权限）"
    return True, ("防火墙已开启（域/专用/公用三档，netsh 官方接口；"
                  "本工具绝不做 allprofiles state off）")


def powercfg_monitor_timeout(ac: int = 15, dc: int = 10) -> tuple:
    """设显示器关闭超时（powercfg /change monitor-timeout-ac|dc，官方）。"""
    if not _is_windows():
        return False, "非 Windows 环境，powercfg 写接口不可用（降级为文档指引）"
    if not shutil.which("powercfg"):
        return False, "未找到 powercfg（Windows 应自带），跳过"
    rc, out = common.run(
        f"powercfg /change monitor-timeout-ac {ac} & "
        f"powercfg /change monitor-timeout-dc {dc}")
    if rc != 0:
        return False, out or "powercfg /change 失败（超时值需在允许范围内）"
    return True, (f"显示器关闭超时 插电={ac}min / 电池={dc}min"
                  "（powercfg 官方接口；0 表示从不）")


def powercfg_hibernate_reduced() -> tuple:
    """把休眠文件缩减为 reduced（powercfg /h /type reduced，官方）。

    比 `powercfg /hibernate off` 温和：hiberfil.sys 从「内存 40%」降到更小，
    仍保留快速启动（Fast Startup），适合想回收空间又不想丢快速启动的机器。
    """
    if not _is_windows():
        return False, "非 Windows 环境，powercfg 写接口不可用（降级为文档指引）"
    if not shutil.which("powercfg"):
        return False, "未找到 powercfg（Windows 应自带），跳过"
    rc, out = common.run("powercfg /h /type reduced")
    if rc != 0:
        return False, out or "powercfg /h /type reduced 失败（需管理员权限）"
    return True, ("休眠文件类型=reduced（powercfg 官方接口；"
                  "保留快速启动、只压缩 hiberfil.sys；彻底关闭请用 powercfg /hibernate off）")


def sfc_scan() -> tuple:
    """系统文件校验并修复（sfc /scannow，官方；只还原受保护系统文件）。"""
    if not _is_windows():
        return False, "非 Windows 环境，sfc 不可用（降级为文档指引）"
    if not shutil.which("sfc"):
        return False, "未找到 sfc（Windows 应自带），跳过"
    rc, out = common.run("sfc /scannow", timeout=600)
    if rc != 0:
        return False, out or "sfc /scannow 未正常结束（需管理员权限、耗时较长）"
    return True, ("sfc /scannow 已完成（官方校验并还原受保护系统文件，"
                  "不动用户数据；明细见 %SystemRoot%\\Logs\\CBS\\CBS.log）")


# 官方写接口清单（仅用于展示，**不在展示时调用**——调用即写系统）。
# 每项：(函数名, 官方写子命令说明)
TUNES = (
    ("fsutil_disable_last_access", "fsutil behavior set DisableLastAccess 1（NTFS 少写元数据、减 SSD 写放大）"),
    ("fsutil_disable_8dot3", "fsutil behavior set disable8dot3 1（不再生成 8.3 短名）"),
    ("netsh_tcp_autotuning", "netsh int tcp set global autotuninglevel=normal（RFC 7323 窗口自动调优）"),
    ("netsh_tcp_rss", "netsh int tcp set global rss=enabled（接收侧缩放，多核分摊收包）"),
    ("netsh_tcp_ecn", "netsh int tcp set global ecncapability=enabled（RFC 3168 ECN）"),
    ("netsh_firewall_on", "netsh advfirewall set allprofiles state on（防火墙只开不关）"),
    ("powercfg_monitor_timeout", "powercfg /change monitor-timeout-ac|dc <分钟>（官方电源微调）"),
    ("powercfg_hibernate_reduced", "powercfg /h /type reduced（缩减休眠文件，保留快速启动）"),
    ("sfc_scan", "sfc /scannow（官方校验并还原受保护系统文件，不动用户数据）"),
)


def windows_tune_list() -> list:
    """返回 Windows 官方写接口（深度调优）清单，供 CLI/GUI 展示。只读展示，不执行。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
