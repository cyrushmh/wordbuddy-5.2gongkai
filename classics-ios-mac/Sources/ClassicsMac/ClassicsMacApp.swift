import SwiftUI
import ClassicsHarmony

/// macOS 可执行 App 入口（对应 HarmonyOS 版 EntryAbility）。
/// 复用共享库 ClassicsHarmony 的 ContentView（NavigationSplitView 分支在 macOS 生效）。
@main
struct ClassicsMacApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowResizability(.contentSize)
    }
}
