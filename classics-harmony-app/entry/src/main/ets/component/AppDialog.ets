/**
 * 信息 / 错误弹框封装（来自 ArkUIExperience 的 CustomDialogController 用法）。
 *
 * 当前应用散用 Toast 做反馈；未来统一为弹框时可替换。提供：
 *   - TipDialog：@CustomDialog 组件，标题 + 内容 + 确认按钮；
 *   - makeTipDialog(opts)：工厂，返回 CustomDialogController，直接 .open() 即可。
 *
 * 接线（待你定）：页面内声明 `dialog: CustomDialogController = makeTipDialog({ content: '...' })`，
 * 需要提示时 `this.dialog.open()`；错误提示同理，多传 title 即可。
 */
import { CustomDialogController } from '@kit.ArkUI';

@CustomDialog
export struct TipDialog {
  controller: CustomDialogController;
  title: string = '';
  content: string = '';
  confirmText: string = '知道了';
  onConfirm?: () => void;

  build() {
    Column() {
      if (this.title.length > 0) {
        Text(this.title)
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .margin({ bottom: 8 });
      }
      Text(this.content)
        .fontSize(15)
        .fontColor('#333');
      Button(this.confirmText)
        .margin({ top: 16 })
        .onClick(() => {
          if (this.onConfirm) {
            this.onConfirm();
          }
          this.controller.close();
        });
    }
    .padding(20)
    .alignItems(HorizontalAlign.Center);
  }
}

export function makeTipDialog(opts: {
  title?: string;
  content: string;
  confirmText?: string;
  onConfirm?: () => void;
}): CustomDialogController {
  return new CustomDialogController({
    builder: TipDialog({
      title: opts.title ?? '',
      content: opts.content,
      confirmText: opts.confirmText ?? '知道了',
      onConfirm: opts.onConfirm
    }),
    autoCancel: true
  });
}
