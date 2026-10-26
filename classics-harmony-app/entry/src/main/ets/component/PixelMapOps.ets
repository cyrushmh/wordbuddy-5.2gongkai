/*
 * 位图像素操作（构建块 · 未接线，翻写 NEXT）
 * 概念来源：PixelMap（Java API8 ohos.media.image.PixelMap create / readPixel / writePixel / getPixelBytesCapacity）
 * 翻写：@kit.ImageKit image.createPixelMap(InitializationOptions) + PixelMap.readPixels / writePixels
 * 适老化：老人批注/水印道藏图、程序化生成缩略图或拼图底图；与 B27 ImageTranscoder 衔接做落盘保存
 * 权限：无（纯内存位图操作；若要把结果写文件才需存储权限）
 * 注：NEXT PixelMap 像素读写 API 名称以官方文档为准（createPixelMap / readPixels / writePixels），本块为模式骨架待接线核验
 */
import { image } from '@kit.ImageKit';

export class PixelMapOps {
  /** 由颜色数组创建可编辑位图（colors 长度须 = 宽×高，每像素一个 ARGB int） */
  static create(colors: ArrayBuffer | number[], w: number, h: number): image.PixelMap | null {
    const opts: image.InitializationOptions = {
      size: { width: w, height: h },
      pixelFormat: image.PixelFormat.RGBA_8888,
      editable: true,
    };
    try {
      return image.createPixelMap(colors as ArrayBuffer, opts);
    } catch (e) {
      console.error(`PixelMapOps.create fail: ${(e as Error).message}`);
      return null;
    }
  }

  /** 由已有位图克隆一份可编辑副本 */
  static clone(src: image.PixelMap): image.PixelMap | null {
    const opts: image.InitializationOptions = {
      size: { width: src.getImageInfoSync().size.width, height: src.getImageInfoSync().size.height },
      pixelFormat: image.PixelFormat.RGBA_8888,
      editable: true,
    };
    try {
      return image.createPixelMap(src, opts);
    } catch (e) {
      console.error(`PixelMapOps.clone fail: ${(e as Error).message}`);
      return null;
    }
  }

  /** 读取指定坐标像素颜色（返回 ARGB int） */
  static readAt(pm: image.PixelMap, x: number, y: number): number {
    const buf = new ArrayBuffer(4);
    try {
      pm.readPixels({ x, y, width: 1, height: 1 }, buf);
      return new DataView(buf).getUint32(0, true);
    } catch (e) {
      console.error(`PixelMapOps.readAt fail: ${(e as Error).message}`);
      return 0;
    }
  }

  /** 在指定坐标写入像素颜色（color 为 ARGB int） */
  static writeAt(pm: image.PixelMap, x: number, y: number, color: number): void {
    try {
      const buf = new ArrayBuffer(4);
      new DataView(buf).setUint32(0, color, true);
      pm.writePixels({ x, y, width: 1, height: 1 }, buf);
    } catch (e) {
      console.error(`PixelMapOps.writeAt fail: ${(e as Error).message}`);
    }
  }

  /** 读取整图字节容量 / 行字节数（裁剪或调参预判用） */
  static info(pm: image.PixelMap): { capacity: number; rowBytes: number } {
    return { capacity: pm.getPixelBytesCapacity(), rowBytes: pm.getBytesNumberPerRow() };
  }

  /** 释放位图（aboutToDisappear / 页面销毁时调，避免内存泄漏） */
  static release(pm: image.PixelMap | null): void {
    pm?.release();
  }
}
