#!/usr/bin/env python3
"""quantum-kernel/scripts/gen_version_patch.py — 为指定 LTS 版本生成量子架构专属补丁。

背景：patches/0001-quantum-architecture-v1.patch 针对 6.18.57 生成。应用到其他
LTS 分支时，大部分新增文件段可跨版本复用，但以下三类必须按目标版本处理：

1. drivers/Kconfig、drivers/Makefile 与 Documentation/index.rst 三个「既有文件
   追加」hunk 的上下文随版本漂移（各分支 endmenu 前最后一项不同、index.rst
   头部条目增减），按目标版本真实上下文重建；
2. arch/quantum/include/asm/Kbuild 的 generic-y 全集需与目标版本 asm-generic
   实有头取交集（fprobe.h 于 6.13 引入等，旧分支没有）；
3. 量子架构自身文件对 6.13+ 内核面的依赖需按旧分支形态改写
   （page_to_phys/mk_pte/__pgd_alloc/atomic xchg·cmpxchg 原语、
   kernel/Makefile head.o 双链、traps.c trap_init、process.c
   pm_power_off 等，详见 adapt_new_file_section 的适配点清单）。

用法：
    python3 gen_version_patch.py <版本号> <源码树路径> [输出补丁路径]

产物：零 fuzz、零失败的版本专属补丁（a/ b/ 风格，patch -p1 与 git apply 通用）。
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATCH = HERE.parent / "patches" / "0001-quantum-architecture-v1.patch"
BASE_TREE = HERE.parent / "linux-6.18.57"

# 各既有文件的新增行（与 0001 一致，内容不随版本变化）
KCONFIG_ADD = 'source "drivers/quantum/Kconfig"'
MAKEFILE_ADD = "obj-$(CONFIG_QUANTUM_QPU_DEV)\t+= quantum/"

# arch/quantum/include/asm/Kbuild 中与版本无关的 bespoke 段（古老头，各版本都有）
KBUILD_BESPOKE = """# SPDX-License-Identifier: GPL-2.0
# Generic-y forwarding for the quantum architecture: reuse asm-generic
# wherever the emulated architecture has no bespoke hardware semantics.
generic-y += extable.h
generic-y += mcs_spinlock.h
generic-y += parport.h
generic-y += ring_buffer.h
generic-y += mm_hooks.h
generic-y += agp.h
generic-y += error-injection.h
generic-y += hugetlb.h
generic-y += iomap.h
generic-y += spinlock.h
generic-y += spinlock_types.h
generic-y += statfs.h
generic-y += tlb.h
generic-y += string.h
"""


def split_sections(text: str):
    """把 0001 补丁按文件切成有序段：(目标路径, 段文本)。

    注意：0001 由两次 diff 拼接而成——新增文件段带 ``diff --color`` 行，
    3 个既有文件段（Documentation/index.rst、drivers/Kconfig、drivers/Makefile）
    只有 ``--- /tmp/kbase/...`` 行。因此以 ``---`` 行作为段边界最稳。
    """
    lines = text.splitlines(keepends=True)
    sections = []
    cur_name, cur = None, []
    for ln in lines:
        m = re.match(r"--- /tmp/kbase/linux-[\d.]+/(\S+)", ln)
        if m:
            if cur_name is not None:
                sections.append((cur_name, cur))
            cur_name = m.group(1)
            cur = [ln]
        elif cur_name is not None:
            cur.append(ln)
    if cur_name is not None:
        sections.append((cur_name, cur))
    return sections


def rewrite_header(section_lines, path: str):
    """把 /tmp/kbase 风格段改写为标准 unified 段（--- a/X +++ b/X，新文件用 /dev/null）。

    段首可能带 ``diff --color ...`` 行（新增文件段）或什么都没有（既有文件段）。
    不输出 ``diff --git`` 行——纯 unified 格式对 ``patch -p1`` 与 ``git apply``
    都最宽容（git apply 遇到 ``diff --git`` 会按 git 语义要求 new file mode 等标记）。
    """
    out = []
    is_new = any(l.startswith("--- ") and "\t1970-01-01" in l for l in section_lines)
    for ln in section_lines:
        if ln.startswith("diff --color"):
            continue
        if ln.startswith("--- "):
            out.append("--- /dev/null\n" if is_new else f"--- a/{path}\n")
        elif ln.startswith("+++ "):
            out.append(f"+++ b/{path}\n")
        else:
            out.append(ln)
    return out


def make_hunk(path: str, old_lines, new_lines) -> list:
    """用 difflib 生成标准 unified hunk（3 行上下文，纯 unified 段头）。"""
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="\n", n=3))
    body = [ln if ln.endswith("\n") else ln + "\n" for ln in diff]
    # unified_diff 输出 '--- \n+++ \n@@' 前两行无文件名，替换为标准头
    body = [ln for ln in body if not ln.startswith(("--- ", "+++ "))]
    return [f"--- a/{path}\n", f"+++ b/{path}\n"] + body


def gen_new_file_section(path: str, content_lines) -> list:
    """生成新文件段（--- /dev/null，@@ -0,0 +1,N @@ 全新增行）。

    行数按**物理行**计且逐物理行加 '+' 前缀：元素可能含内嵌换行
    （如 gen_kbuild_hunk 的 "\n# ──...\n" 分隔元素），若按元素整体加前缀，
    第二段起会变成无前缀裸行——GNU patch 宽容放过，但 git apply 直接报
    "corrupt patch"（#660 实测：6.12 补丁 Kbuild 段中文注释行裸奔）。
    """
    phys = []
    for ln in content_lines:
        parts = ln.splitlines(keepends=True) or [ln]
        for sub in parts:
            phys.append("+" + sub if sub.endswith("\n") else "+" + sub + "\n")
    n = len(phys)
    out = [f"--- /dev/null\n", f"+++ b/{path}\n", f"@@ -0,0 +1,{n} @@\n"]
    out.extend(phys)
    return out


def gen_kbuild_hunk(tree: Path) -> tuple:
    """arch/quantum/include/asm/Kbuild：按目标版本 asm-generic 实际头文件重建 generic-y。

    6.18 的 Kbuild 第二块列了 asm-generic 全集；旧分支没有其中部分头
    （如 fprobe.h 于 6.13 引入、codetag.lds.h 于 6.11 引入），
    generic-y 指向不存在的头会让构建在 wrapper 生成阶段直接失败
    （No rule to make target .../generated/asm/fprobe.h）。
    做法：bespoke 段原样保留；全集段取 6.18 清单 ∩ 该版本 asm-generic 实有头。
    该文件在目标版本中不存在，产出**新文件段**。
    """
    base_kbuild = BASE_TREE / "arch" / "quantum" / "include" / "asm" / "Kbuild"
    base_lines = base_kbuild.read_text(encoding="utf-8").splitlines()
    bespoke_set = {x.split()[2] for x in KBUILD_BESPOKE.splitlines()
                   if x.startswith("generic-y")}
    full_list = [ln.split("+=")[1].strip() for ln in base_lines
                 if ln.strip().startswith("generic-y +=")
                 and ln.split("+=")[1].strip() not in bespoke_set]
    avail = {p.name for p in (tree / "include" / "asm-generic").glob("*.h")}
    avail |= {p.name for p in (tree / "include" / "asm-generic").glob("*.lds.h")}
    kept = [h for h in full_list if h in avail]
    dropped = [h for h in full_list if h not in avail]
    new = KBUILD_BESPOKE.splitlines(keepends=True)
    new.append(f"\n# ── asm-generic 转发（按本版本 asm-generic 实有头取交集；"
               f"相对 6.18 清单略去 {len(dropped)} 个本版本不存在的头）──\n")
    for h in kept:
        new.append(f"generic-y += {h}\n")
    return gen_new_file_section("arch/quantum/include/asm/Kbuild", new), dropped


def _insert_before(body, anchor, new_lines):
    """在首个含 anchor 的行前插入 new_lines（元素均带行尾 \n）。"""
    for i, ln in enumerate(body):
        if anchor in ln:
            return body[:i] + new_lines + body[i:]
    raise SystemExit(f"!! 适配锚点未找到：{anchor}")


def _append_before_final_endif(body, new_lines):
    """在文件末尾第一个 #endif 行前插入（用于原子头等尾部追加）。"""
    for i in range(len(body) - 1, -1, -1):
        if body[i].startswith("#endif"):
            return body[:i] + new_lines + body[i:]
    return body + new_lines


