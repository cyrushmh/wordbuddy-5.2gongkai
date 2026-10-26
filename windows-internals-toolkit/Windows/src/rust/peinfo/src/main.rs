//! 稳定版 Rust（edition 2021）实现的 PE 头查看器，纯标准库、零第三方依赖。
//! 默认解析自身，也可 `peinfo <文件>`。与 C 版 peinfo / Python 版 pe_inspect 同源同义。
//! `--json` 输出机器可读 JSON，便于自动化与跨语言一致性校验。

use std::env;
use std::fs;
use std::process;

fn rd_u16(b: &[u8], off: usize) -> u16 {
    u16::from_le_bytes([b[off], b[off + 1]])
}
fn rd_u32(b: &[u8], off: usize) -> u32 {
    u32::from_le_bytes([b[off], b[off + 1], b[off + 2], b[off + 3]])
}
fn rd_u64(b: &[u8], off: usize) -> u64 {
    let mut a = [0u8; 8];
    a.copy_from_slice(&b[off..off + 8]);
    u64::from_le_bytes(a)
}

fn machine_name(m: u16) -> &'static str {
    match m {
        0x14c => "x86 (80386)",
        0x8664 => "x64 (AMD64)",
        0x1c0 => "ARM (32-bit)",
        0xaa64 => "ARM64",
        0x200 => "Intel Itanium",
        _ => "未知",
    }
}

fn subsystem_name(s: u16) -> &'static str {
    match s {
        1 => "Native",
        2 => "Windows GUI",
        3 => "Windows CUI (控制台)",
        7 => "POSIX CUI",
        9 => "Windows CE GUI",
        10 => "EFI 应用程序",
        12 => "EFI 启动服务驱动",
        13 => "EFI 运行时驱动",
        14 => "EFI ROM",
        16 => "XBOX",
        _ => "未知",
    }
}

const DATA_DIRS: [&str; 16] = [
    "Export", "Import", "Resource", "Exception", "Security", "BaseRelocation", "Debug",
    "Architecture", "GlobalPtr", "TLS", "LoadConfig", "BoundImport", "IAT", "DelayImport",
    "COMDescriptor", "Reserved",
];

fn section_chars(c: u32) -> String {
    let mut v = Vec::new();
    if c & 0x20 != 0 { v.push("CODE"); }
    if c & 0x40 != 0 { v.push("INIT_DATA"); }
    if c & 0x80 != 0 { v.push("UNINIT_DATA"); }
    if c & 0x20000000 != 0 { v.push("EXECUTE"); }
    if c & 0x40000000 != 0 { v.push("READ"); }
    if c & 0x80000000 != 0 { v.push("WRITE"); }
    v.join("|")
}

