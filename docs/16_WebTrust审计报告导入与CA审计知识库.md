# GoDaddy WebTrust for CAs 2026 审计报告导入（归档 + 知识库 + CLI 跨库反查）

> 任务组 #361–#365 ｜ 2026-10 ｜ 用户指令：**投递《GoDaddy - 2026 WebTrust for CAs - Report.pdf》并继续被中断的收尾链**。
> 承 docs/14（RFC 全量目录）、docs/15（修真图谱）之后，本文记录一份**第三方鉴证报告**进入仓库的完整链路：归档 → 事实底稿 → 可复现构建 → 三道消费（CLI/测试/跨库反查）。

---

## 一、做了什么

用户投递的 PDF 是 Schellman & Company, LLC 对 **Starfield Technologies, LLC（GoDaddy 子公司）** CA 运营的 WebTrust 鉴证报告（覆盖期 2025-07-01 至 2026-06-30，报告日 2026-07-27，准则 WebTrust P&C for CAs **v2.2.2**，结论**无保留意见**）。处理完全沿用前两轮的知识库范式：

```
research/caaudit/manifest.json                       # 归档清单（SHA256/页数/加密属性/许可边界）
research/caaudit/GoDaddy - 2026 WebTrust for CAs - Report.pdf   # 原件副本（281,366 字节 / 17 页）
research/caaudit/webtrust_report_facts.json          # 事实底稿（人工逐行复核 PDF 提取文本）
research/caaudit/build_ca_audit_standards.py         # 唯一构建脚本（join + 断言）
   ↓ 交叉 join
sysweeper/data/rfc_standards.json                    # RFC 5280 条目标题（rfc05280）
   ↓
sysweeper/data/ca_audit_standards.json               # CA 审计知识库（35 CA / 12 地点 / 4 事项）
   ↓
sysweeper/native/ca_audit.py                         # 只读消费层（CA 检索 / 事项 / 跨库反查）
sysweeper/cli.py cmd_caudit                          # CLI 十个子命令
```

### 1.1 归档与核验

| 项 | 值 |
|---|---|
| SHA-256 | `1d1b1a691f9c4de2333037eb69e0b10aff74bc85502f86dab4bade9746446711`（原件与副本一致） |
| 页数 / 字节 | 17 页 / 281,366 字节 |
| 提取 | 本地 pdftotext 得 550 行全文（PDF 为 AES-256 加密但禁的只是"复制"权限，本地提取不受影响；manifest 如实记录） |
| 许可边界 | 报告为 Schellman 专有保密文件；仓库仅作**研究性存档 + 客观事实引用**（CA 清单/指纹/事项均为事实记录），不复制报告正文、不用于再分发；每条知识库条目带 PDF 页码可回溯 |

### 1.2 计数复核（诚实记录一次修正）

首遍速读摘要曾把根 CA 计为 13、签发 CA 计为 16、地点计为 11；**逐行复核 PDF 提取文本后修正为根 12 / 交叉签名 8 / 签发 15 / 地点 12（共 35 个 CA）**。该修正留痕在 `webtrust_report_facts.json` 的 `verification.counting_note`。构建脚本对计数做断言，底稿与生成物不符即 `sys.exit(1)`。

## 二、知识库模型（35 CA / 4 事项 / 12 地点）

| 分组 | 数量 | 内容 |
|---|---|---|
| 根 CA | 12 | Go Daddy Class 2、Go Daddy Root CA - G2、Starfield Class 2、Starfield Root G2/G5/G6、Starfield Services Root、GoDaddy Root G5/G6、GoDaddy/Starfield TLS Root CA – R1、GoDaddy Verified Mark Root CA - VMCR1（全带 SHA-256 指纹） |
| 交叉签名 CA | 8 | Class 2 → G2/PM（含 Starfield Services 两枚）、G2 → TLS R1 |
| 签发 CA | 15 | Secure CA（DV/OV/EV）、Secure Code Signing、TLS Intermediate DV/EV/OV – R1v1、VMC Intermediate |
| 地点 | 12 | Tempe/Phoenix/Ashburn/Scottsdale 5 处（含物理环境测试范围标记）+ MPIC Servers 6 个云区域（新加坡/孟买/爱尔兰/巴黎/俄勒冈/弗吉尼亚） |

**4 项 Mozilla Bugzilla 事项及标准条款映射**（管理声明表 + 正文"Other Matters"）：

| # | Bug | 违反条款 | 状态（报告期末） | Schellman 核查结论 |
|---|---|---|---|---|
| 1 | 2004845 AIA 以 PEM 提供签发者证书 | RFC 5280 §4.2.2.1 + BR §7.1.2.10.3 | Closed（2026-02-11） | 已充分解决根因 |
| 2 | 2002402 R1 中间件 CRL URL 未登 CCADB | CCADB policy §6.2 | Closed（2026-01-13） | 已充分解决根因 |
| 3 | 2007216 CCADB CRL 披露与叶证书不符 | CCADB policy v2.0 | **Open（未关闭）** | 若正确实施并有效运行可解决根因（**报告期末尚在实施**，如实录入不粉饰） |
| 4 | 2007217 分区 CRL 缺 Issuing Distribution Point 扩展 | BR §7.2.2.1 | Closed（2026-04-17） | 已充分解决根因 |

