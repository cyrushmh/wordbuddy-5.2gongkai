/**
 * 录音构建块（概念来自 AudioCapturer 样例，已翻译为 HarmonyOS NEXT 的 AudioCapturer）。
 *
 * 来源说明（重要）：
 *   原始 AudioCapturer 是「旧版鸿蒙 Java API 8」工程（ohos.media.audio.AudioCapturer +
 *   AbilitySlice），不能直接编译进本应用的 ArkTS Stage 模型。本块保留其「开始/停止采集
 *   双声道 16-bit PCM @44100」的采集骨架，底层改用 NEXT 的 @kit.AudioKit
 *   （audio.createAudioCapturer）实现，面向两个真实场景：语音搜索输入、以及长辈口述批注/
 *   读书笔记（录音存为本地 PCM，未来可转写或随书签一并组网同步）。
 *
 * 权限（务必处理）：
 *   - 麦克风采集需要 ohos.permission.MICROPHONE，须在 module.json5 声明并在运行时拉起；
 *     建议在设置面板用「为何录音」文案 + 一键跳转权限页（见 Batch14 的 WantOpenSetting 思路）。
 *
 * 为什么值得做（无障碍 + 组网）：
 *   - 语音输入 = 视障/不擅打字的组长辈最自然的检索与批注方式；
 *   - 录音产物可与书签、笔记一起通过 DeviceSync（分布式 KV）跨设备同步，呼应「组网无障碍」。
 *
 * 默认不接线：sandbox 无 SDK 验证、且无麦克风硬件/权限，故先沉淀为本块，待你定。
 *
 * 接线（待你定）：
 *   1) module.json5 的 requestPermissions 加 ohos.permission.MICROPHONE（reason 文案）；
 *   2) 检索框旁加「语音」按钮 → 调 start()，录音中显示计时 + 停止按钮；
 *   3) 停止后把 PCM buffer 落盘（rawfile 或应用沙箱），或交给语音识别；联网态下可触发同步。
 *
 * 适老化要点：开始/停止按钮 tap 区 ≥44、配高对比色；录音中状态用 announce() 读屏
 *   「正在录音」，停止时播报「录音已保存」。
 *
 * ⚠️ SDK 未验证：AudioCapturerOptions / read() 的返回值类型与状态机以官方文档为准，
 *   真机/DevEco 接入时核对 samplingRate / sampleFormat / channels / SourceType.SOURCE_TYPE_MIC。
 */
import { audio } from '@kit.AudioKit';
import { Column, Row, Text, Button, State, Component, FlexAlign } from '@kit.ArkUI';

@Component
export struct AudioRecorder {
  @State recording: boolean = false;
  @State elapsedSec: number = 0;

  private capturer?: audio.AudioCapturer;
  private timer?: number;

  /** 构建采集参数：双声道、16-bit PCM、44.1kHz、麦克风源。 */
  private buildOptions(): audio.AudioCapturerOptions {
    return {
      streamInfo: {
        samplingRate: audio.AudioSamplingRate.SAMPLE_RATE_44100,
        sampleFormat: audio.AudioSampleFormat.SAMPLE_FORMAT_PCM_16_BIT,
        channels: audio.AudioChannel.CHANNEL_2,
        encoding: audio.AudioEncodingType.ENCODING_TYPE_RAW
      },
      capturerInfo: {
        source: audio.SourceType.SOURCE_TYPE_MIC,
        capturerFlags: 0
      }
    };
  }

  /** 开始录音。 */
  private async start(): Promise<void> {
    if (this.recording) {
      return;
    }
    const opts = this.buildOptions();
    this.capturer = await audio.createAudioCapturer(opts);
    await this.capturer.start();
    this.recording = true;
    this.elapsedSec = 0;
    // 简易计时（仅供 UI 展示；真机用系统时钟更稳）
    this.timer = setInterval(() => {
      this.elapsedSec += 1;
    }, 1000) as unknown as number;
    // 读取循环：read() 阻塞取 PCM buffer，落盘/转写在此处理（示例略）
    // const bufSize = await this.capturer.getBufferSize();
    // const buf = await this.capturer.read(bufSize, audio.AudioCapturer.ReadMode.READ_MODE_BLOCKING);
  }

  /** 停止录音并释放。 */
  private async stop(): Promise<void> {
    if (!this.recording || !this.capturer) {
      return;
    }
    if (this.timer !== undefined) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
    await this.capturer.stop();
    await this.capturer.release();
    this.capturer = undefined;
    this.recording = false;
  }

  build() {
    Column() {
      Text(this.recording ? `录音中 ${this.elapsedSec}s` : '待录音')
        .fontSize(16)
        .fontColor(this.recording ? '#C00' : '#333')
        .accessibilityText(this.recording ? `正在录音，已 ${this.elapsedSec} 秒` : '未录音')

      Row({ space: 24 }) {
        Button(this.recording ? '停止' : '开始录音')
          .height(44)
          .backgroundColor(this.recording ? '#C00' : '#1698CE')
          .onClick(() => {
            if (this.recording) {
              this.stop();
            } else {
              this.start();
            }
          })
      }
      .justifyContent(FlexAlign.Center)
      .width('100%')
    }
    .width('100%')
    .padding(12)
  }

  aboutToDisappear(): void {
    if (this.timer !== undefined) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
    this.capturer?.release();
    this.capturer = undefined;
  }
}
