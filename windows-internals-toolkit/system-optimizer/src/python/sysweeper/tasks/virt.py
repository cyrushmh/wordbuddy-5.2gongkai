"""虚拟机环境任务（platform=any，跨平台）。

只读识别本工具运行在哪一层虚拟化，并给出「在不同虚拟机内优雅降级」的应对；
任何装增强工具/改 QEMU-crosvm 配置/加载内核模块的高危动作一律只给规范指引，不代执行
——严守本项目只读红线。

引擎（detect_hypervisor / degradation_plan / virt_report）是纯函数，由 virt_report
串联；GUI 可让用户看到当前 env 与退化档位，确认整体在受限 VM 内只降级不崩溃。"""

from __future__ import annotations

from ..models import Action, Task

S = lambda cmd, desc="", rev=False: Action("shell", cmd, desc, rev)
M = lambda text, desc="": Action("manual", text, desc)
N = lambda op, desc="": Action("native", op, desc)


TASKS = [
    Task(
        id="virt_report",
        platform="any",
        title="虚拟机环境识别与优雅降级（只读报告）",
        category="maintenance",
        risk="low",
        desc="只读识别本工具自身运行在裸金属/KVM/VMware/VirtualBox/Hyper-V/Xen/WSL/容器哪一层，"
             "并给出该环境下各只读探针的「可用/退化」结论，确保整体在不同虚拟机内都能正常运行"
             "（只降级不崩溃）。绝不装增强工具/改配置/加载模块。",
        actions=[
            N("virt.virt_report", "端到端生成虚拟机环境报告（识别层→退化计划→子系统影响）"),
        ],
        notes=["软件只读能力面：只探测、只降级、只给指引，不装驱动/不改配置/不加载内核模块。"],
        standards=["[国际] systemd-detect-virt（跨 Hypervisor 统一用户态检测接口）",
                  "[国际] DMTF SMBIOS / DMI（product_name/sys_vendor 暴露虚拟化层）",
                  "[国际] DMTF Redfish（硬件/虚拟化资源管理事实标准）",
                  "[国际] OCI 运行时规范（容器隔离：runc/crun）",
                  "[国际] libvirt（统一虚拟化管理层）"],
    ),
    Task(
        id="virt_guest_tools_guidance",
        platform="any",
        title="guest 内增强工具安装（规范指引）",
        category="maintenance",
        risk="low",
        desc="给出在 KVM/QEMU、VMware、VirtualBox、Hyper-V、WSL 内安装增强工具（open-vm-tools/"
             "Guest Additions/virtio 驱动/Linux 集成服务）的规范指引，绝不自动安装。",
        actions=[
            M("KVM/QEMU 装 spice-vdagent+qemu-guest-agent；VMware 装 open-vm-tools；"
              "VirtualBox 装 Guest Additions；Hyper-V 启用 Linux 集成服务；容器无需 guest 工具。",
              "guest 内增强工具安装（规范指引，不代执行）"),
            N("virt.guide_guest_tools", "输出 guest 内增强工具安装指引（只给步骤，不装驱动/不改配置）"),
        ],
        notes=["增强工具安装属于写操作，一律只给规范指引；是否施工由用户在 guest 内或厂商工具确认。"],
        standards=["[国际] systemd-detect-virt / open-vm-tools（VMware 开源 guest 工具）",
                  "[国际] VirtualBox Guest Additions 文档",
                  "[国际] Hyper-V Linux 集成服务（hv_utils）"],
    ),
    Task(
        id="virt_full_run_support",
        platform="any",
        title="虚拟机完整运行支持（只读探测 + 模板生成）",
        category="maintenance",
        risk="low",
        desc="只读探测本机能否完整跑起一层虚拟化（/dev/kvm 可读性、CPU VT-x/AMD-V 标志、嵌套开关 kvm_intel.nested/"
             "kvm_amd.nested），列出可嵌入 initramfs 的半虚拟化驱动模块（virtio/9p/vhost/DRM/Hyper-V/Xen 前端）"
             "并给 dracut/mkinitcpio/update-initramfs 嵌入指引，生成各 Hypervisor 只读运行配置模板"
             "（libvirt XML / QEMU 命令行 / VBoxManage / VMware .vmx / WSL .wslconfig）。"
             "绝不加载内核模块/启动 VM/装驱动/改配置——只探测、只生成模板、只给指引。",
        actions=[
            N("virt.full_run_capability", "探测 /dev/kvm、CPU 虚拟化标志与嵌套开关"),
            N("virt.embeddable_modules", "列出可嵌入 initramfs 的半虚拟化驱动模块并给嵌入指引"),
            N("virt.run_config_template", "生成各 Hypervisor 只读运行配置模板"),
        ],
        notes=["完整运行支持严守只读红线：只探测/模板/指引，不加载内核模块、不启动 VM、不装驱动、不改配置；"
               "是否施工始终由用户在 guest 内或厂商工具确认。"],
        standards=["[国际] KVM /dev/kvm 与 nested 参数（内核文档 admin-guide/kernel-parameters）",
                  "[国际] libvirt 域 XML（type='kvm' / virtio 设备总线）",
                  "[国际] OVMF/UEFI + virtio 半虚拟化设备规范",
                  "[国际] Hyper-V 嵌套虚拟化 ExposeVirtualizationExtensions / WSL .wslconfig",
                  "[国际] VMware .vmx vhv.enable 嵌套虚拟化开关"],
    ),
]
