#!/usr/bin/env python3
"""syspkg —— 仓库统一打包器（**语言底层：Python 3.8+，纯标准库**）。

设计原则
--------
本项目把 **Python 3** 当作"语言底层"：多数 Linux / macOS / BSD 发行版自带，
Windows 一条命令就能装，且本包零第三方依赖。因此本打包器：

* 只用标准库（zipapp / zipfile / tarfile / hashlib / subprocess），
  不 require setuptools、wheel、build、pip 任何东西；
* 首推产物是 **单文件 .pyz**（zipapp）：任一有 python3 的机器
  `python3 sysweeper-0.5.22.pyz detect` 即可跑，跨系统跨硬件通用；
* Go / Rust / Kotlin(Android) 视为"可选加速层"：探测到工具链才构建，
  探测不到就跳过，**永不因此失败**。

用法
----
    python3 tools/syspkg.py probe      # 探测本机有哪些语言工具链 / 能产出什么
    python3 tools/syspkg.py targets    # 列出支持的（系统 × 硬件）矩阵
    python3 tools/syspkg.py pyz        # 单文件 .pyz（推荐，零依赖）
    python3 tools/syspkg.py wheel      # 纯标准库手写 wheel（pip 可装）
    python3 tools/syspkg.py sdist      # 源码分发 tar.gz
    python3 tools/syspkg.py go         # Go 交叉编译（按硬件矩阵）
    python3 tools/syspkg.py rust       # cargo 构建（Windows 子项目）
    python3 tools/syspkg.py android    # Gradle 构建 Android 14 APK
    python3 tools/syspkg.py smoke      # 对 dist/ 里的 .pyz 冒烟
    python3 tools/syspkg.py all        # 能打的都打，缺工具链自动跳过

通用参数：`--out DIR`（默认 `<repo>/dist`）、`--version X.Y.Z`、`--json`。

安全底线：只读 + 只写 `dist/`，不改任何系统设置。
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipapp
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_SRC = ROOT / "system-optimizer" / "src" / "python"
PY_PROJ = ROOT / "system-optimizer" / "pyproject.toml"
PY_README = ROOT / "system-optimizer" / "README.md"
GO_SRC = ROOT / "system-optimizer" / "src" / "go"
ANDROID_DIR = ROOT / "android"
RUST_DIRS = [ROOT / "Windows" / "src" / "rust" / "peinfo",
             ROOT / "Windows" / "src" / "rust" / "peview-egui"]
DEFAULT_OUT = ROOT / "dist"
PACKAGE = "sysweeper"

# ---------------------------------------------------------------- 硬件矩阵

# Go：CGO_ENABLED=0 纯静态交叉编译，覆盖各系统 × 主流硬件架构
GO_TARGETS = [
    ("linux", "amd64", ""),
    ("linux", "arm64", ""),
    ("linux", "riscv64", ""),
    ("windows", "amd64", ".exe"),
    ("windows", "arm64", ".exe"),
    ("darwin", "arm64", ""),
    ("darwin", "amd64", ""),
]

# Android：按 ABI（硬件指令集）拆包 + universal
ANDROID_ABIS = ["arm64-v8a", "armeabi-v7a", "x86_64"]

# 语言底层（Python）目标：纯 Python 产物，与硬件无关（noarch）
PY_TARGETS = ["pyz", "wheel", "sdist"]


# ---------------------------------------------------------------- 基础工具


def which(name: str):
    return shutil.which(name)


def run(cmd, cwd=None, env=None, timeout=1800):
    """跑一条命令，返回 (rc, 合并输出)。"""
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    out = p.stdout.decode("utf-8", "replace") if isinstance(p.stdout, bytes) else (p.stdout or "")
    return p.returncode, out.strip()


def tool_version(cmd, timeout=60):
    """取工具版本串；找不到返回 None。"""
    if which(cmd[0]) is None and not os.path.exists(cmd[0]):
        return None
    rc, out = run(cmd, timeout=timeout)
    if rc != 0:
        return None
    if not out:
        return "unknown"
    for line in out.splitlines():          # 有的工具（gradle）首行是分隔线
        if re.search(r"\d", line):
            return line.strip()
    return out.splitlines()[0].strip()


def sha256_record(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return "sha256=" + digest.decode("ascii")


# ---------------------------------------------------------------- 元数据


def parse_pyproject() -> dict:
    """极简 PEP 621 解析（只取打包需要的字段，避免引入 tomllib 依赖）。

    Python 3.11+ 有 tomllib，但本文件要能在 3.8 上跑，故统一用正则。
    """
    text = PY_PROJ.read_text(encoding="utf-8") if PY_PROJ.exists() else ""
    meta = {
        "version": "0.0.0",
        "summary": "跨系统 / 跨语言 / 跨平台的系统优化与清理任务库",
        "requires_python": ">=3.8",
        "license": "MIT",
        "keywords": [],
        "classifiers": [],
    }

    def scalar(key):
        m = re.search(r'^\s*%s\s*=\s*"([^"]*)"' % re.escape(key), text, re.M)
        return m.group(1) if m else None

    for key in ("version", "requires-python", "license"):
        val = scalar(key)
        if val:
            meta[key.replace("-", "_")] = val
    if scalar("description"):
        meta["summary"] = scalar("description")

    m = re.search(r"^\s*keywords\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if m:
        meta["keywords"] = re.findall(r'"([^"]+)"', m.group(1))
    m = re.search(r"^\s*classifiers\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if m:
        meta["classifiers"] = re.findall(r'"([^"]+)"', m.group(1))
    return meta


def project_version(cli_version=None) -> str:
    if cli_version:
        return cli_version
    return parse_pyproject()["version"]


# ---------------------------------------------------------------- 探测


def probe() -> dict:
    """探测本机语言工具链 + 可产出目标。"""
    tools = {}

    def add(key, cmd, note=""):
        ver = tool_version(cmd) if cmd else None
        tools[key] = {
            "found": ver is not None,
            "version": ver or "",
            "path": which(cmd[0]) if cmd else "",
            "note": note,
        }

    add("python3", ["python3", "--version"], "语言底层：几乎所有 Linux/macOS/BSD 自带")
    add("go", ["go", "version"], "可选加速层：交叉编译多硬件二进制")
    add("rustc", ["rustc", "--version"], "可选加速层：Windows PE 解析原生实现")
    add("cargo", ["cargo", "--version"], "Rust 构建器")
    add("java", ["java", "-version"], "Android 构建需要 JDK 17+（Android 的语言底层是 ART/Java）")
    add("gradle", ["gradle", "--version"], "可选：本机 Gradle（否则用 android/gradlew）")
    add("adb", ["adb", "version"], "可选：免装 APK、用 adb 只读审计 Android 设备")

    java_ok = False
    jv = tools["java"]["version"]
    if jv:
        m = re.search(r"(\d+)", jv.replace('"', ""))
        if m and int(m.group(1)) >= 17:
            java_ok = True

    artifacts = list(PY_TARGETS)  # Python 语言底层：永远能产出
    if tools["go"]["found"]:
        artifacts += [f"go-{os_}-{arch}" for os_, arch, _ in GO_TARGETS]
    if tools["cargo"]["found"]:
        artifacts.append("rust-native")
    if java_ok and (ANDROID_DIR / "gradlew").exists():
        artifacts += [f"android-{abi}" for abi in ANDROID_ABIS] + ["android-universal"]

    return {
        "host": {
            "system": platform.system().lower(),
            "machine": platform.machine().lower(),
            "python": platform.python_version(),
        },
        "tools": tools,
        "artifacts": artifacts,
        "skipped": _skipped(tools, java_ok),
    }


def _skipped(tools, java_ok) -> list:
    out = []
    if not tools["go"]["found"]:
        out.append({"target": "go-*", "reason": "未检测到 go，跳过 Go 交叉编译（不影响 Python 产物）"})
    if not tools["cargo"]["found"]:
        out.append({"target": "rust-native", "reason": "未检测到 cargo，跳过 Rust 构建"})
    if not java_ok:
        out.append({"target": "android-*", "reason": "未检测到 JDK 17+，跳过 APK 构建"})
    if not tools["adb"]["found"]:
        out.append({"target": "android-audit", "reason": "未检测到 adb，跳过设备端只读审计（仍可用 APK）"})
    return out


def print_probe(info: dict, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    host = info["host"]
    print(f"主机：{host['system']} / {host['machine']} / Python {host['python']}")
    print("")
    print(f"{'工具':<10}{'状态':<8}{'版本':<28}说明")
    print("-" * 96)
    for key, t in info["tools"].items():
        status = "有" if t["found"] else "缺"
        print(f"{key:<10}{status:<8}{t['version'][:26]:<28}{t['note']}")
    print("")
    print("可产出目标：" + ", ".join(info["artifacts"]))
    if info["skipped"]:
        print("")
        print("跳过（缺工具链，非错误）：")
        for s in info["skipped"]:
            print(f"  - {s['target']}: {s['reason']}")


def print_targets(as_json: bool = False) -> None:
    rows = []
    for name in PY_TARGETS:
        rows.append({"layer": "L0 Python（语言底层，多数系统默认有）", "target": name,
                     "os": "任意（有 python3.8+ 即可）", "arch": "noarch"})
    for os_, arch, ext in GO_TARGETS:
        rows.append({"layer": "L1 Go（可选加速层）", "target": f"go-{os_}-{arch}",
                     "os": os_, "arch": arch})
    for abi in ANDROID_ABIS + ["universal"]:
        rows.append({"layer": "L2 Kotlin/ART（Android 语言底层）", "target": f"android-{abi}",
                     "os": "android 13+（targetSdk 34）", "arch": abi})
    rows.append({"layer": "L1 Rust（可选加速层）", "target": "rust-native",
                 "os": "本机", "arch": platform.machine().lower()})
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print(f"{'层':<34}{'目标':<26}{'系统':<26}硬件")
    print("-" * 104)
    for r in rows:
        print(f"{r['layer']:<34}{r['target']:<26}{r['os']:<26}{r['arch']}")


# ---------------------------------------------------------------- L0：Python


def build_pyz(out: Path, version: str, log=print) -> list:
    """单文件 .pyz（zipapp）。任一有 python3 的机器可直接跑。"""
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{PACKAGE}-{version}.pyz"

    def _keep(p: Path) -> bool:
        return "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != ".DS_Store"

    if target.exists():
        target.unlink()
    zipapp.create_archive(
        str(PY_SRC), str(target),
        interpreter="/usr/bin/env python3",
        main=f"{PACKAGE}.__main__:main",
        filter=_keep,
    )
    try:
        target.chmod(0o755)
    except OSError:
        pass
    log(f"  [pyz]   {target}  ({target.stat().st_size / 1024:.0f} KB)")
    return [str(target)]


def _wheel_entries():
    """收集 wheel 内的包文件：(arcname, data)。"""
    entries = []
    root = PY_SRC / PACKAGE
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(PY_SRC)
        if "__pycache__" in rel.parts or path.suffix in (".pyc", ".pyo"):
            continue
        if path.suffix not in (".py", ".json", ".txt", ".md"):
            continue
        entries.append((rel.as_posix(), path.read_bytes()))
    return entries


def build_wheel(out: Path, version: str, log=print) -> list:
    """纯标准库手写 wheel（PEP 427）。不依赖 setuptools / build / wheel。"""
    out.mkdir(parents=True, exist_ok=True)
    meta = parse_pyproject()
    tag = "py3-none-any"
    dist_info = f"{PACKAGE}-{version}.dist-info"
    wheel_path = out / f"{PACKAGE}-{version}-{tag}.whl"

    readme = ""
    if PY_README.exists():
        readme = PY_README.read_text(encoding="utf-8")

    metadata = [
        "Metadata-Version: 2.1",
        f"Name: {PACKAGE}",
        f"Version: {version}",
        f"Summary: {meta['summary']}",
        f"License: {meta['license']}",
        f"Requires-Python: {meta['requires_python']}",
    ]
    if meta["keywords"]:
        metadata.append("Keywords: " + ",".join(meta["keywords"]))
    for c in meta["classifiers"]:
        metadata.append(f"Classifier: {c}")
    metadata.append("Description-Content-Type: text/markdown")
    metadata.append("")
    metadata.append(readme)
    metadata_text = "\n".join(metadata)

    wheel_meta = "\n".join([
        "Wheel-Version: 1.0",
        "Generator: syspkg.py (Python stdlib, no setuptools)",
        "Root-Is-Purelib: true",
        f"Tag: {tag}",
        "",
    ])
    entry_points = "[console_scripts]\nsysweeper = sysweeper.cli:main\n"

    blobs = [(f"{dist_info}/METADATA", metadata_text.encode("utf-8")),
             (f"{dist_info}/WHEEL", wheel_meta.encode("utf-8")),
             (f"{dist_info}/entry_points.txt", entry_points.encode("utf-8")),
             (f"{dist_info}/top_level.txt", (PACKAGE + "\n").encode("utf-8"))]
    blobs += [(arc, data) for arc, data in _wheel_entries()]

    records = []
    with zipfile.ZipFile(wheel_path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in blobs:
            z.writestr(arc, data)
            records.append(f"{arc},{sha256_record(data)},{len(data)}")
        records.append(f"{dist_info}/RECORD,,")
        z.writestr(f"{dist_info}/RECORD", "\n".join(records) + "\n")

    log(f"  [wheel] {wheel_path}  ({wheel_path.stat().st_size / 1024:.0f} KB)")
    return [str(wheel_path)]


def build_sdist(out: Path, version: str, log=print) -> list:
    """源码分发 tar.gz。"""
    out.mkdir(parents=True, exist_ok=True)
    meta = parse_pyproject()
    base = f"{PACKAGE}-{version}"
    tar_path = out / f"{base}.tar.gz"

    pkg_info = "\n".join([
        "Metadata-Version: 2.1",
        f"Name: {PACKAGE}",
        f"Version: {version}",
        f"Summary: {meta['summary']}",
        f"License: {meta['license']}",
        f"Requires-Python: {meta['requires_python']}",
        "",
    ])

    with tarfile.open(tar_path, "w:gz") as tar:
        _tar_add_text(tar, f"{base}/PKG-INFO", pkg_info)
        for src, arc in ((PY_PROJ, f"{base}/pyproject.toml"),
                         (PY_README, f"{base}/README.md"),
                         (ROOT / "LICENSE", f"{base}/LICENSE")):
            if src.exists():
                tar.add(str(src), arcname=arc)
        for path in sorted((PY_SRC / PACKAGE).rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(PY_SRC)
            if "__pycache__" in rel.parts or path.suffix in (".pyc", ".pyo"):
                continue
            tar.add(str(path), arcname=f"{base}/src/python/{rel.as_posix()}")
        tests = ROOT / "system-optimizer" / "tests"
        if tests.exists():
            for path in sorted(tests.glob("*.py")):
                tar.add(str(path), arcname=f"{base}/tests/{path.name}")

    log(f"  [sdist] {tar_path}  ({tar_path.stat().st_size / 1024:.0f} KB)")
    return [str(tar_path)]


def _tar_add_text(tar: tarfile.TarFile, arcname: str, text: str) -> None:
    data = text.encode("utf-8")
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    info.mtime = 0
    tar.addfile(info, io.BytesIO(data))


# ---------------------------------------------------------------- L1：Go / Rust


def build_go(out: Path, version: str, log=print, only=None) -> list:
    if which("go") is None:
        log("  [go]    跳过：未检测到 go")
        return []
    out.mkdir(parents=True, exist_ok=True)
    produced = []
    for goos, goarch, ext in GO_TARGETS:
        if only and f"{goos}-{goarch}" not in only:
            continue
        name = f"{PACKAGE}-go-{goos}-{goarch}{ext}"
        target = out / name
        env = dict(os.environ, GOOS=goos, GOARCH=goarch, CGO_ENABLED="0")
        rc, msg = run(["go", "build", "-trimpath", "-ldflags", "-s -w",
                       "-o", str(target), "."], cwd=str(GO_SRC), env=env)
        if rc == 0 and target.exists():
            log(f"  [go]     {target.name}  ({target.stat().st_size / 1024:.0f} KB)")
            produced.append(str(target))
        else:
            log(f"  [go]     {goos}/{goarch} 失败（跳过）：{msg.splitlines()[0] if msg else rc}")
    return produced


def build_rust(out: Path, version: str, log=print) -> list:
    if which("cargo") is None:
        log("  [rust]  跳过：未检测到 cargo")
        return []
    out.mkdir(parents=True, exist_ok=True)
    produced = []
    for proj in RUST_DIRS:
        if not (proj / "Cargo.toml").exists():
            continue
        rc, msg = run(["cargo", "build", "--release"], cwd=str(proj), timeout=2400)
        if rc != 0:
            log(f"  [rust]  {proj.name} 构建失败（跳过）：{msg.splitlines()[0] if msg else rc}")
            continue
        for exe in sorted((proj / "target" / "release").glob("*")):
            if exe.is_file() and (exe.suffix == ".exe" or os.access(str(exe), os.X_OK)) \
                    and not exe.name.endswith((".d", ".rlib", ".rmeta")):
                dest = out / f"{proj.name}-{exe.name}"
                shutil.copy2(str(exe), str(dest))
                log(f"  [rust]   {dest.name}  ({dest.stat().st_size / 1024:.0f} KB)")
                produced.append(str(dest))
    return produced


# ---------------------------------------------------------------- L2：Android


def build_android(out: Path, version: str, log=print) -> list:
    gradlew = ANDROID_DIR / "gradlew"
    if not gradlew.exists():
        log("  [android] 跳过：无 android/gradlew")
        return []
    jv = tool_version(["java", "-version"]) or ""
    m = re.search(r"(\d+)", jv.replace('"', ""))
    if not m or int(m.group(1)) < 17:
        log("  [android] 跳过：需要 JDK 17+（当前：" + (jv or "未检测到 java") + "）")
        return []
    out.mkdir(parents=True, exist_ok=True)
    gradlew_cmd = ["bash", str(gradlew)] if os.name != "nt" else [str(gradlew.with_suffix(".bat"))]
    rc, msg = run(gradlew_cmd + ["assembleRelease", "--no-daemon", "-q"],
                  cwd=str(ANDROID_DIR), timeout=3600)
    if rc != 0:
        log("  [android] assembleRelease 失败（跳过）：" + (msg.splitlines()[-1] if msg else str(rc)))
        return []
    produced = []
    apk_dir = ANDROID_DIR / "app" / "build" / "outputs" / "apk" / "release"
    for apk in sorted(apk_dir.glob("*.apk")):
        dest = out / f"{PACKAGE}-android-{version}-{apk.name}"
        shutil.copy2(str(apk), str(dest))
        log(f"  [android] {dest.name}  ({dest.stat().st_size / 1024:.0f} KB)")
        produced.append(str(dest))
    if not produced:
        log("  [android] 构建成功但未找到 apk 产物")
    return produced


# ---------------------------------------------------------------- 命令分发


BUILDERS = {
    "pyz": build_pyz,
    "wheel": build_wheel,
    "sdist": build_sdist,
    "go": build_go,
    "rust": build_rust,
    "android": build_android,
}


SMOKE_CASES = [
    ["detect"],
    ["hardware"],
    ["android"],
    ["--platform", "windows", "--version", "11", "list"],
    # lowcode 低层码制（v0.6.0）：概览 + 每层各挑一例，确保子包随 .pyz 一起打包成功
    ["code"],
    ["code", "bits", "--value", "-7", "--width", "8"],
    ["code", "chars", "--value", "中文", "--action", "charset"],
    ["code", "comm", "--value", "010300000001", "--action", "crc"],
    ["code", "logic", "--value", "A & B | !C", "--action", "simplify"],
    ["code", "machine", "--action", "py", "--value", "x = 1 + 2"],
]


def cmd_smoke(out: Path, version: str, as_json: bool) -> int:
    """对 dist/ 里的 .pyz 做冒烟：能跑、有输出、知识库没被静默吞掉。"""
    hits = sorted(out.glob(f"{PACKAGE}-*.pyz"))
    if not hits:
        msg = f"未找到 .pyz（请先运行：python3 tools/syspkg.py pyz --out {out}）"
        print(msg, file=sys.stderr)
        return 1
    pyz = hits[-1]
    results = []
    ok = True
    for case in SMOKE_CASES:
        rc, text = run([sys.executable, str(pyz)] + case, timeout=180)
        first = next((l for l in text.splitlines() if l.strip()), "")
        results.append({"argv": case, "rc": rc, "first_line": first,
                        "chars": len(text)})
        if rc != 0 or len(text) < 20:
            ok = False
    if as_json:
        print(json.dumps({"pyz": str(pyz), "results": results, "ok": ok},
                         ensure_ascii=False, indent=2))
    else:
        print(f"冒烟对象：{pyz}\n")
        for r in results:
            flag = "OK " if r["rc"] == 0 and r["chars"] >= 20 else "FAIL"
            print(f"  [{flag}] {' '.join(r['argv']):<42} rc={r['rc']} "
                  f"{r['chars']} 字符 | {r['first_line'][:40]}")
        print("\n冒烟结果：" + ("全部通过" if ok else "存在失败"))
    return 0 if ok else 1


def cmd_all(out: Path, version: str, as_json: bool) -> int:
    info = probe()
    produced = {}
    log = (lambda *a: None) if as_json else print
    if not as_json:
        print(f"输出目录：{out}")
        print(f"版本：{version}\n")
    for key in ("pyz", "wheel", "sdist", "go", "rust", "android"):
        produced[key] = BUILDERS[key](out, version, log=log)
    total = sum(len(v) for v in produced.values())
    if as_json:
        print(json.dumps({"version": version, "out": str(out),
                          "artifacts": produced, "count": total,
                          "skipped": info["skipped"]},
                         ensure_ascii=False, indent=2))
    else:
        print("")
        print(f"共 {total} 个产物；跳过项 {len(info['skipped'])} 个（缺工具链，非错误）")
        for s in info["skipped"]:
            print(f"  - {s['target']}: {s['reason']}")
    return 0 if any(produced.values()) else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="syspkg",
        description="仓库统一打包器（语言底层 = Python 3，纯标准库；Go/Rust/Kotlin 为可选加速层）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：python3 tools/syspkg.py all --out /tmp/dist")
    parser.add_argument("command",
                        choices=["probe", "targets", "pyz", "wheel", "sdist",
                                 "go", "rust", "android", "smoke", "all"],
                        help="probe=探测工具链 / targets=硬件矩阵 / smoke=pyz 冒烟 / all=能打的都打")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="产物输出目录")
    parser.add_argument("--version", default=None, help="覆盖版本号（默认读 pyproject.toml）")
    parser.add_argument("--only", default=None,
                        help="仅构建指定目标（逗号分隔，如 go:linux-amd64,windows-arm64）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args(argv)

    version = project_version(args.version)
    out = Path(args.out).resolve()

    if args.command == "probe":
        print_probe(probe(), args.json)
        return 0
    if args.command == "targets":
        print_targets(args.json)
        return 0
    if args.command == "all":
        return cmd_all(out, version, args.json)
    if args.command == "smoke":
        return cmd_smoke(out, version, args.json)

    builder = BUILDERS[args.command]
    log = (lambda *a: None) if args.json else print
    if not args.json:
        print(f"输出目录：{out}")
    only = args.only.split(",") if args.only else None
    if args.command == "go":
        produced = builder(out, version, log=log, only=only)
    else:
        produced = builder(out, version, log=log)
    if args.json:
        print(json.dumps({"version": version, "out": str(out), "artifacts": produced},
                         ensure_ascii=False, indent=2))
    return 0 if produced else 1


if __name__ == "__main__":
    sys.exit(main())
