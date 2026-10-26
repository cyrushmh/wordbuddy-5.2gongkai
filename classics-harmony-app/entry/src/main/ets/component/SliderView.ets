/**
 * 滑块构建块（来自 Slider，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.agp.components.Slider`：orientation / progress_color / progress_width，水平 + 垂直两个。
 * NEXT 用 ArkUI `Slider({ value, min, max, style, direction })`，
 * direction: Axis.Horizontal / Axis.Vertical 对应旧 orientation；
 * 颜色 trackColor / selectedColor，粗细 trackThickness。
 * 适老化：亮度 / 音量 / 字号滑杆，配大点区与实时数值显示，拖拽不误触。
 *
 * 未接线构建块：默认不接入任何页面。
 */
import { Slider, SliderStyle, Axis, Column, Text } from '@kit.ArkUI';

@Component
export struct SliderView {
  @Prop value: number = 50;
  @Prop min: number = 0;
  @Prop max: number = 100;
  @Prop vertical: boolean = false;
  @Prop label: string = '';
  private onChange: (v: number) => void = () => {};

  build() {
    Column({ space: 8 }) {
      if (this.label) {
        Text(`${this.label}：${this.value}`).fontSize(18).fontColor('#333')
      }
      Slider({
        value: this.value,
        min: this.min,
        max: this.max,
        style: SliderStyle.OutSet,
        direction: this.vertical ? Axis.Vertical : Axis.Horizontal
      })
        .blockSize(28)
        .trackThickness(12)
        .trackColor('#E0E0E0')
        .selectedColor('#1A73E8')
        .onChange((v: number) => {
          this.value = v;
          this.onChange(v);
        })
    }
  }
}
