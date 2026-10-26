// 远程 HTTP 抓取构建块 —— 由 ArkTSHttp 样例迁移。
//
// 用途：在 app 内拉取远程文本/数据（如扩展书目、道藏图片元数据），
// 取代「外部浏览器打开」的体验，实现站内加载。
//
// ⚠️ 默认未接入主流程（当前 道藏/书目走 OpenUrl 外部打开）。本文件是「可复用构建块」：
//    - module.json5 需声明权限 "ohos.permission.INTERNET"；
//    - 道藏正文接口（m.daorenjia.com/api/apiscontent.php）此前实测存在
//      nid/tid 与正文错位（如 nid=16&tid=712 把《太平经》误标《南华真经》），
//      接入前务必先人工复核目标 id 映射，避免注入错乱正文；
//    - 搭配 ArkTSImageCodec（@ohos.multimedia.image createImageSource→createPixelMap）
//      可把抓回的图片字节渲染为 PixelMap（见 fetchImagePixelMap 注释示例）。
// 接入方式（需要时）：在需要远程数据的页面 import { fetchText } 后 await 调用。

import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';

/** GET 拉取远程文本，返回字符串；非 200 或异常返回空串。 */
export async function fetchText(url: string, timeoutMs: number = 60000): Promise<string> {
  const httpRequest = http.createHttp();
  try {
    const data = await httpRequest.request(url, {
      method: http.RequestMethod.GET,
      connectTimeout: timeoutMs,
      readTimeout: timeoutMs,
      header: { 'Content-Type': 'application/json' }
    });
    if (data.responseCode === http.ResponseCode.OK) {
      return typeof data.result === 'string' ? data.result : JSON.stringify(data.result);
    }
    return '';
  } catch (err) {
    const e = err as BusinessError;
    console.error(`HttpFetcher fetchText failed: Code:${e.code},message:${e.message}`);
    return '';
  } finally {
    // 每个 httpRequest 用完即销毁，避免句柄泄漏。
    httpRequest.destroy();
  }
}

/*
 * 图片扩展（需 ArkTSImageCodec 能力时启用）：
 *   import image from '@ohos.multimedia.image';
 *   const src = image.createImageSource(imageBuffer); // imageBuffer: ArrayBuffer | uri
 *   const pm = await src.createPixelMap({ ... });
 *   this.pixelMap = pm; // @State pixelMap: PixelMap
 */
