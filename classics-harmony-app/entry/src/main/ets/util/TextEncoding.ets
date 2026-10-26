/**
 * 编码安全导入工具（呼应 justjavac/unicode-encoding-error-table 的「中文乱码速查表」）。
 *
 * 古籍 / 外部文本常以错误编码读取，产生典型乱码：
 *   - 古文码：以 GBK 方式读 UTF-8（鐢辨湀…）
 *   - 口字码：以 UTF-8 方式读 GBK（□□□）
 *   - 符号码 / 拼音码：以 ISO8859-1 读 UTF-8 或 GBK（ç”±æœˆ…）
 *   - 问句码：GBK 读 UTF-8 后再以 UTF-8 读（末尾变 ?）
 *   - 锟拷码：UTF-8 读 GBK 再以 GBK 读（锟斤拷…）
 *
 * 本工具策略（绝不崩溃，宁可缺字不崩）：
 *   1. 有 UTF-8 BOM（EF BB BF）先剥离；
 *   2. 严格 UTF-8 解码，成功即用；
 *   3. 否则严格 GB18030 解码（国家标准的 GBK 超集）；
 *   4. 两者皆失败，逐字节有损修复，非法序列统一替换为 U+FFFD。
 *
 * 注意：经典文本一律以 UTF-8（`original`/`translation` 字段）内嵌于工程中；
 * 本工具专门用于「用户从外部导入 txt/epub 纯文本」的入口，防止错配编码污染正文。
 */
import { util } from '@kit.ArkTS';

/** 严格解码：成功返回字符串，失败返回 null（不抛到调用方）。 */
function strictDecode(bytes: Uint8Array, label: string): string | null {
  try {
    const decoder = new util.TextDecoder(label, { fatal: true, ignoreBOM: false });
    return decoder.decodeToString(bytes);
  } catch (e) {
    return null;
  }
}

/** 有损兜底：非严格 UTF-8（ICU 把非法字节转成 U+FFFD）；失败再逐字节修复。 */
function lossyRepair(bytes: Uint8Array): string {
  try {
    const decoder = new util.TextDecoder('utf-8', { fatal: false, ignoreBOM: false });
    return decoder.decodeToString(bytes);
  } catch (e) {
    let out = '';
    for (let i = 0; i < bytes.length; i++) {
      const b = bytes[i];
      // ASCII 直出；其余（无法成合法 UTF-8 的）用替换符
      if (b >= 0x20 && b < 0x7f) {
        out += String.fromCharCode(b);
      } else {
        out += '�';
      }
    }
    return out;
  }
}

/**
 * 安全解码外部字节流为字符串。
 * @param bytes 文件读取得到的字节数组
 * @returns 解码后的文本；任何编码异常都不会抛出
 */
export function decodeTextSafe(bytes: Uint8Array): string {
  // 1. 剥离 UTF-8 BOM
  let data = bytes;
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    data = bytes.subarray(3);
  }
  // 2. 严格 UTF-8
  const utf8 = strictDecode(data, 'utf-8');
  if (utf8 !== null) {
    return utf8;
  }
  // 3. 严格 GB18030（GBK 超集，覆盖繁体/生僻字更全）
  const gbk = strictDecode(data, 'gb18030');
  if (gbk !== null) {
    return gbk;
  }
  // 4. 有损兜底
  return lossyRepair(data);
}

/**
 * 乱码特征自检：供导入预览时提示用户「该文本疑似编码错配」。
 * 命中任一典型乱码指纹即返回 true（如「锟斤拷」「烫烫烫」「屯屯屯」）。
 */
export function looksLikeMojibake(text: string): boolean {
  const fingerprints = ['锟斤拷', '烫烫烫', '屯屯屯', '����', 'ç”±', '□□□'];
  return fingerprints.some((fp) => text.includes(fp));
}
