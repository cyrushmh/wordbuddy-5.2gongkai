#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「sciences」自然科学概念系统构建（v0.6.67，第十一概念系统，sciences）。

立意（用户原话）：「材料学、热力学、气候学、环境学、物理、化学、生物等以及相关
对产品（设备设施）长期运行和基本保护的协议和标准查看」。

本系统把七门自然科学作为只读概念系统登记，与 protec（产品保护）构成「科学底座 →
工程保护」的对照；并设 methodology（科学方法）轴，把可证伪/可重复/对照/溯因/定量/
同行评审/不确定度七条方法论原则作 protec 保护原则的科学依据：

    ├─ 轴1 materials      材料学（腐蚀/相变/疲劳/蠕变）
    ├─ 轴2 thermodynamics 热力学（定律/热传导/熵/相平衡）
    ├─ 轴3 climatology    气候学（温室效应/洋流/ENSO/碳循环）
    ├─ 轴4 environmental  环境学（污染/生态/可持续）
    ├─ 轴5 physics        物理（电磁/量子/力学）
    ├─ 轴6 chemistry      化学（电化学/反应动力学/元素周期）
    ├─ 轴7 biology        生物（细胞/进化/基因/生物圈）
    └─ 轴8 methodology    科学方法（= principles：可证伪/可重复/对照/溯因/定量/同行评审/不确定度）

桥接目标在 protec 与既有概念系统中必须真实存在，构建期校验无悬空。user_face 为
构建期实测，由 --check 逐键比对防漂移。

诚实边界：只读登记、科学表述按通行口径、不臆造实测数字；桥接只作「科学原理 ↔
工程保护/编译/量子/网络/工程伦理」的结构翻译，不宣称等同；凡未核对原典/版次者
统一挂 needs_verify。
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
OUT = DATA_DIR / "sciences_taxonomy.json"
DENO_DIR = ROOT / "src" / "deno"

VERSION = "0000.0000.0000.0067.20261025"
SCHEMA = "sciences_taxonomy/v1"

DOMAINS = [
    {"domain": "materials", "label": "材料学", "note": "设备材料的失效与相变基础：腐蚀/相变/疲劳/蠕变"},
    {"domain": "thermodynamics", "label": "热力学", "note": "能量与熵：定律/热传导/熵/相平衡"},
    {"domain": "climatology", "label": "气候学", "note": "地球气候系统：温室效应/洋流/ENSO/碳循环"},
    {"domain": "environmental", "label": "环境学", "note": "污染/生态/可持续，与 IEC 60721 环境分类配套"},
    {"domain": "physics", "label": "物理", "note": "电磁/量子/力学——protec 电气与防护的物理底座"},
    {"domain": "chemistry", "label": "化学", "note": "电化学/反应动力学/元素周期——腐蚀与接地的化学底座"},
    {"domain": "biology", "label": "生物", "note": "细胞/进化/基因/生物圈——自组织与适应范式"},
    {"domain": "methodology", "label": "科学方法", "note": "七条方法论原则（= principles）：可证伪/可重复/对照/溯因/定量/同行评审/不确定度"},
]

