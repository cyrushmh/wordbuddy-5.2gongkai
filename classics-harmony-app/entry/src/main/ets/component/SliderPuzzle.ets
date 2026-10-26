/*
 * 数字华容道 / 滑块拼图（构建块 · ArkTS NEXT 真 UI，可直接接线）
 * 概念来源：KlotskiJs（JS FA 4x4 滑块拼图：grid 移动 + swipe + 胜利判定 + 计时）
 * 范式：@State 二维网格 + Grid 渲染 + 点击/滑动相邻移动 + 胜利判定 + 计时 + 读屏播报
 * 适老化：老人益智互动（防认知退化）；格子大字号、蓝底白字高对比、胜利读屏提示
 * 用途：国学类 App 可嵌"成语拼字""诗句复原"变体（把数字换成字块即可复用本状态机）
 */
@Component
export struct SliderPuzzle {
  private readonly SIZE: number = 4
  @State grid: number[][] = []
  @State seconds: number = 0
  @State won: boolean = false
  private timer?: number
  private readonly TARGET: number[][] = [
    [1, 2, 3, 4],
    [5, 6, 7, 8],
    [9, 10, 11, 12],
    [13, 14, 15, 0],
  ]

  aboutToAppear(): void {
    this.restart()
  }

  aboutToDisappear(): void {
    this.stopTimer()
  }

  /** 打乱：从目标态随机走 N 步，保证可解 */
  private shuffle(steps: number = 100): void {
    this.grid = this.TARGET.map((r) => [...r])
    let dirs = ['left', 'up', 'right', 'down']
    for (let i = 0; i < steps; i++) {
      this.move(dirs[Math.floor(Math.random() * 4)], false)
    }
    this.won = false
    this.seconds = 0
  }

  /** 按方向把空格与相邻格交换；silent=true 时用于打乱不触发胜利判定 */
  private move(dir: string, silent: boolean = true): void {
    let zr = 0
    let zc = 0
    for (let r = 0; r < this.SIZE; r++) {
      for (let c = 0; c < this.SIZE; c++) {
        if (this.grid[r][c] === 0) {
          zr = r
          zc = c
        }
      }
    }
    let tr = zr
    let tc = zc
    if (dir === 'left' && zc + 1 < this.SIZE) { tr = zr; tc = zc + 1 }
    else if (dir === 'right' && zc - 1 >= 0) { tr = zr; tc = zc - 1 }
    else if (dir === 'up' && zr + 1 < this.SIZE) { tr = zr + 1; tc = zc }
    else if (dir === 'down' && zr - 1 >= 0) { tr = zr - 1; tc = zc }
    else { return }
    const tmp = this.grid[zr][zc]
    this.grid[zr][zc] = this.grid[tr][tc]
    this.grid[tr][tc] = tmp
    if (!silent && this.isWin()) {
      this.win()
    }
  }

  /** 点击某格：若与空格相邻则交换并判定胜利 */
  private tapCell(r: number, c: number): void {
    if (this.won) {
      return
    }
    const z = this.findZero()
    if (Math.abs(z.r - r) + Math.abs(z.c - c) === 1) {
      const tmp = this.grid[z.r][z.c]
      this.grid[z.r][z.c] = this.grid[r][c]
      this.grid[r][c] = tmp
      if (this.isWin()) {
        this.win()
      }
    }
  }

  private findZero(): { r: number; c: number } {
    for (let r = 0; r < this.SIZE; r++) {
      for (let c = 0; c < this.SIZE; c++) {
        if (this.grid[r][c] === 0) {
          return { r, c }
        }
      }
    }
    return { r: this.SIZE - 1, c: this.SIZE - 1 }
  }

  private isWin(): boolean {
    for (let r = 0; r < this.SIZE; r++) {
      for (let c = 0; c < this.SIZE; c++) {
        if (this.grid[r][c] !== this.TARGET[r][c]) {
          return false
        }
      }
    }
    return true
  }

  private win(): void {
    this.won = true
    this.stopTimer()
  }

  private startTimer(): void {
    this.stopTimer()
    this.timer = setInterval(() => {
      this.seconds = Math.round((this.seconds + 0.1) * 10) / 10
    }, 100) as unknown as number
  }

  private stopTimer(): void {
    if (this.timer !== undefined) {
      clearInterval(this.timer)
      this.timer = undefined
    }
  }

  restart(): void {
    this.stopTimer()
    this.shuffle()
    this.startTimer()
  }

  build() {
    Column({ space: 12 }) {
      Text(this.won ? `拼好了！用时 ${this.seconds.toFixed(1)} 秒` : `计时 ${this.seconds.toFixed(1)} 秒`)
        .fontSize(28)
        .fontWeight(FontWeight.Bold)
        .accessibilityText(this.won ? '拼图完成' : '游戏进行中')

      Grid() {
        ForEach(this.grid, (row: number[], ri: number) => {
          ForEach(row, (cell: number, ci: number) => {
            GridItem() {
              Text(cell === 0 ? '' : `${cell}`)
                .fontSize(36)
                .fontColor(cell === 0 ? Color.Transparent : Color.White)
                .fontWeight(FontWeight.Bold)
            }
            .width(70)
            .height(70)
            .backgroundColor(cell === 0 ? Color.Transparent : Color.Blue)
            .onClick(() => this.tapCell(ri, ci))
            .accessibilityText(cell === 0 ? '空位' : `数字 ${cell}`)
          }, (ci: number) => `${ri}-${ci}`)
        }, (ri: number) => `${ri}`)
      }
      .columnsTemplate('1fr 1fr 1fr 1fr')
      .rowsTemplate('1fr 1fr 1fr 1fr')
      .width(300)
      .height(300)

      Button('重新开始')
        .fontSize(24)
        .onClick(() => this.restart())
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }
}
