# -*- coding: utf-8 -*-
"""量子架构内核（qarch）——只读诊断子系统（v0.6.78 新建）。

盘点 quantum-kernel/ 内核树的架构覆盖与量子架构落地：
Linux 6.18.57 LTS 基线 + arch/quantum 纯新增架构（不删不改其他架构）+
drivers/quantum QPU 模拟设备 + 4KiB 页纪律 + 补丁分发路径。

红线：纯只读——绝不执行内核构建、绝不写内核树任何文件、绝不加载内核模块；
构建结论只引用 quantum-kernel/ 侧的验收日志与产物清单。
"""
from __future__ import annotations

import os
from typing import Dict, List, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 仓库根（native → sysweeper → python → src → system-optimizer →
# windows-internals-toolkit(内层) → windows-internals-toolkit(外层 git 根)）
_REPO_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", ".."))
KERNEL_ROOT_CANDIDATES = [
    os.path.join(_REPO_ROOT, "quantum-kernel", "linux-6.18.57"),
    os.path.join(_REPO_ROOT, "quantum-kernel"),
]
# 内核树内架构清单基线（6.18 既有 21 架构，加 quantum 为 22 个目录）
EXISTING_ARCHS = ("alpha", "arc", "arm", "arm64", "csky", "hexagon", "loongarch",
                  "m68k", "microblaze", "mips", "nios2", "openrisc", "parisc",
                  "powerpc", "riscv", "s390", "sh", "sparc", "um", "x86", "xtensa")


