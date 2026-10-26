# quantum-kernel —— 量子架构内核（Linux 6.18.57 LTS + arch/quantum）

> v0.6.79 · 把「量子架构」作为**纯新增架构**接入 Linux 内核树。
> **不删除、不修改任何其他架构**——arch/Kconfig 以
> `source "arch/$(SRCARCH)/Kconfig"` 动态接入，顶层 Makefile 默认
> `SRCARCH := $(ARCH)`，新目录本身即注册。
> **基线 6.18.57 之外，同一补丁系列适配五个在维护 LTS 分支**
> （6.12 / 6.6 / 6.1 / 5.15 / 5.10），见「各 LTS 版本补丁」。

## 本目录结构（Linux 内核树 discipline）

```
quantum-kernel/
├── arch/quantum/               新增架构（全量镜像，与内核树内路径一致）
│   ├── Kconfig                 架构选项（QUANTUM、QUBITS=8、LINK_SLOTS=7、QPU、
│   │                           EXCITED_LEVELS 等能量能级选项）
│   ├── Makefile                KBUILD_DEFCONFIG、core-y 路径
│   ├── configs/quantum_defconfig
│   ├── boot/                   grub.cfg / lilo.conf 命令行样例（idle=mwait 等）
│   ├── include/asm/            Kbuild（generic-y 转发）+ quantum.h/page.h/irq.h
│   ├── include/uapi/asm/       byteorder/ptrace/sigcontext（三个无 generic 版的头）
│   ├── kernel/                 setup/head/irq/time/qpu-core/quantum-energy/module
│   │                           + vmlinux.lds
│   ├── mm/                     模拟内存初始化（含 TLB 空实现）
│   └── lib/                    （空；generic lib 覆盖）
├── drivers/quantum/            /dev/qpuN 模拟设备（QPU_ENC/DEC/STATS/RESET）
├── include/uapi/linux/quantum.h  用户 API
├── Documentation/quantum/      架构文档（index + energy-model.rst 能量激发态模型）
├── patches/0001-quantum-architecture-v1.patch   上游→修改的单一补丁（基线 6.18.57）
├── patches/0001-quantum-architecture-v1-<ver>.patch  五个 LTS 分支适配补丁
│                                                     （6.12.113/6.6.159/6.1.190/
│                                                      5.15.223/5.10.272）
├── scripts/fetch_kernel.sh     下载校验解压上游 LTS
├── scripts/build.sh            三层构建验收
├── scripts/regen_base_patch.py 从源码重生基线补丁（含完整性硬校验）
├── scripts/gen_version_patch.py 按目标版本内核面重生分支补丁
└── linux-6.18.57/              完整内核树（本地保留，不入 git；/linux-*/ 全部排除）
```

## 各 LTS 版本补丁（六个分支，同一补丁系列）

基线补丁 `patches/0001-quantum-architecture-v1.patch` 对原始 6.18.57 树
round-trip 验证（洁净应用且复现整树）；`scripts/gen_version_patch.py` 以基线为
输入、按**目标版本内核面**重生分支补丁——`drivers/Kconfig`、`drivers/Makefile`、
`Documentation/index.rst`、`arch/quantum/include/asm/Kbuild` 四个段按目标树真实
内容重建（消除行号漂移，保持零 fuzz、零 offset），量子头文件段按契约差异适配：

| 适配点 | 版本 | 内核面差异与做法 |
|---|---|---|
| atomic.h | 6.1/5.15 | 追加 `arch_atomic{,64}_{xchg,cmpxchg}`；删除与回退层 `#ifndef` 守卫冲突的 6 个 static inline |
| atomic.h | 5.10 | 回退层无条件别名 `arch_atomic_*`→generic 名：以 generic 名提供完整 plain API + 末尾 `#undef` 19 个宏 |
| cache.h | 5.15/5.10 | 删 `ARCH_KMALLOC_MINALIGN` 自定义（旧 slab.h 无守卫、两分支都定义，同值由 `ARCH_DMA_MINALIGN` 推导） |
| pgtable.h | 6.1 | 置 `__HAVE_ARCH_PTE_SWP_EXCLUSIVE` 抑制通用层恒等 swp 实现 |
| pgtable.h | 6.1/5.15/5.10 | 补 `pte_mkwrite(pte)`（6.3 起才有 vma→novma 拆分，旧版 arch 必须自备） |
| cmpxchg.h | 5.10 | 无 `ARCH_ATOMIC` 路径下补裸 `xchg/cmpxchg/cmpxchg64`（llist.h 直接用裸 `xchg`） |
| page/processor/irq/pgtable/pgalloc.h | 各旧分支 | `page_to_phys` 自补、`struct task_struct`/`seq_file` 前置声明、`mk_pte`、`__pgd_alloc`（ptdesc 路径随版本而变） |

