"""其他系统软件（systemd / D-Bus / NetworkManager / PipeWire / BlueZ / udev / polkit / Wayland）
的核对、清理与优化任务（platform="linux"）。

「触类旁通、举一反三」：既然 Linux 内核（硬件/软件/网络）与桌面环境（GNOME/KDE/XFCE）
的优化都能各自引用权威文档，那么**其余系统软件同样按自身的协议与接口**核对与优化：

- systemd        : 单元指令 + D-Bus org.freedesktop.systemd1 + journal 字段
- D-Bus          : D-Bus Specification + Introspectable / Properties
- NetworkManager : D-Bus org.freedesktop.NetworkManager + nm-settings(5)
- PipeWire       : PipeWire 原生协议(SPA) + D-Bus org.pipewire
- BlueZ          : D-Bus org.bluez
- udev           : 规则语法 udev(7) + hwdb(7)
- polkit         : D-Bus org.freedesktop.PolicyKit1 + .policy / .rules
- Wayland        : wayland.xml 核心协议 + xdg-shell 扩展

每项任务的标准依据一律指向该软件自己的官方文档（见 data/syssoftware_docs.json）。
未安装该软件时原生探测自动降级为「指引」，不强求安装；删除类动作默认需 --apply。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)

SD = "[国际] systemd 文档（systemd.unit(5) / systemd.service(5) / systemd-journald.service(8)" \
     " / org.freedesktop.systemd1）"
DBUS = "[国际] D-Bus Specification（freedesktop.org，org.freedesktop.DBus" \
       " / .Introspectable / .Properties）"
NM = "[国际] NetworkManager 文档（networkmanager.dev：nmcli(1) / nm-settings(5)" \
     " / org.freedesktop.NetworkManager）"
PW = "[国际] PipeWire 文档（docs.pipewire.org：pipewire.conf(5) / SPA 协议 / org.pipewire）"
BZ = "[国际] BlueZ 文档（bluetoothd(8) / bluetoothctl(1) / org.bluez.Adapter1(5)）"
UD = "[国际] udev 文档（udev(7) 规则语法 / udevadm(8) / hwdb(7)）"
PK = "[国际] polkit 文档（polkit(8) / pkaction(1) / org.freedesktop.PolicyKit1(5)）"
WL = "[国际] Wayland 协议规范（wayland.freedesktop.org：wayland.xml 核心 / xdg-shell 扩展）"


TASKS = [
    Task(
        id="syssw_systemd_journal",
        platform="linux",
        title="回收 systemd 日志（journalctl --vacuum）",
        category="cleanup",
        risk="low",
        desc="用 journalctl --vacuum-time 按官方接口回收 systemd journal 日志，避免直接删 /var/log/journal。",
        actions=[
            S('if command -v journalctl >/dev/null; then journalctl --vacuum-time=7d 2>/dev/null; '
              'else echo "未安装 journalctl（非 systemd），跳过"; fi',
              "回收 7 天前的 systemd 日志（官方 --vacuum 接口，非直接删文件）", rev=True),
        ],
        standards=[SD],
        notes=["参考 systemd-journald.service(8)：journal 以二进制字段化存储，回收须走 journalctl"
               " --vacuum-size/--vacuum-time，直接删文件会破坏索引与轮转状态。",
               "持久化需 /var/log/journal 存在（Storage=persistent）；否则日志仅在内存 /run/log/journal。"],
        caveats=["会删除 7 天前的日志（审计/排障记录），确认无需保留再执行；如需留档请先 journalctl -o export 导出。"],
    ),
    Task(
        id="syssw_systemd_analyze",
        platform="linux",
        title="启动耗时分析（systemd-analyze blame / critical-chain）",
        category="optimize",
        risk="low",
        desc="用 systemd-analyze 找出启动最慢的单元与关键链，为开机优化提供官方依据。",
        actions=[
            S('if command -v systemd-analyze >/dev/null; then '
              'systemd-analyze blame 2>/dev/null | head -10; echo "--- 关键链 ---"; '
              'systemd-analyze critical-chain 2>/dev/null | head -10; '
              'else echo "未安装 systemd-analyze（非 systemd），跳过"; fi',
              "列出启动最慢单元与关键链（只读分析，不修改）"),
        ],
        standards=[SD],
        notes=["参考 systemd-analyze(1)：blame 按单元耗时降序，critical-chain 显示启动关键路径；"
               "两者都是只读分析，不改任何单元。",
               "定位到慢单元后可 `systemctl disable <unit>` 或 `systemctl mask <unit>`（需确认影响）。"],
        caveats=["禁用系统关键单元（如 dbus / systemd-udevd）会导致系统不可用；仅对明确可省的第三方服务操作。"],
    ),
    Task(
        id="syssw_systemd_failed",
        platform="linux",
        title="失败单元核对（systemctl --failed）",
        category="maintenance",
        risk="low",
        desc="列出启动失败的 systemd 单元，便于定位反复重启/退化的服务。",
        actions=[
            N("syssoftware.systemd_report", "核对失败单元 / journal 占用 / 启动耗时（只读）"),
        ],
        standards=[SD],
        notes=["参考 systemctl(1)：--failed 仅列出进入 failed 状态的单元（不修改任何东西）；"
               "配合 `systemctl status <unit>` 看具体错误。",
               "单元状态经 org.freedesktop.systemd1 的 Unit 对象暴露，程序化核对同理。"],
        caveats=["仅读取状态，不重启/不重置失败单元（重置需 systemctl reset-failed，本任务不执行）。"],
    ),
    Task(
        id="syssw_dbus_report",
        platform="linux",
        title="D-Bus 总线服务自省（busctl，按 D-Bus 规范）",
        category="maintenance",
        risk="low",
        desc="按 D-Bus Specification 列出系统总线的服务名，核对哪些服务在总线上注册。",
        actions=[
            N("syssoftware.dbus_report", "列出 D-Bus 系统总线服务名（只读自省，不改总线）"),
        ],
        standards=[DBUS],
        notes=["参考 D-Bus Specification：服务以「总线名 + 对象路径 + 接口」三元组寻址；"
               "busctl list 即按规范枚举总线名。",
               "自省某服务: `busctl introspect <name> <path>`；会话总线用 `busctl --user list`。"],
        caveats=["D-Bus 只做进程间通信，不产生可清理的垃圾；本任务仅核对，不调用任何变更方法。"],
    ),
    Task(
        id="syssw_nm_report",
        platform="linux",
        title="NetworkManager 连接与状态核对（nmcli）",
        category="optimize",
        risk="low",
        desc="用 nmcli 核对 NetworkManager 全局状态与活动连接，确认网络由 NM 官方接口管理。",
        actions=[
            N("syssoftware.networkmanager_report", "核对 NM 状态与活动连接（只读 D-Bus 查询）"),
        ],
        standards=[NM],
        notes=["参考 nmcli(1) 与 org.freedesktop.NetworkManager：nmcli 是官方 CLI，"
               "其每一项都映射到 D-Bus 属性，故核对结果与程序化查询一致。",
               "连接配置以 keyfile 存于 /etc/NetworkManager/system-connections（格式见 nm-settings(5)）。"],
        caveats=["仅只读核对，不改连接/DNS；改 DNS 后端请改 NetworkManager.conf 的 [main].dns，勿手改 /etc/resolv.conf。"],
    ),
    Task(
        id="syssw_pipewire_report",
        platform="linux",
        title="PipeWire 音视频节点图核对（pw-cli）",
        category="optimize",
        risk="low",
        desc="按 PipeWire 协议列出节点图，核对音频/视频链路与采样率，定位无声/卡顿根因。",
        actions=[
            N("syssoftware.pipewire_report", "列出 PipeWire 节点图与守护状态（只读，按 SPA 协议）"),
        ],
        standards=[PW],
        notes=["参考 docs.pipewire.org：PipeWire 把设备抽象为节点(node)、经端口(port)链接成图；"
               "pw-cli ls / pw-top 即按协议展示该图。",
               "采样率/量子缓冲在 pipewire.conf 或 wireplumber 策略中调整；未装 pw-cli 时降级为套接字探测。"],
        caveats=["仅读取节点图，不重载守护进程、不改默认设备（设默认设备需 pw-metadata，属用户选择）。"],
    ),
    Task(
        id="syssw_bluez_report",
        platform="linux",
        title="蓝牙适配器与配对设备核对（BlueZ）",
        category="maintenance",
        risk="low",
        desc="按 org.bluez 列出蓝牙适配器与已配对设备，便于停用无用蓝牙省电或排查连接问题。",
        actions=[
            N("syssoftware.bluez_report", "列出蓝牙适配器与已配对设备（只读 D-Bus 查询）"),
        ],
        standards=[BZ],
        notes=["参考 bluetoothd(8)：BlueZ 经 org.bluez 暴露 Adapter1/Device1；bluetoothctl 是官方 CLI。",
               "不需要蓝牙时可 `systemctl stop/disable bluetooth.service` 省电（走 systemd 单元管理）。"],
        caveats=["仅读取设备列表；清 /var/lib/bluetooth 会丢失全部配对密钥，本任务绝不执行。"],
    ),
    Task(
        id="syssw_udev_report",
        platform="linux",
        title="udev 自定义规则核对（udevadm）",
        category="maintenance",
        risk="low",
        desc="核对 /etc/udev/rules.d 下的自定义规则数量，并按 udev(7) 提示只读调试接口。",
        actions=[
            N("syssoftware.udev_report", "核对自定义 udev 规则与调试接口（只读，按 udev(7)）"),
        ],
        standards=[UD],
        notes=["参考 udev(7)：规则以匹配键(MATCH)筛选设备、赋值键(ASSIGN)命名/设权限；"
               "udevadm info 可只读查看设备属性。",
               "新增/修改规则后需 `udevadm control --reload && udevadm trigger` 生效。"],
        caveats=["仅统计与提示，不修改/不重载规则；误写规则会导致网卡重命名或设备无权限，改前先备份。"],
    ),
    Task(
        id="syssw_polkit_report",
        platform="linux",
        title="polkit 授权 action 审计（pkaction）",
        category="maintenance",
        risk="low",
        desc="列出已注册的 polkit action 与默认授权，核对是否存在过度宽松的提权策略。",
        actions=[
            N("syssoftware.polkit_report", "列出已注册 action 与默认授权（只读 pkaction）"),
        ],
        standards=[PK],
        notes=["参考 polkit(8)：action 由服务注册于 /usr/share/polkit-1/actions/*.policy，"
               "管理员可用 /etc/polkit-1/rules.d/*.rules 覆盖判定。",
               "判定经 org.freedesktop.PolicyKit1 的 CheckAuthorization 完成，本任务只枚举不调用。"],
        caveats=["仅审计不改策略；收紧授权请新增 /etc/polkit-1/rules.d/*.rules，勿改发行版自带 .policy（升级会被覆盖）。"],
    ),
    Task(
        id="syssw_wayland_report",
        platform="linux",
        title="Wayland 会话与合成器协议核对",
        category="maintenance",
        risk="low",
        desc="判定当前是否为 Wayland 会话，并按 wayland.xml / xdg-shell 提示核对合成器支持的协议。",
        actions=[
            N("syssoftware.wayland_report", "核对 Wayland 会话与合成器全局接口（只读）"),
        ],
        standards=[WL],
        notes=["参考 Wayland 协议规范：核心协议 wayland.xml 定义 surface/seat 等全局接口，"
               "窗口行为由 xdg-shell 等扩展协议标准化。",
               "`wayland-info` 可列出合成器实际支持的全部全局接口（需安装）；X11 应用经 XWayland 兼容。"],
        caveats=["仅读取环境变量与协议列表，不改显示会话；缺失扩展协议属合成器支持范围，非配置问题。"],
    ),
]
