// Command sysweeper-go 是 system-optimizer 的 Go 侧命令行组件。
//
// 目标：让同一套「分类规范整体 / 无障碍环境」口径不依赖 Python 运行时也能查询，
// 便于在没有 Python 的环境（或需要单文件二进制分发）下使用。
//
// 设计原则与 Python 侧一致：
//   - 纯标准库、零第三方依赖，交叉编译友好（GOOS/GOARCH 直接可切）；
//   - 只读探测优先，命令缺失 / 执行失败一律降级提示，不 panic、不中断；
//   - 标准引用按受众分层：国内优先国家平台/国标，对外用国际标准，必要时按地区。
//
// 子命令：
//
//	standards [--audience cn|intl|regional]  分类规范整体（分类 → 标准出处）
//	a11y                                     无障碍环境报告（ORCA / AT-SPI2）
//	list                                     列出支持的分类与平台
//	version                                  版本信息
package main

import (
	"fmt"
	"os"
)

const version = "0000.0000.0000.0034.20261026"

func usage() {
	fmt.Println("用法: sysweeper-go <子命令> [选项]")
	fmt.Println()
	fmt.Println("子命令:")
	fmt.Println("  standards [--audience cn|intl|regional]  分类规范整体（分类 → 标准出处，按受众分层）")
	fmt.Println("  a11y                                    无障碍环境报告（ORCA / AT-SPI2 协议与接口）")
	fmt.Println("  arch [--audience cn|intl|regional|us|jp|eu|de]  架构/指令集与开源硬件（龙芯/MIPS/RISC-V/OSHWA）")
	fmt.Println("  list                                    列出支持的分类与平台")
	fmt.Println("  version                                 版本信息")
	fmt.Println()
	fmt.Println("示例:")
	fmt.Println("  sysweeper-go standards --audience cn      # 国内优先：国家标准/国家平台 在前")
	fmt.Println("  sysweeper-go standards --audience intl    # 面向外国用户：国际标准在前")
	fmt.Println("  sysweeper-go a11y                         # ORCA / AT-SPI2 环境自检")
	fmt.Println("  sysweeper-go arch                         # 架构探测 + 三层标准 + GOARCH")
}

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	switch os.Args[1] {
	case "standards", "std":
		cmdStandards(os.Args[2:])
	case "a11y", "accessibility":
		cmdA11y(os.Args[2:])
	case "arch", "isa":
		cmdArch(os.Args[2:])
	case "list", "ls":
		cmdList()
	case "version", "-v", "--version":
		fmt.Printf("sysweeper-go %s (Go %s %s/%s)\n", version, goVersion(), runtimeGOOS(), runtimeGOARCH())
	case "help", "-h", "--help":
		usage()
	default:
		fmt.Fprintf(os.Stderr, "未知子命令: %s\n\n", os.Args[1])
		usage()
		os.Exit(2)
	}
}
