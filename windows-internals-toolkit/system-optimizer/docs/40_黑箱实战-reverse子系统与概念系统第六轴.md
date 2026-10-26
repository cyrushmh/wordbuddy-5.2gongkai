# 40 · 黑箱实战：UPX / MinGW / GDB —— reverse 子系统与概念系统第六轴

> 指令原文：「使用upx wming gdb 等尝试黑箱操作，进行新应用，完善工具链，
> 并且整合到概念系统；继续被中断」。
>
> 本档记录一次完整的黑箱实战：用 MinGW-w64 自造样本、UPX 加壳、自写只读扫描器、
> GDB 四连、strip 前后对照，全部数据固化进 `reverse` 子系统四件套；再把这套
> 实战经验整合进 comp 概念系统（新增第六轴「黑箱逆向」6 条概念）；最后补推
> v0.6.72 欠账。

## 1. 实战链路（全部沙箱只读实测）

```
miniprog.c ──mingw GCC 13──▶ miniprog64.exe / miniprog32.exe   （自造样本）
                                  │
                                  ├──UPX 4.2.2 --best --lzma──▶ 加壳样本（双格式）
                                  │
                                  ├──自写 binary_scan() ──▶ 熵/节区/UPX marker 三特征
                                  │
                                  ├──GDB 四连 ──▶ info functions / disassemble /
                                  │              info proc mappings / break
                                  │
                                  └──strip 前后对照 ──▶ 16000→14472B / 熵 1.522→1.235
```

## 2. 实测数据（v0.6.73 固化为测试常量）

| 测量项 | 裸本 | 壳本 | 口径 |
|--------|------|------|------|
| miniprog64.exe 体积 | 249562 B（PE32+，19 节） | 121050 B（48.50%） | `--best --lzma` |
| miniprog32.exe 体积 | 237482 B（PE32，17 节） | 126378 B（53.22%） | `--best` |
| 整体熵 | 5.898 | 7.035 | 逐节香农熵 |
| UPX! marker | — | @0x205（.text 末尾） | 三特征之一 |
| strip 前后（ELF） | 16000 B / 熵 1.522 | 14472 B / 熵 1.235 | 本地符号移除，PLT 保留 |
| wine 启动 PE | ExecuteEx failed | — | 沙箱限制，事实登记不硬凑 |

PE 解析链（自写扫描器）：MZ → `e_lfanew`(@0x3C) → PE\0\0 → COFF（节数@+2、
optsz@+16）→ 可选头 magic（0x10B=PE32 / 0x20B=PE32+）→ 节表 = COFF+20+optsz，
每节 40 字节。ELF 侧读 `e_ident` 与 machine（62=0x3E=x86-64）。

`packed_guess` 判据：UPX! marker 在位 **或** UPX0/1/2 节名 **或**（节熵>7.5 且
节数≤5）。三特征任一即标「疑似加壳」，不解壳也能判断。

## 3. reverse 子系统四件套

| 文件 | 职责 |
|------|------|
| `data/reverse_docs.json` | 8 条知识：upx_packer_signature / entropy_packing_signal / pe_section_anatomy / mingw_cross_toolchain / gdb_blackbox_basics / elf_vs_pe_tradeoffs / strip_static_analysis / readonly_reverse_ethics（均带 `_note` 沙箱实测口径 + `_position` 只读边界） |
| `native/reverse.py` | 只读层 + `binary_scan(path)`：解析 PE 节表 / 逐节熵 / UPX 三特征；`REVERSE_CHECKS` 8 项全部回链 REFS；`_SELF_POSITION` 只读边界 |
| `tasks/reverse.py` | 3 任务：`reverse_blackbox_scan`（native 动作）/ `reverse_entropy_reading` / `reverse_gdb_playbook` |
| `tests/test_reverse.py` | 16 测试：合成最小 PE（magic 偏移 pe_off+4+20）/ `test_measured_baseline_frozen` 固化全部实测常量 / `test_no_execute_or_network_in_layer` 禁 subprocess·os.system·socket·ctypes·eval·exec / `test_axes_include_reverse` |

**只读边界是硬约束**：native 层禁止执行二进制、禁止网络；GDB 只读观察不下断写
内存——调试是提问，不是修改。授权与法律边界（DMCA 反规避）写入
`readonly_reverse_ethics` 条目。

