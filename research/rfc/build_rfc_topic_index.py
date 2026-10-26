#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RFC 主题域索引构建器（heuristic，命中留痕）
============================================
输入：data/rfc_standards.json（rfc-editor.org 官方 RFC INDEX 解析产物）
输出：data/rfc_topic_index.json —— 9,848 条已发布 RFC → 13 个主题域的
      启发式分类索引。

设计口径（与 harvest 脚本一脉相承的可复现流水线）：
  1. **仅匹配标题**：规则只作用于 RFC 标题（t 字段），不读全文，
     全文无法本地获取，标题是本地可核验的唯一权威文本；
  2. **显式规则集**：每条规则是 (domain, rule_id, regex) 三元组，
     规则 id 全局唯一，可逐条审计/删改，不靠黑箱模型；
  3. **命中留痕**：每条 RFC 记录命中的 domain 与 rule_id 列表，
     复核时可直接反查「为什么这条 RFC 被分到这个域」；
  4. **heuristic 标注**：本文是本地启发式分类，**不是** IETF 官方分类，
     meta.method 已声明；一条 RFC 可归多域（如 DNS over IPv6 同归
     dns 与 ip-core），未命中任何规则者如实留在 unclassified——
     不强行 100% 覆盖；
  5. **对账模式**：--check 从磁盘重读产物，逐项断言（规则可编译/
     id 唯一/键存在于目录/classified+unclassified==issued/按规则
     重算与落盘完全一致），防止手工篡改数据层。

用法：
  python3 build_rfc_topic_index.py             # 构建并写盘
  python3 build_rfc_topic_index.py --check     # 只校验磁盘产物
  python3 build_rfc_topic_index.py --report    # 打印分布摘要（不写盘）
  RFC_CATALOG=... RFC_TOPIC_OUT=...            # 覆盖默认路径
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_DEFAULT_DATA = (REPO / "windows-internals-toolkit/system-optimizer/"
                 "src/python/sysweeper/data")
CATALOG_PATH = os.environ.get(
    "RFC_CATALOG", str(_DEFAULT_DATA / "rfc_standards.json"))
OUT_PATH = os.environ.get(
    "RFC_TOPIC_OUT", str(_DEFAULT_DATA / "rfc_topic_index.json"))

# ---------------------------------------------------------------
# 主题域定义（label 面向最终用户展示）
# ---------------------------------------------------------------
DOMAINS = {
    "tls-pki": "TLS/SSL 与 PKI 密码学",
    "http-web": "HTTP 与 Web 体系",
    "dns": "域名系统 DNS",
    "ip-core": "IPv4/IPv6 核心与地址",
    "transport": "传输层协议",
    "routing": "路由与交换",
    "mail": "电子邮件体系",
    "security": "网络安全与认证授权",
    "management": "网络管理与监控",
    "time-sync": "时间同步",
    "realtime-media": "实时音视频媒体",
    "iot-constrained": "物联网与受限网络",
    "data-formats": "数据格式与国际化",
}

