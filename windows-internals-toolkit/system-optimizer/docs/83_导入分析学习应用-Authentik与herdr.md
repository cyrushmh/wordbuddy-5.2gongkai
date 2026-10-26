# 导入分析学习应用 batch-7：Authentik（自建身份 IdP）与 herdr（AI Agent 终端复用器）

> 用户指令：「导入分析学习应用引用」——今日头条两篇（自建成身份认证 Authentik；GitHub 趋势榜第一替代 tmux 管理多 Agent 终端）。
> 处理口径：**只读查据，不克隆 / 不安装 / 不构建 / 不复制代码**（系统级红线）；按 docs/59 + #591 纪律——**有 counterpart 回填、无 counterpart 仅沉淀学习笔记、绝不加概念**。

## 0. 链接与来源

| # | 主题 | 头条短链 | 落地域名 | 性质 |
|---|---|---|---|---|
| ① | 自建身份认证用 Authentik（SSO/MFA/LDAP 一个面板） | `m.toutiao.com/is/JDMIdB7xA28/` | toutiao（作者「程序员老王」） | 第三方技术分享文 |
| ② | GitHub 趋势榜第一！专为 AI 编程而生！替代 tmux 管理多 Agent 终端（herdr） | `m.toutiao.com/is/D31SrppLEek/` | toutiao（作者「AI开源求索」） | 第三方技术分享文 |

两篇均为**第三方转述/科普**，非一手官方文档；文中实测数字、star 数、许可条款均按先例挂 `needs_verify`，不取单一值。

## 1. ① Authentik —— 开源自托管身份提供商（IdP）

### 1.1 定位与协议覆盖
- **定位**：完整身份提供商（IdP），把公司内部散落的独立账号（Jenkins/GitLab/Grafana/wiki…）收拢为一处认证、所有系统通行（SSO）。
- **协议覆盖**：OAuth2 / OIDC、SAML、LDAP、SCIM、以及给反向代理用的 **ForwardAuth**（给没有登录功能的内部小工具在反代层套一层认证）。
- **新派应用走 OIDC、老系统只认 LDAP 也能接、内部小工具靠 ForwardAuth**——一个面板收拢新老系统认证。

### 1.2 部署
- 官方推荐 **Docker Compose**（依赖 PostgreSQL + Redis，compose 自带）：`wget https://goauthentik.io/docker-compose.yml`；`openssl rand` 生成 `PG_PASS` / `AUTHENTIK_SECRET_KEY` 写 `.env`；`docker compose up -d`。
- 初始化 `http://localhost:9000/if/flow/initial-setup/`；管理界面 `/if/admin/`。

### 1.3 核心概念（文章「别被绕晕」）
- **Provider（提供商）**：对接某应用的协议配置（如「给 Grafana 用的 OIDC Provider」）。
- **Application（应用）**：被保护的系统，绑定一个 Provider。
- **Flow（流程）**：登录/注册/找回密码等可编排步骤；**MFA 即往登录 Flow 插一个验证 Stage**。
- **Stage（阶段）**：Flow 单步（输密码 / 验 TOTP / 同意授权）。
- 配一个应用接入 ≈ 「建 Provider → 建 Application 绑上去 → 调整 Flow」三步。

### 1.4 接入示例（Grafana 走 OIDC）
`grafana.ini` 的 `[auth.generic_oauth]`：`client_id`/`client_secret`/`scopes=openid profile email`/`auth_url`/`token_url`/`api_url`；`role_attribute_path = contains(groups,'grafana-admins') && 'Admin' || 'Viewer'`。加 MFA 只在 Authentik 登录 Flow 加 TOTP Stage，**所有接入应用一起生效**——安全策略集中管。

### 1.5 同类对比（文章口径）
| 方案 | 开源自托管 | 协议覆盖 | 上手难度 | 适合 |
|---|---|---|---|---|
| **Authentik** | 是 | OIDC/SAML/LDAP/ForwardAuth 全 | 中（概念多） | 中小团队全场景自建 |
| Keycloak | 是 | 全、老牌 | 偏重（Java 系） | 大型、要成熟生态 |
| Authelia | 是 | 主打反代 ForwardAuth | 轻 | 只想给反代加认证 |
| Okta / Auth0 | 否（SaaS） | 全 | 低 | 不想自运维、预算够 |

### 1.6 几个坑（文章经验）
1. **别裸 HTTP 上生产**——身份系统是全公司钥匙串，务必 HTTPS、密钥妥善保管。
2. **Flow 配错会锁自己**——改登录 Flow 留后路、先备份（作者曾误删 Stage 进容器改库救回）。
3. **独立 worker 进程**跑后台任务（邮件/LDAP 同步/过期清理），部署别只起 server 忘 worker，否则静默不工作。

