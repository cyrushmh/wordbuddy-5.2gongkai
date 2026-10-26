import SwiftUI

/// 文本综合（镜像 HarmonyOS 版 TextView.ets）：颜色 / 字号 / 自适应 / 多行省略 / 对齐 / 斜体 / 字重。
public struct TextView: View {
    public init() {}

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text("丹之所为，金碧峥嵘")
                    .font(.largeTitle)
                    .foregroundStyle(.red)                 // 红=丹砂（适老化高对比）
                Text("字号自适应铺满")
                    .font(.system(size: 28))
                    .minimumScaleFactor(0.5)              // 自适应字号
                    .frame(width: 200)
                Text("道可道，非常道。名可名，非常名。无名天地之始，有名万物之母。")
                    .font(.system(size: 18, design: .serif))
                    .lineLimit(2)
                    .truncationMode(.tail)                // 多行省略
                Text("致虚极，守静笃。")
                    .italic()
                    .fontWeight(.bold)                    // 斜体 / 字重
                Text("左对齐示例文字，铺陈道法自然之意境。")
                    .multilineTextAlignment(.leading)     // 对齐
            }
            .padding()
        }
    }
}
