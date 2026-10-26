"""时空与全维度管理器任务（platform=any，跨平台）。

全部只读观测 + 标准/官方指引；任何「改系统时钟/时区/分区格式化/升级替换组件/
执行量子写操作」的高危动作一律只给规范指引，不代执行——严守本项目只读红线。

引擎（assess_time_domain / assess_space_domain / compose_spacetime /
assess_future_compat / cycle_dimensions / chrono_report）是纯函数，由 chrono_report
串联；GUI 可让用户勾选维度标签后即时看到全时空全维度报告与循环往复观察轮次。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="chrono_report",
        platform="any",
        title="时空与全维度报告（只读观测 + 循环往复管理器）",
        category="maintenance",
        risk="low",
        desc="以量子/计算机原理为透镜，只读观测时间维（时钟/时区/生命周期）、空间维（存储/地址空间/"
             "NUMA）、施时空组合维（事件-资源因果链）、未来兼容维（标准 EOL/后量子），并跑全时空"
             "全维度循环往复管理器（round-robin 周而复始、每维一视同仁），每条回链知识库。",
        actions=[
            N("chrono.chrono_report", "端到端生成时空与全维度报告（时间→空间→施时空组合→未来兼容→循环往复管理器）"),
        ],
        notes=["软件只读能力面：不改时钟/时区、不分区/格式化、不升级替换组件、不执行量子写操作。"],
        standards=["[国际] IETF RFC 5905（NTPv4）/ IEEE 1588（PTP）",
                  "[国际] Linux Foundation FHS 3.0 / POSIX 地址空间",
                  "[国际] NIST FIPS 203/204/205（后量子 ML-KEM/ML-DSA/SLH-DSA）",
                  "[国际] IEEE 7130 / ISO·IEC 4879（量子技术词汇）",
                  "[国际] endoflife.date（标准 EOL 事实源）"],
    ),
    Task(
        id="chrono_time_guidance",
        platform="any",
        title="时钟同步与时区校准（规范指引）",
        category="maintenance",
        risk="low",
        desc="只读观测时间维（时钟同步偏差、时区一致性、生命周期阶段）；给出 NTP/PTP 同步与"
             "时区校准的规范指引，绝不自动改时钟/时区。",
        actions=[
            M("Linux：timedatectl set-ntp true 启用 NTP；工业/金融用 PTP(IEEE 1588) 微秒级同步；"
              "Windows：w32time；macOS：timed。统一时区（IANA tz database）避免日志/证书/排程错位。",
              "时钟同步与时区校准（规范指引，不代执行）"),
            N("chrono.guide_time_sync", "输出时钟同步与时区校准指引（只给步骤，不改系统时钟）"),
        ],
        notes=["时间维只观测不改正；任何改时钟/时区由用户在系统设置或厂商工具确认。"],
        standards=["[国际] IETF RFC 5905（NTPv4）", "[国际] IEEE 1588（PTP）", "[国际] IANA tz database"],
    ),
    Task(
        id="chrono_space_guidance",
        platform="any",
        title="空间维盘点与扩容（规范指引）",
        category="maintenance",
        risk="low",
        desc="只读盘点空间维（磁盘分区占用、内存容量、挂载点、NUMA 拓扑）；给出扩容/迁移的"
             "规范指引，绝不自动分区/格式化/清理。",
        actions=[
            M("按 FHS 检查 / /usr /var /home /tmp 占用，避免日志/临时区被挤占；OOM 即地址空间失衡，"
              "按存储层级（内存→NVMe→HDD）分别定位；NUMA 多节点内存敏感负载按亲和排布。",
              "空间维盘点与扩容（规范指引，不代执行）"),
            N("chrono.guide_space_rebalance", "输出空间维盘点与扩容指引（只给步骤，不分区/格式化）"),
        ],
        notes=["空间维只盘点不整理；任何分区/格式化/清理由用户在图形界面或厂商工具确认。"],
        standards=["[国际] Linux Foundation FHS 3.0", "[国际] POSIX 虚拟地址空间", "[国际] NUMA 拓扑（sys/devices/system/node）"],
    ),
    Task(
        id="chrono_future_guidance",
        platform="any",
        title="未来兼容迁移（EOL / 后量子，规范指引）",
        category="maintenance",
        risk="low",
        desc="只读评估未来兼容维（标准/组件 EOL、后量子迁移、前向兼容原则）；给出迁移方向，"
             "绝不自动升级/替换组件。",
        actions=[
            M("以 data/*.json 标准库与 endoflife.date 比对各标准/组件 EOL，规划前向兼容迁移；"
              "加密/会话安全组件向 FIPS 203/204/205 后量子算法演进；新标准须向后兼容既有。",
              "未来兼容迁移（规范指引，不代执行）"),
            N("chrono.guide_future_migrate", "输出未来兼容迁移指引（只给方向，不替换组件）"),
            N("chrono.guide_quantum_safe", "输出后量子安全就绪指引（只给步骤，不执行量子写）"),
        ],
        notes=["未来兼容维只评估给迁移方向；任何升级/替换由用户/厂商工具执行。"],
        standards=["[国际] NIST FIPS 203/204/205（后量子密码）", "[国际] endoflife.date（EOL 事实源）"],
    ),
]
