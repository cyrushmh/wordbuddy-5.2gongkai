# 09 · 拆解真实 Arch 包：数据子包拆分与中文 Man 规范

本轮投入了一个真实的 Arch 包 **`man-pages-zh_cn-1.6.4.5-1-any.pkg.tar.7z`**（简体中文 Linux man 手册）。把它拆开读完，再把它身上的规范落到本项目上。

---

## 一、拆解：一个真实包里有什么

```
man-pages-zh_cn-1.6.4.5-1-any.pkg.tar.7z   （2.5 MB）
  └─ man-pages-zh_cn-1.6.4.5-1-any.pkg.tar.zst
       ├─ .PKGINFO     包元数据
       ├─ .MTREE       文件清单 + sha256（pacman 用它校验已装文件）
       ├─ .BUILDINFO   构建环境记录（可复现构建）
       └─ usr/share/man/zh_CN/man{1..8}/…   746 个 man 页
```

**规模分布**：man1 288 / man2 13 / man3 168 / man4 2 / man5 50 / man6 1 / man7 151 / man8 73，共 746 个文件，全部 gzip 压缩（`.1.gz`），权限 644。

### 1.1 `.PKGINFO`：它是个 **split package**

```
pkgbase = man-pages-zh          ← 一个源码包
pkgname = man-pages-zh_cn       ← 产出其中一个子包
xdata = pkgtype=split           ← 分包标记
arch = any                      ← 纯文档，不随架构变化
license = GFDL-1.2-or-later / GPL-2.0-only / … （多许可证并存）
depend = man
makedepend = cmake, opencc, python, git
```

**`arch = any` 是本轮最关键的收获**：内容不随 CPU 变化的东西就该单独成包、只打一份。这正是我上一轮文档里「把典籍数据拆成独立数据子包」设想的标准做法。

### 1.2 `.MTREE`：pacman 的完整性校验清单

```
#mtree
/set type=file uid=0 gid=0 mode=644
./.BUILDINFO time=… size=6877 sha256digest=f43e776c…
./.PKGINFO   time=… size=698  sha256digest=c60c82ff…
./usr        time=… mode=755 type=dir
./usr/share/licenses/man-pages-zh_cn/COPYRIGHT time=… mode=644 size=7440 sha256digest=…
```

**目录与文件按路径统一排序**，每个文件带 `mode`/`size`/`sha256digest`。我之前只生成了 `.PKGINFO`——这是缺口。

### 1.3 `.BUILDINFO`：可复现构建记录

```
format = 2
buildenv = !distcc / color / !ccache / check / !sign
options = strip / docs / !libtool / !staticlibs / emptydirs / zipman / purge / debug
```

其中 **`options = zipman`** 正好解释了为什么包里 746 个 man 页全是 `.gz`——压缩是 makepkg 按这个选项自动做的，不是手工 gzip。

### 1.4 中文 man 的组织方式：`zh_CN` locale 子目录

中文页**不是**塞进 `/usr/share/man/man1/`，而是放在 **`/usr/share/man/zh_CN/man1/`**，与英文页同名。`man` 会按 `LANG` 优先取 locale 子目录，取不到再回退英文。这是中文 man 的正确落点。

---

## 二、落地一：把典籍数据拆成独立数据子包

依 `arch = any` 范式，把「不随架构变化的典籍文本」从主包里拆出来。

### 2.1 Debian 侧

`debian/control` 新增子包，主包依赖它：

```
Package: classics
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}, classics-data (>= ${source:Version})

Package: classics-data
Architecture: all
Multi-Arch: foreign
```

`debian/rules` 用两个独立的 `DESTDIR` 分别安装，避免「先全装再挪」的临时态：

```make
override_dh_auto_install:
	$(MAKE) install-bin  DESTDIR=$(CURDIR)/debian/classics
	$(MAKE) install-data DESTDIR=$(CURDIR)/debian/classics-data
```

Makefile 相应拆出 `install-bin` / `install-data` 两个目标（`install` 仍兼容全量）。

**产物**：`classics_<ver>_<arch>.deb`（架构相关）+ `classics-data_<ver>_all.deb`（架构无关）。

### 2.2 Arch 侧

PKGBUILD 改为 split package，`package_classics-data()` 里把 `arch` 覆盖为 `any`：

```bash
pkgbase=classics
pkgname=('classics' 'classics-data')

package_classics() {
  depends=('glibc' "classics-data=$pkgver-$pkgrel")
  make DESTDIR="$pkgdir" install-bin
  …
}

package_classics-data() {
  arch=('any')          # ← 子包覆盖：纯文本不随架构重复打包
  make DESTDIR="$pkgdir" install-data
  …
}
```

