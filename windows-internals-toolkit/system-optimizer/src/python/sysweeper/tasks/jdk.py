"""OpenJDK / JVM 任务定义（v0.6.66；原 jvm.py 拆分）。

内核 module/firmware/eBPF 部分已拆到同目录 `kmod.py`——按 omni 子系统
「按 key 归位」原则，本文件 ↔ `jdk` 子系统。

这块的底线是**只读**：

- **OpenJDK**：只 `java -version` / `--list-modules` / `PrintFlagsFinal` /
  `jcmd -l` 这类查询命令。绝不改 `JAVA_HOME`、不设 GC 参数、不录制 JFR、
  不 attach 进程。系统属性只输出白名单键（口令/令牌类只报存在性）。

任务分两类：
- `jdk_*`：OpenJDK 只读体检（platform="any"，因为 JVM 各平台都有）。
- 指引类：需要 root 或会改状态的动作，一律以 manual 文本给出，
  并显式写明「本工具不执行」。

依赖语言：JDK 相关任务标 `requires_lang="java"`——没装 JDK 时自动隐藏，
不强求安装（与全库的语言自动启用机制一致）。

对应 native 层：`native/jdk.py`（java_runtime_report / java_properties_report /
modules_report / gc_report / jit_report / diag_tools_report /
jvm_processes_report / jfr_capability_report / build_tool_cache_report / jdk_report）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    # ------------------------------------------------------------------ #
    # OpenJDK / JVM 只读体检（platform="any"；无 JDK 时自动隐藏）         #
    # ------------------------------------------------------------------ #
    Task(
        id="jdk_runtime",
        platform="any",
        title="OpenJDK 运行时总览（java -version / JAVA_HOME，只读）",
        category="maintenance",
        risk="low",
        requires_lang="java",
        desc="读 java 版本、javac 是否可用、JAVA_HOME 与运行架构，确认当前用的是哪个 JDK。",
        actions=[N("jdk.java_runtime_report", "java -version / javac -version / JAVA_HOME 只读")],
        standards=["[官方] OpenJDK 官网：https://openjdk.org/",
                   "[官方] java -version / javac -version（JDK 工具官方子命令）",
                   "[国际] Java SE 规范（JVM Spec，java.version / java.home 系统属性）"],
        notes=["多版本并存时用 JAVA_HOME 或 PATH 顺序决定实际生效的 JDK。",
               "本工具不安装 JDK、不改 JAVA_HOME、不动 PATH。"],
        caveats=["输出含 java.home 等本机路径，属预期（本机自检），不外传。"],
    ),
    Task(
        id="jdk_properties",
        platform="any",
        title="JVM 系统属性体检（白名单键，口令类不回显）",
        category="privacy",
        risk="low",
        requires_lang="java",
        desc="读 -XshowSettings:properties 的白名单键；疑似口令/令牌的键只报「存在」不打印值。",
        actions=[N("jdk.java_properties_report", "java -XshowSettings:properties（只输出白名单键）")],
        standards=["[官方] java -XshowSettings:properties（JVM 诊断输出）",
                   "[国际] Java SE 规范：System Properties（java.home / os.arch / file.encoding 等）",
                   "[国标] GB/T 35273《信息安全技术 个人信息安全规范》（属性表可能含环境信息，按敏感处理）"],
        notes=["为什么不全量输出：属性表里混有 http.proxyPassword、令牌、带凭据 URL，"
               "整段 dump 会造成敏感信息落盘。",
               "白名单机制与 OpenWrt 层的敏感键处理同一条底线。"],
        caveats=["这是隐私体检项：它证明「我们不打印敏感值」，不要反过来用去 dump 全部属性。"],
    ),
    Task(
        id="jdk_modules",
        platform="any",
        title="JPMS 模块系统体检（java --list-modules，只读）",
        category="maintenance",
        risk="low",
        requires_lang="java",
        desc="列出 JPMS 模块清单与顶层分类统计，判断模块层是否完整、java.se 根模块是否在位。",
        actions=[N("jdk.modules_report", "java --list-modules（JPMS 模块清单，只读）")],
        standards=["[官方] JEP 261: Module System（JPMS 总纲）",
                   "[官方] java --list-modules / --describe-module（模块工具官方子命令）",
                   "[国际] JEP 277: JDK 内部模块化（--add-exports/--add-opens 的由来）"],
        notes=["JDK 8 无 JPMS，会明确降级为「此版本无模块系统」而非报错。",
               "排查 NoClassDefFoundError / IllegalAccessError 时先看模块层。",
               "用 jlink 裁剪运行时镜像是写操作，本工具只给指引。"],
        caveats=["模块清单本身不敏感，但会暴露用了哪些框架（可作资产测绘参考，请勿外传）。"],
    ),
    Task(
        id="jdk_gc",
        platform="any",
        title="垃圾收集器体检（PrintFlagsFinal，只读不改）",
        category="optimize",
        risk="low",
        requires_lang="java",
        desc="读各 Use*GC 标志的最终生效值，报告当前实际选中的收集器。",
        actions=[N("jdk.gc_report", "java -XX:+PrintFlagsFinal（只打印最终值，不修改）")],
        standards=["[官方] GC Tuning Guide：https://docs.oracle.com/en/java/javase/21/gctuning/index.html",
                   "[官方] JEP 439: Generational ZGC（JDK 21 分代 ZGC）",
                   "[官方] JEP 379: Shenandoah（低暂停收集器）"],
        notes=["PrintFlagsFinal 是只打印不修改的诊断开关，JVM 执行完即退出。",
               "JDK 9+ 默认 G1；JDK 8 默认 Parallel GC。"],
        caveats=["本工具只报告，不替你选 GC——换 GC 是架构决策，应以官方调优指南与压测为准。"],
    ),
    Task(
        id="jdk_jit",
        platform="any",
        title="JIT 分层编译体检（启动慢的根因定位，只读）",
        category="optimize",
        risk="low",
        requires_lang="java",
        desc="读 TieredCompilation / CompileThreshold / 内联上限等标志，解释「刚启动慢、跑一会就快」。",
        actions=[N("jdk.jit_report", "java -XX:+PrintFlagsFinal（只看 JIT 相关标志，只读）")],
        standards=["[官方] Java SE 规范第 7 章：Code Generation",
                   "[官方] JEP 165: Compiler Control",
                   "[国际] JVM 规范：TieredCompilation / CompileThreshold 标志语义"],
        notes=["分层编译关闭时只有解释器 + C2，冷启动明显更慢——这是最常见的「启动慢」原因。",
               "MaxInlineSize / FreqInlineSize 影响热点方法内联，是吞吐/体积的权衡点。"],
        caveats=["只看当前默认值，无法反映你实际启动脚本里带的 -XX 参数（那些不在 JVM 标志里）。"],
    ),
    Task(
        id="jdk_diag",
        platform="any",
        title="OpenJDK 诊断工具面与本机 JVM 进程（只读）",
        category="maintenance",
        risk="low",
        requires_lang="java",
        desc="列出 jcmd/jps/jstack/jmap/jstat/jfr 是否在 PATH，并用 jps/jcmd -l 列本机 JVM 进程。",
        actions=[N("jdk.diag_tools_report", "列诊断工具可用性（只查 PATH，不执行子命令）"),
                 N("jdk.jvm_processes_report", "jps -l / jcmd -l（只列进程，不 attach）")],
        standards=["[官方] jcmd：https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html",
                   "[官方] jps ：https://docs.oracle.com/en/java/javase/21/docs/specs/man/jps.html",
                   "[国际] JDK 工具链规范（jcmd 查询型子命令 vs 有副作用子命令的区分）"],
        notes=["jstack/jmap/jfr 虽有副作用，本工具**不执行**，只报告可用性。",
               "「有没有东西在偷偷跑 JVM」是内存占用的常见排查起点。"],
        caveats=["jmap -histo:live 会触发 full GC、jfr start 持续写盘——均属高开销，本工具禁跑。",
                 "进程列表会暴露命令行参数（可能含口令），属本机自检，勿外传。"],
    ),
    Task(
        id="jdk_jfr",
        platform="any",
        title="JFR 飞行记录器能力核对（只查不录制）",
        category="maintenance",
        risk="low",
        requires_lang="java",
        desc="核对当前 JDK 是否具备 JFR、jfr 工具是否在 PATH，并给出录制用法的指引文本。",
        actions=[N("jdk.jfr_capability_report", "核对 JFR 能力（只查工具与版本，不 start/dump）")],
        standards=["[官方] JFR API：https://docs.oracle.com/en/java/javase/21/jfapi/index.html",
                   "[官方] jcmd JFR.start（JFR 录制入口，本工具不调用）",
                   "[国际] JDK 11 开源 JFR；JDK 8u262+ 回移植"],
        notes=["用法指引：jcmd <pid> JFR.start name=x duration=60s filename=a.jfr，"
               "随后 jfr print a.jfr 查看——**本工具只给文本，不代跑**。",
               "JFR 是 JDK 自带的低开销剖析器，已取代大部分传统的 jstack 抓取流程。"],
        caveats=["录制会持续写盘并可能带来轻微停顿，属诊断期短时操作，不是常驻项。"],
    ),
    Task(
        id="jdk_build_cache",
        platform="any",
        title="Java 构建缓存体积统计（Gradle / Maven，只读）",
        category="cleanup",
        risk="low",
        requires_lang="java",
        desc="统计 ~/.gradle/caches 与 ~/.m2/repository 体积，只报数不删任何文件。",
        actions=[N("jdk.build_tool_cache_report", "Gradle / Maven 缓存体积（只读统计）")],
        standards=["[官方] Gradle 用户主页缓存（~/.gradle/caches）",
                   "[官方] Maven 本地仓库（~/.m2/repository，localRepository 默认值）",
                   "[国际] Maven/Gradle 官方文档：缓存与本地仓库管理"],
        notes=["统计体积以便判断「值不值得清」，清理动作请自行决定。",
               "Gradle 缓存可安全重建（下次构建重新下载），Maven 本地仓库同理但可能含未发布的 SNAPSHOT。"],
        caveats=["本工具只统计，**不删任何缓存**——Maven 仓库里可能有你自己 install 的 SNAPSHOT 构件。"],
    ),
    Task(
        id="jdk_nohard_guide",
        platform="any",
        title="JVM 调优：只给指引不代改（高危动作清单）",
        category="optimize",
        risk="low",
        requires_lang="java",
        desc="列出那些「会真改 JVM 行为」的高危动作及其官方依据，本工具一律只给文本。",
        actions=[M("改 JAVA_HOME / 写 JAVA_TOOL_OPTIONS：影响所有 Java 进程启动，改前确认无遗留进程；"
                   "换 GC（如 -XX:+UseZGC）：以官方 GC Tuning Guide + 压测为准，"
                   "改后用 -Xlog:gc* 观察而非凭感觉；"
                   "设 TieredCompilation=false：冷启动变慢，只在长驻服务且启动不敏感时考虑；"
                   "jcmd GC.run / jmap -histo:live：会触发 full GC，生产环境等同一次故障演练；"
                   "jfr start/dump：持续写盘 + 轻微停顿，务必设定 duration 并及时清理 .jfr 文件。",
                  "JVM 调优高危动作清单（只给指引，本工具不执行任何一条）")],
        standards=["[官方] OpenJDK 官网与各 JEP（JDK 8u262+ 开源 JFR、JEP 439/379 等）",
                   "[国际] Oracle Java SE 文档：GC Tuning Guide / JVM Flags 索引"],
        notes=["本任务的 action 是 manual 文本——它把「不该自动做的事」明确写出来。"],
        caveats=["任何 JVM 参数调整都应先在预发环境验证并观察 GC 日志。"],
    ),
]
