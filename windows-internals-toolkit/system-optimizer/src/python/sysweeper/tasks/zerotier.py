"""ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断任务（platform="any"，v0.6.17）。

立项：把 ZeroTier（在物理网之上建加密虚拟二层网 VL1）的「该看什么」钉进本工具——
zerotier-one 安装/版本、运行态、identity.public（公钥）、已加入网络（networks.d）、
是否控制器（controller.d）、moon（moons.d）。本任务只读，与 Tor/OSI/DNS 共同构成
网络模块的「虚拟组网层」视图。

注：「zeroist」即 ZeroTier（SD-WAN/零信任组网，2026 定位 Simple SD-WAN and Zero Trust
Access）；GitHub 上同名用户「zeroist」仅为 Java 学习仓库，与本模块无关。

参照（权威资料，仅用于把诊断维度钉死）：
- github.com/zerotier/ZeroTierOne —— ZeroTier 源码（C++；40 位节点地址、identity
  公钥/私钥、networks.d、controller.d、moons.d）
- ZeroTier 官方文档（what/controller/moon）—— 控制器签发网络、moon 为私有根
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

ZEROTIER = ("[上游] ZeroTier（github.com/zerotier/ZeroTierOne；虚拟二层网 VL1，C++；"
            "40 位节点地址 + identity 公钥/私钥、networks.d、controller.d、moons.d）")


TASKS = [
    Task(
        id="zerotier_report",
        platform="any",
        title="ZeroTier 虚拟网络（SD-WAN / 零信任组网）只读诊断",
        category="network",
        risk="low",
        desc="只读核验 ZeroTier 是否安装、版本、运行态、identity.public（公钥）、已加入网络"
             "（networks.d/*.conf，文件名即网络 ID）、是否控制器（controller.d）、moon"
             "（moons.d/*.moon）。与 Tor/OSI/DNS 共同构成网络模块的虚拟组网层视图。",
        actions=[
            N("zerotier.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("zerotier.zerotier_report", "输出 ZeroTier 虚拟网络只读诊断"),
            M("join/leave 网络、起停 zerotier-one、改 networks.d 等写操作由你决定"
              "（本工具不开此路径）", "改 ZeroTier 配置（写操作，opt-in）"),
        ],
        standards=[ZEROTIER],
        notes=[
            "identity.public 是公钥（可对外）；identity.secret 是私钥，本工具只报存在、绝不读。",
            "networks.d/*.conf 文件名即网络 ID，等于「已加入哪些虚拟网」。",
            "controller.d 存在＝本机可托管/签发网络；moons.d 存在＝部署了私有根（moon）。",
            "虚拟网默认端到端加密；信任边界在控制器（谁能进网）与 moon（根在哪）。",
        ],
        caveats=[
            "只读任务：不启动/停止 zerotier-one、不 join/leave 网络、不改 networks.d、不连控制端口。",
            "identity.secret 属私钥，本工具绝不读取，仅 os.path.exists 判定存在性。",
        ],
    ),
]
