#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「大同」概念系统构建（v0.6.62，第九概念系统，datong）。

立意（用户原话）：「人类命运是一个的，古今中外的宗教哲学都融合进来，
这才是人类文明文化生活」，「一体两面，三位一体，主的神恩如狱，
还有萨满巫觋等」；并修正：「虽然人类是一体的，但是想要人类健康科学
有序的发展，还是要宣扬天罡元阳、地煞元阴的正道，类似科学的，把固
液气、电磁波，这六样是正道」。

本系统（datong）把古今中外宗教哲学的**命题面**融为一体，与 daoxue
（治理理念面）构成「理—用」两面；并以「正道六象」——固、液、气、
电、磁、波——为自然底座，按天罡元阳（气·电·波，外发）／地煞元阴
（固·液·磁，内聚）正名登记（本系统约定，非物理学分类），每象带
科学口径、跨传统通名与工程落法：

    ├─ 轴1 traditions  文明传统 15 条（儒/道/佛/基督/伊斯兰/犹太/印度/
    │                    耆那/锡克/琐罗亚斯德/希腊/神道/萨满巫觋/古埃及两河/巴哈伊）
    ├─ 轴2 theses      核心命题 20 条（一体两面/三位一体/神恩如狱/黄金法则/
    │                    和而不同/绝地天通/因果业报/轮回解脱/道成肉身/中道/无为/
    │                    空性/慈悲/宇宙公民/四海皆兄弟/虔敬/静默冥想/净化禁忌/命运自由）
    ├─ 轴3 six         正道六象 6 条（固/液/气/电/磁/波——类科学的自然正道）
    ├─ 轴4 practices   实践形态 12 条（祷告/禅定/萨满出神/朝觐/节期安息/诵经持咒/
    │                    斋戒/苦行/洗礼圣餐/告解/占卜/驱邪净坛）
    └─ 轴5 ethics      人间落法九原则（命题 → 可审计工程原则，= principles）

桥接目标在既有八个概念系统中必须真实存在（daoxue principles /
zhuangzi concepts+principles / baigong concepts+principles / plang
concepts / comp concepts / quantum concepts / netsys modules / apilab
concepts），构建期校验无悬空。user_face 为构建期实测：datong 接线后
CLI 子命令 106→107、GUI 窗口 90→91，由 --check 逐键比对防漂移。

诚实边界：只读登记、不宣扬任何宗教为真理、不复制经典全文、引文按
通行本登记；一体两面/三位一体等跨传统条目只作**结构同构**登记
（神学内涵各自不同，显式说明）；元阳元阴六象之分属为本系统的
正名约定（科学口径按物理学登记）；神恩如狱为用户诗化表达，按恩典
论/前定论/业力观作学术口径登记并作喻解。凡未核对原典/年代有争议
/词源存疑者，统一挂 needs_verify，不臆造。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "python"
DATA_DIR = ROOT / "src/python/sysweeper/data/concepts"
OUT = DATA_DIR / "datong_taxonomy.json"
DENO_DIR = ROOT / "src" / "deno"

VERSION = "0000.0000.0000.0062.20261023"
SCHEMA = "datong_taxonomy/v1"

AXIS_LABELS = {
    "traditions": "文明传统",
    "theses": "核心命题",
    "six": "正道六象",
    "practices": "实践形态",
    "ethics": "人间落法",
}

DOMAINS = [
    {"domain": "traditions", "label": "文明传统", "note": "古今中外 15 传统，一传统一条目，不复制经典全文"},
    {"domain": "theses", "label": "核心命题", "note": "跨传统命题 21 条，同构非同质（唯道独尊为宗）"},
    {"domain": "six", "label": "正道六象", "note": "固/液/气/电/磁/波：天罡元阳（气电波·外发）/ 地煞元阴（固液磁·内聚）"},
    {"domain": "practices", "label": "实践形态", "note": "宗教哲学的文化生活实践 12 条"},
    {"domain": "ethics", "label": "人间落法", "note": "九条可审计工程原则（= principles）"},
]

