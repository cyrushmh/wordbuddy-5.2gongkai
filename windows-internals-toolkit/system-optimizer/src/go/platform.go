package main

import (
	"fmt"
	"runtime"
)

// 运行时信息（供 version / list 展示，纯标准库）
func runtimeGOOS() string   { return runtime.GOOS }
func runtimeGOARCH() string { return runtime.GOARCH }
func goVersion() string     { return runtime.Version() }

// 支持的平台（与 Python 侧 registry.PLATFORM_NAMES 对应）
var platforms = []struct{ Key, Name string }{
	{"windows", "Windows"},
	{"macos", "macOS"},
	{"linux", "Linux"},
	{"bsd", "BSD"},
	{"unix", "Unix (System V)"},
	{"android", "Android"},
	{"ios", "iOS"},
	{"uniapp", "uni-app（跨端目标：App/H5/小程序）"},
	{"any", "通用（跨平台）"},
}

// 支持的语言运行时（与 Python 侧 langdetect.LANGUAGES 对应）
var languages = []struct{ Key, Name, Note string }{
	{"python", "Python", "本工具即 Python 实现，默认可用"},
	{"ruby", "Ruby", "可用 Ruby 标准库做去重/大文件分析"},
	{"go", "Go", "本 Go 组件即其体现：单文件二进制、交叉编译"},
	{"node", "Node.js", "可做项目依赖审计 / 缓存清理"},
	{"perl", "Perl", "UNIX 传统脚本语言，做文本/日志分析"},
	{"lua", "Lua", "轻量嵌入语言，做配置/日志处理"},
	{"rust", "Rust", "可编译一次性系统工具"},
	{"java", "Java", "可做跨平台分析工具"},
	{"dotnet", ".NET", "可做跨平台分析工具"},
}

func cmdList() {
	fmt.Println()
	fmt.Println("==== sysweeper 支持的平台（跨系统） ====")
	for _, p := range platforms {
		fmt.Printf("  %-26s %s\n", p.Name, p.Key)
	}
	fmt.Println()
	fmt.Println("==== 支持的语言运行时（跨语言，仅在该语言存在时自动启用对应任务） ====")
	for _, l := range languages {
		fmt.Printf("  %-10s %s\n", l.Name, l.Note)
	}
	fmt.Println()
	fmt.Println("==== 支持的分类（分类规范整体） ====")
	for _, c := range categories {
		fmt.Printf("  %-14s %s\n", c.Label, c.Key)
	}
	fmt.Println()
	fmt.Printf("当前构建: %s %s/%s\n", goVersion(), runtimeGOOS(), runtimeGOARCH())
}
