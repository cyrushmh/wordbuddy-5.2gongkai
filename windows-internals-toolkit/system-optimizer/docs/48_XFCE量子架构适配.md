# 48 XFCE 量子架构适配（"修改成量子架构"的实义）—— v0.6.80

> 用户指令原文：「量子系统需要适配的 xfce，必须修改成量子架构，不然无意义」。
>
> **落地口径：不是给 XFCE 源码打补丁改造成"量子桌面"，而是把 XFCE 会话/守护进程/
> 面板小程序/主题做成一个真正接线量子架构内核诚实接口的桌面基座——并且这个基座
> 作为 Debian 源包可为目标架构（含 `ARCH=quantum`）构建与安装。**
> "改成量子架构"的实义是：**桌面系统基座在架构层面对齐量子内核，而非声称 XFCE
> 能在已引导的量子处理器上运行。**

## 1. 什么叫"把 XFCE 改成量子架构"（不回避的边界）

| 维度 | 做了什么（真实） | 没做、也不声称（边界） |
|---|---|---|
| 会话 | 新增 `quantum.desktop` 会话变体 + `quantum-session` 包装（设量子主题/壁纸、拉起守护进程） | 不声称 XFCE 在真实量子处理器上引导运行 |
| 守护进程 | `quantum-core` 读 `/proc/quantum-energy`、`/dev/qpu0`，写 `state.json`、经 DBus 暴露 `org.quantum.Core` | 不声称读取的是真实量子硬件；接口缺失时优雅降级 |
| 面板 | 两个 Genmon 小程序（能级 / QPU 链路）消费 `state.json` | 不伪造任何量子测量值 |
| 外观 | 量子色系 GTK 主题（相干绿-紫渐变）+ 壁纸 | 视觉层面，不影响"是否真实" |
| 打包 | `xfce4-quantum` Debian 源包，**双二进制包**，可在目标架构构建 | 不声称包能在量子硅上原生运行 |

> 这是与 [doc 44 §8](../44_量子架构内核.md) / [doc 47](../47_量子架构测试床与initrd.md) 一致的诚实口径：
> 量子架构是**宿主模拟架构**（`arch/um` 同型），没有 gcc 后端、没有可引导镜像格式。
> "改成量子架构"因此必须以**架构可构建/可安装 + 接口诚实接线**来兑现，而非虚报运行环境。

## 2. 桌面集成文件（`quantum-kernel/desktop/`）

| 路径 | 作用 |
|---|---|
| `quantum-core/` | C 守护进程（读接口、写 `state.json`、可选 DBus）+ systemd 用户单元 + sysv init |
| `debian/` | debhelper 源包：`control`/`rules`/`changelog`/`compat`/`source/format`/两个 `.install` |
| `xsessions/quantum.desktop` | XFCE 会话变体（显示管理器可选 "Quantum XFCE Session"） |
| `xsessions/autostart-quantum-core.desktop` | 会话内 autostart 拉起 `quantum-core` |
| `session/quantum-session` | 会话包装：设 `Quantum` 主题/壁纸（尽力），再 `startxfce4` |
| `session/quantum-panel-add-genmon.sh` | 向 XFCE 面板注入两个 Quantum Genmon（需在会话内运行） |
| `genmon/quantum-energy-genmon.sh` | 面板小程序：展示能级/相干/纠缠/Bell 快照 |
| `genmon/quantum-qpu-genmon.sh` | 面板小程序：展示 QPU 链路（slots/buffered/overwrites） |
| `theme/Quantum/` | 量子色系 GTK3 覆盖主题（`index.theme` + `gtk-3.0/gtk.css`） |
| `theme/quantum-wallpaper.svg` | 量子语义壁纸（相干绿-紫渐变 + `ARCH=quantum` 标注） |
| `quantum-settings/` | 桌面设置入口（状态 + 诚实边界，`zenity` 优先、终端回退） |
| `build_deb.sh` | 轻量打包（不依赖 debhelper，用 `dpkg-deb -b` 直接构两个包） |

## 3. Debian 打包：可为目标架构构建（验证过）

源包 `xfce4-quantum` 拆成两个二进制包，契合"量子架构可为目标架构构建"：

