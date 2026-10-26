/**
 * 首页：经典文库列表 + 检索 + 我的书签。
 *
 * - 检索框参考 waylau TextField 示例（Java TextField + hint）→ ArkTS TextInput。
 * - 书签列表参考 waylau Todo 示例（Java ListContainer + CustomData）→ ArkTS List + ForEach，
 *   数据持久化复用 ReaderPrefs 的 Preferences 层。
 * - 经典列表参考 waylau AdaptiveBoxLayout 示例（Java 自适应盒子布局，按屏宽自动调列数）
 *   → ArkTS GridRow / GridCol + breakpoints：窄屏单列、平板/2in1 双列。
 */
import { router } from '@kit.ArkUI';
import { BreakpointsReference, AccessibilityLevel } from '@kit.ArkUI';
import { CLASSICS, ClassicBook } from '../model/ClassicsData';
import { BookmarkItem, loadBookmarksAsync, removeBookmark } from '../model/ReaderPrefs';
import { subscribeBookmarkChanged, unsubscribeBookmarkChanged, publishBookmarkChanged } from '../model/ReadingEvents';
import { VERSES, DailyVerse } from '../model/DailyVerse';
import { announce } from '../model/Accessibility';
import DeviceSync from '../model/DeviceSync';
import { isNetworkActive } from '../model/NetworkHelper';

@Entry
@Component
struct Index {
  @State books: ClassicBook[] = CLASSICS;
  @State keyword: string = '';
  @State bookmarks: BookmarkItem[] = [];
  @State syncText: string = DeviceSync.statusText;
  @State syncOn: boolean = DeviceSync.enabled;
  @State netActive: boolean = false;
  @State refreshing: boolean = false;

  aboutToAppear(): void {
    loadBookmarksAsync().then((list: BookmarkItem[]) => {
      this.bookmarks = list;
    });
    // 组网无障碍：只读呈现 WiFi 联网状态（无需权限弹框），供读屏/长辈模式感知。
    this.netActive = isNetworkActive();
    // 订阅「书签变更」公共事件：ChapterDetail 加/删书签后即时刷新（跨页广播）。
    subscribeBookmarkChanged(() => {
      loadBookmarksAsync().then((list: BookmarkItem[]) => {
        this.bookmarks = list;
      });
    });
    // 深链直达：外部 classics://book?... 拉起时，跳到指定典籍/章节（消费后清除，避免回首页重跳）。
    const target = AppStorage.get('launchTarget') as { bookId: string; chapterId: number } | undefined;
    if (target && target.bookId) {
      AppStorage.delete('launchTarget');
      if (target.chapterId >= 0) {
        router.pushUrl({ url: 'pages/ChapterDetail', params: { bookId: target.bookId, index: target.chapterId } });
      } else {
        router.pushUrl({ url: 'pages/BookDetail', params: { bookId: target.bookId } });
      }
    }
  }

  aboutToDisappear(): void {
    unsubscribeBookmarkChanged();
  }

  /** 按书名/作者/简介过滤（TextField 检索模式）。 */
  private get filteredBooks(): ClassicBook[] {
    const kw = this.keyword.trim();
    if (!kw) {
      return CLASSICS;
    }
    return CLASSICS.filter(
      (b: ClassicBook) =>
        b.title.includes(kw) ||
        b.author.includes(kw) ||
        (b.intro ?? '').includes(kw)
    );
  }

  /** 由书签取出书名（文库里查不到时显示占位）。 */
  private bookTitleOf(bookId: string): string {
    const found = CLASSICS.find((b: ClassicBook) => b.id === bookId);
    return found ? found.title : '未知典籍';
  }

  /** 切换多设备同步（组网无障碍）：更新状态文案并读屏播报。 */
  private toggleSync(): void {
    this.syncOn = !this.syncOn;
    const ctx = this.getUIContext().getHostContext();
    DeviceSync.setEnabled(this.syncOn, ctx);
    this.syncText = DeviceSync.statusText;
    announce(ctx, this.syncText);
  }

