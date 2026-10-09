# -*- coding: utf-8 -*-
"""
PDF 公文更名：從「已經改好檔名」的歷史檔案學習辨識規則（在使用者自己的電腦上執行）
================================================================================
後端在 Render 上看不到 G 槽，所以這支程式在使用者電腦上跑：
  1. 掃描已上架電廠底下每個案場的 03 契約／04 電廠設計圖／06 政府函文及相關文件／
     07 設備保固及出廠證明 資料夾。
  2. 把人工改好的檔名（例如 桃1_20250106_併聯審查.pdf）拆成「簡稱／日期／文件類型」，
     當作正確答案。
  3. 讀 PDF 前幾頁的文字（電子檔直接讀；掃描檔可選用主控台設定好的 Google OCR）。
  4. 分析每種文件：靠哪些關鍵字可以分辨、日期在文件上是怎麼寫的（發文日期／中華民國／
     簽約日…）、目前的規則能猜對幾成，產生 report.md（給人看）跟 report.json（給後端
     匯入規則用）。
每個類型「在每個區域」最多抽樣 --per-type 份（預設 10，各區平均學到），已讀過的檔案會快取，中斷後重跑會接著做。

用法（Windows 命令提示字元／PowerShell）：
  pip install pypdf requests
  python pdf_learn.py "G:\\共用雲端硬碟\\永續電力處\\02 專案\\01 已上架電廠"
  （掃描檔要 OCR：加 --ocr；每次最多 OCR --ocr-limit 份，預設 150）
結果在同一層的 pdf_learn_data\\ 資料夾：report.md、report.json、samples.jsonl。
"""
import argparse
import base64
import collections
import io
import json
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("請先安裝：pip install pypdf requests")
    sys.exit(1)

BACKEND = "https://epc-backend-4aj2.onrender.com"
CATEGORY_RE = re.compile(r"^0?([3467])\s*[\.、_ -]?\s*(契約|電廠設計圖|政府函文|設備保固)")
CATEGORY_NAMES = {"3": "03 契約", "4": "04 電廠設計圖", "6": "06 政府函文及相關文件", "7": "07 設備保固及出廠證明"}
DATE_TOKEN_RE = re.compile(r"^(20\d{2})(\d{2})(\d{2})$|^(1\d{2})(\d{2})(\d{2})$")
CJK = "\u4e00-\u9fff"
MAX_TEXT = 3000
MIN_TEXT = 40
FULLWIDTH = str.maketrans("０１２３４５６７８９－（）．／：", "0123456789-()./:")


def log(*a):
    print(*a, flush=True)


# ---------------- 檔名解析 ----------------

def parse_filename(stem):
    """桃1_20250106_併聯審查 → (桃1, 2025-01-06, 併聯審查)；桃1_免雜附件一 → (桃1, '', 免雜附件一)。"""
    parts = [p for p in re.split(r"[_＿]", stem.strip()) if p.strip()]
    if len(parts) < 2:
        return None
    prefix, date, rest = "", "", []
    for i, p in enumerate(parts):
        m = DATE_TOKEN_RE.match(p.strip())
        if m and not date:
            if m.group(1):
                date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            else:
                date = f"{int(m.group(4)) + 1911}-{m.group(5)}-{m.group(6)}"
            continue
        if i == 0:
            prefix = p.strip()
        else:
            rest.append(p.strip())
    if not rest:
        return None
    doc_type = "_".join(rest)
    base = re.sub(r"\s*[\(（]\d+[\)）]$", "", doc_type)                 # 檔名(1)
    base = re.sub(r"附件[一二三四五六七八九十\d]*$", "附件", base)          # 免雜附件一 → 免雜附件
    base = re.sub(r"[-_ ]?\d+$", "", base) or doc_type                     # 契約2 → 契約
    return {"prefix": prefix, "date": date, "type": doc_type, "type_base": base.strip()}


# ---------------- 讀 PDF ----------------

def pdf_text(path, max_pages=3):
    with open(path, "rb") as f:
        data = f.read()
    reader = PdfReader(io.BytesIO(data))
    pages = len(reader.pages)
    text = "\n".join((p.extract_text() or "") for p in reader.pages[:max_pages])
    return data, reader, pages, text