新文件 `arch/quantum/include/uapi/asm/bitsperlong.h`（64 位声明）与 Kbuild
去掉 `bitsperlong.h` 转发：5.15/5.10 的 asm-generic 硬编码 `__BITS_PER_LONG=32`，
会让 64 位指针架构的 `size_t` 只有 32 位，触发 `-Wint-to-pointer-cast` /
`-Wbuiltin-declaration-mismatch`（-Werror 即失败）；6.6+ 的自动探测结果同为 64，
自备文件对各分支一致无害。

六个分支的干跑全部 **rc=0、零 offset、零失败**；三层构建验收矩阵
（defconfig 解析 / x86_64 对照 / vmlinux 链接与 `quantum_*` 符号）见
sysweeper `../windows-internals-toolkit/system-optimizer/docs/46_各LTS版本补丁矩阵.md`——结论以该文实测为准。

## 一键重建

```sh
sh scripts/fetch_kernel.sh .            # 下载 6.18.57 + 校验 + 解压
cd linux-6.18.57
git init -q && git add -A && git commit -qm upstream   # 可选：便于审计
patch -p1 < ../patches/0001-quantum-architecture-v1.patch
cd .. && sh scripts/build.sh linux-6.18.57
```

## 构建验收（三层如实报告）

1. **defconfig 全解析**：`make ARCH=quantum quantum_defconfig` 通过，
   `CONFIG_QUANTUM=y / QUBITS=8 / LINK_SLOTS=7 / EXCITED_LEVELS=4 / HAVE_PAGE_SIZE_4KB=y`；
2. **其他架构不破坏**：`make ARCH=x86_64 defconfig` 正常生成（实测 4395 项配置），
   既有 21 个架构目录原封未动（补丁仅含新增 + 纯追加注册）；
3. **真实全量构建**：`make ARCH=quantum O=build -j$(nproc)` 链接出
   **vmlinux（宿主机器码）**，`quantum_*` 符号与 `/proc/quantum-energy`、
   `/proc/qpuinfo` 均在位。
   **诚实边界：vmlinux 是宿主工具链产出的真实镜像，但①量子处理器没有
   gcc 后端（QPU 为宿主模拟）②无 quantum 可引导镜像格式
   ③空闲/能量模型是量子力学启发的记账语义**——不虚报「已在量子硬件运行」。

## 能量激发态模型（量子物理语义层）

`arch/quantum/kernel/quantum-energy.c` 把量子物理核心概念建模为内核可观测的
记账语义（详见 `Documentation/quantum/energy-model.rst`）：

- **能级量子化**：`E_n = n × ΔE` 离散谱（基态 E_0 + 激发态）；
- **叠加 / 幺正相位演化**：能量本征态只积累相位 `φ_n(t)=ω_n·t`；
- **干涉**：`2·w_a·w_b·cos(φ_a−φ_b)`（定点 sin 表 + 相干度衰减）；
- **测量/坍缩**：中断送达 = 一次测量，空闲叠加态坍缩到确定能级；
- **退相干**：T1 布居弛豫 + T2 相干半衰；
- **虚光子入链**：退激发 ΔE 作为交换记录压入 PiLink 环形链路；
- **选择定则 / 纠缠登记**：`|Δn|=1` 允许、Bell 对联动记账。

## idle= 启动参数（GRUB / LILO）

