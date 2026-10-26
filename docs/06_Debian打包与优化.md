# 06 · Linux 文档/Manpage/Release/Changelog 分析学习 × Debian 打包（按硬件与版本）

> 承接"全选继续"。本轮把项目主线"编码安全（TextEncoding）"落到 **Linux 原生 CLI**，
> 并系统学习 Debian 打包体系（manpage / 真实包 `debian/` / changelog 与 release 惯例），
> 用标准 `debhelper` 流程产出按**硬件架构**（amd64 / arm64）与**发行版本**
>（noble / jammy / bookworm）分别构建的 `.deb`。

---

## 一、分析学习对象与方法

| 学习对象 | 取法 | 落点 |
|---|---|---|
| `man dpkg-buildpackage` / `man dh` / `man dpkg-architecture` / `man lintian` | 官方手册的序列、目标、`-a` 交叉、`override_dh_*` 钩子 | `debian/rules` 极简 `dh $@` + 必要钩子 |
| 真实包 `hello` 的 `debian/`（`apt-get source hello`） | `debhelper-compat (= 13)` 内联、`Rules-Requires-Root: no`、`Architecture: any`、`${shlibs:Depends}`、changelog 的 `distribution` 维度 | 直接套用范式 |
| 真实包 `gzip` 的 `debian/rules` | 经典**交叉编译 CC 选择**写法（按 `DEB_BUILD_ARCH != DEB_HOST_ARCH` 选 host 前缀 gcc） | 现代化简化为统一 `$(DEB_HOST_GNU_TYPE)-gcc` |
| `dpkg-buildflags`（noble 默认） | `-D_FORTIFY_SOURCE=3` / `-fstack-protector-strong` / `-fstack-clash-protection` / `-fcf-protection` / `-Wl,-z,relro` / LTO | Makefile `include buildflags.mk` 自动继承 |
| `/usr/share/dpkg/*.mk` | `architecture.mk` / `buildflags.mk` / `default.mk` 的官方片段机制 | Makefile 直接 `include`，零手写 flag |
| Debian changelog / release 惯例 | `pkg (version) distribution; urgency=` + RFC2822 签名；版本号随发行版加后缀（Ubuntu `ubuntuN`、backports `~bpoN+1`） | `build-debs.sh` 按发行版改写版本与 distribution |

---

## 二、提炼并落地的技巧 / 优化

1. **交叉编译 CC 统一选择（核心）**
   在 `Makefile` 中 `include /usr/share/dpkg/architecture.mk`，然后
   `CC = $(DEB_HOST_GNU_TYPE)-gcc`（仅在 CC 未外部指定时覆盖）。
   原生 `x86_64-linux-gnu-gcc` 与交叉 `aarch64-linux-gnu-gcc` 在 Ubuntu 均存在，
   **一套代码原生/交叉通吃**，比 gzip 老式 `build!=host` 分支更干净。

2. **hardening 自动继承**
   `include /usr/share/dpkg/buildflags.mk` 注入 noble 的全部 hardening 默认值；
   `rules` 再显式 `export DEB_BUILD_MAINT_OPTIONS = hardening=+all` 以可控、可读。

3. **Rules-Requires-Root: no** —— 构建无需 root，符合现代策略。

4. **`Architecture: any`** —— 二进制包随目标架构构建，配合 `-a` 出多 arch。

5. **可重现构建**：dpkg 自动注入 `-ffile-prefix-map` / `-fdebug-prefix-map`，剥离构建路径。

6. **dbgsym 自动分离**：`dh_strip` 自动产出 `classics-dbgsym_*.ddeb`，无需手写。

7. **man page 入包**：`debian/classics.manpages` 列出 `classics.1`
   （**注意路径相对源码根目录，而非 `debian/`**），`dh_installman` 自动压缩安装到 `/usr/share/man/man1/`。

8. **发行维度**：通过 changelog 的 `distribution` + 版本后缀区分（3.0 native 无连字符版本）：
   noble=`1.0.0ubuntu1`、jammy=`1.0.0~jammy1`、bookworm=`1.0.0~bpo12+1`。

9. **交叉 `dh_shlibdeps` 修复**：交叉构建时 dpkg-shlibdeps 找不到 host 的 `libc.so.6`，
   钩子 `override_dh_shlibdeps` 传 `-l/usr/$(DEB_HOST_MULTIARCH)/lib` 指到交叉 sysroot
   （原生 amd64 时该路径不存在、无副作用）。

---