另录 1 项附事项：CP/CPS 披露的某些 CA 未入公开仓库（WebTrust v2.2.2 Control 6.5），2025-08 补入；这些根受约束且从未运营、未签发，意见未修改。

**排除项（审计未覆盖，如实录入）**：无 CA 密钥托管、无订阅者密钥生成/存储/恢复、无 IC 卡生命周期、无证书暂停服务。控制域 7 组（披露/管理/环境 10 项/CA 密钥 10 项/订阅者密钥 1 项/证书生命周期 7 项/从属 CA 1 项）与 CP/CPS 六版谱系（v5.02→v5.06 + Mark CA v1.0）全部入库。

## 三、引擎侧：CLI 与只读消费层

```
sysweeper caudit                          # 速览：标的/审计师/意见/规模/事项一览
sysweeper caudit list [--kind root|cross|issuing]   # 按种类列 CA（指纹 + 出处页码）
sysweeper caudit search <词>              # 名称/指纹前缀检索
sysweeper caudit show <名称>              # 单 CA：id/种类/指纹/上级根/出处
sysweeper caudit children <根>            # 某根下的交叉/签发 CA（如 Starfield G2 → 4 个）
sysweeper caudit matters [--bug 编号]     # 事项详情：条款映射/整改/审计师核查结论/出处
sysweeper caudit locations                # 12 地点（含物理测试范围）
sysweeper caudit std [rfc <编号>]         # 标准引用清单；rfc 5280 跨库反查
sysweeper caudit cpcps / domains          # CP/CPS 谱系 / 控制域 + 排除项
```

CA 解析入口：**精确 id > 名称精确 > 名称前缀（重名取最短 id，防 G2/G5/G6 误配）> 指纹前缀（≥8 位）**；查无返回 None 并诚实提示，不臆造。

**跨库反查**（本轮新增的连接）：`caudit std rfc 5280` 经由 `rfc_catalog.rfc_info(5280)` 查得该 RFC 的标题/状态/日期/作者/DOI——与 RFC 轮（docs/14）的目录数据交叉验证，知识库里 RFC 5280 标题与 RFC 目录**逐字一致**（测试断言）。

## 四、验证（能测必测，不能测诚实声明）

| 层 | 验证 | 结果 |
|---|---|---|
| 归档 | 原件 vs 副本 SHA-256 一致；页数/字节如实记录 | ✅ |
| 事实底稿 | 35 CA / 12 地点 / 4 事项计数断言；指纹 64-hex 且全库唯一 | ✅ |
| 构建脚本 | `--check` 模式：悬空 root 指针 = 0（曾真实抓住 cross 表 "Certification" vs root 表 "Certificate" 行文差异，以显式 `root_alias` 消歧而非模糊匹配） | ✅ |
| 只读消费层 | pytest 8 项：完整性/解析入口（en dash 名称、指纹前缀、前缀防误配）/children/事项映射/RFC 反查/CLI 冒烟 | ✅ 全绿 |
| 全量回归 | `pytest -q` 全仓 | ✅ 1080 passed / 3 skipped / 0 failed |

**未验证（诚实声明）**：
- 报告为 Schellman 专有保密文件，本仓库不复制其正文文本；知识库收录的是客观事实（CA 清单/指纹/日期/状态），事实性由"引文即出处（页码）"保证，未对审计结论做独立复核（也无从复核——那是鉴证业务本身）。
- 事项 3（#2007216）在报告期末仍 Open，其整改有效性未经 Schellman 确认——如实录入为 `pending_implementation`，不粉饰为"已解决"。
- Python 侧 CLI 冒烟在沙箱可复现；Go 侧本轮仅同步版本号（与 xiuzhen 轮一致），未加 Go 子命令。

## 五、产物清单

| 文件 | 说明 |
|---|---|
| `research/caaudit/manifest.json` | 归档清单（SHA256/页数/加密属性/许可边界/结构） |
| `research/caaudit/GoDaddy - 2026 WebTrust for CAs - Report.pdf` | 原件副本 |
| `research/caaudit/webtrust_report_facts.json` | 事实底稿（唯一数据源，含计数复核留痕） |
| `research/caaudit/build_ca_audit_standards.py` | 构建脚本（join RFC 标题 + 悬空/指纹/计数断言，`--check` 模式） |
| `system-optimizer/.../data/ca_audit_standards.json` | CA 审计知识库 |
| `system-optimizer/.../native/ca_audit.py` | 只读消费层（含 RFC 跨库反查） |
| `system-optimizer/.../cli.py` | `cmd_caudit` + `sp_caudit`（v0.6.47） |
| `system-optimizer/tests/test_ca_audit.py` | pytest 8 项 |
| `system-optimizer/README.md` | 数据树 + 命令表新增 `caudit` |

版本：Python `__version__` / pyproject / Go const 三处同步 **0.6.46 → 0.6.47**。
