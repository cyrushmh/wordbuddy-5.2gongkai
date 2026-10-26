/**
 * 滚动容器构建块（来自 ScrollView，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.agp.components.ScrollView` 包一条多行 Text（italic / serif / 蓝色）。
 * NEXT 用 ArkUI `Scroll()` 包裹内容；长文用 `Text` 配 fontStyle / fontFamily / lineHeight，
 * 适老化放大字号与行距，竖向可滚。
 * 未接线构建块：默认不接入任何页面。
 */
import { Scroll, Column, Text, ScrollDirection, BarState, FontStyle } from '@kit.ArkUI';

@Component
export struct ScrollView {
  @Prop content: string = '';

  build() {
    Scroll() {
      Column() {
        Text(this.content)
          .fontSize(20)
          .lineHeight(32)
          .fontColor('#0000FF')
          .fontStyle(FontStyle.Italic)
          .fontFamily('serif')
          .width('100%')
      }.padding(16)
    }
    .scrollable(ScrollDirection.Vertical)
    .scrollBar(BarState.Auto)
    .width('100%')
    .height('100%')
  }
}
