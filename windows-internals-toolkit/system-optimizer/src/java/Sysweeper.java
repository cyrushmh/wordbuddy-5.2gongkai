/*
 * sysweeper-java — system-optimizer 的 Java 侧命令行组件。
 *
 * 目标：让同一套「只读诊断」口径在有 JVM 的环境也能查询，
 * 便于企业/服务器场景（JDK 预装）下使用。
 *
 * 设计原则与 Python/Go/C 侧一致：
 *   - 纯 JDK 标准库，零第三方依赖；
 *   - 只读探测，异常一律降级提示，不 throw 到用户端；
 *   - 红线：不启停服务、不改配置、不连控制端口。
 *
 * 用法:
 *   java Sysweeper version        版本信息
 *   java Sysweeper sysinfo        系统信息（JVM / 内存 / CPU）
 *   java Sysweeper jdk            JDK 环境诊断
 *   java Sysweeper help           帮助
 *
 * 编译:
 *   javac Sysweeper.java
 */

import java.lang.management.ManagementFactory;
import java.lang.management.RuntimeMXBean;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class Sysweeper {

    static final String VERSION = "0.6.40";

    static void printVersion() {
        System.out.println("sysweeper-java " + VERSION);
        System.out.println("  JVM: " + System.getProperty("java.vm.name"));
        System.out.println("  Java: " + System.getProperty("java.version"));
        System.out.println("  Vendor: " + System.getProperty("java.vendor"));
        System.out.println("  OS: " + System.getProperty("os.name") + " " + System.getProperty("os.arch"));
    }

    static void printSysinfo() {
        System.out.println("=== sysweeper-java 系统信息（只读） ===\n");

        // --- JVM 内存 ---
        Runtime rt = Runtime.getRuntime();
        long maxMB = rt.maxMemory() / (1024 * 1024);
        long totalMB = rt.totalMemory() / (1024 * 1024);
        long freeMB = rt.freeMemory() / (1024 * 1024);
        long usedMB = totalMB - freeMB;
        System.out.println("  JVM 最大堆: " + maxMB + " MB");
        System.out.println("  JVM 已分配: " + totalMB + " MB");
        System.out.println("  JVM 已使用: " + usedMB + " MB");

        // --- CPU ---
        int ncpu = rt.availableProcessors();
        System.out.println("  CPU 核数: " + ncpu);

        // --- OS ---
        System.out.println("  操作系统: " + System.getProperty("os.name") + " " + System.getProperty("os.version"));
        System.out.println("  架构: " + System.getProperty("os.arch"));
        System.out.println("  用户: " + System.getProperty("user.name"));
        System.out.println("  工作目录: " + System.getProperty("user.dir"));

        // --- JVM 运行时参数 ---
        RuntimeMXBean rmb = ManagementFactory.getRuntimeMXBean();
        System.out.println("  JVM PID: " + rmb.getPid());
        System.out.println("  JVM 启动时间: " + new java.util.Date(rmb.getStartTime()));

        System.out.println("\n  红线：只读探测，不修改任何系统状态。");
    }

    static void printJdk() {
        System.out.println("=== sysweeper-java JDK 诊断（只读） ===\n");

        // --- JDK 版本 ---
        System.out.println("  java.version: " + System.getProperty("java.version"));
        System.out.println("  java.vm.version: " + System.getProperty("java.vm.version"));
        System.out.println("  java.vm.name: " + System.getProperty("java.vm.name"));
        System.out.println("  java.home: " + System.getProperty("java.home"));
        System.out.println("  java.vendor: " + System.getProperty("java.vendor"));

        // --- classpath ---
        String cp = System.getProperty("java.class.path");
        System.out.println("  classpath: " + cp);

        // --- 关键目录存在性 ---
        String javaHome = System.getProperty("java.home");
        Path javacPath = Paths.get(javaHome, "bin", "javac");
        String javacName = System.getProperty("os.name").toLowerCase().startsWith("win") ? "javac.exe" : "javac";
        Path javacPath2 = Paths.get(javaHome, "bin", javacName);

        System.out.println("  javac 存在: " + (Files.exists(javacPath) || Files.exists(javacPath2)));

        // --- JIT 编译器 ---
        String jit = System.getProperty("java.compiler", "(未知)");
        System.out.println("  JIT 编译器: " + jit);

        // --- GC ---
        String gcName = ManagementFactory.getGarbageCollectorMXBeans().stream()
                .map(b -> b.getName())
                .reduce((a, b) -> a + ", " + b)
                .orElse("(未知)");
        System.out.println("  GC: " + gcName);

        // --- 系统属性摘要 ---
        System.out.println("\n  关键系统属性:");
        String[] keys = {"file.encoding", "file.separator", "line.separator",
                         "user.timezone", "user.language", "user.country"};
        for (String k : keys) {
            System.out.println("    " + k + " = " + System.getProperty(k, "(未设置)"));
        }

        System.out.println("\n  红线：只读诊断，不启停服务、不改配置。");
    }

    static void printUsage() {
        System.out.println("用法: java Sysweeper <子命令>\n");
        System.out.println("子命令:");
        System.out.println("  version     版本信息");
        System.out.println("  sysinfo     系统信息（JVM 内存 / CPU / OS）");
        System.out.println("  jdk         JDK 环境诊断（版本 / 路径 / GC / JIT）");
        System.out.println("  help        帮助\n");
        System.out.println("示例:");
        System.out.println("  java Sysweeper version");
        System.out.println("  java Sysweeper sysinfo");
        System.out.println("  java Sysweeper jdk");
        System.out.println("\n编译: javac Sysweeper.java");
    }

    public static void main(String[] args) {
        if (args.length < 1) {
            printUsage();
            System.exit(2);
        }

        String cmd = args[0];
        switch (cmd) {
            case "version":
            case "-v":
            case "--version":
                printVersion();
                break;
            case "sysinfo":
            case "info":
                printSysinfo();
                break;
            case "jdk":
                printJdk();
                break;
            case "help":
            case "-h":
            case "--help":
                printUsage();
                break;
            default:
                System.err.println("未知子命令: " + cmd + "\n");
                printUsage();
                System.exit(2);
        }
    }
}
