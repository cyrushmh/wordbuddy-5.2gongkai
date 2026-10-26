# 72 导入分析学习应用：openKylin 软件包管理 SIG（gitee.com/openkylin/community · sig/packaging）

> **来源**：用户指令「导入分析学习应用」新增批次（2026-10-25），目标仓库 `https://gitee.com/openkylin/community/tree/master/sig/packaging`。
> **落点**：全部资源**只作只读分析**（2026-10-25 经 gitee 仓库树页被验证码拦截后，改用 gitee API `contents` 接口 + 各文件 `raw` 直链只读抓取 README.md / sig.yaml / 开发者贡献指南.md / 打包实践操作指南.md / 评审规则.md / 贡献积分排行.md 六份文件），不克隆、不安装、不构建、不下载、不复制其代码进本仓。
> **纪律红线**：只登记可核实事实；仓库树页（HTML）被 gitee 安全验证码拦截，故目录清单与文件正文均取自 API/raw 直链，页面交互层未核实；无法独立复核的标 `needs_verify`，不臆造；本仓（windows-internals-toolkit/system-optimizer）对「发行版级打包治理」**无真实概念系统 counterpart**，按 #591 先例（docs/59、docs/70、docs/71）**一律只沉淀为学习笔记、对照既有 docs/packaging.md，不新增概念**。

## 一、资源概览与可复用点（2026-10-25 只读核实，取自 gitee API/raw）

| 资源 | 性质 | 许可证 / 归属 | 规模 / 技术要点（可核实） | 可复用工程纪律（仅学习，不落地代码） |
|---|---|---|---|---|
| `openkylin/community` · `sig/packaging` | openKylin 社区「软件包管理 SIG」 | 社区治理仓库（gitee，开源社区协议以仓库 LICENSE 为准，`needs_verify` 精确条款） | 6 份文件：README.md / sig.yaml / 开发者贡献指南.md / 打包实践操作指南.md / 评审规则.md / 贡献积分排行.md；SIG Owner = `maozhou`，sig.yaml 列 14 名顶层 maintainer | ① **SIG 职责边界显式化**（规范/准入/公共包/发布清单/依赖冲突协调/工具框架）↔ 本仓 docs/packaging.md「总原则·各自规范」同构；② **Owner+Maintainer+包级维护者三级治理**↔ 本仓「各自规范与目录结构」分责任纪律同构 |
| `sig.yaml` | SIG 元数据 + 包清单 | 同上 | `description: packaging team`；`owner: [maozhou]`；`maintainers` 14 名（含 owner）；`packages` 字段为体量大到数千条的包列表，部分包以嵌套结构指定**包级专属维护者**（如 `bash→kylinos-aq-xinjiahao,zhoukangyu`、`openjdk-17/25→wjw_2022`、`avahi→szm-min`） | ① **包级维护者下沉到具体包**的精细责任划分（谁的孩子谁抱走）↔ 本仓「子项目自包含、各端各自规范」同构；② SIG 元数据中**缺 name/mailing-list 硬编码字段**（邮件列表在 README 为 `packaging@lists.openkylin.top`）——治理元数据与展示元数据分离，值得本仓 schema 版本化参考 |
| `打包实践操作指南.md` | 打包操作 SOP（以 debhello 为例） | 同上 | 完整 Debian 化流程：**debmake** 生成 debian/ 模板（control/copyright/changelog/rules/source/format/watch…）→ 改 changelog 版本号为 `0.0.1-ok1`、distribution 改 `yangtze` → `dpkg-buildpackage -S -nc --no-sign` 出 `.dsc/.debian.tar.xz/.buildinfo/.changes` → 在 `packages/` 建 `debhello.yaml` 维护信息 → 向 `openkylin/community` 提 PR → 平台自动建 `openkylin/debhello` 仓库 → `git-buildpackage`(gbp) `import-dsc --pristine-tar --debian-branch=openkylin/yangtze --upstream-branch=upstream` 反向构建 git 仓库 → 改 `debian/source/format` 为 `3.0 (native)` → 推 gitee | ① **源码包规范化 + 反向 git 化**的双轨（源码包 ↔ git 仓库）↔ 本仓「源码树与交付件分离、构建产物不污染源码树」同构；② **版本后缀 `-ok1` + 发行代号 `yangtze`** 的发行版标记纪律（本仓用 `NNNN.NNNN.NNNN.NNNN.YYYYMMDD` D 段升版，口径不同但「版本号显式可溯」同构）；③ **pristine-tar 锁定 orig tar 内容**避免重打包漂移 ↔ 本仓 `--check` 防漂移纪律同构 |
| `开发者贡献指南.md` | 开发者贡献 SOP | 同上 | 以 `openkylin/debhello` 为例：fork → `git clone` → 改 `src/hello.c`（新增按 `LANG` 输出中/英） → `git add/commit/push` → 网页端向 `openkylin/debhello` 提 PR → **maintainer 代码审核通过后，平台内部自动打包/测试/编译** | ① **PR 合入即触发平台自动构建测试**的 CI 门禁 ↔ 本仓 `audit-concepts.yml`/`build-*.yml`「提交前门禁全绿」同构；② **fork→改→PR→审核**的标准上游协作范式 ↔ 本仓开源协作纪律同构 |
| `评审规则.md` | 贡献积分评判规则 | 同上 | 评判依据：PR 数量(n)、PR 内容(b∈[1,5]：bug 严重度/功能完整度)、代码质量(c∈[1,3])、maintainer 评审 PR 数(d∈[0,5])、技术决策(a∈[1,5])；公式：`日常积分 = b*n*3 + c*n*2 + d*n`；**首次上传源码包 `50*n`**；**技术决策 `a*n*3`** | ① **多因子加权积分**的可量化贡献度量（而非单纯 PR 数）↔ 本仓「可审计、可溯源」度量思维同构；② 该规则为社区治理文本，**本仓无对应治理系统**，仅作编目学习 |
| `贡献积分排行.md` | 成员贡献积分榜单 | 同上 | 按评审规则累计排行的成员榜单（具体名次/分值以文件为准，`needs_verify` 精确数值） | ① 公开透明的贡献可视 ↔ 本仓「概念体检/审计可溯源」精神同构；仅学习 |

