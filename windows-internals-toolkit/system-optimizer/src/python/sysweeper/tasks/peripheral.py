"""外部设备连接与兼容任务（platform=any，跨平台）。

全部只读探针 + 标准/官方指引；任何「刷星闪/USB 固件/装私有外设驱动/改写 PD 协商」
的高危动作一律只给规范指引，不代执行——严守本项目只读红线，也契合用户
「个人行为在完全图形界面控制操作」：工具出标准引入与方案，用户在图形界面或厂商工具确认。

引擎（introduce_nearlink / assess_touch_compat / assess_external_compat /
peripheral_report）是纯函数，由 peripheral_report 串联；GUI 可让用户勾选设备标签后
即时看到兼容报告。本子系统与「供电与环境安全（electrical）」「设备长期使用保护
（durability）」并列，共同支撑「外部设备连接与设备长期保障运行」。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="peripheral_report",
        platform="any",
        title="外部设备连接与兼容评估（只读 + 标准引入）",
        category="maintenance",
        risk="low",
        desc="整体引入星闪(NearLink)标准，并据设备标签（触控/USB-C PD/HID/星闪）只读识别触控"
             "设备与多点触控协议、USB 版本与 PD 能力、HID 即插即用状态，给兼容与选型建议；"
             "每条回链知识库。",
        actions=[
            N("peripheral.peripheral_report", "端到端生成外部设备连接与兼容报告（星闪引入→触控→USB-C PD/HID）"),
        ],
        notes=["软件只读能力面：不刷固件、不装私有驱动、不挂钩输入流、不改写 PD 协商。"],
        standards=["[国标] 工信部行业标准（星闪进入行业标准制定路径，std.samr.gov.cn 检索）",
                  "[国际] USB-IF USB4 / USB PD 3.1（usb.org）",
                  "[地区] IEC 62680（欧盟 USB-C 强制充电接口标准）",
                  "[国际] Linux kernel input multitouch protocol / USB-IF HID"],
    ),
    Task(
        id="peripheral_nearlink_guidance",
        platform="any",
        title="按星闪(NearLink)选型无线外设（规范指引）",
        category="maintenance",
        risk="low",
        desc="把星闪作为外部设备连接与兼容的推荐国产短距无线标准整体引入：无线鼠标/键盘/"
             "手写笔/耳机优先按星闪选型，微秒时延+一拖上千并发，接入须配对与身份校验。",
        actions=[
            M("在设备管理器/系统信息确认外设标注 SparkLink/NearLink 即视为已支持；鼠标/键盘/"
              "手写笔/耳机优先选星闪版；首次使用完成配对与身份校验，并与 BLE/Wi-Fi 做 2.4G 共存调度。",
              "按星闪选型与接入无线外设（规范指引，不代执行）"),
            N("peripheral.guide_nearlink_adopt", "输出星闪选型接入指引（只给步骤，不刷固件）"),
        ],
        notes=["星闪经 SoC/复合 dongle 接入，软件只能力面识别，不探测私有固件。"],
        caveats=["星闪固件写入/刷写属不可逆高风险，本工具绝不执行；由用户在厂商工具确认。"],
        standards=["[国标] 星闪联盟团体标准 T/SL 系列（通信/接入/基础/测试）",
                  "[国际] 蓝牙 SIG（BLE）/ Wi-Fi Alliance（IEEE 802.11，对标参考）"],
    ),
    Task(
        id="peripheral_touch_guidance",
        platform="any",
        title="触控设备驱动与兼容（规范指引）",
        category="maintenance",
        risk="low",
        desc="只读识别触控屏/精确触控板与多点触控协议（MT-A/MT-B）；缺 hid-multitouch/I2C-HID "
             "即给官方指引，绝不采集按键/触控内容。",
        actions=[
            M("Linux 确认内核加载 hid-multitouch 与 I2C-HID（触控板/屏常见传输），缺失即装对应模块；"
              "Windows 选用 Precision Touchpad 认证触控板；触控屏/笔优先选主动笔+星闪 SLE 低时延通道。",
              "补全触控驱动获得多点跟手（规范指引，不代执行）"),
            N("peripheral.guide_touch_driver", "输出触控驱动兼容指引（只给步骤，不装私有驱动）"),
        ],
        notes=["本工具只读识别触控设备与协议类型，绝不挂钩输入流（契合键盘/输入内容刻意不采集的红线）。"],
        standards=["[国际] Linux kernel Documentation/input/multi-touch-protocol.rst（MT-A/MT-B）",
                  "[国际] USB-IF HID / 微软 Precision Touchpad 规范"],
    ),
    Task(
        id="peripheral_usb_c_pd_guidance",
        platform="any",
        title="USB-C/USB4 与 PD 供电兼容（规范指引）",
        category="maintenance",
        risk="low",
        desc="只读识别 USB 版本（2.0/3.2/4）与 PD 能力（是否 EPR/双向）；提示带 e-Marker 线缆才"
             "支持 100W/视频，标注欧盟 IEC 62680 强制 USB-C；绝不改写 PD 协商、不刷接口固件。",
        actions=[
            M("高功率/视频须用带 e-Marker 的 USB-C 线缆（否则仅充电/降速）；确认端口与线缆支持目标"
              "Alt Mode（DP/Thunderbolt/星闪）；PD 3.1 EPR 最高 240W，注意欧盟 IEC 62680 强制 USB-C。",
              "USB-C/USB4 与 PD 供电兼容选型（规范指引，不代执行）"),
            N("peripheral.guide_usb_c_pd", "输出 USB-C/PD 兼容选型指引（只给步骤，不改 PD 协商）"),
        ],
        notes=["PD 由端口与设备经 CC 线私有协商，软件只能读已协商结果，不能改写功率档。"],
        standards=["[国际] USB-IF USB4（基于 Thunderbolt 3，40Gbps）/ USB PD 3.1（100W/240W EPR）",
                  "[地区] IEC 62680（欧盟 USB-C 强制充电接口标准）",
                  "[国际] USB BC 1.2（Battery Charging，传统充电端口）"],
    ),
]