# ------------------------- 轴1 文明传统（15） ------------------------- #
TRADITIONS = [
    {"id": "rujia", "name": "儒", "gist": "仁义礼智信，仁者爱人；修身齐家治国平天下。",
     "detail": "六经为典（诗/书/礼/乐/易/春秋），四书为阶（大学/中庸/论语/孟子）。"
               "「己所不欲，勿施于人」（论语·卫灵公）；「大道之行也，天下为公」"
               "（礼记·礼运大同篇）；慎终追远，礼以别异，乐以和同。",
     "engineering": "工程落法：五常 → 五条可审计红线（诚信日志/无害删除/守中容量/"
                    "信言不美（如实报错）/知不知（未知标 needs_verify））。"},
    {"id": "daojia", "name": "道", "gist": "道法自然，无为而无不为；上善若水，柔弱胜刚强。",
     "detail": "道德经「道可道，非常道」「人法地，地法天，天法道，道法自然」；"
               "庄子「一庄生梦蝶」；元气论以气为化生之媒——与正道六象之「气」相通。",
     "engineering": "工程落法：无为 → 配置默认化不代用户作选择；弱界面 → API 最小面。"},
    {"id": "fojiao", "name": "佛", "gist": "四圣谛、八正道、缘起性空；三法印：诸行无常、诸法无我、涅槃寂静。",
     "detail": "苦集灭道；戒定慧；三身（法身/报身/化身）——与三位一体作结构同构登记"
               "（内涵不同）；汉传八宗、南传巴利三藏、藏传显密并存。",
     "engineering": "工程落法：无常 → 一切状态可弃可重建（不可变基础设施）；无我 → 服务无状态化。"},
    {"id": "jidujiao", "name": "基督", "gist": "三位一体、神恩如狱、因信称义；爱神爱人如己。",
     "detail": "旧约新约；尼西亚信经（325）确立圣父圣子圣灵一体三位；奥古斯丁"
               "《忏悔录》与加尔文预定论见恩典的主权面向——临及不由人择，如狱之"
               "不可出入（系统按学术口径作此喻解；「神恩如狱」为用户诗化表达）；"
               "黄金法则的正面形式：「你们愿意人怎样待你们，你们也要怎样待人」"
               "（马太福音 7:12）。",
     "engineering": "工程落法：恩典如狱 → 安全红线零豁免、无一处特权后门（零信任）。"},
    {"id": "yisilan", "name": "伊斯兰", "gist": "认主独一（tawhid），真主仁慈；五功六信，前定与自由意志并存。",
     "detail": "古兰经 114 章，圣训为辅；五功（念/礼/斋/课/朝）；六信（真主/天使/"
               "经典/使者/后世/前定 qadar）——前定观与神恩如狱、业力不失作命题同构；"
               "「凭恩典与公正」：慈悯与公义并举。",
     "engineering": "工程落法：五功式例行 → 每日定时健康自检（体检/巡检）不扰正常业务。"},
    {"id": "youtai", "name": "犹太", "gist": "一神立约，谨守诫命；修理世界（tikkun olam）。",
     "detail": "妥拉（摩西五经）+ 塔木德；613 条诫命可逐条审计；安息日停工使人得息；"
               "亚伯拉罕之约与弥赛亚盼望。",
     "engineering": "工程落法：诫命清单化 → 每条红线独立成项、逐条可查（类比合规清单）。"},
    {"id": "yindu", "name": "印度", "gist": "梵我合一；三相神创造/护持/毁灭；业轮回解脱四目标。",
     "detail": "四吠陀、奥义书「我即梵」（aham brahāsmi）；三相神（梵天/毗湿奴/"
               "湿婆）与三位一体作结构同构登记（神学内涵不同）；业（karma）法"
               "（dharma）轮回（samsara）解脱（moksha）；两大史诗与薄伽梵歌。",
     "engineering": "工程落法：三相 → 构建三阶段（编译/运行/回收）分工同构登记。"},
    {"id": "qinna", "name": "耆那", "gist": "不害（ahimta）第一；正信正知正行；苦行节欲。",
     "detail": "大雄为二十四祖之末；天衣派（裸行）与白衣派两派；极端不害——"
               " filters 滤水、扫地扫路径，护生及微。",
     "engineering": "工程落法：不害 → 一切破坏性操作二次确认 + 白名单触达。"},
    {"id": "xike", "name": "锡克", "gist": "一神之下人人平等；劳动/分享/铭记三柱。",
     "detail": "那纳克上师开宗，十位上师，第十代后将《阿底格兰特》立为永存上师；"
               "谒师所四门向四方敞开，平等食堂不分种姓信仰共食。",
     "engineering": "工程落法：四门敞开 → 接口公开文档化；共食 → 公共资源配额公平。"},
    {"id": "suoluo", "name": "琐罗亚斯德", "gist": "善恶二元（阿胡拉·马兹达 vs 安格拉·曼纽），火为神圣象征。",
     "detail": "阿维斯陀（含伽萨）；法拉瓦哈；火庙；末世清算后善终胜恶。"
               "生卒与教期年代学界有约公元前 1500—前 600 区间诸说（needs_verify）。",
     "engineering": "工程落法：二元 → 输入输出两面审计（脏输入防线 + 输出合规）。"},
    {"id": "xila", "name": "希腊", "gist": "逻各斯与理性；太一流溢；宇宙城邦；中庸与不动心。",
     "detail": "赫拉克利特「人不能两次踏入同一条河流」（logos）；柏拉图理念与洞穴；"
               "亚里士多德四因 + 中庸 + 第一推动者；斯多亚「宇宙城邦」「不动心」；"
               "普罗提诺太一流溢——与一体两面之「一」呼应。",
     "engineering": "工程落法：中庸 → 容量/时延取中而非极端；流溢 → 单一内核多前端。"},
    {"id": "shendao", "name": "神道", "gist": "八百万神，万物有灵；净（harae）以除秽（kegare）。",
     "detail": "记纪（古事记/日本书纪）；伊势神宫式年迁宫；神社鸟居为界线；"
               "洁净与感恩为中心的生活礼。",
     "engineering": "工程落法：净 → 沙箱隔离与重置（每轮构建全新环境）。"},
    {"id": "saman", "name": "萨满巫觋", "gist": "出神（ecstasy）灵旅三界，鼓声为途；巫觋通天地。",
     "detail": "shaman/saman 词源通古斯语说为主流，学界有争议（needs_verify）；"
               "三界宇宙轴（axis mundi 世界树/天柱）；伊利亚德《萨满教：古代的"
               "迷魂技术》为学术参照；中国先秦巫觋见《国语·楚语下》绝地天通"
               "（颛顼命重黎中断人神杂糅）、楚辞《九歌》；藏地苯教、蒙古博、"
               "西伯利亚诸族、萨米、美洲原住民灵旅并存。",
     "engineering": "工程落法：出神 → 调试态沙箱巡游；绝地天通 → 特权通道分层收口。"},
    {"id": "gudai", "name": "古埃及两河", "gist": "玛特（maat，真理/秩序）对抗伊瑟菲特（乱）；占卜问兆。",
     "detail": "亡灵书与称心称量；《吉尔伽美什》追问生死与洪水；汉谟拉比法典"
               "以牙还牙同态复仇；肝卜（liver omen）与星兆为决策传统。",
     "engineering": "工程落法：秩序 → 一切事务落账可查（账本式审计日志）。"},
    {"id": "bahai", "name": "巴哈伊", "gist": "人类一体（大同主命题）；宗教同源渐进启示；独立寻求真理。",
     "detail": "巴哈欧拉 19 世纪立教；摒弃教士阶层；灵曦堂向一切信仰敞开；"
               "「地球乃一国，人类皆其民」为最直接的「人类命运是一个的」之经典表述。",
     "engineering": "工程落法：一体 → 单一事实源（single source of truth）跨端一致。"},
]

