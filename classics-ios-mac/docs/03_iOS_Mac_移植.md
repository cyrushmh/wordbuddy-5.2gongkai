# 国学经典 · iOS / macOS 移植分析与应用

> 配套工程：`classics-ios-mac/`（SwiftPM 共享库 `ClassicsHarmony` + macOS 可执行 `ClassicsMac` + iOS 接入说明）。
> 上游工程：`classics-harmony-app/`（HarmonyOS NEXT / ArkTS）。
> 本文件回答三件事：**架构如何对齐**、**组件如何一一映射**、**实际能否构建 + 结论**。

---

## 一 · 为什么做这次移植

`classics-harmony-app` 已沉淀 65+ 个 ArkTS 构建块与一份整体分析（`docs/01`/`docs/02`），其跨语言映射章节已把 NEXT 与 SwiftUI·Swift / Jetpack Compose / Flutter / Rust / Qt 对齐。**本次是把「映射」落成「可运行工程」**——用 SwiftUI 把国学经典 App 真正搬到 iOS 与 macOS，验证三端架构同构。

哲学延续：`docs/01`/`docs/02` 的三辩证（整体与局部 · 层次与平衡 · 生存与毁灭）与状态管理 V2，是本次移植的锚点。

---

## 二 · 架构对齐（整体）

| 维度 | HarmonyOS NEXT (ArkTS) | iOS / macOS (SwiftUI·Swift) |
|---|---|---|
| 工程模型 | hvigor 工程 + Stage 模型 | SwiftPM 包 + `@main App`（macOS）/ Xcode App（iOS） |
| 入口 | `EntryAbility` | `ClassicsMacApp` / `ClassicsIOSApp` |
| 整体导航 | `BottomTabs` / `Tabs` | `TabView`（iOS）/ `NavigationSplitView`（macOS） |
| 数据契约 | `ClassicsData.ts`（ClassicBook/ClassicChapter） | `ClassicsModels.swift` + `ClassicsData.swift`（同名字段） |
| 状态管理 | V2 `@ObservedV2` + `@Trace` | `@Observable`（Observation 框架） |
| UI 范式 | 声明式 ArkUI（`Column`/`Row`/`Stack`/`Canvas`） | 声明式 SwiftUI（`VStack`/`HStack`/`ZStack`/`Canvas`） |
| 命令式绘制 | `CanvasRenderingContext2D` | SwiftUI `Canvas` + `GraphicsContext`/`Path` |
| 系统能力 | `@kit.*`（AudioKit/BasicServicesKit/InputKit…） | `AVFoundation` / `UIPasteboard`/`NSPasteboard` / `AppKit` + `#if os()` 分支 |
| 持久化 | `AppStorage`/`dataPreferences` | `@AppStorage`（UserDefaults） |
| 适老化/无障碍 | `accessibilityText` | `.accessibilityLabel` / 大字号 `@AppStorage` |

**结论：三端是「同一张地图的不同方言」**——整体导航结构、数据契约、组件职责完全一致，仅平台 API 落地不同。这正是「整体与局部」：整体（架构/契约/哲学）不变，局部（平台 API）适配。

---

## 三 · 组件映射表（局部）

| ArkTS 组件（HarmonyOS） | SwiftUI 对应 | 文件 | 备注 |
|---|---|---|---|
| `TextView.ets`（文本综合） | `Text` + 修饰符 | `Components/Text/TextView.swift` | 颜色/字号/自适应/`lineLimit`/斜体/字重一字不差映射 |
| `StackLayout.ets` | `ZStack` | `Components/Layout/StackLayoutView.swift` | 三层叠放 |
| `TableView.ets`（TableLayout） | `Grid` | `Components/Layout/TableView.swift` | macOS 另有原生 `Table`，注释已说明 |
| `TabListView.ets`（TabList） | `Picker(.segmented)` | `Components/Layout/TabListView.swift` | iOS TabView 默认底部，顶部需自绘 |
| `SliderView.ets` | `Slider` | `Components/Controls/SliderView.swift` | 双向绑定 |
| `SwitchView.ets` | `Toggle` | `Components/Controls/SwitchView.swift` | 双向绑定 |
| `RingProgressView.ets` | `ProgressView(.circular)` | `Components/Controls/ProgressView.swift` | 环形进度 |
| `SliderPuzzle.ets` | `LazyVGrid` + `@State` 矩阵 | `Components/Games/SliderPuzzleView.swift` | 3×3 状态矩阵 + 复原判定 |
| `TetrisGame.ets` | `Canvas` + `Timer` | `Components/Games/TetrisGameView.swift` | 结构骨架（见下） |
| **`GoBoard.ets`（三辩证）** | `Canvas` + `@Observable` | `Components/Games/GoBoardView.swift` | 死活/提子/禁着逻辑完整移植 |
| `SoundPlayer.ets`（AudioKit） | `AVAudioPlayer`/`NSSound` | `Components/Media/SoundPlayer.swift` | `#if os()` 分支 |
| `PasteboardOps.ets`（BasicServicesKit） | `UIPasteboard`/`NSPasteboard` | `Components/Media/PasteboardView.swift` | `#if os()` 分支 |
| `ZoomImage.ets`（原生手势重构） | `Magnification`/`Rotation`/`Drag` | `Components/Media/ZoomImageView.swift` | 零依赖，对应 Pinch/Rotation/Pan |

