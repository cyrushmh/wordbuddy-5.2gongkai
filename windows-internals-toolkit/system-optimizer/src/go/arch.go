package main

// arch.go：架构 / 指令集（ISA）与开源硬件查询，与 Python 侧 arch.py 同口径。
//
// 覆盖龙芯 LoongArch（国产自主）、MIPS、RISC-V（开源 ISA）、OpenPOWER、
// OpenRISC、x86、ARM，以及开源硬件（OSHWA / CERN OHL / DIN SPEC 3105）。
//
// 设计原则：纯标准库、只读探测（用 runtime.GOARCH + uname），
// 缺失即降级提示，不 panic。

import (
	"fmt"
	"os/exec"
	"runtime"
	"strings"
)

// goarchToKey 把 Go 的 GOARCH 值归一化成架构键。
var goarchToKey = map[string]string{
	"loong64":  "loongarch",
	"mips":     "mips",
	"mipsle":   "mips",
	"mips64":   "mips",
	"mips64le": "mips",
	"riscv64":  "riscv",
	"riscv":    "riscv",
	"ppc64":    "openpower",
	"ppc64le":  "openpower",
	"amd64":    "x86",
	"386":      "x86",
	"arm64":    "arm",
	"arm":      "arm",
}

// archGoarch 架构键 → 交叉构建时的 GOARCH（首选值）。
var archGoarch = map[string]string{
	"loongarch":     "loong64",
	"mips":          "mips64le",
	"riscv":         "riscv64",
	"openpower":     "ppc64le",
	"openrisc":      "or1k",
	"x86":           "amd64",
	"arm":           "arm64",
	"open_hardware": "",
}

// archToolchain 架构键 → 交叉工具链三元组提示。
var archToolchain = map[string]string{
	"loongarch": "loong64 / loongarch64-linux-gnu-*（优先取龙芯/系统厂商源与原生包）",
	"mips":      "mips64el-linux-gnuabi64-* / mipsel-linux-gnu-*（大端 mips 与小端 mipsel ABI 不通用）",
	"riscv":     "riscv64-linux-gnu-*（常用 -march=rv64gc -mabi=lp64d）",
	"openpower": "powerpc64le-linux-gnu-*（小端 ppc64le 为主流 ABI）",
	"openrisc":  "or1k-elf-* / or1k-linux-gnu-*（FPGA / 教学场景）",
	"x86":       "本机原生；可用 -march=native（便携分发慎用）",
	"arm":       "aarch64-linux-gnu-*（注意 arm64 与 armhf 变体）",
}

// Arch 描述一个架构及其三层标准出处。
type Arch struct {
	Key           string
	Name          string
	Standard      string
	Org           string
	National      []string
	International []string
	Regional      []string
	Advice        string
}