def first_pages_pdf(reader, n=2):
    w = PdfWriter()
    for p in reader.pages[:n]:
        w.add_page(p)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def ocr(pdf_bytes, url):
    import requests
    r = requests.post(url, json={"pdf": base64.b64encode(pdf_bytes).decode()}, timeout=300)
    data = r.json()
    if not data.get("ok"):
        raise Exception(data.get("error") or "OCR 失敗")
    return data.get("text") or ""


def flat(text):
    t = (text or "").translate(FULLWIDTH).replace("　", " ")
    return re.sub(r"\s+", "", t)


# ---------------- 收集 ----------------

def find_targets(root, max_depth=5):
    """找出所有 03/04/06/07 資料夾，回傳 (分類, 案場資料夾, 區域, 資料夾路徑)。
    雲端硬碟每打開一個資料夾都要連網路，所以一找到「案場」（底下有 03/04/06/07 的資料夾）
    就只進這幾個分類，案場裡其他資料夾（施工照片、空拍…動輒上千個檔案）完全不打開。"""
    queue = [(root, 0)]
    scanned = 0
    while queue:
        path, depth = queue.pop(0)
        try:
            subdirs = sorted(e.name for e in os.scandir(path) if e.is_dir())
        except OSError as e:
            log(f"  讀不到資料夾，略過：{path}（{e}）")
            continue
        scanned += 1
        if scanned % 20 == 0:
            log(f"  已掃描 {scanned} 個資料夾…（目前：{os.path.basename(path)}）")
        cats = [(d, CATEGORY_RE.match(d.strip())) for d in subdirs]
        cats = [(d, m) for d, m in cats if m]
        if cats:  # 這是案場資料夾
            region = os.path.basename(os.path.dirname(path))
            for d, m in cats:
                yield CATEGORY_NAMES[m.group(1)], os.path.basename(path), region, os.path.join(path, d)
            continue
        if depth < max_depth:
            queue.extend((os.path.join(path, d), depth + 1) for d in subdirs)


