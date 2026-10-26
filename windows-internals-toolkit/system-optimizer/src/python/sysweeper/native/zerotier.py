"""ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断。

ZeroTier 在物理网络之上建加密的虚拟二层网络（VL1）：每个节点有一个 40 位地址与一对
identity（公钥 identity.public / 私钥 identity.secret）。网络由「控制器」签发、成员
节点加入，moon 是私有根。本模块只做只读核验：

- zerotier-one 是否安装、版本（zerotier-one -v）
- 是否在跑（systemd active / zerotier-cli info 返回 200）
- identity.public 是否存在（公钥，可对外）；identity.secret 只报存在、绝不读取
- 已加入网络（networks.d/*.conf，文件名即网络 ID）
- 是否控制器（controller.d 存在）
- moon（moons.d/*.moon，私有根）

红线：不启动/停止 zerotier-one、不 join/leave 网络、不改 networks.d、不连控制端口
      下发写命令；只读本地文件与版本号。identity.secret 属私钥，本工具绝不读取。
"""
import os
import shutil
from . import common

ZT_DIR = "/var/lib/zerotier-one"
ZT_BIN = "zerotier-one"
ZT_CLI = "zerotier-cli"


def _zt_binary() -> tuple:
    """返回 (found, version_str)。"""
    binpath = shutil.which(ZT_BIN)
    if not binpath:
        for p in ("/usr/sbin/zerotier-one", "/usr/bin/zerotier-one"):
            if os.path.exists(p):
                binpath = p
                break
    if not binpath:
        return (False, "")
    rc, out = common.run(f'"{binpath}" -v', timeout=10)
    if rc == 0 and out.strip():
        return (True, out.strip().split()[0])
    return (True, "（版本未知）")


def _running() -> str:
    rc, out = common.run("systemctl is-active zerotier-one 2>/dev/null", timeout=5)
    if rc == 0 and "active" in out:
        return "运行中（systemd active）"
    if shutil.which(ZT_CLI):
        rc, out = common.run(f"{ZT_CLI} info 2>/dev/null", timeout=5)
        if rc == 0 and out.strip().startswith("200"):
            return "运行中（zerotier-cli info 返回 200）"
        if rc == 0 and out.strip().startswith("300"):
            return "未授权（zerotier-cli 返回 300；服务在但本机未授权）"
    return "未运行"


def _identity() -> tuple:
    """返回 (has_public, has_secret)。secret 只报存在，绝不读。"""
    return (os.path.exists(os.path.join(ZT_DIR, "identity.public")),
            os.path.exists(os.path.join(ZT_DIR, "identity.secret")))


def _networks() -> list:
    """已加入网络：networks.d/*.conf 文件名（即网络 ID）。"""
    nd = os.path.join(ZT_DIR, "networks.d")
    if not os.path.isdir(nd):
        return []
    return sorted(f[:-5] for f in os.listdir(nd) if f.endswith(".conf"))


def _is_controller() -> bool:
    return os.path.isdir(os.path.join(ZT_DIR, "controller.d"))


def _moons() -> list:
    md = os.path.join(ZT_DIR, "moons.d")
    if not os.path.isdir(md):
        return []
    return sorted(f for f in os.listdir(md) if f.endswith(".moon"))


def capabilities_report() -> tuple:
    lines = [
        "ZeroTier 虚拟网络（SD-WAN / 零信任组网）诊断 · 能力自检",
        "可诊断维度：",
        "  1. zerotier-one 是否安装 + 版本（zerotier-one -v）",
        "  2. 守护进程状态（systemd active / zerotier-cli info 200）",
        "  3. identity.public 是否存在（公钥，可对外）；identity.secret 仅报存在",
        "  4. 已加入网络（networks.d/*.conf，文件名即网络 ID）",
        "  5. 是否控制器（controller.d）/ 是否部署 moon（moons.d）",
        "红线：不启动/停止 zerotier-one、不 join/leave 网络、不改 networks.d、",
        "      不连控制端口写命令；identity.secret 属私钥，本工具绝不读取。",
    ]
    return (True, "\n".join(lines))


def zerotier_report() -> tuple:
    lines = ["==== ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断 ===="]
    found, ver = _zt_binary()
    lines.append(f"[zerotier-one] {'已安装（' + ver + '）' if found else '未安装'}")
    lines.append(f"[运行状态] {_running()}")
    if os.path.isdir(ZT_DIR):
        lines.append(f"[数据目录] {ZT_DIR} 存在")
    has_pub, has_sec = _identity()
    if has_pub:
        lines.append("[identity] identity.public 存在（公钥，可对外）")
    if has_sec:
        lines.append("[identity] identity.secret 存在（私钥；本工具不读取）")
    nets = _networks()
    lines.append(f"[已加入网络] {('；'.join(nets)) if nets else '无（networks.d 空/不存在）'}")
    lines.append(f"[控制器] {'是（controller.d 存在，可托管网络）' if _is_controller() else '否（普通成员节点）'}")
    moons = _moons()
    lines.append(f"[moon] {', '.join(moons) if moons else '无（moons.d 空/不存在）'}")
    lines.append("")
    lines.append("提示：ZeroTier 在物理网之上建加密虚拟二层网（VL1），每节点 40 位地址 + identity；")
    lines.append("networks.d 是已加入网络、controller.d 是自建控制器、moons.d 是私有根（moon）。")
    lines.append("虚拟网默认端到端加密；但控制器能决定谁能进网，moon 决定根在哪——信任边界在自己手里。")
    return (True, "\n".join(lines))
