"""链接层/传输层协议注册表 + 本地自组网（mesh）/ 人机交互（HCI）。

本模块把用户要求的「多种网络链接协议」按各自协议与接口登记，并提供一层
**本地自组网（mesh）**：启用网络后，多于 1 台设备能自己通信（UDP 广播发现 +
TCP 可靠通道），并支持人机交互（HCI）。

设计原则（与全局一致）：纯标准库、零依赖、离线优先；只读探测与写接口均返回
``(ok, msg)`` 元组；非对应平台/接口返回 ``(False, 降级说明)``，绝不抛异常。

安全底线（最关键）：mesh 的命令通道**只接受只读安全命令**
（``info`` / ``ping`` / ``probe`` / ``msg``），用固定白名单分发，**绝不在任
何情况下执行任意命令**（不调 shell、不 eval、不落盘脚本）。``msg`` 是人机交互
通道，仅做消息回显/记录，不触发任何写操作。

引用标准（见 data/link_protocols.json）：
- TCP  : RFC 9293 / RFC 7323 / RFC 9002（IETF，传输层）
- UDP  : RFC 768（IETF，传输层）
- RFCOMM: Bluetooth SIG（ETSI TS 07.10，串口仿真，承载于 L2CAP）
- 串口 : TIA-232 / ITU-T V.24（物理层）
- BLE  : Bluetooth Core Spec 4.0+（LE 链路层，GATT/ATT 之上）
- 802.15.4: IEEE 802.15.4-2020（Zigbee/Thread/6LoWPAN 的 PHY+MAC 底座）
"""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
import time
from typing import Dict, List, Optional, Tuple

from . import common

# --------------------------------------------------------------------------- #
# 链接层/传输层协议注册表（按各自协议与接口引用权威文档）                         #
# --------------------------------------------------------------------------- #


def _load_docs() -> dict:
    """从 data/link_protocols.json 载入协议文档（含 protocols/interfaces 等）。"""
    try:
        from importlib import resources
        data = resources.files("sysweeper.data").joinpath(
            "link_protocols.json").read_text(encoding="utf-8")
        return json.loads(data)
    except Exception:
        return {}


LINK_DOCS = _load_docs()


def _have(cmd: str) -> bool:
    return bool(shutil_which(cmd))


def shutil_which(cmd: str) -> Optional[str]:
    try:
        import shutil
        return shutil.which(cmd)
    except Exception:  # noqa: BLE001
        return None


# 各协议的「能力探测」：只读、优雅降级，返回 (ok, msg)。
# ok=True 表示本机具备该协议所需的接口/栈；否则给出降级说明。
def _cap_tcp() -> Tuple[bool, str]:
    """TCP：只要有可用 IP 栈即可（几乎全平台）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.close()
        return True, "TCP 栈可用（socket(AF_INET, SOCK_STREAM) 成功）"
    except Exception as e:  # noqa: BLE001
        return False, f"TCP 栈不可用: {e}"


def _cap_udp() -> Tuple[bool, str]:
    """UDP：只要有可用 IP 栈即可（几乎全平台）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.close()
        return True, "UDP 栈可用（socket(AF_INET, SOCK_DGRAM) 成功）"
    except Exception as e:  # noqa: BLE001
        return False, f"UDP 栈不可用: {e}"


def _cap_rfcomm() -> Tuple[bool, str]:
    """RFCOMM：经典蓝牙串口仿真，依赖 bluetoothd + 已配对设备。"""
    if not _have("bluetoothctl") and not _bluez_bus():
        return False, "未检测到 BlueZ（bluetoothctl 不可用），RFCOMM 需蓝牙栈支持"
    return True, "BlueZ 可用（RFCOMM 在已配对链路上经 rfcomm bind 仿真串口）"


def _cap_serial() -> Tuple[bool, str]:
    """串口：看本机是否有 tty 设备（/dev/ttyS*/ttyUSB*/ttyACM*）。"""
    devs = []
    for base in ("/dev/ttyS", "/dev/ttyUSB", "/dev/ttyACM", "/dev/ttyAMA"):
        for i in range(8):
            p = f"{base}{i}"
            if os.path.exists(p):
                devs.append(p)
    if devs:
        return True, f"发现串口设备: {', '.join(devs[:6])}" + (" …" if len(devs) > 6 else "")
    return False, "未发现串口设备（/dev/ttyS*|ttyUSB*|ttyACM*）；嵌入式/调试场景才有"


