import Foundation
#if canImport(Glibc)
import Glibc
#endif

/// 编码安全导入工具（呼应 justjavac/unicode-encoding-error-table 的「中文乱码速查表」）。
///
/// 古籍 / 外部文本常以错误编码读取，产生典型乱码：
///   - 古文码：以 GBK 方式读 UTF-8（鐢辨湀…）
///   - 口字码：以 UTF-8 方式读 GBK（□□□）
///   - 符号码 / 拼音码：以 ISO8859-1 读 UTF-8 或 GBK（ç”±æœˆ…）
///   - 问句码：GBK 读 UTF-8 后再以 UTF-8 读（末尾变 ?）
///   - 锟拷码：UTF-8 读 GBK 再以 GBK 读（锟斤拷…）
///
/// 策略（绝不崩溃，宁可缺字不崩）：
///   1. 有 UTF-8 BOM（EF BB BF）先剥离；
///   2. 严格 UTF-8 解码，成功即用；
///   3. 否则严格 GB18030 解码（国家标准的 GBK 超集）；
///   4. 两者皆失败，有损修复（无效字节替换为 U+FFFD）。
///
/// 经典文本一律以 UTF-8 内嵌于工程；本工具专用于「用户从外部导入 txt 纯文本」入口，
/// 防止错配编码污染正文。
public enum TextEncoding {
    /// 安全解码外部字节流为字符串。任何编码异常都不会抛出。
    public static func decodeSafe(_ bytes: Data) -> String {
        // 1. 剥离 UTF-8 BOM
        var data = bytes
        if bytes.count >= 3, bytes[0] == 0xEF, bytes[1] == 0xBB, bytes[2] == 0xBF {
            data = bytes.subdata(in: 3..<bytes.count)
        }
        // 2. 严格 UTF-8（无效即返回 nil）
        if let s = String(data: data, encoding: .utf8) {
            return s
        }
        // 3. 严格 GB18030（GBK 超集）
        //    Apple 平台走 CoreFoundation 的编码表；Linux（swift-corelibs-foundation 无 CFString
        //    私有编码表）走 glibc iconv。两者语义一致：遇非法字节即整体失败，不做有损替换。
#if canImport(Glibc)
        if let s = decodeGB18030ViaIconv(data) {
            return s
        }
#else
        let cfEnc = CFStringConvertEncodingToNSStringEncoding(
            CFStringEncoding(CFStringEncodings.GB_18030_2000.rawValue))
        let nsEnc = String.Encoding(rawValue: cfEnc)
        if let s = String(data: data, encoding: nsEnc) {
            return s
        }
#endif
        // 4. 有损兜底：无效字节替换为 U+FFFD（替换字符）
        return String(decoding: data, as: UTF8.self)
    }

#if canImport(Glibc)
    /// Linux 路径：用 glibc iconv 做**严格** GB18030→UTF-8 转换。
    /// 严格的含义：输入中只要有一个字节无法映射，整体返回 nil，落回外层第 4 步的有损兜底，
    /// 与 CoreFoundation 的 `String(data:encoding:)` 语义对齐（不做半途替换）。
    private static func decodeGB18030ViaIconv(_ data: Data) -> String? {
        guard let cd = iconv_open("UTF-8", "GB18030") else { return nil }
        defer { iconv_close(cd) }

        var inBytes = [UInt8](data)
        let inLen = inBytes.count
        guard inLen > 0 else { return "" }

        // GB18030 最坏情况：2 字节汉字 → 3 字节 UTF-8；4 字节区 → 至多 4 字节 UTF-8。
        // 取 4 倍 + 16 余量足以容纳。
        var outBuf = [UInt8](repeating: 0, count: inLen * 4 + 16)
        let outCap = outBuf.count
        var outLeft = outCap
        var ok = false

        inBytes.withUnsafeMutableBytes { inRaw in
            var inPtr = inRaw.baseAddress?.assumingMemoryBound(to: CChar.self)
            var inLeft = inLen
            outBuf.withUnsafeMutableBytes { outRaw in
                var outPtr = outRaw.baseAddress?.assumingMemoryBound(to: CChar.self)
                let r = iconv(cd, &inPtr, &inLeft, &outPtr, &outLeft)
                // iconv 返回 (size_t)-1 表示失败；成功时输入应被完全消耗。
                ok = (r != UInt.max) && inLeft == 0
            }
        }
        guard ok else { return nil }
        return String(decoding: outBuf.prefix(outCap - outLeft), as: UTF8.self)
    }
#endif

    /// 「以 GBK/GB18030 误读 UTF-8」时高频产生的字（即「古文码」的典型产物）。
    ///
    /// 这些字本身是合法汉字，但极少在正常中文文本中**彼此相邻**出现。
    /// 之所以需要这条启发式：严格 GB18030 解码在遇到混合编码文件时会「成功」——
    /// 每个字节都能映射，函数不返回 nil，但产物是彻头彻尾的乱码（实测：UTF-8 的
    /// 「测试」被读作「娴嬭瘯」）。仅靠「解码是否失败」无法识破，必须看产物面相。
    private static let gbkMisreadMarkers: Set<Character> =
        ["娴", "嬭", "瘯", "噭", "浣", "犲", "ソ", "鐢", "湀", "銆", "垚", "畾", "锟", "拷"]

    /// 乱码特征自检：供导入预览时提示用户「该文本疑似编码错配」。
    public static func looksLikeMojibake(_ text: String) -> Bool {
        let fingerprints = ["锟斤拷", "烫烫烫", "屯屯屯", "����", "ç”±", "□□□"]
        if fingerprints.contains(where: text.contains) { return true }
        // 连续相邻的误读产物字 ≥ 2 个即判定错配（单字可能是正常用词，成串几乎不可能是）
        var run = 0
        for ch in text {
            if gbkMisreadMarkers.contains(ch) {
                run += 1
                if run >= 2 { return true }
            } else {
                run = 0
            }
        }
        return false
    }
}
