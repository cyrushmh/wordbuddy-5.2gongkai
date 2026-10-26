# 10 · Linux 目录规范与发行版包管理重学 + 黄庭三经数据落地

> 本轮两件事：① 黄庭三经（内景/外景/内外双景）+《道德真经》81 章全本数据四端落地；② 从权威规范原文整体重学 Linux 目录结构与三家发行版包管理规则，并用其核验本项目打包体系。
> 规范来源：FHS 3.0（refspecs.linuxfoundation.org，已下载全文 223 KB 存档）、systemd 255 `file-hierarchy(7)`（本机 man 全文 777 行）、Debian Policy 4.7.4.1 第 9/10 章、Arch Package Guidelines、Fedora Packaging Guidelines。

---

## 一、黄庭三经与《道德真经》数据落地（#337）

### 1.1 数据源与抓取结论

| 典籍 | 道藏编号 | 章节结构 | 备注 |
|---|---|---|---|
| 道德真经（道藏无注本） | 15-649 | 81 章，卷上《道经》37 章 / 卷下《德经》44 章 | 章题为河上公章句系（体道章第一→显质章第八十一），约出于宋代，底本《正统道藏》洞神部本文类。这是唐玄宗御注、宋徽宗御解等**经世解读共用的分章系统** |
| 太上黄庭内景玉经 | 20-992 | 36 章（上清章第一→沐浴章第三十六） | 魏华存传，务成子注叙；晚唐五斗米道道士奉为养生要典 |
| 太上黄庭外景玉经 | 20-993 | 3 部（上/中/下） | 经文中部夹 2 条参校记（如「1.向：疑当作"何"」），已滤出收入 `collation_notes` |
| 黄庭内外玉景经解 | 20-997 | 蒋慎修 18 则 | 每则含经文 + 双行夹注，注文注入 `commentary` 字段——这是四端数据契约中 `commentary` 的首次真实使用 |

### 1.2 ctext 计划的结论：不可抓取

`ctext.org` 的 robots/使用条款明确声明："LLMs/robots do not have authorization to scrape… will intermittently intentionally return corrupted data"。**结论：ctext 仅可作参校底本引用，不可程序抓取。** 本 Talmudic 项目的经文来源全部为道藏站点 `m.daorenjia.com` 的经文章节 API（`neirongapi.php?id=`），gb18030/big5 系文本经严格 UTF-8 校验后入库。

### 1.3 「经世版」歧义声明（待用户确认）

用户要求"完善道德经（以经世版为主）"。经 6+ 轮检索（百度百科谱系文、Bing 精确引号搜索、经世书院/书局等渠道），**公网无「经世版」《道德经》这一通行版本名**。当前落地策略：

- **主**：以「河上公章句系道藏无注本」81 章全本补全（与"经世"读经传统的分章系统同源，分章与章题严格对应）；
- **双读**：保留既有帛书本（爱好者整理）不受影响；
- 若用户所指"经世版"为特定注本/校本（如某出版社经世丛书系列），切换底本即可，四端生成管线已工具化（`build_classics_data.py` 单一数据源 → 四端发射器），换源重跑一次即可。

### 1.4 重复标题待办（TS 端）

ArkTS `ClassicsData.ts` 中参同契迁移残留 **73 章标题前置重复**（如 `世人好小术世人好小术，…`，Swift 端已清洗）。构建不阻塞（非字符串语法问题），但阅读体验受影响，**下一轮修复**：把 Swift 端干净版回写到 TS，或重跑生成管线对齐。

### 1.5 四端落地状态

| 端 | 状态 | 验证方式 |
|---|---|---|
| ArkTS | ✅ 0 错误 | `tsc --noEmit --strict`；顺带修复两处既有跨行字符串字面量（会炸构建的隐患） |
| Swift | ✅ 233 章 | `swift build` + `classics list` 9 部；模型层补 `commentary`/`daozangNid`/`daozangId`/`onlineUrl` 字段 |
| Rust | ✅ 6 条目 | `cargo build`；`embedded_entries()` 增 4 条 `include_str!` 编译期嵌入 |
| C CLI | ✅ 6 部 | `make` + `CLASSICS_DATADIR=data ./classics show huangting-neijing` 首章验证 |

打包附带修复：`install-data` 从 `cp -r data/.` 收紧为 `install -m 0644 data/*.txt`——防构建工具与源 JSON 泄入安装包（下节有实证）。

---

## 二、Linux 目录结构重学（FHS 3.0 + systemd 255）

### 2.1 本次精读确立的核心规则（含原文要点）

**FHS 3.0**（http://refspecs.linuxfoundation.org/FHS_3.0/fhs-3.0.html，全文已存档 `/tmp/fhs3.html`）：