# ------------------------- 轴1 材料学（4） ------------------------- #
MATERIALS = [
    {"id": "corrosion", "name": "腐蚀", "gist": "金属与环境介质发生电化学/化学反应的渐进破坏。",
     "detail": "电化学腐蚀分阴阳极两半反应，潮湿+电解质（盐雾/凝露）加速；点蚀/缝隙腐蚀/"
               "应力腐蚀开裂为隐蔽高危形态；钝化膜与涂层是抗蚀主线。",
     "engineering": "工程落法：抗蚀材料/涂镀层/排水防潮，与 protec:corrosion 同源。",
     "standards": ["IEC 60068-2-11", "ISO 9223", "GB/T 10125"]},
    {"id": "phase-transition", "name": "相变", "gist": "物质在温压条件下固/液/气相等结构转变。",
     "detail": "相图刻画平衡态；马氏体相变、熔融、玻璃化转变直接决定材料可用温度窗口；"
               "相变伴随体积/潜热变化，影响尺寸与热管理。",
     "engineering": "工程落法：按相图定工作温区、避开相变温区选材料（protec:material-selection）。",
     "standards": ["GB/T 2423"]},
    {"id": "fatigue", "name": "疲劳", "gist": "循环应力下低于屈服强度的反复加载致裂纹扩展。",
     "detail": "高周（S-N 曲线）/低周（应变控制）两范式；焊点/弹片/支架高发；振动与温度循环叠加。",
     "engineering": "工程落法：避应力集中、留寿命裕度、定期更换（protec:fatigue 同源）。",
     "standards": ["ISO 1099", "GB/T 3075"]},
    {"id": "creep", "name": "蠕变", "gist": "高温/长期载荷下的缓慢塑性变形。",
     "detail": "蠕变三阶段（初/稳/加速）；塑料/焊料/紧固件在高温显著；预紧力随蠕变松弛致松脱。",
     "engineering": "工程落法：抗蠕变材料、控温、定期复紧（protec:creep 同源）。",
     "standards": ["GB/T 2039"]},
]

# ------------------------- 轴2 热力学（4） ------------------------- #
THERMO = [
    {"id": "thermo-laws", "name": "热力学定律", "gist": "能量守恒与熵增：第一定律守恒、第二定律指向不可逆。",
     "detail": "零/一/二/三定律分别定温标、守恒、熵增、绝对零度；第二定律约束一切热机效率上限，"
               "也是设备散热与热老化的根本约束。",
     "engineering": "工程落法：热设计必须给散热通路与热裕度（protec:thermal-aging 同源）。",
     "standards": ["ASHRAE TC9.9"]},
    {"id": "heat-transfer", "name": "热传导", "gist": "导热/对流/辐射三种传热机制。",
     "detail": "傅里叶导热、牛顿对流、斯特藩-玻尔兹曼辐射；设备散热靠三者协同；"
               "接触热阻是界面温升主因（与 protec:contact-heating 同类）。",
     "engineering": "工程落法：导热界面材料、风道/ heatsink、温度越限降频（protec:thermal-aging）。",
     "standards": ["ASHRAE TC9.9", "GB 50174"]},
    {"id": "entropy", "name": "熵", "gist": "系统无序度的度量，过程总是趋向熵增。",
     "detail": "克劳修斯/玻尔兹曼两种表述；信息熵与热力学熵同构；熵增即不可逆，是寿命与"
               "耗散的判据。",
     "engineering": "工程落法：不可逆损耗即老化，降耗=延寿（protec:derating 同源）。",
     "standards": []},
    {"id": "phase-equilibrium", "name": "相平衡", "gist": "多相共存的热力学平衡条件（化学势相等）。",
     "detail": "吉布斯相律约束自由度；相平衡决定材料在服役环境下的稳定相，是相变与腐蚀"
               "热力学基础。",
     "engineering": "工程落法：选服役环境下稳定相的材料、避相分离（protec:material-selection）。",
     "standards": []},
]

# ------------------------- 轴3 气候学（4） ------------------------- #
CLIMATOLOGY = [
    {"id": "greenhouse", "name": "温室效应", "gist": "大气温室气体吸收地表长波辐射致地表增温。",
     "detail": "CO₂/CH₄/H₂O 吸收红外；增强的温室效应驱动全球变暖；数据中心/设备散热与"
               "室外气候强相关，需按 ASHRAE 包络定温控。",
     "engineering": "工程落法：按气候带定温控与散热策略（protec:ashrae-thermal 同源）。",
     "standards": ["ASHRAE TC9.9", "GB 50174"]},
    {"id": "ocean-circulation", "name": "洋流", "gist": "海洋环流在全球尺度输运热量与碳。",
     "detail": "温盐环流（AMOC）等调节气候；其减弱会改变区域气候与极端事件频率，影响"
               "户外设备的环境基线。",
     "engineering": "工程落法：户外设备环境等级随气候带动态调整（protec:iec60721-class）。",
     "standards": ["IEC 60721"]},
    {"id": "enso", "name": "ENSO", "gist": "厄尔尼诺-南方涛动：赤道太平洋海温的准周期振荡。",
     "detail": "厄尔尼诺/拉尼娜改变全球降水与温度格局，致极端天气频次变化；是环境适应性"
               "设计的低频背景。",
     "engineering": "工程落法：极端环境工况取 ENSO 相位的最不利组合定防护（protec:ip-code）。",
     "standards": ["IEC 60721"]},
    {"id": "carbon-cycle", "name": "碳循环", "gist": "碳在大气/海洋/陆地间的交换与封存。",
     "detail": "光合/呼吸/风化/燃烧收支；人为排放打破平衡致累积；碳基线决定长期环境分类"
               "与可持续约束。",
     "engineering": "工程落法：环境分类含碳/化学腐蚀基线（protec:iec60721-class 同源）。",
     "standards": ["IEC 60721", "ISO 14040"]},
]

