# classics-linux · arm 架构 deb 构建任务 · 会话交接单

> 生成时间：2026-10-24
> 用途：**记忆库/会话清空后，把本文件全文（或第 0 节引导语 + 正文）复制粘贴到新会话开头，即可无缝继续任务。** 状态全部以文件与命令实证为准，不依赖任何会话内记忆。

---

## 0. 粘贴引导语（复制这一段到新会话开头）

```
请忘记之前对话的全部内容，不要参考任何旧上下文。
这是一个进行中的工程任务的交接状态，以下文字是唯一事实来源：
任务：为 classics-linux 项目构建 arm 架构 Debian 包（Debian + Ubuntu）。
仓库：/workspace/windows-internals-toolkit/classics-linux/（monorepo 内）。
状态：任务 #570-#573 已全部完成并有实证；#574（文档更新 + git 提交推送）待办，
       详见交接单正文「第 6 节」。请先读 classics-linux/ 下的 debian/rules 与
       build-debs.sh 确认与本文描述一致，再执行 #574。
铁律：所有结论须以代码/命令实证，禁止虚构；「只读 + opt-in 写」。
```

---

## 1. 用户指令原文

1. （已完成，commit `972be4d` 已推送） disposable-env.sh 一次性隔离环境（手动版 chroot）。
2. （本交接单主题）**「构建arm架构的deb包，系统当然是linux，发行版是debian和ubuntu」**

## 2. 仓库与关键路径

| 项 | 值 |
|---|---|
| 项目目录 | `/workspace/windows-internals-toolkit/classics-linux/` |
| 打包设施 | `debian/`（control、rules、changelog、3.0 native 格式） |
| 矩阵构建脚本 | `build-debs.sh`（**用 `bash build-debs.sh` 调用**，文件可能无执行位） |
| 上游构建 | `Makefile`（经 `/usr/share/dpkg/architecture.mk` 的 `DEB_HOST_GNU_TYPE` 统一原生/交叉） |
| 源码 | `src/classics.c`（单文件 C，典籍阅读 + 乱码安全解码） |
| 数据 | `data/*.txt`（6 本典籍，进 classics-data 子包） |
| 产物目录 | `classics-linux/build/`（deb + 构建日志） |

分包结构：`classics`（Architecture: any，Depends `${shlibs:Depends}, ${misc:Depends}, classics-data`）+ `classics-data`（Architecture: all，Multi-Arch: foreign）。

## 3. #570 已修：arm 交叉构建 libc 依赖过度收紧（2.39 → 实测 2.34）

**问题**：交叉工具链的 `libc6-arm64-cross` 只有 `.shlibs` 无 `.symbols`，dpkg-shlibdeps 把依赖钉在工具链 libc 版本 2.39；而二进制 `objdump -T` 实测最高符号仅 GLIBC_2.34——会把 Debian bookworm（libc 2.36）用户误挡在门外。

**修复**：`debian/rules` 新增 `override_dh_gencontrol`——dh_gencontrol 读 substvars 之前，对 `debian/classics/usr/bin/classics` 做 `objdump -T` 实测，sed 改写 `debian/classics.substvars` 中 `shlibs:Depends` 的 libc6 下限；实测失败（MAXVER 为空）则保持原值。

**实证**：
- arm64 bookworm 构建日志：「libc6 依赖下限按 objdump 实测改写为 2.34」；产物 `Depends: libc6:arm64 (>= 2.34)`
- **对照实验**：既有 amd64 deb（原生 shlibdeps 精确计算）与改写后新 amd64 deb 均为 `libc6 (>= 2.34)`——原生构建零副作用
- armhf 同样改写为 2.34

## 4. #571 已扩展：构建矩阵

`build-debs.sh` 现状（2026-10-24 已扩至**全架构 13 × 发行版 4 = 52 格**）：

```bash
declare -A VER=(
  [noble]="1.0.0ubuntu1"
  [jammy]="1.0.0~jammy1"
  [bookworm]="1.0.0~bpo12+1"
  [trixie]="1.0.0"
)
ARGS=(amd64 arm64 armel armhf i386 mips mipsel mips64 mips64el powerpc ppc64el riscv64 s390x)
DISTS=(noble jammy bookworm trixie)
```

- 交叉工具链：13 架构全部装齐（`crossbuild-essential-*`，详见第 9 节），armhf/arm64/aarch64 等 gcc 13.3.0，mips 系 12.4.0
- 覆盖：Debian（bookworm 12 / trixie 13）+ Ubuntu（jammy 22.04 / noble 24.04）× 13 架构
- r6 变体（mips64r6/mips64r6el/mipsr6/mipsr6el）工具链在但 Ubuntu 无 libc 运行索引，暂不纳入
- `build-debs.sh` 已补执行位（chmod +x）

## 5. #572/#573 已完成：52 格构建 + 三重验证

**构建**：13 架构 × 4 发行版 = 52 格全部成功（`build/` 下 52 个主包 deb + 4 个 `classics-data_*_all.deb` + 52 个 `build_<dist>_<arch>.log`）。

**验证结论**：
1. **元数据**：`dpkg-deb -f` 核对——52 包 Architecture 正确，所有架构包 `Depends: libc6:<arch> (>= 2.34)`，data 包版本与主包联动
2. **lintian**：56 个 deb（52 主包 + 4 data）全部**零 E/W tag**
3. **qemu-user 实跑**：13 架构全部 PASS（amd64 原生 + 12 qemu 仿真，`list` 6 本典籍 rc=0）；
   arm64/armhf/riscv64 另测过 `show/decode/lint` 四子命令（decode 纯 GB18030 正确转换、
   混合损坏保守拒绝+指纹命中、lint 干净文件 OK）
4. **PIE 一致性**：6 个架构（armel/mips/mipsel/mips64/mips64el/powerpc）初版 lintian 报
   `hardening-no-pie`——dpkg-buildflags 对这些架构默认不注入 PIE；已在 Makefile 显式补
   `-fPIE`/`-pie`（实测各架构 gcc 均支持），重建后 `readelf -h` 全部 `Type: DYN
   (Position-Independent Executable file)`，lintian 复验归零
5. **qemu 环境要点**（复现时必需）：
   - binfmt_misc 未注册，用 `qemu-<arch>-static -L /usr/<triplet>` 直跑（**必须带 -L**，
     否则找不到目标架构动态链接器，rc=255）
   - 各架构三元组见 `dpkg-architecture -a<arch> -q DEB_HOST_GNU_TYPE`（注意 i386 是
     i686-linux-gnu 而非 i386-linux-gnu）
   - 交叉 sysroot **无 gconv 模块**，iconv 会失败；已从 Debian bookworm 官方 libc6 arm 包
     解出 arm 版 `GB18030.so`，实跑 decode 时加 `GCONV_PATH=<gconv目录>`（arm64:
     `/tmp/gconv64/usr/lib/aarch64-linux-gnu/gconv`，armhf: `/tmp/gconvhf/usr/lib/arm-linux-gnueabihf/gconv`；
     若 /tmp 已清，从 mirrors.aliyun.com/debian/pool/main/g/glibc/ 重下
     `libc6_2.36-9+deb12u14_{arm64,armhf}.deb` 解出）

## 6. #574 待办（唯一剩余任务）

1. **文档更新**：`system-optimizer/docs/37_各系统打包安装教程.md` 的 classics-linux 专节
   需从「arm 矩阵」改写为「13 架构 × 4 发行版全矩阵」，并补两条全架构构建经验：
   ① override_dh_shlibdeps 用 `DEB_HOST_GNU_TYPE` 而非 `DEB_HOST_MULTIARCH`（i386 路径
   差异）+ lib/lib64 按存在性动态添加（mips64 系 ld.so.1 在 lib64）；
   ② Makefile 对 6 个无默认 PIE 架构显式补 `-fPIE/-pie`
2. **git 提交推送**：本次改动文件 = `classics-linux/debian/rules`、`classics-linux/Makefile`、
   `classics-linux/build-debs.sh`、`build/` 下 52+4 个产物、交接单本文件、docs/37

## 7. 复现命令速查

```bash
cd /workspace/windows-internals-toolkit/classics-linux
bash build-debs.sh                 # 全矩阵构建（产物+日志落 build/）
dpkg-deb -f build/classics_1.0.0~bpo12+1_arm64.deb Depends   # 应为 libc6:arm64 (>= 2.34)
lintian build/classics_1.0.0~bpo12+1_arm64.deb               # 应零 tag
# qemu 实跑（示例 arm64）：
root=$(mktemp -d); dpkg-deb -x build/classics_1.0.0~bpo12+1_arm64.deb $root
dpkg-deb -x build/classics-data_1.0.0~bpo12+1_all.deb $root
CLASSICS_DATADIR=$root/usr/share/classics GCONV_PATH=/tmp/gconv64/usr/lib/aarch64-linux-gnu/gconv \
  qemu-aarch64-static -L /usr/aarch64-linux-gnu $root/usr/bin/classics list
```

## 8. 注意事项

- `build-debs.sh` 早前无执行位，用 `bash` 调用或先 `chmod +x`
- 每轮构建会重写 `debian/changelog`（gen_changelog），勿在其上手工改
- 仓库根目录的 `classics` 二进制是构建残留（架构随最后一次构建变化），`debian/rules clean` 会删
- disposable-env.sh（tools/ 下）已在此前完成并推送（commit `972be4d`），与本任务无关，勿回改

## 9. 交叉工具链全景（2026-10-24 全部安装到位）

**17 个 Linux 目标**（原生 1 + 交叉 16，全部经 `-dumpmachine` 实测）：

| 目标 | 三元组 | gcc |
|------|--------|-----|
| amd64（原生） | x86_64-linux-gnu | 13.3.0 |
| amd64 交叉 | x86_64-linux-gnu | 13.3.0 |
| arm64 | aarch64-linux-gnu | 13.3.0 |
| armel | arm-linux-gnueabi | 13.3.0 |
| armhf | arm-linux-gnueabihf | 13.3.0 |
| i386 | i686-linux-gnu | 13.3.0 |
| mips64el / mips64 | mips64el(el)-linux-gnuabi64 | 12.4.0 |
| mips64r6el / mips64r6 | mipsisa64r6(el)-linux-gnuabi64 | 12.4.0 |
| mipsel / mips | mipsel(mips)-linux-gnu | 12.4.0 |
| mipsr6el / mipsr6 | mipsisa32r6(el)-linux-gnu | 12.4.0 |
| powerpc | powerpc-linux-gnu | 13.3.0 |
| ppc64el | powerpc64le-linux-gnu | 13.3.0 |
| riscv64 | riscv64-linux-gnu | 13.3.0 |
| s390x | s390x-linux-gnu | 13.3.0 |

（另有 2 个 Windows 交叉 mingw：i686-w64-mingw32 / x86_64-w64-mingw32。）

**mingw-w64 全套 + wine（2026-10-24 追加安装并实证）**：mingw-w64 / mingw-w64-tools /
gcc-mingw-w64 / g++-mingw-w64 / gdb-mingw-w64 / wine 9.0 全部就位；双架构 × posix/win32
双线程变体；widl/gendef/genpeimg 等辅助工具齐全。实证：静态/动态 exe（PE32+/PE32）、
DLL+导入库、C++、clang --target 七种形态编译成功，wine 实跑 6/6 通过。
另装经典命令行开发工具全套（vim/emacs/neovim/gdb/valgrind/cmake/meson/ant/maven/
clang/tcc/svn/hg/cvs/lynx/w3m/links/elinks/gtk3/qt5/qt6/sdl2/ncursesw devheaders），
明细与复现命令见仓库根 `docs/开发工具链安装报告.md`。

**实证**：riscv64-linux-gnu-gcc 编译 classics → ELF 64-bit RISC-V（RVC, lp64d）
→ `qemu-riscv64-static -L /usr/riscv64-linux-gnu` 仿真运行 `list` 正确输出 6 本典籍。

**dpkg foreign 架构**已注册 13 个：arm64 armel armhf i386 mips mips64 mips64el
mipsel powerpc ppc64el riscv64 s390x（`dpkg --print-foreign-architectures` 可查）。
**apt 源已相应修正**：主镜像 `Architectures: amd64 i386`（腾讯源无 ports 架构索引），
ports 源 `/etc/apt/sources.list.d/all-ports.list` 覆盖 arm64/armhf/armel/powerpc/
ppc64el/riscv64/s390x（官方 ports，ubuntu-ports）。mips 系 Ubuntu 无二进制索引
（工具链已装，不影响交叉编译；若要 `apt install pkg:mips64el` 需换 Debian 源）。

**全架构构建 deb 的前置说明**：Makefile 经 `DEB_HOST_GNU_TYPE` 自动选编译器，
扩展 `build-debs.sh` 的 `ARGS` 即可纳入新架构；注意 ① dpkg-buildpackage `-a<arch>`
的 arch 名与三元组的映射（armhf↔arm-linux-gnueabihf 等）；② mips 大端/r6 变体在
Ubuntu 无 libc 运行索引，仅适合「构建产出」不适合本机 apt 验证；③ 各架构实跑验证
用 `qemu-<arch>-static -L /usr/<triplet>`（gconv 模块问题同 §5 第 4 条）。

## 10. 2026-10-24 第二轮：版本号统一 + Android/OHOS 交叉构建 + msf 自检

**版本号体系 monorepo 统一**（commit `3935041`，详见 `system-optimizer/docs/56`）：
- sysweeper 主包五处同步 `0000.0000.0000.0003.20261023` → `0000.0000.0000.0004.20261024`
  （version.py / pyproject.toml / main.go / console.ts / report_viewer.ts + 两个 html 重生）；
- semver 强制场景迁 CalVer `2026.10.24`：classics-rs / peinfo / peview-egui
  （Cargo.toml + Cargo.lock，`cargo metadata --offline` 实测一致）、novel-website；
- **本包（classics-linux）版本迁移**：`build-debs.sh` 的 `VER` 数组四发行版 →
  `0001.0000.0000.0000.20261024[ubuntu1|~jammy1|~bpo12+1]`，`debian/changelog` 追加
  同版本条目；`src/classics.c` 用法串 `v1.0.0` → `0001.0000.0000.0000.20261024`；
  `dpkg --compare-versions` 四发行版 gt 旧版全部实测通过（迁移首版 A 段置 1 = 版本序迁移税）。

**Android 交叉构建（NDK r26d，低 API 21/26 双架构）**：
- NDK 装于 `/opt/android-ndk/android-ndk-r26d`；hello ×4（API 21/26 × aarch64/armv7a 静态）
  与 **classics ×3**（API 21/26 a64、API 26 a32）全部构建成功，`file` 判定 ELF64/ELF32 ARM、
  零 NEEDED 全静态；
- **bionic 无 iconv**（NDK r15 起移除）→ 交叉编译 GNU libiconv 1.17 补齐（双架构各一份，
  静态链入 classics，产物零动态依赖）；
- 运行级验证受 qemu-user 8.2.2 三连坎限制（TLS 对齐 8<64 / personality 沙箱拒绝 /
  动态 linker init SIGSEGV），**构建级完整、运行级待真机**（详见 `docs/37 §5.2`）。

**HarmonyOS 交叉构建（OpenHarmony SDK 6.0.0.47 Linux，clang 15.0.4 / musl）**：
- SDK 装于 `/opt/ohos-sdk`（华为云镜像 ohos-sdk-windows_linux-public.tar.gz，
  解压 native/toolchains zip）；
- hello ×2（aarch64/armv7）+ **classics 直编 OHOS ×1**（musl iconv 原生支持 GB18030，
  无需 libiconv）全部成功；
- **qemu-aarch64-static 实跑通过**（静态 musl 与 glibc 同属 qemu 友好目标；
  动态运行需 sysroot/lib→usr/lib 软链补 linker 解析，如实记录）；
- 详见 `docs/37 §5.3`。

