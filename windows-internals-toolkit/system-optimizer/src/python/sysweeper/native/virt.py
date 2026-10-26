"""虚拟机环境只读诊断（virt）：识别本工具自身运行在哪一层虚拟化，并给出「在不同虚拟机内优雅降级」的应对。

覆盖：裸金属（bare-metal）/ KVM / QEMU / VMware / VirtualBox / Hyper-V / Xen / WSL / 容器 /
未识别（unknown）。所有探测只读，绝不加载内核模块、绝不改 QEMU/crosvm 配置、绝不装增强工具。

设计目标（对齐用户「导入虚拟机，让整体在不同虚拟机都能正常运行」）：
- 先看清「自己站在哪一层」——这决定本工具各只读探针能用多少、退化多少；
- 再把退化清单回链到各子系统：裸金属全开，受限 VM / 容器退化为概念观测（只给指引不读敏感信号）。

红线：只探测、只降级、只给指引；任何装驱动/改配置/加载模块只给规范指引，不代执行。
"""

from __future__ import annotations

import os


# ── 虚拟化层注册表（id, 中文名）── 用于退化计划与报告展示 ──
HYPERVISORS = (
    ("kvm", "KVM/QEMU 虚拟化"),
    ("vmware", "VMware 虚拟化"),
    ("virtualbox", "VirtualBox 虚拟化"),
    ("hyperv", "Hyper-V 虚拟化"),
    ("wsl", "WSL（Windows 子系统）"),
    ("xen", "Xen 虚拟化"),
    ("container", "容器（Docker/Podman/LXC）"),
    ("baremetal", "物理机（裸金属）"),
    ("unknown", "未识别环境"),
)

# 哪些 env 属于「受限虚拟机」（硬件视角受限，部分探针退化）
_RESTRICTED_VM = ("kvm", "vmware", "virtualbox", "hyperv", "xen")
# 哪些 env 属于「强隔离」（容器/WSL，大量 /proc//sys 受限或无完整 init）
_STRONG_ISOLATED = ("container", "wsl")


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# 只读探针：分层识别虚拟化（不写任何状态）                                       #
# --------------------------------------------------------------------------- #

def _detect_systemd_virt() -> str | None:
    """优先用 systemd-detect-virt（用户态统一接口，零副作用）。"""
    import shutil
    if shutil.which("systemd-detect-virt") is None:
        return None
    import subprocess
    try:
        out = subprocess.run(["systemd-detect-virt"], capture_output=True,
                              text=True, timeout=5).stdout.strip().lower()
    except (OSError, subprocess.SubprocessError):
        return None
    mapping = {
        "kvm": "kvm", "qemu": "kvm", "vmware": "vmware", "oracle": "virtualbox",
        "microsoft": "hyperv", "xen": "xen", "wsl": "wsl",
        "docker": "container", "podman": "container", "container-other": "container",
    }
    return mapping.get(out)


def _detect_cpuinfo() -> str | None:
    txt = _read("/proc/cpuinfo")
    if not txt:
        return None
    low = txt.lower()
    if "hypervisor" not in low:
        return None  # 物理机标志：无 hypervisor 字段
    if "kvm" in low or "qemu" in low:
        return "kvm"
    if "vmware" in low:
        return "vmware"
    if "virtualbox" in low or "oracle" in low:
        return "virtualbox"
    if "microsoft" in low:
        return "hyperv"
    if "xen" in low:
        return "xen"
    return "unknown"


def _detect_dmi() -> str | None:
    name = _read("/sys/class/dmi/id/product_name") or ""
    vendor = _read("/sys/class/dmi/id/sys_vendor") or ""
    blob = (name + " " + vendor).lower()
    if "vmware" in blob:
        return "vmware"
    if "virtualbox" in blob or "oracle" in blob:
        return "virtualbox"
    if "qemu" in blob or "kvm" in blob:
        return "kvm"
    if "microsoft" in blob:
        return "hyperv"
    if "xen" in blob:
        return "xen"
    return None


def _detect_wsl() -> str | None:
    ver = _read("/proc/version") or ""
    rel = _read("/proc/sys/kernel/osrelease") or ""
    if "microsoft" in ver.lower() or "wsl" in rel.lower() or "microsoft-standard" in rel.lower():
        return "wsl"
    return None


def _detect_container() -> str | None:
    if os.path.isfile("/.dockerenv"):
        return "container"
    cg = _read("/proc/1/cgroup") or ""
    if any(k in cg for k in ("docker", "kubepods", "podman", "containerd", "libpod")):
        return "container"
    return None


