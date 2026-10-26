/*
 * 围棋构建块（道家经典文库 · 益智对弈）。
 *
 * 设计哲学 ——「整体与局部 · 层次与平衡 · 生存与毁灭」：
 *   1. 整体与局部：死活由「整块棋的气」决定（整体），但单点（急所/手筋，局部）可逆转全局；
 *      局部服从整体之气，局部又能破整体之势。
 *   2. 层次与平衡：布局（势）→ 中盘（战斗）→ 收官（地），外势与实空须权衡；
 *      工程上 UI 层 / 状态层 / 能力层分明，声明式 ArkUI 与命令式 Canvas 互补平衡。
 *   3. 生存与毁灭：棋子有气则生、无气且未提子则被提（毁灭）；
 *      工程上「错误静默降级」即生存，崩溃即毁灭——落子/触摸/绘制均做边界与判空保护。
 *
 * 规则范围（简化版，适老化手脑协调）：
 *   - 落子合法：交叉点空 + 非自杀（除非该手能提子）。
 *   - 提子（毁灭）：落子后对方任何「无气连通组」整组移除。
 *   - 禁着点：落子后己方该组无气且未提子，撤销（不计入历史）。
 *   - 暂不含：打劫禁着、眼位活棋判定（高级），数子为「地+子」简化中国规则。
 *
 * 状态管理：采用 NEXT V2（@ObservedV2 + @Trace）——棋盘状态集中于可观察类，
 *   视图自动追踪 @Trace 字段变更，作为「新块统一用 V2」的参考样板。
 *
 * 未接线构建块：默认不接入任何页面。
 */
import {
  Canvas,
  CanvasRenderingContext2D,
  Column,
  Row,
  Text,
  Button,
  FlexAlign,
  Color,
  TouchType,
  ObservedV2,
  Trace,
} from '@kit.ArkUI';

// 棋子状态：0 空 / 1 黑 / 2 白
const EMPTY: number = 0;
const BLACK: number = 1;
const WHITE: number = 2;

interface Snap {
  board: number[][];
  turn: number;
  capB: number;
  capW: number;
}

// V2 可观察状态：棋盘所有可变字段用 @Trace 标注，视图自动响应
@ObservedV2
class GoState {
  @Trace size: number = 19;            // 9 / 13 / 19 路自适应
  @Trace board: number[][] = [];
  @Trace turn: number = BLACK;         // 黑先
  @Trace capB: number = 0;            // 黑方提子数（毁灭计数）
  @Trace capW: number = 0;            // 白方提子数
  @Trace tip: string = '黑先行';

  initBoard(n: number): void {
    this.size = n;
    this.board = Array.from({ length: n }, () => new Array<number>(n).fill(EMPTY));
    this.turn = BLACK;
    this.capB = 0;
    this.capW = 0;
    this.tip = `${n} 路 · 黑先行`;
  }
}

@Component
export struct GoBoard {
  private ctx: CanvasRenderingContext2D = new CanvasRenderingContext2D();
  @State model: GoState = new GoState();
  private history: Snap[] = [];        // 悔棋快照栈（非 UI 状态，不追踪）

  aboutToAppear(): void {
    this.model.initBoard(this.model.size);
  }

  // 棋盘像素边长恒定约 340vp，格子随路数自适应
  private cellSize(): number {
    return Math.max(12, Math.floor(340 / this.model.size));
  }

  // 星位（天元 + 角星），按路数取基点
  private hoshi(): [number, number][] {
    const marks: number[] = this.model.size === 19 ? [3, 9, 15] : this.model.size === 13 ? [3, 6, 9] : [2, 4, 6];
    const pts: [number, number][] = [];
    for (const r of marks) {
      for (const c of marks) {
        pts.push([r, c]);
      }
    }
    return pts;
  }

  private inBounds(r: number, c: number): boolean {
    return r >= 0 && r < this.model.size && c >= 0 && c < this.model.size;
  }

  // 收集 (r,c) 同色连通组，并返回该组是否有「气」（相邻空点）
  private collectGroup(sr: number, sc: number, color: number): { group: [number, number][]; hasLiberty: boolean } {
    const group: [number, number][] = [];
    const seen: Set<string> = new Set<string>();
    const stack: [number, number][] = [[sr, sc]];
    seen.add(sr + ',' + sc);
    let hasLiberty: boolean = false;
    const dirs: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    while (stack.length > 0) {
      const cur: [number, number] = stack.pop() as [number, number];
      group.push(cur);
      for (const [dr, dc] of dirs) {
        const nr: number = cur[0] + dr;
        const nc: number = cur[1] + dc;
        if (!this.inBounds(nr, nc)) {
          continue;
        }
        const v: number = this.model.board[nr][nc];
        if (v === EMPTY) {
          hasLiberty = true;            // 生存：至少一口气
        } else if (v === color && !seen.has(nr + ',' + nc)) {
          seen.add(nr + ',' + nc);
          stack.push([nr, nc]);
        }
      }
    }
    return { group, hasLiberty };
  }