- `quantum-core`：`Architecture: any`（编译产物，取 `dpkg --print-architecture`；在 `ARCH=quantum`
  目标上用对应工具链即得到该架构的包）；`Depends: libc6, libdbus-1-3, dbus`。
- `xfce4-quantum`：`Architecture: all`（纯脚本/数据）；`Depends: xfce4, xfce4-goodies,
  quantum-core, dbus`；`Provides: quantum-desktop-base`。

两种构建路径都已实测通过：

```bash
# 方式一：debhelper 标准（建议在 chroot/CI）
cd quantum-kernel/desktop && dpkg-buildpackage -us -uc -b
# 方式二：build_deb.sh 轻量（最小环境可用，无需 debhelper）
cd quantum-kernel/desktop && ./build_deb.sh
```

沙箱实测产出（arch=amd64, version=0.6.80）：

```
quantum-core_0.6.80_amd64.deb         （守护进程 + systemd 用户单元 + sysv init）
xfce4-quantum_0.6.80_all.deb          （会话/主题/小程序/设置入口）
```

`dpkg-deb -I`/`-c` 校验：控制信息（架构/依赖/Provides）与文件清单均正确。

## 4. 端到端验证（host 模式，诚实降级）

在沙箱 host 模式（无 `/dev/qpu0`、无 `/proc/quantum-energy`）跑通：

```bash
./quantum-core/quantum-core --once
# /dev/qpu0 不可用（host 模式）  → 不崩溃
# DBus session bus 不可用 → 降级为 state.json
cat /run/quantum-core/state.json
# energy.available=false  qpu.available=false
# note: "emulated accounting model; not real quantum hardware"
bash genmon/quantum-energy-genmon.sh   # Q·E: host(模拟)
bash genmon/quantum-qpu-genmon.sh      # Q·QPU: host(模拟)
bash quantum-settings/quantum-settings.sh   # 终端回退打印状态 + 诚实边界
```

结论：守护进程在接口缺失时**优雅降级**（标记不可用、不伪造），Genmon 与设置入口正确
消费 `state.json`——接口接线与降级逻辑已闭环验证。

## 5. 测试床可选目标（`scripts/quantum-testbed.sh --with-xfce`）

默认路径**不变**（仍只编译内核 + 生成 initrd，轻量核心）。加 `--with-xfce`（或
`WITH_XFCE=1`）后，在 [doc 47](../47_量子架构测试床与initrd.md) 的 chroot 内额外：

1. 装 `xfce4 xfce4-goodies`（含 `pkg-config libdbus-1-dev` 供守护进程编译）；
2. `dpkg-buildpackage` 构建并 `dpkg -i` 安装 `xfce4-quantum`（证明桌面基座可为目标架构构建/安装）；
3. 写入 initrd hook `quantum-xfce`，把量子会话/主题/小程序带进 initrd 配方（参考配方，量子无引导协议）。

```bash
WITH_XFCE=1 sh scripts/quantum-testbed.sh
# 或：sh scripts/quantum-testbed.sh /path/rootfs 6.18.57 bookworm <mirror> amd64 --with-xfce
```

## 6. 与本仓其余部分的协同

- **概念系统**：`netsys` 组网模块增强（#487）、`quantum` network 域深化（#488）把"量子↔组网"
  跨系统桥接贯通；本桌面基座是这些概念在用户态的可视化落点（能级/纠缠/QPU 链路）。
- **内核**：[doc 44](../44_量子架构内核.md) 的 `arch/quantum` 暴露 `/proc/quantum-energy` 与
  `/dev/qpu0`；本适配是用户态接线点（守护进程 + Genmon）。
- **测试床**：[doc 47](../47_量子架构测试床与initrd.md) 的 chroot 流程通过 `--with-xfce`
  升级为"量子架构桌面基座可在目标架构构建/安装"的端到端演示。

## 7. 诚实边界再声明

- 量子架构是宿主模拟架构，`/proc/quantum-energy`、`/dev/qpu0` 读写的是**模拟/记账模型**；
- 本适配**不声称** XFCE 能在"已引导的量子处理器"上运行（无 bzImage/Image 引导协议）；
- `quantum-core` 在宿主缺接口时优雅降级：可用标记 `false`，不崩溃、不伪造数据；
- 版本随主线 bump 至 **v0.6.80**（见 README 倒序 changelog）。
