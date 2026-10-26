"""声学与音律任务（platform=any，跨平台）。

用户线索：「声音、频率、振动、音调、声率、黄钟大吕……最可能应用在无线技术、
电磁波，还有就是喇叭或耳机」。四轴落法：

1. 声学基础（IEC 61672-1）→ 频率/波长/声速/共振/分贝的工程换算器；
2. 中国音律（黄钟大吕·三分损益）→ 十二律生成器 + 音分偏差对账；
3. 无线电磁（ITU RR·ISM）→ 频段/波长/天线尺寸参照（只读，绝不发射）；
4. 音频硬件（IEC 60268·EN 50332）→ 喇叭/耳机标准限值与听力保护参照。

全部只读：不播放声音、不调音量、不采集麦克风内容、无射频发射路径。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="acoustics_report",
        platform="any",
        title="声学与音律总报告（只读：设备面 + 换算 + 音律 + 知识库）",
        category="maintenance",
        risk="low",
        desc="端到端声学报告：本机音频设备只读枚举（ALSA/PulseAudio）、波动几何换算"
             "（c=f·λ）、三分损益十二律生成、四轴知识库引用与 EN 50332 听力保护参照。",
        actions=[
            N("acoustics.acoustics_report", "端到端生成声学与音律报告（只读+知识库驱动）"),
        ],
        notes=["本子系统绝不播放任何声音、绝不调音量、绝不采集麦克风内容、无任何射频发射路径。"],
        standards=["[国际] IEC 61672-1（声级计·频率计权 A/C/Z）",
                  "[国际] IEC 60268 系列（音响系统设备）",
                  "[国际] EN 50332-1/-2（耳机声压与输出电压限值）"],
    ),
    Task(
        id="acoustics_devices",
        platform="any",
        title="本机音频设备只读盘点（ALSA/PulseAudio 能力面）",
        category="maintenance",
        risk="low",
        desc="枚举本机声卡与音频设备（/proc/asound、aplay/arecord -l、pactl info），"
             "只看设备与驱动状态，为喇叭/耳机选型与故障定位提供能力面。",
        actions=[
            N("acoustics.devices_report", "输出音频设备只读盘点（枚举存在性，不播放/不调音量）"),
        ],
        notes=["容器或纯 PipeWire 环境可能无 ALSA 设备清单，优雅降级不伪造。",
               "设备型号与驱动版本仅用于兼容性判断，绝不采集任何声音内容。"],
        standards=["[国际] ALSA（Advanced Linux Sound Architecture）内核接口",
                  "PulseAudio / PipeWire 服务器协议（能力面只读）"],
    ),
    Task(
        id="acoustics_pitch_lvlv",
        platform="any",
        title="黄钟大吕·三分损益十二律生成与音分对账",
        category="maintenance",
        risk="low",
        desc="以黄钟管长 81 为基数，按三分损益（损一 ×2/3、益一 ×4/3，注意蕤宾→大吕"
             "连续两次益一）生成十二律，输出各律管长、频率与相对十二平均律的音分偏差，"
             "并展示「清黄钟不能还原」（comma）与朱载堉新法密率的解法。",
        actions=[
            N("acoustics.lvlv_report", "输出三分损益十二律表（管长/频率/音分偏差）"),
            M("基准频率默认 C4 = 261.6256 Hz（仅换算基准）；黄钟绝对音高各代不同"
              "（1909 年对照表作 D、明代作 A、朱载堉一说约 650 Hz，均 needs_verify），"
              "本工具不代史学期刊下结论。",
              "黄钟绝对音高的诚实边界说明"),
        ],
        notes=["三分损益与古希腊五度相生律数学同源（2:3 比）；音分偏差自林钟起每律约 +1.96。",
               "六阳律：黄钟·太簇·姑洗·蕤宾·夷则·无射；六阴吕：大吕·夹钟·中吕·林钟·南吕·应钟。"],
        standards=["[典籍] 《吕氏春秋·古乐》（伶伦制律）",
                  "[典籍] 《淮南子·天文训》（十二律配十二月）",
                  "[典籍] 朱载堉《律历融通》（新法密率=十二平均律）"],
    ),
    Task(
        id="acoustics_wireless_reference",
        platform="any",
        title="ISM 频段与频率-波长-天线尺寸参照（只读，绝不发射）",
        category="network",
        risk="low",
        desc="ITU 无线电规则 ISM 频段表（RR 5.138/5.150/5.280）与中国微功率设备管理口径"
             "（工信部 2019 年第 52 号公告），并给出 433.92 MHz / 2.45 GHz / 5.8 GHz 的"
             "波长与 λ/4 天线尺寸换算——喇叭选型与无线天线共通的波动几何底座。",
        actions=[
            N("acoustics.conversion_report", "输出频率↔波长↔天线尺寸工程换算"),
            M("ISM 频段内使用微功率设备：不得对合法台站产生有害干扰、不得提出免受干扰保护，"
              "还须承受 ISM 设备的射频能量干扰；不得擅自扩频段/加功放/改天线"
              "（工信部 2019 年第 52 号公告）。",
              "中国微功率短距离设备使用红线（规范指引）"),
        ],
        notes=["本工具无任何射频发射路径：不改网卡功率/信道/监管域，不发任何无线信号。",
               "2.4 GHz 全球通用故最拥挤；5.8 GHz 带宽宽但绕射弱；433 MHz 绕射强但速率低。"],
        caveats=["涉及无线电发射设备的功率/频点合规以工信部公告原文为准；第三方检测机构解读"
                 "（如 2.4 GHz EIRP≤10 dBm）标 needs_verify。"],
        standards=["[国际] ITU Radio Regulations Article 5（脚注 5.138/5.150/5.280）",
                  "[国家] 工信部公告 2019 年第 52 号（微功率短距离无线电发射设备目录和技术要求）",
                  "[国家] 《中华人民共和国无线电管理条例》（2016 修订）"],
    ),
]
