#!/usr/bin/env python3
"""重建 patches/0001-quantum-architecture-v1.patch —— 从当前 6.18.57 源码树全量重生。

背景：源码树在 6.18.57 验收构建后又有修订（cmpxchg.h local 变体、Kbuild 清理、
pgtable.h 去重定义、processor.h 前置声明、setup.h early_qpu_setup、syscall.h
SYSCALL_MAX_ARGS、process.c 去 NULL memset、setup.c cpu.h、qpu-gates.c 头包含），
旧基础补丁未跟随，导致版本补丁内容过期。本脚本以源码树为权威重新生成基础补丁。

格式与旧补丁一致（gen_version_patch.py 的 split_sections 依赖）：
  - 新文件段：diff --color 行 + `--- /tmp/kbase/linux-6.18.57/<path>`（epoch 时间戳，
    标识新文件）+ `+++ linux-6.18.57/<path>` + `@@ -0,0 +1,N @@` + `+` 行；
  - 3 个既有文件段（Documentation/index.rst、drivers/Kconfig、drivers/Makefile）
    从旧补丁原样复用（已验证与当前树一致，均为 append-only 且未再变动）。
段序沿用旧补丁，新文件 arch/quantum/kernel/screen_info.c 插入 kernel/ 字母序位置。
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QK = HERE.parent
SRC = QK / "linux-6.18.57"
OLD_PATCH = QK / "patches" / "0001-quantum-architecture-v1.patch"
OUT = QK / "patches" / "0001-quantum-architecture-v1.patch"

EXISTING = {"Documentation/index.rst", "drivers/Kconfig", "drivers/Makefile"}


def fmt_ts(stat) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(stat.st_mtime).astimezone()
    ns = int((stat.st_mtime % 1) * 1e9)
    return dt.strftime("%Y-%m-%d %H:%M:%S") + f".{ns:09d} " + dt.strftime("%z")[:3] + ":" + dt.strftime("%z")[3:]


def _parse(path):
    """按段边界切分补丁文件：{path: 段文本}。段从其 `---` 行开始。

    幂等性修复（#654 实测发现）：段尾可能残留下一段的 `diff --color` 头
    （既往插入 bug 的产物，每次重生会 +1 行无限累积）。这些行出现在本段
    `---` 行之前、属于下一段的头部，解析时一律剔除——修补内容行均以
    `+`/`-`/` ` 开头，不会误伤。
    """
    text = path.read_text(encoding="utf-8")
    secs = {}
    cur_name, cur = None, []
    for ln in text.splitlines(keepends=True):
        if ln.startswith("--- /tmp/kbase/linux-6.18.57/"):
            if cur_name is not None:
                secs[cur_name] = "".join(cur)
            cur_name = ln.split("linux-6.18.57/", 1)[1].split("\t", 1)[0].rstrip()
            cur = [ln]
        elif cur_name is not None:
            if ln.startswith("diff --color"):
                continue
            cur.append(ln)
    if cur_name is not None:
        secs[cur_name] = "".join(cur)
    return secs


def old_sections():
    """旧补丁切分（原样复用既有文件段）。"""
    return _parse(OLD_PATCH)


def new_file_section(path: str) -> str:
    p = SRC / path
    data = p.read_bytes()
    text = data.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if not lines:
        raise SystemExit(f"!! 空文件不支持：{path}")
    for ln in lines:
        if not ln.endswith("\n"):
            raise SystemExit(f"!! 文件末尾无换行（diff 需 \\ No newline 标记）：{path}")
    out = []
    out.append("diff --color --color -ruN '--exclude=build' '--exclude=build-x86' "
               f"/tmp/kbase/linux-6.18.57/{path} linux-6.18.57/{path}\n")
    out.append(f"--- /tmp/kbase/linux-6.18.57/{path}\t1970-01-01 08:00:00.000000000 +0800\n")
    out.append(f"+++ linux-6.18.57/{path}\t{fmt_ts(p.stat())}\n")
    out.append(f"@@ -0,0 +1,{len(lines)} @@\n")
    out.extend("+" + ln for ln in lines)
    return "".join(out)


def main():
    old = old_sections()
    order = [l.strip() for l in OLD_PATCH.read_text(encoding="utf-8").splitlines()
             if l.startswith("--- /tmp/kbase/linux-6.18.57/")]
    order = [l.split("linux-6.18.57/", 1)[1].split("\t", 1)[0].rstrip() for l in order]
    # 去重（保留首次出现）：旧补丁若已残留重复段（上次运行的插入bug），
    # 以本次为准清掉，保证补丁每文件恰好一段。
    seen = set()
    order = [p for p in order if not (p in seen or seen.add(p))]
    # 新文件插入 kernel/ 字母序位置（quantum-energy.c 与 setup.c 之间）；
    # 幂等：补丁里已存在该段时不再插（本脚本会重复运行，旧补丁即上一次产物）。
    new_file = "arch/quantum/kernel/screen_info.c"
    if new_file not in order:
        idx = order.index("arch/quantum/kernel/setup.c")
        order.insert(idx, new_file)

    # 补齐源码树里有、旧补丁没有段的新文件（如 qpu-gates.h：旧补丁生成后
    # 才新建，只重生旧段会静默漏掉它，而 qpu-gates.c 已 #include 它）。
    # 按路径字典序插入到首个大于它的段之前，保持同目录相邻。
    src_files = set()
    for sub in ("arch/quantum", "drivers/quantum", "Documentation/quantum"):
        src_files |= {str(p.relative_to(SRC)) for p in (SRC / sub).rglob("*")
                      if p.is_file()}
    missing = sorted(src_files - set(order))
    for path in missing:
        pos = next((i for i, q in enumerate(order) if q > path), len(order))
        order.insert(pos, path)

    result = []
    n_new = n_reuse = 0
    for path in order:
        if path in EXISTING:
            if path not in old:
                raise SystemExit(f"!! 旧补丁缺少既有文件段：{path}")
            result.append(old[path])
            n_reuse += 1
        else:
            result.append(new_file_section(path))
            n_new += 1
    # 硬校验：源码量子文件必须全部有段（防再漏）
    if src_files - set(order):
        raise SystemExit(f"!! 仍有文件无段：{src_files - set(order)}")
    OUT.write_text("".join(result), encoding="utf-8")
    # 幂等性硬校验：重新解析产物，任何段文本内不得残留 `diff --color` 头
    # （新文件段的头由 new_file_section 统一生成，既有段不应带头）。
    for p, txt in _parse(OUT).items():
        if any(ln.startswith("diff --color") for ln in txt.splitlines()):
            raise SystemExit(f"!! 段内残留 diff --color 头（幂等性破坏）：{p}")
    print(f"→ {OUT}")
    print(f"  新文件段 {n_new} 个（从当前源码重生），既有文件段 {n_reuse} 个（旧补丁原样复用）")
    if missing:
        print(f"  相对旧补丁新增补齐的段：{', '.join(missing)}")
    print(f"  总段数 {len(order)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
