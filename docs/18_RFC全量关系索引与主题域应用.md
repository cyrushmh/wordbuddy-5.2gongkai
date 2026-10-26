# RFC 全量关系索引与主题域应用：从「目录」到「可对账的知识层」

> 任务组 #371–#375 ｜ 2026-10 ｜ 用户指令：**全面全量全索引的引入导入 RFC 以及应用**。
> 承 docs/14（v0.6.45 RFC 目录）+ docs/13（RFC 9846 TLS 1.3 规范留存）之后。本轮把 RFC 层从「七字段目录」升级为**带关系语义、带主题域、带应用对账**的三层结构。

---

## 一、数据层补全：v2 重采，关系字段回归

docs/14 首采（v1）时埋了一个静默 bug：无冒号关系段（`Obsoletes RFC8415`）被整段当作键名（`fields["Obsoletes RFC8415"]`），而取值用 `fields["Obsoletes"]` 永远落空——obs/oby/upd/udy 四个关系字段**全量丢失**，v1 数据层只有 also。

v2 重采修复（关键词整词前缀匹配，`Obsoleted by`/`Updated by` 双词词头单独判）：

| 字段 | 覆盖条数 | 说明 |
|---|---|---|
| obsoletes | 1,265 | 本 RFC 废弃了谁 |
| obsoleted_by | 1,384 | 谁废弃了本 RFC（沿链求现行版的关键） |
| updates | 1,293 | 本 RFC 更新了谁 |
| updated_by | 1,242 | 谁更新了本 RFC |
| also | 449 | STD/BCP/FYI 系列归属 |

- 重采结果与 v1 **逐字段回归零差异**（10,036 条，issued 9,848，Not Issued 188 如实保留）；
- 悬空指针 0：所有关系指向编号均在本索引内；
- 采集器与报告：`research/harvest/rfc_index_harvest.py`、`research/rfc/rfc_index_harvest_report.json`；
- 原始索引 SHA256 与拉取记录：`research/rfc/manifest.json`（harvest_history 保留 v1/v2 两条沿革，含 bug 说明）。

## 二、native 层：四类新 API（只读）

`sysweeper/native/rfc_catalog.py` 在 v1 基础上新增：

| API | 语义 | 诚实边界 |
|---|---|---|
| `rfc_relations(num)` | 关系视图，指向编号尽力解析标题/状态/日期 | 指向编号不在目录时只给编号 + `resolved: False`，不臆造元数据 |
| `rfc_current(num)` | 沿 obsoleted-by 链求末端 | status ∈ OK / NOT_IN_CATALOG / DANGLING_TARGET / CYCLE / TOO_DEEP，链分叉记 `other_successors` |
| `series_index()` / `series_members(s)` | 367 个 STD/BCP/FYI 系列 → 成员 | 系列名归一化（`STD 13`/`std13` → `STD13`） |
| `citation_audit()` | 任务引用三分 | 悬空 / 真过期引用 / 说明性提及（同文本共现现行编号者不算过期） |

**应用对账实效**：扫描 registry 全部任务的 standards 字段，48 个被引用 RFC 全部解析成功。审计当场发现 **2 个真实过期引用**并已修复：

| 任务 | 修复前 | 修复后 |
|---|---|---|
| `net_ipv6_privacy`（network.py） | RFC 4941（2007，DRAFT STANDARD） | **RFC 8981**（2021-02 现行版，standards/desc/actions/notes 四处同步） |
| `webnews_fetch`（webnews.py） | RFC 7231（2014） | **RFC 9110**（2022-06 INTERNET STANDARD） |

修复后复测：cited 48 / resolved 48 / **dangling 0 / obsolete_cited 0**；剩余 3 条（4941、7231、8446）是任务文本里「RFC 8981（……RFC 4941 的现行版……）」式**说明性提及**，审计如实单列，不算过期——这正是「只报告不改写」口径的意义。

另：`tls13_posture_audit` 曾把「废弃 RFC 8446」识别为过期引用，实为 RFC 9846 取代说明，同文本共现判定已将其归入说明性提及。

## 三、主题域索引：heuristic，但可审计（#373）

13 个主题域 × 89 条显式规则（`(domain, rule_id, regex)` 三元组，仅匹配标题）：