# ---------------------------------------------------------------
# 规则集：(domain, rule_id, pattern, label)
# pattern 仅作用于小写化标题；写规则时假设输入已 .lower()。
# 宁可漏判不可错判——宽泛词一律配 \b 边界。
# ---------------------------------------------------------------
RULES = [
    # ---- tls-pki ----
    ("tls-pki", "tls", r"\btls\b|transport layer security", "TLS 协议族"),
    ("tls-pki", "ssl", r"\bssl\b|secure socket layer", "SSL 历史协议"),
    ("tls-pki", "dtls", r"\bdtls\b", "数据报 TLS（DTLS）"),
    ("tls-pki", "x509", r"\bx\.?509\b", "X.509 证书"),
    ("tls-pki", "pki", r"\bpki\b|public[- ]key infrastructure|trust anchor",
     "PKI 基础设施"),
    ("tls-pki", "cert", r"certificate", "证书签发/撤销/路径"),
    ("tls-pki", "cms", r"\bcms\b|cryptographic message syntax|\bsmime\b|"
     r"s/mime", "CMS/S/MIME"),
    ("tls-pki", "crypto", r"cryptograph|\bcipher|elliptic curve|"
     r"diffie[- ]hellman|key (exchange|agreement|establishment|management|"
     r"generation)|\bhmac\b|\bprf\b|\bnonce\b", "密码算法与密钥"),

    # ---- http-web ----
    ("http-web", "http", r"\bhttp\b|hypertext transfer", "HTTP"),
    ("http-web", "webdav", r"\bwebdav\b|\bcaldav\b|\bcarddav\b", "WebDAV 家族"),
    ("http-web", "uri", r"\burls?\b|\buris?\b|\burn\b|uniform resource "
     r"(name|locator|identifier)", "URL/URI/URN"),
    ("http-web", "cgi", r"\bcgi\b|common gateway", "CGI"),
    ("http-web", "cookie", r"\bcookie", "Cookie"),
    ("http-web", "webarch", r"web (architecture|linking|services)|well[- ]known"
     r"|syndication|\brss\b|open search|\bpubsub\b|\bwebsocket\b|\bwebpush\b|"
     r"\batom\b|\bcdn\b|content delivery (network|interconnection)", "Web 架构/订阅"),
    ("http-web", "soap", r"\bsoap\b|simple object access|\bwsdl\b", "SOAP/WSDL"),

    # ---- dns ----
    ("dns", "dns", r"\bdns\b|domain names?\b|name server",
     "DNS 协议族"),
    ("dns", "mdns", r"multicast dns|\bdns[- ]sd\b|\bmdns\b", "组播与服务发现"),
    ("dns", "zone", r"zone (transfer|file|increment)|\baxfr\b|\bixfr\b|"
     r"dynamic dns update", "区域传送/动态更新"),
    ("dns", "enum", r"\benum\b|e\.164|telephone number", "ENUM/电话号码映射"),
    ("dns", "idn", r"internationali[sz]ed domain|\bidn\b|\bpunycode\b",
     "IDN/Punycode"),
    ("dns", "discovery", r"discovery (protocol|mechanism|service)|\bslp\b|"
     r"service location protocol", "服务发现协议"),

    # ---- ip-core ----
    ("ip-core", "ip", r"\bipv4\b|\bipv6\b|internet protocol version|\bip version\b|"
     r"\binternet protocol\b|\bppp\b|point[- ]to[- ]point protocol|"
     r"\bpppoe\b|\bip\b (header|datagram|packet|fragment|address|forward|option|"
     r"multicast|sender|source|suite)|ip addressing", "IPv4/IPv6 协议"),
    ("ip-core", "addr", r"address (allocation|assignment|autoconfiguration|"
     r"space|aggregation|family|sharing|selection|resolution)|\bsubnet\b|"
     r"\bprefix\b|\bcidr\b|classless|\bnetmask\b|\barp\b|\binarp\b|\brarp\b",
     "地址分配/解析"),
    ("ip-core", "icmp", r"\bicmp\b|\bicmpv6\b|internet control message", "ICMP"),
    ("ip-core", "nd", r"neighbor discovery|router (solicitation|advertisement)|"
     r"stateless address|neighbor unreachability", "邻居发现/自动配置"),
    ("ip-core", "dhcp", r"\bdhcp\b|\bdhcpv6\b|\bbootp\b|dynamic host "
     r"configuration", "DHCP/BOOTP"),
    ("ip-core", "frag", r"fragment|\bmtu\b|path mtu|maximum transmission unit|"
     r"packet size", "分片与 MTU"),
    ("ip-core", "tunnel", r"\btunnel|\bgre\b|\b6to4\b|\b6in4\b|\b6rd\b|"
     r"\b4in6\b|\bisatap\b|\bteredo\b|transition (technolog|mechan|protocol)|"
     r"\bnat64\b|\bdns64\b|\bnat\b|network address (translator|translation)|"
     r"\bivs\b|ipv[46] (transition|translation)|\bl2tp\b|\bpptp\b|\bsst\b|"
     r"layer two tunneling|\bpcp\b|port control protocol", "隧道/过渡/NAT"),

    # ---- transport ----
    ("transport", "tcp", r"\btcp\b|transmission control protocol", "TCP"),
    ("transport", "udp", r"\budp\b|user datagram|udp[- ]lite", "UDP"),
    ("transport", "quic", r"\bquic\b", "QUIC"),
    ("transport", "sctp", r"\bsctp\b|stream control transmission", "SCTP"),
    ("transport", "dccp", r"\bdccp\b|datagram congestion control", "DCCP"),
    ("transport", "mptcp", r"\bmptcp\b|multipath tcp|\bmultipath\b", "MPTCP"),
    ("transport", "cong", r"congestion (control|window|avoidance)|\bcubic\b|"
     r"slow start|retransmis|\breno\b|tcp (option|checksum|extension|"
     r"congestion|recovery|friendly)|\back\b", "拥塞控制与 TCP 扩展"),
    ("transport", "port", r"port (number|range|map|assignment|registry)|"
     r"well[- ]known port|service name", "端口与服务名"),

    # ---- routing ----
    ("routing", "bgp", r"\bbgp\b|border gateway protocol", "BGP"),
    ("routing", "ospf", r"\bospf\b|open shortest path first", "OSPF"),
    ("routing", "isis", r"\bis[- ]?is\b|intermediate system to intermediate",
     "IS-IS"),
    ("routing", "rip", r"\brip\b|routing information protocol", "RIP"),
    ("routing", "pim", r"\bpim\b|protocol independent multicast|\bmsdp\b|"
     r"\bssm\b|\bigmp\b|\bmld\b|multicast (router|group|listener)|group "
     r"membership protocol", "组播路由"),
    ("routing", "mpls", r"\bmpls\b|multi[- ]protocol label|\bldp\b|label "
     r"(distribution|switching|stack)", "MPLS/标签交换"),
    ("routing", "gen", r"\brouter\b|routing (protocol|table|policy|metric|"
     r"loop|domain|architecture|information)|\broute\b|\brouting\b|interior "
     r"gateway|exterior gateway|\bidrp\b|\bidpr\b|anycast|traffic engineering|"
     r"\bnsis\b|next steps in signaling|\bgist\b|\balto\b|application[- ]"
     r"layer traffic|fast reroute|\bfrr\b|\bevpn\b|ethernet vpn|\bvpls\b|"
     r"virtual private lan|\bvxlan\b|\bgeneve\b|\bnvgre\b|overlay (network|"
     r"encapsulation|virtual)", "路由通用"),
    ("routing", "te", r"\brsvp\b|resource reservation|\bpcep\b|path computation|"
     r"\bbfd\b|bidirectional forwarding detection|constraint[- ]based routing|"
     r"loose (source )?route|\bcrldp\b", "流量工程(RSVP/PCEP/BFD)"),
    ("routing", "idloc", r"\blisp\b|locator/id|\bilnp\b|identifier[- ]locator|"
     r"\bhip\b|host identity|\bdsr\b|dynamic source routing|\bmipv6\b|"
     r"mobile ip|\bnemo\b|network mobility", "身份/位置分离(LISP/HIP/ILNP)"),
    ("routing", "sdn", r"software[- ]defined networking|\bopenflow\b|segment "
     r"routing|\bsrv6\b", "SDN/段路由"),

    # ---- mail ----
    ("mail", "smtp", r"\bsmtp\b|simple mail transfer", "SMTP"),
    ("mail", "imap", r"\bimap\b|internet message access", "IMAP"),
    ("mail", "pop", r"\bpop3?\b|post office protocol", "POP3"),
    ("mail", "fmt", r"\bmail\b|electronic mail|message (header|format|store)",
     "邮件报文格式"),
    ("mail", "mailauth", r"\bdkim\b|domainkeys|\bspf\b|sender policy framework|"
     r"\bdmarc\b|mail authentication|authenticated received chain|\barc\b",
     "邮件认证(DKIM/SPF/DMARC)"),
    ("mail", "sieve", r"\bsieve\b|mail filter|manage ?sieve|vacation", "Sieve"),
    ("mail", "list", r"mailing list|\blistserv\b|list (owner|poster|"
     r"distribution)", "邮件列表"),

    # ---- security ----
    ("security", "ipsec", r"\bipsec\b|\bike\b|\bikev2\b|internet key exchange|"
     r"\besp\b|encapsulating security payload", "IPsec/IKE"),
    ("security", "ssh", r"\bssh\b|secure shell|\bsftp\b", "SSH"),
    ("security", "kerberos", r"\bkerberos\b", "Kerberos"),
    ("security", "aaa", r"\bradius\b|\bdiameter\b|\btacacs\b|\baaa\b|"
     r"authentication,? authori[sz]ation,? (and accounting|accounting)|remote "
     r"authentication", "AAA(RADIUS/DIAMETER)"),
    ("security", "auth", r"\bsasl\b|simple authentication and security|"
     r"\bgss[- ]api\b|\bkrb5\b|one[- ]time password|\botp\b|\bhotp\b|\btotp\b|"
     r"password[- ]based|authenticated key exchange", "认证机制(SASL/GSS)"),
    ("security", "ddos", r"denial of service|\bddos\b|source address "
     r"validation|\burpf\b|\bbcp ?38\b", "DDoS/源地址验证"),
    ("security", "secgen", r"security (considerations|architecture|threat|"
     r"model|policy|framework|guidelines|mechanism|evaluation|report|"
     r"handling)|\bthreat model|vulnerabilit|\bhardening\b|security audit|"
     r"firewall|\bvpn\b|middlebox|\bmidcom\b|nat (control|traversal|discovery)|"
     r"\bgeopriv\b|location (privacy|information)", "安全通用/威胁模型"),
    ("security", "pgp", r"\bpgp\b|pretty good privacy|\bopenpgp\b", "PGP/OpenPGP"),
    ("security", "incident", r"incident|forensic|\bcsirt\b|\bcve\b|common "
     r"vulnerabilit|security team", "安全事件响应"),

    # ---- management ----
    ("management", "snmp", r"\bsnmp\b|simple network management|\bmib\b|"
     r"structure of management information|\brmon\b|remote monitoring",
     "SNMP/MIB"),
    ("management", "ldap", r"\bldap\b|lightweight directory access|\bx\.500\b|"
     r"directory (server|protocol|service|schema|information)|\bwhois\b|"
     r"\brwhois\b|\bweirds\b|registration data (access|protocol|directory)",
     "目录/注册查询(LDAP/X.500/whois)"),
    ("management", "netconf", r"\bnetconf\b|\byang\b|network configuration "
     r"protocol", "NETCONF/YANG"),
    ("management", "syslog", r"\bsyslog\b", "Syslog"),
    ("management", "flow", r"flow (specification|label|export)|\bipfix\b|"
     r"\bnetflow\b|\bsflow\b|packet sampling", "流量导出(IPFIX)"),
    ("management", "monitor", r"monitor|measurement|traceroute|\bping\b|"
     r"\bioam\b|performance (metric|measurement)", "监控与测量"),
    ("management", "ops", r"operations (and|&) management|\bmanagement "
     r"(framework|information base|station|plane)|\bdisman\b|\bcapwap\b|"
     r"wireless (access point|lan)|control and provisioning of wireless",
     "运维管理框架"),

    # ---- time-sync ----
    ("time-sync", "ntp", r"\bntp\b|\bsntp\b|network time protocol|time "
     r"(synchronization|protocol|server|client|daemon)|clock "
     r"(synchronization|selection|discipline|offset)|\bchrony", "NTP/时间同步"),
    ("time-sync", "ptp", r"\bptp\b|precision time protocol|\bieee ?1588\b",
     "PTP/IEEE 1588"),
    ("time-sync", "leap", r"leap second|\bdut1\b|\bearth rotation\b|\butc\b|"
     r"coordinated universal time|time zone", "闰秒/时区/UTC"),
    ("time-sync", "ts", r"timestamp|time stamp|utc (offset|time)", "时间戳"),

    # ---- realtime-media ----
    ("realtime-media", "rtp", r"\brtp\b|\brtcp\b|real[- ]time (transport|"
     r"control|streaming|protocol)|\bsrtp\b|\bzrtp\b", "RTP/RTCP"),
    ("realtime-media", "sip", r"\bsip\b|session initiation|\bsdp\b|session "
     r"description", "SIP/SDP"),
    ("realtime-media", "im", r"\bpresence\b|instant messag|\bcpim\b|\bmsrp\b|"
     r"message session relay|chat (room|server)", "即时消息与在线状态"),
    ("realtime-media", "webrtc", r"\bwebrtc\b|\bjsep\b|\bice\b|\bstun\b|"
     r"\bturn\b|web real[- ]time", "WebRTC/ICE/STUN"),
    ("realtime-media", "codec", r"codec|\bopus\b|\bspeex\b|\bh\.26\d\b|"
     r"\bmpeg\b|\bvp[89]\b|\bav1\b|audio (coding|streaming)|voice|speech",
     "编解码/音频"),
    ("realtime-media", "fax", r"\bfax\b|facsimile|\bt\.30\b", "传真"),
    ("realtime-media", "pstn", r"voice over ip|\bvoip\b|telephony|\bpstn\b|"
     r"\bisdn\b|\bss7\b|\bsigtran\b|numbering (plan|portability)|\bstir\b|"
     r"\bshan\b|telephone (number|identity|call)|caller id", "电话网/PSTN"),

    # ---- iot-constrained ----
    ("iot-constrained", "coap", r"\bcoap\b|constrained application protocol",
     "CoAP"),
    ("iot-constrained", "6lowpan", r"\b6lowpan\b|\b6tisch\b|routing over "
     r"low[- ]power|low[- ]power (and )?lossy|\broll\b|constrained node|"
     r"\b802\.15\.4\b|ipv6 (packets )?over (ieee 802\.15|low[- ]power|lossy|"
     r"constrained)", "6LoWPAN/6TiSCH"),
    ("iot-constrained", "iot", r"internet of things|\biot\b|\bsensor\b|\bm2m\b|"
     r"\bzigbee\b|\bthread\b|\bwpan\b|\bbluetooth\b|\bble\b|\brfid\b|\bnfc\b|"
     r"smart (city|grid|home|building)", "IoT/传感网"),
    ("iot-constrained", "lpwan", r"\blora\b|\blpwan\b|\bsigfox\b|\bnb[- ]?"
     r"iot\b|\blte[- ]m\b|low power wide area", "LPWAN"),

    # ---- data-formats ----
    ("data-formats", "xml", r"\bxml\b|extensible markup|\bxmpp\b|\bxop\b|"
     r"\bxpath\b|\bxslt\b", "XML 家族"),
    ("data-formats", "json", r"\bjson\b|javascript object notation", "JSON"),
    ("data-formats", "mime", r"\bmime\b|multipurpose internet mail|media "
     r"type|content[- ]type|\bicalendar\b|\bvcard\b", "MIME/内容类型"),
    ("data-formats", "charset", r"\butf[- ]?8\b|\butf[- ]?16\b|unicode|"
     r"\biso ?10646\b|\bucs\b|character (set|encoding|repertoire|model)|"
     r"\bidna\b|\bpunycode\b", "字符集/Unicode"),
    ("data-formats", "i18n", r"internationali[sz]ation|locali[sz]ation|"
     r"\bi18n\b|\bl10n\b|language tag|locale|\bcollation\b|transliteration|"
     r"internationali[sz]ed resource", "国际化/本地化"),
]

