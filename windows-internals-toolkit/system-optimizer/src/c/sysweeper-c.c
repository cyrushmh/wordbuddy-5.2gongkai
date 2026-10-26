/*
 * sysweeper-c — system-optimizer 的 C 侧命令行组件。
 *
 * 目标：让同一套「只读诊断」口径不依赖 Python/Go 运行时也能查询，
 * 便于嵌入式/最小系统（仅有 gcc + libc）下使用。
 *
 * 设计原则与 Python/Go 侧一致：
 *   - 纯标准库（libc），零第三方依赖；
 *   - 只读探测，命令缺失/执行失败一律降级提示，不 abort；
 *   - 标准引用按受众分层。
 *
 * 用法:
 *   sysweeper-c version          版本信息
 *   sysweeper-c sysinfo         系统信息（uname / 内存 / CPU）
 *   sysweeper-c help            帮助
 *
 * 编译:
 *   cc -std=c11 -Wall -Wextra -O2 -o sysweeper-c sysweeper-c.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __linux__
  #include <sys/utsname.h>
  #include <sys/sysinfo.h>
  #include <unistd.h>
#elif defined(__APPLE__)
  #include <sys/utsname.h>
  #include <unistd.h>
  #include <mach/mach.h>
#elif defined(_WIN32)
  #include <windows.h>
  #include <sysinfoapi.h>
#endif

#define VERSION "0.6.40"

static void print_version(void) {
    printf("sysweeper-c %s\n", VERSION);
#if defined(__linux__)
    printf("  platform: Linux (C)\n");
#elif defined(__APPLE__)
    printf("  platform: macOS (C)\n");
#elif defined(_WIN32)
    printf("  platform: Windows (C)\n");
#else
    printf("  platform: Unknown (C)\n");
#endif
    printf("  compiler: %s\n",
#ifdef __GNUC__
           "GCC " __VERSION__
#else
           "unknown"
#endif
    );
}

static void print_sysinfo(void) {
    printf("=== sysweeper-c 系统信息（只读） ===\n\n");

    /* --- uname --- */
#ifdef __linux__
    struct utsname uts;
    if (uname(&uts) == 0) {
        printf("  内核:     %s %s\n", uts.sysname, uts.release);
        printf("  主机名:   %s\n", uts.nodename);
        printf("  架构:     %s\n", uts.machine);
        printf("  版本:     %s\n", uts.version);
    } else {
        printf("  uname:    失败\n");
    }

    /* --- 内存 --- */
    struct sysinfo si;
    if (sysinfo(&si) == 0) {
        unsigned long total_mb = si.totalram * (unsigned long)si.mem_unit / (1024 * 1024);
        unsigned long free_mb = si.freeram * (unsigned long)si.mem_unit / (1024 * 1024);
        printf("  内存总量: %lu MB\n", total_mb);
        printf("  内存可用: %lu MB\n", free_mb);
        printf("  交换总量: %lu MB\n",
               si.totalswap * (unsigned long)si.mem_unit / (1024 * 1024));
    } else {
        printf("  sysinfo:  失败\n");
    }

    /* --- CPU --- */
    long ncpu = sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu > 0) {
        printf("  CPU 核数: %ld\n", ncpu);
    }

    /* --- uptime --- */
    if (sysinfo(&si) == 0) {
        unsigned long days = si.uptime / 86400;
        unsigned long hours = (si.uptime % 86400) / 3600;
        unsigned long mins = (si.uptime % 3600) / 60;
        printf("  运行时间: %lu天 %lu时 %lu分\n", days, hours, mins);
    }

#elif defined(__APPLE__)
    struct utsname uts;
    if (uname(&uts) == 0) {
        printf("  内核:     %s %s\n", uts.sysname, uts.release);
        printf("  主机名:   %s\n", uts.nodename);
        printf("  架构:     %s\n", uts.machine);
    }
    long ncpu = sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpu > 0) {
        printf("  CPU 核数: %ld\n", ncpu);
    }

#elif defined(_WIN32)
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    printf("  架构:     %u\n", si.dwProcessorType);
    printf("  CPU 核数: %lu\n", si.dwNumberOfProcessors);

    MEMORYSTATUSEX mem;
    mem.dwLength = sizeof(mem);
    if (GlobalMemoryStatusEx(&mem)) {
        printf("  内存总量: %llu MB\n", (unsigned long long)(mem.ullTotalPhys / (1024 * 1024)));
        printf("  内存可用: %llu MB\n", (unsigned long long)(mem.ullAvailPhys / (1024 * 1024)));
    }
#else
    printf("  （当前平台不支持 sysinfo）\n");
#endif

    printf("\n  红线：只读探测，不修改任何系统状态。\n");
}

static void print_usage(void) {
    printf("用法: sysweeper-c <子命令>\n\n");
    printf("子命令:\n");
    printf("  version     版本信息\n");
    printf("  sysinfo     系统信息（uname / 内存 / CPU / uptime）\n");
    printf("  help        帮助\n\n");
    printf("示例:\n");
    printf("  sysweeper-c version\n");
    printf("  sysweeper-c sysinfo\n");
    printf("\n编译: cc -std=c11 -Wall -Wextra -O2 -o sysweeper-c sysweeper-c.c\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        print_usage();
        return 2;
    }

    if (strcmp(argv[1], "version") == 0 || strcmp(argv[1], "-v") == 0 || strcmp(argv[1], "--version") == 0) {
        print_version();
    } else if (strcmp(argv[1], "sysinfo") == 0 || strcmp(argv[1], "info") == 0) {
        print_sysinfo();
    } else if (strcmp(argv[1], "help") == 0 || strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0) {
        print_usage();
    } else {
        fprintf(stderr, "未知子命令: %s\n\n", argv[1]);
        print_usage();
        return 2;
    }

    return 0;
}
