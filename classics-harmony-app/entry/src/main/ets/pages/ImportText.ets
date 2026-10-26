/**
 * 导入文本页（镜像 iOS/macOS 端 ImportView）：从外部 txt 导入纯文本，
 * 经 TextEncoding 安全解码（BOM 剥离 → 严格 UTF-8 → 严格 GB18030 → 有损兜底），
 * 并做乱码指纹自检，把编码防护落到用户路径（呼应 justjavac/unicode-encoding-error-table）。
 *
 * 与跨端一致：经典文本内嵌一律 UTF-8，本页只服务「外部导入」入口，
 * 防止错配编码（古文码/口字码/锟拷码）污染正文。
 *
 * 依赖（HarmonyOS NEXT @kit 体系）：
 *   - @kit.CoreFileKit：picker（DocumentViewPicker 选文件）+ fileIo（读字节）
 *   - @kit.ArkUI：router 导航
 */
import { picker, fileIo } from '@kit.CoreFileKit';
import { decodeTextSafe, looksLikeMojibake } from '../util/TextEncoding';
import { router } from '@kit.ArkUI';

@Entry
@Component
struct ImportText {
  @State text: string = '';
  @State fileName: string = '';
  @State mojibake: boolean = false;
  @State errorMsg: string = '';

  /** 选文件 → 读字节 → 安全解码 → 乱码自检。任何异常都不崩溃，只回显错误。 */
  private async pickFile(): Promise<void> {
    try {
      const documentPicker = new picker.DocumentViewPicker();
      const uris: Array<string> = await documentPicker.select({ maxSelectNumber: 1, mimeType: 'text/plain' });
      if (!uris || uris.length === 0) {
        return;
      }
      const uri = uris[0];
      const file = fileIo.openSync(uri, fileIo.OpenMode.READ_ONLY);
      const stat = fileIo.statSync(file.fd);
      const buf = new ArrayBuffer(stat.size);
      fileIo.readSync(file.fd, buf);
      fileIo.closeSync(file.fd);
      const bytes = new Uint8Array(buf);
      const decoded = decodeTextSafe(bytes);
      this.text = decoded;
      this.fileName = uri.split('/').pop() ?? '';
      this.mojibake = looksLikeMojibake(decoded);
      this.errorMsg = '';
    } catch (e) {
      this.errorMsg = '读取失败：' + (e as Error).message;
    }
  }

  build() {
    Column() {
      Row() {
        Button('选择 TXT 文件导入')
          .height(36)
          .onClick(() => this.pickFile());
        if (this.fileName) {
          Text(this.fileName)
            .fontSize(13)
            .fontColor('#888')
            .margin({ left: 12 })
            .layoutWeight(1);
        }
      }
      .width('90%')
      .margin({ top: 16, bottom: 12 });

      if (this.errorMsg) {
        Text(this.errorMsg)
          .fontSize(13)
          .fontColor('#c0392b')
          .width('90%')
          .margin({ bottom: 8 });
      }

      if (this.mojibake) {
        Text('疑似编码错配（命中典型乱码指纹）。已按最安全方式解码，建议你确认原文件编码后重新导出。')
          .fontSize(13)
          .fontColor('#b9770e')
          .backgroundColor('#fef5e7')
          .borderRadius(8)
          .padding(10)
          .width('90%')
          .margin({ bottom: 12 });
      }

      if (this.text) {
        Scroll() {
          Text(this.text)
            .fontSize(16)
            .width('100%')
            .padding(12);
        }
        .layoutWeight(1)
        .width('100%');
      } else {
        Column() {
          Text('尚未导入')
            .fontSize(18)
            .fontColor('#999');
          Text('从本地选择一本 txt 古籍／文本，自动识别 UTF-8 / GB18030 编码并安全解码。')
            .fontSize(13)
            .fontColor('#aaa')
            .margin({ top: 8 })
            .textAlign(TextAlign.Center);
        }
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center);
      }
    }
    .width('100%')
    .height('100%');
  }
}