def detect_hypervisor() -> tuple:
    """只读识别本机虚拟化层。返回 (ok, dict)。

    命中则返回 (True, {env, method, product_name})；全未命中视为裸金属 (True, {env:'baremetal'})。
    """
    steps = [
        ("systemd-detect-virt", _detect_systemd_virt),
        ("dmi", _detect_dmi),
        ("wsl", _detect_wsl),
        ("container", _detect_container),
        ("cpuinfo", _detect_cpuinfo),
    ]
    for method, fn in steps:
        r = fn()
        if r and r != "unknown":
            info = {"env": r, "method": method}
            pn = _read("/sys/class/dmi/id/product_name")
            if pn:
                info["product_name"] = pn.strip()
            return True, info
    return True, {"env": "baremetal", "method": "none", "note": "无 hypervisor 标志，判定为物理机"}


def virt_environment() -> str:
    """便捷函数：返回当前 env id（baremetal/kvm/vmware/.../unknown）。"""
    return detect_hypervisor()[1].get("env", "unknown")


# --------------------------------------------------------------------------- #
# 退化计划：把 env 映射到各子系统的可用/退化结论（纯函数，不碰系统）              #
# --------------------------------------------------------------------------- #

def degradation_plan(env: str | None = None) -> list:
    """由虚拟化层生成「各子系统可用/退化」清单（纯函数，只读不写）。

    - baremetal      : 全开（所有只读探针可用）
    - 受限 VM        : 硬件/传感器类退化，OS 级正常
    - 容器/WSL       : 强隔离，硬件/传感器/时空空间维退化，init 类退化
    - unknown        : 保守退化（按受限 VM 处理，避免误读）
    """
    if env is None:
        env = virt_environment()
    if env == "baremetal":
        return [{
            "env": env,
            "tier": "full",
            "title": "物理机：所有只读探针全开（硬件本征/电气传感器/设备长期保障/时空空间维均可用）",
            "scope": "全部子系统",
        }]
    if env in _RESTRICTED_VM:
        return [{
            "env": env,
            "tier": "vm_degraded",
            "title": f"{env} 受限虚拟机：硬件本征与电气传感器按虚拟化硬件处理，"
                     f"SMART/温湿度/IPMI 多不可用，其余 OS 级探针正常",
            "scope": "硬件本征/电气/设备长期保障退化；OS/网络/兼容层正常",
        }, {
            "env": env,
            "tier": "guidance",
            "title": "装增强工具（open-vm-tools / Guest Additions / virtio 驱动）只给规范指引，不代执行",
            "scope": "装驱动/改配置一律指引",
        }]
    if env in _STRONG_ISOLATED:
        return [{
            "env": env,
            "tier": "strong_isolated",
            "title": f"{env} 强隔离环境：/proc//sys 大量受限、无完整 init（WSL）/共享宿主内核（容器），"
                     f"硬件本征/电气传感器/时空空间维（NUMA/真实挂载）退化为概念观测",
            "scope": "硬件/电气/时空空间维退化；init 类探针退化；其余 OS 级按宿主内核口径",
        }]
    # unknown：保守
    return [{
        "env": env,
        "tier": "conservative",
        "title": "未识别环境：保守按受限 VM 处理，硬件/传感器类探针降级为概念观测，避免误读真实状态",
        "scope": "硬件/电气/时空空间维退化",
    }]


def environment_report() -> list:
    """返回本机虚拟化探测概览（✓ 识别出 / ✗ 裸金属）。"""
    ok, info = detect_hypervisor()
    env = info.get("env", "unknown")
    label = dict(HYPERVISORS).get(env, env)
    lines = ["虚拟机环境（virt）· 本机只读探测："]
    lines.append(f"   · 运行环境: {label}（detect via {info.get('method', 'n/a')}）")
    if info.get("product_name"):
        lines.append(f"   · DMI product_name: {info['product_name']}")
    lines.append(f"   · 退化档位: {degradation_plan(env)[0]['tier']}")
    return lines


