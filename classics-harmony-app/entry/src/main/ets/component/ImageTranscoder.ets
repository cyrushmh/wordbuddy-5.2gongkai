/*
 * 图片转码：解码（缩放/裁剪/旋转）+ 编码（压缩保存）（构建块 · 未接线，翻写 NEXT）
 * 概念来源：ImageCodec（Java API8 ohos.media.image.ImageSource 解码 + ImagePacker 编码）
 * 翻写：@kit.ImageKit image.createImageSource + image.packToFile / DecodingOptions / PackingOptions
 * 适老化：道藏图离线下载后压缩为缩略图、按屏宽裁剪，省存储、长辈端加载快不冻屏
 */
import { image } from '@kit.ImageKit';

export class ImageTranscoder {
  /**
   * 解码图片并按尺寸/区域/旋转输出 PixelMap
   * @param uri 图片 URI
   * @param opts size=[宽,高] 目标尺寸；region=[x,y,宽,高] 裁剪区域；rotate 旋转角度
   */
  static decode(
    uri: string,
    opts: { size?: [number, number]; region?: [number, number, number, number]; rotate?: number } = {}
  ): image.PixelMap | null {
    try {
      const src = image.createImageSource(uri);
      const decodingOpts: image.DecodingOptions = {};
      if (opts.size) {
        decodingOpts.desiredSize = { width: opts.size[0], height: opts.size[1] };
      }
      if (opts.region) {
        const [x, y, w, h] = opts.region;
        decodingOpts.desiredRegion = { x, y, width: w, height: h };
      }
      if (opts.rotate !== undefined) {
        decodingOpts.rotateDegrees = opts.rotate;
      }
      const pm = src.createPixelMap(decodingOpts);
      src.release();
      return pm;
    } catch (e) {
      console.error(`ImageTranscoder.decode fail: ${(e as Error).message}`);
      return null;
    }
  }

  /**
   * 将 PixelMap 编码为 JPEG 文件（指定质量 0-100，100 最佳）
   * @returns 目标文件 URI，失败返回 ''
   */
  static async encodeToFile(pixelMap: image.PixelMap, targetUri: string, quality: number = 90): Promise<string> {
    try {
      const packOpts: image.PackingOptions = { format: 'image/jpeg', quality };
      await image.packToFile(pixelMap, targetUri, packOpts);
      return targetUri;
    } catch (e) {
      console.error(`ImageTranscoder.encodeToFile fail: ${(e as Error).message}`);
      return '';
    }
  }
}
