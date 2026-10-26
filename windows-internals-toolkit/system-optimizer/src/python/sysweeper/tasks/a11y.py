"""无障碍辅助任务（分类 accessibility）：ORCA / AT-SPI2 协议与接口。

面向 Linux ORCA 屏幕阅读器与 AT-SPI2（D-Bus 辅助技术总线 org.a11y.Bus）提供
「协议/接口自检 + 开关启用 + 只读报告」的便利能力，同时覆盖 Windows 讲述人与
macOS VoiceOver 的对应入口，保证跨系统一致。

设计原则与全局一致：
- 只读探测优先（native 通道走 sysweeper.a11y），原生接口缺失时降级为指引；
- 开关类动作用 gsettings 显式设置且可回退（rev=True 表示可撤销）；
- 纯标准库、零依赖；缺 orca / dbus / gsettings 时只提示，不报错。

标准参考（分层，见 models.CATEGORY_STANDARDS["accessibility"]）：
  国标 GB/T 37668 / GB/T 38652 → 国际 AT-SPI2 / WCAG 2.2 / WAI-ARIA / ITU-T F.790
  → 地区 EN 301 549 / Section 508 / JIS X 8341（用 standards --audience 切换）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

TASKS = [
    Task(
        id="any_a11y_report",
        platform="any",
        title="无障碍环境报告（ORCA / AT-SPI2）",
        category="accessibility",
        risk="low",
        desc="只读探测屏幕阅读器（ORCA）、AT-SPI2 辅助技术总线、读屏器自启动开关与语音后端，"
             "输出屏幕阅读器友好的纯文本报告。",
        actions=[N("common.a11y_report", "生成无障碍环境报告（只读，不修改系统）")],
        notes=[
            "协议：AT-SPI2 构建在 D-Bus 之上（辅助技术总线 org.a11y.Bus），"
            "ORCA 通过 libatspi / pyatspi2 访问应用程序的无障碍树。",
            "报告已去除框线等装饰字符，便于屏幕阅读器连续朗读。",
        ],
        caveats=["缺少 orca / dbus / gsettings 时逐项降级提示，不影响其他任务。"],
    ),
    Task(
        id="linux_atspi_bus",
        platform="linux",
        title="AT-SPI2 辅助技术总线自检",
        category="accessibility",
        risk="low",
        desc="探测 org.a11y.Bus 是否响应（dbus-send / gdbus 调 Registry.GetRegisteredEvents），"
             "判断读屏器能否收到应用的无障碍事件。",
        actions=[N("common.a11y_atspi_bus", "探测 org.a11y.Bus 是否可用（只读）")],
        notes=[
            "接口：org.a11y.atspi.Registry（对象路径 /org/a11y/atspi/registry）。",
            "未响应通常是 at-spi-bus-launcher 未启动或处于非图形会话（SSH/TTY）。",
        ],
        caveats=["纯 SSH / 无图形会话环境一般不可用，属正常现象。"],
    ),
    Task(
        id="linux_orca_status",
        platform="linux",
        title="ORCA 屏幕阅读器状态",
        category="accessibility",
        risk="low",
        desc="读取 ORCA 版本与「是否随会话自动启动」开关（gsettings screen-reader-enabled）。",
        actions=[N("common.a11y_orca_status", "读取 ORCA 版本与自启动开关（只读）")],
        notes=[
            "开关：org.gnome.desktop.a11y.applications screen-reader-enabled。",
            "未安装 ORCA 时提示可用包管理器安装（gnome-orca / orca）。",
        ],
    ),
    Task(
        id="linux_orca_enable",
        platform="linux",
        title="启用屏幕阅读器自启动（ORCA）",
        category="accessibility",
        risk="low",
        desc="把 GNOME 的 screen-reader-enabled 置为 true，使 ORCA 随会话自动启动。",
        actions=[S(
            'if command -v gsettings >/dev/null 2>&1; then '
            'gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled true; '
            'else echo "未找到 gsettings（非 GNOME 会话），跳过"; fi',
            "开启 screen-reader-enabled（可用 false 回退）", rev=True)],
        notes=[
            "回退：gsettings set org.gnome.desktop.a11y.applications screen-reader-enabled false",
            "启动/重启 ORCA：orca --replace；设置：orca --setup。",
            "配置目录：~/.local/share/orca（首次运行后生成）。",
        ],
        caveats=["仅在 GNOME/兼容桌面生效；KDE 等桌面请用其自带无障碍设置。"],
    ),
    Task(
        id="linux_atspi_toolkit",
        platform="linux",
        title="启用 AT-SPI 辅助技术接口（toolkit-accessibility）",
        category="accessibility",
        risk="low",
        desc="开启 GNOME 的 toolkit-accessibility，让 GTK/Qt 应用向 AT-SPI2 总线暴露无障碍树。",
        actions=[S(
            'if command -v gsettings >/dev/null 2>&1; then '
            'gsettings set org.gnome.desktop.interface toolkit-accessibility true; '
            'else echo "未找到 gsettings（非 GNOME 会话），跳过"; fi',
            "开启 toolkit-accessibility（可用 false 回退）", rev=True)],
        notes=[
            "该开关是 AT-SPI2 生效的前提之一：应用需向 org.a11y.Bus 注册无障碍对象。",
            "回退：gsettings set org.gnome.desktop.interface toolkit-accessibility false",
        ],
        caveats=["开启后应用会额外暴露无障碍接口，资源占用略有增加（通常可忽略）。"],
    ),
    Task(
        id="win_narrator_hint",
        platform="windows",
        title="Windows 讲述人（Narrator）入口",
        category="accessibility",
        risk="low",
        desc="给出 Windows 讲述人的开关与快捷键指引（对应 Linux ORCA 的读屏能力）。",
        actions=[M(
            "Win+Ctrl+Enter 启动/退出讲述人；设置 → 辅助功能 → 讲述人 可配置语音与详细程度。"
            "（命令行可选：start narrator）",
            "讲述人开关与配置指引")],
        notes=[
            "Windows 的无障碍接口为 UI Automation（UIA）与 MSAA，与 Linux AT-SPI2 属同类机制。",
            "标准参考：GB/T 37668（国标）/ WCAG 2.2（国际）/ Section 508（地区）。",
        ],
    ),
    Task(
        id="mac_voiceover_hint",
        platform="macos",
        title="macOS VoiceOver 入口",
        category="accessibility",
        risk="low",
        desc="给出 macOS VoiceOver 的开关与快捷键指引（对应 Linux ORCA 的读屏能力）。",
        actions=[M(
            "Cmd+F5 启动/关闭 VoiceOver；Cmd+F5 按住 Control+Option 组合可朗读项目。"
            "系统设置 → 辅助功能 → VoiceOver 可配置语音与 rotor。",
            "VoiceOver 开关与配置指引")],
        notes=[
            "macOS 的无障碍接口为 NSAccessibility（AX API），与 Linux AT-SPI2 属同类机制。",
        ],
    ),
    Task(
        id="any_a11y_multi",
        platform="any",
        title="多系统无障碍适配报告（Windows/macOS/Linux/Android/iOS/鸿蒙）",
        category="accessibility",
        risk="low",
        desc="按各系统各自的协议与接口只读探测屏幕阅读器状态：Windows 讲述人（UI Automation/MSAA）、"
             "macOS VoiceOver（NSAccessibility AX）、Linux ORCA（AT-SPI2/D-Bus）、"
             "Android TalkBack（AccessibilityService/adb settings secure）、"
             "iOS VoiceOver（设备端）、鸿蒙屏幕朗读（AccessibilityExtensionAbility/hdc）。",
        actions=[N("common.a11y_multi_report", "多系统无障碍只读探测报告")],
        notes=[
            "适配原则：每个系统用**它自己**的原生无障碍接口，不做跨系统猜测；"
            "非当前平台一律降级为「请在目标系统操作」的指引，不报错。",
            "Windows: HKCU\\Software\\Microsoft\\Narrator + Win+Ctrl+Enter；"
            "macOS: com.apple.universalaccess 域 + Cmd+F5；"
            "Linux: org.a11y.Bus + gsettings screen-reader-enabled；"
            "Android: adb shell settings get secure accessibility_enabled；"
            "iOS/鸿蒙: 只能在设备端设置中开启。",
        ],
        caveats=["iOS 与鸿蒙不允许主机直接开启读屏器，本任务只给设备端指引。"],
    ),
    Task(
        id="any_a11y_docs",
        platform="any",
        title="多系统无障碍权威文档（协议与接口出处）",
        category="accessibility",
        risk="low",
        desc="列出各系统无障碍的权威文档与对应协议/接口：AT-SPI2、UI Automation、"
             "NSAccessibility、AccessibilityService、AccessibilityExtensionAbility，"
             "并给出 WCAG 2.2 / ISO 9241-171 / GB/T 37668 等标准出处。",
        actions=[N("common.a11y_docs_report", "列出多系统无障碍权威文档")],
        notes=[
            "文档来源：GNOME docs、Microsoft Learn、Apple Developer、"
            "Android Developers、华为开发者文档、W3C、ISO、SAC。",
        ],
    ),
    Task(
        id="win_narrator_enable",
        platform="windows",
        title="启用 Windows 讲述人（UI Automation 通道）",
        category="accessibility",
        risk="low",
        desc="给出 Windows 讲述人的启用命令与设置入口（对应 Linux ORCA 自启动开关）。",
        actions=[M(
            "Win+Ctrl+Enter 启动讲述人；或 PowerShell: Start-Process narrator。"
            "完整配置在「设置 → 辅助功能 → 讲述人」。",
            "讲述人启用指引（Windows 侧操作）")],
        notes=[
            "接口：UI Automation（UIA）/ MSAA；应用需实现 IUIAutomation 提供者的属性与控件模式。",
            "注册表仅作**只读**探测（HKCU\\Software\\Microsoft\\Narrator），不主动改写。",
        ],
        caveats=["Windows 上改注册表有风险，本任务只给 GUI 与命令行入口，不写注册表。"],
    ),
    Task(
        id="mac_voiceover_enable",
        platform="macos",
        title="启用 macOS VoiceOver（NSAccessibility 通道）",
        category="accessibility",
        risk="low",
        desc="给出 macOS VoiceOver 的启用快捷键与设置入口（对应 Linux ORCA 自启动开关）。",
        actions=[M(
            "Cmd+F5 开启/关闭 VoiceOver；或 系统设置 → 辅助功能 → VoiceOver。"
            "只读查询：defaults read com.apple.universalaccess voiceOverOnOffKey",
            "VoiceOver 启用指引（macOS 侧操作）")],
        notes=[
            "接口：NSAccessibility（AX API），AXUIElement 暴露 AXRole/AXTitle/AXValue 等属性。",
        ],
        caveats=["不写 defaults（避免破坏用户偏好），启用请在系统设置中操作。"],
    ),
    Task(
        id="android_talkback_enable",
        platform="android",
        title="Android TalkBack 状态与启用指引（adb 只读）",
        category="accessibility",
        risk="low",
        desc="只读查询 Android 无障碍服务开关状态，并给出 TalkBack 启用指引。",
        actions=[N("common.a11y_multi_report", "查询 Android 无障碍状态（只读）")],
        notes=[
            "只读：adb shell settings get secure accessibility_enabled / "
            "enabled_accessibility_services。",
            "启用：设置 → 无障碍 → TalkBack；用 adb settings put secure 属变更，默认不做。",
        ],
        caveats=["需要设备已授权 USB 调试；未连接设备时降级为指引。"],
        opt_in=True,
    ),
    Task(
        id="harmony_screenreader_enable",
        platform="harmony",
        title="鸿蒙屏幕朗读（AccessibilityExtensionAbility）指引",
        category="accessibility",
        risk="low",
        desc="给出鸿蒙系统「屏幕朗读」的启用入口与无障碍扩展能力说明。",
        actions=[M(
            "设置 → 辅助功能 → 无障碍 → 屏幕朗读（ScreenReader）开启；"
            "开发者侧通过 AccessibilityExtensionAbility 提供无障碍扩展。",
            "鸿蒙屏幕朗读启用指引（设备端操作）")],
        notes=[
            "接口：HarmonyOS Accessibility（AccessibilityExtensionAbility）；"
            "主机侧可用 hdc shell 做只读查询。",
        ],
        caveats=["同 iOS，主机不允许直接开启读屏器，只给指引。"],
    ),
    Task(
        id="any_a11y_standards",
        platform="any",
        title="无障碍标准对照（国标/国际/地区）",
        category="accessibility",
        risk="low",
        desc="列出无障碍分类的三层标准出处，并按受众（国内/对外/按地区）给出引用优先级。",
        actions=[M(
            "国标：GB/T 37668 信息技术 无障碍 通用设计规范、GB/T 38652 网页无障碍要求；"
            "国际：AT-SPI2（GNOME）、W3C WCAG 2.2 / WAI-ARIA 1.2、ITU-T F.790；"
            "地区：EN 301 549（欧盟）、Section 508（美国）、JIS X 8341（日本）。"
            "用 `standards --audience cn|intl|regional` 查看切换后的优先级。",
            "无障碍分层标准清单与引用策略")],
        notes=[
            "引用策略：国内优先国家平台/国家标准；给外国人用改用国际标准；"
            "个别场景按所在国家/地区标准执行。",
        ],
    ),
]
