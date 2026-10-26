# 41 · DOS / BusyBox 完善与位宽·PAE 能力 —— legacy 子系统补全与概念系统第七轴

> 指令原文：「完善dos busybox 或开源 dos 整合进概念系统，并且构建支持 8位元
> 16位元 32位元的 能力，自动开启支持 PAE ，也能为32位XP系统开启支持 PAE」。
>
> 本档记录三件事：① v0.6.36 gen-stub 留下的 dos/busybox/dosbox 三个空壳 data
> 库正式填充、由 `native/legacy.py` 真正消费；② 新建位宽世代能力矩阵
> （8/16/32/64 位元）与 PAE 只读检测 + 开启指引（含 32 位 XP 官方口径）；
> ③ 把这套能力整合进 comp 概念系统第七轴「位宽与寻址世代」。

## 1. 起点：三个孤儿 data 库

盘点发现：`data/dos.json` / `data/busybox.json` / `data/dosbox.json` 是 v0.6.36
omni `gen-stub` 生成的空壳（0 refs / 0 items），`data/compat_docs.json` 同样
**全仓无消费者**；而 `native/legacy.py` 有真探测（dos/busybox/dosbox 三报告）
却不消费任何知识层。正确修法不是删 stub，而是**填充 + 让 legacy 消费**。

## 2. 知识层填充（schema 齐备化 + needs_verify 挂牌）

| 库 | 条目数 | 内容 | 证据口径 |
|----|--------|------|----------|
| `data/dos.json` | 5 | msdos-3.1-coordinate（历史坐标）/ freedos-1.4 / dosemu2 / dos-boot-media / dos-era-apis | FreeDOS 1.4 官方源实检（freedos.org/download，2026-10：LiveCD 301.9 MiB、BASE 65 包/20MiB、FULL 191 包/275MiB、2025-04-05 发布、Floppy Edition 可上 IBM PC/XT/AT）；MS-DOS 3.1 历史坐标与 DOSEMU2 打包差异挂 needs_verify |
| `data/busybox.json` | 4 | busybox-overview / busybox-version-line / busybox-applets / busybox-embed-contexts | busybox.net 官方口径：1.37.0（2024-09-27 稳定线）/ 1.38.0（unstable，2026-05-13）；发行版打包版本挂 needs_verify |
| `data/dosbox.json` | 3 | dosbox-core / dosbox-derived / dosbox-limits | dosbox.com 官网/Wiki 实检；衍生线 Win9x 兼容程度挂 needs_verify |
| `data/compat_docs.json` | +4 键 | freedos / dosemu2 / pae / bitwidth（现 10 键） | PAE 条目带微软官方 URL 与诚实边界 |