# ------------------------- 轴4 环境学（3） ------------------------- #
ENVIRONMENTAL = [
    {"id": "pollution", "name": "污染", "gist": "有害物质进入环境并超阈值的累积。",
     "detail": "气/水/土/电磁多介质；污染物（盐雾/硫化物/粉尘）直接加速腐蚀与绝缘下降；"
               "环境分级即污染分级。",
     "engineering": "工程落法：按污染等级定 IP 与三防（protec:humidity-ingress 同源）。",
     "standards": ["IEC 60721", "GB/T 2423"]},
    {"id": "ecology", "name": "生态", "gist": "生物与其环境的相互关系的网络。",
     "detail": "食物链/种群动态/生态位；设备退役与材料流动对局部生态有影响；生态网络与"
               "netsys 组网在「节点-链路-冗余」结构上可互文。",
     "engineering": "工程落法：冗余拓扑抗单点失效（netsys:meshnet 互文；protec:redundancy）。",
     "standards": ["ISO 14040"]},
    {"id": "sustainability", "name": "可持续", "gist": "满足当代而不损后代的发展约束。",
     "detail": "能源/材料/全生命周期视角；与降额延寿、可维护同构——延长设备寿命即减碳减废。",
     "engineering": "工程落法：延寿（降额/可维护）即可持续（protec:derating/maintainability）。",
     "standards": ["ISO 14040"]},
]

# ------------------------- 轴5 物理（3） ------------------------- #
PHYSICS = [
    {"id": "electromagnetism", "name": "电磁", "gist": "电与磁统一于麦克斯韦方程组。",
     "detail": "库仑/高斯/安培/法拉第-麦克斯韦；电磁波以光速传播；电生磁、磁生电是电机、"
               "变压器与无线的基础，也是 protec 电气安全的物理底座。",
     "engineering": "工程落法：EMC/接地/屏蔽（protec:grounding-rcd 同源）。",
     "standards": ["IEC 61000"]},
    {"id": "quantum-physics", "name": "量子", "gist": "微观粒子的叠加/纠缠/离散测度。",
     "detail": "波函数/测不准/量子比特；量子测度的离散性与「可证伪」在方法论上同构；"
               "是 quantum 概念系统的科学底座。",
     "engineering": "工程落法：可测即可控（quantum:measurement 同构；protec:monitoring）。",
     "standards": []},
    {"id": "mechanics", "name": "力学", "gist": "力与运动的牛顿/连续介质框架。",
     "detail": "静力/动力/振动/强度；应力集中是疲劳与蠕变的诱发源；振动环境是设备"
               "寿命的关键工况。",
     "engineering": "工程落法：避应力集中、抗振设计（protec:fatigue/creep 同源）。",
     "standards": ["GB/T 3075"]},
]

