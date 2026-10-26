import { router } from '@kit.ArkUI';
import { CLASSICS, ClassicBook, ClassicChapter } from '../model/ClassicsData';
import { daozangUrlOf } from '../model/OpenUrl';

@Entry
@Component
struct BookDetail {
  @State bookId: string = '';
  @State book: ClassicBook = CLASSICS[0];

  aboutToAppear(): void {
    const params = router.getParams() as Record<string, Object>;
    this.bookId = (params['bookId'] as string) ?? '';
    const found = CLASSICS.find((b: ClassicBook) => b.id === this.bookId);
    if (found) {
      this.book = found;
    }
  }

  /** 元数据键值行（HealthyDiet ContentTable 的 @Builder 模式）：左侧标签 + 右侧值，读屏逐行播报。 */
  @Builder
  private metaRow(title: string, value: string) {
    Row() {
      Text(title)
        .fontSize(14)
        .fontColor('#999')
        .width(84);
      Text(value)
        .fontSize(14)
        .fontColor('#333')
        .layoutWeight(1)
        .accessibilityText(title + '：' + value);
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 7, bottom: 7 })
    .border({ width: { bottom: 1 }, color: '#f0f0f0' });
  }

  build() {
    Column() {
      Row() {
        Column() {
          Text(this.book.title)
            .fontSize(24)
            .fontWeight(FontWeight.Bold);
          Text(this.book.author)
            .fontSize(14)
            .fontColor('#888')
            .margin({ top: 4 });
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start);

        if (daozangUrlOf(this.book).length > 0) {
          Button('道藏')
            .fontSize(13)
            .height(32)
            .accessibilityText('打开道藏原文（应用内查看）')
            .onClick(() => router.pushUrl({ url: 'pages/DaozangViewer', params: { url: daozangUrlOf(this.book) } }));
        }
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 18, bottom: 6 });

      Text(this.book.intro)
        .fontSize(13)
        .fontColor('#666')
        .margin({ left: 16, right: 16, bottom: 12 });

      // 元数据键值表（HealthyDiet ContentTable @Builder 模式）：把可量化信息结构化呈现，读屏友好。
      Column() {
        this.metaRow('篇数', this.book.chapters.length + ' 篇');
        this.metaRow('白话译文', this.book.hasTranslation ? '已收录' : '暂未收录');
        if (this.book.daozang) {
          this.metaRow('道藏归属', '第 ' + this.book.daozang.nid + ' 函 · 第 ' + this.book.daozang.id + ' 册');
        }
        if (this.book.onlineUrl) {
          this.metaRow('在线底本', '已挂载道藏在线阅读');
        }
        if (this.book.note) {
          this.metaRow('附记', this.book.note);
        }
      }
      .width('100%')
      .margin({ bottom: 12 });

      List() {
        ForEach(this.book.chapters, (ch: ClassicChapter, idx: number) => {
          ListItem() {
            Text(ch.label)
              .fontSize(17)
              .padding(14)
              .width('100%')
              .accessibilityText('第' + (idx + 1) + '章：' + ch.label);
          }
          .onClick(() => {
            router.pushUrl({
              url: 'pages/ChapterDetail',
              params: { bookId: this.book.id, index: idx }
            });
          });
        }, (ch: ClassicChapter, idx: number) => this.book.id + idx);
      }
      .layoutWeight(1)
      .width('100%');
    }
    .width('100%')
    .height('100%');
  }
}