```
routing 1511 · ip-core 1231 · management 875 · realtime-media 780 · tls-pki 735
security 608 · data-formats 430 · http-web 401 · mail 392 · transport 370
dns 350 · iot-constrained 99 · time-sync 56
```

**覆盖 6,319 / 9,848（64.2%），未分类 3,529 条如实保留**——heuristic 不追求 100% 覆盖。一条 RFC 可归多域（DNS over IPv6 同归 dns 与 ip-core），domains 列表去重、rules 逐条留痕。

构建器 `research/rfc/build_rfc_topic_index.py` 的三条工程纪律：

1. **命中留痕**：每条 RFC 记录命中的 rule_id，复核可反查「为什么分到这个域」；
2. **`--check` 七项断言**：规则可编译 / id 唯一 / 域归属有效 / assignment 键存在且 issued / classified+unclassified==issued / 交叉引用有效 / **按规则重算与磁盘完全一致**（防手工篡改）；
3. **反篡改已实证**：测试与手工注入两类篡改（改 domains、插未发布键）均被 `--check` 精确抓获并列出差异条目。

规则迭代留痕：首版 82 条规则后按未分类扫描补漏（ppp 70 / ldap 65 / rsvp 46 / presence 37 / pcep 29 / lisp 29 / bfd 21 / whois-xmpp-arp-evpn-cdn-capwap-stir 等）至 89 条，并修掉两处误判（「IPv6 over Token Ring/FDDI」误入 6lowpan、「IPv6 Packets over」过宽）。抽样验证 50+ 标杆 RFC（1034/1035 DNS、8446/9846 TLS、9110 HTTP、4291 IPv6、4271 BGP、5321 SMTP、4251 SSH、5905 NTP……）落域全部符合预期。

## 四、CLI：rfc 组扩到 13 个子命令（v0.6.50）

```
rfc                        # 目录速览（含关系/主题域/官方WG三维计数）
rfc list / search / show / citing          # v0.6.45 原有
rfc relations <编号>                        # 关系视图（目录外指向如实标注未解析）
rfc current <编号>                          # 废止链 → 现行版（8415 -> 9915）
rfc series [名]                             # 367 个 STD/BCP/FYI 系列 / 某系列成员
rfc topics / topic <域名>                   # 主题域速览 / 成员列表（show 也带主题域归属）
rfc refs                                    # 任务侧引用全量核验（悬空/过期/说明三分）
rfc wgs                                    # 官方 WG/RG 索引速览（area + Top WG）
rfc wg <名>                                # 某 WG/RG 或 area（datatracker 代码）的成员列表
```

## 五、测试与回归

- `tests/test_rfc_catalog.py` 19 项：v1 五项 + v2 四项（关系视图/废止链/系列/引用三分）+ v3 五项（主题域统计闭合/排序/成员/留痕/`--check` 子进程集成）+ v4 五项（WG 统计闭合/排序/成员/留痕/`--check` 子进程集成）；
- 全量 pytest 回归通过（测试套件随仓库演进）；
- 版本 0.6.48 → 0.6.49（#371-#375）→ **0.6.50**（#376，WG 第二索引源；`__init__.py` / `pyproject.toml` / Go `const version` 三处由 `test_pkg_layer` 强制同步，README 与 CLI 文档串同步更新口径）。

## 六、口径与边界（诚实声明）

- RFC 索引为公开规范性文献目录，**只收录索引元数据，不复制 RFC 正文**（承 docs/14 边界）；
- 主题域分类是**本地启发式**，非 IETF 官方分类，meta.method 已声明；官方分组由 **WG 第二索引源**提供（见第七节），两层互补：WG 层给官方归属口径，heuristic 层兜底独立投稿/IAB/早期 Legacy RFC；
- WG 归属来自 RFC 提交时的 `draft-ietf-{wg}-*` 命名（rfc-index.xml）+ datatracker WG/area 名录标签；早期 RFC 无 draft 段，如实归 legacy/independent，不臆造 WG；
- 引用审计只报告不改写：是否把任务文本里的「RFC 4941 的现行版」简化为「RFC 8981」由维护者定夺，本轮保留说明性文本以维持可读性。

## 七、官方 WG/RG 第二索引源（v0.6.50, #376）

