import SwiftUI

/// 顶部选项卡（镜像 HarmonyOS 版 TabListView.ets，旧代为 TabList）：
/// 用 segmented Picker 模拟顶部 Tab 切换（iOS TabView 默认为底部，顶部需自绘）。
public struct TabListView: View {
    @State private var tab = 0
    private let titles = ["原文", "译文", "注疏"]

    public init() {}

    public var body: some View {
        VStack {
            Picker("视图", selection: $tab) {
                ForEach(Array(titles.enumerated()), id: \.offset) { i, t in
                    Text(t).tag(i)
                }
            }
            .pickerStyle(.segmented)
            .padding()

            Group {
                switch tab {
                case 0:
                    Text("原文：道生一，一生二，二生三，三生万物。")
                case 1:
                    Text("译文：道生成一，一衍生二，二衍生三，三衍生万物。")
                default:
                    Text("注疏：河上公曰，一生二谓太极生阴阳。")
                }
            }
            .font(.system(size: 18, design: .serif))
            .padding()

            Spacer()
        }
    }
}
