#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""脏话 / 规避式拼音 / 伪装外语 检测器（外部代码准入前置检查）

用法:
    python3 tools/lint_swear.py                     # 扫当前目录（仓库根）
    python3 tools/lint_swear.py /path/to/import     # 扫指定路径（可多个）
    python3 tools/lint_swear.py --json              # 机器可读输出
    python3 tools/lint_swear.py --strict            # 零宽字符污染也算失败

退出码:
    0  干净（或仅 INFO 级提示且未开 --strict）
    1  命中脏话（ERROR 级）
    2  用法/路径错误

设计要点（为什么不会误报）:
    1. 拼音/英文一律「整词边界」匹配 —— minimal/Animation 里的 nima、
       mojibake 里的 jiba、marker-end 里的 eren 都不会命中。
    2. 三层归一化后再匹配，防规避：
         NFD 去声调 (cào -> cao) + 同形字映射 (с/č/ć/全角 -> c) + 去伪装分隔符 (c.a.o -> cao)
    3. 行级白名单正则兜底技术误报（RFC 作者姓 Cao/Kao/Bi、梵文 shabda 等）。
    4. 零宽字符单独列为 INFO（是数据污染，不是脏话），--strict 才计入失败。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

SKIP_DIRS = {".git", "node_modules", "__pycache__", "target", "dist", "build",
             ".pytest_cache", ".yarn", ".codebuddy", "vendor", ".venv", "venv",
             "site-packages", ".mypy_cache", "imports"}
TEXT_EXT = {".py", ".md", ".json", ".txt", ".html", ".htm", ".js", ".ts", ".tsx",
            ".jsx", ".rs", ".c", ".h", ".cpp", ".hpp", ".sh", ".zsh", ".bash",
            ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv", ".sql", ".go",
            ".java", ".kt", ".rb", ".php", ".xml", ".css", ".svg", ".ipynb",
            ".ets", ".vue", ".po", ".pot", ".gradle", ".kts"}
MAX_SIZE = 4 * 1024 * 1024
MAX_LINE = 5000
# 自身与自测文件必然含脏话样本（词表、用例），扫描时跳过
SKIP_FILES = {"lint_swear.py", "test_lint_swear.py"}

# ---------------- 词表：拼音 / 英文（整词边界匹配） ----------------
WORD = [
    # cao 系（含规避改写 chao / 分隔符 / 同形字）
    "cao", "chao", "kao", "wocao", "caonima", "caonm", "cnmb", "nmsl",
    "nmb", "cnmd", "caodan", "chaodan", "caoni",
    # ma 系
    "nima", "nimabi", "nimade", "tamade", "tamate", "mabi", "mab",
    "tmd", "tnd",
    # bi 系
    "shabi", "shab", "saobi", "sabi", "bichi", "jiba", "jb", "j8",
    # 其他
    "gundan", "gundanchu", "rile", "wori", "riniang", "ganliniang",
    "danteng", "chedan", "diaosi", "shadiao", "zhizhang", "naocan",
    "chunhuo", "bendan", "hundan", "wangbadan", "saoqi", "jianhuo",
    "jianren", "biaozi", "liumang", "eren",
    # 英文
    "fuck", "fuxk", "fxxk", "shit", "sh1t", "bitch", "bi7ch", "asshole",
    "damnit", "motherfucker",
]
# 全部拼音词一律「整词边界」匹配（前后非拉丁字母）。
# 这样 minimal/Animation 里的 nima、mojibake 里的 jiba、marker-end 里的 eren
# 都不会命中，无需逐条写白名单。

# ---------------- 词表：中文直写 ----------------
CN = ["傻逼", "傻B", "傻b", "沙雕", "煞笔", "沙比", "二逼", "二b", "尼玛", "玛德",
      "妈的", "他妈", "你妈", "草泥马", "卧槽", "卧草", "我操", "我靠", "我肏",
      "婊子", "骚货", "贱人", "蠢货", "蠢猪", "王八蛋", "混蛋", "滚蛋", "去死",
      "脑残", "智障", "日了狗", "瞎了狗眼", "狗东西", "屁话", "废柴", "白痴"]

