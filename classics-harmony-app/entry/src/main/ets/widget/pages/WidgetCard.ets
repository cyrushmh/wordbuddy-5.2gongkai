/**
 * 今日经典卡片（2*2）。
 * - 通过 @LocalStorageProp 绑定 EntryFormAbility 推送的 verse / source 字段。
 * - 点击经 postCardAction 拉起 EntryAbility 进入应用。
 * 参考 waylau ArkTSAtomicService 的 WidgetCard 结构。
 */
import { AccessibilityLevel } from '@kit.ArkUI';

@Entry
@Component
struct WidgetCard {
  @LocalStorageProp('verse') verse: string = '道可道，非常道。';
  @LocalStorageProp('source') source: string = '道德经·第一章';

  readonly ACTION_TYPE: string = 'router';
  readonly ABILITY_NAME: string = 'EntryAbility';
  readonly FULL_WIDTH: string = '100%';
  readonly FULL_HEIGHT: string = '100%';

  build() {
    Stack() {
      Image($r('app.media.layered_image'))
        .width(this.FULL_WIDTH)
        .height(this.FULL_HEIGHT)
        .objectFit(ImageFit.Cover)
        .accessibilityLevel(AccessibilityLevel.No);

      Column() {
        Text($r('app.string.widget_title'))
          .fontSize(14)
          .fontColor('#ffffff')
          .fontWeight(FontWeight.Bold)
          .opacity(0.95);

        Text(this.verse)
          .fontSize(15)
          .fontColor('#ffffff')
          .maxLines(3)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .margin({ top: 6 });

        Text(this.source)
          .fontSize(12)
          .fontColor('#ffffff')
          .opacity(0.8)
          .margin({ top: 6 })
          .alignSelf(HorizontalAlign.End);
      }
      .width(this.FULL_WIDTH)
      .height(this.FULL_HEIGHT)
      .alignItems(HorizontalAlign.Start)
      .justifyContent(FlexAlign.Center)
      .padding(12)
    }
    .width(this.FULL_WIDTH)
    .height(this.FULL_HEIGHT)
    .onClick(() => {
      postCardAction(this, {
        action: this.ACTION_TYPE,
        abilityName: this.ABILITY_NAME,
        params: { message: 'open_daily' }
      });
    });
  }
}
