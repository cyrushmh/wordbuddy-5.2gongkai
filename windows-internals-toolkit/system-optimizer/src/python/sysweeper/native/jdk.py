"""OpenJDK / JVM 只读原生接口层（参照 OpenJDK 官方工程与 JEP 文档）。

「推进 openJDK」在本工具里的含义是**把 OpenJDK 当成一个被优化的对象**来体检，
而不是装 JDK 本身。和 Linux/Windows/macOS 那一层完全同构：按**它自己的规范与
接口**逐项只读核对，绝不套 dpkg/rpm 写法、也绝不写 JAVA_OPTS / jcmd 写命令。

覆盖的官方接口面（全部只读）：

- **运行时识别**：`java -version` / `javac -version` / `java -XshowSettings:properties`
  （vendor、build 版本、位数、VM 名称、class path、GC、JIT 相关系统属性）。
- **JPMS 模块系统（JDK 9+）**：`java --list-modules` / `--describe-module`，
  核对模块层是否完整、`java.se` 是否为根。
- **GC 家族**：`java -XX:+PrintFlagsFinal -version` 里 grep 出 UseG1GC/UseParallelGC/
  UseZGC/UseShenandoahGC/UseEpsilonGC 等，报告当前选中的收集器。
- **JIT 编译**：C1/C2 阈值（TieredCompilation、CompileThreshold）、内联上限。
- **JFR 飞行记录**：`jfr` 工具是否可用、`jcmd` 能否列出本机 JVM 进程
  （`jcmd -l` 只列进程，不 attach、不写）。
- **诊断命令面**：`jcmd` / `jfr` / `jstack` / `jmap` / `jstat` 是否存在，只列不改。

安全边界（三条硬约束）：

1. **只读**。只跑 `-version` / `--list-modules` / `-l` 这类查询命令。
   绝不跑 `jcmd <pid> GC.run`、`jmap -histo:live <pid>`（触发 full GC）、
   `jfr start`（挂录制）、`-XX:+PrintFlagsFinal` 之外带副作用的开关。
2. **绝不改系统环境**。不写 `JAVA_HOME`、不改 `JAVA_TOOL_OPTIONS`、
   不动 `~/.m2/settings.xml` / `~/.gradle/gradle.properties`。
3. **绝不打印敏感信息**。`-XshowSettings:properties` 会带出 classpath、
   可能的代理口令与 `java.home` 路径；本模块只挑**白名单键**输出，
   且对疑似含口令的键（password/token/secret/key）**只报存在性、不回显值**——
   与 openwrt 层的敏感键处理同一条底线。

未装 JDK 时全部返回 (False, 降级说明)，绝不抛异常。
"""

from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 文档层：OpenJDK 官方文档与工程引用
# --------------------------------------------------------------------------- #

