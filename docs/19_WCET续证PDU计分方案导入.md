# WCET 续证 PDU 计分方案：从投递的 .xls 到可对账的规则知识层

> 归类：导入引入分析学习应用线（与 RFC / CA 审计 / MongoDB 同款 ingestion 范式）
> 版本：v0.6.51　任务：#380　命令：`sysweeper recert`

## 一、来源与边界（诚实声明）

用户投递两个 `recert*.zip`，各含一个 `.xls` 续证跟踪表：

- `Recertification PDU Spreadsheet (3 year cycle) FINAL.xls`（原作者 Dr. Mohamed Moustafa）
- `Recertification PDU spreadsheet 5 year (Dec2016).xls`

**这是 IEEE WCET（Wireless Communications Engineering Technologies，无线通信工程技术）认证的续证 PDU 跟踪工作簿**——不是加密文件、不是待破解物（与 iOS/MongoDB 那条「破解线」无关）。WCET 认证项目已于 **2019 年停办**，本知识库仅供继续教育 / PDU 跟踪方法论参考。

边界（与 docs/14/16/17 一致）：

- **只收录计分规则元数据，不复制表内个人隐私字段**（Contact Info 页的姓名 / WCET ID 等原件不入库，仅留规则知识）；
- 原件为个人使用模板，按用户版权边界处理；
- PDU 计算与认定以官方 WCET Candidate Handbook 为准，本库是规则知识层，可被查询与对账。

## 二、解析出的方案结构

**全局门槛（READ FIRST 页）**

| 项 | 值 |
|---|---|
| 最小计量 | 0.25 小时（15 分钟） |
| 三年周期下限 | ≥ 60 PDU |
| 五年周期下限 | ≥ 100 PDU |
| 活动分布 | ≥ 3 个自然年 |
| 技术知识领域 | 覆盖 ≥ 3 / 共 7 个 |

**10 个活动分类（PDU 计分 + 双周期封顶）**

```
work          专业工作          10/6 PDU·年(≥6mo)   封顶 30/30
volunteering  行业志愿          1 PDU·小时          封顶 20/30（每年 10）
wcet_support  WCET 项目贡献     1 PDU·小时          封顶 15/25
teaching      课程开发/授课     开发2/授课1 PDU·小时 封顶 20/30
publications  论文/著作         1 PDU·小时(撰写)    封顶 15/25
training      正规培训          1 PDU·小时          封顶 15/25
self_study    自学             1 PDU·小时(须评估)  封顶 10/15
license_cert  其他执照/认证     1 PDU·小时          封顶 15/25
conferences   行业会议          1 PDU·小时(参会)    封顶 15/20
member_rank   会员升级          固定额(5/15/20)     封顶 15/25
```

专利：申请 5 / 获奖 10 PDU（三年），五年周期获奖最多 20；每周期仅 1 项。自学须含评估方法；非纯无线主题按相关占比折算；执照/认证与培训重复计时不可双报。

**七大技术知识领域**：原表引用 WCET Candidate Handbook Appendix A 但未在表内枚举。本库列出公开 WCET BoK 常见 6 类（RF and Propagation / Signal Processing / Communication Theory / Networks·Systems·Access / Hardware·Digital·Multimedia / Software），**第 7 类明确标注「待核实」——不臆造**（项目已停办，仅历史存档可查）。

## 三、数据层与流水线性（可复现）

```
research/recert/source/*.xls  ──build_recert_docs.py──►  data/recert_docs.json
   （用户投递原件，留 SHA256）        （解析规则 prose +           （10 活动分类 / 双周期 /
                                        结构化封顶，--check 溯源）     7 领域 / 合规清单）
```

`build_recert_docs.py` 工程纪律（与 RFC/CA/Mongo 同款）：

1. 规则 prose 直接取自 .xls 指令单元格（权威源），不手抄改写；
2. 结构化封顶（cycle_cap / pdu_per_unit）为本工具对 prose 的解释，附 source_sheet；
3. `--check` 反向校验：逐分类逐周期核对 `.xls` 指令文本仍含各封顶数，源变更即失败（防漂移）；并校验磁盘产物与重建一致。

## 四、native 层与 CLI（只读不联网）

`native/recert.py` 只读函数：`info()` / `cycles()` / `technical_areas()` / `categories()` / `category(key)` / `requirements()` / `validation_rules()` / `summary()` / `max_attainable(cycle)`。

CLI `recert`：

```
recert                # 方案速览（认证/作者/停办声明/四行摘要）
recert cycles         # 两周期下限与跨度 + 全局门槛
recert areas          # 七大技术知识领域（第 7 类标注待核实）
recert categories     # 10 活动分类计分与封顶
recert show <类>      # 单类规则（work/teaching/conferences…）
recert rules          # 续证合规校验清单（只报告不改写）
recert caps           # 各分类理论封顶合计（仅合规提示，非刷分建议）
```

## 五、测试与回归

- `tests/test_recert.py` 7 项：info/停办声明、双周期门槛、10 分类完整性与双周期封顶、单类归一化查询、第 7 领域诚实标注、封顶合计 > 下限、合规清单；
- 全量 pytest 回归通过；版本 0.6.50 → **0.6.51**（`__init__.py` / `pyproject.toml` / Go `const version` 三处同步，README 与 CLI 串同步）。
