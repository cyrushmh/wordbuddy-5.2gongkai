# 导入分析学习应用：在 LVM 逻辑卷上安装 Slackware（README_LVM.TXT）

> **本批来源**：用户贴出的一截 Slackware 官方安装指南（`README_LVM.TXT`），文本在
> `The resulting initrd image will be written to th` 处被截断。本档做两件事：
> 1. **补全 + 完善优化**：以官方上游原文补齐截断尾部，并重写为结构化中文、增「关键步骤速览 / 常见陷阱 / 优化注解」；
> 2. **导入分析学习应用引用**：按本仓「导入分析学习应用」流水线（docs/59 + #591 铁律）核查 counterpart、回填、落账。
>
> **上游权威源（已核实可达）**：`https://mirrors.slackware.com/slackware/slackware-15.0/README_LVM.TXT`
> **署名**：Eric Hameleers `<alien@slackware.com>`，2013-10-13（随 Slackware 15.0 发布树发布）。
> **适用**：Slackware 自 12.0 起安装器原生识别/激活 LVM；本例基于 15.0，默认 SMP 内核 `5.15.19-smp`。

---

## 一、补全 + 优化后的完整指南（结构化中文，命令原样保留）

### 1. 引言

很长一段时间里，其他发行版普遍支持把系统装到逻辑卷（LV）上；Slackware 的安装器历来不原生支持，但老手总能手动建好 LV 再把系统装上去 / 迁移过去。在 Slackware 12.0 之前，把整系统装在 LVM 上近乎不可能；如今安装器已内置了更好的 LVM 支持。

### 2. 准备逻辑卷（LV）

- **已有 LV**：安装器会自动识别并激活硬盘上任何预先存在的逻辑卷，它们可作为 `/`、`/usr`、`/home`、`/var` 等文件系统的创建目标。
- **新建 LV**：必须在启动 `setup` 之前完成。先跑 `(c)fdisk` 划出要用于 LVM 的分区，并把分区类型设为 **`8e`（Linux LVM）**。

  示例：用单块 20 GB 分区 `/dev/sda1` 作卷组（VG）。一个 VG 可由多个物理卷（分区 / 整盘）组成（此处略），之后也可随时向 VG 追加物理卷。建一个名为 `myvg` 的 VG，并在其上建两个 LV：`root`（15 GB，承载 `/`）与 `home`（4 GB，承载 `/home`）。

  ```sh
  # pvcreate /dev/sda1
  # vgcreate myvg /dev/sda1
  # lvcreate -L 15G -n root myvg
  # lvcreate -L 4G  -n home myvg
  ```

  > **注记（优化注解）**：若想把 VG 内剩余空间全部给某个 LV，改用 `-l` 而非 `-L`：
  > `# lvcreate -l 100%FREE -n home myvg`
  > 创建 LV 时设备节点会自动生成并激活。这就是跑 `setup` 之前要做的全部准备。

### 3. 在 setup 中使用 LVM

在 setup 主菜单选 `TARGET` 时，LV 会出现在 Linux 分区选择里，显示为 `/dev/myvg/root` 与 `/dev/myvg/home`。选前者作根（`/`）、后者作 `/home`，在上面创建任意文件系统（作者偏好 `ext4`，也可选 `btrfs`、`jfs`、`xfs`）。

setup 正常进行，直到出现 lilo 配置对话框——这时就快到最后一道手动调整了。照常配置 lilo，并把 `/dev/myvg/root` 选作要引导的根文件系统。**注意：根文件系统位于逻辑卷上时必须用初始内存盘（initrd）**，而 Slackware 安装器**不会**替你生成它，需在 setup 结束回到命令行后手动处理。所以此刻照常走完 setup，但**先不要重启！**

setup 末尾会提示选 `EXIT` 并按 `Ctrl-Alt-Del` 重启——退出菜单，**但先别重启！** 接下来要生成 initrd。安装器已经替我们做了部分工作：它创建了 lilo 所需的 LVM 设备节点，并挂载了 `/sys` 与 `/proc`。我们进入 `chroot` 生成 initrd，并让 lilo 配合 generic 内核使用它。

```sh
# chroot /mnt
```

在 chroot 内生成带 LVM 支持的 initrd（示例假定根文件系统为 `ext4`、根设备为 `/dev/myvg/root`、运行 Slackware 15.0 默认 SMP 内核 `5.15.19-smp`）：

