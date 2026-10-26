import SwiftUI

/// 表格（镜像 HarmonyOS 版 TableView.ets，旧代为 TableLayout）：
/// 跨端用 Grid；macOS 另有原生 Table（见 docs/03_iOS_Mac_移植.md）。
public struct TableView: View {
    private let rows: [(String, String, String)] = [
        ("卷", "名", "要旨"),
        ("上", "周易上经", "乾坤定位"),
        ("中", "系辞", "穷理尽性"),
        ("下", "说卦", "八卦之象"),
    ]

    public init() {}

    public var body: some View {
        Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 16, verticalSpacing: 8) {
            ForEach(rows, id: \.0) { r in
                GridRow {
                    Text(r.0).bold()
                    Text(r.1)
                    Text(r.2).foregroundStyle(.secondary)
                }
            }
        }
        .padding()
    }
}
