/**
 * 道藏查看器（Batch15「ArkTSWebComponent / ArkTSWebComponentHTML」样例应用）。
 *
 * - 用 @kit.ArkWeb 的 Web 组件在应用内渲染道藏在线页面（替代直接跳系统浏览器）；
 * - 远端 src 需 ohos.permission.INTERNET（已在 module.json5 声明）；
 * - 顶部栏：返回 + 标题 + 「用浏览器打开」（openExternal 兜底，满足系统使用无障碍的出口需求）。
 *
 * 无障碍：Web 组件与按钮均加 accessibilityText；返回/打开按钮放大点击区（系统使用无障碍）。
 */
import { router, webview, promptAction } from '@kit.ArkUI';
import { openExternal } from '../model/OpenUrl';
import { announce } from '../model/Accessibility';

@Entry
@Component
struct DaozangViewer {
  @State url: string = '';
  @State title: string = '道藏原文';
  private controller: webview.WebviewController = new webview.WebviewController();

  aboutToAppear(): void {
    const params = router.getParams() as Record<string, Object>;
    const rawUrl = params ? (params['url'] as string) : '';
    this.url = rawUrl || '';
    if (!this.url) {
      promptAction.showToast({ message: '该书暂未提供在线阅读', duration: 2000 });
    } else {
      announce('正在打开道藏原文网页');
    }
  }

  build() {
    Column() {
      // 顶部栏：返回 + 标题 + 用浏览器打开（系统使用无障碍：放大点击区 + 读屏文案）
      Row() {
        Button('返回')
          .fontSize(15)
          .height(44)
          .accessibilityText('返回上一页')
          .onClick(() => router.back());

        Text(this.title)
          .fontSize(17)
          .fontWeight(FontWeight.Bold)
          .fontColor('#222')
          .layoutWeight(1)
          .textAlign(TextAlign.Center);

        Button('浏览器打开')
          .fontSize(15)
          .height(44)
          .accessibilityText('用系统浏览器打开道藏原文')
          .onClick(() => openExternal(this.url));
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 10, bottom: 10 })
      .alignItems(VerticalAlign.Center);

      if (this.url) {
        Web({ src: this.url, controller: this.controller })
          .layoutWeight(1)
          .width('100%')
          .accessibilityText('道藏原文网页内容，可用读屏浏览');
      } else {
        Column() {
          Text('该书暂未提供在线阅读')
            .fontSize(16)
            .fontColor('#888');
        }
        .layoutWeight(1)
        .width('100%')
        .justifyContent(FlexAlign.Center);
      }
    }
    .width('100%')
    .height('100%');
  }
}
