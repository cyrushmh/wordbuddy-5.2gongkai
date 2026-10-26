# RFC 全量标准目录导入 sysweeper（数据层 + CLI 检索 + 任务引用核验）

> 任务组 #351–#356 ｜ 2026-10 ｜ 用户指令：**「尽量引入导入全部所有 RFC 标准，不能的可以忽略，全面完善推进整体」+ AskUserQuestion 三决策（数据层/App/CLI 全都要 ① 全量索引精简+CLI检索 ② 先 RFC 后图谱 ③）**。

---

## 一、做了什么

把 **IETF 官方 RFC INDEX 全量导入** sysweeper，让「每一条任务标准引用里的 RFC NNNN」都能回溯到官方索引条目：

```
research/rfc/rfc-index.txt            # 官方 RFC INDEX 原文（2,027,473 字节 / 42,904 行，sha256 见 manifest.json）
research/rfc/manifest.json            # 抓取出处与指纹（诚实标注一次拉取即全文）
research/harvest/rfc_index_harvest.py # 解析器（可复现：SRC= 可指向任意副本）
   ↓
windows-internals-toolkit/system-optimizer/src/python/sysweeper/data/rfc_standards.json
   # 顶层 dict，key=rfcNNNN（五位零填充），10,036 条
   ↓
native/rfc_catalog.py   # 只读消费层：rfc_info/search/by_status/latest/citing_tasks
cli.py cmd_rfc          # CLI：sysweeper rfc [list|search|show|citing]
tests/test_rfc_catalog.py + tests/test_rfc_cli.py  # 15 项断言
```

### 1.1 数据规模（官方 RFC INDEX，2026-10-16 版）

| 指标 | 值 |
|---|---|
| 索引条目总数 | **10,036** |
| 已发布（issued） | 9,848 |
| 编号保留未发布（Not Issued，如 RFC 14/26） | 188 |
| INTERNET STANDARD | 132 |
| BEST CURRENT PRACTICE（BCP） | 337 |
| PROPOSED STANDARD | 4,430 |
| HISTORIC | 353 |
| STD/BCP/FYI 子系列收录 | 367 条 |

单条字段（紧凑键）：`n` 编号 / `t` 标题 / `a` 作者 / `d` 日期 / `f` 格式 / `s` 状态 / `obs` 废弃 / `oby` 被废弃 / `upd` 更新 / `udy` 被更新 / `also` 子系列 / `doi` / `i` 是否已发布。Not Issued 条目如实保留为 `{"n": N, "i": false}`——**不臆造任何元数据**。

### 1.2 解析质量（诚实标注）

- 解析失败 **0** 条；单条标题/作者/日期句界切分对现代条目（RFC 800+）全部正确。
- 已知瑕疵已写入 `research/rfc/rfc_index_harvest_report.json`：1969–1971 年前后 **11 条老条目**标题与作者粘连（源头形态如此，如 RFC 16 原记录无标题），未手工篡改索引原文。
- 作者/日期分离回归校验：authors 带月份残留 **0** 条、issued 无日期 **0** 条。

## 二、CLI：`sysweeper rfc` 家族

```bash
python -m sysweeper rfc                    # 目录速览（纯文本，屏幕阅读器可朗读）
python -m sysweeper rfc list --status "INTERNET STANDARD" --limit 20
python -m sysweeper rfc search "TLS"       # 标题/作者检索
python -m sysweeper rfc show 9846          # 单条 + 引用它的本系统任务
python -m sysweeper rfc citing 9846        # 只列引用任务
```

`rfc show <编号>` 的输出含：标题 / 作者 / 日期 / 状态 / 子系列 / 废弃与被废弃 / 更新与被更新 / 格式 / DOI / **本系统引用它的任务清单**。未分配编号（如 10544）如实回答「不在官方 RFC INDEX 中」，Not Issued 编号（如 14）如实回答「编号保留未发布」。

## 三、任务侧引用核验（185 处全部可回溯）

对 `models.py` + 全部 `tasks/*.py` 里出现的 `RFC NNNN` 做了全量核验（对照官方索引）：

- **可核验 185 处、不可核验 0 处、误引 Not Issued 0 处**。
- 本轮修正 3 处：
  1. `dnshealth_report` 补引 **RFC 1035**（Domain names - implementation and specification；nameserver 语义与 A 查询确实被该任务覆盖）。
  2. `meshnet` 两处 + `models.py` KEYWORD_STANDARDS：原「WireGuard（RFC 牵引的点对点加密隧道）」**含混且暗示存在 WireGuard RFC**——经官方索引核实截至 2026-10 **不存在 WireGuard RFC**（易误记的 9585 实为 IMAP Response Code）。改为诚实表述：现行规范见 wireguard.com 论文，所用密码原语引 **RFC 7748（Curve25519）/ RFC 7693（BLAKE2s）/ RFC 8439（ChaCha20-Poly1305）/ RFC 5869（HKDF）**（四个编号均经官方索引核实）。
  3. `dnshealth` 的 EDNS(0)（6891）与 NXDOMAIN（8020）**不加**——任务只做 nameserver/A 查询/stub 诊断，加了就是无据引用；`browser_report` 的 HTTP 9110/9111/9112 同理不加（任务只做浏览器/引擎探测与 BCD 兼容参考）；`zerotier` VL1 为私有协议、IETF 无 RFC，**诚实跳过**。

## 四、全量回归与巡检

- `pytest tests/`：**1065 passed, 3 skipped**（含本轮新增 10 项：test_rfc_catalog 5 + test_rfc_cli 5）。
- `python3 scripts/audit_standards_eol.py`：69 个知识库，`rfc_standards.json`（10,036 项）已纳入巡检，结构校验通过、需复核 0。

## 五、复现方式

```bash
# 重新抓取（服务端一次返回全文；manifest.json 记录 sha256 以便校验）
curl -sS https://www.rfc-editor.org/rfc-index.txt -o research/rfc/rfc-index.txt
# 重新解析
python3 research/harvest/rfc_index_harvest.py
```

注意：脚本以绝对路径 `BASE` 定位仓库；`SRC` 环境变量可指向任意 rfc-index.txt 副本。RFC 索引为公开规范性文献目录（IETF），本文档与数据层**只收录元数据（标题/状态/DOI 等），不复制 RFC 正文**。
