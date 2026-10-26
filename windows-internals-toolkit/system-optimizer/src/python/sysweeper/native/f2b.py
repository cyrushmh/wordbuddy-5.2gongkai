"""fail2ban 学习应用只读层（f2b，v0.6.84）——十二都天神煞大阵。

概念与理念
----------
fail2ban 以单一守护进程统观全部日志源、按规则集中响应，如**十二都天神煞**
环绕一周、周遍防御（「十二」取周遍之义：每接入一个受监控服务就如添一尊
神煞，十二乃至更多）。本仓库学习其架构模式与分级响应思想，落为只读咨询。

指导理念（两大阵法共用总纲）：
  - **道法自然**：响应顺应攻击的自然节律——阈值分级、退避递进，不一刀切；
  - **活在当下**：本机装了 fail2ban 才解析其配置，没有就降级为模式学习，不虚构战果；
  - **只有生存才能发展**：先设 ignoreip 白名单防误封——把自己封在门外是生存事故；
  - **在发展中能更好的生存**：分级封禁与累犯升级提升安全，反哺系统更好地存续；
  - **如此循环，亦复如是**：观测 → 响应 → 再观测，循环上升。

原路返回（操作语义）
------------------
配置建议仅以文本交还用户，由用户沿原路执行；本层绝不代写 jail.local、
绝不重启 fail2ban、绝不代行封禁/解封。对 fail2ban-client 仅调用白名单内的
只读子命令（status），写操作子命令（set/unban/reload/restart…）一律不碰。

许可证边界
----------
fail2ban 为 GPL-2.0（强拷贝左）项目。本仓库**不 vendored 其源代码**，
只在自有模块中引用官方源并学习其架构模式——学习不等于打包，引用不等于
拷贝；所有模式总结均为本仓库原创表述（见 data/f2b_refs.json）。
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA = Path(__file__).resolve().parent.parent / "data" / "f2b_refs.json"

# 对 fail2ban-client 仅允许的只读子命令（写操作子命令一律不调用）
READONLY_CLIENT_CMDS = ("status", "version", "get")


def _load_refs() -> dict:
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def upstream() -> dict:
    return _load_refs()["upstream"]


def philosophy() -> List[str]:
    return _load_refs()["philosophy"]["items"]


def detect() -> Tuple[bool, dict]:
    """只读探测 fail2ban 是否安装（活在当下：有才解析，无则降级）。"""
    info = {
        "client": shutil.which("fail2ban-client"),
        "server": shutil.which("fail2ban-server"),
        "regex": shutil.which("fail2ban-regex"),
        "config_dir": "/etc/fail2ban" if os.path.isdir("/etc/fail2ban") else None,
        "jail_local": "/etc/fail2ban/jail.local"
                      if os.path.isfile("/etc/fail2ban/jail.local") else None,
    }
    installed = bool(info["client"] or info["server"] or info["config_dir"])
    return installed, info


def parse_ini(text: str) -> Dict[str, Dict[str, str]]:
    """只读解析 fail2ban 风格 ini：section + key=value，支持 #/; 注释与 \\ 续行。

    [DEFAULT] 段的键按 ini 语义继承给其余各段（展示用浅合并）。
    """
    sections: Dict[str, Dict[str, str]] = {}
    cur = None
    pending = ""
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if pending:
            line = pending + " " + line.strip()
            pending = ""
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.endswith("\\"):
            pending = stripped[:-1].strip()
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            cur = stripped[1:-1].strip()
            sections.setdefault(cur, {})
            continue
        if cur is None or "=" not in stripped:
            continue
        key, _, val = stripped.partition("=")
        sections[cur][key.strip()] = val.strip()
    if "DEFAULT" in sections:
        defaults = sections["DEFAULT"]
        for name, kv in sections.items():
            if name == "DEFAULT":
                continue
            for k, v in defaults.items():
                kv.setdefault(k, v)
    return sections


def read_jail_file(path: str) -> Dict[str, Dict[str, str]]:
    """只读读取并解析单个 jail 配置文件（不写、不改）。"""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return parse_ini(f.read())
    except OSError:
        return {}


def jails() -> List[dict]:
    """汇总本机 jail 配置（只读）：jail.local + jail.d/*.local，不存在则空。"""
    out: List[dict] = []
    paths = ["/etc/fail2ban/jail.local"]
    paths += sorted(glob.glob("/etc/fail2ban/jail.d/*.local"))
    seen = set()
    for p in paths:
        if p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        for name, kv in read_jail_file(p).items():
            if name in ("DEFAULT", "INCLUDES"):
                continue
            out.append({"source": p, "name": name, **kv})
    return out


def status_jails() -> Tuple[bool, str]:
    """只读调用 fail2ban-client status 取 jail 列表（仅白名单只读子命令）。"""
    client = shutil.which("fail2ban-client")
    if not client:
        return False, "fail2ban-client 不可用（未安装或不在此环境）"
    try:
        r = subprocess.run([client, "status"], capture_output=True,
                           text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"fail2ban-client status 调用失败（只读探针跳过）：{e}"
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "").strip()[:200] or "status 非零退出"
    return True, (r.stdout or "").strip()


def patterns_report() -> List[str]:
    """架构模式学习（原创总结）：六层模式及其教训。"""
    lines = ["十二都天神煞大阵 · fail2ban 架构模式学习（本仓库原创总结，非其文档译文）："]
    for layer in _load_refs()["architecture"]["layers"]:
        lines.append(f"   · [{layer['label']}] {layer['pattern']}")
        lines.append(f"     → 教训：{layer['lesson']}")
    return lines


def consult(env: Optional[List[str]] = None) -> List[str]:
    """只读咨询：给出配置建议文本（沿原路返回，是否执行由用户决定）。"""
    wanted = set(env or [])
    lines = ["只读咨询（配置建议仅文本——是否写入 /etc/fail2ban 由用户沿原路执行）："]
    for tpl in _load_refs()["consult_templates"]:
        if wanted and tpl["id"] not in wanted:
            continue
        lines.append(f"   · {tpl['label']}")
        for ln in tpl["text"].splitlines():
            lines.append(f"     {ln}")
    return lines


def common_jails_report() -> List[str]:
    """常见 jail 只读登记（供咨询时对照）。"""
    lines = ["常见 jail 只读登记（参数语义为 fail2ban 通用口径）："]
    for j in _load_refs()["common_jails"]["jails"]:
        lines.append(f"   · [{j['id']}] {j['label']}：日志 {j['logpath']}，典型 {j['typical']}")
    return lines


def f2b_report(env: Optional[List[str]] = None) -> Tuple[bool, str]:
    """十二都天神煞大阵端到端只读报告：探测 → jail 登记 → 模式学习 → 咨询。"""
    lines: List[str] = []
    lines.append("==== 十二都天神煞大阵 · fail2ban 学习应用只读咨询（f2b） ====")
    lines.append("   指导理念：道法自然 · 活在当下 · 只有生存才能发展 · 在发展中能更好的生存 · 如此循环，亦复如是")
    lines.append("")

    up = upstream()
    lines.append("-- 上游与许可证边界 --")
    lines.append(f"   · 官方源：{up['homepage']}  源码：{up['source']}")
    lines.append(f"   · 许可：{up['license']}（强拷贝左）——{up['license_note']}")
    lines.append("")

    installed, info = detect()
    lines.append("-- 本机探测（活在当下：有才解析，无则降级）--")
    lines.append(f"   · fail2ban-client: {info['client'] or '不可用'}")
    lines.append(f"   · fail2ban-server: {info['server'] or '不可用'}")
    lines.append(f"   · 配置目录: {info['config_dir'] or '不存在'}")
    lines.append(f"   · 判定：{'已安装' if installed else '未安装——降级为模式学习，不虚构战果'}")
    lines.append("")

    if installed:
        lines.append("-- jail 配置只读登记 --")
        js = jails()
        if js:
            for j in js:
                bits = [f"{k}={v}" for k, v in sorted(j.items())
                        if k not in ("source", "name")]
                lines.append(f"   · [{j['name']}]（{j['source']}）{' '.join(bits)}")
        else:
            lines.append("   （有配置目录但未解析到 jail 段；或 jail.local 为空）")
        ok, st = status_jails()
        lines.append("-- fail2ban-client status（只读白名单命令）--")
        if ok:
            for ln in st.splitlines():
                lines.append(f"   {ln}")
        else:
            lines.append(f"   · {st}")
        lines.append("")

    lines.append("-- 架构模式学习（都天神煞的布阵之道）--")
    lines.extend(patterns_report())
    lines.append("")

    lines.append("-- 常见 jail 对照 --")
    lines.extend(common_jails_report())
    lines.append("")

    lines.extend(consult(env))
    lines.append("")
    lines.append("安全不变量：只读学习 ≠ 授权施工——不代写 jail.local、不重启 fail2ban、")
    lines.append("           不代行封禁/解封；fail2ban-client 仅调 status/version/get 只读子命令。")
    return True, "\n".join(lines)


def environment_report() -> List[str]:
    """本机 fail2ban 环境概览（只读）。"""
    installed, info = detect()
    lines = ["fail2ban 学习应用环境（只读概览）:"]
    lines.append(f"   · 安装判定：{'已安装' if installed else '未安装（降级为模式学习）'}")
    lines.append(f"   · 可执行文件：client={info['client'] or '-'} server={info['server'] or '-'} "
                 f"regex={info['regex'] or '-'}")
    lines.append(f"   · 配置目录：{info['config_dir'] or '-'}；jail.local：{info['jail_local'] or '-'}")
    return lines


if __name__ == "__main__":  # 手工自检：python3 -m sysweeper.native.f2b
    ok, rep = f2b_report()
    print(rep)
    raise SystemExit(0 if ok else 1)