def _replace_function(body, signature, new_lines):
    """把「签名行 + 其上紧邻注释块 + 函数体到下一个行首 }」整体替换。"""
    for i, ln in enumerate(body):
        if signature in ln:
            start = i
            while start > 0 and body[start - 1].lstrip().startswith(("*", "/*")):
                start -= 1
            for j in range(i + 1, len(body)):
                if body[j].rstrip("\n") == "}":
                    return body[:start] + new_lines + body[j + 1:]
    raise SystemExit(f"!! 待替换函数未找到：{signature}")


def _remove_function(body, signature):
    """删除「签名行 + 函数体到下一个行首 }」（连同紧随其后的空行）。

    用于 6.1/5.15：回退层 atomic-arch-fallback.h 以 #ifndef 守卫提供同名
    static inline 函数——守卫只拦宏定义，拦不住函数，与 quantum 自带的
    同名 static inline 构成重定义。回退层版本语义与本架构实现一致
    （inc_return→add_return(1)、64 位 read/set acquire/release→smp_*），
    直接删除本架构定义、交由回退层提供。
    """
    for i, ln in enumerate(body):
        if signature in ln:
            for j in range(i + 1, len(body)):
                if body[j].rstrip("\n") == "}":
                    end = j + 1
                    if end < len(body) and body[end].strip() == "":
                        end += 1
                    return body[:i] + body[end:]
    raise SystemExit(f"!! 待删除函数未找到：{signature}")