| 目录 | FHS 定义（精简） | 对本项目的意义 |
|---|---|---|
| `/usr/bin` | "Most user commands"——最终用户直接使用的命令 | CLI 主程序装这里 |
| `/usr/lib` | "Libraries for programming and packages" | 私有数据/内部二进制的容身所 |
| `/usr/share` | **"Architecture-independent data"** —— 跨包共享资源（man/文档/时区/字体） | 典籍文本正解 |
| `/usr/share/man` | "Manual pages" | man1 + zh_CN/man1 |
| `/usr/local` | Local hierarchy，**仅供本地管理员** | 发行包永不触碰 |
| `/opt` | 自包含大型附加包 | 不适用 |

**systemd 255 `file-hierarchy(7)`**（现代发行版事实标准，777 行全文读完）：

- `/usr/bin/`："Package executables that shall appear in the $PATH executable search path… It is **not recommended to place internal binaries or binaries that are not commonly invoked from the shell** in this directory, such as daemon binaries. As this directory is shared with most other packages of the system, **special care should be taken to pick unique names** for files placed here"——包内二进制是公共命名空间，`classics` 这个名字需要保持唯一。
- `/usr/share/`：跨包共享资源的标准位置；`/usr/lib/package/` 是"Private static vendor resources"（私有底座）。
- **Table 1 系统厂商文件位置表**（vendor files）与 **Table 2 变量文件位置表**（`/etc/package/` 配置、`/run/package/` 运行时、`/var/cache|lib|log/package/`）——本项目无守护进程、无配置、无状态，天然只落在 Table 1 的静态行。
- `/etc`、`/usr` 可能以只读挂载；应用必须能在无写权限下运行——CLI 无状态设计正是此规范的实践。
- `/bin`、`/sbin`、`/lib` 在现代系统上全部是指向 `/usr` 下对应目录的**兼容符号链接**（usrmerge）。

### 2.2 Debian Policy 对 FHS 的关键修订（4.7.4.1）

- **第 10 章**：包不得向 `/bin/*`、`/lib/*`、`/sbin/*` 安装文件（除 `base-files` 创建别名符号链接）；"Packages may assume that `/bin`, `/lib` and `/sbin` are always symbolic links"。
- **第 9.1.1 例外 01**（对本项目最重要）：FHS「arch-independent 静态文件应在 /usr/share」从强制降为建议——**但如果某个目录完全由 arch-independent 文件组成，它应位于 /usr/share**。`classics-data` 的 6 个 txt 100% 架构无关 → `/usr/share/classics/` 是最优解。
- **第 9.1.2**：`/usr/local` 仅供本地管理员独占，"a package must not rely on the presence or absence of files or directories in /usr/local for normal operation"。

---

## 三、三家发行版包管理理念对照

| 维度 | Debian（deb/dpkg） | Arch（makepkg/PKGBUILD） | Fedora（RPM） |
|---|---|---|---|
| 哲学 | 自由软件社会契约 + 制度化治理（Constitution/Policy） | KISS：一切从简，用户自担 | 上游优先 + FPC 集中审批 |
| 目录依据 | FHS + Debian Policy 修订 | FHS + Arch Package Guidelines | FHS + Guidelines 例外 |
| /usr/local | 禁止安装（FHS 强制） | "Packages should **never** be installed to /usr/local" | 同样禁止（"no Fedora package can contain files… under /usr/local"） |
| usrmerge | 已完成（/bin→/usr/bin 等，Policy 10.1） | 早已合并 | 已完成，且 `%files` 必须写**真实路径**（RPM 依赖按 %files 路径判定，非文件系统实际路径） |
| 架构无关数据 | `Architecture: all`，可加 `Multi-Arch: foreign` | `arch=('any')` | `BuildArch: noarch`（可豁免"至少一个主架构构建成功"） |
| 许可文件 | `/usr/share/doc/<pkg>/copyright`（DEP-5 机读格式） | `/usr/share/licenses/<pkg>/LICENSE` | `%license` 宏自动放 `/usr/share/licenses/<pkg>/` |
| man 页 | `/usr/share/man/man1/*.1.gz`；翻译页惯例入 `<locale>/man1/` | `/usr/share/man`，makepkg 自动压缩；中文 man 范式参照 `man-pages-zh_cn`（`arch=any` 分包） | `%{_mandir}/man1/foo.1*`（**必须通配符**，RPM 会重压缩）；且 mandir 文件自动标记为文档，无需 `%doc` |
| 分包范式 | 一个 source 多 binary 包（`classics` + `classics-data`） | split package：`pkgname=('classics' 'classics-data')`，子包可覆盖 `arch` | 主包 + `-doc`/`-devel` 子包惯例 |
| 命名 | 小写 | 仅字母数字 + `@. _+-`，**不得**以 `-`/`.` 开头 | 类似，禁止版本号后缀（除非无法滚动升级） |
| 构建洁癖 | lintian 全量检查（数千条 tag） | makepkg 职责链：build→check→package→compress | rpmlint |

