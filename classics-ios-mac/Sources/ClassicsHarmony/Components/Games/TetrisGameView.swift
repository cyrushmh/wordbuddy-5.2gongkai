import SwiftUI

/// 俄罗斯方块（镜像 HarmonyOS 版 TetrisGame.ets）：Canvas 命令式自绘 + 计时下落。
///
/// 说明：本跨端版为「结构骨架」——保留棋盘矩阵、Canvas 绘制、定时下落三要素，
/// 完整 tetromino 旋转/碰撞逻辑可在 Xcode 中按 HarmonyOS 版逐项补齐（构建块不替你写满，
/// 仅沉淀可复用框架）。以下以「逐行下移」演示下落与重绘闭环。
public struct TetrisGameView: View {
    private let cols = 10
    private let rows = 20

    @State private var board: [[Int]] = Array(repeating: Array(repeating: 0, count: 10), count: 20)
    @State private var timer = Timer.publish(every: 0.5, on: .main, in: .common).autoconnect()

    public init() {}

    public var body: some View {
        VStack(spacing: 10) {
            Canvas { ctx, size in
                let cw = size.width / CGFloat(cols)
                let ch = size.height / CGFloat(rows)
                for r in 0..<rows {
                    for c in 0..<cols {
                        if board[r][c] != 0 {
                            let rect = CGRect(x: CGFloat(c) * cw, y: CGFloat(r) * ch, width: cw, height: ch)
                            ctx.fill(Path(rect), with: .color(.brown))
                            ctx.stroke(Path(rect), with: .color(.secondary.opacity(0.4)), lineWidth: 1)
                        }
                    }
                }
            }
            .frame(width: 200, height: 400)
            .border(.gray)
            .onReceive(timer) { _ in
                // 演示下落：顶部插入随机行，底行移除（完整版替换为单块下移+碰撞）
                board.removeFirst()
                board.append((0..<cols).map { _ in Int.random(in: 0...1) })
            }

            Text("结构骨架：棋盘矩阵 + Canvas 绘制 + 定时下落（完整 tetromino 待 Xcode 补齐）")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 240)
        }
        .padding()
    }
}
