"""TLS 1.3 配置态势只读审计（v0.6.33）：只读，绝不改注册表/配置。

参照 RFC 9846（TLS 1.3, 2026-07）与 RFC 8996（废止 TLS 1.0/1.1），并贯彻三条硬原则：

  1) 适老化 / 无障碍必须留存：所有对外输出为纯文本，屏幕阅读器可直接朗读；
     提供 a11y_tls13_summary() 给出「人话」状态，与既有无障碍(a11y)子系统统一口径。
     不使用只读缩写、不用纯图标，风险分级用「必须处理/建议处理/由你决定」等人话表达。

  2) 老旧设备/设施仍能用：协议处置分级——
       · retire（淘汰，必须禁）：SSL 2.0/3.0、TLS 1.0/1.1（已废止/已破）
       · bridge_keep（保留，兼容桥）：TLS 1.2 —— 网内老旧设备/设施常只支持到 TLS 1.2，
         保留但按 RFC 9846 附录 D 对 TLS 1.2 的新要求加固（不粗暴全关）
       · primary（现代主力）：TLS 1.3 —— 含 KEM/后量子就绪度（仅检测能力，不实现 ML-KEM）
     一刀切「全关 TLS1.2」会让老旧设备连不上，故单列为兼容桥。

  3) 红线：全程只读。绝不修改 Schannel 注册表、绝不启停任何协议/套件、
     绝不实现 TLS 握手或任何加解密。写操作一律只给官方指引（见 tasks/tls13.py）。
"""

from __future__ import annotations

import platform
from typing import Dict, List

from ..data import rfc9846_spec as SPEC

# 协议处置分级（适老化 + 老旧设备兼容的核心表）
PROTOCOL_TIERS: Dict[str, Dict] = {
    "SSL 2.0":  {"tier": "retire",      "why": "既废弃又不安全，必须禁用"},
    "SSL 3.0":  {"tier": "retire",      "why": "存在 POODLE 等已公开攻击，必须禁用"},
    "TLS 1.0":  {"tier": "retire",      "why": "已被 RFC 8996 废止，必须禁用"},
    "TLS 1.1":  {"tier": "retire",      "why": "已被 RFC 8996 废止，RFC 9846 禁止协商"},
    "TLS 1.2":  {"tier": "bridge_keep", "why": "为老旧设备/设施保留作兼容桥，须按 RFC 9846 附录 D 对 TLS 1.2 的新要求加固"},
    "TLS 1.3":  {"tier": "primary",     "why": "现代主力协议，支持 KEM/后量子密钥交换"},
}
_PROTO_ORDER = ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1", "TLS 1.2", "TLS 1.3"]

# Windows Schannel 协议开关注册表路径
_SCHANNEL = r"SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols"


def _read_windows_schannel() -> Dict[str, Dict[str, str]]:
    """只读读取 Schannel 各协议 Client/Server 的 Enabled/DisabledByDefault。"""
    out: Dict[str, Dict[str, str]] = {}
    try:
        import winreg  # type: ignore
    except ImportError:
        return out
    for proto in _PROTO_ORDER:
        sub: Dict[str, str] = {}
        for role in ("Client", "Server"):
            key_path = f"{_SCHANNEL}\\{proto}\\{role}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path,
                                    access=winreg.KEY_READ) as k:
                    for val in ("Enabled", "DisabledByDefault"):
                        try:
                            sub[f"{role}.{val}"], _ = winreg.QueryValueEx(k, val)
                        except OSError:
                            sub.setdefault(f"{role}.{val}", "default")
            except OSError:
                # 未显式配置：沿用系统默认
                sub.setdefault(f"{role}.Enabled", "default")
                sub.setdefault(f"{role}.DisabledByDefault", "default")
        out[proto] = sub
    return out


def _protocol_state(sub: Dict[str, str]) -> str:
    """合并 Client/Server 读数为 'enabled'/'disabled'/'default'。"""
    states = set()
    for role in ("Client", "Server"):
        en = sub.get(f"{role}.Enabled", "default")
        dd = sub.get(f"{role}.DisabledByDefault", "default")
        if en == 1 and dd != 1:
            states.add("enabled")
        elif en == 0 or dd == 1:
            states.add("disabled")
        else:
            states.add("default")
    # 任一端显式启用即视为启用（安全从严），否则任一端禁用则禁用，再否则 default
    if "enabled" in states and "disabled" not in states:
        return "enabled"
    if "disabled" in states and "enabled" not in states:
        return "disabled"
    if states == {"default"}:
        return "default"
    return "mixed"


