//! PE 头查看器 GUI —— Rust + egui（稳定版，immediate-mode 原生 GUI）。
//! 仅依赖 eframe/egui，跨 Windows / Linux / macOS 编译；本仓库用于演示 Rust 的 GUI 路线。

use eframe::egui;
use std::fs;

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

struct PeApp {
    path: String,
    report: String,
}

fn parse_pe(bytes: &[u8]) -> String {
    if bytes.len() < 0x40 || &bytes[0..2] != b"MZ" {
        return "不是合法 PE（缺少 MZ 头）".into();
    }
    let e_lfanew = rd_u32(bytes, 0x3C) as usize;
    if e_lfanew + 4 > bytes.len() || &bytes[e_lfanew..e_lfanew + 4] != b"PE\0\0" {
        return "缺少 PE\\0\\0 签名".into();
    }
    let coff = e_lfanew + 4;
    let machine = rd_u16(bytes, coff);
    let nsec = rd_u16(bytes, coff + 2);
    let optsize = rd_u16(bytes, coff + 16);
    let opt = coff + 20;
    let magic = rd_u16(bytes, opt);
    let pe32p = magic == 0x20B;
    let entry = rd_u32(bytes, opt + 16);
    let ib = if pe32p {
        rd_u64(bytes, opt + 24)
    } else {
        rd_u32(bytes, opt + 28) as u64
    };
    let subsys = rd_u16(bytes, opt + 68);

    let mut s = format!(
        "Machine : {:#06x}\n节数     : {}\nMagic    : {}\n入口点   : {:#010x}\nImageBase: {:#010x}\n子系统   : {}\n",
        machine,
        nsec,
        if pe32p { "PE32+" } else { "PE32" },
        entry,
        ib,
        subsys
    );
    let sec = opt + optsize as usize;
    for i in 0..nsec as usize {
        let b = sec + i * 40;
        if b + 40 > bytes.len() {
            break;
        }
        let name = String::from_utf8_lossy(&bytes[b..b + 8])
            .trim_end_matches('\0')
            .to_string();
        let vaddr = rd_u32(bytes, b + 12);
        let vsize = rd_u32(bytes, b + 8);
        s.push_str(&format!(
            "  节 {}: {} VA={:#010x} VSize={:#x}\n",
            i, name, vaddr, vsize
        ));
    }
    s
}

impl PeApp {
    fn new() -> Self {
        Self {
            path: String::new(),
            report: "在上方输入框粘贴 PE 文件路径，点击「分析」。\n（Windows 下可直接用 egui 内嵌文件对话框或 rfd 替代）".into(),
        }
    }
}

impl eframe::App for PeApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label("PE 文件路径:");
                ui.text_edit_singleline(&mut self.path);
                if ui.button("分析").clicked() {
                    match fs::read(&self.path) {
                        Ok(b) => self.report = parse_pe(&b),
                        Err(e) => self.report = format!("读取失败: {}", e),
                    }
                }
            });
            ui.separator();
            egui::ScrollArea::vertical().show(ui, |ui| {
                ui.label(&self.report);
            });
        });
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        "PE Viewer (egui)",
        options,
        Box::new(|_cc| Ok(Box::new(PeApp::new()))),
    )
}
