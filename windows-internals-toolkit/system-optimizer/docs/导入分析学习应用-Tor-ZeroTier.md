# 导入分析学习应用：Tor / ZeroTier（v0.6.17「优化网络模块」）

> 模式与 v0.6.14 / v0.6.15 一致：把外部项目的「该看什么」吸收进本工具，落为**只读诊断模块**，
> 绝不引入执行/写路径。本工具红线不变：不启停服务、不改配置、不连控制端口写命令、
> 不打印任何密钥明文。

## 一、本轮回到的两个项目

| 项目 | 定位 | 上游 | 落地点 |
|---|---|---|---|
| **Tor**（The Onion Router） | 应用层洋葱加密覆盖网络，隐藏「谁在连什么」 | gitlab.torproject.org/tpo/core/tor（C/Rust；GitHub 为镜像） | `native/tor.py` |
| **ZeroTier** | 在物理网之上建加密虚拟二层网（VL1）的 SD-WAN / 零信任组网 | github.com/zerotier/ZeroTierOne（C++） | `native/zerotier.py` |

> 关于「zeroist」：GitHub 用户 `zeroist` 的仓库全是 Java 学习练习（图书馆 app / demo），
> 与网络无关；结合本工具既有 mesh 网络栈与「优化网络模块」语境，判定你指的是 **ZeroTier**
> （其 2026 定位正是 *Simple SD-WAN and Zero Trust Access*）。若你另有所指（如 ZeroNet /
> 某具体仓库），告诉我即可改。

## 二、从项目里学到了什么（吸收为诊断维度）

### Tor
- **端口坐标系**：SOCKS 代理 9050（客户端）/ 9150（Tor 浏览器）；控制端口 9051 / 9151。
- **配置面（torrc）**：`SocksPort` / `ControlPort` / `Bridge` / `ClientTransportPlugin`（可插拔传输
  obfs4 / snowflake / meek / lyrebird）/ `ORPort`·`DirPort`（中继）/ `ExitRelay`（出口）。
- **受审查网络**：靠 `Bridge` + 可插拔传输绕过封锁；桥接/传输二进制（obfs4proxy 等）就位是关键。
- **角色责任**：做中继/出口节点有带宽与法务责任，出口节点看得到明文目的——提醒用户读懂 Relay 文档再定。
- **红线学习**：控制端口可下发写命令；本工具只读、绝不连。torrc 敏感项（HashedControlPassword /
  HiddenServiceDir 等）只报存在名、不回显明文。

### ZeroTier
- **身份模型**：每节点 40 位地址 + `identity.public`（公钥，可对外）/ `identity.secret`（私钥，绝不读）。
- **网络构成**：`networks.d/*.conf`（文件名即网络 ID＝已加入网络）；`controller.d`（自建控制器、可签发网络）；
  `moons.d/*.moon`（私有根 moon）。
- **信任边界**：虚拟网默认端到端加密，但控制器决定「谁能进网」、moon 决定「根在哪」——提醒用户边界在自己手里。
- **红线学习**：`identity.secret` 属私钥，本工具仅 `os.path.exists` 判定存在性，绝不 `open` 读取。

## 三、落到代码（v0.6.17）

- `native/tor.py`：`tor_report()`（安装/版本/运行态/torrc 配置/可插拔传输二进制/数据目录）+
  `capabilities_report()`，全只读。
- `native/zerotier.py`：`zerotier_report()`（安装/版本/运行态/identity/已加入网络/控制器/moon）+
  `capabilities_report()`，全只读，私钥不读。
- `tasks/tor.py` / `tasks/zerotier.py`：platform="any"、category="network"、risk="low"，动作均为 native 只读 +
  一条 opt-in 手动建议（改配置由用户决定）。
- `registry.py`：导入并注册 `tor`、`zerotier`（import 行 + 循环行）。
- `cli.py`：`tor` / `zerotier` 两个只读子命令。
- `gui.py`：顶栏新增「Tor 诊断」「ZeroTier」两个只读窗口按钮（沿用 `_readonly_window` 通用骨架）。
- `native/__init__.py`：docstring + `__all__` 增补 `tor`、`zerotier`。
- 测试：`tests/test_tor.py`（6 项，含 torrc 解析 + 密钥明文不泄露红线）、
  `tests/test_zerotier.py`（6 项，含网络枚举 + 私钥绝不读/不泄露红线）。

## 四、网络模块现在的覆盖（叠加后）

物理(L1) → 数据链路(L2) → 网络(L3, network/osi) → 传输(L4) → 会话/表示/应用(L5–L7, osi) →
DNS 解析(dnshealth) → **覆盖层/隐私层(Tor)** → **虚拟组网层(ZeroTier)** → 本地 mesh(meshchat/netlink)。
网络模块从「本机栈」延伸到「匿名覆盖 + 虚拟组网 + 自组网」三层，诊断视图更完整。

## 五、边界与下一步（你挑）

- 沙箱内 tor / zerotier 均未安装，模块给出「未安装」结论并提示该看什么；真实机器上会读到实际配置。
- ZeroTier 的「zeroist=ZeroTier」为判定，若有误请纠正。
- 可选深化：tor 控制端口只读探针（需 auth cookie，仍不写）、zerotier-cli 解析（listnetworks 文本）、
  把 Tor/ZeroTier 纳入 `network` 模块的总览报告。
