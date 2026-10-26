import { router, promptAction } from '@kit.ArkUI';
import { CLASSICS, ClassicBook, ClassicChapter } from '../model/ClassicsData';
import {
  READER_KEYS,
  ReaderTheme,
  s2t,
  persistReaderPref,
  addBookmark,
  BookmarkItem,
  ThemeColors
} from '../model/ReaderPrefs';
import { daozangUrlOf } from '../model/OpenUrl';
import { publishBookmarkChanged } from '../model/ReadingEvents';
import {
  effectiveFontScale,
  effectiveLineScale,
  effectiveColors,
  announce
} from '../model/Accessibility';

@Entry
@Component
struct ChapterDetail {
  @State bookId: string = '';
  @State index: number = 0;
  @State book: ClassicBook = CLASSICS[0];
  @State chapter: ClassicChapter = CLASSICS[0].chapters[0];
  @State showSettings: boolean = false;

  @StorageLink(READER_KEYS.fontScale) fontScale: number = 1.0;
  @StorageLink(READER_KEYS.lineScale) lineScale: number = 1.0;
  @StorageLink(READER_KEYS.theme) theme: string = ReaderTheme.Light;
  @StorageLink(READER_KEYS.trad) trad: boolean = false;
  @StorageLink(READER_KEYS.elderMode) elderMode: boolean = false;
  @StorageLink(READER_KEYS.highContrast) highContrast: boolean = false;
  @StorageLink(READER_KEYS.followSystemFont) followSystemFont: boolean = false;

  /** 系统字体缩放（跟随系统字体时乘入）。异常时回退 1.0。 */
  private get sysScale(): number {
    try {
      return this.getUIContext().getFontScale();
    } catch (e) {
      return 1.0;
    }
  }

  /** 有效字号：长辈模式优先，跟随系统字体再乘系统缩放。 */
  private get fScale(): number {
    return effectiveFontScale(this.fontScale, this.elderMode, this.sysScale, this.followSystemFont);
  }

  /** 有效行距：长辈模式优先。 */
  private get lScale(): number {
    return effectiveLineScale(this.lineScale, this.elderMode);
  }

  private get colors(): ThemeColors {
    return effectiveColors(this.theme, this.highContrast);
  }

  /** 适老化点击区：长辈模式放大到 44vp，满足最小可点尺寸。 */
  private get tapH(): number {
    return this.elderMode ? 44 : 32;
  }

  /** 读屏播报封装（取当前上下文，空则跳过）。 */
  private a11ySay(text: string): void {
    const ctx = this.getUIContext().getHostContext();
    announce(ctx, text);
  }

  aboutToAppear(): void {
    const params = router.getParams() as Record<string, Object>;
    this.bookId = (params['bookId'] as string) ?? '';
    this.index = (params['index'] as number) ?? 0;
    const found = CLASSICS.find((b: ClassicBook) => b.id === this.bookId);
    if (found && found.chapters[this.index]) {
      this.book = found;
      this.chapter = found.chapters[this.index];
    }
  }

  private displayOriginal(): string {
    return this.trad ? s2t(this.chapter.original) : this.chapter.original;
  }

  /** 把当前章加入书签（Todo 的「加项」模式 + ToastDialog 反馈）。 */
  private addCurrentBookmark(): void {
    const item: BookmarkItem = {
      bookId: this.bookId,
      index: this.index,
      label: `${this.book.title} · ${this.chapter.label}`
    };
    addBookmark(item);
    publishBookmarkChanged();
    promptAction.showToast({ message: '已加入书签', duration: 1500 });
    this.a11ySay(`已加入书签：${this.book.title} ${this.chapter.label}`);
  }

  private displayTranslation(): string {
    if (!this.chapter.translation) {
      return '';
    }
    return this.trad ? s2t(this.chapter.translation) : this.chapter.translation;
  }

  build() {
    Stack() {
      Column() {
        Row() {
          Text(this.chapter.label)
            .fontSize(22 * this.fScale)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.colors.text)
            .layoutWeight(1);

          Button('道藏')
            .fontSize(13)
            .height(this.tapH)
            .accessibilityText('打开道藏原文（应用内查看）')
            .onClick(() => router.pushUrl({ url: 'pages/DaozangViewer', params: { url: daozangUrlOf(this.book) } }));

          Button('设置')
            .fontSize(13)
            .height(this.tapH)
            .margin({ left: 8 })
            .accessibilityText('打开阅读设置')
            .onClick(() => (this.showSettings = true));

          Button('书签')
            .fontSize(13)
            .height(this.tapH)
            .margin({ left: 8 })
            .accessibilityText('将本章加入书签')
            .onClick(() => this.addCurrentBookmark());
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 18, bottom: 8 });

        Scroll() {
          Column() {
            Text('【原文】')
              .fontSize(14)
              .fontColor(this.colors.accent)
              .margin({ bottom: 6 });

            Text(this.displayOriginal())
              .fontSize(18 * this.fScale)
              .lineHeight(30 * this.lScale)
              .fontColor(this.colors.text)
              .width('100%');

            if (this.book.hasTranslation && this.chapter.translation) {
              Text('【译文】')
                .fontSize(14)
                .fontColor(this.colors.sub)
                .margin({ top: 18, bottom: 6 });

              Text(this.displayTranslation())
                .fontSize(15 * this.fScale)
                .lineHeight(26 * this.lScale)
                .fontColor(this.colors.sub)
                .width('100%');
            }
          }
          .padding(16)
          .alignItems(HorizontalAlign.Start);
        }
        .layoutWeight(1)
        .width('100%');
      }
      .width('100%')
      .height('100%')
      .backgroundColor(this.colors.bg);

