//! classics-rs —— 跨平台「典籍阅读 + 乱码安全解码」核心库
//!
//! 设计哲学（与移动端 TextEncoding / Linux C 工具一致）：
//!   严格 UTF-8 优先 → 失败回退 GB18030 → 仍失败则标注损失（绝不假装成功）。
//! 并且对结果做乱码指纹自检（锟斤拷 / 烫烫烫 / 屯屯屯 / □□□ / U+FFFD）。
//!
//! 该库是「一次编写、全平台运行」的载体：Rust 原生交叉编译到
//! Linux(x86-64/ARM64/RISC-V) / Windows / macOS / Web(WASM) / 嵌入式，
//! 并通过 cdylib 把同一内核导出为 C-ABI，供 C/Go/Swift/Python/Java 等绑定。

use encoding_rs::GB18030;
use std::ffi::{c_char, CString};

// ───────────────────────────────────────────────────────────
// 1. 编码安全内核
// ───────────────────────────────────────────────────────────

/// 实际采用的编码路径
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EncodingUsed {
    /// 输入严格符合 UTF-8
    Utf8,
    /// UTF-8 失败，但可无损按 GB18030 解码
    Gb18030,
    /// 两种编码都失败，已用 U+FFFD 损失性替换
    Lossy,
}

/// 已知的乱码指纹种类
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MojibakeKind {
    /// 文本中已存在 U+FFFD 替换符（很可能是更早的损坏）
    ReplacementChar,
    /// "锟斤拷"：UTF-8 的 U+FFFD 被再次按 GBK 解读的典型产物
    KunJinKao,
    /// "烫烫烫"：MSVC 调试栈填充 0xCC 被当 GBK 解读
    TangTangTang,
    /// "屯屯屯"：MSVC 未初始化堆填充 0xCD 被当 GBK 解读
    TunTunTun,
    /// "□□□"：无法映射时的最简占位
    BoxBoxBox,
    /// GBK 误读 UTF-8 时高频产物的**连续串**（如「测试」→「娴嬭瘯」）。
    ///
    /// 必要性：严格 GB18030 解码在混合编码文件上会「成功」——每个字节都能映射，
    /// 函数不报错，但产物是彻头彻尾的乱码。仅看「解码是否失败」无法识破，必须看产物面相。
    /// 这些字本身合法，但极少在正常中文里彼此相邻，故要求连续 ≥ 2 个才判定。
    GbkMisreadRun,
}

/// 解码结果
#[derive(Debug, Clone)]
pub struct DecodeResult {
    /// 解码后的文本（损失处含 U+FFFD）
    pub text: String,
    /// 实际采用的编码
    pub encoding: EncodingUsed,
    /// 是否存在无法正确还原的字节
    pub had_invalid: bool,
    /// 命中的乱码指纹（可能多个）
    pub mojibake: Vec<MojibakeKind>,
}

/// 统计一段 CJK 文本里某个字符的最长连续出现长度
fn longest_run(text: &str, ch: char) -> usize {
    let mut best = 0;
    let mut cur = 0;
    for c in text.chars() {
        if c == ch {
            cur += 1;
            if cur > best {
                best = cur;
            }
        } else {
            cur = 0;
        }
    }
    best
}

/// 乱码指纹自检：扫描文本中的经典损坏模式
pub fn detect_mojibake(text: &str) -> Vec<MojibakeKind> {
    let mut out = Vec::new();
    if text.contains('\u{FFFD}') {
        out.push(MojibakeKind::ReplacementChar);
    }
    if text.contains("锟斤拷") {
        out.push(MojibakeKind::KunJinKao);
    }
    if text.contains("烫烫烫") || longest_run(text, '烫') >= 3 {
        out.push(MojibakeKind::TangTangTang);
    }
    if text.contains("屯屯屯") || longest_run(text, '屯') >= 3 {
        out.push(MojibakeKind::TunTunTun);
    }
    if text.contains("□□□") {
        out.push(MojibakeKind::BoxBoxBox);
    }
    if has_gbk_misread_run(text) {
        out.push(MojibakeKind::GbkMisreadRun);
    }
    out
}

/// 「以 GBK/GB18030 误读 UTF-8」时高频产生的字（古文码的典型产物）。
/// 这些字本身合法，但极少在正常中文文本中**彼此相邻**出现，故要求连续 ≥ 2 个。
const GBK_MISREAD_MARKERS: [char; 14] = [
    '娴', '嬭', '瘯', '噭', '浣', '犲', 'ソ', '鐢', '湀', '銆', '垚', '畾', '锟', '拷',
];

/// 是否存在连续 ≥ 2 个 GBK 误读产物字
fn has_gbk_misread_run(text: &str) -> bool {
    let mut run: usize = 0;
    for ch in text.chars() {
        if GBK_MISREAD_MARKERS.contains(&ch) {
            run += 1;
            if run >= 2 {
                return true;
            }
        } else {
            run = 0;
        }
    }
    false
}

