// sysweeper-zig — system-optimizer 的 Zig 侧只读系统信息探针。
//
// 目标：让同一套「只读诊断」口径不依赖 Python/Go/C 运行时也能查询，
// 便于在仅有 zig 工具链的环境下做单文件二进制分发。
//
// 设计原则与 Python/Go/C 侧一致：
//   - 纯 Zig 标准库，零第三方依赖；
//   - 只读探测，命令缺失 / 执行失败一律降级提示，不 panic、不中断；
//   - 标准引用按受众分层。
//
// 红线：只读探测，不修改任何系统状态。
//
// 用法:
//   sysweeper-zig version     版本信息
//   sysweeper-zig sysinfo     系统信息（OS / 架构 / CPU / 内存 / uptime）
//   sysweeper-zig help        帮助
//
// 编译:
//   zig build-exe sysweeper.zig -O ReleaseFast
//   或直接运行: zig run sysweeper.zig version

const std = @import("std");
const builtin = @import("builtin");
const fs = std.fs;
const os = std.os;

// 版本号（与仓库其他语言侧保持一致）
const version = "0.6.40";

// 红线提示（贯穿所有只读子命令）
const red_line = "只读探测，不修改任何系统状态。";

pub fn main() !void {
    // 通用分配器解析命令行参数；进程退出时自动释放
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const args = try std.process.argsAlloc(allocator);
    defer std.process.argsFree(allocator, args);

    // 无子命令时打印用法，返回非零退出码
    if (args.len < 2) {
        printUsage();
        std.process.exit(2);
    }

    const sub = args[1];

    if (std.mem.eql(u8, sub, "version") or
        std.mem.eql(u8, sub, "-v") or
        std.mem.eql(u8, sub, "--version"))
    {
        printVersion();
    } else if (std.mem.eql(u8, sub, "sysinfo") or
        std.mem.eql(u8, sub, "info"))
    {
        printSysInfo();
    } else if (std.mem.eql(u8, sub, "help") or
        std.mem.eql(u8, sub, "-h") or
        std.mem.eql(u8, sub, "--help"))
    {
        printUsage();
    } else {
        const stderr = std.io.getStdErr().writer();
        stderr.print("未知子命令: {s}\n\n", .{sub}) catch {};
        printUsage();
        std.process.exit(2);
    }
}

// 打印版本信息：自身版本、平台、架构、Zig 版本（来自 builtin）
fn printVersion() void {
    const stdout = std.io.getStdOut().writer();
    stdout.print("sysweeper-zig {s}\n", .{version}) catch {};
    stdout.print("  platform: {s} (Zig)\n", .{platformName()}) catch {};
    stdout.print("  arch:     {s}\n", .{archName()}) catch {};
    stdout.print("  zig:      {s}\n", .{builtin.zig_version_string}) catch {};
}

// 打印系统信息：OS、架构、CPU 核数、内存（Linux 读 /proc/meminfo）、uptime（Linux 读 /proc/uptime）
fn printSysInfo() void {
    const stdout = std.io.getStdOut().writer();
    stdout.print("=== sysweeper-zig 系统信息（只读） ===\n\n", .{}) catch {};

    // --- 操作系统与架构（来自 builtin，编译期可知）---
    stdout.print("  操作系统: {s}\n", .{platformName()}) catch {};
    stdout.print("  架构:     {s}\n", .{archName()}) catch {};

    // --- CPU 核数（跨平台，标准库实现）---
    const cpu_count = std.Thread.getCpuCount() catch 0;
    if (cpu_count > 0) {
        stdout.print("  CPU 核数: {d}\n", .{cpu_count}) catch {};
    } else {
        stdout.print("  CPU 核数: 未知\n", .{}) catch {};
    }

    // --- 内存与 uptime：Linux 下读 /proc，其他平台降级提示 ---
    switch (builtin.os.tag) {
        .linux => {
            printLinuxMemInfo(stdout);
            printLinuxUptime(stdout);
        },
        else => {
            stdout.print("  内存:     （当前平台不支持 /proc/meminfo 读取）\n", .{}) catch {};
            stdout.print("  运行时间: （当前平台不支持 /proc/uptime 读取）\n", .{}) catch {};
        },
    }

    stdout.print("\n  红线：{s}\n", .{red_line}) catch {};
}

// Linux 下读取 /proc/meminfo，提取 MemTotal / MemAvailable / SwapTotal
fn printLinuxMemInfo(writer: anytype) void {
    var buf: [8192]u8 = undefined;
    const content = readProcFile("/proc/meminfo", &buf) orelse {
        writer.print("  内存:     读取 /proc/meminfo 失败\n", .{}) catch {};
        return;
    };

    var total_kb: ?u64 = null;
    var avail_kb: ?u64 = null;
    var swap_kb: ?u64 = null;

    // 逐行解析：键: 值 kB
    var it = std.mem.splitScalar(u8, content, '\n');
    while (it.next()) |line| {
        if (std.mem.startsWith(u8, line, "MemTotal:")) {
            total_kb = parseKbValue(line);
        } else if (std.mem.startsWith(u8, line, "MemAvailable:")) {
            avail_kb = parseKbValue(line);
        } else if (std.mem.startsWith(u8, line, "SwapTotal:")) {
            swap_kb = parseKbValue(line);
        }
    }

    if (total_kb) |t| {
        writer.print("  内存总量: {d} MB\n", .{t / 1024}) catch {};
    } else {
        writer.print("  内存总量: 未知\n", .{}) catch {};
    }
    if (avail_kb) |a| {
        writer.print("  内存可用: {d} MB\n", .{a / 1024}) catch {};
    } else {
        writer.print("  内存可用: 未知\n", .{}) catch {};
    }
    if (swap_kb) |s| {
        writer.print("  交换总量: {d} MB\n", .{s / 1024}) catch {};
    } else {
        writer.print("  交换总量: 未知\n", .{}) catch {};
    }
}