_REFS: Dict[str, dict] = {
    "jdk": {
        "name": "OpenJDK（Open Java Development Kit）",
        "org": "OpenJDK 社区 / Oracle JDK（同一套规范两种构建）",
        "url": "https://openjdk.org/",
        "docs": [
            "OpenJDK 官网：https://openjdk.org/",
            "JDK 文档总入口：https://docs.oracle.com/en/java/javase/",
        ],
        "summary": ("OpenJDK 是 Java 平台的参考实现。JDK 8 及以前以「JRE + JDK」两件套"
                    "分发；JDK 9 起采用模块化运行时（JPMS），并以 LTS 每两年一版推进"
                    "（8/11/17/21/25）。本工具只做只读体检，不安装、不改 JAVA_HOME。"),
        "advice": ("体检只读运行 `java -version` 与 `-XshowSettings:properties -version`；"
                   "版本口令与本工具一致：命令行与本地开发用 LTS（17/21），"
                   "生产按上游支持周期选择。不在工具里改环境变量。"),
    },
    "jvm": {
        "name": "HotSpot JVM（虚拟机：运行时/JIT/GC 宿主）",
        "org": "OpenJDK / Oracle",
        "url": "https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html",
        "docs": [
            "JVM Spec（Java SE 规范，jvm 章节）",
            "HotSpot 源码：https://github.com/openjdk/jdk",
        ],
        "summary": ("JVM 抽象层之上，HotSpot 提供解释器 + C1/C2 两级 JIT 与多代 GC。"
                    "排查「慢」要先分清是编译不足、GC 压力还是内存不足。"),
        "advice": ("`java -XX:+PrintFlagsFinal -version` 可列全部 JVM 调优标志的最终生效值；"
                   "本工具只 grep 关键标志，不改任何标志值。"),
    },
    "jpms": {
        "name": "JPMS 模块系统（Java Platform Module System，JDK 9+）",
        "org": "OpenJDK / JEP 团队",
        "url": "https://openjdk.org/jeps/261",
        "docs": [
            "JEP 261: Module System（模块系统总纲）",
            "JEP 277: JDK 内部模块化（--add-exports/--add-opens 的由来）",
        ],
        "summary": ("JPMS 用 module-info.java 显式声明依赖，取代 classpath 的"
                    "「全都能看见」；并支持 jlink 按需裁剪出一个只含必要模块的运行时镜像，"
                    "显著压缩容器体积。"),
        "advice": ("`java --list-modules` 只读列出模块；排查 NoClassDefFoundError/IllegalAccessError "
                   "时先看模块层是否被封装。jlink 裁剪是写操作，本工具只给指引不做。"),
    },
    "gc": {
        "name": "GC 家族（G1 / Parallel / Z / Shenandoah / Epsilon）",
        "org": "OpenJDK",
        "url": "https://docs.oracle.com/en/java/javase/21/gctuning/index.html",
        "docs": [
            "GC Tuning Guide：https://docs.oracle.com/en/java/javase/21/gctuning/index.html",
            "JEP 439: Generational ZGC（JDK 21，ZGC 迈向分代）",
            "JEP 379: Shenandoah（低暂停收集器）",
        ],
        "summary": ("HotSpot 的收集器可在命令行用 -XX:+Use<Name>GC 选择；"
                    "JDK 9 起 G1 成为默认；JDK 21 起 ZGC 支持分代。"),
        "advice": ("本工具只读 `PrintFlagsFinal` 里各 Use*GC 的生效值并报告当前选中者，"
                   "不改任何 GC 参数。生产参数请以官方 GC Tuning Guide 为准。"),
    },
    "jit": {
        "name": "JIT 编译（C1 客户端 / C2 服务端两级）",
        "org": "OpenJDK",
        "url": "https://docs.oracle.com/en/java/javase/21/vm/compilation.html",
        "docs": [
            "JVM Spec 第 7 章：Code Generation",
            "JEP 165: Compiler Control（可动态开关编译）",
        ],
        "summary": ("分层编译下，热点方法先由 C1 快速编译（低码优化），"
                    "再由 C2 做激进优化；阈值由 CompileThreshold 控制。"),
        "advice": ("只读 TieredCompilation / CompileThreshold / MaxInlineSize 等标志的最终值，"
                   "用于判断「启动慢是解释器慢还是编译没跟上」。"),
    },
    "jfr": {
        "name": "JFR 飞行记录器（Java Flight Recorder）",
        "org": "OpenJDK",
        "url": "https://docs.oracle.com/en/java/javase/21/jfapi/index.html",
        "docs": [
            "JFR API 文档：https://docs.oracle.com/en/java/javase/21/jfapi/index.html",
            "jcmd JFR.start：https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html",
        ],
        "summary": ("JFR 是 JVM 内建低开销事件记录器（JDK 11+ 开源，JDK 8u262+ 回移植），"
                    "可记录 GC、锁竞争、IO、线程转储等，替代传统的 jstack 抓取。"),
        "advice": ("**开始/落盘录制属于写操作，本工具绝不做。** "
                   "这里只检查 `jfr`/`jcmd` 工具是否可用，以及 `jcmd -l` 能列出哪些 JVM 进程"
                   "（只列进程，不 attach、不 dump）。"),
    },
    "diagnostics": {
        "name": "诊断命令面（jcmd / jstack / jmap / jstat / jps）",
        "org": "OpenJDK",
        "url": "https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html",
        "docs": [
            "jcmd：https://docs.oracle.com/en/java/javase/21/docs/specs/man/jcmd.html",
            "jps  ：https://docs.oracle.com/en/java/javase/21/docs/specs/man/jps.html",
        ],
        "summary": ("这组工具对运行中的 JVM 做观测。jcmd 的查询子命令（VM.version、"
                    "GC.heap_info、Thread.print）只读；而 GC.run、VM.native_memory="
                    "baseline 等子命令有副作用。"),
        "advice": ("本工具只调用**查询型**动作：`jcmd -l`、`jcmd <pid> VM.version`、"
                   "`jps -l`。带 `GC.run`/`heap_dump`/`VM.set_flag` 的一律不给、不跑。"),
    },
}


