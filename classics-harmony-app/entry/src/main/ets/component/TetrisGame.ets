/*
 * 俄罗斯方块构建块（来自 Tetris，HarmonyOS Java API8 旧代）。
 * 旧代：Grid.java 硬编码 7 色方块共 4 格形态 + 旋转序列；Slice 用 int[15][10] 二维数组 +
 *       Canvas DrawTask 自绘 + TaskDispatcher.delayDispatch(750ms) 定时下移 +
 *       左右移动 / 旋转 / 消行 / 游戏结束判定。
 * NEXT 翻写：@State 网格 + 经典 tetromino 数据模型（4 格坐标 + 顺时针旋转）+ ArkUI Canvas 自绘
 *       （CanvasRenderingContext2D，同 ChartCanvas.ets）+ setInterval 定时下落（同 SliderPuzzle.ets）。
 * 概念：游戏主循环 / 碰撞检测 / 旋转（墙踢）/ 消行 / 计分 / 读屏播报。
 * 适老化：手脑协调小游戏（防认知退化）；格子蓝底白字高对比、胜利/结束读屏提示。
 * 未接线构建块：默认不接入任何页面。
 */
import { Canvas, CanvasRenderingContext2D, Column, Row, Text, Button, FlexAlign, Color } from '@kit.ArkUI';

const ROWS: number = 15;
const COLS: number = 10;
const CELL: number = 20;

type Shape = [number, number][];

interface Piece {
  cells: Shape;
  color: number;
}

// 7 种方块（4 格坐标 [行,列]；颜色按旧代 1-7 映射）
const PIECES: Piece[] = [
  { cells: [[0, 0], [0, 1], [0, 2], [0, 3]], color: 3 }, // I 青
  { cells: [[0, 0], [0, 1], [1, 0], [1, 1]], color: 7 }, // O 黄
  { cells: [[0, 0], [0, 1], [0, 2], [1, 1]], color: 4 }, // T 品红
  { cells: [[0, 1], [0, 2], [1, 0], [1, 1]], color: 2 }, // S 绿
  { cells: [[0, 0], [0, 1], [1, 1], [1, 2]], color: 5 }, // Z 蓝
  { cells: [[0, 0], [1, 0], [1, 1], [1, 2]], color: 1 }, // J 红
  { cells: [[0, 2], [1, 0], [1, 1], [1, 2]], color: 6 }, // L 白
];

// 0 为空（灰底）
const COLOR_MAP: string[] = [
  '#696969',
  '#FF0000', '#00AA00', '#00FFFF', '#FF00FF',
  '#0000FF', '#FFFFFF', '#FFFF00',
];

@Component
export struct TetrisGame {
  private ctx: CanvasRenderingContext2D = new CanvasRenderingContext2D();
  private timer: number = -1;
  @State grid: number[][] = [];
  @State score: number = 0;
  @State tip: string = 'Start!';
  @State running: boolean = false;

  private cur: Piece = PIECES[0];
  private curRow: number = 0;
  private curCol: number = 0;

  aboutToAppear(): void {
    this.resetGrid();
  }

  aboutToDisappear(): void {
    this.stopTimer();
  }

  private resetGrid(): void {
    this.grid = Array.from({ length: ROWS }, () => new Array(COLS).fill(0));
  }

  private spawn(): void {
    this.cur = PIECES[Math.floor(Math.random() * PIECES.length)];
    this.curRow = 0;
    this.curCol = Math.floor((COLS - 4) / 2);
    if (!this.canPlace(this.cur.cells, this.curRow, this.curCol)) {
      this.tip = 'Game Over!';
      this.running = false;
      this.stopTimer();
    }
  }

  // 碰撞检测：所有格是否在界内且目标为空
  private canPlace(cells: Shape, row: number, col: number): boolean {
    for (const [r, c] of cells) {
      const rr = row + r;
      const cc = col + c;
      if (cc < 0 || cc >= COLS || rr >= ROWS) {
        return false;
      }
      if (rr >= 0 && this.grid[rr][cc] !== 0) {
        return false;
      }
    }
    return true;
  }

  // 顺时针旋转：newCell = [-c, r]，再平移回非负
  private rotate(cells: Shape): Shape {
    const rotated: Shape = cells.map(([r, c]) => [-c, r] as [number, number]);
    const minR = Math.min(...rotated.map((p) => p[0]));
    const minC = Math.min(...rotated.map((p) => p[1]));
    return rotated.map(([r, c]) => [r - minR, c - minC] as [number, number]);
  }

