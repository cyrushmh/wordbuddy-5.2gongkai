#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章归集器
====================
输入：URL 清单文件（每行一个 mp.weixin.qq.com 文章 URL，# 开头为注释）
处理：直连抓取 → 提取 msg_title / create_time / js_content → 清洗 → 落盘 Markdown
特性：
  - 断点续跑：已完成 URL 记入 done.txt，重跑自动跳过
  - 失败重试：每篇最多 3 次，指数退避
  - 严格 UTF-8 无 BOM 落盘（与 classics 数据管线同一纪律）
  - 文件名清洗：去路径非法字符，超长截断

用法：
  python3 wechat_harvest.py <account> <urls.txt>
    account = daoyi-ketang | daojiao-yixue  （决定落盘目录）
"""
import os, re, sys, html, time, json, hashlib, urllib.request, urllib.error

BASE = "/workspace/windows-internals-toolkit/research"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

ACCOUNTS = {
    "daoyi-ketang": "道医课堂",
    "daojiao-yixue": "道教医学",
}

def fetch(url, tries=3):
    """抓取 mp 文章页，带重试与指数退避"""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last

def clean_content(raw_html):
    """js_content HTML → 干净正文"""
    s = raw_html
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|section|li|h[1-6]|tr|div)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)          # 去其余标签
    s = html.unescape(s)
    s = re.sub(r"[ \t\u3000]+", " ", s)    # 全角空格归一
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def safe_name(title, maxlen=60):
    t = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", title).strip().strip(".")
    return t[:maxlen] if len(t) > maxlen else t

def parse_article(page_bytes):
    s = page_bytes.decode("utf-8", errors="replace")
    out = {}
    m = re.search(r'var msg_title\s*=\s*[\"\'](.*?)[\"\']\.html\(false\)', s) or \
        re.search(r"var msg_title\s*=\s*['\"](.*?)['\"]", s, re.S)
    out["title"] = html.unescape(m.group(1)).strip() if m else "(无标题)"
    m = re.search(r'var nickname\s*=\s*[\"\'](.*?)[\"\']', s)
    out["nickname"] = html.unescape(m.group(1)).strip() if m else ""
    m = re.search(r'var create_time\s*=\s*"(\d+)"', s) or re.search(r'var ct\s*=\s*"(\d+)"', s)
    out["create_ts"] = int(m.group(1)) if m else 0
    m = re.search(r'id="js_content"[^>]*>(.*?)</div>\s*<script', s, re.S)
    if not m:
        m = re.search(r'class="rich_media_content[^"]*"[^>]*>(.*?)</div>\s*<script', s, re.S)
    out["content"] = clean_content(m.group(1)) if m else ""
    return out

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ACCOUNTS:
        print(__doc__); sys.exit(1)
    account, listfile = sys.argv[1], sys.argv[2]
    outdir = os.path.join(BASE, account)
    os.makedirs(outdir, exist_ok=True)
    done_file = os.path.join(BASE, "harvest", f"done_{account}.txt")
    harvest_dir = os.path.join(BASE, "harvest")
    os.makedirs(harvest_dir, exist_ok=True)
    done = set()
    if os.path.exists(done_file):
        done = set(x.strip() for x in open(done_file, encoding="utf-8") if x.strip())

    urls = []
    for line in open(listfile, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 兼容 "标题\tURL" 与纯 "URL" 两种格式：正则直接抠出 URL
        m = re.search(r"https://mp\.weixin\.qq\.com/s\?\S+", line)
        if m:
            urls.append(m.group(0))
    # 去重保序
    seen, todo = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); todo.append(u)

    stats = {"ok": 0, "skip": 0, "fail": 0, "empty": 0}
    for i, u in enumerate(todo, 1):
        if u in done:
            stats["skip"] += 1
            continue
        try:
            page = fetch(u)
        except Exception as e:
            stats["fail"] += 1
            print(f"[{i}/{len(todo)}] FETCH-FAIL {e} | {u[:90]}")
            continue
        a = parse_article(page)
        if not a["content"] or len(a["content"]) < 50:
            stats["empty"] += 1
            print(f"[{i}/{len(todo)}] EMPTY-BODY | {a['title'][:40]} | {u[:90]}")
            # 仍记录到 done，避免反复撞同一篇坏页
            with open(done_file, "a", encoding="utf-8") as f:
                f.write(u + "\n")
            continue
        ts = a["create_ts"]
        date = time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else "未知日期"
        fn = f"{date}_{safe_name(a['title'])}.md"
        path = os.path.join(outdir, fn)
        if os.path.exists(path):  # 同名不同 URL 的极端情况
            path = os.path.join(outdir, f"{date}_{safe_name(a['title'])}_{hashlib.md5(u.encode()).hexdigest()[:6]}.md")
        fm = (
            "---\n"
            f"title: {json.dumps(a['title'], ensure_ascii=False)}\n"
            f"account: {ACCOUNTS[account]}\n"
            f"source: {u}\n"
            f"publish_date: {date}\n"
            f"chars: {len(a['content'])}\n"
            f"harvested_at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            "---\n\n"
        )
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(fm + f"# {a['title']}\n\n" + a["content"] + "\n")
        with open(done_file, "a", encoding="utf-8") as f:
            f.write(u + "\n")
        stats["ok"] += 1
        print(f"[{i}/{len(todo)}] OK {date} {a['title'][:40]} ({len(a['content'])}字)")
    print("STATS:", json.dumps(stats, ensure_ascii=False))

if __name__ == "__main__":
    main()
