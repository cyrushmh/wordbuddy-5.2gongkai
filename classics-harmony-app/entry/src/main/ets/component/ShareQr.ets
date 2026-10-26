/**
 * 分享二维码构建块（来自 ArkUIExperience 的 QRCode 组件）。
 *
 * 把「典籍 / 章节」编码为 classics:// 深链（呼应 Batch8 深链直达），再交给 QRCode 渲染，
 * 支持「扫一扫直达指定典籍 / 章节」。
 *
 * 注意：QRCode 是纯渲染组件，本文件只提供「深链字符串」与「渲染组件」两样东西，
 * 未接入任何页面（默认不接线）。
 *
 * 接线（待你定）：在 BookDetail / ChapterDetail 加一个「分享」按钮，弹出一个含
 *   <ShareQr({ value: bookDeepLink(this.book.id) }) /> 的弹框或页面即可。
 */
import { QRCode, Visibility } from '@kit.ArkUI';

/** 生成典籍 / 章节的 classics:// 深链（与 EntryAbility 捕获逻辑同源）。 */
export function bookDeepLink(bookId: string, chapterId: number = -1): string {
  if (chapterId >= 0) {
    return `classics://book?bookId=${bookId}&chapterId=${chapterId}`;
  }
  return `classics://book?bookId=${bookId}`;
}

@Component
export struct ShareQr {
  @Prop value: string = '';
  @Prop size: number = 200;

  build() {
    Column() {
      if (this.value.length > 0) {
        QRCode(this.value)
          .color(0x000000)
          .width(this.size)
          .height(this.size)
          .accessibilityText('本书分享二维码：' + this.value);
      }
      Text(this.value)
        .fontSize(12)
        .fontColor('#666')
        .margin({ top: 8 })
        .visibility(this.value.length > 0 ? Visibility.Visible : Visibility.None);
    }
    .alignItems(HorizontalAlign.Center);
  }
}