# ---------------- 行级白名单（技术误报兜底） ----------------
ALLOW_LINE = [
    r"[A-Z]\.\s*Cao\b", r"Cao,\s", r"\bCao\b.*RFC",          # RFC 作者姓 Cao
    r"[A-Z]\.\s*Kao\b", r"Kao,\s",                            # RFC 作者姓 Kao
    r"\bJ\.\s*Bi\b", r"\bBi,\s",                              # RFC 作者姓 Bi
    r"shabda", r"Shabbat",                                    # 梵文「声」/ 安息日
    r"SHA[- ]based", r"Secure Hash Algorithms",
    r"allowOrigin", r"show-origin", r"flow-oriented",         # wori 误报
    r"Fetched and", r"Switched and",                          # chedan 误报
    r"varilength",                                            # rile 误报
    r"Brainfuck", r"brainfuck",                               # esolang 语言名
    r"mojibake", r"Mojibake",                                 # 乱码检测（核心功能）
    r"kaomoji", r"\borca\b", r"ORCA",                         # 颜文字 / 屏幕阅读器
    r"Resilient Packet Rings", r"bi-directional", r"bi-lingual",
    r"EntryFormAbility", r"FormExtensionAbility",             # mabi 误报
    r"splits\.abi", r"sysfs ABI", r"arch-vendor-os-abi",     # sabi 误报
    r"RECLAIMABLE",                                           # mab 误报
    r"draft-ietf",                                            # xr-jb 误报
    r"-mabi\s*=\s*lp64", r"march=rv64gc",                     # RISC-V GCC 选项
    r"msgstr", r"msgid",                                       # PO 键值行（西里尔译文经映射会假阳性）
    r"NIMA\s*TR\d", r"TR8350",                                 # 美国国家影像测绘局标准号
]
# 大小写敏感白名单：人名缩写必须是大写，否则会被小写规避写法 c.a.o 蹭到豁免
ALLOW_LINE_CS = [
    r"[A-Z]\.[A-Z]\.",                                        # RFC 作者名缩写 J.B. North
]
ALLOW_RE = re.compile("|".join(ALLOW_LINE), re.I)
ALLOW_RE_CS = re.compile("|".join(ALLOW_LINE_CS))

# ---------------- 同形字 / 零宽 ----------------
HOMO = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y",
    "А": "a", "Е": "e", "О": "o", "Р": "p", "С": "c", "Х": "x", "У": "y",
    "α": "a", "ο": "o", "ρ": "p", "ν": "v", "τ": "t",
    "ｃ": "c", "ａ": "a", "ｏ": "o", "Ｃ": "c", "Ａ": "a", "Ｏ": "o",
    "ć": "c", "č": "c", "ç": "c", "ĉ": "c", "к": "k",
}
ZERO_W = re.compile("[\u200b\u200c\u200d\u2060\ufeff\u00ad]")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def dehomoglyph(s: str) -> str:
    return "".join(HOMO.get(c, c) for c in s)


def desep(s: str) -> str:
    """去掉拉丁字母之间的伪装分隔符与零宽字符：c.a.o / c-a-o -> cao

    刻意**不删空格**：删了会把「what the fuck」粘成「whatthefuck」，
    整词边界随之失效（真脏话反而漏网），也会让俄文
    「Ошибка общего」拼出假阳性。代价是「c a o」式空格规避检不出——
    中文里空格分隔的拼音太常见，删空格的误报代价远大于收益。
    """
    s = ZERO_W.sub("", s)
    s = re.sub(r"(?<=[A-Za-z])[\.\-_\*~/|·•]+(?=[A-Za-z])", "", s)
    return s


