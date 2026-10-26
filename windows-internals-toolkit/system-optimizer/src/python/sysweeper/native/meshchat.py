"""组网后的设备间通信：文字 / 图片 / 视频 / 文件 / 表情 / 颜文字。

为什么单独一层
--------------
`netlink` 解决的是「能不能连上」（链接协议注册表 + mesh 发现 + 只读命令通道），
本模块解决的是「连上之后聊什么、传什么」。分工是：

    netlink   链接/发现/心跳 —— 谁在线、走哪条链路
    meshchat  内容层 —— 文字、图片、视频、文件、表情、颜文字、全体广播

协议兼容：IP Messenger（飞鸽传书 / IPMsg）
------------------------------------------
Linux 上的 **iptux**、Windows 上的 **飞鸽传书**、国内的飞秋，都跑同一套
IP Messenger 协议，因此本层按它编码就能与它们互通（前提是对方在同一网段、
端口 2425 未被防火墙拦）。

包格式（出自 H.Shirouzu 的 ipmsg.h，协议版本 1.0）：

    Ver(1):PacketNo:SenderName:SenderHost:CommandNo:AdditionalSection

- 端口 **UDP/TCP 2425**（`IPMSG_DEFAULT_PORT = 0x0979`）
- **消息走 UDP**，**文件走 TCP**（UDP 只发"我要发文件给你"的通知）
- 命令字低 8 位为主命令（`GET_MODE`），高 24 位为选项（`GET_OPT`）
- 附件属性：`fileID:filename:size:mtime:attr`，size/mtime/attr 是**十六进制**，
  多个文件用 `\\a` 分隔，文件名里的 `:` 转义成 `::`

与 Linux `wall` 的对应
----------------------
`wall` 是「给所有登录终端广播一条消息」。在组网语境里等价物是
**向所有在线节点广播**——本模块的 `wall_*` 系列就是这个语义
（点对点用 `send_text`，全体用 `wall_text`）。Android 上没有 wall，
所以广播走的是同一个 IPMsg 广播通道，不依赖系统命令。

四条安全底线（与全局一致，且本层尤其重要）
------------------------------------------
1. **附件绝不自动落盘**。收到图片/视频/文件只登记**元信息**（名字、大小、类型、
   来源），进"待收清单"，必须用户显式接受才写盘。理由：自动接收=自动执行未知
   来源的内容，是蠕虫的经典入口。
2. **绝不解析、绝不解码**收到的媒体内容。只认扩展名与大小，不调 PIL、不调
   解码器、不 eval、不起子进程。
3. **有上限**：单附件默认提示阈值 20 MiB、单条消息正文 8 KiB，超了就标注
   「过大，需人工确认」，不硬收。
4. **不执行任何对方下发的东西**：消息正文是数据，不是命令；本层没有任何
   shell / eval / importlib 调用路径。

编码坑（本模块的现实约束）
--------------------------
IPMsg 1.0 头文件里**没有** UTF-8 选项位；UTF8OPT/ENCRYPTOPT 是后来的实现
（iptux / 飞秋）扩的。本模块：
- 编码时**默认带 UTF8OPT**（与 iptux 一致的现代做法），
- 解码时**同时兼容**不带 UTF8OPT 的老包（先试 UTF-8，失败退回 GBK 再退 latin-1），
  并在结果里标出实际用的编码——不假装所有包都是 UTF-8。
"""

from __future__ import annotations

import os
import socket
import time
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# IP Messenger 协议常量（源自 ipmsg.h，协议版本 1.0）                          #
# --------------------------------------------------------------------------- #

IPMSG_VERSION = 1
IPMSG_PORT = 2425                 # 0x0979；UDP 消息 / TCP 文件
BROADCAST_ADDR = "255.255.255.255"

