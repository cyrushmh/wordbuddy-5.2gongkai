# peinfo（Rust 稳定版）

纯标准库实现的 PE 头解析器，edition 2021、MSRV 1.74，**零第三方依赖**——
这意味着它不会因为任何外部 crate 停止维护而需要重写，符合仓库「稳定版/LTS」策略。

## 构建

```bash
# 本机（Linux/macOS/Windows）
cargo build --release
./target/release/peinfo            # 解析自身
./target/release/peinfo foo.dll    # 解析任意 PE

# 交叉编译为 Windows PE（无需 Windows，需 mingw-w64）
rustup target add x86_64-pc-windows-gnu
cargo build --release --target x86_64-pc-windows-gnu
# 产物：target/x86_64-pc-windows-gnu/release/peinfo.exe
```

工具链由 `rust-toolchain.toml` 锁定为 `stable`，版本下限由 `Cargo.toml: rust-version` 约束，
`Cargo.lock` 保证每次构建可复现。
