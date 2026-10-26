# MongoDB 权威指南（第2版）导入：知识索引 + 系统调优与 sysweeper 交叉对账

> 任务组 #366–#370 ｜ 2026-10 ｜ 用户指令：**投递《MongoDB权威指南（第2版）-2014-中文版.pdf》**。
> 承 docs/14（RFC 目录）、docs/15（修真图谱）、docs/16（WebTrust 审计图谱）之后。本轮与前几轮的最大差异：**首次遇到明确受限的商业出版物**，归档策略因此改变。

---

## 一、做了什么，以及为什么原件不入库

```
用户投递 PDF（802 页 / 5.8MB / 未加密）
   ↓ 核验（SHA256 + pdfinfo）
   ↓ pdftotext 提取（18,718 行 / 688KB，仅作本地分析）
research/mongodb/manifest.json         # 书目元数据 + SHA256 + 版权边界 + 不入库决策
research/mongodb/mongo_book_facts.json # 事实底稿：章节体系 + 43 概念 + 16 条系统调优
research/mongodb/build_mongo_docs.py   # 构建脚本（含交叉引用真实性断言）
   ↓
sysweeper/data/mongo_docs.json         # 知识库（结构索引 + 概念 + 调优）
   ↓
sysweeper/native/mongo_catalog.py      # 只读消费层
sysweeper/cli.py cmd_mongo             # CLI 八个子命令
```

**版权边界（本轮核心判断）**：PDF 版权页写明「您购买的图灵电子书仅供您个人使用，未经授权，不得以任何方式复制和传播本书内容」。因此：

| 资产 | 处置 |
|---|---|
| PDF 原件（5.8MB） | **不入库**——整本放进公开仓库即构成复制传播；仅保留 SHA256 供后续核验同一文件 |
| 提取全文（688KB） | **不入库**——同理；只在沙箱 `/tmp/mongobook/` 作本地分析副本 |
| 章节体系 | 入库——取自目录页，属结构性索引（类同 RFC 目录，本就是给人查阅的导航信息） |
| 概念条目（43 条） | 入库——通用技术知识的自行概括（读书笔记级），每条标注所属章节编号便于回书核对，**不复制正文段落** |

与 docs/16 的取舍对比：WebTrust 报告是第三方审计的客观事实文件（CA 清单/指纹/事项），可存档原件；本件是明确受限的商业出版物，原件不入库。**同一套纪律，因材料性质不同而结论不同**——不是"有 PDF 就往仓库里塞"。

## 二、知识库模型

| 部分 | 章 | 主题 |
|---|---|---|
| 一 MongoDB介绍 | 1–4 | 简介、基础知识（文档/集合/数据类型/ObjectId）、CRUD、查询 |
| 二 设计应用 | 5–8 | 索引、特殊索引与集合（TTL/全文/地理/GridFS/固定集合）、聚合、应用设计 |
| 三 复制 | 9–12 | 创建副本集、组成（同步/心跳/选举/回滚）、应用连接（写关注/读偏好）、管理 |
| 四 分片 | 13–16 | 分片、配置、片键选择、分片管理 |
| 五 应用管理 | 17–19 | 应用动态/诊断、数据管理、持久性（journal） |
| 六 服务器管理 | 20–23 | 启停、监控、备份、部署 |

43 条概念分 9 类：数据模型 6、增删改 4、查询 5、索引与特殊集合 8、聚合 3、应用设计 4、复制 6、分片 4、管理与持久性 3。

## 三、CLI

```
sysweeper mongo                        # 书目 + 规模 + 版权边界 + 分类分布
sysweeper mongo chapters [--part p3]   # 章节清单（按部分过滤）
sysweeper mongo show 23                # 某章全部 24 个小节 + 本章相关概念
sysweeper mongo concepts [--cat index] # 按类别看概念（均标所属章节）
sysweeper mongo search <词>            # 概念与调优条目混检
sysweeper mongo deploy                 # 第 23 章 16 条系统层调优
sysweeper mongo cross                  # 只列与 sysweeper 对得上的项（运行期核验）
sysweeper mongo book                   # 书目 + ISBN + SHA256 + 版权处置说明
```

## 四、系统调优 × sysweeper 交叉对账（本轮的实际产出）

第 23 章「部署 MongoDB」的 16 条系统层建议，与本项目既有的 461 个任务 / 93 个子命令对账：