# 主命令（低 8 位）
C_NOOPERATION = 0x00000000
C_BR_ENTRY = 0x00000001      # 上线广播
C_BR_EXIT = 0x00000002       # 下线广播
C_ANSENTRY = 0x00000003      # 应答上线
C_BR_ABSENCE = 0x00000004    # 改为缺席
C_SENDMSG = 0x00000020       # 发送消息
C_RECVMSG = 0x00000021       # 收到回执
C_READMSG = 0x00000030
C_DELMSG = 0x00000031
C_GETFILEDATA = 0x00000060   # （TCP）请求文件数据
C_RELEASEFILES = 0x00000061  # 停止接收
C_GETDIRFILES = 0x00000062   # （TCP）请求目录
C_GETINFO = 0x00000040
C_SENDINFO = 0x00000041

# 选项位（高 24 位）
O_ABSENCEOPT = 0x00000100
O_SERVEROPT = 0x00000200
O_DIALUPOPT = 0x00010000
O_SENDCHECKOPT = 0x00000100    # 要求回执（send 命令专用语义）
O_SECRETOPT = 0x00000200       # 密封消息
O_BROADCASTOPT = 0x00000400    # 广播
O_MULTICASTOPT = 0x00000800
O_NOPOPUPOPT = 0x00001000
O_FILEATTACHOPT = 0x00200000   # 带附件
# 以下两项是 iptux / 飞秋等后续实现扩展的，不在 1.0 头文件内，按兼容位处理
O_UTF8OPT = 0x00800000
O_ENCRYPTOPT = 0x00400000

# 附件类型
F_REGULAR = 0x00000001
F_DIR = 0x00000002
F_RETPARENT = 0x00000003

HOSTLIST_DELIMIT = "\a"   # 多文件分隔符

_COMMAND_NAMES = {
    C_NOOPERATION: "NOOPERATION", C_BR_ENTRY: "BR_ENTRY",
    C_BR_EXIT: "BR_EXIT", C_ANSENTRY: "ANSENTRY", C_BR_ABSENCE: "BR_ABSENCE",
    C_SENDMSG: "SENDMSG", C_RECVMSG: "RECVMSG", C_READMSG: "READMSG",
    C_DELMSG: "DELMSG", C_GETFILEDATA: "GETFILEDATA",
    C_RELEASEFILES: "RELEASEFILES", C_GETDIRFILES: "GETDIRFILES",
    C_GETINFO: "GETINFO", C_SENDINFO: "SENDINFO",
}

_OPTION_NAMES = [
    (O_FILEATTACHOPT, "FILEATTACH"), (O_ENCRYPTOPT, "ENCRYPT"),
    (O_UTF8OPT, "UTF8"), (O_NOPOPUPOPT, "NOPOPUP"),
    (O_MULTICASTOPT, "MULTICAST"), (O_BROADCASTOPT, "BROADCAST"),
    (O_SECRETOPT, "SECRET"), (O_DIALUPOPT, "DIALUP"),
    (O_SERVEROPT, "SERVER"),
    # 注意：O_SENDCHECKOPT 与 O_ABSENCEOPT 同为 0x100，不在这里重复登记，
    # 由 option_names() 按主命令二选一，避免同一位报出两个名字。
    (O_ABSENCEOPT, "ABSENCE"),
]

# 本层自己的消息类型（IPMsg 只认"消息/附件"，具体是图片还是视频由我们判断）
KIND_TEXT = "text"
KIND_EMOJI = "emoji"
KIND_KAOMOJI = "kaomoji"
KIND_IMAGE = "image"
KIND_VIDEO = "video"
KIND_FILE = "file"

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".heic", ".avif",
             ".tiff", ".svg")
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv", ".m4v", ".ts",
             ".3gp", ".wmv")

MAX_TEXT = 8 * 1024          # 正文上限（字节）
MAX_ATTACH_HINT = 20 * 1024 * 1024   # 单附件提示阈值：超过只登记不自动收

# --------------------------------------------------------------------------- #
# 表情 / 颜文字（纯数据，离线可用，不联网拉取）                                  #
# --------------------------------------------------------------------------- #

