# -*- coding: utf-8 -*-
"""
PDF 公文更名：用 pdf_learn.py 收集的 samples.jsonl（已改名的歷史檔案＋文字）訓練文件類型分類模型
==========================================================================================
做法（不需要額外套件）：
  - 檔名裡的類型歸併成正式類型（依 app.py PDF_DEFAULT_DOC_TYPES 的 synonyms）
  - 特徵＝文件前 1,500 字裡的中文 2～4 字片段（有沒有出現）
  - 只留「至少 3 個不同案場都出現過」的片段（排除個別案場的地址、人名），
    每類取最有鑑別力的 300 個，權重＝這類出現率 vs 其他類出現率的 log 比
  - 依案場分組做交叉驗證（測試的案場完全沒被學過），估計新檔案的準確度
  - 另外統計每類「檔名日期在文件中前面的字」，產生各類的日期抓取順序（date_keys）
輸出 pdf_model.json（放在 app.py 旁邊，後端啟動時讀取）。

用法：python tools/pdf_train.py samples.jsonl [pdf_model.json]
"""
import collections
import json
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ.setdefault("AIRTABLE_TOKEN", "x")

HEAD = 1500
MIN_CASES = 3
PER_CLASS = 300
MIN_CLASS_DOCS = 5
CJK = re.compile(r"[一-鿿]+")


def flat(text):
    t = (text or "").translate(str.maketrans("０１２３４５６７８９－（）：", "0123456789-():"))
    return re.sub(r"\s+", "", t)


def grams(text):
    out = set()
    for seg in CJK.findall(flat(text)[:HEAD]):
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                out.add(seg[i:i + n])
    return out


def load_canon():
    import app as A
    canon = {}
    for t in A.PDF_DEFAULT_DOC_TYPES:
        canon[t["name"]] = t["name"]
        for x in re.split(r"[、,，]", t.get("synonyms") or ""):
            x = x.strip()
            if x:
                canon[x] = t["name"]
    return canon, A


def norm_label(tb, canon):
    tb = tb.split("_")[-1]
    if tb in canon:
        return canon[tb]
    for k in sorted(canon, key=len, reverse=True):
        if len(k) >= 2 and k in tb:
            return canon[k]
    return None


def train(docs):
    """docs: [(label, case, gramset)] → {label: {"prior": p, "w": {gram: weight}}}"""
    n_by = collections.Counter(d[0] for d in docs)
    labels = [l for l, n in n_by.items() if n >= MIN_CLASS_DOCS]
    df = {l: collections.Counter() for l in labels}
    cases_of = collections.defaultdict(set)
    total = collections.Counter()
    for l, case, g in docs:
        total.update(g)
        for x in g:
            cases_of[x].add(case)
        if l in df:
            df[l].update(g)
    N = len(docs)
    model = {}
    for l in labels:
        nl = n_by[l]
        scored = []
        for x, c in df[l].items():
            if c < 2 or len(cases_of[x]) < MIN_CASES:
                continue
            p_in = (c + 0.5) / (nl + 1)
            p_out = (total[x] - c + 0.5) / (N - nl + 1)
            w = math.log(p_in / p_out)
            if w > 0.7:
                scored.append((w * min(1.0, p_in * 2), w, x))
        scored.sort(reverse=True)
        model[l] = {"prior": math.log(nl / N), "w": {x: round(w, 3) for _, w, x in scored[:PER_CLASS]}}
    return model


def classify(model, g):
    best = []
    for l, m in model.items():
        s = sum(w for x, w in m["w"].items() if x in g) + 0.3 * m["prior"]
        best.append((s, l))
    best.sort(reverse=True)
    return best


