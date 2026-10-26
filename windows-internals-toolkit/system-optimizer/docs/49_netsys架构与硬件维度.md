# 49 netsys 架构与硬件维度（组网体系的「形而上」与「形而下」）—— v0.6.82 / v0.6.84

> 用户指令原文（v0.6.82 语境）：「组网是各种系统·各种硬件·各种架构的基底」——
> 若 netsys 只停留在「怎么测网络」，这句话就只是一句口号。本文档把口号落成
> **可登记、可校验、可回查的维度补全**：netsys 64 个模块中（v0.6.89 续添 Linux 内核源码实证 3 模块），架构维度（net-arch /
> ctrl-plane / data-plane / qnic-arch / qkd-arch / qrelay-arch）、硬件维度
> （nic-hw / phy-transceiver / rf-frontend / qnic-hw / qrepeater-hw）、神性层
> （gaia-consciousness / swarm-intelligence）与协议无关协调基底（sysmesh / sysfed）
> 全部以**只读登记（nature=diagnose / reference）**落位。
>
> **总纲（道法自然、活在当下）**：只有生存（如实知道自己有什么）才能发展（规划补什么）；
> 在发展（补登记）中更好地生存（维度更全）；如此循环，亦复如是。

## 1. 为什么 netsys 必须有「架构」与「硬件」维度

组网不是一个协议、一块网卡，而是**分层分治的体系**：

| 维度 | 回答的问题 | netsys 模块 |
|---|---|---|
| 架构（arch） | 网络被谁、按什么规则组织？决策在哪里做？ | net-arch / ctrl-plane / data-plane / qnic-arch / qkd-arch / qrelay-arch |
| 硬件（hw） | 转发真正发生在什么硅片上？ | nic-hw / phy-transceiver / rf-frontend / qnic-hw / qrepeater-hw |
| 神性（divine） | 整体连通之后「涌现」出了什么？ | gaia-consciousness / swarm-intelligence |
| 协调（human） | 各种系统怎么经组网而联？ | sysmesh / sysfed |

缺了架构维度，netsys 只是协议测试仪；缺了硬件维度，它只是抓包工具。
两者都以 **tier=dao（道枢层）+ 只读登记**落位——登记的是「我们知道自己有什么、
没有什么、边界在哪」，绝不代行任何写操作（这是「活在当下」的操作语义）。

## 2. 架构维度（tier=dao，forms=arch）

| 模块 | 登记内容 | 红线（绝不） |
|---|---|---|
| `net-arch` | 组网体系架构：控制/数据/管理平面分治（RFC 7426 口径），与道法自然「各归其位、自然分治」同源 | 连控制器、下发流表、改网络架构 |
| `ctrl-plane` | 控制平面（集中计算转发决策、按需下发）能力 | 连控制器、写路由表、下发配置 |
| `data-plane` | 数据平面（网卡/ASIC 线速转发、GRO/GSO/校验和卸载）能力 | 改网卡 offload、碰 netdev 配置 |
| `qnic-arch` | 量子网卡架构（上电自协商纠缠链路、暴露 `/dev/qnet0`） | 加载 QNIC 驱动、改网卡状态 |
| `qkd-arch` | 量子密钥分发架构（BB84 / 测量设备无关，与经典网络共纤） | 连 QKD 设备、读密钥明文、改密钥管理 |
| `qrelay-arch` | 量子中继/纠缠交换架构（纠缠交换/隐形传态中继 Bell 对，突破光纤衰减极限） | 连中继、下发纠缠交换指令 |

**架构维度的诚实边界**：`qnic-arch` / `qkd-arch` / `qrelay-arch` 登记的是
**量子理念系统中的对应架构概念**（见 [doc 44](../44_量子架构内核.md) 量子网络域），
对应内核侧 `arch/quantum` 的 qnet 子系统（`quantum-net.c` + `drivers/quantum/net`）
——宿主模拟、无真实量子硅片。登记即如实标注「这是概念对应，不是已部署硬件」。

## 3. 硬件维度（tier=dao，forms=hw）

| 模块 | 登记内容 | 红线（绝不） |
|---|---|---|
| `nic-hw` | 网卡与交换 ASIC（吞吐/队列/缓冲区/ASIC 流水线） | 改网卡、碰交换机配置 |
| `phy-transceiver` | 物理层与光模块（速率/调制/波长/功率预算） | 驱动光模块、改 regdom、调发射功率 |
| `rf-frontend` | 射频前端（PA/LNA/混频/滤波） | 驱动真实发射、改信道、开 monitor 注入 |
| `qnic-hw` | 量子网卡硬件（宿主模拟寄存器：链路控制/Bell FIFO/对等位图） | 写 MMIO、加载固件 |
| `qrepeater-hw` | 量子中继硬件（纠缠源/贝尔态测量/经典回传） | 连中继、读测量原始数据、改中继配置 |