def jdk_reference(key: str) -> dict:
    """返回某 OpenJDK 主题的官方文档参考。"""
    return _REFS.get(key, {})


def jdk_reference_all() -> dict:
    """返回全部 OpenJDK 主题文档参考。"""
    return _REFS


def jdk_doc_list() -> List[str]:
    """返回 OpenJDK 文档引用清单（纯文本行），供 CLI/GUI 展示。"""
    out: List[str] = []
    for key, ref in _REFS.items():
        out.append(f"· {key} — {ref.get('name', '')}")
        out.append(f"    归属: {ref.get('org', '')}")
        out.append(f"    入口: {ref.get('url', '')}")
        for d in ref.get("docs", []):
            out.append(f"    文档: {d}")
        out.append(f"    摘要: {ref.get('summary', '')}")
        out.append(f"    建议: {ref.get('advice', '')}")
    return out


# --------------------------------------------------------------------------- #
# 敏感键白名单处理：只报存在性，不回显值
#
# `java -XshowSettings:properties` 会把所有系统属性打出来，其中可能混有
# 代理口令（http.proxyPassword）、令牌、以及带凭据的 URL 拼接串。
# 我们**只输出白名单键**，其余一律不出现——从源头避免泄漏。
# --------------------------------------------------------------------------- #

#: 允许原样输出的 -XshowSettings:properties 键（白名单）
_PROPS_ALLOW = (
    "java.version", "java.vendor", "java.vendor.url", "java.home",
    "java.class.version", "java.class.path", "java.specification.version",
    "java.vm.name", "java.vm.version", "java.vm.vendor", "java.vm.info",
    "java.runtime.name", "java.runtime.version", "java.vm.specification.version",
    "os.name", "os.arch", "os.version",
    "java.io.tmpdir", "user.language", "user.country", "user.timezone",
    "sun.arch.data.model", "sun.jnu.encoding", "file.encoding",
    "native.encoding", "stdout.encoding", "java.awt.headless",
)

#: 命中即视为敏感（只报「存在」，绝不回显值）
_PROPS_SECRET_HINTS = ("password", "passwd", "secret", "token", "credential",
                       "apikey", "api.key", "auth", "passphrase")

#: 允许的 key 命名空间（与仓库其他模块的 key 规则一致：[a-z0-9][a-z0-9_.-]{1,63}）
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")


# --------------------------------------------------------------------------- #
# 运行时识别
# --------------------------------------------------------------------------- #

def java_home() -> str:
    """返回 JAVA_HOME 环境变量的值（未设返回空串）。只读。"""
    return os.environ.get("JAVA_HOME", "").strip()


def java_bin() -> str:
    """返回可用的 java 解释器路径；找不到返回空串。"""
    return shutil.which("java") or ""


def javac_bin() -> str:
    """返回可用的 javac 编译器路径；找不到返回空串（JRE-only 发行版没有）。"""
    return shutil.which("javac") or ""


def java_version() -> Tuple[bool, str]:
    """读 `java -version`（只读，输出走 stderr，所以 common.run 已合并）。"""
    if not java_bin():
        return False, ("未找到 java（JDK 未安装或不在 PATH）；"
                       "如需体检请先安装 OpenJDK LTS 17/21（降级为文档指引）")
    rc, out = common.run("java -version", timeout=60)
    if rc != 0 or not (out or "").strip():
        return False, (out or "java -version 无输出").strip()[:200]
    return True, out.strip()


