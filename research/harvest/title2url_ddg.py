#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标题 → 真实 mp URL 还原器（DuckDuckGo HTML 版）
对每个标题执行 site:mp.weixin.qq.com "标题" 精确搜索，解码 uddg redirect 拿直链。
"""
import re, sys, time, json, html, base64, urllib.request, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def ddg_search(query, tries=3):
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", errors="replace")
        except Exception as e:
            time.sleep(3 * (i + 1))
    return ""

def decode_uddg(u):
    m = re.search(r"uddg=([^&]+)", u)
    if not m: return None
    t = urllib.parse.unquote(m.group(1))
    return t

def find_mp_urls(query):
    page = ddg_search(query)
    urls, seen = [], set()
    for m in re.finditer(r'href="([^"]*uddg=[^"]+)"', page):
        u = decode_uddg(m.group(1))
        if u and "mp.weixin.qq.com/s?" in u and u not in seen:
            seen.add(u); urls.append(u)
    return urls

if __name__ == "__main__":
    titles_json, out_json = sys.argv[1], sys.argv[2]
    titles = json.load(open(titles_json, encoding="utf-8"))
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else len(titles)
    results = {}
    for i, it in enumerate(titles[:limit], 1):
        t = it["title"]
        q = f'site:mp.weixin.qq.com "{t}"'
        urls = find_mp_urls(q)
        # 兜底：不带 site:
        if not urls:
            urls = find_mp_urls(f'mp.weixin.qq.com "{t}"')
        results[t] = urls
        print(f"[{i}/{limit}] {t[:36]} -> {len(urls)} url(s)")
        time.sleep(2.0)
    json.dump(results, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = sum(len(v) for v in results.values())
    print(f"DONE: {total} urls for {len(results)} titles -> {out_json}")