_UNCLASSIFIED_SAMPLE = 60


def _load_catalog() -> dict:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _compile_rules():
    """规则集编译 + 唯一性/域归属自检（构建与校验共用）。"""
    seen = {}
    compiled = []
    for domain, rid, pat, label in RULES:
        if rid in seen:
            raise SystemExit(f"规则 id 重复：{rid}（{seen[rid]} 与 {domain}）")
        if domain not in DOMAINS:
            raise SystemExit(f"规则 {rid} 指向未定义域：{domain}")
        seen[rid] = domain
        compiled.append((domain, rid, re.compile(pat), label))
    return compiled


def _classify(catalog: dict):
    """核心分类循环（build 与 check 共用，保证重算一致）。"""
    rules = _compile_rules()
    out = {}
    for key, e in catalog.items():
        if not e.get("i"):
            continue
        title = (e.get("t") or "").lower()
        hit_domains, hit_rules = [], []
        for domain, rid, rx, _label in rules:
            if rx.search(title):
                if domain not in hit_domains:
                    hit_domains.append(domain)
                hit_rules.append(rid)
        if hit_rules:
            out[key] = {"domains": hit_domains, "rules": hit_rules}
    return out


def build(catalog: dict) -> dict:
    """按规则集分类全部 issued RFC，返回完整索引结构。"""
    assignments = _classify(catalog)
    issued = sum(1 for e in catalog.values() if e.get("i"))
    unclassified = [k for k in catalog if k not in assignments
                    and catalog[k].get("i")]
    return {
        "_meta": {
            "generated_by": "research/rfc/build_rfc_topic_index.py",
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "source": "data/rfc_standards.json（rfc-editor.org RFC INDEX 解析）",
            "method": "标题关键词规则匹配（heuristic，非 IETF 官方分类）",
            "match_scope": "title_only（仅 RFC 标题，不读全文）",
            "multi_domain": True,
            "catalog_total": len(catalog),
            "catalog_issued": issued,
            "rule_count": len(RULES),
            "domain_count": len(DOMAINS),
            "classified": len(assignments),
            "unclassified": issued - len(assignments),
            "unclassified_note": "未命中任何规则者如实保留；heuristic "
                                 "分类不追求 100% 覆盖",
        },
        "domains": {d: {"label": label,
                        "rules": [rid for dm, rid, _p, _l in RULES if dm == d]}
                    for d, label in DOMAINS.items()},
        "rules": {rid: {"domain": dm, "label": label, "pattern": pat}
                  for dm, rid, pat, label in RULES},
        "assignments": assignments,
        "unclassified_sample": sorted(unclassified[:_UNCLASSIFIED_SAMPLE]),
    }


