package main

import (
	"fmt"
	"os/exec"
	"strings"
)

// AT-SPI2 协议常量（与 Python 侧 a11y.py 一致）
const (
	atspiBus          = "org.a11y.Bus"
	atspiRegistryPath = "/org/a11y/atspi/registry"
	atspiRegistryIF   = "org.a11y.atspi.Registry"
	atspiLauncher     = "at-spi-bus-launcher"
	gsSchema          = "org.gnome.desktop.a11y.applications"
	gsKeyScreenReader = "screen-reader-enabled"
	gsSchemaInterface = "org.gnome.desktop.interface"
	gsKeyToolkit      = "toolkit-accessibility"
)

// AT-SPI2 常用接口（供读屏器/辅助技术调试时引用）
var atspiInterfaces = []string{
	"org.a11y.atspi.Accessible",
	"org.a11y.atspi.Action",
	"org.a11y.atspi.Application",
	"org.a11y.atspi.Collection",
	"org.a11y.atspi.Component",
	"org.a11y.atspi.Document",
	"org.a11y.atspi.EditableText",
	"org.a11y.atspi.Hyperlink",
	"org.a11y.atspi.Hypertext",
	"org.a11y.atspi.Image",
	"org.a11y.atspi.Selection",
	"org.a11y.atspi.Socket",
	"org.a11y.atspi.Table",
	"org.a11y.atspi.Text",
	"org.a11y.atspi.Value",
}

func lookPath(name string) string {
	p, err := exec.LookPath(name)
	if err != nil {
		return ""
	}
	return p
}

// run 执行一条命令，返回 (是否成功, 输出)。失败也返回，不 panic。
func run(name string, args ...string) (bool, string) {
	cmd := exec.Command(name, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return false, strings.TrimSpace(string(out))
	}
	return true, strings.TrimSpace(string(out))
}

func cmdA11y(args []string) {
	fmt.Println()
	fmt.Println("==== 无障碍环境报告（ORCA / AT-SPI2） ====")
	fmt.Println("（Go 组件：只读探测，命令缺失时逐项降级提示）")

	// ORCA
	if p := lookPath("orca"); p != "" {
		if ok, out := run("orca", "--version"); ok {
			fmt.Printf("ORCA 安装      : 是 — %s\n", firstLine(out))
		} else {
			fmt.Printf("ORCA 安装      : 是 — 版本读取失败: %s\n", firstLine(out))
		}
	} else {
		fmt.Println("ORCA 安装      : 否 — 未安装 orca（可用包管理器安装 gnome-orca / orca）")
	}

	// AT-SPI2 总线
	switch {
	case lookPath("dbus-send") != "":
		ok, out := run("dbus-send", "--bus="+atspiBus, "--dest="+atspiRegistryIF,
			"--type=method_call", "--print-reply", atspiRegistryPath,
			atspiRegistryIF+".GetRegisteredEvents")
		if ok {
			fmt.Println("AT-SPI2 总线   : 可用 — org.a11y.Bus 已响应")
		} else {
			fmt.Printf("AT-SPI2 总线   : 不可用 — %s\n", firstLine(out))
		}
	case lookPath("gdbus") != "":
		ok, out := run("gdbus", "call", "--bus="+atspiBus, "--dest="+atspiRegistryIF,
			"--object-path", atspiRegistryPath, "--method", atspiRegistryIF+".GetRegisteredEvents")
		if ok {
			fmt.Println("AT-SPI2 总线   : 可用 — gdbus 探测成功")
		} else {
			fmt.Printf("AT-SPI2 总线   : 不可用 — %s\n", firstLine(out))
		}
	default:
		fmt.Println("AT-SPI2 总线   : 无法探测 — 未找到 dbus-send / gdbus（可安装 dbus-tools）")
	}

	// 读屏器自启动开关
	if lookPath("gsettings") != "" {
		ok, out := run("gsettings", "get", gsSchema, gsKeyScreenReader)
		if ok {
			fmt.Printf("读屏器自启动   : %s（%s）\n", boolText(out), out)
		} else {
			fmt.Printf("读屏器自启动   : 读取失败 — %s\n", firstLine(out))
		}
		ok2, out2 := run("gsettings", "get", gsSchemaInterface, gsKeyToolkit)
		if ok2 {
			fmt.Printf("AT-SPI 接口暴露: %s（%s）\n", boolText(out2), out2)
		}
	} else {
		fmt.Println("读屏器自启动   : 无法探测 — 未找到 gsettings（非 GNOME 会话）")
	}

	// 语音后端
	backend := ""
	for _, b := range []struct{ cmd, name string }{
		{"spd-say", "speech-dispatcher（spd-say，ORCA 默认语音服务）"},
		{"espeak-ng", "eSpeak NG"},
		{"espeak", "eSpeak"},
		{"say", "macOS say"},
	} {
		if lookPath(b.cmd) != "" {
			backend = b.name
			break
		}
	}
	if backend == "" {
		fmt.Println("语音后端       : （无——结果以纯文本呈现，便于复制给读屏器）")
	} else {
		fmt.Printf("语音后端       : %s\n", backend)
	}

	fmt.Println()
	fmt.Println(strings.Repeat("-", 68))
	fmt.Println("协议与接口（AT-SPI2 / D-Bus）：")
	fmt.Printf("  辅助技术总线: %s（由 %s 拉起）\n", atspiBus, atspiLauncher)
	fmt.Printf("  注册表对象  : %s (%s)\n", atspiRegistryPath, atspiRegistryIF)
	fmt.Printf("  常用接口    : %s …\n", strings.Join(atspiInterfaces[:4], ", "))
	fmt.Printf("  自检命令    : dbus-send --bus=%s --dest=%s --type=method_call --print-reply %s %s.GetRegisteredEvents\n",
		atspiBus, atspiRegistryIF, atspiRegistryPath, atspiRegistryIF)
	fmt.Println("  读屏器      : orca --replace（重启）/ orca --setup（设置）")
	fmt.Printf("  开关        : gsettings set %s %s true\n", gsSchema, gsKeyScreenReader)

	fmt.Println()
	fmt.Println("标准参考（按受众分层，见 standards --audience）：")
	fmt.Println("  国标: GB/T 37668 信息技术 无障碍 通用设计规范 / GB/T 38652")
	fmt.Println("  国际: W3C WCAG 2.2 / WAI-ARIA 1.2 / AT-SPI2（GNOME at-spi2-core）")
	fmt.Println("  地区: EN 301 549（欧盟）/ Section 508（美国）/ JIS X 8341（日本）")
}

func boolText(v string) string {
	if strings.Contains(strings.ToLower(v), "true") {
		return "已启用"
	}
	return "未启用"
}

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return s[:i]
	}
	return s
}