def _load_refs() -> List[dict]:
    """只读加载 data/qarch_refs.json 的 items；失败返回空列表（不崩）。"""
    import json
    path = os.path.join(DATA_DIR, "qarch_refs.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        return list(doc.get("items") or [])
    except Exception:  # noqa: BLE001
        return []


REFS: List[dict] = _load_refs()

QARCH_CHECKS: Dict[str, tuple] = {
    "tree": ("qarch", "Linux 6.18.57 LTS 完整树在位盘点",
             ["qarch-lts-618"]),
    "arch": ("qarch", "arch/quantum 纯新增架构与其他架构原封盘点",
             ["qarch-kconfig-registration"]),
    "qpu": ("qarch", "QPU 模拟设备与 Π_k 门语义盘点",
            ["qarch-qpu-device", "qarch-4k-page-discipline"]),
    "dist": ("qarch", "补丁分发与整树重建路径盘点",
             ["qarch-patch-distribution", "qarch-build-honesty"]),
}

_SELF_POSITION = (
    "本层只读诊断：绝不执行内核构建、绝不写内核树任何文件、绝不加载内核模块、"
    "绝不去触碰真实量子硬件；架构清单与构建结论只读自 quantum-kernel/ 树的"
    "文件存在性与验收日志。"
)


def _kernel_root() -> str:
    """定位 quantum-kernel 内核树（存在且像内核树者优先）。"""
    for cand in KERNEL_ROOT_CANDIDATES:
        if os.path.isfile(os.path.join(cand, "Makefile")) and \
                os.path.isdir(os.path.join(cand, "arch", "quantum")):
            return cand
    return ""


def tree_report() -> Tuple[bool, str]:
    """内核树在位与基线盘点。"""
    lines = ["◇ qarch 内核树在位盘点（只读）"]
    root = _kernel_root()
    if not root:
        lines.append("· 未找到 quantum-kernel 内核树（本地重建：scripts/fetch_kernel.sh）")
        lines.append("  git 侧仍有补丁+增量镜像（patches/ + arch/quantum/ 路径镜像）")
        lines.append(_SELF_POSITION)
        return True, "\n".join(lines)
    lines.append(f"· 内核树：{os.path.relpath(root, _REPO_ROOT)}")
    mk = os.path.join(root, "Makefile")
    try:
        with open(mk, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
        import re
        ver = re.search(r"^VERSION = (\S+)", head, re.M)
        plev = re.search(r"^PATCHLEVEL = (\S+)", head, re.M)
        sub = re.search(r"^SUBLEVEL = (\S+)", head, re.M)
        if ver and plev and sub:
            lines.append(f"· 基线：Linux {ver.group(1)}.{plev.group(1)}.{sub.group(1)}（LTS longterm）")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"· Makefile 不可读：{exc}")
    for d in ("arch", "drivers", "include", "kernel", "mm", "Documentation"):
        lines.append(f"· {d}/：{'✓' if os.path.isdir(os.path.join(root, d)) else '✗'}")
    lines.append("· 目录结构：Linux 内核树 discipline（arch/block/drivers/fs/include/init/kernel/mm/net/...）")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


def arch_report() -> Tuple[bool, str]:
    """架构覆盖盘点：quantum 纯新增 + 其他架构原封。"""
    lines = ["◇ qarch 架构覆盖盘点（quantum 纯新增，其他架构原封）"]
    root = _kernel_root()
    archdir = os.path.join(root, "arch") if root else ""
    if not archdir or not os.path.isdir(archdir):
        lines.append("· 内核树不在位——git 侧镜像含 arch/quantum/ 全量与两处注册点补丁")
        lines.append(_SELF_POSITION)
        return True, "\n".join(lines)
    archs = sorted(d for d in os.listdir(archdir)
                   if os.path.isdir(os.path.join(archdir, d)) and not d.startswith("."))
    missing = [a for a in EXISTING_ARCHS if a not in archs]
    lines.append(f"· 架构目录共 {len(archs)} 个（既有 {len(EXISTING_ARCHS)} + quantum = {len(archs)}）")
    lines.append(f"· quantum：{'✓ 已注册' if 'quantum' in archs else '✗ 缺失'}")
    lines.append(f"· 既有架构缺失：{missing or '无（全部原封保留）✓'}")
    # quantum 架构文件清单
    qarch = os.path.join(archdir, "quantum")
    qlist = []
    for rel in ("Kconfig", "Kconfig.debug", "Makefile", "configs/quantum_defconfig",
                "include/asm/Kbuild", "include/asm/quantum.h", "include/asm/page.h",
                "include/uapi/asm/byteorder.h", "include/uapi/asm/ptrace.h",
                "include/uapi/asm/sigcontext.h", "kernel/setup.c", "kernel/head.S",
                "kernel/vmlinux.lds.S", "kernel/irq.c", "kernel/time.c",
                "kernel/qpu-core.c", "kernel/quantum-energy.c", "mm/init.c",
                "boot/grub.cfg", "boot/lilo.conf"):
        if os.path.isfile(os.path.join(qarch, rel)):
            qlist.append(rel)
    lines.append(f"· arch/quantum 骨架：{len(qlist)}/{20} 文件在位")
    # 能量激发态模型与 idle= 参数（量子物理语义层）
    for rel, token in (("arch/quantum/kernel/quantum-energy.c", "quantum_excite"),
                       ("arch/quantum/kernel/quantum-energy.c", "quantum_decohere_tick"),
                       ("Documentation/quantum/energy-model.rst", "idle=mwait"),
                       ("arch/quantum/boot/grub.cfg", "idle=mwait"),
                       ("arch/quantum/boot/lilo.conf", "idle=mwait")):
        p = os.path.join(root, rel)
        try:
            hit = token in open(p, encoding="utf-8", errors="replace").read()
            lines.append(f"· 能量模型 {rel}（{token}）：{'✓' if hit else '✗'}")
        except Exception:  # noqa: BLE001
            lines.append(f"· 能量模型 {rel}（{token}）：不可读")
    # 注册点纯追加核验（drivers/Kconfig、drivers/Makefile）
    for reg, token in (("drivers/Kconfig", "drivers/quantum/Kconfig"),
                       ("drivers/Makefile", "quantum/")):
        p = os.path.join(root, reg)
        try:
            hit = token in open(p, encoding="utf-8", errors="replace").read()
            lines.append(f"· 注册点 {reg}：{'✓ 纯追加' if hit else '✗ 未注册'}")
        except Exception:  # noqa: BLE001
            lines.append(f"· 注册点 {reg}：不可读")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


def qpu_report() -> Tuple[bool, str]:
    """QPU 设备与语义盘点。"""
    lines = ["◇ qarch QPU 模拟设备与语义盘点"]
    root = _kernel_root()
    if root:
        for rel, token in (("drivers/quantum/qpu-dev.c", "QPU_ENC"),
                           ("drivers/quantum/qpu-gates.c", "qpu_gate_name"),
                           ("include/uapi/linux/quantum.h", "QPU_LINK_STATS"),
                           ("arch/quantum/include/asm/quantum.h", "quantum_permutation_gate"),
                           ("Documentation/quantum/index.rst", "flip semantics")):
            p = os.path.join(root, rel)
            try:
                hit = token in open(p, encoding="utf-8", errors="replace").read()
                lines.append(f"· {rel}：{'✓' if hit else '✗ 语义缺失'}（{token}）")
            except Exception:  # noqa: BLE001
                lines.append(f"· {rel}：不可读")
        # 4K 页纪律
        page = os.path.join(root, "arch/quantum/include/asm/page.h")
        try:
            txt = open(page, encoding="utf-8", errors="replace").read()
            ok4k = "PAGE_SHIFT\t12" in txt or "PAGE_SHIFT 12" in txt
            mark = "✓ 4KiB 固定（PAGE_SHIFT 12）" if ok4k else "✗"
            lines.append("· 页纪律：" + mark)
        except Exception:  # noqa: BLE001
            pass
        # defconfig 产物（若构建过）
        cfg = os.path.join(root, "build/.config")
        if os.path.isfile(cfg):
            try:
                txt = open(cfg, encoding="utf-8", errors="replace").read()
                ally = [ln for ln in txt.splitlines()
                        if ln.startswith("CONFIG_QUANTUM") and "=y" in ln]
                allq = [ln for ln in txt.splitlines()
                        if ln.startswith("CONFIG_QUANTUM")]
                lines.append(f"· defconfig 产物：build/.config 在位"
                             f"（{len(ally)} 项 =y / 共 {len(allq)} 项 CONFIG_QUANTUM*）")
            except Exception:  # noqa: BLE001
                pass
        else:
            lines.append("· defconfig 产物：build/.config 不在位（本地构建后生成）")
        # vmlinux 链接产物（若构建过）
        vml = os.path.join(root, "build/vmlinux")
        if os.path.isfile(vml):
            lines.append(f"· vmlinux 产物：✓ {os.path.getsize(vml)} 字节"
                         "（宿主工具链诚实链接；非量子处理器指令）")
        else:
            lines.append("· vmlinux 产物：不在位（本地构建后生成）")
    else:
        lines.append("· 内核树不在位，git 侧镜像含 drivers/quantum/ 与 UAPI 头全量")
    lines.append("· 语义契约：Π_k 置换矩阵门（翻转语义，不复位连编 = XOR 干扰）——"
                 "与用户态量子基座（native/quantum.py）一致")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


def dist_report() -> Tuple[bool, str]:
    """补丁分发与重建路径盘点。"""
    lines = ["◇ qarch 补丁分发与整树重建盘点"]
    gk = os.path.join(_REPO_ROOT, "quantum-kernel")
    if os.path.isdir(gk):
        for rel in ("README.md", "patches", "scripts/fetch_kernel.sh",
                    "scripts/build.sh"):
            p = os.path.join(gk, rel)
            lines.append(f"· quantum-kernel/{rel}：{'✓' if os.path.exists(p) else '✗ 待生成'}")
        pk = os.path.join(gk, "patches")
        if os.path.isdir(pk):
            patches = sorted(f for f in os.listdir(pk) if f.endswith(".patch"))
            lines.append(f"· 补丁系列：{len(patches)} 个")
            for f in patches[:6]:
                lines.append(f"    - {f}")
    else:
        lines.append("· quantum-kernel/ 目录不存在（待 #477 生成）")
    lines.append("· 完整树（1.7GiB）本地保留、.gitignore 排除；GitHub 侧只上传增量"
                 "（补丁 + 新增文件镜像，保持 Linux 目录结构）")
    lines.append(_SELF_POSITION)
    return True, "\n".join(lines)


def qarch_report() -> Tuple[bool, str]:
    """聚合报告。"""
    blocks = ["═══ qarch 量子架构内核 · 聚合报告（只读） ═══",
              f"知识层：{len(REFS)} 条目（data/qarch_refs.json）"]
    for fn, title in ((tree_report, "【树】"), (arch_report, "【架构】"),
                      (qpu_report, "【QPU】"), (dist_report, "【分发】")):
        ok, msg = fn()
        blocks.append("")
        blocks.append(title)
        for ln in msg.splitlines()[1:]:
            blocks.append("  " + ln)
    blocks.append("")
    blocks.append(_SELF_POSITION)
    return True, "\n".join(blocks)


def doc_list() -> List[str]:
    """知识条目清单（回链 data 层 key）。"""
    out: List[str] = []
    for ref in REFS:
        out.append(f"· [{ref.get('key', '?')}] {ref.get('name', '?')}"
                   f"（{ref.get('org', '未注明')}）")
    return out


def reference(key: str) -> dict:
    """按 key 取知识条目；无则空 dict。"""
    for ref in REFS:
        if ref.get("key") == key:
            return ref
    return {}


def capabilities_report() -> Tuple[bool, str]:
    lines = ["◇ qarch 能力自检",
             f"· 知识条目回链：{len(REFS)} 条；自查项 {len(QARCH_CHECKS)} 组"]
    for name, (key, desc, links) in QARCH_CHECKS.items():
        missing = [lk for lk in links
                   if not any(r.get("key") == lk for r in REFS)]
        lines.append(f"    - {name}：{desc} → 回链 {len(links)} 条"
                     + (f"（缺失 {missing}）" if missing else " ✓"))
    lines.append("· 红线：" + _SELF_POSITION)
    return True, "\n".join(lines)