def collect(args, out_dir):
    cache_path = os.path.join(out_dir, "samples.jsonl")
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    cache[r["key"]] = r
                except Exception:
                    pass
    log(f"已快取 {len(cache)} 份，開始掃描資料夾（雲端硬碟第一次讀取會比較慢）…")

    files = []
    n_folders = 0
    for cat, case_dir, region, folder in find_targets(args.root):
        n_folders += 1
        for dirpath, _, fnames in os.walk(folder):
            for fn in fnames:
                files.append((cat, case_dir, region, os.path.join(dirpath, fn), fn))
        if n_folders % 20 == 0:
            log(f"  已找到 {n_folders} 個分類資料夾、{len(files)} 個檔案…")
    log(f"找到 {len(files)} 個檔案（含非 PDF）")

    if args.only:
        files = [f for f in files if f[0].startswith(args.only.zfill(2))]
        log(f"只處理 {args.only}：{len(files)} 個檔案")
    # 06 政府函文最重要（也幾乎都是掃描檔），先處理 06 → 04 → 07 → 03
    order = {"06": 0, "04": 1, "07": 2, "03": 3}
    # 同一分類裡各區域輪流排（桃園一份、新竹一份、臺中一份…），OCR 額度才不會都用在前面幾區
    groups = collections.defaultdict(list)
    for f in files:
        groups[(order.get(f[0][:2], 9), f[2])].append(f)
    files = []
    for cat_order in sorted({k[0] for k in groups}):
        regs = [groups[k] for k in sorted(groups) if k[0] == cat_order]
        for i in range(max(len(g) for g in regs)):
            files.extend(g[i] for g in regs if i < len(g))

    ocr_url = args.ocr_url
    if args.ocr and not ocr_url:
        for attempt in range(3):   # Render 免費方案剛醒來可能要 1 分鐘
            try:
                import requests
                ocr_url = requests.get(BACKEND + "/api/pdf-rename/status", timeout=120).json()["settings"].get("ocr_url", "")
                break
            except Exception as e:
                log(f"讀取主控台 OCR 設定失敗（第 {attempt + 1} 次）：{e}")
    if args.ocr:
        if not ocr_url:
            log("⚠ 沒有 OCR 網址，掃描檔不會 OCR（主控台「⚙ 命名格式與函文規則」設定，或加 --ocr-url）")
        else:
            try:
                import requests
                info = requests.get(ocr_url, timeout=60).json()
                log(f"OCR 連線測試：{info.get('message') or info}")
                if "v2" not in str(info.get("message", "")):
                    log("⚠ Apps Script 不是最新版（v2），OCR 可能會失敗（Invalid Value）。"
                        "請到主控台設定畫面複製新程式碼，並用「管理部署作業 → 新版本」重新部署")
            except Exception as e:
                log(f"⚠ OCR 連線測試失敗，掃描檔不會 OCR：{e}")
                ocr_url = ""
    ocr_errors = collections.Counter()
    per_type = collections.Counter()
    ocr_used = 0
    # errors="replace"：少數 PDF 抽出來的文字有壞掉的字元（例如單獨的 surrogate），寫不進 UTF-8 檔會整個中斷，改成問號
    out = open(cache_path, "a", encoding="utf-8", errors="replace")
    rows = []
    last_log, n_cached, n_new = time.time(), 0, 0
    for i, (cat, case_dir, region, path, fn) in enumerate(files):
        # 每 30 秒回報一次進度（讀過的檔案會直接跳過、OCR 一份要 10～40 秒，不回報看起來像停住）
        if time.time() - last_log > 30:
            log(f"  {i}/{len(files)}…（沿用上次讀過的 {n_cached} 份、這次新讀 {n_new} 份、OCR {ocr_used} 份）目前：{fn[:40]}")
            last_log = time.time()
        stem, ext = os.path.splitext(fn)
        label = parse_filename(stem)
        row = {"category": cat, "case_dir": case_dir, "region": region, "file": fn,
               "rel": os.path.relpath(path, args.root), "ext": ext.lower(), "label": label}
        if ext.lower() != ".pdf" or not label:
            rows.append(row)
            continue
        tkey = (cat, label["type_base"], region)
        try:
            st = os.stat(path)
        except OSError:
            continue
        key = f"{row['rel']}|{st.st_size}|{int(st.st_mtime)}"
        if key in cache and not (args.ocr and ocr_url and cache[key].get("scan") and not cache[key].get("ocr")
                                 and ocr_used < args.ocr_limit) and not cache[key].get("error"):
            rows.append(cache[key])
            per_type[tkey] += 1
            n_cached += 1
            continue
        if per_type[tkey] >= args.per_type or st.st_size > args.max_mb * 1024 * 1024:
            rows.append(row)
            continue
        try:
            data, reader, pages, text = pdf_text(path)
            row.update(pages=pages, size=st.st_size)
            if len(re.sub(r"\s", "", text)) < MIN_TEXT:
                row["scan"] = True
                if args.ocr and ocr_url and ocr_used < args.ocr_limit:
                    ocr_used += 1
                    try:
                        text = ocr(first_pages_pdf(reader), ocr_url)
                        row["ocr"] = True
                    except Exception as e:
                        msg = f"{type(e).__name__}: {e}"[:160]
                        ocr_errors[msg] += 1
                        row["ocr_error"] = msg
                        if ocr_errors[msg] <= 2:
                            log(f"  ⚠ OCR 失敗（{fn}）：{msg}")
                        if sum(ocr_errors.values()) >= 10 and not any(r.get("ocr") for r in rows[-30:]):
                            log("  ⚠ OCR 連續失敗，這次先停止 OCR，請把上面的錯誤訊息截圖給 Claude")
                            ocr_url = ""
            row["text"] = text[:MAX_TEXT]
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"[:200]
        row["key"] = key
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        out.flush()
        rows.append(row)
        per_type[tkey] += 1
        n_new += 1
    out.close()
    if ocr_errors:
        log("OCR 錯誤統計：")
        for msg, n in ocr_errors.most_common(5):
            log(f"  {n} 次：{msg}")
    log(f"這次 OCR 了 {ocr_used} 份")
    return rows


# ---------------- 分析 ----------------

