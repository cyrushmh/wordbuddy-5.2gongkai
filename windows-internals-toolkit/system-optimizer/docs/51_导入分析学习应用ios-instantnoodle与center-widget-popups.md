# 51 导入分析学习应用：ios-instantnoodle 与 center-widget-popups（v0.6.85）

> 来源：`https://github.com/haxi0/ios-instantnoodle`、`https://github.com/terminallywell/center-widget-popups`
> 落点：comp 概念系统新增第八轴「引导与实测纪律」（4 概念 + 4 条桥接）、zhuangzi
> ergonomics 域新增「幂等护栏」（第 8 条人体工程学原则）。
> 纪律红线（沿用 docs/31）：只登记可核实的事实；无法核实的标 `needs_verify`，不臆造；
> 桥接目标必须真实存在（构建期 `--check` 校验无悬空）；两个源仓库均只作**只读分析**，
> 不复制其代码进本仓、不打包其产物。

## 一、资源概览与可复用点

| 资源 | 性质 | 规模 | 可复用工程纪律 |
|---|---|---|---|
| haxi0/ios-instantnoodle | XNU(iOS 16) 引导 shim：arm64 Linux Image 头 + 自管 MMU + live-FDT 探查 + UFS 驱动；OnePlus 7 Pro(guacamole)/8(instantnoodle)/Redmi Note 10 Pro(sweet) 三板 | 169 文件，shim C+asm 约 900 行 + tools 30 个 Python 脚本 + XNU 补丁系列 0082 号 | ① 无载荷先出 live-FDT bring-up 诊断报告（probe.c）；② *(verify)* 标注纪律（未经硬件观测的数字不信任）；③ 构建期绝对重定位门禁（readelf ABS64=0 才放行）；④ -DHOST_TEST=1 宿主 harness 无硬件验证；⑤ AGENTS.md/NOTES.md 交接纪律（观测与猜测分记、里程碑留痕） |
| terminallywell/center-widget-popups | KDE Plasma 6 KWin 脚本：把用户定义水平区间内弹出的 widget popup 移到屏幕水平中心 | 9 文件，main.js 约 40 行（MIT） | ① 幂等护栏（\|geo.x-x\|<1 即返回，frameGeometryChanged 回调不自我触发）；② 范围纪律（区间外不顺动、只改水平位置，README 如实挂 Limitations）；③ 配置夹紧（a<=b?[a,b]:[b,a] 防倒置 + kcfg min/max/default）；④ AI Use Disclosure（人类审查后在 Plasma 6.8 实测） |

两仓库的诚实口径都值得记一笔：ios-instantnoodle 的 README 用「What works / What does
not work (yet）」两张表把「能开机到桌面」与「无 GPU/无无线电/安全模型关闭」分开陈述；
center-widget-popups 明示「未经垂直面板与多显示器测试」。**先划边界再讲能力**，与本仓
概念系统的 needs_verify / 诚实边界段同构。

## 二、comp 新增第八轴「引导与实测纪律」（66 → 70 概念，67 → 71 桥接）

轴定义：把运行期才炸的错误提前到构建期/引导期——诊断优先引导 / 在役设备树探查 /
绝对重定位门禁 / 宿主测试 harness。每条都带 engineering（工程落法），写清它在本仓的
对应物，不写本仓没有的能力。

| 新概念 | 一句话 | 桥接（comp 首批 quantum 边 + daoxue 边） |
|---|---|---|
| `diagnostic-first-boot` | 无载荷可引导时先出诚实诊断报告，而非静默失败或伪造成功 | → quantum:qsim-asset（可验证诊断：诊断先行，两头都诚实） |
| `live-fdt-probe` | 先观测后信任：编译期 profile 数字未经硬件观测永远标 *(verify)* | → daoxue:zhi-bu-zhi（知不知上：知道自己有所不知） |
| `abs-reloc-gate` | 构建期对每个 C 目标跑 readelf -r，ABS64 非零即构建失败 | → quantum:qkern-patch-distribution（可复现门禁：洁净回放 ↔ 零绝对重定位） |
| `host-test-harness` | -DHOST_TEST=1 宿主编译运行同一份 C：无目标硬件也能验证 | → quantum:qsim-engine（宿主验证：都不依赖目标硬件，也都不假装拥有它） |

**本仓对应物（engineering 落法，全部已真实存在）**：quantum-core 缺接口时 state.json
记 available=false + 面板「host(模拟)」（v0.6.84 实测）；needs_verify 纪律 + audit_concepts
--strict 拦截「未核实冒充已核实」；check_repo_guard.py / build --check / HTML sha256
同步校验；宿主模拟架构（docs/44 §8）+ pytest 1579 项 + quantum-core make check。

## 三、zhuangzi 新增第 8 条人体工程学原则「幂等护栏」（19 → 20 概念）

canon_refs: 应帝王。gist：改动必有阈值护栏，回调不触发反馈环——只动该动的，动过之后
不再动。

- 源模式：center-widget-popups 的 `|geo.x - x| < 1` 重入护栏——移动引发的
  frameGeometryChanged 回调再进来时已在目标位，不再触发第二次移动；
- 范围纪律：弹窗水平中心落在用户区间（默认 25%–50% 屏宽）外则保持 Plasma 原位，
  只改水平位置——「顺性不抢」在窗口管理层的一个精确落法；
- 本仓对应：GUI 报告「生成/关闭」按钮模式不重入、genmon 定时刷新只读不写、破坏性
  操作前置确认——每个自动改动可重复执行而不累积副作用。

## 四、拓扑与门禁核验（构建后实测）

```
comp   70 概念（+4）/ 71 桥接（+3 quantum / +1 daoxue / netsys 2→3）   --check 通过
zhuangzi 20 概念（+1）/ 18 桥接（不变）                                  --check 通过
```

- `research/comp/build_comp.py --check`：70 概念、语言编译需要 15 实测、71 条桥接无悬空；
- `research/zhuangzi/build_zhuangzi.py --check`：20 概念、18 条桥接无悬空、用户端面
  事实与源码实测一致；
- comp→quantum 首批 3 条边：诊断优先/可复现门禁/宿主验证 ↔ qsim-asset / qkern-patch-
  distribution / qsim-engine（build_comp.py 桥接校验新增 quantum 目标池 + 测试同步）。

## 五、诚实边界（未落地 / 待核实）

- **两仓库代码零复制**：本仓不 vendored ios-instantnoodle 的任何 C/补丁，不打包
  center-widget-popups 的 kwinscript；仅把可复用纪律登记为概念与工程落法。
- **ios-instantnoodle 的移植结论（iOS 16 在 OnePlus 上开机到桌面）是上游项目的事实**，
  登记为源仓库观测，不构成本仓能力声称；本仓量子架构仍是宿主模拟（docs/44 §8）。
- **XNU/Mach-O/arm64 启动细节未逐条核对**：本文档只引用 README/NOTES/源码中可直读的
  事实（build.sh 的 ABS64 门禁、probe.c 的 FDT 走法、main.js 的阈值护栏），未在
  本机复现其构建（缺 aarch64 交叉工具链与目标硬件），按 needs_verify 口径不扩写。
- **center-widget-popups 未经本仓实测**：其 Limitations（垂直面板/多显示器未测）原样
  转述；本仓桌面基座是 XFCE genmon（docs/48），KWin 脚本只作模式参照，不声称等效。
- **AGENTS.md 交接纪律**：ios-instantnoodle 的「NOTES.md 活跃交接 + 观测与猜测分记」
  与本仓既有 AGENTS.md 口径一致，本轮不新增纪律条目，仅在本文档记一笔对照。
