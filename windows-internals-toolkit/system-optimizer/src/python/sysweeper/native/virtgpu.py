"""虚拟化与 GPU 虚拟化只读诊断。

基于 arehnman/yttrium-virtio-gpu 与社区 virtio-gpu 协议：guest 内 virtio-gpu 设备
通过 Venus 协议把 Vulkan/D3D/GL 命令转发到宿主 Vulkan 驱动（virglrenderer/crosvm），
无需 GPU 直通即可获得加速。本模块只读核验「是否虚拟化、是否 virtio 设备、
是否有 virtio-gpu、GPU 渲染后端」。

红线：不加载/卸载内核模块、不装驱动、不改 QEMU/crosvm 配置、不连校外网。
"""
from . import common

_DEF = "（未知）"


def _hypervisor() -> str:
    rc, out = common.run("cat /proc/cpuinfo 2>/dev/null", timeout=5)
    if rc == 0:
        low = out.lower()
        if "hypervisor" in low:
            if "kvm" in low or "qemu" in low:
                return "KVM/QEMU 虚拟化"
            if "vmware" in low:
                return "VMware"
            if "xen" in low:
                return "Xen"
            if "microsoft" in low:
                return "Hyper-V / WSL"
            return "检测到 hypervisor 标志（虚拟化）"
    return "物理机（无 hypervisor 标志）"


def _virtio_devices() -> list:
    rc, out = common.run("ls /sys/bus/virtio/devices 2>/dev/null", timeout=5)
    if rc != 0 or not out.strip():
        return []
    return [d.strip() for d in out.splitlines() if d.strip()]


def _virtio_gpu() -> bool:
    rc, modalias = common.run(
        "for d in /sys/bus/virtio/devices/*; do cat $d/modalias 2>/dev/null; done", timeout=5)
    if rc == 0 and "virtio:" in modalias and "gpu" in modalias.lower():
        return True
    return False


def _gpu_cards() -> list:
    rc, out = common.run("ls /sys/class/drm/card* 2>/dev/null", timeout=5)
    if rc != 0 or not out.strip():
        return []
    # /sys/class/drm 下 card0 是 GPU 实体，card0-* 是连接器/编码器符号链接，需排除
    cards = []
    for c in out.splitlines():
        name = c.strip().split("/")[-1]
        if name[:4] == "card" and name[4:].isdigit():
            cards.append(name)
    return cards


def capabilities_report() -> tuple:
    lines = [
        "虚拟化 / GPU 虚拟化诊断 · 能力自检",
        "可诊断维度：",
        "  1. hypervisor 标志（/proc/cpuinfo: vmx/svm/hypervisor）",
        "  2. virtio 设备枚举（/sys/bus/virtio/devices）",
        "  3. virtio-gpu 设备（Venus 协议后端，无需 GPU 直通）",
        "  4. DRM 显示卡（/sys/class/drm/card*）",
        "红线：不加载模块、不装驱动、不改 QEMU/crosvm、不连校外网。",
    ]
    return (True, "\n".join(lines))


def virtgpu_report() -> tuple:
    lines = []
    lines.append("==== 虚拟化与 GPU 虚拟化只读诊断 ====")
    lines.append(f"[虚拟化] {_hypervisor()}")
    devs = _virtio_devices()
    lines.append(f"[virtio 设备] {len(devs)} 个"
                 + (f": {', '.join(devs[:6])}" if devs else "（非 virtio 环境）"))
    lines.append(f"[virtio-gpu] {'检测到（Venus 协议后端可用，无需 GPU 直通）' if _virtio_gpu() else '未检测到'}")
    cards = _gpu_cards()
    lines.append(f"[显示卡] {', '.join(cards) if cards else _DEF}")
    lines.append("")
    lines.append("提示（基于 yttrium-virtio-gpu）：guest 内 virtio-gpu + Venus 协议")
    lines.append("把 Vulkan 命令转发到宿主驱动，是云游戏/虚拟机 GPU 加速的常用路径。")
    lines.append("注：本模块只读取，下一步改动由你决定。")
    return (True, "\n".join(lines))
