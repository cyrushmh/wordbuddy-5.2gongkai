/*
 * PhotoAlbum.ets —— 图片网格相册（构建块，ArkTS NEXT 真实可用）
 * 来源：Batch25 ElectronicAlbum（Java API8：rawfile 取图 + AnimatorProperty 旋转/淡入 + delayDispatch 自动轮播幻灯片）
 * 代际：旧版 Java 工程，NEXT 翻写；抽「图片集合浏览」概念。原自动轮播幻灯片在 NEXT 用 Swiper.autoPlay 表达
 *      （见 Batch25 ImageCarousel），本块取其「网格缩略图总览 → 点开大图」范式，更贴合图册检索场景。
 * NEXT 对应：ArkUI Grid + GridItem + Image；点开大图接 Batch18 ZoomImage（Pinch-Zoom 看图）。
 * 用途：道藏图册总览（按册/按页网格）、书影墙、离线书目封面墙。长辈模式可加大 columnsGap 间距、降列数。
 * 默认可接线：纯 UI 原语，无需权限。
 */
export interface AlbumItem {
  src: Resource | string; // 缩略图资源或路径
  name?: string;         // 无障碍描述 / 标题
  fullSrc?: string;      // 点开后大图路径（不填则用 src）
}

@Component
export struct PhotoAlbum {
  @Prop items: AlbumItem[] = [];
  @Prop columns: number = 3;       // 网格列数（长辈模式可调小，如 2）
  @State previewUri: string = '';  // 当前预览大图路径（非空则弹 ZoomImage 层）

  build() {
    Column() {
      Grid() {
        ForEach(this.items, (it: AlbumItem, i: number) => {
          GridItem() {
            Image(it.src)
              .width('100%')
              .height(110)
              .objectFit(ImageFit.Cover)
              .borderRadius(6)
              .accessibilityText(it.name ?? '图片')
              .onClick(() => {
                // 接线：打开 Batch18 ZoomImage 预览
                // this.previewUri = it.fullSrc ?? (typeof it.src === 'string' ? it.src : '');
                // 由父页面用 Stack+ZoomImage 持 previewUri 渲染预览层
                void it;
              })
          }
        }, (it: AlbumItem, i: number) => i.toString())
      }
      .columnsTemplate(this.columns === 2 ? '1fr 1fr' : '1fr 1fr 1fr')
      .columnsGap(6)
      .rowsGap(6)
      .width('100%')
    }
  }
}

/*
 * 接线示例（道藏图册网格 → 点开 ZoomImage）：
 *   PhotoAlbum({ items: this.album, columns: this.elderMode ? 2 : 3 })
 *   // 父页面 Stack 内：if (this.previewUri) { ZoomImage({ src: this.previewUri }) }
 * 旧代对照：原 ElectronicAlbum 用单图 + AnimatorProperty 做旋转淡入自动轮播（幻灯片式）；NEXT 下「自动轮播」
 *          交给 ImageCarousel.autoPlay，「网格总览+点开」是本块新增的检索范式，更利于多图快速定位。
 */