```sh
# mkinitrd -c -k 5.15.19-smp -m ext4 -f ext4 -r /dev/myvg/root -L
```

> **`-L` 标志**：让 mkinitrd 加入 LVM 支持（必要时也含 RAID）。

initrd 默认写入 `/boot/initrd.gz`。还需告诉 lilo 这个 initrd：用 `vi` 或 `pico` 打开 `/etc/lilo.conf`（已由 setup 的 `liloconfig` 生成），找到「Linux bootable partition config」段，加入 initrd 行，并把内核文件名改为 **generic** 内核（`liloconfig` 默认加的是 `/boot/vmlinuz`，它是 huge SMP 内核的符号链接；根在 LVM 上必须用带 initrd 的 generic 内核）。结果大致如下：

```sh
image = /boot/vmlinuz-generic-smp-5.15.19-smp
  initrd = /boot/initrd.gz
  root = /dev/myvg/root
  label = linux
  read-only
```

确认 `label`（上例 `linux`）在 `/etc/lilo.conf` 中唯一；满意后存盘、退出编辑器，并在 chroot 内（重新）运行 `lilo`。lilo 会就 `/proc/partitions` 与它所认知的分区差异发几条警告——可放心忽略。

> **优化注解（替代法）**：不想手敲 mkinitrd 命令，可用 mkinitrd 包自带的生成器分析你的安装并给出可用命令行：
> ```sh
> # /usr/share/mkinitrd/mkinitrd_command_generator.sh -r
> # $( /usr/share/mkinitrd/mkinitrd_command_generator.sh -r )   # 直接执行生成 initrd
> ```
> 之后照常更新 `/etc/lilo.conf` 并运行 `lilo` 即可。

chroot 内的工作完成，执行 `exit` 回到原控制台。安装到此结束——祝你拥有「根文件系统跑在 LVM 上」的全新 Slackware！

### 4. 把 SWAP 放在逻辑卷上

setup 能检测并把 LV 当作交换分区使用，**前提**是你必须在启动 `setup` 之前手动把该 LV 格式化为 swap，这样在 `ADDSWAP` 阶段才能选它（setup 会扫描所有 LV 寻找 swap 头）。假设前面已建好 VG `myvg` 并留了未分配空间：

```sh
# lvcreate -L 1G -n swap myvg          # 在 myvg 中建 1 GB 名为 swap 的 LV（名字随意）
# mkswap  /dev/myvg/swap               # 格式化为 swap
```

如此 setup 即可识别。

---

## 二、优化注解（本档增补，不在上游原文内）

### 关键步骤速览

| 阶段 | 动作 | 命令要点 |
|---|---|---|
| 分区 | `(c)fdisk` 建分区，类型 `8e` | `8e` = Linux LVM |
| PV/VG/LV | 建物理卷 / 卷组 / 逻辑卷 | `pvcreate` → `vgcreate` → `lvcreate -L/-l` |
| setup | `TARGET` 选 `/dev/myvg/root`(根)、`/home`；配 lilo 选 `/dev/myvg/root` | 文件系统可 ext4/btrfs/jfs/xfs |
| chroot | `chroot /mnt` 后生成 initrd | `mkinitrd -c -k 5.15.19-smp -m ext4 -f ext4 -r /dev/myvg/root -L` |
| 引导器 | 改 `lilo.conf`：`image=`**generic** + `initrd=` + `root=` | 默认 `vmlinuz`(huge) 须改 generic；`lilo` 重跑 |
| 收尾 | `exit` 出 chroot，重启 | 勿在 setup 末步直接重启 |

### 常见陷阱（优化注解）

- **根在 LVM 上必须有 initrd**：安装器不自动生成；漏掉则启动找不到根。
- **huge vs generic 内核**：`liloconfig` 默认指向 `/boot/vmlinuz`（huge 符号链接）。根在 LVM 上必须改用 **generic** 内核 + initrd，否则 initrd 无意义。
- **`rootdelay` 可用但非强制**：上游示例在 lilo `append` 加 `rootdelay=10` 给内核时间发现 LVM 卷；本例 `mkinitrd -L` 已含 LVM 支持，多数情况不需要，慢存储可加。
- **先 `chroot /mnt` 再 mkinitrd**：在 chroot 内生成的 initrd 才对应新装系统的模块与设备。
- **SWAP-on-LVM 须先 `mkswap` 再进 setup**：否则 `ADDSWAP` 扫不到 swap 头。
- **截断处的内核版本**：用户贴文写作 `5.15.19`，上游完整版为 `5.15.19-smp`（SMP 默认内核）——已据上游补全。