EMOJI: Dict[str, Tuple[str, ...]] = {
    "笑脸": ("😀", "😄", "😊", "🙂", "😉", "😍", "🤩", "😎"),
    "情绪": ("😅", "😂", "🤣", "😭", "😡", "🥺", "😱", "🤔", "😴"),
    "手势": ("👍", "👎", "👏", "🙏", "✌️", "🤝", "👋", "💪"),
    "设备": ("💻", "📱", "🖥️", "⌨️", "🖨️", "💾", "🔌", "📡"),
    "状态": ("✅", "❌", "⚠️", "🔄", "⚡", "🔥", "🐢", "🚀"),
    "传输": ("📤", "📥", "📁", "📄", "🖼️", "🎬", "🔗", "📶"),
}

KAOMOJI: Dict[str, Tuple[str, ...]] = {
    "开心": ("(＾▽＾)", "(￣▽￣)ノ", "(*^ω^*)", "ヽ(´▽`)/", "(๑•̀ㅂ•́)و✧"),
    "无奈": ("(；´д｀)", "(￣▽￣;)", "(-_-;)", "(´･_･`)", "orz"),
    "惊讶": ("(⊙_⊙)", "(°ロ°)☝", "∑(￣□￣;)", "(O_O;)"),
    "抱歉": ("m(_ _)m", "(>_<)", "ヽ(；▽；)ノ", "(；へ：)"),
    "加油": ("(๑•̀ㅂ•́)و", "＼(＾▽＾)／", "(•̀ᴗ•́)و ̑̑"),
    "设备": ("[PC]~(￣▽￣)~*", "(⌐■_■)", "[ _̄_ ]", "┳━┳ ノ(゜-゜ノ)"),
}

# --------------------------------------------------------------------------- #
# 会话内状态：收件箱与待收附件（**只在内存里**，进程退出即清空）                  #
# --------------------------------------------------------------------------- #

_inbox: List[dict] = []
_pending: List[dict] = []
_seq = int(time.time()) % 100000


def _next_seq() -> int:
    global _seq
    _seq = (_seq + 1) % 1000000
    return _seq


def _node_user() -> str:
    return _safe_field(os.environ.get("USER") or os.environ.get("LOGNAME")
                       or "sysweeper")


def _node_host() -> str:
    try:
        return _safe_field(socket.gethostname() or "node")
    except Exception:  # noqa: BLE001
        return "node"


def _safe_field(s: str) -> str:
    """协议字段里 `:` 是分隔符、`\\a` 是记录分隔符，必须转义掉。

    这是**注入防护**：用户名/主机名来自环境，若不转义就能伪造出额外的协议字段
    （例如把主机名写成 `evil:32:...` 来构造一条带命令字的包）。
    """
    return (s or "").replace(":", "::").replace("\a", " ").replace("\n", " ")[:64]


# ----------------------- 编解码（纯函数，可单测） ----------------------- #

def ipmsg_encode(ver: int, seq: int, user: str, host: str, cmd: int,
                 extra: str = "") -> str:
    """编码一个 IPMsg 包为字符串（未编码字节；发送方自行 encode）。

    字段中的 `:` 会被转义为 `::`，防止伪造字段。
    """
    return ":".join([str(ver), str(seq), _safe_field(user), _safe_field(host),
                     str(int(cmd)), extra or ""])


def ipmsg_decode(packet: str) -> dict:
    """解码一个 IPMsg 包。返回 dict，含 command/options/names 等。

    容错原则：**坏包也要返回结构而不是抛异常**（网络对端不可信）。
    字段不足 6 段时按"有多少读多少"处理，并标 `malformed`。
    """
    out = {"raw": packet, "malformed": False, "encoding": "utf-8"}
    raw = (packet or "").rstrip("\x00")
    # 附加段从第 6 个 `:` 之后开始（前 5 段是协议字段），不能简单 split(':')
    parts = raw.split(":", 5)
    if len(parts) < 6:
        out["malformed"] = True
        parts = (parts + [""] * 6)[:6]
    try:
        out["version"] = int(parts[0]) if parts[0].strip() else 0
        out["seq"] = int(parts[1]) if parts[1].strip() else 0
    except ValueError:
        out["malformed"] = True
        out["version"], out["seq"] = 0, 0
    out["user"] = parts[2].replace("::", ":")
    out["host"] = parts[3].replace("::", ":")
    try:
        cmd = int(parts[4])
    except ValueError:
        cmd = 0
        out["malformed"] = True
    out["command"] = cmd
    out["mode"] = cmd & 0x000000FF
    out["options"] = cmd & 0xFFFFFF00
    out["command_name"] = _COMMAND_NAMES.get(out["mode"], f"UNKNOWN(0x{out['mode']:02x})")
    out["option_names"] = option_names(out["mode"], out["options"])
    out["extra"] = parts[5]
    return out