# ------------------------- 轴6 化学（3） ------------------------- #
CHEMISTRY = [
    {"id": "electrochemistry", "name": "电化学", "gist": "化学能与电能经氧化还原反应互换。",
     "detail": "电极电势/能斯特方程；原电池（电偶腐蚀）、电解、电池充放电皆属此；是腐蚀、"
               "接地漏电流与电池衰减的化学本体。",
     "engineering": "工程落法：异种金属隔离、限漏电流、电池管理（protec:galvanic-corrosion/"
                    "grounding-rcd/battery_degradation 同源）。",
     "standards": ["IEC 62619", "GB/T 31485"]},
    {"id": "reaction-kinetics", "name": "反应动力学", "gist": "反应速率随浓度/温度/催化剂变化。",
     "detail": "阿伦尼乌斯定律（温度每升 10K 速率约翻倍）是热老化/蠕变的定量核心；活化能"
               "决定寿命模型。",
     "engineering": "工程落法：按动力学定寿命模型与维护周期（protec:thermal-aging/derating）。",
     "standards": []},
    {"id": "periodic-table", "name": "元素周期", "gist": "元素性质随原子序数周期性变化。",
     "detail": "电负性/电极电势/活泼性周期律；选材与防电偶腐蚀的底层依据——电位差大者"
               "不宜直接搭接。",
     "engineering": "工程落法：按周期律选异种金属配对（protec:material-selection/"
                    "galvanic-corrosion 同源）。",
     "standards": []},
]

# ------------------------- 轴7 生物（4） ------------------------- #
BIOLOGY = [
    {"id": "cell", "name": "细胞", "gist": "生命的基本结构与功能单元。",
     "detail": "细胞膜/代谢/分裂；细胞的「界面屏障」与设备 enclosure 在隔离原理上可互文；"
               "稳态（homeostasis）与设备热稳态同构。",
     "engineering": "工程落法：界面隔离 + 稳态控制（protec:enclosure/monitoring 互文）。",
     "standards": []},
    {"id": "evolution", "name": "进化", "gist": "种群经变异-选择-遗传的适应性改变。",
     "detail": "自然选择塑造适应；系统经「变异-筛选」的演化与编译/构建的迭代同源（comp:make）。",
     "engineering": "工程落法：迭代筛选式构建与回归（comp:make 翻译）。",
     "standards": []},
    {"id": "genetics", "name": "基因", "gist": "遗传信息的存储与表达。",
     "detail": "DNA 编码/转录/翻译；信息编码与接口契约（schema）在「结构即信息」上同构"
               "（apilab:json-schema）。",
     "engineering": "工程落法：契约即编码、向后兼容（apilab:json-schema 翻译）。",
     "standards": []},
    {"id": "biosphere", "name": "生物圈", "gist": "地球全部生命与其环境的耦合系统。",
     "detail": "盖亚假说视地球为自调节整体——与 netsys 盖亚意识/集智体、大同「人类一体」"
               "在「整体自组织」上互文。",
     "engineering": "工程落法：系统作为自调节整体、跨端同口径（netsys/sysmesh；protec:monitoring）。",
     "standards": []},
]

