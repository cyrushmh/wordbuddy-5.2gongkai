"""按网络维度的隐私验证（不保存原始 PII）。

用户要求：不同网络使用「个人输入的两个以上信息」作为验证（如姓名+身份证号，
或邮箱+手机号）；**原始信息不作保存**，但能在下次启动时重新连接（即验证令牌
派生后可重连）。

设计（数据最小化，符合《个人信息保护法》PIPL 精神）：
- 用个人两项以上信息，经「随机 salt + PBKDF2-HMAC」派生一个验证令牌；
- 落盘只存：``salt``（每网络随机盐）+ ``派生令牌`` + ``字段标签``（如 name/id），
  **绝不保存原始 PII**；
- 不同网络用不同 salt，因此同名同 ID 在两个网络派生出的令牌不同（防跨网关联）；
- 下次启动只需重新输入同样两项信息，重派生并与保存的令牌常量时间比对，即「重连」。

所有函数返回 ``(ok, msg)``；非目标/缺字段优雅降级。绝不在任何路径打印或落盘原始值。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from typing import Dict, List, Optional, Tuple

DEFAULT_PATH = os.path.expanduser("~/.config/sysweeper/netauth.json")
_PBKDF2_ITERS = 100_000


# --------------------------------------------------------------------------- #
# 纯函数：派生 / 验证（不含任何 I/O，便于单测与复用）                            #
# --------------------------------------------------------------------------- #

def _normalize(fields: Dict[str, str]) -> bytes:
    """把「字段→值」规范化为可比较的字节串（去除空白、casefold、按字段名排序）。

    字段名与值都做归一化，保证「 张三 」与「张三」、大小写差异不导致验证失败。
    """
    norm = []
    for k, v in fields.items():
        kk = str(k).strip().casefold()
        vv = str(v).strip().casefold()
        if kk and vv:
            norm.append((kk, vv))
    norm.sort()
    return json.dumps(norm, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def derive(fields: Dict[str, str]) -> Tuple[str, str]:
    """派生验证令牌。返回 (salt_hex, token_hex)。

    - salt : 16 字节随机盐（每网络不同，防跨网关联）
    - token: PBKDF2-HMAC-SHA256(salt, 归一化字段)，hex
    输入为原始字段，本函数**不**持久化它们；调用方须自行丢弃原始值。
    """
    if len(_normalize_pairs(fields)) < 2:
        raise ValueError("验证需要至少两项个人信息（如姓名+身份证号 / 邮箱+手机号）")
    salt = secrets.token_bytes(16)
    token = hashlib.pbkdf2_hmac("sha256", _normalize(fields), salt, _PBKDF2_ITERS)
    return salt.hex(), token.hex()


def _normalize_pairs(fields: Dict[str, str]) -> List[tuple]:
    return [p for p in
            [(str(k).strip().casefold(), str(v).strip().casefold())
             for k, v in fields.items()] if p[0] and p[1]]


def select_by_labels(fields: Dict[str, str], labels: List[str]) -> Dict[str, str]:
    """只保留 ``labels`` 中声明过的字段（键名归一化匹配），其余输入**忽略**。

    这样用户重连时多填了额外信息（例如顺手填了邮箱）也不会导致验证失败；
    少填则留给 :func:`auto_reconnect` 给出「请补充 X」的明确提示。
    """
    wanted = {str(l).strip().casefold() for l in (labels or []) if str(l).strip()}
    out: Dict[str, str] = {}
    for k, v in (fields or {}).items():
        kk = str(k).strip().casefold()
        if kk in wanted and str(v).strip():
            out[kk] = str(v).strip()
    return out


def normalize_fields(fields: Dict[str, str]) -> bytes:
    """对外暴露的规范化入口（供跨设备身份指纹复用），不返回任何原始值。"""
    return _normalize(fields)


def verify(fields: Dict[str, str], salt_hex: str, token_hex: str,
           labels: Optional[List[str]] = None) -> bool:
    """用相同 salt 重派生并与保存的令牌做常量时间比对。返回 True/False。

    传入 ``labels`` 时只取这些字段参与派生，多余输入被忽略。
    """
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(token_hex)
    except (ValueError, TypeError):
        return False
    if len(salt) != 16:
        return False
    if labels:
        fields = select_by_labels(fields, labels)
    trial = hashlib.pbkdf2_hmac("sha256", _normalize(fields), salt, _PBKDF2_ITERS)
    return hmac.compare_digest(trial, expected)


def identity_fingerprint(fields: Dict[str, str], net_id: str,
                         passphrase: str = "") -> str:
    """跨设备**一致**的身份指纹（确定性派生，不含随机 salt，也不落盘原始值）。

    用途：认定「同一个人」。同一人在两台设备上、对同一 ``net_id``、输入相同的
    验证字段与相同的共享口令，即派生出相同的指纹 —— 从而把两台设备归为同一身份，
    允许共享算力（GPU/NPU/TPU/CPU/网络），而**不共享**个人数据与关键资产数据。

    安全性：salt 由 net_id 确定性派生（同网一致），输入含 PBKDF2 单向派生的字段
    与共享口令；不知道原始两项信息与口令者无法伪造出同一指纹，可用于**防止他人
    盗用你的网络互联互通能力**（冒用身份蹭算力/蹭网）。
    """
    if len(_normalize_pairs(fields)) < 2:
        raise ValueError("身份指纹需要至少两项个人信息（如姓名+身份证号 / 邮箱+手机号）")
    net_salt = hashlib.sha256(
        ("sysweeper/netauth/identity/" + str(net_id)).encode("utf-8")).digest()[:16]
    material = _normalize(fields) + b"|" + str(passphrase or "").strip().encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", material, net_salt, _PBKDF2_ITERS).hex()


def same_identity(fp_a: str, fp_b: str) -> bool:
    """常量时间比较两个身份指纹是否一致（认定「同一人登录」）。"""
    try:
        return hmac.compare_digest(str(fp_a), str(fp_b))
    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------- #
# 落盘：只存 salt + 派生令牌 + 字段标签（绝不存原始 PII）                          #
# --------------------------------------------------------------------------- #

def _load_store(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_store(path: str, data: dict) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)            # 原子替换，避免半写


def store(path: str, net_id: str, fields: Dict[str, str],
          labels: Optional[List[str]] = None) -> Tuple[bool, str]:
    """为某网络设置验证：派生令牌并只落盘 salt + 令牌 + 字段标签（不存原始值）。

    返回 (ok, msg)。net_id 为网络维度标识（如 "home_wifi" / "office_lan"）。
    ``labels`` 可显式指定用哪几项做验证（默认取全部非空字段），未列入的字段不参与派生。
    """
    try:
        chosen = select_by_labels(fields, labels) if labels else {
            str(k).strip().casefold(): str(v).strip()
            for k, v in fields.items() if str(k).strip() and str(v).strip()
        }
        if len(chosen) < 2:
            return False, "验证需要至少两项个人信息（如姓名+身份证号 / 邮箱+手机号）"
        salt_hex, token_hex = derive(chosen)
        labels = sorted(chosen.keys())
        data = _load_store(path)
        data[net_id] = {
            "salt": salt_hex,
            "token": token_hex,
            "labels": labels,          # 仅字段标签，不含任何原始值
            "version": 1,
        }
        _save_store(path, data)
        # 显式丢弃原始字段引用，提醒调用方不要再持有
        del fields
        return True, (f"已为网络 {net_id!r} 写入验证（仅 salt+派生令牌+标签"
                      f"{labels}，未保存任何原始个人信息）")
    except Exception as e:  # noqa: BLE001
        return False, f"写入验证失败: {e}"


def load(path: str, net_id: str) -> Optional[Tuple[str, str, List[str]]]:
    """读出某网络的 (salt_hex, token_hex, labels)；不存在返回 None。"""
    data = _load_store(path)
    rec = data.get(net_id)
    if not isinstance(rec, dict) or "salt" not in rec or "token" not in rec:
        return None
    return rec["salt"], rec["token"], list(rec.get("labels", []))


def auto_reconnect(path: str, net_id: str, fields: Dict[str, str]) -> Tuple[bool, str]:
    """下次启动重连：重新输入两项信息，重派生并与保存令牌比对（不保存原始值）。

    返回 (ok, msg)。ok=True 表示信息匹配、可重连。
    """
    rec = load(path, net_id)
    if rec is None:
        return False, f"网络 {net_id!r} 尚无验证记录（请先 setup）"
    salt_hex, token_hex, labels = rec
    picked = select_by_labels(fields, labels) if labels else {
        str(k).strip().casefold(): str(v).strip()
        for k, v in fields.items() if str(k).strip() and str(v).strip()
    }
    if len(picked) < 2:
        return False, "验证需要至少两项个人信息（如姓名+身份证号 / 邮箱+手机号）"
    if labels and len(picked) < len(labels):
        missing = sorted(set(str(l).strip().casefold() for l in labels) - set(picked))
        return False, (f"验证信息不完整：该网络注册了 {len(labels)} 项（{labels}），"
                       f"请补充 {missing}（多填的无关字段会被忽略）")
    ok = verify(picked, salt_hex, token_hex, labels)
    if ok:
        return True, (f"验证通过，已重连网络 {net_id!r}（标签 {labels}；"
                      f"原始信息未被保存，仅本次重输入用于比对）")
    return False, f"验证未通过，未能重连网络 {net_id!r}（请确认输入与首次一致）"


# --------------------------------------------------------------------------- #
# 任务派发无参包装（runner 以 fn() 派发）；非目标环境优雅降级为指引。            #
# --------------------------------------------------------------------------- #

def netauth_report() -> Tuple[bool, str]:
    """报告隐私验证状态（只读，不打印任何原始值）。"""
    try:
        data = _load_store(DEFAULT_PATH)
        if not data:
            return True, ("尚未为任何网络设置隐私验证。setup 时只需输入两项个人信息"
                         f"（如姓名+身份证号 / 邮箱+手机号），工具仅保存 salt+派生令牌"
                         f"+字段标签，绝不保存原始信息；下次重输即可重连。")
        lines = [f"已为 {len(data)} 个网络设置隐私验证（仅存 salt+派生令牌+标签，原始值未保存）："]
        for nid, rec in data.items():
            labels = list((rec or {}).get("labels", []))
            lines.append(f"  · {nid}  标签={labels}")
        return True, "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return False, f"读取验证状态失败: {e}"


def netauth_demo() -> Tuple[bool, str]:
    """无参演示派生/验证往返（**使用明显假数据、不落盘、不保存任何真实 PII**）。

    用于任务派发与离线测试，证明「原始值可立即丢弃、仅凭重输入即可重连」。
    """
    try:
        demo = {"name": "示例用户", "id_number": "110000000000000000"}
        salt_hex, token_hex = derive(demo)
        same = verify(demo, salt_hex, token_hex)
        diff = verify({"name": "示例用户", "id_number": "999"}, salt_hex, token_hex)
        ok = same and not diff
        return ok, ("隐私验证演示（假数据，未落盘）："
                   f"重输入一致→重连={same}，输入不一致→拒绝={not diff}；"
                   "真实使用 store() 只落盘 salt+令牌+标签，原始值不保存。")
    except Exception as e:  # noqa: BLE001
        return False, f"演示失败: {e}"


__all__ = [
    "DEFAULT_PATH", "derive", "verify", "store", "load", "auto_reconnect",
    "normalize_fields", "select_by_labels",
    "identity_fingerprint", "same_identity",
    "netauth_report", "netauth_demo",
]
