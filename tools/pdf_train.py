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
import gzip
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
os.environ.setdefault("AIRTABLE_TOKEN", "x")
import pdf_learncore as C   # noqa: E402


def load_canon():
    import app as A
    return C.canon_from_doc_types(A.PDF_DEFAULT_DOC_TYPES), A


def norm_label(tb, canon):
    return C.norm_label(tb, canon)


# 舊程式相容（tools/ 其他分析腳本用）
flat = C.flat
grams = C.grams


def train(docs):
    return C.model_from_stats(C.stats_from_docs(docs))


def classify(model, g):
    return [(s, l) for s, l, _ in C.classify(model, g)]


def main():
    canon, _ = load_canon()
    rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8", errors="replace")]
    model, base = C.build_base(rows, canon)
    with open(os.path.join(ROOT, "pdf_model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)
    with gzip.open(os.path.join(ROOT, "pdf_base_stats.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, separators=(",", ":"))
    print(f"已存 pdf_model.json、pdf_base_stats.json.gz（{os.path.getsize(os.path.join(ROOT, 'pdf_base_stats.json.gz')) // 1024} KB）")


if __name__ == "__main__":
    main()
