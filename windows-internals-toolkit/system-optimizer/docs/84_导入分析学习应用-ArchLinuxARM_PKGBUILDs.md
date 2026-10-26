# 导入分析学习应用 batch-8：Arch Linux ARM PKGBUILDs 构建脚本仓

> 用户指令：「导入分析学习应用引入 `https://github.com/archlinuxarm/PKGBUILDs`」。
> 处理口径：**只读查据，不克隆 / 不安装 / 不构建 / 不复制代码**（系统级红线）；按 docs/59 + #591 纪律——**有 counterpart 回填、无 counterpart 仅沉淀学习笔记**。

## 0. 链接与来源

| # | 主题 | URL | 性质 |
|---|---|---|---|
| ① | Arch Linux ARM PKGBUILDs（ARM 架构构建脚本仓） | `https://github.com/archlinuxarm/PKGBUILDs` | GitHub 官方组织仓（Arch Linux ARM） |

## 1. 仓库事实（WebFetch 核实）

- **组织 / 维护**：`archlinuxarm` 组织，主要维护者 `kmihelich`；近期提交活跃（2026-10-25 `extra/java-openjdk`、2026-10-24 `core/linux-am33x`、2026-10-11 `aur/qt6-base-headless`）。
- **定位**：托管**从上游 Arch Linux 改写、以在 Arch Linux ARM（ALARM）支持的 ARM 架构上构建**的 PKGBUILD；**未改动的纯上游包不属于本仓**。
- **与 pacman 的关系**：本仓是**源码构建脚本**；pacman 是安装产物 `.pkg.tar.zst` 的二进制包管理器。本仓 `packages_docs.json` 的 `pacman` 条目 `url` 已指向 PKGBUILD wiki，二者同属 Arch/PKGBUILD 域。

### 1.1 仓库布局（README）
| 目录 | 内容 |
|---|---|
| `core` / `extra` | 仅含同名上游仓库的包（内核等 ALARM 认为属此范围的例外） |
| `aur` | 社区高需求、预编译便于安装的 AUR 包精选；也可直接在 ALARM 上用 cower/packer 从 AUR 编译安装 |
| `alarm` | ALARM 自建、或相对上游/AUR 改动大到不再属于前述位置的包（为 ARM 系统启功能） |

### 1.2 构建系统专用 PKGBUILD 变量（非官方 PKGBUILD 规范）
| 变量 | 语义 |
|---|---|
| `noautobuild` | 非 0 时构建系统标记完成、**不为任何架构构建**（需非公开接口才能入仓，常规不使用） |
| `buildarch` | 目标架构**位掩码**（取十进制等效）：`1`=默认=全架构；`4`=仅 armv7h；`8`=仅 armv8（AArch64）；可位或组合多选 |
| `highmem` | 非 0 时标记需 >2GB RAM 的构建机才能成功构建 |

> 这些变量是 ALARM 构建系统私有扩展，不属于上游 PKGBUILD 规范；改写/上游/AUR 的 PKGBUILD 须在头部保留作者名+邮箱+改动变更日志，便于向新版本合并。

## 2. 边界分级（counterpart 判定，守 #591/docs/59 铁律）

| 资源 | 候选子系统 | 判定 | 处理 |
|---|---|---|---|
| Arch Linux ARM PKGBUILDs（ARM 构建脚本仓） | `packages_docs.json` → `pacman` 段（"pacman（Arch Linux / 衍生）"，`url` 即 PKGBUILD wiki） | **有真实 counterpart**：本仓 `packages_docs.pacman` 是 Arch/pacman/PKGBUILD 域的操作规范条目，与本仓 `arch.json`（armv7/aarch64）架构域同主题；全仓 `data/` 多文件命中 `pkgbuild`/`makepkg`/`pacman`/`archlinux`/`aur` | **回填** `packages_docs.pacman.references`（权威来源指针）；详细事实沉淀于本 docs |

