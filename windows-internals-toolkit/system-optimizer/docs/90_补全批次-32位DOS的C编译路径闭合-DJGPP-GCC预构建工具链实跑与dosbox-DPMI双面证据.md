# 90_补全批次——32 位 DOS 的 C 编译路径闭合：DJGPP GCC 预构建工具链实跑与 dosbox DPMI 双面证据

> 批次定位：接 0028 轮挂号的诚实缺口「DJGPP 的 GCC/libc/stub 包不在 apt（仅 binutils 侧 as/ld）；
> watcom 不可得——32 位 DOS 侧只有汇编链、没有 C 编译器（needs_verify）」。本批按「闭环-缺口分类
> 与按需补齐」纪律真正闭合该缺口：**不新写轮子，从上游取经预构建工具链，实跑 ANSI C 闭环**，
> 并以 DOS 侧双面证据（stdout 流 + 文件回读）与独立复算钉死结果。

## 一、缺口定位与路线选择（先探测再决策，不臆造）

32 位 DOS 档在 0028 批次止于 **as/ld 手写链**：`i586-pc-msdosdjgpp-as` + `ld` 从手写汇编产
go32 DPMI 可执行（hello32.exe 7628B，dosbox 实跑 exit 0）。C 编译路径的三块拼图：

| 拼图 | apt 现状 | 上游可得性 | 本批决策 |
|---|---|---|---|
| DJGPP binutils (as/ld/objdump) | ✅ binutils-djgpp 2.35.1+dfsg-2 | — | 沿用 apt 版（预构建包亦自带） |
| DJGPP GCC（C/C++ 前端 + 代码生成） | ❌ 不在 apt | andrewwutw/build-djgpp v3.4 预构建 Linux64 资产（GCC 12.2.0，2023-06-12） | **下载预构建** |
| DJGPP libc + stub（crt/go32/stubedit） | ❌ 不在 apt | 同上资产内一并提供 | **下载预构建** |

路线对比（探测后决策）：

1. **apt 直装**：`apt-cache search djgpp` 只有 binutils-djgpp——GCC/libc 不在 Debian/Ubuntu
   任何套件（watcom 亦不在 apt）。排除。
2. **从源码构建交叉 GCC**（djcross / build-djgpp.sh 源码路线）：需 gcc+binutils+djgpp-cvs
   全套源码 + makeinfo/bison/flex/zlib，构建时长以小时计，且 djgpp C 库要从 CVS 取。
   **不必要——社区已有同脚本产出的 Linux64 预构建资产**（NetHack 3.7 官方交叉编译指引即引用它）。
3. **预构建资产**：`github.com/andrewwutw/build-djgpp/releases/tag/v3.4` 的
   `djgpp-linux64-gcc1220.tar.bz2`（**80,596,981 字节**，sha256
   `8464f17017d6ab1b2bb2df4ed82357b5bf692e6e2b7fee37e315638f3d505f00`）。**采用**。

## 二、工具链获取与下载工程（wget 中断 + aria2 续传的血泪）

预构建资产走 GitHub release-assets CDN（`release-assets.githubusercontent.com`），单连接速度
约 40KB/s → 5MB/min，且连接频繁抖动。**踩坑与正解**：

- 首用 `wget -c` 循环续传，被中断时 tail 半块未写完；随后装 **aria2 1.37.0**（多连接
  `-x16 -s16 -k1M`）**从该不对齐断点续传拼接** → 文件大小恰为 80,596,981（= 远端全长），
  但 `bzip2 -t` 报 **"data integrity (CRC) error"**——中段拼接处坏字节。
- **正解**：删除损坏文件，aria2 从头干净重下（`-c` 仅用于**断点对齐**的续传），二次
  `bzip2 -t` → **OK**，sha256 与预期一致。
- **纪律**：续传必须断点对齐（区间分块边界），无法保证对齐时宁删重下；完整性用
  `bzip2 -t` + sha256 双验，不以「大小对」为准。

工具链解包后 `djgpp/bin/` 含 `i586-pc-msdosdjgpp-{gcc,g++,ld,as,objdump,ar,...}`，
GCC 12.2.0 / GNU ld 2.30 / GNU as 2.30。

## 三、ANSI C 编译（hello32c.c → hello32c.exe）

闭环程序 `hello32c.c`（ANSI C，继承 8 位档 sdcc 教训，不用任何扩展）：

- 计数器 `counter=0x55`，消息 `"Z32C-RT-OK"`（10 字符）；
- 累加 `counter = 0x55 + Σ字符 + 0x0A`，**设计值 0xFB**（独立复算：字符和 0x29C）；
- 两面证据同文：stdout 两行 + `fopen/fprintf/fclose` 写 `Z32C.TXT` 同两行。

编译：`i586-pc-msdosdjgpp-gcc -O2 -Wall -Wextra hello32c.c` → **零警告**，
`hello32c.exe` **197852 字节**，`file` 判为
`MS-DOS executable, MZ for MS-DOS, COFF for MS-DOS, DJGPP go32 DOS extender`；
`objdump -d` 反汇编 24212 指令行，可见 `__exit`/`_exit` 调用链（`return 0` 的退出路径）。

## 四、实跑闭环（dosbox 0.74-3 无头 + DPMI）

dosbox 0.74-3 的 DPMI 与 DJGPP 12.2 的 go32 桩不兼容，工程上需两步：

