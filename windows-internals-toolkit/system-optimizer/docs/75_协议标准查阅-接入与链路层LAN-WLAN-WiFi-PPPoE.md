# 75 协议标准查阅：接入与链路层（LAN / WLAN / Wi-Fi / PPPoE 及相关）

> **来源**：用户指令「还继续 lan、wlan、wifi、ppoe 等协议标准查看」（2026-10-25，接续 docs/74）。标准正文取自 **IEEE 802 LMSC**（ieee802.org）、**WiFi Alliance**、**IETF RFC Editor** 及交叉印证的技术文献（历史速率/安全事件类来自第三方安全研究，标 `needs_verify`）。
> **落点**：本篇为**只读标准查阅与对照笔记**，不克隆、不安装、不构建任何驱动/协议栈实现；标准编号以 IEEE / IETF 发布为准。
> **纪律红线**：只登记可核实事实；标准号逐一标注；无法独立复核的（各 802.11 修订版精确速率、厂商实现偏差、安全事件 CVE 全量）挂 `needs_verify`，不臆造；本仓（windows-internals-toolkit/system-optimizer）对「接入/链路层协议栈」**无 counterpart**（本仓 `network`/`meshnet`/`netlink` 仅做应用层组网与命令通道，非 Ethernet/WiFi 驱动），按 #591 纪律先沉淀为查阅笔记，是否进 `protec` 概念系统「接入与链路（access）」域**待立项**（见第四节）。

## 一、标准概览与可复用点（2026-10-25 只读核实）

| 协议 / 标准 | 标准号（机构） | 性质 / 层 | 关键能力（可核实） | 本仓 counterpart |
|---|---|---|---|---|
| **IEEE 802.3（Ethernet）** | IEEE 802.3（持续演进：u 快速/ab 千兆/ae 万兆/z 40-400G） | 物理层 + MAC / 有线 LAN | CSMA/CD→全双工；10M→400G；与 802.1 协同（端口走 802.3、交换走 802.1） | 无（非驱动层） |
| **IEEE 802.1D（STP）/ 802.1w（RSTP）/ 802.1s（MSTP）** | IEEE 802.1 | 链路层 / 桥接 | 防环生成树；RSTP 快速收敛；MSTP 按 VLAN 多实例 | 无 |
| **IEEE 802.1Q（VLAN）** | IEEE 802.1Q | 链路层 / 虚拟桥接 LAN | VLAN 标签（802.1p 优先级）；单物理网划多逻辑网 | 无 |
| **IEEE 802.1X（端口访问控制 NAC）** | IEEE 802.1X | 链路层 / 端口认证 | 端口开/关状态控制接入；企业 WiFi 认证基石（配合 EAP/RADIUS） | 无 |
| **IEEE 802.1AE（MACsec）** | IEEE 802.1AE | 链路层 / 帧加密 | 二层帧加密，无状态密钥 | 无 |
| **IEEE 802.1AX（LACP）** | IEEE 802.1AX | 链路层 / 链路聚合 | 多链路捆绑（bonding）提带宽与冗余 | 无 |
| **IEEE 802.1AB（LLDP）** | IEEE 802.1AB | 链路层 / 设备发现 | 邻居设备发现协议 | 无 |
| **IEEE 802.11（Wi-Fi）家族** | 802.11a/b/g/n/ac/ax(Wi-Fi6)/be(Wi-Fi7) | 物理层 + MAC / 无线 LAN | 2.4/5/6 GHz；MIMO/MU-MIMO/OFDMA/信道绑定；CSMA/CA；AP 透明桥接 Ethernet（同 48 位 MAC、同上层 IP/TCP） | 无 |
| **IEEE 802.11i / WPA2** | 802.11i（2004）；WPA2 强制认证自 2006 | 无线安全 | 以 **AES-CCMP** 取代 TKIP，机密+完整+认证一体；四步握手派生 PTK/GTK；Personal(PSK)/Enterprise(802.1X) | 无 |
| **WPA3** | WiFi Alliance 2018；Wi-Fi6E/7 强制 | 无线安全 | **SAE（Dragonfly/PAKE）** 取代 PSK 四步握手，抗离线字典+前向安全；**强制 PMF（802.11w）**；GCMP；Enterprise 可选 192 位 CNSA 套件；开放网 **OWE/Enhanced Open** 加密 | 无 |
| **802.1X / EAP / RADIUS（企业模式）** | IEEE 802.1X + IETF EAP（RFC 3748 等） | 认证框架 | 每用户/设备独立认证；EAP-TLS（证书，金标准）/ PEAP / EAP-TTLS / LEAP(废) / EAP-FAST；RADIUS 集中校验 | 无 |
| **PPPoE** | RFC 2516（IETF，1999） | 链路层 / 以太网上的 PPP | 在 Ethernet 上封装 PPP，提供拨号式认证(PAP/CHAP)+动态地址；宽带接入（ADSL/光纤入户）经典承载 | 无 |
| **802.11k/v/r（漫游）/ 802.11e（QoS）/ 802.11w（PMF）** | IEEE 802.11 修订 | 无线增强 | k/v/r 协助无缝漫游；e 提供 WMM QoS；w 保护管理帧（抗 deauth 伪造） | 无 |

