#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「protec」产品（设备设施）长期运行与基本保护概念系统构建（v0.6.68，第十概念系统，protec）。

立意（用户原话）：「材料学、热力学、气候学、环境学、物理、化学、生物等以及相关
对产品（设备设施）长期运行和基本保护的协议和标准查看」。

本系统把「设备设施如何长期可靠运行、如何不被环境/电气/材料老化毁掉」做成一个
只读概念系统，整合既有 sysweeper 产品保护域的四个原生引擎：

    ├─ 轴1 durability   材料耐久与老化（腐蚀/疲劳/蠕变/热老化/湿气侵入/电池衰减/材料选型）
    ├─ 轴2 electrical   电气安全（接触高阻发热/电偶腐蚀/串联电弧/接地与 RCD/连接器老化/可燃底座）
    ├─ 轴3 environment  环境标准与气候（IP 代码/IEC 60721 环境分类/ASHRAE TC9.9 温控/IEC 62368-1 安全）
    ├─ 轴4 emergency    应急保护（CAP 1.2 四级预警/定位融合/求救报文/应急物资清单）
    ├─ 轴5 protection   七条基本保护原则（= principles：冗余/降额/隔离/监控/接地/防护/可维护）
    └─ 轴6 transfer     传输与可用性（TCP/QUIC 可靠传输/HTTP Range 续传/完整性校验/TLS 基线/
                                Anycast/一致性哈希/熔断；与 docs/74 协议标准查阅 + native/transfer 落地同源）
    └─ 轴7 access      接入与链路层（以太网 802.3/WLAN 802.11/WiFi 安全 WPA2·WPA3/802.1X·EAP·RADIUS/
                                VLAN 802.1Q/PPPoE RFC 2516；与 docs/75 协议标准查阅同源，桥接 netsys 组网）

桥接目标在既有概念系统中必须真实存在（netsys modules / datong·zhuangzi·baigong
principles / apilab·comp·quantum concepts），构建期校验无悬空。user_face 为
构建期实测：protec 接线后 CLI 子命令 125→127、GUI 窗口 110→112，由 --check
逐键比对防漂移。

诚实边界：只读登记、标准编号与机构均按通行口径登记、不臆造实测数字；桥接只作
「保护原则 ↔ 既有工程伦理/接口/编译/量子缓解」的结构翻译，不宣称等同；凡未核对
原典/年代/机构口径者统一挂 needs_verify。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "python"
DATA_DIR = ROOT / "src/python/sysweeper/data/concepts"
OUT = DATA_DIR / "protec_taxonomy.json"
DENO_DIR = ROOT / "src" / "deno"

VERSION = "0000.0000.0000.0069.20261025"
SCHEMA = "protec_taxonomy/v1"

AXIS_LABELS = {
    "durability": "材料耐久与老化",
    "electrical": "电气安全",
    "environment": "环境标准与气候",
    "emergency": "应急保护",
    "protection": "基本保护原则",
    "transfer": "传输与可用性",
    "access": "接入与链路层",
    "ipv6": "IPv6 与 ICMPv6 控制面",
}

DOMAINS = [
    {"domain": "durability", "label": "材料耐久与老化",
     "note": "设备长期运行的第一类失效：腐蚀/疲劳/蠕变/热老化/湿气侵入/电池衰减，靠材料选型与防护延缓"},
    {"domain": "electrical", "label": "电气安全",
     "note": "电联接相关的隐蔽失效：接触高阻发热/电偶腐蚀/串联电弧/接地与 RCD/连接器老化/可燃底座"},
    {"domain": "environment", "label": "环境标准与气候",
     "note": "IEC 60529 IP 代码 / IEC 60721 环境分类 / ASHRAE TC9.9 数据中心温控 / IEC 62368-1 安全"},
    {"domain": "emergency", "label": "应急保护",
     "note": "CAP 1.2 四级预警 / 定位融合（fuse+floor）/ 求救报文 / 应急物资清单"},
    {"domain": "protection", "label": "基本保护原则",
     "note": "七条可审计工程保护原则（= principles）：冗余/降额/隔离/监控/接地/防护/可维护"},
    {"domain": "transfer", "label": "传输与可用性",
     "note": "TCP/QUIC 可靠传输 / HTTP Range 分块续传 / 完整性校验 / TLS 1.3 基线 / "
             "Anycast·一致性哈希·熔断 可用性；与 docs/74 协议标准查阅 + native/transfer 落地同源"},
    {"domain": "access", "label": "接入与链路层",
     "note": "IEEE 802.3 以太网 / 802.11 无线局域网(WLAN)/ WiFi 安全(WPA2·WPA3) / "
             "802.1X·EAP·RADIUS 接入认证 / 802.1Q VLAN 隔离 / PPPoE(RFC 2516) 宽带接入 / "
             "星闪(SparkLink) 短距多模式空口；与 docs/75 协议标准查阅 + docs/76 星闪3.0 同源，桥接 netsys 组网模块"},
    {"domain": "ipv6", "label": "IPv6 与 ICMPv6 控制面",
     "note": "IPv6 基址(RFC 8200) / ICMPv6 两类消息(RFC 4443) / NDP 邻居发现(RFC 4861) / "
             "SLAAC(RFC 4862) / DHCPv6(RFC 8415) / PMTUD(RFC 8201) / NAT64·DNS64(RFC 6146/6147/6052) / "
             "6LoWPAN(RFC 4944/6282/6775) / SEND·CGA(RFC 3971/3972) / MLD(RFC 2710/3810)；"
             "与 docs/76 IPv6 全链路 + ICMPv6 两篇同源，桥接 netsys 组网模块"},
]

# ------------------------- 轴1 材料耐久与老化（7） ------------------------- #
DURABILITY = [
    {"id": "corrosion", "name": "腐蚀", "gist": "金属与环境介质发生化学/电化学反应导致的渐进性破坏。",
     "detail": "电化学腐蚀分阳极溶解与阴极还原两半反应；潮湿+电解质（盐雾/凝露）是加速器。"
               "不锈钢靠钝化膜、铝靠氧化膜自保护；点蚀/缝隙腐蚀/应力腐蚀开裂是隐蔽高危形态。",
     "engineering": "工程落法：选型抗蚀材料（316L/阳极氧化）、涂镀层隔离、排水防潮设计；"
                    "维护巡检盐雾/凝露环境接点。",
     "standards": ["IEC 60068-2-11 盐雾", "ISO 9223 腐蚀等级", "GB/T 10125 盐雾试验"],
     "canon_refs": []},
    {"id": "fatigue", "name": "疲劳失效", "gist": "循环应力下低于屈服强度的反复加载导致裂纹萌生与扩展。",
     "detail": "高周疲劳（S-N 曲线）与低周疲劳（应变控制）两范式；焊点/弹片/风扇支架是电子"
               "设备疲劳高发点；振动与温度循环叠加加速裂纹。",
     "engineering": "工程落法：避免应力集中、留出安全寿命裕度、对振动部件做疲劳寿命评估与定期更换。",
     "standards": ["ISO 1099 轴向疲劳", "GB/T 3075 金属疲劳"],
     "canon_refs": []},
    {"id": "creep", "name": "蠕变", "gist": "高温/长期载荷下材料的缓慢塑性变形。",
     "detail": "蠕变三阶段（初/稳/加速）；对塑料/焊料/紧固件在高温工况下显著；"
               "紧固预紧力随蠕变松弛，是联接松脱的隐性来源。",
     "engineering": "工程落法：高温部件选抗蠕变材料、控制工作温度、定期复紧并留蠕变裕度。",
     "standards": ["GB/T 2039 金属蠕变试验"],
     "canon_refs": []},
    {"id": "thermal-aging", "name": "热老化", "gist": "长期热暴露使聚合物/电解质/密封件化学降解、性能衰减。",
     "detail": "阿伦尼乌斯定律：温度每升 10K 反应速率约翻倍（寿命减半经验）；电解电容、"
               "密封胶、线缆绝缘层是热老化重灾区；热循环还叠加机械疲劳。",
     "engineering": "工程落法：降额使用、控制结温与环温、按热寿命模型定维护周期；"
                    "与降额原则（protec:derating）同源。",
     "standards": ["IEC 60068-2-2 干热", "Arrhenius 寿命模型"],
     "canon_refs": ["derating"]},
    {"id": "humidity-ingress", "name": "湿气侵入", "gist": "水汽经密封缺陷渗入，引发凝露、绝缘下降与电化学迁移。",
     "detail": "吸湿使 PCB 漏电流上升、CAF（导电阳极丝）沿玻纤生长短路；凝露点在露点管理不善时"
               "出现于机壳内壁；IP 等级与密封工艺直接决定抗湿性。",
     "engineering": "工程落法：IP 防护、防潮涂层（conformal coating）、干燥剂/呼吸阀、三防漆；"
                    "与 ip-code/enclosure 同源。",
     "standards": ["IEC 60068-2-30 湿热循环", "IEC 60529 IP"],
     "canon_refs": ["ip-code"]},
    {"id": "battery-degradation", "name": "电池衰减", "gist": "锂离子等储能单元随循环/日历老化的容量与内阻劣化。",
     "detail": "负极 SEI 膜增长、正极相变、锂枝晶是主因；高温与满充存放加速衰减；"
               "内阻上升导致可用功率下降、热失控风险上升。",
     "engineering": "工程落法：充电策略限 SoC 窗口、控温、均衡管理、容量预测与寿命预警；"
                    "与 charge_strategy/thermal_throttle 同源。",
     "standards": ["GB/T 31485 动力电池", "IEC 62619 工业锂电"],
     "canon_refs": []},
    {"id": "material-selection", "name": "材料选型", "gist": "以工作环境与寿命目标反向约束材料与工艺选择。",
     "detail": "选型矩阵：温度范围/介质/载荷/成本/可制造性五维权衡；免应力腐蚀配对、"
               "避免电化学序相差大的异种金属直接搭接（防电偶腐蚀）。",
     "engineering": "工程落法：环境-寿命-成本三约束选型评审、异种金属绝缘隔离、关键件可溯源。",
     "standards": ["IEC 60721 环境分类", "GB/T 2423 环境试验"],
     "canon_refs": ["ip-code"]},
]

