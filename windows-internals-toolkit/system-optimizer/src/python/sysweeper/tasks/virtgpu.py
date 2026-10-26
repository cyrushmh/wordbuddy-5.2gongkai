"""虚拟化与 GPU 虚拟化诊断任务（platform="any"，v0.6.15「导入 yttrium-virtio-gpu」）。

立项：把 arehnman/yttrium-virtio-gpu 与社区 virtio-gpu 协议吸收进本工具——guest 内
virtio-gpu 设备经 Venus 协议把 Vulkan/D3D/GL 命令转发到宿主 Vulkan 驱动，无需 GPU 直通
即可加速。本任务只读诊断「是否虚拟化、是否 virtio 设备、有无 virtio-gpu、GPU 后端」。

参照（权威文档，仅用于把「该看什么」钉死）：
- github.com/arehnman/yttrium-virtio-gpu —— Windows KVM/QEMU guest 的 VirtIO GPU
  （D3D/VK/GL 经 Venus 协议到宿主 Vulkan，无需 GPU 直通）
- VirtIO / virglrenderer / crosvm 上游文档 —— virtio-gpu 设备协议与渲染后端职责边界
"""
from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)
M = lambda text, desc="": Action("manual", text, desc)

VIRTGPU = ("[社区] arehnman/yttrium-virtio-gpu（Windows KVM/QEMU guest 的 VirtIO GPU："
           "D3D/VK/GL 经 Venus 协议转发到宿主 Vulkan，无需 GPU 直通即可加速）")


TASKS = [
    Task(
        id="virtgpu_report",
        platform="any",
        title="虚拟化与 GPU 虚拟化只读诊断（VirtIO-GPU / Venus 坐标系）",
        category="hardware",
        risk="low",
        desc="只读核验本机是否虚拟化（hypervisor 标志）、有无 virtio 设备、是否挂着 virtio-gpu"
             "（Venus 协议后端，可免直通加速）、以及 DRM 显示卡后端。",
        actions=[
            N("virtgpu.capabilities_report", "能力自检：各维度是否可诊断 + 红线声明"),
            N("virtgpu.virtgpu_report", "输出虚拟化/GPU 虚拟化整体只读诊断"),
            M("云游戏/虚拟机需硬件加速时，确认 guest 启用 virtio-gpu + 宿主有 Vulkan 驱动"
              "（配置改动，由你决定做不做）", "确认加速路径（写操作，opt-in）"),
        ],
        standards=[VIRTGPU],
        notes=[
            "虚拟化判定：/proc/cpuinfo 的 hypervisor 标志 + vmx/svm；细分 KVM/QEMU、VMware、"
            "Xen、Hyper-V/WSL。",
            "virtio 设备：枚举 /sys/bus/virtio/devices；virtio-gpu 看设备 modalias 是否含 "
            "virtio:...gpu，由 Venus 协议后端驱动。",
            "显示卡：/sys/class/drm/card*；物理机直出还是虚拟 GPU 一眼可分。",
            "Venus 协议让 guest 内 Vulkan 命令旁路到宿主驱动，是云游戏/虚拟机 GPU 加速主路径。",
        ],
        caveats=[
            "只读任务：不加载/卸载内核模块、不装驱动、不改 QEMU/crosvm 配置、不连校外网。",
        ],
    ),
]