def _cap_ble() -> Tuple[bool, str]:
    """BLE：低功耗蓝牙，依赖支持 LE 的蓝牙适配器。"""
    if not _have("bluetoothctl") and not _bluez_bus():
        return False, "未检测到 BlueZ，BLE 需蓝牙栈支持"
    return True, "BlueZ 可用（BLE 设备经 bluetoothctl scan on 发现，GATT 在 L2CAP/ATT 之上）"


def _cap_ieee802154() -> Tuple[bool, str]:
    """802.15.4：低速无线个域网，依赖内核 ieee802154 子系统 + 收发器。"""
    if os.path.exists("/sys/class/ieee802154"):
        return True, "内核已编入 IEEE 802.15.4 子系统（/sys/class/ieee802154 存在）"
    if _have("iwpan"):
        return True, "发现 iwpan（wpan-tools），可通过 iwpan phy 配置 802.15.4 设备"
    return False, ("未检测到 802.15.4 收发器（无 /sys/class/ieee802154、无 iwpan）；"
                   "桌面通常无此硬件，属正常降级")


def _bluez_bus() -> bool:
    """粗略判断 BlueZ D-Bus 是否可能存在（不强制依赖 dbus 模块）。"""
    if os.path.exists("/var/run/dbus"):
        return True
    return _have("busctl") or _have("dbus-send")


# 注册表：(协议 id, OSI 层, 能力探测函数)。能力探测均为只读、优雅降级。
LINK_PROTOCOLS = (
    ("tcp", "L4 传输层", _cap_tcp),
    ("udp", "L4 传输层", _cap_udp),
    ("rfcomm", "L2 之上（串口仿真，承载于 L2CAP）", _cap_rfcomm),
    ("serial", "L1 物理层", _cap_serial),
    ("ble", "L1/L2（LE 链路层，GATT/ATT 之上）", _cap_ble),
    ("ieee802154", "L1/L2（PHY+MAC，Zigbee/Thread/6LoWPAN 底座）", _cap_ieee802154),
)


def protocol_doc(pid: str) -> dict:
    """返回某链接协议的文档（含 protocols/interfaces/docs/summary/advice）。"""
    return LINK_DOCS.get(pid, {})


def protocol_capable(pid: str) -> Tuple[bool, str]:
    """探测本机是否具备某链接协议所需接口/栈（只读）。"""
    for id_, _layer, fn in LINK_PROTOCOLS:
        if id_ == pid:
            return fn()
    return False, f"未知链接协议: {pid}"


def list_protocols() -> List[str]:
    """返回链接协议注册表的文本行（供 CLI/GUI 展示）。"""
    lines = ["链接层/传输层协议注册表（按各自协议与接口引用权威文档）："]
    for id_, layer, _fn in LINK_PROTOCOLS:
        doc = LINK_DOCS.get(id_, {})
        name = doc.get("name", id_)
        org = doc.get("org", "")
        lines.append(f"  · {id_}  [{layer}]  {name}")
        lines.append(f"      机构: {org}")
        lines.append(f"      文档: {doc.get('url', '')}")
        lines.append(f"      标准: {'; '.join(doc.get('protocols', [])[:3])}")
        lines.append(f"      接口: {'; '.join(doc.get('interfaces', [])[:3])}")
        cap, msg = protocol_capable(id_)
        lines.append(f"      本机能力: {'✓ 可用' if cap else '× 不可用'} — {msg}")
    return lines


def environment_report() -> List[str]:
    """本机链接协议能力概览（✓ 可用 / × 不可用）。"""
    lines = ["链接协议能力概览："]
    for id_, layer, _fn in LINK_PROTOCOLS:
        cap, msg = protocol_capable(id_)
        mark = "✓" if cap else "✗"
        lines.append(f"   {mark} {id_} [{layer}] — {msg}")
    return lines