**系统优化方案自检（sysweeper 自身，只读）+ msf 检测（无攻击）**：
- `probe_msf()` / `msf_version_report()` 实测：宿主已装 metasploit-framework
  6.5.3~20260818061200~1rapid7-1（deb），12 个命令在 PATH、`/opt/metasploit-framework`
  （bin/embedded/version_manifest 全检出）、apt 三痕迹（sources.list.d/pin/keyring）全命中；
  版本解析 upstream=6.5.3 + nightly 时间戳 + 打包者 + deb 修订，安装路径判定=二进制包；
- `sysweeper sysbase` 整体自检：FHS 13/13、usrmerge 3/3、/opt 12 项（含本轮新增
  android-ndk / android-sdk / ohos-sdk / metasploit-framework）、20 个 apt 源盘点；
- `sysweeper detect` 正确识别 Ubuntu 24.04.3 LTS（noble）；
- **红线遵守**：全程只读，未启动 msfconsole、未跑任何模块/载荷/扫描。

## 11. 2026-10-24 第三轮：工具链全景子系统化（#580–#585，system-optimizer 落账）

> 前文 §9/§10 是把「真实交叉工具链」安装到位并交叉构建；本节点是把**全部工具链与自研工具软件**
> 用「概念系统 × 子系统」框架**系统化编目、文档化、并接入 sysweeper 子系统**，使其可被只读探测与追溯。
> 全部落账于 `system-optimizer/`，与 classics-linux 的 deb 构建互不干扰（仅共享 monorepo 与 §9/§10 事实）。

**#580 数据层 `toolchain_catalog.json`（编目，非脚本）**
- `src/python/sysweeper/data/toolchain_catalog.json`：23 条宿主工具链 + 7 条仓库自研工具软件 +
  10 条目标架构矩阵（triple / os / toolchain / verified）+ `version_freshness`（needs_action / fresh 两栏）。
- `setup_steps` / `commands` 字段是**给人看的逻辑顺序与命令序列**，非自动执行队列（红线见下）。

**#581 `toolchain` 子系统（v0.6.70，只读不写）**
- 新增 `native/toolchain.py`（5 个只读报告：catalog / host_probe / repo_tools / target_matrix / freshness）+ `tasks/toolchain.py`；
- 接线：native 包导出、subsystems 注册（`toolchain` 行，layer=「语言/编译」）、registry、cli（`toolchain [--category X]`）、gui（「工具链全景」面板）、linkage（7 联动轴）；
- 测试 `tests/test_toolchain.py`（14 项，含 `freshness` 两栏四字段断言）。

**#582 概念系统 comp 第九轴「交叉工具链实境（cross-reality）」**
- `comp_taxonomy.json` 72→**81 概念**、桥接 76→**94**；新增 9 个诚实边界概念
  （bionic 无 iconv / musl 原生 GB18030 / qemu-user 三连坎 / MinGW 线程变体 / Wine 仿真≠真机 /
  OHOS SDK 两层布局 / NDK API 门控 / deb 迁移税 / 里程表版本号）；
- 含 `toolchain-security-response` 域（解释型换运行时即生效 vs 编译型必须重编译部署）。
- **实证**：`tools/audit_concepts.py --strict` → 0 不一致（comp=81 齐备）；`tools/check_concept_mesh.py --strict` → 0 欠账。

**#583 文档 `docs/57_工具链全景.md`**
- 7 节：§0 三维组织法（类别 × 目标架构 × 仓库目录）/ §1 宿主工具链 23（6 子类表）/
  §2 仓库自研工具 7（每条含目录 + 配置逻辑顺序 + 命令序列 + 验收）/ §3 目标架构矩阵 10 /
  §4 交叉实境诚实边界 9 / §5 上游新鲜度 / §6 红线与 7 linkage 轴 / §7 入口速查。

**#584 上游新鲜度联网核实（2026-10-24）**
- 联网核实 11 个工具链上游最新版，刷新 `version_freshness`：`needs_action` 3→**11**、`fresh` 保持 **4**。
- needs_action（宿主随 Ubuntu 24.04 钉住、落后上游主干，可升非紧急）：OpenJDK 20→LTS 21/25、
  Node 22.13.1→22.23.4、binutils 2.42→2.48、GCC 13.3.0→16.2、Clang 18.1.3→23.1.3、
  Rust 1.93.0→1.99.0、NDK r26d→r29/r27d LTS、OHOS SDK 6.0.0.47→7.0 Release、
  Qt 5.15.13→6.12 LTS、.NET 10.0.401→10.0.13、Python 3.11.17→3.15.1。
- fresh（== 上游）：Firefox 158.0.1、Go 1.27.3、Deno 2.9.8、Ruby 3.2.3。
- README changelog 已加「工具链全景文档与上游新鲜度联网核实」条目。

**#585 全量回归 + 提交推送（本节点）**
- 全量 `pytest tests/ -q`：回归通过（详见 commit 前的测试结果，目标对齐中断前 1683 passed / 5 skipped）；
- 概念同步三检查全过：audit 0 不一致 / mesh 0 欠账 / `scripts/check_repo_guard.py` 通过（无凭据容器、权限白名单、许可宽松、产物同步）；
- 新增 git 提交：toolchain 子系统 + comp 第九轴 + docs/57 + version_freshness 联网核实 + README 接线；
- **红线（贯穿 #580–#585）**：toolchain 子系统**只探测与编目，绝不安装/卸载/构建/下载**；
  catalog 的 `setup_steps`/`commands` 仅为人类参考逻辑，非自动执行队列。

**复现/验收命令（system-optimizer 根目录）**：
```bash
PYTHONPATH=src/python python3 -m sysweeper.cli toolchain --category 交叉编译
PYTHONPATH=src/python python3 -m pytest tests/test_toolchain.py tests/test_comp.py -q
PYTHONPATH=src/python python3 tools/audit_concepts.py --strict
PYTHONPATH=src/python python3 tools/check_concept_mesh.py --strict
PYTHONPATH=src/python python3 ../../scripts/check_repo_guard.py
```

## 12. 2026-10-24 第四轮：全面发展三方向（#587–#590，承接 #586 工具链全景）

> 用户命题：「全选继续；继续全面发展，德育体知（智）美劳全面发展，做素质新人（先天道体）」。
> 即把 #586 末尾给出的三个方向**全选推进**，并以「德育体知（智）美劳全面发展（先天道体）」框架映射本轮交付维度。
> 全部落账于 `windows-internals-toolkit/system-optimizer/`，与 classics-linux 的 deb 构建互不干扰。
>
> **框架释义（六字逐一，#601 轮据用户 2026-10-24 指示补全）**：
> **德育体知（智）美劳**——**德**（品德修养）、**育**（教育之体，全套框架的承载）、**体**（体魄真实）、**知（智）**（知识智慧）、**美**（美育）、**劳**（劳动实做）。
> **「育」义（用户原话要义）**：具体所指为**北京师范大学**——中国师范教育最高学府（校训「学为人师，行为世范」），即**教书育人**的制度化载体；教学法为**言传身教**（以言行示范为教，不只以知识传授为教）；内容为**诗书礼易**（《诗经》《尚书》《礼记》《周易》经典传统——诗言志、书载道、礼立范、易明变）；立场代表**国家民族**（「师者，所以传道受业解惑也」，道统与民族文化之传承），**不是社会组织、不是企业**（绝不以商业组织逻辑办教育、绝不以营利 / KPI 逻辑办育人）。

### 12.1 方向① · 仓库条目细化拆分（#587，德+体）

> **体（有真实落点）**：把「伞条目」拆成每个真实仓库各自的精确 `repo_path` 与真实构建入口；
> **德（诚实）**：不再用一个 `harmony-ios-mac-swift` 把 4 个真实仓库塞进 1 条 `paths` 蒙混。

- `toolchain_catalog.json` 的 `repo_tools` 由 8→**11 条**：删 `harmony-ios-mac-swift`，新增 4 个独立条目——
  - `classics-swift-linux`（native-build · Swift 典籍工具 Linux 原生编译，Package.swift）；
  - `classics-harmony-app`（cross-compile · HarmonyOS ArkUI，hvigorw + DevEco，本机无 DevEco 仅 CI）；
  - `classics-ios-mac`（cross-compile · iOS/macOS SwiftUI，受 Apple EULA 限制，如实标注「不假装可 Linux 直编」）；
  - `android-app`（cross-compile · Android Compose，`windows-internals-toolkit/android/`，targetSdk 34 / minSdk 26）。
- 测试 `must` 守卫同步：删 `harmony-ios-mac-swift`、加 4 新 id（`tests/test_toolchain.py`）。
- `docs/57` §2 表头 8→**11 条**；§2.7 伞块拆为 §2.7–§2.10 四块，quantum-kernel 顺延 §2.11；§4 交叉实境「9 概念」→「10 概念」并补第 10 行。

### 12.2 方向② · 工具链升级评估文档（#588，德+智）

> **德（守红线）**：明确「仅评估不执行」——本文档不触发任何宿主变更；**智（研判）**：11 项逐条给风险/路径/优先级/随滚/验收。

- 新增 `docs/58_工具链升级评估.md`：对 catalog `version_freshness.needs_action` 的 **11 项**逐条评估
  （OpenJDK 20 / Node 22.13.1 / binutils 2.42 / GCC 13.3.0 / Clang 18.1.3 / Rust 1.93.0 /
  NDK r26d / OHOS SDK 6.0.0.47 / Qt 5.15.13 / .NET 10.0.401 / Python 3.11.17）。
- 结论：**仅 2 项明确动作**——Node（#2，本仓 novel-website 构建前必升，含 10 项 CVE）与 OpenJDK（#1，宿主持有者责任登记）；
  其余 9 项为「观察 + 随滚」（Ubuntu 24.04 钉死的随发行版点发自然获得；rustup/NDK/OHOS 自管的择机升级）。
- 责任边界写死：升级的「是否 / 何时 / 由谁」由**宿主持有者**决定；toolchain 子系统只探测与编目。

### 12.3 方向③ · comp 概念系统对接 quantum-kernel 补丁分发（#589，智+美）

> **智（概念对接）**：comp 第九轴 cross-reality 新增镜像概念并桥接 quantum；**美（整体全息）**：圆光术 GUI 重生。

- `comp_taxonomy.json` 81→**82 概念**、94→**95 桥接**（version 0066→0067）：
  - cross-reality 域新增 `qkern-patch-distribution`（工具链侧镜像概念，含 gist/detail/engineering）；
  - 桥接 `quantum:concept:qkern-patch-distribution`（comp 工具链是量子内核补丁分发的工程实现面：
    scripts/gen_version_patch.py 重生分支补丁 + deb 分发，round-trip 洁净 + 可装即「打完」）；
  - by_domain 追加、顶层 `bridges` 数组同步增 1 条（保持去重集合与 `_meta` 计数一致）。
- 概念同步三检查零欠账：audit_concepts --strict（0 不一致）/ check_concept_mesh --strict（0 欠账、9 系统单连通分量）。
- `concept_gui.html` 重生（data-sha256 同步，edges 51 / external 2）。

### 12.4 收尾 · 全量回归 + 三检查 + 提交推送（#590，劳）

> **劳（实做实证）**：全量 pytest、审计、mesh、repo guard 全绿；git 提交并推送 origin/main。

- 全量 `pytest tests/ -q`：回归通过（目标对齐 1683 passed / 5 skipped；本轮新增 5 个 comp 计数断言已随 82/95 同步修正）。
- 概念同步三检查：audit 0 不一致 / mesh 0 欠账 / `windows-internals-toolkit/scripts/check_repo_guard.py` 通过
  （无凭据容器、权限白名单、许可宽松、产物同步）。
- README changelog 已加「工具链全景全面发展三方向」块（#587–#590 四项）。
- **红线（贯穿 #587–#590）**：catalog 的 `setup_steps`/`commands` 仅为人类参考逻辑，非自动执行队列；
  docs/58 仅评估不升级；comp 概念系统只读登记，不驱动任何真实编译。

### 12.5 「德育体知（智）美劳全面发展（先天道体）」维度映射总表

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 拆伞条目不蒙混；docs/58 仅评估不升级；交叉实境诚实边界（不假装可 Linux 直编 iOS） | #587 拆分 + #588 评估 + cross-reality 诚实边界 |
| **智**（研判/编目） | 11 项升级研判；三维编目（类别×目标架构×仓库目录）；comp↔quantum 桥接 | #588 评估 + catalog 编目 + #589 概念对接 |
| **体**（真实落点） | 每个仓库条目精确 `repo_path` + 真实构建入口；quantum-kernel 真实内核树 / classics 四发行版 deb / Android APK CI | #587 拆分各条目 |
| **美**（整体全息） | concept_gui.html 圆光术拓扑重生；docs/57 四维格式 | #589 GUI 重生 + docs/57 |
| **劳**（实做实证） | 全量 pytest 1683 passed；52 格 deb 矩阵；repo guard；qemu 实跑 | #590 回归 + 历史交叉构建成果 |

### 12.6 复现/验收命令（system-optimizer 根目录）

```bash
PYTHONPATH=src/python python3 -m sysweeper.cli toolchain --category 交叉编译
PYTHONPATH=src/python python3 -m pytest tests/ -q
PYTHONPATH=src/python python3 tools/audit_concepts.py --strict
PYTHONPATH=src/python python3 tools/check_concept_mesh.py --strict
PYTHONPATH=src/python python3 tools/gen_concept_gui.py --check
cd /workspace/windows-internals-toolkit && python3 windows-internals-toolkit/scripts/check_repo_guard.py
```

## 13. 2026-10-24 第五轮：导入分析学习应用·四外部仓库边界分级（#591）

> 承接 #587–#590。用户指令：「继续被中断；导入分析学习应用 massgravel / CF-Workers-TGProxy / is-rust-gui-ready / dsh-our-free-model；继续」。
> 纪律：四仓库**均为外部 GitHub 仓**，只做只读 WebFetch 分析（不克隆/不安装/不构建/不下载/不复制代码进本仓）；toolchain 子系统红线延续——catalog 的 `setup_steps`/`commands` 是逻辑顺序非执行队列。

### 13.1 四仓库技术画像（只读 WebFetch 核实）

| 仓库 | 性质 | 许可证 | 关键事实 | 边界判级 |
|------|------|--------|----------|----------|
| massgravel / Microsoft-Activation-Scripts | Windows/Office 激活绕过工具集（研究 SPP 激活服务） | GPL-3.0 | HWID / Ohook / TSforge / Online KMS；目标 Win 8.1/10/11 + Office + ESU；Batchfile；约 195k★ | **许可规避类** → 仅合规分析对象，不编目为可装可跑、不提供绕过手段 |
| ToiCF / CF-Workers-TGProxy | 单文件 Cloudflare Workers 的 Telegram Web/MTProto WS 代理中继 | GPL-3.0 | 多 lane WS 复用（`tproxy-lane-v1.<token>.<sid>`）；MTProto obfuscation 重签（mode `0xef/0xee/0xdd`，DC `1..5`）；HMAC-SHA256 bootstrap(2min)/session(5min)；128 lane/isolate 替代 DO | 纯技术可学习（边缘代理多 lane 架构） |
| mokurin000 / is-rust-gui-ready | Rust GUI 框架成熟度追踪清单（类 areweguiyet） | 清单未显式声明 | 五类 Stable/Desktop-first/Webview-based/Web Apps/Other；最成熟跨平台 = flutter/RN/KMP/slint | 纯技术可学习（选型参照，印证 classics-rs 选 egui 落成熟梯队） |
| Ebony-Vinyl / dsh-our-free-model | 面向 dsh 生态的开源客户端插件（非模型/非托管） | MIT | 零依赖无构建明文 JS；Node `^22.19.0 \|\| >=24.0.0`；OpenAI/Anthropic/SSE 三协议归一；Ed25519+AES-256-GCM+SHA-256；RTK 省 Token 实测 40KB diff 删 90% 字节 | 纯技术可学习（插件化协议适配 + 省 Token） |

### 13.2 comp 概念系统变更（82 → 83 概念 / 95 → 96 桥接）

