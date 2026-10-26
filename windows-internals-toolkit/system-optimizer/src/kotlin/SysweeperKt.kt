/*
 * sysweeper-kotlin — system-optimizer 的 Kotlin 侧命令行组件。
 *
 * 目标：让同一套「只读诊断」口径在有 JVM 的环境也能查询，
 * 便于企业/服务器场景（Kotlin 预装）下使用。
 *
 * 设计原则与 Python/Go/C/Java 侧一致：
 *   - 纯 Kotlin/JVM 标准库，零第三方依赖；
 *   - 只读探测，异常一律降级提示，不 throw 到用户端；
 *   - 红线：不启停服务、不改配置、不连控制端口。
 *
 * 用法:
 *   java -jar sysweeper-kotlin.jar version     版本信息
 *   java -jar sysweeper-kotlin.jar sysinfo     系统信息（JVM / 内存 / CPU）
 *   java -jar sysweeper-kotlin.jar help        帮助
 *
 * 编译:
 *   kotlinc SysweeperKt.kt -include-runtime -d sysweeper-kotlin.jar
 */

import java.lang.management.ManagementFactory
import java.nio.file.Files
import java.nio.file.Paths

const val VERSION = "0.6.40"

fun printVersion() {
    println("sysweeper-kotlin $VERSION")
    println("  JVM: ${System.getProperty("java.vm.name")}")
    println("  Java: ${System.getProperty("java.version")}")
    println("  Kotlin: ${KotlinVersion.CURRENT}")
    println("  Vendor: ${System.getProperty("java.vendor")}")
    println("  OS: ${System.getProperty("os.name")} ${System.getProperty("os.arch")}")
}

fun printSysinfo() {
    println("=== sysweeper-kotlin 系统信息（只读） ===\n")

    val rt = Runtime.getRuntime()
    val maxMB = rt.maxMemory() / (1024 * 1024)
    val totalMB = rt.totalMemory() / (1024 * 1024)
    val freeMB = rt.freeMemory() / (1024 * 1024)
    val usedMB = totalMB - freeMB
    println("  JVM 最大堆: $maxMB MB")
    println("  JVM 已分配: $totalMB MB")
    println("  JVM 已使用: $usedMB MB")

    val ncpu = rt.availableProcessors()
    println("  CPU 核数: $ncpu")

    println("  操作系统: ${System.getProperty("os.name")} ${System.getProperty("os.version")}")
    println("  架构: ${System.getProperty("os.arch")}")
    println("  用户: ${System.getProperty("user.name")}")
    println("  工作目录: ${System.getProperty("user.dir")}")

    val rmb = ManagementFactory.getRuntimeMXBean()
    println("  JVM PID: ${rmb.pid}")
    println("  JVM 启动时间: ${java.util.Date(rmb.startTime)}")

    // GC 信息
    val gcName = ManagementFactory.getGarbageCollectorMXBeans().joinToString(", ") { it.name }
    println("  GC: $gcName")

    println("\n  红线：只读探测，不修改任何系统状态。")
}

fun printUsage() {
    println("用法: java -jar sysweeper-kotlin.jar <子命令>\n")
    println("子命令:")
    println("  version     版本信息")
    println("  sysinfo     系统信息（JVM 内存 / CPU / OS）")
    println("  help        帮助\n")
    println("示例:")
    println("  java -jar sysweeper-kotlin.jar version")
    println("  java -jar sysweeper-kotlin.jar sysinfo")
    println("\n编译: kotlinc SysweeperKt.kt -include-runtime -d sysweeper-kotlin.jar")
}

fun main(args: Array<String>) {
    if (args.isEmpty()) {
        printUsage()
        kotlin.system.exitProcess(2)
    }

    when (args[0]) {
        "version", "-v", "--version" -> printVersion()
        "sysinfo", "info" -> printSysinfo()
        "help", "-h", "--help" -> printUsage()
        else -> {
            System.err.println("未知子命令: ${args[0]}\n")
            printUsage()
            kotlin.system.exitProcess(2)
        }
    }
}