def javac_version() -> Tuple[bool, str]:
    """读 `javac -version`（只读）。JRE-only 发行版无 javac，属正常降级。"""
    if not java_bin():
        return False, "未找到 java（JDK 未安装或不在 PATH）"
    if not javac_bin():
        return True, ("未找到 javac（当前是 JRE-only 发行版或只装了运行时；"
                      "编译类体检项将降级，运行时体检不受影响）")
    rc, out = common.run("javac -version", timeout=60)
    if rc != 0 or not (out or "").strip():
        return False, (out or "javac -version 无输出").strip()[:200]
    return True, out.strip()


def java_runtime_report() -> tuple:
    """运行时总览：java 版本 / JAVA_HOME / javac / 架构（只读）。"""
    if not java_bin():
        return False, ("未找到 java（JDK 未安装或不在 PATH）；"
                       "本工具不安装 JDK，只在已有 JDK 时做只读体检（降级为文档指引）")
    ok, ver = java_version()
    if not ok:
        return False, ver
    okc, verc = javac_version()
    arch = common.run("java -XshowSettings:properties -version 2>&1 | "
                      "grep -E '^\\s*(os.arch|sun.arch.data.model) ='", timeout=90)
    home = java_home() or "(未设 JAVA_HOME，由 PATH 定位)"
    lines = [f"JDK 运行时（{java_bin()}）：",
             "  " + ver.replace("\n", "\n  ")]
    lines.append(f"   javac: {verc if okc else '不可用'}"
                 if okc else f"   javac: 不可用（{verc}）")
    lines.append(f"   JAVA_HOME: {home}")
    if (arch[1] or "").strip():
        lines.append("   " + arch[1].strip().replace("\n", "\n   "))
    return True, "\n".join(lines)


