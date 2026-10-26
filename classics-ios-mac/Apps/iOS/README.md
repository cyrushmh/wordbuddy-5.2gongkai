# 国学经典 · iOS App 接入说明

本目录用于把共享库 `ClassicsHarmony` 接入一个 iOS 应用（SwiftUI）。

## 为什么不在 SwiftPM 里直接出 iOS .app

SwiftPM 的 `executableTarget` 在 macOS 可以跑命令行/简单 GUI，但 **iOS 的 `.app` 包（签名、Entitlements、Asset Catalog、Launch Screen）必须经由 Xcode / `xcodebuild`**。所以 iOS 端采用「Xcode 工程引用 SwiftPM 本地包」的标准做法。

## 步骤

1. 打开 Xcode → `File ▸ New ▸ Project ▸ iOS ▸ App`，Interface 选 **SwiftUI**，Language 选 **Swift**。
   建议名称 `ClassicsIOS`，Bundle ID 自定（如 `com.example.classicsios`）。

2. 把本仓库的 `classics-ios-mac` 目录拖入 Xcode 工程左侧导航：
   - 在弹出的对话框勾选 **Add to: ClassicsIOS**，并勾选 **Create folder references**（或作为 Package 引用）。
   - Xcode 会自动识别 `Package.swift`，把 `ClassicsHarmony` 作为本地 Swift Package 依赖。

3. 在 `ClassicsIOS` 的 target → **General ▸ Frameworks, Libraries, and Embedded Content** 中，点 `+` 添加 `ClassicsHarmony`（选择 **Do Not Embed**，因为 App 直接静态链包）。

4. 替换 `ContentView.swift`（iOS 工程自动生成的）为以下代码，复用共享库：

   ```swift
   import SwiftUI
   import ClassicsHarmony

   @main
   struct ClassicsIOSApp: App {
       var body: some Scene {
           WindowGroup {
               ContentView()
           }
       }
   }
   ```

   > `ContentView`（在 ClassicsHarmony 内）已通过 `#if os(iOS)` 走底部 `TabView`（书架 / 对弈 / 设置）分支，无需额外适配。

5. 如需真机/模拟器运行：`Product ▸ Run`（⌘R）。最低部署目标 iOS 17（用到了 `@Observable` / `Canvas`）。

## 资源（可选）

- 声音：`SoundPlayer` 会从包内读 `tip.wav`；把音频拖进 `ClassicsIOS` 的 Assets/Resource 即可生效，缺失则静默降级。
- 图片：`ZoomImageView` 默认取 `startIcon`，可换成你的古籍图资源名。

## 与 HarmonyOS 版的关系

| 端 | 工程 | 入口 | 状态管理 |
|---|---|---|---|
| HarmonyOS NEXT | `classics-harmony-app` | `EntryAbility` | ArkTS V2 `@ObservedV2`/`@Trace` |
| iOS | 本 Xcode 工程 | `ClassicsIOSApp` | SwiftUI `@Observable`（V2 对应） |
| macOS | `ClassicsMac`（SwiftPM 可执行） | `ClassicsMacApp` | 同上 |

数据契约（`ClassicBook` / `ClassicChapter`）三端一致，UI 组件一一镜像。详见 `docs/03_iOS_Mac_移植.md`。