def option_names(mode: int, options: int) -> List[str]:
    """把选项位翻译成名字。

    注意 `0x00000100` 是**同值不同义**的：ipmsg.h 里它既叫 `ABSENCEOPT`
    （通用命令）又叫 `SENDCHECKOPT`（send 命令专用）。必须按主命令区分，
    否则一条普通发消息会被误报成"缺席"。
    """
    names = []
    for bit, name in _OPTION_NAMES:
        if not (options & bit):
            continue
        if bit == O_ABSENCEOPT:
            names.append("SENDCHECK" if mode == C_SENDMSG else "ABSENCE")
        else:
            names.append(name)
    return names


def decode_bytes(data: bytes) -> dict:
    """按字节解码：UTF-8 → GBK → latin-1 逐级回退（老客户端不都是 UTF-8）。"""
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            d = ipmsg_decode(data.decode(enc))
            d["encoding"] = enc
            return d
        except UnicodeDecodeError:
            continue
    d = ipmsg_decode(data.decode("utf-8", "replace"))
    d["encoding"] = "utf-8(replace)"
    d["malformed"] = True
    return d


def file_entry_encode(file_id: int, name: str, size: int, mtime: int,
                      attr: int = F_REGULAR) -> str:
    """编码一条附件属性：fileID:filename:size(hex):mtime(hex):attr(hex)。"""
    return f"{file_id}:{_safe_field(name)}:{size:x}:{mtime:x}:{attr:x}"


def _split_escaped(s: str, sep: str = ":") -> List[str]:
    """按分隔符切分，但把 `::` 当作**字面量**冒号（协议规定的转义）。

    直接 `split(":")` 会把 `a::photo.png` 拆成三段，导致 size 字段错位——
    这是解析带冒号文件名时的经典坑，必须按转义规则扫一遍。
    """
    out: List[str] = []
    buf = ""
    i = 0
    n = len(s or "")
    while i < n:
        ch = s[i]
        if ch == sep:
            if i + 1 < n and s[i + 1] == sep:   # 转义冒号
                buf += sep
                i += 2
                continue
            out.append(buf)
            buf = ""
            i += 1
            continue
        buf += ch
        i += 1
    out.append(buf)
    return out


def file_entry_decode(entry: str) -> dict:
    """解码一条附件属性；size/mtime/attr 是十六进制。坏条目不抛异常。"""
    parts = _split_escaped(entry)
    out = {"raw": entry, "malformed": True}
    try:
        if len(parts) >= 5:
            out.update({
                "file_id": int(parts[0], 16),
                "name": parts[1].replace("::", ":"),
                "size": int(parts[2], 16) if parts[2] else 0,
                "mtime": int(parts[3], 16) if parts[3] else 0,
                "attr": int(parts[4], 16) if parts[4] else 0,
                "malformed": False,
            })
            out["kind"] = classify_kind(out["name"])
    except ValueError:
        pass
    return out


def attachments_decode(extra: str) -> List[dict]:
    """解析一条 SENDMSG|FILEATTACH 包里的附件清单（多条用 \\a 分隔）。

    格式：`正文\\0fileID:name:size:mtime:attr\\a下一条...`
    正文与附件清单之间用 **字符 0**（\\0）分隔。
    """
    if not extra:
        return []
    body = extra
    if "\0" in extra:
        body = extra.split("\0", 1)[1]
    return [file_entry_decode(e) for e in body.split(HOSTLIST_DELIMIT) if e.strip()]


