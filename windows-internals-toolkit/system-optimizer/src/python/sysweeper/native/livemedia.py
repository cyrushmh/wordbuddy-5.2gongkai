"""可启动介质制作能力只读诊断（吸收 livecd / live DVD / live BD / 可启动 USB 制作技术）。

可启动介质（Live CD / DVD / Blu-ray / USB）是把一个「能直接从光盘或 U 盘启动并运行」的
系统镜像做出来。制作链路是一套跨「镜像构建 → 引导加载 → 混合 → 压缩根 → 写入」的工程：

- 镜像构建 : xorriso（GNU，mkisofs/genisoimage 的现代继任者，原生支持 El Torito /
            isohybrid / UDF）/ mkisofs（cdrtools）/ genisoimage（Debian 系 GPL 复刻）/
            grub-mkrescue（GRUB2 一键产出 BIOS+UEFI 双启 rescue 镜像）/ mtools（造 EFI FAT 映像）
- 引导加载   : BIOS 侧 = ISOLINUX(isolinux.bin) / SYSLINUX(extlinux) / GRUB(i386-pc)；
            UEFI 侧 = GRUB(EFI) 产出 grubx64.efi（标准入口 /EFI/BOOT/BOOTX64.EFI）/
            systemd-boot(bootctl)
- El Torito : ISO 9660 的可启动扩展（BIOS 引导）；-no-emul-boot/-boot-load-size 4/
            -boot-info-table；UEFI 替代引导 -eltorito-alt-boot -efi-boot
- 混合镜像   : isohybrid —— 给 ISO 加一个 MBR/GPT 头，使之既能刻光盘也能 dd 到 U 盘启动
            （xorriso 的 -isohybrid-mbr 或 SYSLINUX 的 isohybrid）
- 压缩根系统 : squashfs（mksquashfs/unsquashfs，Live 系统的只读压缩根）/ overlayfs（写时
            叠加，persistence 基础）/ casper（Debian/Ubuntu Live 的 initramfs 持久化钩子）
- 写入 U 盘  : dd（混合镜像直接块复制）/ Ventoy（多 ISO 启动器）；Rufus/balenaEtcher 为
            Windows/macOS 工具，本机不直接探测
- 固件/模式  : 本机当前是 UEFI（/sys/firmware/efi 存在）还是 BIOS(Legacy)，决定回启动介质
            必须含哪种引导入口
- 介质规格   : CD 650/700MB(ISO9660) / DVD 4.7GB 单层·8.5GB 双层(ISO9660/UDF) /
            BD 25GB 单层·50GB 双层·100/128GB BDXL(UDF 2.50+，可启动) / USB 任意容量
            （UEFI 需 ESP FAT32 含 /EFI/BOOT/BOOTX64.EFI，或 isohybrid 镜像直接 dd）

「你中有我、系统的看待一切」：制作可启动介质是 storage(块设备/分区) + kernel(overlayfs 模块)
+ osi/network(若 Live 系统要联网) + media(若 Live 含图像优化工作流) + 固件(启动模式) 的交汇。
本模块只读核验「本机具备制作何种可启动介质的能力」，把分散前置拼成一张能力地图。

红线：不执行任何写入/构建命令——绝不 mkisofs/xorriso 实际打包、绝不 dd 到任何设备、绝不
挂载/解包 ISO、绝不 modprobe overlay、不改固件变量。仅 shutil.which + 目录与 /sys 存在性 +
对「给定 ISO 路径」只读元数据（file/isoinfo/xorriso -report_el_torito，均为只读探测）。
"""

from __future__ import annotations

import os
import re
import shutil

from . import common


# ISO 构建工具链：(显示名, which 名, 常见备用绝对路径)
_ISO_TOOLS = (
    ("xorriso",       "xorriso",       ()),
    ("mkisofs",       "mkisofs",       ("/usr/bin/mkisofs", "/opt/schily/bin/mkisofs")),
    ("genisoimage",   "genisoimage",   ("/usr/bin/genisoimage",)),
    ("grub-mkrescue", "grub-mkrescue", ("/usr/bin/grub-mkrescue",)),
    ("mtools(mformat)", "mformat",     ("/usr/bin/mformat",)),
    ("isohybrid",     "isohybrid",     ("/usr/bin/isohybrid",)),
)

# BIOS 引导加载器：(显示名, 探测方式)
# 用 (which_name, extra_path) 二元组；extra_path 存在即判就位
_BIOS_LOADER = (
    ("ISOLINUX(isolinux.bin)", None, "/usr/lib/ISOLINUX/isolinux.bin"),
    ("SYSLINUX(extlinux)",     "extlinux", "/usr/bin/extlinux"),
    ("GRUB(i386-pc)",          "grub-install", "/usr/lib/grub/i386-pc"),
)

# UEFI 引导加载器：(显示名, which_name, 模块/二进制目录)
_UEFI_LOADER = (
    ("GRUB(EFI x86_64-efi)", "grub-mkimage", "/usr/lib/grub/x86_64-efi"),
    ("systemd-boot(bootctl)", "bootctl", "/usr/lib/systemd/boot/efi/systemd-bootx64.efi"),
)