## 二、边界分级与诚实边界

本仓库按「是否可实做落地」分档，本仓守界如右：

- **纯治理/流程类（仅对照学习，不新增概念）**：sig/packaging 的 6 份文档均属此档。本仓**无发行版级打包治理 counterpart**（无 SIG/包级维护者/贡献积分系统）；本仓已有的是 `docs/packaging.md` 这一**多端打包策略文档**（Debian `debian/` + Arch `PKGBUILD` + Rust `Cargo` + Python `.pyz` 等各自规范），与 openKylin「单一 Debian/OK 体系治理」在**「因地制宜、各自规范、兼容层」总原则上同构**，但治理形态不同——openKylin 是社区级 SIG 准入+积分，本仓是 monorepo 多端自包含。按 #591 纪律**只沉淀为学习笔记**，不新增 comp / netsys / 任何概念系统概念。
- **基础设施类（只作架构学习，不落地代码）**：debmake / dpkg-buildpackage / git-buildpackage(pristine-tar/quilt) / gitee 平台自动构建——属外部发行版工具链/平台，本仓**不接入、不查询、不镜像**；仅学习其「源码包规范化 ↔ git 反向构建 ↔ 合入自动构建测试」的三段式纪律。
- **第三方口径类（needs_verify 挂牌，不背书）**：① gitee 仓库树 HTML 页被安全验证码拦截，目录清单与正文取自 API/raw 直链，页面交互层未独立复核；② sig.yaml 的**精确包总数**（数千条，未逐一计）、**14 名 maintainer 完整名单**、**包级维护者全量映射**均为文件单方呈现，未独立复现；③ `贡献积分排行.md` 的具体名次/分值；④ 社区 LICENSE 精确条款——均 `needs_verify`。

诚实边界重申：本文技术要点来自 2026-10-25 的只读抓取（API/raw 直链），以文件当时呈现为准。openKylin 发行版版本代号（`yangtze`）、版本后缀（`-ok1`）、工具链（debmake/dpkg-buildpackage/gbp）等均来自官方 SIG 文档原文，可信度高；但包总数、维护者全量名单、积分榜单数值为文件单方陈述，未独立复现（`needs_verify`）。

## 三、分主题学习笔记

### 3.1 SIG 治理：职责边界显式化 + 三级维护者

- **职责（README 原文）**：制定/发布/维护社区打包规范、打包原则、依赖规范；执行技术委员会包引入/退出机制、预审软件包进入发布版申请；维护管理公共软件包；协调发布软件包清单（与 sig-release、sig-QA 共撑版本发布）；协调各 SIG 包划分与依赖冲突；建立维护包管理工具框架（自动化、可溯源）；维护版本发布件软件包基线列表。
- **治理层级**：SIG Owner（`maozhou`）→ 顶层 maintainer（sig.yaml 列 14 名，含 owner）→ **包级专属维护者**（packages 列表中部分包以嵌套结构指定，未必在顶层名单，如 `bash`、`openjdk-17/25`、`avahi`）。责任下沉到具体包，避免「谁都管、谁都不管」。
- **可复用纪律**：① 职责边界**逐条显式罗列**（不像很多项目把治理藏进 wiki）→ 本仓 `docs/packaging.md` 的「总原则表 + 各自规范对照表」同构；② 三级维护者 ↔ 本仓「子项目自包含、各端各自规范、顶层命名一致性」的分责任纪律同构。本仓无 SIG/积分治理 counterpart，不落地。