  // 落子后，提掉对方所有「无气连通组」（毁灭）
  private captureOpponent(r: number, c: number, color: number): number {
    const opp: number = color === BLACK ? WHITE : BLACK;
    const dirs: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    const handled: Set<string> = new Set<string>();
    let captured: number = 0;
    for (const [dr, dc] of dirs) {
      const nr: number = r + dr;
      const nc: number = c + dc;
      if (!this.inBounds(nr, nc) || this.model.board[nr][nc] !== opp) {
        continue;
      }
      const key: string = nr + ',' + nc;
      if (handled.has(key)) {
        continue;
      }
      const { group, hasLiberty } = this.collectGroup(nr, nc, opp);
      for (const [gr, gc] of group) {
        handled.add(gr + ',' + gc);
      }
      if (!hasLiberty) {
        for (const [gr, gc] of group) {
          this.model.board[gr][gc] = EMPTY;   // 毁灭：整组提掉
        }
        captured += group.length;
      }
    }
    return captured;
  }

  // 触摸落子：换算最近交叉点
  private onTap(x: number, y: number): void {
    const cell: number = this.cellSize();
    const col: number = Math.round((x - cell / 2) / cell);
    const row: number = Math.round((y - cell / 2) / cell);
    if (Number.isNaN(row) || Number.isNaN(col) || !this.inBounds(row, col)) {
      return;
    }
    this.place(row, col);
  }

  // 落子主流程（含禁着点判定）
  private place(r: number, c: number): void {
    if (this.model.board.length !== this.model.size || this.model.board[r][c] !== EMPTY) {
      return;                           // 占位或越界：静默忽略（生存式降级）
    }
    const color: number = this.model.turn;
    // 落子前快照（用于悔棋）
    this.history.push({
      board: this.model.board.map((row: number[]) => row.slice()),
      turn: this.model.turn,
      capB: this.model.capB,
      capW: this.model.capW,
    });
    if (this.history.length > 200) {
      this.history.shift();
    }

    this.model.board[r][c] = color;
    const captured: number = this.captureOpponent(r, c, color);
    if (captured === 0) {
      // 未提子：检查己方该组是否自杀
      const self = this.collectGroup(r, c, color);
      if (!self.hasLiberty) {
        this.model.board[r][c] = EMPTY;
        this.history.pop();             // 撤销：禁着点不入库
        this.model.tip = '禁着点：落子后无气且未提子';
        return;
      }
    }

    if (color === BLACK) {
      this.model.capB += captured;
    } else {
      this.model.capW += captured;
    }
    this.model.turn = color === BLACK ? WHITE : BLACK;
    this.model.tip = `黑提 ${this.model.capB} · 白提 ${this.model.capW} · ${this.model.turn === BLACK ? '黑' : '白'}行`;
    this.draw();
  }

  private undo(): void {
    const snap: Snap | undefined = this.history.pop();
    if (!snap) {
      this.model.tip = '无可悔之棋';
      return;
    }
    this.model.board = snap.board.map((row: number[]) => row.slice());
    this.model.turn = snap.turn;
    this.model.capB = snap.capB;
    this.model.capW = snap.capW;
    this.model.tip = '已悔棋';
    this.draw();
  }

  // 简化数子（中国规则：地+子）。空区仅与单色相邻则归该色；死子请先提净。
  private countScore(): void {
    let black: number = 0;
    let white: number = 0;
    for (let r = 0; r < this.model.size; r++) {
      for (let c = 0; c < this.model.size; c++) {
        if (this.model.board[r][c] === BLACK) {
          black++;
        } else if (this.model.board[r][c] === WHITE) {
          white++;
        }
      }
    }
    const seen: Set<string> = new Set<string>();
    const dirs: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    for (let r = 0; r < this.model.size; r++) {
      for (let c = 0; c < this.model.size; c++) {
        if (this.model.board[r][c] !== EMPTY || seen.has(r + ',' + c)) {
          continue;
        }
        // flood fill 一个空区，记录相邻颜色
        const region: [number, number][] = [];
        const stack: [number, number][] = [[r, c]];
        seen.add(r + ',' + c);
        let touchB: boolean = false;
        let touchW: boolean = false;
        while (stack.length > 0) {
          const cur: [number, number] = stack.pop() as [number, number];
          region.push(cur);
          for (const [dr, dc] of dirs) {
            const nr: number = cur[0] + dr;
            const nc: number = cur[1] + dc;
            if (!this.inBounds(nr, nc)) {
              continue;
            }
            const v: number = this.model.board[nr][nc];
            if (v === EMPTY && !seen.has(nr + ',' + nc)) {
              seen.add(nr + ',' + nc);
              stack.push([nr, nc]);
            } else if (v === BLACK) {
              touchB = true;
            } else if (v === WHITE) {
              touchW = true;
            }
          }
        }
        if (touchB && !touchW) {
          black += region.length;
        } else if (touchW && !touchB) {
          white += region.length;
        }
        // 双色相交（单官）不计
      }
    }
    this.model.tip = `数子：黑 ${black} · 白 ${white}（地+子；死子请先提净）`;
  }

