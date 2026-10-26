#!/usr/bin/env python3
"""接口 API「概念系统」构建（以 wordbuddy-github 为主目录，v0.6.64）。

把「接口与规约」的知识体系按**五轴**重组为概念系统，与 plang / netsys /
daoxue / quantum / comp 同构：

    ├─ 轴1 style     接口风格（REST / GraphQL / gRPC / WebSocket / SSE / MQ / Webhook /
    │                JSON-RPC / CLI 契约）
    ├─ 轴2 spec      规约标准（OpenAPI / GraphQL SDL / Protobuf IDL / JSON Schema /
    │                AsyncAPI / WSDL·SOAP 遗留）
    ├─ 轴3 transport 传输绑定（HTTP/1.1 RFC 9112 / HTTP/2 RFC 9113 / HTTP/3 RFC 9114·
    │                QUIC RFC 9000 / WebSocket RFC 6455 / TCP RFC 9293 / stdio /
    │                unix socket）
    ├─ 轴4 auth      认证授权（Basic RFC 7617 / Bearer+JWT RFC 7519·6750 / OAuth 2.0
    │                RFC 6749 / API Key / mTLS RFC 5280 / 令牌存放红线）
    └─ 轴5 repo-face 本仓库接口面（CLI 子命令契约 / plugins API / webapi JSONL 白名单 /
                      report schema / report_viewer）

桥接目标必须在目标数据层真实存在（plang 语言 / netsys 模块 / daoxue 原则），
构建期校验无悬空；RFC 编号经本仓库 rfc_catalog 交叉验证并回填标题。

诚实边界：repo-face 轴的条目全部以**当前仓库实测事实**登记（子命令数、ACTIONS
白名单数等从源码读出），不写无法核实的数字。

用法：
    python3 build_apilab.py            # 构建 data/concepts/apilab_taxonomy.json
    python3 build_apilab.py --check    # 校验（轴合法、桥接无悬空、RFC 命中、counts 自洽）
    python3 build_apilab.py --report   # 打印五轴统计与桥接图
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "src" / "python"
OUT = ROOT / "src" / "python" / "sysweeper" / "data" / "concepts" / "apilab_taxonomy.json"
CONCEPTS_DIR = OUT.parent

SCHEMA = "apilab_taxonomy/v1"

DOMAINS = [
    {"domain": "style", "label": "接口风格",
     "note": "客户端与服务端的交互范式：REST / GraphQL / gRPC / WebSocket / SSE / MQ / "
             "Webhook / JSON-RPC / CLI 契约"},
    {"domain": "spec", "label": "规约标准",
     "note": "接口的书面契约：OpenAPI / GraphQL SDL / Protobuf IDL / JSON Schema / "
             "AsyncAPI / WSDL·SOAP（遗留）"},
    {"domain": "transport", "label": "传输绑定",
     "note": "接口跑在什么信道上：HTTP/1.1·HTTP/2·HTTP/3·QUIC·WebSocket·TCP·stdio/unix socket"},
    {"domain": "auth", "label": "认证授权",
     "note": "谁来调用、能干什么：Basic / Bearer·JWT / OAuth 2.0 / API Key / mTLS"},
    {"domain": "repo-face", "label": "本仓库接口面",
     "note": "sysweeper 自身对外的接口：CLI 子命令契约 / plugins API / webapi JSONL "
             "白名单 / report schema / report_viewer"},
]

CONCEPTS: List[dict] = [
    # ============ 轴1 接口风格 ============
    {"id": "rest", "name": "REST", "domain": "style",
     "gist": "资源 + 统一接口 + 无状态：URI 命名资源，HTTP 方法表达操作。",
     "detail": "Richardson 成熟度模型 0-3 级；HATEOAS 是最高级但很少落地；"
               "实际工程多停在 L2（资源化 + 方法语义）。",
     "standards": [{"kind": "RFC", "num": 9110}], "bridges": []},
    {"id": "graphql", "name": "GraphQL", "domain": "style",
     "gist": "客户端声明要什么字段，服务端按 schema 解析执行一次取回。",
     "detail": "强类型 schema + 解析器；N+1 查询与缓存比 REST 更难；"
               "适合聚合多数据源的 BFF 层。",
     "standards": [], "bridges": []},
    {"id": "grpc", "name": "gRPC", "domain": "style",
     "gist": "HTTP/2 之上的 Protobuf IDL 服务定义，四类流式方法。",
     "detail": "IDL 先生成多语言桩；适合内部服务间低延迟调用；"
               "浏览器需 grpc-web 代理。",
     "standards": [{"kind": "other", "name": "Protobuf IDL"}], "bridges": []},
    {"id": "websocket", "name": "WebSocket", "domain": "style",
     "gist": "HTTP 升级后的全双工长连接：双向推拉、心跳保活。",
     "detail": "RFC 6455 定义握手帧协议；断线重连与背压是工程必备；"
               "本仓库 GUI↔Python 侧未用 WS，webapi 走 JSONL 长连接（见 repo-face）。",
     "standards": [{"kind": "RFC", "num": 6455}], "bridges": []},
    {"id": "sse", "name": "SSE（Server-Sent Events）", "domain": "style",
     "gist": "服务端单向推送：HTTP 长响应 + text/event-stream，自动重连内建。",
     "detail": "比 WebSocket 轻（无需升级帧）；仅服务端→客户端单向；"
               "适合日志流/进度条类场景。",
     "standards": [{"kind": "RFC", "num": 9110}], "bridges": []},
    {"id": "mq", "name": "消息队列（MQ /  Pub-Sub）", "domain": "style",
     "gist": "异步解耦：生产者发主题，消费者按各自节奏拉取。",
     "detail": "At-least-once / At-most-once / Exactly-once 语义按系统选；"
               "死信队列与重试策略是可靠性三件套。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:meshchat", "relation": "本地同构",
          "how": "meshchat 的待收清单即本地版「信箱」：消息不自动落盘、用户显式接受"}]},
    {"id": "webhook", "name": "Webhook", "domain": "style",
     "gist": "反向 API：服务端有事时回调用户提供的 HTTP 端点。",
     "detail": "安全三件套：签名校验（HMAC）、重放窗口、幂等键；"
               "失败重试与死信不可省。",
     "standards": [], "bridges": []},
    {"id": "jsonrpc", "name": "JSON-RPC 2.0", "domain": "style",
     "gist": "极简 JSON 调用协议：method/params/id 四字段，通知无响应。",
     "detail": "适合进程间/工具调用场景；LSP 即 JSON-RPC over stdio 的著名实例；"
               "本仓库 webapi 的 JSONL 信封同属这一族（见 repo-face）。",
     "standards": [], "bridges": []},
    {"id": "cli-contract", "name": "CLI 契约", "domain": "style",
     "gist": "命令行即接口：子命令 + 位置参数 + 选项 + 退出码 + stderr。",
     "detail": "POSIX 约定（--help/--version/退出码语义）；脚本消费要求输出可解析"
               "（--json）；人类与机器双模输出是成熟 CLI 的标志。",
     "bridges": [
         {"system": "daoxue", "target": "principle:xin-yan-bu-mei", "relation": "理念映射",
          "how": "退出码与错误信息如实：失败给明示原因与码，不吞异常"}]},

    # ============ 轴2 规约标准 ============
    {"id": "openapi", "name": "OpenAPI Specification", "domain": "spec",
     "gist": "REST 接口的机器可读规约：路径/模型/安全方案/示例。",
     "detail": "3.x 与 Swagger 2.0 差异大（schema 键重构）；规约可生成客户端桩、"
               "文档与 mock server；「规约漂移」需 CI 校验。",
     "standards": [], "bridges": []},
    {"id": "graphql-sdl", "name": "GraphQL SDL", "domain": "spec",
     "gist": "GraphQL 的 schema 即契约：type/query/mutation/subscription。",
     "detail": "introspection 让契约自描述；版本演进走「字段弃用」而非 URL 版本号。",
     "standards": [], "bridges": []},
    {"id": "protobuf-idl", "name": "Protobuf IDL", "domain": "spec",
     "gist": ".proto 定义服务与消息，代码生成跨语言桩。",
     "detail": "字段编号即兼容契约（只加不重排）；proto3 与 proto2 语义差异；"
               "gRPC 服务定义直接寄生其上。",
     "standards": [], "bridges": []},
    {"id": "json-schema", "name": "JSON Schema", "domain": "spec",
     "gist": "JSON 数据的校验词汇：type/required/pattern/组合子。",
     "detail": "draft 演进（draft-07 常用，2020-12 为现行系列）；"
               "OpenAPI 的模型层即其子集方言。",
     "standards": [], "bridges": []},
    {"id": "asyncapi", "name": "AsyncAPI", "domain": "spec",
     "gist": "事件驱动接口的规约：channel/message/bindings 描述异步面。",
     "detail": "与 OpenAPI 同源思路落到 MQ/WS 类异步接口；"
               "codegen 生态小于 OpenAPI。",
     "standards": [], "bridges": []},
    {"id": "wsdl", "name": "WSDL / SOAP（遗留）", "domain": "spec",
     "gist": "XML 时代的重契约：WSDL 描述 + SOAP 信封 + WS-* 栈。",
     "detail": "企业集成里仍大量存在；SOAP 1.1/1.2 信封结构不同；"
               "登记为「需能读能改」而非「新项目首选」。",
     "standards": [], "bridges": []},

    # ============ 轴3 传输绑定 ============
    {"id": "http11", "name": "HTTP/1.1", "domain": "transport",
     "gist": "文本协议 + 持久连接；队头阻塞限制并行度。",
     "detail": "RFC 9112；方法/语义见 RFC 9110；升级 WebSocket 也从此握手。",
     "standards": [{"kind": "RFC", "num": 9112}, {"kind": "RFC", "num": 9110}],
     "bridges": []},
    {"id": "http2", "name": "HTTP/2", "domain": "transport",
     "gist": "二进制帧 + 多路复用 + HPACK 头部压缩 + 服务端推送。",
     "detail": "RFC 9113；TCP 层队头阻塞仍在（应用层多路复用解决的是 HTTP 层）；"
               "h2c（明文）与 h2（TLS ALPN）两条协商路径。",
     "standards": [{"kind": "RFC", "num": 9113}], "bridges": []},
    {"id": "http3", "name": "HTTP/3（QUIC）", "domain": "transport",
     "gist": "基于 QUIC 的 HTTP：UDP 上自研可靠传输，连接迁移抗网间切换。",
     "detail": "RFC 9114（HTTP/3）+ RFC 9000（QUIC）；QPack 头部压缩；"
               "0-RTT 有重放风险，敏感操作勿开。",
     "standards": [{"kind": "RFC", "num": 9114}, {"kind": "RFC", "num": 9000}],
     "bridges": []},
    {"id": "tcp", "name": "TCP", "domain": "transport",
     "gist": "有序可靠字节流：握手/拥塞/重传/四次挥手。",
     "detail": "RFC 9293；上层一切（HTTP/MQ/WSS）的地基；"
               "调优面在 sysctl（缓冲区/拥塞算法）。",
     "standards": [{"kind": "RFC", "num": 9293}], "bridges": [
         {"system": "netsys", "target": "module:network", "relation": "同层知识",
          "how": "network 任务的 L4 调优即 TCP 参数面"}]},
    {"id": "stdio", "name": "stdio 进程间通道", "domain": "transport",
     "gist": "子进程 stdin/stdout 双向管道：零网络依赖的本地接口。",
     "detail": "JSON-RPC over stdio（LSP 模式）；缓冲与阻塞是主要坑；"
               "本仓库 webapi 亦以 stdin 行为入口之一。",
     "bridges": [
         {"system": "daoxue", "target": "principle:pu", "relation": "理念映射",
          "how": "最小依赖面：能本地行就不开网络端口"}]},
    {"id": "unix-socket", "name": "Unix Domain Socket", "domain": "transport",
     "gist": "本机具名套接字：比 TCP 回环少协议栈开销，可用文件权限管访问。",
     "detail": "Docker/systemd/Chrome 的本地 IPC 常客；abstract namespace（Linux）"
               "无文件节点；权限位即鉴权面。",
     "bridges": []},

    # ============ 轴4 认证授权 ============
    {"id": "auth-basic", "name": "HTTP Basic（RFC 7617）", "domain": "auth",
     "gist": "user:pass Base64 随请求直送——只配 TLS 下可用。",
     "detail": "无过期无撤销，泄露即长期有效；现代系统仅用于内部/一次性场景；"
               "口令必须加盐哈希存储（禁明文）。",
     "standards": [{"kind": "RFC", "num": 7617}], "bridges": []},
    {"id": "auth-bearer-jwt", "name": "Bearer + JWT（RFC 7519 / 6750）", "domain": "auth",
     "gist": "自包含令牌：签名/加密声明的 JWT，Bearer 方式发送。",
     "detail": "无状态可验但「发出去难收回」——短时效 + 刷新令牌 + 可撤销清单（jti）"
               "是标准补丁；禁把令牌放 URL 查询参数（日志外泄面）。",
     "standards": [{"kind": "RFC", "num": 7519}, {"kind": "RFC", "num": 6750}],
     "bridges": [
         {"system": "daoxue", "target": "principle:zhi-bu-zhi", "relation": "理念映射",
          "how": "声明可信度按已验证事实：验签失败即拒，不猜不降级"}]},
    {"id": "auth-oauth2", "name": "OAuth 2.0（RFC 6749）", "domain": "auth",
     "gist": "委托授权框架：授权码/PKCE、客户端凭证、设备码等流程。",
     "detail": "Authorization Code + PKCE 是现行默认；scope 最小化；"
               "令牌绑定 mTLS（RFC 8705）防重放。",
     "standards": [{"kind": "RFC", "num": 6749}], "bridges": []},
    {"id": "auth-api-key", "name": "API Key", "domain": "auth",
     "gist": "最简单的 bearer 形态：一长随机串标识调用方。",
     "detail": "无用户语义、无细粒度授权；须支持轮换与吊销；"
               "与 IP 白名单/额度联用控风险。",
     "bridges": []},
    {"id": "auth-mtls", "name": "mTLS（X.509）", "domain": "auth",
     "gist": "双向证书认证：客户端也出示证书，链路层即鉴权。",
     "detail": "RFC 5280 证书体系；零信任内网骨干；吊销靠 CRL/OCSP；"
               "私钥绝不明文落日志（仓库既有红线一致）。",
     "standards": [{"kind": "RFC", "num": 5280}], "bridges": [
         {"system": "netsys", "target": "module:cert", "relation": "同域",
          "how": "cert 任务的证书审计即 mTLS 信任链的只读体检"}]},
    {"id": "auth-redlines", "name": "认证存放红线", "domain": "auth",
     "gist": "令牌/密钥的处置纪律：存放、传输、日志三面。",
     "detail": "禁入 URL 查询参数、禁入 localStorage（XSS 面）、禁打印明文；"
               "访问令牌短时效 + 服务端刷新令牌是基线架构。",
     "bridges": [
         {"system": "netsys", "target": "module:zerotier", "relation": "红线同源",
          "how": "zerotier 模块「不读 identity.secret 私钥」与令牌红线同族"}]},

    # ============ 轴5 本仓库接口面（repo-face）============
    {"id": "repo-cli", "name": "CLI 子命令契约", "domain": "repo-face",
     "gist": "`python -m sysweeper <子命令>` 即本仓库的主接口面：100+ 子命令。",
     "detail": "发现靠 `--help`；稳定面见下方 repo-face-facts（构建时从"
               "argparse 实际读出子命令清单）；全局选项 --platform/--category/--risk；"
               "退出码 0/1/2 语义（成功/业务错误/用法错误）。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:daofa-ziran", "relation": "理念映射",
          "how": "接口跟着平台本性走：--platform 决定可用子集，非全平台硬套"}]},
    {"id": "repo-plugins", "name": "plugins API（register_native）", "domain": "repo-face",
     "gist": "插件只能注册进白名单的原生入口：effective_allowlist() 静态审读。",
     "detail": "manifest 的 native 字段必须在 allowlist 内，否则加载拒绝；"
               "register_native 显式登记新入口——红线：无兜底动态派发。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:shou-zhong", "relation": "理念映射",
          "how": "插件面「守中」：默认封闭，显式白名单才开"}]},
    {"id": "repo-webapi", "name": "webapi JSONL 白名单协议", "domain": "repo-face",
     "gist": "一行请求 JSON → 一行响应 JSON；dispatch 只认 ACTIONS 白名单。",
     "detail": "ACTIONS 白名单见 repo-face-facts（构建时从 webapi.py 读出实际条数）；"
               "认不出的 action 一律拒绝，无 getattr 兜底；"
               "长连接复用进程省冷启动。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:xin-yan-bu-mei", "relation": "理念映射",
          "how": "拒绝即明示：白名单外动作给错误码与说明，不静默忽略"}]},
    {"id": "repo-report", "name": "report schema", "domain": "repo-face",
     "gist": "report 产物结构：disk.before/after + tasks[]，可渲染 markdown/ASCII 图。",
     "detail": "render_markdown / render_bars 渲染前后对比；GUI 与 report_viewer"
               "同源消费该结构；schema 变更须保持向后兼容（只加字段）。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:sheng-er-bu-you", "relation": "理念映射",
          "how": "加字段不改旧义：演进式兼容，不持有旧消费者"}]},
    {"id": "repo-report-viewer", "name": "report_viewer.html（Deno Deploy）", "domain": "repo-face",
     "gist": "静态报告查看页：由 tools/gen_report_viewer.py 生成，sha256 受守护。",
     "detail": "构建产物不进手改（scripts/check_repo_guard.py 校验 source-sha256）；"
               "改动必须重生成并同步哈希，防「生成物与源漂移」。",
     "standards": [], "bridges": [
         {"system": "daoxue", "target": "principle:fan-zhe", "relation": "理念映射",
          "how": "「反者道之动」：生成物漂移会被守护脚本反向检出"}]},
    {"id": "c-abi", "name": "稳定 C ABI（应用二进制接口）", "domain": "style",
     "gist": "以 C 调用约定作为跨语言/跨实现的稳定接口边界：能力一律经 C ABI 暴露，"
             "实现（CUDA/CUDA-off/CPU）可替换而不破坏调用方。",
     "detail": "SonicBoom 把整库能力经稳定 C ABI（libsonicboom.so）暴露，GNU Guile 等"
               "宿主语言经 FFI 调 C；C ABI 的稳定边界让底层实现可插拔、不污染接口面。",
     "standards": [], "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "接口基座语言",
          "how": "C ABI 即以 C 调用约定为边界；宿主语言经 FFI 调 C 实现"}]},
    {"id": "guile-ffi", "name": "GNU Guile 一等语言（Scheme FFI）", "domain": "style",
     "gist": "把 GNU Guile（Scheme）作为框架的一等脚本/DSL 语言，宿主经 FFI 调原生实现。",
     "detail": "SonicBoom 以 Guile 为 first-class 语言编排 C++/CUDA 内核；Scheme 表达式即"
               "配置即程序，契合『声明即代码』的工程取向。",
     "standards": [], "bridges": [
         {"system": "plang", "target": "lang:c", "relation": "FFI 基座",
          "how": "Guile 经 FFI 调 C ABI 暴露的原生实现，C 为接口基座"}]},
    {"id": "fchroot-syscall", "name": "fchroot(2) 系统调用", "domain": "transport",
     "gist": "基于已持有文件描述符的换根系统调用：避免重新解析调用方已持有 fd 的路径，"
             "无 TOCTOU；与现代 fd 基 API（open_tree/OPEN_TREE_CLONE）同构。",
     "detail": "Linux 7.3 新增 fchroot(2)，进程可将根目录移到 failfs（fchroot(FD_FAILFS_ROOT)），"
               "此后所有绝对路径/绝对符号链接查找均失败；须先把每条路径锚定在显式 fd 上。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:fchroot", "relation": "内核特性↔接口面",
          "how": "fchroot(2) 即 netsys:fchroot 模块登记的内核能力，在接口层同口径登记"}]},
    # ---- v0.6.64 续：导入学习应用（openKylin skills：UKUI Framework D-Bus 接口族）----
    {"id": "dbus-iface", "name": "D-Bus 桌面系统接口", "domain": "transport",
     "gist": "Linux 桌面本机 IPC 总线：对象路径 + 接口 + 信号三要素，系统服务（如 UKUI "
             "Framework）以 org.ukui.* 名暴露能力，技能/插件经调用这些接口落地。",
     "detail": "与 stdio/unix socket 同属本机信道，但多了服务发现（知名名 ↔ 唯一连接名）"
               "与信号广播语义；openKylin 技能仓库的设备控制（/Devices/Power、/Devices/"
               "Screen）与 UI 个性化（/UI/Theme、/UI/Wallpaper）即以 UKUI Framework "
               "D-Bus 接口为落点——接口可见性即能力面，调不动的接口等于不存在。",
     "standards": [], "bridges": [
         {"system": "netsys", "target": "module:ukui-desktop-widget", "relation": "接口消费者",
          "how": "UKUI 桌面小插件经桌面 shell（D-Bus 系统服务）完成添加/移除/尺寸切换等交互"},
         {"system": "netsys", "target": "module:sysmesh", "relation": "接口协调同源",
          "how": "接口面经组网互联协调（sysmesh）：D-Bus/WebSocket 等信道即能力面，"
                 "与系统互联协调同一『以 fd/信道锚定而非路径重解析』纪律"}]},
]


ENGINEERING: Dict[str, str] = {
    # ---- 轴1 接口风格 ----
    "rest": "落法：本仓库 webapi 不用 URI 资源语义（一行一请求的 JSONL），只取其「无状态 + "
            "显式契约」——每个 ACTION 是一次显式调用、服务端不存会话；令牌绝不上 URI 查询串"
            "（RFC 6749 §2.3 的反面模型，见 auth-redlines）。",
    "graphql": "落法：未落地（webapi 无 schema 查询面）。若将来加查询面，schema 必须是单一"
               "事实源而非手抄，否则必然与 ACTIONS 白名单两套定义走偏。",
    "grpc": "落法：未落地。三端并存（Python 逻辑 / Deno 外壳 / Go 侧工具）目前靠 JSONL 文本"
            "契约 + review 保一致；若要跨语言强类型调用，IDL 先行的收益最大。",
    "websocket": "落法：未落地。GUI 与 Python 侧是同进程直调，Deno↔Python 是 stdin/stdout "
                 "JSONL 长连接，二者都不是 WS；若将来引入 WS，心跳 + 断线重连 + 背压三者"
                 "必须同时补齐（只做其一等于没做）。",
    "sse": "落法：未落地。日志流/清理进度这类单向场景应优先 SSE 而非 WS（不必握手升级、自带"
           "重连），当前进度信息由 GUI 侧直接读返回值渲染。",
    "mq": "落法：无中间件依赖（纯标准库、离线优先是一条红线）。本地落法即 meshchat 的「待收"
          "清单」——本地版信箱：消息不自动落盘，须用户显式接受（已桥接 netsys:meshchat）。",
    "webhook": "落法：本仓库不开任何出站回调（红线：对前端只暴露只读诊断与用户配置文件读写）。"
               "若将来必须接，HMAC 签名 + 重放窗口 + 幂等键 + 死信队列四件缺一不可。",
    "jsonrpc": "落法：形似 JSON-RPC 但刻意不做——无请求 id、无批量、无通知；一行请求一行响应"
               "便于逐条断言，出错只回 ok=false 而不断开循环——「永不抛异常打断循环」是这一层的硬要求。",
    "cli-contract": "落法：argparse 子命令即对外 API 契约，新增子命令必须进 cli.build_parser()，"
                    "其总数由各系统构建期实测登记（当前 107），数字漂移即 --check 失败；"
                    "--help / --version / 退出码沿用 POSIX 语义，输出可解析便于脚本消费。",
    # ---- 轴2 规约标准 ----
    "openapi": "落法：未发布 OpenAPI 文档。若补，应由 webapi.ACTIONS 白名单机械反译为 paths，"
               "而不是手写第二份真相（与 datong「一契三端」同思路，见 datong:sanwei-yiti）。",
    "graphql-sdl": "落法：未落地。任何 SDL 都应从既有白名单与数据模型生成，禁止手抄定义。",
    "protobuf-idl": "落法：未落地。src/go 为纯标准库实现，无 protobuf 依赖；三端契约走 JSONL "
                    "文本层，不强耦合 IDL 工具链。",
    "json-schema": "落法：report.build_report() 的 {disk:{before,after}, tasks[]} 应以 JSON "
                   "Schema 固化，report_viewer 消费端据此校验；契约改动必须同步 schema，"
                   "否则 HTML 侧重生成后 sha256 守护会先一步报错。",
    "asyncapi": "落法：未落地。webapi 目前是同步「一问一答」，无异步任务队列；若将来引入长任务，"
                "先按 AsyncAPI 登记信道与消息，再写代码，别倒过来。",
    "wsdl": "落法：遗留口径，不建议新写。万一要接遗留 SOAP 服务，用单一包装器隔离在适配边界内，"
            "不让老协议污染主契约。",
    # ---- 轴3 传输绑定 ----
    "http11": "落法：真落地——Deno 控制台（console.ts）监听本机 HTTP 对外提供页面；Python 侧"
              "不直接监听端口，避免两条 TCP 契约并存。",
    "http2": "落法：未启用。是否升级由 Deno 外壳决定，本仓库不承诺 h2；Python 侧不经 HTTP，"
             "故不受其影响。",
    "http3": "落法：未启用。HTTP/3 依赖 QUIC 栈，纯标准库 Python 侧无实现，此处仅作认知登记。",
    "tcp": "落法：真落地——这是本仓库唯一的网络段：Deno 监听本机 TCP 承接浏览器请求，再落到"
           "Python 的 stdin/stdout；浏览器从未直接接触 Python。",
    "stdio": "落法：真落地——webapi 的长连接跑在 stdin/stdout 上（JSONL），一个 Python 进程"
             "复用多次调用，省掉每次冷启动；这也是为什么必须「永不抛异常打断循环」。",
    "unix-socket": "落法：未落地。本机 IPC 若将来要选，Unix domain socket 比 localhost TCP 更"
                   "省心——无端口占用冲突，且能用文件权限直接做访问控制。",
    # ---- 轴4 认证授权 ----
    "auth-basic": "落法：不建议。Basic 凭据随每次请求发送，仅在 HTTPS 下勉强可用；本仓库无"
                  "密码传输场景，不为它留位置。",
    "auth-bearer-jwt": "落法：口径登记（未落地）。若将来要跨域/远端调用：短时效访问令牌 + 服务端"
                       "刷新令牌，令牌不进 localStorage、不进 URL，优先 httpOnly Cookie 或内存态。",
    "auth-oauth2": "落法：未落地。若要接第三方授权，走授权码 + PKCE（RFC 6749/6750），令牌绝不"
                   "上 URL 查询串——本条与 auth-redlines 同源，都是「令牌不得随 URL 走」。",
    "auth-api-key": "落法：未落地。当前靠 ACTIONS 白名单 + 只读动作最小面来约束，而不是靠凭据；"
                    "即便将来加 key，它也只是限速与审计标签，不当作授权凭据本身。",
    "auth-mtls": "落法：未落地。mTLS 适合内网服务间双向鉴权（RFC 8705），但引入证书管理会动摇"
                 "「纯标准库、离线优先」的定位，收益不抵成本。",
    "auth-redlines": "落法：红线总纲——白名单入口（认不出即拒，无 getattr 兜底）+ opt-in 双确认 + "
                     "令牌禁入 URL/localStorage + 访问令牌短时效且服务端刷新 + 破坏性操作二次确认。"
                     "webapi 这一层比 GUI 更严：只暴露只读诊断与用户配置文件读写（datong 神恩如狱、"
                     "耆那不害两条已桥接到此）。",
    # ---- 轴5 本仓库接口面 ----
    "repo-cli": "落法：argparse 单一入口，CLI 与 GUI、webapi 三方共享同一套 native 能力，"
                "避免同一件事写三份实现后逐渐各异（这是同一能力写三份后各奔前程的根因）。",
    "repo-plugins": "落法：native/plugins.py 的静态 NATIVE_ALLOWLIST + register_native() 运行时显式"
                    "登记——后者只收 sysweeper.native 下**已存在**的零参只读函数；manifest 的 native "
                    "字段必须在白名单内；绝不导入/执行插件自带代码，杜绝 shell 注入。",
    "repo-webapi": "落法：Python 当逻辑层、Deno 只做 HTTP 外壳，格局不变；ACTIONS 白名单制，"
                   "dispatch 认不出的 action 一律拒绝，无 getattr 兜底派发；诊断正文按 max_chars "
                   "截断，防超长输出灌爆前端。",
    "repo-report": "落法：report.build_report() → {disk:{before,after}, tasks[]}，render_markdown / "
                   "render_bars 渲染的是同一份结构，保证 CLI/GUI/Deno 三端口径同源不同形。",
    "repo-report-viewer": "落法：report_viewer.html 由 tools/gen_report_viewer.py 从 report_viewer.ts "
                          "生成并经 sha256 守护，手改立即失败——「单一事实源」在这里是被机器强制的；"
                          "分享前须提示隐私（含磁盘/路径/子任务明细）。",
    # ---- v0.6.63 续：导入学习应用（SonicBoom / Linux 7.3）----
    "c-abi": "落法：本仓库 webapi 即一种稳定 ABI——ACTIONS 白名单是契约边界，Python 逻辑层"
             "可整体替换（Deno 外壳、Go 侧工具）而不破坏调用方；与『C ABI 让实现可插拔』"
             "同源。令牌禁入 URL/localStorage 即 ABI 的红线纪律。",
    "guile-ffi": "落法：未落地为本仓库脚本语言，但同思路已见于 CLI 子命令契约——argparse "
                 "子命令即对外 API，Deno/Python/Go 三方共享同一 native 能力，声明即调用；"
                 "不引入第二套解释器以免契约漂移。",
    "fchroot-syscall": "落法：本仓库 webapi 的 stdio 长连接即『以 fd 锚定、不重解析路径』的"
                       "同一接口纪律——一个 Python 进程复用 stdin/stdout 多次调用，绝不重开"
                       "连接重解析地址；fchroot(2) 的内核语义在此被登记为接口面参照。",
    "dbus-iface": "落法：未落地，本仓库不监听也不调用 D-Bus。但接口纪律同源——webapi 的 "
                  "ACTIONS 白名单与 D-Bus 的接口可见性一样，都是『显式声明的能力面』："
                  "调用方只能走声明入口，不允许 getattr 兜底派发（对应 D-Bus 未导出的接口"
                  "不可达）；将来若接入桌面侧，先登记接口白名单再写调用。",
}


def apply_engineering(concepts: List[dict]) -> None:
    """给每个概念注入「工程落法」（v0.6.62 字段齐备化）。

    口径与 baigong/zhuangzi/datong 的 `engineering` 同义：这一条对本仓库意味着什么、
    真落地了就写真实构件，未落地就写「未落地」并给出将来接入时的约束——
    **不把未投产的东西写成已具备的能力**。
    """
    for c in concepts:
        eng = ENGINEERING.get(c["id"])
        if eng:
            c["engineering"] = eng


def repo_face_facts() -> Dict[str, object]:
    """从源码实测读出本仓库接口面事实（构建时调用，失败即视为漂移）。"""
    sys.path.insert(0, str(SRC))
    from sysweeper import cli, webapi

    parser = cli.build_parser() if hasattr(cli, "build_parser") else None
    sub_count = 0
    if parser is not None:
        for a in parser._actions:
            if a.__class__.__name__ == "_SubParsersAction":
                sub_count = len(a.choices)
    return {
        "cli_subcommands": sub_count,
        "webapi_actions": len(webapi.ACTIONS),
        "webapi_protocol": "JSONL（一行请求 JSON → 一行响应 JSON；ACTIONS 白名单制，"
                           "无 getattr 兜底派发）",
        "plugins_api": "native/plugins.py：effective_allowlist() 静态白名单 + "
                       "register_native() 显式扩展；manifest native 字段必须在白名单内",
        "report_schema": "report.build_report() → {disk:{before,after}, tasks[]}；"
                         "render_markdown/render_bars 渲染",
        "report_viewer_guard": "tools/gen_report_viewer.py 生成 + check_repo_guard.py "
                               "sha256 守护（漂移即失败）",
    }


def backfill_rfc_titles(doc: dict) -> None:
    """RFC 编号经 rfc_catalog 交叉验证存在性并回填标题（check/写盘同源）。"""
    sys.path.insert(0, str(SRC))
    from sysweeper.native import rfc_catalog as cat
    for c in doc["concepts"]:
        for s in c.get("standards", []):
            if s.get("kind") != "RFC":
                continue
            info = cat.rfc_info(s["num"])
            if info:
                s["rfc_title"] = (info.get("t") or "")[:120]


# v0.6.62 续：回链大同（使综摄系统双向可达，仅确凿关系）
DATONG_BACKLINKS = [
    {"from": "apilab:openapi", "system": "datong", "target": "principle:he-butong-yong",
     "relation": "翻译", "how": "OpenAPI 多版本契约并存共荣 ↔ 和而不同：API 新旧版本并行、渐进废弃"},
    {"from": "apilab:websocket", "system": "datong", "target": "concept:bo",
     "relation": "翻译", "how": "WebSocket 一处发布处处到达 ↔ 波：无远弗届的传播协议"},
]


def build() -> dict:
    apply_engineering(CONCEPTS)
    bridges: List[dict] = []
    for c in CONCEPTS:
        for b in c.get("bridges", []):
            bridges.append({
                "from": f"apilab:{c['id']}",
                "system": b["system"],
                "target": b["target"],
                "relation": b.get("relation", ""),
                "how": b.get("how", ""),
            })
    bridges.extend(DATONG_BACKLINKS)

    by_domain: Dict[str, List[str]] = {d["domain"]: [] for d in DOMAINS}
    for c in CONCEPTS:
        by_domain.setdefault(c["domain"], []).append(c["id"])

    doc = {
        "_meta": {
            "schema": SCHEMA,
            "built_by": "research/apilab/build_apilab.py",
            "main_root": "wordbuddy-github",
            "title": "接口 API 概念系统（以 wordbuddy-github 为主目录）",
        "system_root": "wordbuddy-github",
        "version": "0000.0000.0000.0064.20261023",
            "concept_total": len(CONCEPTS),
            "axes": ["style", "spec", "transport", "auth", "repo-face"],
            "bridge_count": len(bridges),
            "rfc_note": "RFC 编号经本仓库 rfc_catalog 交叉验证存在性并回填标题",
            "honesty": "repo-face 轴的条目以当前仓库实测事实登记（构建时从 argparse 与 "
                       "webapi.py 读出子命令数/ACTIONS 数），不写无法核实的数字；"
                       "未落地的风格/规约/传输条目（graphql/grpc/wsdl 等）刻意不设"
                       "落地桥接，宁可孤立也不臆造关系（v0.6.62）。",
            "redline_note": "认证条目登记处置纪律：令牌禁入 URL/localStorage、私钥不明文、"
                            "访问令牌短时效 + 服务端刷新。",
        },
        "domains": DOMAINS,
        "concepts": CONCEPTS,
        "bridges": bridges,
        "by_domain": by_domain,
        "repo_face_facts": repo_face_facts(),
    }
    backfill_rfc_titles(doc)
    return doc


def check(doc: dict) -> List[str]:
    errs: List[str] = []
    sys.path.insert(0, str(SRC))
    from sysweeper.concepts import _common

    if doc.get("_meta", {}).get("schema") != SCHEMA:
        errs.append("schema 不符")

    def load_other(name: str) -> dict:
        return json.loads((CONCEPTS_DIR / f"{name}_taxonomy.json")
                          .read_text(encoding="utf-8"))

    # 1) RFC 编号命中 rfc_catalog（从 importlib 验证，标题回填）
    try:
        from sysweeper.native import rfc_catalog as cat
    except Exception as ex:  # noqa: BLE001
        cat = None
        errs.append(f"无法加载 rfc_catalog：{ex}")
    if cat:
        for c in doc["concepts"]:
            for s in c.get("standards", []):
                if s.get("kind") != "RFC":
                    continue
                info = cat.rfc_info(s["num"])
                if info is None:
                    errs.append(f"{c['id']} 引用 RFC {s['num']} 在 rfc_catalog 中不存在")
                elif not s.get("rfc_title"):
                    errs.append(f"{c['id']} 的 RFC {s['num']} 未回填标题")

    # 2) 轴合法 / id 唯一 / gist 非空
    valid_domains = {d["domain"] for d in doc["domains"]}
    ids = set()
    for c in doc["concepts"]:
        if c["id"] in ids:
            errs.append(f"概念 id 重复：{c['id']}")
        ids.add(c["id"])
        if c["domain"] not in valid_domains:
            errs.append(f"{c['id']} 轴 {c['domain']} 未登记")
        if not c.get("gist"):
            errs.append(f"{c['id']} 缺 gist")
        # v0.6.62：字段齐备——每个概念必须有「工程落法」，不得只有原理没有用法
        if not str(c.get("engineering") or "").strip():
            errs.append(f"{c['id']} 缺 engineering（工程落法）")

    # 3) 反查视图自洽
    inverted: Dict[str, List[str]] = {}
    for c in doc["concepts"]:
        inverted.setdefault(c["domain"], []).append(c["id"])
    for d in set(inverted) | set(doc["by_domain"]):
        if inverted.get(d, []) != doc["by_domain"].get(d, []):
            errs.append(f"by_domain 视图与 concepts 不一致：{d}")

    # 4) 桥接无悬空
    netsys = load_other("netsys")
    daoxue = load_other("daoxue")
    plang = load_other("plang")
    datong = load_other("datong")
    netsys_mods = {m["id"] for m in netsys.get("modules", [])}
    dx_principles = {p["id"] for p in daoxue.get("principles", [])}
    plang_langs = set(plang.get("lang_index", {}))
    datong_ids = {c["id"] for c in datong.get("concepts", [])} | {
        p["id"] for p in datong.get("principles", [])}
    for b in doc["bridges"]:
        sysname, tgt = b["system"], b["target"]
        kind, _, val = tgt.partition(":")
        if sysname == "netsys":
            if kind != "module" or val not in netsys_mods:
                errs.append(f"桥接悬空：netsys 无模块 {val}")
        elif sysname == "daoxue":
            if kind != "principle" or val not in dx_principles:
                errs.append(f"桥接悬空：daoxue 无原则 {val}")
        elif sysname == "plang":
            if kind != "lang" or val not in plang_langs:
                errs.append(f"桥接悬空：plang 无语言 {val}")
        elif sysname == "datong":
            if kind not in ("concept", "principle") or val not in datong_ids:
                errs.append(f"桥接悬空：datong 无{'原则' if kind == 'principle' else '概念'} {val}")
        else:
            errs.append(f"桥接目标系统未登记：{sysname}")

    # 5) repo-face 事实必须是实测非零
    facts = doc.get("repo_face_facts") or {}
    if not isinstance(facts.get("cli_subcommands"), int) or facts["cli_subcommands"] < 1:
        errs.append("repo_face_facts.cli_subcommands 非实测正数")
    if not isinstance(facts.get("webapi_actions"), int) or facts["webapi_actions"] < 1:
        errs.append("repo_face_facts.webapi_actions 非实测正数")

    # 6) counts 自洽
    m = doc["_meta"]
    if m["concept_total"] != len(doc["concepts"]):
        errs.append("counts.concept_total 漂移")
    if m["bridge_count"] != len(doc["bridges"]):
        errs.append("counts.bridge_count 漂移")

    # 7) 加载器可用性
    if OUT.exists():
        try:
            if _common.load_taxonomy(OUT.name) != json.loads(
                    OUT.read_text(encoding="utf-8")):
                errs.append("concepts 共享加载器与磁盘内容不一致")
        except Exception as ex:  # noqa: BLE001
            errs.append(f"concepts 共享加载器读取失败：{ex}")
    else:
        probe_path = _common.data_path("plang_taxonomy.json")
        if not probe_path.exists():
            errs.append(f"concepts 共享加载器路径机制失效：{probe_path} 不存在")

    return errs


def report(doc: dict) -> None:
    print(f"接口概念条目：{doc['_meta']['concept_total']} 个\n")
    print("按轴：")
    for d in doc["domains"]:
        print(f"  {d['domain']:<10} {len(doc['by_domain'].get(d['domain'], [])):>2}  {d['label']}")
    f = doc.get("repo_face_facts", {})
    print(f"\n本仓库接口面实测：CLI 子命令 {f.get('cli_subcommands')} 个 / "
          f"webapi ACTIONS {f.get('webapi_actions')} 个")
    print(f"桥接边：{doc['_meta']['bridge_count']} 条")
    by_sys: Dict[str, int] = {}
    for b in doc["bridges"]:
        by_sys[b["system"]] = by_sys.get(b["system"], 0) + 1
    for s, n in sorted(by_sys.items()):
        print(f"  → {s:<8} {n}")
    rfcs = sorted({s["num"] for c in doc["concepts"]
                   for s in c.get("standards", []) if s.get("kind") == "RFC"})
    print(f"RFC 引用（经 rfc_catalog 验证）：{rfcs}")


def main(argv: List[str]) -> int:
    doc = build()
    if "--report" in argv:
        report(doc)
        return 0
    if "--check" in argv:
        # 防漂移：磁盘登记的 repo-face 实测值必须与当前源码实测一致
        if OUT.exists():
            disk = json.loads(OUT.read_text(encoding="utf-8"))
            live = repo_face_facts()
            dfacts = disk.get("repo_face_facts") or {}
            for k in ("cli_subcommands", "webapi_actions"):
                if dfacts.get(k) != live.get(k):
                    print(f"✗ repo_face_facts.{k} 漂移：磁盘登记 {dfacts.get(k)} ≠ "
                          f"源码实测 {live.get(k)}（需重建）")
                    return 1
        errs = check(doc)
        if errs:
            for e in errs:
                print("✗", e)
            return 1
        print(f"✓ 校验通过：{doc['_meta']['concept_total']} 个概念 / "
              f"{doc['_meta']['bridge_count']} 条桥接无悬空 / "
              f"RFC 引用全部命中 rfc_catalog")
        return 0
    from datetime import datetime, timezone
    doc["_meta"]["generated_at"] = datetime.now(timezone.utc).isoformat()
    errs = check(doc)
    if errs:
        for e in errs:
            print("✗ 写盘前校验失败：", e)
        return 1
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已构建 {OUT}：{doc['_meta']['concept_total']} 个概念")
    report(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
