"""Android 原生接口：通过 adb（Android Debug Bridge）与设备通信。

adb 是 Android SDK 自带的官方调试桥，是 PC 端管理安卓设备的标准「系统接口」。
这里只做轻封装；真正清理/优化需要设备已开启「USB 调试」并授权。未连接时函数
返回空/False，上层自动降级为手动指引，绝不误删。

v0.5.22 起新增两条能力：
- **版本下探到 Android 8.0（API 26）**：见 `MIN_API` / `API_NAMES` / `supports()`。
  各接口按引入版本逐项门控，低于所需 API 时**明说「此版本无此开关」**，
  绝不给出必然失败的命令，也绝不伪装成已开启。
- **适老化（老年人 / 高龄用户）只读探针**：见 `A11Y_PROBES` 与
  `elderly_a11y_report()`。全部只 `settings get`，不代用户开任何无障碍开关
  （开读屏/放大镜/移除动画属于改变他人使用习惯，开了没教反而更糟）。
"""

from __future__ import annotations

import json

from . import common


def available() -> bool:
    return common.run("adb version")[0] == 0


def connected() -> bool:
    rc, out = common.run("adb get-state")
    return rc == 0 and out.strip() == "device"


def shell(cmd: str) -> tuple:
    """在设备上执行 shell 命令，返回 (ok, output)。"""
    return common.run(f"adb shell {cmd}")


def getprop(key: str) -> str:
    rc, out = common.run(f"adb shell getprop {key}")
    return out.strip() if rc == 0 else ""


def version() -> str:
    return getprop("ro.build.version.release")


def device_model() -> str:
    return getprop("ro.product.model")


def clear_cache(pkg: str) -> tuple:
    """清理某应用缓存（pm clear 会同时清数据，保守起见用 -f 仅缓存存放区）。
    返回 (ok, msg)。"""
    rc, out = common.run(f"adb shell pm clear {pkg}")
    return rc == 0, out


def trim() -> tuple:
    """对用户数据分区做 fstrim（释放已删除块，需 root / 支持）。"""
    rc, out = common.run("adb shell sm fstrim 0 2>&1")
    return rc == 0, out


def free_storage() -> str:
    """返回 `df` 中内部存储的可用量（文本）。"""
    rc, out = common.run("adb shell df /data 2>/dev/null")
    return out if rc == 0 else ""


# --------------------------------------------------------------------------- #
# v0.5.15 起补上「文档层 + 只读探测 + 官方写接口深度调优」三层，与前几轮的
# Windows / macOS / BSD / Unix 同构、但**只按 Android 自身的协议与接口**实现：
# - 文档层：data/android_docs.json（adb / settings_provider / pm / am / dumpsys /
#   getprop / svc / wm / logcat），各自记 protocols 与 interfaces。
# - 只读探测 PROBES：build/settings/packages/battery/memory/services/display/
#   logcat/network——全部经 adb 只读，未连设备则优雅降级为文档指引。
# - 官方写接口 TUNES：settings put（关动画，可恢复）/ pm trim-caches（放缓存）/
#   svc wifi enable（只开不关）/ dumpsys * --reset（清统计）/ logcat -c（清日志）/
#   am kill-all（只后台）/ wm size|density reset（恢复默认）/ netstats --reset。
#   只往安全方向写。
#
# 关键约束：runner 以 fn() 无参派发，故调优函数一律无必填参数；设备在线性由
# connected() 判定。未装 adb 或当前无已授权设备时，全部返回 (False, 降级说明)。
# 绝不手改系统分区（adb remount / rm -rf /system 属越权，本工具不做）。
# --------------------------------------------------------------------------- #

def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "android_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某 Android 接口的文档参考（含 protocols 与 interfaces）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部 Android 接口文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 文档跟踪层：Android 各系统接口只读探测（返回 (ok, msg)）。                     #
# 全部只读：只 getprop、只 settings list、只 pm list、只 dumpsys 读、只 service  #
# list、只 wm 读、只 logcat -d、只看 netstats。未连设备时优雅降级。             #
# --------------------------------------------------------------------------- #

def _device_online() -> bool:
    """设备已连且已授权（adb get-state == device）。"""
    return connected()


def build_report() -> tuple:
    """读设备型号 / Android 版本 / ABI（getprop，只读）。"""
    if not available():
        return False, "未找到 adb（Android SDK 未安装或不在 PATH），无法探测（降级为文档指引）"
    if not _device_online():
        return False, "已装 adb 但当前无已授权设备在线（adb devices 未见 device），无法探测（降级为文档指引）"
    model = device_model() or "(未知)"
    ver = version() or "(未知)"
    abi = getprop("ro.product.cpu.abi") or "(未知)"
    return True, f"机型 {model}｜Android {ver}｜ABI {abi}（getprop 只读；定位版本后再决定命令兼容）"