# --------------------------------------------------------------------------- #
# 本地自组网（PeerMesh）：UDP 广播发现 + TCP 可靠通道 + 只读安全命令通道          #
# --------------------------------------------------------------------------- #
#
# 设计要点：
#   - 发现（discovery）：UDP 广播/组播「信标」(beacon)，带本节点 info；非连接态。
#   - 互联（channel）  ：TCP 监听 + 接受；每条消息用 frame()/parse() 定长帧封装。
#   - 命令通道（HCI）  ：仅白名单 info/ping/probe/msg，handle_mesh_command 固定
#                        分发，**绝不执行任意命令**。msg 仅回显/记录，不写系统。
# --------------------------------------------------------------------------- #

MESH_PORT = 47999
MESH_MAGIC = b"SWMH"          # SysWeeper Mesh Header 魔数
MESH_VERSION = 1
_HEAD_FMT = "!BHI"                                    # 版本(B) + 载荷长度(I) + 标志(H) = 7
_HEAD_LEN = len(MESH_MAGIC) + struct.calcsize(_HEAD_FMT)   # 4 + 7 = 11
MESH_ADDR = "255.255.255.255"  # 受限广播（本网段发现）
MESH_COMMANDS = ("info", "ping", "probe", "msg")  # 只读安全命令白名单
# 节点自报能力（供 peers 选择用哪种链接协议互联，呼应上面的注册表）
_NODE_NAME = socket.gethostname() or "sysweeper-node"
_NODE_VERSION = "0.5.18"