### 1.7 诚实边界
- 文章**未给出 Authentik 具体 LICENSE 条款**（needs_verify）；开源自托管属实但许可义务未独立核实。
- 对比表中的 star/市占等均为文章单方口径（needs_verify）。
- **不复制 / 不链接 / 不移植**任何 Authentik 代码（GPL/AGPL 类工具均遵守）。

## 2. ② herdr —— Rust 编写的 AI Agent 终端复用器

### 2.1 定位
- 终端原生的 **AI Agent 运行时与多路复用器**，被开发者称为「AI 时代专属 tmux」；专门解决**多 AI 编程 Agent 统一管理**痛点（Claude Code / Codex / Cursor / Devin… 多开分不清谁在跑、谁在等审批、谁已跑完）。
- **精确措辞**：tmux 管理终端会话，herdr 管理终端里运行的 AI Agent——不是「替代 tmux」，是补上 Agent 感知 / 会话恢复 / 自动化编排。
- 2026-03 诞生，上线后登 GitHub Trending。

### 2.2 基础参数（文章口径，needs_verify 项见 §2.7）
- **语言**：Rust，单二进制分发，无 Electron / 无 GUI 依赖。
- **兼容 Agent**：Claude Code、Codex、Cursor Agent、Devin CLI、GitHub Copilot CLI、Kimi Code CLI、Grok CLI、OpenCode、Pi 等。
- **许可证**：AGPL-3.0-or-later，并提供商业许可选项。
- **生态**：macOS / Linux 支持，Windows 为**预览支持**；可在 tmux 中运行。
- **官方地址**：herdr.dev / github.com/herdrdev/herdr。

### 2.3 herdr vs tmux 核心对比
| 能力维度 | tmux | herdr |
|---|---|---|
| 会话持久化 / 断连重连 | ✅ | ✅ |
| 分屏 / 标签 / 多工作区 | ✅ | ✅ |
| SSH 远程连接 / 跨设备重连 | ✅ | ✅ |
| Agent 实时状态自动识别 | ❌ | ✅ |
| 开箱即用（无需配置） | 需配置 | ✅ 更轻量 |
| 原生鼠标拖拽分屏 / 窗口点击 | 需配置 | ✅ |
| Agent 自主编排 / 跨窗格调度 | 主要靠人工脚本 | ✅ CLI 与 Socket API |
| Agent 深度语义集成（会话恢复） | 无 | ✅ 部分 Agent |
| 运行中服务无缝迁移 | ❌ | 实验性（update --handoff） |

**操作对齐 tmux**：默认前缀 `ctrl+b`；`v` 右分屏 / `-` 下分屏 / `c` 新建标签 / `q` 断开客户端（Agent 后台持续）/ `w` 切换工作区 / `?` 全部快捷键。

### 2.4 三大核心能力
1. **Agent 状态全局感知**：状态分 `blocked`（卡住等确认/密钥/审批）/ `working` / `done` / `idle`；识别原理——基础模式（进程名匹配 + 终端输出启发式，多数 CLI 开箱识别）、深度集成（部分 Agent 官方集成，更精确语义状态 + 原生会话恢复）。
2. **轻量上手**：一行命令安装即启动；鼠标原生（点击窗格/切标签/拖分隔边框）；右键菜单常见操作；配置非必须（官方 README 明确无需配置文件）。
3. **Socket API 实现 Agent 自主编排**：CLI + 本地 Socket API 作为一等能力，支持「Agent 调度 Agent」（完成开发→自动开新窗格启审查 Agent；主 Agent 拆分测试/文档/接口为并行子 Agent；完成任务自动切工作区/通知/清理闲置进程）。安装官方技能包 `npx skills add herdrdev/herdr --skill herdr -g`。

### 2.5 落地实操要点
- **安装**：Linux/macOS `curl -fsSL https://herdr.dev/install.sh | sh`；Windows PowerShell/Bat；Homebrew / mise / Nix；源码 `git clone … && cargo build --release`。
- **基础流**：`herdr` 启动 → 窗格启 Agent（claude/codex）→ 鼠标/快捷键分屏 → 侧边栏看状态优先处理 blocked → `ctrl+b q` 断开后台继续 → `herdr` 重连。
- **远程**：SSH 后直接 `herdr`，或本地 `--remote ssh://you@server:2222` 连远程会话。
- **集成**：`herdr integration install claude` / `codex`；`herdr integration status` 查状态。
- **实验功能**：`herdr update --handoff`（运行中窗格/进程迁新版本，实验性）。

### 2.6 选型指南（文章）
- **继续 tmux**：个人 `.tmux.conf` 高度定制、主要 shell/vim/运维、只跑 1–2 个 Agent、已用 hooks/脚本稳定工作流。
- **优先 herdr**：并行 ≥3 个 Agent、不想维护复杂终端配置、需远程长期驻留 Agent、希望关机/断网任务不丢失或可恢复、想搭多 Agent 协作流水线。

