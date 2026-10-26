/**
 * 环形进度构建块（来自 RoundProgressBar，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.agp.components.RoundProgressBar`：progress / progress_width / progress_color，
 * 还支持 start_angle / max_angle / progress_hint_text（起止弧度 + 中央提示文字）。
 * NEXT 用 ArkUI `Progress({ value, total, type: ProgressType.Ring })`，
 * 粗细 .style({ strokeWidth })；旧 start_angle / max_angle 在 NEXT 无直接公开参数，
 * 可用 .rotate() 旋转起点近似（max_angle 需 Canvas 自绘，本块未覆盖）。
 * 中央提示文字用独立 Text 叠加（NEXT 无内建 hint）。
 * 适老化：锻炼 / 服药完成度环形，大字号百分比居中。
 * 未接线构建块：默认不接入任何页面。
 */
import { Progress, ProgressType, Column, Stack, Text } from '@kit.ArkUI';

@Component
export struct RingProgressView {
  @Prop value: number = 20;
  @Prop total: number = 100;
  @Prop strokeWidth: number = 30;
  @Prop color: string = '#47CC47';
  @Prop startAngle: number = 0;      // 旧 start_angle：NEXT 用 .rotate 近似
  @Prop hintText: string = '';

  build() {
    Column() {
      Stack({ alignContent: Alignment.Center }) {
        Progress({ value: this.value, total: this.total, type: ProgressType.Ring })
          .width(300)
          .height(300)
          .style({ strokeWidth: this.strokeWidth, enableSmoothEffect: true })
          .color(this.color)
          .backgroundColor('#E0E0E0')
          .rotate({ angle: this.startAngle, centerX: '50%', centerY: '50%' })
        if (this.hintText) {
          Text(this.hintText).fontSize(18).fontColor('#007DFF')
        } else {
          Text(`${Math.round((this.value / this.total) * 100)}%`)
            .fontSize(28).fontColor('#333')
        }
      }
    }
  }
}
