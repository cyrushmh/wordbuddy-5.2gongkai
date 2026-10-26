"""TLS 1.3 配置态势审计任务（v0.6.33）：只读审计 + 加固指引，写操作只给官方指引不代执行。

规范锚点: RFC 9846（TLS 1.3, 2026-07，废弃 RFC 8446/5246 等）+ RFC 8996（废止 TLS 1.0/1.1）
          + NIST FIPS 203（ML-KEM，后量子就绪度参照）。
三原则: 适老化/无障碍必须留存（纯文本、人话、屏幕阅读器可朗读）；
        老旧设备/设施仍能用（保留并硬化 TLS 1.2 作兼容桥，只淘汰真死的 SSL/1.0/1.1）；
        红线——全程只读，绝不改注册表、绝不停启协议/套件、绝不实现 TLS 握手。
"""

from __future__ import annotations

from ..models import Action, Task

# 原生只读审计
N = lambda op, desc="": Action("native", op, desc)
# 只给官方工具指引（不代执行）
M = lambda text, desc="": Action("manual", text, desc)

TASKS = [
    Task(
        id="tls13_posture_audit",
        platform="any",
        title="TLS 1.3 配置态势 只读审计",
        category="privacy",
        risk="low",
        actions=[N("tls13.tls13_audit_report",
                   "只读审计（无障碍文本）：各协议分级处置 + 已废止协议是否仍启用 + TLS 1.2 兼容桥状态 "
                   "+ 强制/推荐密码套件 + RFC 9846 的 KEM/后量子就绪度（仅检测能力）")],
        desc="以 RFC 9846（TLS 1.3, 2026-07）为基准，只读核查系统 TLS 配置并分级："
             "淘汰 SSL 2.0/3.0、TLS 1.0/1.1，为老旧设备保留并硬化 TLS 1.2，把 TLS 1.3 作主力。"
             "输出为纯文本，屏幕阅读器可朗读、适老人话。绝不读私钥、绝不改配置。",
        standards=["[国际] RFC 9846（TLS 1.3, 2026-07，废弃 RFC 8446/5246 等）",
                   "[国际] RFC 8996（废止 TLS 1.0/1.1）",
                   "[国际] NIST FIPS 203（ML-KEM，后量子密钥交换参照）",
                   "[官方] Windows Schannel 策略 / Linux crypto-policies / macOS security 偏好"],
        notes=["无障碍：纯文本输出，含『人话简述』，屏幕阅读器可直接朗读，无图形依赖",
               "『KEM 就绪度』仅检测加密栈是否提供 KEM 组，不实现 ML-KEM",
               "老旧设备兼容：不会一刀切要求关停 TLS 1.2，而是保留为兼容桥并提示加固"],
    ),
    Task(
        id="tls13_disable_legacy_guidance",
        platform="any",
        title="禁用真正淘汰的旧 TLS 版本（指引）",
        category="privacy",
        risk="medium",
        actions=[M(
            "仅禁用「已废止且不安全」的：SSL 2.0/3.0、TLS 1.0/1.1（RFC 8996 废止、RFC 9846 禁协商）。"
            "⚠️ 不要一并关掉 TLS 1.2——它常是老旧设备/设施唯一能用的协议。"
            "Windows：组策略/注册表 SCHANNEL\\Protocols 下，对上述已废止协议的 Client/Server 设 "
            "Enabled=0、DisabledByDefault=1（本工具只说步骤，不改注册表）；"
            "Linux：update-crypto-policies 用含 Legacy 最小化的策略（如 FUTURE）；"
            "macOS：defaults / MDM。禁用后回归测试业务与旧设备连通性。",
            "禁用旧 TLS 属中危（可能影响老旧客户端连通），建议先在非生产环境验证、保留 TLS 1.2")],
        desc="按 RFC 8996/9846 淘汰 SSL 2.0/3.0、TLS 1.0/1.1；明确保留 TLS 1.2 以免老旧设备/设施失联。",
        standards=["[国际] RFC 8996（废止 TLS 1.0/1.1）", "[国际] RFC 9846 §1.2"],
        opt_in=True,
        notes=["中危指引，需用户在 GUI 确认后自行执行；本工具不代改任何设置",
               "关键：保留 TLS 1.2 作老旧设备兼容桥，不做一刀切"],
    ),
    Task(
        id="tls13_legacy_device_coexistence_guidance",
        platform="any",
        title="老旧设备/设施 TLS 兼容共存（指引）",
        category="privacy",
        risk="low",
        actions=[M(
            "原则：保两头、稳中间——淘汰 SSL2/3 与 TLS1.0/1.1，保留 TLS 1.2 作兼容桥，主力切 TLS 1.3。"
            "若网内存在只支持 TLS 1.2 的老旧设备（旧 POS/工控机/打印机/摄像头/NAS/早期系统）："
            "① 服务端保留 TLS 1.2；② 按 RFC 9846 附录 D 对 TLS 1.2 的新要求加固（禁用 RC4/3DES/EXPORT、"
            "SHA-1 签名的握手、弱 CBC 套件，优先 AEAD）；③ 对可升级设备逐步推进 TLS 1.3；"
            "④ 对无法升级设备纳入网络隔离或到期替换计划。本工具只给指引。",
            "老旧设备替换需排期；短期以『保留+硬化 TLS 1.2』保障业务连续")],
        desc="为仍依赖 TLS 1.2 的老旧设备/设施提供兼容共存方案：保留并硬化 TLS 1.2、渐进迁移、隔离或替换收尾。",
        standards=["[国际] RFC 9846 附录 D（对 TLS 1.2 实现的新要求）",
                   "[国际] RFC 8996", "[国际] NIST SP 800-52r2（TLS 配置指南）"],
        opt_in=True,
        notes=["低风险指引，纯建议；『保留并硬化』而非一刀切是关键"],
    ),
    Task(
        id="tls13_pqc_readiness_guidance",
        platform="any",
        title="后量子(KEM/ML-KEM)就绪评估（指引）",
        category="privacy",
        risk="low",
        actions=[M(
            "RFC 9846 将密钥交换从『仅 (EC)DHE』泛化为『KEM-based』，可经 key_share 承载"
            "ML-KEM（如 Kyber/混合组）公钥。若需抗量子前瞻：优先选用含 TLS 1.3 + ML-KEM 混合握手"
            "的 TLS 栈（OpenSSL 3.x / BoringSSL 近期构建），服务端启用 KEM NamedGroup，并评估"
            "混合模式（ECDHE+ML-KEM）以兼顾兼容与抗量子；老旧设备若不支持，可经 TLS 1.2 兼容桥过渡。"
            "本工具只评估、只给指引，不替你编译或替换库。",
            "后量子迁移为前瞻项，按资产敏感度排期，不必立即全量切换")],
        desc="基于 RFC 9846 的 KEM 密钥交换能力，给后量子 TLS 就绪度评估与迁移指引（纯建议）。",
        standards=["[国际] RFC 9846 §1.3（KEM-based key exchange）",
                   "[国际] NIST FIPS 203（ML-KEM）"],
        opt_in=True,
        notes=["低风险前瞻指引，纯建议；与老旧设备兼容桥并行不冲突"],
    ),
]
