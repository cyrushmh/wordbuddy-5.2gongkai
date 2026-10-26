"""远程接入与传输客户端任务（platform=any，跨平台）。

全部只读审计 + 手动/官方工具指引；任何「改 sshd_config / 停 telnetd / 改 FileZilla
站点 / 改 PuTTY 注册表」的写操作一律只给官方指引，不代执行——严守只读红线，也契合
用户「个人行为在完全图形界面控制操作」：本模块出方案，用户在 GUI/OEM 工具里点官方工具做。

文档跟踪与接口全部按各客户端**自身协议与接口**核对（SSH=RFC 425x 加密通道；
Telnet=RFC 854 明文；FileZilla=FTP/RFC959 明文 vs SFTP vs FTPS/RFC4217；PuTTY=Windows SSH）。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="remote_clients_audit",
        platform="any",
        title="远程接入与传输客户端 只读安全审计",
        category="maintenance",
        risk="low",
        desc="跨平台只读审计 ssh/telnet/filezilla/putty 可用性与安全配置，标出明文风险项（不读解密口令、不改配置）。",
        actions=[
            N("remote.remote_audit_report", "端到端只读审计（客户端清单 + ssh 安全 + telnet 风险 + filezilla 安全）"),
        ],
        notes=["telnet 明文、明文 FTP、口令登录均会被标出；本机无相关客户端即降级为文档指引。"],
        standards=["[国际] RFC 4251/4252/4253/4254（SSH-2）",
                  "[国际] RFC 854（Telnet 明文）",
                  "[国际] RFC 959（FTP 明文）/ RFC 4217（FTPS）"],
    ),
    Task(
        id="remote_ssh_harden",
        platform="any",
        title="SSH 服务端加固（指引）",
        category="optimize",
        risk="medium",
        desc="建议 sshd 禁用口令登录改公钥、限制 root 直登、仅留 SSH-2，降低凭据与暴力风险。",
        actions=[
            M("编辑 /etc/ssh/sshd_config：PasswordAuthentication no、PubkeyAuthentication yes、"
              "PermitRootLogin prohibit-password；ssh-keygen -t ed25519 生成密钥；"
              "sshd -t 校验后 systemctl reload sshd。",
              "SSH 加固（OEM/官方配置，不代执行）"),
            N("remote.read_ssh_security", "只读读取 sshd_config 关键项（不改、不给写命令）"),
        ],
        notes=["改配置前先确保有另一可用登录方式（控制台/现有密钥），避免锁死自己。"],
        caveats=["sshd_config 是服务端关键文件，本工具只给指引；是否改、何时改由你确认并自行备份。"],
        standards=["[官方] sshd_config(5) / ssh_config(5) man",
                  "[国际] RFC 4252（publickey 认证优先）",
                  "[官方] NIST SP 800-63B（密钥/口令认证强度）"],
    ),
    Task(
        id="remote_telnet_disable",
        platform="any",
        title="停用 telnet 明文（指引）",
        category="maintenance",
        risk="low",
        desc="telnet 全程明文，口令与数据可被嗅探；建议停用 telnetd 并改用 SSH。",
        actions=[
            M("确认 telnetd 未监听 23 端口；如启用，停用并改 SSH（systemctl disable --now … 或注释 inetd.conf）。",
              "停用 telnet（OEM/官方，不代执行）"),
            N("remote.audit_telnet_risk", "只读判定 telnet 客户端可用 + 23 端口监听状态"),
        ],
        notes=["仅本地串行控制台/老网管设备调试才用 telnet 客户端，勿上不可信网。"],
        standards=["[国际] RFC 854（Telnet 明文 NVT）"],
    ),
    Task(
        id="remote_filezilla_secure",
        platform="any",
        title="FileZilla 站点安全（指引）",
        category="privacy",
        risk="low",
        desc="避免明文 FTP、给站点口令设主密码二次加密，降低凭据泄露风险。",
        actions=[
            M("FileZilla 站点协议选 SFTP（端口 22）；设置 → 主密码，给 sitemanager.xml 口令二次加密；"
              "不在不可信网用明文 FTP。",
              "FileZilla 安全（用户操作，不替你改站点、不读口令）"),
            N("remote.read_filezilla_security", "只读判定明文 FTP / 主密码标记（不读解密任何口令）"),
        ],
        notes=["本工具只读 sitemanager.xml 的协议取值与主密码提示，绝不读取或解密任何口令。"],
        standards=["[国际] RFC 959（FTP 明文）/ RFC 4217（FTPS）",
                  "[官方] FileZilla 文档（主密码加密）"],
    ),
    Task(
        id="remote_putty_secure",
        platform="windows",
        title="PuTTY 安全（指引，Windows）",
        category="privacy",
        risk="low",
        desc="PuTTY 默认 SSH + ED25519 公钥，避免用其 Telnet 模式上不可信网。",
        actions=[
            M("连接类型选 SSH；puttygen 生成 ED25519 并设私钥口令；pageant 持有代理而非反复输口令。",
              "PuTTY 安全（用户操作，不替你改注册表会话）"),
            N("remote.probe_putty", "只读判定 PuTTY 是否安装（不读注册表口令）"),
        ],
        notes=["PuTTY 的 Telnet 模式仅本地串行调试用；私钥放 pageant 而非明文落盘口令。"],
        standards=["[官方] PuTTY 文档（密钥/代理）"],
    ),
    Task(
        id="remote_keepalive_guidance",
        platform="any",
        title="连接保活与重连（只读观测 + 指引）",
        category="maintenance",
        risk="low",
        desc="只读检查 SSH 客户端 ServerAliveInterval 保活心跳，给 TCP keepalive / autossh / VPN 自动重连的"
             "通用指引（D10 借鉴自 docker-easyconnect 自动保活实践）；绝不改连接配置、绝不注入重连进程。",
        actions=[
            M("长连接设 SSH ServerAliveInterval 30 / ServerAliveCountMax 3 保活；常驻隧道用 autossh 自动重连；"
              "VPN 设连接保活与自动重拨，避免隧道静默掉线。",
              "连接保活与重连（规范指引，不代执行）"),
            N("remote.assess_keepalive", "只读观测 SSH 保活配置并给重连指引（不注入重连进程）"),
        ],
        notes=["对外服务暴露面遵循「默认拒绝入站、端口只绑 localhost」的基线（见安全基线）"
               "——保活只管本端连接韧性，不扩大对外暴露面。"],
        standards=["[国际] RFC 4254（SSH 连接保活/通道）",
                  "[国际] RFC 1122（TCP keepalive）"],
    ),
]
