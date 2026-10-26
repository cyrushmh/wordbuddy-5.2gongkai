# 26 · 接口 API 概念系统（v0.6.59）

以仓库 **wordbuddy-github 为主目录（概念系统）** 新增的**接口 API 层**：把公开的
接口设计理念（风格/规约/传输/认证）按五轴结构化登记，并单开 `repo-face` 轴把
**本仓库自己的接口面**以实测事实入册（只读、不联网），桥接到 `daoxue`（治理原则）、
`netsys`（网络组网模块）。

## 1. 五轴结构（32 个概念）

| 轴 | 定位 | 概念数 | 内容 |
|---|---|---|---|
| `style` | 接口风格 | 9 | 客户端与服务端的交互范式：REST / GraphQL / gRPC / WebSocket / SSE / MQ / Webhook / JSON-RPC / CLI 契约 |
| `spec` | 规约标准 | 6 | OpenAPI Specification / GraphQL SDL / Protobuf IDL / JSON Schema / AsyncAPI / WSDL·SOAP（遗留） |
| `transport` | 传输绑定 | 6 | HTTP/1.1 / HTTP/2 / HTTP/3·QUIC / TCP / WebSocket / JSONL 行式绑定 |
| `auth` | 认证授权 | 6 | Basic / Bearer·JWT / OAuth 2.0 / mTLS / API Key / 服务端刷新令牌纪律 |
| `repo-face` | 本仓库接口面 | 5 | 以当前仓库实测事实登记的接口面（见下） |

## 2. 标准登记：12 条 RFC（全验证）+ 1 条 IDL

所有 RFC 编号经本仓库 `rfc_catalog`（10,036 条官方 RFC INDEX 本地解析）
**交叉验证存在性并回填标题**：

| RFC | 标题 | 归属概念 |
|---|---|---|
| 9110 | HTTP Semantics | rest |
| 9112 | HTTP/1.1 | http11 |
| 9113 | HTTP/2 | http2 |
| 9114 | HTTP/3 | http3 |
| 9000 | QUIC: A UDP-Based Multiplexed and Secure Transport | http3 |
| 9293 | Transmission Control Protocol (TCP) | tcp |
| 6455 | The WebSocket Protocol | websocket |
| 7617 | The 'Basic' HTTP Authentication Scheme | auth-basic |
| 7519 | JSON Web Token (JWT) | auth-bearer-jwt |
| 6750 | OAuth 2.0 Bearer Token Usage | auth-bearer-jwt |
| 6749 | The OAuth 2.0 Authorization Framework | auth-oauth2 |
| 5280 | Internet X.509 PKI Certificate and CRL Profile | auth-mtls |

另登记 1 条非 RFC 规约：Protobuf IDL（grpc）。

## 3. repo-face：本仓库接口面（构建时实测，防漂移）

| 事实 | 实测值 |
|---|---|
| CLI 子命令数 | **103**（构建时从 argparse 子解析器逐个数出） |
| webapi ACTIONS 数 | **29**（构建时从 `sysweeper/webapi.py` 白名单读出） |
| webapi 协议 | JSONL：一行请求 JSON → 一行响应 JSON；ACTIONS 白名单制，无 `getattr` 兜底派发 |
| 插件 API | `native/plugins.py`：`effective_allowlist()` 静态白名单 + `register_native()` 显式扩展；manifest native 字段必须在白名单内 |
| report 结构 | `report.build_report()` → `{disk:{before,after}, tasks[]}`；`render_markdown`/`render_bars` 渲染 |
| report_viewer 守护 | `tools/gen_report_viewer.py` 生成 + `check_repo_guard.py` sha256 守护（漂移即失败） |

**防漂移机制**：`build_apilab.py --check` 会把**磁盘 JSON 登记值**与**源码实测值**
逐键比对，不一致即失败——实测链路在开发期真实检出过 99→102→103 的漂移链并重建。

## 4. 桥接：12 条边到既有概念系统（无悬空）

| 目标系统 | 边数 | 代表 |
|---|---|---|
| `daoxue` | 8 | `principle:xin-yan-bu-mei`（信言不美：错误响应如实）、`principle:zhi-bu-zhi`、`principle:pu`（见素抱朴：接口最少依赖）、`principle:daofa-ziran`、`principle:shou-zhong` |
| `netsys` | 4 | `module:meshchat`（组网通信）、`module:network`、`module:cert`（mTLS 证书纪律）、`module:zerotier` |

## 5. 用法

```bash
# CLI（只读不联网）
python3 -m sysweeper apilab                  # 五轴速览
python3 -m sysweeper apilab auth             # 认证授权轴全部概念
python3 -m sysweeper apilab of repo-cli      # 单概念（含桥接边）
python3 -m sysweeper apilab repo             # 本仓库接口面实测事实（103 CLI / 29 ACTIONS）
python3 -m sysweeper apilab rfc               # 引用的 12 条 RFC 登记册
python3 -m sysweeper apilab bridge daoxue    # 接口理念 → daoxue 的桥接边
python3 -m sysweeper apilab search 令牌       # 跨轴检索
python3 -m sysweeper apilab verify           # 诚实边界
python3 -m sysweeper apilab stats            # 规模统计

# 构建与防漂移（磁盘登记值 vs 源码实测值）
python3 research/apilab/build_apilab.py --check

# GUI：底部「接口 API」按钮（五页：五轴分类轴 / 标准登记册 / 仓库接口面+RFC 依据 / 桥接 / 检索·待核实）
```

## 6. 诚实边界与红线

- repo-face 轴条目**以当前仓库实测事实登记**（构建时从 argparse 与 webapi.py
  读出子命令数/ACTIONS 数），不写无法核实的数字；本系统 `needs_verify` 仅一条
  口径说明（meta 级），repo-face 数字不设 needs_verify——要么实测、要么不登记。
- **认证处置纪律（红线，承接 daoxue 原则）**：令牌禁入 URL 查询参数、禁入
  localStorage；私钥不明文落盘/回显；访问令牌短时效 + 服务端刷新令牌。
- 接口风格轴登记**公开设计范式**，不代表本仓库全部实现了对应风格的服务端。

## 7. 文件清单

| 文件 | 作用 |
|---|---|
| `research/apilab/build_apilab.py` | 可复现构建 + `--check`（磁盘 vs 源码实测防漂移）；桥接悬空即失败 |
| `src/python/sysweeper/data/concepts/apilab_taxonomy.json` | 数据层（5 轴 / 32 概念 / 12 桥接 / 12 RFC + repo_face_facts） |
| `src/python/sysweeper/concepts/apilab.py` | 只读层（通用 API + `standards`/`repo_facts`） |
| `src/python/sysweeper/cli.py` | CLI 子命令 `apilab`（10 个动作） |
| `src/python/sysweeper/gui.py` | GUI 面板 `show_apilab` + 底部「接口 API」按钮 |
| `tests/test_apilab.py`、`tests/test_gui_quantum.py` | 数据层不变量（含与源码实测动态比对）+ GUI mock 冒烟 |

## 8. 遗留与后续

- CLI 子命令数随功能增长而变化（103 为当前实测值）：每次新增子命令后
  `--check` 会要求重建，属**预期行为**（防登记漂移）。
- webapi ACTIONS 如新增，同样触发重建；JSONL 协议与白名单制纪律不变。
- 可增加「风格 → 本仓库实际取舍」的对照概念（如为何 webapi 选 JSONL 而非 WS）。
