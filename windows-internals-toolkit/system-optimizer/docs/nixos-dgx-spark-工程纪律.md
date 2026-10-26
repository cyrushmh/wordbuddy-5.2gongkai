# nixos-dgx-spark 工程纪律 · 提炼与本地应用

> 来源仓库：<https://github.com/graham33/nixos-dgx-spark>（CLAUDE.md + .github/workflows）
> 应用目标：本项目"新增文件"时，沿用其可复用工程纪律（**不**照搬其 Nix/gettext 实现，它本身不含 i18n）。

---

## 1. 提炼出的可复用模式

| # | 模式 | 仓库里的形态 |
|---|---|---|
| P1 | **模块化分层（flake-parts）** | 系统无关输出进 `flake` 块，per-system 进 `perSystem`；`systems=[...]` 显式声明支持架构 |
| P2 | **git 先追踪再构建** | flake 只认 git 跟踪文件；未 `git add` 的新文件在求值期报"path does not exist" |
| P3 | **pre-commit 门禁** | `nixpkgs-fmt` / `prettier`(md) / `trailing-whitespace` / `end-of-file-fixer`；提交前 `pre-commit run --all-files` |
| P4 | **README 表格登记** | 每个 playbook 在顶层 README 加一行；注册即入 CI 矩阵 |
| P5 | **label-gated CI** | `full-build` 按 cpu-hour 计费、opt-in；常规 PR 只跑 `check`，昂贵构建手动打标 |
| P6 | **写作规范统一** | 文档/注释/commit 统一 British English |
| P7 | **fork PR 最小权限** | 跨仓 PR 无 secret，昂贵构建须手动 dispatch，且先读 diff |

> 注：该仓库**不含 gettext/i18n**——它用 Nix 表达可复现构建。我们的国际化走 GNU gettext（见 `本地化计划.md`），只借其"工程纪律"，不借其翻译机制。

---

## 2. 映射到本项目（system-optimizer）

项目是**纯 Python 标准库**，无 Nix/flake，故 P1/P2 的"Nix 求值"不直接适用，但**纪律精神可转译**：

| 模式 | 本项目对应落地 | 已落实处 |
|---|---|---|
| P1 分层模块化 | `src/python/sysweeper/` 按 `native/`(系统接口)、`tasks/`(平台任务)、`lowcode/`(五层码制)、`data/`(文档 JSON) 分目录；新增代码归到对应层 | lowcode/i18n 走 `sysweeper.i18n` 子模块 |
| P2 先登记再生效 | **新增文件须 `git add` 且进对应目录**，CI/导入才认；未登记的 `.py` 不会被打包 | i18n.py / locales / make_mo.py 已落位 |
| P3 格式门禁 | 接 Python 既有 lint（pylama）；md 表格由 prettier 风格统一；**提交前本地跑 lint** | 测试套件守住行为 |
| P4 登记表 | **新增模块/子命令/能力，在 README 与相关管理表登记一行**（如 lowcode 五层、storage 任务） | README 平台表、storage `fs_lvm_report` 已登记 |
| P5 昂贵构建门禁 | 跨平台/交叉编译（Go 组件、CI 矩阵）按平台 opt-in；不常跑的昂贵步骤手动触发 | `src/go/` 交叉编译单独说明 |
| P6 写作规范 | 项目界面源语言=zh_CN、文档中文；**代码注释/commit 统一简体中文**，不自创英中混排风格 | i18n 源串即中文 |
| P7 外部贡献最小权限 | 本仓库为单人维护，等价纪律：**改依赖/加平台任务前先读 diff、先本地验证** | — |

---

## 3. 对"新增文件"的硬性清单（落地纪律）

每新增一个文件/模块，按此自检（对应 P2/P4）：

1. **归层正确**：放 `native/`(系统接口) 或 `tasks/`(平台任务) 或 `lowcode/`(码制) 或 `data/`(文档) 或 `tools/`(构建脚本)。
2. **git 跟踪**：`git add` 新文件；未跟踪文件不进打包/不进 CI 矩阵。
3. **README 登记**：若是新平台能力/子命令，在 `README.md` 对应表加一行；若是新工具脚本，在 `tools/` 注明用途。
4. **测试兜底**：行为变更加/改 `tests/`，跑 `pytest` 全绿再提交。
5. **本地 lint**：提交前过项目 lint（Python）+ 文档格式。
6. **不污染后台**：界面文案进 i18n，机器数据（opcode/字节）不进 PO（见 `本地化计划.md` 第 1 节）。

---

## 4. 本轮已按此纪律新增的文件

| 文件 | 归层 | 登记/测试 |
|---|---|---|
| `src/python/sysweeper/i18n.py` | lowcode/基础设施 | 测试 `test_i18n_default_zh_and_switch_en` |
| `locales/{zh_CN,en}/LC_MESSAGES/sysweeper.{po,mo}` | i18n 资源 | `make_mo.py` 编译 + 冒烟 |
| `tools/make_mo.py` | 构建脚本 | 零依赖，可单测 |
| `lowcode/bits.py` · `machine.py` · `__init__.py` 改 | 码制层 | i18n 串过 `_()`，测试守住 |
| `docs/本地化计划.md` · 本文 · `LVM-维基知识沉淀.md` | 文档 | README 待补链接 |

---

## 5. 不照搬的部分（边界）

- ❌ 不引入 Nix/flake：项目是纯 Python 标准库，跨平台靠 `shutil.which` 探测与惰性守卫，无需可复现构建系统。
- ❌ 不复制其 gettext 用法：它没有 i18n，我们的 gettext 体系独立设计（源语言 zh_CN、显式 `--locale`）。
- ❌ 不照搬 British English：本项目界面与文档以简体中文为源，写作规范是中文统一。