def adapt_new_file_section(path: str, sec_lines, tree: Path, branch: int) -> list:
    """按目标版本改写新文件段内容（保留为 --- /dev/null 新文件段）。

    适配点均为「6.18 依赖的新内核面在旧分支缺失或形态不同」：

    ================== 适配点 ==================
    page.h       ≤6.12  asm-generic/memory_model.h 无 page_to_phys → arch 自补
    processor.h          struct task_struct 前置声明（否则落入参数作用域，
                        与 linux/sched.h 真实类型冲突：__get_wchan）
    irq.h                struct seq_file 前置声明（同理：arch_show_interrupts）
    pgtable.h    ≤6.12  mk_pte 由 arch 提供（6.13+ 起 include/linux/mm.h 通用）
    pgalloc.h    6.12   __pgd_alloc 自补（pagetable_alloc_noprof ptdesc 路径）
                 6.6    同上（pagetable_alloc ptdesc 路径）
                 ≤6.1   无 ptdesc：get_zeroed_page 整页分配（配对 free_page）
    atomic.h     6.1/   追加 arch_atomic_{,64}_xchg / arch_atomic{,64}_cmpxchg
                 5.15   （6.12+ 回退层有 defined() 守卫可自行派生）；并删除
                        本架构自带的 6 个同名 static inline——回退层 #ifndef
                        守卫只拦宏、拦不住函数，会重定义（其版本语义一致：
                        inc_return=add_return(1)、64 位 acquire/release=smp_*）
                 5.10   回退层把 arch_atomic_* 无条件别名到 generic 名：以
                        generic 名提供完整 plain API（read/set/add/add_return/
                        fetch_add/sub/sub_return/fetch_sub/and/fetch_and/or/
                        fetch_or/xor/fetch_xor ×32/64 位 + xchg/cmpxchg）；
                        inc/dec/*_return 派生、andnot 及各 acquire/release/
                        relaxed/try_cmpxchg 变体由回退层自备、不得提供；
                        末尾 #undef 本头 19 个 arch_atomic* 宏，避免回退层
                        再别名时触发 redefined 警告
    cache.h     5.15/   删 ARCH_KMALLOC_MINALIGN 自定义：旧 slab.h 无守卫，
                 5.10   #if defined(ARCH_DMA_MINALIGN) && >8 两分支都定义它，
                        与本架构同值定义构成 redefined（-Werror 报错）；删后
                        由 ARCH_DMA_MINALIGN 推导，值不变（均为 64）
    pgtable.h   6.1    置 __HAVE_ARCH_PTE_SWP_EXCLUSIVE：6.1 通用层在
                        #ifndef 该宏下自带三个恒等 swp 实现，与本架构定义
                        重定义；置宏声明自备、保留排他位记账（5.15/5.10
                        通用层无此组函数，无需置）
                6.1/   pte_mkwrite 无 vma→novma 拆分（6.3 起通用层才包装
                 5.15/ 2 参数版），通用头不提供 1 参数版，而 mm.h 的
                 5.10   maybe_mkwrite 直接调用——arch 自备转授 novma
    cmpxchg.h   5.10   未定义 ARCH_ATOMIC → linux/atomic.h 走 atomic-fallback
                        分支：该头把 xchg_relaxed/acquire/release 直接别名到
                        裸 xchg、cmpxchg* 同（假设 arch 自备裸名），且 llist.h
                        的 llist_del_all 直接用裸 xchg（6.1 起改 try_cmpxchg
                        且由 atomic-instrumented 提供裸名）。补 xchg/cmpxchg/
                        cmpxchg64 三个裸名转授 arch_* 实现
    """
    # 取出段体（@@ 之后的行），去掉行首 '+'
    body = []
    in_hunk = False
    for ln in sec_lines:
        if ln.startswith("@@"):
            in_hunk = True
            continue
        if in_hunk and ln.startswith("+"):
            body.append(ln[1:])

    if path == "arch/quantum/include/asm/page.h":
        mm = tree / "include" / "asm-generic" / "memory_model.h"
        if "page_to_phys" not in mm.read_text(encoding="utf-8"):
            body.append("")
            body.append("/* 旧分支（≤6.12）asm-generic/memory_model.h 无 page_to_phys；"
                        "按老内核 arch 惯例自补 */\n")
            body.append("#ifndef page_to_phys\n")
            body.append("#define page_to_phys(page)\tPFN_PHYS(page_to_pfn(page))\n")
            body.append("#endif\n")

    elif path == "arch/quantum/include/asm/processor.h":
        body = _insert_before(body, "unsigned long thread_saved_pc(", [
            "/* 旧分支：本头常先于 linux/sched.h 被 include；若 struct task_struct\n",
            " * 在此首次出现会被收进参数作用域，之后与 sched.h 的真实类型冲突\n",
            " *（__get_wchan conflicting types）。前置声明消歧。 */\n",
            "struct task_struct;\n",
            "\n",
        ])
        if branch in (15, 10):
            # 5.15/5.10 的 include/linux/sched/task.h 不声明 release_thread
            # （6.1+ 才补），而 kernel/exit.c 直接调用；补一个原型，与 process.c
            # 的定义一致。
            body = _insert_before(body, "unsigned long __get_wchan(", [
                "/* 5.15/5.10：include/linux/sched/task.h 不声明 release_thread\n",
                " *（6.1+ 才补），而 kernel/exit.c 直接调用；补原型，与 process.c\n",
                " * 的定义一致（x86 同款声明位于 arch/x86/include/asm/processor.h）。 */\n",
                "void release_thread(struct task_struct *dead_task);\n",
                "\n",
            ])
        if branch == 10:
            # 5.10 的 include/linux/sched.h 不声明 get_wchan（6.1+ 才补 extern
            # 声明），而 kernel/sched/fair.c、fs/proc/* 直接调用；补原型，与
            # process.c 末尾的同名转发定义一致。
            body = _insert_before(body, "unsigned long __get_wchan(", [
                "/* 5.10：include/linux/sched.h 不声明 get_wchan（6.1+ 才补\n",
                " * extern 声明），而 kernel/sched/fair.c、fs/proc/* 直接调用；\n",
                " * 补原型，与 process.c 末尾的同名转发定义一致。 */\n",
                "unsigned long get_wchan(struct task_struct *p);\n",
                "\n",
            ])

    elif path == "arch/quantum/include/asm/irq.h":
        body = _insert_before(body, "int arch_show_interrupts(", [
            "/* 旧分支：同理——前置声明避免 struct seq_file 落入参数作用域后与\n",
            " * linux/interrupt.h 的声明冲突（arch_show_interrupts）。 */\n",
            "struct seq_file;\n",
            "\n",
        ])

    elif path == "arch/quantum/include/asm/pgtable.h":
        body = _insert_before(body, "#define pte_pfn(pte)", [
            "/* 旧分支（≤6.12）mk_pte 由 arch 提供（6.13+ 起 include/linux/mm.h\n",
            " * 有通用实现）；按各 arch 惯例经 pfn_pte 构造。 */\n",
            "#define mk_pte(page, pgprot)\tpfn_pte(page_to_pfn(page), (pgprot))\n",
        ])
        if branch == 1:
            body = _insert_before(body, "static inline bool pte_swp_exclusive(", [
                "/* 6.1：通用层 include/linux/pgtable.h 在 #ifndef\n",
                " * __HAVE_ARCH_PTE_SWP_EXCLUSIVE 下自带三个恒等 swp 实现，\n",
                " * 与本架构定义构成重定义；置该宏声明本架构自备，保留\n",
                " * _PAGE_SWP_EXCLUSIVE 位记账语义（5.15/5.10 通用层无此组\n",
                " * 函数，无需置）。 */\n",
                "#define __HAVE_ARCH_PTE_SWP_EXCLUSIVE\n",
                "\n",
            ])
        if branch in (1, 15, 10):
            body = _insert_before(body, "pte_mkwrite 由通用头", [
                "/* 旧分支（≤6.1）pte_mkwrite 尚无 vma→novma 拆分（6.3 起通用\n",
                " * 层才包装 2 参数版），通用头也不提供 1 参数版，而 mm.h 的\n",
                " * maybe_mkwrite 直接调用 pte_mkwrite(pte)——arch 必须自备，\n",
                " * 按老内核惯例转授本架构 novma 实现。 */\n",
                "#define pte_mkwrite(pte)\tpte_mkwrite_novma(pte)\n",
                "\n",
            ])
        if branch in (1, 15, 10):
            # 旧分支（6.1/5.15/5.10）通用 include/linux/pgtable.h 不提供
            # set_pte_at（6.12+ 起才定义为 set_ptes 的 1 元封装宏）；通用层
            # 多处直接调用（pte_mkold / pte_wrprotect / 页表填充），故 arch
            # 必须自备。按老内核惯例经 set_pte 实现（mm/addr 在模拟架构无
            # 特殊语义，直接写项即可）。
            body = _insert_before(body, "#define set_pte(ptep, pte)", [
                "/* 旧分支（6.1/5.15/5.10）通用 include/linux/pgtable.h 不提供\n",
                " * set_pte_at（6.12+ 起才定义为 set_ptes 的 1 元封装宏）；通用\n",
                " * 层多处直接调用（pte_mkold/pte_wrprotect/页表填充），arch 须\n",
                " * 自备，按老内核惯例经 set_pte 实现。 */\n",
                "#ifndef set_pte_at\n",
                "#define set_pte_at(mm, addr, ptep, pte)\tset_pte(ptep, pte)\n",
                "#endif\n",
                "\n",
            ])
        if branch in (15, 10):
            # 5.15/5.10 的 mm/mmap.c 用 __P000..__S111 构造 protection_map[16]；
            # 5.10 的 mm/memory.c 还要 pmd_pgtable、mm/mmap.c 还要
            # FIRST_USER_ADDRESS，而 5.10 的通用 include/linux/pgtable.h 一个都
            # 不提供。5.15 的通用层已自备后两者（用 #ifndef 守卫避免重定义），
            # 仅缺 __P000 组。6.1+ 通用层改走其他路径不再引用 __P000，且
            # FIRST_USER_ADDRESS/pmd_pgtable 也由通用层自备——故统一以守卫补齐，
            # 缺失时才生效（模拟架构保护位纯记账，全部映射至既有 PAGE_* 面）。
            body = _append_before_final_endif(body, [
                "\n",
                "/* 旧分支兜底：5.10 通用 include/linux/pgtable.h 不定义\n",
                " * FIRST_USER_ADDRESS / pmd_pgtable，且 5.15/5.10 的 mm/mmap.c\n",
                " * 用 __P000..__S111 构造 protection_map[16]；6.1+ 通用层已自备\n",
                " * 前两者且不再引用 __P000，故用 #ifndef 守卫仅在缺失时补齐。 */\n",
                "#ifndef FIRST_USER_ADDRESS\n",
                "#define FIRST_USER_ADDRESS\t0UL\n",
                "#endif\n",
                "\n",
                "#ifndef pmd_pgtable\n",
                "#define pmd_pgtable(pmd)\tpmd_page(pmd)\n",
                "#endif\n",
                "\n",
                "#ifndef __P000\n",
                "#define __P000\tPAGE_NONE\n",
                "#define __P001\tPAGE_READONLY\n",
                "#define __P010\tPAGE_COPY\n",
                "#define __P011\tPAGE_COPY\n",
                "#define __P100\tPAGE_READONLY\n",
                "#define __P101\tPAGE_READONLY\n",
                "#define __P110\tPAGE_COPY\n",
                "#define __P111\tPAGE_COPY\n",
                "#define __S000\tPAGE_NONE\n",
                "#define __S001\tPAGE_READONLY\n",
                "#define __S010\tPAGE_SHARED\n",
                "#define __S011\tPAGE_SHARED\n",
                "#define __S100\tPAGE_READONLY\n",
                "#define __S101\tPAGE_READONLY\n",
                "#define __S110\tPAGE_SHARED\n",
                "#define __S111\tPAGE_SHARED\n",
                "#endif\n",
            ])

    elif path == "arch/quantum/include/asm/cache.h" and branch in (15, 10):
        # 5.15/5.10 的 include/linux/slab.h 无 ARCH_KMALLOC_MINALIGN 守卫：
        # #if defined(ARCH_DMA_MINALIGN) && ARCH_DMA_MINALIGN > 8 的两个分支
        # 都会定义它（6.1 起才补 !defined(ARCH_KMALLOC_MINALIGN) 判断）。
        # 本架构自定义同值（L1_CACHE_BYTES=64）触发 redefined 警告，
        # -Werror 下即构建失败；删除后由 slab.h 从 ARCH_DMA_MINALIGN
        # 推导，取值不变。
        body = [ln for ln in body
                if not ln.startswith("#define ARCH_KMALLOC_MINALIGN")]

    elif path == "arch/quantum/include/asm/cmpxchg.h" and branch == 10:
        # 5.10：quantum 未定义 ARCH_ATOMIC → linux/atomic.h 取
        # linux/atomic-fallback.h 分支。该头在 #ifndef xchg_relaxed 下把
        # xchg_relaxed/acquire/release 直接别名到裸 xchg（cmpxchg* 同理），
        # 即契约假设 arch 自备裸名；llist.h 的 llist_del_all 也直接用裸
        # xchg（6.1 起改用 try_cmpxchg 且由 atomic-instrumented 插桩层
        # 提供裸名，故 6.1/5.15 无需此补）。按 arch 惯例提供三个裸名，
        # 转授 arch_* 实现（其 __typeof__ 表达式已保住指针类型）。
        body = _insert_before(body, "#endif /* __ASSEMBLY__ */", [
            "/*\n",
            " * 5.10 无 ARCH_ATOMIC 路径：atomic-fallback.h 与 llist.h 都直接\n",
            " * 使用裸 xchg()/cmpxchg()；按 arch 惯例转授本架构实现。\n",
            " */\n",
            "#define xchg(ptr, x)\t\tarch_xchg((ptr), (x))\n",
            "#define cmpxchg(ptr, o, n)\tarch_cmpxchg((ptr), (o), (n))\n",
            "#define cmpxchg64(ptr, o, n)\tarch_cmpxchg64((ptr), (o), (n))\n",
            "\n",
        ])

    elif path == "arch/quantum/include/asm/pgalloc.h":
        # 注意：branch 取自版本号第二段（6.12→12、5.15→15、5.10→10），
        # 并非按内核新旧单调——5.15 的 branch=15 反而大于 6.12 的 12。
        # 此处必须按「等于 12」精确命中 6.12，绝不能写 >=12，否则 5.15
        # 会被错误纳入 6.13+ 的 ptdesc 路径（pagetable_alloc_noprof/
        # ptdesc_address 在 5.15 不存在 → 隐式声明报错）。
        if branch == 12:
            body = _insert_before(
                body, "static inline pgd_t *pgd_alloc(struct mm_struct *mm)", [
                "/* 旧分支（≤6.12）asm-generic/pgalloc.h 不提供 __pgd_alloc（6.13+\n",
                " * 才有），按 6.18 同款 ptdesc 路径自补；6.12 起 pagetable_alloc\n",
                " * 已更名为 pagetable_alloc_noprof，且尚无 pgd ctor（6.13+ 引入）。 */\n",
                "static inline pgd_t *__pgd_alloc(struct mm_struct *mm, unsigned int order)\n",
                "{\n",
                "\tgfp_t gfp = GFP_PGTABLE_USER;\n",
                "\tstruct ptdesc *ptdesc;\n",
                "\n",
                "\tif (mm == &init_mm)\n",
                "\t\tgfp = GFP_PGTABLE_KERNEL;\n",
                "\tgfp &= ~__GFP_HIGHMEM;\n",
                "\n",
                "\tptdesc = pagetable_alloc_noprof(gfp, order);\n",
                "\tif (!ptdesc)\n",
                "\t\treturn NULL;\n",
                "\n",
                "\treturn ptdesc_address(ptdesc);\n",
                "}\n",
                "\n",
            ])
        elif branch == 6:
            body = _insert_before(
                body, "static inline pgd_t *pgd_alloc(struct mm_struct *mm)", [
                "/* 旧分支（≤6.12）asm-generic/pgalloc.h 不提供 __pgd_alloc（6.13+\n",
                " * 才有），按 6.18 同款 ptdesc 路径自补；6.6 用 pagetable_alloc\n",
                " * 原名，尚无 pgd ctor（6.13+ 引入）。 */\n",
                "static inline pgd_t *__pgd_alloc(struct mm_struct *mm, unsigned int order)\n",
                "{\n",
                "\tgfp_t gfp = GFP_PGTABLE_USER;\n",
                "\tstruct ptdesc *ptdesc;\n",
                "\n",
                "\tif (mm == &init_mm)\n",
                "\t\tgfp = GFP_PGTABLE_KERNEL;\n",
                "\tgfp &= ~__GFP_HIGHMEM;\n",
                "\n",
                "\tptdesc = pagetable_alloc(gfp, order);\n",
                "\tif (!ptdesc)\n",
                "\t\treturn NULL;\n",
                "\n",
                "\treturn ptdesc_address(ptdesc);\n",
                "}\n",
                "\n",
            ])
        else:
            body = _replace_function(
                body, "static inline pgd_t *pgd_alloc(struct mm_struct *mm)", [
                "/* 旧分支（≤6.1）asm-generic/pgalloc.h 无 ptdesc 路径（pgd_alloc 需\n",
                " * arch 自备；pgd_free 走通用 free_page）。按老内核模拟 arch 惯例\n",
                " * 整页零化分配，与 free_page 配对。 */\n",
                "static inline pgd_t *pgd_alloc(struct mm_struct *mm)\n",
                "{\n",
                "\treturn (pgd_t *)get_zeroed_page(GFP_KERNEL);\n",
                "}\n",
            ])
            # 旧分支（≤6.1）无 ptdesc：tlb_remove_ptdesc/page_ptdesc 于 6.6+
            # 才引入；__pte_free_tlb 退化为直接 pte_free（asm-generic/pgalloc.h
            # 已提供，参数即 pgtable_t）。
            for i, ln in enumerate(body):
                if ln.startswith("#define __pte_free_tlb"):
                    new_block = [
                        "/* 旧分支（≤6.1）无 ptdesc（tlb_remove_ptdesc/page_ptdesc\n",
                        " * 于 6.6+ 才引入），__pte_free_tlb 退化为直接 pte_free\n",
                        " *（asm-generic/pgalloc.h 提供）。 */\n",
                        "#define __pte_free_tlb(tlb, pte, addr) \\\n",
                        "\tpte_free((tlb)->mm, pte)\n",
                    ]
                    body = body[:i] + new_block + body[i + 2:]
                    break

    elif path == "arch/quantum/mm/init.c":
        if branch in (15, 10):
            # 旧分支（5.15/5.10）mm/mmap.c 自带 vm_get_page_prot 并调用
            # arch_vm_get_page_prot；量子须改提供后者、并移除自身的
            # vm_get_page_prot（否则与通用层构成重定义）。函数体（VMA 标志→
            # _PAGE_* 位面记账）原样保留，仅更名与导出符号对齐——这是量子
            # 正确声明自身页保护契约的移植动作，并非修当前架构。6.1+ 通用层
            # 不提供 vm_get_page_prot，故那几版保留本架构定义、无需改动。
            # 注意：adapt_new_file_section 重建 body 时已剥离行首 '+'，故此处
            # 按无 '+' 的形态匹配。
            for i, ln in enumerate(body):
                if ln.startswith("pgprot_t vm_get_page_prot("):
                    body[i] = ln.replace("vm_get_page_prot", "arch_vm_get_page_prot")
                if ln.strip() == "EXPORT_SYMBOL(vm_get_page_prot);":
                    body[i] = "EXPORT_SYMBOL(arch_vm_get_page_prot);\n"

    elif path == "arch/quantum/Kconfig" and branch == 10:
        # 5.10：include/asm-generic/uaccess.h 仍提供 static inline
        # strncpy_from_user/strnlen_user；若再选 GENERIC_STRNCPY_FROM_USER/
        # GENERIC_STRNLEN_USER 会让 lib/ 的实现与内联实现构成重定义。故 5.10
        # 不使能这俩 GENERIC_*（亦不应选与 GENERIC_STRNLEN_USER 矛盾的
        # ARCH_HAS_STRNLEN_USER），改走 asm-generic 内联实现（底层
        # __strncpy_from_user 由 asm-generic 默认提供，UACCESS_MEMCPY 直接
        # 承载）。6.x 的 asm-generic 仅 extern 声明、须由 lib/ 提供，故那些
        # 版本保留 GENERIC_* 选择，此处不改动。
        body = [ln for ln in body
                if not ln.strip().lstrip("+").strip().startswith(
                    "select GENERIC_STRNCPY_FROM_USER")
                and not ln.strip().lstrip("+").strip().startswith(
                    "select GENERIC_STRNLEN_USER")
                and not ln.strip().lstrip("+").strip().startswith(
                    "select ARCH_HAS_STRNLEN_USER")]

    elif path == "arch/quantum/kernel/Makefile" and branch in (15, 10):
        # 5.15/5.10 顶层 Makefile（5.10:1181 / 5.15 同构）：
        #   KBUILD_VMLINUX_OBJS := $(head-y) $(patsubst %/,%/built-in.a, $(core-y))
        # head.o 同时经 head-y 与 core-y→kernel/built-in.a 两路进链接，
        # quantum_start 重复定义（multiple definition of `quantum_start'）。
        # 6.1+ 顶层改为 KBUILD_VMLINUX_OBJS := ./built-in.a 单聚合，head.o
        # 必须留在 obj-y 方能进聚合。旧分支约定（x86/arm64 同款）：head.o
        # 只进 head-y，kernel/Makefile 的 obj-y 不含它（extra-y 仍构建它）。
        body = [ln.replace("obj-y := head.o ", "obj-y := ", 1)
                if ln.startswith("obj-y := head.o ") else ln
                for ln in body]

    elif path == "arch/quantum/kernel/traps.c" and branch == 10:
        # 5.10：init/main.c 无 __weak trap_init（5.15 起才补弱定义），
        # start_kernel 直接调用 trap_init()；x86 同款落点为
        # arch/x86/kernel/traps.c。模拟架构无真实陷阱初始化动作，
        # 空桩诚实满足链接契约。
        body = _append_before_final_endif(body, [
            "/* 5.10：init/main.c 无 __weak trap_init（5.15 起才有），直接调用；\n",
            " * 模拟架构无真实陷阱初始化动作，空桩诚实满足链接契约。 */\n",
            "void __init trap_init(void)\n",
            "{\n",
            "}\n",
            "\n",
        ])

    elif path == "arch/quantum/kernel/process.c":
        # 量子 process.c 按 6.18 内核面编写；旧分支的进程/线程与 core 钩子
        # 签名不同，须按目标版本改写：
        #   copy_thread  5.15/5.10 仍为 5 参数旧签名
        #                (clone_flags, sp, arg, p, stack_size)，6.1+ 起缩为
        #                2 参数 (p, kernel_clone_args)——本架构实现恒返回 0；
        #   elf_core_copy_task_fpregs  6.1/5.15/5.10 的通用 elfcore.h 已以
        #                static inline 提供 3 参数(t, regs, fpu)且无 #ifndef
        #                守卫，本架构再定义即重定义——删除本架构定义、交由通用层
        #                提供；通用层在 ELF_CORE_COPY_FPREGS 未定义时转调 arch
        #                提供的 dump_fpu（模拟架构无 FPU，桩返回 0），故一并补
        #                dump_fpu；6.12/6.6 通用层仅声明 2 参数原型、不提供定义，
        #                故那两版保留本架构定义、且无需 dump_fpu；
        #   get_wchan    5.10 通用层直接调用 get_wchan（6.1+ 起更名
        #                __get_wchan），而本架构仅实现 __get_wchan，补同名转发。
        if branch in (15, 10):
            body = _replace_function(body, "int copy_thread(struct task_struct *p,", [
                "/* 5.15/5.10：旧内核 copy_thread 为 5 参数签名\n",
                " * (clone_flags, sp, arg, p, stack_size)；模拟架构无栈帧/寄存器\n",
                " * 可复制，返回 0。 */\n",
                "int copy_thread(unsigned long clone_flags, unsigned long sp,\n",
                "\t\tunsigned long arg, struct task_struct *p,\n",
                "\t\tunsigned long stack_size)\n",
                "{\n",
                "\treturn 0;\n",
                "}\n",
            ])
        if branch in (15, 10):
            # 5.15/5.10：kernel/reboot.c 以 extern 引用 pm_power_off（6.1+ 起
            # 通用层 kernel/reboot.c 自带 __weak 定义， arch 可不提供）；按各
            # arch 惯例（arm64 同款落点：arch/arm64/kernel/process.c）由本架构
            # 提供全局钩子，NULL = 模拟架构无真实关机硬件，reboot 走默认路径。
            body = _append_before_final_endif(body, [
                "/* 5.15/5.10：kernel/reboot.c 以 extern 引用 pm_power_off（6.1+\n",
                " * 起通用层自带 __weak 定义）；按 arch 惯例由本架构提供全局钩子，\n",
                " * NULL = 模拟架构无真实关机硬件，reboot 走默认路径。 */\n",
                "void (*pm_power_off)(void);\n",
                "\n",
            ])
        if branch in (1, 15, 10):
            # 6.1/5.15/5.10：通用 include/linux/elfcore.h 已以 static inline
            # 提供 elf_core_copy_task_fpregs（3 参数 t,regs,fpu，无 #ifndef 守卫），
            # 本架构再定义即与通用层构成重定义；直接删除本架构定义、交由通用层
            # 提供（模拟架构不产出真实浮点 core 段，语义一致）。6.12/6.6 的
            # 通用层仅声明 2 参数原型、不提供定义，故那两版仍保留本架构定义。
            body = _remove_function(
                body, "int elf_core_copy_task_fpregs(struct task_struct *t, elf_fpregset_t *fpu)")
            # 通用层在 ELF_CORE_COPY_FPREGS 未定义时转调 arch 提供的 dump_fpu；
            # 量子无 FPU，桩返回 0（无浮点状态可落盘）——这是模拟架构的诚实声明，
            # 而非修当前架构。签名与通用 elfcore.h 的 extern 声明一致。用
            # _append_before_final_endif 落位，避免依赖仅分支 10 才有的
            # get_wchan 锚点。
            body = _append_before_final_endif(body, [
                "/* 6.1/5.15/5.10：通用 elfcore.h 在 ELF_CORE_COPY_FPREGS 未定义\n",
                " * 时转调 arch 提供的 dump_fpu；量子无 FPU，桩返回 0（无浮点\n",
                " * 状态可落盘），是模拟架构的诚实声明，并非修当前架构。 */\n",
                "int dump_fpu(struct pt_regs *regs, elf_fpregset_t *fpu)\n",
                "{\n",
                "\treturn 0;\n",
                "}\n",
                "\n",
            ])
        if branch == 10:
            body = _append_before_final_endif(body, [
                "/* 5.10：通用层（kernel/sched/fair.c、fs/proc/*）调用 get_wchan，\n",
                " * 而 6.18 起该接口更名为 __get_wchan；本架构仅实现 __get_wchan，\n",
                " * 这里补一个同名转发。 */\n",
                "unsigned long get_wchan(struct task_struct *p)\n",
                "{\n",
                "\treturn __get_wchan(p);\n",
                "}\n",
                "\n",
            ])

    elif path == "arch/quantum/include/asm/atomic.h" and branch in (1, 15):
        # 回退层以 #ifndef 守卫提供这 6 个同名 static inline（守卫只拦宏、
        # 拦不住函数 → 重定义）。回退层版本语义与本架构实现一致
        #（inc_return=add_return(1)、64 位 acquire/release=smp_*），
        # 删除本架构定义、交由回退层提供。先删后追加：_remove_function
        # 会吞掉函数后的空行，若先追加，dec_return 后的空行被吞会挤掉
        # 追加块与上一个 #define 之间的分隔空行。
        for sig in (
            "static __always_inline int arch_atomic_inc_return(atomic_t *v)",
            "static __always_inline int arch_atomic_dec_return(atomic_t *v)",
            "static __always_inline s64 arch_atomic64_read_acquire(const atomic64_t *v)",
            "static __always_inline void arch_atomic64_set_release(atomic64_t *v, s64 i)",
            "static __always_inline s64 arch_atomic64_inc_return(atomic64_t *v)",
            "static __always_inline s64 arch_atomic64_dec_return(atomic64_t *v)",
        ):
            body = _remove_function(body, sig)
        body = _append_before_final_endif(body, [
            "/* 旧分支（6.1/5.15）atomic 回退层要求 arch 提供 xchg/cmpxchg 原语\n",
            " *（6.12+ 起回退层带 defined() 守卫可自行派生）；单核模拟语义与\n",
            " * 本文件其余 ops 一致：读-判-写。 */\n",
            "static __always_inline int arch_atomic_xchg(atomic_t *v, int i)\n",
            "{\n",
            "\treturn arch_xchg(&(v)->counter, (i));\n",
            "}\n",
            "\n",
            "static __always_inline int arch_atomic_cmpxchg(atomic_t *v,\n",
            "\t\t\t\t     int old, int new)\n",
            "{\n",
            "\tint r = arch_atomic_read(v);\n",
            "\n",
            "\tif (r == old)\n",
            "\t\tarch_atomic_set(v, new);\n",
            "\treturn r;\n",
            "}\n",
            "\n",
            "static __always_inline s64 arch_atomic64_xchg(atomic64_t *v, s64 i)\n",
            "{\n",
            "\treturn arch_xchg(&(v)->counter, (i));\n",
            "}\n",
            "\n",
            "static __always_inline s64 arch_atomic64_cmpxchg(atomic64_t *v,\n",
            "\t\t\t\t\t     s64 old, s64 new)\n",
            "{\n",
            "\ts64 r = arch_atomic64_read(v);\n",
            "\n",
            "\tif (r == old)\n",
            "\t\tarch_atomic64_set(v, new);\n",
            "\treturn r;\n",
            "}\n",
            "\n",
        ])

    elif path == "arch/quantum/include/asm/atomic.h" and branch == 10:
        # 5.10 回退层契约（include/linux/atomic-fallback.h，已逐条核对）：
        #  1. "#define arch_atomic_X atomic_X" 为无条件别名 → plain 名
        #     （read/set/add/add_return/fetch_add/sub/sub_return/fetch_sub/
        #     and/fetch_and/or/fetch_or/xor/fetch_xor，32/64 位共 28 个）
        #     在回退层无 #ifndef 守卫，必须由 arch 以 generic 名提供；
        #  2. inc/dec/inc_return/dec_return/fetch_inc/fetch_dec/andnot/
        #     fetch_andnot 及全部 acquire/release/relaxed/try_cmpxchg 变体
        #     由回退层 #ifndef 自备——arch 提供即重定义，故不得提供；
        #  3. xchg/cmpxchg 的回退层定义位于 "#ifndef atomic_xchg_relaxed"
        #     的 #else 分支内：本架构不定义 relaxed 变体，该分支不进，
        #     以 generic 名提供不会撞车。
        # 转发体在解析期展开（回退层的别名 #define 发生在本头之后），语义与
        # 本文件其余 ops 一致（单核模拟：读-判-写）。
        plain = []
        for pfx, ty, aty in (("atomic_", "int", "atomic_t"),
                             ("atomic64_", "s64", "atomic64_t")):
            apfx = "arch_" + pfx
            plain += [
                (pfx + "read", ty, "const " + aty + " *v", apfx + "read(v)"),
                (pfx + "set", "void", aty + " *v, " + ty + " i",
                 apfx + "set(v, i)"),
                (pfx + "add", "void", ty + " i, " + aty + " *v",
                 apfx + "add(i, v)"),
                (pfx + "add_return", ty, ty + " i, " + aty + " *v",
                 apfx + "add_return(i, v)"),
                (pfx + "fetch_add", ty, ty + " i, " + aty + " *v",
                 apfx + "fetch_add(i, v)"),
                (pfx + "sub", "void", ty + " i, " + aty + " *v",
                 apfx + "sub(i, v)"),
                (pfx + "sub_return", ty, ty + " i, " + aty + " *v",
                 apfx + "sub_return(i, v)"),
                (pfx + "fetch_sub", ty, ty + " i, " + aty + " *v",
                 apfx + "fetch_sub(i, v)"),
                (pfx + "and", "void", ty + " i, " + aty + " *v",
                 apfx + "and(i, v)"),
                (pfx + "fetch_and", ty, ty + " i, " + aty + " *v",
                 apfx + "fetch_and(i, v)"),
                (pfx + "or", "void", ty + " i, " + aty + " *v",
                 apfx + "or(i, v)"),
                (pfx + "fetch_or", ty, ty + " i, " + aty + " *v",
                 apfx + "fetch_or(i, v)"),
                (pfx + "xor", "void", ty + " i, " + aty + " *v",
                 apfx + "xor(i, v)"),
                (pfx + "fetch_xor", ty, ty + " i, " + aty + " *v",
                 apfx + "fetch_xor(i, v)"),
            ]
        block = [
            "/* 5.10 回退层契约（atomic-fallback.h，逐条核对）：arch_atomic_* 被\n",
            " * 无条件别名到 generic 名，plain API 无守卫须由 arch 提供；派生名\n",
            " *（inc/dec/andnot 及全部 acquire/release/relaxed/try_cmpxchg 变体）\n",
            " * 由回退层自备、arch 不得提供；xchg/cmpxchg 的回退层定义在\n",
            " * #ifndef atomic_xchg_relaxed 的 #else 分支内，本架构不定义 relaxed\n",
            " * 变体故该分支不进、不会撞车。以下转发体解析期展开，语义同本文件\n",
            " * 其余 ops（单核模拟：读-判-写）。 */\n",
        ]
        for name, ret, params, call in plain:
            block.append("static __always_inline " + ret + " " + name +
                         "(" + params + ")\n")
            block.append("{\n")
            block.append("\t" + call + ";\n" if ret == "void"
                         else "\treturn " + call + ";\n")
            block.append("}\n")
            block.append("\n")
        block += [
            "static __always_inline int atomic_xchg(atomic_t *v, int i)\n",
            "{\n",
            "\treturn arch_xchg(&(v)->counter, (i));\n",
            "}\n",
            "\n",
            "static __always_inline int atomic_cmpxchg(atomic_t *v,\n",
            "\t\t\t\t     int old, int new)\n",
            "{\n",
            "\tint r = arch_atomic_read(v);\n",
            "\n",
            "\tif (r == old)\n",
            "\t\tarch_atomic_set(v, new);\n",
            "\treturn r;\n",
            "}\n",
            "\n",
            "static __always_inline s64 atomic64_xchg(atomic64_t *v, s64 i)\n",
            "{\n",
            "\treturn arch_xchg(&(v)->counter, (i));\n",
            "}\n",
            "\n",
            "static __always_inline s64 atomic64_cmpxchg(atomic64_t *v,\n",
            "\t\t\t\t      s64 old, s64 new)\n",
            "{\n",
            "\ts64 r = arch_atomic64_read(v);\n",
            "\n",
            "\tif (r == old)\n",
            "\t\tarch_atomic64_set(v, new);\n",
            "\treturn r;\n",
            "}\n",
            "\n",
            "/* 回退层随后会把 arch_atomic_* 再次别名到 generic 名；先 undef 本\n",
            " * 头的 arch_atomic* 宏（含 14 个自标记宏），避免 redefined 警告。\n",
            " * undef 之后回退层的别名仍使 arch_atomic_* 调用点经 generic 名落到\n",
            " * 上面的实现，后续使用者无感。 */\n",
        ]
        for m in ("arch_atomic_read", "arch_atomic_set",
                  "arch_atomic_set_release",
                  "arch_atomic_add_return", "arch_atomic_sub_return",
                  "arch_atomic_fetch_add", "arch_atomic_fetch_sub",
                  "arch_atomic_fetch_and", "arch_atomic_fetch_or",
                  "arch_atomic_fetch_xor",
                  "arch_atomic64_read", "arch_atomic64_set",
                  "arch_atomic64_add_return", "arch_atomic64_sub_return",
                  "arch_atomic64_fetch_add", "arch_atomic64_fetch_sub",
                  "arch_atomic64_fetch_and", "arch_atomic64_fetch_or",
                  "arch_atomic64_fetch_xor"):
            block.append("#undef " + m + "\n")
        block.append("\n")
        body = _append_before_final_endif(body, block)

    return gen_new_file_section(path, body)