主题域 heuristic 层是「内容分类」，但 IETF 真正的官方分组是 **Working Group（工作组）/ Research Group（研究组）/ Area（领域）**。这一层用 rfc-editor 官方 `rfc-index.xml` 的 `draft` 段（`draft-ietf-{wg}-*` / `draft-irtf-{rg}-*` / `draft-iab-*`）+ IETF datatracker 的 WG/area 名录标签构建，作为第二索引源，**补充而非替换** heuristic 层。

**数据管线**：`research/rfc/build_rfc_wg_index.py`

```
rfc-index.xml (rfc-editor 官方) ──解析 draft 段──┐
ietf_wg_list.json (datatracker 名录: 1128 WG + 17 area) ──标签──┼─► rfc_wg_index.json
                                            (9,848 issued RFC 归属)            │
heuristic rfc_topic_index.json ──模态一致率对账──────────────────┘
```

**产出口径**：

- 571 个 WG/RG 覆盖 6,432 条已发布 RFC（覆盖 65.3%）；area 16 个；kind 分布 legacy 1467 / wg 6302 / independent 1808 / iab 141 / rg 130；
- `assignments`：每条 RFC → `{kind, w, a(area), s(stream), d(draft)}`，非 WG 归属（legacy/independent）如实留 `w=None`；
- `groups` / `areas`：WG→RFC 列表 + area 聚合，带 datatracker 中文标签与状态（active/concluded）；
- 与 heuristic 主题域层的**模态一致率 81.8%**（共同分类 3,908 / 4,778）——两层互证：WG 给官方归口，heuristic 兜独立投稿。

**构建纪律（与主题域同款）**：`--check` 对账断言（名单可加载 / area 映射有效 / 归属键存在且 issued / 覆盖闭合 / 模态一致率∈(0,1)）；`--report` 域分布 + Top WG。`rfc_wg_index.json` 与 `rfc_topic_index.json` 同为仓库内派生数据，由 `research/rfc/*.py` 可复现重建。

**native 层**：v4 四个只读函数 `wg_stats()` / `wgs()` / `wg_members()` / `wg_of()`；CLI `rfc wgs` / `rfc wg <名>` 接线（area 名用 datatracker 代码：`sec`/`rtg`/`int`/`app`…）。标杆核验：RFC 8446→tls(sec)、RFC 7230→httpbis、RFC 4281→独立投稿（honest 空归属）、RFC 0001→legacy。

## 八、GUI RFC 知识库面板（v0.6.52, #377）

CLI 已能浏览主题域与第二索引源，但 GUI 此前没有对应面板。本轮在 `gui.py` 补一个
**只读「RFC 知识库」面板**（`SysweeperGUI.show_rfc`），与 CLI `rfc topics / topic / wgs / wg`
口径一致，纯展示、不改动任何数据。底部按钮栏新增「RFC 知识库」入口。

**三页结构**（ttk.Notebook）：

- **主题域**（heuristic 层）：13 个域按成员数降序列表，点选即在右侧文本框列出成员 RFC（标题 + 编号，最多 200 条）；
- **工作组(WG)**（官方第二索引源）：先列 IETF area（按 RFC 数降序），再列 Top WG，点选列出成员 RFC；
- **单号查询**：输入编号回车或点「查询」，并陈两层归属——`topic_of()` 给 heuristic 主题域 + 命中规则，`wg_of()` 给官方 WG 名称 / area / stream / 起草草案；示例按钮直接填 8446。

**接线纪律**：面板只读调用 `native.rfc_catalog` 的 `topics()` / `topic_members()` / `wgs()` / `wg_members()` / `topic_of()` / `wg_of()` / `rfc_info()`，与 CLI 同一数据层，不引入第二套索引逻辑；无图形环境（SSH/容器/CI）时 `gui.py` 整体优雅降级，面板不参与无头执行。

**测试**：`tests/test_gui_rfc.py` 用最小 tkinter mock（`_tk()` 注入假 Toplevel/Notebook/Listbox/ScrolledText）在无 DISPLAY 环境真实跑 `show_rfc` 三页逻辑——断言窗口标题含「RFC 知识库」、主题域页填充并点选列出成员、WG 页点选列出成员、单号查询 8446 同时给出「Transport Layer Security」官方归属与「tls-pki」主题域归属。4 项；与 `test_rfc_catalog.py` 的数据层测试互补。
