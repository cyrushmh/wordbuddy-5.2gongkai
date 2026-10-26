"""无线电技术与标准任务（v0.6.75 新建）。

把无线电射频/链路/SDR 工具链/法规口径作为**只读诊断**能力登记，并嵌入整体系统
（关联 link_protocols / meshnet / openwrt / recert / comp 位宽轴）。
全部 platform="any" / category="network" / risk="low"；只读引用，绝不驱动任何真实发射。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="radio_rf_capability",
        platform="any",
        title="本机射频与无线接口只读盘点（rfkill/iw/蓝牙/总线）",
        category="network",
        risk="low",
        standards=[
            "[法规] 《无线电管理条例》（国务院·中央军委令第672号，2016修订）",
            "[法规] 《无线电频率划分规定》（工信部令第62号，2023施行）",
            "[法规] ITU《无线电规则》（2020年版）+ 第三区频率口径",
        ],
        desc="只读盘点本机射频面：rfkill 开关态、iw phy 无线物理能力（Wiphy/频段/"
             "信道）、regdom 监管域、蓝牙控制器、PCI/USB 总线射频器件；"
             "顺带核对中国 ISM 频段与 6GHz IMT 划分口径。不改任何射频参数。",
        actions=[N("radio.rf_switch_report", "看 rfkill 射频开关态（软/硬阻塞）"),
                 N("radio.wifi_phys_report", "看 Wi-Fi 物理能力与 regdom（只读）"),
                 N("radio.bluetooth_report", "看蓝牙控制器（只 show 不扫描）"),
                 N("radio.rf_devices_report", "看总线射频器件枚举（lsusb/lspci 过滤）")],
        notes=[
            "regdom 决定 2.4/5GHz 信道与发射功率合法上限；6GHz（6425-7125MHz）已划归 IMT（5G/6G）。",
            "中国 ISM 常规可用：13553-13567kHz/26957-27283kHz/40.66-40.7MHz/2400-2500MHz/5725-5875MHz/24-24.25GHz。",
            "433.05-434.79MHz 与 902-928MHz 是国外 ISM 频段；第三区（含中国）100MHz-1GHz 无 ISM 专用划分。",
            "与 link_protocols（ble/802.15.4）同族：链路知识维度见彼库，本任务看本机物理面。",
        ],
        caveats=["绝不驱动发射：不改 regdom/信道/txpower、不开 monitor 注入、不扫描不配对；"
                 "开关射频属用户场景操作，本工具不代切换。"],
    ),
    Task(
        id="radio_sdr_toolchain",
        platform="any",
        title="SDR 与无线工具链存在性盘点（GNU Radio/rtl-sdr/Hamlib 等，不启动）",
        category="network",
        risk="low",
        standards=[
            "[开源] GNU Radio（GPL-3.0；3.10.10 稳态 / 4.0 线社区维护，MIT 核心）",
            "[开源] rtl-sdr（osmocom，RTL2832U 电视棒宽带前端）",
            "[开源] Hamlib（LGPL-2.1 库 + GPL 工具；WSJT-X/FLRig/Gpredict 依赖）",
            "[开源] SoapySDR（设备抽象层）",
        ],
        desc="只 which 盘点 SDR/无线工具链：GNU Radio、rtl-sdr、SoapySDR、Hamlib/"
             "rigctl、gqrx、multimon-ng、direwolf、kismet、aircrack-ng、Wireshark 等；"
             "给出组合读法（如『有流图无前端』）。绝不启动任何接收/发射流程。",
        actions=[N("radio.sdr_toolchain_report",
                   "列 SDR/无线工具链存在性矩阵（只 which 不启动）")],
        notes=[
            "SDR 把模拟前端数字化后的信号处理搬到 CPU：IQ 样本流经工具链流转（rtl_sdr | 解调器）。",
            "『能解调就能伪造』边界：本工具只盘点存在性，操作合规性由用户在法规框架内自行负责。",
            "射频 MCU（AVR/ESP32/STM32WL）是位宽世代里最小几档的算力底座——与 comp 第七轴互参。",
        ],
        caveats=["只盘点存在性：绝不启动任何 SDR/电台/抓包/破解工具；attack 类工具仅登记存在，"
                 "破解未授权网络、私设电台违反《无线电管理条例》。"],
    ),
    Task(
        id="radio_regulation_check",
        platform="any",
        title="无线电法规与频段合规口径核对（型号核准/微功率/ISM/业余/无线充电）",
        category="network",
        risk="low",
        standards=[
            "[法规] 型号核准（SRRC/CMIIT ID，国家无线电办公室，miit.gov.cn）",
            "[法规] 工信部公告2019年第52号《微功率短距离无线电发射设备目录和技术要求》",
            "[法规] 《业余无线电台管理办法》（工信部令第67号，2024-03-01 施行）",
            "[法规] 《无线充电（电力传输）设备无线电管理暂行规定》（2024-09-01 实施）",
        ],
        desc="核对无线电合规五条线：型号核准（有发射原则要核准）/ 微功率目录（免核准仍受限值）/"
             " ISM 频段（中国口径与 433·915 国外口径之别）/ 业余电台执照·呼号与 A·B·C 类"
             "操作验证（功率分档 25W/15W/1000W）/ 无线充电专项频率与功率限值。",
        actions=[N("radio.regulation_report",
                   "列法规与频段口径（官方源登记 + 合规路径）")],
        notes=[
            "A 类 30-3000MHz ≤25W；B 类 30MHz 以下 <15W / 以上 ≤25W；C 类 30MHz 以下 ≤1000W / 以上 ≤25W。",
            "业余业务限于相互通信/技术研究/自我训练，不得谋取商业利益；应急处置经批准可超限值并申领临时呼号。",
            "无线充电器免核准但限频限功率（移动便携 ≤80W）、须标专用标识；含 Wi-Fi/蓝牙的信息传输单元仍走型号核准。",
            "WCET（IEEE 无线通信认证）续证 PDU 规则见 data/recert_docs.json；认证项目本身 2019 年已停办。",
        ],
        caveats=["只核对口径，不代办任何许可：频率使用许可/台站执照/型号核准均须向无线电管理机构申请；"
                 "具体产品合规以当期官方公告与核准目录为准。"],
    ),
]
