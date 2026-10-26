//! sysweeper-rust — system-optimizer 的 Rust 侧命令行组件。
//!
//! 目标：让同一套「只读诊断」口径在纯 Rust 标准库下也能查询，
//! 便于嵌入式/最小系统（仅有 rustc）下使用。
//!
//! 设计原则与 Python/Go/C/Java 侧一致：
//!   - 纯标准库、零第三方依赖，单文件即可 `rustc` 直编；
//!   - 只读探测，文件缺失/读取失败一律降级提示，不 panic、不中断；
//!   - 红线：只读探测，不修改任何系统状态。
//!
//! 用法:
//!   sysweeper-rust version      版本信息
//!   sysweeper-rust sysinfo      系统信息（OS / 架构 / CPU / 内存 / uptime）
//!   sysweeper-rust help         帮助
//!
//! 编译:
//!   rustc --edition 2021 -O -o sysweeper-rust sysweeper.rs

use std::env;
use std::fs;
use std::process::{self, Command};
use std::thread;

/// 版本常量；须与项目其余 4 处版本号保持一致（见 AGENTS.md「版本号同步」）。
const VERSION: &str = "0.6.40";

/// 读取 procfs 文本文件；失败返回 None（供降级路径使用）。
fn read_proc(path: &str) -> Option<String> {
    fs::read_to_string(path).ok()
}

/// 运行时探测 rustc 版本（只读，不改系统状态）；缺失则降级提示。
fn rustc_version() -> String {
    Command::new("rustc")
        .arg("--version")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                String::from_utf8(o.stdout).ok().map(|s| s.trim().to_string())
            } else {
                None
            }
        })
        .unwrap_or_else(|| "(rustc 未找到)".to_string())
}

/// 从 /proc/meminfo 文本中按前缀提取 kB 值，换算为 MB。
fn memfield_mb(meminfo: &str, key: &str) -> Option<u64> {
    for line in meminfo.lines() {
        if let Some(rest) = line.strip_prefix(key) {
            // 形如 "MemTotal:       16384000 kB"
            let kb: u64 = rest.trim().split_whitespace().next()?.parse().ok()?;
            return Some(kb / 1024);
        }
    }
    None
}

fn print_version() {
    println!("sysweeper-rust {}", VERSION);
    println!("  platform: {} ({})", env::consts::OS, env::consts::ARCH);
    println!("  rustc: {}", rustc_version());
}

fn print_sysinfo() {
    println!("=== sysweeper-rust 系统信息（只读） ===\n");

    // --- 操作系统与架构（编译期常量，跨平台可用） ---
    println!("  操作系统: {}", env::consts::OS);
    println!("  架构:     {}", env::consts::ARCH);

    // --- CPU 核数（available_parallelism 跨平台；失败降级） ---
    let ncpu = thread::available_parallelism()
        .map(|n| n.get().to_string())
        .unwrap_or_else(|_| "(未知)".to_string());
    println!("  CPU 核数: {}", ncpu);

    // --- 内存：仅 Linux 经 /proc/meminfo 读取，缺失则降级 ---
    if cfg!(target_os = "linux") {
        match read_proc("/proc/meminfo") {
            Some(m) => {
                if let Some(mb) = memfield_mb(&m, "MemTotal:") {
                    println!("  内存总量: {} MB", mb);
                } else {
                    println!("  内存总量: （解析失败）");
                }
                if let Some(mb) = memfield_mb(&m, "MemAvailable:") {
                    println!("  内存可用: {} MB", mb);
                } else {
                    println!("  内存可用: （解析失败）");
                }
            }
            None => println!("  内存:     （/proc/meminfo 读取失败）"),
        }
    } else {
        println!("  内存:     （当前平台不支持 /proc/meminfo）");
    }

    // --- uptime：仅 Linux 经 /proc/uptime 读取，缺失则降级 ---
    if cfg!(target_os = "linux") {
        match read_proc("/proc/uptime") {
            Some(u) => {
                // 形如 "123456.78 87654.32"，首字段为系统运行秒数。
                let secs: f64 = u
                    .split_whitespace()
                    .next()
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0.0);
                let total = secs as u64;
                let days = total / 86400;
                let hours = (total % 86400) / 3600;
                let mins = (total % 3600) / 60;
                println!("  运行时间: {}天 {}时 {}分", days, hours, mins);
            }
            None => println!("  运行时间: （/proc/uptime 读取失败）"),
        }
    } else {
        println!("  运行时间: （当前平台不支持 /proc/uptime）");
    }

    println!("\n  红线：只读探测，不修改任何系统状态。");
}

fn print_usage() {
    println!("用法: sysweeper-rust <子命令>\n");
    println!("子命令:");
    println!("  version     版本信息");
    println!("  sysinfo     系统信息（OS / 架构 / CPU / 内存 / uptime）");
    println!("  help        帮助\n");
    println!("示例:");
    println!("  sysweeper-rust version");
    println!("  sysweeper-rust sysinfo");
    println!("\n编译: rustc --edition 2021 -O -o sysweeper-rust sysweeper.rs");
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        print_usage();
        process::exit(2);
    }
    match args[1].as_str() {
        "version" | "-v" | "--version" => print_version(),
        "sysinfo" | "info" => print_sysinfo(),
        "help" | "-h" | "--help" => print_usage(),
        other => {
            eprintln!("未知子命令: {}\n", other);
            print_usage();
            process::exit(2);
        }
    }
}
