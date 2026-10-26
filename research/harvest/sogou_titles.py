#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜狗微信搜索列表收集器
======================
从 weixin.sogou.com 翻页收集文章标题（搜狗结果页无需验证，已验证可访问）。
产出：标题清单（去重），供下一阶段用搜索引擎按标题还原真实 mp URL。
"""
import re, sys, time, json, html, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", errors="replace")

def collect(query, pages=10):
    titles = []
    for p in range(1, pages + 1):
        url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(query)}&page={p}"
        try:
            s = fetch(url)
        except Exception as e:
            print(f"  page {p}: ERR {e}")
            break
        items = re.findall(r'<h3[^>]*>\s*<a[^>]*>(.*?)</a>\s*</h3>', s, re.S)
        clean = [html.unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in items]
        clean = [t for t in clean if t]
        if not clean:
            print(f"  page {p}: empty (maybe antispider or end)")
            if "antispider" in s or "验证" in s[:2000]:
                print("  !! ANTISpider hit, stopping")
            break
        # 来源账号（若有）
        srcs = re.findall(r'<a[^>]*class="account"[^>]*>(.*?)</a>', s, re.S) or \
               re.findall(r'<label[^>]*>公众号[：:]\s*</label>\s*<a[^>]*>(.*?)</a>', s, re.S)
        srcs = [re.sub(r"<[^>]+>", "", x).strip() for x in srcs]
        for t in clean:
            titles.append({"page": p, "title": t, "account": srcs[clean.index(t)] if len(srcs) == len(clean) else ""})
        print(f"  page {p}: {len(clean)} titles")
        time.sleep(1.2)
    # 去重
    seen, out = set(), []
    for it in titles:
        if it["title"] not in seen:
            seen.add(it["title"]); out.append(it)
    return out

if __name__ == "__main__":
    query, pages, outfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    res = collect(query, pages)
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"TOTAL {len(res)} unique titles -> {outfile}")