### 2.7 诚实边界与风险（文章 + 本仓复核）
1. **许可证风险**：AGPL-3.0-or-later，修改源码并分发需关注 AGPL 义务。
2. **状态检测局限**：不同 Agent 识别精度不同，小众/新增 Agent 可能只支持基础检测。
3. **版本迭代快**：命令/集成/行为可能随版本变化。
4. **嵌套限制**：herdr 可在 tmux 中运行，但多层嵌套影响交互流畅度。
5. **Windows 支持**：当前预览支持，部分终端环境兼容性待验证。
- star/fork 计数页面未呈现（needs_verify）；AGPL 代码**不复制 / 不链接 / 不移植**。

## 3. 边界分级（counterpart 判定，守 #591/docs/59 铁律）

| 资源 | 候选子系统 | 判定 | 处理 |
|---|---|---|---|
| Authentik（IdP/SSO/LDAP/OIDC） | `netauth.json`（网络隐私验证，空占位桩 `items:0`、明确「不自动填充正文」） | **无真实 counterpart**：netauth 是「网络隐私验证」桩、非身份提供商域；全仓 `data/` 无 sso/ldap/oidc/idp/mfa 关键词命中 | **仅学习笔记，不新增概念、不填充 stub** |
| herdr（AI Agent 终端复用器） | `reverse_docs` / `toolchain_catalog`（候选，非实装） | **无真实 counterpart**：全仓 `data/` 无「终端复用器 / Agent 运行时」数据层归宿；rfc/toolchain 中的 `tmux`/`agent`/`multiplex` 命中为协议/工具链上下文误碰（如 RFC 术语、toolchain 资产名），非概念归宿 | **仅学习笔记，不新增概念** |

> 本仓既有「导入分析学习应用」先例（docs/69/70/72/73/76/77/81）一贯做法：**无 counterpart 一律只沉淀学习笔记、不新增概念、不污染权威数据、不填充空 stub**。本轮严格沿用。

## 4. 候选映射（仅标注，不创建、不实现）

- **Authentik → `netauth`（needs_action 候选）**：若未来补全「身份提供商」域（SSO/LDAP/OIDC/SAML/ForwardAuth/SCIM + Authentik/Keycloak/Authelia 对照），可作回填落点；当前 netauth 为「网络隐私验证」空桩，不在本轮扩展其语义。
- **herdr → `reverse_docs` / `toolchain_catalog`（needs_action 候选）**：作为「Agent 运行时 / 终端工具」候选登记；当前无实装数据层。

## 5. 可复用工程纪律（仅纪律层面，非功能移植）

- **CLI + Socket API 一等公民（Agent 调度 Agent）** ↔ 本仓 opt-in 写入类「选择 + 确认」先例（非破坏性执行、先划边界再讲能力）。
- **Agent 状态四态感知（blocked/working/done/idle）** ↔ 本仓 native 探针状态机（`working`/`idle`/`blocked` 降级不炸主流程）。
- **生命周期 pause/resume 持久化（关机/断网恢复）** ↔ 本仓 `restart_docs` / 持久化口径（只读盘点、不自动重启）。
- **配置非必须但支持（开箱即用 + 可选配置）** ↔ 本仓双 HTML 生成器 / 构建脚本 `--check` 防漂移（可缺省配置、可校验）。
- **AGPL 义务披露前置** ↔ 本仓 README 风险警示「先划边界再讲能力」。
- **混合工具链单仓集成（Rust 核心 + 多平台安装器）** ↔ 本仓多语言四入口（`src/` 14 语言组件 + Windows PE 查看器 `parity_test.py`）分层接线。

## 6. 落点

- **新增** `docs/83_导入分析学习应用-Authentik与herdr.md` 学习笔记（两篇事实 + 边界分级 + 诚实边界 + 候选映射 + 可复用纪律）。
- **README 本块**（0024 块内追加导入分析 batch-7 条目）。
- **不改动**：任何概念数据语义、概念系统拓扑与桥接、`netauth.json` 空桩、版本号（本轮为学习笔记、无功能/数据层改动，沿用 `0000.0000.0000.0024`）。

## 7. 验证

- 全量 pytest **1755 passed / 6 skipped 零回归**（本轮未改任何代码/数据语义，仅增 docs + README 文本）。
- `audit_concepts --strict` 归零（概念系统未动）。
- 双 HTML / 六构建 `--check` 同步（未触发重生）。

## 8. 诚实边界汇总

- 两篇均为**第三方头条转述文**，非一手官方文档；Authentik 具体 LICENSE、herdr star/fork 计数、对比表数字均 `needs_verify`，不取单一值。
- **只读红线恪守**：不克隆 / 不安装 / 不构建 / 不复制代码；Authentik（开源 IdP）、herdr（AGPL-3.0）代码均不复制、不链接、不移植。
- **无 counterpart 不新增概念**（#591）：两资源只沉淀学习笔记，不污染 protec/sciences/baigong/datong/zhuangzi 十一概念系统，不填充 `netauth` 空桩。