def classify_kind(name: str, has_attach: bool = True) -> str:
    """按扩展名判断内容类型。没有附件名则按正文判 emoji/颜文字。"""
    n = (name or "").lower()
    if not has_attach or not n:
        return KIND_TEXT
    if n.endswith(IMAGE_EXT):
        return KIND_IMAGE
    if n.endswith(VIDEO_EXT):
        return KIND_VIDEO
    return KIND_FILE


def classify_text(text: str) -> str:
    """判断一段纯文本是普通文字、emoji 还是颜文字。

    判据简单但可解释：含颜文字骨架字符（如 `´`、`ω`、`╹`、`orz` 等组合）
    判为 kaomoji；含 Unicode emoji 区段判为 emoji；否则 text。
    """
    t = text or ""
    if any(ch in t for ch in "＾▽￣ω´`；дω°⊙∑へ_") and "(" in t and ")" in t:
        return KIND_KAOMOJI
    if any(ord(ch) > 0x1F000 for ch in t):
        return KIND_EMOJI
    return KIND_TEXT


def build_send(text: str, files: Optional[List[dict]] = None,
               want_receipt: bool = True, broadcast: bool = False) -> Tuple[str, int]:
    """构造一条 SENDMSG 包（含可选附件）。返回 (包字符串, 命令字)。

    附件只登记**属性**（名字/大小/时间），**不含内容**——内容走 TCP 且需对方确认。
    """
    cmd = C_SENDMSG | O_UTF8OPT
    if want_receipt:
        cmd |= O_SENDCHECKOPT
    if broadcast:
        cmd |= O_BROADCASTOPT
    extra = (text or "")[:MAX_TEXT]
    if files:
        cmd |= O_FILEATTACHOPT
        entries = [file_entry_encode(f.get("file_id", i + 1), f.get("name", ""),
                                     int(f.get("size", 0)), int(f.get("mtime", 0)),
                                     int(f.get("attr", F_REGULAR)))
                   for i, f in enumerate(files)]
        extra = extra + "\0" + HOSTLIST_DELIMIT.join(entries)
    return (ipmsg_encode(IPMSG_VERSION, _next_seq(), _node_user(), _node_host(),
                         cmd, extra), cmd)


def build_entry(absent: bool = False) -> Tuple[str, int]:
    """上线广播包（BR_ENTRY），缺席模式用 BR_ABSENCE。"""
    cmd = (C_BR_ABSENCE | O_ABSENCEOPT) if absent else C_BR_ENTRY
    return (ipmsg_encode(IPMSG_VERSION, _next_seq(), _node_user(), _node_host(),
                         cmd, _node_host()), cmd)


def build_exit() -> Tuple[str, int]:
    """下线广播包（BR_EXIT）。"""
    return (ipmsg_encode(IPMSG_VERSION, _next_seq(), _node_user(), _node_host(),
                         C_BR_EXIT, ""), C_BR_EXIT)


def build_receipt(seq: int) -> Tuple[str, int]:
    """收到回执（RECVMSG）：附加段填对方包序号。"""
    return (ipmsg_encode(IPMSG_VERSION, _next_seq(), _node_user(), _node_host(),
                         C_RECVMSG, str(seq)), C_RECVMSG)


# ----------------------- 收件箱（只登记，不落盘） ----------------------- #

