"""声学与音律子系统（acoustics）：只读探针 + 频率/波动工程换算 + 三分损益生成器。

用户缘起：「声音、频率、振动、音调、声率、黄钟大吕……最有可能应用在无线技术、
电磁波，还有就是喇叭或耳机」。本子系统把这条线索落成四轴知识库（data/
acoustics_docs.json）：

1. **sound_basics**   声学基础：频率·波长·声速·共振·分贝（IEC 61672-1 / ISO 226）
2. **chinese_pitch**  中国音律：黄钟大吕·十二律·三分损益（管律，典籍口径）
3. **wireless_em**    无线与电磁波：ITU 无线电规则与 ISM 频段（c = λf）
4. **audio_hardware** 音频硬件：喇叭与耳机的电声标准（IEC 60268 / EN 50332）

红线（与全工具一致，本模块**绝不**越界）：
- **绝不播放任何声音**（无 aplay/play 写路径，不试音、不响铃）；
- **绝不调音量**（无 pactl set-sink-volume / amixer set 路径）；
- **绝不采集麦克风内容**（不录音、不抓音频流，只枚举设备存在性）；
- **无任何射频发射路径**（不改网卡功率/信道/监管域，不发无线信号）。

本模块做三件事：① 频率↔波长/声速/天线尺寸的工程换算（波动几何公共底座）；
② 三分损益十二律生成器（古典频率计量算例，音分偏差自动对十二平均律）；
③ 本机音频设备只读枚举（ALSA/PulseAudio 能力面）与 EN 50332 听力保护参照。
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess


def _load_refs() -> dict:
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "acoustics_docs.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:  # noqa: BLE001
        return {}


REFS = _load_refs()


def reference(key: str) -> dict:
    """返回某声学主题的文档参考（含 protocols/interfaces/advice）。"""
    return REFS.get(key, {})


def reference_all() -> dict:
    """返回全部声学主题文档参考。"""
    return REFS


# --------------------------------------------------------------------------- #
# 波动几何换算（纯函数：c = f·λ；空气中 c ≈ 331.3 + 0.606·T，T 为摄氏温度）      #
# --------------------------------------------------------------------------- #

# 各介质声速基准（m/s）；空气按 331.3 + 0.606·T 温度修正（教材级口径）
SPEED_OF_SOUND_MEDIA = {
    "air": ("空气", None),            # 需按温度修正
    "water": ("水（25 °C）", 1497.0),
    "seawater": ("海水（25 °C）", 1531.0),
    "steel": ("钢（纵波）", 5960.0),
    "aluminum": ("铝（纵波）", 6420.0),
    "glass": ("玻璃", 5640.0),
    "concrete": ("混凝土", 3400.0),
    "wood": ("橡木（顺纹）", 3850.0),
}

# 电磁波速（真空，m/s，定义值）
SPEED_OF_LIGHT = 299_792_458.0


def speed_of_sound(medium: str = "air", temp_c: float = 20.0) -> float:
    """返回介质声速（m/s）。空气用线性温度近似 c ≈ 331.3 + 0.606·T。"""
    if medium == "air":
        return 331.3 + 0.606 * float(temp_c)
    entry = SPEED_OF_SOUND_MEDIA.get(medium)
    if entry and entry[1]:
        return float(entry[1])
    raise ValueError(f"未知介质: {medium!r}（可选: {sorted(SPEED_OF_SOUND_MEDIA)}）")


def wavelength(freq_hz: float, medium: str = "air", temp_c: float = 20.0) -> float:
    """频率 → 波长（m）。λ = c/f；f ≤ 0 抛 ValueError。"""
    f = float(freq_hz)
    if f <= 0:
        raise ValueError("频率必须为正数（Hz）")
    return speed_of_sound(medium, temp_c) / f


def frequency_from_wavelength(wavelength_m: float, medium: str = "air",
                              temp_c: float = 20.0) -> float:
    """波长（m）→ 频率（Hz）。f = c/λ。"""
    lam = float(wavelength_m)
    if lam <= 0:
        raise ValueError("波长必须为正数（m）")
    return speed_of_sound(medium, temp_c) / lam


def em_wavelength(freq_hz: float) -> float:
    """电磁波频率 → 真空波长（m）。λ = c/f，c = 299 792 458 m/s。"""
    f = float(freq_hz)
    if f <= 0:
        raise ValueError("频率必须为正数（Hz）")
    return SPEED_OF_LIGHT / f


def antenna_length(freq_hz: float, fraction: float = 0.25) -> float:
    """天线振子长度估算（m）：默认 λ/4 单极子，也可取 0.5（半波偶极）。"""
    if fraction <= 0:
        raise ValueError("fraction 必须为正数（0.25=λ/4，0.5=λ/2）")
    return em_wavelength(freq_hz) * float(fraction)


def db_sum(levels_db) -> float:
    """多个同量纲分贝值按能量叠加（10·log10(Σ10^(L/10))）。"""
    vals = [float(x) for x in levels_db if x is not None]
    if not vals:
        raise ValueError("levels_db 不能为空")
    if any(v <= 0 for v in vals) and len(vals) == 1:
        # 单一声源直接返回（允许 0 dB 参考点场景）
        return vals[0]
    return 10.0 * math.log10(sum(10.0 ** (v / 10.0) for v in vals))


# --------------------------------------------------------------------------- #
# IEC 61672-1 频率计权查表（就近取标称频点，对数频率轴取最近邻）                 #
# --------------------------------------------------------------------------- #

def weighting_correction(freq_hz: float, weight: str = "A") -> float:
    """返回 IEC 61672-1 某频率的计权修正值（dB，相对 1 kHz）。

    标称值只有有限频点（31.5 Hz–20 kHz 倍频程），取对数频率轴上最近的频点。
    """
    w = weight.upper()
    table = REFS.get("sound_basics", {}).get("weighting_table", {}).get(w)
    if not table:
        raise ValueError(f"无 {weight} 计权表（可用: A/C/Z）")
    f = float(freq_hz)
    if f <= 0:
        raise ValueError("频率必须为正数（Hz）")
    freqs = sorted(float(k) for k in table)
    nearest = min(freqs, key=lambda k: abs(math.log2(k) - math.log2(f)))
    return float(table[str(int(nearest)) if str(int(nearest)) in table
                       else str(nearest)])


# --------------------------------------------------------------------------- #
# 三分损益十二律生成器（黄钟基数 81；损一 ×2/3，益一 ×4/3）                     #
# --------------------------------------------------------------------------- #

# 生成顺序：黄钟 →(损) 林钟 →(益) 太簇 →(损) 南吕 →(益) 姑冼 →(损) 应钟 →(益) 蕤宾
# →(益) 大吕 →(损) 夷则 →(益) 夹钟 →(损) 无射 →(益) 中吕 →(损) 清黄钟
# 注意：损益并非简单奇偶交替——「蕤宾→大吕」是连续第二次「益一」（×4/3），
# 这正是三分损益「不谐」的来源之一，故用显式操作序列表而非奇偶推断。
LVLV_SEQUENCE = [
    ("黄钟", "阳律"), ("林钟", "阴吕"), ("太簇", "阳律"), ("南吕", "阴吕"),
    ("姑冼", "阳律"), ("应钟", "阴吕"), ("蕤宾", "阳律"), ("大吕", "阴吕"),
    ("夷则", "阳律"), ("夹钟", "阴吕"), ("无射", "阳律"), ("中吕", "阴吕"),
    ("清黄钟", "—"),
]

# 从上一律到本律所用的操作（12 个操作对应 13 个律）：损=×2/3，益=×4/3
LVLV_OPS = ["损", "益", "损", "益", "损", "益", "益", "损", "益", "损", "益", "损"]

# 与十二平均律对照的半音阶位置（0=黄钟，折回一个八度内）
ET_DEGREE = {
    "黄钟": 0, "大吕": 1, "太簇": 2, "夹钟": 3, "姑冼": 4, "中吕": 5,
    "蕤宾": 6, "林钟": 7, "夷则": 8, "南吕": 9, "无射": 10, "应钟": 11,
}


def sanfen_sunyi(base_freq: float = 261.6256) -> list:
    """三分损益生成十二律（默认基准 261.6256 Hz = C4，仅为换算基准）。

    返回 list[dict]：律名/阴阳/管长（基数 81）/ 损益步骤/ 频率比（折回八度内）/
    频率（Hz）/ 相对十二平均律的音分偏差。清黄钟不能还原（comma）在 note 标注。
    """
    base = float(base_freq)
    if base <= 0:
        raise ValueError("基准频率必须为正数（Hz）")
    out: list = []
    length = 81.0
    for i, (name, yy) in enumerate(LVLV_SEQUENCE):
        ratio_raw = 81.0 / length          # 频率比（未折八度）
        folded = ratio_raw
        while folded >= 2.0:
            folded /= 2.0
        while folded < 1.0:
            folded *= 2.0
        freq = base * folded
        entry = {
            "lvlv": name, "yin_yang": yy,
            "length": round(length, 4),
            "freq_ratio": round(folded, 9),
            "freq_hz": round(freq, 4),
        }
        if i > 0:
            op = LVLV_OPS[i - 1]
            entry["step"] = "三分损一（×2/3）" if op == "损" else "三分益一（×4/3）"
        else:
            entry["step"] = "基准音（81）"
        if name in ET_DEGREE:
            et = base * (2.0 ** (ET_DEGREE[name] / 12.0))
            entry["et_hz"] = round(et, 4)
            entry["cents_vs_et"] = round(1200.0 * math.log2(folded / (et / base)), 2)
        if name == "清黄钟":
            entry["note"] = "管长 39.9549 ≠ 81 之半 40.5：黄钟不能还原（三分损益 comma）"
        out.append(entry)
        # 下一步操作按显式序列表推进（最后一律不再推进）
        if i < len(LVLV_OPS):
            length = length * (2.0 / 3.0) if LVLV_OPS[i] == "损" else length * (4.0 / 3.0)
    return out


# --------------------------------------------------------------------------- #
# 只读探针（只枚举设备存在性与驱动状态，绝不播放/调音量/采集声音内容）            #
# --------------------------------------------------------------------------- #

def _run(cmd: list, timeout: float = 6.0) -> tuple:
    """跑一个只读命令，返回 (ok, stdout或错误串)。绝不在此放任何写命令。"""
    if not shutil.which(cmd[0]):
        return False, f"未找到命令 {cmd[0]}"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ, "LC_ALL": "C"})
    except (OSError, subprocess.TimeoutExpired) as e:  # noqa: BLE001
        return False, f"{cmd[0]} 执行失败: {e}"
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        return False, f"{cmd[0]} 返回码 {r.returncode}"
    return True, out


def probe_alsa() -> tuple:
    """只读枚举 ALSA 声卡（/proc/asound/cards + aplay/arecord -l 清单）。

    绝不播放（无 aplay <file> 路径）；无 ALSA 的环境（容器/纯 PipeWire）优雅降级。
    """
    cards = []
    try:
        with open("/proc/asound/cards", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    cards.append(" ".join(parts[1:]))
    except OSError:
        pass
    lines = []
    for tool, label in (("aplay", "播放设备"), ("arecord", "录音设备")):
        ok, out = _run([tool, "-l"])
        if ok and out:
            lines.append(f"{label}（{tool} -l）：")
            lines.extend("   " + ln for ln in out.splitlines())
        elif ok:
            lines.append(f"{label}（{tool} -l）：无设备清单")
        else:
            lines.append(f"{label}（{tool} -l）：{out}")
    if not cards and not lines:
        return False, "无 /proc/asound（非 Linux 或容器隔离）"
    return True, {"cards": cards, "devices": lines}


def probe_pulseaudio() -> tuple:
    """只读 PulseAudio/PipeWire 服务器信息（pactl info）。绝不调音量。"""
    ok, out = _run(["pactl", "info"])
    if not ok:
        return False, out
    info = {}
    for ln in out.splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            info[k.strip()] = v.strip()
    keep = {k: v for k, v in info.items()
            if k in ("Server Name", "Server Version", "Default Sink", "Default Source")}
    return True, keep or info


def probe_audio_tools() -> tuple:
    """只读探测本机音频命令行工具存在性（aplay/arecord/pactl/pipewire）。"""
    tools = ["aplay", "arecord", "pactl", "pipewire", "pw-cli", "amixer"]
    present = {t: bool(shutil.which(t)) for t in tools}
    found = [t for t, ok in present.items() if ok]
    return bool(found), {"present": present, "found": found}


PROBES = (
    ("probe_audio_tools", "音频命令行工具面（aplay/arecord/pactl/pipewire，只读存在性）"),
    ("probe_alsa", "ALSA 声卡与设备清单（/proc/asound + aplay/arecord -l，不播放）"),
    ("probe_pulseaudio", "PulseAudio/PipeWire 服务器信息（pactl info，不调音量）"),
)


def acoustics_devices_report() -> list:
    """返回本机音频设备只读概览（✓ 可用 / ✗ 降级）。"""
    lines = ["声学与音律 · 本机音频设备只读面："]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


def devices_report() -> tuple:
    """本机音频设备只读盘点（(ok, msg) 包装，供任务/runner 调用）。"""
    lines = ["-- 本机音频设备只读面（ALSA/PulseAudio 枚举，绝不播放/调音量/采集内容）--"]
    for fn_name, label in PROBES:
        ok, msg = globals()[fn_name]()
        mark = "✓" if ok else "✗"
        lines.append(f"   {mark} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return True, "\n".join(lines)


def lvlv_report() -> tuple:
    """三分损益十二律生成报告（(ok, msg) 包装）。"""
    lines = ["-- 三分损益十二律（基准 C4 = 261.6256 Hz，仅换算基准；管长基数 81）--"]
    lines.append("   " + "律名   阴阳   管长      频率(Hz)   偏离平均律")
    for e in sanfen_sunyi():
        cents = e.get("cents_vs_et")
        ctxt = f"{cents:+.2f} 音分" if cents is not None else "—"
        lines.append(f"   {e['lvlv']:<4}  {e['yin_yang']}  {e['length']:<8}  "
                     f"{e['freq_hz']:<9.2f}  {ctxt}")
    lines.append("   注：自林钟起每律约 +1.96 音分（comma÷12）；清黄钟管长 39.9549 ≠ 40.5，"
                 "即「黄钟不能还原」——三分损益的固有局限，朱载堉以十二平均律终结之。")
    return True, "\n".join(lines)


def conversion_report() -> tuple:
    """波动几何换算报告（(ok, msg) 包装：声波波长 + 电磁波长/天线）。"""
    lines = ["-- 波动几何换算（c = f·λ；空气 331.3+0.606·T，20 °C 时 343 m/s）--"]
    for label, f in (("声波 100 Hz", 100.0), ("声波 1 kHz", 1000.0),
                     ("声波 10 kHz", 10000.0)):
        lines.append(f"   · {label:<12} λ = {wavelength(f):.3f} m")
    for label, f in (("ISM 433.92 MHz", 433.92e6), ("ISM 2.45 GHz", 2.45e9),
                     ("ISM 5.8 GHz", 5.8e9)):
        lines.append(f"   · {label:<14} λ = {em_wavelength(f)*100:.2f} cm，"
                     f"λ/4 天线 ≈ {antenna_length(f)*1000:.1f} mm")
    lines.append("   应用：喇叭低频重放需振膜尺寸与波长匹配（大口径低音）；无线天线按 λ/4 设计"
                 "（低频天线大、高频天线小）——同一波动几何的两侧。")
    return True, "\n".join(lines)


def acoustics_doc_list() -> list:
    """返回声学主题文档参考清单（供 CLI/GUI 展示），逐条回链知识库。"""
    lines = []
    for key, ref in REFS.items():
        lines.append(f"· {key} — {ref.get('name', '')}")
        lines.append(f"    机构/标准: {ref.get('org', '')}")
        lines.append(f"    文档: {ref.get('url', '')}")
    return lines


def conversion_examples() -> list:
    """四轴联动的工程换算示例（波动几何公共底座）。"""
    lines = []
    for label, f in (("低频 100 Hz（空气中）", 100.0), ("人声 1 kHz（空气中）", 1000.0),
                     ("高频 10 kHz（空气中）", 10000.0)):
        lines.append(f"   · {label}: λ = {wavelength(f):.3f} m（20 °C）")
    for label, f in (("ISM 433.92 MHz", 433.92e6), ("ISM 2.45 GHz", 2.45e9),
                     ("ISM 5.8 GHz", 5.8e9)):
        lines.append(f"   · {label}: λ = {em_wavelength(f)*100:.2f} cm，"
                     f"λ/4 天线 ≈ {antenna_length(f)*1000:.1f} mm")
    return lines


def hearing_protection_guide() -> tuple:
    """听力保护指引（EN 50332 限值参照；不测实际声压，只做行为提醒）。"""
    lim = REFS.get("audio_hardware", {}).get("en50332_limits", {})
    msg = (
        "听力保护指引（EN 50332 / IEC 60268 口径，本工具无校准传声器、不测实际声压）：\n"
        f"  1) 欧盟强制：便携播放器+耳机整机最大声压 ≤ {lim.get('whole_system_max_spl_db', 100)} dB"
        f"（{lim.get('averaging', '5 次平均')}）；\n"
        f"  2) 播放器最大输出电压 ≤ {lim.get('player_max_output_voltage_mv', 150)} mV"
        f"（{lim.get('load_ohm', 32)} Ω 负载）；耳机宽带特性电压 WBCV ≥ "
        f"{lim.get('headphone_wbcv_min_mv', 75)} mV；\n"
        "  3) 分贝是对数量：音量每 +3 dB 声能翻倍；长时间连续聆听建议不超过 85 dB"
        "（8 小时等效暴露口径，needs_verify）；\n"
        "  4) 本工具不播放测试音、不调音量、不采集声音内容——音量与时长始终由用户控制。"
    )
    return True, msg


def acoustics_report() -> tuple:
    """端到端声学与音律报告（只读设备面 + 工程换算 + 音律生成 + 知识库引用）。"""
    lines: list = []
    lines.append("==== 声学与音律（只读 + 知识库驱动，绝不发声/调音量/采集声音） ====")
    lines.append("")
    lines.append("-- 本机音频设备（只读枚举，ALSA/PulseAudio 能力面）--")
    lines.extend(acoustics_devices_report()[1:])
    lines.append("")
    lines.append("-- 波动几何换算（c = f·λ；空气中 331.3+0.606·T，20 °C 时 343 m/s）--")
    lines.extend(conversion_examples())
    lines.append("")
    lines.append("-- 三分损益十二律（基准 C4 = 261.6256 Hz，仅换算基准）--")
    for e in sanfen_sunyi():
        tail = f"；{e['note']}" if e.get("note") else ""
        cents = e.get("cents_vs_et")
        ctxt = f"，偏离平均律 {cents:+.2f} 音分" if cents is not None else ""
        lines.append(f"   · {e['lvlv']:<4}（{e['yin_yang']}）管长 {e['length']:<8} "
                     f"频率 {e['freq_hz']:.2f} Hz{ctxt}{tail}")
    lines.append("")
    lines.append("-- 知识库引用（data/acoustics_docs.json：声学基础/中国音律/无线电磁/音频硬件）--")
    lines.extend(acoustics_doc_list())
    lines.append("")
    lines.append("-- 听力保护参照（EN 50332 限值）--")
    lines.append("   " + hearing_protection_guide()[1].replace("\n", "\n   "))
    lines.append("")
    lines.append("安全不变量：本子系统只读设备存在性、只做数学换算——绝不播放任何声音、"
                 "绝不调音量、绝不采集麦克风内容、无任何射频发射路径。")
    return True, "\n".join(lines)
