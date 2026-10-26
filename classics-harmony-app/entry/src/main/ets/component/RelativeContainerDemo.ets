/*
 * RelativeContainerDemo.ets —— 相对定位浮层（构建块，翻 NEXT ArkUI RelativeContainer）
 * 来源：Batch24(中断补) DependentLayout（Java API8：DependentLayout 相对依赖定位）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「相对容器 + 锚点规则」概念做成未接线组件块。
 * NEXT 对应：ArkUI RelativeContainer + .alignRules（DependentLayout 的「相对另一组件定位」在 NEXT 即 RelativeContainer）。
 * 用途：在书页图（ZoomImage）上叠加书签角标 / 批注气泡 / 朗读进度点——Column/Row 做不到「浮在图上某处」，
 *        RelativeContainer 用锚点规则把浮层钉在容器角落或某个组件旁。
 * 默认不接线：纯 UI 原语，无需权限。
 */
@Component
export struct RelativeContainerDemo {
  @State tagText: string = '已读到此处';

  build() {
    // 接线：把本容器叠在 ZoomImage 之上（Stack 包裹），用 alignRules 钉浮层位置。
    RelativeContainer() {
      Text(this.tagText)
        .id('bookmarkTag')
        .fontSize(12)
        .padding({ left: 6, right: 6, top: 2, bottom: 2 })
        .backgroundColor('#CC3A5FCD')
        .fontColor('#FFFFFF')
        .alignRules({
          top: { anchor: '__container__', align: VerticalAlign.Top },
          right: { anchor: '__container__', align: HorizontalAlign.End }
        })
    }
    .width('100%')
    .height(220)
  }
}

/*
 * 接线伪代码（书页批注浮层）：
 *   Stack() {
 *     ZoomImage({ src: this.pageUri })          // Batch18 看图组件
 *     RelativeContainerDemo({ tagText: '第3章·批注2' })   // 浮层钉在右上角
 *   }
 * 旧代对照：原 DependentLayout 用「相对父/相对兄弟」定位子组件；NEXT 用 RelativeContainer + alignRules
 *          （anchor 取 '__container__' 或某组件 .id），等价表达依赖关系，且支持同时四向锚定。
 * 注：Batch24 另三个 DirectionalLayout 变体（DirectionalLayout / WithJava / WithXml）均为 Column/Row + layoutWeight
 *     的等价表达，应用已大量使用，不再单列构建块，映射见分析笔记。
 */
