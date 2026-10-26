/*
 * 文本组件综合构建块（来自 Text 包 8 个演示，HarmonyOS Java API8 旧代）。
 * 旧代用 8 个独立 Ability 各演示一个 Text 属性；NEXT 用 ArkUI Text 声明式修饰符统一覆盖。
 * 旧代 XML 属性 → NEXT 修饰符映射（可直接取用）：
 *   text_color            → fontColor
 *   text_size             → fontSize
 *   text_alignment        → textAlign（TextAlign 枚举，支持位或组合）
 *   italic=true           → fontStyle(FontStyle.Italic)
 *   text_weight="700"     → fontWeight(FontWeight.Bold 或 FontWeight.700)
 *   text_font="serif"     → fontFamily('serif')
 *   max_text_lines + 省略 → maxLines(n) + textOverflow({ overflow: TextOverflow.Ellipsis })
 *   auto_font_size=true   → constraintSize 限宽 + maxFontSize/minFontSize 自适应（下例）
 * 适老化：大字号、高对比、可聚焦文本，读屏友好。未接线构建块（演示各属性）。
 */
import { Column, Text, TextOverflow, FontStyle, FontWeight, TextAlign, Alignment } from '@kit.ArkUI';

@Component
export struct TextView {
  private longText: string =
    '道可道非常道名可名非常名无名天地之始有名万物之母故常无欲以观其妙常有欲以观其徼此两者同出而异名同谓之玄玄之又玄众妙之门';

  build() {
    Column({ space: 14 }) {
      // 颜色 + 字号：旧代 text_color="#0000FF" text_size="40vp"
      Text('Hello World')
        .fontSize(40)
        .fontColor('#0000FF')
        .accessibilityText('蓝色大字示例')

      // 斜体 + 字重 + 字体：旧代 italic=true text_weight="700" text_font="serif"
      Text('Hello World')
        .fontSize(40)
        .fontStyle(FontStyle.Italic)
        .fontWeight(FontWeight.Bold)
        .fontFamily('serif')
        .accessibilityText('斜体加粗衬线字体示例')

      // 对齐：旧代 text_alignment="horizontal_center|bottom"，需固定宽高才能看出
      Text('Hello World')
        .fontSize(40)
        .fontStyle(FontStyle.Italic)
        .fontWeight(FontWeight.Bold)
        .fontFamily('serif')
        .width(300)
        .height(100)
        .textAlign(TextAlign.Center)
        .align(Alignment.Bottom)
        .accessibilityText('底部居中对齐示例')

      // 多行省略：旧代 multiple_lines=true max_text_lines="2" + 截断省略
      Text(this.longText)
        .width(300)
        .fontSize(28)
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .accessibilityText('两行省略长文本示例')

      // 自适应字号：旧代 auto_font_size=true，NEXT 用限宽 + 字号上下限自动缩放
      Text('Hello World')
        .width(300)
        .fontSize(40)
        .constraintSize({ maxWidth: 300 })
        .maxFontSize(40)
        .minFontSize(10)
        .accessibilityText('宽度受限自适应字号示例')
    }
    .width('100%')
    .padding(12)
  }
}
