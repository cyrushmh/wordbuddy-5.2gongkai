/**
 * 多选勾选行构建块（来自 ArkUIShopping 的 ShopCartListItem：
 * Toggle(ToggleType.Checkbox) + @Consume 跨组件累计状态）。
 *
 * 用途：书签批量管理 / 「加入书架」多选。勾选把 id 加入共享的选中集合，
 * 底部可一键「删除选中 / 同步选中 / 加入书架」，直接服务组网无障碍（批量同步多设备）。
 *
 * 默认不接线：当前书签在 Index 内只读展示，无批量操作入口，故先沉淀为本块，待你定。
 *
 * 接线（待你定）：
 *   1) 在书签列表页父级 `@Provide selectedIds: Set<string> = new Set()`；
 *   2) 每个书签行用本 CheckableItem，@Consume selectedIds，勾选时 add/delete；
 *   3) 底部汇总栏用 @Consume 读取集合大小与内容，调用 DeviceSync 批量同步并 announce 播报。
 *
 * 适老化要点：Toggle 命中区放大（建议 44×44 包裹），勾选状态用高对比色 + 文字「已选/未选」。
 */
import { Toggle, ToggleType, Row, Column, Text, Image, HorizontalAlign, VerticalAlign } from '@kit.ArkUI';

@Component
export struct CheckableItem {
  @Consume selectedIds: Set<string>;
  @Prop id: string = '';
  @Prop title: string = '';
  @Prop subtitle: string = '';
  @Prop thumb?: Resource;

  build() {
    Row() {
      Toggle({ type: ToggleType.Checkbox, isOn: this.selectedIds.has(this.id) })
        .width(28).height(28)
        .margin({ left: 12, right: 8 })
        .onChange((on: boolean) => {
          if (on) { this.selectedIds.add(this.id); }
          else { this.selectedIds.delete(this.id); }
        });

      if (this.thumb) {
        Image(this.thumb)
          .width(56).height(56).objectFit(ImageFit.ScaleDown)
          .margin({ right: 10 });
      }

      Column() {
        Text(this.title).fontSize(15).fontColor('#222');
        if (this.subtitle.length > 0) {
          Text(this.subtitle).fontSize(12).fontColor('#888').margin({ top: 2 });
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)
      .accessibilityText(this.title + (this.selectedIds.has(this.id) ? '，已选' : '，未选'));
    }
    .width('100%')
    .height(72)
    .alignItems(VerticalAlign.Center)
    .backgroundColor('#FFFFFF');
  }
}