/// 乱码安全解码：严格 UTF-8 → 回退 GB18030 → 仍失败则损失性替换并标注。
///
/// 这是本工具链在所有平台共享的核心函数。
pub fn decode_safe(bytes: &[u8]) -> DecodeResult {
    // 1) 严格 UTF-8（Rust 的 from_utf8 即为严格校验）
    if std::str::from_utf8(bytes).is_ok() {
        let text = String::from_utf8_lossy(bytes).into_owned();
        let moji = detect_mojibake(&text);
        return DecodeResult {
            text,
            encoding: EncodingUsed::Utf8,
            had_invalid: false,
            mojibake: moji,
        };
    }
    // 2) 回退 GB18030（GB18030 可映射全部 Unicode，故合法输入不会引入 U+FFFD）
    let (cow, had_errors) = GB18030.decode_without_bom_handling(bytes);
    let text = cow.into_owned();
    let (encoding, had_invalid) = if had_errors {
        (EncodingUsed::Lossy, true)
    } else {
        (EncodingUsed::Gb18030, false)
    };
    let moji = detect_mojibake(&text);
    DecodeResult {
        text,
        encoding,
        had_invalid,
        mojibake: moji,
    }
}

/// 对一段已解码文本做乱码指纹体检（对应 CLI 的 `lint`）
pub fn lint_text(text: &str) -> String {
    let hits = detect_mojibake(text);
    if hits.is_empty() {
        "OK: 未发现已知乱码指纹".to_string()
    } else {
        let names: Vec<&str> = hits
            .iter()
            .map(|k| match k {
                MojibakeKind::ReplacementChar => "U+FFFD替换符",
                MojibakeKind::KunJinKao => "锟斤拷(UTF-8/GBK二重损坏)",
                MojibakeKind::TangTangTang => "烫烫烫(MSVC栈填充0xCC)",
                MojibakeKind::TunTunTun => "屯屯屯(MSVC堆填充0xCD)",
                MojibakeKind::BoxBoxBox => "□□□(占位)",
                MojibakeKind::GbkMisreadRun => "GBK误读UTF-8(混合编码)",
            })
            .collect();
        format!("WARN: 命中乱码指纹 -> {}", names.join(", "))
    }
}

// ───────────────────────────────────────────────────────────
// 2. 典籍数据（内嵌样本，保证二进制自包含；WASM/Web 亦可用）
// ───────────────────────────────────────────────────────────

/// 内嵌典籍条目（编译期固化，跨平台一致）
pub struct EmbeddedEntry {
    pub id: &'static str,
    pub title: &'static str,
    pub content: &'static str,
}

/// 返回内嵌的典籍样本（与 iOS/macOS、HarmonyOS、Linux C 工具同源）
pub fn embedded_entries() -> &'static [EmbeddedEntry] {
    &[
        EmbeddedEntry {
            id: "daodejing",
            title: "道德经（节选）",
            content: include_str!("../data/daodejing.txt"),
        },
        EmbeddedEntry {
            id: "xinjing",
            title: "般若波罗蜜多心经",
            content: include_str!("../data/xinjing.txt"),
        },
        EmbeddedEntry {
            id: "daodejing-daozang",
            title: "道德经（道藏无注本·河上公分章）",
            content: include_str!("../data/daodejing-daozang.txt"),
        },
        EmbeddedEntry {
            id: "huangting-neijing",
            title: "黄庭内景经（太上黄庭内景玉经）",
            content: include_str!("../data/huangting-neijing.txt"),
        },
        EmbeddedEntry {
            id: "huangting-waijing",
            title: "黄庭外景经（太上黄庭外景玉经）",
            content: include_str!("../data/huangting-waijing.txt"),
        },
        EmbeddedEntry {
            id: "huangting-shuangjing",
            title: "黄庭经（内外双景合参·蒋慎修经解）",
            content: include_str!("../data/huangting-shuangjing.txt"),
        },
    ]
}

/// 运行期加载：优先用环境变量 CLASSICS_DATADIR 指向的目录（原生平台），
/// 否则回退到内嵌样本。文件系统访问在非 wasm 平台才启用。
#[cfg(not(target_arch = "wasm32"))]
pub fn list_entries() -> Vec<(String, String)> {
    if let Ok(dir) = std::env::var("CLASSICS_DATADIR") {
        if let Ok(entries) = std::fs::read_dir(&dir) {
            let mut v: Vec<(String, String)> = entries
                .filter_map(|e| e.ok())
                .filter_map(|e| {
                    let p = e.path();
                    if p.extension().map(|x| x == "txt").unwrap_or(false) {
                        let name = p.file_stem()?.to_string_lossy().to_string();
                        let content = std::fs::read_to_string(&p).ok()?;
                        let title = content.lines().next().unwrap_or("").to_string();
                        Some((name, title))
                    } else {
                        None
                    }
                })
                .collect();
            if !v.is_empty() {
                v.sort();
                return v;
            }
        }
    }
    embedded_entries()
        .iter()
        .map(|e| (e.id.to_string(), e.title.to_string()))
        .collect()
}

/// wasm 平台无文件系统，始终返回内嵌样本
#[cfg(target_arch = "wasm32")]
pub fn list_entries() -> Vec<(String, String)> {
    embedded_entries()
        .iter()
        .map(|e| (e.id.to_string(), e.title.to_string()))
        .collect()
}