# --------------------------------------------------------------------------- #
# 完整运行支持（v0.6.43）：只读探测 + 模板生成 + 指引                            #
#   目标（对齐用户「让整体支持在虚拟机完整运行」）：                            #
#   - 看清本机能否完整跑起一层虚拟化（/dev/kvm、CPU VT-x/AMD-V、嵌套开关）；   #
#   - 列出可嵌入 initramfs 的半虚拟化驱动模块并给嵌入指引；                     #
#   - 生成各 Hypervisor 的只读运行配置模板（不写文件、不启动 VM）。             #
#   红线：只探测、只生成模板、只给指引；绝不加载内核模块/启动 VM/装驱动/改配置。#
# --------------------------------------------------------------------------- #

# 各 Hypervisor 在 guest 内「再运行一层虚拟化」的可行性与前提（只读知识库）
_NESTED_SUPPORT = {
    "kvm": ("嵌套虚拟化（KVM-on-KVM）",
            "宿主开启 kvm_intel/kvm_amd 的 nested=1（内核参数），guest 内即可再看到 /dev/kvm；"
            "纯软件退路：qemu-system-* -accel tcg（无 KVM 也能跑，性能低）"),
    "vmware": ("VMware 嵌套（VMM-on-VMM）",
               "宿主 Workstation/ESXi 开启「虚拟化 Intel VT-x/EPT 或 AMD-V/RVI」透传；"
               "纯软件退路：guest 内再装 VMware + 走软件虚拟化（受限）"),
    "virtualbox": ("VirtualBox 嵌套",
                   "宿主开启 VT-x/AMD-V 且 VirtualBox 勾选「启用嵌套分页」；"
                   "纯软件退路：无（VirtualBox 无纯软件加速，需宿主透传）"),
    "hyperv": ("Hyper-V 嵌套（VBS/容器隔离）",
               "宿主开启「嵌套虚拟化」ExposeVirtualizationExtensions；WSL2 可用 .wslconfig 开 nestedVirtualization"),
    "xen": ("Xen 嵌套（PV/HVM 域）",
            "需在宿主 Xen 域开启 nested HVM（nestedhvm=1）；HVM 域可再起 HVM"),
    "wsl": ("WSL2 内运行其他 Hypervisor",
            "WSL2 本身即轻量 Hyper-V VM；在 .wslconfig 设 nestedVirtualization=true 后可跑 KVM/VMware；"
            "纯软件退路：qemu -accel tcg"),
    "container": ("容器内运行虚拟化",
                  "容器内默认无 /dev/kvm（共享宿主内核、无嵌套）；用 --device=/dev/kvm 透传或 qemu -accel tcg 软件模拟；"
                  "privileged + 宿主 nested 才可能看到 /dev/kvm"),
    "baremetal": ("裸金属直接运行",
                  "原生即有 /dev/kvm（需 CPU 支持 VT-x/AMD-V 且 bios 开启）；各 Hypervisor 均可直接装"),
    "unknown": ("未识别环境", "保守处理：先确认 /dev/kvm 与 CPU 虚拟化标志，再决定走硬件加速或软件退路"),
}


def _read_kv(path: str) -> str | None:
    """只读读 /sys 单值参数（如 nested），失败返回 None。"""
    v = _read(path)
    return v.strip() if v else None


def full_run_capability(env: str | None = None) -> list:
    """只读探测「本机能否完整跑起一层虚拟化」：/dev/kvm 可读性、CPU 虚拟化标志、嵌套开关、各 Hypervisor 再运行可行性。

    纯函数、零副作用：不创建 /dev/kvm、不加载 kvm 模块、不启动 VM。
    """
    if env is None:
        env = virt_environment()
    lines = []

    # 1) /dev/kvm 可读性
    kvm_dev = "/dev/kvm"
    if os.path.exists(kvm_dev):
        readable = os.access(kvm_dev, os.R_OK | os.W_OK)
        lines.append(f"   · /dev/kvm: 存在（{'可读写' if readable else '存在但当前无权限'}）— 硬件加速虚拟化可用")
    else:
        lines.append("   · /dev/kvm: 不存在 — 无硬件加速，需走 qemu -accel tcg 软件模拟或确认 bios/模块")

    # 2) CPU 虚拟化标志（VT-x / AMD-V）
    cpu = _read("/proc/cpuinfo") or ""
    clo = cpu.lower()
    if "vmx" in clo and "processor" in clo:
        lines.append("   · CPU 标志: vmx（Intel VT-x）存在")
    elif "svm" in clo and "processor" in clo:
        lines.append("   · CPU 标志: svm（AMD-V）存在")
    else:
        lines.append("   · CPU 标志: 未检测到 vmx/svm（虚拟化可能未开 bios 或被屏蔽）")

    # 3) 嵌套虚拟化开关（只读 /sys）
    nested_intel = _read_kv("/sys/module/kvm_intel/parameters/nested")
    nested_amd = _read_kv("/sys/module/kvm_amd/parameters/nested")
    if nested_intel is not None:
        lines.append(f"   · 嵌套开关 kvm_intel.nested: {nested_intel}（Y 表示可为 guest 再暴露 /dev/kvm）")
    if nested_amd is not None:
        lines.append(f"   · 嵌套开关 kvm_amd.nested: {nested_amd}（1 表示可为 guest 再暴露 /dev/kvm）")
    if nested_intel is None and nested_amd is None:
        lines.append("   · 嵌套开关: /sys 未暴露（多为 guest 或 bios 未开 nested；不影响本机直接跑 VM）")

    # 4) 各 Hypervisor 在本环境下的再运行可行性
    lines.append("   · 各 Hypervisor 再运行可行性（只读知识库）:")
    title, prereq = _NESTED_SUPPORT.get(env, _NESTED_SUPPORT["unknown"])
    lines.append(f"     - 当前环境（{env}）: {title}")
    lines.append(f"       前提: {prereq}")
    return lines