# ------------------------- 轴2 核心命题（20） ------------------------- #
THESES = [
    {"id": "renti-yiti", "name": "人类一体", "gist": "人类命运是一个的。",
     "detail": "巴哈伊「人类一体」，礼记大同「天下为公」，斯多亚宇宙城邦皆主人"
               "翁——差别是枝叶，一体是根干。",
     "engineering": "工程落法：单一事实源 + 跨端同口径（CLI/webapi/GUI/deno 一处登记四处读）。",
     "traditions": ["bahai", "rujia", "xila"]},
    {"id": "yiti-liangmian", "name": "一体两面", "gist": "一而不二，两面相成。",
     "detail": "阴阳互根（易/道）；玛特与伊瑟菲特（埃及）；阿胡拉与安格拉（琐罗亚"
               "斯德）；诺斯替灵与质二元；电场与磁场之电磁一体两面（科学侧最直白"
               "的同构：电生磁、磁生电，电磁本一）。",
     "engineering": "工程落法：每一功能面配对称风险面（读/写/删三面各配审计面）。",
     "traditions": ["daojia", "suoluo", "gudai", "xila"]},
    {"id": "sanwei-yiti", "name": "三位一体", "gist": "一位三分，三而一，一而三。",
     "detail": "尼西亚信经 325：圣父/圣子/圣灵一体三位；同构登记（非等同）：印度"
               "三相神创造/护持/毁灭、佛教三身法身/报身/化身——结构同形，神学内"
               "涵各自不同，不可混同（needs_verify：同构为系统自定的比较框架）。",
     "engineering": "工程落法：一契三端（CLI/webapi/GUI 三分一体共用同一契约——"
                    "契约即信经，三端即三位）。",
     "traditions": ["jidujiao", "yindu", "fojiao"]},
    {"id": "shenen-ruyu", "name": "神恩如狱", "gist": "恩典/法则临及，不由人择，不可出入。",
     "detail": "「神恩如狱」为用户诗化表达；学术口径：奥古斯丁恩典论、加尔文预定"
               "论见恩典之主权——临及不由人择，如狱墙不可跃出亦不可拒入；伊斯兰前定"
               "（qadar）、佛教业力不失为其跨传统同构。",
     "engineering": "工程落法：红线即狱墙——安全红线不挑对象、无一处后门（零信任）。",
     "traditions": ["jidujiao", "yisilan", "fojiao"]},
    {"id": "huangjin-faze", "name": "黄金法则", "gist": "己所不欲，勿施于人（负面式）；愿人怎样待你，你就怎样待人（正面式）。",
     "detail": "论语·卫灵公（负面形式）；马太福音 7:12（正面形式）；相同或相近"
               "表述见于世界百余传统的通行本研究（数量为概说，needs_verify）。",
     "engineering": "工程落法：契约对称——调用方与实现方义务对称，接口文档即黄金法则。",
     "traditions": ["rujia", "jidujiao", "youtai", "yisilan"]},
    {"id": "heer-butong", "name": "和而不同", "gist": "君子和而不同，小人同而不和。",
     "detail": "论语·子路；一体不是抹平差异——人类一体而文明多样，如五味调和"
               "而非一味独尊。",
     "engineering": "工程落法：多版本契约并存共荣（向后兼容 + 渐进废弃）。",
     "traditions": ["rujia", "bahai"]},
    {"id": "juedi-tiantong", "name": "绝地天通", "gist": "天地各有其分，通灵之权收于一。",
     "detail": "国语·楚语下：观射父述颛顼命重（南正重司天以属神）黎（火正黎司地"
               "以属民）「绝地天通」——人神杂糅之世终结，祭祀之权分层收口。",
     "engineering": "工程落法：特权分层——日常低权运行，非常之务走唯一提升通道（守御 opt-in）。",
     "traditions": ["rujia", "saman", "gudai"]},
    {"id": "yinguo-yebao", "name": "因果业报", "gist": "种因得果，业力不失。",
     "detail": "佛教十二因缘；印度业（karma）不随形灭；民间「不是不报时候未到」"
               "——与工程侧的幂等可溯同构：每个动作都留痕、每个状态都有出处。",
     "engineering": "工程落法：因果链可复盘（请求 ID 贯穿 + 结构化日志）。",
     "traditions": ["fojiao", "yindu", "daojia"]},
    {"id": "lunhui-jietuo", "name": "轮回与解脱", "gist": "轮转不息，解脱有门。",
     "detail": "印度轮回（samsara）与解脱（moksha）四目标（法/利/欲/解脱）；佛教"
               "涅槃寂静；「无常故可重生」——与可弃可重建的基础设施同构。",
     "engineering": "工程落法：服务无状态化，随时重建（分分钟杀死重建而不中断服务）。",
     "traditions": ["yindu", "fojiao"]},
    {"id": "daocheng-roushen", "name": "道成肉身", "gist": "无限者取有限形，自上而下降而为人。",
     "detail": "基督教「道成肉身」（约翰福音 1:14）；同构登记：印度化身（avatara，"
               "如毗湿奴十化）——下降临在一格，内涵各自不同。",
     "engineering": "工程落法：高层概念须落到可执行的最小形态（一个主义 → 一个可跑的最小样例）。",
     "traditions": ["jidujiao", "yindu"]},
    {"id": "zhongdao", "name": "中道", "gist": "离两边，行乎中。",
     "detail": "佛教中道（苦乐二边）；亚里士多德中庸（过度/不及之间）；孔子中庸"
               "「过犹不及」——三重同构，皆拒极端。",
     "engineering": "工程落法：容量/时延/日志级别取中，配置给默认值而非极值。",
     "traditions": ["fojiao", "xila", "rujia"]},
    {"id": "wuwei", "name": "无为", "gist": "不妄作，顺势成。",
     "detail": "道德经「无为而无以为」；禅宗「平常心是道」；斯多亚「顺应自然」"
               "——不逆势强为，非不作为。",
     "engineering": "工程落法：默认配置优于默认行为；自动化优先于人工介入。",
     "traditions": ["daojia", "fojiao", "xila"]},
    {"id": "kongxing", "name": "空性", "gist": "缘起性空，无自性。",
     "detail": "般若经与《心经》「色不异空，空不异色」（daoxue 系统已收心经，作"
               "跨系统同源登记）；龙树中观八不。",
     "engineering": "工程落法：对象只有关系没有本质（接口优于实现类）。",
     "traditions": ["fojiao"]},
    {"id": "cibei", "name": "慈悲", "gist": "慈予乐，悲拔苦。",
     "detail": "佛教慈悲（karuna）；基督教爱（agape）；儒仁；伊斯兰拉赫曼"
               "（至慈）——诸传统共许的核心德性。",
     "engineering": "工程落法：失败提示须可救济（每条错误给下一步，不只报错）。",
     "traditions": ["fojiao", "jidujiao", "rujia", "yisilan"]},
    {"id": "yuzhou-gongmin", "name": "宇宙公民", "gist": "世界一城邦，人皆其公民。",
     "detail": "斯多亚犬儒第欧根尼「我是世界公民」；斯多亚「宇宙城邦」；与大同"
               "「天下为公」东西对望。",
     "engineering": "工程落法：跨端移植优先（Windows/Linux/macOS 行为同口径）。",
     "traditions": ["xila", "rujia"]},
    {"id": "sihai-jie-xiongdi", "name": "四海皆兄弟", "gist": "四海之内皆兄弟也。",
     "detail": "论语·颜渊；巴哈伊「地球乃一国」；大同「老有所终，壮有所用，"
               "幼有所长，矜寡孤独废疾者皆有所养」。",
     "engineering": "工程落法：公共资源配额公平（无任何用户/任务被歧视性限流）。",
     "traditions": ["rujia", "bahai"]},
    {"id": "qianjing", "name": "虔敬与敬畏", "gist": "有所畏，而后有所守。",
     "detail": " mysterium tremendum（奥托《神圣的观念》「令人颤栗的神秘」）；"
               "儒「祭如在，祭神如神在」；希腊「哲学始于惊异」（thaumazein）；"
               "「敬」如狱之警卫——有所畏故不敢肆意。",
     "engineering": "工程落法：破坏性操作敬畏化（删除/覆写必经确认与留痕）。",
     "traditions": ["jidujiao", "rujia", "xila"]},
    {"id": "jingmo-shenxiu", "name": "静默与冥想", "gist": "万缘放下，静中生明。",
     "detail": "犹太 hitbodedut（独处祷告）；基督教 contemplatio（静观）；禅坐"
               "（zazen）；苏菲 dhikr/寂灭（fana）——各传统共有的静默法门。",
     "engineering": "工程落法：静默模式——降噪运行、日志脱敏、默认不言语。",
     "traditions": ["youtai", "jidujiao", "fojiao", "yisilan"]},
    {"id": "jinghua-jinji", "name": "净化与禁忌", "gist": "有所不履，方能为履。",
     "detail": "神道除秽（harae）；伊斯兰净礼（wudu 小净）；犹太饮食诫命；佛道"
               "斋戒；工程同构：禁忌清单即白名单，先定不做什么。",
     "engineering": "工程落法：白名单制（默认拒，明确许可方行）。",
     "traditions": ["shendao", "yisilan", "youtai", "fojiao", "daojia"]},
    {"id": "mingyun-ziyou", "name": "命运与自由", "gist": "命定之墙内，仍是择义之身。",
     "detail": "希腊 moira（命运三女神）；伊斯兰前定（qadar）；基督教恩典与自由"
               "意志之争（奥古斯丁/伯拉纠）；佛教业力自受——命定与自由的张力是"
               "人类共问。",
     "engineering": "工程落法：约束内最大化选择（沙箱决定边界不决定动作）。",
     "traditions": ["xila", "yisilan", "jidujiao", "fojiao"]},
    {"id": "weidao-duzun", "name": "唯道独尊", "gist": "古来唯道独成尊——万流殊涂同归，道为所宗。",
     "detail": "用户立意「古来唯道独成尊」；典据：《道德经》第二十五章「有物混成，"
               "先天地生……吾不知其名，强字之曰道」、二十一章「孔德之容，惟道是从」；"
               "《庄子·齐物论》「道通为一」；《周易·系辞下》「天下同归而殊涂，一致"
               "而百虑」——诸传统如百川，道为海；此为本系统的立意取向（用户所言），"
               "非对各传统价值高下的学术评判（needs_verify 口径见清单）。",
     "engineering": "工程落法：单一内核（道）·多面前端（殊涂）——一核多端，万变不离其宗"
                    "（本仓库 daoxue 以道德经 81 章为中心即此结构之先例）。",
     "traditions": ["daojia", "rujia", "bahai"]},
]