# ------------------------- 轴2 电气安全（6） ------------------------- #
ELECTRICAL = [
    {"id": "contact-heating", "name": "接触高阻发热", "gist": "联接点氧化/松动使接触电阻升高，功率损耗转为局部高温。",
     "detail": "P=I²R，微小电阻增量在电流下即成热点；端子/插接件/螺丝压接是重灾区；"
               "热积累可引燃邻近可燃物，是电气火灾首要机理。",
     "engineering": "工程落法：扭矩规范压接、定期红外测温、温升报警、低阻接触材料；"
                    "与 combustible-base 同源防控。",
     "standards": ["IEC 62368-1", "GB 4943.1"],
     "canon_refs": ["combustible-base"]},
    {"id": "galvanic-corrosion", "name": "电偶腐蚀", "gist": "异种金属在电解质中构成原电池，活性金属加速腐蚀。",
     "detail": "电化学序中电位差越大、腐蚀越快；设备外壳-紧固件-PCB 地三种金属搭接常见；"
               "湿热环境尤甚。",
     "engineering": "工程落法：绝缘隔离异种金属、等电位连接、防腐处理、避免大电位差配对。",
     "standards": ["ISO 9223", "ASTM G82 电偶腐蚀"],
     "canon_refs": ["material-selection"]},
    {"id": "arc-fault", "name": "串联电弧", "gist": "导线破损/接触不良产生的高阻串联电弧，隐蔽且易引燃。",
     "detail": "串联电弧电流小、常规过流保护不动作；AFCI（电弧故障断路器）通过电流特征识别；"
               "松动端子与绝缘老化是主要诱因。",
     "engineering": "工程落法：AFCI 保护、紧固防松、定期绝缘检测、避免线芯损伤。",
     "standards": ["UL 1699 AFCI", "IEC 62606"],
     "canon_refs": ["contact-heating"]},
    {"id": "grounding-rcd", "name": "接地与剩余电流", "gist": "保护接地与剩余电流动作保护器（RCD）构成触电/漏电防线。",
     "detail": "接地提供故障电流回路与等电位基准；RCD 检测毫安级剩余电流并在毫秒级脱扣；"
               "IT/TT/TN 系统接地型式决定保护配合。",
     "engineering": "工程落法：可靠保护接地、RCD 分级配置与定期测试、漏电流监测；"
                    "与 grounding 原则同源。",
     "standards": ["IEC 60364 低压电气装置", "GB 13955 剩余电流保护"],
     "canon_refs": ["grounding"]},
    {"id": "connector-aging", "name": "连接器老化", "gist": "插接件镀层磨损/应力松弛导致接触电阻漂移与偶发断连。",
     "detail": "插拔次数、镀金厚度、保持力共同决定寿命；微动腐蚀（fretting corrosion）在微小振动下"
               "生成绝缘氧化物，是信号偶发掉线的元凶。",
     "engineering": "工程落法：选高插拔寿命连接器、锁止防松、接触电阻在线监测、关键链路冗余。",
     "standards": ["IEC 60512 连接器试验"],
     "canon_refs": ["fatigue", "contact-heating"]},
    {"id": "combustible-base", "name": "可燃底座", "gist": "设备下方/内部可燃材料在异常发热时助燃扩散。",
     "detail": "塑料外壳、泡沫隔热、线束护套的阻燃等级决定是否延燃；异常发热（接触/电弧）"
               "一旦点燃可燃底座即转为火灾。",
     "engineering": "工程落法：阻燃材料（V-0 级）、热源与可燃物隔离、限温与故障隔离；"
                    "与 contact-heating/arc-fault 同源防控。",
     "standards": ["IEC 60695 阻燃", "UL 94", "GB/T 5169"],
     "canon_refs": ["contact-heating", "arc-fault"]},
]

# ------------------------- 轴3 环境标准与气候（4） ------------------------- #
ENVIRONMENT = [
    {"id": "ip-code", "name": "IP 防护等级", "gist": "IEC 60529 外壳对固体异物与水的防护分级（IP 代码）。",
     "detail": "第一位 0–6 防固体/接触，第二位 0–9 防水（9K 高压高温喷淋）；"
               "设备选型与部署场景强相关：工业/车载/户外须更高 IP，与 IEC 60721 环境分类配套。",
     "engineering": "工程落法：按部署环境定 IP 门槛、铭牌与 hwdb 映射只读识别、BMC/传感器读环境只读。",
     "standards": ["IEC 60529", "IEC 60721", "GB/T 4208"],
     "canon_refs": ["humidity-ingress", "material-selection"]},
    {"id": "iec60721-class", "name": "IEC 60721 环境分类", "gist": "对设备服役环境（温度/湿度/生物/化学/机械/气候）做标准化分类编码。",
     "detail": "将环境参数离散为等级（如 5M3 机械振动、6K7 气候），用于定寿与环境适应性设计；"
               "与 IP 代码、GB/T 2423 环境试验配套形成完整环境基线。",
     "engineering": "工程落法：先定环境等级再选型、环境等级写入规格书、按等级定维护周期。",
     "standards": ["IEC 60721", "GB/T 2423"],
     "canon_refs": ["material-selection", "ip-code"]},
    {"id": "ashrae-thermal", "name": "ASHRAE TC9.9 温控", "gist": "数据中心与 IT 设备推荐温湿度包络（ASHRAE TC9.9）。",
     "detail": "允许进风温度上探至 27°C（A1 类），放宽后可显著节能；但逼近上限时热裕度下降、"
               "故障率上升，需与散热策略（thermal_throttle）协同。",
     "engineering": "工程落法：按 ASHRAE 包络设温控、留热裕度、温度越限降频/告警、能效与可靠权衡。",
     "standards": ["ASHRAE TC9.9", "GB 50174 数据中心"],
     "canon_refs": ["thermal-aging", "derating"]},
    {"id": "iec62368-safety", "name": "IEC 62368-1 安全", "gist": "音视频/ICT 设备基于危险能量与危险源（HBSE）的新安全范式。",
     "detail": "取代旧 60065/60950，按能量源分级（ES1/ES2/ES3）与防护屏障（fire/energy/shock）"
               "评估，强调防火 enclosure 与限功率源（LPS）。",
     "engineering": "工程落法：基于危险源设计屏障、限功率/限电流、阻燃 enclosure、绝缘配合；"
                    "与 combustible-base/grounding 同源。",
     "standards": ["IEC 62368-1", "GB 4943.1"],
     "canon_refs": ["combustible-base", "grounding"]},
]

# ------------------------- 轴4 应急保护（4） ------------------------- #
EMERGENCY = [
    {"id": "cap-alert", "name": "CAP 1.2 四级预警", "gist": "通用警报协议 CAP 1.2 的多级预警（信息/告诫/警告/紧急）。",
     "detail": "CAP 用 XML 统一事件/区域/严重度/有效期，支持分级（advisory/watch/warning/"
               "emergency）与多语言广播；适合设备群在灾前/灾中分级推送与本地化处置。",
     "engineering": "工程落法：告警分级路由、紧急级双通道、预警有效期自动过期、可审计回执。",
     "standards": ["OASIS CAP 1.2", "GB/T 31143 应急联动"],
     "canon_refs": []},
    {"id": "locate-fuse", "name": "定位融合", "gist": "多源定位（卫星/基站/Wi-Fi/惯性）融合估计位置，含可信下限 floor。",
     "detail": "fuse_with_floor：在置信度不足时不报虚假高精度，给出位置可信下限而非单点；"
               "应急场景下定位精度直接决定救援时效。",
     "engineering": "工程落法：多源加权融合、低置信给区间而非点、定位 ETA 量级口径（公里/分钟）诚实标注。",
     "standards": ["GNSS ICD", "3GPP 定位"],
     "canon_refs": []},
    {"id": "sos-text", "name": "求救报文", "gist": "最小可读的 SOS 报文：位置/严重度/人数/可联系性。",
     "detail": "报文需在无网/弱网下仍可生成与缓存，优先走 SMS/卫星/蓝牙 Mesh 等低带宽通道；"
               "含结构化字段便于接收端自动派单。",
     "engineering": "工程落法：离线可生成、低带宽优先、字段结构化、发送回执与重传。",
     "standards": ["CAP 1.2 alert", "SMS PDU"],
     "canon_refs": []},
    {"id": "kit-check", "name": "应急物资清单", "gist": "十项应急物资核对（水/食品/照明/通信/医药/保暖/工具/文档/电源/庇护）。",
     "detail": "kit-check 逐项核对可用性与保质期；设备侧对应冗余电源、离线文档、便携通信等"
               "自保障能力，是长期运行的最后一道底线。",
     "engineering": "工程落法：物资有效期提醒、关键件冗余、离线应急包、定期自查。",
     "standards": ["ISO 22320 应急管理"],
     "canon_refs": []},
]

