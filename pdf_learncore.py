# -*- coding: utf-8 -*-
"""
PDF 公文更名：文件類型分類模型的核心計算（app.py 自動重新學習、tools/pdf_train.py 共用）
==================================================================================
模型＝「每類文件常出現、其他類少出現的中文 2～4 字片段」的權重。
為了能「累加學習」又不用保留原始文件，學習資料存成用字統計（stats）：
  N        總份數
  n_by     {類型: 份數}
  df       {片段: {類型: 出現在幾份}}
  cases    {片段: 出現在幾個不同案場}
  date_ctx {類型: {日期前面的字: 次數}}
只保留至少 3 個不同案場都出現過的片段（個別案場的地址、人名不會留下來）。
"""
import collections
import math
import re

HEAD = 1500
MIN_CASES = 3
PER_CLASS = 300
MIN_CLASS_DOCS = 5
CJK = re.compile(r"[一-鿿]+")
_FW = str.maketrans("０１２３４５６７８９－（）：", "0123456789-():")


def flat(text):
    return re.sub(r"\s+", "", (text or "").translate(_FW))


def grams(text, head=HEAD):
    out = set()
    for seg in CJK.findall(flat(text)[:head]):
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                out.add(seg[i:i + n])
    return out


def empty_stats():
    return {"N": 0, "n_by": {}, "df": {}, "cases": {}, "date_ctx": {}}


def stats_from_docs(docs, weight=1):
    """docs: [(類型, 案場, 片段集合)]"""
    st = empty_stats()
    cases_of = collections.defaultdict(set)
    for label, case, g in docs:
        st["N"] += weight
        st["n_by"][label] = st["n_by"].get(label, 0) + weight
        for x in g:
            d = st["df"].setdefault(x, {})
            d[label] = d.get(label, 0) + weight
            cases_of[x].add(case)
    st["cases"] = {x: len(c) for x, c in cases_of.items()}
    return st


def merge_stats(a, b):
    out = {"N": a["N"] + b["N"], "n_by": dict(a["n_by"]), "df": {x: dict(d) for x, d in a["df"].items()},
           "cases": dict(a["cases"]), "date_ctx": {k: dict(v) for k, v in (a.get("date_ctx") or {}).items()}}
    for l, n in b["n_by"].items():
        out["n_by"][l] = out["n_by"].get(l, 0) + n
    for x, d in b["df"].items():
        t = out["df"].setdefault(x, {})
        for l, c in d.items():
            t[l] = t.get(l, 0) + c
    for x, c in b["cases"].items():
        out["cases"][x] = out["cases"].get(x, 0) + c
    for l, d in (b.get("date_ctx") or {}).items():
        t = out["date_ctx"].setdefault(l, {})
        for k, c in d.items():
            t[k] = t.get(k, 0) + c
    return out


def prune_stats(st, min_cases=MIN_CASES):
    """存檔前只留跨 min_cases 個案場以上的片段。"""
    keep = {x for x, c in st["cases"].items() if c >= min_cases}
    return dict(st, df={x: d for x, d in st["df"].items() if x in keep}, cases={x: st["cases"][x] for x in keep})


def model_from_stats(st, per_class=PER_CLASS, min_class_docs=MIN_CLASS_DOCS, min_cases=MIN_CASES):
    N = max(1, st["N"])
    total = {x: sum(d.values()) for x, d in st["df"].items()}
    labels = [l for l, n in st["n_by"].items() if n >= min_class_docs]
    by_label = {l: [] for l in labels}
    for x, d in st["df"].items():
        if st["cases"].get(x, 0) < min_cases:
            continue
        for l, c in d.items():
            if l in by_label and c >= 2:
                by_label[l].append((x, c))
    model = {}
    for l in labels:
        nl = st["n_by"][l]
        scored = []
        for x, c in by_label[l]:
            p_in = (c + 0.5) / (nl + 1)
            p_out = (total[x] - c + 0.5) / (N - nl + 1)
            w = math.log(p_in / p_out)
            if w > 0.7:
                scored.append((w * min(1.0, p_in * 2), w, x))
        scored.sort(reverse=True)
        model[l] = {"prior": math.log(nl / N), "w": {x: round(w, 3) for _, w, x in scored[:per_class]}}
    return model


def classify(model_classes, g, allowed=None):
    """回傳 [(分數, 類型, 命中的 [(權重, 片段)])]，分數高的在前。"""
    out = []
    for l, m in model_classes.items():
        if allowed is not None and l not in allowed:
            continue
        hits = [(w, x) for x, w in m["w"].items() if x in g]
        out.append((sum(w for w, _ in hits) + 0.3 * m["prior"], l, hits))
    out.sort(key=lambda t: -t[0])
    return out


def date_context(text, iso):
    """檔名（或確認）的日期在文件中出現時，前面 2～4 個中文字。找不到回傳 []。"""
    t = flat(text)
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except ValueError:
        return []
    roc = y - 1911
    pats = [rf"{roc}\s*年\s*0?{m}\s*月\s*0?{d}\s*日", rf"{roc}[./-]0?{m}[./-]0?{d}(?!\d)",
            rf"{y}\s*年\s*0?{m}\s*月\s*0?{d}\s*日", rf"{y}[./-]0?{m}[./-]0?{d}(?!\d)"]
    for p in pats:
        mm = re.search(p, t)
        if mm:
            before = re.sub(r"[^一-鿿]", "", t[max(0, mm.start() - 12):mm.start()])
            before = before.replace("中華民國", "").replace("民國", "")
            return [before[-n:] for n in (4, 3, 2) if len(before) >= n]
    return []


def date_keys_from_ctx(date_ctx, min_count=3, top=4):
    keys = {}
    for lab, c in (date_ctx or {}).items():
        picked = []
        for k, n in sorted(c.items(), key=lambda kv: -kv[1]):
            if n < min_count:
                break
            if re.search(r"[號巷弄路街段]", k) or any(k in p or p in k for p in picked):
                continue
            picked.append(k)
            if len(picked) >= top:
                break
        if picked:
            keys[lab] = picked
    return keys
