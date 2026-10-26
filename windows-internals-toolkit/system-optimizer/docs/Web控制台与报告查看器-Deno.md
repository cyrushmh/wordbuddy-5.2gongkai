# Web 控制台与报告查看器（Deno · v0.6.26）

> 架构：**Python 当逻辑层，Deno 只做 HTTP 外壳**。
> 诊断、参数、子系统、导入逻辑全部复用 GUI/CLI 同款 Python 实现，前端只渲染，
> 不存在第二套实现。本工具的核心价值是**读本机**（sysfs / 注册表 / 硬件 / 已装软件），
> 所以真操作必须在本机；远端只做「报告查看」。

> ⚠️ **Deno Deploy 退场提醒（2026-10-09 起）**：Deno 团队整体加入 Cloudflare，官方已明确
> **Deno Deploy 约 6 个月后（≈2027-04）停止服务**，Deno runtime 本身再获约 1 年支持。
> 因此下面「远端查看器」**首选不依赖任何平台的自托管静态页**，Deno Deploy 只作过渡期备选项。

## 一 · 本机 Web 控制台（Deno + Python）

### 启动

```bash
sysweeper web                 # 默认 http://127.0.0.1:8787，自动开浏览器
sysweeper web --port 9000 --no-open
```

等价的手动方式（想自己控制 deno 参数时）：

```bash
deno run --allow-net --allow-read --allow-run src/deno/console.ts --port 8787
```

- 未装 Deno 时 `sysweeper web` **不自动安装**，只给官方安装指引：
  `curl -fsSL https://deno.land/install.sh | sh`
- 权限刻意最小化：只申请 `--allow-net / --allow-read / --allow-run`，
  **不申请** `--allow-write` 与 `--allow-env`（Python 路径用 `-c` 引导注入 sys.path，
  不靠环境变量）。写配置一律走 Python 侧动作白名单。
- 只监听 `127.0.0.1`，外部机器访问不到。

### 页面功能（八个标签）

| 标签 | 能做什么 |
|---|---|
| 总览 | 宿主信息 + 全量只读总览 + 诊断状态计数（正常/提示/不适用/异常） |
| 参数与阈值 | 13 项参数可视化编辑；● 高亮已改动项；单项复位 / 全部复位；显示每项**生效点** |
| 子系统开关 | 51 项子系统逐一开关（勾选即生效），按层过滤，全开/全关 |
| 单子系统诊断 | 任选一个子系统跑只读诊断，按状态徽标呈现正文 |
| 导入 | 剪贴板 / 本地文件 / 图片二维码 / 摄像头 四来源读取；显式确认后才载入为参数 |
| 变更留痕 | 谁在什么时候把哪项从什么改成什么（只记键与值，绝不记导入全文） |
| 快照报告 | 生成只读诊断快照 JSON，可下载/复制，喂给报告查看器 |
| **档位与评分** | 量化评分四卡（总分 / 归一化熵 / Gini / 任务数）＋四档位与场景档命中数、详情、两档 Jaccard 对比、内核只读体检 |

## 二 · 统一 JSON 接口（`sysweeper webapi`）

控制台与报告查看器共用这一层；也可以直接拿它当后端自己写前端。

```bash
# 一次性调用（脚本/测试用）
sysweeper webapi --once '{"action":"ping"}' --pretty

# JSONL 长连接（一行请求一行响应，Deno 控制台就靠它）
sysweeper webapi   # 从 stdin 逐行读
```

### 动作清单（白名单制，之外一律拒绝）