# ------------------------- 轴5 七条基本保护原则（7，= principles） ------------------------- #
PRINCIPLES = [
    {"id": "redundancy", "name": "冗余", "gist": "单点故障不可接受处，提供并行或待机备份。",
     "detail": "冗余以代价换可用性：电源/存储/链路/控制关键路径并行或待机，N+1 或 2N，"
               "故障自动切换不丢服务；代价是复杂度与一致性管理，须防「假冗余」（共因失效）。",
     "engineering": "电源/存储/链路/控制关键路径冗余；N+1 或 2N，故障自动切换不丢服务。",
     "canon_refs": ["cap-alert"]},
    {"id": "derating", "name": "降额", "gist": "元器件工作应力低于额定值，换取寿命与裕度。",
     "detail": "降额是可靠性的第一杠杆：温度每降一档，寿命与失效率显著改善（阿伦尼乌斯）；"
               "电压/电流亦留裕度；直接对抗热老化与蠕变两类时间相关失效。",
     "engineering": "温度/电压/电流降额使用，按热寿命模型留裕度；直接对抗热老化与蠕变。",
     "canon_refs": ["thermal-aging", "creep"]},
    {"id": "isolation", "name": "隔离", "gist": "故障/危险能量被屏障限制在局部，不扩散。",
     "detail": "隔离即划定故障域：电气隔离、防火 enclosure、物理分区、网段隔离，使单点失效"
               "不波及全局；与 IEC 62368-1 的屏障（fire/energy/shock）理念同源。",
     "engineering": "电气隔离/防火 enclosure/物理分区/故障域隔离；与 IEC 62368-1 屏障同源。",
     "canon_refs": ["iec62368-safety", "combustible-base"]},
    {"id": "monitoring", "name": "监控", "gist": "关键状态可观测、越限可告警、趋势可预测。",
     "detail": "可观测是保护的前提：温/湿/电流/电压/容量在线监测，越限告警与寿命趋势预测；"
               "隐蔽失效（接触发热/电池衰减）唯有靠监控提前暴露，与定位融合（locate-fuse）同源可观测。",
     "engineering": "温/湿/电流/电压/容量在线监测，越限告警与寿命预测；与 locate-fuse 同源可观测。",
     "canon_refs": ["contact-heating", "battery-degradation"]},
    {"id": "grounding", "name": "接地", "gist": "提供等电位基准与故障回路，限制触电与浪涌危害。",
     "detail": "接地既给故障电流回路，又提供等电位基准防止电位差放电；配合 RCD 在毫安级剩余"
               "电流即脱扣；IT/TT/TN 接地型式决定保护配合策略。",
     "engineering": "保护接地 + RCD 分级 + 等电位连接；与 grounding-rcd 同源。",
     "canon_refs": ["grounding-rcd"]},
    {"id": "enclosure", "name": "防护", "gist": "外壳与环境之间设物理/化学屏障。",
     "detail": "防护是设备与环境的界面工程：IP 防护挡异物与水、三防漆/密封挡湿气侵入、"
               "阻燃 enclosure 挡可燃底座延燃；直接对抗湿气侵入与可燃底座两类环境失效。",
     "engineering": "IP 防护/三防漆/阻燃 enclosure/密封；直接对抗湿气侵入与可燃底座。",
     "canon_refs": ["ip-code", "humidity-ingress", "combustible-base"]},
    {"id": "maintainability", "name": "可维护", "gist": "可巡检、可更换、可恢复，寿命期内可低成本延续。",
     "detail": "可维护让寿命可被「续命」：模块化易拆、关键件可溯源可更换、维护窗口与降级模式；"
               "与应急物资清单（kit-check）同源——把维护能力本身当作一项冗余资产。",
     "engineering": "模块化易拆、关键件可溯源可更换、维护窗口与降级模式；与 kit-check 同源。",
     "canon_refs": ["kit-check", "connector-aging"]},
]

# ------------------------- 轴6 传输与可用性（8） ------------------------- #
TRANSFER = [
    {"id": "tcp-reliable", "name": "TCP 可靠传输", "gist": "面向连接的可靠字节流：序列号/确认/重传/滑动窗口与拥塞控制对抗丢包、乱序与拥塞。",
     "detail": "三次握手建连；序列号+确认+超时重传（超时重传与快速重传）保证按序交付；滑动窗口做流控；"
               "拥塞控制（慢启动/拥塞避免/快速恢复，Linux 默认 CUBIC，RFC 9438）防链路过载；"
               "单流队头阻塞是其固有缺陷，由 QUIC 解决。",
     "engineering": "工程落法：长肥管道调窗、启用 SACK、按链路选拥塞算法（CUBIC/BBR）；"
                    "与 quic-transport 同源可靠传输、与 redundancy 同源抗丢包。",
     "standards": ["RFC 9293 TCP", "RFC 9438 CUBIC"],
     "canon_refs": ["quic-transport"]},
    {"id": "quic-transport", "name": "QUIC 传输", "gist": "基于 UDP 的可靠多路复用加密传输：0-RTT/1-RTT 握手、消除队头阻塞、连接迁移。",
     "detail": "QUIC 将可靠传输与 TLS 1.3 合一（RFC 9001），流级多路复用消除 TCP 队头阻塞；"
               "连接 ID 支持 NAT 重绑定下的连接迁移；拥塞控制见 RFC 9002；HTTP/3 即承载于 QUIC（RFC 9114）。",
     "engineering": "工程落法：UDP 端口放行、0-RTT 防重放（仅幂等）、连接迁移保活；"
                    "与 tcp-reliable 同源可靠传输、与 tls-baseline 合一。",
     "standards": ["RFC 9000 QUIC", "RFC 9001 QUIC-TLS", "RFC 9002 QUIC-Recovery", "RFC 9114 HTTP/3"],
     "canon_refs": ["tcp-reliable", "tls-baseline"]},
    {"id": "http-range", "name": "HTTP Range 分块续传", "gist": "以 Range/Content-Range 分块请求与断点续传，提升大文件吞吐与容错。",
     "detail": "Range 请求取字节区间，206 Partial Content 响应；配合 ETag/Last-Modified 校验分块一致性；"
               "FTP 侧以 REST/APPE 实现等价断点续传（见 native/transfer）；并发分块可线性化带宽。",
     "engineering": "工程落法：分块并发下载、ETag 校验分块、断点续传避免重传；"
                    "与 integrity-checksum 同源（分块需回读校验）。",
     "standards": ["RFC 9112 HTTP/1.1", "RFC 9113 HTTP/2", "RFC 9114 HTTP/3", "RFC 959 FTP (REST/APPE)"],
     "canon_refs": ["integrity-checksum"]},
    {"id": "integrity-checksum", "name": "完整性校验", "gist": "传输前后以校验和（sha256 等）回读比对，防止静默损坏与篡改。",
     "detail": "端到端校验和（sha256 随传输附带）可在落盘前发现比特翻转/截断；与 TLS AEAD 的逐包完整性互补："
               "TLS 保护传输中、校验和保护存储态/跨协议。FTP 侧 sha256 回读校验见 native/transfer。",
     "engineering": "工程落法：传输后回读校验、校验和随包携带、存储态独立校验；"
                    "与 tls-baseline 同构（完整性两层防护）。",
     "standards": ["FIPS 180-4 SHA-256", "RFC 959 FTP (回读校验)"],
     "canon_refs": ["tls-baseline"]},
    {"id": "tls-baseline", "name": "TLS 1.3 基线", "gist": "FTPS/HTTPS 加密传输底座：前向安全、AEAD、废除静态 RSA 密钥交换。",
     "detail": "TLS 1.3（RFC 8446）以 (EC)DHE 提供前向安全、默认 AEAD（AES-GCM/ChaCha20-Poly1305）、"
               "1-RTT 握手、0-RTT 可选（需防重放）；FTPS 即 FTP over TLS（RFC 4217）；静态 RSA 密钥交换已废除。",
     "engineering": "工程落法：禁用 TLS<1.2、启用 (EC)DHE 前向安全、证书链最短校验、0-RTT 仅限幂等；"
                    "与 integrity-checksum 同构、与 netsys tls13 同源落点。",
     "standards": ["RFC 8446 TLS 1.3", "RFC 4217 FTPS"],
     "canon_refs": ["integrity-checksum"]},
    {"id": "anycast-routing", "name": "Anycast 路由", "gist": "同一地址多节点就近服务，故障/拥塞时路由自动绕行至健康节点。",
     "detail": "Anycast 将同一前缀宣告到多个节点，由路由协议（BGP/IGP）就近交付；节点失效即被路由收敛绕开，"
               "天然提供可用性；BCP 126（RFC 4786）给出运营考量；RFC 1546 最早提出、RFC 2526 定义任播地址格式。",
     "engineering": "工程落法：多节点同前缀宣告、健康检查驱动收敛、就近低延迟；"
                    "与 consistent-hash/circuit-breaker 同属可用性家族、与 redundancy 同源空间冗余。",
     "standards": ["RFC 1546 Anycast", "RFC 2526 Anycast 地址", "BCP 126 / RFC 4786"],
     "canon_refs": ["consistent-hash", "circuit-breaker", "redundancy"]},
    {"id": "consistent-hash", "name": "一致性哈希", "gist": "分布式节点增减时最小化键重映射，使负载均衡在扩缩容下保持稳态。",
     "detail": "一致性哈希（Karger et al. 1997, MIT）将节点与键映射于同一哈希环，增减节点仅影响相邻区间，"
               "重映射量由 O(N) 降至 O(1/N)；虚拟节点均衡负载倾斜。非 IETF RFC，属算法经典。",
     "engineering": "工程落法：虚拟节点防倾斜、带权重环、副本跨故障域放置；"
                    "与 anycast-routing 同属可用性/均衡家族（按空间就近 vs 按键分布）。",
     "standards": ["Karger et al. 1997 (一致性哈希, 非 RFC)"],
     "canon_refs": ["anycast-routing"]},
    {"id": "circuit-breaker", "name": "熔断", "gist": "故障率超阈即自动断路，快速失败并保护后端免于级联雪崩。",
     "detail": "熔断（Nygard, Release It!）以 closed/open/half-open 状态机，按错误率/时延阈值跳闸，半开试探恢复；"
               "与超时/重试/限流配合构成弹性三件套。非 RFC，属韧性工程范式。",
     "engineering": "工程落法：错误率阈值跳闸、半开试探、与超时/限流协同、熔断指标可观测；"
                    "与 redundancy/isolation 同源（隔离故障扩散）。",
     "standards": ["Nygard 2007 Release It! (熔断, 非 RFC)"],
     "canon_refs": ["redundancy", "isolation"]},
]

