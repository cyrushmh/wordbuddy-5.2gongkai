import SwiftUI

/// 滑块（镜像 HarmonyOS 版 SliderView.ets）：双向绑定 value。
public struct SliderView: View {
    @State private var value: Double = 50

    public init() {}

    public var body: some View {
        VStack(spacing: 10) {
            Slider(value: $value, in: 0...100, step: 1) { Text("进度") }
                .padding(.horizontal)
            Text("当前：\(Int(value))")
                .foregroundStyle(.secondary)
        }
        .padding()
    }
}
