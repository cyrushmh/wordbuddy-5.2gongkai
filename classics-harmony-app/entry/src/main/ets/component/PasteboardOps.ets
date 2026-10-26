/**
 * 系统剪贴板构建块（来自 SystemPasteboardSetter / SystemPasteboardGetter，HarmonyOS Java API8 旧代）。
 *
 * 旧代 `ohos.miscservices.pasteboard.SystemPasteboard`：
 * setPasteData(PasteData.creatPlainTextData) / getPasteData() 遍历 Record 取
 * MIMETYPE_TEXT_PLAIN / MIMETYPE_TEXT_HTML。
 * NEXT 用 `@kit.BasicServicesKit` 的 `pasteboard.getSystemPasteboard()`，
 * setData(pasteboard.createPlainTextData) / getData().getRecordAt(i).plainText。
 * 适老化：一键把老人读到的经文 / 地址复制到剪贴板，或读屏读出剪贴板内容。
 * 未接线构建块：默认不接入任何页面（剪贴板无需特殊权限）。
 */
import { pasteboard } from '@kit.BasicServicesKit';

export class PasteboardOps {
  private pb: pasteboard.Pasteboard | undefined;

  private ensure(): pasteboard.Pasteboard {
    if (!this.pb) {
      this.pb = pasteboard.getSystemPasteboard();
    }
    return this.pb!;
  }

  setText(text: string): void {
    this.ensure().setData(pasteboard.createPlainTextData(text));
  }

  getText(): string {
    const data = this.ensure().getData();
    if (!data) return '';
    for (let i = 0; i < data.getRecordCount(); i++) {
      const rec = data.getRecordAt(i);
      if (rec.mimeType === pasteboard.MIMETYPE_TEXT_PLAIN) {
        return rec.plainText as string;
      }
    }
    return '';
  }
}
