//! classics CLI —— 与 Linux C 工具、iOS/macOS、HarmonyOS 同源的命令面。
//! 仅原生平台启用（wasm 下不提供命令行入口）。

use classics::{decode_safe, embedded_entries, get_entry, lint_text, list_entries, encoding_name};
use std::io::Read;
use std::process::exit;

#[cfg(not(target_arch = "wasm32"))]
fn real_main() -> i32 {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("classics {} — 典籍阅读与乱码安全解码", classics::VERSION);
        eprintln!("用法:");
        eprintln!("  classics list                      列出已安装典籍");
        eprintln!("  classics show <book> [chapter]      显示典籍正文");
        eprintln!("  classics decode <file>              乱码安全解码文件");
        eprintln!("  classics lint <file>                乱码指纹体检");
        eprintln!("\n环境变量 CLASSICS_DATADIR 可覆盖样本数据目录（原生平台）。");
        return 1;
    }
    match args[1].as_str() {
        "list" => {
            println!("已安装典籍：");
            for (id, title) in list_entries() {
                println!("  {}  —  {}", id, title);
            }
            0
        }
        "show" => {
            if args.len() < 3 {
                eprintln!("用法: classics show <book> [chapter]");
                return 1;
            }
            match get_entry(&args[2]) {
                Some(text) => {
                    println!("{}", text);
                    0
                }
                None => {
                    eprintln!("classics: 未找到典籍 '{}'", args[2]);
                    1
                }
            }
        }
        "decode" => {
            if args.len() < 3 {
                eprintln!("用法: classics decode <file>");
                return 1;
            }
            let mut buf = Vec::new();
            match std::fs::File::open(&args[2]).and_then(|mut f| f.read_to_end(&mut buf)) {
                Ok(_) => {
                    let r = decode_safe(&buf);
                    println!("{}", r.text);
                    eprintln!(
                        "[classics] 编码={} 损失={} 乱码指纹={:?}",
                        encoding_name(r.encoding),
                        r.had_invalid,
                        r.mojibake
                    );
                    0
                }
                Err(e) => {
                    eprintln!("classics: 无法读取 {}: {}", args[2], e);
                    1
                }
            }
        }
        "lint" => {
            if args.len() < 3 {
                eprintln!("用法: classics lint <file>");
                return 1;
            }
            let mut buf = Vec::new();
            match std::fs::File::open(&args[2]).and_then(|mut f| f.read_to_end(&mut buf)) {
                Ok(_) => {
                    let r = decode_safe(&buf);
                    println!("{}", lint_text(&r.text));
                    0
                }
                Err(e) => {
                    eprintln!("classics: 无法读取 {}: {}", args[2], e);
                    1
                }
            }
        }
        "embedded" => {
            // 调试用：打印内嵌样本 id 列表
            for e in embedded_entries() {
                println!("{}  —  {}", e.id, e.title);
            }
            0
        }
        other => {
            eprintln!("classics: 未知命令 '{}'", other);
            1
        }
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn main() {
    exit(real_main());
}

#[cfg(target_arch = "wasm32")]
fn main() {
    // wasm 下由 JS 胶水通过导出的 C-ABI 调用，无命令行入口
}
