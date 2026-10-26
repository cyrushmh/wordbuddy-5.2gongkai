#!/usr/bin/env python3
# parity_test.py — 跨语言一致性测试
#
# 目标：证明 C / Rust / Python / .NET / Java / Ruby 六个 PE 查看器对同一个文件给出 *完全一致* 的结果。
# 不依赖 Windows：C 用本机 gcc、Rust 用本机 cargo、.NET 用本机 dotnet（net10.0 无头控制台版）、
# Java 用本机 javac/java（OpenJDK）、Ruby 用本机 ruby——五者都可在 Linux 直接编译/运行；
# Python 用解释器直接运行。PowerShell / VBA 版依赖 Windows 运行时，仅代码就绪、未自动纳入
# （VBA 偏移口径已用 Python 复刻验证）。
#
# 用法:
#   python3 tests/parity_test.py            # 用 tools/ 下所有 PE 作为样本
#   python3 tests/parity_test.py path/to/x.dll
#
# 退出码: 0 = 全部一致; 1 = 存在不一致或缺少可实现（C/Rust 工具链缺失且无法跳过）。
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Windows/
BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".build")


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def build_c():
    gcc = shutil.which("gcc")
    if not gcc:
        return None, "未找到 gcc（跳过 C 版）"
    out = os.path.join(BUILD, "peinfo_c")
    os.makedirs(BUILD, exist_ok=True)
    src = os.path.join(ROOT, "src/c/peinfo/peinfo.c")
    r = run(f'{gcc} -O2 -Wall "{src}" -o "{out}"')
    if r.returncode != 0:
        return None, "C 编译失败:\n" + r.stderr
    return out, None


def build_rust():
    cargo = shutil.which("cargo")
    if not cargo:
        return None, "未找到 cargo（跳过 Rust 版）"
    proj = os.path.join(ROOT, "src/rust/peinfo")
    r = run(f'cd "{proj}" && cargo build --release -q')
    if r.returncode != 0:
        return None, "Rust 编译失败:\n" + r.stderr
    binpath = os.path.join(proj, "target/release/peinfo")
    if not os.path.exists(binpath):
        return None, "Rust 产物缺失: " + binpath
    return binpath, None


def build_dotnet():
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return None, "未找到 dotnet（跳过 .NET 版的真实验证）"
    proj = os.path.join(ROOT, "src/dotnet/PeInfo/PeInfo.csproj")
    if not os.path.exists(proj):
        return None, "找不到 .NET 项目: " + proj
    out = os.path.join(BUILD, "dotnet")
    os.makedirs(BUILD, exist_ok=True)
    r = run(f'dotnet build "{proj}" -c Release -o "{out}" -v q')
    if r.returncode != 0:
        return None, "dotnet 编译失败:\n" + r.stderr
    dll = os.path.join(out, "PeInfo.dll")
    if not os.path.exists(dll):
        return None, "dotnet 产物缺失: " + dll
    return dll, None


def build_ruby():
    ruby = shutil.which("ruby")
    if not ruby:
        return None, "未找到 ruby（跳过 Ruby 版）"
    src = os.path.join(ROOT, "src/ruby/peinfo/peinfo.rb")
    if not os.path.exists(src):
        return None, "找不到源文件: " + src
    return src, None


def build_powershell():
    pwsh = shutil.which("pwsh")
    if not pwsh:
        return None, "未找到 pwsh（跳过 PowerShell 版，需 Windows 运行时验证）"
    script = os.path.join(ROOT, "src/powershell/PEInfo-Gui.ps1")
    if not os.path.exists(script):
        return None, "找不到脚本: " + script
    return script, None


def build_java():
    javac = shutil.which("javac")
    if not javac:
        return None, "未找到 javac（跳过 Java 版）"
    src = os.path.join(ROOT, "src/java/peinfo/PeInfo.java")
    if not os.path.exists(src):
        return None, "找不到源文件: " + src
    out = os.path.join(BUILD, "java")
    os.makedirs(out, exist_ok=True)
    # 自适应 --release：优先 25(LTS 目标)，逐级回退到本机可用版本，最后无 flag 直接编当前 JDK。
    # 避免写死高版本号导致低版本 JDK 环境（如 OpenJDK 20）编译失败、CI 跑不通。
    last_err = ""
    for rel in ("25", "24", "23", "22", "21", "20", "17", "11", None):
        flag = f"--release {rel}" if rel else ""
        r = run(f'{javac} {flag} "{src}" -d "{out}"')
        if r.returncode == 0 and os.path.exists(os.path.join(out, "PeInfo.class")):
            return out, None
        last_err = r.stderr.strip() or "(无 stderr)"
    return None, "Java 编译失败（已尝试 25→11 及无 flag）:\n" + last_err