### 3.2 打包 SOP：源码包规范化 ↔ git 反向构建 双轨

- **流程（打包实践操作指南原文梳理）**：
  1. 取上游源码 tarball（压缩包名版本号须与源码版本一致）；
  2. `debmake` 生成 `debian/` 模板（control/copyright/changelog/rules/source/format/watch/patches/series…）；
  3. 改 `debian/changelog`：版本号 `0.0.1-1` → `0.0.1-ok1`，distribution `UNRELEASED` → `yangtze`；按上游实际改 `debian/control`（Build-Depends、Section、Standards-Version 等）；
  4. `dpkg-buildpackage -S -nc --no-sign` 出 `.dsc` / `.debian.tar.xz` / `.buildinfo` / `.changes`（source format `3.0 (quilt)`）；
  5. 在 `packages/` 建 `<pkg>.yaml` 维护信息（`name/path/maintainers`），向 `openkylin/community` 提 PR；
  6. PR 合入后平台**自动建 `openkylin/<pkg>` 仓库**；
  7. `git-buildpackage`(gbp) `import-dsc --pristine-tar --debian-branch=openkylin/yangtze --upstream-branch=upstream` 反向构建 git 仓库；可改 `debian/source/format` 为 `3.0 (native)`；推 gitee。
- **可复用纪律**：① **源码包 ↔ git 仓库双轨**，pristine-tar 锁定 orig tar 内容防重打包漂移 ↔ 本仓 `--check` 防漂移、schema 版本化同构；② **发行版标记外置**（`-ok1` 后缀 + `yangtze` 代号）使「哪个发行版、哪次社区修订」一目了然 ↔ 本仓 D 段升版 `NNNN.NNNN.NNNN.NNNN.YYYYMMDD` 的可溯纪律（口径不同、精神同构）；③ **源码树与交付件分离**（`.deb`/`.dsc` 不污染源码树）→ 本仓 `classics-linux/build/*.deb` 归档、`*.deb` 根级忽略同构。本仓无 dpkg/gbp 工具链 counterpart（仅有 Debian `debian/` + Arch `PKGBUILD` 静态元数据），不接入外部工具。

### 3.3 协作范式：fork→改→PR→平台自动构建测试

- **开发者贡献指南**：fork `openkylin/<pkg>` → clone → 改源码（示例按 `LANG` 输出中/英）→ add/commit/push → 网页提 PR → **maintainer 审核通过即由平台自动打包/测试/编译**。
- **可复用纪律**：① **合入即触发平台自动构建测试**的 CI 门禁（质量闸门前移）→ 本仓 `audit-concepts.yml` + `build-*.yml`「提交前门禁全绿再合 main」同构；② 标准上游协作（fork/PR/审核）↔ 本仓开源协作纪律同构。本仓无发行版 CI 平台 counterpart（仅有 GitHub Actions 工作流守护概念组网与多端构建），不落地。

### 3.4 贡献度量：多因子加权积分

- **评审规则**：日常积分 `= b*n*3 + c*n*2 + d*n`（b=PR 内容[1,5]、c=代码质量[1,3]、d=maintainer 评审 PR 数[0,5]、n=PR 数）；首次上传源码包 `50*n`；技术决策 `a*n*3`（a∈[1,5]）。
- **可复用纪律**：**多因子加权**（内容质量/代码质量/评审贡献/技术决策）而非单纯数 PR，使贡献度量更贴近真实价值 ↔ 本仓「可审计、可溯源、概念体检零悬空」的量化治理精神同构。该规则为社区治理文本，本仓无对应系统，仅作编目学习。

## 四、落实动作（本仓只对照沉淀，不落地外部代码/概念）

- 本文为**只读学习笔记**，不向本仓引入任何新概念、新依赖、新构建步骤；openKylin 发行版治理/工具链/积分系统本仓**无 counterpart**，按 #591 纪律一律只沉淀、对照既有 `docs/packaging.md`，不新增概念。
- 与本仓既有 `docs/packaging.md` 的**对照结论**：openKylin 是「单一 Debian/OK 体系 + 社区 SIG 准入 + 贡献积分」的发行版级治理；本仓是「多端 monorepo（Debian/Arch/Rust/Python/鸿蒙/Apple/Swift/Web/Windows）各自规范 + 兼容性默认 `.pyz`」的跨平台策略。**二者在「因地制宜、分段讨论、分别应用、兼容层兜底」总原则上同构**，可作为本仓多端打包策略的外部佐证笔记留存。
- 待核实项（`needs_verify`，若用户要求可单独立项补抓）：gitee 树页 HTML 交互层、sig.yaml 精确包总数与 maintainer 全量名单、包级维护者全量映射、`贡献积分排行.md` 具体数值、社区 LICENSE 精确条款。
- 既有 sysweeper 只读层/文档/HTML 不受影响；本仓发布工件（deb/压缩包/多架构二进制）与本文无关。