  private setSize(n: number): void {
    this.model.initBoard(n);
    this.history = [];
    this.draw();
  }

  private draw(): void {
    const c: CanvasRenderingContext2D = this.ctx;
    if (!c) {
      return;                           // 安全降级：context 未就绪不绘制
    }
    const cell: number = this.cellSize();
    const span: number = this.model.size * cell;
    const pad: number = cell / 2;

    c.clearRect(0, 0, span, span);
    c.fillStyle = '#E8B974';            // 楸木盘
    c.fillRect(0, 0, span, span);

    // 网格线（交叉点）
    c.strokeStyle = '#5A3A1A';
    c.lineWidth = 1;
    c.beginPath();
    for (let i = 0; i < this.model.size; i++) {
      const p: number = pad + i * cell;
      c.moveTo(pad, p);
      c.lineTo(pad + (this.model.size - 1) * cell, p);
      c.moveTo(p, pad);
      c.lineTo(p, pad + (this.model.size - 1) * cell);
    }
    c.stroke();

    // 星位
    c.fillStyle = '#5A3A1A';
    const hr: number = Math.max(2, cell / 6);
    for (const [r, col] of this.hoshi()) {
      c.beginPath();
      c.arc(pad + col * cell, pad + r * cell, hr, 0, 2 * Math.PI);
      c.fill();
    }

    // 棋子
    const radius: number = cell / 2 - 2;
    for (let r = 0; r < this.model.size; r++) {
      for (let col = 0; col < this.model.size; col++) {
        const v: number = this.model.board[r][col];
        if (v === EMPTY) {
          continue;
        }
        const cx: number = pad + col * cell;
        const cy: number = pad + r * cell;
        c.beginPath();
        c.arc(cx, cy, radius, 0, 2 * Math.PI);
        c.fillStyle = v === BLACK ? '#1A1A1A' : '#F5F5F5';
        c.fill();
        if (v === WHITE) {
          c.strokeStyle = '#999999';
          c.lineWidth = 1;
          c.stroke();
        }
      }
    }
    c.invalidate();                     // 触发 Canvas 重绘
  }

  build() {
    Column({ space: 8 }) {
      Row({ space: 12 }) {
        Text(this.model.tip)
          .fontSize(20)
          .fontColor(Color.White)
          .accessibilityText(this.model.tip)
        Text(`当前：${this.model.turn === BLACK ? '黑' : '白'}`)
          .fontSize(20)
          .fontColor(Color.White)
          .accessibilityText(this.model.turn === BLACK ? '轮到黑方' : '轮到白方')
      }

      Canvas(this.ctx)
        .width(this.model.size * this.cellSize())
        .height(this.model.size * this.cellSize())
        .backgroundColor('#E8B974')
        .onReady(() => {
          this.draw()
        })
        .onTouch((e: TouchEvent) => {
          if (e.type === TouchType.Down) {
            const t = e.touches[0];
            if (t) {
              this.onTap(t.x, t.y);
            }
          }
        })
        .accessibilityText('围棋棋盘，点击交叉点落子')

      Row({ space: 8 }) {
        Button('9 路').fontSize(18).onClick(() => this.setSize(9)).accessibilityText('切换九路棋盘')
        Button('13 路').fontSize(18).onClick(() => this.setSize(13)).accessibilityText('切换十三路棋盘')
        Button('19 路').fontSize(18).onClick(() => this.setSize(19)).accessibilityText('切换十九路棋盘')
      }

      Row({ space: 8 }) {
        Button('悔棋').fontSize(18).onClick(() => this.undo()).accessibilityText('悔棋')
        Button('数子').fontSize(18).onClick(() => this.countScore()).accessibilityText('数子结算')
        Button('重开').fontSize(18).onClick(() => this.setSize(this.model.size)).accessibilityText('重新开始')
      }
    }
    .width('100%')
    .padding(10)
  }
}