| 原书条目 | sysweeper 落点 | 核验 |
|---|---|---|
| 23.3.3 禁用大内存页面（THP） | 任务 `linux_thp_compaction` | ✅ 运行期 `registry.by_id` 命中 |
| 23.3.4 SSD/NVMe 磁盘调度 | 任务 `linux_io_scheduler` | ✅ |
| 23.1.5 交换空间 / swappiness | 任务 `linux_swappiness` | ✅ |
| 23.3.1 禁用 NUMA | 子命令 `kernel` | ✅ |
| 23.3.5 不要记录访问时间（noatime） | 子命令 `storage` | ✅ |
| 23.5.1 时钟同步（NTP） | 子命令 `chrono` | ✅ |
| 其余 10 条（RAID/文件系统/ulimit/OOM/虚拟化等） | `storage`/`hardware`/`virt`/`network`/`settings` | ✅ 子命令存在（条目级覆盖待后续） |

构建期从 cli.py / tasks/*.py 抓取真实的任务 id 与子命令名做断言，运行期再用 `registry.by_id` 二次核验——**引用不存在即构建失败**，杜绝"看起来很有道理但项目里根本没有"的虚假对账。

## 五、验证

| 层 | 验证 | 结果 |
|---|---|---|
| 底稿自检 | 23 章号连续、概念 chapter 引用非悬空、计数对账（曾抓到 concepts 写作 41 实为 43、section 正则过严误判 23.4） | ✅ 已修正 |
| 构建脚本 | `--check`：章节连续/引用非悬空/sysweeper 任务与子命令真实存在 | ✅ |
| 消费层 | pytest 7 项（完整性/章节与概念/检索/交叉引用存在性/版权边界/CLI 冒烟） | ✅ 全绿 |
| 全量回归 | `pytest -q` 全仓 | ✅ 1087 passed / 3 skipped / 0 failed |

**诚实声明**：
- 概念条目为通用技术知识的自行概括，非原文引用；如与原书表述有出入，以原书为准（条目已标章节号便于核对）。
- 原书为 2013/2014 时点作品（MongoDB 2.x 时代），其中「无跨文档事务」「不适合强事务场景」等判断已随版本演进改变——知识库按原书面貌录入，未做现代化修正（避免以今度古造成新的不实）。
- **存量问题提示（主动披露）**：docs/16 轮曾把 WebTrust 报告 PDF 原件（标注 Proprietary & Confidential）复制入公开仓库。该报告虽属公开鉴证类文件，但报告本身载明禁止复制分发，严格讲不宜整本入库——事实底稿与知识库已含全部可用信息，原件副本可从仓库移除。是否移除由用户决定（见下节待办）。

## 六、产物清单

| 文件 | 说明 |
|---|---|
| `research/mongodb/manifest.json` | 书目元数据 + SHA256 + 版权边界与不入库决策 |
| `research/mongodb/mongo_book_facts.json` | 事实底稿（23 章体系 / 43 概念 / 16 调优） |
| `research/mongodb/build_mongo_docs.py` | 构建脚本（`--check` 模式 + 交叉引用真实性断言） |
| `system-optimizer/.../data/mongo_docs.json` | 知识库 |
| `system-optimizer/.../native/mongo_catalog.py` | 只读消费层（含 cross_ref 运行期核验） |
| `system-optimizer/.../cli.py` | `cmd_mongo` + `sp_mongo`（v0.6.48） |
| `system-optimizer/tests/test_mongo.py` | pytest 7 项 |
| `system-optimizer/README.md` | 数据树 + 命令表新增 `mongo` |

版本：Python `__version__` / pyproject / Go const 三处同步 **0.6.47 → 0.6.48**。

## 七、未完成（诚实阻塞）

- **《iOS编程 第4版》**：PDF 本体被 ZIP 传统加密（ZipCrypto）锁住，密码指向第三方引流站点（`yiquma.com` → `manongbook.com`）。**未做破解**（pdfcrack/rarcrack 一类工具不用：那是受版权保护的商业出版物，爆破等于绕过访问控制）；16 个来自包内文本自身的候选密码尝试全部失败，未做字典爆破。已归档：三层封装结构、各层哈希、两张明文封面/截图（可确认书目身份）。**待用户提供密码或解密版后再续**。