## 三、项目落点：`classics` Linux 原生 CLI（C99，仅依赖 glibc iconv）

复用移动端 `TextEncoding.decodeSafe` / HarmonyOS `decodeTextSafe` 的**编码防护哲学**，在 Linux 端落地：

- `classics list` —— 列出 `/usr/share/classics` 下的典籍（`CLASSICS_DATADIR` 可覆盖，便于测试/便携）
- `classics show <book>` —— 输出整本（省略 `.txt` 也行）
- `classics decode <file>` —— **严格 UTF-8 校验 → 失败回退严格 GB18030 → 仍失败则明确标注**，绝不假装成功
- `classics lint <file>` —— 扫描乱码指纹（锟斤拷 / 烫烫烫 / 屯屯屯 / 裸 U+FFFD）与非法 UTF-8 区段

目录：`classics-linux/{src/classics.c, Makefile, data/*.txt, debian/*, build-debs.sh}`。

---

## 四、构建矩阵结果

运行 `classics-linux/build-debs.sh`（架构 × 版本 = 6 个包），产物在 `classics-linux/build/`：

| 架构 | noble (24.04) | jammy (22.04) | bookworm (Debian 12) |
|---|---|---|---|
| **amd64** | `classics_1.0.0ubuntu1_amd64.deb` | `classics_1.0.0~jammy1_amd64.deb` | `classics_1.0.0~bpo12+1_amd64.deb` |
| **arm64** | `classics_1.0.0ubuntu1_arm64.deb` | `classics_1.0.0~jammy1_arm64.deb` | `classics_1.0.0~bpo12+1_arm64.deb` |

- **架构校验**：amd64 包内为 `x86-64` ELF，arm64 包内为 `ARM aarch64` ELF —— 字段与二进制一致。
- **端到端验证**：arm64 二进制经 `qemu-aarch64-static -L /usr/aarch64-linux-gnu` 实跑，
  `list` / `decode` / `lint` 全部正常（证明交叉产物可用）。
- **lintian**：6 个包 **全部 0 E / 0 W**（已修 `description-too-short` 等）。

---

## 五、关键踩坑与修复（已解决）

| 问题 | 现象 | 修复 |
|---|---|---|
| UTF-8 校验致命 bug | `lo/hi` 误声明为 `unsigned char`（上限 255），所有多字节序列被误判非法，合法 UTF-8 全走 GB18030 | 改为 `uint32_t` |
| man page 未进包 | `dh_installman` 报 `Cannot find classics.1` | 移到**源码根目录** `classics.1`，`debian/classics.manpages` 写 `classics.1`（相对源码根） |
| 交叉 `dh_shlibdeps` 失败 | `cannot find library libc.so.6 ... elf64-littleaarch64` | `override_dh_shlibdeps` 加 `-l/usr/$(DEB_HOST_MULTIARCH)/lib` |
| `default.mk` 未注入 CC | 独立 `make` 下 `dpkg-buildapi` 返回 0，buildtools 未包含 | 不依赖 buildapi，显式用 `DEB_HOST_GNU_TYPE` 选 CC（更稳妥、跨 dpkg 版本一致） |

---

## 六、复现命令

```bash
# 1) 原生单机构建（noble/amd64）
cd classics-linux && dpkg-buildpackage -us -uc -b

# 2) 矩阵构建（amd64+arm64 × noble+jammy+bookworm）
bash classics-linux/build-debs.sh        # 产物在 classics-linux/build/

# 3) 校验
dpkg-deb -I  classics-linux/build/classics_1.0.0ubuntu1_arm64.deb | grep -E 'Architecture|Depends'
lintian      classics-linux/build/*.deb
file $(dpkg-deb -x ... /tmp/x; echo /tmp/x/usr/bin/classics)   # 看 ELF 架构

# 4) 实跑 arm64（需 qemu-user-static）
qemu-aarch64-static -L /usr/aarch64-linux-gnu /tmp/x/usr/bin/classics list
```

---

## 七、结论与下一步

- 把"编码安全"主线从移动端延伸到 Linux，并借 Debian 打包**系统学习**了官方手册、真实包范式与
  changelog/release 惯例；所提炼的 9 项技巧已全部落到 `debian/` 与 `Makefile`。
- 6 个包 lintian 干净、架构正确、交叉产物实跑通过 —— 满足"分别基于硬件和版本"的构建目标。
- 可作为 `Architecture: all` 的**数据子包**独立出典籍文本（当前数据随二进制包走）；或接 `dput` 推到 PPA/仓库。
