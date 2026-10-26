/**
 * 短音播放构建块（来自 SoundPlayer，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.media.audio.SoundPlayer`：createSound(rawfile) → play(soundId, params)，
 * 配 loop / speed / volume；pause / stop(soundId)。
 * NEXT 用 `@kit.AudioKit` 的 `SoundPool`：createSoundPool → load(rawFd) → play(params)，
 * 返回 playId，stop(playId) 停单条。SoundPool 无原生暂停，旧 pause 以 stop(playId) 近似
 * （或保留 playId 待重播）；循环 / 速率走 SoundPoolPlayParameters。
 * 适老化：按键音 / 提醒叮咚 / 操作反馈短音，老人不用看屏也能靠声音确认。
 *
 * 未接线构建块：默认不接入任何页面；rawfile 资源（如 test.wav）需自行放入 resources/rawfile/。
 */
import { audio } from '@kit.AudioKit';
import { common } from '@kit.AbilityKit';

/** 短音播放封装（构建块逻辑层，页面接线时持有并 init/release）。 */
export class ShortSoundPlayer {
  private soundPool: audio.SoundPool | undefined = undefined;
  private soundId: number = -1;
  private playId: number = -1;
  private rawFileName: string;

  constructor(rawFileName: string = 'test.wav') {
    this.rawFileName = rawFileName;
  }

  /** 接线时传入真实 UIAbilityContext；加载完成才能 play。 */
  async init(context: common.UIAbilityContext): Promise<void> {
    const rendererInfo: audio.AudioRendererInfo = {
      content: audio.ContentType.CONTENT_TYPE_SONIFICATION,
      usage: audio.StreamUsage.STREAM_USAGE_MEDIA,
      rendererFlags: 0
    };
    this.soundPool = await audio.createSoundPool(1, rendererInfo);
    const rawFd = await context.resourceManager.getRawFd(this.rawFileName);
    this.soundId = await new Promise<number>((resolve) => {
      this.soundPool!.on('loadComplete', (sid: number) => resolve(sid));
      this.soundPool!.load(rawFd.fd, rawFd.offset, rawFd.length);
    });
  }

  play(loop: number = 0, rate: number = 1.0): void {
    if (!this.soundPool || this.soundId < 0) return;
    const params: audio.SoundPoolPlayParameters = {
      soundId: this.soundId,
      loop: loop,
      rate: rate,
      parallelism: 1,
      volumes: [1.0]
    };
    this.playId = this.soundPool.play(params);
  }

  /** 旧代 pause：SoundPool 无原生暂停，以停当前播放近似。 */
  pause(): void {
    this.stop();
  }

  stop(): void {
    if (this.soundPool && this.playId >= 0) {
      this.soundPool.stop(this.playId);
      this.playId = -1;
    }
  }

  release(): void {
    this.stop();
    if (this.soundPool) {
      if (this.soundId >= 0) this.soundPool.unload(this.soundId);
      this.soundPool.release();
    }
    this.soundPool = undefined;
  }
}

@Component
export struct SoundPlayerDemo {
  private player: ShortSoundPlayer = new ShortSoundPlayer();
  @State status: string = '待播放';

  build() {
    Column({ space: 12 }) {
      Text(this.status).fontSize(20).fontColor('#333')
      Button('播放').fontSize(28).onClick(() => { this.player.play(10, 1.0); this.status = '播放中'; })
      Button('暂停').fontSize(28).onClick(() => { this.player.pause(); this.status = '已暂停'; })
      Button('停止').fontSize(28).onClick(() => { this.player.stop(); this.status = '已停止'; })
    }.padding(16)
  }
}
