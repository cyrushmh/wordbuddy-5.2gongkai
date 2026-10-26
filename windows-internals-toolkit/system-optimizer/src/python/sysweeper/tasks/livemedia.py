"""可启动介质制作能力任务（吸收 livecd / live DVD / live BD / 可启动 USB 制作技术）。

只读核验本机制作可启动介质的能力：ISO 构建工具链 / BIOS·UEFI 引导加载器 /
El Torito·混合镜像 / 压缩根系统(squashfs/overlayfs/casper) / U 盘写入工具 / 固件模式。
绝不执行 dd/xorriso/mkisofs 实际构建、绝不挂载/解包 ISO、绝不写设备。
"""

from __future__ import annotations

from ..models import Action, Task

N = lambda op, desc="": Action("native", op, desc)

TASKS = [
    Task(
        id="livemedia_capability",
        platform="any",
        title="可启动介质制作能力诊断",
        category="maintenance",
        risk="low",
        desc="只读核验本机制作 livecd/dvd/bd/usb 的能力：ISO 构建工具链(xorriso/mkisofs/"
             "genisoimage/grub-mkrescue/mtools/isohybrid)、BIOS·UEFI 引导加载器、"
             "El Torito·混合镜像、压缩根系统(squashfs/overlayfs/casper)、U 盘写入工具、"
             "本机固件启动模式；可选传入 ISO 路径做只读可启动性校验。",
        standards=["livecd/dvd/bd/usb 制作技术：可启动介质 = 镜像构建(El Torito/isohybrid)"
                   " + 引导加载(ISOLINUX/GRUB/systemd-boot) + 压缩根(squashfs)"
                   " + 写入(dd/Ventoy)；BD 用 UDF 2.50+ 且可启动，UEFI 介质须含"
                   " /EFI/BOOT/BOOTX64.EFI"],
        actions=[
            N("livemedia.livemedia_report", "只读核验可启动介质制作能力（可选 ISO 路径校验）"),
        ],
        notes=["制作双启 Live USB：用 xorriso 或 grub-mkrescue 产出 isohybrid 镜像后 dd 到 U 盘。",
               "本机为 UEFI 固件时，回启动介质必须含 EFI 引导入口（GRUB-EFI 或 systemd-boot）。",
               "Live 系统只读压缩根用 squashfs，写时叠加/持久化靠 overlayfs + casper。"],
        caveats=["仅读工具存在性/目录与 /sys 状态/给定 ISO 的只读元数据；绝不 mkisofs/xorriso "
                 "构建、绝不 dd 到设备、绝不挂载/解包 ISO、绝不 modprobe。"],
    ),
]