      if (this.showSettings) {
        Column() {
          Row()
            .layoutWeight(1)
            .width('100%')
            .backgroundColor('#00000066')
            .onClick(() => (this.showSettings = false));

          Column() {
            this.fontRow('字号', this.fontScale, 0.8, 1.8, 0.1, READER_KEYS.fontScale, (v: number) => (this.fontScale = v));
            this.fontRow('行距', this.lineScale, 1.0, 1.8, 0.1, READER_KEYS.lineScale, (v: number) => (this.lineScale = v));
            this.themeRow();
            this.tradRow();
            this.elderRow();
            this.contrastRow();
            this.followFontRow();
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 16, bottom: 24 })
          .backgroundColor('#ffffff')
          .borderRadius({ topLeft: 16, topRight: 16 });
        }
        .width('100%')
        .height('100%');
      }
    }
    .width('100%')
    .height('100%');
  }

  @Builder
  private fontRow(
    label: string,
    value: number,
    min: number,
    max: number,
    step: number,
    key: string,
    onChange: (v: number) => void
  ) {
    Row() {
      Text(label).fontSize(15).fontColor('#333').width(48);
      Button('-')
        .width(36)
        .height(36)
        .onClick(() => {
          const v = Math.max(min, Math.round((value - step) * 10) / 10);
          this.fontScale = v;
          persistReaderPref(key, v);
          onChange(v);
        });
      Text(value.toFixed(1))
        .fontSize(15)
        .width(44)
        .textAlign(TextAlign.Center);
      Button('+')
        .width(36)
        .height(36)
        .onClick(() => {
          const v = Math.min(max, Math.round((value + step) * 10) / 10);
          this.fontScale = v;
          persistReaderPref(key, v);
          onChange(v);
        });
    }
    .width('100%')
    .justifyContent(FlexAlign.Start)
    .margin({ bottom: 14 });
  }

  @Builder
  private themeRow() {
    Row() {
      Text('配色').fontSize(15).fontColor('#333').width(48);
      this.themeDot(ReaderTheme.Light, '#ffffff', '#222');
      this.themeDot(ReaderTheme.Sepia, '#f5ecd8', '#4a3f2f');
      this.themeDot(ReaderTheme.Dark, '#1a1a1a', '#d8d8d8');
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
    .margin({ bottom: 14 });
  }

  @Builder
  private themeDot(t: string, bg: string, fg: string) {
    Row()
      .width(36)
      .height(36)
      .margin({ left: 12 })
      .borderRadius(18)
      .border({ width: this.theme === t ? 3 : 1, color: this.theme === t ? '#1989fa' : '#ccc' })
      .backgroundColor(bg)
      .onClick(() => {
        this.theme = t;
        persistReaderPref(READER_KEYS.theme, t);
      });
  }

  @Builder
  private tradRow() {
    Row() {
      Text('简繁').fontSize(15).fontColor('#333').width(48);
      Toggle({ type: ToggleType.Switch, isOn: this.trad })
        .onChange((isOn: boolean) => {
          this.trad = isOn;
          persistReaderPref(READER_KEYS.trad, isOn);
        });
      Text(this.trad ? '繁體' : '简体')
        .fontSize(14)
        .fontColor('#666')
        .margin({ left: 10 });
    }
    .width('100%')
    .alignItems(VerticalAlign.Center);
  }

  @Builder
  private elderRow() {
    Row() {
      Text('长辈模式')
        .fontSize(15)
        .fontColor('#333')
        .layoutWeight(1);
      Toggle({ type: ToggleType.Switch, isOn: this.elderMode })
        .accessibilityText(this.elderMode ? '关闭长辈模式' : '开启长辈模式')
        .onChange((isOn: boolean) => {
          this.elderMode = isOn;
          persistReaderPref(READER_KEYS.elderMode, isOn);
          this.a11ySay(isOn ? '已开启长辈模式，字号与行距已放大' : '已关闭长辈模式');
        });
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
    .margin({ bottom: 14 });
  }

  @Builder
  private contrastRow() {
    Row() {
      Text('高对比度')
        .fontSize(15)
        .fontColor('#333')
        .layoutWeight(1);
      Toggle({ type: ToggleType.Switch, isOn: this.highContrast })
        .accessibilityText(this.highContrast ? '关闭高对比度' : '开启高对比度')
        .onChange((isOn: boolean) => {
          this.highContrast = isOn;
          persistReaderPref(READER_KEYS.highContrast, isOn);
          this.a11ySay(isOn ? '已开启高对比度' : '已关闭高对比度');
        });
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
    .margin({ bottom: 14 });
  }

  @Builder
  private followFontRow() {
    Row() {
      Text('跟随系统字体')
        .fontSize(15)
        .fontColor('#333')
        .layoutWeight(1);
      Toggle({ type: ToggleType.Switch, isOn: this.followSystemFont })
        .accessibilityText(this.followSystemFont ? '关闭跟随系统字体' : '开启跟随系统字体')
        .onChange((isOn: boolean) => {
          this.followSystemFont = isOn;
          persistReaderPref(READER_KEYS.followSystemFont, isOn);
          this.a11ySay(isOn ? '已开启跟随系统字体' : '已关闭跟随系统字体');
        });
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
    .margin({ bottom: 14 });
  }
}
