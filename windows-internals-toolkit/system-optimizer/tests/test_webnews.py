"""webnews 聚合优化知识库测试（v0.6.11）。

只测纯逻辑与只读行为：解析、抽取、来源白名单、缓存、报告；
不真正联网（fetch_all 注入假的 fetch_fn）。
"""

import time

from sysweeper.native import webnews


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>测试源</title>
  <item><title>Linux 内核新补丁修复 ext4 死锁</title>
    <link>https://example.com/1</link>
    <description>SSD trim 与内核参数调优相关</description>
    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
  </item>
  <item><title>Windows 注册表优化技巧</title>
    <link>https://example.com/2</link>
    <description>组策略与 powershell 加速启动</description>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom 源</title>
  <entry><title>IPv6 隐私扩展与 DNS 优化</title>
    <link href="https://example.com/a" rel="alternate"/>
    <summary>网络层开启 DOT 提升隐私</summary>
    <updated>2024-02-01T00:00:00Z</updated>
  </entry>
</feed>"""


def test_is_allowed_url():
    assert webnews.is_allowed_url("https://x.com/f.xml")
    assert webnews.is_allowed_url("http://x.com/f")
    assert not webnews.is_allowed_url("file:///etc/passwd")
    assert not webnews.is_allowed_url("ftp://x.com/f")
    assert not webnews.is_allowed_url("javascript:alert(1)")


def test_parse_feed_rss():
    items = webnews.parse_feed(RSS_SAMPLE)
    assert len(items) == 2
    assert items[0]["title"].startswith("Linux")
    assert items[0]["link"] == "https://example.com/1"
    assert "trim" in items[0]["summary"].lower()


def test_parse_feed_atom():
    items = webnews.parse_feed(ATOM_SAMPLE)
    assert len(items) == 1
    assert items[0]["title"].startswith("IPv6")
    assert items[0]["link"] == "https://example.com/a"


def test_parse_feed_bad():
    assert webnews.parse_feed("不是 xml <<<") == []
    assert webnews.parse_feed("") == []


def test_extract_tips():
    tips = webnews.extract_tips("Linux 内核 SSD trim 优化与散热降频问题")
    assert "linux" in tips
    assert "storage" in tips
    assert "hardware" in tips
    # 空文本不归任何类
    assert webnews.extract_tips("") == {}


def test_fetch_all_offline(monkeypatch, tmp_path):
    # 把缓存重定向到临时目录，避免污染真机 ~/.config
    monkeypatch.setattr(webnews, "_state_dir", lambda: tmp_path)

    calls = {}

    def fake_fetch(url, timeout):
        calls[url] = True
        return True, RSS_SAMPLE if "rss" in url else ATOM_SAMPLE

    srcs = ["https://example.com/rss", "https://example.com/atom"]
    res = webnews.fetch_all(sources=srcs, fetch_fn=fake_fetch)
    assert res["sources_total"] == 2
    assert res["fetched"] == 2
    assert res["items"] == 3
    # 知识点应覆盖 linux / windows / network / storage / privacy 等
    assert "linux" in res["tips_by_cat"]
    assert "windows" in res["tips_by_cat"]
    assert "network" in res["tips_by_cat"]


def test_fetch_all_rejects_bad_source(monkeypatch, tmp_path):
    monkeypatch.setattr(webnews, "_state_dir", lambda: tmp_path)

    def fake_fetch(url, timeout):
        return True, RSS_SAMPLE

    # file:// 会被 is_allowed_url 拒掉，不会调用 fake_fetch
    res = webnews.fetch_all(sources=["file:///etc/passwd"], fetch_fn=fake_fetch)
    assert res["sources_total"] == 0
    assert res["fetched"] == 0


def test_knowledge_report_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(webnews, "_state_dir", lambda: tmp_path)
    ok, msg = webnews.knowledge_report()
    assert ok
    assert "缓存为空" in msg or "还没有资讯" in msg


def test_knowledge_report_from_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(webnews, "_state_dir", lambda: tmp_path)
    webnews.fetch_all(sources=["https://example.com/rss"],
                      fetch_fn=lambda u, t: (True, RSS_SAMPLE))
    ok, msg = webnews.knowledge_report()
    assert ok
    assert "linux" in msg.lower() or "Linux" in msg


def test_capabilities_report():
    ok, msg = webnews.capabilities_report()
    assert ok
    assert "只读" in msg