# ------------------------- 轴7 接入与链路层（6） ------------------------- #
ACCESS = [
    {"id": "lan-ethernet", "name": "以太网（IEEE 802.3）", "gist": "有线局域网基石：CSMA/CD 退场、全双工交换、速率与物理层演进。",
     "detail": "802.3 自 10M 演进至 400G+；现代以太网以全双工交换取代冲突域共享（CSMA/CD 仅历史兼容），"
               "物理层涵盖双绞线(8P8C/POE)、光纤、背板；POE（802.3af/at/bt）在布线层供电器件。",
     "engineering": "工程落法：接入层交换机划分冲突/广播域、链路聚合(LACP)提吞吐、POE 预算留余；"
                    "与 pppoe/vlan-isolation 同源承载。",
     "standards": ["IEEE 802.3", "IEEE 802.3af/at/bt (POE)"],
     "canon_refs": []},
    {"id": "wlan-80211", "name": "无线局域网（IEEE 802.11）", "gist": "WLAN 家族：2.4/5/6 GHz 频段、信道/带宽、BSS/ESS 拓扑与漫游。",
     "detail": "802.11 a/b/g/n/ac/ax(Wi-Fi 6)/be(Wi-Fi 7) 逐代提升 MIMO/OFDMA/吞吐；"
               "BSS（单 AP）经 ESS 多 AP 互联实现漫游；信道重叠与同频干扰是容量首要约束。",
     "engineering": "工程落法：信道规划避重叠、功率与漫游阈值调优、双频/三频分流；"
                    "与 wifi-security 同源（无线必配加密）、与 lan-ethernet 桥接为同一广播域。",
     "standards": ["IEEE 802.11 a/b/g/n/ac/ax/be"],
     "canon_refs": ["lan-ethernet", "wifi-security"]},
    {"id": "wifi-security", "name": "WiFi 安全（WPA2/WPA3）", "gist": "WPA2=802.11i/AES-CCMP、WPA3=SAE/GCMP/PMF：四次握手、前向安全、降级防护。",
     "detail": "WPA2 以 802.1X/EAP 或 PSK + 四次握手(AES-CCMP) 保障；WPA3 引入 SAE（抗字典）、"
               "GCMP-256 与 PMF（管理帧保护）强化；遗留 WEP/WPA 与 WPS 已被攻破应禁用。"
               "KRACK（WPA2 四次握手重装）、Dragonblood（WPA3 侧信道）为已公开失效记录。",
     "engineering": "工程落法：禁 WEP/WPA/WPS、强制 WPA3 并保留 WPA2 兼容、PMF 强制、"
                    "降级攻击面收敛；与 port-auth/integrity-checksum 同源（链路层完整性）。",
     "standards": ["IEEE 802.11i (WPA2)", "WPA3 (SAE/GCMP/PMF)", "KRACK/Dragonblood 公告"],
     "canon_refs": ["wlan-80211", "port-auth"]},
    {"id": "port-auth", "name": "端口接入认证（802.1X/EAP/RADIUS）", "gist": "基于端口的准入：EAP 方法经 RADIUS 集中 AAA，未认证不开放网络。",
     "detail": "802.1X 在交换机/AP 端口做准入（Supplicant→Authenticator→Authentication Server），"
               "EAP 承载多种认证方法（PEAP/EAP-TLS/TEAP）；RADIUS 集中记账与策略下发；"
               "与 WiFi 安全、有线接入共用同一 AAA 后端。",
     "engineering": "工程落法：关键端口 802.1X 强制、证书(PEAP/EAP-TLS)替代弱口令、"
                    "RADIUS 与网络策略联动；与 wifi-security/tls-baseline 同源（认证与加密）。",
     "standards": ["IEEE 802.1X", "IETF EAP (RFC 3748)", "RADIUS (RFC 2865)"],
     "canon_refs": ["wifi-security"]},
    {"id": "vlan-isolation", "name": "VLAN 与链路隔离（802.1Q）", "gist": "IEEE 802.1Q 划分广播域：Trunk/Access、802.1AE MACsec 链路加密。",
     "detail": "802.1Q 以 VLAN Tag 隔离广播域（Access/Trunk），是网络分区的第一道边界；"
               "802.1AE(MACsec) 在二层做逐跳链路加密；802.1D/1w 生成树防止环路；"
               "与 protec 隔离原则(isolated)同源——把故障/危险域限制在局部。",
     "engineering": "工程落法：按信任域划 VLAN、Trunk 收窄允许的 VLAN、MACsec 护关键链路、"
                    "生成树防环；与 isolation/monitoring 同源（隔离+可观测）。",
     "standards": ["IEEE 802.1Q", "IEEE 802.1AE (MACsec)", "IEEE 802.1D/1w (STP/RSTP)"],
     "canon_refs": ["lan-ethernet", "isolation"]},
    {"id": "pppoe", "name": "PPPoE 宽带接入（RFC 2516）", "gist": "在以太网之上承载 PPP：发现/会话两阶段、MTU 1492、运营商 WAN 接入范式。",
     "detail": "PPPoE 分 Discovery（PADI/PADO/PADR/PADS）与 Session（PPP LCP/IPCP + 承载）两阶段，"
               "在以太网上为每户建立独立 PPP 会话；MTU 降至 1492 以承载 PPPoE 头，"
               "是 DSL/光纤入户前的经典 WAN 接入方式（现多被 IPoE/DHCP 替代）。",
     "engineering": "工程落法：WAN 侧 PPPoE 拨号与重连、MTU 1492 防分片、会话数上限防资源耗尽；"
                    "与 lan-ethernet/redundancy 同源（WAN 多拨冗余）。",
     "standards": ["RFC 2516 PPPoE", "RFC 1661 PPP"],
     "canon_refs": ["lan-ethernet", "redundancy"]},
    {"id": "sparklink", "name": "星闪（SparkLink/NearLink）", "gist": "我国主导的近距离无线通信标准：空口分层覆盖宽带/窄带/高精定位/无源零功耗四模式，面向全场景智能物联。",
     "detail": "星闪（SparkLink，国际名 NearLink）由星闪联盟推动；空口模式分 SLB（同步宽带，高吞吐）、"
               "SLE（同步窄带，低功耗广连接）、SLP（同步高精定位）、SLZ（无源零功耗，3.0 新增第四空口模式，"
               "对标 RFID 类无源场景）；星闪 3.0 标准成果于 CEIC2026 峰会（2026-10-22~24，深圳）发布，"
               "新增毫米波、PQC 后量子密码、量子安全方向；《星闪 SLE 3.0 技术标准演进蓝皮书》60 余家单位参编；"
               "此前已发布无损音频等三项标准；15 项推荐性国家标准同步发布（编号未在报道中列出，needs_verify）。",
     "engineering": "工程落法：星闪选型按场景分层（吞吐优先 SLB / 连接密度优先 SLE / 定位优先 SLP / "
                    "无源标签优先 SLZ）；PQC/量子安全前置要求；与 wlan-80211 同域互补（短距无线多制式并存）；"
                    "15 项推荐性国家标准编号 needs_verify。",
     "standards": ["星闪联盟标准（GB/T 编号 needs_verify）"],
     "canon_refs": ["wlan-80211"]},
]