1. **开启 conf 的 `dpmi=true`**（默认配置文件不含该行，须手工在 `[cpu]` 段后插入）；
2. 仅开 dpmi 仍报 **`Load error: no DPMI - Get csdpmi*b.zip`**——DJGPP 12.2 桩不接受
   dosbox 内建 DPMI，须**自带 CWSDPMI**：从 `delorie.com` 取 `csdpmi7b.zip`，解出
   `CWSDPMI.EXE`（21325B）放到 C: 挂载目录，go32 桩自动找到。
3. **cwd 落到 C:**：`[autoexec]` 段写 `mount c <dir>` / `c:` / `cd \`——否则程序相对路径
   `fopen("Z32C.TXT")` 落在 dosbox 只读虚拟盘 Z: 上 → FILE-FAIL。

调用：
```
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 60 dosbox \
  -conf dosbox-dpmi.conf -c 'hello32c.exe > C:\OUT.TXT' -c 'exit'
```
结果：**dosbox rc=0**。

## 五、双面证据与独立复算

| 证据面 | 载体 | 内容 | 字节 |
|---|---|---|---|
| stdout 流 | `OUT.TXT`（DOS `>` 重定向，文本模式 `\n`→`\r\n`） | `Z32C-RT-OK55\nFB\n` | 18 |
| 文件回读 | `Z32C.TXT`（fopen/fprintf/fclose，二进制 `wb`） | `Z32C-RT-OK55\nFB\n` | 16 |

两面一致；累加值 **0xFB** 与独立复算 `0x55 + 0x29C + 0x0A` 吻合（`msg` 10 字符和 0x29C）。
18 vs 16 的差异正是 DOS 文本重定向的 `\r\n` 与二进制 `\n` 之别，非数据不一致。

## 六、工程坑实录（本批入账 5 条）

| # | 坑 | 正解 |
|---|---|---|
| 1 | wget 中断尾部半块 + aria2 从不对齐断点续传拼接 → bzip2 CRC 坏（大小对内容腐） | 删文件从头干净重下；续传须断点对齐 |
| 2 | dosbox 0.74-3 `dpmi=true` 仍报 "no DPMI" | DJGPP 12.2 桩需自带 CWSDPMI(csdpmi7b) |
| 3 | 批处理 + CWSDPMI 下 `%ERRORLEVEL%` 不 propagate，`echo` 后 dosbox 退出挂起(rc=124) | 进程完成证据取直跑 rc=0 + fclose 写全，退出码面不伪证 |
| 4 | `-c "C:"` 换驱对后续 `-c` 不生效 | 用 `C:\` 全路径；批处理内部 `cd \` 生效 |
| 5 | 程序相对 `fopen` 落 Z: 只读盘 → FILE-FAIL | autoexec 把 cwd 设到 C:，或程序写绝对路径 |

## 七、诚实边界（不夸大半句）

- **退出码面不做伪证**：批处理 + CWSDPMI 下 DOS `%ERRORLEVEL%` 不 propagate、dosbox 退出会
  挂起，故进程完成以「直跑 rc=0 + `fclose` 成功写全两文件」为证；程序 `return 0` →
  DJGPP exit → int 21h AH=4Ch 经 DPMI 反射，与上批手写 hello32.exe 同路径，未逐字节追 exit code。
- **工具链为预构建二进制**：非本仓从源码构建，版本/内容以上游 release + sha256 钉死；不声称
  「自建工具链」。
- **dosbox DPMI 的兼容性**是本批实证结论（对 DJGPP 12.2 桩不适用），不外推为「dosbox 无 DPMI」。

## 八、整合落点

- `research/comp/build_comp.py`：`protected-32` concept detail + engineering 换「三路径实测」
  口径（as/ld 手写链 + gcc -m32 宿主 + DJGPP GCC C 闭环），缺口改为**已闭合**。
- `research/comp/`：新增 `hello32c.c` / `hello32c.exe`(197852B) / `hello32c_evidence.txt`。
- `tests/test_djgpp32c.py`：设计值 0xFB 独立复算 + 宿主 gcc `-std=c89 -pedantic` 三面
  roundtrip + DOS 侧 MZ 头与证据归档口径（**3 passed**）。
- 版本：comp taxonomy 0071→**0072**；包版本 D 段 0029→**0030**（version.py + pyproject +
  console.ts + report_viewer.ts + go + cnstd 数据 + 5 系统经重建同步）；concept_gui.html 重生
  （data-sha256 `cd5bc5ee…`→`a529aa57…`，11 系统/66 边/2 外部拓扑不变）。

## 九、验证与仓外交付

- 定向：`test_djgpp32c`(3) + `test_comp` + `test_cnstd` + `test_concept_gui` + `test_z80core`
  共 **37 passed**；全量 pytest 见提交。
- 静态：11 系统 `build --check` 全过；`tools/audit_concepts.py --strict` 不一致 0。
- 仓外交付：`/workspace/dos-toolchain-20261026/`——`hello32c.c` / `hello32c.exe` /
  `hello32c_evidence.txt` / `collect_32c_evidence.sh` / `dosbox-dpmi.conf` / `CWSDPMI.EXE` /
  `djgpp-cross/`（含 `djgpp-linux64-gcc1220.tar.bz2`）。
