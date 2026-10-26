# 46 · 各 LTS 版本补丁矩阵（arch/quantum 六分支适配）

> v0.6.84 · 上游基线 6.18.57，同一补丁系列适配五个在维护 LTS 分支（6.12 / 6.6 / 6.1 / 5.15 / 5.10）——**六分支全部三层验收通过**（2026-10-25 实测）

## 1. 概述

`arch/quantum` 作为**纯新增架构**接入 Linux 内核树（不修改、不删除任何其他架构）。基线 6.18.57 的单一补丁 `patches/0001-quantum-architecture-v1.patch` 对该分支通用；对 5 个在维护 LTS 分支，由 `scripts/gen_version_patch.py` 在基线之上做「版本面适配」，生成 `patches/0001-quantum-architecture-v1-<ver>.patch`。

适配分两类：

- **既有文件段重建**：`drivers/Kconfig`、`drivers/Makefile`、`Documentation/index.rst`、`arch/quantum/include/asm/Kbuild` 按目标版本原始文本重建（在既有内容上追加 quantum 段）。这些文件各版本差异大，不能直接套用基线文本。
- **量子自身文件契约适配**：13 个量子文件（8 个头文件 + `kernel/process.c` + `kernel/Makefile` + `kernel/traps.c` + `mm/init.c` + `Kconfig`）按目标版本的内核 API / 链接协议契约做差异修改。

## 2. 补丁文件清单

| 分支 | 补丁文件 | 行数 | 类型 |
|---|---|---|---|
| 6.18.57（基线）| `0001-quantum-architecture-v1.patch` | 70 段（67 新文件 + 3 既有）| 通用 |
| 6.12.113 | `0001-quantum-architecture-v1-6.12.113.patch` | 4073 | 适配 |
| 6.6.159 | `0001-quantum-architecture-v1-6.6.159.patch` | 4071 | 适配 |
| 6.1.190 | `0001-quantum-architecture-v1-6.1.190.patch` | 4080 | 适配 |
| 5.15.223 | `0001-quantum-architecture-v1-5.15.223.patch` | 4115 | 适配 |
| 5.10.272 | `0001-quantum-architecture-v1-5.10.272.patch` | 4334 | 适配 |

> 行数随版本内核面差异浮动；5.10 因 asm-generic 头缺项最多（Kbuild 略去 10 项）且适配点最全（head.o / pm_power_off / trap_init / 5 参数 copy_thread 等），补丁行数最长。以上为 2026-10-25 按当前基线重生后的实数（旧版本文档所记 3486–3736 行为旧基线产物，已淘汰）。

## 3. 逐版本内核面与 Kbuild 略去头

`gen_version_patch.py` 按目标版本重建 `arch/quantum/include/asm/Kbuild` 的 `generic-y` 清单，**略去该版本不存在**的 asm-generic 头（否则 wrapper 指向缺失文件 → 构建失败）：

| 分支 | 内核面 | Kbuild 略去的 asm-generic 头（该版本不存在）|
|---|---|---|
| 6.18.57 | 6.18 | —（基线，全量自备 / 转发）|
| 6.12.113 | 6.12 | fprobe.h, text-patching.h, thread_info_tif.h, ticket_spinlock.h |
| 6.6.159 | 6.6 | codetag.lds.h, fprobe.h, mmzone.h, text-patching.h, thread_info_tif.h, ticket_spinlock.h |
| 6.1.190 | 6.1 | codetag.lds.h, fprobe.h, mmzone.h, text-patching.h, thread_info_tif.h, ticket_spinlock.h |
| 5.15.223 | 5.15 | access_ok.h, codetag.lds.h, fprobe.h, mmzone.h, text-patching.h, thread_info_tif.h, ticket_spinlock.h |
| 5.10.272 | 5.10 | access_ok.h, codetag.lds.h, fprobe.h, logic_io.h, mmzone.h, nommu_context.h, numa.h, text-patching.h, thread_info_tif.h, ticket_spinlock.h |