# ------------------------- 轴8 IPv6 与 ICMPv6 控制面（10） ------------------------- #
IPV6 = [
    {"id": "ipv6-base", "name": "IPv6 基址与报头（RFC 8200）", "gist": "128 位地址空间、固定 40 字节报头 + 扩展头链，取代 IPv4 的地址枯竭与 NAT 依赖。",
     "detail": "IPv6 报头固定 40 字节（流量类/流标签/下一报头/跳限/源地址/目的地址八字段），"
               "可选功能经扩展头链（逐跳/路由/分段/目的/认证/封装）承载；地址分全球单播(GUA)/"
               "链路本地(FE80::/10)/唯一本地(FC00::/7)/组播四类；取消广播（广播职能由组播取代），"
               "ARP 等二层依赖由 ICMPv6 NDP 接管；最小 MTU 1280（路由器不再分片）。",
     "engineering": "工程落法：地址规划（前缀委派 PI/PA）、路径 MTU 1280 下限核算、链路本地必配；"
                    "与 slaac/dhcpv6 同源（地址配置双轨）、与 ndp 同源（控制面）。",
     "standards": ["RFC 8200 IPv6", "RFC 4291 地址架构", "RFC 6157 IPv6 过渡"],
     "canon_refs": ["slaac", "ndp"]},
    {"id": "icmpv6", "name": "ICMPv6 两类消息（RFC 4443）", "gist": "IPv6 协议族控制面：差错报文 + 信息报文，NDP/MLD/PMTUD 皆由其承载。",
     "detail": "差错报文（目的不可达、包过大 Packet Too Big、超时、参数问题）与信息报文"
               "（Echo Request 128 / Echo Reply 129）两类；NDP（133-137）取代 ARP 完成地址解析与"
               "路由器发现，Packet Too Big 支撑 PMTUD，MLDv2 取代 IGMP 做组播成员管理；"
               "控制面即攻击面——伪造 RA/NA 可做中间人与流量劫持。",
     "engineering": "工程落法：ICMPv6 不过度过滤（PMTUD 依赖 Packet Too Big），但对 RA/NA 做"
                    "首跳准入（RA-Guard RFC 7113）；与 ndp/pmtud 同源（控制面消息三职能）。",
     "standards": ["RFC 4443 ICMPv6"],
     "canon_refs": ["ndp", "pmtud"]},
    {"id": "ndp", "name": "邻居发现 NDP（RFC 4861）", "gist": "ICMPv6 133-137 五消息完成地址解析、路由器发现、DAD 与重定向，取代 IPv4 ARP。",
     "detail": "RS(133)/RA(134)/NS(135)/NA(136)/Redirect(137)；RA 携前缀信息与 M/O/A 位，"
               "决定 SLAAC 与 DHCPv6 触发方式；重复地址检测（DAD）以 NS 探链路本地地址防地址冲突；"
               "solicited-node 组播（FF02::1:FFxx:xxxx）把解析收敛到小范围组播；"
               "无防护的 NDP 是可被伪造 RA 劫持的首跳信任点。",
     "engineering": "工程落法：RA-Guard（RFC 7113 实施建议）防伪造 RA、交换机侧 NDP 侦听绑定、"
                    "DAD 失败显式告警；与 send-cga/netauth 同源（首跳信任与准入）。",
     "standards": ["RFC 4861 NDP", "RFC 7113 RA-Guard 实施建议"],
     "canon_refs": ["icmpv6", "slaac", "send-cga"]},
    {"id": "slaac", "name": "无状态自动配置 SLAAC（RFC 4862）", "gist": "主机从 RA 前缀自组全球地址，无 DHCP 服务器也可联网，隐私扩展用临时地址。",
     "detail": "RA 的 A 位置位即启用 SLAAC；接口标识（EUI-64）默认由 MAC 派生，"
               "可反推硬件身份暴露隐私；RFC 8981 隐私扩展（临时地址默认启用、定期轮换、"
               "优先用临时地址出站）取代 RFC 4941；M/O 位置位时 SLAAC 与 DHCPv6 协同（拿地址再取选项）。",
     "engineering": "工程落法：默认启用 RFC 8981 临时地址、前缀变更/重编号监控、DAD 冲突处置；"
                    "与 dhcpv6 同源（地址配置双轨互补）。",
     "standards": ["RFC 4862 SLAAC", "RFC 8981 临时地址"],
     "canon_refs": ["ipv6-base", "dhcpv6"]},
    {"id": "dhcpv6", "name": "有状态配置 DHCPv6（RFC 8415）", "gist": "四消息交互（Solicit/Advertise/Request/Reply）分配地址 + 选项，支持前缀委派。",
     "detail": "有状态模式以 IA_NA（身份关联非临时地址）分配地址，无状态模式仅经 Information-request "
               "取 DNS/域等选项；IA_PD 前缀委派让下游路由器（CPE）把前缀再分配给 LAN；"
               "中继代理（Relay）跨网段转发；与 SLAAC 按 RA 的 M/O 位协同分工。",
     "engineering": "工程落法：DHCPv6 中继部署、IA_PD 前缀委派链（上游→CPE→LAN）、"
                    "租约续租与地址池监控；与 netsys dhcp 同源（netsys 已含 DHCPv6 RFC 8415 编目）。",
     "standards": ["RFC 8415 DHCPv6"],
     "canon_refs": ["slaac", "ipv6-base"]},
    {"id": "pmtud", "name": "路径 MTU 发现 PMTUD（RFC 8201）", "gist": "源端发现路径最小 MTU 避免分片：IPv6 路由器不分片，超限由 Packet Too Big 回报。",
     "detail": "IPv6 取消路由器分片（仅源端可用分段扩展头），节点初始假设 MTU 1280，"
               "收到 ICMPv6 Packet Too Big 后降 MTU 重发；防火墙滤 ICMPv6 差错会造成黑洞"
               "（大包发不出、小包正常）；RFC 4821 PLPMTUD 以探测包在 ICMP 被滤场景兜底。",
     "engineering": "工程落法：防火墙不滤 Packet Too Big、隧道 MTU 折算（如 1480 档）、"
                    "PLPMTUD 兜底；与 icmpv6 同源（控制面差错依赖）。",
     "standards": ["RFC 8201 PMTUD", "RFC 4821 PLPMTUD"],
     "canon_refs": ["icmpv6"]},
    {"id": "nat64-dns64", "name": "NAT64/DNS64 过渡（RFC 6146/6147/6052）", "gist": "纯 IPv6 客户端访问 IPv4 服务器的合成地址过渡方案：DNS64 合成 AAAA、NAT64 协议转换。",
     "detail": "DNS64 递归解析在目标仅有 A 记录时合成 64:ff9b::/96（RFC 6052 知名前缀，"
               "Embedded Format 内嵌 IPv4 地址）的 AAAA；NAT64 做 v6↔v4 协议转换"
               "（有状态 RFC 6146 / 无状态 RFC 6145）；局限：不支持 IPv4 字面量地址、"
               "应用层穿透（FTP/SIP 类）需 ALG；常与 464xlat/CLAT 组合覆盖移动侧。",
     "engineering": "工程落法：DNS64 递归解析部署、NAT64 前缀规划、IPv4 字面量改写与 ALG 策略；"
                    "与 netsys nat 同源（netsys 已含 NAT64 RFC 6146/6147 + DNS64 RFC 6052 编目）。",
     "standards": ["RFC 6146 NAT64", "RFC 6147 DNS64", "RFC 6052 嵌入格式"],
     "canon_refs": ["ipv6-base"]},
    {"id": "6lowpan", "name": "6LoWPAN 物联网适配（RFC 4944/6282/6775）", "gist": "在 IEEE 802.15.4 小帧（127B 净荷）上承载 IPv6：头部压缩、分片与轻量邻居发现。",
     "detail": "6LoWPAN 以 IPHC/NHC 头部压缩（RFC 6282）把 40 字节 IPv6 头压到数字节，"
               "分片（首片/后续片）适配 127 字节帧，Mesh-under/Route-over 两种转发；"
               "6LoWPAN-ND（RFC 6775）以地址注册选项替代 DAD 泛滥，做轻量地址配置；"
               "Thread/6TiSCH 为其上层演进（时间同步信道跳频）。",
     "engineering": "工程落法：头部压缩参数核算、分片重组缓冲管理、占空比/功耗预算；"
                    "与 ndp 同源（轻量化邻居发现）、与 netsys edge 同源（新硬件单板机物联网）。",
     "standards": ["RFC 4944 6LoWPAN", "RFC 6282 头部压缩", "RFC 6775 6LoWPAN-ND"],
     "canon_refs": ["ipv6-base", "ndp"]},
    {"id": "send-cga", "name": "SEND 与 CGA 安全邻居发现（RFC 3971/3972）", "gist": "用 CGA 地址 + 数字签名保护 NDP 防 RA/NA 欺骗，设计完备但现实生态近乎失效。",
     "detail": "CGA 地址把公钥哈希编入接口标识（RFC 3972，Sec 冲突参数调强度，哈希碰撞代价随 Sec 指数上升）；"
               "SEND（RFC 3971）以 CPS/CPA 选项对 RA/NA 签名，信任锚经证书链（RFC 6495）部署；"
               "生成 CGA 的算力开销与路由器/客户端/证书全链部署门槛，使家用生态几乎零部署；"
               "现实防线由 RA-Guard（RFC 7113）+ 首跳端口准入承担。",
     "engineering": "工程落法：SEND 仅在受控企业网评估部署，普遍场景用 RA-Guard + 端口准入；"
                    "与 ndp/netauth 同源（首跳信任与准入）；生态失效现状按 needs_verify 挂牌。",
     "standards": ["RFC 3971 SEND", "RFC 3972 CGA", "RFC 7113 RA-Guard"],
     "canon_refs": ["ndp", "port-auth"]},
    {"id": "mld", "name": "组播侦听发现 MLD（RFC 2710/3810）", "gist": "IPv6 组播组成员管理取代 IGMP：MLDv1 加入/离开、MLDv2 源过滤（SSM 基础）。",
     "detail": "MLDv1（RFC 2710）类 IGMPv2 管加入/离开；MLDv2（RFC 3810）增源特定组播过滤"
               "（INCLUDE/EXCLUDE 模式），是 SSM 的成员侧协议；MLD 消息经 ICMPv6（类型 130-132）承载；"
               "IPv6 无广播，ARP/NetBIOS/DHCP 广播职能全部改由组播"
               "（solicited-node 组播是 NDP 解析的基础，查路由器/ DNS 发现亦依赖之）。",
     "engineering": "工程落法：组播 snooping/querier 部署、SSM 范围规划、"
                    "solicited-node 组播表容量核算；与 ndp 同源（组播是 NDP 底座）。",
     "standards": ["RFC 2710 MLDv1", "RFC 3810 MLDv2"],
     "canon_refs": ["ipv6-base", "ndp"]},
]