# ------------------------- 轴3 正道六象（6） ------------------------- #
SIX = [
    {"id": "gu", "name": "固", "gist": "地煞元阴——凝而成体，静而有序。",
     "detail": "科学口径：固体为凝聚相，粒子（原子/离子/分子）按晶格有序排布，"
               "有定形定容（晶体/非晶两族）。跨传统通名：土/地/石/金刚（不动之"
               "体）。工程落法：状态固化——不变式与快照，配置即宪法。",
     "engineering": "工程落法：不可变基础设施（镜像/快照/一次性写入，改动即换版）。"},
    {"id": "ye", "name": "液", "gist": "地煞元阴——流而随形，润物无声。",
     "detail": "科学口径：液体为凝聚流体，有定容无定形，近不可压，表面张力与"
               "黏性两征。跨传统通名：水（上善若水/生命之液）。工程落法：流式"
               "处理与管道——随形而不失其质。",
     "engineering": "工程落法：流处理/队列/管道（背压可控，无一处无限缓冲）。"},
    {"id": "qi", "name": "气", "gist": "天罡元阳——散而弥虚，动而无形。",
     "detail": "科学口径：气体为弥散相，无定形无定容，分子动理论（压强/温度/"
               "体积三律）。跨传统通名：希伯来 ruach、希腊 pneuma、中国气（元气"
               "论）、印度 prana、日本 ki、拉丁 spiritus——万传统共有的「呼吸"
               "之体」。工程落法：事件总线与气压式批量。",
     "engineering": "工程落法：事件驱动/消息总线（轻量事件高扇出，风过无痕）。"},
    {"id": "dian", "name": "电", "gist": "天罡元阳——激而迅发，应时而动。",
     "detail": "科学口径：电荷及其电场（库仑/高斯），电流为电荷定向迁移，电势"
               "差为驱动。跨传统通名：宙斯雷霆、雷部、电母——诸传统皆以「迅而"
               "可惧」象之。工程落法：信号与触发。",
     "engineering": "工程落法：信号/触发/激励（布尔边沿敏感，电平持守）。"},
    {"id": "ci", "name": "磁", "gist": "地煞元阴——引而内聚，定向不移。",
     "detail": "科学口径：磁场与洛伦兹力，磁体两极，同极相斥异极相吸；电生磁、"
               "磁生电——与「电」共为电磁一体两面（麦克斯韦方程组统一之）。"
               "跨传统通名：慈石（吸铁）与指南。工程落法：约束场。",
     "engineering": "工程落法：约束/吸附/寻的（依赖注入磁场，服务被引到位）。"},
    {"id": "bo", "name": "波", "gist": "天罡元阳——播而及远，无远弗届。",
     "detail": "科学口径：电磁波以光速 c 传播（麦克斯韦预言、赫兹验证），波长/"
               "频率连续成谱（无线电/微波/红外/可见光/紫外/X/伽马）。跨传统通名："
               "声（梵 shabda）、光、逻各斯之传。工程落法：传播协议。",
     "engineering": "工程落法：广播/波前/传播协议（版本波前推进，一处发布处处到达）。"},
]