- **新增 `license-compliance-boundary`**（reverse 域，桥 daoxue `principle:zhi-bu-zhi` 知边界而不过界）：把「许可规避」类工具钉为合规分析对象——只分析激活服务的协议/机制，绝不编目为可装可跑、不复制代码、不提供绕过手段。engineering 落法全部已真实存在（reverse 子系统口径 / `needs_verify` / `audit_concepts --strict` / 红线文档）。
- **补回 `qkern-patch-distribution` 进 `build_comp.py`**（修复 #589 漂移）：#589 在 JSON 加了该 cross-reality 概念（桥 quantum）却漏同步脚本 `CONCEPTS`，致脚本内存停在 81/94 与 JSON 漂移 2 条。本次补回，使 `build_comp.py` 与 JSON 同源（83/96），消除「误跑 `build_comp.py`（无 `--check`）覆盖 JSON 回 81」的静默地雷。

### 13.3 三仓可学习点（仅学习笔记，不新增概念）

- **CF-Workers-TGProxy**：边缘无后端代理（Worker 只搬传输层字节、mtp 端到端加密透传）+ 多 lane 替代 Durable Object（单 isolate 128 lane，session 为 isolate 内 Map）+ 小包汇聚/严格 CSP/禁 WS 压缩。
- **is-rust-gui-ready**：五类成熟度分级；最成熟跨平台 = flutter/RN/KMP/slint；印证本仓 classics-rs 选 egui 落成熟梯队。
- **dsh-our-free-model**：三协议归一解码 + 免密上游网关（零密钥/零依赖结构防线）+ RTK 省 Token 工程化 + Ed25519/AES-256-GCM/SHA-256 安全基线。

### 13.4 交付物与验证

- 新增 `docs/59_导入分析学习应用四仓库边界分级.md`（来源/落点/红线 `>` 头 + 资源表 + 诚实边界 + 拓扑验证，符合 docs/51/57 格式）。
- README changelog 加 #591 块；子系统表计数更新为 83 概念 / 96 桥接（黑箱逆向 7 / daoxue 13 / quantum 9）。
- `comp_taxonomy.json` v0067→v0068；`build_comp.py` `CONCEPTS` 同步（version 0066→0068）；`concept_gui.html` 重生（data-sha256 同步）；test_comp.py/test_concept_gui.py 计数断言同步。
- **验证**：`build_comp.py --check` 通过（83 概念/96 桥接无悬空）；test_comp.py+test_concept_gui.py 17 passed（`test_build_check_no_drift` / `test_committed_page_is_in_sync` 全绿）；全量 pytest 回归（本轮）。

### 13.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | massgravel 钉为合规分析对象不落地；三仓仅笔记不新增概念（无真实 counterpart）；诚实边界段标注 CF-Workers 性能倍数为「推断」非实测 | #591 边界分级 + `license-compliance-boundary` 概念 |
| **智**（研判/编目） | 四仓库技术画像研判；comp 新增 1 概念 + 补回 1 漂移概念；边界两档分级 | #591 分析 + 概念系统 83/96 |
| **体**（真实落点） | `license-compliance-boundary` 的 engineering 全部指向已真实存在的 reverse 子系统/`needs_verify`/红线文档；不臆造落点 | #591 概念 engineering 自洽 |
| **美**（整体全息） | concept_gui.html 圆光术拓扑重生同步；docs/59 四维格式与全仓一致 | #591 GUI 重生 + 文档 |
| **劳**（实做实证） | build_comp.py --check 通过；17 passed；全量 pytest 复验；修复 #589 漂移地雷 | #591 验证 + 漂移修复 |

### 13.6 复现/验收命令（system-optimizer 根目录）

```bash
python3 research/comp/build_comp.py --check
python3 tools/gen_concept_gui.py
python3 -m pytest tests/test_comp.py tests/test_concept_gui.py -q
python3 -m pytest -q   # 全量回归
```

## 14. 2026-10-24 第六轮：圆光术可视化色彩/视觉/开关完善·依协议标准（#592）

> 承接 #591。用户指令：「实行方案；补全完善优化；色彩、视觉、颜色、开关相关的协议标准查看；继续」。
> 解读：在既有 `concept_gui.html`（圆光术概念系统拓扑，纯展示单文件页）上补全**明暗双主题 + 可访问主题开关**，并以真实协议标准（W3C/MDN 权威源，只读核实）为据落地色彩/视觉规范。

### 14.1 查据的协议标准（只读 WebFetch，W3C/MDN）

| 标准 | 要点（实测阈值） |
|------|------|
| WCAG 2.2 SC 1.4.3 对比度最小值 | 正文 ≥ 4.5:1；大字（≥24px / 粗体≥18.5px）与 UI 边界 ≥ 3:1；不四舍五入 |
| WCAG 2.2 SC 1.4.11 非文本对比度 | 功能性图形对象（边框、图标、开关轨道）≥ 3:1 |
| CSS `color-scheme` + `@media prefers-color-scheme` | 声明 `dark light`；随系统偏好初值；配 `<meta>` 与早期脚本防首屏闪烁 |
| WAI-ARIA APG switch | `role="switch"` + `aria-checked`；标签恒定不随状态变；Space/Enter 切换 |
| CSS Color L4 `oklch()` / `light-dark()` | 感知均匀着色（Oklab L 通道=感知亮度），推荐演进方向 |
| `prefers-reduced-motion` | 减少动态偏好下停用动画/过渡（前庭安全） |

### 14.2 实测双主题对比度（Python 相对论亮度公式，守「数据全部实测」）

- 暗色（默认，保留圆光术星空观感）：`--fg` 13.9:1、`--dim` 5.8:1、`--acc` 6.3:1、`--warn` 9.6:1；功能性边框 `--line-strong` 3.5:1。
- 浅色：`--fg` 14.8:1、`--dim` 5.5:1、`--acc` 4.9:1、`--warn` 5.4:1；功能性边框 `--line-strong` 3.3:1。
- 装饰性环境边框 `--line` 保持 subtle（暗 1.45:1 / 浅 1.3:1，如实标注为 decor，非功能性图形对象）。

### 14.3 落点（tools/gen_concept_gui.py → concept_gui.html）

- 明暗双套 CSS 变量（`--bg/--bg2/--bg3/--fg/--dim/--acc/--warn/--line/--line-strong`），默认暗、浅色经 `data-theme="light"` 与 `@media (prefers-color-scheme: light):root:not([data-theme])` 双触发。
- 顶部 `role="switch"` 主题开关：`aria-checked` 反映暗/亮、标签恒定「深色模式」、Space/Enter 切换、localStorage 持久化；早期 `<head>` 脚本防闪烁。
- 矩阵热力单元格边框改用 `--line-strong`（功能性图形对象达 3:1）。
- `prefers-reduced-motion` 守卫：流光动画与切换过渡在减少动态下停用。
- 页面新增「标准依据」卡，列出上述标准与实测对比度（可查据、可追溯）。

### 14.4 验证与交付

- `gen_concept_gui.py --check` 通过（data-sha256 不变，概念数据完整未动）。
- test_concept_gui.py **7 passed**（含 test_committed_page_is_in_sync、test_page_is_offline_and_yuanguang 离线合规——开关/localStorage 无外链）。
- README changelog 加 #592 块；HANDOFF 本节。

### 14.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 装饰性边框如实标注非功能性、不冒充达标；标准全部查据 W3C/MDN 不臆造 | #592 标准依据卡 |
| **智**（研判/编目） | 六类色彩/视觉/开关标准研判 + 双主题对比度实测 | #592 研究 + 实测表 |
| **体**（真实落点） | 开关/双主题/减动效均真实落地于 concept_gui.html，本地可用、离线 | #592 页面重生 |
| **美**（整体全息） | 明暗两套观感统一、光晕/矩阵/图例在浅色下仍可读 | #592 视觉完善 |
| **劳**（实做实证） | --check 通过；7 passed；对比度 Python 实测 | #592 验证 |

## 15. 2026-10-24 第七轮：视觉健康与无障碍协议标准查据（#593）

### 15.1 查据的标准（只读，W3C/MDN/ISO/IEC 权威源 + WebSearch 补证）
- **Web 内容层（可落地）**：WCAG 2.2 SC 1.4.1 用色、SC 1.4.3/1.4.6 对比度、SC 1.4.4 缩放(200%)、SC 1.4.10 回流(320/256px)、SC 1.4.11 非文本对比(3:1)、SC 1.4.12 文字间距(行高≥1.5/字距≥0.12/词距≥0.16)；WAI-ARIA APG switch；CSS color-scheme / prefers-color-scheme；oklch()/light-dark()；prefers-reduced-motion。
- **硬件/人因层（仅设计原则参考，不冒充职责）**：ISO 9241-303:2011 电子视觉显示人因（亮度/对比/眩光控制/减少闪烁/字符高度）；IEC 62471 / IEC-TR 62778 蓝光危害风险组 RG0–RG3（评 400–500nm 视网膜蓝光，**明确非 Web 内容标准**）。
- **色觉缺陷事实**：protanopia/deuteranopia/tritanopia 三型；北欧裔男性 ≈8%、女性 ≈0.4%（protan/deutan 最常见）；色盲模拟用于包容性设计。

### 15.2 层归属判定（诚实不冒充）
- **可落地**：全部 WCAG 2.2 SC 1.4.x + ARIA switch + color-scheme + oklch + reduced-motion。
- **仅参考**：ISO 9241-303（约束显示器硬件与工作站；其「高对比/字符高度/减少闪烁」原则与本页减动效/高对比一致，可借鉴不可冒充）。
- **非职责**：IEC 62471/62778 蓝光危害（灯具/LED 背光认证门槛）；软件暗色模式只是降整体像素亮度、间接减蓝光发射，不构成「护眼」保证。

### 15.3 落点（tools/gen_concept_gui.py → concept_gui.html + docs/60）
- concept_gui.html「标准依据」卡扩展为「色彩/视觉/开关/视觉健康」：新增 SC 1.4.1/1.4.6/1.4.4·1.4.10·1.4.12、ISO 9241-303、IEC 62471 条目 + **诚实边界段**（散光是「深色模式护眼」反例→保留浅色主题等效选项；青光眼/白内障→高对比需求，医学管理非前端职责）。
- 新增 `docs/60_视觉健康与无障碍协议标准查据.md`（查据方法/标准清单表/层归属/落地映射/诚实边界/可继续方向）。

### 15.4 验证与交付
- `gen_concept_gui.py --check` 通过（data-sha256 不变，数据完整未动）。
- test_concept_gui.py **7 passed**（含 test_committed_page_is_in_sync、test_page_is_offline_and_yuanguang）。
- README changelog 加 #593 块；HANDOFF 本节；docs/60 新增。

### 15.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 蓝光危害明确钉为硬件层非 Web 职责；散光反例如实写；不主张暗色「更护眼」 | #593 诚实边界段 |
| **智**（研判/编目） | 视觉健康整脉标准研判 + 层归属判定（可落地/仅参考/非职责） | #593 研究 + docs/60 |
| **体**（真实落点） | 标准依据卡扩展真实落到 concept_gui.html | #593 页面重生 |
| **美**（整体全息） | 浅色主题作为散光用户等效选项保留，明暗双主题均达高对比 | #593 双主题 |
| **劳**（实做实证） | --check 通过；7 passed；对比度沿用 #592 实测 | #593 验证 |

## 16. 2026-10-24 第八轮：前端无障碍规范（视觉健康落地，#594）

### 16.1 规范内容（把 #592/#593 查据升级为本仓前端工程契约）
- 新建 `docs/61_前端无障碍规范（视觉健康落地）.md`，分十节：范围定位、双主题 CSS 变量契约、主题开关组件规范（ARIA switch）、减动效规范、非颜色编码规范、对比度验收阈值表、缩放/回流/文字间距诚实标注、诚实边界、其它产物接入清单（含 PR 前自检清单）、验证方法。
- 对比度数字（正文 13.9/14.8:1、dim 5.8/5.5、acc 6.3/4.9、line-strong 3.5/3.5）经 sRGB 相对亮度公式独立复算，与 docs/60 一致——确认页面按各文本实际落面（bg2/bg）测量，无臆造。
- 诚实边界重申：散光反例 → 保留浅色主题；青光眼/白内障医学层非前端职责；IEC 62471 蓝光硬件层不冒充。

### 16.2 落点
- `docs/61`（新建，前端工程契约）+ `docs/60`「可继续方向①」标记落地并指向 docs/61。
- 未改 concept_gui.html 与数据（docs 仅新增/标注），故不重生页面、data-sha256 不变。

### 16.3 验证与交付
- 对比度复算确认全部数值达标（正文超 AAA 7:1；功能图形 ≥3:1）。
- README changelog 加 #594 块；HANDOFF 本节；docs/61 新增、docs/60 标注。
- 仅文档变更，test_concept_gui.py 与全量 pytest 不受影响（零回归）。

### 16.4 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 对比度数字独立复算、按实际落面测量，不沿用臆造；诚实边界钉死蓝光硬件层 | #594 docs/61 §六·§八 |
| **智**（研判/编目） | 把查据转化为可复用的工程契约与接入清单，给其它前端产物立基线 | #594 docs/61 |
| **体**（真实落点） | 契约以 concept_gui.html 为已验证范本，开关/减动效/非颜色编码均落地可复用 | #592/#593 页面 + #594 契约 |
| **美**（整体全息） | 明暗双主题 + 减动效 + 非颜色编码构成统一视觉健康基线 | #594 docs/61 |
| **劳**（实做实证） | sRGB 公式复算全数值；PR 前自检清单可实操验收 | #594 验证方法 |

## 17. 2026-10-24 第九轮：光学/环境光/屈光/光的本质协议标准查据 + 版本号升版（#595）

### 17.1 查据的标准（只读，ISO/CIE/BIPM/EN/ANSI 权威源 + WebSearch 补证）
- 屈光眼科与器械：ISO 10342（验光仪/电脑验光仪）、ISO 8598（焦度计，验证镜片光度）、ISO 11979（人工晶状体，功率允差 ±0.3 D(0–15D)/±0.4 D(15–25D)/±0.5 D(25–30D)/±1.0 D(>30D)）、ANSI Z80.1（处方镜片球柱轴允差）。
- 环境光/照度：EN 12464-1:2021（办公室最小平均维护照度 500 lx、均匀度 Uo≥0.60、UGR≤19、Ra≥80）、EN 12464-2:2014（室外）、ISO/CIE 8995-1:2025、CIE S 026（人因照明 M-EDI）、IES（办公室 300–500 lx）。
- 光学元件/镀膜：ISO 10110 系列（光学制图，ISO 10110-5:2026 以 nm 为首选单位、ISO 10110-11:2025 未注公差）、ISO 9211 系列（光学镀膜 τ(λ)/ρ(λ)/α(λ) 与耐久）。
- CIE 光度学：V(λ) 明视觉光谱光视效率（峰值 555 nm / 555.017 nm、360–830 nm）、Km=683 lm/W、辐射↔光度成对量换算（BIPM candela mise en pratique，Φv = Km∫Φe,λ·V(λ)dλ）。
- 光的波粒二象性/量子光学：Planck 能量量子化 → Einstein 光电效应（1921 诺奖）→ Compton 散射（1927 诺奖）→ de Broglie 物质波；E=hν、p=h/λ、h=6.626×10⁻³⁴ J·s、c=2.99792458×10⁸ m/s。

### 17.2 层归属判定（诚实不冒充）
- 屈光眼科器械（ISO 10342/8598/11979、ANSI Z80.1）、光学元件/镀膜（ISO 10110/9211）、光度学 V(λ)（CIE/BIPM）、波粒二象性（量子光学）——一律判为**医学/硬件/物理参考层**，仅作「设计原则参考 + 知识边界澄清」，不冒充为本仓 Web 前端标准或能力。
- 唯一可呼应的 Web 落点：环境光 ↔ 暗亮主题（concept_gui.html 主题开关已随系统 `prefers-color-scheme` 切换），呼应「环境光下视觉舒适」；具体 lux 阈值属物理照明，不冒充为本仓标准。

