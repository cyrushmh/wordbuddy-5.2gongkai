// swift-tools-version:5.9
// Linux 原生 Swift 端口：复用 iOS/macOS 的纯逻辑核心（ClassicsCore），
// 外加一个命令行前端。核心文件与 classics-ios-mac 同源拷贝，保持数据契约一致。
//
// 构建（需 Swift 官方 Linux 工具链，见 https://www.swift.org/install/）：
//   export PATH=/opt/swift/usr/bin:$PATH
//   swift build -c release
//   .build/release/classics list
import PackageDescription

let package = Package(
    name: "classics-swift-linux",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .library(name: "ClassicsCore", targets: ["ClassicsCore"]),
        .executable(name: "classics", targets: ["classics-cli"])
    ],
    targets: [
        // 纯逻辑核心：仅依赖 Foundation，无 SwiftUI / AppKit，Linux 可直接编译
        .target(name: "ClassicsCore"),
        .executableTarget(name: "classics-cli", dependencies: ["ClassicsCore"])
    ]
)