  /** 下拉刷新（组网无障碍 + 适老化）：复检联网状态、重载书签，读屏播报结果。 */
  private onHomeRefresh(): void {
    this.netActive = isNetworkActive();
    loadBookmarksAsync().then((list: BookmarkItem[]) => {
      this.bookmarks = list;
      const ctx = this.getUIContext().getHostContext();
      announce(ctx, '已刷新：' + (this.netActive ? 'WiFi 已联网' : 'WiFi 未连接') + '，书签 ' + list.length + ' 条');
      this.refreshing = false;
    });
  }

  @Builder
  private bookCard(book: ClassicBook) {
    Column() {
      Row() {
        Text(book.title)
          .fontSize(20)
          .fontWeight(FontWeight.Medium);
        Text(`${book.chapters.length} 章`)
          .fontSize(12)
          .fontColor('#999')
          .margin({ left: 8 });
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceBetween);

      Text(book.author)
        .fontSize(14)
        .fontColor('#888')
        .margin({ top: 4 });

      Text(book.intro)
        .fontSize(13)
        .fontColor('#666')
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .margin({ top: 6 });
    }
    .alignItems(HorizontalAlign.Start)
    .padding(14)
    .width('100%')
    .backgroundColor('#ffffff')
    .borderRadius(10)
    .shadow({ radius: 4, color: '#00000010', offsetY: 1 })
    .accessibilityText('打开' + book.title + '，作者' + book.author + '，共' + book.chapters.length + '章')
    .accessibilityDescription(book.intro ?? '')
    .onClick(() => {
      router.pushUrl({ url: 'pages/BookDetail', params: { bookId: book.id } });
    });
  }

