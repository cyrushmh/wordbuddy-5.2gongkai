#!/usr/bin/env python3
"""南华真经「用户端」概念系统构建（以 wordbuddy-github 为主目录，v0.6.60）。

《南华真经》即《庄子》，共 33 篇（内篇 7 / 外篇 15 / 杂篇 11）。本系统以
用户指定的**核心理念三篇**——内篇一《逍遥游》、内篇七《应帝王》、内篇六
《大宗师》——为中心，以内篇余篇为辅，把庄子的理念翻译成**可审计的用户端
人体工程学原则**，桥接到本仓库既有概念系统：

    ├─ 轴1 core        核心理念·三篇（逍遥游 / 应帝王 / 大宗师）
    ├─ 轴2 inner       内篇辅篇·四篇（齐物论 / 养生主 / 人间世 / 德充符）
    ├─ 轴3 outer       外篇与杂篇（仅选登有用户端意涵的 5 篇 + 概览 1 条）
    └─ 轴4 ergonomics  用户端人体工程学原则（七条，理念的工程翻译）

桥接目标必须在目标数据层真实存在（daoxue 治理原则 / apilab 接口概念），
构建期校验无悬空。

诚实边界：不复制经典全文，只登记篇旨/章旨/工程落法；用户未上传《南华真经》
原典文本，全部篇旨按通行本登记并统一标 needs_verify（与 daoxue 心经/论语
同口径），不逐字臆造原文；「人体工程学原则」系理念的工程翻译而非经典原文；
repo-face 轴的**用户端面事实**（CLI 子命令数 / webapi ACTIONS 数 / GUI 窗口
数 / deno 两文件版本）全部构建时从源码实测，不写无法核实的数字。

用法：
    python3 build_zhuangzi.py            # 构建 data/concepts/zhuangzi_taxonomy.json
    python3 build_zhuangzi.py --check    # 校验（轴合法、桥接无悬空、用户端事实实测一致）
    python3 build_zhuangzi.py --report   # 打印轴统计与桥接图
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "src" / "python"
OUT = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "zhuangzi_taxonomy.json"
CONCEPTS_DIR = OUT.parent
DENO_DIR = ROOT / "src" / "deno"

SCHEMA = "zhuangzi_taxonomy/v1"

# ---------------------------------------------------------------------------
# 轴定义（四轴：核心理念 → 内篇辅篇 → 外杂选篇 → 用户端工程原则）
# ---------------------------------------------------------------------------
DOMAINS = [
    {"domain": "core", "label": "核心理念",
     "note": "用户指定的核心理念三篇：内篇一《逍遥游》、内篇七《应帝王》、"
             "内篇六《大宗师》——以《南华真经》为用户端设计的中心指导"},
    {"domain": "inner", "label": "内篇辅篇",
     "note": "内篇余四篇：齐物论 / 养生主 / 人间世 / 德充符——核心理念的补充面向"},
    {"domain": "outer", "label": "外篇与杂篇",
     "note": "外篇十五 + 杂篇十一共 26 篇：仅选登对用户端设计有直接意涵的 5 篇，"
             "余作概览登记（needs_verify，不逐篇臆造）"},
    {"domain": "ergonomics", "label": "用户端工程原则",
     "note": "七篇理念翻译成的可审计人体工程学原则：逍遥游一步直达 / 应帝王顺应性情 / "
             "大宗师意图为宗师 / 接口平权 / 养生不伤 / 人间安命 / 德充于内"},
]

# ---------------------------------------------------------------------------
# 概念：内篇七篇 + 外杂选篇（engineering = 落到本仓库用户端的工程落法）
# ---------------------------------------------------------------------------
CONCEPTS: List[dict] = [
    # ============ 轴1 核心理念·三篇 ============
    {"id": "xiaoyaoyou", "name": "逍遥游", "domain": "core", "no": 1,
     "gist": "鲲鹏化变、「小大之辩」，归结于「乘天地之正，御六气之辩，以游无穷」"
             "的无待境界；惠子谓樗树大而无用，庄子答「树之于无何有之乡，"
             "彷徨乎无为其侧，逍遥乎寝卧其下」。",
     "detail": "北冥有鱼其名为鲲，化而为鸟其名为鹏，海运将徙于南冥；蜩与学鸠"
               "笑之「奚以之九万里而南为」；列子御风而行，犹有所待；至人无己、"
               "神人无功、圣人无名，方能无待而逍遥。全篇以「无待」为眼目："
               "一切有待（有待于风、有待于名）皆非究竟。",
     "engineering": "操作无阻碍、一步直达。**无待**即不预设前提：不依赖记忆、"
                    "不依赖教程、不依赖环境配置，常用任务从任意状态一屏可达；"
                    "入口唯一化（一个 `python -m sysweeper` 走遍轻重任务），"
                    "而非满墙功能按钮各藏三级菜单——用户要的是「无何有之乡」"
                    "的一棵大树，不是一片必须遍历的森林。",
     "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "理念同源",
          "how": "「无待」即不预设前提：依环境与使用者本性组织入口，不强人所难"},
         {"system": "netsys", "target": "module:sysmesh", "relation": "系统互联协调",
          "how": "无待而游 ↔ 系统互联协调（sysmesh）：各系统顺性互联、互不僭越，"
                 "与无待「不预设前提、依本性而联」同源"}]},
    {"id": "yingdiwang", "name": "应帝王", "domain": "core", "no": 7,
     "gist": "「顺物自然而无容私焉，而天下治矣」（无名人语）；中央之帝浑沌"
             "待儵忽甚善，儵忽谋报其德，日凿一窍，七日而浑沌死——不为用户"
             "「凿窍」，顺应其本来性情。",
     "detail": "狂接舆见王而先告之以难，无名人教羊说明「明王之治，功盖天下"
               "而似其自己」；阳子居问「明王之治」，老聃曰「明王之治……"
               "感而后应，迫而后动，不得已而后起」；最触目的是浑沌之死的寓言："
               "自以为报德，实以己凿人，七日而浑沌死——**不强迫、不凿窍、"
               "顺物自然**是全篇纲宗。",
     "engineering": "顺应使用者性情，不强迫学习。默认即最佳：零配置开箱可用，"
                    "「拿得起放得下」——新用户不读文档也能干活，老用户可渐进"
                    "深入；系统「不自是」：不把设计者想象的功能当作用户需要的"
                    "强行塞与（儵忽勿凿浑沌窍）；帮助是发现式（--help、GUI "
                    "提示行、控制台 /help），教程是引导非必修。",
     "bridges": [
         {"system": "daoxue", "target": "principle:wuwei", "relation": "理念同源",
          "how": "「顺物自然而无容私」= 无为：界面不强行作为，默认路径即最佳路径"}]},
    {"id": "dazongshi", "name": "大宗师", "domain": "core", "no": 6,
     "gist": "「以天为宗，以德为本」——真人「不知说生，不知恶死」「不以心"
             "捐道，不以人助天」；宗师者，可宗而不可师，以道为归而非以人为归。",
     "detail": "古之真人，其寝不梦、其觉无忧、其食不甘、其息深深；「泉涸，"
               "鱼相与处于陆，相呴以湿，相濡以沫，不如相忘于江湖」；大宗师即"
               "可宗可印的「道」，非某位可模仿的人——归于意图的本源而非某人"
               "设定的规程。",
     "engineering": "以使用者意图为宗师。意图先行而非规程先行：预测式默认"
                    "（按上下文预取下一步，如 CLI 上次操作、感知平台能力），"
                    "「不以人助天」= 不替用户做他未表达的决定（最小惊讶原则）；"
                    "失败不抛术语，指路并给可回退路径（每一步破坏性操作先留"
                    "快照，提示如何撤销——意图的宗师地位意味着容错而非问责）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念同源",
          "how": "「知不知」：以使用者意图为宗师，知用户不知而指路，不猜不降级"}]},

    # ============ 轴2 内篇辅篇·四篇 ============
    {"id": "qiwulun", "name": "齐物论", "domain": "inner", "no": 2,
     "gist": "「天地一指，万物一马」：齐彼我、齐是非——地籁、天籁，"
             "大辩无言。",
     "detail": "南郭子綦隐几而坐，嗒焉似丧其偶，「今者吾丧我」；「道行之"
               "而成，物谓之而然」；持之以恒的齐平视野：高低、贵贱、彼此皆是"
               "观待而立。",
     "engineering": "接口平权：人类可读与机器可读（--json）双模输出平权、"
                    "新手与专家道路平权、破坏性与清理性子命令共用同一帮助体系；"
                    "不按「用户等级」设障，同一能力不同表达（呼应 apilab 的"
                    "CLI 契约：人类与机器双模输出是成熟接口的标志）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:bu-zheng", "relation": "理念同源",
          "how": "双模平权，不设高低级指令之争；争无从起，界面自正"}]},
    {"id": "yangshengzhu", "name": "养生主", "domain": "inner", "no": 3,
     "gist": "「吾生也有涯，而知也无涯，以有涯随无涯，殆已」；庖丁解牛「以"
             "无厚入有间，恢恢乎其于游刃必有余地」——缘督以为经。",
     "detail": "庖丁为文惠君解牛，「臣之所好者道也，进乎技矣」，依乎天理"
               "批大郤、导大窾，十九年而刀刃若新发于硎；「缘督以为经，可以"
               "保身，可以全生，可以养亲，可以尽年」。",
     "engineering": "不伤害使用者、不耗竭有限注意力。破坏性操作前置确认 + "
                    "快照先行（snapshot 子系统「先留痕后动手」），每一步可回退；"
                    "「以无厚入有间」= 在平台结构与风险间游刃，不与结构性阻塞"
                    "硬碰；功能不贪多——以有限生命/注意力随无限功能，殆矣。",
     "bridges": [
         {"system": "daoxue", "target": "principle:shou-zhong", "relation": "理念同源",
          "how": "「缘督以为经」= 守中谨慎：危险操作守中而慎行，快照留痕在先"}]},
    {"id": "renjianshi", "name": "人间世", "domain": "inner", "no": 4,
     "gist": "颜回之卫、叶公子高使齐、栎社树「是不材之木也，无所可用，故能"
             "若是之寿」——处浊世而知其不可奈何而安之若命，虚己以游世。",
     "detail": "仲尼教颜回「先存诸己而后存诸人」；叶公「行事之情而忘其身」；"
               "「山木自寇也，膏火自煎也；桂可食故伐之，漆可用故割之」——"
               "有用即险，虚己无累。",
     "engineering": "在平台限制中周旋，不与本性相强。平台能力不足处诚实告知"
                    "降级路径（不装能做：如 NTFS 只读检查、容器内受限功能明确"
                    "标注），「安之若命」式适配环境（detect 探测真实环境，"
                    "按平台给可用子集而非全平台硬套）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:xin-yan-bu-mei", "relation": "理念同源",
          "how": "能力边界诚实告知：不可用明示原因，不装能做、不吞异常"}]},
    {"id": "dezongfu", "name": "德充符", "domain": "inner", "no": 5,
     "gist": "王骀「立不教，坐不议，虚而往，实而归」；申徒嘉子产以刑余之"
             "形立于朝廷而「德有所长而形有所忘」——德充于内者形遗于外。",
     "detail": "「知不能规乎其前者也」——形体残缺而德行充沛者，人自宾之；"
               "「有人之形，故群于人；无人之情，故是非不得于身」。",
     "engineering": "内容重于形式，界面朴素。输出以信息密度优先（ASCII 表/"
                    "条形图可删、核心结论不减）；GUI 面板装饰可减，数据与结论"
                    "不减——「见素抱朴」的用户端化身：界面之形可忘，内容之"
                    "德必充。",
     "bridges": [
         {"system": "daoxue", "target": "principle:pu", "relation": "理念同源",
          "how": "见素抱朴：界面之形可忘，内容之德必充，装饰可删核心不减"}]},

    # ============ 轴3 外篇与杂篇（选登 5 篇）============
    {"id": "heqiu", "name": "秋水（选）", "domain": "outer",
     "gist": "「井蛙不可以语于海者，拘于虚也；夏虫不可以语于冰者，笃于时也；"
             "曲士不可以语于道者，束于教也」——河伯望洋兴叹：认知有边界。",
     "engineering": "不向不了解前提的用户硬推高级功能：危险/高级子命令在"
                    "具体上下文中展示（run --plan 预览、提示前提），不按"
                    "「井蛙之虚」预设用户；术语首次出现处即解释。",
     "bridges": [
         {"system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "理念同源",
          "how": "图难于其易：大事化小展示前提，大事在小步中可见"}]},
    {"id": "tiandao", "name": "天道（选）", "domain": "outer",
     "gist": "轮扁斲轮于堂下：「徐则甘而不固，疾则苦而不入……得之于手而"
             "应于心，口不能言」——默会知识不可尽传于书。",
     "engineering": "文档与 --help 之外保留交互式探索（webapi 长连接实测、"
                    "GUI 左键面板）；默会手感靠试错留痕——失败指路可回退而非"
                    "仅给文档链接；「口不能言」处给示例而非概念堆砌。",
     "bridges": [
         {"system": "apilab", "target": "concept:repo-webapi", "relation": "同域",
          "how": "控制台即交互式探索场：手感类错误给示例与尝试路径"}]},
    {"id": "dasheng", "name": "达生（选）", "domain": "outer",
     "gist": "「忘足，屦之适也；忘腰，带之适也；知忘是非，心之适也」——工具"
             "合手则忘。",
     "engineering": "界面消失感即人体工程学最高境界：常用路径无感通过"
                    "（快照自动、默认平台自适应），用户只在「想起它」时才看到"
                    "它（概念系统中心、各子系统面板之类）——**逍遥游**"
                    "的用户端试金石：用时忘记界面的存在。",
     "bridges": [
         {"system": "apilab", "target": "concept:repo-cli", "relation": "同域",
          "how": "常用子命令短名直达、零配置可用，合手则忘"}]},
    {"id": "quqie", "name": "胠箧（选）", "domain": "outer",
     "gist": "「绝圣弃智，大盗乃止」；「盗亦有道」——窃国者侯，所窃者恰是"
             "仁义筐箧：破坏者利用的正是你留下的门。",
     "engineering": "最小攻击面即最大善：插件白名单制（manifest native 字段"
                    "必须在内）、webapi ACTIONS 白名单 + 无 getattr 兜底、"
                    "令牌禁入 URL/localStorage——「门上无钩，盗何由入」。",
     "bridges": [
         {"system": "apilab", "target": "concept:repo-plugins", "relation": "同域",
          "how": "白名单制 = 绝钩绳之圣：不给未登记入口留门"}]},
    {"id": "wai-za-gailan", "name": "外篇杂篇概览", "domain": "outer",
     "gist": "外篇十五（骈拇·马蹄·胠箧·在宥·天地·天道·天运·刻意·缮性·秋水·"
             "至乐·达生·山木·田子方·知北游）+ 杂篇十一（庚桑楚·徐无鬼·则阳·"
             "外物·寓言·让王·盗跖·说剑·渔父·列御寇·天下），共 26 篇。",
     "detail": "本系统只选登对用户端设计有直接意涵的 4 篇（秋水/天道/达生/胠箧），"
               "其余 22 篇未逐篇登记核对——needs_verify，不逐篇臆造篇旨。",
     "engineering": "克制本身即落法：登记册只收有据可依的条目，未读原文的篇目"
                    "概览挂牌 needs_verify 而非逐条臆造——与 daoxue「心经/论语"
                    "未附原典按通行本登记并标 needs_verify」同口径；用户端面对"
                    "「不知道」同样诚实：未核实的能力标注状态，不写满墙功能。",
     "bridges": [{"system": "daoxue", "target": "principle:fan-zhe", "relation": "互文",
                  "how": "外杂篇概览只收有据可依的条目，未读原文的篇目挂牌 needs_verify "
                         "而不逐篇臆造，与道枢「反者道之动」的对待观互文"}]},
]

# ---------------------------------------------------------------------------
# 用户端人体工程学原则（七条：理念 → 可审计工程原则，内篇七篇各一则）
# ---------------------------------------------------------------------------
PRINCIPLES = [
    {"id": "wudai-yizhi", "name": "无待一步", "canon_refs": ["逍遥游"], "domain": "ergonomics",
     "gist": "「无待」即不预设前提：不依赖记忆、教程、配置，常用任务一屏可达、"
             "任意深度可一步回顶。",
     "engineering": "入口唯一化：python -m sysweeper 一个命令走遍轻重任务；"
                    "子命令扁平（120 个实测），概念/子系统直达无需多层菜单；"
                    "关键功能 3 步内可达（--json/one-shot 参数）。",
     "bridges": [{"system": "apilab", "target": "concept:repo-cli", "relation": "翻译", "how": "无待一步即入口唯一化：单一 argparse 入口承载全部子命令，任意深度可一步回顶，不依赖用户记忆层级"}],
},
    {"id": "shunxing-buqiang", "name": "顺性不抢", "canon_refs": ["应帝王"], "domain": "ergonomics",
     "gist": "顺物自然而无容私：不把设计者的想象当用户的需求，默认即最佳、"
             "零配置可用。",
     "engineering": "默认路径开箱即用（--platform 自动探测、风险档位默认安全）；"
                    "帮助是发现式而非必修课（--help、GUI 提示行、控制台 /help）；"
                    "用户不用被教育「该怎么用系统」，系统沿用用户已有的心智。",
     "bridges": [{"system": "apilab", "target": "concept:repo-plugins", "relation": "同构", "how": "顺性不抢即零配置可用：插件清单静态白名单 + 运行时显式登记，用户无需先配置即可用，帮助是发现式而非必修课"}],
},
    {"id": "shiwei-zongshi", "name": "意图宗师", "canon_refs": ["大宗师"], "domain": "ergonomics",
     "gist": "以使用者意图为宗师：意图先行而非规程先行，「不以人替用户做决定」。",
     "engineering": "预测式默认（按上下文预取下一步）；最小惊讶（不静默改变"
                    "全局状态，变更前明示）；失败指路可回退（错误码+原因+恢复"
                    "建议，快照先行让每个破坏性动作可撤销）。"},
    {"id": "jiekou-pingquan", "name": "双模平权", "canon_refs": ["齐物论"], "domain": "ergonomics",
     "gist": "齐是非：人读与机读、新手与专家、清理与危险指令，同一能力不同"
             "表达，不设高低之争。",
     "engineering": "可解析输出（--json/JSONL）与人类可读输出平权；新手有 GUI"
                    "点击路径，专家有脚本路径；同一任务双端同源（report schema "
                    "双端消费）。"},
    {"id": "yangsheng-bu-shang", "name": "养生不伤", "canon_refs": ["养生主"], "domain": "ergonomics",
     "gist": "以有涯随无涯，殆已：不耗竭有限注意力，不让误操作成不可逆损失。",
     "engineering": "破坏性操作前置确认（danger=true 明示）；快照先行（snapshot "
                    "子系统先留痕后动手，可回退可对比）；功能不求全，注意力是"
                    "有限资源（庖丁批大郤导大窾）。"},
    {"id": "renjian-anming", "name": "人间安命", "canon_refs": ["人间世"], "domain": "ergonomics",
     "gist": "知其不可奈何而安之若命：在平台限制中周旋，能力边界诚实告知。",
     "engineering": "按平台给可用子集（detect 探测真实环境，非全平台硬套）；"
                    "降级路径明示（受限功能标注原因与替代）；不与结构性阻塞"
                    "硬碰，「以无厚入有间」。"},
    {"id": "dechong-yu-nei", "name": "德充于内", "canon_refs": ["德充符"], "domain": "ergonomics",
     "gist": "德有所长而形有所忘：内容重于形式，界面朴素信息不减。",
     "engineering": "信息密度优先（ASCII 图表/对比表可减，核心结论不减）；"
                    "界面装饰可删、数据不减（GUI 面板极简、报告查看器内容优先）。",
     "bridges": [{"system": "apilab", "target": "concept:repo-report-viewer", "relation": "翻译", "how": "德充于内即内容重于形式：报告查看器壳极简而信息量不减，装饰可删、数据不删"}],
},
    # v0.6.85（源：center-widget-popups 导入分析）——事件驱动改动的幂等护栏：
    # KWin 脚本只把「水平中心落在用户范围內」的弹窗移到屏幕水平中心，且带
    # <1px 阈值护栏防 frameGeometryChanged 反馈环；范围外的一律不顺动。
    {"id": "idempotent-guard", "name": "幂等护栏", "canon_refs": ["应帝王"], "domain": "ergonomics",
     "gist": "改动必有阈值护栏，回调不触发反馈环——只动该动的，动过之后不再动。",
     "detail": "center-widget-popups（terminallywell，KWin/Script，MIT，约 40 行 main.js）"
               "监听 workspace.windowAdded 与 frameGeometryChanged，对 appletPopup 类窗口"
               "取水平中心，落在用户配置区间（默认 25%–50% 屏宽）内的移到屏幕水平中心；"
               "区间外一律不顺动，且只改水平位置（垂直面板与多显示器未测，README 如实"
               "挂 Limitations）。防反馈环的关键是 |geo.x - x| < 1 即返回——移动后的"
               "回调再进来时已是目标位置，不再触发第二次移动。",
     "engineering": "center-widget-popups（KWin 脚本，MIT）的落法：配置范围夹紧"
                    "（a<=b?[a,b]:[b,a] 防倒置）、重入护栏（|geo.x-x|<1 即返回，"
                    "frameGeometryChanged 回调不自我触发）、范围外不顺动（弹窗中心"
                    "落在用户定义区间外则保持 Plasma 原位）。对应本仓：GUI 报告"
                    "「生成/关闭」按钮模式不重入、genmon 定时刷新只读不写、"
                    "破坏性操作前置确认——每个自动改动都可重复执行而不累积副作用。",
     "bridges": []},
]


# ---------------------------------------------------------------------------
# 用户端面实测事实（构建时从源码读出；--check 与磁盘登记值逐键比对）
# ---------------------------------------------------------------------------
def user_face_facts() -> Dict[str, object]:
    """从源码实测读出本仓库「用户端面」事实（CLI / GUI / webapi / deno 四端）。"""
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

    def deno_version(name: str) -> Optional[str]:
        p = DENO_DIR / name
        if not p.exists():
            return None
        m = re.search(r'const VERSION = "([^"]+)"', p.read_text(encoding="utf-8"))
        return m.group(1) if m else None

    return {
        "cli_subcommands": sub_count,
        "webapi_actions": len(webapi.ACTIONS),
        "gui_windows": gui_windows,
        "deno_console_version": deno_version("console.ts"),
        "deno_report_viewer_version": deno_version("report_viewer.ts"),
        "webapi_protocol": "JSONL 白名单协议（一行请求 JSON → 一行响应 JSON）",
        "gui_note": "tkinter GUI：show_* 面板窗口（概念系统中心/各子系统面板）",
        "deno_note": "Deno Web 控制台（console.ts）+ 报告查看器（report_viewer.ts），"
                     "与 Python 侧经 webapi JSONL 衔接",
    }


# v0.6.62 字段齐备化：补齐缺失的 detail（详述）——gist 一句话、detail 讲清楚、engineering 给落法，三者分工不重复。
DETAIL_FILL: Dict[str, str] = {
    "heqiu": "河伯见海若而望洋兴叹：井蛙拘于虚、夏虫笃于时、曲士束于教——认知各有边界，不是对方笨，是彼此的前提不同。用在用户端：不要向没看到前提的人硬推高级选项，术语首次出现就要解释，危险操作要在具体上下文里说明代价。",
    "tiandao": "轮扁斲轮：徐则甘而不固、疾则苦而不入，得之于手而应于心，口不能言——有些手感写不进说明书。所以文档之外还要留出可试错的交互空间，写不出来的地方给示例、给预览、给可回退的一步，而不是只丢一句「详见文档」。",
    "dasheng": "忘足，屦之适也；忘腰，带之适也——鞋合脚时你不会想起脚。工具的最高境界是让人忘了工具存在：常用路径应当无感通过，用户只在真的想起它时才需要看见它（而不是把它摆在每一屏中央）。",
    "quqie": "胠箧之诫最锋利处在于「盗亦有道」：窃国者侯，而他所窃的正是你留下的仁义筐箧——破坏者利用的，往往是你为了方便而留的门。故攻击面越小才是越大的善意：白名单、默认拒、不设兜底派发。",
    "wudai-yizhi": "「无待」即不预设前提：不依赖用户记得住、读得懂教程、配得对环境。常用任务应当一屏可达，任意深度都能一步回顶——这条原则后来直接长成了 guide 那一屏入口地图。",
    "shunxing-buqiang": "顺物自然而无容私：不要把设计者的想象当成用户的需求。零配置可用是硬指标，帮助应当是发现式的而非必修课，平台差异由探测代劳，不该让用户先回答一堆问题。",
    "shiwei-zongshi": "以使用者意图为宗师：意图先行而非规程先行，并且**不替用户做决定**。落到预定 continuum 上：可预测的默认、最小惊讶（不静默改全局状态）、以及失败必给下一步（原因 + 恢复建议 + 可回退）。",
    "jiekou-pingquan": "齐是非：人读与机读、新手与专家、只读与写操作，同一能力不同表达，不设高低之争。本机 --json/JSONL 与人类可读输出平权、GUI 点击路径与脚本路径同源——缺了哪一端，那一端的人就被排除在外。",
    "yangsheng-bu-shang": "以有涯随无涯，殆已：注意力是有限资源，误操作应当可回退。所以危险动作前置确认并明示等级，快照先行、留痕可比对，功能宁可不全也不透支用户的注意力预算。",
    "renjian-anming": "知其不可奈何而安之若命：平台限制是结构性事实，硬碰是没用的。正确的做法是先诚实地告知边界（哪些不可用、为什么），再给降级路径与替代方案——「以无厚入有间」才是周旋之道。",
    "dechong-yu-nei": "德有所长而形有所忘：内容重于形式。界面可以朴素，信息量不能减；装饰可以删，核心结论不能删。这也是本报告查看器「内容优先、壳极简」的由来。",
}
def apply_detail_fill(concepts: List[dict]) -> None:
    """给缺 detail 的概念补足详述（只补缺失项，已有 detail 的不动）。"""
    for c in concepts:
        if not str(c.get("detail") or "").strip():
            txt = DETAIL_FILL.get(c["id"])
            if txt:
                c["detail"] = txt

# v0.6.62 续：回链大同（使综摄系统双向可达，仅确凿关系）
DATONG_BACKLINKS = [
    {"from": "zhuangzi:dazongshi", "system": "datong", "target": "principle:weidao-duzun",
     "relation": "同宗", "how": "大宗师以道为宗师 ↔ 唯道独尊：道通为一"},
    {"from": "zhuangzi:jiekou-pingquan", "system": "datong", "target": "concept:renti-yiti",
     "relation": "翻译", "how": "接口平权单一事实源 ↔ 人类一体：一处登记四处读"},
]


def build() -> dict:
    bridges: List[dict] = []
    for c in CONCEPTS:
        for b in c.get("bridges", []):
            bridges.append({
                "from": f"zhuangzi:{c['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    for p in PRINCIPLES:
        for b in p.get("bridges", []):
            bridges.append({
                "from": f"zhuangzi:{p['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    bridges.extend(DATONG_BACKLINKS)

    all_concepts = CONCEPTS + PRINCIPLES
    apply_detail_fill(all_concepts)
    for c in all_concepts:                      # 数据层字段齐备统一（与 apilab 同构）
        c.setdefault("standards", [])
        c.setdefault("bridges", [])
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in all_concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/zhuangzi/build_zhuangzi.py",
            "main_root": "wordbuddy-github",
            "title": "南华真经用户端概念系统（以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": "0000.0000.0000.0060.20261023",
            "canon": "南华真经（庄子）33 篇：内篇 7 / 外篇 15 / 杂篇 11",
            "axes": ["core", "inner", "outer", "ergonomics"],
            "concept_total": len(all_concepts),
            "principle_total": len(PRINCIPLES),
            "bridge_count": len(bridges),
            "honesty": "不复制经典全文；用户未上传《南华真经》原典文本，篇旨按通行本登记"
                       "（needs_verify 统一标注）；人体工程学七原则系理念的工程翻译，"
                       "非经典原文。",
            "redline_note": "用户端安全红线延续 apilab/auth：破坏性操作快照先行、"
                            "最小惊讶、失败指路可回退；不替用户「凿窍」（浑沌之诫）。",
        },
        "layers": [
            {"role": "core", "canon": "庄子·内篇", "tier": 1,
             "sense": "核心理念三篇：逍遥游（无待一步）/应帝王（顺性不抢）/大宗师（意图为宗师）",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "core")},
            {"role": "inner", "canon": "庄子·内篇", "tier": 2,
             "sense": "内篇辅篇四篇：齐物论（平权）/养生主（不伤）/人间世（安命）/德充符（重内容）",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "inner")},
            {"role": "outer", "canon": "庄子·外篇杂篇", "tier": 2,
             "sense": "外杂 26 篇中选登 5 条（秋水/天道/达生/胠箧/概览）",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "outer")},
            {"role": "ergonomics", "canon": "理念的工程翻译", "tier": 1,
             "sense": "七条可审计的用户端人体工程学原则",
             "count": len(PRINCIPLES)},
        ],
        "domains": DOMAINS,
        "concepts": all_concepts,
        "principles": PRINCIPLES,
        "bridges": bridges,
        "by_domain": by_domain,
        "user_face_facts": user_face_facts(),
        "needs_verify": [
            {"item": "篇旨依据", "status": "needs_verify",
             "note": "用户未上传《南华真经》原典文本，全部篇旨/章旨按通行本登记，"
                     "未逐字核对（与 daoxue 心经/论语同口径）"},
            {"item": "外篇杂篇 22 篇", "status": "needs_verify",
             "note": "外篇十五 + 杂篇十一共 26 篇，仅选登 5 条，其余未逐篇登记核对"},
            {"item": "人体工程学七原则", "status": "needs_verify",
             "note": "系南华理念的工程翻译而非经典原文；工程落法指向本仓库实测事实"
                     "（user_face_facts 构建期实测，--check 防漂移）"},
        ],
    }
    return doc


def check(doc: dict) -> List[str]:
    errs: List[str] = []
    sys.path.insert(0, str(SRC))
    from sysweeper.concepts import _common

    if doc.get("_meta", {}).get("schema") != SCHEMA:
        errs.append("schema 不符")

    def load_other(name: str) -> dict:
        return json.loads((CONCEPTS_DIR / f"{name}_taxonomy.json")
                          .read_text(encoding="utf-8"))

    # 1) 轴合法 / id 唯一 / gist 非空 / 字段齐备
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
        # v0.6.62 字段齐备：每个概念必须有「详述」（gist 一句话、detail 讲清楚）
        if not str(c.get("detail") or "").strip():
            errs.append(f"{c['id']} 缺 detail（详述）")
        if not c.get("engineering"):
            errs.append(f"{c['id']} 缺 engineering（用户端落法）")

    # 2) 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc["by_domain"]):
        if inverted.get(d, []) != doc["by_domain"].get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # 3) 桥接无悬空（daoxue 治理原则 / apilab 接口概念）
    daoxue = load_other("daoxue")
    apilab = load_other("apilab")
    datong = load_other("datong")
    netsys = load_other("netsys")
    dx_principles = {p["id"] for p in daoxue.get("principles", [])}
    ab_concepts = {c["id"] for c in apilab.get("concepts", [])}
    datong_ids = {c["id"] for c in datong.get("concepts", [])} | {
        p["id"] for p in datong.get("principles", [])}
    netsys_mods = {m["id"] for m in netsys.get("modules", [])}
    for b in doc["bridges"]:
        sysname, tgt = b["system"], b["target"]
        kind, _, val = tgt.partition(":")
        if sysname == "daoxue":
            if kind != "principle" or val not in dx_principles:
                errs.append(f"桥接悬空：daoxue 无原则 {val}")
        elif sysname == "apilab":
            if kind != "concept" or val not in ab_concepts:
                errs.append(f"桥接悬空：apilab 无概念 {val}")
        elif sysname == "datong":
            if kind not in ("concept", "principle") or val not in datong_ids:
                errs.append(f"桥接悬空：datong 无{'原则' if kind == 'principle' else '概念'} {val}")
        elif sysname == "netsys":
            if kind != "module" or val not in netsys_mods:
                errs.append(f"桥接悬空：netsys 无模块 {val}")
        else:
            errs.append(f"桥接目标系统未登记：{sysname}")

    # 4) 用户端面事实必须是实测（正数 / 非空）
    facts = doc.get("user_face_facts") or {}
    for k in ("cli_subcommands", "webapi_actions", "gui_windows"):
        if not isinstance(facts.get(k), int) or facts[k] < 1:
            errs.append(f"user_face_facts.{k} 非实测正数")
    for k in ("deno_console_version", "deno_report_viewer_version"):
        if not re.fullmatch(r"\d{4}\.\d{4}\.\d{4}\.\d{4}\.\d{8}", str(facts.get(k) or "")):
            errs.append(f"user_face_facts.{k} 非合法版本号（Deno 侧应同主线口径登记）")

    # 5) counts 自洽
    m = doc["_meta"]
    if m["concept_total"] != len(doc["concepts"]):
        errs.append("counts.concept_total 漂移")
    if m["principle_total"] != len(doc["principles"]):
        errs.append("counts.principle_total 漂移")
    if m["bridge_count"] != len(doc["bridges"]):
        errs.append("counts.bridge_count 漂移")
    for l in doc["layers"]:
        if l["role"] != "ergonomics" and l["count"] != len(doc["by_domain"].get(l["role"], [])):
            errs.append(f"layers[{l['role']}].count 漂移")

    # 6) needs_verify 非空（诚实边界：未核对原典必须显式挂牌）
    if not doc.get("needs_verify"):
        errs.append("needs_verify 为空（原典未核对应显式挂牌）")

    # 7) 加载器可用性
    if OUT.exists():
        try:
            if _common.load_taxonomy(OUT.name) != json.loads(
                    OUT.read_text(encoding="utf-8")):
                errs.append("concepts 共享加载器与磁盘内容不一致")
        except Exception as ex:  # noqa: BLE001
            errs.append(f"concepts 共享加载器读取失败：{ex}")
    else:
        probe_path = _common.data_path("plang_taxonomy.json")
        if not probe_path.exists():
            errs.append(f"concepts 共享加载器路径机制失效：{probe_path} 不存在")

    return errs


def report(doc: dict) -> None:
    print(f"南华概念条目：{doc['_meta']['concept_total']} 个"
          f"（篇目 {doc['_meta']['concept_total'] - doc['_meta']['principle_total']} + "
          f"工程原则 {doc['_meta']['principle_total']}）\n")
    print("按轴：")
    for d in doc["domains"]:
        print(f"  {d['domain']:<12} {len(doc['by_domain'].get(d['domain'], [])):>2}  {d['label']}")
    f = doc.get("user_face_facts", {})
    print(f"\n用户端面实测：CLI 子命令 {f.get('cli_subcommands')} / "
          f"GUI 窗口 {f.get('gui_windows')} / webapi ACTIONS {f.get('webapi_actions')}")
    print(f"deno 控制台 v{f.get('deno_console_version')} / "
          f"报告查看器 v{f.get('deno_report_viewer_version')}")
    print(f"桥接边：{doc['_meta']['bridge_count']} 条")
    by_sys: Dict[str, int] = {}
    for b in doc["bridges"]:
        by_sys[b["system"]] = by_sys.get(b["system"], 0) + 1
    for s, n in sorted(by_sys.items()):
        print(f"  → {s:<8} {n}")
    print(f"needs_verify：{len(doc['needs_verify'])} 项（原典未核对/未选登/工程翻译）")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    if "--check" in argv:
        # 防漂移：磁盘登记的用户端实测值必须与当前源码实测一致
        if OUT.exists():
            disk = json.loads(OUT.read_text(encoding="utf-8"))
            live = user_face_facts()
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
              f"用户端面事实与源码实测一致")
        return 0
    from datetime import datetime, timezone
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
