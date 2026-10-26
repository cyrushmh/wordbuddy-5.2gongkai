/**
 * 自定义检索输入框（来自 ArkUIExperience 的 Input 组件）。
 *
 * 与首页现有 TextInput 检索框的区别：把「输入框 + 确定按钮」封装成可复用组件，
 * 用 @Link 双向绑定外部 keyword，点确定触发 confirm 回调。
 *
 * 接线（待你定）：在 Index.ets 把
 *   TextInput({ placeholder: '搜索书名 / 作者', text: this.keyword })...
 * 替换为 <SearchInput({ keyword: $keyword }) />，即可获得带按钮的检索框；
 * 若需回车即搜，可在 confirm 里接 this.filteredBooks 已自动随 keyword 变化。
 */
@Component
export struct SearchInput {
  @Link keyword: string;
  confirm?: () => void;

  build() {
    Row() {
      TextInput({ placeholder: '搜索书名 / 作者', text: this.keyword })
        .onChange((v: string) => {
          this.keyword = v;
        })
        .layoutWeight(1)
        .height(40)
        .fontSize(15)
        .backgroundColor('#ffffff')
        .borderRadius(8)
        .accessibilityDescription('输入书名或作者进行搜索');
      Button('搜索', { type: ButtonType.Normal, stateEffect: true })
        .height(36)
        .fontSize(14)
        .margin({ left: 8 })
        .backgroundColor('#aa3333')
        .accessibilityText('执行搜索')
        .onClick(() => {
          if (this.confirm) {
            this.confirm();
          }
        });
    }
    .width('90%')
    .padding(4)
    .backgroundColor('#f0f0f0')
    .borderRadius(10);
  }
}
