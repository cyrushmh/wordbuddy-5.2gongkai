import SwiftUI
import Observation

// MARK: - 围棋状态（V2 可观察类）
//
// 对应 HarmonyOS 版 GoBoard.ets 的 `@ObservedV2 class GoState` + `@Trace` 字段。
// Swift 侧用 Observation 框架的 `@Observable`：所有字段自动可追踪，视图自动响应变更。
// 这是「状态管理 V2」跨端对齐的锚点（ArkTS @ObservedV2/@Trace ⇄ Swift @Observable）。

/// 棋子状态：0 空 / 1 黑 / 2 白
private enum Stone { case empty, black, white }

@Observable
class GoState {
    var size: Int = 19
    var board: [[Int]] = []
    var turn: Int = 1                 // 1 黑 / 2 白，黑先
    var capB: Int = 0                 // 黑方提子数（毁灭计数）
    var capW: Int = 0
    var tip: String = "黑先行"
    private var history: [[[Int]]] = []   // 悔棋快照栈

    init() { initBoard(19) }

    func initBoard(_ n: Int) {
        size = n
        board = (0..<n).map { _ in Array(repeating: 0, count: n) }
        turn = 1; capB = 0; capW = 0; tip = "\(n) 路 · 黑先行"
        history = []
    }

    private func inBounds(_ r: Int, _ c: Int) -> Bool {
        r >= 0 && r < size && c >= 0 && c < size
    }

    // 整体：收集 (r,c) 同色连通组，并求该组是否有「气」（相邻空点）
    private func collectGroup(_ sr: Int, _ sc: Int, _ color: Int) -> (group: [(Int, Int)], hasLiberty: Bool) {
        var group: [(Int, Int)] = []
        var seen = Set<String>()
        var stack: [(Int, Int)] = [(sr, sc)]
        seen.insert("\(sr),\(sc)")
        var hasLiberty = false
        let dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        while !stack.isEmpty {
            let cur = stack.removeLast()
            group.append(cur)
            for (dr, dc) in dirs {
                let nr = cur.0 + dr, nc = cur.1 + dc
                if !inBounds(nr, nc) { continue }
                let v = board[nr][nc]
                if v == 0 {
                    hasLiberty = true            // 生存：至少一口气
                } else if v == color && !seen.contains("\(nr),\(nc)") {
                    seen.insert("\(nr),\(nc)")
                    stack.append((nr, nc))
                }
            }
        }
        return (group, hasLiberty)
    }

    // 毁灭：落子后提掉对方所有「无气连通组」
    private func captureOpponent(_ r: Int, _ c: Int, _ color: Int) -> Int {
        let opp = color == 1 ? 2 : 1
        let dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        var handled = Set<String>()
        var captured = 0
        for (dr, dc) in dirs {
            let nr = r + dr, nc = c + dc
            if !inBounds(nr, nc) || board[nr][nc] != opp { continue }
            if handled.contains("\(nr),\(nc)") { continue }
            let (group, hasLiberty) = collectGroup(nr, nc, opp)
            for g in group { handled.insert("\(g.0),\(g.1)") }
            if !hasLiberty {
                for g in group { board[g.0][g.1] = 0 }   // 整组提掉（毁灭）
                captured += group.count
            }
        }
        return captured
    }

    func place(_ r: Int, _ c: Int) {
        if board[r][c] != 0 { return }              // 占位：静默忽略（生存式降级）
        let color = turn
        history.append(board.map { $0 })
        if history.count > 200 { history.removeFirst() }

        board[r][c] = color
        let captured = captureOpponent(r, c, color)
        if captured == 0 {
            // 未提子：检查己方该组是否自杀（禁着点）
            let selfG = collectGroup(r, c, color)
            if !selfG.hasLiberty {
                board[r][c] = 0
                history.removeLast()
                tip = "禁着点：落子后无气且未提子"
                return
            }
        }
        if color == 1 { capB += captured } else { capW += captured }
        turn = color == 1 ? 2 : 1
        tip = "黑提 \(capB) · 白提 \(capW) · \(turn == 1 ? "黑" : "白")行"
    }

    func undo() {
        if let last = history.popLast() {
            board = last
            tip = "已悔棋"
        } else {
            tip = "无可悔之棋"
        }
    }
}

// MARK: - 围棋视图（三辩证：整体与局部 · 层次与平衡 · 生存与毁灭）
//
// 1. 整体与局部：死活由整块棋的气决定（整体），单点急所可逆转全局（局部）。
// 2. 层次与平衡：输入（点击）→ 状态（提子/禁着）→ 视图（Canvas 重绘）分明；
//    声明式 SwiftUI 与命令式 Canvas 互补平衡。
// 3. 生存与毁灭：有气则生、无气且未提子则被提（毁灭）；
//    工程上越界/判空即静默降级（生存），崩溃即毁灭。
public struct GoBoardView: View {
    @State private var model = GoState()

    public init() {}

    private func cellSize(_ size: CGSize) -> CGFloat {
        let pad: CGFloat = 16
        return (min(size.width, size.height) - pad * 2) / CGFloat(model.size - 1)
    }

    public var body: some View {
        VStack(spacing: 8) {
            HStack(spacing: 12) {
                Text(model.tip).accessibilityLabel(model.tip)
                Text("当前：\(model.turn == 1 ? "黑" : "白")")
            }

            GeometryReader { geo in
                let cell = cellSize(geo.size)
                let pad: CGFloat = 16
                Canvas { ctx, _ in
                    // 楸木盘
                    ctx.fill(Path(CGRect(origin: .zero, size: geo.size)),
                             with: .color(Color(red: 0.91, green: 0.73, blue: 0.45)))
                    // 网格线（交叉点）
                    var path = Path()
                    for i in 0..<model.size {
                        let p = pad + CGFloat(i) * cell
                        path.move(to: CGPoint(x: pad, y: p))
                        path.addLine(to: CGPoint(x: pad + CGFloat(model.size - 1) * cell, y: p))
                        path.move(to: CGPoint(x: p, y: pad))
                        path.addLine(to: CGPoint(x: p, y: pad + CGFloat(model.size - 1) * cell))
                    }
                    ctx.stroke(path, with: .color(.brown), lineWidth: 1)
                    // 棋子
                    for r in 0..<model.size {
                        for c in 0..<model.size {
                            let v = model.board[r][c]
                            if v == 0 { continue }
                            let cx = pad + CGFloat(c) * cell
                            let cy = pad + CGFloat(r) * cell
                            let ellipse = CGRect(x: cx - cell / 2, y: cy - cell / 2, width: cell, height: cell)
                            ctx.fill(Path(ellipse), with: .color(v == 1 ? .black : .white))
                            if v == 2 {
                                ctx.stroke(Path(ellipse), with: .color(.gray), lineWidth: 1)
                            }
                        }
                    }
                }
                .contentShape(Rectangle())
                .onTapGesture { loc in
                    // 换算最近交叉点（局部 → 整体落子）
                    let c = Int((loc.x - pad) / cell + 0.5)
                    let r = Int((loc.y - pad) / cell + 0.5)
                    if r >= 0 && r < model.size && c >= 0 && c < model.size {
                        model.place(r, c)
                    }
                }
            }
            .frame(width: 340, height: 340)

            HStack(spacing: 8) {
                Button("9 路") { model.initBoard(9) }
                Button("13 路") { model.initBoard(13) }
                Button("19 路") { model.initBoard(19) }
            }
            HStack(spacing: 8) {
                Button("悔棋") { model.undo() }
                Button("重开") { model.initBoard(model.size) }
            }
        }
        .padding()
        .accessibilityElement(children: .combine)
    }
}