def _recompute(catalog: dict) -> dict:
    """不落盘重算 assignments，用于 --check 对账（与 build 同一实现）。"""
    return _classify(catalog)


def check() -> int:
    """磁盘产物对账：任一断言失败返回 1 并逐项列出。"""
    errors = []
    catalog = _load_catalog()
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            idx = json.load(f)
    except Exception as exc:
        print(f"[FAIL] 无法读取产物 {OUT_PATH}：{exc}")
        return 1
    meta = idx.get("_meta", {})

    # 1. 规则集自身一致性
    try:
        _compile_rules()
    except SystemExit as exc:
        errors.append(str(exc))

    rules_map = idx.get("rules", {})
    if len(rules_map) != len(RULES):
        errors.append(f"规则数不符：磁盘 {len(rules_map)} != 代码 {len(RULES)}")

    # 2. 目录口径对账
    issued = sum(1 for e in catalog.values() if e.get("i"))
    if meta.get("catalog_issued") != issued:
        errors.append(f"meta.catalog_issued={meta.get('catalog_issued')} "
                      f"!= 目录实测 issued={issued}")
    if meta.get("catalog_total") != len(catalog):
        errors.append(f"meta.catalog_total 不符：{meta.get('catalog_total')} "
                      f"!= {len(catalog)}")

    # 3. assignments 键必须存在于目录且为 issued
    assignments = idx.get("assignments", {})
    bad_keys = [k for k in assignments
                if k not in catalog or not catalog[k].get("i")]
    if bad_keys:
        errors.append(f"{len(bad_keys)} 个 assignment 键不存在或未发布，"
                      f"例：{bad_keys[:5]}")

    # 4. 总量闭合
    classified = len(assignments)
    unclassified = meta.get("unclassified")
    if classified + (unclassified or 0) != issued:
        errors.append(f"总量不闭合：classified {classified} + unclassified "
                      f"{unclassified} != issued {issued}")
    if meta.get("classified") != classified:
        errors.append(f"meta.classified={meta.get('classified')} != "
                      f"实测 {classified}")

    # 5. 每条 assignment 的 domain/rule 引用有效
    bad_ref = 0
    for k, v in assignments.items():
        if not set(v["domains"]) <= set(idx.get("domains", {})):
            bad_ref += 1
        if not set(v["rules"]) <= set(rules_map):
            bad_ref += 1
        for r in v["rules"]:
            if rules_map.get(r, {}).get("domain") not in v["domains"]:
                bad_ref += 1
    if bad_ref:
        errors.append(f"{bad_ref} 条 assignment 的 domain/rule 交叉引用无效")

    # 6. unclassified_sample 不得与 assignments 重叠
    overlap = set(idx.get("unclassified_sample", [])) & set(assignments)
    if overlap:
        errors.append(f"unclassified_sample 与 assignments 重叠 {len(overlap)} 条")

    # 7. 按当前规则集重算，必须与落盘完全一致（防手工篡改）
    recomputed = _recompute(catalog)
    if recomputed != assignments:
        diff = sum(1 for k in set(recomputed) | set(assignments)
                   if recomputed.get(k) != assignments.get(k))
        errors.append(f"重算结果与磁盘不一致：{diff} 条存在差异"
                      f"（规则集或数据被改动？请重新构建）")

    if errors:
        print(f"[FAIL] RFC 主题域索引对账未通过（{len(errors)} 项）：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"[OK] RFC 主题域索引对账通过：issued {issued} 条，"
          f"classified {classified}条（{classified / issued:.1%}），"
          f"unclassified {unclassified} 条，规则 {len(RULES)} 条；"
          f"重算与磁盘完全一致。")
    return 0


