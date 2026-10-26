#!/usr/bin/env escript
%%% sysweeper-erlang — system-optimizer 的 Erlang 侧命令行组件。
%%%
%%% 目标：让同一套「只读诊断」口径在有 Erlang/OTP 的环境也能查询，
%%% 便于电信/高可用场景（Erlang 预装）下使用。
%%%
%%% 设计原则与 Python/Go/C 侧一致：
%%%   - 纯 Erlang/OTP 标准库，零第三方依赖；
%%%   - 只读探测，异常一律降级提示，不 crash；
%%%   - 红线：不启停服务、不改配置、不连控制端口。
%%%
%%% 用法:
%%%   escript sysweeper.erl version        版本信息
%%%   escript sysweeper.erl sysinfo        系统信息（OS / 内存 / CPU / uptime）
%%%   escript sysweeper.erl help           帮助

-module(sysweeper).
-export([main/1]).

-define(VERSION, "0.6.40").

main([]) ->
    print_usage(),
    halt(2);
main([Cmd | _]) ->
    case Cmd of
        "version" -> print_version();
        "-v" -> print_version();
        "--version" -> print_version();
        "sysinfo" -> print_sysinfo();
        "info" -> print_sysinfo();
        "help" -> print_usage();
        "-h" -> print_usage();
        "--help" -> print_usage();
        _ ->
            io:format(standard_error, "未知子命令: ~s~n~n", [Cmd]),
            print_usage(),
            halt(2)
    end.

print_version() ->
    {OTP, _} = string:to_integer(erlang:system_info(otp_release)),
    io:format("sysweeper-erlang ~s~n", [?VERSION]),
    io:format("  Erlang/OTP: ~s~n", [erlang:system_info(otp_release)]),
    io:format("  ERTS: ~s~n", [erlang:system_info(version)]),
    io:format("  Emulator: ~s~n", [erlang:system_info(system_version)]),
    case os:type() of
        {unix, OsName} -> io:format("  platform: ~s (Erlang)~n", [OsName]);
        {win32, _} -> io:format("  platform: Windows (Erlang)~n", [])
    end.

print_sysinfo() ->
    io:format("=== sysweeper-erlang 系统信息（只读） ===~n~n"),
    %% OS
    io:format("  操作系统: ~p~n", [os:type()]),
    %% 主机名
    Hostname = safe_cmd("hostname"),
    io:format("  主机名: ~s~n", [Hostname]),
    %% 架构
    Arch = safe_cmd("uname -m"),
    io:format("  架构: ~s~n", [Arch]),
    %% CPU 核数
    CPU = try erlang:system_info(logical_processors_available)
           catch _:_ -> 0 end,
    io:format("  CPU 核数: ~p~n", [CPU]),
    %% 内存
    Mem = try erlang:memory()
           catch _:_ -> [] end,
    case proplists:get_value(total, Mem, 0) of
        0 -> io:format("  内存: 不可用~n", []);
        Total -> io:format("  Erlang 内存: ~p MB~n", [Total div (1024 * 1024)])
    end,
    case proplists:get_value(processes, Mem, 0) of
        0 -> ok;
        ProcMem -> io:format("  进程内存: ~p MB~n", [ProcMem div (1024 * 1024)])
    end,
    %% uptime（VM 启动时长）
    try
        {WallTime, _} = erlang:statistics(wall_clock),
        Days = WallTime div 86400000,
        Hours = (WallTime rem 86400000) div 3600000,
        Mins = (WallTime rem 3600000) div 60000,
        io:format("  VM 运行时间: ~p天 ~p时 ~p分~n", [Days, Hours, Mins])
    catch _:_ ->
        io:format("  运行时间: 不可用~n", [])
    end,
    %% 进程数
    ProcCount = erlang:system_info(process_count),
    io:format("  Erlang 进程数: ~p~n", [ProcCount]),
    %% 端口数
    PortCount = erlang:system_info(port_count),
    io:format("  Erlang 端口数: ~p~n", [PortCount]),
    io:format("~n  红线：只读探测，不修改任何系统状态。~n", []).

print_usage() ->
    io:format("用法: escript sysweeper.erl <子命令>~n~n", []),
    io:format("子命令:~n", []),
    io:format("  version     版本信息~n", []),
    io:format("  sysinfo     系统信息（OS / 内存 / CPU / uptime）~n", []),
    io:format("  help        帮助~n~n", []),
    io:format("示例:~n", []),
    io:format("  escript sysweeper.erl version~n", []),
    io:format("  escript sysweeper.erl sysinfo~n", []).

%% 安全执行 shell 命令（只读），失败返回 "(未知)"
safe_cmd(Cmd) ->
    try os:cmd(Cmd)
    catch _:_ -> "(未知)"
    end.
