/*
 * ChartCanvas.ets —— Canvas 自绘图表（构建块，ArkUI Canvas，未接线）
 * 来源：Batch30 JsChartSwitch（JS FA 旧代：内置 <chart> 组件画 line/bar/gauge + 开关切换 动态/静态 + setInterval 刷新）
 * 代际：JS FA 旧代；NEXT 无内置 <chart>，改为 ArkUI Canvas + CanvasRenderingContext2D 自绘
 *       （gauge 量规用 NEXT 原生 @ohos.arkui.advanced.Gauge，本块聚焦 line/bar 自绘）。
 * 概念：折线图/柱状图自绘 + 类型切换 + 动态刷新（setInterval 随机生成点）+ 适老化读屏播报。
 * NEXT 对应：import { Canvas, CanvasRenderingContext2D } from '@kit.ArkUI'（Canvas 组件 + 2D 上下文）
 * 用途：读书数据可视化——如「每日阅读时长趋势（折线）/ 各典籍篇幅占比（柱状）」；离线、零三方库、可构建。
 * 权限：无；默认未接线（@Component 封装，可直接塞进统计页）。
 */
import { Canvas, CanvasRenderingContext2D } from '@kit.ArkUI';

type ChartType = 'line' | 'bar';

@Component
export struct ChartCanvas {
  private ctx: CanvasRenderingContext2D = new CanvasRenderingContext2D();
  private timer: number = -1;
  @State chartType: ChartType = 'line';
  @State dynamic: boolean = false;
  @State lineData: number[] = [20, 60, 35, 80, 50];
  @State barData: number[] = [40, 75, 30, 90, 55];

  aboutToAppear(): void {
    this.draw();
  }

  aboutToDisappear(): void {
    this.stopDynamic();
  }

  private tick(): void {
    const rnd = (): number => Math.floor(Math.random() * 99 + 1);
    this.lineData = this.lineData.map(() => rnd());
    this.barData = this.barData.map(() => rnd());
    this.draw();
  }

  private startDynamic(): void {
    if (this.timer !== -1) {
      return;
    }
    this.timer = setInterval(() => this.tick(), 1000);
  }

  private stopDynamic(): void {
    if (this.timer !== -1) {
      clearInterval(this.timer);
      this.timer = -1;
    }
  }

  private draw(): void {
    const c: CanvasRenderingContext2D = this.ctx;
    c.clearRect(0, 0, 300, 200);
    // 坐标轴
    c.strokeStyle = '#888888';
    c.beginPath();
    c.moveTo(30, 10);
    c.lineTo(30, 180);
    c.lineTo(290, 180);
    c.stroke();
    if (this.chartType === 'line') {
      c.strokeStyle = '#17A98E';
      c.lineWidth = 2;
      c.beginPath();
      this.lineData.forEach((v: number, i: number) => {
        const x = 30 + i * 60;
        const y = 180 - (v / 100) * 160;
        if (i === 0) {
          c.moveTo(x, y);
        } else {
          c.lineTo(x, y);
        }
      });
      c.stroke();
    } else {
      const colors: string[] = ['#CF0A2C', '#8477DF', '#17A98E', '#0A7CDC', '#E08A1E'];
      this.barData.forEach((v: number, i: number) => {
        const h: number = (v / 100) * 160;
        c.fillStyle = colors[i % colors.length];
        c.fillRect(36 + i * 50, 180 - h, 36, h);
      });
    }
  }

  build() {
    Column({ space: 12 }) {
      Row({ space: 12 }) {
        Toggle({ type: ToggleType.Switch, isOn: this.dynamic })
          .onChange((on: boolean) => {
            this.dynamic = on;
            if (on) {
              this.startDynamic();
            } else {
              this.stopDynamic();
            }
          })
          .accessibilityText('动态刷新开关')
        Text(this.dynamic ? '动态' : '静态')
          .fontSize(16)
          .accessibilityText(this.dynamic ? '当前动态刷新' : '当前静态')
      }
      Row({ space: 12 }) {
        Button('折线')
          .onClick(() => {
            this.chartType = 'line';
            this.draw();
          })
          .accessibilityText('切换到折线图')
        Button('柱状')
          .onClick(() => {
            this.chartType = 'bar';
            this.draw();
          })
          .accessibilityText('切换到柱状图')
      }
      Canvas(this.ctx)
        .width(300)
        .height(200)
        .backgroundColor('#FFFFFF')
        .onReady(() => this.draw())
    }
    .padding(12)
  }
}
