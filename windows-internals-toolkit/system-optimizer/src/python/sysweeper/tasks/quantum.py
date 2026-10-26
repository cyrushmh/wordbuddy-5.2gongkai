"""量子程序与虚拟机任务（platform="any"，v0.6.70 补 omni 四件套的 task 侧）。

接线背景
--------
v0.6.65 登记量子理念概念系统（data/concepts/quantum_taxonomy.json，8 域 66 概念），
v0.6.68 新增 native/quantum.py（态矢量虚拟机：程序 IR + 测量坍缩 + 经典反馈），
v0.6.69 补量子架构基座（数字转换门 / CPU↔闪存不间断交换 / tan·ctan / π 链路）。
CLI（`quantum` 子命令含 `vm` 动作）与 GUI（量子理念 + 量子虚拟机两个面板）早已接好，
但 omni 自检的「任务 / 知识库」两处仍是欠账——登记进统一清单 ≠ 进得了扫描与执行
流程，「半截能力」用户点了总看得见、总览里却看不出来。本文件补 task 侧，
data/quantum.json（标准知识库）补 data 侧，四件套自此齐全。

红线
----
一切动作**纯计算只读**：态矢量模拟在内存里跑，不写文件、不联网、不接量子硬件或
云量子服务、对宿主零副作用。本仓库为经典系统工程工具箱，不含量子硬件探针——
模拟器是「可跑的教具」（O(2^n) 墙内 ≤20 比特），结论绝不夸大为真实量子硬件表现。
"""

from __future__ import annotations

from ..models import Action, Task

M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="quantum_vm_report",
        platform="any",
        title="量子虚拟机就绪自检（态矢量模拟 + 架构基座，纯计算只读）",
        category="maintenance",
        risk="low",
        desc="对内置量子虚拟机做只读就绪自检：态矢量模拟上限（20 量子比特，纯标准库零依赖）、"
             "门集与参数门、内置程序（bell/ghz/teleport/grover2q/bv2/superposition）、"
             "Bell 冒烟（P(00)/P(11) 计数相关性验证测量坍缩与 Born 规则），并演示量子架构"
             "基座（数字转换门 enc / CPU↔闪存不间断交换至 halt / tan·ctan 返回 / "
             "圆周率数据链路缓冲）。",
        actions=[
            N("quantum.quantum_report",
              "量子虚拟机就绪自检：上限/门集/内置程序 + Bell 冒烟计数相关性"),
            N("quantum.environment_report",
              "环境报告：门集/参数门/内置程序/特性/架构基座/红线逐项列出"),
            N("quantum.architecture_report",
              "量子架构基座演示：enc 数字转换门 / CPU↔闪存交换至 halt / tan·ctan / π 链路"),
            N("qudit.qudit_report",
              "多位元 qudit 报告：d 级系统 log2(d) 比特容量 + 同位能级散逸(T1/T2) + "
              "log 值交换在耗散下的解码值漂移表（纯密度矩阵 + Kraus 通道）"),
            N("qudit.capabilities",
              "qudit 能力面：门集(DFT_d/X_d/Z_d)、通道(振幅阻尼/相位阻尼)、边界诚实声明"),
            M("命令行跑量子程序：sysweeper quantum vm "
              "[bell|ghz|teleport|grover2q|bv2|superposition] [--shots 1024] [--seed N]；"
              "arch 看架构基座；sysweeper quantum 看理念概念系统"
              "（overview/domains/domain <域>/of <id>/standards/bridge/search <词>/verify/stats）",
              "虚拟机与理念概念系统的命令行入口（只读）"),
        ],
        notes=[
            "纯计算只读：态矢量模拟全在内存，不写任何文件、不联网、不接量子硬件或云量子服务。",
            "上限 20 比特是纯 Python 内存约束（态矢量 O(2^n)）：virt 子系统识别出的受限 "
            "VM/容器环境据此降档可用位宽，跑不动大程序不假装能跑。",
            "测量按 Born 规则统计解释；同 seed 同程序可复现（确定性种子），冒烟计数两 bucket "
            "都必须非零才算「相关」通过。",
        ],
        caveats=[
            "本仓库为经典系统工程工具箱：模拟器是可跑的教具而非量子硬件，概率结论按文献现状"
            "登记，不夸大为硬件表现。",
        ],
        standards=[
            "[国际] ISO/IEC 4879（量子技术词汇）",
            "[国际] IEEE 7130（量子计算术语）",
            "[国际] OpenQASM 3（量子线路中间表示规范）",
            "[国际] QIR（Quantum Intermediate Representation）",
            "[国际] ITU-T Y.3800（量子密钥分发网络功能架构）",
            "[国际] ETSI GS QKD 014（QKD 密钥交付 API 协议与数据格式）",
            "[国际] NIST FIPS 203/204/205（后量子 ML-KEM/ML-DSA/SLH-DSA）",
            "[教材] Nielsen & Chuang《Quantum Computation and Quantum Information》（CUP，2010）",
        ],
    ),
]