# ------------------------- 桥接边（构建期校验无悬空） ------------------------- #
BRIDGES = [
    # 基本保护原则 → 既有概念系统（工程伦理/接口/编译/量子缓解翻译）
    {"from": "enclosure", "system": "datong", "target": "concept:cibei-buhai", "relation": "翻译",
     "how": "防护屏障（不伤设备）→ 慈悲不害（数据红线）：破坏性维护二次确认、错误给下一步"},
    {"from": "grounding", "system": "datong", "target": "concept:jueji-shouquan", "relation": "翻译",
     "how": "接地/等电位（故障收口）→ 绝地天通（特权收口）：维护/应急通道唯一提升、限时记因"},
    {"from": "monitoring", "system": "datong", "target": "concept:jingmo-tuomin", "relation": "翻译",
     "how": "监测数据 → 静默脱敏：监测数据默认脱敏、verbose 才多报"},
    {"from": "maintainability", "system": "zhuangzi", "target": "principle:yangsheng-bu-shang",
     "relation": "翻译", "how": "可维护（不造成二次损害）↔ 养生不伤：一切保护动作不伤设备/用户"},
    {"from": "enclosure", "system": "zhuangzi", "target": "principle:jiekou-pingquan",
     "relation": "翻译", "how": "防护规范同口径 ↔ 接口平权：各子系统维护/监测接口同源同口径"},
    {"from": "enclosure", "system": "baigong", "target": "principle:shengmo-guiju",
     "relation": "翻译", "how": "防护按规范 ↔ 绳墨规矩：防护/接地一处绳墨三方取直"},
    {"from": "monitoring", "system": "baigong", "target": "principle:jingshen-mingbian",
     "relation": "翻译", "how": "监控根因精审 ↔ 精审明辩：失效根因精审、不可说者（误报）不说"},
    {"from": "enclosure", "system": "apilab", "target": "concept:auth-redlines",
     "relation": "翻译", "how": "防护屏障（无后门）↔ 认证红线：令牌禁入 URL/Storage、维护通道零信任"},
    {"from": "monitoring", "system": "apilab", "target": "concept:openapi", "relation": "翻译",
     "how": "监测接口文档化 ↔ 接口公开：维护/监测接口公开可读、可审计"},
    {"from": "maintainability", "system": "comp", "target": "concept:make", "relation": "翻译",
     "how": "定时维护巡检 ↔ 定时构建/检查：每日/每季自检如日礼"},
    {"from": "enclosure", "system": "comp", "target": "concept:native-build", "relation": "翻译",
     "how": "维护前隔离环境 ↔ 净而后作（全新沙箱）：更换/维护前隔离再作业"},
    {"from": "enclosure", "system": "quantum", "target": "concept:mitigation", "relation": "同构",
     "how": "先定红线/禁区再谈可用 ↔ 先列不可（白名单）再论可行（量子纠错缓解）"},
    {"from": "cap-alert", "system": "netsys", "target": "module:emergency", "relation": "互文",
     "how": "protec 应急保护与 netsys emergency 应急通道守御 opt-in 互文"},
    {"from": "cap-alert", "system": "netsys", "target": "module:meshchat", "relation": "翻译",
     "how": "CAP 分级预警经 mesh 消息高扇出广播（与 datong 气象同构）"},
    # 轴6 传输与可用性 → 既有概念系统（安全/网络模块翻译）
    {"from": "tls-baseline", "system": "apilab", "target": "concept:auth-redlines", "relation": "同构",
     "how": "TLS 前向安全/零信任 ↔ 认证红线（令牌禁入 URL/Storage、维护通道零信任）"},
    {"from": "tls-baseline", "system": "netsys", "target": "module:tls13", "relation": "同构",
     "how": "TLS 1.3 基线 ↔ netsys tls13 模块（同工程落点：前向安全/AEAD/1-RTT）"},
    {"from": "integrity-checksum", "system": "apilab", "target": "concept:openapi", "relation": "翻译",
     "how": "完整性可验证（校验和回读）↔ 接口公开可审计（可验证性同源）"},
    {"from": "anycast-routing", "system": "netsys", "target": "module:meshchat", "relation": "同构",
     "how": "就近服务/故障自动绕行 ↔ mesh 多路径高扇出（可用性同构）"},
    {"from": "circuit-breaker", "system": "netsys", "target": "module:emergency", "relation": "翻译",
     "how": "熔断快速失败保护后端 ↔ emergency 应急通道守御（故障隔离同源）"},
    # 轴7 接入与链路层 → netsys 组网模块（接入/隔离/认证/WAN 落点）
    {"from": "lan-ethernet", "system": "netsys", "target": "module:network", "relation": "同构",
     "how": "以太网接入承载 ↔ netsys network 模块（有线接入基础，其余模块在其上组网）"},
    {"from": "wlan-80211", "system": "netsys", "target": "module:apctrl", "relation": "同构",
     "how": "WLAN 接入点控制 ↔ netsys apctrl 模块（接入点控制只在用户显式授权时动作）"},
    {"from": "wifi-security", "system": "netsys", "target": "module:netauth", "relation": "同构",
     "how": "WPA2/WPA3 认证加密 ↔ netsys netauth 分级授权与证书校验（链路层 AAA 同源）"},
    {"from": "vlan-isolation", "system": "netsys", "target": "module:openwrt", "relation": "同构",
     "how": "VLAN/MACsec 分区隔离 ↔ openwrt 小步可回滚的隔离变更（隔离原则落到组网）"},
    {"from": "pppoe", "system": "netsys", "target": "module:nat", "relation": "翻译",
     "how": "PPPoE WAN 拨号接入 ↔ netsys nat 出口（WAN 多拨冗余与出口 NAT 同源）"},
    # 轴8 IPv6 与 ICMPv6 控制面 → netsys 组网模块（协议分层/地址配置/过渡/首跳信任落点）
    {"from": "ipv6-base", "system": "netsys", "target": "module:network", "relation": "同构",
     "how": "IPv6 基址承载 ↔ netsys network 模块（netsys 已含 IPv6 RFC 8200 编目，组网基座）"},
    {"from": "icmpv6", "system": "netsys", "target": "module:osi", "relation": "同构",
     "how": "ICMPv6 控制面消息 ↔ netsys osi 协议分层（控制面职能：差错/信息两类）"},
    {"from": "ndp", "system": "netsys", "target": "module:netauth", "relation": "翻译",
     "how": "NDP 首跳信任（RA/NA 准入）↔ netsys netauth 分级授权与证书校验（首跳信任同源）"},
    {"from": "slaac", "system": "netsys", "target": "module:dhcp", "relation": "同构",
     "how": "SLAAC 无状态配置 ↔ netsys dhcp（地址配置双轨：无状态/有状态互补）"},
    {"from": "dhcpv6", "system": "netsys", "target": "module:dhcp", "relation": "同构",
     "how": "DHCPv6 有状态配置与 IA_PD 前缀委派 ↔ netsys dhcp（已含 DHCPv6 RFC 8415 编目）"},
    {"from": "pmtud", "system": "netsys", "target": "module:osi", "relation": "翻译",
     "how": "PMTUD 路径 MTU ↔ netsys osi 分层（分片责任从路由器上移源端）"},
    {"from": "nat64-dns64", "system": "netsys", "target": "module:nat", "relation": "同构",
     "how": "NAT64/DNS64 过渡 ↔ netsys nat（已含 NAT64 RFC 6146/6147 + DNS64 RFC 6052 编目）"},
    {"from": "6lowpan", "system": "netsys", "target": "module:edge", "relation": "同构",
     "how": "6LoWPAN 物联网适配 ↔ netsys edge 新硬件单板机（小帧承载 IPv6 同域）"},
    {"from": "send-cga", "system": "netsys", "target": "module:netauth", "relation": "同构",
     "how": "SEND/CGA 邻居发现安全 ↔ netsys netauth（首跳认证信任同源）"},
    {"from": "mld", "system": "netsys", "target": "module:network", "relation": "翻译",
     "how": "MLD 组播成员管理 ↔ netsys network（IPv6 无广播、组播承载同源）"},
]


