#!/usr/bin/env python3
"""编程语言「概念系统」分类构建（主目录：wordbuddy-github，v0.6.56）。

把 data/langs_docs.json 的 161 条语言组织成**分层概念体系**：

    主目录（概念系统）wordbuddy-github
      └─ 轴1 执行模型 execution_model : native / bytecode-vm / interpreted / jit / transpiled / ir / hdl / non-exec
      └─ 轴2 硬件架构 target_arch     : isa(x86-64·arm64·riscv) / virtual-isa(wasm) /
                                        vm(jvm·clr·beam·evm·js) / accelerator(gpu-simt) /
                                        reconfigurable(fpga) / host(宿主进程) / n-a(非执行)
      └─ 轴3 能力域 domain            : systems / network / data / query / config / web / …
      └─ 轴4 底层标准依据 standard_basis: 各域挂 RFC / ISO / ECMA / IEEE / Unicode 等

「有条件的以硬件架构为子分类」：能明确目标架构的语言按架构归类；纯解释/宿主相关/非执行的
语言如实归 host / n-a，不硬塞架构。

「不足的以 RFC 等底层标准补充」：语言自身标准(standard)字段不足处，由所属**能力域**继承底层
标准依据（RFC 等）；所有 RFC 编号**经本仓库 rfc_catalog 交叉验证存在性**（防写错编号）。

用法：
    python3 build_plang.py            # 构建 data/concepts/plang_taxonomy.json
    python3 build_plang.py --check    # 校验（RFC 均在 rfc_catalog 中、架构/模型合法、覆盖完整）
    python3 build_plang.py --report   # 打印分类统计
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
DATA = (HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "langs_docs.json")
OUT = (HERE.parents[1] / "src" / "python" / "sysweeper" / "data" / "concepts"
       / "plang_taxonomy.json")
PROBE = HERE / "probe_report.json"

# 161 语言字段补全（paradigm/typing/memory/gist/engineering；first_appeared 取数据层 first_year）
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from lang_enrich import LANG_ENRICH  # noqa: E402

ENRICH_FIELDS = ("paradigm", "typing", "memory", "gist", "engineering")


def _unpack_enrich(lid: str) -> Dict[str, str]:
    """把 lang_enrich 的五字段 tuple 转成 dict（供 ** 合并进 lang_index 条目）。"""
    v = LANG_ENRICH.get(lid)
    if not v:
        return {}
    return dict(zip(ENRICH_FIELDS, v))

# ---- 轴1：执行模型 ----
MODELS = [
    {"model": "native", "label": "编译到原生机器码", "note": "经 LLVM/GCC 等后端产出特定 ISA 的可执行文件"},
    {"model": "bytecode-vm", "label": "编译到虚拟机字节码", "note": "产出 JVM/CLR/BEAM/EVM 等字节码"},
    {"model": "interpreted", "label": "解释执行", "note": "由解释器/宿主进程直接求值，无独立目标架构"},
    {"model": "jit", "label": "即时编译(JIT)", "note": "运行时编译到宿主机器码"},
    {"model": "transpiled", "label": "转译到另一语言", "note": "源码→另一高级语言（如 TS→JS）"},
    {"model": "ir", "label": "中间表示/字节码规范", "note": "如 WebAssembly，作为多语言编译目标"},
    {"model": "hdl", "label": "硬件描述(综合到电路)", "note": "经综合/实现工具映射到 FPGA/ASIC"},
    {"model": "non-exec", "label": "非执行型（声明/描述）", "note": "配置、查询、标记、数据、排版、记号等，由宿主工具解释"},
]

# ---- 轴2：硬件架构子分类（kind 区分真实 ISA / 虚拟 ISA / VM / 加速器 / 可重构 / 宿主 / 非执行）----
ARCHS = [
    {"arch": "x86-64", "label": "x86-64 (AMD64)", "kind": "isa",
     "note": "主流桌面/服务器指令集；LLVM·GCC 一等公民"},
    {"arch": "arm64", "label": "ARM64 (AArch64)", "kind": "isa",
     "note": "移动/云原生/Apple Silicon 主流指令集"},
    {"arch": "riscv", "label": "RISC-V", "kind": "isa",
     "note": "开放指令集，LLVM/GCC 已支持"},
    {"arch": "wasm", "label": "WebAssembly", "kind": "virtual-isa",
     "note": "可移植虚拟指令集（W3C 标准），浏览器与边缘运行时"},
    {"arch": "jvm", "label": "JVM 字节码", "kind": "vm", "note": "Java 虚拟机"},
    {"arch": "clr", "label": "CLR / .NET IL", "kind": "vm", "note": "公共语言运行时"},
    {"arch": "beam", "label": "BEAM (Erlang VM)", "kind": "vm", "note": "面向并发与容错的虚拟机"},
    {"arch": "evm", "label": "EVM 及同类链上 VM", "kind": "vm", "note": "智能合约执行环境"},
    {"arch": "js", "label": "JS 引擎 (V8/JSC/SM)", "kind": "vm", "note": "浏览器与 Node/Deno 的 JS 执行引擎"},
    {"arch": "gpu-simt", "label": "GPU (SIMT 加速器)", "kind": "accelerator",
     "note": "数据并行加速，CUDA/OpenCL/ROCm 类"},
    {"arch": "fpga", "label": "FPGA / ASIC", "kind": "reconfigurable", "note": "可重构硬件，由 HDL 综合实现"},
    {"arch": "host", "label": "宿主进程（架构无关）", "kind": "host",
     "note": "解释/JIT 语言，目标架构取决于宿主进程，不单独绑定 ISA"},
    {"arch": "n-a", "label": "非执行（无目标架构）", "kind": "non-exec",
     "note": "配置/查询/标记/数据/排版/记号类，谈「目标架构」无意义"},
]

# ---- 轴3/4：能力域 → 底层标准依据（RFC 等；「不足的以 RFC 补充」的落地）----
DOMAINS = [
    {"domain": "systems", "label": "系统编程",
     "standards": [{"kind": "RFC", "num": 9293, "why": "TCP 等系统网络栈的基础规范（底层协议依据）"}]},
    {"domain": "network", "label": "网络与分布式",
     "standards": [{"kind": "RFC", "num": 9110, "why": "HTTP 语义"},
                   {"kind": "RFC", "num": 9112, "why": "HTTP/1.1 报文语法"},
                   {"kind": "RFC", "num": 8446, "why": "TLS 1.3"},
                   {"kind": "RFC", "num": 1035, "why": "DNS 实现与规范"}]},
    {"domain": "data", "label": "数据序列化与交换",
     "standards": [{"kind": "RFC", "num": 8259, "why": "JSON 文本格式"},
                   {"kind": "RFC", "num": 3629, "why": "UTF-8 字符编码（文本互操作底座）"}]},
    {"domain": "query", "label": "查询与知识图谱",
     "standards": [{"kind": "RFC", "num": 3629, "why": "UTF-8（查询文本与标识符编码）"}]},
    {"domain": "identity", "label": "标识、时间与文本",
     "standards": [{"kind": "RFC", "num": 3986, "why": "URI 通用语法"},
                   {"kind": "RFC", "num": 3339, "why": "日期时间表示"},
                   {"kind": "RFC", "num": 5322, "why": "互联网消息格式"}]},
    {"domain": "web", "label": "Web 与浏览器",
     "standards": [{"kind": "RFC", "num": 9110, "why": "HTTP 语义"},
                   {"kind": "RFC", "num": 8446, "why": "TLS 1.3"}]},
    {"domain": "security-crypto", "label": "安全与密码学",
     "standards": [{"kind": "RFC", "num": 8446, "why": "TLS 1.3"},
                   {"kind": "RFC", "num": 5280, "why": "X.509 证书（可经本仓库 rfc_catalog 反查）"}]},
    {"domain": "esolang", "label": "深奥/实验语言（esolang）", "standards": [],
     "note": "刻意反工程实践的玩具/实验语言；诚实标注——无任何工程标准依据可补，故不继承 RFC"},
    {"domain": "education", "label": "教育与图形化", "standards": [],
     "note": "面向教学/青少年的语言与图形化环境，无强制工程标准依据"},
]

# ---- 显式覆盖：语言 → (执行模型, [目标架构], [能力域]) ----
# 「有条件的以硬件架构为子分类」：能明确目标的在此显式给出
EXPLICIT: Dict[str, tuple] = {
    # 原生编译（多 ISA）
    "rust": ("native", ["x86-64", "arm64", "riscv", "wasm"], ["systems", "network"]),
    "go": ("native", ["x86-64", "arm64", "riscv", "wasm"], ["systems", "network"]),
    "c": ("native", ["x86-64", "arm64", "riscv", "wasm"], ["systems"]),
    "cpp": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "zig": ("native", ["x86-64", "arm64", "riscv", "wasm"], ["systems"]),
    "nim": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "odin": ("native", ["x86-64", "arm64"], ["systems"]),
    "hare": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "v": ("native", ["x86-64", "arm64"], ["systems"]),
    "crystal": ("native", ["x86-64", "arm64"], ["systems"]),
    "swift": ("native", ["x86-64", "arm64"], ["systems", "web"]),
    "ada": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "fortran": ("native", ["x86-64", "arm64"], ["systems"]),
    "pascal": ("native", ["x86-64", "arm64"], ["systems"]),
    "delphi": ("native", ["x86-64"], ["systems"]),
    "modula2": ("native", ["x86-64"], ["systems"]),
    "oberon": ("native", ["x86-64"], ["systems"]),
    "d": ("native", ["x86-64", "arm64"], ["systems"]),
    "chapel": ("native", ["x86-64", "arm64"], ["systems"]),
    "terra": ("native", ["x86-64", "arm64"], ["systems"]),
    "assembly": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "wa": ("native", ["wasm"], ["systems", "web"]),
    "cangjie": ("native", ["arm64", "x86-64"], ["systems", "web"]),
    "mojo": ("native", ["x86-64", "arm64", "gpu-simt"], ["systems"]),
    "carbon": ("native", ["x86-64", "arm64"], ["systems"]),
    "roc": ("native", ["x86-64", "arm64", "wasm"], ["systems"]),
    "pony": ("native", ["x86-64", "arm64"], ["systems", "network"]),
    "futhark": ("native", ["gpu-simt"], ["systems"]),
    "bend": ("native", ["gpu-simt"], ["systems"]),
    "grain": ("native", ["wasm"], ["web"]),
    # JVM 系
    "java": ("bytecode-vm", ["jvm"], ["systems", "network"]),
    "kotlin": ("bytecode-vm", ["jvm"], ["systems", "web"]),
    "scala": ("bytecode-vm", ["jvm"], ["systems"]),
    "clojure": ("bytecode-vm", ["jvm"], ["systems"]),
    "ballerina": ("bytecode-vm", ["jvm"], ["network"]),
    # CLR 系
    "csharp": ("bytecode-vm", ["clr"], ["systems", "web"]),
    "fsharp": ("bytecode-vm", ["clr"], ["systems"]),
    "visualbasic": ("bytecode-vm", ["clr"], ["web"]),
    # BEAM 系
    "erlang": ("bytecode-vm", ["beam"], ["network"]),
    "elixir": ("bytecode-vm", ["beam"], ["network"]),
    "gleam": ("bytecode-vm", ["beam"], ["network"]),
    # 链上 VM
    "solidity": ("bytecode-vm", ["evm"], ["security-crypto", "network"]),
    "move": ("bytecode-vm", ["evm"], ["security-crypto"]),
    "cairo": ("bytecode-vm", ["evm"], ["security-crypto"]),
    "noir": ("bytecode-vm", ["evm"], ["security-crypto"]),
    # JS 引擎系
    "javascript": ("interpreted", ["js"], ["web", "network"]),
    "typescript": ("transpiled", ["js"], ["web"]),
    "dart": ("jit", ["js", "arm64", "x86-64"], ["web"]),
    "elm": ("transpiled", ["js"], ["web"]),
    "purescript": ("transpiled", ["js"], ["web"]),
    "reason": ("transpiled", ["js"], ["web"]),
    "arkts": ("transpiled", ["js", "arm64"], ["web"]),
    # IR
    "wasm": ("ir", ["wasm"], ["web", "systems"]),
    # HDL
    "verilog": ("hdl", ["fpga"], ["systems"]),
    "vhdl": ("hdl", ["fpga"], ["systems"]),
    # 解释/JIT（宿主）
    "python": ("interpreted", ["host"], ["systems", "network", "data"]),
    "ruby": ("interpreted", ["host"], ["web", "network"]),
    "perl": ("interpreted", ["host"], ["identity"]),
    "php": ("interpreted", ["host"], ["web"]),
    "lua": ("interpreted", ["host"], ["systems"]),
    "tcl": ("interpreted", ["host"], ["systems"]),
    "raku": ("interpreted", ["host"], ["identity"]),
    "bash": ("interpreted", ["host"], ["systems"]),
    "awk": ("interpreted", ["host"], ["identity"]),
    "r": ("interpreted", ["host"], ["data"]),
    "matlab": ("interpreted", ["host"], ["data"]),
    "julia": ("jit", ["host"], ["data"]),
    "hack": ("jit", ["host"], ["web"]),
    # 验证/证明（宿主）
    "coq": ("interpreted", ["host"], ["systems"]),
    "agda": ("native", ["host"], ["systems"]),
    "isabelle": ("interpreted", ["host"], ["systems"]),
    "dafny": ("native", ["host"], ["systems"]),
    # 数据/配置/查询/标记/排版/记号 → 非执行
    "protobuf": ("non-exec", ["n-a"], ["data"]),
    "avro": ("non-exec", ["n-a"], ["data"]),
    "flatbuffers": ("non-exec", ["n-a"], ["data"]),
    "capnproto": ("non-exec", ["n-a"], ["data"]),
    "json": ("non-exec", ["n-a"], ["data"]),
    "yaml": ("non-exec", ["n-a"], ["data"]),
    "toml": ("non-exec", ["n-a"], ["data"]),
    "sql": ("non-exec", ["n-a"], ["query"]),
    "sparql": ("non-exec", ["n-a"], ["query"]),
    "cypher": ("non-exec", ["n-a"], ["query"]),
    "xpath": ("non-exec", ["n-a"], ["query"]),
    "datalog": ("non-exec", ["n-a"], ["query"]),
    "graphql": ("non-exec", ["n-a"], ["query", "network"]),
    "nix": ("non-exec", ["n-a"], ["systems"]),
    "hcl": ("non-exec", ["n-a"], ["systems"]),
    "jsonnet": ("non-exec", ["n-a"], ["systems"]),
    "dhall": ("non-exec", ["n-a"], ["systems"]),
    "cue": ("non-exec", ["n-a"], ["systems"]),
    "pkl": ("non-exec", ["n-a"], ["systems"]),
    "starlark": ("non-exec", ["n-a"], ["systems"]),
    "makefile": ("non-exec", ["n-a"], ["systems"]),
    "openapi": ("non-exec", ["n-a"], ["web", "network"]),
    "html": ("non-exec", ["n-a"], ["web"]),
    "css": ("non-exec", ["n-a"], ["web"]),
    "markdown": ("non-exec", ["n-a"], ["identity"]),
    "xslt": ("non-exec", ["n-a"], ["identity"]),
    "latex": ("non-exec", ["n-a"], ["identity"]),
    "postscript": ("non-exec", ["n-a"], ["identity"]),
    "regex": ("non-exec", ["n-a"], ["identity"]),
    "bnf": ("non-exec", ["n-a"], ["identity"]),

    # ---- 逐条细化（原 inferred → explicit，人工判定）----
    # esolang：解释器执行、归宿主；不继承工程标准（域 esolang 无 RFC）
    "brainfuck": ("interpreted", ["host"], ["esolang"]),
    "befunge": ("interpreted", ["host"], ["esolang"]),
    "intercal": ("interpreted", ["host"], ["esolang"]),
    "malbolge": ("interpreted", ["host"], ["esolang"]),
    "piet": ("interpreted", ["host"], ["esolang"]),
    "whitespace": ("interpreted", ["host"], ["esolang"]),
    "lolcode": ("interpreted", ["host"], ["esolang"]),
    "unlambda": ("interpreted", ["host"], ["esolang"]),
    "shakespeare": ("interpreted", ["host"], ["esolang"]),
    "chef": ("interpreted", ["host"], ["esolang"]),
    "wenyan": ("transpiled", ["js"], ["esolang"]),
    # 解释/JIT 宿主类
    "apl": ("interpreted", ["host"], ["systems", "data"]),
    "jlang": ("interpreted", ["host"], ["systems", "data"]),
    "klang": ("interpreted", ["host"], ["data"]),
    "bqn": ("interpreted", ["host"], ["data"]),
    "forth": ("interpreted", ["host"], ["systems"]),
    "iolang": ("interpreted", ["host"], ["systems"]),
    "lisp": ("interpreted", ["host"], ["systems"]),
    "scheme": ("interpreted", ["host"], ["systems"]),
    "racket": ("interpreted", ["host"], ["systems"]),
    "smalltalk": ("bytecode-vm", ["host"], ["systems"]),
    "rebol": ("interpreted", ["host"], ["data"]),
    "rexx": ("interpreted", ["host"], ["systems"]),
    "ring": ("interpreted", ["host"], ["systems"]),
    "mulan": ("interpreted", ["host"], ["systems"]),
    "wolfram": ("interpreted", ["host"], ["data"]),
    "prolog": ("interpreted", ["host"], ["query"]),
    "curry": ("interpreted", ["host"], ["query"]),
    "snobol": ("interpreted", ["host"], ["identity"]),
    "logo": ("interpreted", ["host"], ["education"]),
    "scratch": ("interpreted", ["host"], ["education"]),
    # 原生编译类
    "cplusplus": ("native", ["x86-64", "arm64", "riscv"], ["systems"]),
    "haskell": ("native", ["x86-64", "arm64"], ["systems"]),
    "ocaml": ("native", ["x86-64", "arm64"], ["systems"]),
    "sml": ("native", ["x86-64", "arm64"], ["systems"]),
    "ml": ("native", ["x86-64"], ["systems"]),
    "commonlisp": ("native", ["x86-64", "arm64"], ["systems"]),
    "idris": ("native", ["x86-64", "arm64"], ["systems"]),
    "lean": ("native", ["x86-64", "arm64"], ["systems"]),
    "koka": ("native", ["x86-64", "arm64"], ["systems"]),
    "unison": ("native", ["x86-64", "arm64"], ["network", "systems"]),
    "verse": ("native", ["x86-64", "arm64"], ["systems"]),
    "lobster": ("native", ["x86-64", "arm64"], ["systems"]),
    "red": ("native", ["x86-64", "arm64"], ["data"]),
    "mercury": ("native", ["x86-64", "arm64"], ["query"]),
    "objectivec": ("native", ["x86-64", "arm64"], ["systems", "web"]),
    "eiffel": ("native", ["x86-64", "arm64"], ["systems"]),
    "bosque": ("native", ["x86-64", "arm64"], ["systems"]),
    "cobol": ("native", ["x86-64"], ["systems"]),
    "algol": ("native", ["x86-64"], ["systems"]),
    "bcpl": ("native", ["x86-64"], ["systems"]),
    "blang": ("native", ["x86-64"], ["systems"]),
    "simula": ("native", ["x86-64"], ["systems"]),
    "easylanguage": ("native", ["x86-64"], ["systems"]),
    "hanyu": ("native", ["x86-64"], ["systems"]),
    "xlang": ("native", ["x86-64"], ["systems"]),
    # 转译类（目标不是 JS）
    "goplus": ("transpiled", ["x86-64", "arm64"], ["systems"]),
    "haxe": ("transpiled", ["js", "jvm", "clr", "x86-64"], ["web", "systems"]),
    "zhpy": ("transpiled", ["host"], ["systems"]),
    # 验证/证明类（原被 category 默认误归 non-exec，逐条修正）
    "fstar": ("native", ["host"], ["systems"]),
    "whiley": ("bytecode-vm", ["jvm"], ["systems"]),
    # Factor 有完整优化编译器（可出原生），非纯解释
    "factor": ("native", ["x86-64", "arm64"], ["systems"]),
}

# esolang：明确归 host（解释器执行），不硬给架构
ESOLANG_IDS = {"brainfuck", "befunge", "intercal", "malbolge", "piet", "whitespace",
               "lolcode", "unlambda", "shakespeare", "chef", "wenyan"}


def infer(entry: dict):
    """未显式覆盖的条目：按 category 推断（诚实口径，_meta 会声明）。"""
    cat = entry.get("category", "")
    if entry["id"] in ESOLANG_IDS:
        return "interpreted", ["host"], ["systems"]
    if cat == "compiled":
        return "native", ["x86-64", "arm64"], ["systems"]
    if cat in ("interpreted",):
        return "interpreted", ["host"], ["systems"]
    if cat == "jit":
        return "jit", ["host"], ["systems"]
    if cat == "transpiled":
        return "transpiled", ["js"], ["web"]
    if cat == "ir":
        return "ir", ["wasm"], ["web"]
    if cat == "hdl":
        return "hdl", ["fpga"], ["systems"]
    return "non-exec", ["n-a"], ["systems"]


def build() -> dict:
    langs = json.loads(DATA.read_text(encoding="utf-8"))["languages"]
    index = {}
    for e in langs:
        lid = e["id"]
        if lid in EXPLICIT:
            model, archs, doms = EXPLICIT[lid]
            source = "explicit"
        else:
            model, archs, doms = infer(e)
            source = "inferred"
        index[lid] = {"name": e["name"], "model": model, "archs": archs,
                      "domains": doms, "mapping_source": source,
                      "own_standard": e.get("standard", ""),
                      "first_appeared": e.get("first_year", ""),
                      **_unpack_enrich(lid)}

    # 按架构反查（子分类视图）
    arch_langs: Dict[str, List[str]] = {a["arch"]: [] for a in ARCHS}
    for lid, v in index.items():
        for a in v["archs"]:
            arch_langs.setdefault(a, []).append(lid)
    for a in arch_langs:
        arch_langs[a].sort()

    # 按模型反查
    model_langs: Dict[str, List[str]] = {m["model"]: [] for m in MODELS}
    for lid, v in index.items():
        model_langs.setdefault(v["model"], []).append(lid)
    for m in model_langs:
        model_langs[m].sort()

    # 实测探针（若存在）
    probe = None
    if PROBE.exists():
        probe = json.loads(PROBE.read_text(encoding="utf-8"))

    return {
        "_meta": {
            "title": "编程语言概念系统（分层分类）",
            "system_root": "wordbuddy-github",
            "system_note": "以仓库 wordbuddy-github 为主目录的概念系统；语言知识来自 data/langs_docs.json",
            "version": "0000.0000.0000.0061.20261023",
            "lang_total": len(index),
            "axes": ["execution_model", "target_arch", "domain", "standard_basis"],
            "arch_note": "「有条件的以硬件架构为子分类」：能明确目标架构的语言按 arch 归类；"
                         "解释/JIT 归 host（取决于宿主进程）；配置/查询/标记等非执行类归 n-a。",
            "mapping_note": "mapping_source=explicit 为人工判定；=inferred 为按 category 推断（默认口径，可逐条细化）",
            "enrich_note": "v0.6.61 字段补全：每条语言增加 paradigm/typing/memory/first_appeared/gist/"
                           "engineering 六字段（数据见 research/plang/lang_enrich.py，first_appeared 取自"
                           " data/langs_docs.json 的 first_year）；engineering 遵守诚实口径——仅 probe 实测"
                           "通过的 15 种语言宣称可编译运行，其余只登记工具链名称不宣称结果，"
                           "非执行类与 esolang 如实标注",
            "rfc_note": "能力域的底层标准依据含 RFC 编号，构建时经本仓库 rfc_catalog 交叉验证存在性",
        },
        "execution_models": MODELS,
        "target_archs": ARCHS,
        "domains": DOMAINS,
        "model_langs": model_langs,
        "arch_langs": arch_langs,
        "lang_index": index,
        "probe": (probe or {}).get("_meta"),
        "probe_results": (probe or {}).get("results"),
    }


def check(doc: dict) -> List[str]:
    """校验：RFC 编号均在 rfc_catalog 中；架构/模型合法；覆盖完整。"""
    errs: List[str] = []
    sys.path.insert(0, str(HERE.parents[1] / "src" / "python"))
    try:
        from sysweeper.native import rfc_catalog as cat
    except Exception as ex:  # noqa: BLE001
        errs.append(f"无法加载 rfc_catalog：{ex}")
        cat = None

    if cat:
        for d in doc["domains"]:
            for s in d.get("standards", []):
                if s["kind"] != "RFC":
                    continue
                info = cat.rfc_info(s["num"])
                if info is None:
                    errs.append(f"域 {d['domain']} 引用 RFC {s['num']} 在 rfc_catalog 中不存在")
                else:
                    s["rfc_title"] = (info.get("t") or "")[:120]

    valid_archs = {a["arch"] for a in doc["target_archs"]}
    valid_models = {m["model"] for m in doc["execution_models"]}
    for lid, v in doc["lang_index"].items():
        for a in v["archs"]:
            if a not in valid_archs:
                errs.append(f"{lid} 架构 {a} 未登记")
        if v["model"] not in valid_models:
            errs.append(f"{lid} 执行模型 {v['model']} 未登记")

    langs = {e["id"] for e in json.loads(DATA.read_text(encoding="utf-8"))["languages"]}
    miss = langs - set(doc["lang_index"])
    if miss:
        errs.append(f"未覆盖的语言：{sorted(miss)[:20]}")

    # v0.6.61 字段补全覆盖性校验：六字段齐备，enrich 与数据层一一对应
    enrich_keys = set(LANG_ENRICH)
    stale = enrich_keys - langs
    if stale:
        errs.append(f"lang_enrich 存在数据层没有的语言（陈旧键）：{sorted(stale)}")
    for lid, v in doc["lang_index"].items():
        for f in ("paradigm", "typing", "memory", "first_appeared", "gist", "engineering"):
            if not str(v.get(f, "")).strip():
                errs.append(f"{lid} 补全字段 {f} 为空")
    # probe 实测口径一致性：标「实测通过」的语言必须在 probe_report 中真的通过
    probe_ok = {r["id"] for r in (doc.get("probe_results") or [])
                if r.get("status") == "实测通过"}
    for lid, v in doc["lang_index"].items():
        claims = "probe 实测通过" in v.get("engineering", "")
        passed = lid in probe_ok or (lid == "cplusplus" and "cpp" in probe_ok)
        if claims != passed:
            errs.append(f"{lid} 工程落法与 probe 实测口径不一致（标称 {claims} / 实测 {passed}）")
    return errs


def report(doc: dict) -> None:
    print(f"语言总数：{doc['_meta']['lang_total']}")
    print("\n按执行模型：")
    for m in doc["execution_models"]:
        n = len(doc["model_langs"].get(m["model"], []))
        print(f"  {m['model']:<14} {n:>3}  {m['label']}")
    print("\n按硬件架构（子分类，一条语言可属多个架构）：")
    for a in doc["target_archs"]:
        n = len(doc["arch_langs"].get(a["arch"], []))
        print(f"  [{a['kind']:<14}] {a['arch']:<10} {n:>3}  {a['label']}")
    probed = sum(1 for v in doc["lang_index"].values()
                 if "probe 实测通过" in v.get("engineering", ""))
    print(f"\n工程落法口径：{probed} 种 probe 实测通过；"
          f"{doc['_meta']['lang_total'] - probed} 种如实标注（未实测/宿主工具/esolang）")


def main(argv: List[str]) -> int:
    doc = build()
    if "--check" in argv:
        errs = check(doc)
        if errs:
            for e in errs:
                print("✗", e)
            return 1
        print(f"✓ 校验通过：{doc['_meta']['lang_total']} 条语言分类，RFC 引用全部命中 rfc_catalog，"
              "六补全字段齐备且 probe 口径一致")
        return 0
    if "--report" in argv:
        report(doc)
        return 0

    errs = check(doc)
    if errs:
        for e in errs:
            print("✗", e)
        return 1
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 已构建 {OUT}：{doc['_meta']['lang_total']} 条语言")
    report(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