def learn_date_keys(rows, canon):
    """每類：檔名日期在文件中出現時，前面 2～6 字的片段 → 依次數排序。"""
    ctx = collections.defaultdict(collections.Counter)
    for r in rows:
        lab = norm_label(r["label"]["type_base"], canon)
        if not lab or not r["label"]["date"]:
            continue
        t = flat(r["text"])
        y, m, d = (int(x) for x in r["label"]["date"].split("-"))
        roc = y - 1911
        pats = [rf"{roc}\s*年\s*0?{m}\s*月\s*0?{d}\s*日", rf"{roc}[./-]0?{m}[./-]0?{d}(?!\d)",
                rf"{y}\s*年\s*0?{m}\s*月\s*0?{d}\s*日", rf"{y}[./-]0?{m}[./-]0?{d}(?!\d)"]
        for p in pats:
            mm = re.search(p, t)
            if mm:
                before = re.sub(r"[^一-鿿]", "", t[max(0, mm.start() - 12):mm.start()])
                before = before.replace("中華民國", "").replace("民國", "")
                if before:
                    for n in (4, 3, 2):
                        if len(before) >= n:
                            ctx[lab][before[-n:]] += 1
                break
    keys = {}
    for lab, c in ctx.items():
        picked = []
        for k, n in c.most_common():
            if n < 3:
                break
            if re.search(r"[號巷弄路街段]", k):   # 地址片段，不是日期標籤
                continue
            if any(k in p or p in k for p in picked):
                continue
            picked.append(k)
            if len(picked) >= 4:
                break
        if picked:
            keys[lab] = picked
    return keys


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pdf_model.json")
    canon, A = load_canon()
    rows = [json.loads(l) for l in open(src, encoding="utf-8")]
    rows = [r for r in rows if r.get("label") and r.get("text") and len(flat(r["text"])) >= 40]
    docs = []
    for r in rows:
        lab = norm_label(r["label"]["type_base"], canon)
        if lab:
            docs.append((lab, r["case_dir"], grams(r["text"]), r))
    print(f"可用樣本 {len(docs)} 份、{len(set(d[0] for d in docs))} 類、{len(set(d[1] for d in docs))} 個案場")

    # 依案場分 5 組交叉驗證
    cases = sorted(set(d[1] for d in docs))
    random.Random(42).shuffle(cases)
    fold_of = {c: i % 5 for i, c in enumerate(cases)}
    ok = tot = 0
    by_cat = collections.Counter()
    by_cat_ok = collections.Counter()
    conf = collections.Counter()
    margins = []   # (領先第二名的分數差, 是否正確) → 換算信心分數
    for k in range(5):
        tr = [(l, c, g) for l, c, g, _ in docs if fold_of[c] != k]
        model = train(tr)
        for l, c, g, r in docs:
            if fold_of[c] != k or l not in model:
                continue
            ranked = classify(model, g)
            pred = ranked[0][1]
            margins.append((ranked[0][0] - ranked[1][0], pred == l))
            cat = r["category"][:2]
            tot += 1
            by_cat[cat] += 1
            if pred == l:
                ok += 1
                by_cat_ok[cat] += 1
            else:
                conf[(l, pred)] += 1
    print(f"交叉驗證（沒看過的案場）類型正確率：{ok}/{tot} = {ok * 100 // max(1, tot)}%")
    for cat in sorted(by_cat):
        print(f"  {cat}：{by_cat_ok[cat]}/{by_cat[cat]} = {by_cat_ok[cat] * 100 // by_cat[cat]}%")
    print("最常搞混：", conf.most_common(12))

    # 信心校正：分數差落在各區間時，交叉驗證實際的正確率
    # 依分數差排序切成 8 段，每段的實際正確率＝該段的信心（[段的最小分數差, 正確率]）
    calib = []
    ms = sorted(margins)
    step = max(1, len(ms) // 8)
    for i in range(0, len(ms), step):
        seg = ms[i:i + step]
        if len(seg) < step // 2 and calib:
            continue
        calib.append([round(seg[0][0], 2), round(sum(o for _, o in seg) / len(seg), 3)])
    print("信心校正（[分數差下限, 這段的實際正確率]）：", calib)

    model = train([(l, c, g) for l, c, g, _ in docs])
    date_keys = learn_date_keys([d[3] for d in docs], canon)
    json.dump({"version": 1, "trained_on": len(docs), "head": HEAD, "classes": model, "date_keys": date_keys,
               "calib": calib, "cv_accuracy": round(ok / max(1, tot), 3)}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"模型已存：{out}（{os.path.getsize(out) // 1024} KB）")
    print("各類日期前文：", {k: v for k, v in list(date_keys.items())[:15]})


if __name__ == "__main__":
    main()