var archs = []Arch{
	{
		Key:      "loongarch",
		Name:     "龙芯架构 LoongArch（龙架构）",
		Standard: "LoongArch 指令集架构参考手册（龙芯中科技术股份有限公司）",
		Org:      "龙芯中科（Loongson Technology）",
		National: []string{
			"龙芯 LoongArch 指令集架构（国产自主，国家标准以全国标准信息公共服务平台 std.samr.gov.cn 检索为准）",
			"国产处理器生态适配相关国家标准（GB/T 系列，见国家平台 std.samr.gov.cn）",
		},
		International: []string{
			"LoongArch Reference Manual（基础架构 / 向量 / 虚拟化卷，龙芯中科发布）",
		},
		Advice: "优先取龙芯/系统厂商提供的源与原生包；二进制翻译（LBT）可跑 x86/ARM 程序但有损耗。",
	},
	{
		Key:      "mips",
		Name:     "MIPS 架构（MIPS32 / MIPS64）",
		Standard: "MIPS Architecture for Programmers（MIPS32 / MIPS64 Release 6）",
		Org:      "MIPS Technologies（现 MIPS Open，Wave Computing 开设计划）",
		National: []string{
			"国产化替代：龙芯/MIPS 平台适配相关国家标准（见国家平台 std.samr.gov.cn 检索）",
		},
		International: []string{
			"MIPS Architecture for Programmers Volume I-A（MIPS32 Release 6 指令集）",
			"MIPS Architecture for Programmers Volume II-A（MIPS64 Release 6 指令集）",
			"MIPS Open（开源指令集计划，2019）",
		},
		Advice: "老龙芯（MIPS 授权）与路由器/嵌入式设备多为 MIPS；小端（mipsel）与大端（mips）ABI 不通用。",
	},
	{
		Key:      "riscv",
		Name:     "RISC-V（开源指令集架构）",
		Standard: "RISC-V Instruction Set Specifications（RV32/64 基础 + 扩展）",
		Org:      "RISC-V International（瑞士，会员制标准组织）",
		National: []string{
			"中国 RISC-V 产业联盟（CRVA）/ 开放指令生态相关标准（国家平台 std.samr.gov.cn 可检索）",
		},
		International: []string{
			"RISC-V Unprivileged ISA Specification（RV32I/RV64I 基础 + 标准扩展）",
			"RISC-V Privileged Architecture Specification",
			"RISC-V Profiles（RVA20 / RVA22 / RVA23，ratified 兼容性规范）",
		},
		Advice: "编译用 -march=rv64gc -mabi=lp64d，优先取发行版原生包，避免二进制翻译损耗。",
	},
	{
		Key:      "openpower",
		Name:     "OpenPOWER / Power ISA（开放处理器架构）",
		Standard: "Power ISA（OpenPOWER Foundation 开放规范）",
		Org:      "OpenPOWER Foundation（Linux Foundation）",
		International: []string{
			"Power ISA Specification（OpenPOWER Foundation）",
			"Microwatt 开源 POWER 软核（OpenPOWER / CHIPS Alliance）",
		},
		Advice: "ppc64le 为主流小端 ABI；服务器场景注意 NUMA 与 SMT 调度。",
	},
	{
		Key:      "openrisc",
		Name:     "OpenRISC（开源处理器核）",
		Standard: "OpenRISC 1000 Architecture（OpenRISC 社区 / OpenCores）",
		Org:      "OpenRISC（OpenCores 社区，现由 FOSSi Foundation 协调）",
		International: []string{
			"OpenRISC 1000 Architecture Manual（OpenCores / FOSSi）",
			"GNU 工具链 or1k 后端（gcc / binutils）",
		},
		Advice: "资源受限或 FPGA 运行环境，优化以精简为主：清缓存、关无用服务。",
	},
	{
		Key:      "x86",
		Name:     "x86 / x86-64（AMD64 / Intel 64）",
		Standard: "Intel SDM / AMD APM（x86-64 架构规范）",
		Org:      "Intel / AMD（架构规范由厂商维护）",
		National: []string{
			"兆芯 / 海光 x86 国产处理器适配相关国家标准（见国家平台 std.samr.gov.cn）",
		},
		International: []string{
			"Intel Software Developer Manual（SDM）",
			"AMD Architecture Programmer's Manual（APM）",
			"x86-64 ABI（System V AMD64 ABI / Microsoft x64 calling convention）",
		},
		Advice: "编译可用 -march=native；微码更新由系统固件/发行版提供。",
	},
	{
		Key:      "arm",
		Name:     "ARM / AArch64",
		Standard: "ARM Architecture Reference Manual（ARMv8-A / ARMv9-A）",
		Org:      "Arm Ltd.",
		National: []string{
			"飞腾 / 鲲鹏 ARM 国产处理器适配相关国家标准（见国家平台 std.samr.gov.cn）",
		},
		International: []string{
			"ARM Architecture Reference Manual（Armv8-A / Armv9-A）",
			"Arm SystemReady（固件/启动兼容认证）",
		},
		Advice: "ARM 服务器注意 big.LITTLE 调度与 NUMA；容器镜像需匹配 arm64 变体。",
	},
	{
		Key:      "open_hardware",
		Name:     "开源硬件（Open Source Hardware）认证与许可",
		Standard: "OSHWA 认证 / CERN Open Hardware Licence（OHL）/ DIN SPEC 3105",
		Org:      "OSHWA（Open Source Hardware Association）、CERN、DIN（德国标准化学会）",
		National: []string{
			"开源硬件相关国家标准（见国家平台 std.samr.gov.cn 检索；开源芯片/开放指令生态联盟规范）",
		},
		International: []string{
			"OSHWA Open Source Hardware Definition 1.0 + 认证 UID（oshwa.org）",
			"CERN Open Hardware Licence（OHL v2，强 copyleft 硬件许可）",
			"RISC-V International（开放 ISA，无授权费）",
			"CHIPS Alliance（开放芯片设计与互连标准）",
		},
		Regional: []string{
			"DIN SPEC 3105（德国：开放硬件标准化要求，地区标准）",
			"欧盟开放硬件相关实践（EUPL / 开源硬件倡议，地区标准）",
		},
		Advice: "复用硬件设计前核对许可（CERN OHL / CC 文档许可）与 OSHWA 认证 UID。",
	},
}

// currentArchKey 当前架构键（用 runtime.GOARCH，必要时 uname -m 兜底）。
func currentArchKey() string {
	if k, ok := goarchToKey[runtime.GOARCH]; ok {
		return k
	}
	if out, err := exec.Command("uname", "-m").Output(); err == nil {
		m := strings.ToLower(strings.TrimSpace(string(out)))
		for _, a := range archs {
			for _, um := range unameMachines(a.Key) {
				if m == um {
					return a.Key
				}
			}
		}
	}
	return "unknown"
}

// unameMachines 架构键对应的 uname -m 取值（仅列主流项）。
func unameMachines(key string) []string {
	switch key {
	case "loongarch":
		return []string{"loongarch64", "loongarch32", "loong64", "loong32"}
	case "mips":
		return []string{"mips", "mips64", "mipsel", "mips64el"}
	case "riscv":
		return []string{"riscv64", "riscv32", "rv64", "rv32"}
	case "openpower":
		return []string{"ppc64le", "ppc64", "powerpc64", "powerpc"}
	case "openrisc":
		return []string{"or1k", "openrisc"}
	case "x86":
		return []string{"x86_64", "amd64", "i686", "i386"}
	case "arm":
		return []string{"aarch64", "arm64", "armv7l", "armv8l"}
	}
	return nil
}

