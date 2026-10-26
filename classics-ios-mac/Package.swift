// swift-tools-version:5.9
// 国学经典跨端工程 —— 共享库（iOS / macOS 通用）+ macOS 可执行 App。
//
// 设计对齐：与 classics-harmony-app（HarmonyOS NEXT / ArkTS）同一套「整体与局部」架构，
// 状态管理采用 SwiftUI @Observable（对应 ArkTS V2 的 @ObservedV2/@Trace）。
//
// 编译说明（沙箱不可测，保留代码规范，见 build_ios_mac.sh）：
//   - 共享库 ClassicsHarmony：swift build（需 macOS 或 Swift 工具链）
//   - iOS .app：Xcode 打开 Apps/iOS 工程并引用本 Package（见 Apps/iOS/README.md）
//   - macOS .app：在 Mac 上 `swift build` 后打包，或 Xcode 打开本目录

import PackageDescription

let package = Package(
    name: "ClassicsHarmony",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "ClassicsHarmony", targets: ["ClassicsHarmony"]),
    ],
    targets: [
        .target(
            name: "ClassicsHarmony",
            dependencies: [],
            path: "Sources/ClassicsHarmony"
        ),
        .executableTarget(
            name: "ClassicsMac",
            dependencies: ["ClassicsHarmony"],
            path: "Sources/ClassicsMac"
        ),
    ]
)
