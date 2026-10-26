import SwiftUI

/// 设置（镜像 HarmonyOS 版 SettingsView + SwitchView.ets）：适老化 / 媒体开关，持久化用 @AppStorage。
public struct SettingsView: View {
    @AppStorage("largeText") private var largeText = false
    @AppStorage("autoScroll") private var autoScroll = false
    @AppStorage("soundOn") private var soundOn = true

    public init() {}

    public var body: some View {
        Form {
            Section("适老化") {
                Toggle("大字号模式", isOn: $largeText)
                Toggle("自动滚动", isOn: $autoScroll)
            }
            Section("媒体") {
                Toggle("音效", isOn: $soundOn)
            }
            Section("关于") {
                Text("国学经典 · 跨端阅读（HarmonyOS NEXT / iOS / macOS）")
                Text("状态管理：SwiftUI @Observable（对应 ArkTS V2 @ObservedV2 / @Trace）")
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("设置")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
    }
}
