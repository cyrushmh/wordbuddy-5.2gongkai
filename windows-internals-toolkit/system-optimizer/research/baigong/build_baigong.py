#!/usr/bin/env python3
"""「百工」概念系统构建（以 wordbuddy-github 为主目录，v0.6.61）。

用户原话：「在编程语言、编译语言、汇编语言、api、lib、标准、算法等，具体无解或
暂时不允许或构建程序具体结构的，以墨子、公输般、公孙策、鲁班为指导和理念，
可扩大为三教九流」。

本系统（第八概念系统，baigong）把四位（五偶）中华工程文化符号，翻译成
**可审计的工程原则**，桥接到本仓库既有七个概念系统：

    ├─ 轴1 core       核心理念·四偶一纲
    │                  墨子（非攻守御·明辩精审）／ 公输般（九设九距·制器尚用）／
    │                  鲁班（绳墨规矩·行业祖庭）／ 公孙策（锦囊分策·智囊谋划）／
    │                  三教九流总纲（九流并蓄·各极其用）
    ├─ 轴2 craft      匠作原则·七条（理念 → 可审计工程原则）
    ├─ 轴3 schools    三教九流映射（三教 3 + 九流 9，一流一工程域）
    └─ 轴4 scenes     工程场景（用户点名的三个：具体无解 / 暂时不允许 /
                      构建程序具体结构）

桥接目标必须在目标数据层真实存在（plang lang_index / comp·quantum·apilab
concepts / netsys modules / daoxue principles / zhuangzi 篇目与原则），
构建期校验无悬空。

诚实边界：不复制经典全文；《墨子》引文按通行本（《公输》篇「九设攻城之机变
……九距之」等）登记并统一标 needs_verify（用户未上传原典核对）；公输般与鲁班
为同一人的一名两译（《墨子》作公输盘/公输般），用户并列为两偶，本系统按
「一名两面」处理并显式挂牌；公孙策系《三侠五义》文学形象（非史实人物），
作「智囊型工程文化符号」登记；三教九流各条的工程落法系理念的工程翻译而非
原典；repo-face 事实（CLI 子命令数 / webapi ACTIONS 数 / GUI 窗口数 / deno
两文件版本 / 语言面三项）全部构建时从源码与数据层实测，不写无法核实的数字。

用法：
    python3 build_baigong.py            # 构建 data/concepts/baigong_taxonomy.json
    python3 build_baigong.py --check    # 校验（桥接无悬空 / 用户端面事实实测一致）
    python3 build_baigong.py --report   # 打印轴统计与桥接图
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
OUT = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "baigong_taxonomy.json"
CONCEPTS_DIR = OUT.parent
DENO_DIR = ROOT / "src" / "deno"

SCHEMA = "baigong_taxonomy/v1"

# ---------------------------------------------------------------------------
# 轴定义（四轴：核心理念 → 匠作原则 → 三教九流 → 工程场景）
# ---------------------------------------------------------------------------
DOMAINS = [
    {"domain": "core", "label": "核心理念",
     "note": "用户指定的四位（五偶）理念：墨子（非攻守御·明辩精审）/ 公输般"
             "（九设九距·制器尚用）/ 鲁班（绳墨规矩·行业祖庭）/ 公孙策"
             "（锦囊分策·智囊谋划）/ 三教九流总纲（九流并蓄·各极其用）"},
    {"domain": "craft", "label": "匠作原则",
     "note": "七条可审计的匠作工程原则：四偶理念各落一到两条——守御 / 明辩 / "
             "九设九距 / 绳墨 / 锦囊 / 名实 / 三表"},
    {"domain": "schools", "label": "三教九流",
     "note": "三教（儒/释/道）+ 九流（儒/道/阴阳/法/名/墨/纵横/杂/农）共 12 条，"
             "一条一工程域映射；儒道二条与 daoxue 系统同源交叉（注明不复制）"},
    {"domain": "scenes", "label": "工程场景",
     "note": "用户点名的三个场景：具体无解（悬置与降级）/ 暂时不允许（守御与"
             "opt-in）/ 构建程序具体结构（绳墨与九设九距）"},
]

# ---------------------------------------------------------------------------
# 概念：核心理念五偶 + 三教九流 12 条 + 工程场景 3 条
# （engineering = 落到本仓库的工程落法；bridges 内嵌，构建期校验无悬空）
# ---------------------------------------------------------------------------
CONCEPTS: List[dict] = [
    # ============ 轴1 核心理念·五偶 ============
    {"id": "mozi", "name": "墨子", "domain": "core", "no": 1,
     "gist": "墨家创始人；《墨子》七十一篇，含《经上/经下/经说上/经说下》形名"
             "逻辑之学（端/尺/厚/日中/影之损益）与《备城门》以下十一篇守城之法；"
             "止楚攻宋——「子墨子解带为城，以牒为械，公输般九设攻城之机变，"
             "子墨子九距之」。",
     "detail": "墨学十题：兼爱 / 非攻 / 尚贤 / 尚同 / 节用 / 节葬 / 非乐 / 天志 / "
               "明鬼 / 非命。十题中「非攻」与「经说」两端对本仓库最切：非攻 → "
               "安全即守御工程；形名之辩 → 概念精确与悬置纪律。",
     "engineering": "落成「守御 + 明辩」两路工程纪律。**守御**：纵深防御、入口"
                    "白名单、最小攻击面——《七患》「备者，国之急」= 红线先立于"
                    "功能之先（本仓库插件白名单、webapi ACTIONS 白名单、opt-in "
                    "开关、令牌禁入 URL）。**明辩**：「名实」先于实现——概念经"
                    "定义、枚举、分类三审而后落码；不可证不可判之事悬置 "
                    "needs_verify，不臆造（墨子三表法「本之者 / 原之者 / 用之者」"
                    "= 事有本原有用，以实测为断）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:shou-zhong", "relation": "理念同源",
          "how": "「备者国之急」= 守中慎行：红线先立，防患于未发"},
         {"system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "理念同源",
          "how": "图难于其易 = 备患于未然：难事先在易处着手（守御先于功能）"},
         {"system": "apilab", "target": "concept:auth-redlines", "relation": "同域",
          "how": "非攻 = 认证与授权红线：入口白名单制，最小攻击面"},
         {"system": "apilab", "target": "concept:json-schema", "relation": "同域",
          "how": "形名之律 = schema 约束：名实相符，先立约束后传数据"},
         {"system": "netsys", "target": "module:emergency", "relation": "同域",
          "how": "备城门 = 应急守御：emergency 子系统即守圉之有余的现代形态"},
         {"system": "netsys", "target": "module:sysmesh", "relation": "系统互联协调",
          "how": "非攻 = 系统经组网而互联、互不僭越：sysmesh 即百工各司其职、经网协同的协调基底"}]},
    {"id": "gongshuban", "name": "公输般", "domain": "core", "no": 2,
     "gist": "春秋末鲁国巧匠（公输班，般/班古通），造云梯、钩拒等攻守器械；"
             "与墨子「九设攻城之机变，子墨子九距之」的攻防推演，是中国技术史"
             "上最早有记载的「设计—对抗—迭代」循环。",
     "detail": "《墨子·公输》：子墨子见公输般，公输般九设攻城之机变，子墨子"
               "九距之，「公输般之攻械尽，子墨子之守圉有余」。后世尊为工匠"
               "祖师之一（与鲁班并为一人，见 needs_verify 一名两译之说明）。",
     "engineering": "**每设一器，即受一试**：结构不是写完的，是攻防推演剩下"
                    "来的——契约先行、parity 跨语言一致性测试、模糊与对抗输入"
                    "均出于此；「机变」即方案分册（plan A/B），迭代以试错为代价"
                    "但不以试错为常态（先沙盘后施工：--plan 预览、run 预演）。",
     "bridges": [
         {"system": "comp", "target": "concept:pipeline-overview", "relation": "同域",
          "how": "九设九距 = 流水线逐阶段一设一受：词法/语法/语义每过一门即受一验"},
         {"system": "comp", "target": "concept:make", "relation": "同域",
          "how": "器械列伍 = 构建编排：make check / 一致性测试即当代攻防演练"},
         {"system": "plang", "target": "lang:assembly", "relation": "同域",
          "how": "汇编层即器械层：每条指令一试便知，无玄学可藏"}]},
    {"id": "luban", "name": "鲁班", "domain": "core", "no": 3,
     "gist": "民间工匠祖师，木工鼻祖；传有锯、刨、墨斗之发明，其要者在「绳墨」"
             "——无绳墨则曲直无据，无规矩则方员不成。",
     "detail": "绳墨（墨斗）以目正绳、以绳定曲直，是中国工匠「标准先于施工」的"
               "化身；行业以「班门」为尊，师承谱系延续至今。本系统按文化符号"
               "登记（一名两译之诚实在 needs_verify 挂牌）。",
     "engineering": "**标准与度量先于施工**：凡入码之事，先登记标准依据（RFC / "
                    "ISO / IEEE / Unicode 编号，经 rfc_catalog 交叉验证防写错编号），"
                    "后落实现；「规矩」化为可审计的度量——阈值、契约、schema、"
                    "兼容性矩阵；不立绳墨之器不造（未登记标准的实现裸奔）。",
     "bridges": [
         {"system": "apilab", "target": "concept:openapi", "relation": "同域",
          "how": "契约 = 绳墨：接口先立规格（OpenAPI），后生双端实现"},
         {"system": "comp", "target": "concept:cmake", "relation": "同域",
          "how": "构建规程 = 规矩：CMake 跨平台标准流程，凭绳墨不凭手感"}]},
    {"id": "gongsunce", "name": "公孙策", "domain": "core", "no": 4,
     "gist": "包公案文学形象（《三侠五义》），智囊型谋士：善断疑难、勤筹锦囊"
             "——分阶段、分对手、分情形的预案体系，是中国民间「智谋型工程文化」"
             "的代表符号。",
     "detail": "形象三件套：明查暗访（取证）/ 锦囊妙计（分阶段预案）/ 权衡调度"
               "（分派资源）。文学形象非史实人物，作工程文化符号登记"
               "（needs_verify 显式挂牌）。",
     "engineering": "**复杂问题分层预案**：算法即策——精确解（穷举 / 动态规划）、"
                    "近似解（启发式 / 参数化）、随机化（蒙特卡洛）、并行（分治"
                    "调度）按梯次而降；「锦囊」= 关键处预置触发条件与回退路径"
                    "（degradation ladder 显式登记）；明查暗访 = 观测先行（日志、"
                    "留痕、快照）而后论断。",
     "bridges": [
         {"system": "quantum", "target": "concept:qaoa", "relation": "同域",
          "how": "困难优化按梯次降级：QAOA/VQE 即当代锦囊——不求最优先求可行"},
         {"system": "comp", "target": "concept:opt", "relation": "同域",
          "how": "优化即谋略：编译器优化通道按收益与代价分册施策"},
         {"system": "netsys", "target": "module:apctrl", "relation": "同域",
          "how": "调度智囊：接入点控制器即权衡分派的现代锦囊"},
         {"system": "zhuangzi", "target": "principle:shiwei-zongshi", "relation": "理念同源",
          "how": "锦囊 = 预判意图：智囊先一步备策，正合大宗师「意图为宗师」"}]},
    {"id": "sanjiao-jiuliu", "name": "三教九流总纲", "domain": "core", "no": 5,
     "gist": "三教（儒 / 释 / 道）与九流（儒 / 道 / 阴阳 / 法 / 名 / 墨 / 纵横 / "
             "杂 / 农）是中国思想技术的总谱；本系统取其「术有专攻、各极其用」"
             "之意，扩大为工程文化映射（schools 轴逐条展开）。",
     "detail": "用户原话「可扩大为三教九流」：本系统以四偶为纲、九流为目——"
               "一流一工程域映射，构建期校验桥接目标真实存在；儒道二流与 "
               "daoxue 系统同源交叉（详见其条目注记，不复制 daoxue 内容）。",
     "engineering": "不以一家之法盖全栈：语言 / 编译 / 接口各域各有其「流」——"
                    "类型归名、文法归法、协议归纵横、集成归杂、基设归农；域间"
                    "以桥接边相接而非层级相辖（概念系统中心即「杂家」之具）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "理念同源",
          "how": "兼收而不强同：九流并蓄而各极其用，即道法自然之规模化"},
         {"system": "zhuangzi", "target": "concept:qiwulun", "relation": "理念同源",
          "how": "九流平权 = 齐物：一流一法而无高下之争，双模平权"}]},

    # ============ 轴3 三教九流（三教 3 + 九流 9）============
    {"id": "rujiao", "name": "儒教（三教）", "domain": "schools",
     "gist": "三教之一，以礼乐仁义为核心；工程对应「规范之礼」——风格一致性、"
             "命名礼制、文档之节。",
     "engineering": "接口有节：同一风格贯穿全站（REST 资源命名、错误码体例、"
                    "CLI 子命令扁平名）；文档如礼经——先总纲后条目，每条可查"
                    "（README / docs 分层）。",
     "bridges": [
         {"system": "apilab", "target": "concept:rest", "relation": "同域",
          "how": "风格之礼：REST 的资源与动词之节，即礼制的接口化"}]},
    {"id": "fojiao", "name": "佛教（三教）", "domain": "schools",
     "gist": "三教之一，以戒定慧为次第、缘起性空为观；工程对应「不变量与"
             "所有权」——戒即编译期不变量，缘起缘灭即资源生命周期。",
     "engineering": "持戒二门：不变量与生命周期。类型与借用检查是「戒」——编译"
                    "期即拒越轨（rust 所有权模型为其极致）；「缘起」= 引用/拥有"
                    "权关系显式化，缘灭 = 析构确定，不留悬资源。",
     "bridges": [
         {"system": "plang", "target": "lang:rust", "relation": "同域",
          "how": "所有权即戒律：编译期持戒，borrow checker 即戒坛"},
         {"system": "quantum", "target": "concept:measurement", "relation": "同域",
          "how": "刹那生灭 = 测量坍缩：量子态一测即转，正如生命周期一越即终"}]},
    {"id": "daojiao", "name": "道教（三教）", "domain": "schools",
     "gist": "三教之一；其治理理念已在 daoxue 系统完整登记（道德经 / 早晚坛"
             "功课经 / 心经 / 论语），本系统不复制，仅作交叉桥接。",
     "engineering": "取其「有无相生」：状态空间与叠加观提醒我们，未观测的分支"
                    "同样在场（观测即选择，默认即一种选定）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "同源交叉",
          "how": "详见 daoxue 系统（道枢治理层），此处不重复登记"},
         {"system": "quantum", "target": "concept:superposition", "relation": "同域",
          "how": "有无相生 → 叠加态：未观测的分支亦在场，观测即坍缩为选择"}]},
    {"id": "rujia", "name": "九流·儒家", "domain": "schools",
     "gist": "九流之一，祖述尧舜、宪章文武，以礼乐刑政为务；工程对应「规范"
             "治理」——标准的产生、评议与演进（PEP / RFC 流程）。",
     "engineering": "规范治理：语言演进走「提案—评议—成文」之路（如 Python "
                    "PEP、Rust RFC），反对私定标准；本仓库文档即礼乐之官——"
                    "每轮改动入 docs 归档。",
     "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "同域",
          "how": "PEP 流程 = 评议之礼：标准经公议而后立，不私定"}]},
    {"id": "daojia", "name": "九流·道家", "domain": "schools",
     "gist": "九流之一，以道法自然、无为为宗；治理面已在 daoxue 系统登记，"
             "此处仅作交叉（详见该儒道二教之注记）。",
     "engineering": "软件的自然之性：不逆环境强行（平台探测 detect 先行为），"
                    "「为学日益、为道日损」= 功能可增，默认必损之又损（零配置"
                    "可用）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:wuwei", "relation": "同源交叉",
          "how": "详见 daoxue 系统；无为 = 界面不强行作为、默认即最佳"}]},
    {"id": "yinyangjia", "name": "九流·阴阳家", "domain": "schools",
     "gist": "九流之一，观阴阳消息、五行生克；工程对应「状态与相位」——二进制、"
             "并发相位、协议握手的状态机之舞。",
     "engineering": "相位显式化：字节以位立、事务以相位推进（TLS 握手一阴一阳"
                    "数往返）；数字电路以阴阳为砖（0/1），状态机以显式为法"
                    "（无隐式相位）。",
     "bridges": [
         {"system": "netsys", "target": "module:tls13", "relation": "同域",
          "how": "握手即阴阳交替：密钥交换数往返而定相位，推进有时"},
         {"system": "plang", "target": "lang:verilog", "relation": "同域",
          "how": "数字电路以 0/1 阴阳为基砖，HDL 即阴阳家的积木"}]},
    {"id": "fajia", "name": "九流·法家", "domain": "schools",
     "gist": "九流之一，以法、术、势为治；工程对应「规则与法度」——文法规则、"
             "编译器之法、法典化标准。",
     "engineering": "法度先于自由：语法即法（grammar 定义什么可写）、语义即术"
                    "（类型规则裁断含义）、标准即势（ISO/IEC 法典号令双端）。",
     "bridges": [
         {"system": "comp", "target": "concept:lex-parse", "relation": "同域",
          "how": "文法即法度：词法/语法规则先行，越轨即语法错误"},
         {"system": "plang", "target": "lang:c", "relation": "同域",
          "how": "ISO/IEC 9899 = C 之法典：双端共守一法，不私刑"}]},
    {"id": "mingjia", "name": "九流·名家", "domain": "schools",
     "gist": "九流之一，以「坚白」「同异」之辩著称，苛察缴绕、正名务实；工程"
             "对应「类型与命名」——名实之辩在当代的化身即类型系统。",
     "engineering": "正名而后编程：每一个标识符名副其实（命名即契约）、每一个"
                    "类型名实相符（类型即谓词）；「离坚白」= 把复合概念拆成"
                    "正交小概念（关注点分离）。",
     "bridges": [
         {"system": "comp", "target": "concept:sema", "relation": "同域",
          "how": "正名 = 语义分析与类型检查：名实不符即编译期拒收"},
         {"system": "plang", "target": "lang:haskell", "relation": "同域",
          "how": "类型系统是名学之极致：类型即谓词，程序即证明"}]},
    {"id": "mojia", "name": "九流·墨家", "domain": "schools",
     "gist": "九流之一，本系统之纲；形名逻辑、守御工程与实测三表法即其骨干"
             "（详见 core 轴墨子条目）。",
     "engineering": "墨辩之逻辑传统在当代工程的三支：证明助手（形式验证）、"
                    "白名单（守御）、probe 实测（三表法「本之原之用之」）。",
     "bridges": [
         {"system": "plang", "target": "lang:coq", "relation": "同域",
          "how": "墨辩逻辑传统 → 证明助手：命题可证可征，不悬空立论"}]},
    {"id": "zonghengjia", "name": "九流·纵横家", "domain": "schools",
     "gist": "九流之一，以合纵连横、游说诸侯为务；工程对应「协议与谈判」——"
             "双方（多方）如何就通信达成并维持契约。",
     "engineering": "协议即谈判术：API 契约（OpenAPI / IDL）先谈而后行；长连接"
                    "即合纵（WebSocket 持久通道）、网即连横（mesh 多节点协商）；"
                    "版本谈判（Content-Type / 能力协商）是游说的技术化。",
     "bridges": [
         {"system": "apilab", "target": "concept:websocket", "relation": "同域",
          "how": "长连接谈判：WebSocket 一次握手定长久之约，如合纵之约"},
         {"system": "netsys", "target": "module:meshchat", "relation": "同域",
          "how": "多节点纵横协商：组网通信即连横术的工程形态"}]},
    {"id": "zajia", "name": "九流·杂家", "domain": "schools",
     "gist": "九流之一，「兼儒墨、合名法」；工程对应「集成与互操作」——多语言"
             "混编、跨端一致、概念系统中心即杂家之具。",
     "engineering": "兼容并包而有主次：多语言工具链（LLVM 一后端多前端）、多目标"
                    "转译（Haxe 类语言）、跨端一致（report schema 双端消费）；"
                    "杂不是芜杂——集成有主而后兼收。",
     "bridges": [
         {"system": "comp", "target": "concept:llvm-toolchain", "relation": "同域",
          "how": "兼收并蓄 = 多前端统一后端：LLVM 是最大的杂家"},
         {"system": "plang", "target": "lang:haxe", "relation": "同域",
          "how": "转译多目标 = 杂家工具箱：写一次，编译到各家"}]},
    {"id": "nongjia", "name": "九流·农家", "domain": "schools",
     "gist": "九流之一，「农谓之农家」——播百谷、劝耕桑、以足食；工程对应"
             "「基础设施」——构建、包管理、操作系统适配这些「田土」之事。",
     "engineering": "先事田土后谈收获：构建系统与包管理是底仓（native build / "
                    "gradle-maven 类）；基础设施勤养护（平台探测、架构交叉编译、"
                    "CI 定时耕种）；「不违农时」= 版本节奏（stable/LTS/fresh "
                    "通道按农时轮作）。",
     "bridges": [
         {"system": "comp", "target": "concept:native-build", "relation": "同域",
          "how": "构建即农耕：按架构与季节（CI）耕作，按时收获产物"}]},

    # ============ 轴4 工程场景（用户点名的三个）============
    {"id": "scene-wujie", "name": "具体无解", "domain": "scenes",
     "gist": "范畴内「当前无解」的问题：不可判定（停机问题）、难解（P vs NP、"
             "NP-hard 优化）、极限（熵与压缩、CAP 不可得三角）——诚实登记其"
             "状态，不宣称万能。",
     "detail": "本仓库的登记口径：尚无解的问题一律挂牌（needs_verify / "
               "redline），不写「假解」；可近似的问题按梯次降级登记方法边界"
               "（启发式、随机化、并行、量子近似算法族）。",
     "engineering": "悬置 + 降级两级处置：**悬置**——不可证不可判之事 needs_verify "
                    "挂牌（知不知，不臆造）；**降级**——难解问题按方法梯次降级："
                    "精确 → 启发 → 随机 → 并行 → 量子近似，每级登记其代价与"
                    "适用范围（不越级宣称）。",
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念同源",
          "how": "知不知：无解即悬置挂牌，知道「不知道」是工程的第一步"},
         {"system": "quantum", "target": "concept:mitigation", "relation": "同域",
          "how": "误差缓解 = 无精确解时的应对：承认噪声而后缓解，不装作无噪"},
         {"system": "comp", "target": "concept:opt", "relation": "同域",
          "how": "宁求可行解：优化通道按代价分册，不承诺最优"}]},
    {"id": "scene-buyunxu", "name": "暂时不允许", "domain": "scenes",
     "gist": "当前不允许做之事：平台权限不足（容器内/受限宿主）、合规红线"
             "（数据出境、隐私法域）、策略性默认关闭（危险开关 opt-in）——以"
             "守御处之，不为而不可夺。",
     "detail": "本仓库的登记口径：opt-in 开关 + 双确认 + 白名单三重门（网络类"
               "任务默认关闭、需显式选择并确认；插件与 ACTIONS 白名单制；令牌"
               "禁入 URL）。",
     "engineering": "**守御式不为**：默认关闭（opt-in 双确认）、能力边界诚实"
                    "告知（受限功能标注原因与替代，不装能做）、红线先立（安全"
                    "红线 register 于功能之前）——楚攻宋之守：不为在先，故不"
                    "可夺。",
     "bridges": [
         {"system": "daoxue", "target": "principle:shou-zhong", "relation": "理念同源",
          "how": "守中不为：暂时不允许之事守中不启，双确认而后行"},
         {"system": "netsys", "target": "module:tor", "relation": "同域",
          "how": "默认关闭需显式启用：Tor 即 opt-in 守御的样板（不默认开）"}]},
    {"id": "scene-jiegou", "name": "构建程序具体结构", "domain": "scenes",
     "gist": "数据结构、控制流、模块系统、调用约定与 ABI 等「程序的具体结构」"
             "之事——以绳墨定其规，以九设九距验其固，以名实正其名。",
     "detail": "本仓库的登记口径：结构先登记标准（RFC / ISO / IEEE / Unicode，"
               "经 rfc_catalog 交叉验证），后落实现；跨端结构以 parity 测试"
               "保一致（PE 查看器六语言实现同题同答）。",
     "engineering": "**标准 → 构造 → 验证**三步：标准先行（绳墨：schema / 契约 / "
                    "标准号登记）、构造有法（名实相符的命名与分层）、验证以试"
                    "（parity / 契约 / 模糊对抗各一试）——结构不是想出来的，"
                    "是受得住试的。",
     "bridges": [
         {"system": "comp", "target": "concept:codegen", "relation": "同域",
          "how": "结构生成 = 造器：代码生成器按绳墨（目标契约）产出结构"},
         {"system": "comp", "target": "concept:link", "relation": "同域",
          "how": "结构装配 = 榫卯：链接器把造好的器部按约定拼合，差之毫厘即拒"},
         {"system": "netsys", "target": "module:osi", "relation": "同域",
          "how": "层级结构之分：OSI 分层是结构之道的样板（每层名实相符）"}]},
]

# ---------------------------------------------------------------------------
# 匠作原则（七条：理念 → 可审计工程原则，四偶各落到一至两条）
# ---------------------------------------------------------------------------
PRINCIPLES = [
    {"id": "feigong-shouyu", "name": "非攻守御", "canon_refs": ["墨子"], "domain": "craft",
     "gist": "非攻：安全即防御工程——纵深防御、入口白名单、最小攻击面；"
             "「备者，国之急」，红线先立于功能之先。",
     "engineering": "插件白名单制（manifest native 字段必须在内）；webapi ACTIONS "
                    "白名单 + 无 getattr 兜底；令牌禁入 URL/localStorage；破坏性"
                    "操作 opt-in 双确认；私钥不明文。",
     "bridges": [{"system": "apilab", "target": "concept:auth-redlines", "relation": "同源", "how": "非攻守御即安全红线总纲：白名单入口 + opt-in 双确认 + 令牌禁入 URL/localStorage，与 apilab 认证红线同源同据"}],
},
    {"id": "jingshen-mingbian", "name": "精审明辩", "canon_refs": ["墨子"], "domain": "craft",
     "gist": "经说形名之学：概念经定义、枚举、分类三审而后落码；不可证不可判"
             "之事悬置 needs_verify，不臆造。",
     "engineering": "概念系统每条目登记 gist/detail/engineering 三件套；桥接"
                    "构建期校验无悬空；未核实项统一挂牌（needs_verify）而非"
                    "留空或填充假值。"},
    {"id": "jiushe-jiudi", "name": "九设九距", "canon_refs": ["公输般", "墨子"], "domain": "craft",
     "gist": "每设一器，即受一试：结构不是写完的，是攻防推演剩下来的——"
             "契约先行，对抗输入各一试。",
     "engineering": "parity 跨语言一致性测试（同题同答）；模糊与对抗输入"
                    "（hostile input）用例；契约测试先于实现；--plan 预演"
                    "先于 run 执行。",
     "bridges": [{"system": "comp", "target": "concept:sema", "relation": "翻译", "how": "九设九距即「每设一器即受一试」：语义分析层正是把类型与名字的攻防检查提前到编译期，与对抗式验证同思路"}],
},
    {"id": "shengmo-guiju", "name": "绳墨规矩", "canon_refs": ["鲁班"], "domain": "craft",
     "gist": "无绳墨则曲直无据：标准与度量先于施工——凡入码之事，先登记标准"
             "依据，后落实现。",
     "engineering": "标准依据轴（RFC/ISO/IEEE/Unicode）逐条登记，RFC 编号经 "
                    "rfc_catalog 交叉验证；产物 report schema 定契约；阈值"
                    "入 settings 注册表，不硬编码于代码。"},
    {"id": "jinnang-celue", "name": "锦囊分策", "canon_refs": ["公孙策"], "domain": "craft",
     "gist": "复杂问题分层预案：精确 → 近似 → 随机 → 并行，按梯次而降，"
             "每一级登记代价与适用范围。",
     "engineering": "困难问题登记方法梯次（degradation ladder）；回退路径显式"
                    "（降级时明示原因与替代）；观测先行（日志/留痕/快照）"
                    "而后论断。",
     "bridges": [{"system": "comp", "target": "concept:opt", "relation": "同构", "how": "锦囊分策的梯次降级（精确→近似→随机→并行）与优化 pass 的层级取舍同构：每一级都登记代价与适用范围"}],
},
    {"id": "qiyong-mingshi", "name": "器以用途", "canon_refs": ["公输般", "鲁班"], "domain": "craft",
     "gist": "制器尚用、名实相符：每个程序结构为用途而生，其名即其用。",
     "engineering": "产物按用途登记（artifact-static-lib / shared-lib / exe / "
                    "bytecode…）；API 资源命名即用途（repo-cli / repo-webapi…）；"
                    "不为通用而造无名之器。",
     "bridges": [{"system": "comp", "target": "concept:artifact-pkg", "relation": "翻译", "how": "器以用途、名实相符：产物按用途分类登记（静态库/动态库/可执行/字节码/包/镜像），名即其用"}],
},
    {"id": "shishi-sanbiao", "name": "实事三表", "canon_refs": ["墨子"], "domain": "craft",
     "gist": "本之者 / 原之者 / 用之者：事有本原有用，以实测为断——不凭"
             "说明书宣称能力，凭探针。",
     "engineering": "plang probe 真实执行样例（15 种语言实测登记）；user_face "
                    "构建期从源码实测（CLI/GUI/webapi/deno）；probe 未通过的"
                    "语言如实标 needs_verify，不宣称可编译。",
     "bridges": [{"system": "apilab", "target": "concept:repo-webapi", "relation": "翻译",
                  "how": "实事三表以实测为断：用户端面数字全部由构建期读源码实测"
                         "（CLI/GUI/webapi/deno），与 repo-face 同一纪律"}]}
]


# ---------------------------------------------------------------------------
# 用户端面 + 语言面实测事实（构建时从源码与数据层读出；--check 防漂移）
# ---------------------------------------------------------------------------
def user_face_facts() -> Dict[str, object]:
    """从源码实测读出本仓库「用户端面」事实 + 从 plang/comp 数据层读出语言面事实。"""
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

    plang = json.loads((CONCEPTS_DIR / "plang_taxonomy.json").read_text(encoding="utf-8"))
    comp = json.loads((CONCEPTS_DIR / "comp_taxonomy.json").read_text(encoding="utf-8"))

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
    }


# v0.6.62 字段齐备化：补齐缺失的 detail（详述）——gist 一句话、detail 讲清楚、engineering 给落法，三者分工不重复。
DETAIL_FILL: Dict[str, str] = {
    "rujiao": "以孔子为宗、六艺为教：礼定长幼尊卑之序、乐成上下之和、仁义为内在尺度。三教之中它最重「入世的规矩」，故工程上对应的不是性能而是**一致性**——同一套命名、同一套错误体例、同一种文档层次，使陌生者也能按预期找到东西。",
    "fojiao": "以戒、定、慧为次第：戒是「不该做的事先写明」，定是「心不散乱故能观」，慧是「照见缘起性空」。工程翻译过来极贴切：编译期不允许的事先写明（类型/借用检查），运行时状态要有确定的生灭（资源生命周期），二者都靠**先把规则写死**而非靠人自觉。",
    "daojiao": "以道为宗、以自然为法；其治理理念（无为而无不为、治大国若烹小鲜等）已在 daoxue 系统按道德经八十一章完整登记。此处**刻意不复制**，只保留一枚交叉指针——同一份内容在两个系统里各抄一遍，迟早会对不上，这是本仓库反复回避的坑。",
    "rujia": "祖述尧舜、宪章文武，以礼乐刑政为务；在九流中是「制度派」。它的当代形态就是标准化流程：新东西不是不能用，而是要先走「提案—评议—成文」的路，公开讨论、留下记录、有编号可查——PEP、RFC、ISO 皆是此道。",
    "daojia": "以道法自然、无为为宗，是九流里的「减法派」。软件里最难的从来不是加功能，而是敢于删默认值：每个默认值都是对用户的一次猜测，猜错了就要用配置项去救，配置项再长出文档与兼容承诺——所以「损之又损」在工程上是硬功夫。",
    "yinyangjia": "观阴阳消息、五行生克，把一个系统的状态迁移当作头等大事。工程上这就是**显式状态机**：TLS 握手往返几次、事务处于什么相位、电路以 0/1 为砖——凡隐式相位一旦漏掉，就会在特定时序下才炸，最难查。",
    "fajia": "以法、术、势为治，重明文规则而不重道德感召。翻译到工程：文法定「什么可写」、类型规则定「含义如何裁断」、标准号令双端对齐。它的告诫是——**规则要写在明处并可执行**，写在文档里靠自觉的，不算规则。",
    "mingjia": "以「坚白」「同异」之辩著称，苛察而务实，专抠名实是否相符。这正是类型系统要做的事：一个名字宣称什么，它的实现就得守住什么。「离坚白」那条主张把复合之物拆为正交小概念，也就是今天说的关注点分离。",
    "mojia": "九流之一，也是本系统的纲领所在：形名逻辑（概念要定义清楚）、守御工程（入口要白名单）、实测三表法（能力要probe 起来看）三支皆出墨家。详见 core 轴墨子条目，此处只留指针，避免同一份内容双写失同步。",
    "zonghengjia": "以合纵连横、游说诸侯为务，是九流里的「谈判派」。多方要想协作就得先达成契约——这正是 OpenAPI/IDL 与版本协商的处境：先谈清楚，再写代码；握手不成的后果不是报错，而是各说各话。",
    "zajia": "「兼儒墨、合名法」，博采而不专守。它在工程里对应集成与互操作：多语言工具链、多目标转译、跨端同源输出。要点在后半句——杂不等于芜杂，集成必先定主次与主数据源，否则只是把三家的错摆在一起。",
    "nongjia": "播百谷、劝耕桑、以足食，是最不起眼却最要命的一流：没人先种地，后面都谈不上。工程里的对应物是构建系统、包管理与平台适配这些「田土」之事——它们不产生新功能，但没有它们，什么功能都发不出去。",
    "feigong-shouyu": "非攻不是无用，是守御：「备者，国之急」——先有城墙再有市集。它主张红线先立于功能之先：把不可做的事明确写下来并强制生效，而不是指望用户不去碰。安全边界一旦靠约定，迟早会被绕过。",
    "jingshen-mingbian": "经说形名之学要求：一个概念要经过定义、枚举、分类三审才许落码。落到本仓库就是每条目必须登记 gist/detail/engineering 三件套、桥接边在构建期校验无悬空、查不清的东西统一挂 needs_verify——**宁留白，不填假值**。",
    "jiushe-jiudi": "公输般九设攻城之机变、墨子九距之：结构不是写完就完，是被反复攻到只剩骨架。工程里的等价物是同题同答的跨语言对照、敌意输入的模糊测试、以及执行前的预演（--plan 先看再跑）。",
    "shengmo-guiju": "无绳墨则曲直无据：度量先于施工。落码之前先把依据登记下来——RFC/ISO/IEEE/Unicode 编号要可核（本仓库还用 rfc_catalog 反查标题），产物结构要先有 schema，阈值要有出处。**先立规，后动手**。",
    "jinnang-celue": "锦囊之策贵在分层：精确解 → 近似解 → 随机法 → 并行化，逐级下降，每一级都登记代价与适用范围。工程上最怕的不是降级，而是**静默降级**——用户不知道自己拿到的是哪一档答案。",
    "qiyong-mingshi": "制器尚用、名实相符：每个结构为用途而生，它的名字就该说出它的用途。本仓库据此给产物分类（静态库/动态库/可执行/字节码/包/镜像），也给 API 资源命名——名不符实时，读代码的人要为你的含糊付费。",
    "shishi-sanbiao": "本之者、原之者、用之者：事有本、有用、有验，以实测为断。所以本仓库的能力清单靠 probe 真跑（15 种语言实测），用户端面的数字靠构建期读源码（CLI/GUI/webapi/deno）——不凭说明书宣称能力，凭探针。",
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
    {"from": "baigong:sanjiao-jiuliu", "system": "datong", "target": "principle:weidao-duzun",
     "relation": "同宗", "how": "九流并蓄各极其用 ↔ 唯道独尊：殊涂同归，道为所宗"},
]


def build() -> dict:
    bridges: List[dict] = []
    for c in CONCEPTS:
        for b in c.get("bridges", []):
            bridges.append({
                "from": f"baigong:{c['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    for p in PRINCIPLES:
        for b in p.get("bridges", []):
            bridges.append({
                "from": f"baigong:{p['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    bridges.extend(DATONG_BACKLINKS)

    all_concepts = CONCEPTS + PRINCIPLES
    apply_detail_fill(all_concepts)
    for c in all_concepts:                      # 数据层字段齐备统一（与 zhuangzi 同构）
        c.setdefault("standards", [])
        c.setdefault("bridges", [])
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in all_concepts:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/baigong/build_baigong.py",
            "main_root": "wordbuddy-github",
            "title": "百工概念系统（墨子/公输般/公孙策/鲁班 → 三教九流，以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": "0000.0000.0000.0061.20261023",
            "canon": "墨子·七十一篇（经说四篇 + 备城门十一篇守御之法）；"
                     "公输般/鲁班（一名两译之工匠祖师）；公孙策（三侠五义文学形象）",
            "axes": ["core", "craft", "schools", "scenes"],
            "concept_total": len(all_concepts),
            "principle_total": len(PRINCIPLES),
            "bridge_count": len(bridges),
            "honesty": "不复制经典全文；《墨子》引文按通行本登记并统一标 needs_verify"
                       "（用户未上传原典核对）；公输般即鲁班一名两译，用户并列两偶，"
                       "本系统按「一名两面」处理；公孙策系文学形象非史实人物；"
                       "三教九流落法系理念的工程翻译非原典。",
            "redline_note": "安全红线延续 apilab/auth 与墨子非攻：白名单入口、"
                            "opt-in 双确认、令牌禁入 URL/localStorage；「暂时不允许」"
                            "之事以守御处之，不为而不可夺。",
        },
        "layers": [
            {"role": "core", "canon": "墨子/公输般/鲁班/公孙策", "tier": 1,
             "sense": "核心理念五偶：墨子（守御·明辩）/ 公输般（九设九距）/ 鲁班（绳墨）/ "
                      "公孙策（锦囊）/ 三教九流总纲",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "core")},
            {"role": "craft", "canon": "理念的工程翻译", "tier": 1,
             "sense": "七条可审计的匠作工程原则（四偶各落到一至两条）",
             "count": len(PRINCIPLES)},
            {"role": "schools", "canon": "三教九流", "tier": 2,
             "sense": "三教 3 + 九流 9：一教/一流一工程域映射（儒=规范礼制 / 释=戒律与缘起 / "
                      "道=自然无为×daoxue 交叉 + 儒/道/阴阳/法/名/墨/纵横/杂/农）",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "schools")},
            {"role": "scenes", "canon": "用户点名的工程场景", "tier": 1,
             "sense": "具体无解（悬置降级）/ 暂时不允许（守御 opt-in）/ 构建程序具体结构"
                      "（绳墨与九设九距）",
             "count": sum(1 for c in CONCEPTS if c["domain"] == "scenes")},
        ],
        "domains": DOMAINS,
        "concepts": all_concepts,
        "principles": PRINCIPLES,
        "bridges": bridges,
        "by_domain": by_domain,
        "user_face_facts": user_face_facts(),
        "needs_verify": [
            {"item": "《墨子》引文依据", "status": "needs_verify",
             "note": "用户未上传《墨子》原典文本，「九设攻城之机变……九距之」等引文"
                     "按通行本登记，未逐字核对（与 daoxue/zhuangzi 同口径）"},
            {"item": "公输般即鲁班一名两译", "status": "needs_verify",
             "note": "《墨子》作公输盘/公输般，民间与鲁班并为一人；用户并列两偶，"
                     "本系统按「一名两面」处理（公输般=攻防器械/九设九距；"
                     "鲁班=绳墨规矩/匠作祖庭），未另核史源"},
            {"item": "公孙策系文学形象", "status": "needs_verify",
             "note": "公孙策出自《三侠五义》包公案，非史实人物；本系统作「智囊型"
                     "工程文化符号」登记，不作为历史考证"},
            {"item": "三教九流工程映射", "status": "needs_verify",
             "note": "12 条三教九流落法系理念的工程翻译而非原典本义；儒道二流与 "
                     "daoxue 系统同源交叉，详见该系统登记"},
        ],
    }
    return doc


# ---------------------------------------------------------------------------
# 桥接目标解析（七个既有系统 + zhuangzi 篇目/原则，目标必须真实存在）
# ---------------------------------------------------------------------------
def _target_ids(name: str, doc: dict) -> Optional[set]:
    """返回某既有概念系统的可桥接目标 id 全集（按各系统数据层结构）。"""
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
    if name == "datong":
        return ({c["id"] for c in doc.get("concepts", [])}
                | {p["id"] for p in doc.get("principles", [])})
    return None


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
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    # 2) 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc["by_domain"]):
        if inverted.get(d, []) != doc["by_domain"].get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # 3) 桥接无悬空（七系统 + zhuangzi，目标结构各自解析）
    cache: Dict[str, Optional[set]] = {}
    for b in doc["bridges"]:
        sysname, tgt = b["system"], b["target"]
        if sysname not in cache:
            cache[sysname] = _target_ids(sysname, load_other(sysname))
        target_ids = cache[sysname]
        if target_ids is None:
            errs.append(f"桥接目标系统未登记：{sysname}")
            continue
        kind, _, val = tgt.partition(":")
        if val not in target_ids or not kind:
            errs.append(f"桥接悬空：{sysname} 无目标 {tgt}")

    # 4) 用户端面 / 语言面事实必须是实测（正数 / 非空）
    facts = doc.get("user_face_facts") or {}
    for k in ("cli_subcommands", "webapi_actions", "gui_windows",
              "lang_total", "probe_verified", "comp_lang_needs"):
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
        if l["role"] != "craft" and l["count"] != len(doc["by_domain"].get(l["role"], [])):
            errs.append(f"layers[{l['role']}].count 漂移")

    # 6) needs_verify 非空（诚实边界：未核对原典 / 一名两译 / 文学形象必须挂牌）
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
    print(f"百工概念条目：{doc['_meta']['concept_total']} 个"
          f"（五偶与三教九流/场景 {doc['_meta']['concept_total'] - doc['_meta']['principle_total']} + "
          f"匠作原则 {doc['_meta']['principle_total']}）\n")
    print("按轴：")
    for d in doc["domains"]:
        print(f"  {d['domain']:<12} {len(doc['by_domain'].get(d['domain'], [])):>2}  {d['label']}")
    f = doc.get("user_face_facts", {})
    print(f"\n用户端面实测：CLI 子命令 {f.get('cli_subcommands')} / "
          f"GUI 窗口 {f.get('gui_windows')} / webapi ACTIONS {f.get('webapi_actions')}")
    print(f"deno 控制台 v{f.get('deno_console_version')} / "
          f"报告查看器 v{f.get('deno_report_viewer_version')}")
    print(f"语言面实测：plang {f.get('lang_total')} 条语言 / probe 实测 "
          f"{f.get('probe_verified')} 种 / comp 语言编译需要 {f.get('comp_lang_needs')} 条")
    print(f"桥接边：{doc['_meta']['bridge_count']} 条")
    by_sys: Dict[str, int] = {}
    for b in doc["bridges"]:
        by_sys[b["system"]] = by_sys.get(b["system"], 0) + 1
    for s, n in sorted(by_sys.items()):
        print(f"  → {s:<8} {n}")
    print(f"needs_verify：{len(doc['needs_verify'])} 项（引文未核对/一名两译/文学形象/工程翻译）")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    if "--check" in argv:
        # 防漂移：磁盘登记的实测值必须与当前源码/数据层实测一致
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
              f"用户端面·语言面事实与源码实测一致")
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