def inbox_add(decoded: dict, source: str = "") -> dict:
    """把一条解码后的消息登记进收件箱。

    附件**只登记元信息**并进"待收清单"，绝不自动保存、绝不解码内容。
    """
    atts = []
    if decoded.get("options", 0) & O_FILEATTACHOPT:
        atts = attachments_decode(decoded.get("extra", ""))
    text = decoded.get("extra", "")
    if atts:
        text = text.split("\0", 1)[0]
    entry = {
        "seq": decoded.get("seq"),
        "from_user": decoded.get("user", ""),
        "from_host": decoded.get("host", ""),
        "source": source,
        "encoding": decoded.get("encoding", "utf-8"),
        "text": text[:MAX_TEXT],
        "kind": KIND_FILE if atts else classify_text(text),
        "ts": int(time.time()),
        "attachments": [
            {"name": a.get("name", ""), "size": a.get("size", 0),
             "kind": a.get("kind", KIND_FILE),
             "too_big": a.get("size", 0) > MAX_ATTACH_HINT}
            for a in atts
        ],
    }
    _inbox.append(entry)
    if len(_inbox) > 200:
        _inbox[:] = _inbox[-200:]
    for a in entry["attachments"]:
        _pending.append({"from": f"{entry['from_user']}@{entry['from_host']}",
                         **a, "seq": entry["seq"], "accepted": False})
    return entry


def inbox() -> List[dict]:
    return list(_inbox)


def pending_files() -> List[dict]:
    """待用户确认的附件清单（默认全部未接受）。"""
    return list(_pending)


def inbox_clear() -> None:
    _inbox.clear()
    _pending.clear()


# ----------------------- 网络动作（失败一律降级，不抛异常） ----------------------- #

def _udp_send(payload: str, addr: str, port: int = IPMSG_PORT,
              timeout: float = 2.0) -> Tuple[bool, str]:
    try:
        data = payload.encode("utf-8", "replace")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(timeout)
            s.sendto(data, (addr, port))
        return True, f"已发送到 {addr}:{port}（{len(data)} 字节）"
    except Exception as e:  # noqa: BLE001
        return False, f"发送失败（{e}）：检查网段、防火墙是否放行 UDP {port}"


def announce(absent: bool = False) -> Tuple[bool, str]:
    """向本网段广播上线（对应飞鸽的"我来也"）。"""
    pkt, cmd = build_entry(absent)
    return _udp_send(pkt, BROADCAST_ADDR)


def say_goodbye() -> Tuple[bool, str]:
    pkt, _ = build_exit()
    return _udp_send(pkt, BROADCAST_ADDR)


def send_text(target: str, text: str, want_receipt: bool = True) -> Tuple[bool, str]:
    """点对点发文字（含表情 / 颜文字，它们本质也是文字）。"""
    if not target:
        return False, "缺少目标地址"
    pkt, _ = build_send(text, want_receipt=want_receipt)
    return _udp_send(pkt, target)


def wall_text(text: str) -> Tuple[bool, str]:
    """全体广播（对应 Linux `wall` 的语义：所有在线节点都收到）。"""
    pkt, _ = build_send(text, want_receipt=False, broadcast=True)
    return _udp_send(pkt, BROADCAST_ADDR)


def send_files(target: str, files: List[dict], text: str = "") -> Tuple[bool, str]:
    """发附件通知：UDP 只发**属性**，真正的字节走 TCP 且需对方发起请求。

    本函数**不读取文件内容**、不建 TCP 监听——那需要用户显式决定要不要共享，
    属于写操作，交给上层（任务层）以 manual 指引给出。
    """
    if not target:
        return False, "缺少目标地址"
    if not files:
        return False, "没有附件"
    big = [f for f in files if int(f.get("size", 0)) > MAX_ATTACH_HINT]
    pkt, _ = build_send(text or "（附件）", files=files)
    ok, msg = _udp_send(pkt, target)
    if ok and big:
        msg += f"；注意：{len(big)} 个附件超过 {MAX_ATTACH_HINT // 1024 // 1024} MiB，对方需确认"
    return ok, msg