## 4. 量子自身文件契约适配（通用修法）

内核各 LTS 分支的通用头 / 通用代码对 arch 钩子的契约随版本漂移，量子架构需逐个对齐。下表为各适配点的根因与修法：

| 量子头文件 | 影响版本 | 契约漂移与修法 |
|---|---|---|
| `bitsperlong.h`（asm 非 uapi）| 全部 6 分支 | 自备 `BITS_PER_LONG` / `__BITS_PER_LONG` / `small_const_nbits` = 64，**不走 `generic-y` wrapper**。根因：① 内核 C 编译时 `arch/quantum/include/asm` 优先于 `.../include/uapi/asm`，故 `#include <asm/bitsperlong.h>` 命中非 uapi 版，本文件必须同时给出内核用 `BITS_PER_LONG` 与 uapi 头（`signal.h` / `posix_types.h`）用的 `__BITS_PER_LONG`；② 5.15 / 5.10 的 `asm-generic/bitsperlong.h` 在 64 位下 `__BITS_PER_LONG` 落不到 64（无 `__CHAR_BIT__*__SIZEOF_LONG__` 自动探测，6.6 起才有），且其 `small_const_nbits` 依赖该文件被间接包含。uapi 版（`arch/quantum/include/uapi/asm/bitsperlong.h`）保留，供用户空间导出 `__BITS_PER_LONG`。 |
| `atomic.h` | 6.1 / 5.15 | 删除与回退层 `#ifndef` 守卫冲突的 6 个 `static inline`（`arch_atomic_inc_return` / `arch_atomic_dec_return` / `arch_atomic64_read_acquire` / `arch_atomic64_set_release` / `arch_atomic64_inc_return` / `arch_atomic64_dec_return`）。回退层以 `#ifndef` 提供同名函数，而守卫只拦宏、拦不住函数 → 重定义；删除后由回退层自备（语义等价）。 |
| `atomic.h` | 5.10 | 回退层把 `arch_atomic_*` **无条件别名**到 generic 名：以 generic 名提供完整 plain API（`read` / `set` / `add` / `add_return` / `fetch_add` / `sub` / `sub_return` / `fetch_sub` / `and` / `fetch_and` / `or` / `fetch_or` / `xor` / `fetch_xor` ×32/64 位 + `xchg` / `cmpxchg`）；`inc` / `dec` / `*_return`、andnot 及各 acquire/release/relaxed/try_cmpxchg 变体由回退层自备、不得提供；末尾 `#undef` 本头 19 个 `arch_atomic*` 宏，避免回退层再别名时触发 redefined 警告。 |
| `pgtable.h` | 6.1 | 置 `__HAVE_ARCH_PTE_SWP_EXCLUSIVE`：6.1 通用层在 `#ifndef __HAVE_ARCH_PTE_SWP_EXCLUSIVE` 下自带三个恒等 swp 实现，与本架构定义重定义；置宏声明自备、保留排他位记账语义（5.15 / 5.10 通用层无此组函数，无需置）。 |
| `pgtable.h` | 6.1 / 5.15 / 5.10 | 补 `#define pte_mkwrite(pte) pte_mkwrite_novma(pte)`：6.3 起才有 vma→novma 拆分，旧版通用层不提供 1 参数版，`arch` 必须自备。 |
| `cache.h` | 5.15 / 5.10 | 删 `ARCH_KMALLOC_MINALIGN` 自定义：旧 `slab.h` 无守卫、两分支都定义该宏，同值（64）应由 `ARCH_DMA_MINALIGN` 推导，删除后避免重定义。 |
| `cmpxchg.h` | 5.10 | 无 `ARCH_ATOMIC` 路径下补裸 `xchg` / `cmpxchg` / `cmpxchg64`：`llist.h` 直接用裸 `xchg`，5.10 的 `atomic-fallback.h` 假设 arch 提供（6.1+ 改用 `try_cmpxchg`，由插桩层提供裸 `xchg`）。 |
| `kernel/Makefile` | 5.15 / 5.10 | `obj-y` 去掉 `head.o`：≤5.15 顶层 Makefile `KBUILD_VMLINUX_OBJS := $(head-y) $(core-y→built-in.a)`，head.o 经 head-y 与 obj-y **双路入链** → `multiple definition of quantum_start`；6.1+ 起顶层只链 `./built-in.a` 单聚合，head.o 必须留在 obj-y。旧分支按 x86/arm64 约定：head.o 只进 head-y（`extra-y` 仍构建它）。 |
| `kernel/process.c` | 5.15 / 5.10 | 追加 `void (*pm_power_off)(void);`：6.1+ `kernel/reboot.c` 自带 `__weak` 定义，5.15/5.10 仅 `extern` 声明须 arch 提供；NULL = 模拟架构无真实关机硬件（arm64 同款落点）。 |
| `kernel/traps.c` | 5.10 | 追加 `void __init trap_init(void) {}` 空桩：5.10 `init/main.c` 无 `__weak trap_init`（5.15 起才有），`start_kernel` 直接调用；模拟架构无真实陷阱初始化动作（x86 同款落点）。 |