# 压缩根系统 / 持久化
_SQUASH_BINS = ("mksquashfs", "unsquashfs")
_CASPER_PATH = "/usr/share/initramfs-tools/scripts/casper"

# U 盘写入工具
_USB_WRITE = (
    ("dd", "dd", ()),
    ("Ventoy", "ventoy", ("/opt/ventoy/Ventoy", "/usr/bin/VentoyGUI")),
)

# 介质规格知识（只读参考，恒定文本）
_MEDIA_SPEC = (
    ("CD",   "650/700 MB",        "ISO 9660"),
    ("DVD",  "4.7GB 单层 / 8.5GB 双层(DVD-DL)", "ISO 9660 / UDF"),
    ("BD",   "25GB 单层 / 50GB 双层 / 100-128GB BDXL", "UDF 2.50+（可启动）"),
    ("USB",  "任意",              "FAT32(≤32GB 单文件)/exFAT；UEFI 需 ESP(FAT32) 含 /EFI/BOOT/BOOTX64.EFI，或 isohybrid 镜像直接 dd"),
)


def _ver(bin_name: str, extra_paths=()) -> tuple:
    """返回 (found, version_str)。仅读取版本号，绝不执行写入/构建。"""
    bp = shutil.which(bin_name)
    if not bp:
        for p in extra_paths:
            if os.path.exists(p):
                bp = p
                break
    if not bp:
        return (False, "")
    ver = ""
    for flag in ("--version", "-version"):
        rc, out = common.run(f'"{bp}" {flag}', timeout=10)
        if rc == 0 and out.strip():
            for line in out.splitlines():
                m = re.search(r"(\d+\.\d+(?:\.\d+)?)", line)
                if m:
                    ver = m.group(1)
                    break
            if not ver:
                ver = "（版本未知）"
            break
    return (True, ver)


def _firmware() -> tuple:
    """返回 (uefi_present, efivars_present, secureboot_note)。"""
    efi = os.path.isdir("/sys/firmware/efi")
    efivars = os.path.isdir("/sys/firmware/efi/efivars")
    sb = "不适用（非 UEFI 固件）"
    if efivars:
        try:
            ents = os.listdir("/sys/firmware/efi/efivars")
            if any(n.startswith("SecureBoot-") for n in ents):
                sb = "变量存在（固件支持 Secure Boot；当前启用态需 root 读该变量，只读不解析）"
            else:
                sb = "变量区可见但无 SecureBoot 项（多半未启用 Secure Boot）"
        except OSError:
            sb = "变量区不可列（权限不足，无法判定 Secure Boot）"
    return efi, efivars, sb


def _iso_check(iso_path: str) -> str:
    """对给定 ISO 路径只读核验可启动性（file/isoinfo/xorriso -report_el_torito）。"""
    if not iso_path or not os.path.exists(iso_path):
        return "（未传入有效 ISO 路径——仅做工具链/能力诊断；传入路径可额外校验其可启动性）"
    lines = [f"给定镜像校验（只读元数据）：{iso_path}"]
    rc, out = common.run(f'file -b "{iso_path}"', timeout=10)
    if rc == 0 and out.strip():
        lines.append(f"  file 类型 : {out.strip()}")
    rc, out = common.run(f'isoinfo -d -i "{iso_path}" 2>/dev/null', timeout=10)
    if rc == 0 and out.strip():
        has_el = "El Torito" in out
        lines.append(f"  isoinfo   : {'含 El Torito 引导目录（BIOS 可启动）' if has_el else '未含 El Torito'}")
        for line in out.splitlines():
            if "Platform" in line or "Boot" in line:
                lines.append(f"             : {line.strip()}")
    rc, out = common.run(f'xorriso -report_el_torito as_mkisofs "{iso_path}" 2>/dev/null', timeout=15)
    if rc == 0 and out.strip():
        lines.append("  xorriso El Torito 报告（节选）：")
        for line in out.splitlines()[:14]:
            lines.append(f"    {line}")
    return "\n".join(lines)


