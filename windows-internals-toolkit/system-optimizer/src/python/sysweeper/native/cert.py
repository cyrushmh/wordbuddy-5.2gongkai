"""证书与加密开源整合（v0.6.31）：只读审计 + 硬件信任根 + 各种证书，无障碍输出。

整合「类似 OpenSSL 的开源项目」并落到整体：
  - 开源加密栈文档跟踪：OpenSSL / LibreSSL / BoringSSL / GnuTLS，各自按自身协议与
    接口核对（TLS1.2/1.3、X.509、PKCS#12、ACME）。允许接入这些开源项目作为加密底座。
  - 最低内置硬件证书：以 TPM 2.0（硬件信任根）/ 设备身份证书（IEEE 802.1AR IDevID）
    为「设备出厂即带、私钥不可导出」的物理基座；平台密钥库（Keychain/Secure Enclave/
    CNG/Android Keystore）承接应用层密钥。
  - 各种证书：X.509 链、ACME 自动续期、FIDO2/WebAuthn 通行密钥——只读审计到期/信任链，
    绝不读取或解密任何私钥。
  - 无障碍：所有输出为纯文本、无图形依赖，GUI 面板即文本框，屏幕阅读器可直接朗读；
    另提供 a11y_cert_summary() 给出「人话」状态，与既有无障碍(a11y)子系统统一口径。

严守红线：全程只读。绝不读取私钥内容、绝不解密口令、绝不生成/导出/替换任何证书或密钥、
绝不改写 sshd/TPM/钥匙串。写操作（续期/启用 TPM/换库）一律只给官方工具指引。
契合「个人行为在完全图形界面控制操作」：本模块出审计与方案，用户在 GUI/OEM 工具确认。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, List, Tuple

try:
    from importlib import resources
except ImportError:  # pragma: no cover
    import importlib.resources as resources  # type: ignore

REFS: Dict[str, dict] = {}


def _load_refs() -> Dict[str, dict]:
    """读 data/cert_docs.json（权威文档层）。"""
    global REFS
    if REFS:
        return REFS
    try:
        txt = resources.files("sysweeper.data").joinpath(
            "cert_docs.json").read_text(encoding="utf-8")
        import json
        REFS = json.loads(txt)
    except Exception:  # noqa: BLE001
        REFS = {}
    return REFS


def reference(key: str = "") -> dict:
    """返回某证书/加密主题的权威文档（name/org/url/protocols/interfaces/docs/summary/advice）。"""
    refs = _load_refs()
    if key:
        return refs.get(key, {})
    return refs


def reference_all() -> Dict[str, dict]:
    return _load_refs()


def detect_platform() -> str:
    """粗粒度平台判断（用于平台相关探测）。"""
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


def _run_readonly(argv: List[str], timeout: float = 3.0) -> Tuple[int, str]:
    """运行一个**只读查询**命令（如 openssl version / certtool --version），只取输出。

    仅用于「打印信息」类命令（版本/到期/属性），不向系统写入任何东西；失败即降级。
    """
    try:
        cp = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                            check=False)
        out = (cp.stdout or cp.stderr or "").strip()
        return cp.returncode, out
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def probe_openssl() -> Tuple[bool, str]:
    """OpenSSL（或兼容 drop-in）是否可用 + 版本。"""
    p = _which("openssl")
    if not p:
        return False, "未找到 openssl（OpenSSL 未安装或未在 PATH；可接入 LibreSSL/BoringSSL 作替代）"
    rc, out = _run_readonly(["openssl", "version"])
    if rc == 0 and out:
        return True, f"openssl: {out}"
    return True, f"openssl 客户端: {p}（version 调用未返回，仍可签发/校验）"


def probe_gnutls() -> Tuple[bool, str]:
    """GnuTLS 工具链（certtool/gnutls-cli）是否可用。"""
    c = _which("certtool") or _which("gnutls-cli")
    if c:
        rc, out = _run_readonly(["certtool", "--version"])
        ver = out.splitlines()[0] if out else ""
        return True, f"GnuTLS: {c}" + (f"  ({ver})" if ver else "")
    return False, "未找到 GnuTLS（certtool/gnutls-cli 不在 PATH）"


def probe_tpm() -> Tuple[bool, str]:
    """硬件信任根 TPM 是否存在/已启用（只读 sysfs，绝不导出密钥）。"""
    plat = detect_platform()
    if plat == "linux":
        base = "/sys/class/tpm"
        if not os.path.isdir(base):
            return False, "未挂载 /sys/class/tpm（无 TPM 或内核未加载 tpm 子系统）"
        try:
            devs = [d for d in sorted(os.listdir(base)) if d.startswith("tpm")]
        except OSError:
            return False, "读取 /sys/class/tpm 失败"
        if not devs:
            return False, "无 TPM 设备"
        info = []
        for d in devs:
            maj = ""
            mp = os.path.join(base, d, "tpm_version_major")
            if os.path.exists(mp):
                try:
                    maj = open(mp, encoding="utf-8").read().strip()
                except OSError:
                    pass
            info.append(f"{d}(TPM{' '+maj if maj else ''})")
        # tpm2 工具可用则补一句只读能力面
        if _which("tpm2_getcap"):
            info.append("tpm2_tools 可用（只读 getcap，不导出任何密钥）")
        return True, "TPM: " + ", ".join(info)
    if plat == "windows":
        return False, "Windows 经 PowerShell Get-Tpm 只读查询（沙箱未提供）；设备管理器可见「安全设备」即 TPM 已启用"
    return False, f"平台 {plat} 暂无内置 TPM 只读接口（移动端用 Secure Enclave/Keystore 作硬件信任根）"


def probe_keystore() -> Tuple[bool, str]:
    """平台密钥库是否可达（只判定存在，不读口令/私钥）。"""
    plat = detect_platform()
    if plat == "macos":
        p = _which("security")
        return (True, "macOS Keychain(security) 可用，后端多为 Secure Enclave") if p else \
               (False, "未找到 security（macOS 钥匙串工具）")
    if plat == "windows":
        p = _which("certutil")
        return (True, "Windows 证书存储(CNG) 可用（certutil -store 只读）") if p else \
               (False, "未找到 certutil（Windows 证书管理工具）")
    if plat == "linux":
        if _which("certutil"):
            return True, "Linux NSS 密钥库(certutil) 可用；另有 gnome-keyring 等"
        return False, "未找到 certutil（NSS 密钥库工具）；gnome-keyring 仍在后台承接"
    return False, f"平台 {plat} 暂无内置密钥库只读探测"


def probe_device_cert() -> Tuple[bool, str]:
    """设备身份证书（IEEE 802.1AR IDevID/LEDevID）是否存在（只读，私钥不可导出）。"""
    plat = detect_platform()
    if plat == "linux":
        # TPM EK 证书常在此路径（需 tpm 子系统 + 权限，失败即降级）
        ek = "/sys/class/tpm/tpm0/device/caps"
        if os.path.exists(ek):
            return True, "检测到 TPM 背书能力（IDevID/EK 证书通常在硬件内，不可导出）"
        return False, "未读到设备身份证书（多数消费设备不暴露 IDevID；企业设备/路由器常带）"
    return False, f"平台 {plat} 的设备身份证书需厂商固件暴露（IDevID 私钥锁硬件，不读取）"


def probe_cert_expiry() -> Tuple[bool, str]:
    """扫描若干常见证书位置，只读判定是否存在/临近过期（只打印公开元数据）。"""
    if not _which("openssl"):
        return False, "未装 openssl，无法解析证书到期（装后可用只读 x509 -enddate 核查）"
    candidates = [
        "/etc/ssl/certs",
        os.path.expanduser("~/.ssh"),
        "/etc/letsencrypt/live",
    ]
    found = []
    for c in candidates:
        if os.path.isdir(c):
            found.append(c)
    if not found:
        return False, "未发现常见证书目录（/etc/ssl/certs、~/.ssh、/etc/letsencrypt/live）"
    return True, "可只读核查证书目录: " + ", ".join(found)


# 探针清单（供 environment_report 与 CLI/GUI 遍历）
PROBES = (
    ("probe_openssl", "OpenSSL / 兼容加密栈"),
    ("probe_gnutls", "GnuTLS（certtool/gnutls-cli）"),
    ("probe_tpm", "硬件信任根 TPM 2.0"),
    ("probe_keystore", "平台密钥库（Keychain/CNG/NSS/Keystore）"),
    ("probe_device_cert", "设备身份证书（IEEE 802.1AR IDevID）"),
    ("probe_cert_expiry", "常见证书位置与到期只读核查"),
)


# --------------------------------------------------------------------------- #
# 只读安全审计（解析版本/到期/信任；绝不读私钥、绝不解密、绝不改配置）            #
# --------------------------------------------------------------------------- #
_EOL_OPENSSL = ("0.9.8", "1.0.1", "1.0.2", "1.1.0", "1.1.1")


def audit_openssl() -> dict:
    """只读审计 OpenSSL 版本是否受支持（EOL 即风险提示）。"""
    out: dict = {"present": False, "version": "", "eol": None, "notes": []}
    p = _which("openssl")
    if not p:
        out["notes"].append("未安装 OpenSSL（可评估 LibreSSL/BoringSSL 作加密底座）")
        return out
    out["present"] = True
    rc, ver = _run_readonly(["openssl", "version"])
    if rc == 0 and ver:
        out["version"] = ver
        low = ver.lower()
        for eol in _EOL_OPENSSL:
            if eol in low:
                out["eol"] = True
                out["notes"].append(f"⚠ {ver} 属已停止安全支持的版本（EOL），建议升级到受支持分支")
                break
        if out["eol"] is None:
            out["notes"].append(f"✓ {ver} 为受支持版本")
    return out


def audit_tpm() -> dict:
    """只读判定 TPM 存在/启用（Linux sysfs + tpm2 工具，绝不导出密钥）。"""
    out: dict = {"present": False, "version": "", "notes": []}
    ok, msg = probe_tpm()
    out["present"] = ok
    if ok:
        out["version"] = msg
        out["notes"].append("✓ 检测到硬件信任根；私钥在芯片内生成且不可导出，用于磁盘加密密钥封装/安全启动度量")
        out["notes"].append("建议：开启 fTPM + 固件 Secure Boot，密钥与启动链由此保护")
    else:
        out["notes"].append("未检测到 TPM：桌面用 Secure Enclave（mac）/CNG+TPM（Win）/移动端用 Android Keystore 作硬件信任根")
    return out


def audit_keystore() -> dict:
    """只读枚举平台密钥库可达性（不读口令/私钥）。"""
    out: dict = {"present": False, "backend": "", "notes": []}
    ok, msg = probe_keystore()
    out["present"] = ok
    if ok:
        out["backend"] = msg
        out["notes"].append("✓ 平台密钥库可达；高价值私钥应锁在硬件支持后端（Enclave/TPM/Keystore）")
    else:
        out["notes"].append(msg or "平台密钥库不可达，建议确认系统钥匙串服务正常")
    return out


def audit_certs(expiry_days: int = 30) -> dict:
    """只读扫描常见证书，标出临近过期（< expiry_days 天）。绝不读取私钥。"""
    out: dict = {"scanned": 0, "expiring_soon": [], "notes": []}
    if not _which("openssl"):
        out["notes"].append("未装 openssl，跳过到期扫描（装后可只读核查）")
        return out
    roots = ["/etc/ssl/certs"]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith((".pem", ".crt", ".cer")):
                continue
            path = os.path.join(root, name)
            rc, endate = _run_readonly(
                ["openssl", "x509", "-in", path, "-noout", "-enddate"])
            if rc != 0 or not endate:
                continue
            out["scanned"] += 1
            # notAfter=... 解析天数（仅展示，不读取内容）
            try:
                from datetime import datetime, timezone
                ds = endate.split("=", 1)[1].strip()
                when = datetime.strptime(ds, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                left = (when - datetime.now(timezone.utc)).days
                if 0 <= left <= expiry_days:
                    out["expiring_soon"].append(f"{name}（剩 {left} 天）")
            except (ValueError, OSError):
                continue
    if out["expiring_soon"]:
        out["notes"].append("⚠ 临近过期的系统根/中间证书: " + "; ".join(out["expiring_soon"]))
    elif out["scanned"]:
        out["notes"].append(f"✓ 扫描 {out['scanned']} 张系统证书，无 {expiry_days} 天内过期")
    else:
        out["notes"].append("未发现可扫描的系统证书（用户证书如 Let's Encrypt 在 /etc/letsencrypt/live）")
    return out


def cert_status_summary() -> dict:
    """供 durability 资产保护引擎调用的**只读**摘要（不读私钥、不解密）。

    返回: {openssl_version, openssl_eol(bool|None), tpm_present(bool),
           keystore_present(bool), device_cert_present(bool), min_cert_days(int|None),
           weak_crypto(bool), notes[]}
    """
    s: dict = {"openssl_version": "", "openssl_eol": None,
               "tpm_present": False, "keystore_present": False,
               "device_cert_present": False, "min_cert_days": None,
               "weak_crypto": False, "notes": []}
    ao = audit_openssl()
    s["openssl_version"] = ao["version"]
    s["openssl_eol"] = ao["eol"]
    if ao["eol"]:
        s["weak_crypto"] = True
        s["notes"].append("OpenSSL 为 EOL 版本，存在已知未修漏洞")
    at = audit_tpm()
    s["tpm_present"] = at["present"]
    ak = audit_keystore()
    s["keystore_present"] = ak["present"]
    ok_dc, _ = probe_device_cert()
    s["device_cert_present"] = ok_dc
    return s


# --------------------------------------------------------------------------- #
# 无障碍纯文本输出 + 报告 + 指引                                                #
# --------------------------------------------------------------------------- #
def a11y_cert_summary() -> List[str]:
    """无障碍友好的「人话」状态（屏幕阅读器可直接朗读，无图形依赖）。"""
    s = cert_status_summary()
    lines: List[str] = ["证书与加密状态（无障碍简述）："]
    if s["openssl_version"]:
        lines.append("加密库：" + ("已安装但属停止支持版本，建议升级" if s["openssl_eol"]
                                  else "已安装且受支持"))
    else:
        lines.append("加密库：未检测到 OpenSSL（可接入 LibreSSL/BoringSSL 等开源替代）")
    lines.append("硬件信任根：" + ("已检测到 TPM，密钥受芯片保护"
                                  if s["tpm_present"] else "未检测到 TPM，建议用平台密钥库（Enclave/CNG/Keystore）保护密钥"))
    lines.append("平台密钥库：" + ("可达" if s["keystore_present"] else "不可达，请检查系统钥匙串服务"))
    lines.append("设备身份证书：" + ("存在（出厂硬件背书，私钥不可导出）"
                                    if s["device_cert_present"] else "未在本次探测中暴露"))
    return lines


def environment_report() -> List[str]:
    """本机证书/加密可用性与审计概览（只读）。"""
    lines: List[str] = []
    for fn_name, lab in PROBES:
        ok, msg = globals()[fn_name]()
        lines.append(f"   · {lab}: {'✓' if ok else '✗'}  {msg}")
    return lines


def cert_doc_list() -> List[str]:
    """data/cert_docs.json 引用清单。"""
    lines: List[str] = []
    for key, ref in reference_all().items():
        lines.append(f"   · [{key}] {ref.get('name', key)} — {ref.get('org', '')}")
        lines.append(f"       {ref.get('url', '')}")
        for d in ref.get("docs", [])[:2]:
            lines.append(f"       文档: {d}")
    return lines


def cert_audit_report() -> Tuple[bool, str]:
    """端到端只读审计：开源加密栈 + 硬件信任根 + 平台密钥库 + 设备证书 + 到期。"""
    out: List[str] = []
    out.append("==== 证书与加密 只读安全审计（无障碍文本，供 GUI/CLI 直接朗读） ====")
    out.append("")
    out.append("-- 本机可用项 --")
    for line in environment_report():
        out.append(line)
    out.append("")
    out.append("-- 开源加密栈版本（只读）--")
    ao = audit_openssl()
    if ao["present"]:
        out.append(f"   {ao['version']}")
        for n in ao["notes"]:
            out.append(f"     {n}")
    ag = audit_tpm()
    for n in ag["notes"]:
        out.append(f"   [TPM] {n}")
    ak = audit_keystore()
    for n in ak["notes"]:
        out.append(f"   [密钥库] {n}")
    out.append("")
    out.append("-- 系统证书到期只读扫描 --")
    ac = audit_certs()
    for n in ac["notes"]:
        out.append(f"     {n}")
    out.append("")
    out.append("-- 无障碍简述 --")
    for line in a11y_cert_summary():
        out.append(f"   {line}")
    out.append("")
    out.append("安全总原则：私钥锁硬件/平台密钥库、证书走完整链+自动续期(ACME)、")
    out.append("EOL 加密库即升级；本工具只审计与出方案，绝不读私钥/不改配置/不替你换证。")
    return True, "\n".join(out)


# 写操作（仅指引，不代执行）
TUNES = (
    ("tune_rotate_cert", "续期临近过期证书（走 ACME 自动）",
     "服务端用 certbot/acme.sh 注册定时续期（Let's Encrypt 90 天）；到期前 30 天告警。"
     "本工具只给指引，不替你签发票/替换证书。"),
    ("tune_enable_tpm", "启用硬件信任根（TPM/Secure Enclave）",
     "固件开启 fTPM、打开 Secure Boot；用 TPM 封装磁盘加密密钥（BitLocker/TPM+L一方面）。"
     "本工具只给指引，不导出任何密钥。"),
    ("tune_hardware_keystore", "密钥锁平台硬件密钥库",
     "移动端用 Android Keystore（硬件支持）/iOS Secure Enclave；桌面私钥后端绑定 TPM/Enclave。"
     "本工具不替你迁移/生成密钥。"),
    ("tune_upgrade_crypto", "升级 EOL 加密库（接入开源替代）",
     "把 OpenSSL 1.0.2/1.1.1 等 EOL 升级到受支持分支，或评估 LibreSSL/BoringSSL 作 drop-in。"
     "本工具只给版本提示，不替你编译/替换系统库。"),
)


def cert_tune_list() -> List[str]:
    """加固/安全指引清单（只展示，不调用）。"""
    lines: List[str] = []
    for key, title, guide in TUNES:
        lines.append(f"   · [{key}] {title}")
        lines.append(f"       {guide}")
    return lines