| 动作 | 读写 | 说明 |
|---|---|---|
| `ping` / `manifest` | 只读 | 连通自检 / 全部动作清单 |
| `settings.list` / `settings.get` | 只读 | 参数清单（含当前值、已改动项）/ 查单项 |
| `settings.set` | 写配置 | 批量设置（`{"pairs":{"cmd.timeout":300}}`），值未变不留痕 |
| `settings.reset_one` / `settings.reset` | 写配置 | 单项 / 全部恢复默认 |
| `settings.history` / `settings.history.clear` | 只读 / 写配置 | 变更留痕读取 / 清空 |
| `subsystems.list` | 只读 | 51 项子系统与开关态 |
| `subsystems.set` / `.set_many` / `.all` | 写配置 | 单个 / 批量 / 全开全关 |
| `diagnose` | 只读 | 跑单个或多个子系统的只读诊断（`{"keys":["kernel"]}`） |
| `sysmap` / `sysmap.capabilities` | 只读 | 系统统筹总览正文 |
| `import.capabilities` / `import.read` | 只读 | 导入能力探测 / 按来源读取外部内容 |
| `import.load` | 写配置 | 把导入的设置 JSON 载入为参数（**显式调用才写**） |
| `profiles.list` | 只读 | 任务档位与场景档清单，及当前平台命中任务数 |
| `profiles.show` | 只读 | 单档位规则、任务清单（`limit` 限返回条数）与覆盖度评分文本 |
| `profiles.compare` | 只读 | 两档对比：Jaccard 重合度、共有项、`sample` 条独有 id 示例 |
| `score.overview` | 只读 | 量化评估：WSM 总分、四分项、Shannon 熵、Gini、平台分布、覆盖缺口 |
| `kmod.report` | 只读 | 内核 module / firmware / eBPF 只读体检（含 kernel.org 文档出处与禁用命令清单） |
| `report.build` | 只读 | 生成快照报告 JSON（`include` 选段，`max_chars` 控截断） |

### 快照报告的段

`report.build` 的 `include` 可选：`host / settings / history / subsystems / sysmap /
diagnose / score / kmod`。不传 `include` 时默认全给（含 `score` 与 `kmod`）。

其中两段是给**远端查看**准备的：

- `score` —— 不需要跑任何探测也能回答「这套优化覆盖得够不够全」：
  覆盖度总分（加权求和 S=Σwᵢx̂ᵢ）、归一化熵 H/log₂n、Gini 集中度、平台任务分布、覆盖缺口。
- `kmod` —— 内核层的只读事实：加载了哪些模块、`/sys/module` 全景、模块参数当前值、
  firmware 库统计、eBPF 能力、modprobe 黑名单、电源与温区。状态按「可读探针占比」判定
  （`N/M 项只读探针可读`），因为容器里必然有一部分接口被屏蔽。

### 协议示例

```json
→ {"action": "settings.set", "params": {"pairs": {"cmd.timeout": 300}}, "source": "web"}
← {"ok": true, "action": "settings.set", "readonly": false,
   "data": {"results": [{"key": "cmd.timeout", "ok": true, "value": 300}], "changed": ["cmd.timeout"]}}
```

## 三 · 远端报告查看器（手机查看 / 分享）

纯展示服务：无后端存储、无密钥、无数据库，**数据只留在浏览器里**。

### 方案 1（推荐）：单文件静态网页，零依赖、零 token

仓库里已生成 `report_viewer.html`——它就是查看器的全部前端，**一个文件、无外链、无后端、
双击即用**，渲染效果与 Deno Deploy 版本完全一致（它是从 `report_viewer.ts` 的 `page()`
直接抽出的静态等价物）。

- **本机**：浏览器直接打开 `report_viewer.html`（`file://` 即可）；
- **手机**：把文件传过去用浏览器打开（微信 / AirDrop / 邮件附件都行）；或走下面任一托管拿固定链接：
  - **GitHub Pages（免费、永久）**：仓库 `Settings → Pages → Source` 选 `personal-branch`、
    目录选 `/（root）`，保存后访问
    `https://<你的用户名>.github.io/windows-internals-toolkit/system-optimizer/report_viewer.html`；
  - 任意静态托管：Vercel / Cloudflare Pages / 对象存储静态站点，传这一个文件即可。
- 数据只在浏览器里：粘贴 / 拖入 JSON，或用 `#r=<base64url>` 链接携带；**永不回传任何服务器**。

> 这版**不需要 Deno、不需要 token、不受 Deno Deploy 退场影响**，是长期最稳的托管方式。

### 方案 2（过渡期可用）：Deno Deploy

只建议在「平台还在的几个月窗口」里临时用；**不要为它投入长期配置或长期 token**。

- **token 时长**：若一定要建 Personal Access Token，**选 1 年，不要选 forever**——
  这是能读写你 Deno 账号的令牌，平台本身都在变，长期不过期不划算；30/60/90 天又太短，
  到期重配会打断自动化。反正平台 ~6 个月后没了，1 年足够覆盖过渡期。
