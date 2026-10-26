/*
 * ImageCarousel.ets —— 图片轮播（构建块，ArkTS NEXT 真实可用）
 * 来源：Batch25 EtsUISwiper（基础 Swiper）+ EtsUISwiperAutoPlay（Swiper.autoPlay(true)）两个 ArkTS NEXT 样例合并
 * 代际：ArkTS NEXT 真代码（@Entry/@Component/Swiper/ForEach），非旧代；直接可用，仅做适配封装。
 * NEXT 对应：ArkUI Swiper（autoPlay / interval / indicator / itemSpace）。原样例用 Flex 容器，本块改用 Column 更贴合现状。
 * 用途：书封轮播、道藏图册滑动浏览、首页推荐书目横滑。与 Batch18 ZoomImage（单图缩放）、Batch25 PhotoAlbum（网格）互补。
 * 默认可接线：纯 UI 原语，无需权限。src 支持 $r 资源或字符串路径（道藏离线图走 file:// 或沙箱路径）。
 */
export interface CarouselItem {
  src: Resource | string; // 图片资源（$r）或路径字符串（离线图册）
  name?: string;          // 无障碍描述 / 角标
}

@Component
export struct ImageCarousel {
  @Prop items: CarouselItem[] = [];
  @Prop autoPlay: boolean = false;   // 自动播放（EtsUISwiperAutoPlay 范式）
  @Prop interval: number = 3000;     // 自动播放间隔(ms)
  @Prop showIndicator: boolean = true;
  @Prop height: number = 220;

  build() {
    Column() {
      if (this.items.length > 0) {
        Swiper({ autoPlay: this.autoPlay, interval: this.interval, indicator: this.showIndicator }) {
          ForEach(this.items, (it: CarouselItem, i: number) => {
            Image(it.src)
              .width('100%')
              .height(this.height)
              .objectFit(ImageFit.Cover)
              .accessibilityText(it.name ?? '轮播图')
          }, (it: CarouselItem, i: number) => i.toString())
        }
        .width('100%')
        .itemSpace(8)
      }
    }
  }
}

/*
 * 接线示例（道藏图册轮播，自动播放）：
 *   ImageCarousel({
 *     items: this.daozangPages.map(p => ({ src: p.uri, name: p.title })),
 *     autoPlay: true, interval: 4000
 *   })
 * 旧代对照：原样例在 index.ets 直接写 Swiper+ForEach；本块抽成可复用 @Component，支持资源与路径两种 src，
 *          并补 accessibilityText 让读屏报图名（适老化）。
 */
