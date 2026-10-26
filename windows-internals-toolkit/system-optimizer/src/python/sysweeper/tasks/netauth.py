"""按网络维度的隐私验证任务定义（v0.6.66；原 network.py 拆分）。

按 omni 子系统「按 key 归位」原则，本文件 ↔ `netauth` 子系统；原
`network.py` 中的 net_auth_setup 迁到此处（id 不变——`sysweaver netlink
auth` 命令按 id 列举，cli.py 不关心任务定义在哪个文件）。

核心底线：**原始个人信息绝不落盘**——只存随机 salt + PBKDF2 派生令牌
+ 字段标签；不同网络用不同 salt，防跨网关联；重连靠重新输入同样信息
重派生 + 常量时间比对。跨设备认定同一人用 identity_fingerprint
确定性派生（需原始信息 + 共享口令双因子）。

对应 native 层：`native/netauth.py`（netauth_demo / netauth_report /
derive / verify / identity_fingerprint / same_identity / store / load /
auto_reconnect）。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)
S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)


TASKS = [
    # ------------------------------------------------------------------ #
    # 按网络维度的隐私验证（原始值不落盘，只存 salt+令牌+标签）             #
    # ------------------------------------------------------------------ #
    Task(
        id="net_auth_setup",
        platform="any",
        title="按网络维度的隐私验证（两项以上个人信息）",
        category="network",
        risk="low",
        opt_in=True,
        standards=["[国标] GB/T 35273 个人信息安全规范（数据最小化、去标识化）",
                   "[国际] IETF RFC 8018（PBKDF2 口令派生）"],
        desc="不同网络用「个人输入的两个以上信息」作验证（如姓名+身份证号，或邮箱+手机号）；"
             "**原始信息不作保存**，只存随机 salt + PBKDF2 派生令牌 + 字段标签；"
             "下次启动重新输入同样信息即可重新连接。",
        actions=[N("netauth.netauth_demo", "演示派生/验证往返（假数据，不落盘）"),
                 N("netauth.netauth_report", "查看已设置验证的网络（只列标签，不含原始值）")],
        notes=[
            "派生：token = PBKDF2-HMAC-SHA256(salt, 归一化字段)；不同网络用不同 salt，"
            "同名同 ID 在两个网络派生结果不同（防跨网关联）。",
            "落盘只含 salt + 令牌 + 字段标签，原始姓名/证件号/邮箱/手机号一律不落盘。",
            "重连：重新输入同样两项信息，重派生后常量时间比对，一致即重连。",
            "跨设备认定同一人：identity_fingerprint(字段, 网络, 共享口令) 确定性派生，"
            "不知道原始信息与口令者无法伪造。",
        ],
        caveats=["验证信息一经设定不可找回（因为未保存原始值），忘记需重新设置。"],
    ),
    Task(
        id="net_auth_fingerprint",
        platform="any",
        title="跨设备同一人认定：身份指纹原理与用法（指引）",
        category="network",
        risk="low",
        opt_in=True,
        standards=["[国标] GB/T 35273 个人信息安全规范（去标识化、防关联）",
                   "[国际] IETF RFC 8018（PBKDF2 口令派生密钥）",
                   "[国际] IETF RFC 9106（Argon2 等现代 KDF 的选型参考）"],
        desc="讲清 identity_fingerprint 如何确定性派生「同一人」凭证："
             "同样的字段 + 同样网络 + 共享口令 → 同一指纹；缺任何一项都推不出，"
             "从而在不交换原始个人信息的前提下跨设备认定同一人。",
        actions=[M("原理（native 层 identity_fingerprint / same_identity，本任务只讲不跑）：\n"
                   "  fingerprint = PBKDF2-HMAC-SHA256(\n"
                   "      password = 共享口令,\n"
                   "      salt     = net_id（网络标识，保证各网络指纹互不关联）,\n"
                   "      dkLen    = 32 字节 → 十六进制编码\n"
                   "  )\n"
                   "  输入 = 归一化后的字段串（如 name|id 排序拼接后 UTF-8 编码）。\n"
                   "用法：两台设备各自离线计算指纹，只交换指纹值；\n"
                   "  same_identity(fp_a, fp_b) 用恒定时间比较，一致即认定同一人。\n"
                   "安全性质：\n"
                   "  ① 不交换原始个人信息——指纹不可逆推回姓名/证件号；\n"
                   "  ② 双因子——同时知道原始字段与共享口令才能算出指纹；\n"
                   "  ③ 抗枚举——PBKDF2 的迭代次数让暴力猜口令的成本随硬件线性上升；\n"
                   "  ④ 防关联——salt 绑定 net_id，同一人在两个网络的指纹不同。\n"
                   "落地位置：同人资源共享（reshare）授权前先比对指纹；\n"
                   "  他人指纹一律拒绝并记审计，只落盘指纹与授权种类，绝不落盘个人信息。",
                  "跨设备身份指纹：原理、用法与安全性质（只给指引，不代跑）")],
        notes=[
            "这是指引任务：把「怎么在不泄露个人信息的前提下认定同一人」讲透，"
            "而不是替用户按下按钮——native 层的 identity_fingerprint 是带参函数，"
            "由 reshare/netlink 流程在运行时按用户输入调用。",
            "指纹交换只走本地网段 mesh 通道（info/probe 白名单），不外传。",
        ],
        caveats=["共享口令是第一道门：强度不足会把双因子退化成一因子；"
                 "建议口令熵 ≥ 60 bit（如四个无关词 Diceware）。"],
    ),
]
