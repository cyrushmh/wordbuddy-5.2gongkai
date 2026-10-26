/*
 * 图片元信息 / EXIF 读取（构建块 · 未接线，翻写 NEXT）
 * 概念来源：ImageSourceExifUtils（Java API8 ohos.media.image.ImageSource + ExifUtils）
 * 翻写：@kit.ImageKit image.createImageSource + image.ExifUtils
 * 适老化：拍道藏碑帖后读 EXIF 经纬度/海拔，配合 Batch26 GeoCoder 转可读地名展示
 * 接线前：本块仅抽概念，真实场景需验证 image.ExifUtils 具体方法名与返回类型（不同 API 版本略有差异）
 */
import { image } from '@kit.ImageKit';

export class ImageMetaReader {
  /**
   * 读取图片 EXIF 经纬度
   * @param uri 图片沙箱/文件 URI（file://... 或沙箱路径）
   * @returns [纬度, 经度]，失败返回 null
   */
  static getLatLong(uri: string): [number, number] | null {
    try {
      const src = image.createImageSource(uri);
      const ll = image.ExifUtils.getLatLong(src);
      src.release();
      if (!ll || ll.length < 2) {
        return null;
      }
      return [ll[0], ll[1]]; // [lat, long]
    } catch (e) {
      console.error(`ImageMetaReader.getLatLong fail: ${(e as Error).message}`);
      return null;
    }
  }

  /**
   * 读取图片 EXIF 海拔（米），缺失时返回默认值
   */
  static getAltitude(uri: string, defaultValue: number = 0): number {
    try {
      const src = image.createImageSource(uri);
      const alt = image.ExifUtils.getAltitude(src, defaultValue);
      src.release();
      return alt;
    } catch (e) {
      console.error(`ImageMetaReader.getAltitude fail: ${(e as Error).message}`);
      return defaultValue;
    }
  }

  /**
   * 读取嵌入缩略图信息（尺寸/格式），用于快速预览不解码全图
   */
  static getThumbnailInfo(uri: string): image.ThumbnailInfo | null {
    try {
      const src = image.createImageSource(uri);
      const info = image.ExifUtils.getThumbnailInfo(src);
      src.release();
      return info ?? null;
    } catch (e) {
      console.error(`ImageMetaReader.getThumbnailInfo fail: ${(e as Error).message}`);
      return null;
    }
  }
}
