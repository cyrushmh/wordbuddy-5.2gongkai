#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《黃帝內經·素問》81 篇正文采集器（可复现流水线）
================================================
输入：一份公有领域纯文本《素问》转录（默认从 GitHub 公有仓库拉取，
      亦可读取本地已下载文件以避免重复网络请求）。
处理：按索引规范篇名定位 81 章起点 → 切分 → 清洗 → UTF-8 无 BOM 落盘
      → 以 docs/11 §3.2 的 verify_map 锚点校验（防吃书）。
特性：
  - 多模式篇头匹配：兼容「篇第N」「论第七十六」(无篇) 及 OCR 异文(角/形、致/政)
  - 断点续跑：已生成的章文件跳过（done 由文件存在判定）
  - 严格 UTF-8 无 BOM（与 classics 数据管线同一纪律）
  - 诚实标注：来源缺章 / 篇头异文 / 篇号错乱 写入 manifest，绝不伪造

用法：
  python3 suwen_harvest.py                 # 优先本地 /tmp/suwen_raw.txt，否则下载
  SRC=/path/to/suwen.txt python3 suwen_harvest.py
"""
import os, re, sys, json, time, urllib.request, urllib.error, hashlib

BASE = "/workspace/windows-internals-toolkit/research"
INDEX = os.path.join(BASE, "suwen_81_index.json")
OUTDIR = os.path.join(BASE, "suwen")
HARVEST_DIR = os.path.join(BASE, "harvest")
SRC_URL = ("https://raw.githubusercontent.com/daizhigeATxy2401/yicang/master/"
           "%E9%BB%84%E5%B8%9D%E5%86%85%E7%BB%8F%E7%B4%A0%E9%97%AE-%E6%88%98%E5%9B%BD-%E4%BD%9A%E5%90%8D.txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CN = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'零':0}
EDITION = "黄帝内经素问译解（佚名/战国 attribution；公有领域转录，github:daizhigeATxy2401/yicang）"

# 索引繁体篇名 -> 简体（仅真实简化映射；藏/虛/厥 等在本源保持原样）
TRAD2SIM = {'傳':'传','別':'别','匱':'匮','從':'从','徵':'征','應':'应','時':'时','標':'标',
    '氣':'气','異':'异','瘧':'疟','節':'节','紀':'纪','終':'终','絡':'络','經':'经','脈':'脉',
    '舉':'举','著':'着','蘭':'兰','診':'诊','評':'评','調':'调','論':'论','變':'变','運':'运',
    '過':'过','鍼':'针','長':'长','陰':'阴','陽':'阳','離':'离','靈':'灵','類':'类','風':'风',
    '齊':'齐','寶':'宝','湯':'汤','熱':'热','機':'机','虛':'虚','繆':'缪','實':'实'}
# 已知异文（源转录 OCR / 版本差异）
VARIANTS = {'形':'角','角':'形','政':'致','致':'政'}


def simp(s):
    return ''.join(TRAD2SIM.get(c, c) for c in s)


def cn2int(s):
    tot = 0; cur = 0
    for ch in s:
        if ch == '十':
            tot += (cur if cur else 1) * 10; cur = 0
        elif ch == '百':
            tot += (cur if cur else 1) * 100; cur = 0
        else:
            cur = CN[ch]
    return tot + cur


def fetch(url, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def load_source():
    p = os.environ.get("SRC") or "/tmp/suwen_raw.txt"
    if os.path.exists(p) and os.path.getsize(p) > 100000:
        print(f"[src] 使用本地文件 {p} ({os.path.getsize(p)} bytes)")
        return open(p, encoding="utf-8").read()
    print(f"[src] 下载 {SRC_URL}")
    raw = fetch(SRC_URL)
    open(p, "wb").write(raw)
    print(f"[src] 已下载 {len(raw)} bytes -> {p}")
    return raw.decode("utf-8", errors="replace")


def locate_chapters(data, names):
    """返回 {no: start_pos}；无法定位的章返回 None。
    主模式要求源篇号 == 期望章号（交叉引用引用的是其它章，篇号不同，自然排除）。"""
    units = {1:'一',2:'二',3:'三',4:'四',5:'五',6:'六',7:'七',8:'八',9:'九'}
    def cn_num(n):
        if n == 10:
            return '十'
        if n <= 10:
            return units[n]
        if 11 <= n <= 19:
            return '十' + units[n - 10]
        if n == 20:
            return '二十'
        if 21 <= n <= 99:
            t = n // 10; o = n % 10
            return units[t] + '十' + (units[o] if o else '')
        return '一百'
    found = {}
    for no, nm in names.items():
        stem = nm[:-1] if nm.endswith('论') else nm
        exp = cn_num(no)
        cand = None
        # 1) 段首 … stem + 论?篇?第 + 期望篇号（主信号，排除交叉引用）
        m = re.search(r'(?:^|\n)[^\n]*?(' + re.escape(stem) + r')论?篇?第' + exp, data)
        if m:
            cand = m.start(1)
        # 2) 篇号错置晚期章：取段首同名篇头「末次出现」= 真章头（any 论?篇?第 + 数字）
        if cand is None:
            ms = list(re.finditer(r'(?:^|\n)[^\n]*?(' + re.escape(stem) + r')论?篇?第[一二三四五六七八九十百零]+', data))
            if ms:
                cand = ms[-1].start(1)
        # 3) 异文替换（角/形、致/政），末次
        if cand is None:
            for i, ch in enumerate(nm):
                if ch in VARIANTS:
                    alt = nm[:i] + VARIANTS[ch] + nm[i+1:]
                    ast = alt[:-1] if alt.endswith('论') else alt
                    ms = list(re.finditer(r'(?:^|\n)[^\n]*?(' + re.escape(ast) + r')论?篇?第[一二三四五六七八九十百零]+', data))
                    if ms:
                        cand = ms[-1].start(1); break
        # 4) 容错：篇名前两字 + 至多 2 字 + 篇?第 + 期望篇号（ch41 源「刺腰论痛篇第四十一」）
        if cand is None:
            m = re.search(r'(?:^|\n)[^\n]*?' + re.escape(nm[:2]) + r'[\u4e00-\u9fff]{0,2}篇?第' + exp, data)
            if m:
                cand = m.start()
        # 5) ch81 兜底：本病论正文以「篇第八十一」定位（源误标为「微论篇第八十一」）
        if cand is None and no == 81:
            m = re.search('篇第八十一', data)
            if m:
                cand = m.start()
        found[no] = cand
    return found


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    idx = json.load(open(INDEX, encoding="utf-8"))
    names = {c['no']: simp(c['name']) for c in idx['chapters']}
    data = load_source().lstrip('\ufeff')

    found = locate_chapters(data, names)
    missing = [n for n in sorted(names) if found[n] is None]
    print(f"[locate] 定位 {81 - len(missing)}/81，缺失: {missing}")

    # 按位置排序切分（升序）
    located = sorted((n for n in names if found[n] is not None), key=lambda n: found[n])
    # 单调性校验（防止交叉引用误定位）
    pos = [found[n] for n in located]
    if not all(pos[i] < pos[i+1] for i in range(len(pos)-1)):
        print("[WARN] 章起点非单调，可能存在交叉引用误定位", file=sys.stderr)

    anchors = idx.get("verify_map_docs11", {}).get("citations", [])
    manifest = {
        "harvested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "edition": EDITION,
        "source": SRC_URL,
        "total_chars": len(data),
        "located": len(located),
        "missing_chapters": missing,
        "anchor_validation": [],
        "anomalies": [],
    }

    stats = {"ok": 0, "skip": 0, "fail": 0}
    for i, no in enumerate(located):
        start = found[no]
        end = found[located[i+1]] if i + 1 < len(located) else len(data)
        body = data[start:end].strip()
        if len(body) < 30:
            stats["fail"] += 1
            print(f"[{no}] EMPTY-BODY skip")
            continue
        nm_simp = names[no]
        nm_trad = next(c['name'] for c in idx['chapters'] if c['no'] == no)
        fn = f"{no:02d}_{nm_simp}.md"
        path = os.path.join(OUTDIR, fn)
        if os.path.exists(path):
            stats["skip"] += 1
            continue
        # 抽取源篇头（用于异常标注）
        mh = re.search(r'([一-鿿]{1,12}?)(?:篇第|)([一二三四五六七八九十百零]+)', body[:40])
        src_header = mh.group(0) if mh else ""
        fm = (
            "---\n"
            f'title: {json.dumps("素问·第%d篇 %s" % (no, nm_trad), ensure_ascii=False)}\n'
            f"no: {no}\n"
            f"name_index: {nm_trad}\n"
            f"name_source: {nm_simp}\n"
            f"edition: {json.dumps(EDITION, ensure_ascii=False)}\n"
            f"source: {SRC_URL}\n"
            f"retrieved_at: {time.strftime('%Y-%m-%d')}\n"
            f"chars: {len(body)}\n"
            f"source_header: {json.dumps(src_header, ensure_ascii=False)}\n"
            "---\n\n"
        )
        # 严格 UTF-8 无 BOM 落盘
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(fm + body + "\n")
        stats["ok"] += 1

    # 预切分各章正文（用于锚点校验）
    slices = {}
    for i, no in enumerate(located):
        s = found[no]
        e = found[located[i + 1]] if i + 1 < len(located) else len(data)
        slices[no] = data[s:e]

    # 锚点校验（防吃书）：取引号归一化后的稳健前缀做子串匹配（容忍省略号/转述）
    XIE = str.maketrans({'泻': '泄', '藏': '脏'})  # 通假/异文归一：泻↔泄、藏↔脏
    def norm(s):
        s = s.translate(XIE)
        return re.sub(r'[\s　、，。：；…—（）()“”"\'\',.!?]', '', s)
    for c in anchors:
        q = norm(c["quote"]).split('…')[0][:12]; exp = c["expect_chapter"]
        hit = [no for no in located if q in norm(slices[no])]
        # 防吃书语义：期望章必须含锚点引文（出现在其它章为正常现象，不判失败）
        ok = (exp in hit)
        manifest["anchor_validation"].append({
            "quote": c["quote"], "expect_chapter": exp,
            "match_key": q, "found_in": hit, "pass": ok,
        })
        if not ok:
            print(f"[ANCHOR-FAIL] {c['quote']} 期望第{exp}篇，实际: {hit}")

    # 异常标注
    for mno in missing:
        mname = next(c['name'] for c in idx['chapters'] if c['no'] == mno)
        flag = next((c.get('flag', '') for c in idx['chapters'] if c['no'] == mno), '')
        note = f"第{mno}篇 {mname}（{flag or '正篇'}）在本源转录中整章缺失，未伪造内容；"
        if mno == 80:
            note += "仅见交叉引用『论在刺法中』，需另补来源（如《素问》遗篇善本）"
        elif mno == 79:
            note += "全本未收，需另补来源（如《素问》遗篇善本）"
        else:
            note += "需另补来源"
        manifest["anomalies"].append(note)
    if found.get(81):
        manifest["anomalies"].append("第81篇 本病论 源篇头误标为「微论篇第八十一」，已按正文内容(经论从容/形法阴阳刺灸汤液)校正归位")
    if found.get(74):
        manifest["anomalies"].append("第74篇 示从容论 源篇头为「示从容论第七十六」(无『篇』字，且篇号错乱)，已按篇名归位")

    json.dump(manifest, open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("STATS:", json.dumps(stats, ensure_ascii=False))
    print(f"OUTPUT: {OUTDIR}  ({stats['ok']} 新写, {stats['skip']} 跳过, {stats['fail']} 空)")
    av = sum(1 for a in manifest["anchor_validation"] if a["pass"])
    print(f"ANCHORS: {av}/{len(manifest['anchor_validation'])} 通过")


if __name__ == "__main__":
    main()
