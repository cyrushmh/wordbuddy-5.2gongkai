# AGENTS.md

本文件为在本仓库工作的 AI 编码代理提供指引。结构参考 Outline Foundation 的 outline-sdk（AGENTS.md 模式），内容按本仓库（system-optimizer / sysweeper）真实约定本地化。

## 模块结构（多语言，已声明不限制程序语言）

- `src/python/sysweeper/` —— **逻辑层**（Python）。诊断、子系统、JSON 接口、CLI 都在这里。
- `src/deno/` —— **HTTP 外壳 + 查看器**（Deno / TypeScript）。`console.ts` 本机 Web 控制台；`report_viewer.ts` 远端报告查看器；`web/` 静态前端（HTML/JS）。
- `src/go/main.go` —— **CLI 入口**（Go），仅薄封装。
- `src/uni-app/` —— **移动端前端**（Vue3 + uni-app），一套代码覆盖 H5 / App / 微信小程序，对接 `console.ts` 的 `POST /api`。
- 另见历史 feature 分支：`feature/rust-multi-gui`、`feature/multi-lang-tools`（跨语言 GUI 探索）。
- 工作分支：`personal-branch`（用户推送目标）；`main` 为基线；不要直接向 `main` 推功能。

## 命令

- Python 测试：`python3.11 -m pytest tests/ -q`
- 前端语法：`deno check src/deno/console.ts src/deno/report_viewer.ts`；`node --check src/deno/web/app.js`
- 端到端冒烟：`python3.11 tools/smoke_web_jdk.py`（Playwright headless chromium；需 `PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright`）
- 不变量校验：`python3.11 -m pytest tests/test_repo_guard.py -q`（版本号一致性 + 红线审计）

## 红线（只读优先，最高优先级）

本仓库是**系统优化/诊断工具**，但对外只暴露**只读诊断 + 用户自己的配置文件读写**。任何破坏这条红线的改动都必须拒绝或改走用户显式 `--yes` 路径：

1. **webapi 只暴露只读诊断**：动作在 `src/python/sysweeper/webapi.py` 的白名单里**静态登记**（第三字段 `readonly`）；无 `getattr` 动态派发、不 `eval`、不执行导入内容。
2. **禁止动作**：清理 / 应用变更 / 启停系统服务 / 写系统位置 / 加载内核模块 / 重启。各子系统有命令子串黑名单——新增探测命令前先对照 `FORBIDDEN_COMMANDS`（kmod）、`FORBIDDEN_SUBCOMMANDS`（jdk）等。
3. **Deno 最小权限**：控制台只申请 `--allow-net --allow-read --allow-run`，**刻意不申请** `--allow-write` 与 `--allow-env`（控制台本身不写文件、不读环境变量）。改权限模型前先想清楚是否真需要。
4. **诊断函数只跑在册只读报告**：异常只标「异常」，绝不外抛堆栈到前端。

## 版本号同步（5 处必须一致）

升版本时**同时**改以下 5 处，否则 `test_repo_guard.py` 会红：

- `src/python/sysweeper/__init__.py`（`__version__`）
- `pyproject.toml`（`version`）
- `src/go/main.go`（`const version`）
- `src/deno/console.ts`（`VERSION` 常量 + 文件头注释）
- `src/deno/report_viewer.ts`（`VERSION` 常量 + 文件头注释 + `schema` 行的 `version` 字段）

## JSONL 桥契约

- Python 是逻辑后端，Deno 是 HTTP 外壳：请求经 `POST /api` 发 `{action, params, source}`，回 `{ok, data}`（或 `{ok:false, error}`）。
- 并发请求由 Deno 侧用 **Promise 链串行化**（JSONL 行协议），避免 Python 子进程交错。改并发模型前先确认串行化仍成立。
- 新增动作 = 在 `webapi.py` 白名单加一行 + （如需要）前端加按钮/渲染块 + 补 `tests/` + （如改了报告形状）同步 `report_viewer.ts` 与 `report_viewer.html`。

## 坑点