# ------------------------- 轴8 科学方法原则（7，= principles） ------------------------- #
METHODOLOGY = [
    {"id": "falsifiability", "name": "可证伪", "gist": "一个主张须能被观测证伪才算科学。",
     "detail": "波普尔判据：不可证伪的命题（如纯诗化表达）不属科学断言；工程上对应「先列"
               "不可（白名单）再论可行」，与量子纠错缓解同构。",
     "engineering": "工程落法：先定红线/禁区再谈可用（quantum:mitigation 同构；protec:enclosure）。",
     "canon_refs": []},
    {"id": "reproducibility", "name": "可重复", "gist": "实验须在他人处可独立重现。",
     "detail": "可重复是可信任的前提；工程上对应「定时构建/巡检可复现」——每日自检如日礼。",
     "engineering": "工程落法：定时构建/检查可复现（comp:make 翻译；protec:maintainability）。",
     "canon_refs": []},
    {"id": "controlled-experiment", "name": "对照", "gist": "设对照组隔离变量以确证因果。",
     "detail": "对照/随机/盲法是确证因果的支柱；工程上对应 A/B 与故障注入对照，避免把相关当因果。",
     "engineering": "工程落法：变更前后对照、故障注入对照（protec:monitoring 同源）。",
     "canon_refs": []},
    {"id": "abductive-reasoning", "name": "溯因", "gist": "由现象反推最省解释（最佳说明推理）。",
     "detail": "皮尔士三推理之一；根因分析即溯因；与百工「锦囊策略」的谋定而后动同源。",
     "engineering": "工程落法：根因分析/故障定位（baigong:jinnang-celue 翻译；protec:monitoring）。",
     "canon_refs": []},
    {"id": "quantification", "name": "定量", "gist": "以可测数值表达，避免模糊断言。",
     "detail": "定量使结论可比较可验证；接口契约（schema）把语义定量为结构，与 JSON Schema 同源。",
     "engineering": "工程落法：契约定量、schema 即测度（apilab:json-schema 翻译；protec:monitoring）。",
     "canon_refs": []},
    {"id": "peer-review", "name": "同行评审", "gist": "结论须经独立同行批判验证。",
     "detail": "评审是纠错的集体机制；与百工「精审明辩」的工前审验同源——不可说者不说、可言者说清。",
     "engineering": "工程落法：变更评审/代码评审（baigong:jingshen-mingbian 翻译；protec:enclosure）。",
     "canon_refs": []},
    {"id": "uncertainty", "name": "不确定度", "gist": "任何测量都有误差，须声明置信区间。",
     "detail": "不确定度论要求诚实标注精度；应急定位 ETA 须给置信下限（floor）而非虚假高精度，"
               "与「中道取中」同源。",
     "engineering": "工程落法：定位/预测给置信下限、不报虚假精度（protec:locate-fuse；datong:zhongdao-rong）。",
     "canon_refs": []},
]

# ------------------------- 桥接边（构建期校验无悬空） ------------------------- #
BRIDGES = [
    # 各学科 → protec（科学底座 → 工程保护）
    {"from": "corrosion", "system": "protec", "target": "concept:corrosion", "relation": "同源",
     "how": "材料学腐蚀 = protec 腐蚀：同一电化学失效，科学侧解释、工程侧防护"},
    {"from": "fatigue", "system": "protec", "target": "concept:fatigue", "relation": "同源",
     "how": "材料学疲劳 = protec 疲劳：机理同源"},
    {"from": "creep", "system": "protec", "target": "concept:creep", "relation": "同源",
     "how": "材料学蠕变 = protec 蠕变：高温慢变形同源"},
    {"from": "thermo-laws", "system": "protec", "target": "concept:thermal-aging",
     "relation": "翻译", "how": "热力学第二定律（不可逆）→ protec 热老化：散热裕度即对抗熵增"},
    {"from": "heat-transfer", "system": "protec", "target": "concept:contact-heating",
     "relation": "翻译", "how": "接触热阻（界面温升）→ protec 接触高阻发热：同属界面热失控"},
    {"from": "electrochemistry", "system": "protec", "target": "concept:galvanic-corrosion",
     "relation": "翻译", "how": "电化学原电池 → protec 电偶腐蚀：异种金属电位差"},
    {"from": "electrochemistry", "system": "protec", "target": "concept:grounding-rcd",
     "relation": "翻译", "how": "电化学漏电流 → protec 接地/RCD：毫安级漏电流防护"},
    {"from": "greenhouse", "system": "protec", "target": "concept:ashrae-thermal",
     "relation": "翻译", "how": "温室增温 → protec ASHRAE 温控：室外气候定进风包络"},
    {"from": "carbon-cycle", "system": "protec", "target": "concept:iec60721-class",
     "relation": "翻译", "how": "碳/化学基线 → protec IEC 60721 环境分类"},
    {"from": "pollution", "system": "protec", "target": "concept:humidity-ingress",
     "relation": "翻译", "how": "盐雾/硫化物污染 → protec 湿气侵入：三防与 IP 对抗"},
    # 科学方法原则 → 既有概念系统
    {"from": "falsifiability", "system": "quantum", "target": "concept:mitigation",
     "relation": "同构", "how": "可证伪（先列不可）→ 量子纠错缓解：先列不可再论可行"},
    {"from": "reproducibility", "system": "comp", "target": "concept:make",
     "relation": "翻译", "how": "可重复实验 → 定时构建/巡检可复现（每日自检如日礼）"},
    {"from": "abductive-reasoning", "system": "baigong", "target": "principle:jinnang-celue",
     "relation": "翻译", "how": "溯因根因分析 ↔ 锦囊策略：谋定而后动"},
    {"from": "quantification", "system": "apilab", "target": "concept:json-schema",
     "relation": "翻译", "how": "定量（数值化）→ JSON Schema：契约即测度"},
    {"from": "peer-review", "system": "baigong", "target": "principle:jingshen-mingbian",
     "relation": "翻译", "how": "同行评审 ↔ 精审明辩：工前审验、不可说者不说"},
    {"from": "uncertainty", "system": "datong", "target": "concept:zhongdao-rong",
     "relation": "翻译", "how": "不确定度（给置信区间）→ 中道取中：不报虚假精度"},
    {"from": "evolution", "system": "comp", "target": "concept:pipeline-overview",
     "relation": "翻译", "how": "变异-选择演化 ↔ 构建-回归迭代：筛选式演进"},
    {"from": "ecology", "system": "netsys", "target": "module:meshnet",
     "relation": "互文", "how": "生态网络（节点-链路-冗余）↔ meshnet：抗单点失效"},
]