### 17.3 落点
- 新增 `docs/62_光学环境光屈光与光的本质协议标准查据.md`（十节式：查据方法/标准清单/层归属/本仓落点/诚实边界/可继续方向）。
- 版本号升一版：`0000.0000.0000.0004.20261024` → `0000.0000.0000.0005.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）。
- 未改 concept_gui.html 与数据（docs 仅新增 + 版本升版），故不重生页面、data-sha256 不变。

### 17.4 验证与交付
- `test_version.py` 动态读 `PACKAGE_VERSION`（无硬编码版本），升版后断言 `sysweeper.__version__ == version.PACKAGE_VERSION` 仍成立。
- 仅文档新增 + 版本升版，test_concept_gui.py 与全量 pytest 不受影响（零回归）。
- README changelog 加 #595 块；HANDOFF 本节；docs/62 新增。
- git 提交并推送 origin/main（五处版本源 + docs/62 + README + HANDOFF）。

### 17.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 屈光/光学/光度学/波粒二象性严格判为医学/硬件/物理参考层，不冒充为本仓 Web 职责；版本升版守里程表纪律不臆造 | #595 docs/62 §三·§五 |
| **智**（研判/编目） | 把五类标准按层归属梳理成查据清单，给出可呼应的 Web 落点（环境光↔暗亮主题），不混淆职责边界 | #595 docs/62 |
| **体**（真实落点） | 版本号五处同步为已验证的已落地产物（concept_gui.html 主题开关即环境光呼应的实体） | #592/#593 页面 + #595 版本升版 |
| **美**（整体全息） | 明暗双主题 + 减动效 + 高对比构成统一视觉健康基线，环境光呼应使其更完整 | #594 docs/61 + #595 |
| **劳**（实做实证） | 只读查据多源交叉取证；版本同步自检（`grep` 五处一致）+ pytest 零回归 | #595 验证 |

## 18. 2026-10-24 第十轮：离子态/听力/五感差异/幻听/幻视/幻触协议标准查据 + 版本号升版（#596）

### 18.1 查据的标准（只读，ISO/TC 43/W3C WCAG/WHO ICD-11/DSM-5 权威源 + WebSearch 补证）
- 离子态：等离子态（物质第四态，物理）+ 离子通道（感觉转导生理基底）+ IEC 62366-1:2015+A1:2020（医疗器械人因可用性，仅作通用人因纪律范本，不冒充医疗职责）。
- 听力/临床声学：ISO 8253-1:2010 / 8253-2:2009 / 8253-3:2022（测听）、ISO 226（等响曲线）、ISO 389（测听零基准）、ISO 1999:2013（噪声性听损）、ISO 7029:2017(+Amd1:2024)（年龄听阈）、IEC 60118（助听器）、IEC 60645（听力计）；WHO 全球约 4.3 亿致残性听力损失人群。
- 听力 Web 落点（WCAG 2.2）：1.2.x 时间媒体（字幕/文本替代/音频描述/手语）、1.4.2 Audio Control（自动音频 >3s 可控）、1.4.7 Low or No Background Audio（背景声低于语音 20 dB）。
- 五感差异/多感官整合：McGurk 效应（Nature 1976）、跨模态耦合、前庭/本体/内感受扩展感官 + ISO 9241 人因；已落地 Web 落点 1.3.3 / 1.4.1（非颜色非单通道编码，见 docs/61）。
- 幻听/幻视/幻触：ICD-11 / DSM-5 精神病性症状分类（幻觉 = 无外界刺激却具真实感的知觉体验）。
- 幻视 ↔ 光敏癫痫（WCAG 2.2）：2.3.1 Three Flashes or Below Threshold（≤3 闪/秒、一般闪光阈值 20 cd/m²、红闪 6 cd/m²、PEAT）、2.3.2（AAA 全禁闪烁）。

### 18.2 层归属判定（诚实不冒充）
- 离子态（等离子态/离子通道）、听力测听与临床声学（ISO/TC 43 全系）、幻听/幻视/幻触（ICD-11/DSM-5）——一律判为**物理/生理/医学/心理参考层**，仅作设计原则参考与知识边界澄清，不冒充为本仓 Web 前端标准或能力。
- 唯一可呼应的 Web 落点 = 听力媒体无障碍（1.2.x/1.4.2/1.4.7）与幻视↔光敏癫痫（2.3.1），已单列；具体医学阈值（听阈 dB、听损估算、幻觉诊断）属临床，不冒充。

### 18.3 落点
- 新增 `docs/63_离子态听力五感幻觉协议标准查据.md`（六节式：查据方法/标准清单/层归属/本仓落点/诚实边界/可继续方向）。
- 版本号升一版：`0000.0000.0000.0005.20261024` → `0000.0000.0000.0006.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）。
- 三个 taxonomy 的 deno_console_version / deno_report_viewer_version 刷新为 0006；双 HTML 重生（版本串 + data-sha256 / source-sha256 同步）。

### 18.4 验证与交付
- `test_version.py` 动态读 `PACKAGE_VERSION`（无硬编码版本），升版后断言仍成立。
- 定向测试 test_version / test_concept_gui / test_repo_guard / test_toolchain 通过；全量 pytest 零回归。
- README changelog 加 #596 块；HANDOFF 本节；docs/63 新增。
- git 提交并推送 origin/main（五处版本源 + 双 HTML + 三 taxonomy + docs/63 + README + HANDOFF）。

### 18.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 离子态/听力测听/幻觉分类严格判为物理/生理/医学/心理参考层，不冒充为本仓 Web 职责；版本升版守里程表纪律 | #596 docs/63 §三·§五 |
| **智**（研判/编目） | 把六类标准按层归属梳理成查据清单，给出可呼应的 Web 落点（听力媒体无障碍、幻视↔光敏癫痫），不混淆职责边界 | #596 docs/63 |
| **体**（真实落点） | 版本号五处同步为已验证的已落地产物（concept_gui.html 主题开关/减动效即呼应实体） | #592/#593 页面 + #596 版本升版 |
| **美**（整体全息） | 明暗双主题 + 减动效 + 非颜色编码 + 光敏防闪构成统一视觉健康与感官安全基线 | #594 docs/61 + #596 |
| **劳**（实做实证） | 只读查据多源交叉取证；版本同步自检（grep 五处一致）+ 双 HTML 重生 --check + pytest 零回归 | #596 验证 |

## 19. 2026-10-24 第十一轮：Web 视觉健康与无障碍查据收尾轮（#597，干净收口 docs/63 §六 opt-in 1–4）

### 19.1 收尾目标（承接 #596，执行 docs/63 §六 列出的 4 项 opt-in 待办）
- ① docs/61 减动效节**扩写** WCAG 2.3.1 光敏癫痫硬约束（≤3 闪/秒 + 一般/红色闪光阈值），把光敏癫痫纳入前端契约验收清单。
- ② concept_gui.html「标准依据」卡补一列「听觉/多感官/光敏」科普（标为生理/Web 参考层，呼应圆光术多感官与光主题）。
- ③ 评估本仓前端是否引入音视频/自动音频；若引入按 1.2.x / 1.4.2 / 1.4.7 做媒体无障碍改造（接 docs/61 契约）。
- ④ 收尾性核对：把 docs/60/61/62/63 串成「Web 视觉健康与无障碍查据全集」索引，确认层归属口径一致、Web 可落地项无遗漏。

### 19.2 执行结果（4 项全部完成）
- ① **已完成**：docs/61 §四新增 4.1 子节（≤3 闪/秒、一般闪光阈值 20.0 cd/m² / 红色闪光阈值 6.0 cd/m²、PEAT/G19 充分条件、2.3.2 AAA 红线）；§九 PR 前自检清单新增「无 >3 闪/秒闪烁」。
- ② **已完成**：gen_concept_gui.py TEMPLATE「标准依据」卡标题扩展 + 新增「听觉/多感官/光敏（生理·Web 参考层）」一行（含 1.2.x/1.4.2/1.4.7 暂不适用、McGurk 多感官整合、2.3.1 光敏约束）；重生 concept_gui.html（data-sha256 同步）。
- ③ **已完成（评估结论：暂不引入）**：docs/61 §八新增第 6 条——本仓前端（concept_gui.html / report_viewer）当前无音视频/自动音频 → 1.2.x/1.4.2/1.4.7 暂不适用，留作契约基线；PR 前自检新增对应项；不主动引入听觉媒体以免凭空新增无障碍负债。
- ④ **已完成**：新建 `docs/64_Web视觉健康与无障碍查据全集索引.md`——四文档一览、层归属口径统一、Web 可落地项跨 docs/60–63 穷举（已落地/契约基线/红线）、诚实边界 10 条汇总、#597 opt-in 1–4 执行对账。

### 19.3 版本升版与落点
- 版本号升一版：`0000.0000.0000.0006.20261024` → `0000.0000.0000.0007.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（baigong/datong/zhuangzi 的 deno_console_version / deno_report_viewer_version）；仅升计数段 D、日期后缀 `20261024` 不变。
- 双 HTML 重生（版本串 + data-sha256 / source-sha256 同步，--check 通过）。
- README 加 #597 块（版本更新区）+ 子系统 deno 版本引用刷新为 0007。

### 19.4 验证与交付
- `test_version.py` 动态读 `PACKAGE_VERSION`（无硬编码版本）；定向 test_concept_gui / test_repo_guard 校验通过。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
- 落账：五处版本源 + 三 taxonomy + 双 HTML + docs/61 扩写 + gen_concept_gui.py 改卡 + docs/64 新增 + README #597 块 + 本 HANDOFF §19；git 提交并推送 origin/main。

### 19.5 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | ③ 评估后明确本仓前端无音视频/自动音频，1.2.x/1.4.2/1.4.7 暂不适用、不冒充；参考层（听觉/多感官/光敏）科普严格标为生理·Web 参考层，不越界 | #597 docs/61 §八·6 + concept_gui 标准依据卡 |
| **智**（研判/编目） | ④ 把 docs/60/61/62/63 串成查据全集索引，统一层归属口径、穷举 Web 可落地项、汇总诚实边界，确认无遗漏 | #597 docs/64 |
| **体**（真实落点） | ① 把光敏癫痫硬约束（2.3.1）真正写入前端契约与 PR 前自检，是可验收的实体义务；② 标准依据卡科普真正落地到 concept_gui.html | #597 docs/61 §四 4.1 + concept_gui.html |
| **美**（整体全息） | 明暗双主题 + 减动效 + 非颜色编码 + 光敏防闪 + 多感官/光科普卡构成统一视觉健康与感官安全基线，圆光术光主题与多感官主题在参考层闭环 | #594 docs/61 + #597 |
| **劳**（实做实证） | 版本五处+三 taxonomy 同步自检（grep 一致）+ 双 HTML 重生 --check + 定向/全量 pytest 零回归 | #597 验证 |

## 20. 2026-10-24 第十二轮：肢体残疾/辅助设备/义肢/器官脏腑协议标准查据（#598，只读 + WCAG Operable 契约）

### 20.1 收尾目标（承接 #597，执行 docs/65 §六 列出的 3 项 opt-in 待办）
- ① 写 docs/66：把 WCAG 2.2 Operable 全套（2.1/2.2/2.3/2.4/2.5）落实为前端可验收契约，并对两 HTML 做现状差距清单。
- ② 收尾性核对：把 docs/65/66 串入 docs/64 索引，确认层归属口径一致（参考层不冒充、Web 可落地项无遗漏）。
- ③ 若后续给 concept_gui.html「标准依据」卡补「运动/肢体无障碍」科普列，须显式标注 WCAG 条目为 Web 层、ISO/GB 器械与建筑标准为参考层。

### 20.2 执行结果（3 项全部完成）
- ① **已完成**：新建 `docs/66_前端运动肢体无障碍规范（WCAG_Operable_落地）.md`——§二键盘可达（2.1.1/2.1.2/2.1.4）、§三时间控制（2.2.1/2.2.2）、§四焦点可见与导航（2.4.1/2.4.3/2.4.4/2.4.7/2.4.11/2.5.3）、§五输入模态与目标尺寸（2.5.1/2.5.2/2.5.4/2.5.7/2.5.8，含 24×24 CSS px）、§六两 HTML 现状差距清单（Bash 全文扫描实测登记）、§七 PR 前自检清单、§八诚实边界、§九验证方法。
- ② **已完成**：docs/64 索引扩为七份文档一览、层归属口径五轮统一（① Web 层新增 Operable 全套、② 参考层新增器械/建筑族）、§三 Web 可落地项全集新增 16 行 Operable 条目（含 2.5.7/2.5.8 两个 WCAG 2.2 新增 AA）、§四诚实边界新增第 11–12 条、新增 §五点五 #598 opt-in 对账。
- ③ **已完成（评估结论：暂不执行）**：本轮只读查据不改 HTML；未来执行时按 docs/66 §八第 5 条口径标注（WCAG 为 Web 层、ISO/GB 器械建筑标准为参考层）。

### 20.3 查据要点（docs/65，只读多源交叉取证）
- 辅助产品总纲：ISO 9999:2022（Ed.7，三层三级编码、ICF 全对齐、约 948 条目、删 Class 05 剩 10 大类；**明确排除植入设备**——即「外部/辅助设备」与「植入/器官脏腑器械」的分界）。
- 轮椅/移动：ISO 7176 系列（-2/-5/-8/-11/-16/-19/-28）、ISO 10542（WTORS）、ISO 10865-1/-2、ISO 16840（-4 界面压力峰值 ≤40 kPa/平均 ≤15 kPa）、ISO 11199（助行器）。
- 建筑无障碍：ISO 21542:2021（轮椅足迹 800×1300 mm、坡道 max 1:12 推荐 1:20、路径 ≥1800/1200 mm、回转 ≥1500 mm、Michelson 对比 ≥30%/60%、照度 20–500 lx 分级）、ISO 23599:2019（TWSI）、EN 17210、GB 50763-2012、GB 55019-2021（全文强制 2022-04-01 施行）、《无障碍环境建设法》（2023-09-01 施行）。
- 义肢/矫形：ISO 8549-1、ISO 10328:2016（evidence/ultimate/fatigue 三级强度）、ISO 22523、ISO 22675、ISO 15032、ISO 13405-1/-2/-3（2024 新版）、ISO 8551:2020。
- 器官脏腑/植入与器官支持：ISO 14708 七部分（-1 通用/-2 起搏/-3 神经刺激/-4 输液/-5 循环支持/-6 除颤/-7 人工耳蜗）、ISO 5840 三部分、ISO 22442-1/-2/-3、ISO 7198:2016、ISO 7197、ISO 14607、ISO 14630、IEC 60601 系列、ISO 13485:2016、ISO 14971:2019、IEC 62366-1:2015+A1:2020、IEC 62304:2015、ISO 10993 系列。
- **层归属判定**：以上全部判为物理/硬件/医学/工程参考层，不冒充；唯一 Web 落点 = WCAG 2.2 **Operable 原则**（2.1/2.2/2.3/2.4/2.5），已落为 docs/66 契约。

### 20.4 版本升版与落点
- 版本号升一版：`0000.0000.0000.0007.20261024` → `0000.0000.0000.0008.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（baigong/datong/zhuangzi 的 deno_console_version / deno_report_viewer_version）+ 双 HTML（concept_gui.html 经 gen_concept_gui.py 重生、report_viewer.html 经 gen_report_viewer.py 重生）；仅升计数段 D、日期后缀 `20261024` 不变。
- README 加 #598 块（版本更新区）+ 子系统 deno 版本引用刷新为 0008。

### 20.5 验证与交付
- `test_version.py` 动态读 `PACKAGE_VERSION`（无硬编码版本）；定向 test_concept_gui / test_version 校验通过（18 passed）。
- 双 HTML `--check` 同步通过（concept_gui data-sha256 / report_viewer source-sha256 一致）。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
- 落账：五处版本源 + 三 taxonomy + 双 HTML + docs/65 新增 + docs/66 新增 + docs/64 扩写 + README #598 块 + 本 HANDOFF §20；git 提交并推送 origin/main。

