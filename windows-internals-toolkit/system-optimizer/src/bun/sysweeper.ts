#!/usr/bin/env bun
/**
 * sysweeper-bun — system-optimizer 的 Bun 侧命令行组件。
 *
 * 目标：让同一套「只读诊断」口径在 Bun 运行时环境下也能查询，
 * 便于边缘/轻量场景（Bun 单二进制分发）下使用。
 *
 * 设计原则与 Python/Go/C 侧一致：
 *   - 纯 Bun 运行时 + Node.js 标准库，零第三方依赖；
 *   - 只读探测，异常一律降级提示，不 crash；
 *   - 红线：不启停服务、不改配置、不连控制端口。
 *
 * 用法:
 *   bun sysweeper.ts version        版本信息
 *   bun sysweeper.ts sysinfo        系统信息（OS / 内存 / CPU / uptime）
 *   bun sysweeper.ts help           帮助
 */

import { os } from "node:os";
import { readFileSync } from "node:fs";

const VERSION = "0.6.40";

function safeRead(path: string): string | null {
    try {
        return readFileSync(path, "utf-8");
    } catch {
        return null;
    }
}

function parseMeminfo(content: string): { total: number; available: number } | null {
    const totalLine = content.match(/^MemTotal:\s+(\d+)/m);
    const availLine = content.match(/^MemAvailable:\s+(\d+)/m);
    if (!totalLine || !availLine) return null;
    return {
        total: Math.floor(parseInt(totalLine[1]) / 1024),
        available: Math.floor(parseInt(availLine[1]) / 1024),
    };
}

function printVersion() {
    console.log(`sysweeper-bun ${VERSION}`);
    console.log(`  Bun: ${Bun.version}`);
    console.log(`  platform: ${process.platform}`);
    console.log(`  arch: ${process.arch}`);
    console.log(`  OS: ${os.type()} ${os.release()}`);
}

function printSysinfo() {
    console.log("=== sysweeper-bun 系统信息（只读） ===\n");

    console.log(`  操作系统: ${os.type()} ${os.release()}`);
    console.log(`  主机名: ${os.hostname()}`);
    console.log(`  架构: ${os.arch()}`);
    console.log(`  CPU 核数: ${os.cpus().length}`);

    // 内存（Linux 走 /proc/meminfo，其他平台走 Node os）
    if (process.platform === "linux") {
        const meminfo = safeRead("/proc/meminfo");
        if (meminfo) {
            const mem = parseMeminfo(meminfo);
            if (mem) {
                console.log(`  内存总量: ${mem.total} MB`);
                console.log(`  内存可用: ${mem.available} MB`);
            } else {
                console.log("  内存: 解析失败");
            }
        } else {
            console.log("  内存: /proc/meminfo 不可读");
        }
    } else {
        const totalMB = Math.floor(os.totalmem() / (1024 * 1024));
        const freeMB = Math.floor(os.freemem() / (1024 * 1024));
        console.log(`  内存总量: ${totalMB} MB`);
        console.log(`  内存可用: ${freeMB} MB`);
    }

    // uptime
    const uptimeSec = os.uptime();
    const days = Math.floor(uptimeSec / 86400);
    const hours = Math.floor((uptimeSec % 86400) / 3600);
    const mins = Math.floor((uptimeSec % 3600) / 60);
    console.log(`  运行时间: ${days}天 ${hours}时 ${mins}分`);

    // Bun 内存限制
    try {
        console.log(`  Bun 内存限制: ${Math.floor(Bun.memoryLimit / (1024 * 1024))} MB`);
    } catch {
        // 某些版本可能无此 API
    }

    console.log("\n  红线：只读探测，不修改任何系统状态。");
}

function printUsage() {
    console.log("用法: bun sysweeper.ts <子命令>\n");
    console.log("子命令:");
    console.log("  version     版本信息");
    console.log("  sysinfo     系统信息（OS / 内存 / CPU / uptime）");
    console.log("  help        帮助\n");
    console.log("示例:");
    console.log("  bun sysweeper.ts version");
    console.log("  bun sysweeper.ts sysinfo");
}

const cmd = process.argv[2];

if (!cmd) {
    printUsage();
    process.exit(2);
}

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
    case "help":
    case "-h":
    case "--help":
        printUsage();
        break;
    default:
        console.error(`未知子命令: ${cmd}\n`);
        printUsage();
        process.exit(2);
}
