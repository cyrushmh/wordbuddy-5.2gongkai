# LVM 维基知识沉淀（Arch Linux 中文维基）

> 来源：<https://wiki.archlinux.org/title/LVM>（中文维基 PDF，951 行提取）
> 项目落地：`tasks/storage.py` 的 `fs_lvm_report`（只读 `pvs/vgs/lvs` 占比核对）、`data/storage_docs.json` 的 `lvm` 段
> 原则：**默认只分析、不删不改**——LVM 的缩容/删卷/迁移均高危，工具只给只读报告与指引。

---

## 1. 核心概念（LVM 基本组成）

| 层 | 名称 | 说明 |
|---|---|---|
| PV | 物理卷（Physical Volume） | 磁盘/分区/环回设备上的 LVM 头；`pvcreate` 创建 |
| VG | 卷组（Volume Group） | 一个或多个 PV 的池子；LV 从中分配空间 |
| LV | 逻辑卷（Logical Volume） | 用户可见的"分区"，挂载即用；`lvcreate` 创建 |
| PE | 物理区域（Physical Extent） | VG 分配空间的最小单位 |

快速导览：分区 → `pvcreate` → `vgcreate`(加 PV) → `lvcreate`(在 VG 上) → `mkfs` → `mount`。

> ⚠️ 双系统注意：Windows **不支持** LVM，双系统下 Windows 无法访问 LVM 分区。
> ⚠️ 引导限制：不支持 LVM 的引导程序不能把 `/boot` 放 LVM 中（仅 GRUB 支持）；需独立 `/boot` 分区。根在 LVM 上时 initramfs 须加 `lvm2`(或 `sd-lvm2`) 钩子。

---

## 2. 命令速查（按生命周期）

### 2.1 创建
| 命令 | 作用 |
|---|---|
| `lvmdiskscan` | 列出可作 PV 的设备（先确认设备，防误删数据） |
| `pvcreate /dev/sda2` | 在设备写 LVM 头，建成 PV |
| `pvcreate --dataalignment 1m /dev/sda` | SSD（erase block <1M、未格式化）对齐，减写放大 |
| `vgcreate VolGroup00 /dev/sda2 [/dev/sdb1 ...]` | 建 VG 并加入 PV（可一次多 PV） |
| `vgextend VolGroup00 /dev/sdb1` | 向已有 VG 追加 PV |
| `lvcreate -L 10G VolGroup00 -n lvolhome` | 建 10G 名为 lvolhome 的 LV |
| `lvcreate -l +100%FREE VolGroup00 -n lv` | 用尽 VG 剩余空闲建 LV |
| `lvcreate -L 10G VolGroup00 -n lv /dev/sdc1` | 指定 PV 上建 LV（约束物理位置） |
| `mkfs.ext4 /dev/mapper/VolGroup00-lvolhome` | 在 LV 上建文件系统 |
| `mount /dev/mapper/VolGroup00-lvolhome /home` | 挂载 |

### 2.2 查看
| 命令 | 作用 |
|---|---|
| `pvdisplay` / `pvdisplay -v -m` | PV 信息 / 含物理分段（pvmove 前看空闲区） |
| `vgdisplay` | VG 信息（含空闲 PE，缩容前确认） |
| `vgs` / `pvs` / `lvs` | 简表看 PV/VG/LV 状态（**本项目只读报告用这三项**） |
| `lvdisplay` | LV 详细信息 |

### 2.3 扩 / 缩（高危）
| 命令 | 作用 | 风险 |
|---|---|---|
| `pvresize /dev/sda1` | 物理设备扩容后同步 PV 大小 | 扩安全 |
| `pvresize --setphysicalvolumesize 40G /dev/sda1` | 缩 PV；若已分配区越界会被拒 | 缩须先 `pvmove` 把空闲段移到尾部 |
| `lvresize -L +10G --resizefs MyVolGroup/mediavol` | 扩 LV 并同步扩文件系统 | 扩相对安全（`--resizefs` 自动） |
| `lvresize -L 15G --resizefs MyVolGroup/mediavol` | 缩 LV 并同步缩文件系统 | **必须先缩文件系统再缩 LV**，顺序反了丢数据 |
| `lvresize -L -500M MyVolGroup/mediavol` + `resize2fs` | 手动先缩 fs 再缩 LV | 缩 fs 通常需先 `umount` |

> 口诀（与 `storage_docs.json` 一致）：**缩容 = 先缩文件系统（`resize2fs`/`btrfs filesystem resize`）再缩 LV（`lvreduce`）**；扩容顺序反之。

