"""仓库安全护栏自测（scripts/check_repo_guard.py）。

用临时目录造出「有问题的小仓库」，验证三类问题都能被拦住；
再对真实仓库跑一遍，确保当前状态干净。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "check_repo_guard.py"

PRIVATE_KEY = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDaaaaaaaaaaaaaaa\n"
    "-----END PRIVATE KEY-----\n"
)
MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.CAMERA" />
</manifest>
"""


def _run(root: Path, *extra):
    return subprocess.run([sys.executable, str(GUARD), "--root", str(root), *extra],
                          capture_output=True, text=True, timeout=120)


def _make_repo(tmp_path: Path, *, pem=False, embedded=False, manifest=None):
    (tmp_path / "android" / "app" / "src" / "main").mkdir(parents=True, exist_ok=True)
    if pem:
        (tmp_path / "server.key").write_text("x")
    if embedded:
        (tmp_path / "Config.kt").write_text(PRIVATE_KEY)
    if manifest is not None:
        (tmp_path / "android" / "app" / "src" / "main" / "AndroidManifest.xml").write_text(manifest)
    return tmp_path


def test_detects_credential_file(tmp_path):
    _make_repo(tmp_path, pem=True)
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "server.key" in out.stdout


def test_detects_embedded_private_key(tmp_path):
    _make_repo(tmp_path, embedded=True)
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "Config.kt" in out.stdout


def test_rejects_permission_outside_allowlist(tmp_path):
    _make_repo(tmp_path, manifest=MANIFEST)
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "android.permission.CAMERA" in out.stdout
    assert out.stdout.count("白名单外") == 1, "白名单内的 INTERNET 不应被报错"


def test_clean_repo_passes(tmp_path):
    _make_repo(tmp_path, manifest=MANIFEST.replace(
        '\n    <uses-permission android:name="android.permission.CAMERA" />', ""))
    out = _run(tmp_path)
    assert out.returncode == 0, out.stdout


def test_json_output_shape(tmp_path):
    _make_repo(tmp_path, pem=True)
    out = _run(tmp_path, "--json")
    assert out.returncode == 1
    import json
    data = json.loads(out.stdout)
    assert data["ok"] is False and data["failures"]


def test_real_repository_is_clean():
    """本仓库自身必须通过护栏。"""
    out = _run(ROOT)
    assert out.returncode == 0, out.stdout


# ─────────────────────────────────────────────────────────────────────────────
# 4. 许可证白名单
# ─────────────────────────────────────────────────────────────────────────────

def test_rejects_copyleft_top_level_license(tmp_path):
    (tmp_path / "LICENSE").write_text(
        "GNU GENERAL PUBLIC LICENSE\nVersion 3\n\nThis program is free software...")
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "强拷贝左" in out.stdout


def test_rejects_copyleft_spdx_in_source(tmp_path):
    (tmp_path / "mod.py").write_text(
        "# 某模块\n# SPDX-License-Identifier: GPL-3.0-only\n\ndef f():\n    return 1\n")
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "GPL-3.0-only" in out.stdout


def test_allows_permissive_spdx_in_source(tmp_path):
    (tmp_path / "mod.py").write_text(
        "# 某模块\n# SPDX-License-Identifier: MIT\n\ndef f():\n    return 1\n")
    out = _run(tmp_path)
    assert out.returncode == 0, out.stdout


def test_ignores_copyleft_spdx_in_vendored_dir(tmp_path):
    # vendor/ 下的强拷贝左不算本项目许可（那是第三方）
    (tmp_path / "vendor" / "x").mkdir(parents=True)
    (tmp_path / "vendor" / "x" / "mod.py").write_text(
        "# SPDX-License-Identifier: GPL-2.0\n\ndef f():\n    return 1\n")
    out = _run(tmp_path)
    assert out.returncode == 0, out.stdout


# ─────────────────────────────────────────────────────────────────────────────
# 5. 生成产物 SHA 同步
# ─────────────────────────────────────────────────────────────────────────────

def _make_generated_pair(tmp_path, *, marker="0" * 64, with_marker=True):
    (tmp_path / "src" / "deno").mkdir(parents=True)
    ts = (tmp_path / "src" / "deno" / "report_viewer.ts")
    ts.write_text(
        'const VERSION = "x";\n'
        'function page(): string {\n'
        '  return `<!DOCTYPE html>\n'
        '<html><head><title>t</title></head><body>hello</body></html>`;\n'
        '}\n')
    html = (tmp_path / "report_viewer.html")
    body = '<!DOCTYPE html>\n<html><head><title>t</title>'
    if with_marker:
        body += f'\n<!-- source-sha256:{marker} -->'
    body += '</head><body>hello</body></html>'
    html.write_text(body)
    return tmp_path


def test_detects_stale_generated_artifact(tmp_path):
    _make_generated_pair(tmp_path, marker="0" * 64)  # 故意错 sha
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "不同步" in out.stdout


def test_detects_missing_marker_in_generated_artifact(tmp_path):
    _make_generated_pair(tmp_path, with_marker=False)
    out = _run(tmp_path)
    assert out.returncode == 1
    assert "缺少 source-sha256" in out.stdout


def test_allows_synced_generated_artifact(tmp_path):
    # 标记用「源模板真实 sha」，应与 guard 复算一致
    import hashlib
    ts_text = ('const VERSION = "x";\n'
               'function page(): string {\n'
               '  return `<!DOCTYPE html>\n'
               '<html><head><title>t</title></head><body>hello</body></html>`;\n'
               '}\n')
    m = __import__("re").search(r"function page\(\): string \{.*?return `(.*?)`;\s*\}", ts_text, __import__("re").S)
    real_sha = hashlib.sha256(m.group(1).encode("utf-8")).hexdigest()
    _make_generated_pair(tmp_path, marker=real_sha)
    out = _run(tmp_path)
    assert out.returncode == 0, out.stdout