### 三家的共同底线（本项目全部满足）

1. arch-independent 数据 → `/usr/share`（或子目录）；
2. 永不装 `/usr/local`；
3. 通过 `/usr/bin` 提供 $PATH 可执行文件，命名唯一；
4. man 页进 `/usr/share/man`，许可进 licenses（Arch/Fedora 范式）或 copyright（Debian 范式）；
5. 架构无关数据单独分包，不随 CPU 架构重复打包。

---

## 四、本项目核验矩阵（对照上述规范逐条实证）

| 核验项 | 规范依据 | 本项目实际 | 结论 |
|---|---|---|---|
| CLI 安装位置 | FHS 4.4 / systemd Table 1 | `/usr/bin/classics` | ✅ |
| 数据安装位置 | FHS 4.11 "Arch-independent data"；Debian 例外 01 | `/usr/share/classics/*.txt`（6 个） | ✅ 纯架构无关 |
| arch 无关分包 | Debian `Architecture: all`；Arch `arch=any`；Fedora noarch | deb `Architecture: all` + `Multi-Arch: foreign`；Arch 子包 `arch=('any')` | ✅ 复刻 man-pages-zh_cn 范式 |
| 数据包洁癖 | lintian / 打包卫生 | `install-data` 收紧后 `dpkg -c` 实测：仅 6 txt + doc/copyright，**无 src/、无 JSON** | ✅ 修复生效 |
| man 页 | FHS 4.11.7 | `/usr/share/man/man1/classics.1.gz` + `/usr/share/man/zh_CN/man1/classics.1.gz` | ✅ 中英双页 |
| 许可文件 | Arch `/usr/share/licenses/`；Debian DEP-5 copyright | Arch 侧 `/usr/share/licenses/{classics,classics-data}/LICENSE`；deb 侧 `/usr/share/doc/*/copyright` | ✅ 各随其俗 |
| 不碰 /usr/local | 三家一致禁止 | 无任何 /usr/local 内容 | ✅ |
| 不装 /bin、/sbin | Debian 10.1 / Fedora usrmerge | `dpkg -c` 实证无此类路径 | ✅ |
| 图标命名空间 | systemd Table 1 "pick unique names" | `classics` 无冲突 | ✅ |
| 依赖声明正确性 | Arch depends 带版本号 | `depends=('glibc' "classics-data=$pkgver-$pkgrel")` | ✅ SRCINFO 已含版本依赖 |
| Makepkg 变量纪律 | Arch "Do not introduce new variables" | PKGBUILD 未新增自定义变量/函数 | ✅ |
| RPM 视角前瞻 | Fedora `%files` 真实路径 | 未产 RPM；若未来做 spec：man 引用须 `%{_mandir}/man1/classics.1*` 通配符，数据走 `%{_datadir}/classics` | 📋 预案 |

### 4.1 lintian 实证（Debian 13 trixie lintian，最新版）

对本轮重建的 **10 个 deb**（4 发行版目标 × bin/data 分包，除 noble/oracular 外）逐跑 `lintian`：**全部零 tag、零警告、零错误**。这覆盖了 usrmerge 路径、man 页位置、changelog 版本合法性、maintainer 字段、文件权限等数百条自动规则。

### 4.2 后台构建结果（任务 op5Znu，exit 0）

- deb 矩阵：`classics_1.0.0{ubuntu1,~jammy1,~bpo12+1}_{amd64,arm64}.deb` ×6 + `classics-data_*_all.deb` ×3，全部含新数据；
- Arch：`classics-1.0.0-1-{x86_64,aarch64,riscv64}.pkg.tar.zst` + `classics-data-1.0.0-1-any.pkg.tar.zst`；
- 二进制包 Installed-Size 28 KB（纯 C + glibc 动态链接），数据包 63 KB。

---

## 五、本轮待办

1. **TS 端 73 章标题前置重复**（参同契迁移残留，Swift 端已清洗）——下轮修复；
2. 「经世版」具体所指待用户确认（若为特定注本/校本，重跑生成管线换源）；
3. 如需 RPM spec：按 Fedora 规范，man 引用用通配符、数据与许可走宏路径、`BuildArch: noarch` 拆数据子包；
4. docs/09 曾拆解真实 Arch 包学范式，本轮的原创贡献是把「多规范并行核验」固化为打包流程：每次 `build-debs.sh`/`build-arch.sh` 后追加 lintian + `dpkg -c` 内容清单双检。

---

*参照系：FHS 3.0；systemd 255 file-hierarchy(7)；Debian Policy 4.7.4.1 §9.1/§10；Arch Package Guidelines；Fedora Packaging Guidelines (Filesystem Layout / Using rpm macros / Noarch)。*