**产物**：`classics-1.0.0-1-{x86_64,aarch64,riscv64}.pkg.tar.zst`（各一份）+ `classics-data-1.0.0-1-any.pkg.tar.zst`（**只一份**）。

拆分收益：升级典籍内容只需重发那一个 `any` 包，不必在三个架构上重编二进制。

---

## 三、落地二：补齐之前缺的规范

| 项 | 之前 | 现在 |
|---|---|---|
| `.MTREE` | 无 | 有（mtree 格式，`sha256digest`，目录/文件按路径统一排序） |
| `.BUILDINFO` | 无 | 有（`format = 2` + buildenv/options，含 `zipman`） |
| `.SRCINFO` | 无 | 有（AUR 提交所需，含 pkgbase + 两个 pkgname 段） |
| `sha256sums` | `SKIP` | 真实值（`FILL_SUMS=1` 自动回填 PKGBUILD） |
| 中文 man | 无 | `classics.zh_CN.1` → `/usr/share/man/zh_CN/man1/classics.1.gz` |
| 包的 `xdata` | 无 | `pkgtype=split`（与范本一致） |

`build-arch.sh` 相应升级：`.MTREE` 生成时不包含自身（与真实包一致，清单里只有 `.PKGINFO`/`.BUILDINFO`）；man 页在打包前统一 gzip（对应 `options = zipman`）。

中文 man 已实测可被渲染：

```
$ man -l classics.zh_CN.1
CLASSICS(1)                        用户命令                        CLASSICS(1)
名称
       classics - 典籍阅读与编码安全解码命令行工具
```

---

## 四、踩到的坑（都是真问题，不是环境噪音）

### 4.1 glob 漏匹配，数据包滞留在仓库根

`build-debs.sh` 里写的是 `"$REPO"/classics_*.deb`。但数据包文件名是 `classics-data_<ver>_all.deb`——`classics` 后面是**连字符**不是下划线，所以这个 glob **从来没匹配到它**，数据包一直堆在仓库根，而日志还报着「完成」。

改为 `"$REPO"/classics*.deb` 后，9 个包全部正确归档，仓库根干净。顺带把 `dbgsym` 从「留着靠 gitignore 忽略」改成直接清理。

> 教训：日志报成功 ≠ 产物到位。这次是靠「产物清单里数不对」发现的，不是靠日志。

### 4.2 extended description 的缩进是 **1 个空格**

lintian 报 `description-starts-with-leading-spaces`：我用了 2 个空格缩进 long description，Debian 会把它当作「逐字显示块」（verbatim）。标准是恰好 1 个空格。

---

## 五、验证结论

**Debian（9 个包，lintian 全 0 E/W）**

| 架构 \ 版本 | noble | jammy | bookworm |
|---|---|---|---|
| amd64 | ✓ | ✓ | ✓ |
| arm64 | ✓ | ✓ | ✓ |
| **data（all）** | ✓ | ✓ | ✓ |

**Arch（4 个包）**

| 包 | 架构 | 内容 |
|---|---|---|
| classics | x86_64 / aarch64 / riscv64 | `usr/bin/classics` + man（英+中）+ license |
| classics-data | any | `usr/share/classics/*.txt` + license |

- 三架构主包 ELF 类型逐一核对正确（x86-64 / ARM aarch64 / UCB RISC-V）
- 主包不含数据目录、数据包不含二进制——**分离彻底**
- `.PKGINFO` 含 `pkgbase`/`xdata = pkgtype=split`/`depend = classics-data=1.0.0-1`

---

## 六、复现命令

```bash
# Debian：9 个包（6 架构×版本 + 3 数据包）
cd classics-linux && bash build-debs.sh

# Arch：4 个包（3 主包 + 1 数据子包）+ .SRCINFO
cd classics-linux && FILL_SUMS=1 bash build-arch.sh

# 真 Arch 上直接用（无需上面的复刻脚本）
makepkg -s
makepkg --printsrcinfo > .SRCINFO

# 中文 man 渲染自检
man -l classics.zh_CN.1
```

---

## 七、待办

1. **C 版指纹检测迁移**：仍跑在原始字节上，需改为对转换后文本检测，才能复用「GBK 误读连续产物字」启发式（见 docs/08 §4.1）。
2. **Swift 交叉到 ARM64**：本机 Swift 工具链仅 x86-64 target。
3. `classics-data` 目前只有 2 个示例典籍；可把 iOS/macOS/HarmonyOS 三端已有的典籍数据（含参同契 92 章）统一抽到这个共享数据包里。
