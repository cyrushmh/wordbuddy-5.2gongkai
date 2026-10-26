"""远程接入与传输客户端只读审计（v0.6.30）。

覆盖 telnet / ssh（OpenSSH）/ filezilla / putty 四类「远程 Shell 与文件传输客户端」：
  - 文档跟踪：各自按**自身协议与接口**核对（SSH=RFC 425x 加密通道；Telnet=RFC 854
    明文 NVT；FileZilla=FTP/RFC959 明文 vs SFTP/SSH vs FTPS/RFC4217；PuTTY=Windows SSH 客户端）。
  - 只读探针：检测本机是否安装这些客户端、telnetd 是否在监听 23 端口、sshd_config
    关键项、~/.ssh 公钥、FileZilla 站点管理器路径（**只判定是否明文 FTP / 是否有主密码，
    绝不读取或解密任何口令**）。
  - 安全审计：telnet 明文风险、ssh 口令登录/root 直登、filezilla 明文 FTP + 弱口令存储。
  - 加固指引：禁用 telnet、sshd 改公钥、filezilla 用 SFTP + 设主密码——**只给指引，不代执行**。

严守红线：全程只读，绝不修改 sshd_config / 不停 telnetd / 不读解密任何口令 / 不自动重启。
契合用户「个人行为在完全图形界面控制操作」：本模块出审计与方案，用户在 GUI/OEM 工具确认。
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
from typing import Dict, List, Tuple

try:
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib.resources as resources  # type: ignore

REFS: Dict[str, dict] = {}


def _load_refs() -> Dict[str, dict]:
    """读 data/remote_clients_docs.json（权威文档层）。"""
    global REFS
    if REFS:
        return REFS
    try:
        txt = resources.files("sysweeper.data").joinpath(
            "remote_clients_docs.json").read_text(encoding="utf-8")
        import json
        REFS = json.loads(txt)
    except Exception:  # noqa: BLE001
        REFS = {}
    return REFS


def reference(key: str = "") -> dict:
    """返回某客户端的权威文档（name/org/url/protocols/interfaces/docs/summary/advice）。"""
    refs = _load_refs()
    if key:
        return refs.get(key, {})
    return refs


def reference_all() -> Dict[str, dict]:
    return _load_refs()


def detect_platform() -> str:
    """粗粒度平台判断（用于平台相关探测，如 PuTTY 仅 Windows）。"""
    import sys
    p = sys.platform
    if p.startswith("win"):
        return "windows"
    if p == "darwin":
        return "macos"
    if p.startswith("linux"):
        return "linux"
    if p in ("freebsd", "openbsd", "netbsd", "dragonfly"):
        return "bsd"
    return "posix"


# --------------------------------------------------------------------------- #
# 只读探针（每项返回 (ok, msg)；非目标平台/读不到即优雅降级，绝不补造）          #
# --------------------------------------------------------------------------- #
def _which(name: str) -> str:
    p = shutil.which(name)
    return p or ""


def probe_ssh() -> Tuple[bool, str]:
    """OpenSSH 客户端是否可用。"""
    p = _which("ssh")
    if p:
        return True, f"ssh 客户端: {p}"
    return False, "未找到 ssh 客户端（OpenSSH 未安装或未在 PATH）"


def probe_telnet() -> Tuple[bool, str]:
    """telnet 客户端是否可用 + telnetd 是否在监听 23 端口（明文风险）。"""
    client = _which("telnet")
    msg = f"telnet 客户端: {client}" if client else "未找到 telnet 客户端"
    # 探测 23 端口是否在本地监听（仅本机 loopback，不外出）
    listening = False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.4)
            if s.connect_ex(("127.0.0.1", 23)) == 0:
                listening = True
    except OSError:
        listening = False
    if listening:
        msg += "；⚠ 本机 23 端口有服务在监听（telnetd 明文，建议停用）"
    else:
        msg += "；本机 23 端口无监听"
    return bool(client) or listening, msg


def probe_filezilla() -> Tuple[bool, str]:
    """FileZilla 客户端是否可用 + 站点管理器路径。"""
    p = _which("filezilla")
    candidates = [
        os.path.expanduser("~/.config/filezilla/sitemanager.xml"),       # Linux
        os.path.expanduser("~/Library/Application Support/FileZilla/sitemanager.xml"),  # macOS
        os.path.expandvars(r"%APPDATA%\FileZilla\sitemanager.xml"),      # Windows
    ]
    found = [c for c in candidates if os.path.exists(c)]
    if p:
        msg = f"filezilla 客户端: {p}"
    elif found:
        msg = "filezilla 客户端未在 PATH，但发现站点管理器配置"
    else:
        return False, "未找到 filezilla 客户端与站点管理器配置"
    if found:
        msg += f"；站点管理器: {found[0]}"
    return True, msg


def probe_putty() -> Tuple[bool, str]:
    """PuTTY 是否可用（主要 Windows）。"""
    if detect_platform() != "windows":
        return False, "非 Windows 平台，PuTTY 通常在 Windows 使用"
    p = _which("putty") or _which("putty.exe")
    if p:
        return True, f"putty: {p}"
    return False, "未找到 putty（Windows 平台可安装：https://www.chiark.greenend.org.uk/~sgtatham/putty/）"


def probe_ssh_keys() -> Tuple[bool, str]:
    """~/.ssh 是否存在公钥（只读列 pub，不读私钥内容）。"""
    sshdir = os.path.expanduser("~/.ssh")
    if not os.path.isdir(sshdir):
        return False, "未发现 ~/.ssh 目录（未生成 SSH 密钥）"
    pubs = [f for f in os.listdir(sshdir) if f.endswith(".pub")]
    if pubs:
        return True, f"~/.ssh 公钥: {', '.join(pubs)}（建议用 ED25519 / RSA ≥2048）"
    return False, "~/.ssh 存在但无 .pub 公钥（仅私钥或空）——建议 ssh-keygen -t ed25519"


def probe_sshd_config() -> Tuple[bool, str]:
    """定位 sshd_config（只读，不改）。"""
    for c in ("/etc/ssh/sshd_config",
              "/etc/ssh/sshd_config.d/"):
        if os.path.exists(c):
            return True, f"sshd_config: {c}"
    return False, "未发现 sshd_config（非 SSH 服务端本机/仅客户端）"


# 探针清单（供 environment_report 与 CLI/GUI 遍历）
PROBES = (
    ("probe_ssh", "OpenSSH 客户端"),
    ("probe_telnet", "telnet 客户端 + 23 端口监听"),
    ("probe_filezilla", "FileZilla 客户端 + 站点管理器"),
    ("probe_putty", "PuTTY 客户端"),
    ("probe_ssh_keys", "~/.ssh 公钥"),
    ("probe_sshd_config", "sshd_config 位置"),
)


# --------------------------------------------------------------------------- #
# 只读安全审计（解析配置关键项 / 判定明文风险；绝不读解密口令、绝不改配置）        #
# --------------------------------------------------------------------------- #
def read_ssh_security() -> dict:
    """只读审计 sshd_config / ~/.ssh/config 关键安全项。

    返回 dict：{present, path, items:{项:值}, notes:[...]}；找不到即降级。
    """
    out: dict = {"present": False, "path": "", "items": {}, "notes": []}
    for path in ("/etc/ssh/sshd_config",
                 os.path.expanduser("~/.ssh/config")):
        if not os.path.exists(path):
            continue
        out["present"] = True
        out["path"] = path
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    low = s.lower()
                    for key in ("permitrootlogin", "passwordauthentication",
                                "pubkeyauthentication", "kbdinteractiveauthentication",
                                "protocol"):
                        if low.startswith(key + " ") or low.startswith(key + "\t"):
                            val = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
                            out["items"][key] = val
        except OSError as e:  # noqa: BLE001
            out["notes"].append(f"读取失败: {e}")
        break
    # 判定
    if out["present"]:
        pa = out["items"].get("passwordauthentication", "").lower()
        pr = out["items"].get("permitrootlogin", "").lower()
        proto = out["items"].get("protocol", "")
        if pa == "yes":
            out["notes"].append("⚠ PasswordAuthentication yes：允许口令登录，建议改公钥")
        if "prohibit-password" in pr or pr == "no" or pr == "without-password":
            out["notes"].append("✓ PermitRootLogin 已禁用/限制 root 直登")
        elif pr == "yes":
            out["notes"].append("⚠ PermitRootLogin yes：建议 prohibit-password")
        if proto.startswith("1"):
            out["notes"].append("⚠ Protocol 1：明文/弱协商，必须仅留 SSH-2（删 Protocol 行）")
    return out


def read_filezilla_security() -> dict:
    """只读判定 FileZilla 站点管理器：是否用明文 FTP、是否设主密码。

    **绝不读取或解密任何口令**——只检查 sitemanager.xml 中 <Protocol> 取值与
    是否存在主密码标记（FileZilla 用主密码时 sitemanager.xml 内口令为加密 blob）。
    """
    out: dict = {"present": False, "path": "", "plain_ftp": False,
                 "has_master_pw": None, "notes": []}
    candidates = [
        os.path.expanduser("~/.config/filezilla/sitemanager.xml"),
        os.path.expanduser("~/Library/Application Support/FileZilla/sitemanager.xml"),
        os.path.expandvars(r"%APPDATA%\FileZilla\sitemanager.xml"),
    ]
    path = next((c for c in candidates if os.path.exists(c)), "")
    if not path:
        return out
    out["present"] = True
    out["path"] = path
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        # Protocol=0 → 明文 FTP；=1 → SFTP(SSH)；=3/4 → FTPS
        if "<Protocol>0</Protocol>" in txt or "<Protocol>0</Protocol" in txt:
            out["plain_ftp"] = True
            out["notes"].append("⚠ 存在明文 FTP 站点（Protocol=0）：口令与数据不加密，建议改 SFTP")
        else:
            out["notes"].append("✓ 未发现明文 FTP 站点（多为 SFTP/FTPS）")
        # 主密码标记：FileZilla 设置主密码后会写入 <PassiveMode> 之外的密码保护项；
        # 简化判定：有 <Password> 明文标签且无主密码保护时为弱存储。此处仅提示。
        if "<Password>" in txt:
            out["notes"].append("提示: sitemanager.xml 含 <Password> 项；建议设置「主密码」对其二次加密")
    except OSError as e:  # noqa: BLE001
        out["notes"].append(f"读取失败: {e}")
    return out


def audit_telnet_risk() -> dict:
    """只读判定 telnet 明文风险（客户端可用 + 23 端口监听）。"""
    ok_client, msg_client = probe_telnet()
    out = {"client_available": bool(_which("telnet")),
           "port_23_listening": "23 端口有服务在监听" in msg_client,
           "notes": []}
    if out["client_available"]:
        out["notes"].append("telnet 客户端可用：仅在连本地串行/老网管设备时用，勿上不可信网")
    if out["port_23_listening"]:
        out["notes"].append("⚠ 本机 telnetd 在监听 23：明文远程登录，建议停用、改 SSH")
    else:
        out["notes"].append("✓ 本机 23 端口无监听（telnetd 未启用）")
    return out


# --------------------------------------------------------------------------- #
# 报告与指引                                                                  #
# --------------------------------------------------------------------------- #
def environment_report() -> List[str]:
    """本机远程客户端可用性与审计概览（只读）。"""
    lines: List[str] = []
    for fn_name, lab in PROBES:
        ok, msg = globals()[fn_name]()
        lines.append(f"   · {lab}: {'✓' if ok else '✗'}  {msg}")
    return lines


def remote_doc_list() -> List[str]:
    """data/remote_clients_docs.json 引用清单。"""
    lines: List[str] = []
    for key, ref in reference_all().items():
        lines.append(f"   · [{key}] {ref.get('name', key)} — {ref.get('org', '')}")
        lines.append(f"       {ref.get('url', '')}")
        for d in ref.get("docs", [])[:3]:
            lines.append(f"       文档: {d}")
    return lines


def remote_audit_report() -> Tuple[bool, str]:
    """端到端只读审计：ssh 安全 + telnet 风险 + filezilla 安全 + 客户端清单。"""
    out: List[str] = []
    out.append("==== 远程接入与传输客户端 只读安全审计 ====")
    out.append("")
    out.append("-- 本机客户端可用项 --")
    for line in environment_report():
        out.append(line)
    out.append("")
    out.append("-- SSH 服务端/配置安全（只读）--")
    ssh = read_ssh_security()
    if ssh["present"]:
        out.append(f"   sshd_config/config: {ssh['path']}")
        for k, v in ssh["items"].items():
            out.append(f"     {k} = {v}")
        for n in ssh["notes"]:
            out.append(f"     {n}")
    else:
        out.append("   未发现 sshd_config（本机非 SSH 服务端）；客户端 ssh 可用即够日常连接")
    out.append("")
    out.append("-- Telnet 明文风险（只读）--")
    tel = audit_telnet_risk()
    for n in tel["notes"]:
        out.append(f"     {n}")
    out.append("")
    out.append("-- FileZilla 站点安全（只读，不读解密口令）--")
    fz = read_filezilla_security()
    if fz["present"]:
        out.append(f"   站点管理器: {fz['path']}")
        for n in fz["notes"]:
            out.append(f"     {n}")
    else:
        out.append("   未发现 FileZilla 站点管理器配置（未安装或未使用）")
    out.append("")
    out.append("安全总原则：远程 Shell 与传输一律走加密通道（SSH/SFTP/FTPS），")
    out.append("telnet/明文 FTP 仅限本地可信场景；密钥优于口令，口令不裸存。")
    return True, "\n".join(out)


def assess_keepalive() -> List[dict]:
    """连接保活与重连（只读观测 + 指引，D10 直接借鉴 docker-easyconnect 自动保活）。

    只读检查本机 SSH 客户端配置里的 ServerAliveInterval/ServerAliveCountMax（保活心跳）；
    其余给 TCP keepalive / autossh / VPN 重连的通用指引。绝不改任何连接配置、绝不注入重连进程。
    """
    sug: List[dict] = []
    cfg_paths = ["/etc/ssh/ssh_config", os.path.expanduser("~/.ssh/config")]
    alive = None
    for p in cfg_paths:
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for l in f:
                        m = re.match(r"\s*ServerAliveInterval\s+(\d+)", l)
                        if m:
                            alive = int(m.group(1))
            except OSError:
                pass
    if alive:
        sug.append({
            "id": "ssh_keepalive_set",
            "title": f"检测到 SSH 客户端 ServerAliveInterval={alive}s，连接空闲保活已启用"
                     f"（建议 30–60s，配合 ServerAliveCountMax 判定断线重连）",
            "severity": "info", "action_type": "guidance", "rationale": "remote_clients",
        })
    else:
        sug.append({
            "id": "ssh_keepalive_off",
            "title": "未在 SSH 客户端配置发现 ServerAliveInterval；NAT/防火墙后长连接易被判死，"
                     "建议设 ServerAliveInterval 30 / ServerAliveCountMax 3 保活",
            "severity": "notice", "action_type": "guidance", "rationale": "remote_clients",
        })
    sug.append({
        "id": "autossh_reconnect",
        "title": "需常驻隧道用 autossh 自动重连（断线即拉起，比裸 ssh 自愈更强）；"
                 "VPN 场景设连接保活与自动重拨，避免隧道静默掉线",
        "severity": "info", "action_type": "guidance", "rationale": "remote_clients",
    })
    sug.append({
        "id": "tcp_keepalive",
        "title": "内核 TCP keepalive（net.ipv4.tcp_keepalive_time 默认 7200s 偏长）可在长连接场景调短；"
                 "应用层心跳优先于内核保活",
        "severity": "info", "action_type": "guidance", "rationale": "remote_clients",
    })
    return sug


# 写操作（仅指引，不代执行）
TUNES = (
    ("tune_disable_telnet", "停用 telnetd（明文）",
     "systemctl disable --now inetd/telnet.socket（或注释 /etc/inetd.conf 的 telnet 行）；"
     "改用 sshd。本工具只给命令文本，不替你执行。"),
    ("tune_harden_sshd", "sshd 改公钥登录",
     "编辑 /etc/ssh/sshd_config：PasswordAuthentication no、PubkeyAuthentication yes、"
     "PermitRootLogin prohibit-password，然后 sshd -t 校验并 systemctl reload sshd。"
     "本工具只给指引，不替你改写配置。"),
    ("tune_secure_filezilla", "FileZilla 用 SFTP + 主密码",
     "站点协议选 SFTP（端口 22）；设置 → 主密码，给站点口令二次加密；"
     "不在不可信网用明文 FTP。本工具不替你改站点、不读口令。"),
    ("tune_putty_ssh", "PuTTY 默认 SSH + ED25519",
     "连接类型选 SSH；puttygen 生成 ED25519 并设私钥口令；pageant 持有代理。"
     "本工具不替你改注册表会话。"),
)


def remote_tune_list() -> List[str]:
    """加固/安全指引清单（只展示，不调用）。"""
    lines: List[str] = []
    for key, title, guide in TUNES:
        lines.append(f"   · [{key}] {title}")
        lines.append(f"       {guide}")
    return lines
