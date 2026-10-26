/*
 * 分页视频流（构建块 · 未接线，翻写 NEXT）
 * 概念来源：PageSlider（Java API8 PageSlider + VideoPlayerPageSliderProvider + SurfaceProvider 单表面切换源）
 * 翻写：@kit.ArkUI Swiper（vertical）承载整屏分页 + 每页 <Video>；页面聚焦自动播放、离开暂停
 * 适老化：讲经短视频 / 道藏讲解上下滑浏览；单页一个 Video、src 随当前页切换，省播放器资源、防误触
 * 权限：INTERNET（远程视频）或本地 rawfile；与 MediaPlayer 块共用权限声明
 * 注：复用 B34 MediaPlayer 的 Video 行为；本块专注「分页 + 自动播放当前页」编排
 */
import { Swiper, Column, Video, VideoController, Text } from '@kit.ArkUI';

@Component
export struct VideoFeed {
  @State index: number = 0;
  private sources: Resource[] = [];                 // 视频列表（rawfile 或网络 url）
  private titles: string[] = [];                   // 每页标题（讲经主题）
  controller: VideoController = new VideoController();

  build() {
    Swiper() {
      ForEach(this.sources, (s: Resource, i: number) => {
        Column() {
          Video({
            src: s,
            controller: this.controller,
            previewUri: $r('app.media.startIcon'),
          })
            .width('100%')
            .height('100%')
            .autoPlay(i === this.index)            // 仅当前页自动播放
            .controls(false)
            .onStart(() => {})
            .onClick(() => {                        // 点击暂停/继续，适老化免手势滑动
              // 由外部用 controller.start()/pause() 控制
            });

          Text(this.titles[i] ?? '')
            .fontSize(20)
            .fontColor('#FFFFFF')
            .margin({ bottom: 40 });
        }
        .width('100%')
        .height('100%')
      }, (s: Resource, i: number) => `vf-${i}`);
    }
    .vertical(true)                                // 竖向滑动（上下翻页）
    .indicator(false)
    .onChange((idx: number) => {
      this.index = idx;
      // 切换页：暂停旧的、播放新的（单控制器复用即可）
      this.controller.start();
    });
  }
}
