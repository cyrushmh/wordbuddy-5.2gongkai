# 道家经典文库 · HarmonyOS NEXT（Stage 模型）构建说明

本工程是一个合规的 HarmonyOS NEXT（API 12 / ArkTS / Stage 模型）应用骨架，
用于阅读**道家经典**：《道德经》《周易参同契》《太上老君说常清静经》。

> ⚠️ 沙箱环境**没有** HarmonyOS SDK / ohpm / hvigor 工具链，无法在此出 `.hap`。
> 以下为真机 / DevEco Studio / Command Line Tools 出包步骤；本目录所有配置与源码
> 均已按规范写好，可直接打开构建。

## 内容来源与版权

| 典籍 | 来源 | 状态 |
|---|---|---|
| 《道德经》81 章原文+译文 | https://www.daodejing.org/ 分章页（1.html–81.html） | 全文已内嵌 |
| 《周易参同契》章目+简介 | http://www.fushengwuliang.com/1/zhouyicantongqi.html | 仅章目（源站节选页），正文占位待补全 |
| 《太上老君说常清静经》全文 | 用户提供通行本 | 全文已内嵌（按宣说者分段） |

正文为古籍公共领域文本，本应用仅作**个人阅读/研习展示**，不含任何商业用途、不打包外部二进制。

## 工程结构

```
classics-harmony-app/
├── AppScope/                      # 应用级配置（bundleName / icon / label）
├── entry/src/main/
│   ├── ets/model/
│   │   ├── ClassicsData.ts        # 三书数据模型（CLASSICS: ClassicBook[]）
│   │   ├── ReaderPrefs.ts         # 阅读偏好（字号/行距/配色/简繁 + 适老化/高对比/跟随系统）
│   │   ├── Accessibility.ets      # 无障碍中枢：有效字号/行距/配色 + 读屏播报
│   │   ├── DeviceSync.ets         # 组网无障碍：多设备协同状态（无障碍化封装）
│   │   └── DistributedPrefs.ets   # 分布式 KV 构建块（DeviceSync 的能力底座）
│   ├── ets/pages/
│   │   ├── Index.ets             # 典籍列表 + 组网无障碍状态卡
│   │   ├── BookDetail.ets        # 单书章目
│   │   └── ChapterDetail.ets     # 单章原文（+译文）+ 阅读设置（含适老化/无障碍开关）
│   ├── module.json5              # 模块/能力/页面注册 + 组网权限声明
│   └── resources/...             # 字符串、颜色、图标占位
├── oh-package.json5 / build-profile.json5 / hvigorfile.ts
├── build_hap.sh                   # 一键构建 HAP（调试签名）
└── BUILD.md
```

## 真机 / DevEco 出包（一步）

```bash
# 方式一：本仓库自带一键脚本（需已装 SDK + 调试签名 material）
cd classics-harmony-app
bash build_hap.sh

# 方式二：手动
ohpm install
hvigorw assembleHap --mode debug   # 自动签名需本地配置签名信息（DevEco 首次运行会生成）

# 产物：entry/build/default/outputs/default/entry-default-signed.hap
```

> ⚠️ `build-profile.json5` 的 `signingConfigs` 初始为空（DevEco 模板惯例），
> DevEco 首次「运行/构建」会自动写入本机调试签名；CI / 命令行构建需自备 `material/`。

## 无障碍与适老化（已实现）

本工程把「无障碍」理解为三层，已落地：

1. **系统使用无障碍（UI 读屏）**
   - 关键可交互元素（书卡、检索框、书签删除、章节项、道藏按钮、组网开关）均加
     `accessibilityText` / `accessibilityDescription`；纯装饰图（龙纹、卡片底图）标
     `accessibilityLevel(AccessibilityLevel.No)`，避免读屏冗余。
   - 阅读设置变更、加书签、组网状态变化均通过 `accessibility.announce` 读屏播报
     （`Accessibility.ets` 统一封装，异常静默降级，绝不阻断主流程）。

2. **适老化（长辈模式）**
   - 阅读设置面板新增「长辈模式」一键开关：字号放大到 1.5×、行距 1.4×、点击区放大到 44vp。
   - 新增「高对比度」开关（纯黑底白字亮黄强调）与「跟随系统字体」开关（乘系统字体缩放）。
   - 全部基于 `ReaderPrefs` 既有偏好键扩展，持久化、跨页面 AppStorage 共享。

3. **组网无障碍（多设备协同）**
   - `DeviceSync.ets` 在分布式 KV 之上做无障碍封装：用通俗中文暴露「已连接几台设备 /
     上次同步 / 开关」，状态变化读屏播报。
   - 默认安全降级：无权限 / 无可信设备组时如实说明「组网待开启」，绝不崩溃。
   - `module.json5` 已声明 `ohos.permission.DISTRIBUTED_DATASYNC`（按需授权）。
   - 真实跨设备同步需：真机 + 同一华为账号可信设备组 + 用户在设置中开启本开关。

## 上线前需替换的占位

- `AppScope/resources/base/media/app_icon.png`：1×1 占位图，需替换为正式图标。
- `entry/src/main/resources/base/media/startIcon.png` 与 `layered_image.png`：占位图。
- `module.json5` 中 `startWindowIcon` / `icon` 若需换正式图，调整 `$media` 引用即可。

## 后续可扩展

- 补全《周易参同契》全本正文（替换 `ClassicsData.ts` 中对应 `original` 占位串）。
- 继续把更多典籍（如《庄子》《阴符经》）以相同 `ClassicBook` 结构追加进 `CLASSICS`。
- 组网无障碍：在可信设备组就绪后，把 `DeviceSync` 的开关接入真实跨设备书签/进度漫游
  （当前为无障碍状态呈现 + 播报，能力底座 `DistributedPrefs` 已就位）。
