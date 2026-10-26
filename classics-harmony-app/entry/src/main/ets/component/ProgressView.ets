/**
 * 进度条构建块（来自 ProgressBar，HarmonyOS Java API8 旧代）。
 *
 * 旧代 ProgressBar 用 max/min/progress/orientation/progress_hint_text；
 * NEXT 用 ArkUI Progress({ value, total, type })，type 控形态（Linear/Ring/ScaleRing/Eclipse/Capsule），
 * 提示文字用独立 Text 叠加（NEXT 无内置 hint 文本）。
 * 适老化：下载 / 听书进度 / 缓冲进度，配大字号百分比，色块高对比。
 *
 * 未接线构建块：默认不接入任何页面。
 */
import { Progress, ProgressType, Column, Text } from '@kit.ArkUI';

@Component
export struct ProgressView {
  @Prop value: number = 0;
  @Prop total: number = 100;
  @Prop type: ProgressType = ProgressType.Linear;
  @Prop showPercent: boolean = true;
  @Prop barHeight: number = 24;   // 线性条高度；环形时作直径参考

  build() {
    Column() {
      Progress({ value: this.value, total: this.total, type: this.type })
        .width(this.type === ProgressType.Linear ? '100%' : this.barHeight * 3)
        .height(this.type === ProgressType.Linear ? this.barHeight : this.barHeight * 3)
        .color('#1A73E8')
        .backgroundColor('#E0E0E0')
      if (this.showPercent) {
        Text(`${Math.round((this.value / this.total) * 100)}%`)
          .fontSize(16)
          .fontColor('#333')
          .margin({ top: 6 })
      }
    }
  }
}