# ------------------------- 轴4 实践形态（12） ------------------------- #
PRACTICES = [
    {"id": "daogao", "name": "祷告", "gist": "向所信者发声，祈请/感恩/忏悔。",
     "detail": "基督主祷文；伊斯兰一日五礼（salat）；犹太每日三祷；皆有时有处"
               "有向（麦加克尔白）。",
     "engineering": "工程落法：健康探测请求——定时定向轻问（不干活先问安）。"},
    {"id": "chanding", "name": "禅定/冥想", "gist": "摄心一处，静观其变。",
     "detail": "佛教禅（dhyana）四禅八定；印度瑜伽八支；苏菲 fikr；现代正念"
               "（MBSR）。",
     "engineering": "工程落法：观测模式——metrics/tracing 只观不扰。"},
    {"id": "saman-chushen", "name": "萨满出神", "gist": "鼓声中意识离体，灵游三界求援。",
     "detail": "伊利亚德所述迷魂技术；鼓（框鼓）与鼓绳为途；寻魂/治病/求雨"
               "三类母题；与「绝地天通」的通灵权收口正相反照。",
     "engineering": "工程落法：调试沙箱巡游——可安全「离体」探查生产镜像。"},
    {"id": "chaojin", "name": "朝觐", "gist": "千里赴一圣所，仪式化的同心。",
     "detail": "伊斯兰麦加朝（hajj，伊历十二月）；印度恒河沐浴与卡姆巴梅拉节；"
               "佛教巡礼四大圣迹。",
     "engineering": "工程落法：周期性汇合——定时向中心事实源对齐（cron 汇合）。"},
    {"id": "jieqi-anxi", "name": "节期与安息", "gist": "以时序锚定共同体记忆。",
     "detail": "犹太安息日（Shabbat，第七日停工）；伊斯兰斋月；基督复活节/圣诞；"
               "春节/中元/盂兰；印度排灯节。",
     "engineering": "工程落法：节期式发布窗口——冻结期/发布期轮换。"},
    {"id": "songjing-zhou", "name": "诵经持咒", "gist": "以声载义，反复入心。",
     "detail": "伊斯兰诵经（tajwid 音韵规则）；佛教持咒/念佛；锡克阿底格兰特"
               "诵唱；吠陀口头传承千年（patha 诵法）。",
     "engineering": "工程落法：声入式巡检——重复结构化日志（同格式同字段可检索）。"},
    {"id": "zhaijie", "name": "斋戒", "gist": "有所不取，以清其身。",
     "detail": "伊斯兰斋月（日出至日日落不食不饮）；佛教八关斋戒；基督大斋期；"
               "耆那极端节食（sallekhana 善终）。",
     "engineering": "工程落法：降级斋戒——资源受限时自动进入低耗模式。"},
    {"id": "kuxing", "name": "苦行", "gist": "以苦炼志，以身证道。",
     "detail": "耆那苦行第一；佛教早期六师苦行（释迦中道批评之）；基督教修道"
               "（沙漠教父）；印度瓦拉吉。",
     "engineering": "工程落法：极限演练——混沌演练/故障注入（平时受苦难时少痛）。"},
    {"id": "xili-shengcan", "name": "洗礼与圣餐", "gist": "入教的门，筵席的约。",
     "detail": "基督洗礼（水礼）与圣餐（饼酒）；伊斯兰无入教礼但有念礼；神道"
               "禊祓。",
     "engineering": "工程落法：服务入网礼（健康检查通过方入池）+ 版本筵席（灰度共食）。"},
    {"id": "gaojie", "name": "告解/忏悔", "gist": "认错留痕，重新做人。",
     "detail": "基督告解（和好圣事）；佛教忏悔（金光明经忏悔品）；犹太赎罪日"
               "（Yom Kippur）。",
     "engineering": "工程落法：事故复盘（postmortem）——对事不对人，改进行动留账。"},
    {"id": "zhanbu", "name": "占卜", "gist": "以兆决疑，借天问人。",
     "detail": "中国龟卜/周易；两河肝卜（liver omen）；罗马鸟占；约鲁巴伊法"
               "占卜（Ifa）；现代随机源决策的远亲（社科院/统计决策）。",
     "engineering": "工程落法：需要随机/探索时用白名单随机源（可复现种子），"
                    "不把不确定交给伪随机黑箱。"},
    {"id": "quxie-jingtan", "name": "驱邪净坛", "gist": "划界以洁，逐不祥于外。",
     "detail": "神道大祓；藏地煨桑/风马；基督驱魔；民间净坛/开坛；与「净化"
               "禁忌」同源。",
     "engineering": "工程落法：沙箱隔离+恶意输入过滤（不洁者不得入内）。"},
]

# ------------------------- 轴5 人间落法原则（9，= principles） ------------------------- #
PRINCIPLES = [
    {"id": "he-butong-yong", "name": "和而不同（兼容多样）", "gist": "一体不是抹平差异；契约多版本并存共荣。",
     "engineering": "API 新旧版本并行，渐进废弃路线显式公示（不搞一刀切断更）。",
     "canon_refs": ["rujia", "bahai"]},
    {"id": "yiti-shuangmian-shen", "name": "一体两面同审", "gist": "一功能面，必配对称风险面。",
     "engineering": "读/写/删/连四类动作各自配对审计面（审计缺失即构建失败）。",
     "canon_refs": ["yiti-liangmian", "daojia"]},
    {"id": "zhongdao-rong", "name": "中道（取中配置）", "gist": "过犹不及；默认给中值而非极值。",
     "engineering": "参数默认值取中位经验值，极值须显式 opt-in 并记录理由。",
     "canon_refs": ["zhongdao", "fojiao", "xila"]},
    {"id": "yinguo-bushuang", "name": "因果不爽（可溯）", "gist": "种因得果，业力不失。",
     "engineering": "请求 ID 贯穿 + 结构化日志；无 ID 的变更不进入生产。",
     "canon_refs": ["yinguo-yebao", "fojiao"]},
    {"id": "huangjin-duichen", "name": "黄金法则（契约对称）", "gist": "愿人怎样待你，你就怎样待人（正面式）。",
     "engineering": "文档与实现对称、入参与返回对称；做不到的承诺不进文档。",
     "canon_refs": ["huangjin-faze", "rujia", "jidujiao"]},
    {"id": "jueji-shouquan", "name": "绝地天通（特权收口）", "gist": "通灵之权不可泛施；非常之务走唯一通道。",
     "engineering": "日常低权；特权提升仅一条显式通道（opt-in + 记因 + 时效）。",
     "canon_refs": ["juedi-tiantong", "saman"]},
    {"id": "cibei-buhai", "name": "慈悲不害（红线）", "gist": "慈予乐，悲拔苦；不害第一。",
     "engineering": "删除/覆写二次确认 + 白名单触达；错误提示必给下一步。",
     "canon_refs": ["cibei", "qinna", "fojiao"]},
    {"id": "yuzhou-yizhi", "name": "宇宙公民（跨端）", "gist": "世界一城邦；跨端同权。",
     "engineering": "Windows/Linux/macOS 行为同口径；平台差异显式登记不隐瞒。",
     "canon_refs": ["yuzhou-gongmin", "xila"]},
    {"id": "jingmo-tuomin", "name": "静默脱敏（克制）", "gist": "静默模式；不可说者不说。",
     "engineering": "日志脱敏（令牌/路径/隐私不落盘）；默认静默， verbose 才多话。",
     "canon_refs": ["jingmo-shenxiu", "youtai", "fojiao"]},
]