## 二、边界分级与诚实边界

- **接入/链路层（无 counterpart）**：802.3/802.11/802.1X/PPPoE 均为**网卡/驱动/操作系统协议栈**范畴，本仓 monorepo 无该层实现（`network`/`meshnet`/`netlink` 仅应用层组网与命令通道，非 Ethernet/WiFi 驱动）。按 #591 纪律**只沉淀为查阅笔记**。
- **安全原则（可复用，实现无）**：WPA2/WPA3 的「**前向安全 + 独立认证 + 管理帧保护**」、802.1X 的「**端口级准入、每设备证书**」、PPPoE 的「**链路级认证 + 动态地址**」——其**准入与加密纪律**可对照本仓 `netauth`（网络认证）与 `meshchat`「不自动落盘、显式请求才连」的接入安全思路。
- **已知失效（仅记录，不落地）**：WEP/TKIP 已废；WPS PIN 可 11,000 空间爆破（Viehböck 2011 / Pixie Dust 2014）应禁用；KRACK（CVE-2017-13077~13088）重装密钥、Dragonblood（2019）SAE 侧信道——均属「协议规范/实现缺陷」，记录为安全反面教材。

诚实边界重申：IEEE 标准号以 ieee802.org 发布为准；各 802.11 修订版理论速率（如 802.11ac 6.9G、802.11ax 9.6G）来自厂商/联盟标称，**未独立复现**（`needs_verify`）；安全事件 CVE 全量与厂商补丁时间线以 NVD 为准（`needs_verify`）；WPA3 强制范围（Wi-Fi6E/7）按 WiFi Alliance 认证政策。

## 三、分主题学习笔记

### 3.1 有线 LAN：802.3 物理/MAC + 802.1 桥接管理

- **802.3（Ethernet）** 定义物理层电气/光接口与基本 MAC；**802.1** 定义多链路互连后的桥接/交换/VLAN/管理。现代交换机同时实现两者（端口 802.3、交换逻辑 802.1）。关键子标准：802.1D STP（防环）、802.1w RSTP（快速收敛）、802.1s MSTP（按 VLAN 多实例）、802.1Q VLAN 标签+802.1p 优先级、802.1X 端口 NAC、802.1AE MACsec（二层帧加密）、802.1AX LACP（链路聚合）、802.1AB LLDP（邻居发现）。
- 可复用纪律：① 「**用 VLAN/优先级隔离 + 生成树防环 + 聚合提冗余**」↔ 本仓 `meshnet` 节点隔离与冗余同构；② 「**端口级准入（802.1X）+ 二层加密（MACsec）**」↔ 本仓 `netauth` 接入认证 + `meshchat` 显式连接纪律同构。

### 3.2 无线 LAN：802.11 家族 + Wi-Fi 安全演进