WORD_RE = [(w, re.compile(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", re.I))
           for w in WORD]
CN_RE = [(w, re.compile(re.escape(w), re.I)) for w in CN]


def iter_files(roots):
    """遍历待扫文件；跳过自身（词表定义行会自指命中）"""
    skip = SKIP_FILES | {os.path.basename(os.path.abspath(__file__))}
    for root in roots:
        if os.path.isfile(root):
            if os.path.basename(root) not in skip:
                yield root
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if fn in skip:
                    continue
                if os.path.splitext(fn)[1].lower() in TEXT_EXT:
                    yield os.path.join(dp, fn)


def scan(roots):
    errors, infos = [], []
    files = 0
    for path in iter_files(roots):
        try:
            if os.path.getsize(path) > MAX_SIZE:
                continue
        except OSError:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()
        except Exception:
            continue
        files += 1
        for i, line in enumerate(lines, 1):
            if len(line) > MAX_LINE:
                line = line[:MAX_LINE]
            # 同形字映射只在原始行含拉丁字母时启用：纯西里尔行（俄文译文）
            # 一旦映射会把「Ошибка общего」拼出假阳性。真伪装必然混写拉丁。
            hit = False
            # 归一化后再判断是否值得做拉丁检测：cào / с.а.о 这类规避写法
            # 在原始行里没有连续 ASCII 拉丁，去调/映射/去分隔符后才有。
            norm = desep(strip_accents(dehomoglyph(line)))
            if re.search(r"[A-Za-z]{2,}", norm):
                for w, rx in WORD_RE:
                    m = rx.search(norm)
                    if not m:
                        continue
                    # 白名单只在命中位置左右 30 字符窗口内生效，不整行豁免。
                    # 同时看原始行：归一化后「J.B.」已被拼成「JB」，
                    # 只在 norm 上匹配会漏掉人名缩写类白名单。
                    win = norm[max(0, m.start() - 30):m.end() + 30]
                    win_raw = line[max(0, m.start() - 30):m.end() + 30]
                    if (ALLOW_RE.search(win) or ALLOW_RE.search(win_raw)
                            or ALLOW_RE_CS.search(win) or ALLOW_RE_CS.search(win_raw)):
                        continue
                    errors.append({"level": "ERROR", "kind": "拼音/外文", "word": w,
                                   "file": path, "line": i, "text": line.strip()[:200]})
                    hit = True
                    break
            # 中文直写始终检测（与拉丁检测独立，同一行只报一次）
            if not hit:
                for w, rx in CN_RE:
                    if rx.search(line):
                        errors.append({"level": "ERROR", "kind": "中文直写", "word": w,
                                       "file": path, "line": i, "text": line.strip()[:200]})
                        break
            if ZERO_W.search(line):
                infos.append({"level": "INFO", "kind": "零宽字符",
                              "word": "U+200B 类", "file": path, "line": i,
                              "text": line.strip()[:200]})
    return {"files": files, "errors": errors, "infos": infos}


def main(argv=None):
    ap = argparse.ArgumentParser(description="脏话/规避拼音/伪装外语检测")
    ap.add_argument("paths", nargs="*", default=["."], help="待扫路径（默认当前目录）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--strict", action="store_true", help="零宽字符也计入失败")
    a = ap.parse_args(argv)

    roots = a.paths or ["."]
    for r in roots:
        if not os.path.exists(r):
            print(f"路径不存在: {r}", file=sys.stderr)
            return 2

    res = scan(roots)
    errs, infos = res["errors"], res["infos"]

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"扫描文件 {res['files']} 个  |  ERROR {len(errs)}  |  INFO(零宽) {len(infos)}")
        for e in errs[:50]:
            print(f"  [ERROR] {e['kind']} '{e['word']}'  {e['file']}:{e['line']}")
            print(f"          {e['text']}")
        if len(errs) > 50:
            print(f"  ... 另有 {len(errs) - 50} 条（--json 查看全部）")
        for e in infos[:20]:
            print(f"  [INFO ] 零宽字符  {e['file']}:{e['line']}")
        if not errs and not infos:
            print("  ✓ 干净")

    if errs:
        return 1
    if a.strict and infos:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
