import SwiftUI

/// 环形进度（镜像 HarmonyOS 版 RingProgressView.ets，旧代为 RoundProgressBar）：
/// SwiftUI 原生 ProgressView(.circular)。
public struct ProgressViewRing: View {
    @State private var value: Double = 0.4

    public init() {}

    public var body: some View {
        VStack(spacing: 16) {
            ProgressView(value: value) {
                Text("诵读进度")
            }
            .progressViewStyle(.circular)
            .scaleEffect(2)
            .padding(40)

            Slider(value: $value, in: 0...1) { Text("进度") }
                .padding(.horizontal)
        }
    }
}