def tls13_posture_report() -> Dict:
    """只读态势审计主入口；返回结构化报告（不修改任何状态）。"""
    os_name = platform.system()
    schannel = _read_windows_schannel() if os_name == "Windows" else {}

    per_protocol: Dict[str, Dict] = {}
    retire_still_enabled: List[str] = []
    bridge_enabled = None  # TLS 1.2 是否启用（兼容桥是否搭着）
    for proto in _PROTO_ORDER:
        meta = PROTOCOL_TIERS[proto]
        sub = schannel.get(proto, {})
        state = _protocol_state(sub) if sub else "unknown"
        per_protocol[proto] = {"tier": meta["tier"], "state": state, "why": meta["why"]}
        if meta["tier"] == "retire" and state == "enabled":
            retire_still_enabled.append(proto)
        if proto == "TLS 1.2":
            bridge_enabled = (state if state in ("enabled", "disabled") else None)

    if not schannel:
        platform_note = (
            "非 Windows：本工具不读 Schannel，无法判定协议实际开关。请改查本平台——"
            "Linux 看 /etc/crypto-policies/、update-crypto-policies；macOS 看 "
            "/Library/Preferences/com.apple.security.* 与 defaults；并核验加密栈(OpenSSL 等) "
            "是否含 TLS_AES_128_GCM_SHA256。本工具给出通用判定与建议，不臆断本机开关。"
        )
    else:
        platform_note = "Windows：已只读读取 Schannel 协议开关（Enabled/DisabledByDefault）。"

    # 老旧设备/设施兼容提示
    if bridge_enabled == "disabled":
        legacy_device_note = (
            "未检测到 TLS 1.2 启用：若网内仍有只支持 TLS 1.2 的老旧设备/设施（如旧 POS、"
            "工控机、老旧打印机/摄像头、早期系统），它们可能连不上。建议保留 TLS 1.2 作兼容桥，"
            "并按 RFC 9846 附录 D 对 TLS 1.2 的新要求加固（而非一刀切全关）。"
        )
    elif bridge_enabled == "enabled":
        legacy_device_note = "TLS 1.2 已启用，可作老旧设备/设施的兼容桥（同时按 RFC 9846 附录 D 加固）。"
    else:
        legacy_device_note = "TLS 1.2 状态未能判定（非 Windows/未显式配置）；如需老旧设备兼容，建议显式保留 TLS 1.2 并加固。"

    verdict = "PASS：已废止协议(SSL2/3、TLS1.0/1.1)均未显式启用"
    if retire_still_enabled:
        verdict = f"MUST-FIX：仍启用已废止协议 {retire_still_enabled}（应禁用以满足 RFC 8996/RFC 9846）"
    elif bridge_enabled == "disabled":
        verdict = "REVIEW：旧协议已禁，但 TLS 1.2 未启用——留意老旧设备/设施兼容性"

    return {
        "spec": SPEC.SPEC_SOURCE,
        "obsoletes": SPEC.SPEC_OBSOLETES,
        "a11y_ok": True,
        "output_format": "plain-text",
        "os": os_name,
        "legacy_record_version_must_be": hex(SPEC.TLS_LEGACY_RECORD_VERSION),
        "tls_1_3_wire": hex(SPEC.TLS_1_3_WIRE),
        "per_protocol": per_protocol,
        "compatibility": {
            "retire_must_disable": ["SSL 2.0", "SSL 3.0", "TLS 1.0", "TLS 1.1"],
            "bridge_keep_for_legacy": "TLS 1.2",
            "primary": "TLS 1.3",
            "tls12_state": bridge_enabled,
        },
        "legacy_device_note": legacy_device_note,
        "retire_still_enabled": retire_still_enabled,
        "deprecated_protocols": SPEC.DEPRECATED_PROTOCOLS,
        "mandatory_cipher_suite": SPEC.CIPHER_SUITES[SPEC.MANDATORY_CIPHER_SUITE]["name"],
        "recommended_cipher_suites": [
            SPEC.CIPHER_SUITES[c]["name"] for c in (0x1302, 0x1303)
        ],
        "kem_key_exchange": ("RFC 9846 引入 KEM-based 密钥交换（经 NamedGroup/key_share 承载）；"
                             "检测栈是否提供 KEM 组以判定 PQC-ready"),
        "kem_named_group_hints": list(SPEC.KEM_NAMED_GROUP_HINTS),
        "schannel_raw": schannel,
        "platform_note": platform_note,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# 无障碍纯文本输出（适老化 / 屏幕阅读器可朗读 / 无图形依赖）
# ---------------------------------------------------------------------------
def a11y_tls13_summary(rep: Dict | None = None) -> List[str]:
    """无障碍友好的「人话」状态（屏幕阅读器可直接朗读，无图形依赖，适老表达）。"""
    if rep is None:
        rep = tls13_posture_report()
    lines: List[str] = ["网络加密（TLS）状态（无障碍·人话简述）："]

    retire = rep.get("retire_still_enabled", [])
    if retire:
        lines.append("需要处理：发现还在用不安全的旧版加密协议——" + "、".join(retire)
                     + "。建议关掉它们（本工具只告诉你，不替你改）。")
    else:
        lines.append("放心：没有发现仍在用的过期加密协议，这一步没问题。")

    tls12 = rep.get("compatibility", {}).get("tls12_state")
    if tls12 == "disabled":
        lines.append("由你决定：未启用 TLS 1.2。若家里/单位还有老打印机、旧收银机、老摄像头等旧设备，"
                     "可能会连不上。建议保留 TLS 1.2（同时加固），而不是直接关掉。")
    elif tls12 == "enabled":
        lines.append("良好：TLS 1.2 已启用，可作为旧设备的兼容桥。")
    else:
        lines.append("待确认：TLS 1.2 开关没能自动判断。如有旧设备，建议手动确认并保留 TLS 1.2。")

    lines.append("现代协议：TLS 1.3 是当前主力，更强更快。")
    lines.append("在用的标准：" + rep.get("spec", "RFC 9846") + "。")
    lines.append("说明：以上为只读体检结果。要不要禁用旧协议、是否保留旧版给老设备，都由你决定；"
                 "本工具不给图形、只给文字，屏幕阅读器可直接朗读。")
    return lines


def tls13_audit_report() -> "tuple[bool, str]":
    """TLS 1.3 只读态势审计（无障碍文本，供 GUI/CLI 直接朗读）。返回 (ok, text)。"""
    rep = tls13_posture_report()
    out: List[str] = []
    out.append("==== TLS 1.3 配置态势 只读审计（无障碍文本）====")
    out.append("")
    out.append("-- 裁决 --")
    out.append("   " + rep["verdict"])
    out.append("")
    out.append("-- 协议处置分级（老旧设备/设施兼容）--")
    out.append("   淘汰(必须禁)：" + "、".join(rep["compatibility"]["retire_must_disable"]))
    out.append("   兼容桥(保留)：" + rep["compatibility"]["bridge_keep_for_legacy"]
               + "  （老旧设备常只支持到它；须按 RFC 9846 附录 D 加固）")
    out.append("   现代主力：" + rep["compatibility"]["primary"])
    out.append("")
    out.append("-- 各协议实际状态" + ("（本机 Schannel 只读）" if rep["os"] == "Windows" else "（本机不可读，需手动核）") + "--")
    for proto in _PROTO_ORDER:
        p = rep["per_protocol"][proto]
        st = {"enabled": "启用", "disabled": "已禁", "default": "默认",
              "mixed": "混合配置", "unknown": "未判定"}.get(p["state"], p["state"])
        out.append(f"   · [{p['tier']}] {proto}: {st} —— {p['why']}")
    out.append("")
    out.append("-- 老旧设备/设施兼容 --")
    out.append("   " + rep["legacy_device_note"])
    out.append("")
    out.append("-- 规范要点（保留规范代码，仅参照）--")
    out.append(f"   legacy_version 必须固定 {rep['legacy_record_version_must_be']}；"
               f"真实版本走 supported_versions（TLS 1.3 = {rep['tls_1_3_wire']}）")
    out.append(f"   强制密码套件：{rep['mandatory_cipher_suite']}；推荐："
               + "、".join(rep["recommended_cipher_suites"]))
    out.append("   " + rep["kem_key_exchange"])
    out.append("")
    out.append("-- 平台提示 --")
    out.append("   " + rep["platform_note"])
    out.append("")
    out.append("-- 无障碍简述 --")
    for line in a11y_tls13_summary(rep):
        out.append("   " + line)
    out.append("")
    out.append("安全总原则：只淘汰真正该淘汰的旧协议（SSL2/3、TLS1.0/1.1），为老旧设备保留并加固 "
               "TLS 1.2，把 TLS 1.3（含 KEM）作主力；本工具只审计与出方案，绝不改配置/不实现握手。")
    return True, "\n".join(out)


def reference_summary() -> Dict:
    """返回规范要点摘要（给 GUI/a11y 文本用）。"""
    return SPEC.summary()