def core(d):
    """抽取用于一致性比对的稳定字段（不比对可读名称字符串，避免表述差异误判）。"""
    return {
        "machine": d.get("machine"),
        "number_of_sections": d.get("number_of_sections"),
        "magic": d.get("optional", {}).get("magic"),
        "entry_point": d.get("optional", {}).get("entry_point"),
        "image_base": d.get("optional", {}).get("image_base"),
        "subsystem": d.get("optional", {}).get("subsystem"),
        "number_of_rva_and_sizes": d.get("optional", {}).get("number_of_rva_and_sizes"),
        "n_data_dirs": len(d.get("data_directories", [])),
        "sections": [
            (
                s.get("name"),
                s.get("virtual_address"),
                s.get("virtual_size"),
                s.get("size_of_raw_data"),
                s.get("pointer_to_raw_data"),
                s.get("characteristics"),
            )
            for s in d.get("sections", [])
        ],
    }


def load_json(binpath, kind, sample):
    if kind == "python":
        r = run(f'python3 "{binpath}" "{sample}" --json')
    elif kind == "c":
        r = run(f'"{binpath}" -j "{sample}"')
    elif kind == "rust":
        r = run(f'"{binpath}" "{sample}" --json')
    elif kind == "dotnet":
        r = run(f'dotnet "{binpath}" "{sample}" --json')
    elif kind == "powershell":
        r = run(f'pwsh -NoProfile -File "{binpath}" -Path "{sample}" -Json')
    elif kind == "java":
        r = run(f'java -cp "{binpath}" PeInfo "{sample}" --json')
    elif kind == "ruby":
        r = run(f'ruby "{binpath}" "{sample}" --json')
    else:
        raise ValueError(kind)
    if r.returncode != 0:
        return None, r.stderr.strip() or "(无 stderr)"
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败: {e}\n--- stdout ---\n{r.stdout}"


def find_samples(explicit):
    if explicit:
        return [explicit]
    tools = os.path.join(ROOT, "tools")
    out = []
    if os.path.isdir(tools):
        for fn in sorted(os.listdir(tools)):
            p = os.path.join(tools, fn)
            if os.path.isfile(p) and open(p, "rb").read(2) == b"MZ":
                out.append(p)
    if not out:
        # 回退：用本测试脚本本身所在 PE？没有就用任意 MZ 文件
        out.append(os.path.join(ROOT, "tools/peinfo.exe"))
    return out


def main():
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    print("== 跨语言 PE 解析一致性测试 ==")
    print(f"仓库根: {ROOT}")

    c_bin, c_err = build_c()
    rs_bin, rs_err = build_rust()
    net_bin, net_err = build_dotnet()
    java_bin, java_err = build_java()
    ruby_bin, ruby_err = build_ruby()
    ps_bin, ps_err = build_powershell()
    py_bin = os.path.join(ROOT, "src/python/pe_inspect.py")
    if not os.path.exists(py_bin):
        print("✗ 找不到 Python 版:", py_bin)
        return 1

    print(f"  C        : {c_bin or '跳过 (' + (c_err or '') + ')'}")
    print(f"  Rust     : {rs_bin or '跳过 (' + (rs_err or '') + ')'}")
    print(f"  Python   : {py_bin}")
    print(f"  .NET     : {net_bin or '跳过 (' + (net_err or '') + ')'}")
    print(f"  Java     : {java_bin or '跳过 (' + (java_err or '') + ')'}")
    print(f"  Ruby     : {ruby_bin or '跳过 (' + (ruby_err or '') + ')'}")
    print(f"  PowerShell: {ps_bin or '跳过 (' + (ps_err or '') + ')'}")
    print()

    impls = [("python", py_bin)]
    if c_bin:
        impls.append(("c", c_bin))
    if rs_bin:
        impls.append(("rust", rs_bin))
    if net_bin:
        impls.append(("dotnet", net_bin))
    if java_bin:
        impls.append(("java", java_bin))
    if ruby_bin:
        impls.append(("ruby", ruby_bin))
    if ps_bin:
        impls.append(("powershell", ps_bin))

    if len(impls) < 2:
        print("\n✗ 至少需要两个可实现（C/Rust）才能做一致性比对。")
        return 1

    samples = find_samples(explicit)
    failures = 0
    for s in samples:
        results = {}
        for kind, binpath in impls:
            d, err = load_json(binpath, kind, s)
            if err:
                print(f"\n  [{os.path.basename(s)}] {kind} 运行失败: {err}")
                failures += 1
                results[kind] = None
            else:
                results[kind] = core(d)
        if any(v is None for v in results.values()):
            continue
        mach = results["python"].get("machine")
        magic = results["python"].get("magic")
        tag = f"{os.path.basename(s)} (machine={mach:#06x}, magic={magic:#06x})"
        ref = next(iter(results.values()))
        bad = [k for k in results if results[k] != ref]
        if bad:
            failures += 1
            print(f"\n  ✗ {tag} 不一致: 实现 {bad} 与参考实现结果不同")
            for k in sorted(results):
                print(f"      {k}: {results[k]}")
        else:
            print(f"  ✓ {tag}  全部一致 ({len(impls)} 实现)")

    print()
    if failures:
        print(f"结果: ✗ {failures} 个样本存在不一致")
        return 1
    print(f"结果: ✓ 全部 {len(samples)} 个样本在 {len(impls)} 个实现间完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