- 部署：`deno install -Arf jsr:@deno/deployctl` 后
  `deployctl deploy --project=sysweeper-report src/deno/report_viewer.ts`；
  或 dash 关联 GitHub（分支 `personal-branch`，入口 `src/deno/report_viewer.ts`）。

  > 入口路径以 **git 仓库根** 为准：远端 `wordbuddy-github` 的根目录直接就是 `src/`、`docs/`、
  > `report_viewer.html` 这些，**没有** `system-optimizer/` 这一级——所以入口写 `src/deno/report_viewer.ts`
  > 即可。写 `system-optimizer/src/deno/...` 会报「找不到文件」。
- 本地预览（本机跑，不受退场影响）：`deno run --allow-net src/deno/report_viewer.ts --port 8899`。

### 用法

1. 本机控制台「快照报告」页生成并复制 JSON（手机上想要的话，先在自己电脑上生成，
   或用 `sysweeper webapi --once '{"action":"report.build"}'` 导出成文件）；
2. 打开远端查看器，粘贴 / 拖入 JSON 文件 → 渲染；
3. **前后对比**：依次渲染两份报告，自动出「诊断状态计数 + 量化评分 + 参数变化」对照表；
   评分表只会给变化的行上色，没变的不动；
4. 渲染段落：报告信息、诊断状态计数、**量化评分**、**内核只读体检**、系统统筹总览、
   子系统开关态、逐项诊断（折叠）、参数与阈值、变更留痕；
5. 支持拖文件、示例数据（`载入示例`）、URL 携带（`/#r=<base64url>`，注意等于公开发布）。

## 四 · 红线（与全工具一致，这里更严）

- 接口层是**动作白名单制**：没有 getattr 动态派发，认不出的 action 一律拒绝；
  白名单里**绝不存在** `clean --apply` / 启停服务 / 写系统位置类动作。
- 诊断只跑 `native.subsystems` 在册的只读报告函数；导入内容**绝不自动执行**。
- 唯一允许的写是**用户自己的配置文件**（`~/.config/sysweeper/`），且逐项校验、留痕。
- 控制台只监听 127.0.0.1；单子系统故障只标「异常」，绝不带走整个服务。

## 五 · 测试

```bash
PYTHONPATH=src/python python -m pytest tests/test_webapi.py -q    # 接口层（白名单/派发/参数/子系统/报告/JSONL）
PYTHONPATH=src/python python -m pytest tests/test_metrics.py -q   # 数学评分引擎：25 项
PYTHONPATH=src/python python -m pytest tests/test_profiles.py -q  # 任务档位不变量：16 项
PYTHONPATH=src/python python -m pytest tests/test_kmod.py -q      # 内核只读层 + 源码级红线审计：24 项
~/.deno/bin/deno check src/deno/console.ts src/deno/report_viewer.ts
```

`tests/test_kmod.py` 里有三项是**源码级静态审计**，用 AST 扫描 `native/kmod.py`，
保证这一层将来无论怎么改都不会悄悄变成「可写」：不许出现写模式 `open`、
不许直接 `os.system` / `subprocess`、经 `common.run` 执行的每条命令串不许含写重定向
或装卸模块动作。新增代码破这三条，测试立刻红。

端到端已实测：curl 逐条验证全部动作（含并发 6 请求串行化不错位）、
Playwright 渲染八个标签页零报错、查看器渲染评分与内核段并出前后对比零报错。

## 六 · 移动端（uni-app）

除了本机 Web 控制台（Deno）与单文件静态报告查看器（HTML），还提供 **uni-app
跨平台前端**（`src/uni-app/`，Vue 3，一套代码覆盖 H5 / App / 微信小程序），
文档参照 [uni-app 官方文档](https://hx.dcloud.net.cn/)。它与控制台同源、同协议
（`POST {BASE_URL}/api`）、同只读承诺，只是把「浏览器里看」换成「手机上看」。

三个页面：总览（实时只读诊断）、报告（粘贴快照 JSON 渲染全部段落）、档位
（任务档位 + 量化评分 + 一键跑内核 / OpenJDK 只读体检）。

- 手机真机要访问：把 `src/uni-app/common/config.js` 的 `BASE_URL` 改成电脑局域网
  IP，并让控制台 `--host 0.0.0.0` 监听外部网卡。
- 可用范围：App / 小程序端实时模式正常；**H5 跨域受 CORS 限制**（控制台 `/api`
  未开 CORS），H5 请用「报告」页的粘贴 JSON 模式。
- `src/uni-app/README.md` 有完整运行与对接说明。