接线四入口：registry（3 处）、subsystems（category=安全/逆向）、cli
（`cmd_reverse` + `reverse` 子命令，CLI 112→113）、gui（「黑箱逆向·UPX/GDB/熵」
窗口，GUI 97→98）。

**联动轴 4 条**：llvm → reverse（工具面供给）、reverse → asm（指令实证供给）、
reverse → cert（门控：先签名后加壳的顺序纪律）、reverse → gmsstd（关联：
完整性与壳的两面性）。

## 4. 概念系统整合：comp 第六轴「黑箱逆向」

comp 概念系统由五轴扩为六轴（54→60 概念，桥接 49+8→58）：

| 新概念 | 一句话 | 桥接 |
|--------|--------|------|
| upx-packer-signature | 壳识别三特征：marker/节名/高熵 | plang:lang:c、daoxue:principle:zhi-bu-zhi |
| entropy-signal | 熵是「人写代码↔机器致密化」的分界 | datong:concept:yiti-liangmian |
| binfmt-anatomy | PE/ELF 格式解剖是壳识别/符号检查/熵分析的共用底座 | plang:arch:x86-64、llvm:tool:clang |
| blackbox-debug | GDB 四连：没有源码也能问运行态问题 | plang:lang:c |
| symbol-visibility | strip 去本地符号、留动态符号，是可读性与体积的刻意分级 | plang:lang:go |
| crossbuild-sample | 黑箱结论的地基是可复现的自造样本（三态：裸/壳/strip） | llvm:target:x86_64-w64-mingw32、datong:concept:gu |

每条概念的 `engineering` 字段写明本仓落法：**全部真落地**——binary_scan() 即
壳识别与熵的工程实现，GDB 四连固化为 playbook 任务，实测常量由
`test_measured_baseline_frozen` 钉死（换口径必须显式改测试）。

整合手法： escort 6 条概念进 `research/comp/build_comp.py` 的 CONCEPTS 与
ENGINEERING（先 `--prompt-only` 式通读再构建），重建后**人工补回 guidance
根环补丁**（`_meta.guidance` + `comp:pipeline-overview → daoxue:guidance:
zhengti_zhida` 桥，259 行注入史见 37042ae/7c37c6e）——这是本仓既有约定：
build 脚本产物 + 组网补丁两件事，`--check` 只验构建产物，组网由
`tools/check_concept_mesh.py` 守。

**反向踩坑记录（供后续版本镜鉴）**：apilab/baigong/datong/zhuangzi 四库的提交
版本同样带构建后人工补丁（guidance 块/桥、手改计数器「当前 110」）。本轮曾
整机重建四库，结果 guidance 桥被 build 脚本剥掉（19→18/50→49/51→50），
12 个测试失败。修正：**回退重建，手术式只改三个计数字段**
（cli_subcommands 112→113 / gui_windows 97→98 / deno_report_viewer_version
0.6.72→0.6.73），guidance 与手改字符串原样保留。教训：带组网补丁的 taxonomy
不做整机重建，只 surgically 同步计数。

## 5. 版本同步与验证

- 版本 0.6.72 → 0.6.73：五处（`__init__.py` / `pyproject.toml` /
  `src/go/main.go` / `src/deno/console.ts` / `src/deno/report_viewer.ts`）+
  `tools/gen_report_viewer.py` 重生 report_viewer.html。
- concepts 四库计数据实测同步（CLI 113 / GUI 98 / deno v0.6.73）；
  apilab tagline「112 CLI」→「113 CLI」；test_gui_quantum 两处硬编码同步。
- comp `--check` 60 概念 / 57 桥（构建产物）通过；组网后磁盘 58 桥，
  `check_concept_mesh.py` 与 `audit_concepts.py --strict` 零欠账。
- 全量回归 **1445 passed / 3 skipped / 0 failed**（基线 1429 + reverse 16）。
- README comp 行更新为六轴 60 概念口径。

## 6. 欠账清点

- v0.6.72（ef6c5b2，hmosstd）因弱网未推送，本档收尾时前台重试补推。
- reverse 子系统与概念系统整合构成本轮提交（v0.6.73）。