def gen_kconfig_hunk(tree: Path, ver: str) -> list:
    """drivers/Kconfig：在 endmenu 前插入 quantum source（按该版本真实上下文）。"""
    p = tree / "drivers" / "Kconfig"
    old = p.read_text(encoding="utf-8").splitlines(keepends=True)
    # 找最后一个 endmenu 行，插到它前面
    idx = max(i for i, ln in enumerate(old) if ln.strip() == "endmenu")
    new = old[:idx] + [KCONFIG_ADD + "\n", "\n"] + old[idx:]
    return make_hunk("drivers/Kconfig", old, new)


def gen_makefile_hunk(tree: Path, ver: str) -> list:
    """drivers/Makefile：在文件末尾追加 quantum obj 行（按该版本真实上下文）。"""
    p = tree / "drivers" / "Makefile"
    old = p.read_text(encoding="utf-8").splitlines(keepends=True)
    new = old + [MAKEFILE_ADD + "\n"]
    return make_hunk("drivers/Makefile", old, new)


def gen_index_hunk(tree: Path) -> list:
    """Documentation/index.rst：在文末 genindex 行后追加 quantum 索引条目。

    0001 的该 hunk 按 6.18 上下文生成；旧分支 index.rst 头部条目增减使
    行号漂移（5.10 相差 81 行），直搬会带 offset。各版本均以
    ``* :ref:`genindex``` 收尾，按目标树真实尾部重建，与其他 hunk
    一致保持零 fuzz、零 offset。
    """
    p = tree / "Documentation" / "index.rst"
    old = p.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = max(i for i, ln in enumerate(old) if "* :ref:`genindex`" in ln)
    add = [
        "\n",
        ".. List also in architecture docs\n",
        "   :maxdepth: 1\n",
        "\n",
        "   quantum/index\n",
    ]
    new = old[:idx + 1] + add + old[idx + 1:]
    return make_hunk("Documentation/index.rst", old, new)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    ver, tree = argv[1], Path(argv[2])
    branch = int(ver.split(".")[1])  # 6.12→12、6.6→6、6.1→1、5.15→15、5.10→10
    out_path = Path(argv[3]) if len(argv) > 3 else (
        HERE.parent / "patches" / f"0001-quantum-architecture-v1-{ver}.patch")
    base = BASE_PATCH.read_text(encoding="utf-8")
    sections = split_sections(base)
    result = []
    replaced = set()
    all_dropped = []
    # 需按目标版本改写内容的新文件段（见 adapt_new_file_section 文档）
    adaptable = {
        "arch/quantum/include/asm/page.h",
        "arch/quantum/include/asm/processor.h",
        "arch/quantum/include/asm/irq.h",
        "arch/quantum/include/asm/pgtable.h",
        "arch/quantum/include/asm/pgalloc.h",
        "arch/quantum/include/asm/atomic.h",
        "arch/quantum/include/asm/cache.h",
        "arch/quantum/include/asm/cmpxchg.h",
        "arch/quantum/kernel/process.c",
        "arch/quantum/kernel/Makefile",
        "arch/quantum/kernel/traps.c",
        "arch/quantum/mm/init.c",
        "arch/quantum/Kconfig",
    }
    for name, sec in sections:
        if name == "drivers/Kconfig":
            result += gen_kconfig_hunk(tree, ver)
            replaced.add("drivers/Kconfig")
        elif name == "drivers/Makefile":
            result += gen_makefile_hunk(tree, ver)
            replaced.add("drivers/Makefile")
        elif name == "Documentation/index.rst":
            result += gen_index_hunk(tree)
            replaced.add("Documentation/index.rst")
        elif name == "arch/quantum/include/asm/Kbuild":
            hunk, dropped = gen_kbuild_hunk(tree)
            result += hunk
            replaced.add("arch/quantum/include/asm/Kbuild")
            all_dropped = dropped
        elif name in adaptable:
            result += adapt_new_file_section(name, sec, tree, branch)
        else:
            result += rewrite_header(sec, name)
    missing = {"drivers/Kconfig", "drivers/Makefile",
               "Documentation/index.rst",
               "arch/quantum/include/asm/Kbuild"} - replaced
    if missing:
        print(f"!! 基线补丁缺少段：{missing}", file=sys.stderr)
        return 1
    out_path.write_text("".join(result), encoding="utf-8")
    print(f"→ {out_path}（{len(result)} 行；drivers/Kconfig、drivers/Makefile、"
          f"Documentation/index.rst 与 asm/Kbuild 已按 linux-{ver} 重建，"
          f"{len(adaptable)} 个量子头文件段按 {branch}.x 内核面适配，其余 "
          f"{len(sections) - 4 - len(adaptable)} 段自 0001 复用；Kbuild 略去本版本"
          f"不存在的 asm-generic 头 {len(all_dropped)} 个："
          f"{', '.join(all_dropped) if all_dropped else '无'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