# ------------------------- 桥接边（构建期校验无悬空） ------------------------- #
# from 概念 id → 既有八系统目标；relation ∈ 同源/同构/互文/翻译
BRIDGES = [
    # 文明传统 → 八系统（同源/互文/翻译）
    {"from": "rujia", "system": "baigong", "target": "concept:rujiao", "relation": "同源",
     "how": "baigong 三教九流之儒教条目与本系统儒条目同源互见，双处登记不重复定义"},
    {"from": "rujia", "system": "baigong", "target": "concept:rujia", "relation": "同源",
     "how": "九流之儒家落法与儒工程红线映射同源"},
    {"from": "daojia", "system": "baigong", "target": "concept:daojiao", "relation": "同源",
     "how": "道教条目同源互见"},
    {"from": "daojia", "system": "zhuangzi", "target": "concept:xiaoyaoyou", "relation": "同源",
     "how": "庄子为道家第二经典，南华系统已收，本条只引不重述"},
    {"from": "daojia", "system": "daoxue", "target": "principle:daofa-ziran", "relation": "互文",
     "how": "道法自然（daoxue 原则）与本系统自然底座互为表里"},
    {"from": "fojiao", "system": "baigong", "target": "concept:fojiao", "relation": "同源",
     "how": "佛教条目同源互见"},
    {"from": "fojiao", "system": "quantum", "target": "concept:measurement", "relation": "同构",
     "how": "刹那生灭（诸行无常）与量子测度的离散性作结构同构登记（非等同）"},
    {"from": "fojiao", "system": "plang", "target": "lang:rust", "relation": "同构",
     "how": "戒学（不妄取）与 Rust 所有权（不妄取内存）作同构登记"},
    {"from": "jidujiao", "system": "apilab", "target": "concept:auth-redlines", "relation": "翻译",
     "how": "神恩如狱（恩典红线无豁免）→ 认证零信任红线：令牌禁入 URL/Storage、无后门"},
    {"from": "jidujiao", "system": "daoxue", "target": "principle:xin-yan-bu-mei", "relation": "互文",
     "how": "信言不美（如实报错）与爱人如己的契约化互文"},
    {"from": "yisilan", "system": "comp", "target": "concept:make", "relation": "翻译",
     "how": "五功式例行 → 构建/检查目标定时化（每日巡检如日礼）"},
    {"from": "yisilan", "system": "daoxue", "target": "principle:shou-zhong", "relation": "互文",
     "how": "前定与守中——墙内自由之义互文"},
    {"from": "youtai", "system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "翻译",
     "how": "613 诫命清单化 → 图难于其易：大事化小逐条审计"},
    {"from": "yindu", "system": "comp", "target": "concept:pipeline-overview", "relation": "同构",
     "how": "三相神（创造/护持/毁灭）与流水线三阶段（构建/运行/回收）同构登记"},
    {"from": "weidao-duzun", "system": "daoxue", "target": "principle:daofa-ziran", "relation": "同宗",
     "how": "唯道独尊 ↔ 道法自然：daoxue 以道德经 81 章为中心，即「一核多端」结构先例"},
    {"from": "weidao-duzun", "system": "zhuangzi", "target": "concept:dazongshi", "relation": "同宗",
     "how": "道通为一 / 大宗师：真人以道为宗师，本系统以道为诸命题之宗"},
    {"from": "weidao-duzun", "system": "baigong", "target": "concept:sanjiao-jiuliu", "relation": "同宗",
     "how": "九流并蓄·各极其用 ↔ 殊涂同归：百川并蓄而不失其海"},
    {"from": "qinna", "system": "apilab", "target": "concept:auth-redlines", "relation": "翻译",
     "how": "不害第一 → 白名单制触达：默认拒，明确许可方行"},
    {"from": "xike", "system": "apilab", "target": "concept:openapi", "relation": "翻译",
     "how": "谒师所四门敞开 → 接口文档公开可读（四门即四端）"},
    {"from": "suoluo", "system": "comp", "target": "concept:sema", "relation": "同构",
     "how": "善恶二元 → 输入/输出两面语义审计（脏输入防线）"},
    {"from": "xila", "system": "daoxue", "target": "principle:fan-zhe", "relation": "互文",
     "how": "赫拉克利特流变（万物皆流）与反者道之动互文"},
    {"from": "shendao", "system": "comp", "target": "concept:native-build", "relation": "翻译",
     "how": "除秽（harae）→ 每次构建全新沙箱（净而后作）"},
    {"from": "saman", "system": "netsys", "target": "module:emergency", "relation": "互文",
     "how": "通灵之权分层收口（绝地天通）与应急通道守御 opt-in 互文"},
    {"from": "renti-yiti", "system": "netsys", "target": "module:sysmesh", "relation": "互文",
     "how": "人体一体 → 系统互联协调：各系统经组网而联成一体（sysmesh），与大同「一体双面」互文"},
    {"from": "gudai", "system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "翻译",
     "how": "称心称量（一切落账）→ 图难于其易：逐项审计"},
    {"from": "bahai", "system": "zhuangzi", "target": "principle:jiekou-pingquan", "relation": "同构",
     "how": "人类一体 → 接口平权：单一事实源、四端同口径"},
    # 核心命题 → 八系统
    {"from": "renti-yiti", "system": "zhuangzi", "target": "principle:jiekou-pingquan", "relation": "翻译",
     "how": "单一事实源（single source of truth）一处登记四处读"},
    {"from": "yiti-liangmian", "system": "apilab", "target": "concept:json-schema", "relation": "同构",
     "how": "schema 与实例两面：契约与实例相成"},
    {"from": "yiti-liangmian", "system": "quantum", "target": "concept:superposition", "relation": "同构",
     "how": "一体两面 ↔ 叠加两面性（结构同构，神学/物理内涵各自独立）"},
    {"from": "sanwei-yiti", "system": "apilab", "target": "concept:json-schema", "relation": "翻译",
     "how": "一契三端：schema 即信经，CLI/webapi/GUI 即三位（一体三征）"},
    {"from": "shenen-ruyu", "system": "netsys", "target": "module:tls13", "relation": "互文",
     "how": "恩典之墙不可越（信任锚无处不在）↔ 信任链逐级锚定"},
    {"from": "juedi-tiantong", "system": "netsys", "target": "module:emergency", "relation": "翻译",
     "how": "特权分层：日常低权，非常之务唯一提升通道"},
    {"from": "yinguo-yebao", "system": "comp", "target": "concept:pipeline-overview", "relation": "翻译",
     "how": "因果链可复盘：构建阶段产物可逐级追溯到源码"},
    {"from": "kongxing", "system": "comp", "target": "concept:link", "relation": "同构",
     "how": "空性（无自性，唯关系）↔ 动态链接（符号无实体，唯引用关系）"},
    {"from": "cibei", "system": "zhuangzi", "target": "principle:yangsheng-bu-shang", "relation": "翻译",
     "how": "慈悲不害 → 养生不伤：一切交互不伤用户"},
    {"from": "yuzhou-gongmin", "system": "comp", "target": "concept:cmake", "relation": "翻译",
     "how": "宇宙公民（跨平台）→ 构建描述跨平台一次编写处处构建"},
    {"from": "jingmo-shenxiu", "system": "plang", "target": "lang:python", "relation": "互文",
     "how": "静默模式 ↔ Zen of Python「Flat is better than nested」之克制"},
    {"from": "jinghua-jinji", "system": "quantum", "target": "concept:mitigation", "relation": "同构",
     "how": "净化禁忌（白名单制）↔ 量子纠错缓解（先列不可，再论可行）"},
    # 正道六象 → 八系统
    {"from": "gu", "system": "comp", "target": "concept:codegen", "relation": "翻译",
     "how": "固（凝而成体）→ 代码/产物一次性固化（不可变发布物）"},
    {"from": "ye", "system": "netsys", "target": "module:osi", "relation": "翻译",
     "how": "液（随形流动）→ 分层数据流如流体过管（分层即层流）"},
    {"from": "qi", "system": "netsys", "target": "module:meshchat", "relation": "翻译",
     "how": "气（弥散轻事件）→ mesh 消息轻事件高扇出广播"},
    {"from": "dian", "system": "quantum", "target": "concept:superposition", "relation": "互文",
     "how": "电（激发）↔ 量子比特激发——信号与量子信号之互文"},
    {"from": "dian", "system": "quantum", "target": "concept:voltage-view", "relation": "互文",
     "how": "电（激而迅发）↔ 正负零三极电压读数——信号强度的离散化互文（v0.6.65）"},
    {"from": "qi", "system": "quantum", "target": "concept:phase-matrix", "relation": "互文",
     "how": "气（散而弥虚）↔ 相变矩阵对相位的连续偏转：不改概率、只改相位（v0.6.65）"},
    {"from": "ci", "system": "plang", "target": "lang:verilog", "relation": "翻译",
     "how": "磁（约束吸附）→ 数据流约束（连线如磁力线，元件被引到位）"},
    {"from": "bo", "system": "apilab", "target": "concept:websocket", "relation": "翻译",
     "how": "波（无远弗届）→ WebSocket 推播：一处发布处处到达"},
    # 人间落法原则 → 八系统
    {"from": "he-butong-yong", "system": "apilab", "target": "concept:openapi", "relation": "翻译",
     "how": "API 版本并存：OpenAPI 多版本契约共荣"},
    {"from": "yinguo-bushuang", "system": "netsys", "target": "module:meshchat", "relation": "翻译",
     "how": "消息 ID 贯穿：每信可溯（因果不爽）"},
    {"from": "cibei-buhai", "system": "zhuangzi", "target": "principle:renjian-anming", "relation": "同构",
     "how": "慈悲不害（数据红线）与人间安命（破坏性操作敬畏化）同构"},
    {"from": "yuzhou-yizhi", "system": "baigong", "target": "principle:shengmo-guiju", "relation": "同构",
     "how": "跨端同口径 ↔ 绳墨规矩：一处绳墨三方取直"},
    {"from": "jingmo-tuomin", "system": "baigong", "target": "principle:jingshen-mingbian", "relation": "同构",
     "how": "静默脱敏 ↔ 精审明辩：不可说者不说，可言者说清"},
]