NEEDS_VERIFY = [
    {"item": "标准编号与最新版次", "status": "通行口径登记",
     "note": "IEC/ASHRAE/ISO/GB 等编号按通行口径登记，未逐条核对最新版次"},
    {"item": "温室效应与设备温控映射", "status": "结构性翻译",
     "note": "将全球温室效应翻译为设备 ASHRAE 温控约束，非气候学等效断言"},
    {"item": "量子-可证伪同构", "status": "比较框架自定",
     "note": "可测度与可证伪仅作结构同构登记，物理/科学内涵各自独立"},
]


def live_user_face() -> dict:
    """构建期实测（与 build_protec.py 同一口径，不硬编码）。"""
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
        "lang_note": "语言面：plang 161 条语言（其中 probe 实测 15 种）；--check 与磁盘登记值逐键比对",
        "concept_systems": 11,
    }


def build():
    bridges = [
        {"from": f"sciences:{b['from']}", "system": b["system"], "target": b["target"],
         "relation": b["relation"], "how": b["how"]}
        for b in BRIDGES
    ]
    concepts = _concepts()
    for c in concepts:
        c.setdefault("standards", [])
        c.setdefault("bridges", [])
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/sciences/build_sciences.py",
            "main_root": "wordbuddy-github",
            "title": "sciences 概念系统（材料/热/气候/环境/物理/化学/生物·科学方法，以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": VERSION,
            "canon": "七门自然科学 + 科学方法：材料/热/气候/环境/物理/化学/生物为 protec 工程保护的"
                     "科学底座，方法论七原则（可证伪/可重复/对照/溯因/定量/同行评审/不确定度）"
                     "为 protec 保护原则的科学依据",
            "axes": ["materials", "thermodynamics", "climatology", "environmental",
                     "physics", "chemistry", "biology", "methodology"],
            "concept_total": len(concepts),
            "principle_total": len(METHODOLOGY),
            "bridge_count": len(bridges),
            "honesty": "只读登记、科学表述按通行口径、不臆造实测数字；桥接只作科学原理 ↔ 工程保护/"
                       "编译/量子/网络/工程伦理的结构翻译，不宣称等同；未核对原典/版次者统一挂"
                       "needs_verify；应急定位 ETA 按置信下限诚实标注（v0.6.67）",
            "redline_note": "科学先于工程：先列不可（白名单）再论可行；不确定度诚实标注；"
                            "可重复/可证伪是可信前提；错误提示必给下一步",
        },
        "layers": [
            {"role": "materials", "domain": "materials", "tier": 1, "count": len(MATERIALS),
             "canon": "材料学", "sense": "腐蚀/相变/疲劳/蠕变 4 条"},
            {"role": "thermodynamics", "domain": "thermodynamics", "tier": 1, "count": len(THERMO),
             "canon": "热力学", "sense": "定律/热传导/熵/相平衡 4 条"},
            {"role": "climatology", "domain": "climatology", "tier": 1, "count": len(CLIMATOLOGY),
             "canon": "气候学", "sense": "温室效应/洋流/ENSO/碳循环 4 条"},
            {"role": "environmental", "domain": "environmental", "tier": 1, "count": len(ENVIRONMENTAL),
             "canon": "环境学", "sense": "污染/生态/可持续 3 条"},
            {"role": "physics", "domain": "physics", "tier": 1, "count": len(PHYSICS),
             "canon": "物理", "sense": "电磁/量子/力学 3 条"},
            {"role": "chemistry", "domain": "chemistry", "tier": 1, "count": len(CHEMISTRY),
             "canon": "化学", "sense": "电化学/反应动力学/元素周期 3 条"},
            {"role": "biology", "domain": "biology", "tier": 1, "count": len(BIOLOGY),
             "canon": "生物", "sense": "细胞/进化/基因/生物圈 4 条"},
            {"role": "methodology", "domain": "methodology", "tier": 2, "count": len(METHODOLOGY),
             "canon": "科学方法", "sense": "可证伪/可重复/对照/溯因/定量/同行评审/不确定度 7 条（= principles）"},
        ],
        "domains": DOMAINS,
        "concepts": concepts,
        "by_domain": by_domain,
        "principles": [
            {"id": p["id"], "name": p["name"], "gist": p["gist"],
             "engineering": p["engineering"], "canon_refs": p["canon_refs"]}
            for p in METHODOLOGY
        ],
        "bridges": bridges,
        "needs_verify": list(NEEDS_VERIFY),
        "user_face_facts": live_user_face(),
    }
    return doc


