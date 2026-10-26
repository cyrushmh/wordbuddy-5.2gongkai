"""OpenWrt 写操作「安全指引」层（只预检 + 给命令文本，绝不执行写操作）。

v0.5.20 把 OpenWrt 的各子系统做成了**纯只读**接口。本模块补上另一半：**如何在
OpenWrt 上做写操作的指引**——但依然**不代你执行任何写操作**。

安全设计（与全局一致，且刻意比一般「优化工具」更保守）：
- 本模块只做**只读预检**（读 /etc/openwrt_release、/etc/config/*、用 which() 看命令
  是否存在），**从不调用任何写命令**（不跑 sysupgrade / opkg install / uci set /
  service restart / make image 等）。它给出的命令**仅作为文本**展示，由你自行复制执行。
- 所有函数返回 ``(ok, msg)``；非 OpenWrt 环境优雅降级为「指引」。
- 因此这些「写操作指引」任务被登记为 **risk="high" + opt_in=True**：默认不出现在
  scan/clean，必须显式 `--opt-in` 并确认才会出现，且**即使出现也只是打印命令**。
- 本模块函数**刻意不加入插件白名单 NATIVE_ALLOWLIST**——插件框架只允许调用纯只读
  函数；写指引一律经由用户显式选择的 opt_in 任务触发，避免被插件间接驱动。

覆盖的常见写操作（均只给指引）：
- sysupgrade  固件刷写（最危险，见 OpenWrt sysupgrade 文档）
- 包管理      opkg / apk 安装、升级、卸载
- UCI 配置    uci set + commit + reload（含回滚要点）
- 服务管理    /etc/init.d/* 或 procd 服务启停、重载
"""

from __future__ import annotations

from typing import Tuple

from .openwrt import UCI_DIR, is_openwrt, package_manager

_BANNER = ("以下命令为**指引文本**，本工具不会执行；请自行确认后再手动执行。"
           "写操作请自行评估风险（尤其 sysupgrade 会重写固件分区）。")


def _off_openwrt(what: str) -> Tuple[bool, str]:
    """非 OpenWrt 环境统一的降级提示。"""
    return False, (f"当前不在 OpenWrt 环境，无法预检 {what}。"
                   "写操作指引仅在 OpenWrt 路由器上生成；"
                   "请在路由器上用 `python -m sysweeper --platform openwrt list` 预览。")


# --------------------------------------------------------------------------- #
# sysupgrade（固件刷写）—— 最高危                                                #
# --------------------------------------------------------------------------- #


def sysupgrade_guide() -> Tuple[bool, str]:
    """sysupgrade 固件刷写指引（只预检：核对当前固件/板型与备份建议）。

    绝不执行 sysupgrade。sysupgrade 会重写固件分区，型号/固件不匹配可致设备变砖，
    因此本指引首重强调「先在同型号上验证固件、保留备份」。
    """
    ok, info = is_openwrt()
    if not ok:
        return _off_openwrt("sysupgrade 刷机环境")
    board = info.get("board_name") or info.get("model") or "(未知板型)"
    rel = info.get("RELEASE") or info.get("VERSION_ID") or "(未知版本)"
    target = info.get("TARGET") or "(未知)"
    lines = ["sysupgrade 固件刷写指引（高危；只读预检，不执行）：",
             f"  当前板型: {board}",
             f"  当前固件: {rel}  目标: {target}",
             "",
             "刷机前必读（务必逐条确认）：",
             "  1) 固件必须与**同型号**匹配（board_name 一致）；跨型号刷入会变砖。",
             "  2) 先备份当前配置：`sysupgrade -b /tmp/backup.tar.gz`（只导出配置）。",
             "  3) 确认固件校验和（官方 downloads 的 sha256sums）。",
             "  4) 刷写为写操作，本工具绝不执行；请按官方 sysupgrade 文档操作。",
             "",
             "命令指引（仅文本，不自动执行）：",
             "  # 备份配置（可逆，建议先做）",
             "  sysupgrade -b /tmp/backup.tar.gz",
             "  # 刷写固件（危险：重写固件分区，请确认型号与固件后再手动执行）",
             f"  sysupgrade -n /tmp/openwrt-{target}-*-{rel}.bin",
             "",
             "官方文档: https://openwrt.org/docs/techref/sysupgrade",
             _BANNER]
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 包管理（opkg / apk）—— 安装/升级/卸载                                            #
# --------------------------------------------------------------------------- #