`idle=mwait`：**x86 官方文档已废弃该取值，但参数在 6.18.57 仍可用**，
quantum 架构显式保留「基态等待观测」语义（默认）。另有 `idle=poll`
（强制轮询）与 `idle=halt`。bootloader 样例见
`arch/quantum/boot/grub.cfg` 与 `arch/quantum/boot/lilo.conf`：

```sh
# GRUB
linux /boot/vmlinux-6.18.57-quantum root=/dev/sda1 ro idle=mwait
# LILO
append = "idle=mwait"
```

## 语义（与用户态量子基座一一对应）

- 寄存器：8 qubit 字节宽（上限 20 对齐 `MAX_QUBITS`）；
- 数字转换门：`enc k` = Π_k 置换矩阵（对 k 置 1 位复合 X 门）——
  **翻转语义**：从 |0…0⟩ 编码 k 得 |k⟩，不复位继续编码 j 得 |k⊕j⟩；
- 链路缓冲：`ceil(2π)=7` 槽环形，每步交换入链，满则覆盖计数；
- 页纪律：4KiB——与存储域 ext4 4K 对齐口径同源贯通。

## 许可

内核树内新增代码全部 **GPL-2.0**（内核树纪律）；本目录其余文件随主仓许可。
补丁按内核惯例可自由分发。

## 测试床复验（#661，轻量路径）

`scripts/quantum-testbed.sh` 用 debootstrap + chroot 搭「仅 main 组件」的 Debian 根文件系统，在**宿主内核**下编译/调试 `ARCH=quantum` 树并演示产出一个 initrd。本仓三层构建验收（defconfig 解析 / x86_64 对照 / vmlinux 链接与 `quantum_*` 符号）已在 `../windows-internals-toolkit/system-optimizer/docs/46_各LTS版本补丁矩阵.md` 完成，故 #661 只复验「轻量脚手架路径」，不在 chroot 内重跑内核全量构建。

**2026-10-25 复验结果（诚实记录）**：

| 复验项 | 结论 |
|---|---|
| `bash -n scripts/quantum-testbed.sh` 语法 | ✅ 通过（SYNTAX_OK） |
| 关键工具在位 | `chroot`/`cpio` 在位；`debootstrap`/`mkinitramfs`/`qemu`/`kmod` 缺失（脚本步骤 1 会自装 debootstrap） |
| 安装 debootstrap | ✅ 实装成功（`debootstrap 1.0.134ubuntu2`，`apt-get install -y debootstrap`） |
| ROOTFS→`/tmp` 重定向 | ✅ 逻辑正确（脚本 `$1` 默认 `/workspace/quantum-testbed/rootfs`，本次以 `/tmp/quantum-testbed/rootfs` 传入；`/tmp` 余 192G） |
| `debootstrap --components=main bookworm` 实跑 | ⚠️ **未完成 / needs_action** —— 沙箱网络对 `deb.debian.org` 仅放行 HEAD（探测 `InRelease` 的 HEAD 返回 200），实际 GET 数据下载挂起（30s 超时、0 字节），debootstrap 调用的 `wget` 卡死在 `Retrieving InRelease`。属环境网络限制，**非脚本缺陷** |
| chroot 内 `ARCH=quantum` 构建 + `mkinitramfs` 演示 | ⏸️ 受限于上一步 bootstrap 未成，未执行；内核构建本身已由 docs/46 三层验收覆盖，不重复跑 |
| 脚本 `mkinitramfs` 优雅降级路径 | ✅ 代码已读确认：量子无 `kernel.release` 时脚本输出「跳过真实 mkinitramfs，仅给配方」，不静默通过 |

**收尾结论**：脚本本身结构正确、语法通过、debootstrap 可安装、ROOTFS 重定向可行；但本沙箱**无法完成真实的 bookworm bootstrap**（网络拦截 GET），故「debootstrap bookworm 复验」标记为 **needs_action**——需在具备无限制 Debian 镜像访问的主机上重跑（建议 `sh scripts/quantum-testbed.sh /tmp/quantum-testbed/rootfs`，或直接用默认 `/workspace/quantum-testbed/rootfs`）。届时 chroot 内的 `ARCH=quantum` 构建与 initrd 演示将一并可用（内核构建环节已在 docs/46 验证，预期可链接出 vmlinux 并见到 `quantum_*` 符号）。
