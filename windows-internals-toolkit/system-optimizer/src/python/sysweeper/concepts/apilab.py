"""接口 API 概念系统只读层（v0.6.59，CLI 子命令 `apilab`）。

数据来源：``data/concepts/apilab_taxonomy.json``（由 ``research/apilab/build_apilab.py``
构建；RFC 编号经本仓库 ``rfc_catalog`` 交叉验证存在性并回填标题；repo-face 轴的
条目以当前仓库实测事实登记——构建时从 ``cli.build_parser()`` 数子命令、从
``webapi.ACTIONS`` 数动作，不写无法核实的数字）。

以仓库 wordbuddy-github 为主目录的**接口 API** 概念系统，按五轴组织：

    风格(style)      : REST / GraphQL / gRPC / WebSocket / SSE / 消息队列 / Webhook / JSON-RPC…
    规约(spec)       : OpenAPI / JSON Schema / Protobuf / AsyncAPI / JSON:API / RAML
    传输(transport)  : HTTP 各版本 / QUIC / 分块流式 / 长连接 / 心跳…
    认证(auth)       : Bearer JWT / OAuth2 / API Key / mTLS / Basic / 签名…
    仓库接口面(repo-face) : 本仓库真实接口面——103 个 CLI 子命令、webapi 29 个
                            JSONL ACTIONS、插件白名单 API、report 模式与查看器守护

红线口径（见 ``_meta.redline_note``）：令牌禁入 URL/localStorage、私钥不明文、
访问令牌短时效 + 服务端刷新。

只读、不联网、不改动数据。
"""
from __future__ import annotations

from ._common import load_taxonomy
from typing import Any, Dict, List, Optional

_DATA = "apilab_taxonomy.json"


def _load() -> Dict[str, Any]:
    """加载 data/concepts/<name>_taxonomy.json（共享加载器，带缓存，只读）。"""
    return load_taxonomy(_DATA)


def info() -> Dict[str, Any]:
    """返回 _meta（主目录 / 五轴 / RFC 口径 / 诚实边界 / 红线说明）。"""
    return _load().get("_meta", {})


def domains() -> List[Dict[str, Any]]:
    """五轴清单（含每轴概念数）。"""
    doc = _load()
    by = doc.get("by_domain", {})
    out = []
    for d in doc.get("domains", []):
        ids = by.get(d["domain"], [])
        out.append({**d, "count": len(ids)})
    return out


def domain(name: str) -> Optional[Dict[str, Any]]:
    """取单轴（含概念数）。"""
    q = (name or "").strip().lower()
    for d in domains():
        if d["domain"] == q:
            return d
    return None


def concepts() -> List[Dict[str, Any]]:
    """全部概念（32 条）。"""
    return list(_load().get("concepts", []))


def concepts_of_domain(name: str) -> List[Dict[str, Any]]:
    """某轴下的概念（style / spec / transport / auth / repo-face）。"""
    q = (name or "").strip().lower()
    return [c for c in concepts() if c.get("domain") == q]


def concept(cid: str) -> Optional[Dict[str, Any]]:
    """取单个概念（含其 standards 引用与 bridges）。"""
    q = (cid or "").strip().lower()
    for c in concepts():
        if c["id"] == q:
            return c
    return None


def of(cid: str) -> Optional[Dict[str, Any]]:
    """``concept`` 的别名（与 plang/netsys/quantum/comp 的 ``of`` 口径一致）。"""
    return concept(cid)


def standards() -> List[Dict[str, Any]]:
    """概念引用的标准依据汇总（RFC 等，构建时经 rfc_catalog 回填 rfc_title；去重）。"""
    out: List[Dict[str, Any]] = []
    seen = set()
    for c in concepts():
        for s in c.get("standards", []):
            key = (s.get("kind"), s.get("num"))
            if key in seen:
                continue
            seen.add(key)
            out.append({**s, "from": c["id"]})
    return out


def repo_facts() -> Dict[str, Any]:
    """本仓库接口面的实测事实（CLI 子命令数 / webapi ACTIONS 数 / 协议口径等）。"""
    return dict(_load().get("repo_face_facts", {}))


def needs_verify() -> List[Dict[str, Any]]:
    """诚实边界：repo-face 数字随代码演进会漂移，构建时实测、使用时按需重建。"""
    doc = _load()
    out: List[Dict[str, Any]] = []
    for c in concepts():
        if c.get("needs_verify"):
            out.append({
                "kind": "concept",
                "id": c["id"],
                "item": c.get("name", c["id"]),
                "why": c["needs_verify"],
            })
    note = doc.get("_meta", {}).get("honesty", "")
    if note:
        out.append({"kind": "meta", "id": "honesty",
                    "item": "口径说明", "why": note})
    return out


def bridges(system: str = "") -> List[Dict[str, Any]]:
    """接口概念 → 既有概念系统的桥接边；给 system 则过滤（netsys/daoxue）。"""
    out = list(_load().get("bridges", []))
    if system:
        q = system.strip().lower()
        out = [b for b in out if b.get("system") == q]
    return out


def bridges_of(cid: str) -> List[Dict[str, Any]]:
    """某个概念发出的桥接边（顶层 bridges 中 from == apilab:<cid>）。"""
    q = (cid or "").strip().lower()
    return [b for b in bridges() if b.get("from") == f"apilab:{q}"]


def search(q: str) -> List[Dict[str, Any]]:
    """跨轴检索（id / 名称 / 纲宗 / 详述）。"""
    term = (q or "").strip().lower()
    if not term:
        return []
    out: List[Dict[str, Any]] = []
    for c in concepts():
        hay = " ".join([
            c.get("id", ""), c.get("name", ""), c.get("gist", ""),
            c.get("detail", ""),
        ]).lower()
        if term in hay:
            out.append({
                "where": c.get("domain", ""),
                "id": c["id"],
                "name": c.get("name", ""),
                "text": c.get("gist", ""),
            })
    return out


def stats() -> Dict[str, Any]:
    """概念系统规模统计。"""
    doc = _load()
    return {
        "concept_total": len(doc.get("concepts", [])),
        "domain_count": len(doc.get("domains", [])),
        "bridge_count": len(doc.get("bridges", [])),
        "standard_count": len(standards()),
    }