- **802.11** 与 Ethernet 互操作：同 48 位 MAC、同上层 IP/TCP/UDP，AP 透明桥接（帧格式略有四地址/时长字段差异，在 AP 转换）。演进：a/b/g/n（MIMO）/ac（Wi-Fi5）/ax（Wi-Fi6，OFDMA）/be（Wi-Fi7）。
- **安全演进**：WEP（RC4，已废）→ WPA（TKIP，已废）→ **WPA2=802.11i（AES-CCMP）** → **WPA3（SAE/Dragonfly + GCMP + 强制 PMF）**。WPA3 关键改进：SAE 抗离线字典+前向安全；开放网 OWE 加密（防被动嗅探）；企业模式 192 位 CNSA 套件。
- 企业模式：**802.1X + EAP + RADIUS**，每用户独立密钥；EAP-TLS（证书互认证，金标准）、PEAP/EAP-TTLS（TLS 隧道内 MSCHAPv2，须校验 RADIUS 证书否则遭 evil twin）、LEAP 已废、EAP-FAST 用保护凭据。
- 已知失效：**WPS**（PIN 空间仅 ~11,000，Viehböck 2011 / Pixie Dust 2014 秒级，应禁用）；**KRACK**（CVE-2017-13077~13088，四步握手重装密钥，规范级缺陷，厂商已补）；**Dragonblood**（2019，SAE 侧信道/降级，已补）。
- 可复用纪律：① 「**前向安全 + 独立认证 + 管理帧保护**」↔ 本仓传输层 TLS1.3 前向安全（docs/74）+ `netauth` 每设备认证同构；② 「**禁用弱协议、强制强加密、证书校验不可省**」↔ 本仓 `meshchat`「收到的东西不自动落盘、显式请求才连、不收外部代码」的接入安全底线同构。

### 3.3 宽带接入：PPPoE（RFC 2516）

- **PPPoE** 在 Ethernet 上封装 PPP，提供**链路级认证（PAP/CHAP）+ 动态地址协商 + 计费会话**，是 ADSL/光纤入户的经典承载（用户→BAS/BNG 的拨号式接入）。
- 可复用纪律：① 「**链路级认证 + 动态地址 + 会话生命周期**」↔ 本仓 `netauth` 接入会话管理与 `meshnet` 受控节点表同构；② PPP 的「**LCP 协商 + 认证 + NCP 分配**」三段式 ↔ 本仓「连接前先协商能力、再认证、后授权」的接入纪律同构。

## 四、落实动作（本仓只对照沉淀，落地需立项）

- 本文为**只读标准查阅笔记**，不向本仓引入任何新概念、新依赖、新构建步骤；接入/链路层协议栈本仓**无 counterpart**，按 #591 纪律只沉淀为查阅笔记。
- **候选落地（待立项）**：① 上述接入/链路层标准与「产品基本保护」的**接入安全（准入+加密+防环冗余）**相关，可作为 `protec` 概念系统新增「接入与链路（access）」域素材（覆盖 802.3/802.1X/MACsec/802.11i/WPA3/PPPoE）；② 其**安全纪律**（前向安全、独立认证、证书校验、禁用弱协议）可直接对照本仓 `netauth`/`meshchat` 既有接入安全实现，作为审计基线。该扩展会改动概念计数与版本号，需明确授权再动手。
- 与本仓既有 `docs/组网与分布式计算.md`（mesh/distcompute 内部设计）关系：该篇是**本仓内部组网实现**，本篇是**外部接入/链路层标准查阅**，二者在「准入、加密、冗余、不信任对端」原则上互证；本篇不重复该篇实现细节。
- 待核实项（`needs_verify`）：各 802.11 修订版精确速率与信道规划、WPA3 强制认证范围细则、KRACK/Dragonblood CVE 全量与补丁时间线、PPPoE 现役部署占比。
- 既有 sysweeper 只读层 / 概念 JSON / `concept_gui.html` 不受本文影响。
