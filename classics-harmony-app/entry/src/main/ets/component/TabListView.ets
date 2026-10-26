/*
 * 顶部选项卡构建块（来自 TabList，HarmonyOS Java API8 旧代）。
 * 旧代：TabList + TabList.Tab 运行时 new Tab()/addTab；setFixedMode(true) 固定不滚动；
 *   selectTab(tab1) 初始选中；addTabSelectedListener(onSelected/onUnselected/onReselected)
 *   三态回调；普通色/选中色/指示器色与高度、tab 长度、间距走 XML 属性。
 * NEXT 用 ArkUI Tabs + TabContent + 自定义 tabBar：
 *   BarMode.Fixed 对应 setFixedMode(true)；onChange 对应 addTabSelectedListener；
 *   选中色用 @Builder 内 this.currentIndex 判断，指示器用 .indicator(...) 对应旧代下划线。
 * 适老化：顶部频道 / 分类切换（大字号 tab，易点）。未接线构建块。
 */
import { Tabs, TabContent, Column, Text, Row, BarPosition, BarMode, FlexAlign } from '@kit.ArkUI';

@Component
export struct TabListView {
  @State currentIndex: number = 0;
  private tabs: string[] = ['Tab1', 'Tab2', 'Tab3', 'Tab4'];

  @Builder
  tabBuilder(name: string, index: number): void {
    Column() {
      Text(name)
        .fontSize(30)
        .fontColor(this.currentIndex === index ? '#FF0000' : '#999999')
    }
    .width(140)
    .height(36)
    .margin({ left: 24, right: 24 })
  }

  build() {
    Tabs({ barPosition: BarPosition.Start }) {
      ForEach(this.tabs, (name: string, index: number) => {
        TabContent() {
          Column() {
            Text(`内容区域：${name}`)
              .fontSize(24)
              .accessibilityText(`当前标签 ${name} 的内容区域`)
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
        }
        .tabBar(this.tabBuilder(name, index))
      }, (name: string, index: number) => `${index}`)
    }
    .barMode(BarMode.Fixed) // 对应旧代 setFixedMode(true)
    .barWidth('100%')
    .barHeight(36)
    .animationDuration(0)
    .indicator({ height: 2, color: '#FF0000' }) // 对应 selected_tab_indicator_color/height
    .onChange((idx: number) => {
      this.currentIndex = idx // 对应 addTabSelectedListener 三态回调
    })
    .width('100%')
    .height('100%')
  }
}