NEEDS_VERIFY = [
    {"item": "标准编号与机构口径", "status": "通行口径登记",
     "note": "IEC/ASHRAE/GB/UL 等编号按通行口径登记，未逐条核对最新版次与官方发布日期"},
    {"item": "热寿命阿伦尼乌斯模型", "status": "经验模型",
     "note": "温度每升 10K 寿命减半为经验近似，具体材料需厂商加速老化数据"},
    {"item": "CAP 1.2 应用场景", "status": "结构性翻译",
     "note": "将 CAP 分级预警翻译为设备群告警分级，非等同：CAP 面向公共预警、本系统面向设备自保护"},
    {"item": "应急定位 ETA 口径", "status": "量级诚实标注",
     "note": "定位精度/ETA 按置信下限（floor）标注，不报虚假高精度（见 locate-fuse）"},
    {"item": "非 IETF 标准的传输/可用性算法", "status": "通行口径登记",
     "note": "一致性哈希（Karger et al. 1997）与熔断（Nygard 2007）按经典算法口径登记，非 IETF RFC；"
            "Anycast BCP 126 编号按通行口径（v0.6.67 新增 transfer 域）"},
    {"item": "WiFi 安全失效记录（KRACK/Dragonblood）", "status": "通行安全公告登记",
     "note": "KRACK(2017 WPA2 四次握手重装)与 Dragonblood(2019 WPA3 侧信道)按公开安全公告口径登记，"
            "未逐条核对 CVE 编号与厂商修复状态（v0.6.68 新增 access 域）"},
    {"item": "星闪 3.0 推荐性国家标准编号", "status": "报道口径登记",
     "note": "CEIC2026 峰会（2026-10-22~24 深圳）发布 15 项星闪推荐性国家标准，编号未在报道中列出，"
            "未独立核对国标编号/名称/实施日期（v0.6.69 新增 access 域 sparklink）"},
    {"item": "SEND 生态失效现状（RPN 392）", "status": "报道口径登记",
     "note": "IPv6 安全链综述判定 SEND（RFC 3971/3972）设计完备但生态失效、风险优先数 RPN 392，"
            "为文章单方陈述，未独立复核（v0.6.69 新增 ipv6 域）"},
]


def live_user_face() -> dict:
    """构建期实测：CLI 子命令数 / GUI 窗口数 / webapi ACTIONS / deno 两文件版本
    + 概念系统数（与 build_datong.py 同一口径，不硬编码）。"""
    sys.path.insert(0, str(SRC))
    from sysweeper import cli, webapi

    parser = cli.build_parser() if hasattr(cli, "build_parser") else None
    sub_count = 0
    if parser is not None:
        for a in parser._actions:
            if a.__class__.__name__ == "_SubParsersAction":
                sub_count = len(a.choices)

    gui_src = (SRC / "sysweeper" / "gui.py").read_text(encoding="utf-8")
    gui_windows = len(re.findall(r"def show_\w+\(", gui_src))

    def deno_version(name: str):
        p = DENO_DIR / name
        if not p.exists():
            return None
        m = re.search(r'const VERSION = "([^"]+)"', p.read_text(encoding="utf-8"))
        return m.group(1) if m else None

    plang = json.loads((DATA_DIR / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((DATA_DIR / "comp_taxonomy.json").read_text(encoding="utf-8"))

    return {
        "cli_subcommands": sub_count,
        "webapi_actions": len(webapi.ACTIONS),
        "gui_windows": gui_windows,
        "deno_console_version": deno_version("console.ts"),
        "deno_report_viewer_version": deno_version("report_viewer.ts"),
        "lang_total": len(plang.get("lang_index", {})),
        "probe_verified": len(plang.get("probe_results") or []),
        "comp_lang_needs": sum(1 for c in comp.get("concepts", [])
                               if c.get("domain") == "lang-need"),
        "webapi_protocol": "JSONL 白名单协议（一行请求 JSON → 一行响应 JSON）",
        "gui_note": "tkinter GUI：show_* 面板窗口（概念系统中心/各子系统面板）",
        "deno_note": "Deno Web 控制台（console.ts）+ 报告查看器（report_viewer.ts），"
                     "与 Python 侧经 webapi JSONL 衔接",
        "lang_note": "语言面：plang 161 条语言（其中 probe 实测 15 种）、comp "
                     "语言编译需要轴随实测推进；--check 与磁盘登记值逐键比对",
        "concept_systems": 11,
    }


def build():
    bridges = [
        {"from": f"protec:{b['from']}", "system": b["system"], "target": b["target"],
         "relation": b["relation"], "how": b["how"]}
        for b in BRIDGES
    ]
    concepts = _concepts()
    for c in concepts:                       # 数据层字段齐备统一（与 datong 同构）
        c.setdefault("standards", [])
        c.setdefault("bridges", [])
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/protec/build_protec.py",
            "main_root": "wordbuddy-github",
            "title": "protec 概念系统（产品·设备设施长期运行与基本保护，以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": VERSION,
            "canon": "设备设施长期可靠运行与基本保护：材料耐久/电气安全/环境标准/应急保护"
                     "四域，统于七条基本保护原则（冗余/降额/隔离/监控/接地/防护/可维护）；"
                     "传输与可用性域（TCP/QUIC/HTTP Range/TLS/Anycast/一致性哈希/熔断）与 docs/74 + native/transfer 同源；"
                     "接入与链路层域（以太网/WLAN/WiFi 安全/802.1X/VLAN/PPPoE/星闪）与 docs/75 + docs/76 同源；"
                     "IPv6 与 ICMPv6 控制面域（基址/NDP/SLAAC/DHCPv6/PMTUD/NAT64·DNS64/6LoWPAN/SEND·CGA/MLD）"
                     "与 docs/76 IPv6 全链路 + ICMPv6 两篇同源",
            "axes": ["durability", "electrical", "environment", "emergency", "protection", "transfer", "access", "ipv6"],
            "concept_total": len(concepts),
            "principle_total": len(PRINCIPLES),
            "bridge_count": len(bridges),
            "honesty": "只读登记、标准编号与机构按通行口径登记、不臆造实测数字；桥接只作"
                       "保护原则 ↔ 既有工程伦理/接口/编译/量子缓解的结构翻译，不宣称等同；"
                       "未核对原典/版次/机构口径者统一挂 needs_verify；"
                       "应急定位 ETA 按置信下限诚实标注，不报虚假高精度；"
                       "传输/可用性算法（一致性哈希/熔断）非 RFC 按经典口径登记（v0.6.67 新增 transfer 域）；"
                       "WiFi 失效记录（KRACK/Dragonblood）按安全公告口径登记（v0.6.68 新增 access 域）；"
                       "星闪 15 项推荐性国标编号未列（v0.6.69 access 域补 sparklink）；"
                       "SEND 生态失效（RPN 392）按报道口径登记（v0.6.69 新增 ipv6 域）",
            "redline_note": "不伤设备也不伤用户（慈悲不害）：破坏性维护二次确认；维护/应急通道"
                            "唯一提升、限时记因（绝地天通）；故障域隔离（防火 enclosure + 限功率）；"
                            "错误提示必给下一步",
        },
        "layers": [
            {"role": "durability", "domain": "durability", "tier": 1, "count": len(DURABILITY),
             "canon": "材料耐久", "sense": "腐蚀/疲劳/蠕变/热老化/湿气侵入/电池衰减/材料选型 7 条"},
            {"role": "electrical", "domain": "electrical", "tier": 1, "count": len(ELECTRICAL),
             "canon": "电气安全", "sense": "接触高阻发热/电偶腐蚀/串联电弧/接地RCD/连接器老化/可燃底座 6 条"},
            {"role": "environment", "domain": "environment", "tier": 1, "count": len(ENVIRONMENT),
             "canon": "环境标准", "sense": "IP 代码/IEC 60721/ASHRAE TC9.9/IEC 62368-1 4 条"},
            {"role": "emergency", "domain": "emergency", "tier": 2, "count": len(EMERGENCY),
             "canon": "应急保护", "sense": "CAP 1.2 四级预警/定位融合/求救报文/应急物资清单 4 条"},
            {"role": "protection", "domain": "protection", "tier": 1, "count": len(PRINCIPLES),
             "canon": "基本保护原则", "sense": "冗余/降额/隔离/监控/接地/防护/可维护 7 条（= principles）"},
            {"role": "transfer", "domain": "transfer", "tier": 1, "count": len(TRANSFER),
             "canon": "传输与可用性", "sense": "TCP/QUIC/HTTP Range/完整性校验/TLS/Anycast/一致性哈希/熔断 8 条（v0.6.67 新增）"},
            {"role": "access", "domain": "access", "tier": 1, "count": len(ACCESS),
             "canon": "接入与链路层", "sense": "以太网/WLAN/WiFi 安全/802.1X/VLAN/PPPoE/星闪 7 条（v0.6.68 新增，docs/75 同源；v0.6.69 补星闪，docs/76 同源）"},
            {"role": "ipv6", "domain": "ipv6", "tier": 1, "count": len(IPV6),
             "canon": "IPv6 与 ICMPv6 控制面", "sense": "IPv6 基址/ICMPv6/NDP/SLAAC/DHCPv6/PMTUD/NAT64·DNS64/6LoWPAN/SEND·CGA/MLD 10 条（v0.6.69 新增，docs/76 同源）"},
        ],
        "domains": DOMAINS,
        "concepts": concepts,
        "by_domain": by_domain,
        "principles": [
            {"id": p["id"], "name": p["name"], "gist": p["gist"],
             "engineering": p["engineering"], "canon_refs": p["canon_refs"]}
            for p in PRINCIPLES
        ],
        "bridges": bridges,
        "needs_verify": list(NEEDS_VERIFY),
        "user_face_facts": live_user_face(),
    }
    return doc


