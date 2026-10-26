# OSI 七层网络诊断与发行版注记（v0.6.13）

> 本版把「新闻归新闻，实际使用和维护有很多人，包括产品设备」这句话落到工程上：
> 不再只盯新闻聚合，而是把**计算机原理（OSI 七层）、接口文档（总线/设备）、发行版文档与发行注记**
> 作为权威来源，喂进一套**全只读**的诊断与可读注记能力。

---

## 一、OSI 七层网络诊断（`native/osi.py`）

### 权威来源（检索后钉死「该看什么」）
- **模型**：ISO/IEC 7498-1:1994 / ITU-T X.200 —— 七层参考模型与每层服务定义。
- **TCP/IP 各层实现与运维要求**：RFC 1122 / RFC 1123。
- **各层核心协议**：
  - L3：RFC 791（IPv4）/ RFC 2460（IPv6）/ RFC 792（ICMP）
  - L4：RFC 9293（TCP）/ RFC 768（UDP）
  - L6：RFC 8446（TLS 1.3）/ RFC 7858（DoT）/ RFC 8484（DoH）
  - L7：RFC 1035（DNS）/ RFC 9110（HTTP）

### 七层覆盖（全部只读）
| 层 | 名称 | 看什么 | 数据来源 |
|---|---|---|---|
| L1 | 物理层 Physical | 接口存在性、载波、速率、双工、MTU、总线后端（PCIe/USB/虚拟）、无线 | `/sys/class/net/*`（carrier/operstate/speed/duplex/device 软链） |
| L2 | 数据链路层 Data Link | MAC、MTU、卸载（GSO/GRO/LRO）、桥·绑·VLAN、802.1X 组件 | `ip -br link`、ethtool 存在性 |
| L3 | 网络层 Network | IPv4/IPv6 地址数、默认路由网关、防火墙工具（nft/iptables）、rp_filter、nf_conntrack | `ip`、/proc/sys/net/* |
| L4 | 传输层 Transport | 监听/已建 TCP/UDP、拥塞算法（BBR 是否在可用列表）、连接跟踪占用 | `ss -tunlp`、/proc/sys/net/ipv4/tcp_* |
| L5 | 会话层 Session | tcp_keepalive_time、WireGuard/VTI 隧道特征 | sysctl、/sys/class/net（wg*） |
| L6 | 表示层 Presentation | OpenSSL 密码套件数、TLS1.3 支持、DoT/DoH 解析器配置 | `openssl ciphers`、`/etc/resolv.conf`、resolvectl |
| L7 | 应用层 Application | DNS 解析（localhost/公网）、本地回环监听端口、外网可达性（显式 opt-in） | `socket.getaddrinfo`、`ss -tlnp`、urllib（http/https 仅） |

### 红线（与 webnews/edge 一致）
- 只读：`/sys/class/net`、`ip`/`ss`/`ethtool`/`openssl` 的**只读项**、DNS 解析、`probe_http` 仅 http/https + 短超时。
- 不增删地址、不改路由、不 reload 防火墙、不连校外网做写操作。
- 写操作（ethtool -K、tc qdisc add、BBR 启用）一律留在 `network` 模块的 opt-in 任务里，本模块不碰。

### 用法
```bash
python -m sysweeper osi                 # L1–L7 整体只读诊断
python -m sysweeper osi layer --layer 3 # 只看第 3 层
python -m sysweeper osi caps            # 能力自检
python -m sysweeper osi probe --url https://example.com  # 外网可达性（显式、可审计）
```

---

## 二、发行版文档与发行注记（`native/distro.py`）

### 权威来源
- **身份文件**：systemd `os-release(5)`（/etc/os-release、/usr/lib/os-release）。
- **注记规范**：Debian Policy Manual §4.4（changelog.Debian / NEWS.Debian）。
- **文档位置**：FHS 3.0 §4.11（/usr/share/doc）。
- **字段语义**：LSB Core。

### 能力
1. **识别**：复用 `linux.detect_distro`（/etc/os-release 优先，lsb_release 兜底），输出 ID/VERSION_ID/PRETTY_NAME/VERSION_CODENAME/BUILD_ID。
2. **注记来源清单**：扫描 `/usr/share/doc/*/NEWS.Debian*` 与 `changelog.Debian*`，列出样本；标记包管理日志（apt/dnf/pacman）存在性。
3. **按包读注记**：`distro notes --pkg <包名>` 只读该包本地 NEWS/changelog（.gz 自动解压前若干字符）。

### 红线
- 只读本地 `/usr/share/doc` 与 `/etc/os-release`；**不** `apt-get changelog`（那会联网）、不改源、不写文件。
- 本机未装某包本地注记时，明确说「未安装该包本地注记」，并提示 `apt-get changelog` 会联网——本工具不替你联网。

### 用法
```bash
python -m sysweeper distro            # 发行版身份 + 注记来源清单
python -m sysweeper distro notes --pkg systemd  # 读某包本地变更日志
python -m sysweeper distro caps       # 能力自检
```

---

## 三、接口/总线枚举（`native/hardware.bus_report`）

- 读 `/sys/bus/*`：列出已注册总线（pci / pci_express / usb / platform / i2c / spi / acpi / scsi …）与各自设备数、驱动数。
- PCI 设备驱动绑定抽样：读 `/sys/bus/pci/devices/<addr>/driver` 软链 basename，证明「接口文档」已落到可读设备树。
- 参照 PCI-SIG / USB-IF 类代码；`lspci -nn` / `lsusb` 给设备级细节（改驱动属写操作，本函数不碰）。

### 用法
```bash
python -m sysweeper edge   # 已有；总线枚举后续可经 hardware.bus_report 接入 CLI
```

---

## 四、CLI / GUI / 任务注册
- CLI：`osi`、`distro` 两个新子命令（动作化、只读优先、带安全边界）。
- GUI：顶部新增「OSI 网络诊断」「发行版与注记」按钮，各带只读窗口。
- 任务：`tasks/osi.py`（`osi_report`）、`tasks/distro.py`（`distro_notes`）接入 registry，platform="any"、risk=low。

## 五、待补（开放项，纯数据/翻译）
- i18n：新任务标题/分类已加入提取队列，6 种新语言 `.po` 译文与 zh_TW 的 OpenCC 生成仍未填（纯翻译，不改代码）。
- 接口文档可进一步细化：按 PCI class code / USB device class 做人类可读分类（复用 `data/hardware.json`）。
