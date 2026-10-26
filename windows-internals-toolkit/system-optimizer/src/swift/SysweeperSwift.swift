// SysweeperSwift.swift — system-optimizer 的 Swift 侧命令行组件。
//
// 目标：让同一套「只读诊断」口径不依赖 Python/Go/C 运行时也能查询，
// 便于 macOS / Linux 上具备 Swift 工具链的环境下使用。
//
// 设计原则与 C/Go 侧一致：
//   - 纯标准库（Foundation），零第三方依赖，单文件可直接编译；
//   - 只读探测，命令缺失 / 执行失败一律降级提示，不退出、不修改系统；
//   - 标准引用按受众分层。
//
// 用法:
//   sysweeper-swift version          版本信息
//   sysweeper-swift sysinfo         系统信息（OS / 主机名 / 架构 / CPU / 内存 / uptime）
//   sysweeper-swift help            帮助
//
// 编译:
//   swiftc -O -o sysweeper-swift SysweeperSwift.swift

import Foundation

// 版本号（与仓库其它侧保持一致：src/c、src/go、python 等，统一 0.6.40）
let VERSION = "0.6.40"

// 平台名（编译条件判定，运行时双重兜底）
#if os(macOS)
let platformName = "macOS (Swift)"
#elseif os(Linux)
let platformName = "Linux (Swift)"
#elseif os(Windows)
let platformName = "Windows (Swift)"
#else
let platformName = "Unknown (Swift)"
#endif

// Swift 语言版本（编译期 #if 链推断，纯标准库、无运行时依赖）
#if swift(>=6.0)
let swiftVersion = "6.0+"
#elseif swift(>=5.10)
let swiftVersion = "5.10+"
#elseif swift(>=5.9)
let swiftVersion = "5.9+"
#elseif swift(>=5.8)
let swiftVersion = "5.8+"
#elseif swift(>=5.7)
let swiftVersion = "5.7+"
#elseif swift(>=5.6)
let swiftVersion = "5.6+"
#elseif swift(>=5.5)
let swiftVersion = "5.5+"
#elseif swift(>=5.0)
let swiftVersion = "5.0+"
#else
let swiftVersion = "<5.0"
#endif

// MARK: - 通用工具

// 读小文件工具（纯 Foundation，失败返回 nil 以便降级，绝不抛错）
func readFile(_ path: String) -> String? {
    return try? String(contentsOfFile: path, encoding: .utf8)
}

// MARK: - 版本子命令

func printVersion() {
    print("sysweeper-swift \(VERSION)")
    print("  platform: \(platformName)")
    print("  swift:    \(swiftVersion) (语言模式)")
}

// MARK: - 系统信息子命令

// macOS 侧：uname 取内核 / 主机名 / 架构（Foundation 在 Darwin 下可直连 uname）
#if os(macOS)
func macUname() -> (sysname: String, nodename: String, machine: String, release: String, version: String)? {
    var buf = utsname()
    guard uname(&buf) == 0 else { return nil }
    // 将 utsname 的定长 C 字段安全转成 String
    func field<T>(_ member: UnsafeMutablePointer<T>) -> String {
        return member.withMemoryRebound(to: CChar.self, capacity: MemoryLayout<T>.size) {
            String(cString: $0)
        }
    }
    return (
        field(&buf.sysname),
        field(&buf.nodename),
        field(&buf.machine),
        field(&buf.release),
        field(&buf.version)
    )
}
#endif

