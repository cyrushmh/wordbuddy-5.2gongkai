"""证书与加密任务（v0.6.31）：只读审计 + 加固指引，写操作只给官方指引不代执行。

平台: any（跨系统统一文档跟踪与只读审计；加固指引指向各 OS 官方工具）。
红线: 绝不读私钥/绝不解密/绝不改 sshd/TPM/钥匙串；是否执行始终由用户在 GUI 确认。
"""

from __future__ import annotations

from ..models import Action, Task

# 原生只读审计函数的动作构造
N = lambda op, desc="": Action("native", op, desc)
# 只给官方工具指引（不代执行）
M = lambda text, desc="": Action("manual", text, desc)

TASKS = [
    Task(
        id="cert_audit",
        platform="any",
        title="证书与加密 只读安全审计",
        category="privacy",
        risk="low",
        actions=[N("cert.cert_audit_report",
                   "端到端只读审计：开源加密栈版本 + 硬件信任根(TPM) + 平台密钥库 + 设备证书 + 到期扫描")],
        desc="整合 OpenSSL/LibreSSL/BoringSSL/GnuTLS 等开源加密栈与硬件信任根，做只读审计；"
             "标出 EOL 加密库、未启用 TPM、临近过期证书等风险。绝不读私钥、绝不解密、绝不改配置。",
        standards=["[国际] RFC 5280（X.509 证书）", "[国际] RFC 8555（ACME 自动续期）",
                   "[国际] TPM 2.0（硬件信任根）", "[官方] OpenSSL/LibreSSL/GnuTLS 文档"],
        notes=["审计结果含无障碍纯文本(a11y_cert_summary)，屏幕阅读器可直接朗读"],
    ),
    Task(
        id="cert_openssl_guidance",
        platform="any",
        title="升级 EOL 开源加密库（指引）",
        category="privacy",
        risk="medium",
        actions=[M(
            "检查 OpenSSL 版本：openssl version；若为 1.0.2/1.1.1 等已停止安全支持(EOL)分支，"
            "升级到受支持版本（3.x），或评估 LibreSSL/BoringSSL 作 drop-in 替代。证书/密钥管理"
            "仍走 OpenSSL 兼容接口。本工具只给指引，不替你编译或替换系统库。",
            "升级加密库属中危（影响全局 TLS），建议先备份再升级、升级后回归测试")],
        desc="OpenSSL 1.0.2/1.1.0/1.1.1 等已 EOL，存在未修漏洞；提示升级到受支持分支或接入开源替代。",
        standards=["[官方] OpenSSL 版本支持周期", "[官方] LibreSSL/BoringSSL 文档"],
        opt_in=True,
        notes=["中危指引，需用户在 GUI 确认后自行执行"],
    ),
    Task(
        id="cert_tpm_guidance",
        platform="any",
        title="启用硬件信任根（TPM/Secure Enclave，指引）",
        category="hardware",
        risk="medium",
        actions=[M(
            "固件开启 fTPM（或插 dTPM），打开 Secure Boot；用 TPM 封装磁盘加密密钥"
            "（Windows BitLocker / Linux Clevis+TPM），移动端用 Android Keystore / iOS Secure Enclave。"
            "本工具只给指引，不导出任何密钥、不替你改固件。",
            "硬件信任根保护密钥与启动链，是「最低内置硬件证书」的物理基座")],
        desc="以 TPM 2.0 / 设备身份证书(802.1AR IDevID) 为硬件信任根，把高价值私钥锁在芯片/Enclave 内。",
        standards=["[国际] TPM 2.0（TCG）", "[国际] IEEE 802.1AR（IDevID 设备身份证书）",
                   "[官方] 各 OS 密钥库文档"],
        opt_in=True,
        notes=["中危指引，涉及固件/加密设置，需用户确认"],
    ),
    Task(
        id="cert_keystore_guidance",
        platform="any",
        title="密钥锁平台硬件密钥库（指引）",
        category="privacy",
        risk="low",
        actions=[M(
            "移动端优先用 Android Keystore（硬件支持）/iOS Secure Enclave；桌面私钥后端绑定 "
            "TPM/Secure Enclave；应用层凭据不裸存明文。本工具不替你迁移或生成密钥。",
            "平台密钥库让私钥不可被导出，降低口令裸存与泄露风险")],
        desc="引导高价值私钥进入平台硬件支持密钥库（Keychain/Secure Enclave/CNG/Android Keystore）。",
        standards=["[官方] Apple Keychain/Secure Enclave", "[官方] Windows CNG/证书存储",
                   "[官方] Android Keystore", "[官方] Linux NSS/gnome-keyring"],
        notes=["低风险指引，纯建议"],
    ),
    Task(
        id="cert_expiry_alert",
        platform="any",
        title="证书到期只读预警",
        category="privacy",
        risk="low",
        actions=[N("cert.audit_certs",
                   "只读扫描系统证书与 Let's Encrypt 等位置，标出 30 天内过期项（绝不读私钥）")],
        desc="只读核查常见证书位置到期日，临近过期给出续期提醒（优先 ACME 自动续期），避免通信中断。",
        standards=["[国际] RFC 5280（X.509 有效期）", "[国际] RFC 8555（ACME 自动续期）"],
        notes=["只读预警；续期由用户/ACME 客户端执行"],
    ),
]