def livemedia_report(iso_path: str = None) -> tuple:
    """可启动介质制作能力只读诊断。

    返回 (ok, msg)：ok 恒为 True（任意主机都可诊断）。报告列出 ISO 构建工具链 / BIOS·UEFI
    引导加载器 / El Torito·混合镜像能力 / 压缩根系统 / U 盘写入工具 / 本机固件模式 / 介质规格
    知识，并（可选）对给定 ISO 路径做只读可启动性校验。缺失项标注为制作建议。

    红线：绝不执行 dd/xorriso/mkisofs 实际构建，绝不挂载/解包 ISO，绝不写任何设备，
    绝不 modprobe——仅 which + 目录与 /sys 存在性 + 给定 ISO 的只读元数据。
    """
    lines = ["可启动介质制作能力（只读诊断；吸收 livecd/dvd/bd/usb 制作技术）："]

    # 一、ISO 构建工具链
    lines.append("  一、ISO 镜像构建工具链：")
    for name, which_name, extras in _ISO_TOOLS:
        found, ver = _ver(which_name, extras)
        if found:
            lines.append(f"    {name:<18} : ✓ 已安装（{ver or '版本未知'}）")
        else:
            lines.append(f"    {name:<18} : ✗ 未安装（缺失）")

    # 二、引导加载器
    lines.append("  二、引导加载器（Bootloader）：")
    lines.append("    [BIOS 侧]")
    for name, which_name, extra in _BIOS_LOADER:
        ok = bool(shutil.which(which_name)) if which_name else False
        if not ok and extra:
            ok = os.path.exists(extra)
        lines.append(f"      {name:<24} : {'✓ 已就位' if ok else '✗ 缺失'}")
    lines.append("    [UEFI 侧]")
    for name, which_name, moddir in _UEFI_LOADER:
        ok = bool(shutil.which(which_name)) or (moddir and os.path.exists(moddir))
        lines.append(f"      {name:<24} : {'✓ 已就位' if ok else '✗ 缺失'}")

    # 三、El Torito / 混合镜像
    lines.append("  三、El Torito / 混合镜像能力（isohybrid）：")
    iso_hybrid = bool(shutil.which("isohybrid"))
    xor_ok = bool(shutil.which("xorriso"))
    lines.append(f"    SYSLINUX isohybrid : {'✓ 已就位' if iso_hybrid else '✗ 缺失'}")
    lines.append(f"    xorriso -isohybrid-mbr : {'✓ 已就位' if xor_ok else '✗ 缺失（xorriso 未装）'}")
    lines.append("    混合类型支持         : MBR（≤2TB）/ GPT（>2TB，xorriso 支持）")

    # 四、压缩根系统 / 持久化
    lines.append("  四、压缩根系统 / 持久化（Live 核心）：")
    sq = all(shutil.which(b) for b in _SQUASH_BINS)
    lines.append(f"    squashfs-tools(mksquashfs/unsquashfs) : {'✓ 已安装' if sq else '✗ 未安装'}")
    ovl = os.path.isdir("/sys/module/overlay")
    lines.append(f"    overlayfs 内核支持 : {'✓ 已加载(/sys/module/overlay)' if ovl else '✗ 未加载（可 modprobe overlay，本工具不自动加载）'}")
    casper = os.path.exists(_CASPER_PATH) or bool(shutil.which("casper"))
    lines.append(f"    casper(持久化钩子) : {'✓ 已就位' if casper else '✗ 未安装（Debian/Ubuntu Live 持久化用）'}")

    # 五、U 盘写入工具
    lines.append("  五、可启动介质写入（USB）：")
    for name, which_name, extras in _USB_WRITE:
        found = bool(shutil.which(which_name)) or any(os.path.exists(p) for p in extras)
        lines.append(f"    {name:<12} : {'✓ 可用' if found else '✗ 缺失'}")
    lines.append("    （Rufus / balenaEtcher 为 Windows/macOS 工具，本机不直接探测）")

    # 六、本机固件 / 启动模式
    lines.append("  六、本机固件 / 启动模式（决定回启动介质需含哪种入口）：")
    efi, efivars, sb = _firmware()
    lines.append(f"    当前固件   : {'UEFI（检测到 /sys/firmware/efi）' if efi else 'BIOS(Legacy) 或信息不可读'}")
    lines.append(f"    efivars     : {'✓ 可访问' if efivars else '✗ 不可访问'}")
    lines.append(f"    Secure Boot : {sb}")

    # 七、介质规格知识（只读参考）
    lines.append("  七、介质规格知识（只读参考）：")
    for medium, cap, fs in _MEDIA_SPEC:
        lines.append(f"    {medium:<5} : 容量 {cap:<32} 文件系统 {fs}")

    # 八、可选：给定 ISO 校验
    lines.append("  八、给定 ISO 校验（可选）：")
    lines.append("    " + _iso_check(iso_path).replace("\n", "\n    "))

    # 汇总建议
    lines.append("  汇总 / 制作建议：")
    if not xor_ok and not bool(shutil.which("grub-mkrescue")):
        lines.append("    - 首选 xorriso 或 grub-mkrescue 一条命令产出 BIOS+UEFI 双启镜像；"
                     "二者皆无时无法在本机构作可启动 ISO。")
    if not sq:
        lines.append("    - 缺 squashfs-tools 则无法打包 Live 只读压缩根（mksquashfs）。")
    if not (iso_hybrid or xor_ok):
        lines.append("    - 想把 ISO 同时用于光盘与 U 盘（dd 启动），需 isohybrid 能力（xorriso 或 SYSLINUX）。")
    if efi and not any(shutil.which(n) or (d and os.path.exists(d)) for n, _w, d in _UEFI_LOADER):
        lines.append("    - 本机为 UEFI 固件：回启动介质必须含 /EFI/BOOT/BOOTX64.EFI（GRUB-EFI 或 systemd-boot）。")
    lines.append("    红线：本工具只诊断能力、绝不 mkisofs/xorriso 构建、绝不 dd 到设备、绝不挂载/解包 ISO。")
    return True, "\n".join(lines)
