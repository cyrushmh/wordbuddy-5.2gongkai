import SwiftUI

/// 开关（镜像 HarmonyOS 版 SwitchView.ets）：Toggle 双向绑定。
public struct SwitchView: View {
    @State private var on = false

    public init() {}

    public var body: some View {
        Toggle("适老化大字号", isOn: $on)
            .padding()
    }
}
