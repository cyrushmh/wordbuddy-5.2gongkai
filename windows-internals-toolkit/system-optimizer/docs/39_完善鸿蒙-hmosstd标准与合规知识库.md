# 39 · 完善鸿蒙：hmosstd 标准与合规知识库（第四生态标准库）

> 指令原文：「完善鸿蒙」。
>
> v0.6.71 完成四仓导入（hmos_ecosystem 工程/生态知识）后，盘点发现鸿蒙侧知识体系
> 的最大空白：**标准与合规口径**。androidstd 管国内 Android 侧、gmsstd/fdroidstd
> 管两条 Android 分发通道，而 HarmonyOS NEXT 自己的权限模型、隐私合规、上架审核、
> 安全能力没有标准库。本档记录 hmosstd 的立项、内容与验证。

## 1. 立项依据：鸿蒙侧知识体系的三层分工

盘点 v0.6.71 后的全部鸿蒙相关资产，确认三层结构已有两层、缺第二层：

| 层 | 子系统 | 回答的问题 | 状态 |
|----|--------|-----------|------|
| 探测层 | harmony / harmony_hdc / harmony_device / kaihong | 「这台设备/这个工程是什么」 | v0.6.30 前后已建 |
| **标准层** | **hmosstd** | **「对齐什么标准」** | **本档新建（v0.6.72）** |
| 工程层 | hmos_ecosystem | 「生态怎么干活」 | v0.6.71 已建 |

标准层缺位的直接后果：harmony 探测只回答能力面，hmos_ecosystem 只回答事实面，
**没有任何知识条目回答「App 是否合规、上架要备什么、权限怎么申请才合法」**。

## 2. 知识库内容（11 条）

`data/hmosstd_standards.json`，八字段范式（name/org/url/protocols/interfaces/
docs/advice），口径分法规原文与官方公开文档两类，社区整理逐条 needs_verify：

| key | 主题 | 主源 |
|-----|------|------|
| pipl_harmony | PIPL 上位法（告知-同意/敏感信息单独同意/跨境/个人权利） | npc.gov.cn 法规原文 |
| appgallery_listing | AppGallery 上架要件（软著/备案/隐私政策/首启同意时序） | AppGallery Connect 指南 |
| app_filing_miit | 工信部 App 备案（171 号文，2023-08 起） | beian.miit.gov.cn |
| permission_apl_model | 权限 APL 分级与 user_grant 敏感权限 | HarmonyOS 权限列表 |
| privacy_indicators | NEXT 隐私指示器（相机/麦克风/位置/剪贴板可见化） | 官方文档（社区整理标注） |
| huki_key_management | HUKS 密钥库（密钥不出 TEE/Attestation/用户认证绑定） | HUKS 开发指南 |
| crypto_cert_tee | 加解密框架/证书链校验/iTrustee TEE | CryptoFramework/Cert 指南 |
| api_version_compat | API 版本兼容（@ohos→@kit、canIUse 降级） | 官方文档（社区整理标注） |
| minor_protection | 未成年人保护（14 岁分界/青少年模式） | PIPL 31 条+未保条例 |
| background_network_std | 后台任务与网络权限（长时任务/提醒/网络统计） | 官方文档（社区整理标注） |
| xts_app_testing | XTS/Acts 兼容性测试 | gitee.com/openharmony/xts_acts |

**跨库互证**是同构叙事的延伸：HUKS「密钥不出 TEE」与 gmsstd 的 keystore 口径、
fdroidstd 的可复现构建、cert 子系统的证书链校验分别互证（见联动轴）。

## 3. 交付物（子系统四件套 + 接线）

| 文件 | 职责 |
|------|------|
| `data/hmosstd_standards.json` | 11 条标准知识 |
| `native/hmosstd.py` | 只读层：`reference`/`reference_all`/`hmosstd_doc_list`/`HMOSSTD_CHECKS`（12 项）/`hmosstd_compliance_checklist`/`hmosstd_compliance_report`；`_SELF_POSITION` 声明「不代审、不代申诉、不下合规结论」 |
| `tasks/hmosstd.py` | 3 任务：`hmosstd_overview`（总览）/`hmosstd_listing_privacy`（上架与隐私链路自查）/`hmosstd_security_baseline`（HUKS/TEE/证书链/国密基线） |
| `tests/test_hmosstd.py` | 13 测试：schema 完整/官方源域名在位/社区源 needs_verify/零网络不变量/检查项回链/任务可解析/子系统登记 |

接线四入口：`registry.py`（3 处）、`native/subsystems.py`（Subsystem 登记，
category=隐私/合规，与 std 三库同档）、`cli.py`（`cmd_hmosstd` + `hmosstd`
子命令）、`gui.py`（「鸿蒙标准·权限/隐私/上架」窗口）。CLI 111→112、GUI 96→97、
ergonomics scene 加入 `hmosstd`。

**联动轴 4 条**（`AXES_EXTRA`）：hmosstd → gmsstd（双通道合规关联）、
hmosstd → androidstd（PIPL 共同上位法关联）、hmosstd → hmos_ecosystem
（标准给生态定边界，供给）、hmosstd → cert（Attestation 与信任链门控）——
性质各异、方向明确，孤岛清零。

## 4. 验证

- 测试：test_hmosstd 13 项；omni 真缺口 0 项；联动/兼容/同构三测试通过
- 版本 0.6.72 五处同步 + concepts 四库三字段（cli_subcommands 111→112、
  gui_windows 96→97、deno_report_viewer_version 0.6.71→0.6.72）+
  report_viewer.html 重生
- 全量回归：**1429 passed / 3 skipped / 0 failed**
- 冒烟：`sysweeper hmosstd` 输出 11 条标准 + 12 项对照清单 + 3 任务全链

## 5. 边界

- 法规原文与审核细则随政策更新（备案批次、审核指南改版），本库标注 needs_verify
  或「以官方最新版为准」；法律结论不代律师意见。
- HUKS/cryptoFramework 的算法支持面随 SDK 演进（@ohos→@kit 迁移），具体集合以
  官方 API 文档为准。
- 本库只给对照口径，合规判定权在用户与官方来源——这是与 std 三库一致的自述。