schema 范式与 reverse/hmosstd 对齐：每个 item 必须有 key/name/org/url/
protocols/interfaces/docs/summary/advice/**evidence_status**，docs 统一
`[{"title","url"}]`；不能逐条核实的条目挂 `needs_verify` 说明原因——诚实边界
先于能力叙事。

## 3. native/legacy.py 消费与扩展

- `_load_refs()` / `_load_compat_refs()`：加载 dos/busybox/dosbox 三个 JSON 的
  items 与 compat_docs 的 bitwidth/pae 主题，共 **14 条知识回链**；
- `LEGACY_CHECKS` 五维度（dos_env / busybox_env / dosbox_env / bitwidth_cap /
  pae_support）每项回链的知识 key 全部真实存在（测试守住）；
- `legacy_report()` 扩为 5 段 + `capabilities_report()` 报知识回链数；
- `_SELF_POSITION` 新增红线：**不修改任何引导配置（boot.ini/bcdedit/内核
  命令行）**——PAE 与位宽只检测现状、只给官方命令文本。

## 4. 位宽世代能力矩阵（8/16/32/64 位元）

`bitwidth_report()` 的读法：**本机能力由三件事决定**——cpuinfo flags
（lm/pae）、内核位宽（uname.machine）、模拟层存在性（which 探测，不启动）。

| 世代 | 典型架构 | 本机路径 | 沙箱实测 |
|------|----------|----------|----------|
| 8 位 | 8080/Z80/6502/6809 | 专用模拟器 MAME / FCEU | 未见（存在性盘点） |
| 16 位实模式 | 8086/286 · DOS | dosbox / DOSEMU2 模拟层覆盖 | dosemu2 ✓（which） |
| 32 位保护模式 | 80386+ · Win32/PE32/DPMI | qemu-system-i386 / wine / 32 位用户态 | wine ✓ |
| 32 位 + PAE | 扩展物理寻址 | CPU pae 标志 + pae_report | pae ✓ |
| 64 位长模式 | x86-64/arm64 | 原生全寻址 | x86_64 / 64 位 / lm ✓ |

位宽是能力分档，不是「新=旧」的优劣判词；只探测存在性，绝不启动任何模拟器、
不下载镜像。

## 5. PAE：自动检测 + 开启指引（含 32 位 XP）

微软官方口径（Learn/MSDN，2026-10 联网核实）：

- **XP / Server 2003**：boot.ini 对应条目加 `/PAE`（`/NOPAE` 禁用）；DEP 启用
  （硬件支持或 `/NOEXECUTE`）时 PAE 自动开启。
- **Vista / Win7 32 位**：`bcdedit /set {当前项} pae ForceEnable`；DEP 开着
  则 PAE 禁不掉（需同时 `nx AlwaysOff` + `pae ForceDisable`）。
- **诚实边界（微软官方）**：**Windows XP（所有版本）物理地址空间上限即
  4GB**——开 PAE 的意义是硬件 DEP/NX 与热插拔内存，**不是突破 4GB**；PAE 也
  不改进程虚拟地址空间（用户态仍 2GB）。
- **Linux**：`HIGHMEM64G` 选中后 `select X86_PAE`；PAE 同时是 32 位内核 NX
  的前提，代价是页表查找开销。
- **64 位 Windows**：原生全寻址，不需要也不支持 PAE。

`pae_report()` 只做：读 cpuinfo pae 标志 / 内核位宽 / MemTotal → 给结论与官方
命令文本。**红线：不代改 boot.ini/bcdedit/内核命令行**，执行与否由用户决定。

## 6. 概念系统第七轴「位宽与寻址世代」

按上轮踩坑教训，走「改 build_comp.py → 重建 → 回注 guidance 补丁」正规路径：

- DOMAINS 加轴 `bitwidth`（七轴）；
- CONCEPTS 加 6 条：`bit8-era` / `real-mode-16` / `protected-32` /
  `pae-extension` / `long-mode-64` / `retro-dos-stack`；
- bridges 全部指向合法靶（构建期校验无悬空）：`plang:arch:x86-64`、
  `plang:arch:host`、`llvm:target:i686-linux-gnu`、
  `daoxue:principle:zhi-bu-zhi`、`datong:concept:gu/yiti-liangmian/he-butong-yong`；
- ENGINEERING 6 条全部真落地（bitwidth_report/pae_report 即本仓落法）；
- 重建后回注 guidance 根环补丁（`daoxue:guidance:zhengti_zhida`）：内存构建
  65 桥 → 磁盘 66 桥，`_meta.bridge_count` 同步 66。

分布：plang 40 / llvm 13 / daoxue 5 / datong 7 / netsys 1 = 66 条桥接。
`check_concept_mesh.py` 零欠账。

## 7. 测试与回归

`tests/test_legacy.py` 扩到 **19 项**：三库 schema 齐备（字段/官方源域名/
needs_verify）/ native 消费 14 条回链 / LEGACY_CHECKS 回链真实 key / 位宽矩阵
五行 + monkeypatch cpuinfo flags / PAE 报告 token（boot.ini /PAE、bcdedit、
4GB 诚实边界、不代改）+ 32 位 x86 结论分支 + 禁执行禁网络不变量。

`tests/test_comp.py`：七轴断言（doms +bitwidth、concept_total 66、
domain_count 7、bridge_count 66、CLI 冒烟「桥接边 66 条」）；
`tests/test_concepts_center.py`：comp concept_total 60→66。

## 8. 版本与接线

- 版本号五处同步 0.6.74（`__init__` / pyproject / main.go / console.ts /
  report_viewer.ts）+ `report_viewer.html` 重生；
- legacy 任务扩为 5 个（dos / busybox / dosbox / **bitwidth** / **pae**），
  新 native 动作经 runner getattr 派发自动可用（CLI/GUI/registry 无需改动）；
- 本轮改动文件：4 个 data JSON + compat_docs + native/legacy.py +
  tasks/legacy.py + tests/test_legacy.py + research/comp/build_comp.py +
  comp_taxonomy.json（重建+回注）+ tests/test_comp.py +
  tests/test_concepts_center.py + concepts/comp.py + cli.py + README.md。

## 9. 踩坑记录（承接 docs/40）

1. **schema 补齐发现**：dos.json 首轮填充有 8 个 item 缺 url/docs/
   evidence_status——「填了」不等于「填齐」，测试按范式逐字段守；
2. **docs 字段两形态**：首轮 freedos-1.4 的 docs 是裸字符串数组，reverse 范式
   是 `[{"title","url"}]`——统一为后者，避免消费者按 key 取值崩；
3. **回链范围**：bitwidth/pae 的知识条目在 compat_docs.json 而非三库，native
   层 `_load_compat_refs` 把两个主题映射为 item 形态并入 LEGACY_REFS，
   `reference("bitwidth")` 才能命中；
4. **带组网补丁的 taxonomy**：继续按 docs/40 教训——重建后必须人工回注
   guidance 补丁，否则组网桥回退（66→65）。
