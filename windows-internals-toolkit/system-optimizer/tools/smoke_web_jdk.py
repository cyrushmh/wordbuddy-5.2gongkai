#!/usr/bin/env python3.11
"""Web 控制台 JDK 按钮冒烟：真起 Deno 控制台，Playwright 点 JDK 按钮，断言渲染。

这是对被中断收尾步骤的端到端验证——确认 JSON 接口层（jdk.report）经 Deno
外壳 + JSONL 桥接到 Python 逻辑层的整条链路真实可用，不只是单元测试层面。

    python3.11 tools/smoke_web_jdk.py

退出码 0 = 通过；1 = 失败。
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/root/.cache/ms-playwright")
sys.path.insert(0, str(REPO / "src" / "python"))

PORT = 8791
DENO = "deno"
PY = "python3.11"


def wait_ready(url: str, timeout: float = 40.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    from playwright.sync_api import sync_playwright

    proc = subprocess.Popen(
        [DENO, "run", "--allow-net", "--allow-read", "--allow-run",
         str(REPO / "src" / "deno" / "console.ts"),
         "--port", str(PORT), "--host", "127.0.0.1", "--no-open", "--python", PY],
        cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        url = f"http://127.0.0.1:{PORT}/"
        if not wait_ready(url):
            err = proc.stderr.read().decode(errors="replace")[:2500]
            print("控制台未就绪：\n", err)
            return 1

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until="load")

            btn = page.query_selector("#pf-jdk")
            assert btn, "找不到 #pf-jdk 按钮（第 8 标签未挂载 JDK 卡片）"

            # JDK 卡片在「档位与评分」标签下，默认隐藏，先切到该 tab
            page.click('button.tab[data-view="profiles"]')
            page.wait_for_selector("#view-profiles.active", state="visible", timeout=10000)

            page.click("#pf-jdk")
            page.wait_for_function(
                "(function(){var o=document.getElementById('pf-jdk-out');"
                "return o.textContent.indexOf('跑只读探测中')<0 && "
                "o.textContent.indexOf('（尚未运行）')<0 && "
                "o.textContent.trim().length>0;})()",
                timeout=90000,
            )
            out = page.inner_text("#pf-jdk-out")
            status = page.inner_text("#pf-jdk-status") if page.query_selector(
                "#pf-jdk-status") else ""
            browser.close()

            ok = any(k in out for k in ("只读", "JDK", "java", "项只读接口"))
            print("JDK 状态徽标:", status.strip())
            print("JDK 正文前 240 字:", out[:240].replace("\n", " ⏎ "))
            print("渲染判定:", "通过 ✓" if ok else "未命中关键字 ✗")
            return 0 if ok else 1
    except Exception as e:  # noqa: BLE001
        print("冒烟异常:", repr(e))
        return 1
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=6)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