NEEDS_VERIFY = [
    {"item": "儒道佛三教引文", "status": "未核对原典",
     "note": "论语/礼记/道德经/心经等引文均按通行本登记，用户未上传原典核对；"
             "daoxue 系统同此口径"},
    {"item": "神恩如狱（诗化表达）", "status": "系统自拟学术口径",
     "note": "为用户诗化表达的学术化登记：按奥古斯丁恩典论/加尔文预定论/伊斯兰前定"
             "（qadar）/佛教业力观的「临及不由人择」作喻解，非任何教会官方表述"},
    {"item": "跨传统「三位一体/三身/三相」同构", "status": "比较框架自定",
     "note": "尼西亚三一、印度三相神、佛教三身仅作结构同构登记，神学内涵各自不同，"
             "不得据本系统推任何教义等同"},
    {"item": "琐罗亚斯德生卒与教期", "status": "年代分歧",
     "note": "学界约公元前 1500—前 600 区间诸说并存，本系统不取一说为定论"},
    {"item": "shaman/saman 词源", "status": "词源争议",
     "note": "通古斯语源说为主流，他源说并存；登记以待学界定论"},
    {"item": "正道六象元阳元阴分属", "status": "正名约定",
     "note": "固液气电/磁/波按「外发属天罡元阳（气电波）、内聚属地煞元阴（固液磁）」"
             "为本系统正名约定，非物理学分类；科学口径按物理学登记"},
    {"item": "黄金法则传统计数", "status": "概说",
     "note": "「百余传统有相同或相近表述」为概说，未逐条核计，不作精确统计引用"},
]


def live_user_face() -> dict:
    """构建期实测：CLI 子命令数 / GUI 窗口数 / webapi ACTIONS / deno 两文件版本
    + 语言面三项（与 build_baigong.py 同一口径，不硬编码）。"""
    sys.path.insert(0, str(SRC))
    from sysweeper import cli, webapi, concepts as C

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
        "concept_systems": len(C.systems()),
    }


# v0.6.62 字段齐备化：补齐 ethics 九条缺失的 detail（详述）。
DETAIL_FILL: Dict[str, str] = {
    "he-butong-yong": "《论语·子路》「君子和而不同，小人同而不和」：和是共存，不是同化。巴哈伊「多元一体」（unity in diversity）是同一主张的另一种表述——差异不是要被消除的缺陷，而是体系能长期存活的前提。工程上这意味着契约可以多版本并存，而不是靠一次切断更新来「统一」。",
    "yiti-shuangmian-shen": "「一体两面」要求凡有一面必有对立面：读配写、连配断、增配删。审计的意义正在于此——只登记了功能面而没登记风险面，等于只看见一半。道家「有无相生」提供的是同一结构：看得见的功能与看不见的风险同属一体。",
    "zhongdao-rong": "中道不是折中主义，而是「默认落在经验中位、极值必须显式声明」。佛教离苦乐二边、亚里士多德的 mesotes（中道）同此：默认值选择本身就是一次对用户的设计判断，把它交给显式 opt-in 才是对的做法。",
    "yinguo-bushuang": "「因果不爽」即种因必得果、不失不乱。工程上最直接的表达是：每一次变更都要有可追的因（请求 ID 贯穿）与可查的果（结构化日志留痕）；没有 ID 的变更，事后无法归因，也就不该进生产。",
    "huangjin-duichen": "「己所欲，施于人」这条正面式表达见于儒（己欲立而立人）、基督（爱人如己）等传统，是世界百余传统的公约数（计数为概说，见 needs_verify）。工程化后是契约对称：文档承诺与实现对称、入参与返回对称——做不到的东西不写进文档，是最低限度的诚实。",
    "jueji-shouquan": "「绝地天通」出自《国语·楚语下》：颛顼命重黎断绝人神杂糅，把通天之权收回到唯一通道。萨满传统的通灵权同样有严格的资格限制。对应工程：特权提升只留一条显式通道，日常一律低权，且必须记因、限时。",
    "cibei-buhai": "慈予乐、悲拔苦；耆那教以「不害」（ahimsa）为第一戒，佛教以慈悲为根本。这是本系统唯一一条压过一切的条款：任何功能都不得以损害用户为代价——删除与覆写要二次确认，触达要过白名单，出错要给出下一步而不是甩一个错误码。",
    "yuzhou-yizhi": "「宇宙公民」来自希腊斯多亚派的世界城邦观（第欧根尼自称 kosmopolites）：认同一个整体，不意味着抹去局部差异。工程上就是跨端同权——Windows/Linux/macOS 行为同口径，做不到的差异要显式登记，不藏着掖着假装一致。",
    "jingmo-tuomin": "敬默慎修：犹太传统对不可言之名的敬畏、佛教的慎言、各传统共有的静默修行（冥想/默祷/静修）都指向同一种克制。工程上的落法很具体：日志默认脱敏（令牌、路径、隐私不落盘），默认少说话，只有显式 verbose 才多说——多说一句就可能多泄一分。",
}
def apply_detail_fill(concepts: List[dict]) -> None:
    """给缺 detail 的概念补足详述（只补缺失项，已有 detail 的不动）。"""
    for c in concepts:
        if not str(c.get("detail") or "").strip():
            txt = DETAIL_FILL.get(c["id"])
            if txt:
                c["detail"] = txt

