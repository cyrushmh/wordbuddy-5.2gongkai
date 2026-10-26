# PE Viewer（Rust + egui）

现代 immediate-mode 原生 GUI，跨平台（Windows / Linux / macOS）。仅依赖 `eframe`，
版本固定为 `0.29`，工具链锁定 `stable` —— 符合仓库「稳定版」策略。

## 构建

```bash
# 本机（生成当前平台可执行文件）
cargo run --release

# 交叉编译为 Windows（需 mingw-w64 提供 OpenGL 链接）
rustup target add x86_64-pc-windows-gnu
cargo build --release --target x86_64-pc-windows-gnu
# 产物：target/x86_64-pc-windows-gnu/release/peview-egui.exe
```

> 若希望带原生文件选择框，可加 `rfd` crate 替换文本输入路径的方式。