# 可嵌入驱动模块（initramfs 预加载，用于 guest 启动即拿到半虚拟化设备）
_EMBEDDABLE_MODULES = (
    ("virtio-blk", "virtio 块设备（磁盘）", "guest 启动即识别 virtio 磁盘，避免 initramfs 缺失导致无法挂载根"),
    ("virtio-net", "virtio 网络", "guest 启动即拿到 virtio-net，网络早通"),
    ("virtio-scsi", "virtio SCSI", "virtio 方式暴露 SCSI 设备（光驱/磁盘）"),
    ("virtio-gpu", "virtio 显卡", "半虚拟化显示输出（配合 spice/qxl）"),
    ("virtio-balloon", "virtio 内存气球", "宿主机动态回收 guest 内存"),
    ("virtio-9p", "virtio 9P 文件共享", "host↔guest 目录共享（9p 文件系统）"),
    ("vhost-net", "vhost 网络加速", "内核态 virtio-net 数据面卸载，降低延迟"),
    ("vhost-vsock", "vhost vsock", "guest↔host 套接字通道（qemu-guest-agent 回传）"),
    ("bochs_drm", "bochs 标准 VGA DRM", "QEMU 标准 VGA 显示（无 virtio-gpu 时兜底）"),
    ("qxl", "QXL 显卡", "SPICE 下高性能 2D 显示"),
    ("hv_vmbus", "Hyper-V VMBus", "WSL/Hyper-V guest 半虚拟化总线"),
    ("hv_netvsc", "Hyper-V 网络", "Hyper-V 半虚拟化网卡"),
    ("hv_storvsc", "Hyper-V 存储", "Hyper-V 半虚拟化磁盘"),
    ("xen-blkfront", "Xen 块前端", "Xen PV 域磁盘前端"),
    ("xen-netfront", "Xen 网络前端", "Xen PV 域网络前端"),
)


def embeddable_modules(env: str | None = None) -> list:
    """识别可嵌入 initramfs 的半虚拟化/前端驱动模块，并给嵌入指引（只读，不写 initramfs）。

    模块名与嵌入方式按发行版 initramfs 工具分类给规范指引；是否施工由用户在 guest 内确认。
    """
    if env is None:
        env = virt_environment()
    lines = ["   · 可嵌入 initramfs 的驱动模块（按 guest 类型选装，不代写）:"]
    if env in ("hyperv", "wsl"):
        rec = ("hv_vmbus", "hv_netvsc", "hv_storvsc")
    elif env == "xen":
        rec = ("xen-blkfront", "xen-netfront")
    elif env in ("kvm", "vmware", "virtualbox", "baremetal", "unknown"):
        rec = ("virtio-blk", "virtio-net", "virtio-scsi", "virtio-gpu", "virtio-balloon",
               "virtio-9p", "vhost-net", "vhost-vsock", "bochs_drm", "qxl")
    else:  # container 等强隔离：通常不自己构建 guest initramfs
        rec = ("virtio-blk", "virtio-net")
    for mod, zh, why in _EMBEDDABLE_MODULES:
        mark = "● 推荐" if mod in rec else "○ 可选"
        lines.append(f"     - [{mark}] {mod} — {zh}：{why}")
    lines.append("")
    lines.append("   · initramfs 嵌入指引（规范，不代执行）:")
    lines.append("     dracut       : dracut --add-drivers 'virtio-blk virtio-net vhost-net' -f")
    lines.append("     mkinitcpio   : 在 /etc/mkinitcpio.conf 的 MODULES=(...) 加上述模块后 mkinitcpio -P")
    lines.append("     update-initramfs(Debian): 在 /etc/initramfs-tools/modules 加模块后 update-initramfs -u")
    return lines