### 20.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 器械/建筑/临床标准（ISO 9999/7176/21542/10328/14708 等）一律判参考层不冒充；ISO 9999 排除植入设备即分界；两 HTML 差距如实登记「基线契约 + 差距待补」，不宣称「完全无障碍」 | #598 docs/65 §三·§五 + docs/66 §六·§八 |
| **智**（研判/编目） | 五大标准族（辅助产品/轮椅/建筑/义肢矫形/植入器官）按层归属梳理成查据清单，唯一 Web 落点收敛为 WCAG Operable 原则全套，不混淆职责边界 | #598 docs/65 |
| **体**（真实落点） | WCAG Operable 全套落为可验收前端契约（键盘可达/焦点可见/目标尺寸 ≥24×24 CSS px/拖拽替代），PR 前自检清单 14 项 | #598 docs/66 §二至 §七 |
| **美**（整体全息） | 视觉健康（docs/60/61）+ 听觉五感（docs/63）+ 运动肢体（docs/65/66）三脉合一，构成完整无障碍基线；docs/64 索引七文档闭环 | #598 docs/64 |
| **劳**（实做实证） | 只读查据多源交叉取证（8 次检索族）；两 HTML 现状 Bash 实测登记；版本五处+三 taxonomy+双 HTML 同步 --check + 定向/全量 pytest 零回归 | #598 验证 |

## 21. 2026-10-24 第十三轮：导入分析学习应用四仓库（#599，只读 + 边界分级，docs/67）

### 21.1 收尾目标（承接用户指令「继续被中断；导入分析学习应用四仓库」）
- ① 只读 WebFetch 抓取 `github.com/Gathin23/cleanyourtv`、`github.com/Gathin23`、`github.com/Ansub/tv-detox`、`github.com/leogenot/sony-a7iv-feature-research`，核实许可证 / star / 功能 / 风险关键事实（不克隆、不安装、不构建、不下载）。
- ② 写 docs/67 四仓库学习笔记：结构 / 功能 / 可学点 / 风险 + 可复用工程纪律提炼 + 边界分级（守 #591 先例「无真实 counterpart 不加概念」）+ 诚实边界。
- ③ README 加学习块 + 版本号升一版（0008→0009）+ 本 HANDOFF §21 落账 + 全量 pytest 零回归推送。

### 21.2 执行结果（3 项全部完成）
- ① **已完成**：四仓库页面 2026-10-24 只读抓取核实——`cleanyourtv`（MIT，29.6k★/3.4k fork/380+ 贡献者/840+ merged PR，260 TV 型号·77 品牌·25 语言，497 KB 纯 Java launcher）；`Gathin23` 主页（Sr. DevRel Lead @0G，India，2026-10 单月 6 仓 1,195 commits）；`tv-detox`（MIT，126 commits，star/fork 页面未呈现标 needs_verify）；`sony-a7iv-feature-research`（许可证页面未呈现标 needs_verify，最近提交 2026-09-21，A7 IV 固件 6.02）。
- ② **已完成**：新建 `docs/67_导入分析学习应用-cleanyourtv-tv-detox-sony-a7iv四仓库.md`——§一四仓概览与可复用点表、§二边界分级（纯技术可学习类仅笔记不新增概念 + 风险行为类只登记不采纳）与诚实边界（7 条 needs_verify/两说并存登记）、§三分仓学习笔记（cleanyourtv 可逆优先/最小权限/安全诚实；作者主页真实需求驱动；tv-detox 先分类后动作/保守默认演进/模拟器 CI/撤销完整性审计；sony 仓证据分级/备份先行/单属性隔离/干净分发/上游归因）、§四拓扑与验证、§五落点清单与 opt-in。
- ③ **已完成**：README 版本更新区加 #599 块 + 子系统表三行与清单表两行的 deno 版本引用刷新 0008→0009（历史块 #597/#598 表述不动）；版本号 `0000.0000.0000.0008.20261024` → `0000.0000.0000.0009.20261024` 十三处落点同步；本 HANDOFF §21。

### 21.3 四仓学习要点（docs/67，只读多源交叉取证）
- **cleanyourtv**：Wi-Fi ADB `pm disable-user` 不 root 不卸载一行还原；三步 Back up → Disable → Install launcher（顺序纪律：新 Home 装好运行后才禁原厂 Home）；工程纪律——① 可逆优先（先写恢复记录再改动、电视自身设置也能重启用）；② 最小权限（launcher 零网络权限零后台服务）；③ 工具链同构（.sh/.ps1 双生、tv.py 纯 Python ADB 客户端绕 macOS Local Network privacy、check.py 固件更新后比对重放、privacy.py 遥测候选取证）；④ 安全诚实（明示 ADB 5555 明文、adb-closed.py 验证端口关闭、Tailscale 私网建议）；⑤ 风险分级披露（setupwraith crash-loop、Private DNS 权衡、固件更新覆盖清理）。
- **tv-detox**：AI 驱动 debloat 每步改动前询问确认；`candidates.sh` 只读分 never/keep/safe/review 四档「不确定就保留」；v1.4.1 起默认保留 Google TV 主屏幕（GOOGLE_TV=1 才 opt-in）——从 crash-loop 报告学到的 fail-safe 默认并版本化；GitHub Actions + ShellCheck + 模拟器 smoke test；诚实声明 undo.sh 不撤销 TCL 远程服务改动；卡 logo 恢复手册（adb wait-for-device + pm enable 逐个恢复）。
- **sony-a7iv-feature-research**：证据分级状态表（Verified / display verified / gate unresolved / product-excluded / untested）——不把「实现在固件中」转述为「可用」；实验前保存 checksum 有效备份且原备份与哈希留仓外；一次只改一个 persisted backup property + 冷启动验证；仓内零固件/零解密二进制/零相机备份/零序列号/零密钥的干净分发；显式上游归因（Sony-PMCA-RE / fwtool.py a7iv 分支 / ILCE-7M4-RE）；1,064 更新包文件独立哈希匹配。
- **边界判定**：四仓均无真实 counterpart（本仓无 Android TV debloat 子系统 / 无固件研究面），按 #591 先例（docs/59）一律只沉淀学习笔记、不新增概念；ADB 明文端口与恢复出厂风险只登记不采纳；相机固件纪律只学习不复现、不作任何厂商能力宣称。

### 21.4 版本升版与落点
- 版本号升一版：`0000.0000.0000.0008.20261024` → `0000.0000.0000.0009.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（baigong/datong/zhuangzi 的 deno_console_version / deno_report_viewer_version）+ 双 HTML（concept_gui.html 经 gen_concept_gui.py 重生、report_viewer.html 经 gen_report_viewer.py 重生）；仅升计数段 D、日期后缀 `20261024` 不变。
- README 加 #599 块（版本更新区）+ 子系统 deno 版本引用刷新为 0009；docs/67 新增；本 HANDOFF §21。

### 21.5 验证与交付
- `test_version.py` 动态读 `PACKAGE_VERSION`（无硬编码版本）；定向 test_concept_gui / test_version 校验通过。
- 双 HTML `--check` 同步通过（concept_gui data-sha256=4f2970598979... / report_viewer source-sha256=104c4da9c13e...）。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
- 落账：五处版本源 + 三 taxonomy + 双 HTML + docs/67 新增 + README #599 块 + 本 HANDOFF §21；git 提交并推送 origin/main。

### 21.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 四仓无 counterpart 一律不新增概念（守 docs/59 #591 纪律）；star/fork 未呈现处标 needs_verify 不补数；RAM 两说并存如实登记；ADB 明文端口与恢复出厂风险只登记不采纳；相机固件「零固件零密钥」纪律只学习不复现 | #599 docs/67 §一·§二 |
| **智**（研判/编目） | 四仓按「可复用工程纪律」逐条提炼（可逆优先/最小权限/先分类后动作/保守默认演进/证据分级/备份先行/单属性隔离/干净分发/上游归因），与本仓既有纪律（docs/57 工具链、needs_verify、docs/59 边界分级）同构对照 | #599 docs/67 §三 |
| **体**（真实落点） | 版本号十三处落点同步 + 双 HTML 按生成器纪律重生 --check；README #599 块与 HANDOFF §21 落账可验收 | #599 验证 |
| **美**（整体全息） | 四仓分属「TV debloat / 作者生态 / AI 驱动清理 / 固件研究」四个面向，与 docs/59 四仓库分析（激活绕过/边缘代理/Rust GUI/LLM 插件）共同构成外部仓库学习谱系，边界分级口径全仓统一 | #599 docs/67 + docs/59 |
| **劳**（实做实证） | 四页面只读抓取核实（不克隆不安装）；sed 升版后 grep 验证 14 处到位零残留；双 HTML 重生 --check；定向 + 全量 pytest 零回归 | #599 验证 |

## 22. 2026-10-24 第十四轮：用户原话纠正「德育体知（智）美劳」写法改回（#600）

### 22.1 收尾目标（承接用户指令「德育体知（智）美劳，我读的民办学校都这样，必须改回来」）
- 用户指出：HANDOFF §12 起的「德智体美劳全面发展（先天道体）」维度映射框架，是本仓对用户原始命题的**转写**；用户原话为「**德育体知（智）美劳**全面发展，做素质新人（先天道体）」（HANDOFF §12 引用块所录），该写法源自用户所读民办学校，**必须改回原话**。
- 执行：全仓「德智体美劳全面发展（先天道体）」→「德育体知（智）美劳全面发展（先天道体）」；用户命题引用块（§12，原话）保持不动。

### 22.2 执行结果（12 处全部改回，改后全仓「德智体美劳」零残留）
- **HANDOFF-arm-deb.md 11 处**：§12 转述句（原 line 272，「即把 #586 末尾给出的三个方向全选推进，并以『德智体美劳全面发展（先天道体）』框架映射本轮交付维度」）+ 十个映射表标题（§12.5 / §13.5 / §14.5 / §15.5 / §16.4 / §17.5 / §18.5 / §19.5 / §20.6 / §21.6）。
- **system-optimizer README.md 1 处**：版本更新区 #590 历史块中引用「HANDOFF §12 记录本轮落账与『德智体美劳全面发展（先天道体）』维度映射」——同步改回原话写法，保持文档间引用一致（该处为映射表名称引用，非版本号数字，不涉及历史数字回溯）。
- **保持不动**：§12 用户命题引用块（原话「德育体知（智）美劳全面发展，做素质新人（先天道体）」本就未转写）；十个映射表**表内五行维度标签**（**德**/**智**/**体**/**美**/**劳** 各行）为维度行标非顺序声明，不动。

### 22.3 版本升版与落点
- 版本号升一版：`0000.0000.0000.0009.20261024` → `0000.0000.0000.0010.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（baigong/datong/zhuangzi 的 deno_console_version / deno_report_viewer_version）+ 双 HTML（concept_gui.html 经 gen_concept_gui.py 重生、report_viewer.html 经 gen_report_viewer.py 重生）；仅升计数段 D、日期后缀 `20261024` 不变。
- README 加 #600 块（版本更新区）+ 当前口径 deno 版本引用刷新为 0010（历史块 #597/#598/#599 表述不动）；本 HANDOFF §22。

### 22.4 验证与交付
- sed 替换后 grep 验证：全仓「德智体美劳」0 处、「德育体知（智）美劳全面发展（先天道体）」12 处（HANDOFF 11 + README 1）；版本 0010 在 8 源文件 14 处到位、0009 源文件零残留。
- `test_version.py` 动态读 `PACKAGE_VERSION`；定向 test_concept_gui / test_version 校验通过。
- 双 HTML `--check` 同步通过（concept_gui data-sha256=0cfc232c63f9... / report_viewer source-sha256=f921a50f1c62...）。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
- 落账：HANDOFF 12 处文字 + README 1 处文字 + README #600 块 + 五处版本源 + 三 taxonomy + 双 HTML + 本 HANDOFF §22；git 提交并推送 origin/main。

### 22.5 用户背景登记（memory 级事实）
- 用户所读学校为民办学校，其「全面发展」教育框架的写法/顺序为「**德育体知（智）美劳**」——今后本仓所有「全面发展（先天道体）」维度映射一律沿用用户原话写法，不再转写为「德智体美劳」。

## 23. 2026-10-24 第十五轮：「育」义补全——北京师范大学 / 教书育人 / 言传身教 / 诗书礼易（#601）

### 23.1 收尾目标（承接用户指示「都改动，德育体知（智）美劳，的育当时的具体是北京师范大学，也是教书育人，更是言传身教，还是诗书礼易，代表是国家民族，不是社会组织企业」）
- 用户对「德育体知（智）美劳」中的**「育」**给出完整释义，并要求全仓框架表述据此补全（「都改动」）。
- 执行：§12 框架释义块补全（六字逐一释义，「育」为教育之体、全套框架的承载）；十个映射表标题下统一补「育」义注（compact 版）；本 §23 落账；README #601 块；版本升一版（0010→0011）；memory 更新。

### 23.2 「育」义（用户原话六要义，逐字落账不增删）
- **具体所指：北京师范大学**——中国师范教育最高学府（校训「学为人师，行为世范」），即**教书育人**的制度化载体。
- **教学法：言传身教**——以言行示范为教，不只以知识传授为教。
- **内容：诗书礼易**——《诗经》《尚书》《礼记》《周易》经典传统（诗言志、书载道、礼立范、易明变）。
- **立场：国家民族**——「师者，所以传道受业解惑也」（韩愈《师说》），育是道统与民族文化之传承；**不是社会组织、不是企业**——绝不以商业组织逻辑办教育、绝不以营利 / KPI 逻辑办育人。

### 23.3 执行结果
- §12 框架释义块补全：六字逐一释义（德/育/体/知（智）/美/劳），「育」为教育之体、全套框架的承载；「育」义全量释义（北京师范大学、教书育人、言传身教、诗书礼易、国家民族、非社会组织企业六要义）。
- 十个映射表（§12.5 / §13.5 / §14.5 / §15.5 / §16.4 / §17.5 / §18.5 / §19.5 / §20.6 / §21.6）标题下统一补 compact「育」义注（指向 §12 全量释义）。
- README 加 #601 块 + 当前口径版本引用刷新为 0011；本 §23；memory（user-school-deyutizhimeilao.md）补「育」义。

### 23.4 版本升版与落点
- 版本号升一版：`0000.0000.0000.0010.20261024` → `0000.0000.0000.0011.20261024`，五处同步（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON（baigong/datong/zhuangzi 的 deno_console_version / deno_report_viewer_version）+ 双 HTML（concept_gui.html 经 gen_concept_gui.py 重生、report_viewer.html 经 gen_report_viewer.py 重生）；仅升计数段 D、日期后缀 `20261024` 不变。
- README #601 块（版本更新区）；HANDOFF §23（本节）。

### 23.5 验证与交付
- 脚本插入 10 处「育」义注 + grep 验证（§12 释义块 1 处 + 十表注 10 处 = 11 处「教育之体，全套框架的承载」）。
- `test_version.py` 动态读 `PACKAGE_VERSION`；定向 test_concept_gui / test_version 校验通过。
- 双 HTML `--check` 同步通过。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，不影响九概念系统拓扑与桥接。
- 落账：HANDOFF §12 释义块 + 十表注 + §23 + README #601 块 + 五处版本源 + 三 taxonomy + 双 HTML + memory 更新；git 提交并推送 origin/main。

### 23.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 用户「育」义六要义逐字落账（北京师范大学 / 教书育人 / 言传身教 / 诗书礼易 / 国家民族 / 非社会组织企业），不增删不改写；「非社会组织、非企业」立场明载，杜绝商业逻辑办教育的误读 | #601 §23.2 |
| **智**（研判/编目） | 「育」归位为六字框架中的教育之体与承载；§12 释义块 + 十表注 + memory 三处口径一致 | #601 §12 + §23.3 |
| **体**（真实落点） | §12 释义块、十表 compact 注、README #601 块、memory 更新、版本 0011 十三处落点均可验收 | #601 验证 |
| **美**（整体全息） | 「诗书礼易」经典传统与「言传身教」师范传统入册——框架从工程交付映射升维为国家民族育人框架，「做素质新人（先天道体）」落地 | #601 §23.2 |
| **劳**（实做实证） | 脚本化插入十表注 + grep 验证 11 处；版本 0010→0011 sed 后 14 处到位；双 HTML 重生 --check；定向 + 全量 pytest 零回归 | #601 验证 |