def listen_once(port: int = IPMSG_PORT, timeout: float = 3.0) -> Tuple[bool, str]:
    """听一个 UDP 包并登记进收件箱（**只读**，不回包、不落盘）。

    用于验证「本网段确实有人在说话」；不适合长期驻守（那应走 netlink 的 mesh 服务）。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("", port))
            s.settimeout(timeout)
            data, addr = s.recvfrom(8192)
    except socket.timeout:
        return False, f"{timeout} 秒内没有收到任何 IPMsg 包（本网段可能没有其它节点）"
    except Exception as e:  # noqa: BLE001
        return False, f"监听失败（{e}）：UDP {port} 可能被占用或无权绑定"
    d = decode_bytes(data)
    inbox_add(d, source=f"{addr[0]}:{addr[1]}")
    return True, (f"来自 {addr[0]}:{addr[1]} 的 {d['command_name']} "
                  f"（{d.get('encoding')} 编码）已登记")


# ----------------------- 节点发现注册表（SW-OFFER1 能力通告） ----------------------- #
#
# 背景：distjob 已经能「编码出」能力通告（offer_text，前缀 SW-OFFER1:），
# 但「收到邻居的通告后谁在、能不能接活、多久没动静了该剔除」这套登记逻辑
# 一直没补——等于会广播却不会「听」。本段补齐：把收到的能力通告登记进
# 内存表，带 TTL 过期，让派活方能回答「当前网里哪些节点可派」。
#
# 注意循环依赖：distjob 顶层 import 了 meshchat，所以这里**不能在模块加载期**
# import distjob，只在函数里惰性 import。

_NODES: Dict[str, dict] = {}   # node_id -> {addr, caps, seen, expires_at}
OFFER_TTL = 600                # 能力通告有效期（秒）：超过 10 分钟没再广播就视为离线


def register_offer(payload: str, addr: str, now: Optional[float] = None) -> Tuple[bool, str]:
    """登记一条能力通告（SW-OFFER1:）。解析失败 / 非本前缀 → 忽略不报错。

    addr 是发送方地址（"1.2.3.4:2425" 或 "1.2.3.4"），用于回派活时寻址。
    返回 (是否登记成功, 说明)。
    """
    from . import distjob

    now = now if now is not None else time.time()
    d = distjob.decode_offer(payload)
    if d is None:
        return False, "不是有效的能力通告（前缀/JSON 不对，忽略）"
    node_id = str(addr)
    _NODES[node_id] = {
        "addr": addr,
        "caps": d,
        "seen": now,
        "expires_at": now + OFFER_TTL,
    }
    return True, f"已登记节点 {addr}（cores={d.get('cores')}, score={d.get('score')}）"


def expire_old(now: Optional[float] = None) -> int:
    """剔除过期的节点（超过 TTL 未再广播）。返回剔除数量。"""
    now = now if now is not None else time.time()
    dead = [k for k, v in _NODES.items() if v["expires_at"] < now]
    for k in dead:
        _NODES.pop(k, None)
    return len(dead)


def known_nodes() -> List[dict]:
    """当前在线节点列表（已过期的不算），按最近见到时间倒序。"""
    now = time.time()
    expire_old(now)
    return sorted(_NODES.values(), key=lambda v: v["seen"], reverse=True)


def announce_offer() -> Tuple[bool, str]:
    """广播本机能力通告（SW-OFFER1:），让网里邻居知道我能接活。"""
    from . import distjob

    pkt = distjob.offer_text()
    return _udp_send(pkt, BROADCAST_ADDR)


def node_report() -> Tuple[bool, str]:
    """节点发现状态报告（只读）。"""
    now = time.time()
    expire_old(now)
    lines = [f"==== 节点发现（能力通告 SW-OFFER1，TTL={OFFER_TTL}s）====", ""]
    if not _NODES:
        lines.append("当前未登记到任何邻居节点。")
        lines.append("可在本机运行「能力通告」广播自己，或收到邻居广播后自动登记。")
        return True, "\n".join(lines)
    lines.append(f"在线节点 {len(_NODES)} 个：")
    for v in sorted(_NODES.values(), key=lambda x: x["seen"], reverse=True):
        remain = max(0, int(v["expires_at"] - now))
        caps = v["caps"]
        lines.append(f"  · {v['addr']}  cores={caps.get('cores')} "
                     f"score={caps.get('score')}  TTL 剩余 {remain}s")
    lines.append("")
    lines.append("说明：节点表只在内存，重启清空；过期（10 分钟无广播）自动剔除。")
    return True, "\n".join(lines)


# ----------------------- 报告（给任务层 / GUI / CLI 用） ----------------------- #

def _fmt_size(n: int) -> str:
    f = float(n or 0)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if f < 1024 or unit == "GiB":
            return f"{f:.0f} {unit}" if unit == "B" else f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} GiB"


def emoji_report() -> Tuple[bool, str]:
    """内置表情表（离线，不联网）。"""
    lines = [f"内置表情 {sum(len(v) for v in EMOJI.values())} 个（{len(EMOJI)} 类，离线可用）：", ""]
    for cat, items in EMOJI.items():
        lines.append(f"  {cat}：{' '.join(items)}")
    lines += ["", "说明：emoji 是 Unicode 字符，直接随文字发送即可（走 UTF8OPT）。"]
    return True, "\n".join(lines)


def kaomoji_report() -> Tuple[bool, str]:
    """内置颜文字表（离线，不联网）。"""
    lines = [f"内置颜文字 {sum(len(v) for v in KAOMOJI.values())} 个（{len(KAOMOJI)} 类，离线可用）：", ""]
    for cat, items in KAOMOJI.items():
        lines.append(f"  {cat}：{' '.join(items)}")
    lines += ["", "说明：颜文字由 ASCII/全角标点拼成，兼容性比 emoji 更好——",
              "      老设备（如 Android 8）字体可能缺 emoji，但颜文字一定能显示。"]
    return True, "\n".join(lines)


def inbox_report() -> Tuple[bool, str]:
    """收件箱内容（只读；附件只显示元信息）。"""
    if not _inbox:
        return True, ("收件箱为空。可用「监听一次」接收本网段消息，"
                      "或用「上线广播」让邻居知道你在。")
    lines = [f"收件箱 {len(_inbox)} 条：", ""]
    for e in _inbox[-20:]:
        ts = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
        lines.append(f"  [{ts}] {e['from_user']}@{e['from_host']} "
                     f"（{e['kind']}）: {e['text'][:60]}")
        for a in e["attachments"]:
            flag = " [过大，需确认]" if a["too_big"] else ""
            lines.append(f"        · 附件 {a['name']} · {_fmt_size(a['size'])} "
                         f"· {a['kind']}{flag}")
    if _pending:
        lines += ["", f"待确认附件 {len(_pending)} 个（**未落盘**，需你显式接受）："]
        for p in _pending[:10]:
            lines.append(f"  · {p['from']} → {p['name']}（{_fmt_size(p['size'])}）")
    return True, "\n".join(lines)


def protocol_report() -> Tuple[bool, str]:
    """协议与端口说明（只读；含安全边界）。"""
    lines = [
        "IP Messenger（飞鸽传书 / iptux / 飞秋）协议兼容层：",
        "",
        f"  端口：UDP {IPMSG_PORT}（消息） / TCP {IPMSG_PORT}（文件）",
        "  包格式：版本:序号:用户名:主机名:命令字:附加段",
        f"  本机身份：{_node_user()}@{_node_host()}",
        "",
        "命令字（低 8 位主命令 + 高 24 位选项）：",
    ]
    for cmd, name in sorted(_COMMAND_NAMES.items()):
        if cmd:
            lines.append(f"  0x{cmd:08x}  {name}")
    lines += [
        "",
        "选项位（可组合）：" + "、".join(f"{n}(0x{b:06x})" for b, n in _OPTION_NAMES[:6]),
        "",
        "与 Linux wall 的对应：wall = 向所有在线节点广播（本层 wall_text）。",
        "",
        "安全边界：",
        "  1. 附件绝不自动落盘 —— 只登记元信息，必须你显式接受；",
        "  2. 绝不解码/解析媒体内容 —— 只认扩展名与大小；",
        f"  3. 单附件超过 {MAX_ATTACH_HINT // 1024 // 1024} MiB 只登记不自动收；",
        "  4. 收到的一切都是数据，不是命令 —— 本层无任何执行路径。",
    ]
    return True, "\n".join(lines)
