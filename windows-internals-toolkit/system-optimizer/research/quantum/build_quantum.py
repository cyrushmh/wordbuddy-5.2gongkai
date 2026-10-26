#!/usr/bin/env python3
"""量子理念「概念系统」构建（以 wordbuddy-github 为主目录，v0.6.59）。

把量子计算/量子通信的知识体系按**九域**重组为概念系统，与 plang / netsys /
daoxue 同构（同目录 ``data/concepts/`` 数据层 + ``concepts/`` 只读层 + CLI/GUI 入口）：

    ├─ 域1 state     量子态表示（qubit/叠加/纠缠/布洛赫球/密度矩阵/测量公设）
    ├─ 域2 circuit   量子门与线路（Pauli/H-S-T/旋转/纠缠门/通用门集合/线路模型）
    ├─ 域3 algorithm 量子算法（Deutsch-Jozsa/Bernstein-Vazirani/Simon/Grover/Shor/QPE/
    │                VQE/QAOA/HHL/量子行走）
    ├─ 域4 hardware  硬件平台（超导/离子阱/中性原子/光子/硅自旋/退火/NISQ/耦合拓扑）
    ├─ 域5 error     纠错与噪声（T1·T2/门·读出误差/稳定子码/表面码/魔术态/缓解/阈值）
    ├─ 域6 network   量子网络（QKD 总览/BB84/E91/MDI-QKD/TF-QKD/中继/QKD 网络/PQC）
    ├─ 域7 toolchain 标准·语言·工具链（OpenQASM 3/QIR/ISO-IEC 4879/IEEE 7130/ITU-T
    │                Y.3800/ETSI GS QKD/FIPS 203·204·205/SDK 生态/量子体积）
    ├─ 域8 qsim      经典模拟与语义（本仓库自建 simulator + 同源验证链）
    └─ 域9 qkern     量子架构内核（v0.6.78 起）：LTS 基线/纯新增注册/QPU 模拟设备/
                     能量激发态模型/idle= 启动参数/4KiB 页纪律/补丁分发增量镜像——
                     真实资产 quantum-kernel/，宿主工具链诚实编译，不假装量子硬件

每条概念登记：gist（一句话）+ detail（机理）+ 标准依据（带核实状态）+ 桥接（到
plang / netsys / daoxue / datong / baigong 的既有概念，构建期强制校验无悬空）。

诚实边界：
  * 本仓库是**经典系统**工程工具箱，不含量子硬件、不接量子设备、不执行量子线路；
    本概念系统只做理念与标准登记。
  * 标准编号均标注核实状态（本轮联网核实 / needs_verify），不臆造发布状态。
  * qkern 域登记的是真实可编译的内核资产，但诚实边界锁死：宿主工具链产出宿主
    机器码，在真实量子硬件上运行不可达——两边都是事实，都不许抹。
  * 经典后量子密码（PQC）与量子计算区分登记，并桥接到本仓库既有 tls13/chrono 任务。

用法：
    python3 build_quantum.py            # 构建 data/concepts/quantum_taxonomy.json
    python3 build_quantum.py --check    # 校验（轴合法、桥接无悬空、标准引用完整）
    python3 build_quantum.py --report   # 打印九域统计与桥接图
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
OUT = (HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "concepts"
       / "quantum_taxonomy.json")
CONCEPTS_DIR = OUT.parent

SCHEMA = "quantum_taxonomy/v1"

# ---- 九域 ----
DOMAINS = [
    {"domain": "state", "label": "量子态表示",
     "note": "信息载体：量子比特、叠加、纠缠、混态描述与测量公设"},
    {"domain": "circuit", "label": "量子门与线路",
     "note": "操作原语：Pauli/H·S·T/旋转门/纠缠门/通用门集合与线路模型"},
    {"domain": "algorithm", "label": "量子算法",
     "note": "问题类与加速来源：相位/振幅放大、变分法、线性系统"},
    {"domain": "hardware", "label": "硬件平台",
     "note": "物理实现路线：超导/离子阱/中性原子/光子/硅自旋/退火，及现阶段定位"},
    {"domain": "error", "label": "纠错与噪声",
     "note": "从 NISQ 噪声缓解到容错量子计算的码与阈值"},
    {"domain": "network", "label": "量子网络",
     "note": "量子密钥分发、中继与量子互联网；含经典后量子密码（PQC）"},
    {"domain": "toolchain", "label": "标准·语言·工具链",
     "note": "OpenQASM 3、QIR、词汇标准、QKD 网络标准与开源 SDK 生态"},
    {"domain": "qsim", "label": "经典模拟与语义",
     "note": "本仓库自建构件（v0.6.65）：六比特经典模拟器 research/quantum/simulator/，"
             "含电压三极语义/相变矩阵/数制双读出/Born 观测与同源验证链——"
             "理念登记 + 可执行资产，在 O(2ⁿ) 墙内执行，不假装量子硬件"},
    {"domain": "qkern", "label": "量子架构内核",
     "note": "量子架构作为 Linux 内核架构（arch/quantum）的工程落法（v0.6.78 起，"
             "v0.6.79 补全）：LTS 基线、纯新增注册、QPU 模拟设备、能量激发态模型、"
             "idle= 启动参数、4KiB 页纪律与补丁分发增量镜像——真实可编译的真实资产，"
             "诚实边界：宿主工具链产出宿主机器码，不在真实量子硬件上运行"},
]

# ---- 标准登记册（status: verified=本轮核实 / needs_verify=待核实）----
STANDARDS: Dict[str, dict] = {
    "openqasm3": {
        "kind": "语言规约", "name": "OpenQASM 3.0",
        "status": "verified",
        "source": "openqasm.com 现行 live specification（2026-07 仍为现行版）",
        "note": "量子汇编语言：描述线路模型与测量，OpenQASM 2→3 扩展经典控制流",
    },
    "qir": {
        "kind": "中间表示规约", "name": "QIR（Quantum Intermediate Representation）",
        "status": "verified",
        "source": "QIR Alliance qir-spec（v2.0 用 opaque pointer，需 LLVM 16+；"
                  "v1.0 typed pointer 对应 LLVM ≤15；profiles: base/adaptive）",
        "note": "基于 LLVM IR 的量子程序中间表示：语言前端写一遍、目标后端各写一遍",
    },
    "iso-iec-4879": {
        "kind": "词汇标准", "name": "ISO/IEC 4879:2024 信息技术 量子计算 词汇",
        "status": "verified",
        "source": "iso.org（2024-06 发布；我国牵头制定的全球首个量子计算领域国际标准）",
        "note": "量子计算术语统一：基础理论/量子信息/量子处理/量子技术",
    },
    "ieee-7130": {
        "kind": "术语标准", "name": "IEEE 7130 量子技术定义（草案在册）",
        "status": "verified",
        "source": "IEEE Xplore P7130/D14（2026-08-05 在册，Status: Active-Draft，"
                  "979-8-8557-3786-8）；Quantum Week 2026 标准研讨会报道：Draft 14 "
                  "含 537 条术语/40 页，约 250 条投票意见待清，目标 2027-01 定稿",
        "note": "IEEE 侧量子计算术语标准化项目，与 ISO/IEC 4879 互补；"
                "**草案已核实、正式标准未发布**，引用时不得写成已发布标准",
    },
    "kernel.org-releases": {
        "kind": "发布索引", "name": "kernel.org 发布索引（releases.json）",
        "status": "verified",
        "source": "kernel.org/releases.json（2026-10 实读：mainline 7.3 / stable 7.2 / "
                  "longterm 六个分支 6.18·6.12·6.6·6.1·5.15·5.10）",
        "note": "内核版本基线选择的唯一权威口径：分支状态与发布日期以该 JSON 为准",
    },
    "kernel.org-kconfig": {
        "kind": "构建语言参考", "name": "kernel.org Kconfig 语言参考",
        "status": "verified",
        "source": "Documentation/kbuild/kconfig-language.rst（随 6.18.57 源码树分发）",
        "note": "arch/Kconfig 以 source \"arch/$(SRCARCH)/Kconfig\" 动态接入新架构的语言依据",
    },
    "kernel.org-misc": {
        "kind": "驱动接口参考", "name": "kernel.org misc 设备接口",
        "status": "verified",
        "source": "Documentation/driver-api/misc_devices.rst 与 drivers/char/misc.c"
                  "（随 6.18.57 源码树分发）",
        "note": "/dev/qpuN 以 misc 字符设备落地的接口依据（次设备号 10: 动态分配）",
    },
    "kernel.org-kbuild": {
        "kind": "构建系统参考", "name": "kernel.org Kbuild headers 规约",
        "status": "verified",
        "source": "Documentation/kbuild/headers_install.rst 与 arch/quantum/include/"
                  "（随 6.18.57 源码树分发）",
        "note": "UAPI 头文件导出与页粒度宏（PAGE_SHIFT）定义的构建侧依据",
    },
    "itu-y3800": {
        "kind": "ITU-T 建议书", "name": "ITU-T Y.3800 系列 量子密钥分发网络",
        "status": "verified",
        "source": "itu.int（Y.3800-2019《支持量子密钥分发的网络概述》；Y Suppl. 79 "
                  "论非量子密码在端到端密码服务中的角色，2023-11）",
        "note": "QKD 网络的网络侧架构与术语框架",
    },
    "etsi-qkd-014": {
        "kind": "ETSI 标准", "name": "ETSI GS QKD 014 密钥交付接口",
        "status": "verified",
        "source": "ETSI GS QKD 系列（014 定义 QKD 系统向应用交付密钥的接口，"
                  "公开产品文档广泛引用 etsi 014 密钥输出）",
        "note": "把 QKD 密钥经标准接口送到加密应用的工程约定",
    },
    "fips-pqc": {
        "kind": "NIST FIPS", "name": "NIST FIPS 203/204/205（后量子密码）",
        "status": "verified",
        "source": "NIST（2024-08 发布：203=ML-KEM、204=ML-DSA、205=SLH-DSA；"
                  "本仓库 chrono/tls13 任务已引用，保持一致）",
        "note": "经典计算上抗量子攻击的密码算法；与 QKD 互补而非替代",
    },
}

# ---- 概念条目 ----
# 字段：id, name, domain, gist, detail, standards[], bridges[], redline(可选), needs_verify(可选)
CONCEPTS: List[dict] = [
    # ============ 域1 量子态表示 ============
    {"id": "qubit", "name": "量子比特", "domain": "state",
     "gist": "二能级系统的信息载体：|ψ⟩ = α|0⟩ + β|1⟩，|α|² + |β|² = 1。",
     "detail": "与经典比特只能取 0 或 1 不同，量子比特的态是二维复希尔伯特空间中的"
               "单位向量；测量前处于叠加，测量后得到经典 0/1。n 个比特张成 2^n 维空间。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "superposition", "name": "叠加原理", "domain": "state",
     "gist": "基态的线性组合仍是合法态；并行性来自 2^n 维振幅的同时演化。",
     "detail": "叠加不是「同时是 0 和 1」的日常说法，而是振幅向量；只有能被干涉读出的"
               "相位关系才有计算意义。任何计算优势最终都可追到干涉与振幅放大。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "entanglement", "name": "量子纠缠", "domain": "state",
     "gist": "不能写成子系统张量积的态（Bell 态/EPR 对），非经典关联的来源。",
     "detail": "纠缠是量子通信与量子纠错码的核心资源；Bell 态 (|00⟩+|11⟩)/√2 的测量"
               "结果完全相关但不传递可用信号（不违反无信号定理）。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "bloch-sphere", "name": "布洛赫球", "domain": "state",
     "gist": "单量子比特的几何表示：球面点 (θ,φ) 唯一确定一个纯态。",
     "detail": "Bloch 向量长度 1 为纯态、小于 1 为混态；X/Y/Z 轴的六个极点即六种"
               "计算基与特征态。线路可视化（如 Quantikz）多以此投影。",
     "standards": [], "bridges": []},
    {"id": "density-matrix", "name": "密度矩阵", "domain": "state",
     "gist": "混态与去相干的形式化描述：ρ = Σ pᵢ|ψᵢ⟩⟨ψᵢ|。",
     "detail": "当系统与环境纠缠或我们只知道概率分布时，用 ρ 代替 |ψ⟩；"
               "冯·诺依曼熵与偏迹给出子系统约化描述。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "measurement", "name": "测量公设", "domain": "state",
     "gist": "Born 规则投影测量：得到本征值 k 的概率为 ⟨ψ|Pₖ|ψ⟩，测量后态塌缩到本征子空间。",
     "detail": "量子线路的经典输出只能来自测量；同时决定了不可克隆定理——未知量子态"
               "不能被完整复制，这是 QKD 安全性的物理根基。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "qudit-multi-level", "name": "多位元 qudit（d 级系统）", "domain": "state",
     "gist": "把 qubit 的 2 级推广到 d 级：|ψ⟩=Σ_{k=0}^{d-1}α_k|k⟩，容量 log₂(d) 比特"
             "（d=3 qutrit≈1.585 bit、d=5≈2.322 bit）。",
     "detail": "**可执行**（本仓 native/qudit.py 实证，纯标准库密度矩阵）："
               "门集用广义 Hadamard（DFT_d：U_jk=ω^{jk}/√d，ω=e^{2πi/d}）、循环移位 "
               "X_d（|k⟩→|(k+1) mod d⟩）与相位门 Z_d=diag(1,ω,…,ω^{d-1})——三者均酉"
               "（test_qudit 逐 d 断言 U·U†=I）。**诚实边界（关键）**：多位元的「元」是"
               "**能级数 d**，信息容量是 log₂(d) **比特**而非 d 比特——不把 d 级系统混同"
               "经典 d 位宽（那是把 d 级当二进制，属对量子信息的误读）；与既有 "
               "qubit/trit-register/numeral-convert 同轴但不同层（前者是物理载体，后者是"
               "经典读数）。",
     "standards": ["iso-iec-4879", "ieee-7130"], "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "实现语言",
          "how": "d 级态/门/通道以纯 Python 复数矩阵实现（native/qudit.py，零依赖）"},
         {"system": "daoxue", "target": "principle:fan-zhe", "relation": "类比",
          "how": "二生三、三生万物：量子层级从 qubit（二）经 qutrit（三）推广到 d 级"
                 "（万物），每一级是上一级的推广而非另起炉灶 ↔ 道德经 42 的生成链"
                 "（层级递推展开，非可逆回归——故记类比不记同构）"}]},
    {"id": "qudit-register", "name": "多位元 qudit 寄存器（内存交换位宽）", "domain": "state",
     "gist": "N 个 d 级 qudit 并联成寄存器，总容量 N·log₂(d) 比特；取 d=8（3 bit/qudit）、"
             "N=⌈位宽/3⌉，结合 CPU↔量子核的 π 链路内存交换参数，覆盖经典位宽 8/16/64/128。",
     "detail": "**可执行**（本仓 native/qudit.py 实证，类 QuditRegister）：单 qudit 容量"
               "log₂(d) 比特，N 个并联即 N·log₂(d) 比特——8/16/64/128 位元分别拆成"
               "3/6/22/43 个 d=8 qudit（128 位 → 8⁴³≈2¹²⁹ 维联合态）。**为什么必须"
               "结合内存交换参数**：联合态维数 8^N 绝不可物化为单一密度矩阵，故每个 qudit"
               "仅维持自身 d×d 局部态，CPU↔量子核的每一次交换（encode/gate/dissipation/"
               "measure）都经 PiLink 环形缓冲记录（即 native/quantum.py 的「内存交换参数」"
               "落点）——状态以分块方式经链路交换而非一次性铺满内存。**诚实边界**：不物化"
               "联合态；寄存器容量为分解后总容量；散逸按单 qudit 局部施加；不声称量子优势。"
               "**0033 扩展**：新增 register_roundtrip（值跨全部 N 个 qudit 做 d 进制 digit 编码、"
               "经 PiLink 逐交换、可选散逸+测量后解码回到整数）与 register_experiment（固定位宽扫 γ、"
               "可复现地统计平均/最大符号误码率 BER，诚实量化多位元寄存器在耗散信道下的损失；"
               "BER 随 γ 单调非减），CLI quantum qudexp 可打印该表并 --plot 生成纯标准库 SVG 曲线。"
               "**0034 扩展**：新增降维升维位元转化——dimension_profile / elevate_bits / "
               "reduce_bits / bit_convert / bit_convert_table（W 位经典整数升维成 N 个 d 级 qudit "
               "再降维回位元；精确离散升维↔降维同构 R∘E=I 无损，γ>0 量化耗散损失），CLI quantum "
               "bitconv 打印维数画像与往返、--table 展示 8/16/64/128 全宽维数比。诚实边界：升维/"
               "降维精确部分同构无损、联合态维数仅声明不物化、不宣称量子优势。",
     "standards": ["iso-iec-4879", "ieee-7130"], "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "实现语言",
          "how": "QuditRegister + register_report（native/qudit.py，零依赖；复用 native/quantum.py 的 PiLink）"}]},

    # ============ 域2 量子门与线路 ============
    {"id": "pauli-gates", "name": "Pauli 门 X/Y/Z", "domain": "circuit",
     "gist": "单比特三大门：X 翻转、Y/Z 绕轴 π 旋转（Z 引入相对相位）。",
     "detail": "X 是经典 NOT 的量子推广；Pauli 群还是稳定子码与错误诊断的基本词汇"
               "（X 型翻转/Z 型相位错误分别对应两类基本错误）。",
     "standards": ["openqasm3"], "bridges": []},
    {"id": "hadamard-phase", "name": "H/S/T 与相位门", "domain": "circuit",
     "gist": "H 制造叠加；S/T 逐步注入相位，T 是唯一的非 Clifford 单比特门。",
     "detail": "Clifford 层级（H·S·CNOT）可被经典高效模拟（Gottesman-Knill）；"
               "计算优势的关键在 T 门等非 Clifford 资源及其计数（T-count）。",
     "standards": ["openqasm3"], "bridges": []},
    {"id": "rotation-gates", "name": "旋转门 Rx/Ry/Rz", "domain": "circuit",
     "gist": "绕各轴任意角 θ 的旋转，是参数化线路（变分算法）的基本旋钮。",
     "detail": "VQE/QAOA 里的可训练参数即这些角度；硬件上多以脉冲校准实现，"
               "门保真度随角度深度变化。",
     "standards": ["openqasm3"], "bridges": []},
    {"id": "entangling-gates", "name": "纠缠门 CNOT/CZ/iSWAP", "domain": "circuit",
     "gist": "两比特门制造纠缠；用哪种原生纠缠门由硬件平台决定。",
     "detail": "超导路线原生多为 CZ/-iSWAP，离子阱多为 Mølmer-Sørensen（全连接）；"
               "线路编译要把逻辑纠缠门路由/合成到原生门上。",
     "standards": ["openqasm3"], "bridges": []},
    {"id": "universal-gatesets", "name": "通用门集合", "domain": "circuit",
     "gist": "{H, T, CNOT} 或 {Rz, Rx, CZ} 等集合可逼近任意量子线路（Solovay-Kitaev）。",
     "detail": "「通用」指表达能力；实际代价由合成深度与门数决定。不同硬件选不同"
               "通用集以对齐原生门。",
     "standards": ["openqasm3"], "bridges": []},
    {"id": "circuit-model", "name": "量子线路模型", "domain": "circuit",
     "gist": "比特线 + 门 + 测量组成的 DAG，是 OpenQASM 3 与 QIR 共同描述的对象。",
     "detail": "门按时间片（moment/layer）排列；含经典控制流时形成量子-经典混合程序"
               "（OpenQASM 3 的 for/if 与实时 classical 通道）。",
     "standards": ["openqasm3", "qir"], "bridges": []},

    # ============ 域3 量子算法 ============
    {"id": "deutsch-jozsa", "name": "Deutsch-Jozsa 算法", "domain": "algorithm",
     "gist": "判定函数是常值还是平衡值：量子 1 次查询，经典最坏 2ⁿ⁻¹+1 次。",
     "detail": "教学意义上的「首次显式加速」算法；加速来自查询 oracle 后的干涉相消，"
               "无实用场景但演示了相位反冲机制。",
     "standards": [], "bridges": []},
    {"id": "bernstein-vazirani", "name": "Bernstein-Vazirani 算法", "domain": "algorithm",
     "gist": "一次查询求出隐藏 n 位串 s（f(x)=x·s）；经典需 n 次。",
     "detail": "用 H 掩码与相位反冲把 s 直接写进测量基；同样是干涉读出隐藏参数。",
     "standards": [], "bridges": []},
    {"id": "simon", "name": "Simon 算法", "domain": "algorithm",
     "gist": "求隐藏周期串 s（f(x)=f(x⊕s)），指数级查询加速。",
     "detail": "周期结构的指数加速是 Shor 算法的思想原型（隐藏子群问题 HSP）。",
     "standards": [], "bridges": []},
    {"id": "grover", "name": "Grover 搜索算法", "domain": "algorithm",
     "gist": "无结构搜索 N 项只需 O(√N) 次查询（二次加速，且已证明最优）。",
     "detail": "机制是振幅放大：oracle 标记解、扩散算子反射；对穷举密钥类问题把"
               "安全位束等效减半（AES-128→64 量子比特意义）。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:tls13", "relation": "安全位束折算",
          "how": "Grover 使对称密钥等效安全位束约减半；TLS 套件强度评估须按抗量子口径折算"}]},
    {"id": "shor", "name": "Shor 算法", "domain": "algorithm",
     "gist": "多项式时间完成因子分解与离散对数，威胁 RSA/ECC/DH。",
     "detail": "以量子相位估计（QPE）找模幂周期；「先存后解」使今天截获的密文在未来"
               "量子机可解密——这是迁移 PQC 的时间论据。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:tls13", "relation": "威胁对象",
          "how": "RSA/ECC 被 Shor 威胁；tls13 任务的 RFC 9846 混合 KEM 即迁移前沿"},
         {"system": "netsys", "target": "module:cert", "relation": "证书算法迁移",
          "how": "证书链签名算法（ML-DSA/SLH-DSA）须随 FIPS 204/205 排期迁移"}],
     "redline": "算法登记不构成威胁评估结论；威胁论证须引用标准文献与本仓库任务口径"},
    {"id": "qpe", "name": "量子相位估计", "domain": "algorithm",
     "gist": "估计酉算符本征值相位到 n 比特精度，是 Shor 与量子化学的核心子程序。",
     "detail": "受控-U 幂序列 + 逆 QFT；迭代式 QPE 可省去深 QFT 换取浅线路。",
     "standards": [], "bridges": []},
    {"id": "vqe", "name": "变分量子本征求解器（VQE）", "domain": "algorithm",
     "gist": "参数化线路 + 经典优化器求哈密顿量基态能（量子测能量、经典调参数）。",
     "detail": "NISQ 时代的化学/材料主力方法；瓶颈在于参数-景观崎岖与测量次数"
               "（shot 数），缓解手段如零噪声外插。",
     "standards": [], "bridges": []},
    {"id": "qaoa", "name": "量子近似优化算法（QAOA）", "domain": "algorithm",
     "gist": "组合优化的变分线路近似：交替施加问题哈密顿量与混合层。",
     "detail": "从 MaxCut 出发推广；加速结论对问题实例敏感，尚无对经典启发式的"
               "普适优势证明——登记为路线而非定论。",
     "standards": [], "bridges": []},
    {"id": "hhl", "name": "HHL 线性系统求解", "domain": "algorithm",
     "gist": "对良条件稀疏线性系统给出指数加速（代价是把解读进量子态而非数字）。",
     "detail": "价值高度依赖条件数与读出方案；「读出一个经典答案即失去指数优势」，"
               "适合作量子机器学习的子程序。",
     "standards": [], "bridges": []},
    {"id": "quantum-walk", "name": "量子行走", "domain": "algorithm",
     "gist": "随机游走的量子对应：连续/离散两种，干涉导致不同传播速度。",
     "detail": "量子行走搜索、元素 distinctness 与通用子程序来源；与经典马尔可夫链"
               "分析工具体系不同。",
     "standards": [], "bridges": []},

    # ============ 域4 硬件平台 ============
    {"id": "superconducting", "name": "超导量子比特", "domain": "hardware",
     "gist": "transmon 电路比特，门速 ns 级，需 mK 稀释制冷；可扩产线制造。",
     "detail": "IBM/Google 等路线；耦合拓扑固定（重六角/heavy-hex），需要路由；"
               "门保真度近年进入「容错阈值之下」的两比特门区间。",
     "standards": ["qir"], "bridges": []},
    {"id": "trapped-ion", "name": "离子阱量子比特", "domain": "hardware",
     "gist": "激光操控囚禁离子；全连接、门保真度高、门速较慢（µs-ms）。",
     "detail": "IonQ/Quantinuum 等路线；移动离子实现「任意两比特纠缠」减少路由开销；"
               "扩展依赖分区的互联与光子互联。",
     "standards": [], "bridges": []},
    {"id": "neutral-atom", "name": "中性原子量子比特", "domain": "hardware",
     "gist": "光镊阵列固定里德堡原子，可重构拓扑、天然适合模拟晶格。",
     "detail": "QuEra/Pasqal 等路线；重排（rearrangement）与里德堡 blockade 门；"
               "模拟与通用计算双线推进。",
     "standards": [], "bridges": []},
    {"id": "photonic", "name": "光子量子比特", "domain": "hardware",
     "gist": "光子编码量子信息，室温传输、天然适配网络；多用测量基（MBQC）计算。",
     "detail": "PsiQuantum/Xanadu 等路线；确定性源与探测是工程瓶颈；与 QKD 光纤链路"
               "共享大量器件。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:network", "relation": "介质共享",
          "how": "QKD 与光子计算都依赖光纤/自由空间信道与既有光网运维体系"}]},
    {"id": "silicon-spin", "name": "硅自旋量子点", "domain": "hardware",
     "gist": "半导体工艺路线，CMOS 兼容潜力，尺寸小、功耗相对低。",
     "detail": "Intel 等路线；一致性与良率是其相对超导的卖点，仍处百比特量级验证期。",
     "standards": [], "bridges": []},
    {"id": "annealing", "name": "量子退火", "domain": "hardware",
     "gist": "D-Wave 专用机：绝热演化求优化问题低能态，非通用门模型。",
     "detail": "对特定二次无约束优化（QUBO）有工程价值；「量子加速」结论依问题而"
               "异，不宣称普适优于经典退火。",
     "standards": [], "bridges": []},
    {"id": "nisq", "name": "NISQ（含噪中等规模）", "domain": "hardware",
     "gist": "现阶段定位：数十到千级物理比特、无全面纠错，只能跑浅线路 + 缓解。",
     "detail": "Preskill 2018 提出的阶段判断；本概念系统所有算法/硬件条目均以此为"
               "现实边界，「有实用量子优势」的结论须逐问题给出证据。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "「知不知上」：坦承噪声边界与未证实的优势宣称，不臆造"}],
     "redline": "本仓库不接入、不评估任何真实量子设备；概念登记到此为止"},
    {"id": "connectivity", "name": "耦合拓扑与连接图", "domain": "hardware",
     "gist": "硬件原生两比特连接（coupling map）决定线路编译的路由与 swap 开销。",
     "detail": "线路深度往往被路由而非门本身主导；编译 pass 复杂度近似经典 FPGA 布局"
               "布线问题。",
     "standards": ["qir"], "bridges": [
         {"system": "plang", "target": "lang:rust", "relation": "实现语言",
          "how": "路由/调度等编译 pass 多用 Rust/C++ 实现（如 qirc 工具链）"}]},

    # ============ 域5 纠错与噪声 ============
    {"id": "decoherence", "name": "退相干 T1/T2", "domain": "error",
     "gist": "能量弛豫 T1 与相位退相干 T2 决定可用「相干窗口」。",
     "detail": "噪声是所有路线的共同瓶颈；门时间须远小于 T1/T2，读出误差单独计入。",
     "standards": [], "bridges": []},
    {"id": "level-dissipation", "name": "同位能级散逸（多级 T1/T2）", "domain": "error",
     "gist": "同一物理位（同一 site）内相邻能级间的耗散：振幅阻尼 |k⟩→|k−1⟩（T1）"
             "与非对角相位阻尼（T2）——qudit 的耗散是 qubit 退相干的 d 级推广。",
     "detail": "**可执行**（native/qudit.py）：振幅阻尼用 Kraus 算符 "
               "K0=|0⟩⟨0|+√(1−γ)Σ_{k≥1}|k⟩⟨k|、A_k=√γ|k−1⟩⟨k|，严格 CPTP、迹保持；"
               "相位阻尼 ρ'=(1−λ)ρ+λ Z_d ρ Z_d†，非对角元按 |i−j| 衰减。二者在**密度矩阵**上"
               "演化（耗散非酉，纯态→混态），故必须用 ρ 而非态矢量。诚实边界：单步均匀衰减模型，"
               "不建模真实器件的 T1/T2 频变、串扰与门误差谱；不接硬件。",
     "standards": ["iso-iec-4879"], "bridges": [
         {"system": "daoxue", "target": "principle:fan-zhe", "relation": "同构",
          "how": "能级只能向低跃迁的不可逆（放大器把可逆变不可逆）↔ 反者道之动："
                 "结构的「反向」在不同域各自成立，物理与义理互不隶属"}]},
    {"id": "gate-readout-errors", "name": "门误差与读出误差", "domain": "error",
     "gist": "单/两比特门保真度 + 读出保真度构成 NISQ 质量画像。",
     "detail": "基准测试多按随机基准（RB）报告；缓解（读出校正/零噪声外插）降误差"
               "不等于纠错——外推本身有系统风险。",
     "standards": [], "bridges": []},
    {"id": "stabilizer-code", "name": "稳定子码", "domain": "error",
     "gist": "用多个物理比特的共同测量诊断错误（如 Steane [[7,1,3]]）。",
     "detail": "CSS 码从经典线性码构造；稳定子测量本身是含错测量，需要解码器"
               "（MWPF/UF 等）实时处理综合症。",
     "standards": [], "bridges": []},
    {"id": "surface-code", "name": "表面码", "domain": "error",
     "gist": "主流量子纠错码：二维晶格、阈值约 1%、仅需近邻耦合，适配硬件拓扑。",
     "detail": "码距 d 决定纠错能力，逻辑错误率随 d 指数下降；一个逻辑比特需"
               "数百到数千物理比特（当前工程估算区间）。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "理念映射",
          "how": "「图难于其易」：先 mitigation 度日，再逐级放大码距到容错"}]},
    {"id": "magic-state", "name": "魔术态蒸馏", "domain": "error",
     "gist": "把含噪 T 态纯化为高质量魔术态，供容错 T 门使用。",
     "detail": "非 Clifford 门无法在稳定子码内横向完成，须注入蒸馏后的魔术态；"
               "蒸馏工厂长期占容错机大部分物理比特开销。",
     "standards": [], "bridges": []},
    {"id": "mitigation", "name": "噪声缓解（NISQ 手段）", "domain": "error",
     "gist": "读出误差校正、零噪声外插（ZNE）、概率误差消除等「软」手段。",
     "detail": "与量子纠错（QEC）区分：缓解是后处理/外推，不改编码；开销小但无"
               "严格保证，结论须标注方法学。",
     "standards": [], "bridges": []},
    {"id": "ft-threshold", "name": "容错阈值定理", "domain": "error",
     "gist": "物理错误率低于阈值时，逻辑错误率可指数压低——量子计算的可行性定理。",
     "detail": "阈值数值依码与噪声模型而定（表面码约 1% 量级）；工程上剩余差距在"
               "解码实时性与物理比特规模。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:tu-nan-yu-yi", "relation": "理念映射",
          "how": "阈值之下逐级放大：从易（小码距）到难（大码距）的工程节奏"}]},

    # ============ 域6 量子网络 ============
    {"id": "qkd-overview", "name": "量子密钥分发（QKD）总览", "domain": "network",
     "gist": "用量子信道（或测量设备无关设计）分发对称密钥，安全性基于物理定律。",
     "detail": "协议谱系：BB84 制备-测量、E91 纠缠基、BBM92、诱骗态、MDI-QKD、TF-QKD；"
               "工程形态为可信中继组网。QKD 补认证（仍需经典认证信道），不替代 PQC。",
     "standards": ["itu-y3800", "etsi-qkd-014"], "bridges": [],
     "redline": "本仓库不接入量子信道设备；QKD 只作标准与理念登记"},
    {"id": "bb84", "name": "BB84 协议", "domain": "network",
     "gist": "1984 年首个 QKD 协议：两组共轭基收发 + 基比对 + 抽样估误。",
     "detail": "窃听必然扰动量子态而被误码率暴露；后经诱骗态解决多光子脉冲的"
               "PNS 攻击缺口。",
     "standards": ["itu-y3800"], "bridges": []},
    {"id": "e91", "name": "E91 纠缠协议", "domain": "network",
     "gist": "1991 年基于 EPR 纠缠对的 QKD：Bell 不等式检验信道可信度。",
     "detail": "与 BB84 在安全性上等价（制备-测量 ↔ 纠缠基的对偶）；纠缠源部署"
               "成本更高，多用于研究型与卫星链路。",
     "standards": ["itu-y3800"], "bridges": []},
    {"id": "mdi-qkd", "name": "测量设备无关 QKD（MDI-QKD）", "domain": "network",
     "gist": "把探测端安全性风险转移到不可信中继测量，消除探测端攻击面。",
     "detail": "两用户向中继发态、中继做 Bell 态测量；现役城域 QKD 的主流安全形态。",
     "standards": ["itu-y3800"], "bridges": []},
    {"id": "tf-qkd", "name": "双场 QKD（TF-QKD）", "domain": "network",
     "gist": "单光子干涉把密钥率从线性损耗改为平方根损耗，延长无中继距离。",
     "detail": "对相位稳定性要求苛刻，是现场试验向千公里延伸的代表路线；工程上与"
               "经典相位补偿技术强耦合。",
     "standards": ["itu-y3800"], "bridges": [
         {"system": "netsys", "target": "module:network", "relation": "时钟同步依赖",
          "how": "TF-QKD 的远距相位对齐依赖经典网时钟同步（与 chrono 时间维相邻）"}]},
    {"id": "quantum-repeater", "name": "量子中继", "domain": "network",
     "gist": "纠缠交换 + 纠缠纯化把量子（纠缠）信道接力到城际/洲际尺度。",
     "detail": "需要量子存储（寿命）与预报式纠缠交换；目前处早期试验，"
               "「先可信中继、后量子中继」是现役共识路径。",
     "standards": ["itu-y3800"], "bridges": []},
    {"id": "qkd-network", "name": "QKD 组网（可信中继形态）", "domain": "network",
     "gist": "多对 QKD 链路经密钥中继/可信节点组成运营网络，向应用供密钥。",
     "detail": "ITU-T Y.3800 系列给出网络架构术语；ETSI GS QKD 014 定义向应用交付"
               "密钥的接口；与 SDN/编排协同。",
     "standards": ["itu-y3800", "etsi-qkd-014"], "bridges": [
         {"system": "netsys", "target": "module:meshnet", "relation": "承载选项",
          "how": "QKD 网络依赖底层 IP/光网与可编程 overlay 运维（meshnet/ZeroTier 类）"},
         {"system": "netsys", "target": "module:tls13", "relation": "密钥消费者",
          "how": "QKD 交付的密钥可作 TLS 1.3 预共享/对称材料，接口按 ETSI 014"}]},
    {"id": "pqc", "name": "后量子密码（PQC）", "domain": "network",
     "gist": "经典计算机上抗量子攻击的算法：ML-KEM/ML-DSA/SLH-DSA（FIPS 203/204/205）。",
     "detail": "与 QKD 互补而非替代：PQC 无需量子信道、可软件升级、证书链需整体迁移；"
               "混合模式（经典+PQC）是过渡期工程共识。",
     "standards": ["fips-pqc"], "bridges": [
         {"system": "netsys", "target": "module:tls13", "relation": "已承载",
          "how": "tls13 任务的 PQC 就绪评估与 RFC 9846 混合 KEM 检测承接本条"},
         {"system": "netsys", "target": "module:cert", "relation": "证书链迁移",
          "how": "证书模板/签名算法随 ML-DSA/SLH-DSA 排期迁移"}],
     "redline": "PQC 相关动作在本仓库只给指引不代改（承接 chrono/tls13 红线）"},

    # ============ 域6 量子网络 · 组网能力增强（v0.6.80）============
    # 把「组网」从单点 QKD 协议扩展到量子互联网栈/纠缠交换/隐形传态/拓扑/密钥管理，
    # 并与 netsys 组网模块（meshnet/distcompute/lldp-topo/netlink）显式桥接。
    {"id": "quantum-internet-stack", "name": "量子互联网协议栈", "domain": "network",
     "gist": "把 QKD/纠缠分发/量子中继编排为分层网络，向应用交付端到端量子能力。",
     "detail": "分层：物理（光纤/卫星）、链路（纠缠分发）、网络（纠缠路由/可信中继/"
               "量子中继）、应用（量子密钥/分布式量子计算）；与 ITU-T Y.3800 架构口径"
               "相邻，需经典控制网（SDN 编排）协同。",
     "standards": ["itu-y3800"], "bridges": [
         {"system": "netsys", "target": "module:meshnet", "relation": "承载与编排",
          "how": "量子互联网依赖底层 IP/光 mesh 与 SDN 编排（meshnet/ZeroTier/"
                 "sdn-openflow 类）做控制与管理面"},
         {"system": "netsys", "target": "module:net-arch", "relation": "架构同构",
          "how": "量子互联网的分层架构（物理/链路/网络/应用）与组网体系架构（net-arch 的"
                 "控制/数据/管理平面分治）同源"}]},
    {"id": "entanglement-swapping", "name": "纠缠交换", "domain": "network",
     "gist": "借贝尔态测量把两段独立纠缠链成更长的端到端纠缠——量子中继核心操作。",
     "detail": "与量子隐形传态共用贝尔测量原语；是量子中继与量子网络拓扑的原子操作；"
               "需预报式（heralded）成功信号与量子存储配合。",
     "standards": ["itu-y3800"], "bridges": [
         {"system": "netsys", "target": "module:distcompute", "relation": "分布式节点同构",
          "how": "纠缠交换的预报式成功信号分发与量子中继节点调度，与分布式算力网"
                 "（distcompute）的节点协同同构"},
         {"system": "netsys", "target": "module:qrelay-arch", "relation": "量子中继架构",
          "how": "纠缠交换是量子中继（qrelay-arch）的原子操作，预报式成功信号分发与"
                 "中继节点调度同构"}]},
    {"id": "quantum-teleportation", "name": "量子隐形传态", "domain": "network",
     "gist": "借助共享纠缠 + 经典信道，把未知量子态从一处传到另一处（不传输物质/载体）。",
     "detail": "需经典信道回传贝尔测量结果（受光速限制，不可超光速）；是量子网络与"
               "分布式量子计算的基元；与纠缠交换共用贝尔测量。",
     "standards": ["itu-y3800"], "bridges": [
         {"system": "netsys", "target": "module:network", "relation": "经典回传信道",
          "how": "隐形传态的经典比特回传依赖底层网络信道（network 轴）"},
         {"system": "netsys", "target": "module:qnic-hw", "relation": "经 QNIC 硬件",
          "how": "隐形传态的贝尔测量与经典回传在 QNIC 硬件（qnic-hw）上完成，"
                 "与经典网卡收发同一『接口即能力面』纪律"}]},
    {"id": "quantum-network-topology", "name": "量子网络拓扑与节点模型", "domain": "network",
     "gist": "量子网络的节点（QKD 终端/纠缠源/中继/可信节点）与链路（可信中继/纠缠分发/"
              "量子中继）的拓扑建模。",
     "detail": "与经典网络拓扑发现（LLDP）类比但对象不同：量子链路需纠缠保真度/误码率"
               "度量；拓扑状态含可信节点信任边界。",
     "standards": ["itu-y3800"], "bridges": [
         {"system": "netsys", "target": "module:lldp-topo", "relation": "拓扑发现类比",
          "how": "量子网络拓扑的状态采集与经典链路层拓扑发现（lldp-topo）同一『发现→建模』纪律"},
         {"system": "netsys", "target": "module:netlink", "relation": "组网层契约",
          "how": "量子网络节点互联复用经典组网层（netlink 本地自组网）的链路登记契约"},
         {"system": "netsys", "target": "module:net-arch", "relation": "架构同构",
          "how": "量子网络拓扑的节点/链路建模与组网体系架构（net-arch 的控制/数据/"
                 "管理平面分治）同一『分层建模』纪律"},
         {"system": "netsys", "target": "module:sysmesh", "relation": "系统互联协调同源",
          "how": "量子网络拓扑的跨节点协调与系统互联协调（sysmesh）同一『发现→建模→协调』纪律，"
                 "量子域只是 sysmesh 承载的一个成员系统"}]},
    {"id": "qkd-key-management", "name": "QKD 密钥管理", "domain": "network",
     "gist": "QKD 网络向应用交付与管理密钥：密钥池、密钥中继、密钥与业务绑定。",
     "detail": "ETSI GS QKD 014 定义密钥交付接口；密钥经可信中继逐跳转发或经量子中继"
               "端到端；需与 KMS/TLS 消费端对接。",
     "standards": ["itu-y3800", "etsi-qkd-014"], "bridges": [
         {"system": "netsys", "target": "module:cert", "relation": "密钥消费",
          "how": "QKD 交付密钥供证书/TLS 消费（cert 轴）"},
         {"system": "netsys", "target": "module:meshnet", "relation": "组网承载",
          "how": "密钥中继经底层 mesh/overlay 承载"},
         {"system": "netsys", "target": "module:qkd-arch", "relation": "QKD 架构",
          "how": "QKD 密钥管理交付接口（ETSI GS QKD 014）与 QKD 架构（qkd-arch 的"
                 "BB84/测量设备无关分发、与经典网络共纤）同源"}],
     "redline": "本仓库不接入量子信道设备；QKD 密钥管理只作标准与理念登记"},

    # ============ 域7 标准·语言·工具链 ============
    {"id": "openqasm3", "name": "OpenQASM 3.0", "domain": "toolchain",
     "gist": "开源量子汇编语言规约：线路 + 实时经典控制流（live spec）。",
     "detail": "由 IBM 主导、openqasm.com 维护 live specification；Qiskit 等工具链可"
               "互相导入导出，是线路级互换格式的事实候选。",
     "standards": ["openqasm3"], "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "宿主生态",
          "how": "Qiskit 等以 Python 为主入口输入/输出 OpenQASM 3"}]},
    {"id": "qir", "name": "QIR 量子中间表示", "domain": "toolchain",
     "gist": "基于 LLVM IR 的量子程序 IR：语言前端与硬件后端解耦。",
     "detail": "QIR Alliance 维护；v1.0（typed pointer, LLVM ≤15）/ v2.0（opaque "
               "pointer, LLVM ≥16）；profiles（base/adaptive）约束目标能力子集。",
     "standards": ["qir"], "bridges": [
         {"system": "plang", "target": "lang:rust", "relation": "实现语言",
          "how": "QIR 编译器/模拟器广泛用 Rust/C++（如 qirc、qir-qis）"}]},
    {"id": "iso-iec-4879", "name": "ISO/IEC 4879:2024 词汇标准", "domain": "toolchain",
     "gist": "全球首个量子计算领域国际标准（我国牵头）：术语与词汇。",
     "detail": "2024-06 发布，覆盖基础理论/量子信息/量子处理/量子技术；"
               "跨厂商沟通与标准引用先对齐词汇。",
     "standards": ["iso-iec-4879"], "bridges": []},
    {"id": "ieee-7130", "name": "IEEE 7130 量子技术定义（草案）", "domain": "toolchain",
     "gist": "IEEE 侧量子计算术语标准化项目（与 ISO/IEC 4879 互补）；草案在册、正式未发布。",
     "detail": "P7130 于 2017 年获批；2026-08-05 IEEE Xplore 在册 Draft 14（Active-Draft，"
               "537 条术语/40 页，979-8-8557-3786-8），Quantum Week 2026 报道约 250 条"
               "投票意见待清、目标 2027-01 定稿。诚实口径：**只可称草案，不可称已发布标准**。",
     "standards": ["ieee-7130"], "bridges": []},
    {"id": "itu-y3800", "name": "ITU-T Y.3800 系列", "domain": "toolchain",
     "gist": "ITU-T 的 QKD 网络建议书族：网络架构、术语与非量子密码角色。",
     "detail": "Y.3800-2019 为总览；Y Suppl. 79（2023-11）论非量子密码在端到端密码"
               "服务中的角色——即 PQC 与 QKD 的标准侧分工。",
     "standards": ["itu-y3800"], "bridges": []},
    {"id": "etsi-qkd-014", "name": "ETSI GS QKD 014 密钥交付接口", "domain": "toolchain",
     "gist": "QKD 系统向加密应用交付密钥的标准接口（ETSI 014 密钥输出）。",
     "detail": "QKD 厂商与密码应用解耦的关键约定；与 ETSI 的 QKD SDN 控制接口"
               "同属 GS QKD 系列。",
     "standards": ["etsi-qkd-014"], "bridges": []},
    {"id": "fips-pqc", "name": "NIST FIPS 203/204/205", "domain": "toolchain",
     "gist": "后量子密码三标准：ML-KEM（密钥封装）/ML-DSA/SLH-DSA（签名），2024-08 发布。",
     "detail": "NIST 后量子标准化终点；企业迁移的权威依据，与本仓库 chrono/tls13 "
               "任务引用一致。",
     "standards": ["fips-pqc"], "bridges": [
         {"system": "netsys", "target": "module:tls13", "relation": "任务侧承接",
          "how": "tls13/chrono 任务的 PQC 就绪评估引用同一组 FIPS 编号"}]},
    {"id": "sdks", "name": "开源 SDK 生态", "domain": "toolchain",
     "gist": "Qiskit / Cirq / PennyLane / PyQuil / Q# / Braket / stim 等公开工具链。",
     "detail": "按前端语言生态竞争（Python 为主）；stim 专注 Clifford 模拟与纠错"
               "研究；各 SDK 多以 OpenQASM/QIR 作为交换格式。",
     "standards": ["openqasm3", "qir"], "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "宿主语言",
          "how": "Qiskit/Cirq/PennyLane/PyQuil 均以 Python 为主入口"},
         {"system": "plang", "target": "lang:csharp", "relation": "宿主语言",
          "how": "Microsoft Q# 及 Quantum Development Kit 以 .NET/C# 为宿主"}]},
    {"id": "quantum-volume", "name": "量子体积（QV）等基准", "domain": "toolchain",
     "gist": "综合线路宽度/深度/连通性的复合基准：能跑多大的等宽等深方线路。",
     "detail": "方法论已核实：Cross 等 2019（Validating quantum computers using "
               "randomized model circuits, Phys. Rev. A 100, 032328）定义 QV=2ⁿ（n 为"
               "可通过的最大方线路规模），判据为重输出概率（HOP）>2/3 且 2σ 置信；"
               "2022 年 Quantum 期刊分析指出其置信区间覆盖不足等局限。数值随硬件代际"
               "变化（Quantinuum H2 已达 2²⁵，2025-09），本条只登记方法论不登记数字。",
     "standards": [], "bridges": []},

    # ================= 轴8 经典模拟与语义（v0.6.65 自建构件登记） =================
    # 本域条目全部指向 research/quantum/simulator/ 下的可执行资产：单文件 HTML 模拟器
    # （量子态/门/测量/数制六视图）+ extract_engine.py + verify3/4/5.mjs 同源验证链。
    # 口径：经典硬件在 O(2ⁿ) 墙内执行（上限 6 比特），是「可跑的教具」而非量子硬件。
    {"id": "qsim-engine", "name": "经典模拟引擎", "domain": "qsim",
     "gist": "本仓库自建的六比特量子态经典模拟器：复数状态矢量 + 稠密矩阵门演化。",
     "detail": "单文件 HTML（无外部依赖），JavaScript 引擎与 Python 无关、浏览器/node 双跑；"
               "2/3/6 三档比特数；门原语覆盖 H/X/Y/Z/S/T、旋转 P(θ)、CNOT、SWAP、QFT/QFT†；"
               "状态矢量为 2ⁿ 个 [re,im] 复数，每步门演化 O(2ⁿ)——n=6 即 64 复数，"
               "正是经典模拟的硬墙位置。verify3.mjs 16 条断言与交付代码同源（extract_engine.py "
               "从 HTML 原位提取、不改一行）。",
     "standards": [], "bridges": [
         {"system": "plang", "target": "lang:javascript", "relation": "宿主语言",
          "how": "引擎以 JavaScript 写在单文件 HTML 内，node 同源执行验证链"}]},
    {"id": "voltage-view", "name": "正负零电压语义", "domain": "qsim",
     "gist": "把量子振幅读成正/负/零三极电压：cos·sin 双轨之外的三值离散读数。",
     "detail": "同一份状态矢量三种读法：概率（叠加态格）、cos·sin 连续双轨（含仅 cos/"
               "仅 sin 档）、以及把每个基态映射为正电压/负电压/零电压的三极视图——"
               "三极读数对应「正、零、负」离散轴，与三进制值的古典读法同构；"
               "模拟器中是六态格下的一行电压条，n≤6 时逐基态着色。",
     "standards": [], "bridges": [
         {"system": "datong", "target": "concept:zhongdao", "relation": "同构",
          "how": "正负零三极 ↔ 中道守中：两极之间零位为轴（结构同构，电压/义理各自独立）"}]},
    {"id": "phase-matrix", "name": "相变矩阵", "domain": "qsim",
     "gist": "每个 qubit 一枚相变矩阵 P(θ)=diag(1, e^{iθ})：只改相位不改概率。",
     "detail": "模拟器面板上每 qubit 一枚 P(θ) 按钮，步进 90°/120° 两档；"
               "θ=90° 即 S、180° 即 Z、270° 即 S†（verify5.mjs 逐档断言等价）。"
               "六个相变矩阵连用即用户指令所指的「六个数字转换逻辑门」：相位偏转是"
               "三进制↔二进制导出链路上的相位侧原语。逆操作 P(−θ)=P(360°−θ) 可证可逆。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:fan-zhe", "relation": "同构",
          "how": "相变之逆（P(−θ)=P(360°−θ)）↔ 反者道之动：往复可逆是可计算化的形式"}]},
    {"id": "numeral-convert", "name": "数制转换层", "domain": "qsim",
     "gist": "6 比特 = 3 对，每对 1 个三进制位：6 bit 与 3 trit 双读数导出。",
     "detail": "两种经典编码：定长码（每 trit 2 bit，Сетунь 式）与紧 pack（3 trit=0..26 "
               "恰好装进 5 bit）；1 trit=log₂3≈1.585 bit 是硬汇率。模拟器数制视图把当前"
               "状态矢量的最大概率基态解成三进制值，并显示对码与无效对；"
               "verify5.mjs 以 27 组 trit↔bit 往返断言编码自洽。",
     "standards": [], "bridges": []},
    {"id": "trit-register", "name": "三进制寄存器", "domain": "qsim",
     "gist": "三进制值的量子对应：27 项等幅叠加（1/√27）+ 37 项缺失态。",
     "detail": "tritRegister() 生成 3 trit 全组合的等幅叠加——27 个实态各占 1/√27，"
               "余下 64−27=37 个基态概率为 0（含 11 个无效对码点），可作校验位资源；"
               "「27 实 + 37 虚 = 64」正是 6 比特全空间的另一种分账（verify5.mjs 实证）。",
     "standards": [], "bridges": []},
    {"id": "log-value-exchange", "name": "log 值交换（多级信道承载经典值）", "domain": "qsim",
     "gist": "以 log₂(d) 比特/符号容量，把经典值编码进 qudit 能级分布，经同位能级散逸"
             "信道「交换」后再解码——散逸越大解码值越下漂。",
     "detail": "**可执行**（native/qudit.py）：encode_log_amplitudes 把正实数 v 编成对数"
               "幅度态 α_k∝exp(−(k−μ)²/2σ²)、μ=log₂(v)；经振幅阻尼/相位阻尼后 "
               "decode_log_value 取 v̂=2^{Σk·p_k}。诚实数值（d=5, v=6）：γ(T1)=0 解码 6.15、"
               "γ=0.1→5.73、γ=0.5→4.35、γ=1.0→3.07——信息随能级向低泄漏而单调损失；"
               "整数交换 exchange_integer 以 n 个 d 级 qudit 承载 n·log₂(d) 比特，无损 γ=0 全对、"
               "γ 越大符号误码(ber)越高。**诚实边界**：这是经典数值模拟的对数幅度编码 + 耗散"
               "信道，**不宣称量子优势**；容量 log₂(d) 比特/符号，不是 d 比特。",
     "standards": [], "bridges": [
         {"system": "plang", "target": "lang:python", "relation": "实现语言",
          "how": "对数幅度编码/解码与耗散通道以纯 Python 复数密度矩阵实现"}]},
    {"id": "born-collapse", "name": "Born 观测与塌缩", "domain": "qsim",
     "gist": "按 |振幅|² 采样基态并塌缩重归一化：观测即扰动、中间无过渡态。",
     "detail": "measureQ() 按 Born 规则采样，塌缩后存活项重归一化（概率归 1）；"
               "「正、零、负，以及可能的过渡态为无」在模拟器中的落实——测量前基态"
               "间只有振幅关系，测量一击定值，不存在可观测的过渡中间态。"
               "verify4.mjs 以 Bell 态两次测量 + 10000 次频率实证。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:wu-zhi-you-yong", "relation": "同构",
          "how": "观测后概率分布归于「无」（分布消失只剩一态）↔ 无之以为用：无是边界的语法"}]},
    {"id": "missing-state", "name": "缺失态", "domain": "qsim",
     "gist": "网格中概率为零的空格：三进制对码里的无效对（11）与寄存器外的态。",
     "detail": "64 基态格按亮度=振幅作图时，缺失态显示为虚框空格；三进制对码中 11 为"
               "无效对（标红检出）——「无用之码点」反过来成为校验资源（27+37=64）。"
               "造化无数态与缺失态同源：六态是实、余数是无。",
     "standards": [], "bridges": []},
    {"id": "swap-cut", "name": "交换分区转场", "domain": "qsim",
     "gist": "SWAP 两寄存器水平对穿滑移：天罡↔地煞分区互换。",
     "detail": "SWAP 矩阵作用后两分区沿水平轴对穿换位，出格位置露出虚线缺失态；"
               "3 比特以上截断前 4 行并注明。用处是让「天罡元阳/地煞元阴」两半的"
               "位置互换可视化——分区对穿即六态架构里的转场原语（verify3.mjs SWAP 断言）。",
     "standards": [], "bridges": []},
    {"id": "qft-spectrum", "name": "QFT 谱分析", "domain": "qsim",
     "gist": "对状态矢量施加量子傅里叶变换：从位置侧读出频率侧谱线。",
     "detail": "QFT/QFT† 按 H+受控相变位序实现（QFT†∘QFT=I 有断言）；均匀叠加经 QFT "
               "后谱线收窄到单一基态——六态造化态（64 均匀）进、单峰谱出，是「混沌零态→"
               "造化」的正变换演示。谱视图即模拟器的傅里叶页。",
     "standards": [], "bridges": []},
    {"id": "yinyang-entangle", "name": "阴阳对缠", "domain": "qsim",
     "gist": "阴阳互根的可计算形式：(|罡000·煞111⟩+|罡111·煞000⟩)/√2。",
     "detail": "两个贝尔腿：天罡三比特与地煞三比特永相反（海明距 6 的全反对偶），"
               "单看任一侧都是 50/50 混沌、合看才见秩序——比乘积态「罡=1 煞=0」"
               "更接近阴阳互根。已抓出并修复首版漏清 v[0] 造成三腿态的 bug（verify4.mjs "
               "断言误差 1.0 即漏网之腿）。",
     "standards": [], "bridges": [
         {"system": "datong", "target": "concept:yiti-liangmian", "relation": "同构",
          "how": "阴阳对缠 ↔ 一体两面：两面互根互含（结构同构，物理/义理内涵各自独立）"}]},
    {"id": "six-phase-64", "name": "六态造化 64 态", "domain": "qsim",
     "gist": "六比特 64 基态 = 六十四卦：组合层同构，动力学不同构。",
     "detail": "q0..q5 依次映射电/磁/波/固/液/气六态（天罡=气液固、地煞=波磁电）；"
               "64 基态亮度=振幅、色相=相位，造化态即 64 均匀叠加。与《易》六十四卦"
               "在组合数上同构（2⁶=64）——这仅是编码层同构，卦变规则与量子演化动力学"
               "各自独立，不互相解释。",
     "standards": [], "bridges": [
         {"system": "datong", "target": "concept:dian", "relation": "同构",
          "how": "q0 电（激而迅发）↔ 六态位序第一位：组合层同构"},
         {"system": "datong", "target": "concept:ci", "relation": "同构",
          "how": "q1 磁（引而内聚）↔ 六态位序第二位：组合层同构"},
         {"system": "datong", "target": "concept:bo", "relation": "同构",
          "how": "q2 波（播而及远）↔ 六态位序第三位：组合层同构"},
         {"system": "datong", "target": "concept:gu", "relation": "同构",
          "how": "q3 固（凝而成体）↔ 六态位序第四位：组合层同构"},
         {"system": "datong", "target": "concept:ye", "relation": "同构",
          "how": "q4 液（流而随形）↔ 六态位序第五位：组合层同构"},
         {"system": "datong", "target": "concept:qi", "relation": "同构",
          "how": "q5 气（散而弥虚）↔ 六态位序第六位：组合层同构"}]},
    {"id": "qsim-asset", "name": "模拟器资产与验证链", "domain": "qsim",
     "gist": "同源验证链：extract_engine.py 原位提取 + verify3/4/5.mjs 31 条断言。",
     "detail": "资产位置 research/quantum/simulator/（v0.6.65 由 docs/quantum-viewer/ "
               "迁入 research 层，随构建流程走）；被测代码=交付代码——断言从 HTML 原位"
               "提取引擎块执行，不另抄一份；三轮验证抓出 7 个 bug（Y 门真值、permGate "
               "逆置换、GHZ 链序、v[0] 漏清等）全部登记在 docs/33。",
     "standards": [], "bridges": []},
    # ============ 域9 量子架构内核（v0.6.78 起；v0.6.79 补全至 7 条） ============
    # 本域条目全部指向 quantum-kernel/ 下的真实资产：Linux 6.18.57 LTS 完整树 +
    # arch/quantum 架构 + drivers/quantum 语义设备 + 补丁系列与 git 增量镜像。
    # 口径：真实可编译的真实资产；诚实边界——宿主工具链诚实编译产出宿主机器码，
    # 不在真实量子硬件上运行（硬件不可达，明文记账）。
    {"id": "qkern-lts", "name": "LTS 基线", "domain": "qkern",
     "gist": "量子架构内核以 Linux 6.18.57 longterm 为基线（当期最新 LTS）。",
     "detail": "6.18 是 2026 年当期最新长期分支（6.18.57，2026-10-15）；完整树本地保留"
               "（约 1.7GiB），git 侧以补丁+增量镜像上传，凭 fetch 脚本一键重建。"
               "六个长期分支并存（6.18/6.12/6.6/6.1/5.15/5.10，kernel.org releases.json "
               "2026-10 实测），一个不删。",
     "standards": ["kernel.org-releases"], "bridges": [
         {"system": "datong", "target": "concept:he-butong-yong", "relation": "分支并存",
          "how": "六个长期分支并存、一个不删 ↔ 和而不同（兼容多样）：基线可复现、"
                 "增量可审计，是人类文明重启计划『可长期重建的底座』在内核层的落法。"}]},
    {"id": "qkern-pure-additive", "name": "纯新增架构注册", "domain": "qkern",
     "gist": "arch/quantum 的注册是零修改的：动态 source 与默认映射让新目录本身即注册。",
     "detail": "arch/Kconfig 以 source \"arch/$(SRCARCH)/Kconfig\" 动态接入；顶层 Makefile "
               "默认 SRCARCH := $(ARCH)。既有 21 个架构原封（x86_64 defconfig 实测正常"
               "生成 4395 项配置）。唯一对既有文件的改动是 drivers/Kconfig、drivers/Makefile "
               "两处纯追加注册与 Documentation 索引一行。",
     "standards": ["kernel.org-kconfig"], "bridges": [
         {"system": "baigong", "target": "concept:feigong-shouyu", "relation": "不侵异类",
          "how": "『不能删除其他架构』与墨家非攻守御同构：新增不取代，扩展不驱逐——"
                 "工程的多元共存纪律。"}]},
    {"id": "qkern-qpu-device", "name": "QPU 模拟设备", "domain": "qkern",
     "gist": "/dev/qpuN 把 Π_k 门语义带进内核 UAPI。",
     "detail": "misc 字符设备：QPU_ENC（Π_k 门编码）/QPU_DEC（测量解码、真实坍缩模拟）/"
               "QPU_LINK_STATS（链路统计）/QPU_RESET。寄存器 8qubit 字节宽（上限 20 对齐"
               "用户态 MAX_QUBITS）、链路 ceil(2π)=7 槽、翻转语义契约（不复位连编 = XOR "
               "干扰）与用户态量子基座一一对应。",
     "standards": ["kernel.org-misc"], "bridges": [
         {"system": "netsys", "target": "module:netlink", "relation": "接口契约",
          "how": "QPU 设备的能力面以 ioctl 编号固化，用户态无需依赖实现细节——与 netlink "
                 "以消息类型编号固化内核-用户态契约是同一种接口纪律。"}]},
    {"id": "qkern-energy-excitation", "name": "能量激发态模型", "domain": "qkern",
     "gist": "quantum-energy.c：内核侧的离散能级与退相干语义模型，/proc 只读自报。",
     "detail": "arch/quantum/kernel/quantum-energy.c 随 vmlinux 一并链接：离散能级 "
               "E_n=n×ΔE、叠加布居、相位演化、干涉、测量坍缩、T1/T2 退相干与 Bell 纠缠"
               "记账全部可编译运行，经 /proc/quantum-energy 只读自报。诚实边界：这是"
               "经典代码对量子语义的模拟，不是量子处理器后端。",
     "standards": ["kernel.org-kbuild"], "bridges": [
         {"system": "datong", "target": "concept:yiti-liangmian", "relation": "同构",
          "how": "同一份 energy 模型有两面：内核面是真实可跑的经典 C 代码（编译、链接、"
                 "/proc 自报都实证过），量子面只是从 QM 借来的语义——一体两面，各自成立。"}]},
    {"id": "qkern-idle-param", "name": "idle= 启动参数", "domain": "qkern",
     "gist": "idle= 内核命令行参数选择空闲策略：mwait=基态等待（默认）。",
     "detail": "量子架构的空闲策略经启动参数固化：idle=mwait 时 CPU 停入 MONITOR/MWAIT "
               "基态等待而非空转；GRUB 与 LILO 双样本配置随补丁分发固化，重启后可复现。"
               "默认值即基态等待——无事可做时不作无谓干预。",
     "standards": ["kernel.org-kconfig"], "bridges": [
         {"system": "daoxue", "target": "principle:wuwei", "relation": "无为落法",
          "how": "CPU 无事可做时停摆等待而非空转耗能 ↔ 道常无为而无不为：不做无谓的"
                 "干预，让系统自化——内核空闲路径的无为侧落法。"}]},
    {"id": "qkern-page-discipline", "name": "4KiB 页纪律", "domain": "qkern",
     "gist": "量子架构页粒度固定 4KiB，与存储域 ext4 4K 对齐口径贯通。",
     "detail": "select HAVE_PAGE_SIZE_4KB + arch/quantum/include/asm/page.h 定 4KiB；"
               "存储域口径「字节流→12 位重组 4096 进制→4K 页」从用户态打包贯通到内核"
               "页粒度——同一条 4K 纪律的三层落法。",
     "standards": ["kernel.org-kbuild"], "bridges": [
         {"system": "baigong", "target": "concept:shengmo-guiju", "relation": "规矩同源",
          "how": "页粒度与块粒度同守一条 4K 规矩：规矩不因层次而变，正合绳墨规矩——"
                 "『不以规矩，不能成方圆』。"}]},
    {"id": "qkern-patch-distribution", "name": "补丁分发与增量镜像", "domain": "qkern",
     "gist": "patches/0001 补丁系列 + git 增量镜像：完整树不上传，凭脚本一键重建。",
     "detail": "补丁 0001 共 60 个文件段（125,258 字节），round-trip 验证可洁净回放；"
               "git 侧保持 Linux 目录结构上传增量镜像（arch/quantum、drivers/quantum、"
               "Documentation/quantum、include/uapi/linux/quantum.h），tarball sha256 "
               "记账（154,863,520 字节 ≈ 147.7 MiB）；fetch_kernel.sh 下载校验→打补丁→"
               "build.sh 三层验收，全链可复现。",
     "standards": ["kernel.org-releases"], "bridges": [
         {"system": "datong", "target": "principle:yinguo-bushuang", "relation": "因果可溯",
          "how": "每个补丁段 sha256 记账、round-trip 可回放、改动可逐一审计 ↔ 因果不爽"
                 "（可溯）：分发链上每一环都有据可查。"}]},
]


# engineering（工程落法）口径（v0.6.62 字段齐备化）：本仓库是**经典系统工程工具箱**，
# 不含量子硬件探针、不接入量子设备、不在真实量子硬件上执行量子线路。所以这里的落法一律是
# 「认知迁移 / 纪律转移」：这一条量子概念，对我们这个经典工具箱的判断与取舍产生了什么可迁移的影响；
# 若毫无影响，就如实写「仅认知登记，不改变本仓库任何行为」。
# v0.6.65 补注：qsim 域 12 条是唯一的例外——它们的落法是「可执行资产已交付」
# （research/quantum/simulator/，经典硬件 O(2ⁿ) 墙内 ≤6 比特，同源断言在跑）。
ENGINEERING: Dict[str, str] = {
    # 轴1 量子态表示
    "qubit": "落法：认知登记。唯一落点是通过数据量级判断——评估对称密钥强度时要计入 Grover 的"
             "平方根加速效应（有效安全位减半），本系统已把该折算写入 netsys:tls13 的套件评估口径。",
    "superposition": "落法：认知登记（已桥接 datong:yiti-liangmian 作结构同构）。对本仓库的实际影响"
                     "仅限安全性评估：搜索空间因叠加并行而折损，故对称密钥不要按经典位数自满。",
    "entanglement": "落法：认知登记。量子不可克隆与纠缠关联是 bb84/e91 的安全根基；对本工程的转移点是"
                    "那条老教训——信道不可信时，安全性不能靠「对方听不见」，只能靠物理层面的观测扰动。",
    "bloch-sphere": "落法：认知登记，不做可视化。原因很实际：三维球面需要额外图形依赖，"
                    "而本仓库 tkinter 面板只用二维 Canvas，不为一条认知条目引入 GUI 依赖。",
    "density-matrix": "落法：认知登记。混合态/噪声的刻画工具；本仓库不实现任何态演化，"
                      "但其思维方式是通用的：**用「带不确定度的状态」而非单点值描述系统**。",
    "measurement": "落法：纪律转移。量子测量「观测即扰动且不可重复」这条特性，反衬本仓库自己的"
                   "红线——只读诊断探针必须尽力无副作用，同一份现场观测结果必须可复现，"
                   "否则报告不可信（这也是 inspect 类动作一律只读的原因）。",
    "qudit-multi-level": "落法：**已交付**（native/qudit.py，纯标准库密度矩阵实现）。DFT_d 酉门 + "
                         "广义 X_d/Z_d 门集 + Kraus 耗散通道 + CPTP 迹保持验证全部可执行"
                         "（test_qudit 逐 d 断言 U·U†=I 与 trace=1）。对本仓库的诚实边界登记："
                         "多位元的「元」是能级数 d、容量是 log₂(d) **比特**而非 d 比特——"
                         "不把 d 级系统混同经典 d 位宽（comp 系统的位宽阶梯到 128 位 SIMD 为止，"
                         "qudit 无经典位宽轴）。",
    "qudit-register": "落法：**已交付**（native/qudit.py，类 QuditRegister + register_report + "
                      "register_roundtrip + register_experiment + register_experiment_plot + measure）。"
                      "把单 d 级系统 N 并联成寄存器（总容量 N·log₂(d) 比特），取 d=8（3 bit/qudit）、"
                      "N=⌈位宽/3⌉，结合 native/quantum.py 的 PiLink π 链路（内存交换参数）逐 qudit"
                      "交换而不物化 8^N 联合态——据此覆盖经典位宽 8/16/64/128。0033 扩展："
                      "register_roundtrip 让整数值跨全部 N 个 qudit 做 d 进制 digit 编码并经 PiLink 逐交换、"
                      "可选散逸+测量后无损/带漂解码；register_experiment 固定位宽扫 γ 可复现地统计平均/最大"
                      "符号误码率 BER（随 γ 单调非减）；CLI quantum qudexp 打印该表并 --plot 生成纯标准库 SVG。"
                      "0034 扩展：降维升维位元转化——dimension_profile/elevate_bits/reduce_bits/bit_convert/"
                      "bit_convert_table（W 位经典整数升维成 N 个 d 级 qudit 再降维回位元；精确离散升维↔降维同构 "
                      "R∘E=I 无损，γ>0 量化耗散损失），CLI quantum bitconv 打印维数画像与往返、--table 展示 "
                      "8/16/64/128 全宽维数比；诚实边界：升维/降维精确部分同构无损、联合态维数仅声明不物化。"
                      "诚实边界：不物化联合态、容量为分解后总容量、散逸按单 qudit 局部施加。",
    # 轴2 门与线路
    "pauli-gates": "落法：认知登记。X/Y/Z 作为基础翻转，与经典比特取反的相对应是理解起点；"
                   "本仓库不实现任何门操作。",
    "hadamard-phase": "落法：认知登记。H 门制造叠加的能力是 Grover/Shor 加速的来源；"
                      "对本工程的落点仍是「安全性评估」而非计算。",
    "rotation-gates": "落法：认知登记。连续旋转门对应 NISQ 变分算法的可调参数，"
                      "其精度直接受读出噪声限制——「参数连续、结果带噪」，这个组合在经典调参里同样危险。",
    "entangling-gates": "落法：认知登记。两比特纠缠门的保真度是整个线路的瓶颈；"
                        "可迁移的纪律是：**系统能力由最弱的那一级联环节决定**，"
                        "与本仓库七平台 CI 矩阵里最易失败的平台同理。",
    "universal-gatesets": "落法：纪律转移。通用门集的启示是「最小可用原语集」：只要一组有限原语可做任意"
                          "近似，就不必为每种需求新增特例。本仓库 native 动作白名单正是照这个思路收敛的。",
    "circuit-model": "落法：思维迁移。把计算表示为门（有向无环图）而非语句序列，对应工程里的"
                     "任务 DAG 与流水线分解；本仓库的清理流水线就是这种阶段管道的具体形态。",
    # 轴3 量子算法
    "deutsch-jozsa": "落法：认知登记。教科书式分离证明，无实际工程用途；其价值是让人看清"
                     "「一次查询定全局性质」这种反直觉能力的边界。",
    "bernstein-vazirani": "落法：认知登记。同上，属分离性示例；不与本仓库任何能力挂钩。",
    "simon": "落法：认知登记。Simon 问题是 Shor 的前身；理解它有助于判断「哪些结构能带来指数加速」，"
             "避免把任何量子加速传说都当真。",
    "grover": "落法：**有真实影响**——平方根搜索加速使对称密钥有效安全位减半（AES-128 按 64 位"
              "量级评估），本仓库在 netsys 的 TLS 套件强度口径里已按此折算推荐。",
    "shor": "落法：**有真实影响**——Shor 使 RSA/ECC 在足够规模的机器上失效，这直接推动 PQC 迁移。"
            "对本仓库的取舍：凡涉及证书链/签名的设计，默认向 FIPS 203/204/205 的 PQC 口径看齐，"
            "而不是继续加长 RSA 密钥。",
    "qpe": "落法：认知登记。相位估计是 Shor 与诸多算法的核心子程序；本仓库不实现。",
    "vqe": "落法：认知登记 + 诚实分级。NISQ 时代的变分算法，相对经典方法的优势**尚无定论**，"
           "故不把任何「量子优势」结论当作已然事实登记。",
    "qaoa": "落法：认知登记 + 诚实分级。同上；组合优化在 NISQ 上的实际优势仍处文献探讨阶段。"
            "教训转移：**新方法的收益宣称，要先看到规模化 scalability 证据才计入选型**。",
    "hhl": "落法：认知登记 + 谨慎口径。HHL 对线性方程组有理论加速，但有苛刻前提（稀疏/条件数/读写）"
           "，常被过度宣传。转移纪律：遇到指数级加速的宣称，先找它的前提条款。",
    "quantum-walk": "落法：思维迁移。量子游走是图上搜索与判定的框架；即便不做线路实现，"
                    "「用游走代替遍历」的经典版本在数据面较大的扫描场景同样管用。",
    # 轴4 硬件平台
    "superconducting": "落法：认知登记，不接触设备。其运行条件（极低温/屏蔽）正好划出本仓库的能力边界"
                       "——我们只做主机层面的运维与检测，不做物理层量子硬件的任何探测或控制。",
    "trapped-ion": "落法：认知登记，不接触设备。同上，仅保留技术路线差异（相干时间/连通性）的认知。",
    "neutral-atom": "落法：认知登记，不接触设备。技术路线差异登记，不声称本机具备相关环境。",
    "photonic": "落法：认知登记。光量子路线与 QKD 天然亲近（本系统 network 轴已登记相应协议）。",
    "silicon-spin": "落法：认知登记。工艺兼容 CMOS 是它的工程意义；仅登记不依赖。",
    "annealing": "落法：认知登记。量子退火是专用而非通用路线，选型前先确认问题能否落成 QUBO/Ising。",
    "nisq": "落法：纪律转移。NISQ 时代的核心约束是「无纠错条件下的有限线路深度」——"
            "这很像资源受限环境下的工程：**在有限预算里做尽可能可靠的事，并如实标注能力上限**。",
    "connectivity": "落法：认知登记。比特连通性限制迫使编译器做swap 插入；可迁移点是"
                    "「拓扑约束会吃掉名义性能」，与本仓库登记的拓扑与组网形态同理。",
    # 轴5 纠错与噪声
    "decoherence": "落法：认知登记。退相干是量子计算最大的工程敌人；可迁移纪律："
                   "任何系统都要问「状态能稳定维持多久」，本仓库的任务超时参数即是同理之物。",
    "level-dissipation": "落法：**已交付**（native/qudit.py）。同位能级散逸 = 振幅阻尼（γ/T1，"
                         "|k⟩→|k−1⟩）+ 相位阻尼（λ/T2）双通道，Kraus 算符严格 CPTP、"
                         "迹保持（test_qudit 对每个 γ/λ 断言 tr(ρ')=1）。实证：纯度随耗散"
                         "单调衰减、log 值随 γ 单调下漂（6.15→3.07）。诚实边界：单步均匀衰减"
                         "模型，不建模真实器件 T1/T2 频变、串扰与门误差谱，不接硬件。",
    "gate-readout-errors": "落法：纪律转移。门与读出误差必须先量化才谈得上纠错；对应到经典工程就是"
                           "「先度量，再治理」——本仓库所有优化动作都以先出只读报告为前提。",
    "stabilizer-code": "落法：认知登记。稳定子码以测量提取错误症状而不塌缩数据；其思路与经典系统的"
                       "冗余校验 / 错误检测码同源，值得作为容错设计范式理解。",
    "surface-code": "落法：纪律转移（最有迁移价值的一条）。表面码的阈值定理揭示：低于阈值时加大码距能持续压低错误率，越过阈值则再堆资源也无效。对应工程判断：任何容错机制都有适用区间，越界后要靠改机制而不是加预算。",
    "magic-state": "落法：认知登记。魔态蒸馏是非 Clifford 门的现实代价；可迁移点是"
                   "「通用性要用昂贵代价换取」。",
    "mitigation": "落法：纪律转移。错误缓解（先用有限手段压噪声，不假装已容错）对应本仓库的诚实分级"
                  "——做不到就挂 needs_verify，不做粉饰。datong 的「净化禁忌」已与此条桥接。",
    "ft-threshold": "落法：纪律转移。容错阈值是所有纠错工程的准入线；判断标准是量化的，"
                    "不是感觉的——与本仓库「构建期实测 + --check 逐键比对」同一精神。",
    # 轴6 量子网络
    "qkd-overview": "落法：认知登记。**要记住的区分**：QKD 解决的是密钥分发，不是数据加密，"
                    "且需要专用链路，不替代端到端加密协议。",
    "bb84": "落法：认知登记。BB84 的安全性来自观测扰动可被发现；登记服务于 ITU/ETSI 标准口径理解。",
    "e91": "落法：认知登记。纠缠型协议，安全性基于 Bell 不等式违背。",
    "mdi-qkd": "落法：认知登记。测量设备无关型 QKD，把探测器侧信道攻击面摘掉，是工程实践里的重要改进。",
    "tf-qkd": "落法：认知登记。双场 QKD 提升了传输距离的性能上限；仅登记。",
    "quantum-repeater": "落法：认知登记。中继站是长距离量子网络的瓶颈件，尚未实用化（诚实登记）。",
    "qkd-network": "落法：认知登记。ITU-T Y.3800 系列给出 QKD 网络的架构口径；仅作标准理解。",
    "pqc": "落法：**最有落地价值的一条**——后量子密码（FIPS 203 ML-KEM / 204 ML-DSA / 205 SLH-DSA）"
           "是本仓库真正能用上的部分：凡将来要选密钥协商或签名算法，优先向这三份标准推荐的算法，"
           "不要自研也不要继续依赖纯 RSA/ECC 路线。",
    # 域6 量子网络 · 组网能力增强（v0.6.80）
    "quantum-internet-stack": "落法：认知登记。量子互联网的分层架构（物理/链路/网络/应用）与 ITU-T "
                              "Y.3800 口径相邻；仅作架构理解与跨系统桥接（netsys meshnet/sdn-openflow）。",
    "entanglement-swapping": "落法：认知登记。纠缠交换是量子中继与量子网络的原子操作，与分布式算力网"
                              "（netsys:distcompute）的节点协同同构，仅作理念映射。",
    "quantum-teleportation": "落法：认知登记。隐形传态依赖经典回传信道（netsys:network），"
                              "受光速限制不可超光速；仅作原理登记。",
    "quantum-network-topology": "落法：认知登记。量子网络拓扑的状态采集与经典链路层拓扑发现"
                                 "（netsys:lldp-topo）同一『发现→建模』纪律，仅作类比。",
    "qkd-key-management": "落法：认知登记。QKD 密钥交付接口（ETSI GS QKD 014）与密钥消费端"
                           "（netsys:cert/tls13）对接；本仓库不接入量子信道设备，仅作标准登记。",
    # 轴7 标准语言工具链
    "openqasm3": "落法：认知登记，不涉及编译器实现。可借鉴的是「用 IR 统一不同后端」这一思路，"
                 "与本仓库多语言/多平台用同一套 JSONL 契约的想法同构。",
    "qir": "落法：认知登记。基于 LLVM IR 的量子中间表示；登记其存在与定位，不声称支持。",
    "iso-iec-4879": "落法：标准登记（已 verified）。编号口径与本仓库 rfc_catalog 同一规矩："
                    "编号必须可核，标题须回填，不能凭印象写标准号。",
    "ieee-7130": "落法：标准登记（**已核实为草案**）。IEEE Xplore P7130/D14（2026-08-05）"
                 "在册 + Quantum Week 2026 报道双源互证：537 条术语、目标 2027-01 定稿。"
                 "诚实口径：本仓库所有引用只写「草案」，绝不写成已发布国际标准——"
                 "引文的诚实纪律同此。",
    "itu-y3800": "落法：标准登记（已 verified）。QKD 网络架构系列，用作 network 轴条目的依据。",
    "etsi-qkd-014": "落法：标准登记（已 verified）。QKD 密钥交付接口；其「密钥即服务」的接口化思路可借鉴。",
    "fips-pqc": "落法：**有落地指引**——FIPS 203/204/205 是本仓库在密码选型上唯一肯直接采纳的口径；"
                "它把「抗量子」从讨论变成可落地选型。",
    "sdks": "落法：未落地。本仓库不安装也不调用任何量子 SDK；列这一条是为了明确「我们用不上」，"
            "免得日后有人以为环境里应当有。",
    "quantum-volume": "落法：纪律转移。量子体积试图用一个标量概括机器能力——这恰恰是要警惕的做法"
                      "（过于压缩的指标会掩盖真实瓶颈；2022 年 Quantum 期刊分析亦指出其置信"
                      "区间覆盖不足）。本仓库倾向于多面实测（参考 plang 的八面能力契约评估），"
                      "而不是单指标论英雄。",
    # 轴8 经典模拟与语义（可执行资产已交付，随 research 层走）
    "qsim-engine": "落法：**已交付可执行资产**——research/quantum/simulator/ 单文件 HTML "
                   "模拟器 + 同源验证链；给本仓库的落点是「用可跑的教具取代空口谈概念」，"
                   "且验证链纪律（被测代码=交付代码）可复用到其他模块的回归测试。",
    "voltage-view": "落法：已交付（模拟器电压视图）。三极读数示范了「同一份数据、三种离散化口径」，"
                    "与本仓库报告查看器的多档详略切换同构。",
    "phase-matrix": "落法：已交付（模拟器相变面板，90°/120° 步进）。只改相位不改概率的操作，"
                    "示范了「最小作用原语」：一次偏转、可逆、可组合。",
    "numeral-convert": "落法：已交付（模拟器数制视图）。三进制↔二进制双读数是本仓库数字进制口径的"
                       "唯一定量出口：评估任何进制相关指标时记住 1 trit=1.585 bit 的硬汇率。",
    "trit-register": "落法：已交付（27 实 + 37 虚 = 64 的分账示范）。「实态之外的缺失态可作校验位」"
                     "这一思路可迁移到任何 2ⁿ 定长编码的余数利用。",
    "born-collapse": "落法：已交付（measureQ Born 采样 + 塌缩重归一化）。「观测即扰动、"
                     "不可复盘单次结果」反制了本仓库诊断必须只读、必须可复现的红线——两边的"
                     "规矩恰好互补：模拟器里允许塌缩，探针里绝不允许。",
    "missing-state": "落法：已交付（虚框缺失态 + 无效对标红）。「把无用码点显式画出来」的"
                     "视觉纪律，可直接用于报告查看器中标注未覆盖平台/未执行用例。",
    "swap-cut": "落法：已交付（两寄存器对穿滑移）。分区互换的转场动画是「状态迁移可视化」"
                "的最小示范；本仓库 GUI 里的分页切换可参考其让出位置的处理。",
    "qft-spectrum": "落法：已交付（QFT/QFT† 谱视图）。QFT†∘QFT=I 的正逆往返是本仓库"
                    "「任何转换都要有回路可验证」纪律的量子侧实例。",
    "yinyang-entangle": "落法：已交付（阴阳对缠预设 + 修复 v[0] 漏清 bug）。意义在语义纠正："
                        "阴阳不是两个独立乘积态（两仪分张），而是互根互含的纠缠——"
                        "写概念系统时同构关系必须落到可计算形式上才敢下笔。",
    "six-phase-64": "落法：已交付（64 基态网格 + 六态标签）。64=2⁶=六十四卦只是组合层同构；"
                    "登记它是为了明确边界：卦变规则与量子演化动力学各自独立，不互相解释。",
    "log-value-exchange": "落法：**已交付**（native/qudit.py）。encode_log_amplitudes → "
                          "振幅/相位阻尼信道 → decode_log_value 完整往返可执行；"
                          "诚实数值（d=5, v=6）：γ=0 解码 6.15、γ=0.1→5.73、γ=0.5→4.35、"
                          "γ=1.0→3.07——信息随能级向低泄漏而单调损失；exchange_integer "
                          "以 n 个 d 级 qudit 承载 n·log₂(d) 比特，无损 γ=0 全对。"
                          "诚实边界：经典数值模拟的对数幅度编码 + 耗散信道，不宣称量子优势；"
                          "容量 log₂(d) 比特/符号，不是 d 比特。",
    "qsim-asset": "落法：**资产与验证链本身**。extract_engine.py + verify3/4/5.mjs 共 31 条断言"
                  "证明「测试即契约」在跨语言（HTML/Python/JS）资产上同样可行——"
                  "这是本轮指令最可复用的工程产出。",
    # 轴9 量子架构内核（真实资产：quantum-kernel/，可编译、可验收、可分发）
    "qkern-lts": "落法：**基线已复现到可构建**。quantum-kernel/scripts/fetch_kernel.sh 下载校验 "
                 "linux-6.18.57.tar.xz（sha256 记账）→ 打 patches/0001 → scripts/build.sh "
                 "三层验收。实测：defconfig 全解析、ARCH=quantum 整树编译链接通过（vmlinux "
                 "真实产出，宿主工具链诚实编译——不假装有量子处理器后端），15 个 quantum_* "
                 "符号在 nm 清单内在位。git 侧只传补丁+增量镜像（保持 Linux 目录结构），"
                 "完整树 1.7GiB 凭脚本一键重建。",
    "qkern-pure-additive": "落法：**零修改经 diff 实证**。diff -rq 原始 tarball 解压树与构建树："
                           "仅 3 个既有文件变更——drivers/Kconfig、drivers/Makefile 两处纯追加"
                           "注册与 Documentation/index.rst 索引一行；21 个既有架构目录零改动"
                           "（含文件内容级比对）。回归实证：x86_64 defconfig 正常生成"
                           "（4395 项配置）证明接入无破坏。补丁 0001 共 60 个文件段、"
                           "round-trip 验证可洁净回放。",
    "qkern-qpu-device": "落法：**设备+语义双层已交付**。drivers/quantum/qpu-dev.c（misc 设备）"
                        "+ qpu-gates.c（Π_k 置换门表，含 qpu-gates.h 契约）随 vmlinux "
                        "一并链接；ioctl 编号固化的能力面经 QARCH 六报告实测（设备令牌、"
                        "PAGE_SHIFT 12、build/.config 计数 3=y/10 总、vmlinux 产物字节数）。",
    "qkern-energy-excitation": "落法：**可编译运行的语义模型**。arch/quantum/kernel/"
                               "quantum-energy.c 把退相干（T1/T2）、测量坍缩、Bell 纠缠"
                               "记账写成内核态可执行代码并经 /proc/quantum-energy 只读"
                               "自报——落点是「量子语义可以被经典代码完整模拟且自证」，"
                               "同时用诚实边界锁死：这是模拟，不是量子硬件。",
    "qkern-idle-param": "落法：**双启动样本固化**。idle=mwait 经 GRUB 与 LILO 两份样本配置"
                        "写实，重启后可复现；给本仓库的落点是「启动参数是配置的硬边界」——"
                        "与 settings.py 阈值注册表同一纪律：行为差异必须可追溯到一处显式配置。",
    "qkern-page-discipline": "落法：**页纪律贯穿到构建产物**。arch/quantum/include/asm/page.h "
                             "定 PAGE_SHIFT 12，Kconfig select HAVE_PAGE_SIZE_4KB；构建验收"
                             "读 build/.config 实证 CONFIG_HAVE_PAGE_SIZE_4KB 在位，与 qstore "
                             "存储域 4K 对齐口径（sysfs→lsblk→statvfs 三级核验）形成同源"
                             "不同层的两条证据链。",
    "qkern-patch-distribution": "落法：**分发链全环可审计**。补丁 round-trip 回放 + tarball "
                                "sha256 记账 + git 增量镜像保持 Linux 目录结构，使「完整树"
                                "不上传也能一键重建」成为可验证的承诺而非说法——这套"
                                "「补丁+镜像+脚本」分发法可直接复用到本仓库其他大资产。",
}
def apply_engineering(concepts: List[dict]) -> None:
    """给每个概念注入「工程落法」（同上口径：认知迁移 / 纪律转移，不假装有量子能力）。"""
    for c in concepts:
        eng = ENGINEERING.get(c["id"])
        if eng:
            c["engineering"] = eng

# v0.6.62 续：回链大同（使综摄系统双向可达，仅确凿关系）
DATONG_BACKLINKS = [
    {"from": "quantum:superposition", "system": "datong", "target": "concept:yiti-liangmian",
     "relation": "同构", "how": "叠加两面性 ↔ 一体两面：结构同构，物理/神学内涵各自独立"},
    {"from": "quantum:mitigation", "system": "datong", "target": "concept:jinghua-jinji",
     "relation": "同构", "how": "量子纠错缓解 ↔ 净化禁忌：先列不可，再论可行（白名单制）"},
]


def build() -> dict:
    apply_engineering(CONCEPTS)
    idx = {c["id"]: c for c in CONCEPTS}

    # 桥接（到既有概念系统：plang 语言 / netsys 模块 / daoxue 原则）
    bridges: List[dict] = []
    for c in CONCEPTS:
        for b in c.get("bridges", []):
            bridges.append({
                "from": f"quantum:{c['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    bridges.extend(DATONG_BACKLINKS)

    # 反查视图
    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in CONCEPTS:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    std_refs = sorted({s for c in CONCEPTS for s in c.get("standards", [])})

    return {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/quantum/build_quantum.py",
            "generated_at": None,  # 构建时回填（见 main）
            "main_root": "wordbuddy-github",
            "title": "量子理念概念系统（以 wordbuddy-github 为主目录）",
            "system_root": "wordbuddy-github",
            "version": "0000.0000.0000.0069.20261026",
            "concept_total": len(CONCEPTS),
            "axes": ["domain"],
            "domains": len(DOMAINS),
            "bridge_count": len(bridges),
            "standard_refs": std_refs,
            "honesty": "本仓库为经典系统工程工具箱，不含量子硬件探针、不接入量子设备、"
                       "不在真实量子硬件上执行量子线路；本系统只做理念与标准登记。"
                       "算法结论（如 QAOA 优势）按文献现状登记，不夸大为定论。"
                       "qsim 域（v0.6.65）登记的是本仓库自建的**经典**模拟器"
                       "（research/quantum/simulator/）：在经典硬件的 O(2ⁿ) 墙内执行 "
                       "≤6 比特线路，是「可跑的教具」而非量子硬件——n=30 起即不可承受，"
                       "同源断言（verify3/4/5.mjs）随资产在原地维护。多数条目刻意不设落地"
                       "桥接——本仓库无对应构件，宁可孤立也不臆造落地关系（v0.6.62）。",
            "redline_note": "概念登记不构成威胁评估或采购建议；PQC/QKD 相关动作只给指引"
                            "不代改（承接 chrono/tls13 既有红线）。",
            "needs_verify_note": "标准核实状态逐条标注（verified=本轮联网核实 / "
                                 "needs_verify=待核实），不臆造发布状态。",
        },
        "domains": DOMAINS,
        "standards": STANDARDS,
        "concepts": CONCEPTS,
        "bridges": bridges,
        "by_domain": by_domain,
    }


def check(doc: dict) -> List[str]:
    errs: List[str] = []
    sys.path.insert(0, str(HERE.parents[1] / "src" / "python"))
    from sysweeper.concepts import _common

    concepts_dir = HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "concepts"

    def load_other(name: str) -> dict:
        return json.loads((concepts_dir / f"{name}_taxonomy.json")
                          .read_text(encoding="utf-8"))

    # 1) 域名合法、id 唯一、gist/detail 非空
    valid_domains = {d["domain"] for d in doc["domains"]}
    ids = set()
    for c in doc["concepts"]:
        if c["id"] in ids:
            errs.append(f"概念 id 重复：{c['id']}")
        ids.add(c["id"])
        if c["domain"] not in valid_domains:
            errs.append(f"{c['id']} 域 {c['domain']} 未登记")
        if not c.get("gist") or not c.get("detail"):
            errs.append(f"{c['id']} 缺 gist/detail")
        # v0.6.62 字段齐备：每个概念必须有「工程落法」（认知迁移 / 纪律转移口径）
        if not str(c.get("engineering") or "").strip():
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    # 2) 标准引用完整且状态合法
    for key, s in doc["standards"].items():
        if s["status"] not in ("verified", "needs_verify"):
            errs.append(f"标准 {key} 状态非法：{s['status']}")
        if s["status"] == "verified" and not s.get("source"):
            errs.append(f"标准 {key} 标 verified 但缺 source（核实来源）")
        if s["status"] == "needs_verify" and not s.get("reason"):
            errs.append(f"标准 {key} 标 needs_verify 但缺 reason")
    for c in doc["concepts"]:
        for s in c.get("standards", []):
            if s not in doc["standards"]:
                errs.append(f"{c['id']} 引用未登记标准 {s}")

    # 3) 概念级 needs_verify 必须带原因
    for c in doc["concepts"]:
        if c.get("needs_verify") is False or c.get("needs_verify") is None:
            continue
        if not c.get("needs_verify"):
            errs.append(f"{c['id']} 标了 needs_verify 但无原因")

    # 4) 桥接目标必须在目标系统真实存在（无悬空边）
    plang = load_other("plang")
    netsys = load_other("netsys")
    daoxue = load_other("daoxue")
    datong = load_other("datong")
    baigong = load_other("baigong")
    plang_langs = set(plang.get("lang_index", {}))
    netsys_mods = {m["id"] for m in netsys.get("modules", [])}
    dx_principles = {p["id"] for p in daoxue.get("principles", [])}
    datong_ids = {c["id"] for c in datong.get("concepts", [])} | {
        p["id"] for p in datong.get("principles", [])}
    baigong_ids = {c["id"] for c in baigong.get("concepts", [])}
    ns_axes = set()
    for l in netsys.get("layers", []):
        ns_axes.add(l["layer"])
    for f in netsys.get("forms", []):
        ns_axes.add(f["form"])
    for n in netsys.get("natures", []):
        ns_axes.add(n["nature"])

    for b in doc["bridges"]:
        sysname, tgt = b["system"], b["target"]
        kind, _, val = tgt.partition(":")
        if sysname == "plang":
            if kind == "lang" and val not in plang_langs:
                errs.append(f"桥接悬空：plang 无语言 {val}")
            elif kind in ("arch", "model", "domain") and val != "*" \
                    and val not in plang_langs:
                errs.append(f"桥接悬空：plang 轴 {kind}:{val} 无对应条目")
            elif kind not in ("lang", "arch", "model", "domain", "standard"):
                errs.append(f"plang 桥接 target 形态未知：{tgt}")
        elif sysname == "netsys":
            if kind == "module" and val not in netsys_mods:
                errs.append(f"桥接悬空：netsys 无模块 {val}")
            elif kind in ("layer", "form", "nature") and val != "*" \
                    and val not in ns_axes:
                errs.append(f"桥接悬空：netsys 轴 {kind}:{val} 未登记")
            elif kind not in ("module", "layer", "form", "nature"):
                errs.append(f"netsys 桥接 target 形态未知：{tgt}")
        elif sysname == "daoxue":
            if kind == "principle" and val not in dx_principles:
                errs.append(f"桥接悬空：daoxue 无原则 {val}")
            elif kind != "principle":
                errs.append(f"daoxue 桥接 target 形态未知：{tgt}")
        elif sysname == "datong":
            if kind not in ("concept", "principle") or val not in datong_ids:
                errs.append(f"桥接悬空：datong 无{'原则' if kind == 'principle' else '概念'} {val}")
        elif sysname == "baigong":
            if kind == "concept" and val not in baigong_ids:
                errs.append(f"桥接悬空：baigong 无概念 {val}")
            elif kind != "concept":
                errs.append(f"baigong 桥接 target 形态未知：{tgt}")
        else:
            errs.append(f"桥接目标系统未登记：{sysname}")

    # 5) 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    if inverted != {k: v for k, v in doc["by_domain"].items()}:
        for d in set(inverted) | set(doc["by_domain"]):
            if inverted.get(d, []) != doc["by_domain"].get(d, []):
                errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # 6) 加载器可用性（concepts/_common 能读到本文件；未构建时验证机制可用）
    if OUT.exists():
        try:
            if _common.load_taxonomy(OUT.name) != json.loads(
                    OUT.read_text(encoding="utf-8")):
                errs.append("concepts 共享加载器与磁盘内容不一致")
        except Exception as ex:  # noqa: BLE001
            errs.append(f"concepts 共享加载器读取失败：{ex}")
    else:
        probe = _common.data_path("plang_taxonomy.json")
        if not probe.exists():
            errs.append(f"concepts 共享加载器路径机制失效：{probe} 不存在")

    return errs


def report(doc: dict) -> None:
    print(f"量子概念条目：{doc['_meta']['concept_total']} 个\n")
    print("按域：")
    for d in doc["domains"]:
        print(f"  {d['domain']:<10} {len(doc['by_domain'].get(d['domain'], [])):>2}  {d['label']}")
    nv = [k for k, s in doc["standards"].items() if s["status"] == "needs_verify"]
    print(f"\n标准登记：{len(doc['standards'])} 条（needs_verify: {nv or '无'}）")
    print(f"桥接边：{len(doc['bridges'])} 条")
    by_sys: Dict[str, int] = {}
    for b in doc["bridges"]:
        by_sys[b["system"]] = by_sys.get(b["system"], 0) + 1
    for s, n in sorted(by_sys.items()):
        print(f"  → {s:<8} {n}")
    print("待核实概念：",
          [c["id"] for c in doc["concepts"] if c.get("needs_verify")] or "无")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗", e)
        return 1
    if "--check" in argv:
        print(f"✓ 校验通过：{doc['_meta']['concept_total']} 个概念 / "
              f"{doc['_meta']['bridge_count']} 条桥接无悬空 / "
              f"{len(doc['standards'])} 条标准登记")
        return 0
    from datetime import datetime, timezone
    doc["_meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    # check 已通过、写盘前再跑一次保生成物与校验同源
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
