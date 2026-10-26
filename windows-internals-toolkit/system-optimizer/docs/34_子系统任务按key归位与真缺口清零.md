# 子系统任务按 key 归位与真缺口清零（v0.6.66）

> 来源：用户指令「嗯，已经重构目录，那么开始完善补全」——沿 v0.6.35→v0.6.37
> 建立的闭环方法论（omni 三层自检 + 缺口分类 + 按需补齐），把自检暴露的
> **7 项真缺口**一次补掉，同时按「按 key 归位」原则重整任务文件目录。

## 一、起点：omni 三层自检暴露的 7 项真缺口

`omni gaps`（v0.6.37 修正 data 判定后）收敛出最后 7 项真缺口——共同病症是
**「有 native 只读报告函数、有 CLI 子命令，却没有注册进 TASKS」**，即进不了
scan/list/执行流程：

| key | 标签 | 缺的落点 | native 层已有的函数 |
|---|---|---|---|
| `netlink` | 网络链接协议 | task | `link_report` / `mesh_serve` / `mesh_discover` / `mesh_send_msg` |
| `netauth` | 网络隐私验证 | task | `netauth_report` / `netauth_demo` |
| `jdk` | OpenJDK-JVM | task | `jdk_report`（九项只读体检） |
| `kernel` | 内核调优(sysctl) | task | `kernel_report`（十项聚合） |
| `kmod` | 内核模块 | task | `kmod_report`（十一项只读） |
| `firmware` | 固件(firmware) | task | （module=kmod，回退满足） |
| `modules` | 已加载模块 | task | （module=kmod，回退满足） |

> **判定规则回顾**（`native/omni.py` wiring）：task 维度判 `tasks/<key>.py`
> **文件存在性**（names=[key, module]+入口别名）。firmware/modules 两项的
> module 都是 `kmod`，因此建成 `tasks/kmod.py` 后经 module 回退**自动满足**——
> 实际只需 5 个新文件，而非 7 个。

## 二、方案：按 key 归位，id 全部保持稳定

全库测试**按任务 id 断言、不按文件模块名**（此前已逐项核对 test_v0522 /
test_sysweeper / test_task_i18n / test_remediation_v0636 的契约），因此任务
可以在文件间迁移而不违约。归位原则：**一个任务文件对应一个子系统 key**。

| 动作 | 文件 | 内容 |
|---|---|---|
| `git mv` 保历史 | `tasks/jvm.py` → `tasks/kmod.py` | 只留 11 个 `kmod_*`，docstring 改写为纯内核模块口径 |
| 新建 | `tasks/jdk.py` | 9 个 `jdk_*` 原样迁入（platform=any、requires_lang=java） |
| 新建 | `tasks/netlink.py` | 自 `network.py` 迁入 `net_link_protocols` / `net_mesh_serve` / `net_mesh_discover` / `net_mesh_hci` + 新增 `net_link_env` |
| 新建 | `tasks/netauth.py` | 自 `network.py` 迁入 `net_auth_setup` + 新增 `net_auth_fingerprint` |
| 新建 | `tasks/kernel.py` | 新增 `kernel_sysctl_overview`（不与 linux.py 既有的 10 个 linux_* 细项任务重复） |
| 修改 | `tasks/network.py` | 摘除已迁出的 5 个 net_* 任务块；`net_reshare` 留下（reshare 属 by_design） |
| 修改 | `registry.py` | import 与循环两处 `jvm` → 5 个新模块；新模块追加在 all_tasks() **末尾**（避开 i18n 前 30 条抽样） |

### 新增的三个任务（均 risk=low、非 opt_in/或与同族一致、无 requires_lang）

- **`net_link_env`**（`netlink.environment_report`）：接口/地址概要与 IPv4/IPv6
  双栈外网连通——mesh 排障「能发现不能通信」前的第一跳。
- **`net_auth_fingerprint`**（manual 指引）：讲清 `identity_fingerprint` 如何
  确定性派生「同一人」凭证（PBKDF2，salt=net_id，常量时间比较），不交换原始
  个人信息、双因子、抗枚举、防关联四性质。**不造零参 native op**——
  native 层的 identity_fingerprint 是带参函数，由 reshare 流程运行时调用。
- **`kernel_sysctl_overview`**（`kernel.kernel_report`）：十项内核子系统只读
  报告一次串联的总览入口；standards 含 "Linux kernel Documentation" 字样，
  与 `sysweeper kernel` 命令的列举口径一致（列举数 33 → 34）。

### 为什么不新建 10 个内核文档任务

初判曾以为 `kernel` 子系统缺 10 个「软件/网络内核文档」任务。实测发现
`linux_sched_cfs` 等 10 个 `linux_*` 任务**已在 `tasks/linux.py` 注册**且被
test_sysweeper 的 test_kernel_software_network_tasks_registered 契约锁定。
重复设计会造成 id 冲突与双重挂载——因此 kernel.py 只补「聚合总览」一个入口，
细项仍归 linux.py。

## 三、验证（全绿才算完）

| 检查 | 结果 |
|---|---|
| `omni.real_gaps()` | **7 → 0**（78 子系统中 13 项 incomplete 全为 BY_DESIGN_KEYS：meta/机制类，不计缺口） |
| 全量 pytest | **1290 passed, 3 skipped**（与改动前基线一致） |
| `tools/audit_concepts.py --strict` | 0 不一致，exit 0 |
| 任务总数 | 461 → **464**（+3 新任务）；jdk_* 9 个、kmod_* 11 个不变 |
| 迁移 id 稳定性 | net_link_protocols/net_mesh_*/net_auth_setup/net_reshare/jdk_*/kmod_* 全部在册 |
| minimal 档零风险不变量 | 新任务 risk=low、非 opt_in、无 requires_lang，无违反 |
| `sysweaper kernel` 列举口径 | 34 项（含 kernel_sysctl_overview） |
| `sysweeper netlink list` 六 id | 齐全（cli.py 按 id 列举，不关心定义在哪个文件） |
| runner 派发契约 | 新 native op（netlink.environment_report / kernel.kernel_report）零参、返回 (bool, str) |

## 四、过程中遇到的环境问题（如实记录）

验证期间 `/workspace`（btrfs-on-NBD 挂载）出现**间歇性 statx 故障**：
`src/python/sysweeper` 目录可 readdir、可 open 读文件、git 可见，但
`stat`/`ls` 间歇 ENOENT，导致 Python import（依赖 stat 判包）间歇失败。
处置：先用「同步副本到 /tmp + 导入」的确定性路径完成 omni 自检与不变量核对，
文件系统恢复后从仓库本体复跑全量测试（1290 passed）确认副本结论与本体一致。
**数据未丢失**（git status 与文件读取全程正常），但这一现象提示：
在该环境跑验证要对瞬时故障有重试/旁路准备。

## 五、红线回顾

- 全部新增任务**只读优先**：net_link_env 只探测连通、kernel_sysctl_overview
  只串联只读报告、net_auth_fingerprint 是纯文本指引。
- 未为凑数造任何零参 native op；identity_fingerprint 保持带参设计，
  由 reshare 授权流程调用。
- 文化标签（阴阳互根等）与文化-数学同构表述遵循「非物理声明」口径，
  与本轮代码改动无关但同库纪律不变。