## 24. 2026-10-24 第十六轮：第五仓库只读导入分析——aurora-silicon/mesa（#602）

### 24.1 收尾目标（承接用户指示「看看有什么推进的继续；导入分析学习应用 https://github.com/aurora-silicon/mesa 、 继续」）
- 检视仓库无遗留 pending 任务后（#597–#601 全部 completed 并推送），对第五个外部 GitHub 仓库 `aurora-silicon/mesa` 执行只读导入分析。
- 执行：docs/68 学习笔记（守 #591/docs/59 边界分级）；README #602 块 + 当前口径版本引用刷新；本 §24 落账；版本升一版（0011→0012）。

### 24.2 仓库事实（2026-10-24 只读 WebFetch 核实）
- **性质**：freedesktop Mesa 3D 图形库的 **stock mirror**（描述原文「Mesa 3D graphics library (stock mirror of https://gitlab.freedesktop.org/mesa/mesa)」），默认分支 `aurora-wip`，**231,027 commits**；star / fork 页面未呈现（此前组织页抓取见 2★/4 forks 与 2★/10 forks 两个不一致值，均 `needs_verify` 不取单一值）；LICENSE 未在页面呈现（上游 Mesa 为 MIT，本 mirror 许可 `needs_verify`，不据上游推定）。
- **技术栈**：C + Meson + Ninja + Vulkan + 多 GPU 后端（radv/AMD、Intel、hk/Apple AGX、amd/virtio、ethosu/ARM、gfxstream）；README.rst 构建原文 `meson setup build` / `ninja -C build/` / `sudo ninja -C build/ install`。
- **提交样本**（页面快照）：PR #64（2026-10-24，RyanTheTide）；`hk: make G17P sparse image capabilities match the slice layout`（2026-10-23，署名 Ryan Murray <ryan@aurorasilicon.org>）；`hk: gate the bounded AS-build hint to G17P and kernel capability`（2026-10-22）；`gfya`（2026-10-20，`Co-Authored-By: Claude Opus 5.5`，触及 .github / AGENTS.md / CLAUDE.md / GEMINI.md）。`hk` = Apple AGX/Honeykrisp GPU 驱动后端（G17P 芯片）。
- **组织背景**：aurora-silicon 自述「New light for Apple Silicon」——为 Apple Silicon 交付完整 Linux 体验（内核/图形驱动/工具）并正将 Windows 移植到 Apple Silicon；43 个公开仓库（linux 47★、aurora-installer、aura EL2 monitor、nixos-aurora、m1n1 364 forks、fedora-aurora、asahi-audio、alsa-ucm-conf-asahi 等，计数以页面当时呈现为准 `needs_verify`）。

### 24.3 边界分级（守 #591/docs/59 先例）
- **纯技术可学习类（仅笔记，不新增概念）**：本仓无图形栈 / GPU 驱动 counterpart（native 只读层面向系统优化，不涉及用户态图形驱动、GPU 固件交互或 Vulkan 后端实现），只沉淀为学习笔记，不新增任何概念系统概念。
- **底层系统类（只作架构学习，不落地代码）**：Mesa 的 C 语言 GPU 驱动后端、内核态交互、G17P 芯片使能——不复制、不构建、不安装、不移植，仅学习「驱动与硬件平台解耦」的架构分层思想。
- **风险行为类（只作风险登记，不落地）**：`aurora-wip` 为 Apple Silicon 移植实验性 WIP 分支（bounded AS-build hint 等未稳定改动），不跟踪、不合并、不采纳；上游 README 明言其他仓库代码「not supported」，引用事实一律以上游 gitlab 为准。

### 24.4 可复用工程纪律提炼（仅学习，不落地代码）
1. **上游归因署名链**：镜像提交带 `Part-of: <gitlab.freedesktop.org/mesa/mesa/-/merge_requests/XXXX>` 上游 MR 归因标签——衍生仓库不吞没上游贡献；同构本仓 research/ 镜像纪律、docs/67 上游归因清单、HANDOFF 来源可溯要求。
2. **权威源声明**：README 首段声明上游地址并声明其他仓库「not supported」——先声明权威源再谈衍生；同构本仓「先划边界再讲能力」与 needs_verify 挂牌纪律。
3. **stock mirror + wip 分支工作流**：以 mirror 跟踪上游、以 `aurora-wip` 承载自有衍生分支，分支名自含「wip」性质——衍生与实验分层命名，不自立门户宣称原创。
4. **LLM 辅助署名透明**：`Assisted-by: LLM` / `Co-Authored-By: Claude Opus 5.5`——AI 辅助产出在版本历史中署名可见；同构本仓 HANDOFF AI 辅助开发如实落账纪律。
5. **可复现构建即文档**：Meson/Ninja 三段标准命令 + 上游 install/meson 文档索引；同构本仓 tools/ 构建脚本 `--check` 防漂移、双 HTML 经生成器重生不手改。
6. **平台使能分层**：bootloader（m1n1）→ 内核（linux）→ 驱动 → 发行版集成（nixos-aurora / fedora-aurora）分层交付；同构本仓 native 只读层 / tasks 任务层 / data 知识层 / CLI-GUI-webapi-deno 四入口分层。

### 24.5 执行结果与落点
- docs/68《导入分析学习应用：aurora-silicon/mesa》（§一 概览与可复用点 / §二 边界分级与诚实边界 / §三 分仓笔记 / §四 拓扑与验证 / §五 落点清单与 opt-in）。
- README 版本更新区加 #602 块 + 当前口径版本引用刷新为 0012（行 3/4/5/843/844 五处）；#601 及更早历史块原数字不动。
- HANDOFF 本 §24（第十六轮）；版本号 `0000.0000.0000.0011.20261024` → `0000.0000.0000.0012.20261024`，十四处落点（version.py / pyproject.toml / main.go / console.ts×2 / report_viewer.ts×3 / 三 taxonomy JSON 各 2 处）+ 双 HTML（concept_gui.html / report_viewer.html 经生成器重生）；仅升计数段 D、日期后缀 `20261024` 不变。

### 24.6 验证与交付
- 定向 `test_concept_gui` / `test_version` 校验通过；双 HTML `--check` 同步通过（data-sha256 / source-sha256）。
- 全量 pytest 零回归（基线 1683 passed / 5 skipped）；未改任何概念数据语义，九概念系统拓扑与桥接不变（`build --check` 不受影响）。
- git 提交并推送 origin/main。

### 24.7 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | stock mirror 非原创、star/fork 两值不一、LICENSE 未呈现均按 needs_verify 登记，不据上游 MIT 许可推定本 mirror 许可；「not supported」上游声明如实转述 | #602 §24.2 / docs/68 §二 |
| **智**（研判/编目） | 按「是否可实做落地」分三档（纯技术可学习 / 底层系统 / 风险行为），上游归因署名链、权威源声明、LLM 署名透明等六条纪律逐条同构本仓既有纪律 | #602 §24.3 / §24.4 |
| **体**（真实落点） | docs/68、README #602 块、版本 0012 十四处落点、双 HTML 重生、HANDOFF §24 均可验收 | #602 §24.5 |
| **美**（整体全息） | 「驱动与硬件平台解耦」架构分层思想与本仓 native/tasks/data/四入口分层同构——外部底层系统知识经纪律提炼汇入全仓框架 | #602 §24.4.6 |
| **劳**（实做实证） | 14 处 sed 升版后 0011 零残留；双 HTML 生成器重生 + `--check` 双通过；定向 + 全量 pytest 零回归 | #602 §24.6 |

## 25. 2026-10-24 第十七轮：toolchain 子系统完善补全优化（#603，宿主实装入册 + 探针全覆盖 + 概念补全）

### 25.1 收尾目标（承接用户指示「各工具链完善补全优化」）
- 对 toolchain 子系统（`data/toolchain_catalog.json` + `native/toolchain.py` + `tasks/toolchain.py` + docs/57）与 comp 概念系统工具链域做补全：宿主实装未编目工具链入册、探针层扩展、上游新鲜度联网核实、概念补全、连带计数断言与文档刷新、升版推送。

### 25.2 catalog 补全事实（#636/#637）
- **类别 7→10**：新增 `vcs-network`（版本控制与网络）/ `container`（容器）/ `media`（媒体）；editor-browser note 扩写为「Firefox / Google Chrome / vim 家族 / 终端复用器」。
- **宿主工具链 23→42 条（+19，按「套件合条」粒度，对齐既有 binutils-make-cmake、dpkg-lintian 先例）**：vcs-network 7 条（git 2.43.0 / http-clients curl 8.5.0+wget 1.21.4 / rsync 3.2.7 / openssl 3.0.13 / ssh OpenSSH_9.6p1 / compression-suite tar·gzip·xz·zstd·unzip）；container 1 条（docker 27.5.1）；media 1 条（ffmpeg git 快照）；editor-browser 3 条（chrome 144.0.7559.132 / editor-suite vim 9.1+nvim 0.9.5+emacs 29.3 / terminal-mux tmux 3.4+screen 4.09.01）；quality 4 条（binary-inspect file·xxd·patchelf / autotools-suite autoconf·automake·flex·bison·pkg-config / debug-trace gdb·strace·ltrace·valgrind / lint-format clang-format·clang-tidy·shellcheck）；native-build 4 条（build-extra ninja 1.11.1+meson 1.3.2+scons 4.5.2 / text-data-utils jq 1.7+mawk+bc / perl 5.38.2 / tcl 8.6）。
- **仓库工具软件 11→14 条（+3，均有真实 counterpart）**：`docker-support`（Dockerfile+compose 两文件 find 实证）、`ci-workflows`、`repo-guard`（scripts/check_repo_guard.py + tests/test_repo_guard.py 真实存在，#211/#168）；并修 sysweeper/syspkg 陈旧版本串 0004→0013。
- **上游新鲜度 16 项逐项联网核实**（needs_action 11→27，fresh 4）：安全相关优先——OpenSSL 3.0.13（3.0 系列 2026-09-07 EOL，上游 LTS 3.5.9 支持至 2030-04-08，主线 4.0 安全修复至 2027-05-14）；curl 8.5.0（上游 8.23.0 2026-10-14，8.22.0 一轮修 9 项 10 CVE）；Chrome 144.0.7559.132（上游 stable 152 2026-09-01，落后 8 个大版本含多轮 High CVE）；Docker 27.5.1（上游 29.9.1 2026-10-14）；git 2.43.0（上游 2.55.0 2026-06-29）；Perl 5.38.2（5.38 安全补丁 2026-07-02 止，上游 5.44.0）；jq 1.7（上游 1.8.2 修 17 CVE）；次轮 vim 9.1→9.2（2026-02-14）、nvim 0.9.5→0.12、emacs 29.3→31.1（2026-08-24）、meson 1.3.2→1.12.1（2026-09-22）、ninja 1.11.1→1.13.2（2025-11-20）、scons 4.5.2→4.11.1（2026-08-26）、tmux 3.4→3.8、tcl 8.6→9.1.0（2026-09-29）、ffmpeg 快照→stable 9.0.2（2026-09-18）。

### 25.3 诚实边界（本轮守住的三处）
- **全仓 workflow 实数仅 2 个**（根 `.github/workflows/build.yml` 两 job：build-python/build-go + `Windows/.github/workflows/build.yml`），**无** shellcheck/hadolint/actionlint 接入——ci-workflows 条与 lint-format 条 ci_note 均如实登记「宿主可用、CI 未接入」，lint-gate 概念 engineering 同口径标「未落地」。
- **osxcross 探针如实缺席**：`o64-clang` 不在 PATH（本机实录 ✗），与 catalog「未安装」口径一致；探针小结「在位 41 / 缺席 1 / 覆盖 42/42」。
- **tmux 上游发布日期两源不一**（2026-10-08 vs 2026-09-09），catalog 处置栏如实标「日期待核」，不取单一值。

### 25.4 探针层与概念系统优化（#638/#639）
- **`native/toolchain.py`**：HOST_PROBES 19→39 项 + 3 项绝对路径回退（NDK/OHOS/libiconv），对 catalog 宿主条目 **42/42 全覆盖**；版本旗标特例化（openssl/go 用 `version`、ssh/tmux 用 `-V`、perl 用 `-v`、ffmpeg 用 `-version`、tclsh 走 stdin 读 `$tcl_version`，`_ver_line` 跳过空行修 perl -v 首行空行问题）；小结行加在位/缺席/覆盖率统计；源码零写路径红线保持（测试断言通过）。
- **comp 概念系统**（83→86、桥接 96→98）：build 域新增 `scons`（宿主 4.5.2 vs 上游 4.11.1 记 needs_action）、`container-toolchain`（Dockerfile 多阶段 + compose 最小权限，桥 datong `yiti-liangmian` 一体两面）、`lint-gate`（桥 daoxue `zhi-bu-zhi`，如实登记 CI 未接入）；连带修订 `artifact-container` 陈旧「未落地」记述（本仓实有 Dockerfile/compose，真落地）与 `odometer-versioning` 陈旧版本串；taxonomy _meta 0068→0069。

### 25.5 执行结果与落点
- docs/57 全文计数刷新：宿主 42 条（新增 §1.5 质量套件 / §1.8 vcs-network / §1.9 容器 / §1.10 媒体 + §1.2/§1.4 扩行）、仓库工具 14 条（新增 §2.12–2.14）、新鲜度两栏 27+4 全量列表、回归测试 14→16 项。
- tasks/toolchain.py 四条 desc 刷新（10 类别 42 条 / 全覆盖实采与旗标口径 / needs_action 27 条安全优先）；subsystems toolchain 版本 0001→0002；test_toolchain 断言同步（categories 7→10、subsystem 0002、+22 must ids、全覆盖断言、+2 回归守卫测试）。
- README 版本更新区加 #603 块 + comp 表格行计数刷新（构建系统 9→12、83→86、96→98、daoxue 13→14、datong 7→8）；test_comp 四处断言与 test_concepts_center 一处断言同步。
- 版本号 `0000.0000.0000.0012.20261024` → `0000.0000.0000.0013.20261024`：五处活版本（version.py / pyproject.toml / main.go / console.ts / report_viewer.ts，含头注释与 DEMO schema 串）+ 三 taxonomy JSON 各 2 处 deno 版本引用 + toolchain_catalog 3 处（sysweeper 版本 + 随 sysweeper ×2）+ build_comp.py odometer detail 1 处，共 18 处替换；0012 零残留（docs/68 历史记录与 README 历史块不动）；双 HTML 经生成器重生。

### 25.6 验证与交付
- 定向测试全过：test_toolchain 16 项、test_comp 17 项、test_concept_gui、test_concepts_center、test_version。
- 全量 pytest 零回归（1685 passed / 5 skipped，基线 1683 +2 新守卫测试）。
- `build_comp.py --check` 无漂移（86 概念 / 98 桥接无悬空）；双 HTML `--check` 同步（concept_gui data-sha256 / report_viewer source-sha256）。
- git 提交并推送 origin/main。

### 25.7 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | workflow 实数 2 个即记 2 个（推翻多版本前「6 个工作流」的旧述），lint-gate 如实标「宿主可用、CI 未接入」；tmux 上游日期两源不一挂 needs_verify 不取单一值；osxcross 探针缺席如实记 ✗ | #603 §25.3 / catalog ci_note |
| **智**（研判/编目） | 16 项新增工具链逐项联网核实取上游版本/发布日期/CVE 证据，按「安全相关优先 + 次轮编辑器构建」两档组织；套件合条粒度对齐既有编目先例 | #603 §25.2 / catalog needs_action 27 条 |
| **体**（真实落点） | catalog 42/14/10、探针 42/42 全覆盖、docs/57 全量刷新、tasks/subsystems/测试断言逐处同步，均可 find/--check 验收 | #603 §25.4 / §25.5 |
| **美**（整体全息） | 数据层（catalog）—只读层（native 探针）—任务层（tasks）—概念层（comp 三概念）—文档层（docs/57）五层同源一致，计数全线对齐无漂移 | #603 五层落点 |
| **劳**（实做实证） | 18 处升版替换后 0012 零残留；双 HTML 生成器重生 + `--check` 双通过；全量 pytest 1685 passed 零回归 | #603 §25.6 |

## 26. 2026-10-24 第十八轮：导入分析学习应用——WorkBuddy 瘦身加速（workbuddy-slim）+ OpenSpeedy（#604，双资源只读 + 边界分级）

### 26.1 收尾目标（承接用户指示「继续被中断；导入分析学习应用【WorkBuddy干活变慢还费token，一招教你瘦身加速】点击链接打开👉 https://m.toutiao.com/is/iLkStvDzpxY/ …… 、openspeedy；继续」）
- 对两个外部资源做**只读导入分析**：① 今日头条文章《WorkBuddy干活变慢还费token，一招教你瘦身加速》（全文抓取）；② `github.com/game1024/OpenSpeedy` 仓库页（只读 WebFetch）。均不克隆、不安装、不构建、不下载、不复制代码；按 #591/docs/59 先例做边界分级，沉淀学习笔记、升版推送。

### 26.2 头条文章事实（workbuddy-slim，#641）
- **文章与作者**：《WorkBuddy干活变慢还费token，一招教你瘦身加速》，作者**马佳彬**（公众号「马佳彬」，经「人人都是产品经理」账号发布，2026-10-24 抓取）。
- **根因论断**：Skill / MCP / 记忆 / Agent 规则滚雪球式膨胀，每轮任务全量塞入上下文；长会话（几十甚至上百轮）即使有自动压缩上下文仍爆炸；模型积分倍率差异大（同任务 DeepSeek-V4.1-Flash 约十几积分 vs MiniMax-M3 暴涨十倍——文章单方陈述，needs_verify）；缓存命中率取决于前缀稳定性与任务类型。
- **解法形态**：开源 Skill **`workbuddy-slim`**（github.com/majiabin2020/workbuddy-slim/），**只诊断不删除**；诊断四维度（规则膨胀 / 记忆超限 / 技能与连接器堆积 / 会话卫生）→ 红黄绿体检报告（红=严重、黄=中等、绿=健康）→ 用户逐项确认后**非破坏性执行**；安装提示词「安装这个skill：github.com/majiabin2020/workbuddy-slim/」，触发语「给我的WorkBuddy做个体检」；样例报告 56 个技能 40 个踩红线；官方建议启用工具不超过 80 个；MEMORY.md 内容过多可蒸馏压缩（均为文章口径，needs_verify）。

### 26.3 OpenSpeedy 事实（#642）
- **仓库**：`github.com/game1024/OpenSpeedy`（初抓 `game102` 404，WebSearch 定位真实用户名 `game1024`）；开源游戏变速器「The Best Open-Source Game Speed Controller」；**GPL v3**；版本 **3.3.17**（2026-10-18 bump，初版 v3.1.0 于 2026-06-21，76 commits）；平台 Windows 10+（x86/x64）。
- **技术核心**：**Ring-3 用户态 Hook、无内核侵入**；基于 **MinHook** Hook 十个 Windows 时间 API——Sleep/SetTimer（user32.dll）、timeGetTime（winmm.dll）、GetTickCount/GetTickCount64/QueryPerformanceCounter/GetSystemTimeAsFileTime/GetSystemTimePreciseAsFileTime/SetWaitableTimer/SetWaitableTimerEx（kernel32.dll）。
- **技术栈**：C/C++（speedpatch DLL）+ Rust（Tauri 后端）+ TypeScript/JavaScript（Vite 前端）；UI 用 MUI + Ant Design splitter；构建 `npm run tauri dev`，依赖 Node.js 18+/CMake/VS C++ 工作负载。
- **分发与工程亮点**：安装三途径（winget `--id Game1024.OpenSpeedy --exact --source winget` / Releases 手装 / Steam app 5010920）；防御式失败处理（提交 `fix: remove VC++ redist dependency and stop MH hook failures crashing…`，2026-09-24——Hook 失败不崩目标进程，据提交标题陈述 needs_verify）；winget 同名包匹配冲突修复（`docs: 修正 winget 同名包匹配冲突 (#300)`，2026-10-21）；README 五条风险警示前置（仅教育研究用途 / 反作弊封号风险 / 超速物理引擎崩溃 / 无数字签名杀软误报）。

### 26.4 诚实边界（本轮守界）
- **counterpart 核查**：全仓 grep（`minhook|Ring-?3|api[- ]?hook|detours|speedpatch|GetTickCount|QueryPerformanceCounter`）仅三处命中且均为 **API 可用性版本编目**（`tools/collect_windows_api_baseline.py:39` 的 `("kernel32","GetTickCount64","6.0")`、`docs/windows-api-version-matrix.md:61` 的 Vista(6.0) 行、`research/rfc/rfc-index.xml`），**无任何 hook / 注入 / 变速实装**——按 #591/docs/59 纪律**不新增概念**，九概念系统拓扑与桥接不变。
- **needs_verify 挂牌**：文章系第三方媒体转述、workbuddy-slim 仓库本体未直接抓取（56 技能 40 红线 / ≤80 工具 / 积分倍率数值均未独立复核）；OpenSpeedy 页面未呈现 star / fork 计数；Hook 失败不崩目标进程仅据提交标题。
- **许可边界**：OpenSpeedy 为 GPL v3，**不复制、不链接、不移植**其代码进本仓；游戏变速能力**不提供、不引导、不实现**，仅登记其风险披露纪律。

### 26.5 执行结果与落点
- 新增 `system-optimizer/docs/69_导入分析学习应用-workbuddy瘦身加速与openspeedy.md`（双资源概览表 + 边界分级三档 + 分主题学习笔记 + 拓扑与验证 + 落点清单）。
- README 版本更新区加 **#604 块**（0014 头：文章导入分析 + OpenSpeedy 只读分析两条合一 + bump bullet）；**修复上一轮遗留缺陷**——#603 插入 0013 块时吞并 0012 块头（多出重复的 0011→0012 bump bullet 且 aurora bullet 掉入 0013 块），本轮在 0013 块内补回 `- **0000.0000.0000.0012.20261024（2026-10-24）**` 块头，与 HEAD~1 实证结构对齐；当前口径版本引用五处刷新（行 3/4/5 + 行 853/854 第二副本）。
- 版本号 `0000.0000.0000.0013.20261024` → `0000.0000.0000.0014.20261024`：**二十处替换**——五处源文件（version.py / pyproject.toml / main.go / console.ts 头注释+const / report_viewer.ts 头注释+const+schema 串）+ 三 taxonomy JSON 各 2 处 deno 版本引用 + comp_taxonomy.json odometer detail 1 处 + build_comp.py 源串 1 处 + toolchain_catalog.json 3 处（sysweeper 版本 + 随 sysweeper ×2）+ tests/test_toolchain.py docstring 版本戳 1 处；0013 零残留（README 历史块与 docs/69 升版记述除外）；四个构建脚本重跑（comp / baigong / datong / zhuangzi）+ 双 HTML 经生成器重生。

### 26.6 验证与交付
- 四个构建脚本 `--check` 全过：comp（86 概念 / 98 桥接无悬空）、baigong（27 / 50）、datong（63 / 51）、zhuangzi（20 / 18）。
- 双 HTML `--check` 同步（concept_gui data-sha256 / report_viewer source-sha256）。
- 定向测试 + 全量 pytest 零回归（基线 1685 passed / 5 skipped）。
- git 提交并推送 origin/main。

### 26.7 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 文章转述数字与 star 计数一律挂 needs_verify 不取单一值；GPL v3 代码不复制不移植；「只诊断不删除」「逐项确认后非破坏性执行」的处置-授权分离纪律如实转述 | #604 §26.4 / docs/69 §二 |
| **智**（研判/编目） | 双资源按「可实做落地」分三档（纯技术可学习 / 底层系统 / 风险行为）；counterpart grep 实证无 hook/变速实装后决定不加概念；八条可复用纪律逐条同构本仓既有实践（audit --strict / opt-in 确认 / --check 防漂移 / API 矩阵编目 / 探针降级 / 先划边界） | #604 §26.4 / docs/69 §三 |
| **体**（真实落点） | docs/69、README #604 块、0012 块头缺陷修复、当前口径五处刷新、版本 0014 二十处落点、双 HTML 重生、HANDOFF §26 均可验收 | #604 §26.5 |
| **美**（整体全息） | 「上下文预算体检 ↔ 本仓质量门禁」「Hook 面完整性矩阵 ↔ API 版本编目」「混合工具链 ↔ 四入口分层」三组同构——外部工程知识经纪律提炼汇入全仓框架，而非孤立知识点 | #604 docs/69 §3.1/§3.2 |
| **劳**（实做实证） | 20 处升版替换后 0013 零残留；四构建脚本 + 双 HTML 生成器重生 + `--check` 全过；定向 + 全量 pytest 零回归 | #604 §26.6 |

## 27. 2026-10-25 第十九轮：可持续方向收尾①——前端运动/肢体无障碍差距补齐（#605，docs/66 §六清单全部销项）

### 27.1 收尾目标（承接用户指示「所有可持续继续方向都得继续推进到收尾」）
- 盘点仓内挂起项后判定两个有真实 counterpart 的可持续方向：**方向 A** = docs/66 §六 WCAG 2.2 Operable 差距清单补齐（生成器在手、§九 验收方法明确）；**方向 B** = lint-gate 落地（宿主有 shellcheck、本仓有自有脚本与 workflow，comp 概念系统登记「宿主可用但 CI 未接入」）。docs/69/68 的 opt-in 下一步缺 counterpart，继续挂账不推进。本轮先收尾方向 A。

### 27.2 补齐事实（#648/#649）
- **concept_gui.html（生成器 tools/gen_concept_gui.py）**：全局 `:focus-visible{outline:2px solid var(--acc);outline-offset:2px}` 兜底 + `g[tabindex]:focus-visible` + `.mx td.cell:focus-visible`（2.4.7）；`.btn` 显式 `min-width:24px;min-height:24px`（2.5.8，矩阵格既有 36×26 px）；SVG 中心圆 + 9 系统节点经 el() 置 `tabindex="0"`/`role:"button"`/`aria-label` 并挂 Enter/Space 键控（2.1.1）；矩阵有数格 `tabindex='0' role='button'` + aria-label + 键控，0 值格保持纯展示；`<header class="top">` + `<main class="main" id="main">` landmark + 屏外 skip link（2.4.1）。
- **report_viewer.html（生成器 src/deno/report_viewer.ts）**：全局 `:focus-visible`、`.btn` 24px、`<header>` + `<main id="main">` + skip link；指针取消经 `click` 事件模型天然满足（2.5.2，如实登记不虚设处理器）。

### 27.3 既有 bug 发现与修复（诚实登记）
- **report_viewer.ts page() 反引号模板中 base64url 替换行写 `\/`/`\+`**，按 JS 模板字符串语义产出 `/`/`+`——生成 HTML 中为 `.replace(/+/g,"-").replace(///g,"_")`：`/+/g` 无效正则、`///g` 触发行注释，**整块内联 script 语法错误，页面全部 JS 功能瘫痪**（git log 实证该缺陷自 report_viewer 诞生起存在，历轮字节模式测试未覆盖 JS 可执行性）。
- 修复：源码改双重转义 `\\/`/`\\+`，重生后 `node --check` 双页通过；并把 JS 语法校验固化为门禁（`test_inline_js_syntax_valid`，node 缺席跳过）。

### 27.4 执行结果与落点
- 新增 `system-optimizer/tests/test_a11y_operable.py`（12 项）：契约模式静态断言（focus-visible / 24px / tabindex / role / aria-label / skip link / landmark / keydown 计数）+ 无裸 outline:none + 无 keypress 单字符快捷键（2.1.4 自然满足）+ 无 dragstart/setPointerCapture（2.5.7 自然满足）+ 生成器源码防回退 + node --check 语法门禁。
- docs/66：§六 差距清单**全部销项**（表格改「已满足 + 原差距销项情况」双栏）、§八.5 口径更新（#598 只读查据 → #605 已改造销项）、§九 补 JS 语法门禁与基线计数、尾注版本行更新。
- 双 HTML 经生成器重生；concept_gui data-sha256 35b2681d78da→2bd250ca0916（版本串入 payload，预期内变化，`--check` 通过）；report_viewer source-sha256 同步刷新。
- 版本号 `0000.0000.0000.0014.20261024` → `0000.0000.0000.0015.20261025`：二十处替换 + 新测试 docstring 戳；0014 代码/数据层零残留（README 历史块不动）。**日期后缀跨天变 20261025**（2026-10-25 定版，里程表语义）。
- README 版本更新区加 #605 块 + 当前口径五处刷新为 0015。

### 27.5 验证与交付
- `node --check` 双页内联 JS 通过；`test_a11y_operable` 12 passed；定向 `test_concept_gui` 7 passed。
- 双 HTML `--check` 同步；四构建脚本（comp/baigong/datong/zhuangzi）`--check` 全过。
- 全量 pytest **1697 passed / 5 skipped**（基线 1685 + 12 新门禁），零回归。
- git 提交并推送 origin/main。

### 27.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | docs/66 §八.3「不得宣称完全无障碍」红线守住——销项表述用「已满足（实测在位）」逐条对应 WCAG 条款，不夸大；既有 script 瘫痪 bug 如实登记来源与影响面，不掩饰 | #605 §27.3 / docs/66 §六 |
| **智**（研判/编目） | 差距清单九项逐项分型：真缺口（focus-visible/24px/landmark/SVG 键控）实改；自然满足项（2.5.7 无拖拽、2.5.2 click 模型、2.1.4 无单字符快捷键）核证后登记不虚设处理器 | #605 §27.2 / test_a11y_operable |
| **体**（真实落点） | 双生成器改造 + 双 HTML 重生 + 12 项门禁测试 + docs/66 销项 + README #605 块 + 版本 0015 二十处 + HANDOFF §27 均可验收 | #605 §27.4 |
| **美**（整体全息） | 「契约（docs/66）—差距清单（§六）—门禁测试（test_a11y_operable）—生成器（防回退断言）」四层同源闭环，前 Optional 待办转为既成事实 | #605 docs/66 §六/§九 |
| **劳**（实做实证） | node --check 实证修复（非纸面销项）；1697 passed 零回归；0014 零残留；四构建 + 双 HTML `--check` 全过 | #605 §27.5 |

## 28. 2026-10-25 第二十轮：可持续方向收尾②——lint-gate 落地（#606，shellcheck 一环接入 CI + 文档实数刷新）

### 28.1 收尾目标（承接用户指示「所有可持续继续方向都得继续推进到收尾」）
- 方向 B = lint-gate 落地：宿主 shellcheck 0.9.0 在位、本仓有自有构建脚本与 6 个 workflow，comp 概念系统登记「宿主可用、CI 未接入」——判定有真实 counterpart，推进到收尾。hadolint/actionlint 宿主缺席，如实挂 needs_action 不伪造接入。

### 28.2 落地事实（#652）
- **`scripts/check_shell_lint.sh`（外层仓根，新增）**：白名单制 lint 本仓自有 **11 个 .sh**——classics 六构建脚本（harmony/ios-mac/arch/debs/mobile/rs）+ 内层 `tools/bootstrap.sh`、`tools/disposable-env.sh`、`Windows/build.sh`、`Windows/push-to-github.sh` + 门禁脚本自身；显式排除 **quantum-kernel 上游 Linux 6.18.57 内核源码树**（vendored，lint 口径属上游）与 **`research/plang/samples/bash.sh`**（语法样例）。默认严重级别（含 note/style）零告警才算过；宿主 shellcheck 缺席时如实 SKIP（exit 0 + 明示），CI 侧由 workflow 安装步兜底。
- **防漏网机制**：门禁脚本末尾全仓扫描「非排除」.sh，凡不在白名单者直接失败——新增脚本必须显式入册（脚本 + 守卫测试两处同步）；rogue 文件冒烟实测拦截成功。
- **`.github/workflows/lint-shell.yml`（新增）**：push/PR（paths `**/*.sh` + 门禁脚本 + workflow 自身）+ workflow_dispatch 触发；先 `apt-get install shellcheck` 再跑门禁脚本；concurrency 与既有 workflow 一致（cancel-in-progress 省 Actions 分钟）。
- **`system-optimizer/tests/test_lint_gate.py`（新增，7 项）**：脚本存在可执行（shebang/可执行位）/ 脚本 WHITELIST 与测试 EXPECTED 双向一致 / 白名单覆盖扫描全集（无漏网 + 无失效条目）/ 排除口径非空转（内核树与样例真实存在）/ workflow 存在且引用脚本且含安装步 / hadolint·actionlint 未接入防伪断言 / 实跑 PASS-or-SKIP。PyYAML 挪威问题（`on:` 解析为布尔键 True）在测试内兼容处理。
- **修复既有 5 处 shellcheck 告警**（真实 counterpart 收尾）：`classics-linux/build-arch.sh`（SC2015 `A && B || C` 改为 `cd ... || exit 1` 分行；SC2012 `ls|awk` 改 `find -printf`）、`classics-linux/build-mobile.sh`（SC2015 同上；SC2086 `set -- $spec` 有意拆分，加 disable 指令并注释说明受控字面量）、`Windows/push-to-github.sh`（SC2164 `cd ... || exit 1`）。修复后本仓自有 .sh 全零告警，`bash -n` 语法复验通过。

### 28.3 文档实数刷新（#653）
- **comp `lint-gate` 概念**（`research/comp/build_comp.py` detail/落法/桥接三处 + `comp_taxonomy.json` 重建）：「未落地」→**「部分落地」**——shellcheck 一环落地（脚本 + CI + 守卫），clang-format/clang-tidy 与 hadolint/actionlint 未接入、宿主仅 shellcheck 在位，如实分级；桥接「知止」表述改为「已投产的登记落地、未投产的挂 needs_action」双向如实。
- **`toolchain_catalog.json` ci-workflows 条目**：workflow 实数 **2→9**（find 实证：外层 `.github/workflows/` 7 个——build/audit-concepts/audit-standards-eol/build-android/build-harmony/build-python/lint-shell，内层 `.github` 1 + `Windows/.github` 1）；paths/setup_steps/verify 三字段同步刷新，版本串随轮次升 0016。
- **`docs/57` §2.13**：目录段列全 7 个外层 workflow、配置逻辑顺序记 lint-shell 安装兜底与 needs_action 分级、验收段注明旧「全仓仅 2 个 workflow」为 #652 前状态。
- **过时记述更正纪律**：§25.3（第十七轮）原文「workflow 实数仅 2 个」为当时口径，**历史原文不动**，在本节如实更正沿革（#603 时已 6 个未同步刷新，本轮一并认账）。

### 28.4 执行结果与落点
- 新增：`scripts/check_shell_lint.sh`、`.github/workflows/lint-shell.yml`、`system-optimizer/tests/test_lint_gate.py`（7 项）。
- 修改：三脚本修复 5 处告警；`build_comp.py`（概念三处 + odometer 版本串）；`toolchain_catalog.json`（ci-workflows 内容 + 三处版本串）；`docs/57` §2.13。
- 重生：`comp_taxonomy.json`（含新概念文本）、`datong/baigong/zhuangzi_taxonomy.json`（deno 版本字段）、双 HTML（concept_gui data-sha256 因版本串入 payload 而变、数据语义不变）。
- 版本号 `0000.0000.0000.0015.20261025` → `0000.0000.0000.0016.20261025`（同日，D 段进位）：version.py / pyproject.toml / main.go / console.ts ×2 / report_viewer.ts ×3 / 三 taxonomy JSON ×6 / comp odometer / catalog ×3 / test_toolchain + test_a11y_operable docstring 戳（上轮 a11y docstring 日期笔误 0015.20261024 一并校正为 0016.20261025）。
- README 版本更新区加 #606 块 + 当前口径五处刷新（表格 deno 双文件版本 0015→0016，版本区历史块不动）。

### 28.5 验证与交付
- shellcheck 全仓自有 .sh 零告警（默认级别）；门禁脚本 `[PASS] 11 个脚本、无漏网`；rogue 冒烟拦截成功。
- 守卫测试 7/7 通过；四构建脚本 `--check` 全过；双 HTML `--check` 同步。
- 全量 pytest **1704 passed / 5 skipped**（基线 1697 + 7 新守卫），零回归。
- git 提交并推送 origin/main。

### 28.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | hadolint/actionlint 宿主缺席即挂 needs_action、不伪造接入；「部分落地」分级不夸大全景；§25.3 过时记述认账但历史原文不动；门禁 SKIP 语义如实明示（exit 0 但打印未评估） | #653 §28.1/§28.3 / lint-shell.yml |
| **智**（研判/编目） | 白名单机制替代全仓扫描（内核树 vendored 非本仓资产）；「防漏网」把入册纪律工程化；5 处告警逐处按根因修复而非 blanket disable（唯一 disable 处附受控字面量论证） | #652 §28.2 |
| **体**（真实落点） | 门禁脚本 + CI workflow + 7 项守卫测试 + 三脚本修复 + comp 概念/catalog/docs/57 三处文档 + 双 taxonomy 视角 + README #606 块 + 版本 0016 + HANDOFF 本节，全部可验收 | #652/#653 §28.4 |
| **美**（整体全息） | 「契约（comp 概念）—实数（catalog/docs/57 find 实证）—门禁（脚本+CI）—守卫（测试双向契约）」四层同源；概念落法、catalog 条目、文档口径三处版本串同轮刷新不漂移 | #653 §28.3 |
| **劳**（实做实证） | shellcheck 零告警为实跑非纸面；rogue 冒烟实测拦截；1704 passed 零回归；0015 代码/数据层零残留 | #652/#653 §28.5 |

## 29. 2026-10-25 第二十一轮：导入分析学习应用——Hermes 多项目只读分析（#607，五项目全网核实）

### 29.1 任务来源与核实经过
- 用户指令：「导入分析学习应用 github/google-research2 、github/google-research，其实忘记仓库了，主要是Hermes或类似的英文；继续」——仓库记忆不确切，点名「Hermes 或类似英文名」。
- 联网核实第一步：**`google-research2` 组织不存在（404）**；**`google-research` 组织内无 hermes 仓库**（repo 搜索 total=0，monorepo 顶层树亦无 hermes 路径）——用户记忆中的组织名有混淆。
- 全网以「Hermes」为锚核实出五个真实项目，经 AskUserQuestion 确认，用户批复「**都有，以防未来需要用，还要重新来过**」——五项目全部只读分析入账。

### 29.2 五项目事实（2026-10-25 只读抓取）
- **`m-lab/hermes`**（与用户「google」记忆最吻合项）：ACM SIGCOMM 2026 论文（DOI 10.1145/3789240.3829129，CC BY 4.0），作者 Loqman Salamatian / Kevin Vermeulen / Dave Choffnes / Ethan Katz-Bassett / Phillipa Gill；M-Lab NDT 公开测速（延迟/吞吐/丢包 + 前向 traceroute + 推断反向路径）→ 用户组（源 AS × 都会区 × M-Lab 站点，≥25 基线测试/≥5 客户端 IP/单 IP 防控/地理一致性）→ 统计检测（延迟显著性+最小效应量；吞吐 Wasserstein + Mann–Whitney U；丢包谨慎并列）→ 双向路径层析（时间层析抓改道/链路消失 + 相关层析抓拥塞）→ 三级分类 localized/ambiguous/unresolved；2024-08 起运行；BigQuery 公开数据集 `mlab-collaboration.hermes_union.events_enriched`（六类记录、列名即契约）+ `events_explained_daily`；Docker 管道（env 注入 IPINFO/HOIHO token，默认最近 2 天，`--start-date/--end-date` 区间）；仪表盘 hermes-dashboard.org。评测口径：5 个月 40 亿次测试、166 国 65,000 事件、仅 5.2% 被其他公共观测台捕获、11× 公开讨论事件、Blame-IT 重实现检出 91.4%/片段一致 94.5%、27 起有记录事件检出 25 起（23 起定位一致）、半数肇事链路仅单方向可见、定向补测降歧义 47%/收敛 31%；Indianapolis 案例（ind23372/AS23372，78→2622 事件每日，71 客户端组上传 -95%，Cogent + Hurricane Electric transit）。
- **`S4AI-CornellTech/Hermes`**（ISCA 2025 pp.958–973，MIT）：RAG 算法-系统协同设计；层次化搜索簇跨机 + sample-nprobe(~8)/deep-nprobe(~128) 两阶段检索 + DVFS；栈 Python 3.11 + conda / faiss-gpu 1.8.0 / PyTorch CUDA 11 / vLLM / pyRAPL+pynvml+pymongo；能耗实测 Intel RAPL + `perf stat -e power/energy-pkg/ -e power/energy-ram/`；数据 SPHERE_899M/100M/100K + TriviaQA；模型 GEMMA-2 9B / BGE-Large / BERT-Base；measurements/modeling/figures 三段分离；Docker 需 `--gpus all --privileged -v /sys:/sys`；末次提交 2025-05-02。
- **`nousresearch/hermes-agent`**（组织列表，MIT）：主仓 257k stars（Python，「The agent that grows with you」）；三层插件（official 461 / labs 110 / example 44）；六个记忆提供器独立插件（supermemory/openviking/honcho/mem0/byterover/retaindb）；`hermes-agent-self-evolution`（DSPy + GEPA，5.6k）；`hermes-toolperf-evals`（工具 A/B 评估）+ `hermes-compression-eval`（ContextCompressor 离线评估，方法论改编自 Factory 2025-12《Evaluating Compression》）；碎片插件仓归档并入 official/labs 的治理演进；无人维护仓 ⚠ 明示。
- **`aziksh-ospanov/HERMES`**（arXiv 2511.18760，2025-11-24；仓库页称 ICML 2026 并登 needs_verify，MIT）：单步形式化验证器；对 LangGraph agent 暴露唯一工具 `verify_one_mathematical_step`，Lean 4 自动形式化后返回 CORRECT/INCORRECT/VERIFICATION FAILURE 三值；prover 改编自 Goedel-Prover-V2，Lean4ServerScheduler（4 并发/120s 超时/内存 10）；记忆模块（HuggingFaceEmbeddings + InMemoryStore + Qwen3-Embedding-0.6B，默认关）；栈 Python 3.10+ / LangChain / Lean 4 + Mathlib4 + REPL / OpenAI 兼容 API（默认 DeepSeek）/ Linux only；基准 MATH500/AIME'25/CollegeMath/HARDMath2 × Qwen3-8B/o3-mini/DeepSeek-V3.2（HERMES@5+Skywork 全面最佳，如 DeepSeek-V3.2 98.2/80.0/84.0/36.5）；reward-model 对比行依赖仓外 pipeline（README 明言不在本仓）。
- **`haowei-freesky/HERMES`**（ACL 2026 Main，arXiv 2601.14724）：KV Cache 即层次化记忆的流式视频理解；LLaVA-OneVision 0.5b/7b/72b + Qwen2.5-VL 3B/7B/32B；流式基准 StreamingBench/OVO-Bench/RVS-Ego/RVS-Movie + 离线 VideoMME/MVBench/EgoSchema；kv_size 6000 预算硬参数化 + sample_fps 0.5 + num_chunks 8；基于 ReKV（致谢明示）；2026-03-23 全量代码发布，末次提交 2026-05-08。

### 29.3 边界分级
- **五项目全部「纯技术可学习类」**：本仓无网络性能观测 counterpart（netsys/dnshealth 为诊断概念编目，无 NDT/测速/层析实装）、无 RAG/向量索引 counterpart、无 Agent 运行时 counterpart（docs/69 已登记）、无 Lean 形式化验证 counterpart、无视频理解 counterpart——守 docs/59（#591）纪律，**只沉淀学习笔记，不新增概念**，九概念系统拓扑与桥接不变。
- 第三方口径 needs_verify：Nous star 数（组织页 257k vs 凤凰网报道 14 万→翻倍、OpenRouter 消耗榜首、日耗 271B token）、aziksh venue（arXiv vs ICML 2026 页称）、m-lab star 数与代码许可条款、haowei 许可条款与「HF 每日论文第 3」、各论文宣称指标（94.5%、11×、+67%/-80% FLOPs）均未独立复现。

### 29.4 执行结果与落点
- 新增 `docs/70_导入分析学习应用-Hermes多项目只读分析.md`：五资源概览表 + 边界分级三档 + 分主题笔记 3.1–3.5 + 拓扑验证 + 落点清单；可复用纪律收敛为四条——公开可复现的测量、三值诚实分级、限额显式、评估框架先于宣称（「列名即契约」另列）。
- README 版本更新区加 #607 块 + 当前口径五处刷新（表格 deno 双文件版本 0016→0017，版本区历史块不动）。
- 版本号 `0000.0000.0000.0016.20261025` → `0000.0000.0000.0017.20261025`（同日，D 段进位）：version.py / pyproject.toml / main.go / console.ts ×2 / report_viewer.ts ×3 / 三 taxonomy JSON ×6 / comp odometer / catalog ×3 / 三测试 docstring 戳；0016 代码/数据层零残留（README 历史块不动）。
- 四构建脚本重跑 + 双 HTML 生成器重生（concept_gui data-sha256 因版本串入 payload 而变、数据语义不变）。

### 29.5 验证与交付
- 全量 pytest 零回归（基线 1704 passed / 5 skipped）；四构建 `--check` 全过；双 HTML `--check` 同步；shellcheck 门禁不受影响。
- git 提交并推送 origin/main。

### 29.6 「德育体知（智）美劳全面发展（先天道体）」维度映射

> **育**（教育之体，全套框架的承载）：**北京师范大学**——「教书育人 / 言传身教 / 诗书礼易」，代表**国家民族**的传道受业解惑，**非社会组织、非企业**（全量释义见 §12 框架释义块）。

| 维度 | 本轮落账 | 对应交付 |
|------|----------|----------|
| **德**（诚实/守界） | 用户记忆失实（组织不存在/无 hermes 仓）时先核实再入账，不将错就错；五项目论文指标、star 数、venue、许可全部 needs_verify 挂牌不背书；「同名不同物」明确分割不混为一谈 | #607 §29.1/§29.3 / docs/70 §二 |
| **智**（研判/编目） | 「都有」批复下五项目并行只读抓取、按「问题-方法-纪律」三段式分别入账；可复用纪律跨项目收敛为四条并映射本仓同构实践（三值分级↔needs_verify 旗标、列名即契约↔schema 版本化、限额显式↔探针限额、评估先于宣称↔--check 门禁） | #607 §29.2 / docs/70 §三 |
| **体**（真实落点） | docs/70（五项目学习笔记）+ README #607 块 + 当前口径五处刷新 + 版本 0017 落点 + HANDOFF 本节，全部可验收 | #607 §29.4 |
| **美**（整体全息） | 五个异域项目（网络测量/RAG 能耗/Agent 生态/形式化验证/视频缓存）收束为同一思想家族——**公开可复现的测量 + 三值诚实分级 + 限额显式**，与本仓 catalog 新鲜度两栏、needs_verify 旗标、探针限额同构，形成「他山之石 ↔ 本仓纪律」的互证网络 | #607 docs/70 §三各节 |
| **劳**（实做实证） | 五仓库页/论文页/官方博客逐一双路核实（组织搜索 + monorepo 树 + repo 搜索 + WebFetch）；1704 passed 零回归；0016 零残留 | #607 §29.1/§29.5 |