def java_properties_report() -> tuple:
    """读 `java -XshowSettings:properties` 的**白名单键**（只读，敏感键不回显）。

    这是本模块安全设计的核心：不整段 dump 属性表，只挑 30 余个无害键输出。
    """
    if not java_bin():
        return False, "未找到 java，无法读系统属性（降级为文档指引）"
    rc, out = common.run("java -XshowSettings:properties -version 2>&1",
                         timeout=120, tail=0)
    if rc != 0 or not (out or "").strip():
        return False, (out or "-XshowSettings 无输出").strip()[:200]
    lines = ["java 系统属性（仅白名单键；口令/令牌类一律不回显）："]
    found = 0
    for raw in out.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.]+)\s*=\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        low = key.lower()
        if any(h in low for h in _PROPS_SECRET_HINTS):
            # 只报存在性，绝不回显值——与 OpenWrt 层的敏感键同一条底线
            if val and val.lower() not in ("null", ""):
                lines.append(f"   · {key} = <存在敏感值，已隐藏>")
            continue
        if key not in _PROPS_ALLOW:
            continue
        found += 1
        # 属性值可能自带换行/超长，截断防炸
        lines.append(f"   · {key} = {val[:120]}")
    if found == 0:
        lines.append("   · 未匹配到白名单键（该发行版属性集与预期不同）")
    else:
        lines.append(f"   （共输出 {found} 个白名单键；非白名单键一律不打印，"
                     "以免泄漏代理口令/令牌/带凭据路径）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# JPMS 模块系统（JDK 9+）
# --------------------------------------------------------------------------- #

def modules_report() -> tuple:
    """读 JPMS 模块清单（`java --list-modules`，只读）。JDK 8 无此能力，正常降级。"""
    if not java_bin():
        return False, "未找到 java，无法列模块（降级为文档指引）"
    ok, ver = java_version()
    if not ok:
        return False, ver
    rc, out = common.run("java --list-modules 2>&1", timeout=120, tail=0)
    if rc != 0 or not (out or "").strip():
        return False, ("java --list-modules 无输出——JDK 8 及以前无 JPMS 模块系统，"
                       "属预期降级（JDK 9+ 起才有）")
    mods = [l.strip() for l in out.splitlines() if l.strip()]
    java_se = [m for m in mods if m.startswith("java.se")]
    lines = [f"JPMS 模块系统（java --list-modules，只读）：共 {len(mods)} 个模块"]
    if java_se:
        lines.append(f"   · 根聚合模块: {', '.join(java_se)}")
    else:
        lines.append("   · 未见 java.se 根聚合模块（精简运行时镜像可能已裁剪）")
    # 归类统计，让清单可读
    buckets: Dict[str, List[str]] = {}
    for m in mods:
        top = m.split(".")[0].split("@")[0]
        buckets.setdefault(top, []).append(m)
    for top in sorted(buckets, key=lambda k: -len(buckets[k]))[:8]:
        lines.append(f"   · {top}.* {len(buckets[top])} 个")
    lines.append("   · 裁剪运行时镜像用 jlink（属写操作，本工具只给指引不做）")
    return True, "\n".join(lines)


def module_describe_report() -> tuple:
    """读 `java --describe-module java.se`（只读，看核心模块导出与 requires）。"""
    if not java_bin():
        return False, "未找到 java（降级为文档指引）"
    rc, out = common.run("java --describe-module java.se 2>&1 | head -24", timeout=120)
    if rc != 0 or not (out or "").strip():
        return False, ("--describe-module 无输出（JDK 8 无 JPMS，"
                       "或该镜像未含 java.se，属预期降级）")
    lines = ["java.se 模块描述（只读，看导出面与依赖面）："]
    for l in out.splitlines()[:24]:
        if l.strip():
            lines.append("   " + l.rstrip())
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# GC / JIT 标志（只读 PrintFlagsFinal）
# --------------------------------------------------------------------------- #

#: 关注的 GC 标志 → 中文名
_GC_FLAGS = (
    ("UseG1GC", "G1（JDK 9+ 默认，分Region 低暂停）"),
    ("UseParallelGC", "Parallel Scavenge（吞吐优先）"),
    ("UseSerialGC", "Serial（单线程，嵌入式/小堆）"),
    ("UseZGC", "ZGC（超低暂停，JDK 11+ 引入 / 21 分代）"),
    ("UseShenandoahGC", "Shenandoah（低暂停，吞吐略让）"),
    ("UseEpsilonGC", "Epsilon（只分配不回收，JDK 15+，测试用）"),
)

#: 关注的 JIT 标志 → 中文名
_JIT_FLAGS = (
    ("TieredCompilation", "分层编译（C1→C2 两级）"),
    ("CompileThreshold", "触发 C2 编译的调用/回边阈值"),
    ("Tier3InvocationThreshold", "C1 三级调用阈值"),
    ("MaxInlineSize", "方法内联体积上限（字节）"),
    ("FreqInlineSize", "热点方法内联体积上限（字节）"),
    ("UseCompressedOops", "压缩指针（堆 < 32G 时省内存）"),
    ("UseCompressedClassPointers", "压缩类指针"),
)


def _flags(final: bool = True) -> Tuple[bool, List[Tuple[str, str]]]:
    """内部：`java -XX:+PrintFlagsFinal -version` 解析成 [(flag, value)]。

    `PrintFlagsFinal` 是**只打印标志最终值**的诊断开关，不修改任何运行时状态，
    JVM 执行完即退出，属纯只读。
    """
    if not java_bin():
        return False, []
    # tail=0：PrintFlagsFinal 约 800+ 行，截尾会把关键标志切掉，故要完整输出
    rc, out = common.run("java -XX:+PrintFlagsFinal -version 2>&1",
                         timeout=150, tail=0)
    if rc != 0 or not (out or "").strip():
        return False, []
    pairs: List[Tuple[str, str]] = []
    for raw in out.splitlines():
        # 实际输出形如：
        #   "     bool UseG1GC            = true    {product} {ergonomic}"
        #   "      int Foo                = -1      {product} {default}"
        # 故需先跳过行首的类型前缀（bool/int/uintx/ccstr/...），再取 flag 名与值。
        m = re.match(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*\s+)?([A-Za-z][A-Za-z0-9_]*)\s*"
                     r"=\s*(\{[^}]*\}|\S+)", raw)
        if m:
            pairs.append((m.group(1), m.group(2)))
    if not pairs:
        return False, []
    return True, pairs