## 5. 验收（三层）

- **第 1 层**：各分支 `quantum_defconfig` 全解析（Kconfig 依赖图验收）。
- **第 2 层**：真实全量构建链接 `vmlinux`（宿主工具链机器码，非交叉 / 非模拟二进制）。
- **第 3 层**：`quantum_*` 导出符号计数 + 其他架构零破坏（`x86_64 defconfig` 对照）。

| 分支 | CONFIG_QUANTUM 项 | vmlinux 字节 | `quantum_*` 符号 | x86_64 对照配置项 |
|---|---|---|---|---|
| 6.18.57（基线）| 13 | 4,614,568 | 27 | 1757 |
| 6.12.113 | 13 | 4,340,720 | 27 | 1704 |
| 6.6.159 | 13 | 4,169,136 | 27 | 1635 |
| 6.1.190 | 13 | 4,120,584 | 27 | 1588 |
| 5.15.223 | 13 | 3,904,840 | 27 | 1476 |
| 5.10.272 | 13 | 3,875,552 | 27 | 1453 |

> **六分支全部链接成功**（2026-10-25 实测，TUNA 镜像取官方 sha256 校验的纯净树 + 重生补丁 + `scripts/build.sh` 三层验收）。5.15 / 5.10 的历史链接限制（`multiple definition of quantum_start`、`pm_power_off` / `trap_init` 未定义）已由 §4 表末三行适配点逐根因解除，详见 doc 44 §8.3。各补丁均过双解析器干跑（`patch -p1 --dry-run` 与 `git apply --check` 零 fuzz 零失败，70 文件/版）。

> 验收数值来源：本机实测（`/tmp/lts/build-logs/build2-*.log`；宿主 32 核 -j32 全量构建）。`quantum_*` 导出符号六分支统一为 27，说明导出接口跨分支一致；x86_64 对照配置项随版本内核 defconfig 膨胀而递减（1757 → 1453），仅作「其他架构零破坏」的旁证。

## 6. 诚实边界

- 本补丁系列是**纯新增架构**，`ARCH=quantum` 不修改、不删除任何其他架构（`arch/Kconfig` 以 `source "arch/$(SRCARCH)/Kconfig"` 动态接入，顶层 Makefile 默认 `SRCARCH := $(ARCH)`）。
- `vmlinux` 在宿主工具链上真实链接（宿主机器码），但：① 量子处理器没有 gcc 后端，QPU 本身是宿主模拟；② 没有可引导 quantum 镜像格式（无 bzImage / Image 引导协议）；③ 空闲 / 能量模型是量子力学启发的记账语义（`/proc/quantum-energy`）。
- 验收承诺：**defconfig 全解析 + 全量构建链接 vmlinux + 其他架构零破坏**。
