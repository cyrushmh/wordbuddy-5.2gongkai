"""文档与概念联动任务（platform=any，跨平台）：docs 文档层的联动统合任务。

用户需求：「docs 文档也算是保证概念系统的联动连轴连动的统合与整合」——
把 docs/ 文档层视作概念系统「联动连轴连动」统合整合的一部分。两个任务都只做
只读盘点/列举与交叉引用，绝不写任何文件、绝不执行命令、绝不修改系统。

全部只读：不安装/卸载、不写系统目录、不跑任何写路径。
"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="docs_report",
        platform="any",
        title="文档与概念联动总报告（只读：docs/ 清单 + 联动接入）",
        category="maintenance",
        risk="low",
        desc="端到端文档层报告：枚举 docs/ 规范化文档清单，并把文档层接入联动网格——"
             "docs 作为一等节点，被 subsystems/linkage/sysbase 供给与印证，并反向沉淀可审计知识。",
        actions=[
            N("docs.docs_report", "端到端生成文档与概念联动报告（只读+文档驱动）"),
        ],
        notes=["本节点只读——不写任何文件、不执行命令、不修改系统；仅枚举文档与交叉引用。"],
        standards=["[工程] docs/ 文档层是概念系统「联动连轴连动」统合整合的文档承载",
                  "[工程] 联动网格测试（test_linkage_v0633.py）：孤岛清零、悬空轴自检、端点合法性"],
    ),
    Task(
        id="docs_linkage_inventory",
        platform="any",
        title="文档↔子系统交叉引用盘点（只读：谁是文档节点、谁被文档印证）",
        category="maintenance",
        risk="low",
        desc="盘点统一子系统清单中哪些节点把文档作为供给/印证来源（subsystems/linkage/sysbase），"
             "并列出 docs/ 中与之对应的文档（54_系统基座、55_兼容层common 等），"
             "落实「文档即联动网格一等节点」的统合整合。",
        actions=[
            M("文档层统合整合三句口径：① docs 登记进统一子系统清单（供给）；"
              "② docs 与 linkage 互相印证联动轴的「接没接上」；"
              "③ docs 与 sysbase 互相印证，把概念系统的联动连轴连动沉淀为可审计文档。",
              "文档↔子系统交叉引用三句口径"),
        ],
        notes=["文档层不重复承载数据：事实在 native 只读层与 data 知识库，docs 只做交叉引用与统合呈现。"],
        standards=["[工程] 统一子系统清单（native/subsystems.py）：全量登记、可开关、配置落盘",
                  "[工程] 联动连轴（native/linkage.py）：方向性轴 + 五类性质（供给/门控/印证/闭环/串联）"],
    ),
]
