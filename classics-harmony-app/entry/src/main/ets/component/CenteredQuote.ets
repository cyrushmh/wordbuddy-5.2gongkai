/*
 * 整屏居中题词卡（构建块 · ArkTS NEXT 真 UI 范式，可直接接线）
 * 概念来源：FatherDay（旧代 .ets，Flex 居中 + 大字号祝福语 Text）
 * 范式：Flex 垂直水平居中 + 大号加粗 Text + 行高宽松 + 行内居中
 * 适老化：默认字号 36、可上调至 48+；整屏居中便于长辈一眼读完；读屏播报全句
 * 用途：扉页题词 / 每日一句 / 读书寄语 / 节日祝福（如父亲节）
 */
@Component
export struct CenteredQuote {
  @Prop text: string = ''
  @Prop fontSize: number = 36
  private onTap?: () => void

  build() {
    Flex({
      direction: FlexDirection.Column,
      alignItems: ItemAlign.Center,
      justifyContent: FlexAlign.Center
    }) {
      Text(this.text)
        .fontSize(this.fontSize)
        .fontWeight(FontWeight.Bold)
        .textAlign(TextAlign.Center)
        .lineHeight(this.fontSize * 1.5)
        .maxLines(0)
        .accessibilityText(this.text)
    }
    .width('100%')
    .height('100%')
    .onClick(() => this.onTap?.())
  }
}