def package_write_guide() -> Tuple[bool, str]:
    """包管理写操作指引（只预检：识别 opkg/apk 与已装数量）。

    绝不执行 install/remove/upgrade。安装/卸载会改动系统文件与依赖，故为高危指引。
    """
    ok, _info = is_openwrt()
    if not ok:
        return _off_openwrt("包管理（opkg/apk）")
    pm = package_manager() or "(opkg/apk 命令均不可用)"
    lines = [f"包管理写操作指引（高危；只读预检，不执行）· 包管理器: {pm}",
             "",
             "命令指引（仅文本，不自动执行）："]
    if pm == "apk":
        lines += [
            "  apk update                 # 刷新索引（写：索引缓存）",
            "  apk add <pkg>              # 安装（写）",
            "  apk upgrade                # 升级全部（写）",
            "  apk del <pkg>              # 卸载（写）",
        ]
    elif pm == "opkg":
        lines += [
            "  opkg update                # 刷新索引（写）",
            "  opkg install <pkg>         # 安装（写）",
            "  opkg upgrade <pkg>         # 升级（写）",
            "  opkg remove <pkg>          # 卸载（写）",
        ]
    else:
        lines += [
            "  # 未检测到 opkg/apk 命令；若在路由器上，请确认包管理器是否安装。",
            "  # 23.05 及更早用 opkg；24.10 起默认 apk。",
        ]
    lines += ["",
              "提示：卸载/升级会牵动依赖与配置，务必先看 `list-installed`（只读）确认。",
              "官方文档: https://openwrt.org/docs/guide-user/additional-software/opkg "
              "与 .../opkg-to-apk-migration",
              _BANNER]
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# UCI 配置 —— set/commit/reload                                                    #
# --------------------------------------------------------------------------- #


def uci_write_guide() -> Tuple[bool, str]:
    """UCI 配置写操作指引（只预检：查看待生效变更 / 已存在配置包）。

    绝不执行 uci set/commit/reset。配置写操作影响面广，官方推荐「先 uci changes
    预览 → set → commit → 保留回滚路径」。
    """
    ok, _info = is_openwrt()
    if not ok:
        return _off_openwrt("UCI 配置（/etc/config）")
    try:
        import os
        files = sorted(f for f in os.listdir(UCI_DIR)
                       if os.path.isfile(os.path.join(UCI_DIR, f)))
    except OSError:
        files = []
    lines = ["UCI 配置写操作指引（高危；只读预检，不执行）：",
             f"  当前配置包(/etc/config): {len(files)} 个"
             + (f"（{', '.join(files[:12])}{' …' if len(files) > 12 else ''}）" if files else ""),
             "",
             "命令指引（仅文本，不自动执行）：",
             "  uci show <pkg>            # 只读查看当前值",
             "  uci changes <pkg>         # 只读查看未提交变更（写入前必查）",
             "  uci set <pkg>.<opt>=<val> # 写：设置（未提交）",
             "  uci commit <pkg>          # 写：提交到 /etc/config",
             "  uci revert <pkg>          # 回滚未提交变更（可逆）",
             "  # 生效服务配置通常还需：/etc/init.d/<svc> reload（写）",
             "",
             "安全做法：改前 `uci export <pkg> > /tmp/<pkg>.bak` 备份，写错可 `uci import` 回滚。",
             _BANNER]
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 服务管理（/etc/init.d/*, procd）                                                #
# --------------------------------------------------------------------------- #


def service_write_guide() -> Tuple[bool, str]:
    """服务启停/重载指引（只预检：列举可管理服务名）。

    绝不执行 start/stop/restart/reload。服务启停影响可用性，故为高危指引。
    """
    ok, _info = is_openwrt()
    if not ok:
        return _off_openwrt("服务管理（/etc/init.d）")
    try:
        import os
        names = sorted(os.listdir("/etc/init.d"))
    except OSError:
        names = []
    sample = ", ".join(names[:20]) + (" …" if len(names) > 20 else "") if names else "(无)"
    lines = ["服务管理写操作指引（高危；只读预检，不执行）：",
             f"  可管理服务(/etc/init.d): {len(names)} 个",
             f"  样例: {sample}",
             "",
             "命令指引（仅文本，不自动执行）：",
             "  /etc/init.d/<svc> status     # 只读查看状态",
             "  /etc/init.d/<svc> restart    # 写：重启服务",
             "  /etc/init.d/<svc> reload     # 写：重载配置",
             "  /etc/init.d/<svc> enable|disable  # 写：开机自启",
             "  # procd 运行时亦可：ubus call service <svc> restart（写）",
             "",
             "提示：重启网络/防火墙类服务会短暂断网；远程操作请确保有回带/带外通道。",
             "官方文档: https://openwrt.org/docs/techref/procd",
             _BANNER]
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 任务派发用的无参包装（runner 以 fn() 派发）                                      #
# --------------------------------------------------------------------------- #


def openwrt_write_report() -> Tuple[bool, str]:
    """OpenWrt 写操作指引总览（只读预检 + 命令文本，绝不执行写操作）。"""
    try:
        head = ("OpenWrt 写操作指引（高危；只读预检，命令仅作文本展示，绝不自动执行）\n"
                "本模块从不调用任何写命令；请自行评估风险后再手动执行。\n"
                "------------------------------------------------------------")
        blocks = []
        for fn in (sysupgrade_guide, package_write_guide, uci_write_guide,
                   service_write_guide):
            _ok, msg = fn()
            blocks.append(msg)
        return True, head + "\n\n" + "\n\n".join(blocks)
    except Exception as e:  # noqa: BLE001
        return False, f"OpenWrt 写操作指引生成失败: {e}"


__all__ = [
    "sysupgrade_guide", "package_write_guide", "uci_write_guide",
    "service_write_guide", "openwrt_write_report",
]