// Linux 下读取 /proc/uptime，第一个字段为系统运行秒数
fn printLinuxUptime(writer: anytype) void {
    var buf: [256]u8 = undefined;
    const content = readProcFile("/proc/uptime", &buf) orelse {
        writer.print("  运行时间: 读取 /proc/uptime 失败\n", .{}) catch {};
        return;
    };

    // 第一个空格前为运行秒数（浮点）
    const space = std.mem.indexOfScalar(u8, content, ' ') orelse content.len;
    const secs_str = content[0..space];
    // 只取整数部分（小数点之前）
    const dot = std.mem.indexOfScalar(u8, secs_str, '.') orelse secs_str.len;
    const int_str = secs_str[0..dot];
    const secs = std.fmt.parseInt(u64, int_str, 10) catch {
        writer.print("  运行时间: 解析失败\n", .{}) catch {};
        return;
    };

    const days = secs / 86400;
    const hours = (secs % 86400) / 3600;
    const mins = (secs % 3600) / 60;
    writer.print("  运行时间: {d}天 {d}时 {d}分\n", .{ days, hours, mins }) catch {};
}

// 读取 /proc 下的文件：用 std.fs 打开、std.os 读、std.fs 关闭（满足「使用 std.fs 与 std.os 读 /proc」）
fn readProcFile(path: []const u8, buf: []u8) ?[]const u8 {
    // std.fs 打开文件（只读）
    const file = fs.cwd().openFile(path, .{}) catch return null;
    defer file.close();

    // std.os.linux 直接发起 read 系统调用（fd 取自 std.fs 的 File.handle）
    const n_raw = os.linux.read(file.handle, buf.ptr, buf.len);
    // raw syscall 返回 usize：成功为读到的字节数（<= buf.len）；错误时为 -errno，
    // 重新解释为 usize 后远超 buf.len，据此判定失败并降级返回 null
    if (n_raw > buf.len) return null;
    if (n_raw == 0) return null;
    return buf[0..n_raw];
}

// 从形如 "MemTotal:       16384000 kB" 的行中提取数值部分
fn parseKbValue(line: []const u8) ?u64 {
    // 找到 ':' 之后的内容，跳过空白，取连续数字
    const colon = std.mem.indexOfScalar(u8, line, ':') orelse return null;
    var rest = line[colon + 1 ..];
    rest = std.mem.trim(u8, rest, " \t");
    // 截取到第一个非数字字符
    var end: usize = 0;
    while (end < rest.len and rest[end] >= '0' and rest[end] <= '9') : (end += 1) {}
    if (end == 0) return null;
    return std.fmt.parseInt(u64, rest[0..end], 10) catch null;
}

// 返回当前编译目标的操作系统名称
fn platformName() []const u8 {
    return switch (builtin.os.tag) {
        .linux => "Linux",
        .macos => "macOS",
        .windows => "Windows",
        .freebsd => "FreeBSD",
        .openbsd => "OpenBSD",
        .netbsd => "NetBSD",
        .dragonfly => "DragonFlyBSD",
        .ios => "iOS",
        .wasi => "WASI",
        else => "Unknown",
    };
}

// 返回当前编译目标的 CPU 架构名称
fn archName() []const u8 {
    return switch (builtin.cpu.arch) {
        .x86_64 => "x86_64",
        .x86 => "x86",
        .aarch64 => "aarch64",
        .arm => "arm",
        .riscv64 => "riscv64",
        .riscv32 => "riscv32",
        .mips => "mips",
        .mipsel => "mipsel",
        .mips64 => "mips64",
        .powerpc => "powerpc",
        .powerpc64 => "powerpc64",
        .powerpc64le => "powerpc64le",
        .s390x => "s390x",
        .wasm32 => "wasm32",
        .wasm64 => "wasm64",
        else => @tagName(builtin.cpu.arch),
    };
}

// 打印用法
fn printUsage() void {
    const stdout = std.io.getStdOut().writer();
    stdout.print("用法: sysweeper-zig <子命令>\n\n", .{}) catch {};
    stdout.print("子命令:\n", .{}) catch {};
    stdout.print("  version     版本信息\n", .{}) catch {};
    stdout.print("  sysinfo     系统信息（OS / 架构 / CPU / 内存 / uptime）\n", .{}) catch {};
    stdout.print("  help        帮助\n\n", .{}) catch {};
    stdout.print("示例:\n", .{}) catch {};
    stdout.print("  sysweeper-zig version\n", .{}) catch {};
    stdout.print("  sysweeper-zig sysinfo\n", .{}) catch {};
    stdout.print("\n编译: zig build-exe sysweeper.zig -O ReleaseFast\n", .{}) catch {};
    stdout.print("红线：{s}\n", .{red_line}) catch {};
}