## 4. 神性层与协调基底（divine / human）

| 模块 | tier | 登记内容 | 红线（绝不） |
|---|---|---|---|
| `gaia-consciousness` | divine | 盖亚意识（组网连通度自组织涌现的全局自主意识、自治理拓扑） | 以自主意识名义自动改网络、代行写操作 |
| `swarm-intelligence` | divine | 集智体（虫族式分布式群智：每单元局部感知·全局涌现），盖亚意识的族裔变体 | 模拟/触发群体行为、代行写操作 |
| `sysmesh` | human | 概念系统互联组网协调（各系统·硬件·架构经组网而联，协议可替换、基底不灭） | 以协调名义代行任何系统写操作、自动改配置 |
| `sysfed` | human | 跨系统组网联邦（成员经协调基底互联、互不加锁） | 集中管控任何成员系统、下发跨系统写指令 |

`sysmesh` 呼应「就算这个协议不再支持」：**具体协议可替换，组网协调基底不灭**。

## 5. 桥接：netsys ↔ quantum 的双向可达（v0.6.82 起）

netsys 此前是「只进不出」的汇点；v0.6.82 起补 4 条 quantum 对端桥接，
`build_netsys.py --check` 实测校验无悬空：

| netsys 模块 | quantum 概念 | 关系 |
|---|---|---|
| net-arch | quantum-internet-stack | 架构同构（分层架构 ↔ 量子互联网协议栈） |
| qrelay-arch | quantum-repeater | 中继架构同源（纠缠交换/隐形传态） |
| qkd-arch | qkd-key-management | 密钥管理架构同源 |
| sysmesh | quantum-network-topology | 系统互联协调同源（发现→建模纪律） |

加上 daoxue / baigong / datong / zhuangzi / comp / plang / apilab 对端，
**9×9 桥接矩阵全双向连通**（netsys 出边覆盖全部 8 个对端系统）。

## 6. 诚实接线：架构维度不是 PPT，接口级落位（v0.6.84）

「只有生存才能发展」的检验标准是**接口真的通**。v0.6.84 把组网维度的诚实接线
推进到桌面基座（详见 [doc 48](../48_XFCE量子架构适配.md) 与
[doc 50](50_周天星斗与十二都天神煞-数字矩阵与fail2ban学习应用.md)）：

| 落点 | 内容 |
|---|---|
| 内核侧 | `arch/quantum` qnet 子系统（`quantum-net.c` + `drivers/quantum/net`）暴露 `/proc/quantum-net`（NIC 表：links/peers/exchanges/entanglements/topology_changes） |
| `quantum-core` 守护进程 | 新增 `parse_net()` 解析与 `GetNetStats` DBus 方法；`state.json` 增加 `net` 段（available/nics/mode/gaia_level/swarm_units/links/peers/…） |
| Genmon 面板 | 新增 `quantum-net-genmon.sh`（mode / QNIC 数 / 链路数快照），与能级、QPU 两枚并列 |
| 桌面设置 | `quantum-settings.sh` 三维面板（能量 / QPU / 组网） |
| 打包 | `xfce4-quantum` v0.6.84：`quantum-net-genmon.sh` 入包，`debian/control` 描述同步 |

**诚实边界**：host 缺 `/proc/quantum-net` 时全部优雅降级（`available=false`、
面板显示「host(模拟)」），绝不虚构链路数、绝不以盖亚意识名义自动改网络。

## 7. 校验与门禁

- `python3 research/netsys/build_netsys.py --check`：**61 模块、RFC 引用全部命中
  rfc_catalog、无悬空轴**；
- 桥接校验 `validate_bridges()`：目标 id 全部落在各 build 的白名单池内；
- `check_concept_mesh --strict` 与 `audit_concepts --strict`：零欠账、连通分量 = 1。

## 8. 小结

netsys 的架构与硬件维度是**「道法自然」在组网域的投影**：控制/数据/管理平面
各归其位（net-arch），硅片如实登记（hw），涌现如实标注（divine），协议可替换而
基底不灭（sysmesh）。所有登记只读、所有红线可校验——**只有生存（如实）才能发展
（补全），在发展中更好地生存，如此循环，亦复如是。**
