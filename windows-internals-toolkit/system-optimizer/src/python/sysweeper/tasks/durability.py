"""设备长期使用保护任务（platform=any，跨平台）。

全部只读探针 + 手动/官方工具指引；任何「写设备寄存器/阈值/拆机」的高危动作
一律只给 OEM 官方工具指引，不代执行——严守本项目只读红线，也契合用户
「个人行为在完全图形界面控制操作」：工具出方案与核查，用户在 GUI 里点官方工具做。

引擎（durability_profile / sensor_health_score / build_maintenance_plan /
auto_optimize_suggestions）是纯函数，由 durability_report 串联；GUI 可让用户
选择使用量/期望年限/环境标签后即时看到个性化报告。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="durability_sensor_report",
        platform="any",
        title="设备传感器采集报告（只读）",
        category="maintenance",
        risk="low",
        desc="跨平台只读采集电池/温度/存储/运行时长/环境传感器，标出本机未提供的项（不伪造）。",
        actions=[
            N("durability.read_battery", "读电池电量/温度/健康/循环（sysfs/IOKit，只读）"),
            N("durability.read_thermal", "读 CPU/表面温区（thermal sysfs，只读）"),
            N("durability.read_storage", "读存储剩余/SMART 工具名（只读，不读盘）"),
            N("durability.read_uptime", "读系统运行时长（/proc/uptime，只读）"),
            N("durability.read_env", "读环境温湿度传感器（缺则降级外部接入）"),
        ],
        notes=["任一项读不到即标记「本机未提供」并降级，绝不补造数据。"],
    ),
    Task(
        id="durability_health_assess",
        platform="any",
        title="设备健康评分与保护报告",
        category="maintenance",
        risk="low",
        desc="依据传感器读数做分项健康评分（电池/存储/温湿/运行时长），回链知识库给风险与依据。",
        actions=[
            N("durability.durability_report", "端到端生成保护报告（采集→目标包络→评分→建议+清单）"),
        ],
        notes=["使用量/期望年限/环境标签可在 GUI 选择后即时重算；默认 moderate/4年/无标签。"],
        standards=["[国际] IEC 60529（IP 防护）", "[国际] ASHRAE 温湿度包络",
                  "[官方] 各厂电池保养指南 / NVMe SMART / Linux hwmon"],
    ),
    Task(
        id="durability_charge_opt",
        platform="any",
        title="充电策略优化（指引）",
        category="optimize",
        risk="low",
        desc="长期插电/期望长用的设备建议 80% 充电上限或启用优化/自适应充电，减缓满电应力。",
        actions=[
            M("在 OEM 电源管理（联想 Vantage / 戴尔 Power Manager / 手机设置·电池健康）"
              "开启「充电阈值/养护模式/优化电池充电」，长期插电设 80% 上限。",
              "充电策略优化（OEM 官方工具，不代执行）"),
            N("durability.guide_charge_ceiling", "输出 80% 充电上限操作指引（只给步骤，不写寄存器）"),
        ],
        notes=["浅充浅放（20%-80%）比 0%-100% 循环寿命更长；边快充边高负载最伤电池。"],
        caveats=["充电阈值是 OEM 固件/驱动职责，本工具只读电量温度判断风险，不越权写寄存器。"],
        standards=["[官方] Apple 优化电池充电 / Google 自适应充电 / 各 OEM 养护模式"],
    ),
    Task(
        id="durability_thermal_opt",
        platform="any",
        title="散热与热节流优化（指引）",
        category="optimize",
        risk="low",
        desc="避免封口散热与风道堵塞，长期贴温度上限会加速焊点疲劳与化学衰减。",
        actions=[
            M("放硬面留散热缝、定期外部清灰（软刷/气吹，不拆机）、高负载分段做并歇散热。",
              "散热优化（用户操作，不写热策略）"),
            N("durability.guide_thermal_relief", "输出过热缓解指引（不写热策略、不强制解锁降频）"),
        ],
        notes=["热管理是保护机制，温度越高降频越狠；封口散热（被褥/包内）最伤整机寿命。"],
        standards=["[官方] Linux thermal sysfs / Windows DPTF / macOS SMC 热管理框架"],
    ),
    Task(
        id="durability_storage_care",
        platform="any",
        title="存储保养与 TRIM（指引）",
        category="maintenance",
        risk="low",
        desc="保留 ≥10-15% 空闲利于磨损均衡；确认 TRIM 已启用让 SSD 回收无效块。",
        actions=[
            M("Linux 确认 fstrim.timer 已启用（systemctl status fstrim.timer）；"
              "Windows 默认开启存储优化；保留空闲空间。",
              "存储保养（用户操作，不替你下发写盘命令）"),
            N("durability.guide_storage_trim", "输出 TRIM 指引（只确认启用，不下发写盘命令）"),
        ],
        notes=["满盘（<10% 余量）恶化写放大与磨损均衡；重要数据多重备份而非依赖 SMART。"],
        standards=["[国际] NVMe Base Spec（SMART/Health log）/ ATA ACS（SMART）"],
    ),
    Task(
        id="durability_backup_plan",
        platform="any",
        title="备份与例行维护（指引）",
        category="maintenance",
        risk="low",
        desc="把保养当日历事项：月度看更新、季度核备份、半年查电池与清灰、年度深度清灰。",
        actions=[
            M("用系统/云备份做完整备份并验证可恢复；重要数据保持 ≥2 份跨介质。",
              "备份与例行维护（用户操作，不替你改写盘）"),
            N("durability.guide_backup_now", "输出立即备份指引（不替用户改写任何盘）"),
        ],
        notes=["SMART 显示磨损时优先备份再考虑更换；本工具只读 SMART/健康计数器并提示阈值。"],
        standards=["[官方] 各厂设备保养支持文档 / 通用 IT 资产维护周期实践"],
    ),
    Task(
        id="durability_water_care",
        platform="any",
        title="进水/受潮安全处理（指引）",
        category="maintenance",
        risk="low",
        desc="落水/泼液/高湿环境下正确处理，避免通电短路与氯/酸迟发腐蚀。",
        actions=[
            M("立即断电擦干、接口朝下晾通风 ≥24-48h 再充电；海水/饮料后清水冲净再晾；"
              "充电口潮气被拒充属正常保护。",
              "进水/受潮处理（用户操作，不替你拆机烘干）"),
            N("durability.guide_water_care", "输出进水安全处理指引（不替用户拆机）"),
        ],
        notes=["最隐蔽的是温度循环冷凝——内部结露发生在密闭腔，表面看不出；高湿环境配防潮箱。"],
        standards=["[国际] IEC 60529（IP 等级不覆盖非清水/长期老化）",
                  "[官方] IPC-A-610（腐蚀/污染）", "[官方] 各厂进水处理支持文档"],
    ),
]
