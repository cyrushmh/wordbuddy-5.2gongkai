"""logic —— 逻辑转换层。

把"开关电路"这一层做成可计算的对象：布尔表达式 → 真值表 → 范式 → 卡诺图
→ 最简式 → 门级网表 → 加法器。

这一层是"机器码"的上一站：CPU 里的 ALU 就是这些门堆出来的，理解
「一位全加器 = 2 个异或 + 2 个与 + 1 个或」再看汇编里的 `add` 就不是黑盒了。

支持的语法
----------
    变量   A / b / x1 / ready（字母或下划线开头）
    常量   0 1 T F
    非     !A   ~A   ¬A   not A   A'
    与     A & B   A && B   A*B   A·B   A∧B   A and B   A B（空格表示隐式与）
    注意   变量名是**贪婪匹配**的标识符：AB 是一个叫 "AB" 的变量，
           想表达 A 与 B 要写成 `A B` 或 `A & B`
    或     A | B   A || B   A+B   A∨B   A or B
    异或   A ^ B   A⊕B   A xor B
    蕴含   A -> B   A => B   A→B
    等价   A <-> B   A <=> B   A↔B   A≡B
    括号   ( )

优先级（低→高）：等价 < 蕴含 < 或 < 异或 < 与 < 非。

化简用 **Quine-McCluskey**（变量多也能算，不像卡诺图到 5 变量就难画），
并与真值表交叉验证等价性。

标准出处（STANDARD_REFS）
------------------------
仅用于定位规范；实现的正确性由本仓库单测（含随机表达式等价性检查）独立验证。

纯标准库、纯函数、只读。
"""

from __future__ import annotations
from sysweeper.i18n import _

import re
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

STANDARD_REFS = {
    "boolean": {
        "cn": "GB/T 4728.12《电气简图用图形符号 第12部分：二进制逻辑元件》（等同 IEC 60617-12）",
        "intl": "IEEE Std 91-1984（逻辑函数图形符号）；Boole 1854；Shannon 1938",
        "regional": "EN 60617（欧洲等同 IEC 60617）",
    },
    "karnaugh": {
        "cn": "GB/T 4728.12（同上，含卡诺图约定）",
        "intl": "M. Karnaugh, 1953, AIEE Transactions",
        "regional": "—",
    },
    "quine_mccluskey": {
        "cn": "—",
        "intl": "W. V. Quine 1952；E. J. McCluskey 1956",
        "regional": "—",
    },
    "adder": {
        "cn": "—（整数加法器无独立标准）",
        "intl": "IEEE 754-2019 §6（浮点加法语义）；整数补码加法见各 ISA 手册",
        "regional": "—",
    },
}

CAPABILITIES = [
    "布尔表达式解析（ASCII 与 Unicode 双套运算符）与求值",
    "真值表生成（变量自动收集、按字典序）",
    "最小项 / 最大项与 SOP / POS 范式",
    "积之和与和之积互转",
    "卡诺图文本渲染（2/3/4 变量，含无关项 X）",
    "Quine-McCluskey 化简（质蕴涵项 → 必要项 → 最小覆盖）",
    "门级变换：仅用 NAND / 仅用 NOR 重写，并统计门数",
    "半加器 / 全加器 / 行波进位加法器与溢出判定",
    "补码减法：借加法器实现 A - B",
]

# ---------------------------------------------------------------- 词法


_TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<lparen>[(（])
  | (?P<rparen>[)）])
  | (?P<eqv><->|<=>|↔|≡)
  | (?P<imp>->|=>|→|⊃)
  | (?P<or2>\|\|)
  | (?P<and2>&&)
  | (?P<op>[&|^+~!¬·∧∨⊕'])
  | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<num>[01])
""", re.VERBOSE)

KEYWORDS = {"and": "and", "or": "or", "not": "not", "xor": "xor",
            "nand": "nand", "nor": "nor"}

OP_TEXT = {
    "&": "and", "*": "and", "·": "and", "∧": "and", "&&": "and",
    "|": "or", "+": "or", "∨": "or", "||": "or",
    "^": "xor", "⊕": "xor",
    "~": "not", "!": "not", "¬": "not", "'": "not",
    "->": "imp", "=>": "imp", "→": "imp", "⊃": "imp",
    "<->": "eqv", "<=>": "eqv", "↔": "eqv", "≡": "eqv",
}


def tokenize(text: str) -> List[Tuple[str, str]]:
    """表达式 → token 列表 [(kind, text), ...]。未知字符标 `bad`。"""
    out: List[Tuple[str, str]] = []
    pos = 0
    s = str(text)
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            out.append(("bad", s[pos]))
            pos += 1
            continue
        kind = m.lastgroup
        tok = m.group()
        pos = m.end()
        if kind == "ws":
            continue
        if kind == "word":
            low = tok.lower()
            if low in KEYWORDS:
                out.append((KEYWORDS[low], tok))
            elif len(tok) == 1 and tok.upper() in ("T", "F"):
                out.append(("const", tok.upper()))
            else:
                out.append(("var", tok))
            continue
        if kind == "num":
            out.append(("const", tok))
            continue
        if kind == "op":
            op = OP_TEXT.get(tok, "bad")
            out.append((op, tok))
            continue
        if kind in ("or2", "and2"):
            out.append((OP_TEXT[tok], tok))
            continue
        out.append((kind, tok))
    return out


# ---------------------------------------------------------------- 语法（递归下降）

# AST 节点：("var", name) / ("const", 0|1) / ("not", x)
#          ("and"|"or"|"xor"|"imp"|"eqv", a, b)


class ParseError(ValueError):
    """表达式语法错误。"""


def parse(text: str):
    """布尔表达式 → AST。语法错误抛 ParseError。"""
    toks = tokenize(text)
    if not toks:
        raise ParseError(_("空表达式"))
    if any(k == "bad" for k, _t in toks):
        bad = [t for k, t in toks if k == "bad"]
        raise ParseError(_("无法识别的字符：%s") % " ".join(bad))
    p = _Parser(toks)
    node = p.parse_eqv()
    if p.pos < len(p.toks):
        raise ParseError(_("第 %d 个记号 %r 处有多余内容") % (p.pos + 1, p.toks[p.pos][1]))
    return node


class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else (None, None)

    def next(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def parse_eqv(self):
        left = self.parse_imp()
        while self.peek()[0] == "eqv":
            self.next()
            left = ("eqv", left, self.parse_imp())
        return left

    def parse_imp(self):
        left = self.parse_or()
        while self.peek()[0] == "imp":
            self.next()
            left = ("imp", left, self.parse_or())
        return left

    def parse_or(self):
        left = self.parse_xor()
        while self.peek()[0] == "or":
            self.next()
            left = ("or", left, self.parse_xor())
        return left

    def parse_xor(self):
        left = self.parse_and()
        while self.peek()[0] == "xor":
            self.next()
            left = ("xor", left, self.parse_and())
        return left

    def parse_and(self):
        left = self.parse_unary()
        while True:
            kind, tok = self.peek()
            if kind == "and":
                self.next()
                left = ("and", left, self.parse_unary())
            elif kind in ("var", "const", "lparen", "not"):
                # 隐式与：A B → A AND B（仅在两侧都是"基本项"时成立）
                left = ("and", left, self.parse_unary())
            else:
                break
        return left

    def parse_unary(self):
        kind, tok = self.peek()
        if kind == "not":
            self.next()
            return ("not", self.parse_unary())
        if kind == "lparen":
            self.next()
            node = self.parse_eqv()
            if self.peek()[0] != "rparen":
                raise ParseError(_("缺少右括号"))
            self.next()
            return _maybe_postfix(node, self)
        if kind == "const":
            self.next()
            return _maybe_postfix(("const", 1 if tok in ("1", "T") else 0), self)
        if kind == "var":
            self.next()
            return _maybe_postfix(("var", tok), self)
        raise ParseError(_("意外的记号 %r") % (tok,))


def _maybe_postfix(node, parser):
    """处理后缀 `'`（取反）。"""
    while parser.peek()[0] == "not" and parser.peek()[1] == "'":
        parser.next()
        node = ("not", node)
    return node


# ---------------------------------------------------------------- 语义


def variables(node) -> List[str]:
    """收集 AST 中出现的变量名（按字典序去重）。"""
    found: List[str] = []

    def walk(n):
        if n[0] == "var":
            if n[1] not in found:
                found.append(n[1])
        elif n[0] == "not":
            walk(n[1])
        elif n[0] in ("and", "or", "xor", "imp", "eqv"):
            walk(n[1])
            walk(n[2])

    walk(node)
    return sorted(found)


def evaluate(node, assignment: Dict[str, int]) -> int:
    """在给定赋值下求值，返回 0/1。缺变量按 0。"""
    kind = node[0]
    if kind == "var":
        return 1 if assignment.get(node[1], 0) else 0
    if kind == "const":
        return node[1]
    if kind == "not":
        return 1 - evaluate(node[1], assignment)
    a = evaluate(node[1], assignment)
    b = evaluate(node[2], assignment)
    if kind == "and":
        return a & b
    if kind == "or":
        return a | b
    if kind == "xor":
        return a ^ b
    if kind == "imp":
        return 1 if (not a) or b else 0
    if kind == "eqv":
        return 1 if a == b else 0
    raise ValueError(_("未知节点类型 %r") % kind)


def eval_expr(text: str, assignment: Optional[Dict[str, int]] = None) -> int:
    """一步到位：字符串 + 赋值 → 0/1。"""
    return evaluate(parse(text), assignment or {})


# ---------------------------------------------------------------- 真值表


def truth_table(text: str) -> Dict:
    """生成真值表：变量列表 + 全部 2^n 行 + 输出列 + 最小/最大项。"""
    node = parse(text)
    names = variables(node)
    rows = []
    for combo in product((0, 1), repeat=len(names)):
        assign = dict(zip(names, combo))
        rows.append({"inputs": list(combo), "out": evaluate(node, assign)})
    return {
        "expression": text,
        "variables": names,
        "rows": rows,
        "n": len(names),
        "minterms": [i for i, r in enumerate(rows) if r["out"] == 1],
        "maxterms": [i for i, r in enumerate(rows) if r["out"] == 0],
    }


def minterms(text: str) -> List[int]:
    """输出为 1 的行号（行号 = 变量取值组成的二进制数，第一个变量为最高位）。"""
    t = truth_table(text)
    return [i for i, r in enumerate(t["rows"]) if r["out"] == 1]


def maxterms(text: str) -> List[int]:
    """输出为 0 的行号。"""
    t = truth_table(text)
    return [i for i, r in enumerate(t["rows"]) if r["out"] == 0]


def render_truth_table(text: str) -> List[str]:
    """真值表 → 对齐的文本行。"""
    t = truth_table(text)
    names = t["variables"] or ["(常数)"]
    header = "  ".join("%*s" % (max(1, len(nm)), nm) for nm in names) + "  | 输出"
    sep = "-" * len(header)
    lines = [_("表达式：%s") % text, header, sep]
    for r in t["rows"]:
        cells = "  ".join("%*d" % (max(1, len(nm)), v)
                          for nm, v in zip(names, r["inputs"]))
        lines.append(cells + "  |  %d" % r["out"])
    lines.append(_("最小项 Σm(%s)   最大项 ΠM(%s)") % (
        ",".join(str(m) for m in t["minterms"]) or "—",
        ",".join(str(m) for m in t["maxterms"]) or "—"))
    return lines


# ---------------------------------------------------------------- 范式


def sop_expr(text: str) -> str:
    """积之和（析取范式）：从最小项展开，每项是全变量乘积。"""
    t = truth_table(text)
    names = t["variables"]
    if not names:
        return "1" if t["rows"][0]["out"] else "0"
    terms = []
    for m in t["minterms"]:
        parts = []
        for i, nm in enumerate(names):
            bit = (m >> (len(names) - 1 - i)) & 1
            parts.append(nm if bit else "!" + nm)
        terms.append("(" + " & ".join(parts) + ")")
    return " | ".join(terms) if terms else "0"


def pos_expr(text: str) -> str:
    """和之积（合取范式）：从最大项展开，每项是全变量求和。"""
    t = truth_table(text)
    names = t["variables"]
    if not names:
        return "1" if t["rows"][0]["out"] else "0"
    terms = []
    for m in t["maxterms"]:
        parts = []
        for i, nm in enumerate(names):
            bit = (m >> (len(names) - 1 - i)) & 1
            # 最大项中：变量为 0 写原变量，为 1 写反变量
            parts.append(("!" + nm) if bit else nm)
        terms.append("(" + " | ".join(parts) + ")")
    return " & ".join(terms) if terms else "1"


def canonical_forms(text: str) -> Dict:
    """同时给出 SOP / POS 与最小项、最大项编号。"""
    return {
        "expression": text,
        "variables": variables(parse(text)),
        "minterms": minterms(text),
        "maxterms": maxterms(text),
        "sop": sop_expr(text),
        "pos": pos_expr(text),
    }


# ---------------------------------------------------------------- 卡诺图

_GRAY2 = ["0", "1"]
_GRAY4 = ["00", "01", "11", "10"]


def karnaugh(minterms: Iterable[int], n_vars: int,
             names: Optional[Sequence[str]] = None,
             dont_cares: Iterable[int] = ()) -> Dict:
    """构造卡诺图网格。返回 rows/cols 标签与 cell 值（'0'/'1'/'X'）。"""
    names = list(names) if names else [chr(ord("A") + i) for i in range(n_vars)]
    dc = set(dont_cares)
    mt = set(minterms)
    if n_vars == 1:
        row_labels, col_labels = ["-"], _GRAY2
        def index(r, c): return int(col_labels[c])
    elif n_vars == 2:
        row_labels, col_labels = _GRAY2, _GRAY2
        def index(r, c):
            return int(row_labels[r] + col_labels[c], 2)
    elif n_vars == 3:
        row_labels, col_labels = _GRAY2, _GRAY4
        def index(r, c):
            return int(row_labels[r] + col_labels[c], 2)
    elif n_vars == 4:
        row_labels, col_labels = _GRAY4, _GRAY4
        def index(r, c):
            return int(row_labels[r] + col_labels[c], 2)
    else:
        return {"error": _("卡诺图仅支持 1-4 变量（更多变量请用 Quine-McCluskey）")}
    cells = []
    for r in range(len(row_labels)):
        line = []
        for c in range(len(col_labels)):
            m = index(r, c)
            line.append("X" if m in dc else ("1" if m in mt else "0"))
        cells.append(line)
    # 行 / 列各用几个变量（格雷码顺序：2 变量用 2×2，3 变量 2×4，4 变量 4×4）
    if n_vars == 1:
        row_var, col_var = "", names[0]
    elif n_vars == 2:
        row_var, col_var = names[0], names[1]
    elif n_vars == 3:
        row_var, col_var = names[0], "".join(names[1:3])
    else:
        row_var, col_var = "".join(names[0:2]), "".join(names[2:4])
    return {
        "n_vars": n_vars, "names": names,
        "row_labels": row_labels, "col_labels": col_labels,
        "row_var": row_var, "col_var": col_var,
        "cells": cells,
    }


def render_karnaugh(minterms: Iterable[int], n_vars: int,
                    names: Optional[Sequence[str]] = None,
                    dont_cares: Iterable[int] = ()) -> List[str]:
    """卡诺图 → 文本（行变量在左，列变量在上，均为格雷码顺序）。"""
    k = karnaugh(minterms, n_vars, names, dont_cares)
    if "error" in k:
        return [k["error"]]
    names = k["names"]
    col_var = k["col_var"]
    row_var = k["row_var"]
    width = max(1, len(col_var))
    lines = []
    lines.append(_("卡诺图  行=%s  列=%s（格雷码排序，相邻仅一位不同）") % (
        row_var or "—", col_var))
    header = "%*s | %s" % (max(3, len(row_var)), row_var or "",
                           " ".join("%*s" % (width, c) for c in k["col_labels"]))
    lines.append(header)
    lines.append("-" * len(header))
    for r, label in enumerate(k["row_labels"]):
        lines.append("%*s | %s" % (
            max(3, len(row_var)), label,
            " ".join("%*s" % (width, v) for v in k["cells"][r])))
    return lines


# ---------------------------------------------------------------- Quine-McCluskey


def _pattern(m: int, n: int) -> Tuple[str, ...]:
    return tuple("1" if (m >> (n - 1 - i)) & 1 else "0" for i in range(n))


def _combine(a: Tuple[str, ...], b: Tuple[str, ...]) -> Optional[Tuple[str, ...]]:
    """两个蕴涵项仅差一位则返回合并结果（该位变 '-'），否则 None。"""
    diff = -1
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            if diff >= 0:
                return None
            diff = i
    if diff < 0:
        return None
    out = list(a)
    out[diff] = "-"
    return tuple(out)


def _expand(pattern: Tuple[str, ...]) -> List[int]:
    """蕴涵项 → 覆盖的全部最小项编号。"""
    out = [0]
    for ch in pattern:
        if ch == "-":
            out = [x * 2 for x in out] + [x * 2 + 1 for x in out]
        else:
            out = [x * 2 + int(ch) for x in out]
    return sorted(out)


def _term_string(pattern: Tuple[str, ...], names: Sequence[str]) -> str:
    """蕴涵项 → 乘积项文本。

    用显式 `&` 连接（不能写成 `AB` 这类隐式与：本解析器会把 `AB` 当成
    **一个**变量名，多字母变量名必须留空格或运算符）。
    """
    parts = []
    for ch, nm in zip(pattern, names):
        if ch == "1":
            parts.append(nm)
        elif ch == "0":
            parts.append("!" + nm)
    if not parts:
        return "1"
    return " & ".join(parts)


def quine_mccluskey(minterms: Iterable[int], n_vars: int,
                    names: Optional[Sequence[str]] = None,
                    dont_cares: Iterable[int] = ()) -> Dict:
    """Quine-McCluskey 化简。

    返回：合并过程（steps）、质蕴涵项、必要质蕴涵项、最小覆盖与最简式。
    最小覆盖：先取必要项，剩余部分在项数 ≤ 16 时穷举最优解，否则贪心。
    """
    names = list(names) if names else [chr(ord("A") + i) for i in range(n_vars)]
    on_set = set(minterms)
    dc_set = set(dont_cares)
    universe = sorted(on_set | dc_set)
    if not on_set:
        return {"expression": "0", "prime_implicants": [], "essential": [],
                "cover": [], "steps": ["输出恒为 0，最简式 = 0"], "n_vars": n_vars}
    if not (set(range(1 << n_vars)) - (on_set | dc_set)):
        # 全部行都是 1 或无关项 → 恒 1
        return {"expression": "1", "prime_implicants": [], "essential": [],
                "cover": [], "steps": ["全部最小项为 1（含无关项），最简式 = 1"],
                "n_vars": n_vars, "names": names,
                "minterms": sorted(on_set), "dont_cares": sorted(dc_set)}

    steps = []
    current = {_pattern(m, n_vars): {m} for m in universe}
    all_primes: Dict[Tuple[str, ...], set] = {}
    round_no = 0
    while current:
        used = set()
        nxt: Dict[Tuple[str, ...], set] = {}
        keys = sorted(current.keys())
        merged_pairs = []
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                merged = _combine(keys[i], keys[j])
                if merged is None:
                    continue
                used.add(keys[i])
                used.add(keys[j])
                nxt.setdefault(merged, set()).update(current[keys[i]] | current[keys[j]])
                merged_pairs.append((keys[i], keys[j], merged))
        for k in keys:
            if k not in used:
                all_primes.setdefault(k, set()).update(current[k])
        if merged_pairs:
            round_no += 1
            steps.append({"round": round_no,
                          "merged": [("".join(a), "".join(b), "".join(m))
                                     for a, b, m in merged_pairs]})
        else:
            steps.append({"round": round_no + 1, "merged": [],
                          "note": "无更多可合并项，剩余即质蕴涵项"})
        current = nxt
        if not merged_pairs:
            break

    # 质蕴涵项（只统计对真实最小项的覆盖）
    primes = []
    for pat, covered_raw in sorted(all_primes.items()):
        real = sorted(m for m in covered_raw if m in on_set)
        primes.append({"pattern": "".join(pat), "term": _term_string(pat, names),
                       "covers": real, "size": len(real)})
    # 必要项：某个最小项只被一个质蕴涵项覆盖
    coverage: Dict[int, List[int]] = {}
    for idx, p in enumerate(primes):
        for m in p["covers"]:
            coverage.setdefault(m, []).append(idx)
    essential_idx = set()
    for m, idxs in coverage.items():
        if len(idxs) == 1:
            essential_idx.add(idxs[0])

    covered = set()
    for i in essential_idx:
        covered.update(primes[i]["covers"])
    remaining = sorted(on_set - covered)
    chosen = sorted(essential_idx)
    note = ""
    if remaining:
        candidates = [i for i in range(len(primes)) if i not in essential_idx]
        best = None
        if len(candidates) <= 16:
            best = _exhaustive_cover(candidates, primes, remaining)
        if best is None:
            best = _greedy_cover(candidates, primes, remaining)
            note = "剩余部分项数过多，采用贪心覆盖（不保证全局最小）"
        chosen = sorted(set(chosen) | set(best))
    chosen_primes = [primes[i] for i in sorted(chosen)]
    expr = " | ".join(("(%s)" % p["term"]) if " & " in p["term"] else (p["term"] or "1")
                      for p in chosen_primes)
    return {
        "n_vars": n_vars, "names": names,
        "minterms": sorted(on_set), "dont_cares": sorted(dc_set),
        "prime_implicants": primes,
        "essential": sorted(essential_idx),
        "cover": sorted(chosen),
        "expression": expr or "0",
        "covered": sorted(set().union(*[set(p["covers"]) for p in chosen_primes])) if chosen_primes else [],
        "steps": steps, "note": note,
    }


def _exhaustive_cover(candidates, primes, remaining) -> Optional[List[int]]:
    """穷举最小覆盖（候选项 ≤ 16 时可用）。"""
    target = set(remaining)
    best = None
    total = 1 << len(candidates)
    for mask in range(total):
        pick = [candidates[i] for i in range(len(candidates)) if mask & (1 << i)]
        cov = set()
        for i in pick:
            cov.update(primes[i]["covers"])
        if not target <= cov:
            continue
        key = (len(pick), sum(len(primes[i]["pattern"].replace("-", "")) for i in pick))
        if best is None or key < best[0]:
            best = (key, pick)
    return best[1] if best else None


def _greedy_cover(candidates, primes, remaining) -> List[int]:
    """贪心覆盖：每次选覆盖最多未覆盖项的质蕴涵项。"""
    target = set(remaining)
    pick = []
    while target:
        best_i, best_gain = None, -1
        for i in candidates:
            if i in pick:
                continue
            gain = len(target & set(primes[i]["covers"]))
            if gain > best_gain:
                best_i, best_gain = i, gain
        if best_i is None or best_gain <= 0:
            break
        pick.append(best_i)
        target -= set(primes[best_i]["covers"])
    return pick


def simplify(text: str) -> Dict:
    """化简布尔表达式：真值表 → QM → 最简 SOP，并**验证等价性**。"""
    t = truth_table(text)
    names = t["variables"]
    if not names:
        return {"expression": "1" if t["rows"][0]["out"] else "0",
                "original": text, "equivalent": True, "steps": []}
    res = quine_mccluskey(t["minterms"], len(names), names)
    simplified = res["expression"]
    # 交叉验证：真值表逐行比对
    same = True
    for r in t["rows"]:
        assign = dict(zip(names, r["inputs"]))
        try:
            if evaluate(parse(simplified), assign) != r["out"]:
                same = False
                break
        except ParseError:
            same = False
            break
    res["original"] = text
    res["equivalent"] = same
    res["truth_table"] = t
    return res


def render_qm(text: str) -> List[str]:
    """QM 化简过程 → 文本（含合并轮次与覆盖选择）。"""
    t = truth_table(text)
    names = t["variables"]
    if not names:
        return [_("常量表达式：%s") % text]
    res = quine_mccluskey(t["minterms"], len(names), names)
    lines = [
        _("Quine-McCluskey 化简：%s") % text,
        _("变量：%s    最小项：Σm(%s)") % (
            ",".join(names), ",".join(str(m) for m in res["minterms"]) or "—"),
    ]
    for step in res["steps"]:
        if step.get("note"):
            lines.append(_("  第 %d 轮：%s") % (step["round"], step["note"]))
            continue
        pairs = "，".join("%s+%s→%s" % (a, b, m) for a, b, m in step["merged"])
        lines.append(_("  第 %d 轮合并：%s") % (step["round"], pairs))
    lines.append(_("质蕴涵项（%d 个）：") % len(res["prime_implicants"]))
    for i, p in enumerate(res["prime_implicants"]):
        tag = " 必要" if i in res["essential"] else (" 选中" if i in res["cover"] else "")
        lines.append(_("  %-2d %-10s %-14s 覆盖 m(%s)%s") % (
            i, p["pattern"], p["term"] or "1",
            ",".join(str(m) for m in p["covers"]) or "—", tag))
    lines.append(_("最简式：%s") % res["expression"])
    if res.get("note"):
        lines.append(_("注：%s") % res["note"])
    return lines


# ---------------------------------------------------------------- 门级变换


def gate_count(node) -> Dict[str, int]:
    """统计各类门的个数（按 AST 结构计数）。"""
    counts = {"NOT": 0, "AND": 0, "OR": 0, "XOR": 0, "IMP": 0, "EQV": 0}

    def walk(n):
        kind = n[0]
        if kind in ("var", "const"):
            return
        if kind == "not":
            counts["NOT"] += 1
            walk(n[1])
            return
        key = kind.upper()
        if key in counts:
            counts[key] += 1
        walk(n[1])
        walk(n[2])

    walk(node)
    counts["TOTAL"] = sum(v for k, v in counts.items() if k != "TOTAL")
    return counts


def to_nand(node):
    """把 AST 改写成**只用二输入 NAND** 的等价结构。

    依据：¬A = A↑A；(A·B) = ¬(A↑B)；(A+B) = ¬A↑¬B；
    A⊕B = (A·¬B)+(¬A·B)（先展开再套用上面三条）。
    """
    kind = node[0]
    if kind in ("var", "const"):
        return node
    if kind == "not":
        a = to_nand(node[1])
        return ("nand", a, a)
    if kind == "and":
        a = to_nand(node[1])
        b = to_nand(node[2])
        return ("nand", ("nand", a, b), ("nand", a, b))
    if kind == "or":
        a = to_nand(node[1])
        b = to_nand(node[2])
        return ("nand", ("nand", a, a), ("nand", b, b))
    if kind == "xor":
        # A⊕B = A·¬B + ¬A·B，再套上面的与/或/非规则
        return to_nand(("or", ("and", node[1], ("not", node[2])),
                        ("and", ("not", node[1]), node[2])))
    if kind == "imp":
        return to_nand(("or", ("not", node[1]), node[2]))
    if kind == "eqv":
        return to_nand(("or", ("and", node[1], node[2]),
                        ("and", ("not", node[1]), ("not", node[2]))))
    raise ValueError(_("未知节点 %r") % kind)


def to_nor(node):
    """把 AST 改写成**只用二输入 NOR** 的等价结构。"""
    kind = node[0]
    if kind in ("var", "const"):
        return node
    if kind == "not":
        a = to_nor(node[1])
        return ("nor", a, a)
    a = to_nor(node[1])
    b = to_nor(node[2])
    if kind == "or":
        return ("nor", ("nor", a, b), ("nor", a, b))
    if kind == "and":
        return ("nor", ("nor", a, a), ("nor", b, b))
    if kind == "xor":
        return to_nor(("or", ("and", node[1], ("not", node[2])),
                       ("and", ("not", node[1]), node[2])))
    if kind == "imp":
        return to_nor(("or", ("not", node[1]), node[2]))
    if kind == "eqv":
        return to_nor(("or", ("and", node[1], node[2]),
                       ("and", ("not", node[1]), ("not", node[2]))))
    raise ValueError(_("未知节点 %r") % kind)


def _count_nand(node) -> int:
    if node[0] == "nand":
        return 1 + _count_nand(node[1]) + _count_nand(node[2])
    return 0


def _count_nor(node) -> int:
    if node[0] == "nor":
        return 1 + _count_nor(node[1]) + _count_nor(node[2])
    return 0


def render_expr(node, ascii_only: bool = False) -> str:
    """AST → 表达式文本（可选 ASCII 或 Unicode 符号）。"""
    sym = {"and": "&", "or": "|", "xor": "^", "imp": "->", "eqv": "<->"}
    uni = {"and": "∧", "or": "∨", "xor": "⊕", "imp": "→", "eqv": "≡"}
    table = sym if ascii_only else uni
    kind = node[0]
    if kind == "var":
        return node[1]
    if kind == "const":
        return str(node[1])
    if kind == "not":
        inner = render_expr(node[1], ascii_only)
        if node[1][0] in ("var", "const"):
            return ("!" if ascii_only else "¬") + inner
        return ("!" if ascii_only else "¬") + "(" + inner + ")"
    if kind in ("nand", "nor"):
        op = "↑" if kind == "nand" else "↓"
        if ascii_only:
            op = "~&" if kind == "nand" else "~|"
        return "(" + render_expr(node[1], ascii_only) + " " + op + " " + \
               render_expr(node[2], ascii_only) + ")"
    return "(" + render_expr(node[1], ascii_only) + " " + table[kind] + " " + \
           render_expr(node[2], ascii_only) + ")"


def nand_report(text: str) -> Dict:
    """给一个表达式的门级视图：原门数、NAND 化、NOR 化与门数。"""
    node = parse(text)
    nand = to_nand(node)
    nor = to_nor(node)
    return {
        "expression": text,
        "gate_count": gate_count(node),
        "nand_expr": render_expr(nand, ascii_only=True),
        "nand_gates": _count_nand(nand),
        "nor_expr": render_expr(nor, ascii_only=True),
        "nor_gates": _count_nor(nor),
        "note": "NAND/NOR 门数按 AST 结构展开统计，未做子表达式共享优化",
    }


# ---------------------------------------------------------------- 加法器


GATES = {
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
    "NAND": lambda a, b: 1 - (a & b),
    "NOR": lambda a, b: 1 - (a | b),
    "XOR": lambda a, b: a ^ b,
    "XNOR": lambda a, b: 1 - (a ^ b),
}


def render_gate_table() -> List[str]:
    """六种基本门的两输入真值表。"""
    names = ["AND", "OR", "NAND", "NOR", "XOR", "XNOR"]
    lines = ["A B | " + " ".join("%-4s" % n for n in names)]
    for a, b in product((0, 1), repeat=2):
        row = " ".join("%-4d" % GATES[n](a, b) for n in names)
        lines.append("%d %d | %s" % (a, b, row))
    return lines


def half_adder(a: int, b: int) -> Tuple[int, int]:
    """半加器：S = A⊕B，C = A·B。"""
    return (a ^ b, a & b)


def full_adder(a: int, b: int, cin: int) -> Tuple[int, int]:
    """全加器：S = A⊕B⊕Cin，Cout = A·B + Cin·(A⊕B)。"""
    s = a ^ b ^ cin
    cout = (a & b) | (cin & (a ^ b))
    return (s, cout)


def ripple_add(x: int, y: int, bits: int = 8, sub: bool = False) -> Dict:
    """行波进位加法器（补码）：逐位全加器串起来。

    sub=True 时计算 x - y：把 y 取反加一（补码），即 Cin 初始置 1。
    返回逐位过程、结果（无符号与有符号两种读法）与溢出标志。
    """
    width = max(1, int(bits))
    mask = (1 << width) - 1
    xs = _bits_msb_first(x & mask, width)
    ys = _bits_msb_first((~y & mask) if sub else (y & mask), width)
    carry = 1 if sub else 0
    rows = []
    result = 0
    for i in range(width - 1, -1, -1):
        pos = width - 1 - i          # 从最低位（pos=0）开始逐位相加
        a, b = xs[i], ys[i]
        s, cout = full_adder(a, b, carry)
        rows.append({"bit": pos, "a": a, "b": b, "cin": carry,
                     "sum": s, "cout": cout})
        result |= s << pos
        carry = cout
    # 溢出：进入符号位的进位 ⊕ 出符号位的进位
    cin_msb = rows[-1]["cin"] if rows else 0
    cout_msb = rows[-1]["cout"] if rows else 0
    overflow = cin_msb ^ cout_msb
    return {
        "x": x & mask, "y": y & mask, "bits": width, "sub": sub,
        "rows": list(reversed(rows)),
        "result_unsigned": result & mask,
        "result_signed": (result - (1 << width)) if result & (1 << (width - 1)) else result,
        "carry_out": carry, "overflow": overflow,
        "hex": "%0*X" % ((width + 3) // 4, result & mask),
        "bin": "".join(str(b) for b in _bits_msb_first(result & mask, width)),
    }


def _bits_msb_first(value: int, width: int) -> List[int]:
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def render_adder(x: int, y: int, bits: int = 8, sub: bool = False) -> List[str]:
    """加法器逐位过程 → 文本（含溢出判定）。"""
    r = ripple_add(x, y, bits, sub)
    op = "-" if sub else "+"
    lines = [
        "%d %s %d（%d 位补码）" % (r["x"], op, r["y"], r["bits"]),
        _("位   A  B  Cin | S  Cout"),
    ]
    for row in r["rows"]:
        lines.append(" %2d  %d  %d   %d   | %d   %d" % (
            row["bit"], row["a"], row["b"], row["cin"], row["sum"], row["cout"]))
    lines.append(_("结果：无符号 %d，有符号 %d，二进制 %s（0x%s）") % (
        r["result_unsigned"], r["result_signed"], r["bin"], r["hex"]))
    lines.append(_("进位 Cout=%d    溢出 V=%d（= Cin[符号位] ⊕ Cout[符号位]）%s") % (
        r["carry_out"], r["overflow"], "← 有符号溢出" if r["overflow"] else ""))
    return lines
