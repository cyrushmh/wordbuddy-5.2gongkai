# 79 量子构建⑦：quantum-testbed.sh chroot 测试床（debootstrap + 构建复验 + initrd 演示）

> **任务**：#661 量子构建⑦——`quantum-testbed.sh` 默认轻量路径：debootstrap bookworm main + chroot 内 build.sh 复验 + mkinitramfs initrd 演示；ROOTFS 重定向到 /tmp 避免污染 /workspace。
> **实测日期**：2026-10-25（沙箱 Ubuntu 22.04 / root / x86_64）。
> **诚实边界**：测试床是补丁链的**验收环境**，不是量子硬件；宿主工具链产出宿主机器码的边界不变（与 build_quantum.py 一致）。initrd 仅为**生成演示**——不启动、不引导、不声称任何量子架构内核可运行。任何阶段缺工具/网络/磁盘，脚本以非零退出码 + 明确原因结束，不静默跳过、不假装成功。

## 一、交付物

`research/quantum/quantum-testbed.sh`（v0.6.81，可执行），子命令：

| 子命令 | 作用 | 幂等 |
|---|---|---|
| `check` | 只读体检：debootstrap/mkinitramfs/root/镜像/磁盘/ROOTFS 状态 | 是 |
| `stage1` | debootstrap `--variant=minbase bookworm`（默认 aliyun 镜像）+ chroot 内装 python3/ca-certificates | 是（ROOTFS 可用即跳过；失败 3 次内重试） |
| `stage2` | chroot 内 `python3 build_quantum.py --check`——干净 bookworm + 系统 python3 重建并校验 quantum taxonomy（跨系统桥接无悬空） | 是（重建 staging 目录） |
| `stage3` | initrd 演示：chroot 内装 initramfs-tools+zstd，复用宿主内核模块树 + `/boot/config-<kver>` 生成 initramfs | 否（重复生成） |
| `all` | stage1 → stage2 → stage3 | — |
| `clean` | 删除 ROOTFS（仅限 /tmp 下路径） | 是 |

## 二、安全护栏

1. **ROOTFS 拒绝落 /workspace**：`guard_rootfs()` 硬校验——`/workspace` 及子路径直接 `die`；非 `/tmp` 路径也拒（需显式 `QUANTUM_TESTBED_ROOT`）。测试床是临时环境，不得污染工作树。
2. **镜像默认 aliyun**：2026-10-25 实测对比四个源在 debootstrap 全量下载下的表现——

   | 镜像 | debootstrap minbase 全量结果 |
   |---|---|
   | mirrors.tuna.tsinghua.edu.cn | 偶发 CDN 403（约 10% 包失败；单包手工重下均恢复） |
   | mirrors.aliyun.com/debian | **0 失败** |
   | mirrors.ustc.edu.cn/debian | **0 失败** |
   | mirrors.cloud.tencent.com/debian | **0 失败** |

   wget 对 HTTP 403 不重试（服务器明确拒绝），debootstrap 本身无重试，故 stage1 用外层 3 次有限重试吸收残余抖动；chroot 内 apt 走 `Acquire::Retries=3`。
3. **stage2 布置最小依赖面**：build_quantum.py `--check` 需 `sysweeper.concepts._common` + `data/concepts/` 全部 taxonomy；**不拷** `sysweeper/__init__.py`（会 import `_zipres`/`version`/`registry` 全家，与桥接校验无关）——缺 `__init__.py` 时 sysweeper 退化为 namespace package，`from sysweeper.concepts import _common` 照常工作。

## 三、实测结果（2026-10-25）

```
stage1 ✓  debootstrap minbase bookworm（aliyun）→ /tmp/quantum-testbed/rootfs
          chroot 内 python3 = Python 3.11.2（Debian bookworm 系统包）
          耗时约 4 分钟（含重试逻辑与 apt 安装）
stage2 ✓  chroot 内 python3 build_quantum.py --check：
          ✓ 校验通过：78 个概念 / 51 条桥接无悬空 / 11 条标准登记
          —— 量子 taxonomy 构建不依赖宿主环境特殊包，干净 Debian 基底可复现
stage3 ✓  chroot 内 mkinitramfs（复用宿主 6.6.117-45.14.1.tl4.x86_64 模块树
          + /boot/config）→ initrd-demo.img 26M
          （firmware missing 警告为 minbase 无固件所致，不影响生成）
```

stage3 踩坑记录（脚本已修复）：① mkinitramfs 按 `/boot/config-<kver>` 选压缩器，缺 config 报 `RD_GZIP not supported`——宿主 config 在 `/lib/modules/<kver>/config`，拷入 chroot `/boot/` 即可；② minbase 无 zstd 时装上（W: No zstd → gzip 降级亦可，但有 config+ zstd 更稳）。

## 四、边界与后续

- **未做实跑的部分**：chroot 内**不**启动内核、不引导 initrd（任务范围是「生成演示」）；量子架构补丁链的内核构建验收仍在 scripts/build.sh（#658）与五 LTS 分支补丁（#660 已取消，补丁资产保留在 quantum-kernel/）。
- **清理**：实测后已 `clean`，ROOTFS（约 1GB）不常驻。
- **复用方式**：`QUANTUM_TESTBED_ROOT=/tmp/other bash research/quantum/quantum-testbed.sh all`；换源 `QUANTUM_TESTBED_MIRROR=...`。
- **版本**：脚本 v0.6.81 与本轮版本号同步（docs/77 批次同一轮次）。