> 本仓既有「导入分析学习应用」先例（docs/69/70/72/73/76/77/81）一贯做法：**有 counterpart 回填、无 counterpart 仅学习笔记**。本轮 ALARM PKGBUILDs 命中真实 `pacman` 域 counterpart，按「有 counterpart 回填」路径处理（区别于 batch-7 的 Authentik/herdr 纯学习笔记）。

## 3. 回填落点（packages_docs.pacman.references）

`packages_docs.json` 的 `pacman` 段新增 `references` 数组（对齐 `busybox.json` 等仓内惯例的 `{name, org, url}` 极简指针 schema，测试 `test_packages.py::test_knowledge_base_loads` 仅断言 4 个操作键存在、允许额外键；`native/packages.py` 按固定键 `.get()` 取操作、不遍历全部键，无破环风险）：

```json
"references": [
  {
    "name": "Arch Linux ARM PKGBUILDs（ARM 架构构建脚本仓）",
    "org": "Arch Linux ARM",
    "url": "https://github.com/archlinuxarm/PKGBUILDs"
  }
]
```

详细事实（布局 core/extra/aur/alarm、`buildarch` 位掩码 1/4/8、`noautobuild`/`highmem`）沉淀于本 docs，不在数据层冗余展开——references 仅作权威来源指针。

## 4. 可复用工程纪律（仅纪律层面，非功能移植）

- **`buildarch` 位掩码（1=全 / 4=armv7h / 8=armv8）显式枚举目标架构** ↔ 本仓 `classics-rs/build-rs.sh` 10 目标矩阵、`toolchain_catalog.json` `target_matrix` 29 行——架构选择显式枚举、不靠隐式默认。
- **core/extra/aur/alarm 分层（上游 / 预编译 AUR / 自建 ARM）** ↔ 本仓 native/tasks/data 四入口分层 + 标准 `layering`（官方源 > 厂商/社区 > 第三方）。
- **`noautobuild` / `highmem` 显式标记「本环境不建」** ↔ 本仓 `needs_action` 标记（docs/80 §五 Windows ARM64 工具链、docs/82 classics 交叉 SDK 缺口 —— 明确"本环境不建"的环境项，不虚构修复）。
- **未改动的纯上游包不属于本仓 + 头部保留上游归因** ↔ 本仓「上游归因署名链」先例（aurora-silicon/mesa stock mirror 不吞没上游贡献，提交带上游 MR 归因标签）。

## 5. 落点

- **回填** `src/python/sysweeper/data/packages_docs.json` → `pacman.references`（1 条 ALARM PKGBUILDs 权威指针）。
- **新增** `docs/84_导入分析学习应用-ArchLinuxARM_PKGBUILDs.md` 学习笔记（事实 + 边界分级 + 回填说明 + 可复用纪律）。
- **README 本块**（0024 块内追加导入分析 batch-8 条目）。
- **不改动**：任何概念数据语义、概念系统拓扑与桥接、版本号（`packages_docs.json` 不在版本同步面内，本轮无版本面改动、不升版）。

## 6. 验证

- JSON 合法性校验通过（`packages_docs.json` 仍可解析）。
- `tests/test_packages.py` 全目录跑时通过（`test_knowledge_base_loads` 仅断言 4 操作键存在、允许 references 额外键；`native/packages.py` 按固定键取操作不遍历全部键）。
- 全量 pytest **1755 passed / 6 skipped 零回归**（含上述回填，概念系统未动）。

## 7. 诚实边界汇总

- 仓库为**源码构建脚本仓**，非二进制包；ALARM 二进制包由 `archlinuxarm.org` 镜像分发，不在本仓引用范围。
- 仓库 LICENSE 页面未呈现（needs_verify）；star/fork 计数未呈现（needs_verify）。
- **只读红线恪守**：不克隆 / 不安装 / 不构建 / 不复制代码；仅作权威来源指针与学习笔记，不搬运任何 PKGBUILD 内容。
- **有 counterpart 回填**（packages_docs.pacman.references），不污染 protec/sciences/baigong/datong/zhuangzi 十一概念系统，不新增概念。