def frame(cmd: str, payload=None) -> bytes:
    """把一条 mesh 消息编码成「魔数+版本+长度+JSON」的定长帧（纯函数）。

    cmd 必须是白名单命令之一；payload 为任意可 JSON 序列化的对象。
    返回可被套接字直接 send 的字节串。
    """
    if cmd not in MESH_COMMANDS:
        # 越权命令：拒绝编码，绝不发出任意命令
        cmd = "msg"
        payload = {"error": f"命令 {cmd!r} 不在白名单 {MESH_COMMANDS}"}
    body = json.dumps({"cmd": cmd, "payload": payload or {}},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = MESH_MAGIC + struct.pack(_HEAD_FMT, MESH_VERSION, len(body), 0)
    return header + body


def parse(data: bytes) -> Tuple[str, dict]:
    """解析一条完整的 mesh 帧（纯函数）。返回 (cmd, payload)。

    输入须是 frame() 产出的完整字节串；不完整/损坏的帧抛 ValueError（由调用方
    按连接读取完整帧后再解析，不在此处做网络 I/O）。
    """
    if len(data) < _HEAD_LEN or data[:4] != MESH_MAGIC:
        raise ValueError("非法的 mesh 帧（魔数或长度不符）")
    ver, blen, _flags = struct.unpack(_HEAD_FMT, data[4:_HEAD_LEN])
    if ver != MESH_VERSION:
        raise ValueError(f"不支持的 mesh 帧版本: {ver}")
    body = data[_HEAD_LEN:_HEAD_LEN + blen]
    if len(body) != blen:
        raise ValueError("mesh 帧长度不足（不完整）")
    obj = json.loads(body.decode("utf-8"))
    return obj.get("cmd", "msg"), obj.get("payload", {})


def _recv_frame(sock: socket.socket, timeout: float = 5.0) -> Optional[Tuple[str, dict]]:
    """从已连接 TCP 套接字读取一条完整 mesh 帧（处理拆包）。返回 (cmd, payload)。"""
    sock.settimeout(timeout)
    try:
        head = _recv_exact(sock, _HEAD_LEN)
        if len(head) < _HEAD_LEN or head[:4] != MESH_MAGIC:
            return None
        ver, blen, _flags = struct.unpack(_HEAD_FMT, head[4:_HEAD_LEN])
        if ver != MESH_VERSION:
            return None
        body = _recv_exact(sock, blen)
        if len(body) != blen:
            return None
        obj = json.loads(body.decode("utf-8"))
        return obj.get("cmd", "msg"), obj.get("payload", {})
    except (socket.timeout, OSError, ValueError, json.JSONDecodeError):
        return None


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            break
        buf += chunk
    return buf


def _local_info() -> dict:
    """本节点自报信息（只读，不含任何 PII）。"""
    caps = []
    for id_, _layer, _fn in LINK_PROTOCOLS:
        ok, _ = protocol_capable(id_)
        if ok:
            caps.append(id_)
    info = {
        "name": _NODE_NAME,
        "version": _NODE_VERSION,
        "port": MESH_PORT,
        "caps": caps,                      # 本节点支持的链接协议（供 peers 选择）
        "commands": list(MESH_COMMANDS),  # 本节点支持的只读安全命令
        "ts": int(time.time()),
    }
    # 同人设备资源共享：握手即宣告「愿共享的算力/网络」与「永不共享的数据」。
    # 只含种类标签，不含任何个人信息；探测失败则退化为空清单。
    try:
        from . import reshare
        man = reshare.share_manifest()
        info["share"] = {"offered": man.get("offered", []),
                         "blocked": man.get("blocked", []),
                         "note": man.get("note", "")}
    except Exception:  # noqa: BLE001
        info["share"] = {"offered": [], "blocked": [], "note": ""}
    return info


def handle_mesh_command(cmd: str, payload: dict, info: dict) -> dict:
    """mesh 命令分发（**安全核心**）：仅白名单命令，只读，绝不执行任意命令。

    - info  : 返回本节点信息（自组织/拓扑用）
    - ping  : 回显，用于连通性与时延探测
    - probe : 运行一个本地只读探测（本机链接协议能力），不碰系统配置
    - msg   : 人机交互/设备间消息：仅回显并记入会话日志，不触发任何写操作
    返回响应 dict。任何不在白名单的命令一律当作 msg 处理并给出错误提示。
    """
    payload = payload or {}
    if cmd == "info":
        return {"info": info}
    if cmd == "ping":
        return {"pong": True, "echo": payload.get("text"), "ts": int(time.time())}
    if cmd == "probe":
        # 只读：探测本机链接协议能力（呼应注册表）；不做任何写
        out = []
        for id_, layer, _fn in LINK_PROTOCOLS:
            ok, msg = protocol_capable(id_)
            out.append({"id": id_, "layer": layer, "ok": ok, "msg": msg})
        return {"probe": out}
    if cmd == "msg":
        text = str(payload.get("text", ""))
        # 人机交互通道：仅回显+记录，不执行、不落盘、不转发到 shell
        return {"msg": text, "from": info.get("name"), "received": True,
                "note": "消息通道仅回显/记录，不触发任何写操作"}
    # 越权命令：绝不执行，降级为 msg 错误回显
    return {"msg": f"命令 {cmd!r} 不在只读安全白名单 {MESH_COMMANDS}，已忽略",
            "error": "forbidden"}


# 会话内收到的 mesh 消息（msg 通道），供 GUI/CLI 展示「人机交互」记录。
_mesh_inbox: List[dict] = []
_mesh_lock = threading.Lock()


def _inbox_append(entry: dict) -> None:
    with _mesh_lock:
        _mesh_inbox.append(entry)
        if len(_mesh_inbox) > 200:
            _mesh_inbox[:] = _mesh_inbox[-200:]


def mesh_inbox() -> List[dict]:
    """返回会话内收到的 msg 通道消息（人机交互记录，只读快照）。"""
    with _mesh_lock:
        return list(_mesh_inbox)


class PeerMesh:
    """本地自组网节点：UDP 发现 + TCP 命令通道（只读安全）。

    默认端口 MESH_PORT（47999），魔数/版本见模块常量。服务与发现均在独立线程
    运行，避免阻塞调用方（GUI 主线程）。命令通道只接受 MESH_COMMANDS。
    """

    def __init__(self, port: int = MESH_PORT, bind: str = "0.0.0.0",
                 broadcast: str = MESH_ADDR):
        self.port = port
        self.bind = bind
        self.broadcast = broadcast
        self.info = _local_info()
        self._tcp = None
        self._udp = None
        self._running = threading.Event()
        self._thread = None
        self._disc_thread = None
        self.peers: Dict[str, dict] = {}   # addr -> info

    # ---- 服务：TCP 命令通道 + UDP 信标 ----
    def start(self) -> Tuple[bool, str]:
        if self._running.is_set():
            return True, f"mesh 已在运行（端口 {self.port}）"
        try:
            self._tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._tcp.bind((self.bind, self.port))
            self._tcp.listen(16)
        except OSError as e:
            return False, f"无法绑定 TCP 命令通道 {self.bind}:{self.port} — {e}"
        self._running.set()
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()
        self._disc_thread = threading.Thread(target=self._beacon_loop, daemon=True)
        self._disc_thread.start()
        return True, (f"本地自组网已启动：TCP 命令通道 {self.bind}:{self.port}，"
                      f"UDP 信标广播 {self.broadcast}:{self.port}；"
                      f"命令通道仅接受 {MESH_COMMANDS}")

    def _serve_loop(self) -> None:
        while self._running.is_set():
            try:
                self._tcp.settimeout(1.0)
                conn, addr = self._tcp.accept()
            except (socket.timeout, OSError):
                continue
            t = threading.Thread(target=self._handle_conn,
                                 args=(conn, addr), daemon=True)
            t.start()

    def _handle_conn(self, conn: socket.socket, addr) -> None:
        try:
            while self._running.is_set():
                parsed = _recv_frame(conn, timeout=5.0)
                if parsed is None:
                    break
                cmd, payload = parsed
                # 安全分发：只走白名单，绝不执行任意命令
                resp = handle_mesh_command(cmd, payload, self.info)
                if cmd == "info" and isinstance(payload, dict) and payload.get("peer"):
                    with _mesh_lock:
                        self.peers[str(addr)] = payload.get("peer")
                if cmd == "msg":
                    _inbox_append({"from": str(addr), "text": str(payload.get("text", "")),
                                  "ts": int(time.time())})
                conn.sendall(frame("msg", resp))
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _beacon_loop(self) -> None:
        """周期性发 UDP 信标（发现）。非连接态、只读广播本节点 info。"""
        try:
            self._udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._udp.bind(("", self.port))  # 复用端口收响应
        except OSError:
            return
        while self._running.is_set():
            try:
                self._udp.sendto(frame("info", {"peer": self.info}),
                                 (self.broadcast, self.port))
            except OSError:
                pass
            # 同时尝试收其他节点的信标（发现对端）
            try:
                self._udp.settimeout(0.5)
                data, addr = self._udp.recvfrom(4096)
                parsed = _safe_parse(data)
                if parsed and parsed[0] == "info":
                    peer = (parsed[1] or {}).get("peer", {})
                    if peer:
                        with _mesh_lock:
                            self.peers[str(addr)] = peer
            except (socket.timeout, OSError):
                pass
            time.sleep(2.0)

    def stop(self) -> None:
        self._running.clear()
        for s in (self._tcp, self._udp):
            try:
                if s:
                    s.close()
            except OSError:
                pass

    # ---- 发现：主动探测对端 ----
    def discover(self, timeout: float = 3.0) -> List[dict]:
        """发送 info 探测并收集对端回应的本节点信息（只读发现）。"""
        found: List[dict] = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(timeout)
            s.sendto(frame("info", {"peer": self.info}), (self.broadcast, self.port))
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    data, addr = s.recvfrom(4096)
                except socket.timeout:
                    break
                parsed = _safe_parse(data)
                if parsed and parsed[0] == "info":
                    peer = (parsed[1] or {}).get("peer", {})
                    if peer:
                        peer = dict(peer)
                        peer["addr"] = str(addr)
                        found.append(peer)
        except OSError as e:
            return [{"error": str(e)}]
        finally:
            try:
                s.close()
            except OSError:
                pass
        return found

    # ---- 人机交互：向某 peer 发消息（msg 通道，仅回显/记录）----
    def send_msg(self, text: str, host: str = "127.0.0.1") -> Tuple[bool, str]:
        """向 host:port 发送一条 msg（人机交互通道）。仅回显/记录，不执行命令。"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((host, self.port))
            s.sendall(frame("msg", {"text": text}))
            parsed = _recv_frame(s, timeout=5.0)
            s.close()
            if parsed is None:
                return True, "消息已发出（未收到回执）"
            return True, f"已送达 {host}: {parsed[1].get('msg', '')}"
        except OSError as e:
            return False, f"发送失败: {e}"


def _safe_parse(data: bytes) -> Optional[Tuple[str, dict]]:
    try:
        return parse(data)
    except (ValueError, json.JSONDecodeError):
        return None


# --------------------------------------------------------------------------- #
# 任务派发用的无参包装（runner 以 fn() 派发；详见 runner._run_native）           #
# 这些函数无必填参数，且非目标环境优雅降级为指引，绝不抛异常、绝不执行任意命令。  #
# --------------------------------------------------------------------------- #

def link_report() -> Tuple[bool, str]:
    """多种网络链接协议清单 + 本机能力（只读）。供任务 native 通道调用。"""
    try:
        lines = ["可导入的网络链接协议（按各自协议与接口引用权威文档）："]
        for id_, layer, _fn in LINK_PROTOCOLS:
            doc = protocol_doc(id_)
            name = doc.get("name", id_)
            org = doc.get("org", "")
            protos = "、".join(doc.get("protocols", []) or [])
            ok, msg = protocol_capable(id_)
            lines.append(f"  · [{id_}] {name}（{org}）层级={layer}")
            if protos:
                lines.append(f"      协议: {protos}")
            lines.append(f"      本机能力: {'✓' if ok else '×'} {msg}")
            for u in (doc.get("docs", []) or [])[:2]:
                lines.append(f"      文档: {u}")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"链接协议报告生成失败: {e}"


def mesh_report() -> Tuple[bool, str]:
    """本机链接协议能力 + mesh 可运行性概览（只读报告，供任务 native 通道）。"""
    try:
        lines = ["本地自组网（mesh）/ 人机交互 就绪态："]
        for id_, layer, _fn in LINK_PROTOCOLS:
            ok, msg = protocol_capable(id_)
            lines.append(f"  · {id_} [{layer}]: {'✓' if ok else '×'} {msg}")
        lines.append(f"  · 命令通道白名单: {', '.join(MESH_COMMANDS)}（只读，绝不执行任意命令）")
        lines.append(f"  · 默认端口: {MESH_PORT}（TCP 命令通道 + UDP 发现信标）")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"mesh 报告生成失败: {e}"


def mesh_serve() -> Tuple[bool, str]:
    """启动本地自组网（守护线程：TCP 命令通道 + UDP 发现）。无参、可重复安全调用。"""
    try:
        m = PeerMesh()
        ok, msg = m.start()
        if ok:
            # 保存引用避免被 GC（守护线程仍运行，但保留对象便于 stop）
            _last_mesh.append(m)
        return ok, msg
    except Exception as e:  # noqa: BLE001
        return False, f"mesh 启动失败: {e}"


_last_mesh: List[PeerMesh] = []


def mesh_discover() -> Tuple[bool, str]:
    """发现本网段内的 mesh 对端（只读）。返回 (ok, 节点清单文本)。"""
    try:
        m = PeerMesh()
        found = m.discover(timeout=2.0)
        if not found:
            return True, "未发现其他 mesh 节点（本机可先 mesh_serve 自组一个；需多台设备才互联）"
        lines = [f"发现 {len(found)} 个 mesh 节点（只读）："]
        for p in found:
            lines.append(f"  · {p.get('name', '?')} @ {p.get('addr', '?')}"
                          f"  版本={p.get('version', '?')}  能力={p.get('caps', [])}")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"mesh 发现失败: {e}"


def mesh_info() -> Tuple[bool, str]:
    """返回本节点信息（自组织/拓扑用，只读）。"""
    try:
        info = _local_info()
        return True, "本节点: " + json.dumps(info, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        return False, f"读取本节点信息失败: {e}"


def mesh_send_msg(text: str = "") -> Tuple[bool, str]:
    """人机交互：向本机回环发送一条 msg（演示消息通道）。仅回显/记录。

    优先复用已启动的节点（避免重复绑定同一端口导致 Address already in use）；
    没有则就地起一个。
    """
    try:
        m = _last_mesh[-1] if _last_mesh else None
        if m is None:
            m = PeerMesh()
            ok, msg = m.start()
            if not ok:
                return False, msg
            _last_mesh.append(m)
        time.sleep(0.2)
        return m.send_msg(text or "你好，这是人机交互消息通道测试")
    except Exception as e:  # noqa: BLE001
        return False, f"发送消息失败: {e}"


__all__ = [
    "LINK_DOCS", "LINK_PROTOCOLS", "MESH_PORT", "MESH_COMMANDS", "MESH_VERSION",
    "protocol_doc", "protocol_capable", "list_protocols", "environment_report",
    "frame", "parse", "handle_mesh_command", "PeerMesh", "mesh_inbox",
    "link_report", "mesh_report", "mesh_serve", "mesh_discover", "mesh_info",
    "mesh_send_msg",
]
