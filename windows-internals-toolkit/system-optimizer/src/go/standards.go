package main

import (
	"fmt"
)

// 标准引用的三个层级（与 Python 侧 STANDARD_TIERS 一致）
const (
	tierNational      = "national"
	tierInternational = "international"
	tierRegional      = "regional"
)

var nationalPortal = "全国标准信息公共服务平台（std.samr.gov.cn，国家标准化管理委员会）"

// Category 描述一个优化分类及其三层标准出处
type Category struct {
	Key           string
	Label         string
	Doc           string
	National      []string
	International []string
	Regional      []string
}

// categories 与 Python models.CATEGORY_STANDARDS 保持同口径（精简版，含关键国标/国际/地区条目）
var categories = []Category{
	{
		Key: "cleanup", Label: "清理垃圾", Doc: "（各平台原生缓存/临时目录规范）",
		International: []string{
			"XDG Base Directory（~/.cache，freedesktop 事实规范）",
			"Apple 用户库规范（~/Library/Caches）",
			"Windows Temp / 回收站（Shell32）",
		},
	},
	{
		Key: "optimize", Label: "性能优化", Doc: "（ACPI P-state/C-state、调度与电源规范）",
		National: []string{"中国能效标识（GB 24850；国家平台：" + nationalPortal + "）"},
		International: []string{
			"ACPI Specification（UEFI Forum）",
			"IEEE 802.11 节能模式（WMM / Power Save）",
			"Linux kernel sysctl 调优",
		},
		Regional: []string{"美国 ENERGY STAR（EPA）", "欧盟 ErP 生态设计指令（EU 2019/1781）", "日本 JIS C 能效"},
	},
	{
		Key: "privacy", Label: "隐私清理", Doc: "（隐私 / 数据最小化原则）",
		National:      []string{"《个人信息保护法》(PIPL，中国)；国家平台：" + nationalPortal},
		International: []string{"OWASP 隐私实践", "RFC 7858 / RFC 8484（DoT / DoH）", "ISO/IEC 27001"},
		Regional:      []string{"欧盟 GDPR", "美国 NIST SP 800-53", "日本 個人情報保護法（APPI）"},
	},
	{
		Key: "maintenance", Label: "系统维护", Doc: "data/hardware.json / data/versions.json",
		International: []string{"T13 / ATA8-ACS（S.M.A.R.T.）", "ATA TRIM（DATA SET MANAGEMENT）", "LSB（/etc/os-release）"},
		Regional:      []string{"美国 NIST SP 800-53（配置/维护控制）", "日本 JIS X 系列"},
	},
	{
		Key: "network", Label: "网络/协议优化", Doc: "data/network_standards.json",
		National:      []string{"中国通信行业标准 YD/T 系列（路由 / 接入）；国家平台：" + nationalPortal},
		International: []string{"RFC 4941 / RFC 8200 / RFC 3168 / RFC 9002（IETF）", "IEEE 802.11", "ITU-T Y.1541 / G.992 / G.711"},
		Regional:      []string{"美国 NIST SP 800-119（IPv6 安全部署）", "欧盟 EN 301 549"},
	},
	{
		Key: "fonts", Label: "字体/字符标准", Doc: "data/fonts_standards.json",
		National:      []string{"GB 18030《信息技术 中文编码字符集》（强制国标，向下兼容 Unicode）；国家平台：" + nationalPortal},
		International: []string{"Unicode 18.0.0 / ISO-IEC 10646", "OpenType（ISO/IEC 14496-22）", "W3C WOFF 2.0", "UAX #15（Unicode 规范化）"},
		Regional:      []string{"日本 JIS X 0213"},
	},
	{
		Key: "accessibility", Label: "无障碍辅助", Doc: "sysweeper/a11y.py（ORCA / AT-SPI2 协议与接口）",
		National:      []string{"GB/T 37668《信息技术 无障碍 通用设计规范》；国家平台：" + nationalPortal, "GB/T 38652 网页无障碍要求", "YD/T 系列无障碍通信标准（工信部）"},
		International: []string{"AT-SPI2（GNOME at-spi2-core，D-Bus org.a11y.Bus）", "W3C WCAG 2.2", "W3C WAI-ARIA 1.2", "ITU-T F.790（电信无障碍指南）"},
		Regional:      []string{"欧盟 EN 301 549", "美国 Section 508", "日本 JIS X 8341"},
	},
}

// tierOrder 按受众返回层级优先顺序
func tierOrder(audience string) []string {
	switch audience {
	case "intl", "international":
		return []string{tierInternational, tierNational, tierRegional}
	case "regional", "region":
		return []string{tierRegional, tierNational, tierInternational}
	default: // cn
		return []string{tierNational, tierInternational, tierRegional}
	}
}

func tierTag(tier string) string {
	switch tier {
	case tierNational:
		return "国标"
	case tierInternational:
		return "国际"
	case tierRegional:
		return "地区"
	}
	return tier
}

func (c Category) byTier(tier string) []string {
	switch tier {
	case tierNational:
		return c.National
	case tierInternational:
		return c.International
	case tierRegional:
		return c.Regional
	}
	return nil
}

func cmdStandards(args []string) {
	audience := "cn"
	showTasks := false
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--audience":
			if i+1 < len(args) {
				audience = args[i+1]
				i++
			}
		case "-a":
			if i+1 < len(args) {
				audience = args[i+1]
				i++
			}
		case "--tasks":
			showTasks = true
		}
	}

	order := tierOrder(audience)
	fmt.Println()
	fmt.Println("==== 分类规范整体（分类 → 标准出处，按受众分层） ====")
	fmt.Printf("受众: %s    引用策略: 国内优先国家平台/国标 → 对外用国际标准 → 必要时按地区\n", audience)
	fmt.Printf("国家平台: %s\n", nationalPortal)
	for _, c := range categories {
		fmt.Printf("\n■ %s（%s）\n", c.Label, c.Key)
		if c.Doc != "" {
			fmt.Printf("    标准文档: %s\n", c.Doc)
		}
		for _, tier := range order {
			mark := " "
			if tier == order[0] {
				mark = "①" // 当前受众的优先层
			}
			for _, s := range c.byTier(tier) {
				fmt.Printf("    %s [%s] %s\n", mark, tierTag(tier), s)
			}
		}
		if showTasks {
			fmt.Printf("    （任务清单见 Python 版: python -m sysweeper list --category %s）\n", c.Key)
		}
	}
	fmt.Println()
	fmt.Println("（完整任务清单与执行能力见 Python 版 sysweeper；Go 组件提供同口径的查询与自检）")
}