def report(catalog: dict, built: dict) -> None:
    dist = {}
    for v in built["assignments"].values():
        for d in v["domains"]:
            dist[d] = dist.get(d, 0) + 1
    print("==== RFC 主题域分布（heuristic，标题规则匹配） ====")
    for d in DOMAINS:
        n = dist.get(d, 0)
        print(f"  {d:<16} {DOMAINS[d]:<14} {n:>5} 条")
    print(f"\n分类覆盖：{built['_meta']['classified']} / "
          f"{built['_meta']['catalog_issued']}（{built['_meta']['classified'] / built['_meta']['catalog_issued']:.1%}）"
          f"，未分类 {built['_meta']['unclassified']} 条（如实保留）")
    top_rules = {}
    for v in built["assignments"].values():
        for r in v["rules"]:
            top_rules[r] = top_rules.get(r, 0) + 1
    print("\n命中数前 15 的规则（审计留痕）：")
    for r, n in sorted(top_rules.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {r:<12} {n:>5}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--check", action="store_true", help="只校验磁盘产物")
    ap.add_argument("--report", action="store_true", help="打印分布摘要（不写盘）")
    args = ap.parse_args()
    catalog = _load_catalog()
    if args.check:
        return check()
    built = build(catalog)
    report(catalog, built)
    if args.report:
        return 0
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(built, f, ensure_ascii=False, indent=1, sort_keys=False)
    size = os.path.getsize(OUT_PATH)
    print(f"\n已写入 {OUT_PATH}（{size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