def build():
    bridges = [
        {"from": f"datong:{b['from']}", "system": b["system"], "target": b["target"],
         "relation": b["relation"], "how": b["how"]}
        for b in BRIDGES
    ]
    concepts = _concepts()
    apply_detail_fill(concepts)
    for c in concepts:                       # 数据层字段齐备统一（与 baigong 同构）
        c.setdefault("standards", [])
        c.setdefault("bridges", [])
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/datong/build_datong.py",
            "main_root": "wordbuddy-github",
            "title": "大同概念系统（人类文明一体 · 正道六象，以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": VERSION,
            "canon": "古来唯道独成尊：万流殊涂同归，道为所宗；古今中外宗教哲学命题融为一册；"
                     "固/液/气/电/磁/波六象为自然正道底座（天罡元阳·地煞元阴）",
            "axes": ["traditions", "theses", "six", "practices", "ethics"],
            "concept_total": len(concepts),
            "principle_total": len(PRINCIPLES),
            "bridge_count": len(bridges),
            "honesty": "只读登记不宣扬任何宗教为真理；不复制经典全文；跨传统同构非等同"
                       "（三位一体/三相神/三身等只作结构同构）；元阳元阴分属为正名约定"
                       "非物理学分类；神恩如狱为用户诗化表达的学术口径登记；未核对原典、"
                       "年代分歧、词源争议者统一挂 needs_verify；"
                       "宗教命题与实践类条目多无工程对应物，刻意不设落地桥接——"
                       "宁可孤立，也不臆造关系（v0.6.62）",
            "redline_note": "一体不是抹平差异（和而不同）；红线即狱墙（神恩如狱）+ 白名单"
                            "入口（净化禁忌）+ 特权分层收口（绝地天通）；慈悲不害：一切破坏性"
                            "操作二次确认、错误提示必给下一步",
        },
        "layers": [
            {"role": "traditions", "domain": "traditions", "tier": 1, "count": len(TRADITIONS),
             "canon": "诸传统",
             "sense": "文明传统 15 条：儒/道/佛/基督/伊斯兰/犹太/印度/耆那/锡克/琐罗亚斯德/希腊/神道/萨满巫觋/古埃及两河/巴哈伊"},
            {"role": "theses", "domain": "theses", "tier": 2, "count": len(THESES),
             "canon": "核心命题",
             "sense": "人类一体/一体两面/三位一体/神恩如狱/唯道独尊等 21 条跨传统核心命题"},
            {"role": "six", "domain": "six", "tier": 1, "count": len(SIX),
             "canon": "天罡元阳·地煞元阴",
             "sense": "正道六象：固液气电/磁/波——类科学的自然正道（正名约定见 needs_verify）"},
            {"role": "practices", "domain": "practices", "tier": 2, "count": len(PRACTICES),
             "canon": "文化生活",
             "sense": "实践形态 12 条：祷告/禅定/萨满出神/朝觐/节期/诵经/斋戒/苦行/圣礼/告解/占卜/驱邪净坛"},
            {"role": "ethics", "domain": "ethics", "tier": 1, "count": len(PRINCIPLES),
             "canon": "人间落法",
             "sense": "命题 → 可审计工程原则九条（见 principles）"},
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
    for t in TRADITIONS:
        out.append({"id": t["id"], "domain": "traditions", "name": t["name"],
                    "gist": t["gist"], "detail": t["detail"],
                    "engineering": t["engineering"], "canon_refs": []})
    for th in THESES:
        out.append({"id": th["id"], "domain": "theses", "name": th["name"],
                    "gist": th["gist"], "detail": th["detail"],
                    "engineering": th["engineering"],
                    "canon_refs": th.get("traditions", [])})
    for s in SIX:
        out.append({"id": s["id"], "domain": "six", "name": s["name"],
                    "gist": s["gist"], "detail": s["detail"],
                    "engineering": s["engineering"], "canon_refs": []})
    for p in PRACTICES:
        out.append({"id": p["id"], "domain": "practices", "name": p["name"],
                    "gist": p["gist"], "detail": p["detail"],
                    "engineering": p["engineering"], "canon_refs": []})
    for p in PRINCIPLES:
        out.append({"id": p["id"], "domain": "ethics", "name": p["name"],
                    "gist": p["gist"], "detail": "", "engineering": p["engineering"],
                    "canon_refs": p["canon_refs"]})
    return out


def _target_ids(name: str, doc: dict) -> Optional[set]:
    """返回某既有概念系统的可桥接目标 id 全集（按各系统数据层结构，与
    build_baigong._target_ids 同口径；桥接 target 统一 kind:value 分区校验）。"""
    if name == "daoxue":
        return {p["id"] for p in doc.get("principles", [])}
    if name == "apilab":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "comp":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "quantum":
        return {c["id"] for c in doc.get("concepts", [])}
    if name == "netsys":
        return {m["id"] for m in doc.get("modules", [])}
    if name == "plang":
        return set(doc.get("lang_index", {}))
    if name == "zhuangzi":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    if name == "baigong":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    return None


def check(doc: dict) -> List[str]:
    """防漂移校验，返回错误列表（空 = 通过）：

    schema / 轴合法 / id 唯一 / gist·engineering 齐备 / ethics 与 principles
    对齐 / canon_refs 有据 / 桥接无悬空 / 实测面逐键比对。
    """
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
        # v0.6.62 字段齐备：gist 一句话、detail 讲清楚、engineering 给落法，三者缺一不可
        if not str(c.get("detail") or "").strip():
            errs.append(f"{c['id']} 缺 detail（详述）")
        if not c.get("engineering"):
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    # 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc.get("by_domain", {})):
        if inverted.get(d, []) != doc.get("by_domain", {}).get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # ethics 概念须与 principles 一一对应
    pc_ids = sorted(p["id"] for p in doc["principles"])
    et_ids = sorted(c["id"] for c in doc["concepts"] if c["domain"] == "ethics")
    if pc_ids != et_ids:
        errs.append(f"ethics 概念与 principles 不一致：{set(pc_ids) ^ set(et_ids)}")

    # canon_refs 限登记传统/命题/原则（含唯道独尊之宗）
    known = {c["id"] for c in doc["concepts"] if c["domain"] in ("traditions", "theses", "ethics")}
    for c in doc["concepts"]:
        for r in c.get("canon_refs", []):
            if r not in known:
                errs.append(f"canon_ref 悬空：{c['id']} → {r}")

    # 桥接无悬空（既有八系统，目标结构各自解析；kind:value 分区校验）
    cache: Dict[str, Optional[set]] = {}

    def load_other(name: str) -> dict:
        return json.loads((DATA_DIR / f"{name}_taxonomy.json").read_text(encoding="utf-8"))

    for b in doc["bridges"]:
        fkind, _, fval = b["from"].partition(":")
        if fkind != "datong" or fval not in ids:
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

    # user_face 与源码实测逐键比对（漂移即重建）
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
    print(f"  needs_verify：{len(nv)} 项（" +
          "/".join(v.get("status", "") for v in nv) + "）")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    if "--check" in argv:
        # 防漂移：磁盘登记的实测值必须与当前源码/数据层实测一致
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
