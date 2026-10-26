/**
 * 媒体会话构建块（来自 Batch20 的 AVSession + AVMetadataHelper 两个 Java API8 样例，
 * 已翻成 HarmonyOS NEXT 的 @kit.AVSessionKit / @kit.MediaKit 概念）。
 *
 * 用途：把听书/讲解音频接入「系统媒体控制」——锁屏、通知栏、蓝牙耳机/车机按键、
 * 智慧屏遥控器都能直接播放/暂停/上一首/下一首/拖动进度。对长辈（适老化）尤其关键：
 *   不进 App 也能控制播放，避免在小字界面里找按钮；进度与曲名同步显示，减少困惑。
 *
 * 与 AudioBookPlayer 的关系：AudioBookPlayer 负责「播放与界面」，本块负责「把播放状态
 * 上报给系统 + 接收系统控制指令并回调给播放器」。两者配合 = 完整听书体验。
 *
 * 默认不接线：纯控制壳，需 AudioBookPlayer 在 onPlay/onPause/... 里调 setPosition/setDuration，
 * 并在本块回调里驱动播放器。SDK 未验证（沙箱无 HarmonyOS NEXT SDK），API 名称按官方文档写，
 * 真机接线时以编译器为准。
 *
 * 接线（待你定）：
 *   1) AudioBookPlayer 初始化时：const s = new PlaybackSession(); await s.init(ctx, '清静经·诵读');
 *   2) 播放状态变化：s.setDuration(totalMs); s.setPosition(curMs, isPlaying);
 *   3) 把播放器动作接进回调：s.onPlay = () => this.controller.start(); 等；
 *   4) 页面销毁：s.destroy();
 *
 * 权限：AVSession 为应用内会话，无需额外声明；但「锁屏控制」依赖音频正在播放，
 *   故需 AudioBookPlayer 已有权限（纯音频播放无麦克风需求）。
 */
import { avSession } from '@kit.AVSessionKit';

/** 播放控制回调集合，由 AudioBookPlayer 注入。 */
export interface PlaybackHandlers {
  onPlay?: () => void;
  onPause?: () => void;
  onStop?: () => void;
  onSeek?: (ms: number) => void;
  onNext?: () => void;
  onPrevious?: () => void;
}

export class PlaybackSession {
  private session?: avSession.AVSession;
  handlers: PlaybackHandlers = {};

  /** 创建并激活一个音频会话，绑定系统媒体控制。title 用于锁屏/通知栏显示。 */
  async init(ctx: Context, title: string): Promise<void> {
    // 真实 NEXT API：createAVSession(context, tag, type)
    this.session = await avSession.createAVSession(ctx, 'CLASSICS_AUDIO', avSession.AVSessionType.AVSESSION_TYPE_AUDIO);
    await this.session.activate();

    const meta: avSession.AVMetadata = {
      assetId: 'classics-audio',
      title: title,
      mediaType: avSession.AVMediaType.AVMEDIA_TYPE_AUDIO
    } as avSession.AVMetadata;
    await this.session.setAVMetadata(meta);

    // 系统控制指令 → 回调给播放器
    this.session.on('play', () => this.handlers.onPlay?.());
    this.session.on('pause', () => this.handlers.onPause?.());
    this.session.on('stop', () => this.handlers.onStop?.());
    this.session.on('seek', (ms: number) => this.handlers.onSeek?.(ms));
    this.session.on('playNext', () => this.handlers.onNext?.());
    this.session.on('playPrevious', () => this.handlers.onPrevious?.());
  }

  /** 上报总时长（毫秒），供系统进度条与「剩 X 分」播报。 */
  async setDuration(ms: number): Promise<void> {
    await this.session?.setAVPlaybackState({
      state: avSession.PlaybackState.PLAYBACK_STATE_PLAYING,
      duration: ms,
      position: { elapsedTime: 0, updateTime: Date.now() }
    } as avSession.AVPlaybackState);
  }

  /** 上报当前进度与播放态（isPlaying 决定图标）。 */
  async setPosition(ms: number, isPlaying: boolean): Promise<void> {
    await this.session?.setAVPlaybackState({
      state: isPlaying
        ? avSession.PlaybackState.PLAYBACK_STATE_PLAYING
        : avSession.PlaybackState.PLAYBACK_STATE_PAUSED,
      duration: undefined,
      position: { elapsedTime: ms, updateTime: Date.now() }
    } as avSession.AVPlaybackState);
  }

  /** 释放会话（页面 onPageHide / 组件销毁时调用）。 */
  destroy(): void {
    this.session?.destroy();
    this.session = undefined;
  }
}
