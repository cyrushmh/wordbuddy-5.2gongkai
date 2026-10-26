"""OpenWrt 路由器系统任务（只读优先；高危写操作仅 opt-in 指引）。

把 OpenWrt 的核心子系统登记为任务：

- **只读（risk=low，opt_in=False）**：固件/板型识别、UCI 配置只读审计、包管理盘点
  （opkg/apk）、网络接口、防火墙、无线、DHCP/DNS、存储、构建系统参考。
- **高危写指引（risk=high，opt_in=True）**：sysupgrade 刷机、包管理写操作、UCI 写配置、
  服务启停——这些**只做只读预检 + 给出命令文本**，本工具**绝不执行**任何写操作，
  且默认关闭（opt_in），须显式 --opt-in 且确认才出现。

只读任务用 native 通道调只读函数；写指引任务调 openwrt_write 的「只预检不执行」函数。
任务 platform="openwrt"，仅在 OpenWrt 平台出现；非 OpenWrt 用 `--platform openwrt`
可预览，运行时优雅降级为指引。

安全护栏（与全局一致）：绝不自动执行任意写操作；UCI/无线审计只展示配置项「存在性」，
绝不回显 secret 明文；写指引命令仅作文本展示，由用户自行确认后手动执行。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

TASKS = [
    Task(
        id="openwrt_detect",
        platform="openwrt",
        title="OpenWrt 探测与板型/固件识别（只读）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt 硬件与 sysupgrade 文档（/tmp/sysinfo/*、/etc/openwrt_release）",
            "[仓库] OpenWrt（GPL-2.0，本工具仅只读引用）",
        ],
        desc="读取 /etc/openwrt_release、/etc/os-release、/tmp/sysinfo/{board_name,model}，"
             "识别设备型号、固件版本、目标平台与架构。纯只读。",
        actions=[N("openwrt.openwrt_detect_report",
                   "识别 OpenWrt 板型与固件（/etc/openwrt_release + /tmp/sysinfo）")],
        notes=[
            "board_name / model 给出硬件型号；DISTRIB_RELEASE/TARGET/ARCH 给出固件与架构。",
            "非 OpenWrt 环境会降级为指引（说明需在路由器上运行）。",
        ],
        caveats=["刷机（sysupgrade）为写操作，本工具不自动执行，仅给文档指引。"],
    ),
    Task(
        id="openwrt_uci_audit",
        platform="openwrt",
        title="UCI 配置只读审计（/etc/config/*，不打印 secret 明文）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt UCI 文档（guide-user/base-system/uci + techref/uci）",
        ],
        desc="解析 /etc/config/*（network/system/wireless/firewall/dhcp…），列出每文件节数、"
             "接口、桥接与含敏感配置项的存在性；敏感值绝不回显。",
        actions=[N("openwrt.openwrt_uci_report",
                   "审计 UCI 配置（仅存在性，绝不打印密码/密钥明文）")],
        notes=[
            "可选 `uci show` 检视；无 uci 命令时回退文件解析。",
            "含 key/password/secret/psk 等配置项仅报告「存在」，不打印值。",
        ],
        caveats=["写配置用 `uci set` + `uci commit`，本工具不自动执行任何 uci set。"],
    ),
    Task(
        id="openwrt_pkgs",
        platform="openwrt",
        title="已装软件包只读盘点（opkg/apk 自适应）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt opkg 文档（23.05 及更早）",
            "[官方] OpenWrt opkg→apk 迁移文档（24.10 起默认 apk）",
        ],
        desc="盘点 OpenWrt 已装软件包：24.10 用 apk（/usr/lib/apk/db/installed），"
             "更早用 opkg（/usr/lib/opkg/status）；命令不可用则解析状态文件。",
        actions=[N("openwrt.openwrt_pkgs_report",
                   "只读盘点已装软件包（opkg list-installed / apk info）")],
        notes=[
            "23.05 及更早：opkg；24.10 起默认：apk。",
            "安装/升级为写操作，仅给指引。",
        ],
        caveats=["`opkg install` / `apk add` 为写操作，本工具不自动执行。"],
    ),
    Task(
        id="openwrt_network",
        platform="openwrt",
        title="网络接口只读报告（netifd / ubus / UCI network）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt netifd 文档（techref/netifd）",
            "[官方] OpenWrt ubus 文档（techref/ubus）",
        ],
        desc="解析 /etc/config/network 列出接口/桥接/VLAN；可选 `ubus call network.interface dump`"
             "读取运行时状态。纯只读。",
        actions=[N("openwrt.openwrt_network_report",
                   "只读报告网络接口（/etc/config/network + 可选 ubus）")],
        notes=[
            "接口/桥接/VLAN 来自 UCI；运行时状态来自 ubus（只读方法）。",
        ],
        caveats=["改接口为写操作（uci set + commit 或 ubus 写方法），本工具不自动执行。"],
    ),
    Task(
        id="openwrt_build",
        platform="openwrt",
        title="OpenWrt 构建系统参考（ImageBuilder/SDK/feeds，仅文档）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt ImageBuilder 文档（guide-user/additional-software/imagebuilder）",
            "[官方] OpenWrt SDK 文档（guide-developer/toolchain/using_the_sdk）",
            "[官方] OpenWrt feeds 文档（guide-developer/feeds）",
            "[官方] OpenWrt 构建系统文档（guide-developer/build-system）",
        ],
        desc="列出定制固件的三种路径：ImageBuilder（最快，基于预编译根文件挑包）、"
             "SDK（交叉编译软件包）、完整 menuconfig 编译。均为写操作，仅给文档指引。",
        actions=[N("openwrt.openwrt_build_report",
                   "查看 OpenWrt 构建系统参考（ImageBuilder/SDK/feeds，仅文档）")],
        notes=[
            "ImageBuilder 最快；SDK 用于编译单包；完整编译最灵活最慢。",
        ],
        caveats=["`make image` / SDK make / 完整编译 / sysupgrade 均为写操作，本工具不调用。"],
    ),
    # ---------------- 只读子系统：防火墙 / 无线 / DHCP / 存储（v0.5.21） ----------------
    Task(
        id="openwrt_firewall",
        platform="openwrt",
        title="防火墙只读报告（/etc/config/firewall，zone/转发/规则）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt 防火墙文档（guide-user/security/firewall）",
            "[国际] IETF RFC（NAT/端口转发相关：RFC 3022 / RFC 4787）",
        ],
        desc="解析 /etc/config/firewall，列出区域(zone)、转发(forwarding)、规则(rule)、"
             "重定向(redirect)数量与各区域网络归属、NAT(masq)、input/output 策略；"
             "运行时实现（firewall4/nftables 或 firewall3/iptables）只读检视。纯只读。",
        actions=[N("openwrt.openwrt_firewall_report",
                   "只读报告防火墙配置（/etc/config/firewall）")],
        notes=["zone/forwarding/rule/redirect 来自 UCI；运行时状态只读检视。"],
        caveats=["改防火墙规则为写操作（uci set + commit + reload），本工具不自动执行。"],
    ),
    Task(
        id="openwrt_wireless",
        platform="openwrt",
        title="无线只读报告（/etc/config/wireless，不回显密码）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt 无线文档（guide-user/smart-wifi/start）",
            "[国际] IEEE 802.11（Wi-Fi 频段/信道/加密）",
        ],
        desc="解析 /etc/config/wireless，列出无线电(wifi-device)频段/信道/禁用状态与"
             "无线接口(wifi-iface)的设备/模式/加密方式。含密码的接口仅标记存在性，"
             "绝不回显密钥明文。纯只读。",
        actions=[N("openwrt.openwrt_wireless_report",
                   "只读报告无线配置（/etc/config/wireless，绝不回显密码）")],
        notes=["无线密码(encryption key)仅提示「含密码」，不打印明文。"],
        caveats=["改无线为写操作（uci set + commit + wifi reload），本工具不自动执行。"],
    ),
    Task(
        id="openwrt_dhcp",
        platform="openwrt",
        title="DHCP/DNS 只读报告（/etc/config/dhcp，dnsmasq/odhcpd）",
        category="network",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt DHCP/DNS 文档（guide-user/network/dhcp）",
            "[国际] IETF RFC 2131 / RFC 2132（DHCP）",
            "[国际] IETF RFC 1035（DNS 域名系统）",
        ],
        desc="解析 /etc/config/dhcp，列出 dnsmasq 实例（端口/上游DNS/域）、各接口 DHCP "
             "地址池(start/limit)与静态租约(host)条目数量。纯只读。",
        actions=[N("openwrt.openwrt_dhcp_report",
                   "只读报告 DHCP/DNS 配置（/etc/config/dhcp）")],
        notes=["静态租约仅统计条目数，不逐条展开敏感字段。"],
        caveats=["改 DHCP/DNS 为写操作（uci set + commit + dnsmasq restart），本工具不自动执行。"],
    ),
    Task(
        id="openwrt_storage",
        platform="openwrt",
        title="存储只读报告（/etc/config/fstab + df，不 resize/格式化）",
        category="maintenance",
        risk="low",
        opt_in=False,
        standards=[
            "[官方] OpenWrt 存储文档（guide-user/storage）",
            "[国际] Linux kernel Documentation/filesystems（文件系统）",
        ],
        desc="解析 /etc/config/fstab 列出挂载点（fstype/enabled），并用只读 `df -h` 展示"
             "容量；识别 overlay（叠加根）是否存在。纯只读，不 resize/格式化。",
        actions=[N("openwrt.openwrt_storage_report",
                   "只读报告存储挂载与容量（fstab + df）")],
        notes=["overlay 为固件叠加层；容量不足时清理/扩容是写操作。"],
        caveats=["resize/格式化/清理 overlay 为写操作，本工具不自动执行。"],
    ),
    # ---------------- 高危写操作「安全指引」（opt-in，仅命令文本，绝不执行）（v0.5.21） ----------------
    Task(
        id="openwrt_sysupgrade_guide",
        platform="openwrt",
        title="sysupgrade 固件刷写指引（高危·opt-in·只给命令，不执行）",
        category="maintenance",
        risk="high",
        opt_in=True,
        standards=[
            "[官方] OpenWrt sysupgrade 文档（techref/sysupgrade）",
        ],
        desc="**只读预检**当前板型(board_name/model)与固件(DISTRIB_RELEASE/TARGET)，"
             "给出 sysupgrade 备份(backup)与刷写命令的**文本指引**。本工具只读预检、"
             "绝不执行 sysupgrade——刷机为高危写操作，须同型号固件 + 先备份。",
        actions=[N("openwrt_write.sysupgrade_guide",
                   "sysupgrade 刷机指引（只读预检 + 命令文本，绝不执行刷写）")],
        notes=[
            "默认关闭（opt_in）：需 --opt-in 且确认后才出现，避免误触高危刷机指引。",
            "先 sysupgrade -b 备份配置，再刷写；固件必须与同型号匹配。",
        ],
        caveats=[
            "sysupgrade 重写固件分区，型号/固件不匹配可致设备变砖；本工具绝不执行刷写。",
            "命令仅作文本展示，需你自行确认后手动执行。",
        ],
    ),
    Task(
        id="openwrt_pkg_write_guide",
        platform="openwrt",
        title="包管理写操作指引（高危·opt-in·install/upgrade/remove 只给命令）",
        category="maintenance",
        risk="high",
        opt_in=True,
        standards=[
            "[官方] OpenWrt opkg 文档（23.05 及更早）",
            "[官方] OpenWrt opkg→apk 迁移文档（24.10 起默认 apk）",
        ],
        desc="**只读预检**识别包管理器(opkg/apk)，给出 update/install/upgrade/remove 的"
             "**命令文本指引**。本工具绝不执行包安装/卸载（写操作）。",
        actions=[N("openwrt_write.package_write_guide",
                   "包管理写操作指引（只读预检 + 命令文本，绝不执行安装/卸载）")],
        notes=["23.05 及更早 opkg；24.10 起默认 apk。卸载/升级牵动依赖，务必先只读确认。"],
        caveats=["opkg install / apk add/del 为写操作，本工具绝不执行；命令仅作文本展示。"],
    ),
    Task(
        id="openwrt_uci_write_guide",
        platform="openwrt",
        title="UCI 配置写操作指引（高危·opt-in·uci set/commit 只给命令）",
        category="maintenance",
        risk="high",
        opt_in=True,
        standards=[
            "[官方] OpenWrt UCI 文档（guide-user/base-system/uci + techref/uci）",
        ],
        desc="**只读预检**列出 /etc/config 配置包，给出 uci show/changes(只读) 与 "
             "uci set/commit/revert 的**命令文本指引**，并强调先备份、先看 changes。本工具"
             "绝不执行任何 uci set/commit。",
        actions=[N("openwrt_write.uci_write_guide",
                   "UCI 配置写操作指引（只读预检 + 命令文本，绝不执行 uci set/commit）")],
        notes=["改前 uci export 备份、写前 uci changes 预览、uci revert 可回滚未提交变更。"],
        caveats=["uci set/commit 为写操作，本工具绝不执行；命令仅作文本展示。"],
    ),
    Task(
        id="openwrt_svc_write_guide",
        platform="openwrt",
        title="服务启停/重载指引（高危·opt-in·restart/reload 只给命令）",
        category="maintenance",
        risk="high",
        opt_in=True,
        standards=[
            "[官方] OpenWrt procd 文档（techref/procd）",
        ],
        desc="**只读预检**列举 /etc/init.d 可管理服务，给出 status(只读) 与 "
             "restart/reload/enable 的**命令文本指引**。本工具绝不执行服务启停（写操作）。",
        actions=[N("openwrt_write.service_write_guide",
                   "服务启停指引（只读预检 + 命令文本，绝不执行 restart/reload）")],
        notes=["重启网络/防火墙类服务会短暂断网；远程操作请确保有回带/带外通道。"],
        caveats=["/etc/init.d/<svc> restart/reload 为写操作，本工具绝不执行；命令仅作文本展示。"],
    ),
]
