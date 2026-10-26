import SwiftUI

/// 滑块拼图（镜像 HarmonyOS 版 SliderPuzzle.ets）：3×3 状态矩阵，点击空格相邻块移动，复原判定。
public struct SliderPuzzleView: View {
    @State private var tiles: [Int] = (0..<9).map { $0 }   // 0 = 空白

    public init() {
        shuffle()
    }

    /// 从解状态反推合法移动打乱，保证可解（镜像 ArkTS 的洗牌逻辑）。
    private func shuffle() {
        var t = Array(0..<9)
        for _ in 0..<60 {
            let blank = t.firstIndex(of: 0)!
            let neighbors = [blank - 3, blank + 3,
                            blank % 3 != 0 ? blank - 1 : -1,
                            blank % 3 != 2 ? blank + 1 : -1]
                .filter { $0 >= 0 && $0 < 9 }
            if let swap = neighbors.randomElement() {
                t.swapAt(blank, swap)
            }
        }
        tiles = t
    }

    private func move(at i: Int) {
        guard let blank = tiles.firstIndex(of: 0) else { return }
        let adj = [blank - 3, blank + 3,
                   blank % 3 != 0 ? blank - 1 : -1,
                   blank % 3 != 2 ? blank + 1 : -1]
        if adj.contains(i) {
            tiles.swapAt(blank, i)
        }
    }

    private var solved: Bool { tiles == Array(0..<9) }

    public var body: some View {
        VStack(spacing: 10) {
            LazyVGrid(columns: Array(repeating: .init(.flexible()), count: 3), spacing: 6) {
                ForEach(0..<9, id: \.self) { i in
                    let v = tiles[i]
                    Button { move(at: i) } label: {
                        ZStack {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(v == 0 ? Color.clear : Color.brown.opacity(0.5))
                            if v != 0 {
                                Text("\(v)")
                                    .font(.title)
                                    .foregroundStyle(.white)
                            }
                        }
                        .aspectRatio(1, contentMode: .fit)
                    }
                    .disabled(v == 0)
                }
            }
            .frame(width: 270, height: 270)

            Text(solved ? "已复原 ✅" : "点击空格相邻块移动")
                .foregroundStyle(.secondary)
            Button("重排") { shuffle() }
        }
        .padding()
    }
}
