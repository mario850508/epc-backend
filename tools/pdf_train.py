# -*- coding: utf-8 -*-
"""
PDF 公文更名：用 pdf_learn.py 收集的 samples.jsonl（已改名的歷史檔案＋文字）訓練文件類型分類模型
==========================================================================================
  - 檔名裡的類型歸併成正式類型（依 app.py PDF_DEFAULT_DOC_TYPES 的 synonyms）
  - 特徵／權重的計算在 pdf_learncore.py（後端每天自動重新學習也用同一套）
  - 依案場分組 5 折交叉驗證（測試的案場完全沒被學過），估計新檔案的準確度，並做信心校正
輸出（放在 repo 根目錄，跟 app.py 一起部署）：
  pdf_model.json           分類模型（後端沒有自動重新學習的結果時用這份）
  pdf_base_stats.json.gz   歷史資料的用字統計：後端每天把「主控台確認過的檔案」加上這份重新學習

用法：python tools/pdf_train.py samples.jsonl
"""
import collections
import gzip
import json
import os
import random
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
os.environ.setdefault("AIRTABLE_TOKEN", "x")
import pdf_learncore as C   # noqa: E402


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


# 舊程式相容（tools/ 其他分析腳本用）
flat = C.flat
grams = C.grams


def train(docs):
    return C.model_from_stats(C.stats_from_docs(docs))


def classify(model, g):
    return [(s, l) for s, l, _ in C.classify(model, g)]


def main():
    src = sys.argv[1]
    canon, A = load_canon()
    rows = [json.loads(l) for l in open(src, encoding="utf-8")]
    rows = [r for r in rows if r.get("label") and r.get("text") and len(C.flat(r["text"])) >= 40]
    docs = []
    for r in rows:
        lab = norm_label(r["label"]["type_base"], canon)
        if lab:
            docs.append((lab, r["case_dir"], C.grams(r["text"]), r))
    print(f"可用樣本 {len(docs)} 份、{len(set(d[0] for d in docs))} 類、{len(set(d[1] for d in docs))} 個案場")

    cases = sorted(set(d[1] for d in docs))
    random.Random(42).shuffle(cases)
    fold_of = {c: i % 5 for i, c in enumerate(cases)}
    ok = tot = 0
    by_cat, by_cat_ok, conf = collections.Counter(), collections.Counter(), collections.Counter()
    margins = []
    for k in range(5):
        model = train([(l, c, g) for l, c, g, _ in docs if fold_of[c] != k])
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

    # 信心校正：依分數差排序切 8 段，每段的實際正確率＝信心
    calib = []
    ms = sorted(margins)
    step = max(1, len(ms) // 8)
    for i in range(0, len(ms), step):
        seg = ms[i:i + step]
        if len(seg) < step // 2 and calib:
            continue
        calib.append([round(seg[0][0], 2), round(sum(o for _, o in seg) / len(seg), 3)])
    print("信心校正（[分數差下限, 這段的實際正確率]）：", calib)

    st = C.stats_from_docs([(l, c, g) for l, c, g, _ in docs])
    date_ctx = collections.defaultdict(collections.Counter)
    for l, c, g, r in docs:
        if r["label"]["date"]:
            for k in C.date_context(r["text"], r["label"]["date"]):
                date_ctx[l][k] += 1
    st["date_ctx"] = {l: dict(c) for l, c in date_ctx.items()}
    model = {"version": 2, "trained_on": len(docs), "base_docs": len(docs), "confirmed_docs": 0,
             "head": C.HEAD, "classes": C.model_from_stats(st), "date_keys": C.date_keys_from_ctx(st["date_ctx"]),
             "calib": calib, "cv_accuracy": round(ok / max(1, tot), 3)}
    with open(os.path.join(ROOT, "pdf_model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)
    base = dict(C.prune_stats(st), calib=calib, cv_accuracy=model["cv_accuracy"])
    with gzip.open(os.path.join(ROOT, "pdf_base_stats.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, separators=(",", ":"))
    print(f"已存 pdf_model.json、pdf_base_stats.json.gz（{os.path.getsize(os.path.join(ROOT, 'pdf_base_stats.json.gz')) // 1024} KB）")


if __name__ == "__main__":
    main()
