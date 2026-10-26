#!/usr/bin/env python3
"""从 report_viewer.ts 的 page() 模板抽取并生成单文件静态查看器 report_viewer.html。

与 Deno 部署版（report_viewer.ts 的 page()）保持字节级等价：静态页只是把
服务端模板字符串「落盘」，靠自身 <script> 拉取/解析报告 JSON，不连任何外部资源。

为什么需要它（坑点）：本机的 `sysweeper web` 是 Deno 外壳，但用户要的是「能随时打开、
能粘贴 JSON 离线看、能塞进任意静态托管」的单文件页。Deno Deploy 已退场
（2026-10-09 Deno 团队并入 Cloudflare，Deno Deploy ≈2027-04 停止），静态页是兜底。

同步纪律（被 scripts/check_repo_guard.py 的「构建产物 SHA」检查强制）：
  生成时把「源模板（page() 返回字符串）的 SHA256」写进 html 顶部注释
  <!-- source-sha256:HEX -->；guard 复算并比对，不一致即报错——防止「改了 .ts 却忘了
  重生成 html」这种静默失同步。

纯标准库，离线可用。用法：
    python3 tools/gen_report_viewer.py            # 生成 report_viewer.html
    python3 tools/gen_report_viewer.py --check    # 只校验同步，不写文件（CI 用）
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TS = REPO / "src" / "deno" / "report_viewer.ts"
HTML = REPO / "report_viewer.html"

_TMPL_RE = re.compile(r"function page\(\): string \{.*?return `(.*?)`;\s*\}", re.S)
_MARKER_RE = re.compile(r"source-sha256:([0-9a-f]{64})")


def extract_template(ts_text: str) -> str:
    m = _TMPL_RE.search(ts_text)
    if not m:
        raise SystemExit("page() 模板字符串未找到（report_viewer.ts 结构变了？）")
    return m.group(1)


def unescape(s: str) -> str:
    """还原 .ts 模板字面量里的转义（与 Deno 字符串语义一致）。"""
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt in ("\\", '"', "`", "$"):
                out.append(nxt)
                i += 2
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def template_sha(ts_text: str) -> str:
    return hashlib.sha256(extract_template(ts_text).encode("utf-8")).hexdigest()


def generate() -> int:
    ts_text = TS.read_text(encoding="utf-8")
    tmpl = extract_template(ts_text)
    sha = hashlib.sha256(tmpl.encode("utf-8")).hexdigest()
    html = unescape(tmpl)
    # 在 <title> 之后插入源 SHA 标记（CI 据此校验同步，不参与页面渲染）
    html = html.replace("</title>", f"</title>\n<!-- source-sha256:{sha} -->", 1)
    HTML.write_text(html, encoding="utf-8")
    print(f"written {len(html.encode('utf-8'))} bytes; source-sha256={sha[:12]}...")
    print("has jdk block:", "OpenJDK / JVM 只读体检" in html)
    print("has distcompute block:", "分布式计算" in html)
    print("ends with </html>:", html.rstrip().endswith("</html>"))
    return 0


def check_sync() -> int:
    if not TS.exists():
        print("SKIP: report_viewer.ts 不存在")
        return 0
    if not HTML.exists():
        print("FAIL: report_viewer.html 不存在，请先生成")
        return 1
    want = template_sha(TS.read_text(encoding="utf-8"))
    m = _MARKER_RE.search(HTML.read_text(encoding="utf-8"))
    if not m:
        print("FAIL: report_viewer.html 缺少 source-sha256 标记，请重新生成")
        return 1
    if m.group(1) != want:
        print("FAIL: report_viewer.html 与 report_viewer.ts 不同步（源模板 SHA 不符），请重新生成")
        return 1
    print(f"OK: report_viewer.html 与 report_viewer.ts 同步（source-sha256={want[:12]}...）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="生成/校验单文件报告查看器")
    ap.add_argument("--check", action="store_true", help="只校验同步，不写文件")
    args = ap.parse_args()
    return check_sync() if args.check else generate()


if __name__ == "__main__":
    sys.exit(main())