func findArch(key string) (Arch, bool) {
	for _, a := range archs {
		if a.Key == key {
			return a, true
		}
	}
	return Arch{}, false
}

// regionRank 地区条目排序：命中该地区为 0，其余为 1。
func regionRank(item, region string) int {
	keywords := map[string][]string{
		"us": {"美国", "NIST", "Section 508", "ENERGY STAR", "EPA"},
		"jp": {"日本", "JIS", "APPI", "個人情報"},
		"eu": {"欧盟", "GDPR", "EN 301 549", "ErP", "EUPL"},
		"de": {"德国", "DIN"},
	}
	for _, k := range keywords[region] {
		if strings.Contains(item, k) {
			return 0
		}
	}
	return 1
}

// archAudienceOrder 按受众返回层级顺序。
func archAudienceOrder(audience string) []string {
	switch audience {
	case "intl":
		return []string{"international", "national", "regional"}
	case "regional", "us", "jp", "eu", "de":
		return []string{"regional", "national", "international"}
	}
	return []string{"national", "international", "regional"}
}

// archByTier 取某架构某层的标准条目。
func (a Arch) byTier(tier string) []string {
	switch tier {
	case "national":
		return a.National
	case "international":
		return a.International
	case "regional":
		return a.Regional
	}
	return nil
}

func cmdArch(args []string) {
	audience := "cn"
	for i := 0; i < len(args); i++ {
		if args[i] == "--audience" && i+1 < len(args) {
			audience = args[i+1]
		}
	}
	audienceLabel := map[string]string{
		"cn": "国内（优先国家平台/国家标准）", "intl": "面向外国用户（优先国际标准）",
		"regional": "按国家/地区执行", "us": "美国", "jp": "日本", "eu": "欧盟", "de": "德国",
	}
	label := audienceLabel[audience]
	if label == "" {
		label = audience
	}

	key := currentArchKey()
	fmt.Println()
	fmt.Println("==== 架构 / 指令集报告（sysweeper-go）====")
	fmt.Printf("GOARCH: %s    GOOS: %s    归一化架构键: %s\n", runtime.GOARCH, runtime.GOOS, key)
	fmt.Printf("标准引用受众: %s\n", label)
	fmt.Println()

	a, ok := findArch(key)
	if !ok {
		fmt.Printf("（架构 %s 未收录标准条目，可在 data/arch.json 补充）\n", key)
	} else {
		fmt.Printf("架构: %s\n", a.Name)
		fmt.Printf("标准: %s（%s）\n", a.Standard, a.Org)
		for _, tier := range archAudienceOrder(audience) {
			items := a.byTier(tier)
			if len(items) == 0 {
				continue
			}
			if audience == "us" || audience == "jp" || audience == "eu" || audience == "de" {
				// 稳定排序：该地区条目排前
				sorted := make([]string, 0, len(items))
				var hit, rest []string
				for _, it := range items {
					if regionRank(it, audience) == 0 {
						hit = append(hit, it)
					} else {
						rest = append(rest, it)
					}
				}
				sorted = append(sorted, hit...)
				sorted = append(sorted, rest...)
				items = sorted
			}
			mark := " "
			if len(archAudienceOrder(audience)) > 0 && archAudienceOrder(audience)[0] == tier {
				mark = "①"
			}
			for _, it := range items {
				fmt.Printf("  %s [%s] %s\n", mark, tierTag(tier), it)
			}
		}
		if a.Advice != "" {
			fmt.Printf("建议: %s\n", a.Advice)
		}
	}

	fmt.Println()
	fmt.Printf("工具链: %s\n", archToolchain[key])
	if ga := archGoarch[key]; ga != "" {
		fmt.Printf("Go 交叉构建: GOARCH=%s go build ./...\n", ga)
	} else {
		fmt.Println("Go 交叉构建: go build ./...（该架构未收录 GOARCH 映射）")
	}

	fmt.Println()
	fmt.Println("-- 开源硬件（OSHWA / CERN OHL / DIN SPEC 3105）--")
	if oh, ok := findArch("open_hardware"); ok {
		fmt.Printf("  标准: %s（%s）\n", oh.Standard, oh.Org)
		for _, it := range oh.International {
			fmt.Printf("  [国际] %s\n", it)
		}
		for _, it := range oh.Regional {
			fmt.Printf("  [地区] %s\n", it)
		}
		for _, it := range oh.National {
			fmt.Printf("  [国标] %s\n", it)
		}
	}

	fmt.Println()
	fmt.Println("已收录架构:")
	for _, x := range archs {
		ga := archGoarch[x.Key]
		if ga == "" {
			ga = "-"
		}
		fmt.Printf("  · %-14s GOARCH=%-9s %s\n", x.Key, ga, x.Name)
	}
}
