/**
 * 底部 Tab 导航构建块（来自 ArkUIShopping 的 HomeBottom + @Provide/@Consume 范式，
 * 并升级为 ArkUI 推荐的 Tabs(BarPosition.End) 写法）。
 *
 * 把主页切成「书架 / 检索 / 书签 / 我的」四个常驻入口，取代当前 Index 单页堆叠，
 * 也更契合长辈/视障用户的「一眼看到分类、底部大按钮」心智（系统使用无障碍）。
 *
 * 默认不接线：当前 Index 已用单页 Scroll 承载（书卡+检索+书签+组网卡），重构主页
 * 结构改动面大、且无 SDK 验证，故先沉淀为本块，待你定。
 *
 * 接线（待你定）：
 *   1) 把 Index 根的 Scroll 换成 `Tabs({ barPosition: BarPosition.End })`，
 *      每个 TabContent 放一个分栏（书架 / 检索 / 书签 / 我的）。
 *   2) 分栏间需要共享「当前选中的书/检索词」等状态时，用 @Provide/@Consume 跨组件传递
 *      （如 Shopping 的 currentPage），比 @StorageLink 更轻、仅限组件树内。
 *   3) 底部标签加 accessibilityText + 放大点击区（tapH 44+），呼应无障碍规范。
 *
 * 适老化要点：标签字号建议 ≥16，选中态用高对比色（非纯灰），图标+文字双标识。
 */
import { Tabs, TabContent, Column, Text, Image, TabBarPosition, BarPosition } from '@kit.ArkUI';

/** 单个底部标签的静态配置。 */
export interface TabItem {
  key: string;
  label: string;
  icon?: Resource;       // 未选中图标
  iconSelected?: Resource; // 选中图标（缺省回退到 icon）
}

/**
 * 底部 Tab 栏（自定义 Row 写法，对应 Shopping 的 HomeBottom）。
 * 用 @Consume 接收来自父级 @Provide 的当前页，点击切换并回写。
 */
@Component
export struct BottomTabBar {
  @Consume currentPage: number;
  @Prop items: TabItem[] = [];
  @Prop selectedColor: string = '#B8860B'; // 道观金，高对比
  @Prop idleColor: string = '#888888';

  build() {
    Row() {
      ForEach(this.items, (item: TabItem, idx: number) => {
        Column() {
          if (item.icon) {
            Image(idx === this.currentPage ? (item.iconSelected ?? item.icon) : item.icon)
              .width(26).height(26)
              .margin({ bottom: 2 });
          }
          Text(item.label)
            .fontSize(14)
            .fontColor(idx === this.currentPage ? this.selectedColor : this.idleColor);
        }
        .layoutWeight(1)
        .height(56)
        .accessibilityText(item.label)
        .onClick(() => { this.currentPage = idx; });
      }, (item: TabItem) => item.key);
    }
    .width('100%')
    .height(56)
    .backgroundColor('#FFFFFF')
    .border({ width: { top: 1 }, color: '#EEEEEE' });
  }
}

/**
 * 推荐写法：直接用 Tabs(BarPosition.End) 承载四栏，省去手动维护 currentPage。
 * 内容区域由各分栏自行提供（此处留 @Builder 占位）。
 */
@Component
export struct MainTabs {
  @BuilderParam shelf: () => void = () => {};
  @BuilderParam search: () => void = () => {};
  @BuilderParam bookmark: () => void = () => {};
  @BuilderParam mine: () => void = () => {};

  @State current: number = 0;

  build() {
    Tabs({ barPosition: BarPosition.End }) {
      TabContent() { this.shelf(); }.tabBar('书架')
      TabContent() { this.search(); }.tabBar('检索')
      TabContent() { this.bookmark(); }.tabBar('书签')
      TabContent() { this.mine(); }.tabBar('我的')
    }
    .barWidth('100%')
    .barHeight(56)
    .onChange((idx: number) => { this.current = idx; });
  }
}