def _concepts():
    out = []
    for t in MATERIALS:
        out.append(_mk(t, "materials"))
    for t in THERMO:
        out.append(_mk(t, "thermodynamics"))
    for t in CLIMATOLOGY:
        out.append(_mk(t, "climatology"))
    for t in ENVIRONMENTAL:
        out.append(_mk(t, "environmental"))
    for t in PHYSICS:
        out.append(_mk(t, "physics"))
    for t in CHEMISTRY:
        out.append(_mk(t, "chemistry"))
    for t in BIOLOGY:
        out.append(_mk(t, "biology"))
    for p in METHODOLOGY:
        out.append({"id": p["id"], "domain": "methodology", "name": p["name"],
                    "gist": p["gist"], "detail": p.get("detail", ""),
                    "engineering": p["engineering"], "standards": [],
                    "canon_refs": p["canon_refs"]})
    return out


def _mk(t: dict, domain: str) -> dict:
    return {"id": t["id"], "domain": domain, "name": t["name"], "gist": t["gist"],
            "detail": t["detail"], "engineering": t["engineering"],
            "standards": t.get("standards", []), "canon_refs": t.get("canon_refs", [])}


def _target_ids(name: str, doc: dict) -> Optional[set]:
    """返回某既有概念系统的可桥接目标 id 全集。"""
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
    if name == "protec":
        return {c["id"] for c in doc.get("concepts", [])}
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
    mt_ids = sorted(c["id"] for c in doc["concepts"] if c["domain"] == "methodology")
    if pc_ids != mt_ids:
        errs.append(f"methodology 概念与 principles 不一致：{set(pc_ids) ^ set(mt_ids)}")

    known = {c["id"] for c in doc["concepts"]}
    for c in doc["concepts"]:
        for r in c.get("canon_refs", []):
            if r not in known:
                errs.append(f"canon_ref 悬空：{c['id']} → {r}")

    cache: Dict[str, Optional[set]] = {}

    def load_other(name: str) -> dict:
        return json.loads((DATA_DIR / f"{name}_taxonomy.json").read_text(encoding="utf-8"))

    for b in doc["bridges"]:
        fkind, _, fval = b["from"].partition(":")
        if fkind != "sciences" or fval not in ids:
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
        print(f"    {d['domain']:<13} {len(by.get(d['domain'], [])):>2} 条  {d['label']}——{d['note']}")
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
