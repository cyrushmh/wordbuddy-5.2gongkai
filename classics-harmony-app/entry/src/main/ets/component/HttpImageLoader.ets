/*
 * HTTP 图片下载与解码（构建块 · 未接线，翻写 NEXT）
 * 概念来源：NetManagerHandleURL（Java API8 NetManager + HttpURLConnection GET 图片流 → ImageSource 解码 PixelMap）
 * 翻写：@kit.NetworkKit http.createHttp().request(GET) 取 ArrayBuffer → @kit.ImageKit image.createImageSource → createPixelMap
 * 适老化：远程图册/道藏图在线加载；与 B27 ImageTranscoder 衔接做缩放裁剪、与 B27 ZoomImage 衔接做放大查看；
 *          全程走标准网络栈，无三方库、可离线缓存
 * 权限：ohos.permission.INTERNET（module.json5 声明，接线前确认）
 */
import { http } from '@kit.NetworkKit';
import { image } from '@kit.ImageKit';

export class HttpImageLoader {
  /** 拉取 url 图片并解码为 PixelMap（失败返回 null） */
  async fetch(url: string): Promise<image.PixelMap | null> {
    let conn: http.HttpRequest | null = null;
    try {
      conn = http.createHttp();
      const resp = await conn.request(url, {
        method: http.RequestMethod.GET,
        connectTimeout: 10000,
        readTimeout: 10000,
      });
      if (resp.responseCode !== http.ResponseCode.OK) {
        return null;
      }
      const buf = resp.result as ArrayBuffer;
      const src = image.createImageSource(buf);
      return await src.createPixelMap();
    } catch (e) {
      console.error(`HttpImageLoader.fetch fail: ${(e as Error).message}`);
      return null;
    } finally {
      conn?.destroy();
    }
  }
}