### UEFI / elilo 差异（needs_verify）

> 上游 `README_LVM.TXT` 以 **BIOS/legacy LILO** 为语境。在 UEFI 固件的机器上 Slackware 改用 **elilo**（EFI 引导器），其配置为 `elilo.conf` 而非 `lilo.conf`。**initrd 强制要求与 `mkinitrd -L` 步骤仍然成立**，但引导器配置写法不同（elilo 同样需要 `initrd=` 与 `root=` 行）。具体 elilo 配置以 Slackware 15.0 的 `README_UEFI.TXT` 为准——本档未逐字核实，标记为 **needs_verify**。

---

## 三、导入分析（counterpart 判定 / 事实 / 诚实边界）

### 3.1 counterpart 判定（守 #591 / docs/59）

- **候选 counterpart**：`src/python/sysweeper/data/storage_docs.json` 的 **`lvm` 条目**（"LVM（逻辑卷管理：物理卷/卷组/逻辑卷）"，url 指 `man7.org` 的 `lvm(8)`）。全仓多文件命中 `lvm`（asm_docs/container_docs/langs_docs/quantum/restart_docs/reverse_docs/toolchain_catalog 等），且 `storage_docs.json` 即 LVM/文件系统权威归宿 → **真实 counterpart，走回填路径**（区别于 batch-7 纯笔记）。
- **互补性**：现有 `lvm.advice` 偏**运行期**（lvreduce/lvremove 缩容顺序、pvmove 迁移、thin pool 超额风险），**缺安装期 initrd 强制要点**——本指南正好补这块空白。

### 3.2 事实要点（来自上游原文，已核实）

- PV/VG/LV 创建序列：`pvcreate` → `vgcreate` → `lvcreate -L/-l`；LVM 分区类型 `8e`。
- setup `TARGET` 可见 `/dev/<vg>/<lv>`；可选文件系统 ext4/btrfs/jfs/xfs。
- 根在 LVM 上 **必须 initrd**（`mkinitrd -L` 加 LVM 支持）；安装器不自动生成，须 `chroot /mnt` 后手动做。
- lilo 配置：改 `image=` 为 **generic** 内核、`initrd=/boot/initrd.gz`、`root=/dev/<vg>/<lv>`；`liloconfig` 默认 `vmlinuz`(huge) 须改。
- 替代法 `mkinitrd_command_generator.sh -r` 自动产出等价命令。
- SWAP-on-LVM：须先 `lvcreate` + `mkswap` 再进 setup，`ADDSWAP` 才能识别。

### 3.3 诚实边界（只读红线 + 不臆造）

- **性质**：这是发行版**安装规程文档**（操作指引），非标准/规范类资源；许可证随 Slackware，README 本身为随发行版自由文档，作者署名 Eric Hameleers（已注明）。
- **只读红线恪守**：纯文档分析，**不克隆 / 不安装 / 不构建 / 不复制代码**；未拉取上游仓库、未执行任何 LVM 命令。
- **版本适用**：Slackware 12.0+ 原生支持，示例 15.0；内核 `5.15.19-smp` 为该版默认 SMP 内核（粘贴截断处写作 `5.15.19`，已据上游补全为 `-smp`）。
- **needs_verify**：UEFI/elilo 差异、上游是否在 15.1+ 有更新、具体 `rootdelay` 取值——均标 **needs_verify**，不臆造。

### 3.4 落点 / 验证

- **落点**：`storage_docs.json` 的 `lvm` 条目回填（`references` 权威指针 + `advice` 补安装期 initrd 要点） + 本 docs/85 + README 本块（版本沿用 `0000.0000.0000.0024`，`storage_docs.json` 不在版本同步面内、不升版）。
- **验证**：JSON 合法；`tests/test_sysweeper.py::test_storage_docs_load` 仍通过（仅断言 8 键含 name/org/url/protocols/interfaces/docs/advice，允许额外 `references` 键）；全量 pytest **零回归**（概念系统未动）。