  // 把当前方块写回 / 清除 grid
  private stamp(on: boolean): void {
    for (const [r, c] of this.cur.cells) {
      const rr = this.curRow + r;
      const cc = this.curCol + c;
      if (rr >= 0 && rr < ROWS && cc >= 0 && cc < COLS) {
        this.grid[rr][cc] = on ? this.cur.color : 0;
      }
    }
  }

  private lockAndNext(): void {
    this.stamp(true);
    this.eliminate();
    this.spawn();
  }

  // 满行消除：上方行整体下移，分数 +1
  private eliminate(): void {
    for (let r = ROWS - 1; r >= 0; r--) {
      if (this.grid[r].every((v: number) => v !== 0)) {
        this.score++;
        this.grid.splice(r, 1);
        this.grid.unshift(new Array(COLS).fill(0));
        r++; // 重新检查被顶下的同一行
      }
    }
  }

  private down(): void {
    this.stamp(false);
    if (this.canPlace(this.cur.cells, this.curRow + 1, this.curCol)) {
      this.curRow++;
      this.stamp(true);
    } else {
      this.stamp(true);
      this.lockAndNext();
    }
    this.draw();
  }

  private move(dir: number): void {
    this.stamp(false);
    if (this.canPlace(this.cur.cells, this.curRow, this.curCol + dir)) {
      this.curCol += dir;
    }
    this.stamp(true);
    this.draw();
  }

  private shift(): void {
    this.stamp(false);
    const rotated: Shape = this.rotate(this.cur.cells);
    // 墙踢：原位不行试左移一格
    if (this.canPlace(rotated, this.curRow, this.curCol)) {
      this.cur.cells = rotated;
    } else if (this.canPlace(rotated, this.curRow, this.curCol - 1)) {
      this.cur.cells = rotated;
      this.curCol -= 1;
    }
    this.stamp(true);
    this.draw();
  }

  private draw(): void {
    const c: CanvasRenderingContext2D = this.ctx;
    c.clearRect(0, 0, COLS * CELL, ROWS * CELL);
    for (let r = 0; r < ROWS; r++) {
      for (let col = 0; col < COLS; col++) {
        c.fillStyle = COLOR_MAP[this.grid[r][col]];
        c.fillRect(col * CELL, r * CELL, CELL - 1, CELL - 1);
      }
    }
  }

  private startGame(): void {
    this.resetGrid();
    this.score = 0;
    this.tip = 'Start!';
    this.running = true;
    this.spawn();
    this.draw();
    this.startTimer();
  }

  private startTimer(): void {
    this.stopTimer();
    this.timer = setInterval(() => {
      if (this.running) {
        this.down();
      }
    }, 750) as unknown as number; // 对应旧代 delayDispatch(750)
  }

  private stopTimer(): void {
    if (this.timer !== -1) {
      clearInterval(this.timer);
      this.timer = -1;
    }
  }

  build() {
    Column({ space: 10 }) {
      Row({ space: 16 }) {
        Text(`分数 ${this.score}`)
          .fontSize(24)
          .fontColor(Color.White)
          .accessibilityText(`当前分数 ${this.score}`)
        Text(this.tip)
          .fontSize(24)
          .fontColor(Color.White)
          .accessibilityText(this.tip)
      }

      Canvas(this.ctx)
        .width(COLS * CELL)
        .height(ROWS * CELL)
        .backgroundColor('#000000')
        .onReady(() => {
          this.startGame()
        })

      Row({ space: 12 }) {
        Button('←')
          .fontSize(30)
          .onClick(() => {
            if (this.running) {
              this.move(-1)
            }
          })
          .accessibilityText('左移')
        Button('→')
          .fontSize(30)
          .onClick(() => {
            if (this.running) {
              this.move(1)
            }
          })
          .accessibilityText('右移')
        Button('∽')
          .fontSize(30)
          .onClick(() => {
            if (this.running) {
              this.shift()
            }
          })
          .accessibilityText('旋转')
        Button('R')
          .fontSize(30)
          .onClick(() => {
            this.startGame()
          })
          .accessibilityText('重新开始')
      }
    }
    .width('100%')
    .padding(10)
  }
}
