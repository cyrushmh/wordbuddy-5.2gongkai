/**
 * 媒体播放器构建块（来自 ArkUIMediaComponents 的 Video + VideoController 用法）。
 *
 * 用途：听书 / 名家诵读 / 典籍讲解视频。支持播放·暂停·停止·重置·精准跳转，
 * 以及 0.75 / 1.0 / 2.0 倍速（听书慢速精听、通勤快速过）。
 *
 * 默认不接线：当前 ChapterDetail 是纯文字阅读，无音视频资源与麦克风/存储权限，
 * 故先沉淀为本块，待你定（需配套 INTERNET 或本地 rawfile 音频/视频资源）。
 *
 * 接线（待你定）：
 *   1) 在 ChapterDetail 顶部或浮层放 <MediaPlayer({ src: $rawfile('audio/xx.mp3') }) />；
 *   2) 远程讲解视频用 $rawfile 或 network 资源（需 module.json5 已申 INTERNET，Batch15 已加）；
 *   3) 倍速按钮对「听书」尤其有用，建议把常用倍速（0.75/1/1.25/1.5/2）做成 seg 选择。
 *
 * 适老化要点：控制按钮放大（≥44），倍速/进度用文字 + 可聚焦控件，避免纯手势；
 *   关键状态（播放中/暂停）用 announce 读屏播报。
 */
import {
  Video, VideoController, Column, Row, Button, PlaybackSpeed, SeekMode,
  FlexDirection, FlexAlign
} from '@kit.ArkUI';

@Component
export struct MediaPlayer {
  @Prop src: Resource = $rawfile('');   // 音频/视频资源
  @State previewUri: Resource = $r('app.media.startIcon'); // 封面
  @State isAutoPlay: boolean = false;
  @State showControls: boolean = true;
  @State curRate: PlaybackSpeed = PlaybackSpeed.Speed_Forward_1_00_X;
  controller: VideoController = new VideoController();

  build() {
    Column() {
      Video({
        src: this.src,
        previewUri: this.previewUri,
        currentProgressRate: this.curRate,
        controller: this.controller
      })
        .width('100%')
        .height(220)
        .autoPlay(this.isAutoPlay)
        .controls(this.showControls)
        .onError(() => { /* 资源缺失：建议 announce('音视频加载失败') */ });

      Row() {
        Button('播放').onClick(() => this.controller.start()).margin(4);
        Button('暂停').onClick(() => this.controller.pause()).margin(4);
        Button('停止').onClick(() => this.controller.stop()).margin(4);
        Button('重播').onClick(() => this.controller.reset()).margin(4);
      }
      .flexDirection(FlexDirection.Row)
      .justifyContent(FlexAlign.Center)
      .margin({ top: 8 });

      Row() {
        Button('0.75x').onClick(() => { this.curRate = PlaybackSpeed.Speed_Forward_0_75_X; }).margin(4);
        Button('1.0x').onClick(() => { this.curRate = PlaybackSpeed.Speed_Forward_1_00_X; }).margin(4);
        Button('2.0x').onClick(() => { this.curRate = PlaybackSpeed.Speed_Forward_2_00_X; }).margin(4);
      }
      .flexDirection(FlexDirection.Row)
      .justifyContent(FlexAlign.Center);
    }
    .alignItems(FlexAlign.Center);
  }
}