  build() {
    Refresh({ refreshing: this.refreshing, offset: 120, friction: 100 }) {
      Scroll() {
      Column() {
        // 龙纹题头（SVGChineseLoong：可换色矢量，道家意象）。仅装饰，不挡操作。
        Image($r('app.media.chineseloong'))
          .width(64)
          .height(64)
          .fillColor('#aa3333')
          .margin({ top: 12, bottom: 4 })
          .accessibilityLevel(AccessibilityLevel.No);

        Text('道家经典文库')
          .fontSize(26)
          .fontWeight(FontWeight.Bold)
          .margin({ bottom: 12 });

        // 每日经典轮播（SwiperAnimationMode：自动播放 + 内置指示点）。
        // 数据源为 DailyVerse 内置精选，不依赖网络；与元服务卡片同源。
        Swiper() {
          ForEach(VERSES, (v: DailyVerse) => {
            Column() {
              Text(v.verse)
                .fontSize(17)
                .fontColor('#4a3f2f')
                .fontWeight(FontWeight.Medium)
                .textAlign(TextAlign.Center)
                .maxLines(3)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
                .padding({ left: 16, right: 16 });
              Text(v.source)
                .fontSize(13)
                .fontColor('#9a6a2a')
                .margin({ top: 8 });
            }
            .width('100%')
            .height('100%')
            .justifyContent(FlexAlign.Center);
          }, (v: DailyVerse) => v.source);
        }
        .width('90%')
        .height(120)
        .backgroundColor('#f5ecd8')
        .borderRadius(12)
        .autoPlay(true)
        .interval(4000)
        .loop(true)
        .duration(800)
        .indicator(true)
        .margin({ bottom: 14 });

        // 检索框（TextField 模式）
        TextInput({ placeholder: '搜索书名 / 作者', text: this.keyword })
          .onChange((v: string) => {
            this.keyword = v;
          })
          .width('90%')
          .height(40)
          .fontSize(15)
          .margin({ bottom: 10 })
          .accessibilityDescription('输入书名或作者进行搜索');

        // 导入外部文本（编码安全入口）：复用 TextEncoding 的 BOM 剥离→UTF-8→GB18030→有损兜底。
        Row() {
          Button('导入本地文本')
            .fontSize(14)
            .height(36)
            .accessibilityText('导入本地文本：选择 txt 文件并安全解码')
            .onClick(() => {
              router.pushUrl({ url: 'pages/ImportText' });
            });
        }
        .width('90%')
        .margin({ bottom: 10 });

        // 修真图谱（数据层 + Canvas 骨架 + 文本等价视图）：
        // 典籍/道藏部类/专题/旁参经论/语料 五层关系一屏可视，含读屏等价列表。
        Row() {
          Button('修真图谱')
            .fontSize(14)
            .height(36)
            .accessibilityText('打开修真图谱：典籍、道藏部类、专题与语料的分层关系视图，含读屏等价列表')
            .onClick(() => {
              router.pushUrl({ url: 'pages/XiuzhenMap' });
            });
        }
        .width('90%')
        .margin({ bottom: 10 });

        // 组网无障碍：多设备协同状态（无障碍化呈现 + 读屏播报）。
        // 让视障与长辈用户也能用通俗语言感知「组网是否通畅」。
        Row() {
          Column() {
            Text('多设备同步（组网无障碍）')
              .fontSize(15)
              .fontWeight(FontWeight.Medium)
              .fontColor('#1a3a6a');
            Text(this.syncText)
              .fontSize(13)
              .fontColor('#666')
              .margin({ top: 4 });
            Text(this.netActive ? 'WiFi 已联网' : 'WiFi 未连接')
              .fontSize(13)
              .fontColor('#666')
              .margin({ top: 2 })
              .accessibilityText(this.netActive ? 'WiFi 已联网，可在线阅读与同步' : 'WiFi 未连接，部分在线功能不可用');
          }
          .alignItems(HorizontalAlign.Start)
          .layoutWeight(1);

          Button(this.syncOn ? '关闭' : '开启')
            .fontSize(13)
            .height(32)
            .accessibilityText(this.syncOn ? '关闭多设备同步' : '开启多设备同步')
            .onClick(() => this.toggleSync());
        }
        .width('90%')
        .padding(14)
        .backgroundColor('#eef4ff')
        .borderRadius(10)
        .margin({ bottom: 10 })
        .accessibilityText('多设备同步状态：' + this.syncText);

        // 我的书签（Todo 列表模式）
        if (this.bookmarks.length > 0) {
          Text('我的书签')
            .fontSize(16)
            .fontWeight(FontWeight.Medium)
            .alignSelf(HorizontalAlign.Start)
            .margin({ left: '5%', bottom: 6 });

          List() {
            ForEach(this.bookmarks, (bm: BookmarkItem) => {
              ListItem() {
                Row() {
                  Column() {
                    Text(this.bookTitleOf(bm.bookId))
                      .fontSize(15)
                      .fontWeight(FontWeight.Medium);
                    Text(bm.label)
                      .fontSize(13)
                      .fontColor('#888')
                      .margin({ top: 2 });
                  }
                  .alignItems(HorizontalAlign.Start)
                  .layoutWeight(1);

                  Button('删')
                    .fontSize(12)
                    .height(30)
                    .accessibilityText('删除书签：' + this.bookTitleOf(bm.bookId) + ' ' + bm.label)
                    .onClick(() => {
                      removeBookmark(bm.bookId, bm.index);
                      this.bookmarks = this.bookmarks.filter(
                        (b: BookmarkItem) => !(b.bookId === bm.bookId && b.index === bm.index)
                      );
                      publishBookmarkChanged();
                    });
                }
                .width('100%')
                .padding({ left: 14, right: 14, top: 8, bottom: 8 });
              }
              .onClick(() => {
                router.pushUrl({ url: 'pages/ChapterDetail', params: { bookId: bm.bookId, index: bm.index } });
              });
            }, (bm: BookmarkItem) => `${bm.bookId}#${bm.index}`);
          }
          .width('90%')
          .height(Math.min(this.bookmarks.length * 56 + 8, 240))
          .backgroundColor('#f5f5f5')
          .borderRadius(10)
          .margin({ bottom: 10 });
        }

        // 经典列表（AdaptiveBoxLayout 响应式：窄屏单列 / 平板双列）
        GridRow({
          breakpoints: { value: ['600vp', '840vp'], reference: BreakpointsReference.WindowSize }
        }) {
          ForEach(this.filteredBooks, (book: ClassicBook) => {
            GridCol({ span: { xs: 12, sm: 12, md: 6, lg: 6 } }) {
              this.bookCard(book);
            }
            .padding(6);
          }, (book: ClassicBook) => book.id);
        }
        .width('94%')
        .margin({ top: 4, bottom: 20 });
      }
      .width('100%');
    }
    .width('100%')
    .height('100%');
      }
      .width('100%')
      .height('100%')
      .onRefresh(() => this.onHomeRefresh());
  }
}