def gc_report() -> tuple:
    """读当前生效的 GC（只读 PrintFlagsFinal 里各 Use*GC 的值）。"""
    if not java_bin():
        return False, "未找到 java，无法读 GC 标志（降级为文档指引）"
    ok, pairs = _flags()
    if not ok:
        return False, ("PrintFlagsFinal 无输出或该发行版禁用了诊断标志"
                       "（降级为文档指引）")
    d = dict(pairs)
    lines = ["垃圾收集器（java -XX:+PrintFlagsFinal，只读不修改）："]
    chosen = []
    for flag, name in _GC_FLAGS:
        if flag in d:
            on = d[flag] == "true"
            lines.append(f"   · {flag:<18} = {d[flag]:<6} {name}")
            if on:
                chosen.append(name.split("（")[0])
    if chosen:
        lines.append(f"   → 当前生效: {' + '.join(chosen)}"
                     "（若多开同时为 true，HotSpot 会按固定优先级选一个）")
    else:
        lines.append("   → 未显式开启任何非默认收集器：JDK 9+ 默认 G1，"
                     "JDK 8 默认 Parallel GC")
    lines.append("   · 本工具只读最终值；调 GC 参数请以官方 GC Tuning Guide 为准")
    return True, "\n".join(lines)


def jit_report() -> tuple:
    """读 JIT 分层编译与内联阈值（只读）。用于判断「启动慢」是编译没跟上。"""
    if not java_bin():
        return False, "未找到 java，无法读 JIT 标志（降级为文档指引）"
    ok, pairs = _flags()
    if not ok:
        return False, "PrintFlagsFinal 无输出（降级为文档指引）"
    d = dict(pairs)
    lines = ["JIT 编译（java -XX:+PrintFlagsFinal，只读不修改）："]
    for flag, name in _JIT_FLAGS:
        if flag in d:
            lines.append(f"   · {flag:<26} = {d[flag]:<8} {name}")
    tiered = d.get("TieredCompilation", "?")
    lines.append("   · 分层编译关闭时（TieredCompilation=false）只有解释器 + C2，"
                 "冷启动会明显更慢；这通常就是「刚启动就慢、跑一会儿就快」的原因")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 诊断工具面（JFR / jcmd / jstack / jmap / jstat / jps）——只列不改
# --------------------------------------------------------------------------- #

#: 诊断工具清单：(可执行名, 中文说明, 是否查询型)
DIAG_TOOLS = (
    ("jcmd", "对运行中 JVM 发命令（本工具只用查询型：-l / VM.version）", True),
    ("jps", "列出本机 JVM 进程与主类（-l 只读）", True),
    ("jstack", "线程转储（会 attach 并短暂停顿，不在本工具默认动作里）", False),
    ("jmap", "内存映射/直方图（-histo:live 触发 full GC，本工具不跑）", False),
    ("jstat", "性能采样（jstat -gc 周期采样，只读但需持续观察）", True),
    ("jfr", "飞行记录器（JDK 11+；start/dump 属写操作，本工具不跑）", False),
)

#: 明确不执行的高副作用子命令（文档化禁令，防止后续误加）
FORBIDDEN_SUBCOMMANDS = (
    "jcmd <pid> GC.run        # 主动触发 full GC，会造成长时间停顿",
    "jcmd <pid> heap_dump     # 生成堆转储文件（写盘，体积可达 GB）",
    "jmap -histo:live <pid>   # :live 会强制 full GC",
    "jfr start / jfr dump     # 挂载/落盘 JFR 录制（持续写盘）",
    "jcmd <pid> JFR.start     # 启动 JFR 录制（持续写盘 + 轻微停顿）",
    "jcmd <pid> VM.set_flag   # 运行期改标志（等价于热改生产参数）",
    "java -XX:+Use<Name>GC    # 本工具只读 PrintFlagsFinal，不带任何 GC 选择参数启动",
)


def diag_tools_report() -> tuple:
    """列出 OpenJDK 诊断工具可用性（只读：只查 PATH，不执行任何子命令）。"""
    if not java_bin():
        return False, ("未找到 java（JDK 未安装）；以下仅为 OpenJDK 工具面说明"
                       "（降级为文档指引）")
    lines = ["OpenJDK 诊断工具可用性（只查 PATH，不执行子命令）："]
    hit = 0
    for name, desc, safe in DIAG_TOOLS:
        p = shutil.which(name)
        lines.append(f"   {'✓' if p else '✗'} {name:<7} {'可用' if p else '未找到'}"
                     f"（{'查询型' if safe else '有副作用，本工具不跑'}）— {desc}")
        if p:
            hit += 1
    lines.append(f"   小结：{hit}/{len(DIAG_TOOLS)} 个工具在 PATH 中")
    return True, "\n".join(lines)