# 运行配置只读模板（生成文本，不写文件、不启动）
_RUN_TEMPLATES = {
    "kvm": (
        "libvirt (virsh) 域片段（type='kvm'）",
        "<domain type='kvm'>\n"
        "  <name>guest</name>\n"
        "  <memory unit='KiB'>2097152</memory>\n"
        "  <vcpu placement='static'>2</vcpu>\n"
        "  <devices>\n"
        "    <disk type='file' device='disk'>\n"
        "      <driver name='qemu' type='qcow2'/>\n"
        "      <source file='/path/to/disk.qcow2'/>\n"
        "      <target dev='vda' bus='virtio'/>\n"
        "    </disk>\n"
        "    <interface type='network'>\n"
        "      <source network='default'/>\n"
        "      <model type='virtio'/>\n"
        "    </interface>\n"
        "  </devices>\n"
        "</domain>",
    ),
    "qemu_cmd": (
        "QEMU 命令行（软件模拟退路：-accel tcg；有 /dev/kvm 时改 -enable-kvm）",
        "qemu-system-x86_64 \\\n"
        "  -machine q35,accel=kvm \\      # 无 /dev/kvm 时改 accel=tcg\n"
        "  -m 2G -smp 2 \\\n"
        "  -drive file=/path/to/disk.qcow2,if=virtio,format=qcow2 \\\n"
        "  -netdev user,id=n0 -device virtio-net-pci,netdev=n0 \\\n"
        "  -display spice-app",
    ),
    "virtualbox": (
        "VirtualBox（VBoxManage 命令行，嵌套需勾选「启用嵌套分页」）",
        "VBoxManage createvm --name guest --ostype Linux_64 --register\n"
        "VBoxManage modifyvm guest --memory 2048 --cpus 2 --nestedpaging on\n"
        "VBoxManage storagectl guest --name sata --controller IntelAhci\n"
        "VBoxManage storageattach guest --storagectl sata --port 0 --device 0 \\\n"
        "  --type hdd --medium /path/to/disk.vdi",
    ),
    "vmware": (
        "VMware .vmx 片段（嵌套虚拟化：vhv.enable = \"TRUE\"）",
        "guest.vmx 片段:\n"
        "  vhv.enable = \"TRUE\"\n"
        "  vmx.allowNested = \"TRUE\"\n"
        "  numvcpus = \"2\"\n"
        "  memsize = \"2048\"\n"
        "  scsi0.virtualDev = \"pvscsi\"\n"
        "  ethernet0.virtualDev = \"vmxnet3\"",
    ),
    "wsl": (
        "WSL2 .wslconfig（用户目录 %USERPROFILE%\\.wslconfig，开嵌套虚拟化）",
        "[wsl2]\n"
        "  nestedVirtualization=true\n"
        "  memory=4GB\n"
        "  processors=4",
    ),
    "container": (
        "容器内运行（透传 /dev/kvm 或软件模拟）",
        "docker run --device=/dev/kvm ...   # 宿主开 nested 且透传\n"
        "qemu-system-x86_64 -machine q35,accel=tcg   # 无 KVM 的纯软件退路",
    ),
}


def run_config_template(env: str | None = None) -> list:
    """生成各 Hypervisor 的「只读运行配置模板」（文本，不写文件、不启动 VM）。"""
    if env is None:
        env = virt_environment()
    lines = ["   · 运行配置只读模板（生成文本，不写文件、不启动 VM）:"]
    keys = [env] if env in _RUN_TEMPLATES else []
    if not keys:
        keys = ["kvm", "qemu_cmd", "container"]  # 未知环境给常见三套
    for k in keys:
        title, tmpl = _RUN_TEMPLATES[k]
        lines.append(f"   ── {title} ──")
        for tline in tmpl.splitlines():
            lines.append("     " + tline)
        lines.append("")
    return lines


# --------------------------------------------------------------------------- #
# 端到端报告（无参可调用，供任务/CLI/GUI）                                       #
# --------------------------------------------------------------------------- #