def date_variants(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    r = y - 1911
    return [f"{r}年{m}月{d}日", f"{r}年{m:02d}月{d:02d}日", f"{r}.{m:02d}.{d:02d}", f"{r}.{m}.{d}",
            f"{r}/{m:02d}/{d:02d}", f"{r}/{m}/{d}", f"{r}-{m:02d}-{d:02d}",
            f"{y}年{m}月{d}日", f"{y}年{m:02d}月{d:02d}日", f"{y}/{m:02d}/{d:02d}", f"{y}/{m}/{d}",
            f"{y}-{m:02d}-{d:02d}", f"{y}.{m:02d}.{d:02d}", f"{y}{m:02d}{d:02d}", f"{r}{m:02d}{d:02d}"]


def date_context(text, iso):
    """檔名日期在文件裡出現的位置與前面的字（例如「發文日期:中華民國」）。"""
    t = flat(text)
    for v in date_variants(iso):
        k = t.find(v)
        if k >= 0:
            ctx = re.sub(r"[0-9.:/-]", "", t[max(0, k - 12):k])[-8:]
            return ctx or "(開頭)", k
    return None, None


def grams(text, head=600):
    """標題區（前 head 字）的中文 3～6 字詞片段（2 字太短，容易抓到「照乙」這種無意義片段）。"""
    t = re.sub(f"[^{CJK}]", " ", flat(text)[:head])
    out = set()
    for seg in t.split():
        for n in range(3, 7):
            for i in range(len(seg) - n + 1):
                out.add(seg[i:i + n])
    return out


def learn_keywords(docs_by_type, min_support=0.5, top=8):
    """每個類型找「這類大多有、其他類很少有」的詞。"""
    all_types = list(docs_by_type)
    df = {t: collections.Counter() for t in all_types}
    n = {t: len(docs_by_type[t]) for t in all_types}
    for t, docs in docs_by_type.items():
        for g in docs:
            df[t].update(g)
    total_df = collections.Counter()
    for t in all_types:
        total_df.update(df[t])
    n_all = sum(n.values())
    result = {}
    for t in all_types:
        scored = []
        for g, c in df[t].items():
            p_in = c / n[t]
            if p_in < min_support:
                continue
            out_c = total_df[g] - c
            p_out = out_c / max(1, n_all - n[t])
            scored.append((p_in - p_out, p_in, p_out, g))
        scored.sort(key=lambda x: (-round(x[0], 2), len(x[3])))   # 分數一樣時取短的（比較通用）
        picked = []
        for s in scored:
            if s[0] < 0.3:
                break
            if any(s[3] in p[3] or p[3] in s[3] for p in picked):
                continue
            picked.append(s)
            if len(picked) >= top:
                break
        result[t] = [{"kw": p[3], "in": round(p[1], 2), "out": round(p[2], 3)} for p in picked]
    return result


def classify(g, kw):
    best, best_s = None, 0
    for t, kws in kw.items():
        s = sum(1 for k in kws if k["kw"] in g)
        s = s / max(1, len(kws))
        if s > best_s:
            best, best_s = t, s
    return best


# 文件上的編號（跟後端 app.py 的 PDF_ID_RULES 同一套；後端匯入 report.json 時用來補 Airtable 空白的編號欄位）
ID_RULES = [
    ("同意備案編號", r"備案編號", r"([A-Z]{3}-?\d{3}-?PV-?\d{3,4})"),
    ("設備登記編號", r"設備登記編號", r"([A-Z]{3}-?(?:[A-Z]{2,4}-?)?\d{3}-?PV-?\d{3,4})"),
    ("臺電受理編號", r"(?:受理編號|公司編號)", r"(\d{6}PV\d{4})"),
    ("台電契約編號", r"(?<!登記)契約編號", r"(\d{2}-?PV-?\d{3}-?\d{4})"),
    ("電表租約編號", r"契約登記編號", r"((?:\d{2}-)?PV-\d{3}-\d{4})"),
    ("電號", r"電號", r"(\d{2}-?\d{2}-?\d{4}-?\d{2}-?\d)(?!\d)"),
]
ID_FW = str.maketrans("０１２３４５６７８９－（）：ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ",
                      "0123456789-():ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def extract_ids(text):
    t = re.sub(r"\s+", "", (text or "").translate(ID_FW))
    out = {}
    for field, label, fmt in ID_RULES:
        vals = []
        for m in re.finditer(label + r"[為:：(（「\[]{0,3}" + fmt, t):
            if m.group(1) not in vals:
                vals.append(m.group(1))
        if vals:
            out[field] = vals[:5]
    return out


def analyze(rows, out_dir):
    pdfs = [r for r in rows if r.get("label") and r.get("ext") == ".pdf"]
    with_text = [r for r in pdfs if r.get("text") and len(flat(r["text"])) >= MIN_TEXT]
    lines = ["# PDF 公文更名：歷史檔案分析報告", ""]
    lines.append(f"- 檔案總數：{len(rows)}；PDF 且檔名可解析：{len(pdfs)}；有讀到文字：{len(with_text)}")
    unparsed = [r for r in rows if r.get("ext") == ".pdf" and not r.get("label")]
    lines.append(f"- 檔名不符合「簡稱_日期_類型」：{len(unparsed)}（例：" +
                 "、".join(r["file"] for r in unparsed[:8]) + "）")
    lines.append("")

    # 1. 命名：每個分類的類型與數量、簡稱對照
    lines += ["## 1. 文件類型（依檔名）", "", "| 分類 | 類型 | 份數 | 檔名有日期 | 電子檔比例 | 範例檔名 |", "|---|---|---|---|---|---|"]
    by_cat_type = collections.defaultdict(list)
    for r in rows:
        if r.get("label"):
            by_cat_type[(r["category"], r["label"]["type_base"])].append(r)
    type_stats = []
    for (cat, t), rs in sorted(by_cat_type.items(), key=lambda x: (x[0][0], -len(x[1]))):
        n_date = sum(1 for r in rs if r["label"]["date"])
        read = [r for r in rs if "text" in r or r.get("scan")]
        n_textlayer = sum(1 for r in read if not r.get("scan"))
        type_stats.append({"category": cat, "type": t, "count": len(rs), "with_date": n_date})
        lines.append(f"| {cat} | {t} | {len(rs)} | {n_date * 100 // len(rs)}% | "
                     f"{(n_textlayer * 100 // len(read)) if read else '-'}% | {rs[0]['file']} |")
    lines.append("")

    aliases = collections.defaultdict(collections.Counter)
    for r in rows:
        if r.get("label") and r["label"]["prefix"]:
            aliases[(r["region"], r["case_dir"])][r["label"]["prefix"]] += 1
    alias_map = [{"region": k[0], "case_dir": k[1], "prefix": c.most_common(1)[0][0],
                  "others": [p for p, _ in c.most_common()[1:4]]} for k, c in sorted(aliases.items())]
    lines += ["## 2. 案場資料夾 → 簡稱", "", f"共 {len(alias_map)} 個案場（完整清單在 report.json）；前 30 筆：", "",
              "| 區域 | 案場資料夾 | 簡稱 | 其他寫法 |", "|---|---|---|---|"]
    for a in alias_map[:30]:
        lines.append(f"| {a['region']} | {a['case_dir']} | {a['prefix']} | {'、'.join(a['others'])} |")
    lines.append("")

    # 3. 日期在文件裡的寫法
    lines += ["## 3. 檔名日期在文件中的位置（決定每種文件要抓哪個日期）", "",
              "| 類型 | 有文字的份數 | 找得到檔名日期 | 最常見的前文（日期前面的字） |", "|---|---|---|---|"]
    date_rules = {}
    by_type_text = collections.defaultdict(list)
    for r in with_text:
        by_type_text[r["label"]["type_base"]].append(r)
    for t, rs in sorted(by_type_text.items(), key=lambda x: -len(x[1])):
        dated = [r for r in rs if r["label"]["date"]]
        ctxs = collections.Counter()
        found = 0
        for r in dated:
            ctx, _ = date_context(r["text"], r["label"]["date"])
            if ctx:
                found += 1
                ctxs[ctx] += 1
        date_rules[t] = {"samples": len(dated), "found": found, "contexts": ctxs.most_common(5)}
        lines.append(f"| {t} | {len(rs)} | {found}/{len(dated)} | " +
                     "、".join(f"「{c}」×{n}" for c, n in ctxs.most_common(4)) + " |")
    lines.append("")

    # 4. 關鍵字學習 + 用學到的關鍵字自我驗證（分一半學、一半驗）
    docs = collections.defaultdict(list)
    for r in with_text:
        docs[r["label"]["type_base"]].append(r)
    docs = {t: rs for t, rs in docs.items() if len(rs) >= 3}
    train = {t: [grams(r["text"]) for r in rs[::2]] for t, rs in docs.items()}
    kw_train = learn_keywords(train)
    correct = total = 0
    confusion = collections.Counter()
    for t, rs in docs.items():
        for r in rs[1::2]:
            p = classify(grams(r["text"]), kw_train)
            total += 1
            if p == t:
                correct += 1
            else:
                confusion[(t, p)] += 1
    kw_all = learn_keywords({t: [grams(r["text"]) for r in rs] for t, rs in docs.items()})
    lines += ["## 4. 每種文件的辨識關鍵字（標題區、這類常有而其他類少有）", "",
              f"用一半檔案學、另一半驗證：只靠關鍵字分類正確率 **{correct}/{total}"
              f"（{(correct * 100 // total) if total else 0}%）**（實際系統還會加上案件編號比對、日期規則）", "",
              "| 類型 | 份數 | 關鍵字（本類出現率／其他類出現率） |", "|---|---|---|"]
    for t, kws in sorted(kw_all.items(), key=lambda x: -len(docs[x[0]])):
        lines.append(f"| {t} | {len(docs[t])} | " + "、".join(f"{k['kw']}({k['in']}/{k['out']})" for k in kws) + " |")
    lines += ["", "最常搞混：", ""]
    for (a, b), c in confusion.most_common(12):
        lines.append(f"- {a} 被判成 {b or '（無）'}：{c} 次")
    lines.append("")

    # 5. 每類抽 3 份標題區文字，給人／給我看文件長相
    lines += ["## 5. 各類文件開頭文字範例（每類 3 份，前 300 字）", ""]
    for t, rs in sorted(docs.items(), key=lambda x: -len(x[1])):
        lines.append(f"### {t}")
        for r in rs[:3]:
            lines.append(f"- `{r['file']}`（{r['region']}／{'OCR' if r.get('ocr') else '文字層'}）："
                         + flat(r["text"])[:300].replace("|", "｜"))
        lines.append("")

    # 6. 每份文件上的編號（同意備案、設備登記、受理、台電契約、電表租約、電號）
    case_ids = []
    for r in with_text:
        ids = extract_ids(r["text"])
        if ids:
            case_ids.append({"case_dir": r["case_dir"], "type_base": r["label"]["type_base"], "ids": ids})
    lines += ["## 6. 文件上的編號", "", f"{len(case_ids)} 份文件讀到編號，涵蓋 {len(set(x['case_dir'] for x in case_ids))} 個案場。"
              "到主控台匯入 report.json 會自動填進 Airtable 專案細節空白的編號欄位（已有的不覆蓋）。", ""]

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "case_ids": case_ids,
        "type_stats": type_stats,
        "aliases": alias_map,
        "date_rules": date_rules,
        "keywords": kw_all,
        "holdout_accuracy": [correct, total],
        "confusion": [[a, b, c] for (a, b), c in confusion.most_common(30)],
        "scans_without_text": sum(1 for r in pdfs if r.get("scan") and not r.get("ocr")),
        "ocr_done": sum(1 for r in pdfs if r.get("ocr")),
        "ocr_errors": collections.Counter(r["ocr_error"] for r in pdfs if r.get("ocr_error") and not r.get("ocr")).most_common(5),
    }
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8", errors="replace") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "report.md"), "w", encoding="utf-8", errors="replace") as f:
        f.write("\n".join(lines))
    return report


def main():
    ap = argparse.ArgumentParser(description="從已改名的歷史檔案學習公文辨識規則")
    ap.add_argument("root", help="已上架電廠資料夾，例如 G:\\共用雲端硬碟\\永續電力處\\02 專案\\01 已上架電廠")
    ap.add_argument("--per-type", type=int, default=10, help="每個（分類, 類型, 區域）最多讀幾份，預設 10")
    ap.add_argument("--max-mb", type=int, default=25, help="超過幾 MB 的檔案略過，預設 25")
    ap.add_argument("--ocr", action="store_true", help="掃描檔用主控台設定的 Google OCR 轉文字")
    ap.add_argument("--ocr-url", default="", help="指定 OCR 網址（預設讀主控台設定）")
    ap.add_argument("--ocr-limit", type=int, default=400, help="這次最多 OCR 幾份，預設 400")
    ap.add_argument("--only", default="", help="只處理某個分類，例如 --only 06")
    ap.add_argument("--out", default="", help="輸出資料夾，預設是這支程式旁邊的 pdf_learn_data")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        log("找不到資料夾：", args.root)
        sys.exit(1)
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_learn_data")
    os.makedirs(out_dir, exist_ok=True)
    rows = collect(args, out_dir)
    report = analyze(rows, out_dir)
    acc = report["holdout_accuracy"]
    log("")
    log(f"完成！類型 {len(report['type_stats'])} 種、案場 {len(report['aliases'])} 個、"
        f"關鍵字驗證正確率 {acc[0]}/{acc[1]}、已 OCR {report['ocr_done']} 份、還沒 OCR 的掃描檔 {report['scans_without_text']} 份")
    log("請把這兩個檔案傳給 Claude：")
    log("  ", os.path.join(out_dir, "report.md"))
    log("  ", os.path.join(out_dir, "report.json"))


if __name__ == "__main__":
    main()
