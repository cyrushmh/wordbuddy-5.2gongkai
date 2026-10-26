import SwiftUI

/// 层叠布局（镜像 HarmonyOS 版 StackLayout.ets）：ZStack 三层叠放。
public struct StackLayoutView: View {
    public init() {}

    public var body: some View {
        ZStack(alignment: .center) {
            Text("底层")
                .padding(40)
                .background(.brown.opacity(0.3))
            Text("中层")
                .padding(24)
                .background(.orange.opacity(0.4))
            Text("顶层")
                .padding(8)
                .background(.red.opacity(0.6))
                .foregroundStyle(.white)
        }
    }
}