func printSysinfo() {
    print("=== sysweeper-swift 系统信息（只读） ===\n")

#if os(macOS)
    // --- 内核 / 主机名 / 架构（uname）---
    if let u = macUname() {
        print("  内核:     \(u.sysname) \(u.release)")
        print("  主机名:   \(u.nodename)")
        print("  架构:     \(u.machine)")
        print("  版本:     \(u.version)")
    } else {
        print("  uname:    失败")
    }

    // --- macOS 版本（ProcessInfo）---
    let pi = ProcessInfo.processInfo
    print("  OS 版本:  \(pi.operatingSystemVersionString)")

    // --- CPU 核数（ProcessInfo）---
    print("  CPU 核数: \(pi.processorCount)（活跃 \(pi.activeProcessorCount)）")

    // --- 内存（ProcessInfo.physicalMemory，单位字节）---
    let totalMB = pi.physicalMemory / (1024 * 1024)
    print("  内存总量: \(totalMB) MB")

    // --- 运行时间（ProcessInfo.systemUptime，单位秒）---
    let up = pi.systemUptime
    let days = Int(up) / 86400
    let hours = (Int(up) % 86400) / 3600
    let mins = (Int(up) % 3600) / 60
    print("  运行时间: \(days)天 \(hours)时 \(mins)分")

#elseif os(Linux)
    // --- OS 名称 / 内核（/proc/sys/kernel，纯 Foundation 读文件）---
    let ostype = readFile("/proc/sys/kernel/ostype")?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    let release = readFile("/proc/sys/kernel/osrelease")?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    let version = readFile("/proc/sys/kernel/version")?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    print("  内核:     \(ostype ?? "未知") \(release ?? "")")
    print("  版本:     \(version ?? "未知")")

    // --- 主机名（/proc/sys/kernel/hostname）---
    let host = readFile("/proc/sys/kernel/hostname")?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    print("  主机名:   \(host ?? "未知")")

    // --- 架构（/proc/sys/kernel/arch，部分内核无此项则降级提示）---
    let arch = readFile("/proc/sys/kernel/arch")?
        .trimmingCharacters(in: .whitespacesAndNewlines)
    print("  架构:     \(arch ?? "未知（/proc/sys/kernel/arch 不可读）")")

    // --- 发行版（/etc/os-release，可选信息，缺失即跳过）---
    if let osRelease = readFile("/etc/os-release") {
        for line in osRelease.split(separator: "\n")
        where line.hasPrefix("PRETTY_NAME=") {
            let raw = String(line.dropFirst("PRETTY_NAME=".count))
            let val = raw.replacingOccurrences(of: "\"", with: "")
            print("  发行版:   \(val)")
            break
        }
    }

    // --- CPU 核数（/proc/cpuinfo 中 processor 行计数）---
    if let cpuinfo = readFile("/proc/cpuinfo") {
        var cores = 0
        for line in cpuinfo.split(separator: "\n")
        where line.hasPrefix("processor") {
            cores += 1
        }
        print("  CPU 核数: \(cores)")
    } else {
        print("  CPU 核数: 不可读")
    }

    // --- 内存（/proc/meminfo，单位 kB）---
    if let meminfo = readFile("/proc/meminfo") {
        var totalKB: UInt64 = 0
        var availKB: UInt64 = 0
        var freeKB: UInt64 = 0
        // 解析形如 "MemTotal:       16384000 kB" 的行，取第二列数字
        func parseKB(_ line: Substring) -> UInt64 {
            let parts = line.split(separator: " ", omittingEmptySubsequences: true)
            if parts.count >= 2, let v = UInt64(parts[1]) {
                return v
            }
            return 0
        }
        for line in meminfo.split(separator: "\n") {
            if line.hasPrefix("MemTotal:") {
                totalKB = parseKB(line)
            } else if line.hasPrefix("MemAvailable:") {
                availKB = parseKB(line)
            } else if line.hasPrefix("MemFree:") {
                freeKB = parseKB(line)
            }
        }
        print("  内存总量: \(totalKB / 1024) MB")
        if availKB > 0 {
            print("  内存可用: \(availKB / 1024) MB")
        } else {
            // 老内核无 MemAvailable，回退 MemFree 并标明来源
            print("  内存可用: \(freeKB / 1024) MB（回退 MemFree）")
        }
    } else {
        print("  内存:     不可读")
    }

    // --- 运行时间（/proc/uptime，第一列为开机秒数）---
    if let uptime = readFile("/proc/uptime") {
        let secs = Double(uptime.split(separator: " ").first ?? "") ?? 0
        let days = Int(secs) / 86400
        let hours = (Int(secs) % 86400) / 3600
        let mins = (Int(secs) % 3600) / 60
        print("  运行时间: \(days)天 \(hours)时 \(mins)分")
    } else {
        print("  运行时间: 不可读")
    }

#else
    print("  （当前平台不支持 sysinfo）")
#endif

    print("\n  红线：只读探测，不修改任何系统状态。")
}

// MARK: - 帮助子命令

func printUsage() {
    print("用法: sysweeper-swift <子命令>\n")
    print("子命令:")
    print("  version     版本信息")
    print("  sysinfo     系统信息（OS / 主机名 / 架构 / CPU / 内存 / uptime）")
    print("  help        帮助\n")
    print("示例:")
    print("  sysweeper-swift version")
    print("  sysweeper-swift sysinfo\n")
    print("编译: swiftc -O -o sysweeper-swift SysweeperSwift.swift")
}

// MARK: - 入口

func main() {
    let args = CommandLine.arguments
    guard args.count >= 2 else {
        printUsage()
        exit(2)
    }
    switch args[1] {
    case "version", "-v", "--version":
        printVersion()
    case "sysinfo", "info":
        printSysinfo()
    case "help", "-h", "--help":
        printUsage()
    default:
        // 未知子命令写到 stderr，符合 POSIX 习惯；随后降级到帮助并返回非零
        let msg = "未知子命令: \(args[1])\n\n"
        FileHandle.standardError.write(Data(msg.utf8))
        printUsage()
        exit(2)
    }
}

main()