def jvm_processes_report() -> tuple:
    """列本机运行中的 JVM 进程（只读 `jps -l` / `jcmd -l`）。

    只列进程名与主类/参数，**不 attach、不 dump、不设标志**。这层对「有没有东西在
    偷偷跑 JVM」这一诉求（内存占用排查）有直接价值。
    """
    if not java_bin():
        return False, "未找到 java，无法列 JVM 进程（降级为文档指引）"
    lines = ["本机运行中的 JVM 进程（jps -l / jcmd -l，只读不 attach）："]
    got = False
    jps = shutil.which("jps")
    if jps:
        rc, out = common.run("jps -l 2>&1", timeout=90)
        if rc == 0 and (out or "").strip():
            got = True
            lines.append("   jps -l:")
            for l in out.splitlines():
                if l.strip() and l.strip().split()[0].isdigit():
                    lines.append("   " + l.rstrip()[:140])
    jcmd = shutil.which("jcmd")
    if jcmd:
        rc, out = common.run("jcmd -l 2>&1", timeout=90)
        if rc == 0 and (out or "").strip():
            got = True
            lines.append("   jcmd -l:")
            for l in out.splitlines():
                if l.strip():
                    lines.append("   " + l.rstrip()[:140])
    if not got:
        lines.append("   · jps/jcmd 不可用或无输出（多为无 JVM 在跑，"
                     "或与运行中的 JVM 属不同用户，属正常）")
    else:
        lines.append("   · 只列进程信息；本工具不发任何 jcmd 变更类子命令")
    return True, "\n".join(lines)


def jfr_capability_report() -> tuple:
    """读 JFR 能力可用性（只读查工具与版本；不 start、不 dump）。"""
    if not java_bin():
        return False, "未找到 java（JDK 未安装），无法核对 JFR（降级为文档指引）"
    ok, ver = java_version()
    lines = ["JFR 飞行记录器能力（只读核对，不录制）："]
    lines.append("   " + (ver.replace("\n", "\n   ") if ok else ver))
    # JDK 11 开源 JFR；JDK 8u262+ 回移植。故以 major 版本粗判并明说不精确
    major = 0
    m = re.search(r'version "(\d+)', ver or "")
    if m:
        try:
            major = int(m.group(1))
        except ValueError:
            major = 0
    if major == 0:
        lines.append("   · 版本号解析失败，无法判断 JFR 可用性（不猜）")
    elif major >= 11:
        lines.append(f"   · JDK {major}：JFR 官方开源可用（jdk.jfr 模块），"
                     "`jfr` 工具随 JDK 分发")
    elif major == 8:
        lines.append("   · JDK 8：JFR 自 8u262 起回移植；更早的 8u 无 JFR")
    else:
        lines.append(f"   · JDK {major}：介于两者之间，"
                     "请以 `jfr --version` 实测为准（只读命令）")
    p = shutil.which("jfr")
    lines.append(f"   · jfr 工具：{'可用 ' + p if p else '未在 PATH（随 JDK 完整安装才有）'}")
    lines.append("   · 录制属于写操作（持续写盘 + 可致停顿），本工具只给指引不做；"
                 "用法：`jcmd <pid> JFR.start name=x duration=60s filename=a.jfr` 后 `jfr print a.jfr`")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 构建/依赖工具面（Gradle / Maven）——只查存在与缓存体积，不动依赖图
# --------------------------------------------------------------------------- #

#: 构建工具 → 缓存目录（相对 HOME）
_BUILD_CACHE = (
    ("Gradle", os.path.join("~", ".gradle", "caches"),
     "构建脚本编译与依赖缓存；`gradle --stop` 可停守护进程（属写操作，仅指引）"),
    ("Maven", os.path.join("~", ".m2", "repository"),
     "本地仓库 jar 缓存；`mvn dependency:purge-local-repository` 可清理（仅指引）"),
)