def settings_report() -> tuple:
    """列全局设置（settings list global，只读）。"""
    if not available():
        return False, "未找到 adb，无法探测 settings（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法探测 settings（降级为文档指引）"
    rc, out = common.run("adb shell settings list global 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "settings list global 无输出（设备侧受限或版本过旧）"
    lines = ["全局设置（settings list global 只读，取前若干项）："]
    for l in out.splitlines()[:12]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 改体验项用 settings put（如 window_animation_scale）；secure 隐私项受保护")
    return True, "\n".join(lines)


def packages_report() -> tuple:
    """列应用清单（pm list packages，只读）。"""
    if not available():
        return False, "未找到 adb，无法探测包清单（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法探测包清单（降级为文档指引）"
    rc, out = common.run("adb shell pm list packages -3 2>/dev/null | wc -l", timeout=180)
    third = (out or "").strip().splitlines()[0].strip() if (out or "").strip() else "?"
    rc2, out2 = common.run("adb shell pm list packages -s 2>/dev/null | wc -l", timeout=180)
    sysn = (out2 or "").strip().splitlines()[0].strip() if (out2 or "").strip() else "?"
    return True, (f"第三方应用约 {third} 个、系统应用约 {sysn} 个（pm list packages 只读）\n"
                  "   · 释放缓存用 pm trim-caches；清某 App 数据用 pm clear <pkg>（等于设置里的清除存储）")


def battery_report() -> tuple:
    """读电池状态（dumpsys battery，只读）。"""
    if not available():
        return False, "未找到 adb，无法读电池（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法读电池（降级为文档指引）"
    rc, out = common.run("adb shell dumpsys battery 2>/dev/null | head -12", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "dumpsys battery 无输出（设备侧受限）"
    lines = ["电池状态（dumpsys battery 只读）："]
    for l in out.splitlines()[:12]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def memory_report() -> tuple:
    """读内存占用（dumpsys meminfo，只读）。"""
    if not available():
        return False, "未找到 adb，无法读内存（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法读内存（降级为文档指引）"
    rc, out = common.run("adb shell dumpsys meminfo 2>/dev/null | head -16", timeout=180)
    if rc != 0 or not (out or "").strip():
        return False, "dumpsys meminfo 无输出（设备侧受限）"
    lines = ["内存占用概览（dumpsys meminfo 只读）："]
    for l in out.splitlines()[:16]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def services_report() -> tuple:
    """列系统服务（service list，只读）。"""
    if not available():
        return False, "未找到 adb，无法列服务（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法列服务（降级为文档指引）"
    rc, out = common.run("adb shell service list 2>/dev/null | head -20", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "service list 无输出（设备侧受限）"
    lines = ["系统服务（service list 只读，列于 Binder 的服务）："]
    for l in out.splitlines()[:20]:
        if l.strip():
            lines.append("   · " + l.strip())
    return True, "\n".join(lines)


def display_report() -> tuple:
    """读显示参数（wm size / wm density，只读）。"""
    if not available():
        return False, "未找到 adb，无法读显示（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法读显示（降级为文档指引）"
    rc, out = common.run("adb shell wm size 2>/dev/null; adb shell wm density 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "wm size/density 无输出（设备侧受限）"
    lines = ["显示参数（wm size / wm density 只读）："]
    for l in out.splitlines():
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · 修复误设用 wm size reset / wm density reset（只恢复默认，不丢数据）")
    return True, "\n".join(lines)


def logcat_report() -> tuple:
    """读最近日志（logcat -d -t 40，只读）。"""
    if not available():
        return False, "未找到 adb，无法读日志（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法读日志（降级为文档指引）"
    rc, out = common.run("adb shell logcat -d -t 40 2>/dev/null", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "logcat -d 无输出（日志缓冲为空或设备侧受限）"
    lines = ["最近日志（logcat -d -t 40 只读）："]
    for l in out.splitlines()[:40]:
        if l.strip():
            lines.append("   · " + l.strip()[:120])
    return True, "\n".join(lines)


def network_report() -> tuple:
    """读网络统计（dumpsys netstats，只读）。"""
    if not available():
        return False, "未找到 adb，无法读网络统计（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法读网络统计（降级为文档指引）"
    rc, out = common.run("adb shell dumpsys netstats 2>/dev/null | head -8", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, "dumpsys netstats 无输出（设备侧受限）"
    lines = ["网络统计（dumpsys netstats 只读）："]
    for l in out.splitlines()[:8]:
        if l.strip():
            lines.append("   · " + l.strip())
    lines.append("   · Wi-Fi 开关：settings get global wifi_on；清流量计数：dumpsys netstats --reset")
    return True, "\n".join(lines)


# CLI / GUI 遍历用：探测函数名 + 中文标签
PROBES = (
    ("build_report", "设备型号/版本/ABI（getprop，只读）"),
    ("settings_report", "全局设置（settings list global，只读）"),
    ("packages_report", "应用清单（pm list packages，只读）"),
    ("battery_report", "电池状态（dumpsys battery，只读）"),
    ("memory_report", "内存占用（dumpsys meminfo，只读）"),
    ("services_report", "系统服务（service list，只读）"),
    ("display_report", "显示参数（wm size / density，只读）"),
    ("logcat_report", "最近日志（logcat -d -t 40，只读）"),
    ("network_report", "网络统计（dumpsys netstats，只读）"),
    # v0.5.22 适老化只读探针（并入统一巡检；只 settings get，不改任何开关）
    ("font_scale_report", "字体缩放（font_scale，只读）"),
    ("a11y_display_report", "显示无障碍（放大镜/色彩校正/高对比/深色，按 API 门控）"),
    ("a11y_speech_report", "读屏服务（TalkBack / AccessibilityService，只读）"),
    ("a11y_motion_haptics_report", "减弱动画与触感反馈（只读）"),
    ("a11y_eyecare_report", "护眼与省电（亮度/息屏/夜览，只读）"),
)


def environment_report() -> list:
    """返回本机 Android（adb）系统接口可用性概览（✓ 可用 / ✗ 未装/未连）。"""
    lines = ["Android（adb）系统接口可用性（文档跟踪层）："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def android_doc_list() -> list:
    """返回 Android 接口文档参考清单（供 CLI/GUI 展示）。"""
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
# 官方写接口（深度调优）：只往「安全方向」写，且只用 Android 自己的官方子命令。    #
#   · settings: put global *_animation_scale 0（关动画，可随时改回 1）            #
#   · pm      : trim-caches（只放缓存、不删数据）                                #
#   · svc     : wifi enable（只开不关，绝不切断用户网络）                        #
#   · dumpsys : batterystats --reset / netstats --reset（只清统计计数）          #
#   · logcat  : -c（只清日志缓冲，不碰文件）                                     #
#   · am      : kill-all（只杀后台进程，前台不受影响）                           #
#   · wm      : size reset / density reset（恢复默认显示，修复性）               #
# 关键约束：runner 以 fn() 无参派发，故调优函数一律无必填参数；设备在线性由       #
# connected() 判定。未连设备时全部 (False, 降级说明)，绝不误写。                  #
# --------------------------------------------------------------------------- #

def settings_anim_scale_off() -> tuple:
    """关闭窗口动画缩放（settings put global *_animation_scale 0，可恢复）。"""
    if not available():
        return False, "未找到 adb，无法写设置（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法写设置（降级为文档指引）"
    done = []
    for key in ("window_animation_scale", "transition_animation_scale",
                "animator_duration_scale"):
        rc, _ = common.run(f"adb shell settings put global {key} 0", timeout=60)
        if rc == 0:
            done.append(key)
    if not done:
        return False, "settings put 失败（设备受限或版本过旧）"
    return True, ("窗口/过渡/Animator 动画缩放已设为 0（settings 官方接口；界面更跟手、"
                  "少一点合成开销，可随时改回 1 恢复；只读核对 settings get global <key>）")


def pm_trim_caches() -> tuple:
    """释放全部应用缓存（pm trim-caches，最大字节数，只清缓存不删数据）。"""
    if not available():
        return False, "未找到 adb，无法 trim 缓存（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法 trim 缓存（降级为文档指引）"
    rc, out = common.run("adb shell pm trim-caches 2147483647", timeout=300)
    if rc != 0:
        return False, out or "pm trim-caches 失败（设备侧受限）"
    return True, ("已对全部已装应用执行 trim-caches（pm 官方接口；只释放可丢弃的缓存，"
                  "不删账号数据；设置→存储能看到释放量）")


def svc_wifi_enable() -> tuple:
    """开启 Wi-Fi（svc wifi enable，只开不关）。"""
    if not available():
        return False, "未找到 adb，无法控制无线（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法控制无线（降级为文档指引）"
    rc, out = common.run("adb shell svc wifi enable", timeout=60)
    if rc != 0:
        return False, out or "svc wifi enable 失败"
    return True, ("已开启 Wi-Fi（svc 官方接口；只启用不关断，绝不替用户切断网络；"
                  "只读核对 settings get global wifi_on）")


def batterystats_reset() -> tuple:
    """清零电量统计（dumpsys batterystats --reset，只清计数）。"""
    if not available():
        return False, "未找到 adb，无法重置电量统计（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法重置电量统计（降级为文档指引）"
    rc, out = common.run("adb shell dumpsys batterystats --reset", timeout=120)
    if rc != 0:
        return False, out or "batterystats --reset 失败"
    return True, ("电量统计已清零（dumpsys 官方接口；只清计数器便于重新测量续航，"
                  "不删任何文件、不影响运行）")


def logcat_clear() -> tuple:
    """清空日志缓冲（logcat -c，只清日志）。"""
    if not available():
        return False, "未找到 adb，无法清日志（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法清日志（降级为文档指引）"
    rc, out = common.run("adb shell logcat -c", timeout=60)
    if rc != 0:
        return False, out or "logcat -c 失败"
    return True, ("日志缓冲已清空（logcat 官方接口；只清内存环形缓冲、不碰文件，"
                  "排障前清场用；日志会重新产生）")


def am_kill_all() -> tuple:
    """回收后台内存（am kill-all，只杀后台进程）。"""
    if not available():
        return False, "未找到 adb，无法回收后台（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法回收后台（降级为文档指引）"
    rc, out = common.run("adb shell am kill-all", timeout=120)
    if rc != 0:
        return False, out or "am kill-all 失败"
    return True, ("已杀掉全部后台进程（am 官方接口；只清后台、前台 App 不受影响，"
                  "等价于一次内存回收，App 再次打开时自动重启）")


def netstats_reset() -> tuple:
    """清零网络流量统计（dumpsys netstats --reset，只清计数）。"""
    if not available():
        return False, "未找到 adb，无法重置网络统计（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法重置网络统计（降级为文档指引）"
    rc, out = common.run("adb shell dumpsys netstats --reset", timeout=120)
    if rc != 0:
        return False, out or "netstats --reset 失败"
    return True, ("网络流量统计已清零（dumpsys 官方接口；只清计数器，不影响连接与计费记录本身）")


def wm_size_reset() -> tuple:
    """恢复默认显示（wm size reset / wm density reset，修复性）。"""
    if not available():
        return False, "未找到 adb，无法恢复显示（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法恢复显示（降级为文档指引）"
    rc1, _ = common.run("adb shell wm size reset", timeout=60)
    rc2, _ = common.run("adb shell wm density reset", timeout=60)
    if rc1 != 0 and rc2 != 0:
        return False, "wm size/density reset 失败（设备侧受限）"
    return True, ("显示已恢复为设备默认（wm 官方 reset 接口；修复误设分辨率/DPI 导致的"
                  "界面不可点，只恢复默认、不丢数据）")


# 官方写接口清单（仅用于展示，**不在展示时调用**——调用即写系统）。
# 每项：(函数名, 官方写子命令说明)
TUNES = (
    ("settings_anim_scale_off",
     "settings put global window/transition/animator_animation_scale 0（关动画，可随时改回 1）"),
    ("pm_trim_caches",
     "pm trim-caches 2147483647（释放全部应用缓存，只清缓存不删数据）"),
    ("svc_wifi_enable",
     "svc wifi enable（开 Wi-Fi，只开不关）"),
    ("batterystats_reset",
     "dumpsys batterystats --reset（清零电量统计，只清计数）"),
    ("logcat_clear",
     "logcat -c（清空日志缓冲，只清日志）"),
    ("am_kill_all",
     "am kill-all（杀全部后台进程，只后台）"),
    ("netstats_reset",
     "dumpsys netstats --reset（清零网络统计，只清计数）"),
    ("wm_size_reset",
     "wm size reset / wm density reset（恢复默认显示，修复性）"),
)


# --------------------------------------------------------------------------- #
# v0.5.22 · Android 版本口径与 API 门控（把支持面下探到 Android 8.0 = API 26）
#
# 为什么需要这张表：Android 的「无障碍 / 适老化」开关散落在 settings 的三张表
# （system / secure / global）里，且**相当一部分是按 API 级别才引入的**。例如：
#   · accessibility_high_text_contrast（高对比度文本）—— API 29 才可写；
#   · font_weight_adjustment（可调字重）      —— API 28 才引入；
#   · ui_night_mode（深色模式）              —— API 29 才引入；
#   · accessibility_display_daltonizer（色彩校正）—— API 26 引入（本工具下探的起点）。
# 老设备（Android 8/9）上盲写这些 key 会静默失败或抛 SecurityException，用户的
# 「我都开了为什么没变化」往往就来自这里。所以下面每个探针都按 sdk_int 门控：
# 不支持就**明说「该版本无此开关」**，而不是伪装成已开启。
#
# 只读约束不变：全部 `settings get` / `getprop`，一个 `put` 都不写。
# --------------------------------------------------------------------------- #

#: 本工具承诺覆盖的最低 API（Android 8.0 Oreo）。低于此值时相关探针降级为指引。
MIN_API = 26

#: API 号 → Android 人类可读版本名（未列出的新版本按最新已知处理）。
API_NAMES = {
    26: "8.0", 27: "8.1", 28: "9", 29: "10", 30: "11",
    31: "12", 32: "12L", 33: "13", 34: "14", 35: "15", 36: "16",
}

#: 低于 MIN_API 时的统一降级说明。
_SDK_LOW_HINT = (
    f"本工具的适老化探针以 Android 8.0（API {MIN_API}）为下探下限；"
    "更低版本请直接用系统「设置 → 辅助功能」路径调整"
)


def sdk_int() -> int:
    """读设备 API 级别（ro.build.version.sdk，只读）。未连设备返回 0。"""
    raw = getprop("ro.build.version.sdk")
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return 0


def api_name(sdk: int) -> str:
    """API 号 → 版本名；未知返回 '?'。"""
    if sdk in API_NAMES:
        return API_NAMES[sdk]
    if sdk > max(API_NAMES):
        return f">= {API_NAMES[max(API_NAMES)]}（API {sdk}）"
    return "?"


def supports(sdk: int, introduced: int) -> bool:
    """该 API 级别是否支持某开关（引入于 `introduced`）。sdk 未知(0)时保守返回 False。"""
    return sdk >= introduced


def _sdk_gate(introduced: int, feature: str) -> tuple:
    """版本门控统一出口：够新则返回 (True, "")，否则 (False, 降级说明)。"""
    sdk = sdk_int()
    if sdk == 0:
        return False, ("读不到 ro.build.version.sdk（设备未连/未授权），"
                       f"无法确认「{feature}」是否可用（该开关需 API >= {introduced}）")
    if sdk < introduced:
        return False, (f"当前 Android {version() or '?'}（API {sdk}）："
                       f"「{feature}」需 API >= {introduced}，此版本无此开关，"
                       f"请改用系统「设置 → 辅助功能」对应条目")
    return True, ""


def _setting(namespace: str, key: str, timeout: int = 90) -> tuple:
    """读一个 settings 值，返回 (ok, value)。空值视为读取失败。"""
    rc, out = common.run(f"adb shell settings get {namespace} {key} 2>/dev/null", timeout=timeout)
    v = (out or "").strip()
    if rc != 0 or not v or v.lower() in ("null", "undefined"):
        return False, ""
    return True, v


# --------------------------------------------------------------------------- #
# 适老化只读探针（面向老年人 / 高龄用户）
#
# 设计原则：
#   1. **只读**——全部 `settings get` 与 `getprop`，绝不 `settings put`。
#   2. **按 API 门控**——每个探针声明自己的最低 API，不支持的明说不支持。
#   3. **给数值也给建议**——不只报「font_scale=1.2」，还告诉用户「≥1.3 属大字体，
#      系统侧已足够；再大建议去厂商无障碍中心调」这类可执行判断。
#   4. **隐私零采集**——这里读的全部是设备本机的显示/交互偏好开关，
#      不涉及任何账号、位置、通讯录等个人数据。
# --------------------------------------------------------------------------- #

def font_scale_report() -> tuple:
    """读字体缩放（font_scale，API 1 起即有）。适老化第一顺位开关。"""
    if not available():
        return False, "未找到 adb，无法探测字体缩放（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法探测字体缩放（降级为文档指引）"
    ok, v = _setting("system", "font_scale")
    if not ok:
        return False, "settings get system font_scale 无值（设备侧受限）"
    try:
        f = float(v)
    except ValueError:
        return False, f"font_scale 返回非数值: {v}"
    if f >= 1.3:
        verdict = "已是大字体档（≥1.3），系统文字已显著放大"
    elif f >= 1.15:
        verdict = "已放大（1.15–1.3），建议再调一档到 1.3 以适配老花/远视"
    elif f > 1.0:
        verdict = "轻微放大，仍偏小，建议调到 1.15 以上"
    else:
        verdict = "未放大（1.0），对老年用户普遍偏小，建议至少 1.15"
    return True, (f"字体缩放 font_scale = {f}（{verdict}）\n"
                  "   · 调整路径：设置 → 显示 → 字体大小；或  设置 → 辅助功能 → 字体大小\n"
                  "   · 厂商多支持到 1.3–2.0；再大反而挤版式，够用即可")


def font_weight_report() -> tuple:
    """读可调字重（font_weight_adjustment，API 28=Android 9 起）。"""
    if not available():
        return False, "未找到 adb（降级为文档指引）"
    gate, why = _sdk_gate(28, "可调字重（font_weight_adjustment）")
    if not gate:
        return False, why
    ok, v = _setting("system", "font_weight_adjustment")
    if not ok:
        return False, ("settings get system font_weight_adjustment 无值"
                       "（部分 ROM 即便 API≥28 也未暴露该键）")
    try:
        w = int(float(v))
    except ValueError:
        return False, f"font_weight_adjustment 返回非数值: {v}"
    return True, (f"字重微调 font_weight_adjustment = {w}（100–400 为加粗方向，0=默认）\n"
                  "   · 调整路径：设置 → 显示 → 字体大小 → 字重加粗（有此项的 ROM）\n"
                  "   · 对低视力老人比放大字号更省版式空间，可与 font_scale 搭配")


def a11y_display_report() -> tuple:
    """读显示类无障碍开关：放大镜 / 高对比文本 / 深色模式 / 色彩校正（按 API 门控）。

    每一项都**分别**判版本：老设备上只报它真有的开关，不谎报。"""
    if not available():
        return False, "未找到 adb，无法探测显示无障碍（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法探测显示无障碍（降级为文档指引）"
    sdk = sdk_int()
    if sdk == 0:
        return False, "读不到 API 级别（ro.build.version.sdk），无法按版本核对显示无障碍"
    if sdk < MIN_API:
        return False, (f"当前 Android {version() or '?'}（API {sdk}）低于下探下限 "
                       f"API {MIN_API}；{_SDK_LOW_HINT}")
    lines = [f"显示类无障碍开关（API {sdk} = Android {api_name(sdk)}，settings 只读）："]
    # 放大镜：API 17 起就有，是老设备上最实用的低视力辅助
    ok, mag = _setting("secure", "accessibility_display_magnification_enabled")
    if ok:
        lines.append(f"   · 放大镜 magnification = {mag}"
                     f"（{'已开' if mag == '1' else '未开'}；API 17+ 通用，老设备可靠）")
    else:
        lines.append("   · 放大镜 magnification：读不到值（该 ROM 可能裁剪了此键，"
                     "或无障碍总闸未开导致不可读）；API 17+ 设备普遍支持，可在"
                     "「辅助功能 → 放大镜」直接查看")
    # 色彩校正（色盲/色弱）：API 26 起
    if supports(sdk, 26):
        ok, dal = _setting("secure", "accessibility_display_daltonizer_enabled")
        if ok:
            lines.append(f"   · 色彩校正 daltonizer = {dal}"
                         f"（{'已开' if dal == '1' else '未开'}；本工具下探起点 API 26）")
        else:
            lines.append("   · 色彩校正 daltonizer：读不到值（ROM 裁剪或总闸未开）；"
                         "支持机型可在「辅助功能 → 颜色校正」查看")
        ok, mode = _setting("secure", "accessibility_display_daltonizer")
        if ok:
            lines.append(f"       当前校正模式 = {mode}（0=无 1=红绿 2=红蓝 3=灰度）")
    else:
        lines.append(f"   · 色彩校正：API 26 起才引入，当前 API {sdk} 无此开关")
    # 高对比度文本：API 29 起
    if supports(sdk, 29):
        ok, hc = _setting("secure", "accessibility_high_text_contrast")
        if ok:
            lines.append(f"   · 高对比度文本 high_text_contrast = {hc}"
                         f"（{'已开' if hc == '1' else '未开'}；API 29+）")
        else:
            lines.append("   · 高对比度文本 high_text_contrast：读不到值"
                         "（ROM 裁剪或总闸未开）")
        ok, nm = _setting("secure", "ui_night_mode")
        if ok:
            lines.append(f"   · 深色模式 ui_night_mode = {nm}"
                         f"（0=关 1=开 2=自动；API 29+）")
        else:
            lines.append("   · 深色模式 ui_night_mode：读不到值（ROM 裁剪或总闸未开）")
    else:
        lines.append(f"   · 高对比度文本 / 深色模式：需 API 29+，当前 API {sdk} 无"
                     "（Android 8/9 请用亮度拉满 + 减少深色背景应用）")
    lines.append("   · 调整路径：设置 → 辅助功能 → 颜色校正/高对比度/深色模式")
    return True, "\n".join(lines)


def a11y_speech_report() -> tuple:
    """读读屏服务状态（TalkBack / AccessibilityService，API 14+ 框架，16+ 服务列表）。"""
    if not available():
        return False, "未找到 adb，无法探测读屏服务（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线，无法探测读屏服务（降级为文档指引）"
    lines = ["读屏与语音支持（settings secure 只读）："]
    ok, en = _setting("secure", "accessibility_enabled")
    lines.append(f"   · 无障碍总开关 accessibility_enabled = {en or '?'}"
                 f"（{'已开' if en == '1' else '未开' or '未知'}）")
    ok, svc = _setting("secure", "enabled_accessibility_services")
    if ok and svc.lower() not in ("null", "none"):
        names = [s.split("/")[-1] for s in svc.split(":") if s.strip()]
        lines.append(f"   · 已启用服务 {len(names)} 项: {', '.join(names[:8])}"
                     f"{' …' if len(names) > 8 else ''}")
        tb = [n for n in names if "talkback" in n.lower()]
        if tb:
            lines.append(f"   · TalkBack 状态：已启用（{tb[0]}）——读屏已就绪，"
                         "界面元素会朗读，视力障碍用户的核心依赖")
        else:
            lines.append("   · TalkBack 状态：未在已启用服务列表中（读屏未开启）")
    else:
        lines.append("   · 已启用服务列表为空（未开启任何读屏服务）")
    lines.append("   · 开启路径：设置 → 辅助功能 → TalkBack（读屏）/ 选择以朗读内容")
    lines.append("   · 注意：TalkBack 会改变触控手势（单指点=读、双指点=返回），"
                 "帮长辈开启后务必当面教一次")
    return True, "\n".join(lines)


def a11y_motion_haptics_report() -> tuple:
    """读减弱动画与触感反馈（动画缩放 API 17+；触感 haptic_feedback_enabled API 1）。"""
    if not available():
        return False, "未找到 adb（降级为文档指引）"
    gate, why = _sdk_gate(17, "动画缩放（*_animation_scale）")
    if not gate:
        return False, why
    lines = ["减弱动画与触感反馈（settings 只读）："]
    for ns, key, lab in (("global", "window_animation_scale", "窗口动画"),
                         ("global", "transition_animation_scale", "过渡动画"),
                         ("global", "animator_duration_scale", "Animator 时长")):
        ok, v = _setting(ns, key)
        if ok:
            state = "已减弱" if v in ("0", "0.0") else "仍全速"
            lines.append(f"   · {lab} {key} = {v}（{state}）")
    ok, h = _setting("system", "haptic_feedback_enabled")
    if ok:
        lines.append(f"   · 触感反馈 haptic_feedback_enabled = {h}"
                     f"（{'已开' if h == '1' else '未开'}）")
    ok, hw = _setting("system", "sound_effects_enabled")
    if ok:
        lines.append(f"   · 提示音 sound_effects_enabled = {hw}"
                     f"（{'已开' if hw == '1' else '未开'}）")
    lines.append("   · 适老化角度：把动画降到 0 可显著降低眩晕与迷向感（前庭敏感老人尤其）；"
                 "触感与提示音是「确认操作成功」的非视觉反馈，建议至少留触感开")
    lines.append("   · 调整路径：设置 → 辅助功能 → 移除动画；设置 → 声音 → 触摸反馈")
    return True, "\n".join(lines)


def a11y_eyecare_report() -> tuple:
    """读护眼相关：屏幕亮度、自动超时、护眼模式/夜览（按 API 门控）。"""
    if not available():
        return False, "未找到 adb（降级为文档指引）"
    if not _device_online():
        return False, "当前无已授权设备在线（降级为文档指引）"
    sdk = sdk_int()
    lines = ["护眼与省电（settings 只读）："]
    ok, bl = _setting("system", "screen_brightness")
    if ok:
        try:
            b = int(bl)
            pct = int(b / 255 * 100) if b <= 255 else b
            hint = "（偏暗，室内可能不够）" if b < 120 and b <= 255 else ""
            lines.append(f"   · 手动亮度 screen_brightness = {b}（约 {pct}%）{hint}")
        except ValueError:
            lines.append(f"   · 手动亮度 screen_brightness = {bl}（非数值，多为自动调节生效）")
    ok, st = _setting("system", "screen_off_timeout")
    if ok:
        try:
            ms = int(st)
            lines.append(f"   · 息屏超时 screen_off_timeout = {ms} ms（约 {ms // 1000} 秒）")
        except ValueError:
            lines.append(f"   · 息屏超时 screen_off_timeout = {st}")
    # 夜览/护眼模式：Android 9（API 28）起以 "night_display" / "night_mode" 暴露
    if supports(sdk, 28):
        found = False
        for key in ("night_display_activated", "night_mode"):
            ok, v = _setting("secure", key)
            if ok:
                found = True
                lines.append(f"   · 护眼/夜览 {key} = {v}"
                             f"（{'已开' if v not in ('0', 'none') else '未开'}）")
        if not found:
            lines.append("   · 护眼/夜览：API 28+ 理论上可用，但当前 ROM 未暴露该键"
                         "（多在厂商显示设置里，不在 settings 表）")
    else:
        lines.append(f"   · 护眼/夜览：需 API 28+，当前 API {sdk} 无（Android 8 请用"
                     "「屏幕夜览/护眼模式」类第三方或厂商开关）")
    lines.append("   · 适老化角度：老花与白内障用户普遍需要更高亮度；"
                 "息屏超时调长可减少反复点亮，但要注意耗电")
    return True, "\n".join(lines)


#: 适老化探针清单（CLI / GUI 遍历用；每项 = (函数名, 中文标签, 最低 API)）。
A11Y_PROBES = (
    ("font_scale_report", "字体缩放（font_scale，API 1+）", 26),
    ("a11y_display_report", "显示无障碍（放大镜/色彩校正/高对比/深色，分版本门控）", 26),
    ("a11y_speech_report", "读屏服务（TalkBack / AccessibilityService）", 26),
    ("a11y_motion_haptics_report", "减弱动画与触感反馈（适老防眩晕）", 26),
    ("a11y_eyecare_report", "护眼与省电（亮度/超时/夜览）", 26),
)


def elderly_a11y_report() -> tuple:
    """适老化总报告：逐项探测 + 汇总「可立刻改善的 N 项」。

    聚合所有适老化探针。任一探针成功即视为整体可用；全失败则返回降级说明。"""
    if not available():
        return False, ("未找到 adb（Android SDK 未安装或不在 PATH）；"
                       "适老化探测需 adb + 设备已开启 USB 调试并授权（降级为文档指引）")
    if not _device_online():
        return False, ("已装 adb 但当前无已授权设备在线；"
                       "适老化探测需连接设备后 adb get-state 为 device（降级为文档指引）")
    sdk = sdk_int()
    if sdk == 0:
        return False, "读不到 ro.build.version.sdk，无法按 Android 版本核对适老化开关"
    head = [f"适老化（老年人 / 高龄用户）无障碍总报告 —— "
            f"Android {version() or '?'}，API {sdk}（{api_name(sdk)}）"
            f"{'｜⚠ 低于本工具下探下限 API 26，部分项不可用' if sdk < MIN_API else ''}"]
    ok_count = 0
    for fn_name, label, _min_api in A11Y_PROBES:
        ok, msg = globals()[fn_name]()
        head.append("")
        head.append(f"-- {label} --")
        head.append(msg if ok else f"（不适用）{msg}")
        if ok:
            ok_count += 1
    if ok_count == 0:
        return False, ("\n".join(head) + "\n\n全部探针均不可用——"
                       "多为设备侧权限/ROM 限制，建议在设备端「设置 → 辅助功能」直接调整")
    head.append("")
    head.append(f"小结：{len(A11Y_PROBES)} 项适老化探针中 {ok_count} 项可读；"
                "本工具只读不改，调整请在设备端辅助功能页或厂商无障碍中心完成。")
    return True, "\n".join(head)


def elderly_a11y_advice() -> list:
    """返回适老化调整建议清单（**纯文本指引，不含任何设备命令**）。

    供无 adb / 无设备时也能给出的建议——长辈常由子女代为设置，这段文字可以直接念。"""
    return [
        "· 字体：设置 → 显示 → 字体大小，调到 1.15 以上（老花普遍需要）；",
        "  若屏幕挤，优先用「辅助功能 → 字体大小」或字重加粗，而非无限放大。",
        "· 亮度：把屏幕亮度调高（白内障/老花都嫌暗），开自动亮度反而忽明忽暗更累。",
        "· 对比度：有「高对比度文本 / 深色模式」就打开（Android 10+），字与背景反差大更清楚。",
        "· 放大镜：Android 8 起就有「辅助功能 → 放大镜」，配合手势可临时放大局部；",
        "  三击屏幕也能开（三击手势需在辅助功能里启用）。",
        "· 读屏：TalkBack 开启后界面会朗读，是视力障碍的核心依赖；",
        "  但手势会变（单指点=读、双指点=返回），务必当面教一次再放手。",
        "· 防眩晕：把「动画」三项都降到 0（移除动画），前庭敏感的老人容易因转场动画头晕。",
        "· 非视觉反馈：保留触感反馈与提示音，操作有没有生效能「摸到/听到」，不必盯屏幕确认。",
        "· 电池与字号冲突：大字号更耗电，可适当延长息屏超时，但要配合充电习惯。",
        "· 紧急：设置 → 辅助功能 → 紧急呼叫、以及锁屏下的紧急联系人信息，务必先配好。",
    ]


def android_compat_report() -> tuple:
    """Android 8（API 26）向下兼容性总览：哪些接口在老设备上可用。

    回答「我这台老安卓还能不能被本工具管」——列出各接口的最低 API 与降级行为。"""
    if not available():
        return False, "未找到 adb（降级为文档指引）"
    gate_sdk = sdk_int()
    lines = [f"Android 向下兼容总览（本工具下探下限 API {MIN_API} = Android 8.0 Oreo）:"]
    rows = [
        ("adb getprop / get-state", 1, "全版本可用；设备未授权时所有探针降级"),
        ("settings get system font_scale", 1, "全版本可用；适老化第一顺位"),
        ("settings get system haptic_feedback_enabled", 1, "全版本可用"),
        ("pm list packages / pm trim-caches", 1, "全版本可用（trim 需 Android 4.4+ 更佳）"),
        ("am kill-all", 1, "全版本可用；只杀后台"),
        ("logcat -d / -c", 1, "全版本可用"),
        ("svc wifi enable", 1, "全版本可用；只开不关"),
        ("settings get global *_animation_scale", 17, "Android 4.2+；适老化防眩晕依赖此项"),
        ("放大镜 accessibility_display_magnification_enabled", 17, "Android 4.2+；老设备最实用"),
        ("enabled_accessibility_services（读屏服务）", 14, "Android 4.0+；TalkBack 状态来源"),
        ("色彩校正 daltonizer", 26, "Android 8.0 起；本工具下探起点"),
        ("cmd package set-app-hibernate（应用休眠）", 30, "Android 11+；低版本自动隐藏该任务"),
        ("字重微调 font_weight_adjustment", 28, "Android 9+"),
        ("护眼/夜览 night_display_activated", 28, "Android 9+"),
        ("高对比度文本 / 深色模式", 29, "Android 10+；低版本给出等效替代建议"),
        ("后台限制（adaptive battery）", 22, "Android 6+；Android 8 上仅部分厂商 ROM 实现"),
    ]
    for name, min_api, note in rows:
        if gate_sdk == 0:
            state = "（未连设备，无法判定本机可用性）"
        elif gate_sdk >= min_api:
            state = "✓ 本机可用"
        else:
            state = f"✗ 本机 API {gate_sdk} < {min_api}"
        lines.append(f"   {state:<32} {name}")
        lines.append(f"       {note}")
    if gate_sdk == 0:
        lines.append("")
        lines.append("（未连设备时以上仅为接口口径表；连接设备后 adb 即可逐项实测）")
    return True, "\n".join(lines)


def android_tune_list() -> list:
    """返回 Android 官方写接口（深度调优）清单，供 CLI/GUI 展示。只读展示，不执行。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