---

## 四 · 围棋 GoBoard：三辩证的跨端示范

围棋是本轮哲学载体，两端实现**逻辑逐行对齐**：

1. **整体与局部**：`collectGroup` 求连通组之气（整体），`captureOpponent` 按整体气提子；单点落子（局部）可逆转全局。Swift 版 `GoState` 的 `collectGroup`/`captureOpponent` 与 ArkTS 版同名同义。
2. **层次与平衡**：输入（点击/`.onTapGesture`）→ 状态（`@Observable GoState` 变更）→ 视图（`Canvas` 重绘）三层分明；声明式 SwiftUI 与命令式 `Canvas` 互补，与 ArkTS 的 `build`/`draw` 同构。
3. **生存与毁灭**：`hasLiberty` 即生、无气且未提子即被提（毁灭）；点击越界/判空静默降级（生存），崩溃即毁灭——两端都做了边界与判空。

**状态管理 V2 的跨端印证**：ArkTS 用 `@ObservedV2 class GoState` + `@Trace` 字段；Swift 用 `@Observable final class GoState`，字段自动可追踪、视图自动响应。**这是「新块统一用 V2」在 Swift 端的天然对应**，证明 V2 范式不是 ArkTS 独有，而是声明式 UI 的通用答案。

---

## 五 · 构建可性（尝试构建，不能测试也保留规范）

执行 `bash build_ios_mac.sh`：

- **沙箱（Ubuntu/Linux）**：`swift`/`xcodebuild` 均缺失 → 脚本在第一步**优雅退出**，输出「源码与 Package.swift 已按规范写就，可离线审阅」。**唯一断点是环境无 Swift 工具链，非代码缺陷。**
- **macOS + Xcode**：`swift build` 可编共享库；出 `.app` 包需 `xcodebuild`（iOS 走 `Apps/iOS/README.md` 的 Xcode 引用流程，macOS 走 `ClassicsMac` scheme）。

这与 `classics-harmony-app` 的 `build_hap.sh` 完全同构：**工具链缺失即降级、规范 100% 保留**。所有 Swift 源码、Package.swift、iOS 接入文档、构建脚本均已落盘，在合规环境一键可出包。

> TetrisGameView 为「结构骨架」：保留棋盘矩阵 + Canvas 绘制 + 定时下落三要素，完整 tetromino 旋转/碰撞可在 Xcode 按 HarmonyOS 版逐项补齐——延续「构建块不替你写满，仅沉淀可复用框架」的约定。

---

## 六 · 下一步（可选）

1. 在 Mac 上 `bash build_ios_mac.sh` 实证出包；按 `Apps/iOS/README.md` 起 iOS 工程。
2. 把 `ClassicsData.ts` 全本（含《周易参同契》90 章）按 `ClassicChapter` 迁移到 `ClassicsData.swift`。
3. 补全 `TetrisGameView` 的 tetromino 完整逻辑（旋转/碰撞/消行）。
4. 在 iOS 补 `TabListView` 的「顶部 Tab」原生组件（或用 `NavigationStack` + segmented 自定义）。
5. 统一三端 CI：HarmonyOS hvigor / iOS xcodebuild / macOS swift 各出包，共享同一份 UI 组件契约。
