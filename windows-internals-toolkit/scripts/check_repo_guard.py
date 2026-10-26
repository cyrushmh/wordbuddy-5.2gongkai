#!/usr/bin/env python3
"""仓库安全护栏：CI 第一道关（参考 DiPlay 的 scripts/check_public_tree.py）。

检查五件事，任一命中即失败（exit 1）：

1. **凭据容器**：git 跟踪文件里出现 `.pk8 .p7b .pem .key .p12 .pfx .jks .keystore
   .apk .aab .p8 .idsig` 等后缀，或路径中含 `.private` / `secrets` 目录；
2. **私钥块**：文件内容里出现 `-----BEGIN ... PRIVATE KEY-----`；
3. **Android 权限白名单**：`android/app/src/main/AndroidManifest.xml` 里出现的
   `uses-permission` 必须全部在白名单内（防止某天顺手加个危险权限）。
4. **许可证白名单**：本项目采用宽松许可（MIT/Apache/BSD 等）。顶层 LICENSE 不得是
   强拷贝左（GPL/AGPL/LGPL/EUPL/OSL/CC-BY-SA）；自有源码（排除 vendor/第三方/
   分析文档）的 `SPDX-License-Identifier` 也不得是强拷贝左。导入分析里可以**讨论**
   强拷贝左仓库（如 mihomo 的 GPL-3.0），但不得把其许可带入本项目源码。
5. **生成产物 SHA 同步**：`report_viewer.html` 由 `report_viewer.ts` 的 `page()`
   模板抽取生成，须在顶部注释写入「源模板 SHA256」。若源模板变了却没重生成，
   或标记缺失，即判定失同步（防止「改了 .ts 忘了重生成 html」的静默错位）。

纯标准库实现，只读，不改任何文件。用法：

    python3 scripts/check_repo_guard.py [--root 仓库根] [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BLOCKED_SUFFIXES = {
    ".pk8", ".p7b", ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore",
    ".apk", ".aab", ".p8", ".idsig", ".kdbx", ".ppk",
}
BLOCKED_DIR_PARTS = {".private", "secrets", "private_keys"}
PRIVATE_BLOCK = re.compile(
    rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{40,}")

# Android：只读诊断 App 允许的权限（INTERNET 仅供调试期日志；正式构建建议去掉）
ALLOWED_PERMISSIONS = {
    "android.permission.INTERNET",
}
MANIFEST_REL = "android/app/src/main/AndroidManifest.xml"

ANDROID_NS = "{http://schemas.android.com/apk/res/android}name"


def tracked_files(root: Path) -> list:
    """用 git ls-files；不在 git 仓库里时退回遍历（跳过 .git）。"""
    try:
        out = subprocess.check_output(["git", "ls-files", "-z"], cwd=str(root),
                                      stderr=subprocess.DEVNULL)
        names = [n for n in out.decode("utf-8", "replace").split("\0") if n]
        return [root / n for n in names]
    except Exception:
        files = []
        for path in root.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                files.append(path)
        return files


def scan_tree(root: Path) -> list:
    failures = []
    for path in tracked_files(root):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = set(p.lower() for p in rel.parts)
        if parts & BLOCKED_DIR_PARTS or path.suffix.lower() in BLOCKED_SUFFIXES:
            failures.append(f"凭据/分发容器文件：{rel}")
            continue
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                continue                      # 大文件跳过内容扫描（APK 等已被后缀拦）
            data = path.read_bytes()
        except OSError:
            continue
        if PRIVATE_BLOCK.search(data):
            failures.append(f"文件内含私钥块：{rel}")
    return failures


def scan_manifest(root: Path) -> list:
    manifest = root / MANIFEST_REL
    if not manifest.exists():
        return []
    try:
        tree = ET.parse(str(manifest))
    except ET.ParseError as exc:
        return [f"AndroidManifest.xml 解析失败：{exc}"]
    failures = []
    for node in tree.getroot().iter("uses-permission"):
        name = node.attrib.get(ANDROID_NS) or node.attrib.get("name") or ""
        if not name:
            failures.append("AndroidManifest.xml 有空的 uses-permission")
        elif name not in ALLOWED_PERMISSIONS:
            failures.append(
                f"AndroidManifest 声明了白名单外的权限：{name}"
                f"（当前白名单：{sorted(ALLOWED_PERMISSIONS)}；"
                f"确属必要时请显式加入 ALLOWED_PERMISSIONS 并说明理由）")
    return failures


# ─────────────────────────────────────────────────────────────────────────────
# 4. 许可证白名单（项目自身须宽松；强拷贝左不得进入源码）
# ─────────────────────────────────────────────────────────────────────────────

COPYLEFT_KEYWORDS = (
    "GNU GENERAL PUBLIC LICENSE",
    "GNU LESSER GENERAL PUBLIC LICENSE",
    "GNU AFFERO GENERAL PUBLIC LICENSE",
    "GNU LIBRARY GENERAL PUBLIC LICENSE",
)
COPYLEFT_SPDX = {
    "GPL", "GPL-2.0", "GPL-3.0", "AGPL", "AGPL-3.0",
    "LGPL", "LGPL-2.0", "LGPL-2.1", "LGPL-3.0",
    "EUPL", "EUPL-1.2", "OSL", "OSL-3.0", "CC-BY-SA", "CC-BY-SA-4.0",
}
SOURCE_SUFFIXES = {
    ".py", ".ts", ".go", ".js", ".vue", ".rs", ".java", ".kt",
    ".c", ".h", ".cpp", ".cc", ".hpp",
}
LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
EXCLUDE_DIR_PARTS = {".private", "secrets", "private_keys",
                     "vendor", "third_party", "node_modules", "imports",
                     "tests", "docs"}
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.\-]+)")


def _is_copyleft(text: str) -> str | None:
    up = text.upper()
    for kw in COPYLEFT_KEYWORDS:
        if kw in up:
            return kw
    return None


def scan_licenses(root: Path) -> list:
    """项目自身许可须宽松；强拷贝左只许出现在「被分析」的文档里，不许进源码。"""
    failures = []
    for name in LICENSE_FILES:
        lic = root / name
        if lic.exists():
            try:
                txt = lic.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hit = _is_copyleft(txt)
            if hit:
                failures.append(
                    f"顶层 {name} 为强拷贝左许可（{hit}）；本项目采用宽松许可，禁止引入强拷贝左")
            break  # 只认第一个存在的顶层许可文件
    for path in tracked_files(root):
        rel = path.relative_to(root)
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if EXCLUDE_DIR_PARTS & set(rel.parts):
            continue
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
        except OSError:
            continue
        m = SPDX_RE.search(head)
        if not m:
            continue
        ident = m.group(1)
        base = ident.split("-")[0]
        if base in COPYLEFT_SPDX or ident in COPYLEFT_SPDX:
            failures.append(
                f"源码 {rel} 声明了强拷贝左许可（SPDX: {ident}）；"
                f"本项目只接受宽松许可（MIT/Apache/BSD 等）")
    return failures


# ─────────────────────────────────────────────────────────────────────────────
# 5. 生成产物 SHA 同步（report_viewer.html 必须嵌入源模板 SHA256 标记）
# ─────────────────────────────────────────────────────────────────────────────

_ARTIFACT_TS_RE = re.compile(r"function page\(\): string \{.*?return `(.*?)`;\s*\}", re.S)
_MARKER_RE = re.compile(r"source-sha256:([0-9a-f]{64})")


def _find_generated(root: Path) -> list:
    """返回 [(html_path, ts_path)]；html 与 .ts 同级仓库根（ts.parents[2]）。"""
    pairs = []
    for ts in root.rglob("report_viewer.ts"):
        if "node_modules" in ts.parts:
            continue
        html = ts.parents[2] / "report_viewer.html"
        if html.exists():
            pairs.append((html, ts))
    return pairs


def check_generated_artifacts(root: Path) -> list:
    failures = []
    for html, ts in _find_generated(root):
        try:
            ts_text = ts.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _ARTIFACT_TS_RE.search(ts_text)
        if not m:
            continue
        want = hashlib.sha256(m.group(1).encode("utf-8")).hexdigest()
        try:
            html_text = html.read_text(encoding="utf-8")
        except OSError:
            failures.append(f"生成产物 {html.relative_to(root)} 无法读取")
            continue
        mk = _MARKER_RE.search(html_text)
        if not mk:
            failures.append(
                f"生成产物 {html.relative_to(root)} 缺少 source-sha256 标记，请重新生成"
                f"（python3 tools/gen_report_viewer.py）")
        elif mk.group(1) != want:
            failures.append(
                f"生成产物 {html.relative_to(root)} 与源 {ts.relative_to(root)} 不同步"
                f"（源模板 SHA 不符），请重新生成")
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="仓库安全护栏（凭据 / 私钥 / Android 权限 / 许可证 / 生成产物）")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]),
                        help="仓库根目录")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    failures = (scan_tree(root) + scan_manifest(root)
                + scan_licenses(root) + check_generated_artifacts(root))

    if args.json:
        print(json.dumps({"root": str(root), "failures": failures,
                          "ok": not failures}, ensure_ascii=False, indent=2))
    elif failures:
        print("仓库安全护栏未通过：")
        for item in failures:
            print(f"  - {item}")
    else:
        print("仓库护栏检查通过：无凭据容器 / 私钥块；Android 权限在白名单内；"
              "许可为宽松；生成产物与源同步。")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