### 2.4 迁移 / 改名 / 删除
| 命令 | 作用 |
|---|---|
| `pvmove /dev/sdb1 [/dev/sdf1]` | 把 PV 上数据迁走（缩 PV 前必须；可指定目标 PV） |
| `pvmove /dev/sdb1:1000-1999 /dev/sdc1:0-999` | 区段级精确迁移 |
| `vgreduce myVg /dev/sdb1` / `vgreduce --all vg0` | 从 VG 移除 PV / 移除所有空 PV |
| `pvremove /dev/sdb1` | 清掉 PV 标签（先 vgreduce） |
| `vgrename vg02 my_volume_group` / `lvrename vg02 lvold lvnew` | 改名 |
| `vgchange -a n my_volume_group` | 停用 VG（`-ay` 激活） |
| `lvremove VolGroup00/lvolhome` | 删 LV（先 `umount`，再 `lvs` 确认） |

---

## 3. 特殊逻辑卷

### 3.1 快照（snapshot，写时复制 CoW）
```bash
lvcreate --size 100M --snapshot --name snap01 /dev/vg0/lv   # 建快照
lvconvert --merge /dev/vg0/snap01                            # 合并回原 LV（合并后快照删）
```
- 初始只占 inode 指针，改数据才拷旧值；快照空间耗尽即失效。
- VG 须有未分配空间；**别把整个 VG 空间都分给根 LV**，否则无法给根做快照。
- 快照可挂载，用 `dd`/`tar` 备份；合并可在 LiveCD 进行。

### 3.2 缓存（cache，dm-cache）
```bash
vgextend dataVG /dev/sdx                                    # 快设备加进 VG
lvcreate --type cache --cachemode writethrough -L 20G -n dataLV_cachepool dataVG/dataLV /dev/sdx
lvconvert --uncache dataVG/dataLV                           # 撤销缓存
```
- `writethrough`：写同时落缓存池与源 LV，掉缓存设备不丢数据（默认）。
- `writeback`：性能更好，但缓存设备故障丢数据风险高。

### 3.3 RAID（lvmraid，多 PV）
```bash
pvcreate /dev/sda2 /dev/sdb2
vgcreate VolGroup00 /dev/sda2 /dev/sdb2
lvcreate --type raid1 --mirrors 1 -L 20G -n myraid1vol VolGroup00 /dev/sda2 /dev/sdb2
```
- 支持 raid0/1/4/5/6/10。
- 根在 LVM RAID 上：initramfs 的 `mkinitcpio.conf` 的 `MODULES` 加 `dm-raid raid0 raid1 raid10 raid456`，`HOOKS` 用 `lvm2`(busybox) 或 `sd-lvm2`(systemd)。

### 3.4 精简置备（thin provisioning）
- thin-pool 超额置备后元数据满是常见空间杀手；回收用挂载的 thin LV 上 `fstrim`，或 `thin_trim`/`thin_check` 校验元数据（见 `storage_docs.json`）。

---

## 4. 与本项目存储任务的对接

`tasks/storage.py` 的 `fs_lvm_report`（`id="fs_lvm_report"`）**只读**列本机 LV 与 thin-pool 已用占比，定位超额置备与未释放 LV——完全符合"默认只分析"理念：

- 只读接口：`pvs` / `vgs` / `lvs`（对应维基查看段）。
- 不执行：`lvreduce`/`lvremove`/`pvmove` 等写操作只给指引（对应维基 2.3/2.4 高危段）。
- 知识库：`data/storage_docs.json` 的 `lvm` 段已沉淀"先缩 fs 再缩 LV""thin pool 超额"等要点。

> 后续可增强（保持只读）：在 `fs_lvm_report` 输出中标注"该 VG 是否还有空闲 PE 可做快照""是否存在未 `umount` 却拟删的 LV"等基于维基的风险提示。

---

## 5. 安装/排错要点（来自维基）

- 装 Arch：在"分区与建文件系统"步建 LVM 卷，根放 LV 而非直接格式化分区；Initramfs 步把 `lvm2` 加进 `mkinitcpio.conf`。
- 分区类型：MBR=`8e`(Linux LVM)，GPT=`E6D6D379-F507-44C2-A23C-238F2A3DF928`(gdisk `8e00`)。
- 在其他系统识别 LVM：`modprobe dm-mod` → `vgscan` → `vgchange -ay`。
