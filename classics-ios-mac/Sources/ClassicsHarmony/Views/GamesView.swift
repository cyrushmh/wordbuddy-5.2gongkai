import SwiftUI

/// 对弈/互动（镜像 HarmonyOS 版益智游戏族 SliderPuzzle / TetrisGame / GoBoard）：
/// iOS 列表进入，macOS 用 TabView 同屏切换三局。
public struct GamesView: View {
    public init() {}

    public var body: some View {
        #if os(macOS)
        TabView {
            GoBoardView()
                .tabItem { Label("围棋", systemImage: "circle.grid.3x3") }
            TetrisGameView()
                .tabItem { Label("俄罗斯方块", systemImage: "square.grid.3x3") }
            SliderPuzzleView()
                .tabItem { Label("滑块拼图", systemImage: "square.on.square") }
        }
        .frame(minWidth: 600, minHeight: 600)
        #else
        List {
            NavigationLink("围棋 · 整体与局部 / 生存与毁灭") { GoBoardView() }
            NavigationLink("俄罗斯方块 · Canvas 自绘") { TetrisGameView() }
            NavigationLink("滑块拼图 · 状态矩阵") { SliderPuzzleView() }
        }
        .navigationTitle("对弈")
        #endif
    }
}
