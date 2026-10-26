/*
 * 端侧 AI 图片搜索：图片 OCR 文字识别 + 关键词匹配搜图（构建块 · 未接线，翻写 NEXT）
 * 概念来源：LiuweiweiAiImageSearch（Java API8 ohos.ai.cv.text 端侧 CV 引擎 + ohos.ai.nlu 端侧分词）
 *   旧代逻辑：相册图片 → ITextDetector 端侧 OCR 出每张图文字 → 用户输入关键词 → NluClient 本地分词 → 关键词匹配图片文字 → 高亮命中图
 * 翻写：@kit.CoreVisionKit textRecognition（端侧 OCR，NEXT 原生）；分词 NEXT 无原生 NLU 包，块内给基础切分 + 建议接 @kit.MLKit / 自建词典
 * 适老化：拍书页/道藏图 → 端侧 OCR → 输关键词搜句（离线、不传云、不耗流量、长辈隐私好）
 * 权限：OCR 读的是已选图片（PixelMap/URI），无需相机权限；从相册选图走系统 Picker 即可
 */
import { textRecognition } from '@kit.CoreVisionKit';
import { image } from '@kit.ImageKit';

export interface SearchImage {
  uri: string;
  /** 该图已识别出的文字（调用 ocrImage 后回填，或外部预先提供） */
  text: string;
}

export class ImageKeywordSearch {
  /**
   * 端侧 OCR：对一张图识别文字（不传云）
   * @param src 图片 URI 或已解码的 PixelMap
   * @returns 识别出的整段文字；失败返回 ''
   */
  static async ocrImage(src: string | image.PixelMap): Promise<string> {
    try {
      const visionInfo: textRecognition.VisionInfo = {};
      if (typeof src === 'string') {
        const pm: image.PixelMap = image.createImageSource(src).createPixelMap();
        visionInfo.pixelMap = pm;
      } else {
        visionInfo.pixelMap = src;
      }
      const config: textRecognition.Configuration = {
        // NEXT 端侧 OCR：无需联网、无需密钥
      };
      const result: textRecognition.VisionResult = await textRecognition.recognizeText(visionInfo, config);
      return result.value ?? '';
    } catch (e) {
      console.error(`ImageKeywordSearch.ocrImage fail: ${(e as Error).message}`);
      return '';
    }
  }

  /**
   * 关键词分词（NEXT 无原生 NLU 包，提供基础切分；生产建议接 @kit.MLKit 或自建词典）
   * 规则：去标点空白 → 英文按词、中文按单字→2字滑动窗（简易召回）
   * @param query 用户输入的检索句
   * @returns 关键词数组
   */
  static segment(query: string): string[] {
    const cleaned = query.replace(/[，。、；：！？\s]+/g, ' ').trim();
    if (!cleaned) {
      return [];
    }
    const tokens: string[] = [];
    // 英文/数字按空格成词
    for (const w of cleaned.split(' ')) {
      if (/^[A-Za-z0-9]+$/.test(w)) {
        tokens.push(w.toLowerCase());
      }
    }
    // 中文：单字 + 2字滑窗（轻量召回，非严谨分词）
    const cn = cleaned.replace(/[^一-龥]/g, '');
    for (let i = 0; i < cn.length; i++) {
      tokens.push(cn[i]);
      if (i + 1 < cn.length) {
        tokens.push(cn.slice(i, i + 2));
      }
    }
    return Array.from(new Set(tokens));
  }

  /**
   * 关键词匹配图片：任一关键词出现在图片文字中即命中
   * @param images 待检索图片（含已识别 text）
   * @param keywords segment() 产出的关键词
   * @returns 命中的图片 URI 列表（保持原序去重）
   */
  static match(images: SearchImage[], keywords: string[]): string[] {
    if (!keywords.length) {
      return [];
    }
    const hit: string[] = [];
    for (const img of images) {
      const hay = img.text.toLowerCase();
      if (keywords.some((k) => hay.includes(k.toLowerCase()))) {
        hit.push(img.uri);
      }
    }
    return hit;
  }

  /**
   * 一键管线：对图片列表批量 OCR 后按句搜图
   * @param uris 图片 URI 列表
   * @param query 检索关键词句
   */
  static async search(uris: string[], query: string): Promise<string[]> {
    const images: SearchImage[] = [];
    for (const uri of uris) {
      const text = await ImageKeywordSearch.ocrImage(uri);
      images.push({ uri, text });
    }
    return ImageKeywordSearch.match(images, ImageKeywordSearch.segment(query));
  }
}