- **静态查看器需手动重生成（已被 CI 强制）**：`report_viewer.html` 是从 `report_viewer.ts` 的 `page()` 模板抽出的生成物。改了 `.ts` 的渲染块或版本号后，重跑 `python3 tools/gen_report_viewer.py` 重新生成 `.html`，它会在顶部写入「源模板 SHA256」标记。`scripts/check_repo_guard.py` 的「生成产物 SHA 同步」检查会复算并比对，不一致直接失败——不用靠人记。
- **圆光术拓扑页同样需手动重烘焙（被 tests/test_concept_gui.py 强制）**：`concept_gui.html` 是 `tools/gen_concept_gui.py` 把 `concepts.topo()/overview()` 实测数据烘焙出的单文件静态页（圆光术范式：中心光晕 + 9 系统环 + 桥接辐射线 + 9×9 矩阵）。改了任何 `data/concepts/*_taxonomy.json` 或概念系统代码后，重跑 `python3 tools/gen_concept_gui.py`；页面顶部写「数据摘要 SHA256」，`--check` 用实时数据复算比对，不一致直接失败（`tests/test_concept_gui.py::test_committed_page_is_in_sync` 同步守护）。
- **Deno Deploy 已退场**：2026-10-09 Deno 团队并入 Cloudflare，Deno Deploy ≈2027-04 停止。远端展示走单文件静态 `report_viewer.html`（零外链/零 fetch/零后端），不要新建 Deno Deploy 部署。
- **前端 CORS**：`console.ts` 的 `/api` 无 CORS 头——App/小程序端可直连；H5 跨域受限时由「报告」页粘贴 JSON 快照模式兜底（全端通用）。
- **git 路径无 `system-optimizer/` 一级**：git 根直接是 `src/`，Deno 入口是 `src/deno/report_viewer.ts`。

## 工作流

- 提交用约定式提交，scope 用模块/功能：`feat(v0.6.27): …`、`feat: …`、`docs: …`、`test: …`、`fix(webapi): …`。
- 新功能/新动作都要有测试（`tests/` 同层；纯 JS 模块 `node --check`；`.vue` 经 `@vue/compiler-sfc` 真编译）。
- 不变量（版本一致、红线）由 `test_repo_guard.py` 守护，改相关文件后先跑它。
- 跨语言新增（Rust/鸿蒙/其他）放独立目录或独立 feature 分支，不要污染 Python 逻辑层的核心只读契约。

## 外部代码准入（脏话 / 规避拼音 前置检测）

处理任何**不是本项目自己写的**代码或资料之前（用户导入的仓库/文档、`research/harvest` 抓取数据、第三方 SDK、他人提交），**先跑一次**：

```bash
python3 tools/lint_swear.py <路径>                # 干净 = 退出码 0
python3 tools/lint_swear.py <路径> --strict       # 零宽字符污染也算失败
python3 tools/lint_swear.py <路径> --json         # 机器可读（CI 用）
```

命中 ERROR 先如实报告再决定怎么处理，**不要静默带入本仓库**。

工具设计要点（改词表/白名单前先读 `tools/lint_swear.py` 顶部注释）：

- 拼音/外文一律**整词边界**匹配 —— `minimal` 里的 nima、`mojibake` 里的 jiba、`Brainfuck` 都不误报。
- 三层归一化防规避：**NFD 去声调**（带调拼音 → 去调后命中词表）+ **同形字映射**（西里尔/带抑扬符/全角字形 → 拉丁原形）+ **去标点分隔符**（点杠星号分隔的写法 → 连写后命中）。零宽字符（U+200B 类）单独报 INFO。
- 白名单只在**命中位置 ±30 字符窗口**内生效，不整行豁免，避免一行里既有技术词又有真脏话时被放过。
- 已知取舍：拼音三字母的**空格**分隔写法检不出 —— 归一化若删空格，英文句子（`what the …` 一类）会粘成一团，整词边界失效、真脏话反而漏网。删空格的误报代价远大于收益。
- 大小写敏感的豁免放 `ALLOW_LINE_CS`（人名缩写 `J.B.` 之类），否则小写规避写法会蹭到豁免。

新增技术误报项时：**往 `ALLOW_LINE` 追加正则 + 在 `tests/test_lint_swear.py` 补一条 `test_no_false_positive_*`**。误报一旦泛化，这个门禁就会被人关掉，等于没有。

## 学习来源（已导入分析，见 `docs/导入仓库分析-学习应用.md`）

- outline-sdk（Go 网络 SDK，Apache-2.0）：本 AGENTS.md 的文档结构即应用其模式；其「稳定核心/实验扩展分离 + 版本钉死」「许可证白名单」「跨平台纯层」值得借鉴。
- windows-2000-supermium（Chromium BSD-3-Clause）：Windows API 版本差目录、声明式补丁清单 + SHA 校验模式可应用于 kmod/diagnose 与发布完整性。
- mihomo-kubernetes（GPL-3.0）：常驻依赖 + 「看门狗/定时重启绕过敏感泄漏」的运维模式，适用于未来的 distcompute 常驻组件（注意：GPL-3.0 强拷贝左，不要因此引入 GPL 依赖到本宽松许可项目）。