def virt_report(env_tags: list | None = None, readings: dict | None = None) -> tuple:
    """端到端生成虚拟机环境报告：识别层 → 退化计划 → 子系统影响。只读不写。"""
    readings = readings or {}
    if "hypervisor" not in readings:
        ok, hv = detect_hypervisor()
        readings["hypervisor"] = hv
    else:
        hv = readings["hypervisor"]
    env = hv.get("env", "unknown")
    plan = degradation_plan(env)

    lines = ["== 虚拟机环境报告（virt：识别虚拟化层 + 不同 VM 内优雅降级，只读不写）=="]
    lines.append(f"维度标签: {sorted(set(env_tags or [])) or '未声明（默认基线）'}")
    label = dict(HYPERVISORS).get(env, env)
    lines.append("")
    lines.append("[① 虚拟化层识别]")
    lines.append(f"   · 运行环境: {label}（检测方式: {hv.get('method', 'n/a')}）")
    if hv.get("product_name"):
        lines.append(f"   · DMI product_name: {hv['product_name']}")
    if hv.get("note"):
        lines.append(f"   · 备注: {hv['note']}")

    lines.append("")
    lines.append("[② 优雅降级计划（让整体在不同 VM 都能正常运行）]")
    for p in plan:
        lines.append(f"   · [{p['tier']}] {p['title']}")
        lines.append(f"       影响范围: {p['scope']}")

    lines.append("")
    lines.append("[③ 子系统影响（回链到整体）]")
    if env == "baremetal":
        lines.append("   · 所有子系统按完整能力运行，无退化。")
    elif env in _RESTRICTED_VM:
        lines.append("   · 硬件本征/电气/设备长期保障：按虚拟化硬件退化，只给指引不读敏感信号")
        lines.append("   · 时空空间维（NUMA/真实挂载）：受限 VM 内部分退化")
        lines.append("   · OS/网络/兼容层/远程接入：照常运行")
    elif env in _STRONG_ISOLATED:
        lines.append("   · 硬件本征/电气传感器/时空空间维：强隔离下退化为概念观测")
        lines.append("   · init 类（服务状态/守护）探针：WSL 无完整 init 退化；容器共享宿主内核")
        lines.append("   · OS 级只读探针：按宿主内核口径运行，其余子系统照常")
    else:
        lines.append("   · 未识别：保守退化，硬件/电气/时空空间维降级")

    lines.append("")
    lines.append("[④ 完整运行能力（能否在本地/再嵌套一层跑起虚拟化，只读探测）]")
    for l in full_run_capability(env):
        lines.append(l)

    lines.append("")
    lines.append("[⑤ 可嵌入驱动模块（guest 启动即拿到半虚拟化设备的 initramfs 预加载，只给指引）]")
    for l in embeddable_modules(env):
        lines.append(l)

    lines.append("")
    lines.append("[⑥ 运行配置模板（只读生成，不写文件/不启动 VM）]")
    for l in run_config_template(env):
        lines.append(l)

    lines.append("")
    lines.append("安全不变量：virt 只识别、降级与给完整运行模板，绝不加载内核模块/启动 VM/装驱动/改配置；"
                 "任何改造由用户在 guest 内或厂商工具确认。")
    return True, "\n".join(lines)


# --------------------------------------------------------------------------- #
# 写操作（仅指引，不代执行）                                                     #
# --------------------------------------------------------------------------- #

def guide_guest_tools() -> tuple:
    """指引在 guest 内安装增强工具（不代执行）。"""
    lines = [
        "guest 内增强工具安装（规范指引，不代执行）:",
        "   1. KVM/QEMU: 安装 spice-vdagent + qemu-guest-agent，启用 virtio 驱动",
        "   2. VMware: 安装 open-vm-tools（systemd 启用 vmtoolsd）",
        "   3. VirtualBox: 安装 virtualbox-guest-dkms + virtualbox-guest-utils（Guest Additions）",
        "   4. Hyper-V: 启用 Linux 集成服务（hv_utils），WSL 默认随 Windows 提供",
        "   5. 容器: 无需 guest 工具，资源限制由宿主 cgroup/compose 声明",
    ]
    return True, "\n".join(lines)


TUNES = (
    ("guide_guest_tools", "guest 内增强工具安装（规范指引，不代执行）"),
)


def virt_tune_list() -> list:
    """返回 virt 写指引清单，供 CLI/GUI 展示。只读展示，调用只回指引。"""
    return [f"· {fn}() — {desc}" for fn, desc in TUNES]