def build_tool_cache_report() -> tuple:
    """统计 Gradle / Maven 缓存体积（只读遍历，不删任何文件）。"""
    lines = ["Java 构建工具缓存体积（只读统计，不删文件）："]
    got = False
    for name, rel, note in _BUILD_CACHE:
        path = os.path.expanduser(rel)
        tools = " / ".join(t for t in ("gradle", "mvn") if shutil.which(t)) or "未在 PATH"
        if not os.path.isdir(path):
            lines.append(f"   · {name} 缓存: 不存在（{rel}）— 工具: {tools}")
            continue
        got = True
        size = common.list_dir_size(path)
        lines.append(f"   · {name} 缓存: {common.human(size) if size else '无法读取'}"
                     f"（{rel}）— 工具: {tools}")
        lines.append(f"       {note}")
    if not got:
        lines.append("   · 未发现任何 Java 构建缓存目录（无 Gradle/Maven 本地缓存）")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 聚合入口
# --------------------------------------------------------------------------- #

#: 只读探针清单：(函数名, 中文标签, 是否需 java 可执行)
JDK_PROBES = (
    ("java_runtime_report", "运行时总览（java -version / JAVA_HOME / javac）", True),
    ("java_properties_report", "系统属性（白名单键，敏感键不回显）", True),
    ("modules_report", "JPMS 模块清单（java --list-modules）", True),
    ("module_describe_report", "java.se 模块描述（导出面/依赖面）", True),
    ("gc_report", "垃圾收集器（PrintFlagsFinal，只读）", True),
    ("jit_report", "JIT 分层编译与内联阈值（只读）", True),
    ("diag_tools_report", "诊断工具面（jcmd/jps/jstack/jmap/jstat/jfr）", True),
    ("jvm_processes_report", "本机 JVM 进程（jps -l / jcmd -l，只读）", True),
    ("jfr_capability_report", "JFR 能力可用性（只查不录制）", True),
    ("build_tool_cache_report", "Gradle / Maven 缓存体积（只读统计）", False),
)


def jdk_report() -> tuple:
    """OpenJDK 体检总报告：逐项只读探测 + 汇总。

    任一项成功即视为整体可用；全部失败（多半是没装 JDK）时返回降级说明。
    """
    if not java_bin():
        return False, ("未找到 java（JDK 未安装或不在 PATH）。本工具**不安装 JDK**，"
                       "只做只读体检——请自行安装 OpenJDK LTS 后重试"
                       "（当前降级为文档指引，文档层仍可用 `java -k docs` 风格参考）")
    head = [f"OpenJDK 只读体检总报告（java = {java_bin()}）："]
    okc = 0
    for fn_name, label, _need in JDK_PROBES:
        ok, msg = globals()[fn_name]()
        head.append("")
        head.append(f"-- {label} --")
        head.append(msg if ok else f"（不适用）{msg}")
        if ok:
            okc += 1
    head.append("")
    head.append(f"小结：{len(JDK_PROBES)} 项只读体检中 {okc} 项可读。"
                "全部动作只读：不改 JAVA_HOME、不改任何 JVM 标志、不录制 JFR、"
                "不 attach 任何进程。")
    return True, "\n".join(head)


def environment_report() -> List[str]:
    """返回本机 OpenJDK 接口可用性概览（✓ 可用 / ✗ 未装/降级）。"""
    lines = ["OpenJDK 只读接口可用性："]
    for fn_name, label, _need in JDK_PROBES:
        ok, msg = globals()[fn_name]()
        lines.append(f"   {'✓' if ok else '✗'} {label}")
        if not ok:
            lines.append(f"       {msg}")
    return lines


__all__ = [
    # 文档层
    "jdk_reference", "jdk_reference_all", "jdk_doc_list", "_REFS",
    # 基础识别
    "java_home", "java_bin", "javac_bin", "java_version", "javac_version",
    # 只读报告
    "java_runtime_report", "java_properties_report",
    "modules_report", "module_describe_report",
    "gc_report", "jit_report",
    "diag_tools_report", "jvm_processes_report", "jfr_capability_report",
    "build_tool_cache_report",
    # 聚合
    "jdk_report", "environment_report",
    # 常量
    "JDK_PROBES", "DIAG_TOOLS", "FORBIDDEN_SUBCOMMANDS",
    "_GC_FLAGS", "_JIT_FLAGS", "_BUILD_CACHE",
    "_PROPS_ALLOW", "_PROPS_SECRET_HINTS", "_KEY_RE",
]
