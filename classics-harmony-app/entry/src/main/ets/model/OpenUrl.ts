/**
 * 外链跳转工具。
 *
 * 按数据模型里的 onlineUrl 或 daozang 编号拼接道藏在线阅读地址，
 * 经系统浏览器/AppLinking 打开，并对成败给出 Toast 反馈。
 *
 * 反馈交互参考自 waylau 的 ToastDialog 示例（Java ToastDialog），
 * 在 ArkTS 中对应 @ohos.promptAction 的 showToast（见 API 参考 line 18256）。
 */
import { openLink, promptAction } from '@kit.ArkUI';
import { ClassicBook } from './ClassicsData';

/** 由一本书推导出道藏在线阅读地址；无则返回空串。 */
export function daozangUrlOf(book: ClassicBook): string {
  if (book.onlineUrl && book.onlineUrl.length > 0) {
    return book.onlineUrl;
  }
  if (book.daozang && book.daozang.nid > 0 && book.daozang.id > 0) {
    return `https://a.daorenjia.com/daozang${book.daozang.nid}-${book.daozang.id}`;
  }
  return '';
}

/**
 * 打开外链，并对成败做 Toast 提示（不再静默）。
 * - 无地址：提示该书暂无在线阅读；
 * - 成功：提示正在打开；
 * - 失败/异常：提示失败原因，不中断阅读。
 */
export function openExternal(url: string): void {
  if (!url) {
    promptAction.showToast({ message: '该书暂未提供在线阅读', duration: 2000 });
    return;
  }
  try {
    openLink(url, { appLinkingOnly: false }, (err: Error) => {
      if (err) {
        console.error(`openExternal failed: ${err.message}`);
        promptAction.showToast({ message: '道藏打开失败，请检查网络', duration: 2000 });
      } else {
        promptAction.showToast({ message: '正在打开在线道藏…', duration: 1500 });
      }
    });
  } catch (e) {
    console.error(`openExternal exception: ${(e as Error).message}`);
    promptAction.showToast({ message: '无法启动浏览器', duration: 2000 });
  }
}
