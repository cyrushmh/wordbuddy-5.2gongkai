/**
 * 层叠布局构建块（来自 StackLayout，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.agp.components.StackLayout` 三层 Text 叠放（满屏蓝 / 300x100 青 / 80x80 居中）。
 * NEXT 用 ArkUI `Stack({ alignContent })` 子组件按顺序层叠；单元素定位用
 * .align(Alignment) / .position({ x, y })，背景色 backgroundColor。
 * 适老化：弹层 / 引导遮罩 / 角标，层叠结构一目了然。
 * 未接线构建块：默认不接入任何页面。
 */
import { Stack, Text, Alignment, TextAlign } from '@kit.ArkUI';

@Component
export struct StackLayoutView {
  build() {
    Stack({ alignContent: Alignment.Center }) {
      Text('Layer 1')
        .width('100%').height('100%')
        .textAlign(TextAlign.Bottom)
        .fontSize(24).fontColor('#FFFFFF')
        .backgroundColor('#3F56EA')
      Text('Layer 2')
        .width(300).height(100)
        .textAlign(TextAlign.Bottom)
        .fontSize(24).fontColor('#FFFFFF')
        .backgroundColor('#00AAEE')
      Text('Layer 3')
        .width(80).height(80)
        .textAlign(TextAlign.Center)
        .fontSize(24).fontColor('#FFFFFF')
        .backgroundColor('#00BFC9')
    }
    .width('100%').height('100%')
  }
}
