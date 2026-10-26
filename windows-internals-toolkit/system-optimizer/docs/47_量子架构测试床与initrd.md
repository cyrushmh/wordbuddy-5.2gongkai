# 47 量子架构测试床与 initrd（在目录里验证「架构是否真实」）

> 用户需求原文：「如果想知道是否真实，用类似 chroot 或 fakeroot 在某个目录测试
> 内核，并且使用当前内核编译修改调试成量子内核架构的程序和桌面系统；对了，我想要的
> 是方便的 initrd，也就是几乎完全开源自由版 debian，名字忘记」。

## 1. 为什么在「目录里」测试，而不是真机引导

量子架构是**宿主模拟架构**（`arch/um` 同型）：没有 gcc 后端、没有可引导镜像格式
（无 bzImage/Image 引导协议）。因此「它是否真实」的正确验证方式，是看它在**当前
（宿主）内核 + 宿主工具链**下能否作为一个**真实可编译、可链接的架构**被构建出来——
这正是 `scripts/build.sh` 三层验收做的事。把这套验证搬进一个**隔离目录（chroot）**，
既能复现，又不污染宿主系统，也便于 CI。

- `chroot` / `fakeroot`：在目录里搭一个最小根文件系统，挂载 `/proc /sys /dev`，
  在隔离环境内编译、修改、调试；
- 「当前内核编译修改调试成量子内核架构的程序和桌面系统」：在 chroot 内开发/调试
  **面向量子内核架构的软件基座**——`sysweaver` 只读诊断子系统（qarch）、
  `quantum-taxonomy`（qkern 域）、`drivers/quantum/` 协处理器子系统用户态 round-trip
  等；这些是在宿主上构建的 dev/test harness，而非「为量子处理器交叉编译用户态」。

## 2. 「几乎完全开源自由版 debian」——你忘掉的发行版

你要的其实是一个**自由软件占比最高的 Debian 系根文件系统**，外加一个方便的 initrd。
按自由程度与用途，候选如下（本仓默认走第一个）：

| 发行版 | 与 Debian 关系 | 适合这里的原因 | 注意 |
|---|---|---|---|
| **Debian（仅 `main` 组件）** | 上游本体 | `main` = DFSG 自由软件，排除 `contrib`/`non-free` →「几乎完全自由」；工具链 `debootstrap` 标准 | 默认带 systemd |
| **Devuan** | Debian 去 systemd 衍生版 | **无 systemd** → 最小自定义内核的 initrd 最轻、最少依赖；「自由」双关 | 换 `SUITE=daedalus`、`MIRROR=https://pkgmaster.devuan.org/merged`、装 `devuan-keyring` |
| **PureOS / Trisquel** | Debian / Ubuntu 的 **FSF 纯自由**衍生版 | 100% 自由软件（FSF 背书） | PureOS 基于 Debian；Trisquel 基于 Ubuntu |

> 如果你指的是**带 systemd 的最小 Debian**，那默认就是 **Debian（main）**；如果要
> **initrd 最省事、无 systemd 纠缠**，选 **Devuan**；如果要 **FSF 认证纯自由**，选
> **PureOS / Trisquel**。「方便的 initrd」与「几乎完全自由」两条需求叠在一起，
> 最自然的落点是 **Debian（main）+ `initramfs-tools`**，或去 systemd 的 **Devuan**。

## 3. 测试床脚本（scripts/quantum-testbed.sh）

一键在目录里 bootstrap 一个只含 `main` 组件的 Debian，装量子内核构建依赖，并在 chroot
内编译 `ARCH=quantum`（证明架构真实可构建），再演示产出 initrd：

```bash
# 默认：Debian bookworm（main），根文件系统落在 /workspace/quantum-testbed/rootfs
sh scripts/quantum-testbed.sh

# 换 Devuan（systemd-free，initrd 更轻）：
QUANTUM_KERNEL_TREE=/path/to/quantum-kernel \
  sh scripts/quantum-testbed.sh /workspace/quantum-testbed/rootfs 6.18.57 \
  daedalus https://pkgmaster.devuan.org/merged amd64
```

脚本步骤（`set -euo pipefail`，全程在目录里，不碰真实引导）：
1. 装 `debootstrap`（若缺）；
2. `debootstrap --components=main` 引导一个只含 `main` 的 Debian；
3. 挂载 `/proc /sys /dev`，写入仅 `main` 的 apt 源；
4. chroot 内装构建依赖：`gcc make flex bison bc perl libelf-dev … initramfs-tools`；
5. 绑定挂载量子内核树进 chroot，执行 `sh scripts/build.sh <ver>`（宿主内核下编译）；
6. `mkinitramfs` 演示产出 initrd（见 §4 诚实边界）；
7. 清理挂载。

进入测试床继续开发：
```bash
sudo chroot /workspace/quantum-testbed/rootfs /bin/bash
# 其内 /quantum-kernel 已可 ARCH=quantum 编译；可在此迭代面向量子架构的程序与桌面基座
```

## 4. initrd 配方与诚实边界

- **配方**：用自由 Debian 的 `initramfs-tools`（`mkinitramfs -o initrd.img <kernel-release>`）
  打包；若要最小、无 systemd，选 **Devuan** 基底。
- **诚实边界**：量子没有可引导镜像格式（无 bzImage/Image 引导协议），也没有真实目标板，
  因此产出的 initrd 是**「若有目标板」的参考配方**，**不声称可在真实硬件引导量子内核**；
  chroot 内构建验证的是「架构真实可编译链接」，不是「能在量子处理器上运行」。

## 5. 与文档 44 §8 的关系

本测试床不是「补当前架构」，而是**在隔离目录里验证量子架构本身是否真实可构建**——
与文档 44 §8 的研究架构定位一致：纯新增、有意留桩、EOL 分支（5.15/5.10）的链接限制
不在此测试床的覆盖目标内（那两支仅 `defconfig` 就绪、整链限制已文档化）。受支持的
构建目标（6.18.57 + 6.12/6.6/6.1）均可在 chroot 内复现 `vmlinux` 链接。
