#!/usr/bin/env elixir

# sysweeper-elixir — system-optimizer 的 Elixir 侧命令行组件。
#
# 目标：让同一套「只读诊断」口径不依赖 Python / Go / C 运行时也能查询，
# 便于有 BEAM 的环境（嵌入式 / 容器 / 多语种混合栈）下使用。
#
# 设计原则与 Python / C / Go 侧一致：
#   - 纯 Erlang / Elixir 标准库，零第三方依赖；
#   - 只读探测，命令缺失 / 执行失败一律降级提示，不抛异常中断；
#   - 红线：只读探测，不修改任何系统状态。
#
# 用法:
#   elixir sysweeper.exs version   版本信息
#   elixir sysweeper.exs sysinfo   系统信息（OS / 主机名 / CPU / 内存 / uptime）
#   elixir sysweeper.exs help      帮助

defmodule SysweeperElixir do
  @version "0.6.40"
  @redline "红线：只读探测，不修改任何系统状态。"

  # 入口：解析 System.argv 的第一个子命令
  def main(args) do
    case args do
      [] ->
        print_usage()
        System.halt(2)

      [sub | _rest] ->
        case sub do
          "version" -> print_version()
          "-v" -> print_version()
          "--version" -> print_version()
          "sysinfo" -> print_sysinfo()
          "info" -> print_sysinfo()
          "help" -> print_usage()
          "-h" -> print_usage()
          "--help" -> print_usage()
          other ->
            IO.puts(:stderr, "未知子命令: #{other}\n")
            print_usage()
            System.halt(2)
        end
    end
  end

  # 版本信息
  defp print_version do
    IO.puts("sysweeper-elixir #{@version}")
    IO.puts("  Elixir:      #{System.version()}")
    IO.puts("  Erlang/OTP:  #{to_string(:erlang.system_info(:otp_release))}")
    IO.puts("  platform:    #{platform()}")
  end

  # 系统信息（只读）
  defp print_sysinfo do
    IO.puts("=== sysweeper-elixir 系统信息（只读） ===\n")
    IO.puts("  操作系统:        #{os_name()}")
    IO.puts("  主机名:          #{hostname()}")
    IO.puts("  架构:            #{architecture()}")
    IO.puts("  CPU 核数:        #{cpu_cores()}")
    print_memory()
    IO.puts("  运行时间:        #{uptime()}")
    IO.puts("\n  #{@redline}")
  end

  # 用法
  defp print_usage do
    IO.puts("用法: elixir sysweeper.exs <子命令>\n")
    IO.puts("子命令:")
    IO.puts("  version     版本信息")
    IO.puts("  sysinfo     系统信息（OS / 主机名 / CPU / 内存 / uptime）")
    IO.puts("  help        帮助\n")
    IO.puts("示例:")
    IO.puts("  elixir sysweeper.exs version")
    IO.puts("  elixir sysweeper.exs sysinfo")
  end

  # ---- 各只读探测项均带降级（缺失 / 失败 → 友好提示，不中断）----

  # 操作系统（:os.type/0）
  defp os_name do
    try do
      case :os.type() do
        {:unix, os} -> "Unix / #{os}"
        {:win32, sub} -> "Windows / #{sub}"
        other -> inspect(other)
      end
    rescue
      _ -> "未知"
    end
  end

  # 主机名（外接 hostname 命令，只读；缺失则降级到环境变量 / 未知）
  defp hostname do
    try do
      case System.cmd("hostname", [], stderr_to_stdout: true) do
        {out, 0} -> String.trim(out)
        _ -> System.get_env("HOSTNAME") || "未知"
      end
    rescue
      _ -> System.get_env("HOSTNAME") || "未知"
    end
  end

  # 架构（:erlang.system_info(:system_architecture)）
  defp architecture do
    try do
      case :erlang.system_info(:system_architecture) do
        arch when is_list(arch) and arch != [] -> to_string(arch)
        _ -> "未知"
      end
    rescue
      _ -> "未知"
    end
  end

  # CPU 逻辑核数（按需求：:erlang.system_info(:logical_processors_available)）
  defp cpu_cores do
    try do
      n = :erlang.system_info(:logical_processors_available)
      if is_integer(n) and n > 0, do: to_string(n), else: "未知"
    rescue
      _ -> "未知"
    end
  end

  # 内存（:erlang.memory()，按区段打印 MB）
  defp print_memory do
    try do
      mem = :erlang.memory()
      total = Keyword.get(mem, :total, 0)
      procs = Keyword.get(mem, :processes, 0)
      sys = Keyword.get(mem, :system, 0)
      IO.puts("  内存(total):       #{mb(total)} MB")
      IO.puts("  内存(processes):   #{mb(procs)} MB")
      IO.puts("  内存(system):      #{mb(sys)} MB")
    rescue
      _ -> IO.puts("  内存:            未知")
    end
  end

  # 运行时间（VM uptime）
  # 需求点名 :erlang.statistics(:wall_time) 或 :os.system_time()：
  #   - :wall_time 并非 BEAM 有效键，BEAM 中始终可用的是 :wall_clock，
  #     返回自 VM 启动以来的墙钟毫秒 {总毫秒, 距上次调用毫秒}；
  #   - 失败时降级到 :os.system_time()（仅墙钟纪元时间，无法直接得 uptime，标注不可用）。
  defp uptime do
    try do
      {total_ms, _since_last} = :erlang.statistics(:wall_clock)
      format_uptime(total_ms)
    rescue
      _ ->
        try do
          _ = :os.system_time()
          "不可用（VM 统计失败，仅有 :os.system_time() 时钟）"
        rescue
          _ -> "未知"
        end
    end
  end

  # 字节 → MB（保留两位小数）
  defp mb(bytes) do
    bytes
    |> Kernel./(1024 * 1024)
    |> Float.round(2)
    |> to_string()
  end

  # 毫秒 → 天 / 时 / 分
  defp format_uptime(ms) do
    total_sec = div(ms, 1000)
    days = div(total_sec, 86400)
    hours = div(rem(total_sec, 86400), 3600)
    mins = div(rem(total_sec, 3600), 60)
    "#{days}天 #{hours}时 #{mins}分"
  end

  # 平台标识
  defp platform do
    case :os.type() do
      {:unix, :linux} -> "Linux (BEAM)"
      {:unix, :darwin} -> "macOS (BEAM)"
      {:unix, os} -> "#{os} (BEAM)"
      {:win32, _} -> "Windows (BEAM)"
      _ -> "Unknown (BEAM)"
    end
  end
end

SysweeperElixir.main(System.argv())
