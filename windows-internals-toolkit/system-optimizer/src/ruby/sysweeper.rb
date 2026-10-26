#!/usr/bin/env ruby
# sysweeper-ruby — system-optimizer 的 Ruby 侧命令行组件。
#
# 目标：让同一套「只读诊断」口径在 Ruby 环境也能查询，
# 便于有 Ruby 预装的环境（macOS、各类 Ruby on Rails 服务器等）下使用。
#
# 设计原则与 Python/Go/C/Java 侧一致：
#   - 纯 Ruby 标准库，零第三方依赖；
#   - 只读探测，命令缺失 / 文件不存在一律降级提示，不外抛堆栈到用户端；
#   - 红线：不启停服务、不改配置、不连控制端口。
#
# 用法:
#   ruby sysweeper.rb version        版本信息
#   ruby sysweeper.rb sysinfo        系统信息（OS / 主机 / 架构 / CPU / 内存 / uptime）
#   ruby sysweeper.rb help           帮助

require 'etc'
require 'socket'
require 'rbconfig'
require 'open3'

# 版本号（与 Python / Go / C / Java 侧保持一致：0.6.40）
VERSION = '0.6.40'

# 判断当前平台：返回 :linux / :macos / :other
def detect_platform
  case RbConfig::CONFIG['host_os']
  when /linux/i then :linux
  when /darwin|mac/i then :macos
  else :other
  end
end

# 安全读取文件：失败返回 nil，绝不抛异常（只读降级）
def safe_read(path)
  File.read(path)
rescue StandardError
  nil
end

# 安全运行命令：失败返回 nil（只读降级，不修改任何系统状态）
def safe_cmd(*cmd)
  stdout, _ = Open3.capture2(*cmd)
  stdout
rescue StandardError
  nil
end

# ── version 子命令 ──
def print_version
  puts "sysweeper-ruby #{VERSION}"
  puts "  platform: #{RUBY_PLATFORM}"
  puts "  ruby:     #{RUBY_VERSION}"
  puts "  engine:   #{RUBY_ENGINE}"
end

# ── sysinfo 子命令 ──
def print_sysinfo
  puts "=== sysweeper-ruby 系统信息（只读） ==="
  puts
  platform = detect_platform

  # --- 操作系统 ---
  os_name = case platform
            when :linux then 'Linux'
            when :macos then 'macOS'
            else RUBY_PLATFORM
            end
  puts "  操作系统:   #{os_name}"

  # --- 主机名 ---
  hostname =
    begin
      Socket.gethostname
    rescue StandardError
      '(未知)'
    end
  puts "  主机名:     #{hostname}"

  # --- 架构（优先 uname -m，失败回退 RUBY_PLATFORM）---
  arch = safe_cmd('uname', '-m')
  arch = arch.strip if arch
  arch = (arch && !arch.empty?) ? arch : RUBY_PLATFORM
  puts "  架构:       #{arch}"

  # --- CPU 核数 ---
  ncpu =
    begin
      Etc.nprocessors
    rescue StandardError
      nil
    end
  puts "  CPU 核数:   #{ncpu || '(未知)'}"

  # --- 内存（Linux 走 /proc/meminfo，macOS 走 sysctl）---
  case platform
  when :linux
    print_linux_memory
  when :macos
    print_macos_memory
  else
    puts "  内存:       （当前平台不支持）"
  end

  # --- 运行时间（uptime）---
  print_uptime(platform)

  puts
  puts "  红线：只读探测，不修改任何系统状态。"
end

# Linux 内存：解析 /proc/meminfo（与 C 侧 sysinfo 同源）
def print_linux_memory
  content = safe_read('/proc/meminfo')
  if content.nil? || content.empty?
    puts "  内存:       /proc/meminfo 不可读"
    return
  end
  total = content[/^MemTotal:\s+(\d+)/, 1]
  avail = content[/^MemAvailable:\s+(\d+)/, 1]
  avail ||= content[/^MemFree:\s+(\d+)/, 1]
  total_mb = total ? (total.to_i / 1024) : nil
  avail_mb = avail ? (avail.to_i / 1024) : nil
  puts "  内存总量:   #{total_mb ? total_mb.to_s + ' MB' : '(未知)'}"
  puts "  内存可用:   #{avail_mb ? avail_mb.to_s + ' MB' : '(未知)'}"
end

# macOS 内存：sysctl hw.memsize（字节）
def print_macos_memory
  total = safe_cmd('sysctl', '-n', 'hw.memsize')
  if total && !total.strip.empty?
    total_mb = total.strip.to_i / (1024 * 1024)
    puts "  内存总量:   #{total_mb} MB"
  else
    puts "  内存总量:   (未知)"
  end
  puts "  内存可用:   (macOS 不直接暴露)"
end

# uptime：Linux 走 /proc/uptime，其他平台走 `uptime` 命令兜底
def print_uptime(platform)
  seconds =
    if platform == :linux
      content = safe_read('/proc/uptime')
      content ? content[/^[\d.]+/].to_f : nil
    end

  if seconds.nil? || seconds.zero?
    out = safe_cmd('uptime')
    if out
      puts "  运行时间:   #{out.strip}"
      return
    end
  end

  if seconds && seconds > 0
    days = (seconds / 86400).to_i
    hours = ((seconds % 86400) / 3600).to_i
    mins = ((seconds % 3600) / 60).to_i
    puts "  运行时间:   #{days}天 #{hours}时 #{mins}分"
  else
    puts "  运行时间:   (未知)"
  end
end

# ── help 子命令 ──
def print_usage
  puts "用法: ruby sysweeper.rb <子命令>"
  puts
  puts "子命令:"
  puts "  version     版本信息"
  puts "  sysinfo     系统信息（OS / 主机 / 架构 / CPU / 内存 / uptime）"
  puts "  help        帮助"
  puts
  puts "示例:"
  puts "  ruby sysweeper.rb version"
  puts "  ruby sysweeper.rb sysinfo"
end

# ── 入口：解析 ARGV 子命令 ──
def main(argv)
  if argv.empty?
    print_usage
    exit 2
  end

  cmd = argv[0]
  case cmd
  when 'version', '-v', '--version'
    print_version
  when 'sysinfo', 'info'
    print_sysinfo
  when 'help', '-h', '--help'
    print_usage
  else
    warn "未知子命令: #{cmd}"
    warn
    print_usage
    exit 2
  end
end

main(ARGV.dup) if __FILE__ == $PROGRAM_NAME