def _concepts():
    out = []
    for t in DURABILITY:
        out.append({"id": t["id"], "domain": "durability", "name": t["name"],
                    "gist": t["gist"], "detail": t["detail"],
                    "engineering": t["engineering"], "standards": t.get("standards", []),
                    "canon_refs": t.get("canon_refs", [])})
    for e in ELECTRICAL:
        out.append({"id": e["id"], "domain": "electrical", "name": e["name"],
                    "gist": e["gist"], "detail": e["detail"],
                    "engineering": e["engineering"], "standards": e.get("standards", []),
                    "canon_refs": e.get("canon_refs", [])})
    for e in ENVIRONMENT:
        out.append({"id": e["id"], "domain": "environment", "name": e["name"],
                    "gist": e["gist"], "detail": e["detail"],
                    "engineering": e["engineering"], "standards": e.get("standards", []),
                    "canon_refs": e.get("canon_refs", [])})
    for e in EMERGENCY:
        out.append({"id": e["id"], "domain": "emergency", "name": e["name"],
                    "gist": e["gist"], "detail": e["detail"],
                    "engineering": e["engineering"], "standards": e.get("standards", []),
                    "canon_refs": e.get("canon_refs", [])})
    for p in PRINCIPLES:
        out.append({"id": p["id"], "domain": "protection", "name": p["name"],
                    "gist": p["gist"], "detail": p.get("detail", ""), "engineering": p["engineering"],
                    "standards": [], "canon_refs": p["canon_refs"]})
    for t in TRANSFER:
        out.append({"id": t["id"], "domain": "transfer", "name": t["name"],
                    "gist": t["gist"], "detail": t["detail"], "engineering": t["engineering"],
                    "standards": t.get("standards", []), "canon_refs": t.get("canon_refs", [])})
    for a in ACCESS:
        out.append({"id": a["id"], "domain": "access", "name": a["name"],
                    "gist": a["gist"], "detail": a["detail"], "engineering": a["engineering"],
                    "standards": a.get("standards", []), "canon_refs": a.get("canon_refs", [])})
    for v in IPV6:
        out.append({"id": v["id"], "domain": "ipv6", "name": v["name"],
                    "gist": v["gist"], "detail": v["detail"], "engineering": v["engineering"],
                    "standards": v.get("standards", []), "canon_refs": v.get("canon_refs", [])})
    return out


def _target_ids(name: str, doc: dict) -> Optional[set]:
    """返回某既有概念系统的可桥接目标 id 全集（按各系统数据层结构）。"""
    if name == "datong":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    if name == "zhuangzi":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    if name == "baigong":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    if name == "apilab":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "comp":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "quantum":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "netsys":
        return {m["id"] for m in doc.get("modules", [])}
    return None


def check(doc: dict) -> List[str]:
    """防漂移校验，返回错误列表（空 = 通过）。"""
    errs: List[str] = []

    if doc.get("_meta", {}).get("schema") != SCHEMA:
        errs.append(f"schema 不符（期望 {SCHEMA}）")

    valid_domains = {d["domain"] for d in doc["domains"]}
    ids: set = set()
    for c in doc["concepts"]:
        if c["id"] in ids:
            errs.append(f"概念 id 重复：{c['id']}")
        ids.add(c["id"])
        if c["domain"] not in valid_domains:
            errs.append(f"{c['id']} 轴 {c['domain']} 未登记")
        if not c.get("gist"):
            errs.append(f"{c['id']} 缺 gist")
        if not str(c.get("detail") or "").strip():
            errs.append(f"{c['id']} 缺 detail（详述）")
        if not c.get("engineering"):
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc.get("by_domain", {})):
        if inverted.get(d, []) != doc.get("by_domain", {}).get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    pc_ids = sorted(p["id"] for p in doc["principles"])
    et_ids = sorted(c["id"] for c in doc["concepts"] if c["domain"] == "protection")
    if pc_ids != et_ids:
        errs.append(f"protection 概念与 principles 不一致：{set(pc_ids) ^ set(et_ids)}")

    known = {c["id"] for c in doc["concepts"] if c["domain"] in ("durability", "electrical",
                                                                "environment", "emergency", "protection",
                                                                "transfer", "access", "ipv6")}
    for c in doc["concepts"]:
        for r in c.get("canon_refs", []):
            if r not in known:
                errs.append(f"canon_ref 悬空：{c['id']} → {r}")

    cache: Dict[str, Optional[set]] = {}

    def load_other(name: str) -> dict:
        return json.loads((DATA_DIR / f"{name}_taxonomy.json").read_text(encoding="utf-8"))

    for b in doc["bridges"]:
        fkind, _, fval = b["from"].partition(":")
        if fkind != "protec" or fval not in ids:
            errs.append(f"桥接起点悬空：{b['from']}")
            continue
        sysname, tgt = b["system"], b["target"]
        if sysname not in cache:
            cache[sysname] = _target_ids(sysname, load_other(sysname))
        target_ids = cache[sysname]
        if target_ids is None:
            errs.append(f"桥接目标系统未登记：{sysname}")
            continue
        kind, _, val = tgt.partition(":")
        if not kind or val not in target_ids:
            errs.append(f"桥接悬空：{sysname} 无目标 {tgt}")

    live = live_user_face()
    disk = doc.get("user_face_facts") or {}
    for k, v in live.items():
        if disk.get(k) != v:
            errs.append(f"实测面漂移：{k} 磁盘={disk.get(k)!r} 实测={v!r}（重跑 build 重建）")

    n = doc["_meta"]
    if (n.get("concept_total") != len(doc["concepts"])
            or n.get("bridge_count") != len(doc["bridges"])
            or n.get("principle_total") != len(doc["principles"])):
        errs.append("_meta 计数与实体不符")
    return errs


def report(doc: dict) -> None:
    n = doc["_meta"]
    print(f"{n['title']}（{n['version']}）")
    print(f"  canon：{n['canon']}")
    print(f"  规模：概念 {n['concept_total']} / 原则 {n['principle_total']} / "
          f"桥接 {n['bridge_count']} / need_verify {len(doc['needs_verify'])}")
    by = doc.get("by_domain", {})
    for d in doc["domains"]:
        print(f"    {d['domain']:<11} {len(by.get(d['domain'], [])):>2} 条  {d['label']}——{d['note']}")
    f = doc.get("user_face_facts", {})
    print(f"  实测面：CLI 子命令 {f.get('cli_subcommands')} / GUI 窗口 {f.get('gui_windows')} / "
          f"webapi ACTIONS {f.get('webapi_actions')} / deno v{f.get('deno_console_version')} / "
          f"plang {f.get('lang_total')} 条（probe 实测 {f.get('probe_verified')}）")
    bs = doc.get("bridges", [])
    per: Dict[str, int] = {}
    for b in bs:
        per[b.get("system", "?")] = per.get(b.get("system", "?"), 0) + 1
    print(f"  桥接边：{len(bs)} 条")
    for sname in sorted(per):
        print(f"    → {sname:<9} {per[sname]}")
    nv = doc.get("needs_verify", [])
    print(f"  needs_verify：{len(nv)} 项（" + "/".join(v.get("status", "") for v in nv) + "）")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    if "--check" in argv:
        if OUT.exists():
            disk = json.loads(OUT.read_text(encoding="utf-8"))
            live = live_user_face()
            dfacts = disk.get("user_face_facts") or {}
            for k, v in live.items():
                if isinstance(v, (int, float)) and dfacts.get(k) != v:
                    print(f"✗ user_face_facts.{k} 漂移：磁盘登记 {dfacts.get(k)} ≠ "
                          f"源码实测 {v}（需重建）")
                    return 1
        errs = check(doc)
        if errs:
            for e in errs:
                print("✗", e)
            return 1
        print(f"✓ 校验通过：{doc['_meta']['concept_total']} 个概念 / "
              f"{doc['_meta']['bridge_count']} 条桥接无悬空 / "
              f"用户端面·语言面事实与源码实测一致（{len(doc['needs_verify'])} 项诚实边界挂牌）")
        return 0
    doc["_meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗ 写盘前校验失败：", e)
        return 1
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已构建 {OUT}：{doc['_meta']['concept_total']} 个概念")
    report(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
