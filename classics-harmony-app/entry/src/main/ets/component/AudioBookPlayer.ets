/**
 * 听书播放器构建块（概念来自 AudioPlayer 样例，已翻译为 HarmonyOS NEXT 的 AVPlayer）。
 *
 * 来源说明（重要）：
 *   原始 AudioPlayer 是「旧版鸿蒙 Java API 8」工程（ohos.media.player.Player +
 *   AbilitySlice），不能直接编译进本应用的 ArkTS Stage 模型。本块保留其「可播放列表 +
 *   上/下一首循环 + 播放/暂停 + 进度环 + 标题跑马灯」的交互骨架，底层改用 NEXT 的
 *   @kit.MediaKit（media.AVPlayer）实现纯音频播放。这正是用户所说「编程语言/运行时的不同
 *   带来兼容层差异」的现成案例：同一厂商两套语言代际，旧代用 Java Ability，新代用 ArkTS，
 *   我们守在 NEXT/ArkTS 上才能吃到跨设备 Ark 字节码这层兼容红利。
 *
 * 为什么值得做（直接服务无障碍 + 适老化）：
 *   - 听书 = 视障 / 长辈 / 通勤场景下最可能的阅读形态，是「系统使用无障碍」的核心能力之一。
 *   - 倍速（慢速精听、快速过场）见 Batch17 的 MediaPlayer 思路，本块聚焦纯音频列表。
 *
 * 默认不接线：本应用暂无音频资源（rawfile 下没有 mp3/有声底本）、且 sandbox 无 SDK 验证，
 * 故先沉淀为本块，待你定。
 *
 * 接线（待你定）：
 *   1) 把每本章节/白话译文的有声资源放进 resources/rawfile/，或改用在线音频 URL；
 *   2) 在 ChapterDetail 底部挂一个迷你播放条（标题跑马灯 + 播放/暂停 + 进度）；
 *   3) 进度播报用 announce()（见 model/Accessibility.ets），切歌时读屏「正在播放：XXX」。
 *
 * 适老化要点：播放/暂停按钮 tap 区 ≥44；标题跑马灯配 accessibilityText；进度环用
 *   accessibilityValue 暴露百分比，避免纯视觉进度。
 *
 * ⚠️ SDK 未验证：AVPlayer 的 event 名/状态机以官方文档为准，真机/DevEco 接入时核对
 *   stateChange / timeUpdate / duration / currentTime 等字段。
 */
import { media } from '@kit.MediaKit';
import { Column, Row, Text, Button, Progress, Slider, Image, State, Component, Builder, FlexAlign } from '@kit.ArkUI';

/** 一条有声曲目（书名/篇名 + 资源定位）。 */
export interface AudioTrack {
  name: string;
  /** rawfile 写法：'resource://rawfile/001.mp3'；在线写法：'https://...'（需 INTERNET）。 */
  url: string;
}

@Component
export struct AudioBookPlayer {
  @State tracks: AudioTrack[] = [];
  @State index: number = 0;
  @State playing: boolean = false;
  @State currentTimeMs: number = 0;
  @State durationMs: number = 0;

  private avPlayer?: media.AVPlayer;

  /** 装载播放器（AVPlayer 为异步创建）。 */
  private async ensurePlayer(): Promise<media.AVPlayer> {
    if (this.avPlayer) {
      return this.avPlayer;
    }
    const p = await media.createAVPlayer();
    p.on('stateChange', (state: string) => {
      // 常见状态：initialized -> prepared -> playing -> paused -> stopped -> released
      if (state === 'prepared') {
        this.durationMs = p.duration;
        p.play();
        this.playing = true;
      }
    });
    p.on('timeUpdate', (time: number) => {
      this.currentTimeMs = time; // 毫秒
    });
    p.on('playbackCompleted', () => {
      this.playing = false;
      this.next(); // 播完自动下一首（循环）
    });
    this.avPlayer = p;
    return p;
  }

  /** 播放当前曲目。 */
  private async playCurrent(): Promise<void> {
    const p = await this.ensurePlayer();
    const t = this.tracks[this.index];
    if (t) {
      p.url = t.url; // 赋 URL 触发 initialized -> prepared -> 自动 play
    }
  }

  /** 播放/暂停切换。 */
  private toggle(): void {
    const p = this.avPlayer;
    if (!p) {
      this.playCurrent();
      return;
    }
    if (this.playing) {
      p.pause();
      this.playing = false;
    } else {
      p.play();
      this.playing = true;
    }
  }

  /** 上一首（取模循环）。 */
  private prev(): void {
    if (this.tracks.length === 0) {
      return;
    }
    this.index = (this.index - 1 + this.tracks.length) % this.tracks.length;
    this.playCurrent();
  }

  /** 下一首（取模循环）。 */
  private next(): void {
    if (this.tracks.length === 0) {
      return;
    }
    this.index = (this.index + 1) % this.tracks.length;
    this.playCurrent();
  }

  build() {
    Column() {
      // 当前曲目标题（跑马灯 + 读屏文本）
      Text(this.tracks[this.index]?.name ?? '未选择曲目')
        .fontSize(16)
        .fontColor('#333')
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.MARQUEE })
        .accessibilityText(`正在播放：${this.tracks[this.index]?.name ?? '未选择曲目'}`)

      // 进度条（读屏暴露百分比）
      Progress({ value: this.durationMs > 0 ? this.currentTimeMs / this.durationMs * 100 : 0, total: 100, type: ProgressType.Linear })
        .width('100%')
        .accessibilityValue({ min: 0, max: 100, current: this.durationMs > 0 ? Math.round(this.currentTimeMs / this.durationMs * 100) : 0 })

      // 控制按钮（大点击区，适老化）
      Row({ space: 24 }) {
        Button('上一首').onClick(() => this.prev()).height(44)
        Button(this.playing ? '暂停' : '播放').onClick(() => this.toggle()).height(44)
        Button('下一首').onClick(() => this.next()).height(44)
      }
      .justifyContent(FlexAlign.Center)
      .width('100%')
    }
    .width('100%')
    .padding(12)
  }

  /** 页面销毁时释放播放器。 */
  aboutToDisappear(): void {
    this.avPlayer?.release();
    this.avPlayer = undefined;
  }
}