/// 按 id 取正文（运行期，含 DATADIR 覆盖）
#[cfg(not(target_arch = "wasm32"))]
pub fn get_entry(id: &str) -> Option<String> {
    if let Ok(dir) = std::env::var("CLASSICS_DATADIR") {
        let p = std::path::Path::new(&dir).join(format!("{id}.txt"));
        if let Ok(c) = std::fs::read_to_string(&p) {
            return Some(c);
        }
    }
    embedded_entries()
        .iter()
        .find(|e| e.id == id)
        .map(|e| e.content.to_string())
}

#[cfg(target_arch = "wasm32")]
pub fn get_entry(id: &str) -> Option<String> {
    embedded_entries()
        .iter()
        .find(|e| e.id == id)
        .map(|e| e.content.to_string())
}

// ───────────────────────────────────────────────────────────
// 3. C-ABI 导出（cdylib）：供 C / Go / Swift / Python / Java 等语言绑定
//    也作为 WASM 的导出符号，配合手写 JS 胶水使用。
// ───────────────────────────────────────────────────────────

/// 版本字符串（C 侧需 classics_free_string 释放）
///
/// # Safety
/// 返回指针由本库分配，调用方必须配对调用 `classics_free_string`。
#[no_mangle]
pub extern "C" fn classics_version() -> *mut c_char {
    CString::new(env!("CARGO_PKG_VERSION"))
        .unwrap()
        .into_raw()
}

/// 安全解码：输入字节指针+长度，返回 C 字符串（UTF-8 文本）。
/// 失败时返回空串；调用方必须配对调用 `classics_free_string`。
///
/// # Safety
/// `ptr` 必须指向长度至少为 `len` 的有效内存。
#[no_mangle]
pub unsafe extern "C" fn classics_decode(ptr: *const u8, len: usize) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("").unwrap().into_raw();
    }
    let bytes = std::slice::from_raw_parts(ptr, len);
    let r = decode_safe(bytes);
    CString::new(r.text).unwrap_or_else(|_| CString::new("").unwrap()).into_raw()
}

/// 释放本库返回的 C 字符串。
///
/// # Safety
/// `ptr` 必须来自本库的 `classics_version` / `classics_decode`。
#[no_mangle]
pub unsafe extern "C" fn classics_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        let _ = CString::from_raw(ptr);
    }
}

/// 库版本（Rust 侧常量，便于内部/测试使用）
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

// ───────────────────────────────────────────────────────────
// 4. WASM 专属：零依赖的输入/输出缓冲区（无需 wasm-bindgen）
//    浏览器/Node 通过固定内存区把字节送入内核，再读回结果。
// ───────────────────────────────────────────────────────────

#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub static mut CLASSICS_INBUF: [u8; 65536] = [0u8; 65536];

#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub static mut CLASSICS_OUTBUF: [u8; 65536] = [0u8; 65536];

#[cfg(target_arch = "wasm32")]
const BUF: usize = 65536;

/// 返回输入缓冲区首地址（JS 据此把字节写入 wasm 线性内存）
#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub extern "C" fn classics_inbuf_ptr() -> *mut u8 {
    unsafe { CLASSICS_INBUF.as_mut_ptr() }
}

/// 返回输出缓冲区首地址（JS 据此读回解码文本）
#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub extern "C" fn classics_outbuf_ptr() -> *mut u8 {
    unsafe { CLASSICS_OUTBUF.as_mut_ptr() }
}

/// 解码输入缓冲区前 `len` 字节，结果写入输出缓冲区并以 0 结尾，
/// 返回结果字节长度（不含结尾 0）。
#[cfg(target_arch = "wasm32")]
#[no_mangle]
pub extern "C" fn classics_decode_inbuf(len: usize) -> usize {
    let len = len.min(BUF);
    let input = unsafe { &CLASSICS_INBUF[..len] };
    let r = decode_safe(input);
    let bytes = r.text.as_bytes();
    let n = bytes.len().min(BUF - 1);
    unsafe {
        CLASSICS_OUTBUF[..n].copy_from_slice(&bytes[..n]);
        CLASSICS_OUTBUF[n] = 0;
    }
    n
}

/// 编码枚举的人读名称（供输出）
pub fn encoding_name(e: EncodingUsed) -> &'static str {
    match e {
        EncodingUsed::Utf8 => "utf-8",
        EncodingUsed::Gb18030 => "gb18030",
        EncodingUsed::Lossy => "lossy",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn detects_gbk_misread_run() {
        let s = "中国GBK娴嬭瘯";
        assert!(has_gbk_misread_run(s), "应检出连续误读产物字");
        assert!(detect_mojibake(s).contains(&MojibakeKind::GbkMisreadRun));
    }
    #[test]
    fn no_false_positive_on_normal_text() {
        assert!(!has_gbk_misread_run("涓涓细流，汇成江海。拷问本心，辨别是非。"));
        assert!(!has_gbk_misread_run("道德经：道可道，非常道。"));
    }
}