/// 把节名转成 JSON 字符串字面量（转义引号与反斜杠）。
fn json_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            _ => out.push(c),
        }
    }
    out.push('"');
    out
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let want_json = args.iter().any(|a| a == "--json");
    let target = if args.len() > 1 {
        // 跳过 args[0]（程序名），取第一个非 --json 参数作为文件路径
        args.iter()
            .skip(1)
            .find(|a| a.as_str() != "--json")
            .cloned()
            .unwrap_or_else(|| "self".to_string())
    } else {
        match env::current_exe() {
            Ok(p) => p.to_string_lossy().into_owned(),
            Err(_) => {
                eprintln!("用法: peinfo <文件.exe> [--json]");
                process::exit(1);
            }
        }
    };

    let bytes = match fs::read(&target) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("无法读取 {}: {}", target, e);
            process::exit(1);
        }
    };

    if bytes.len() < 0x40 || &bytes[0..2] != b"MZ" {
        eprintln!("不是合法的 PE（缺少 MZ 头）: {}", target);
        process::exit(1);
    }

    let e_lfanew = rd_u32(&bytes, 0x3C) as usize;
    if e_lfanew + 4 > bytes.len() || &bytes[e_lfanew..e_lfanew + 4] != b"PE\0\0" {
        eprintln!("缺少 PE\\0\\0 签名");
        process::exit(1);
    }

    let coff = e_lfanew + 4;
    let machine = rd_u16(&bytes, coff);
    let nsec = rd_u16(&bytes, coff + 2);
    let tds = rd_u32(&bytes, coff + 4);
    let optsize = rd_u16(&bytes, coff + 16);
    let characteristics = rd_u16(&bytes, coff + 18);

    let opt = coff + 20;
    let magic = rd_u16(&bytes, opt);
    let pe32plus = magic == 0x20B;
    let (imagebase, entry) = if pe32plus {
        (rd_u64(&bytes, opt + 24), rd_u32(&bytes, opt + 16))
    } else {
        (rd_u32(&bytes, opt + 28) as u64, rd_u32(&bytes, opt + 16))
    };
    let subsystem = rd_u16(&bytes, opt + 68);
    let num_rva_off = if pe32plus { opt + 108 } else { opt + 92 };
    let num_rva = rd_u32(&bytes, num_rva_off) as usize;
    let dd_start = if pe32plus { opt + 112 } else { opt + 96 };

    let sec_start = opt + optsize as usize;

    if want_json {
        let mut s = String::new();
        s.push('{');
        s.push_str(&format!("\"e_lfanew\":{},", e_lfanew));
        s.push_str(&format!("\"machine\":{},", machine));
        s.push_str(&format!("\"machine_name\":{},", json_str(machine_name(machine))));
        s.push_str(&format!("\"number_of_sections\":{},", nsec));
        s.push_str(&format!("\"time_date_stamp\":{},", tds));
        s.push_str(&format!("\"size_of_optional_header\":{},", optsize));
        s.push_str(&format!("\"characteristics\":{},", characteristics));
        s.push_str("\"optional\":{");
        s.push_str(&format!("\"magic\":{},", magic));
        s.push_str(&format!("\"entry_point\":{},", entry));
        s.push_str(&format!("\"image_base\":{},", imagebase));
        s.push_str(&format!("\"subsystem\":{},", subsystem));
        s.push_str(&format!("\"number_of_rva_and_sizes\":{}", num_rva));
        s.push_str("},");
        // 数据目录
        s.push_str("\"data_directories\":[");
        let n = num_rva.min(16);
        let mut dirs = Vec::with_capacity(n);
        for i in 0..n {
            let base = dd_start + i * 8;
            let va = rd_u32(&bytes, base);
            let size = rd_u32(&bytes, base + 4);
            dirs.push(format!(
                "{{\"index\":{},\"name\":{},\"rva\":{},\"size\":{}}}",
                i, json_str(DATA_DIRS[i]), va, size
            ));
        }
        s.push_str(&dirs.join(","));
        s.push_str("],");
        // 节表
        s.push_str("\"sections\":[");
        let mut secs: Vec<String> = Vec::new();
        for i in 0..nsec as usize {
            let sp = sec_start + i * 40;
            if sp + 40 > bytes.len() {
                break;
            }
            let mut name = String::new();
            for k in 0..8 {
                let c = bytes[sp + k];
                if c == 0 {
                    break;
                }
                name.push(c as char);
            }
            let vsize = rd_u32(&bytes, sp + 8);
            let vaddr = rd_u32(&bytes, sp + 12);
            let rawsize = rd_u32(&bytes, sp + 16);
            let rawptr = rd_u32(&bytes, sp + 20);
            let chars = rd_u32(&bytes, sp + 36);
            secs.push(format!(
                "{{\"index\":{},\"name\":{},\"virtual_size\":{},\"virtual_address\":{},\"size_of_raw_data\":{},\"pointer_to_raw_data\":{},\"characteristics\":{}}}",
                i, json_str(&name), vsize, vaddr, rawsize, rawptr, chars
            ));
        }
        s.push_str(&secs.join(","));
        s.push_str("]}");
        println!("{}", s);
        return;
    }

    // 人类可读输出
    println!("== {} ==", target);
    println!("MZ 签名: 是 | e_lfanew = {:#x}", e_lfanew);
    println!("PE 签名: PE\\0\\0");
    println!("Machine      : {:#06x} ({})", machine, machine_name(machine));
    println!("节数          : {}", nsec);
    println!("Magic        : {:#06x} ({})", magic, if pe32plus { "PE32+" } else { "PE32" });
    println!("EntryPoint   : {:#x}", entry);
    println!("ImageBase    : {:#x}", imagebase);
    println!("Subsystem    : {} ({})", subsystem, subsystem_name(subsystem));
    let dll = if characteristics & 0x2000 != 0 { " (DLL)" } else { "" };
    println!("Characteristics: {:#06x}{}", characteristics, dll);

    println!("\n--- 数据目录 (最多 16) ---");
    let n = num_rva.min(16);
    for i in 0..n {
        let base = dd_start + i * 8;
        let va = rd_u32(&bytes, base);
        let size = rd_u32(&bytes, base + 4);
        println!("{:2}. {:<14} va={:#010x} size={:#x}", i, DATA_DIRS[i], va, size);
    }

    println!("\n--- 节表 ---");
    for i in 0..nsec as usize {
        let sp = sec_start + i * 40;
        if sp + 40 > bytes.len() {
            break;
        }
        let mut name = String::new();
        for k in 0..8 {
            let c = bytes[sp + k];
            if c == 0 {
                break;
            }
            name.push(c as char);
        }
        let vsize = rd_u32(&bytes, sp + 8);
        let vaddr = rd_u32(&bytes, sp + 12);
        let rawsize = rd_u32(&bytes, sp + 16);
        let rawptr = rd_u32(&bytes, sp + 20);
        let chars = rd_u32(&bytes, sp + 36);
        println!(
            "{:>2}. {:<8} VA={:#010x} VSize={:#x} RawPtr={:#x} RawSize={:#x} [{}]",
            i, name, vaddr, vsize, rawptr, rawsize, section_chars(chars)
        );
    }
}
