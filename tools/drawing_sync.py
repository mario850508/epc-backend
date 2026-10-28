# -*- coding: utf-8 -*-
"""
把 G 槽各案場的「審訖圖」（06 政府函文及相關文件）和「系統送審圖」（04 電廠設計圖）同步到主控台，
讓「採購專區 → 訂單查詢」點進案件時可以直接對照圖面。
2026-10-22 起也同步「台電契約」「細部協商」、10-23 起同步 03 的「工程合約」：主控台上傳時讀出容量／電價，給「掛表資訊確認」比對用。

  py drawing_sync.py "G:\\共用雲端硬碟\\永續電力處\\02 專案\\01 已上架電廠"            # 掃全部
  py drawing_sync.py "<root>" --case 工程宜蘭9號                                       # 只同步一案
  py drawing_sync.py "<root>" --dry-run                                                # 只列出會上傳什麼
  py drawing_sync.py "<root>\\06 潤特綠能" "<root>\\07 陽光工程" --contracts-only           # 只同步台電契約／細部協商（全部案場，檔案小）

2026-10-26 起契約的文字辨識（PDF 文字層＋Google OCR）改在這台電腦做，再把文字傳給主控台算容量／電價
（主控台只有 512MB 記憶體，辨識大檔會被系統殺掉、一直重開）。--reparse 會把主控台上「還沒讀到容量」的契約
下載下來在本機重讀；平常執行完同步也會順便重讀一批（--reparse-limit，預設 100 份）。

規則：每案每種類型只留「檔名日期最新」的一份 PDF；超過 5MB（Airtable 上限）的會列在最後面請人工處理；
已經上傳過且檔名、修改時間都沒變的不重傳。需要環境變數 EPC_SERVICE_KEY（主控台有開登入保護時用）。
"""
import argparse
import base64
import datetime
import time
import os
import re
import sys

import requests

BACKEND = "https://epc-backend-4aj2.onrender.com"
MAX_BYTES = 30 * 1024 * 1024   # 主控台收件上限
# 2026-10-25：5MB 以上一律在本機先切前 6 頁再傳。大檔交給主控台切會吃光 Render 記憶體 → 502、伺服器重開。
TRIM_BYTES = 5 * 1024 * 1024
CASE_RE = re.compile(r"^\d*\s*((?:工程|潤特)[^\d_\s]+\d+號)")
CAT_RE = re.compile(r"^0?([46])\s*[\.、_ -]?\s*(電廠設計圖|政府函文)")
DATE_RE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
# (類型, 該類型要找的分類資料夾 04/06, 檔名關鍵字（任一）, 檔名不能有的字)
# 沒指定資料夾時用這兩個（台電契約／細協都放這裡；排程用 sunny_contract_sync.bat，不用在 .bat 裡寫中文路徑）
DEFAULT_ROOTS = [r"G:\共用雲端硬碟\永續電力處\02 專案\01 已上架電廠\06 潤特綠能",
                 r"G:\共用雲端硬碟\永續電力處\02 專案\01 已上架電廠\07 陽光工程"]
KINDS = [("審訖圖", "6", ("審訖圖",), ()), ("系統送審圖", "4", ("系統送審圖",), ()),
         # 台電契約／細部協商：整個案場資料夾（含子資料夾）都找，不限 06（cat=None）
         ("台電契約", None, ("台電契約", "購售契約", "購售電契約"), ("契約函", "契約函文", "租約", "修約", "帳戶", "匯款")),
         ("細部協商", None, ("細部協商", "細協"), ("補件",)),
         # 2026-10-26：跟台電換文修改購售契約（容量變更等），掛表資訊確認優先用它的容量
         ("換文修約", None, ("換文修約", "修約"), ()),
         # 2026-10-23：03 資料夾的工程合約（跟 EPC 簽的容量、躉購電價、工程單價）＝掛表資訊確認的比對基準
         # 2026-10-28 使用者：檔名有「(潤特)」的是我們的上包合約（潤特↔綠點），不是跟 EPC 簽的 → 不要；
         # 跟 EPC 的是「宜40_工程合約.pdf」或「宜40_工程合約(EPC).pdf」
         ("工程合約", None, ("工程合約", "工程契約"), ("(潤特)", "（潤特）", "_潤特", "(潤特 "))]
CONTRACT_KINDS = ("台電契約", "細部協商", "換文修約", "工程合約")


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drawing_sync_last.log")


def log(msg):
    """印在畫面上，也寫進 drawing_sync_last.log（每次執行重寫），視窗關掉也查得到。"""
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def api(method, path, **kw):
    headers = dict(kw.pop("headers", None) or {})
    key = os.environ.get("EPC_SERVICE_KEY", "").strip()
    if key:
        headers["X-Service-Key"] = key
    return requests.request(method, BACKEND + path, headers=headers, timeout=kw.pop("timeout", 120), **kw)


def find_cases(root):
    """回傳 [(案號, 案場資料夾)]，找到案場資料夾就不再往下走。"""
    out = []
    for dirpath, dirnames, _ in os.walk(root):
        for d in list(dirnames):
            m = CASE_RE.match(d)
            if m:
                out.append((m.group(1), os.path.join(dirpath, d)))
                dirnames.remove(d)
    return out


def have_pdf_lib():
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        try:
            import PyPDF2  # noqa: F401
            return True
        except ImportError:
            return False


def first_pages(path, n=6):
    """超過 30MB 的 PDF（台電契約常 35～55MB 掃描檔）在本機先切前 n 頁再傳；容量／電價都在前幾頁。
    需要 pypdf 或 PyPDF2（Anaconda 通常有 PyPDF2）；都沒有就回 None。"""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        try:
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError:
            return None
    import io
    reader = PdfReader(path)
    writer = PdfWriter()
    for pg in reader.pages[:n]:
        writer.add_page(pg)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


_OCR_URL = {"v": None}


def ocr_url():
    """Google OCR（Apps Script）網址：跟「PDF 公文更名」同一個，從主控台設定讀。"""
    if _OCR_URL["v"] is None:
        try:
            r = api("GET", "/api/pdf-rename/status", timeout=60)
            _OCR_URL["v"] = ((r.json().get("settings") or {}).get("ocr_url") or "").strip()
        except Exception as e:
            log(f"讀取 OCR 設定失敗（之後的掃描檔會讀不到文字）：{e}")
            _OCR_URL["v"] = ""
    return _OCR_URL["v"]


def _pdf_reader(data):
    import io
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    return PdfReader(io.BytesIO(data))


def pdf_text_layer(data, pages=10):
    return "\n".join((p.extract_text() or "") for p in _pdf_reader(data).pages[:pages])


def first_pages_bytes(data, n=6):
    import io
    try:
        from pypdf import PdfWriter
    except ImportError:
        from PyPDF2 import PdfWriter
    reader = _pdf_reader(data)
    if len(reader.pages) <= n:
        return data
    w = PdfWriter()
    for pg in reader.pages[:n]:
        w.add_page(pg)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def read_text(data, kind):
    """契約 PDF → (文字, 讀不到的原因)。先讀文字層；沒有關鍵字（掃描檔）就用 Google OCR（只送前 6 頁）。"""
    need = "躉購電價" if kind == "工程合約" else "總裝置容量"
    text, err = "", ""
    try:
        text = pdf_text_layer(data)
    except Exception as e:
        err = f"讀文字層失敗：{e}"
    if need in text:
        return text, ""
    url = ocr_url()
    if not url:
        return text, err or "掃描檔，主控台沒有設定 Google OCR"
    try:
        head = first_pages_bytes(data, 6)
        resp = requests.post(url, json={"pdf": base64.b64encode(head).decode()}, timeout=300)
        j = resp.json()
        if not j.get("ok"):
            return text, "OCR 失敗：" + str(j.get("error") or "未知錯誤")[:80]
        return j.get("text") or text, ""
    except Exception as e:
        return text, f"OCR 失敗：{e}"[:120]


def reparse_unread(limit):
    """主控台上還沒讀到容量的契約：下載附件、本機辨識文字、回傳。
    2026-10-26：Airtable 附件網址約 2 小時就過期（下載到的會是「This URL has expired…」文字），
    一次重讀幾百份要跑好幾小時 → 每 45 分鐘重拿一次網址；下載到的不是 PDF 也會換新網址再試一次。"""
    def fetch_urls():
        return {i["id"]: i for i in api("GET", "/api/procurement/drawings/unread").json().get("items", [])}
    try:
        items = fetch_urls()
    except Exception as e:
        log(f"讀取待重讀清單失敗：{e}")
        return
    fetched_at = time.time()
    todo = [i for i in items.values() if i.get("url")]
    log(f"\n主控台上還沒讀到容量的契約 {len(items)} 份（有附件 {len(todo)} 份），這次處理 {min(limit, len(todo))} 份")
    if not have_pdf_lib():
        log("⚠️ 這台電腦沒有 PDF 套件（py -m pip install pypdf），沒辦法重讀")
        return

    def download(rid):
        nonlocal items, fetched_at
        if time.time() - fetched_at > 45 * 60:
            items, fetched_at = fetch_urls(), time.time()
        for attempt in (1, 2):
            it = items.get(rid)
            if not it or not it.get("url"):
                return None
            data = requests.get(it["url"], timeout=180).content
            if data[:5] == b"%PDF-":
                return data
            if attempt == 1:   # 網址過期 → 重拿一次再試
                items, fetched_at = fetch_urls(), time.time()
        raise Exception("下載到的不是 PDF（附件網址過期或檔案壞掉）")

    ok = fail = 0
    for it in todo[:limit]:
        try:
            data = download(it["id"])
            if data is None:
                continue   # 這期間已經被讀好或被新的一份取代
            text, why = read_text(data, it["kind"])
            body = {"id": it["id"]}
            if text.strip():
                body["text"] = text[:12000]
            else:
                body["error"] = why or "沒有文字"
            r = api("POST", "/api/procurement/drawings/parsed", json=body, timeout=120)
            if r.status_code >= 400:
                raise Exception(f"HTTP {r.status_code} {r.text[:120]}")
            j = r.json()
            log(f"  {'✓' if text.strip() else '·'} {it['key']}：{j.get('src') or why}")
            ok += 1
        except Exception as e:
            log(f"  ✗ {it.get('key')}：{e}")
            fail += 1
    log(f"重讀完成：成功 {ok}、失敗 {fail}" + (f"，還有 {len(todo) - limit} 份下次再讀" if len(todo) > limit else ""))


def pick_latest(case_dirs, cat, keywords, excludes=()):
    """案場資料夾（同一案可能有好幾個：地區資料夾、買賣合約相關、撤案案件…，2026-10-25 起合併看）底下，
    檔名含 keywords 其中之一（且不含 excludes）的 PDF，選檔名日期（沒有就用修改時間）最新的一份。"""
    if isinstance(case_dirs, str):
        case_dirs = [case_dirs]
    cands = []
    folders = []
    for case_dir in case_dirs:
        if cat is None:
            folders += [dp for dp, _, _ in os.walk(case_dir)]
        else:
            for d in os.listdir(case_dir):
                m = CAT_RE.match(d)
                if m and m.group(1) == cat and os.path.isdir(os.path.join(case_dir, d)):
                    folders.append(os.path.join(case_dir, d))
    for folder in folders:
        for fn in os.listdir(folder):
            if (any(k in fn for k in keywords) and not any(x in fn for x in excludes)
                    and fn.lower().endswith(".pdf") and not fn.startswith("~")):
                p = os.path.join(folder, fn)
                dm = DATE_RE.search(fn)
                doc_date = "-".join(dm.groups()) if dm else ""
                cands.append((doc_date, os.path.getmtime(p), p, fn))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="*", help="案場根資料夾；不給就用 DEFAULT_ROOTS")
    ap.add_argument("--case", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--open-orders", action="store_true",
                    help="只同步「還沒出貨」(已成立／可能撤案) 訂單的案件，省 Airtable 空間；全部案場約 1.4GB，不建議全傳")
    ap.add_argument("--contracts-only", action="store_true", help="只同步台電契約／細部協商／工程合約（掛表資訊確認用）")
    ap.add_argument("--reparse", action="store_true", help="不掃資料夾，只把主控台上還沒讀到容量的契約下載下來在本機重讀")
    ap.add_argument("--reparse-limit", type=int, default=100, help="每次最多重讀幾份（預設 100）")
    args = ap.parse_args()
    args.root = args.root or DEFAULT_ROOTS
    try:
        open(LOG_PATH, "w", encoding="utf-8").close()   # 每次執行重寫記錄檔
    except OSError:
        pass
    log(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + " 開始同步")
    kinds = [k for k in KINDS if k[0] in CONTRACT_KINDS] if args.contracts_only else KINDS
    if args.reparse:
        reparse_unread(args.reparse_limit)
        return 0

    try:
        r0 = api("GET", "/api/procurement/drawings/index")
        if r0.status_code == 401:
            log("主控台有登入保護，要先設定服務金鑰：在命令提示字元執行 setx EPC_SERVICE_KEY \"<Render 上 SERVICE_KEY 的值>\"，"
                "關掉視窗、開一個新的再跑一次")
            return 1
        idx = {i["key"]: i for i in r0.json().get("items", [])}
    except Exception as e:
        log(f"讀取主控台已上傳清單失敗：{e}")
        return 1
    log(f"主控台已有 {len(idx)} 份圖面")
    only = set()
    if args.open_orders:
        for st in ("已成立", "可能撤案"):
            try:
                only |= {r["case_no"] for r in api("GET", "/api/procurement/orders", params={"status": st}).json().get("rows", []) if r.get("case_no")}
            except Exception as e:
                log(f"讀取 {st} 訂單失敗：{e}")
                return 1
        log(f"還沒出貨的訂單共 {len(only)} 個案件")
    up = skip = fail = 0
    too_big, failed = [], []
    # 同一個案號可能有好幾個資料夾（地區資料夾＋「買賣合約相關」＋「撤案案件」…）→ 合併成一案一起挑最新的，
    # 不然兩個資料夾的檔案會輪流蓋掉對方（2026-10-25 發現：每次都整批重傳的真正原因）
    merged = {}
    for root in args.root:
        found = find_cases(root)
        log(f"{root}：找到 {len(found)} 個案場資料夾")
        for case_no, case_dir in found:
            merged.setdefault(case_no, []).append(case_dir)
    log(f"合併後共 {len(merged)} 個案件")
    if not have_pdf_lib():
        log("⚠️ 這台電腦沒有切 PDF 的套件，5MB 以上的檔案會整份上傳，容易讓主控台當掉。"
            "請先按 Ctrl+C 停掉，執行 py -m pip install pypdf 再跑一次。")
    if True:
        for case_no, case_dir in merged.items():
            if args.case and args.case != case_no:
                continue
            if args.open_orders and case_no not in only:
                continue
            for kind, cat, kw, ex in kinds:
                try:
                    best = pick_latest(case_dir, cat, kw, ex)
                except OSError as e:
                    log(f"  ✗ {case_no} {kind} 讀資料夾失敗：{e}")
                    failed.append((case_no, kind, "", f"讀資料夾失敗：{e}"))
                    fail += 1
                    continue
                if not best:
                    continue
                doc_date, mtime, path, fn = best
                mt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                old = idx.get(f"{case_no}|{kind}")
                if old and old.get("manual"):   # 主控台頁面手動上傳過的就以那份為準，不用 G 槽的蓋掉
                    skip += 1
                    continue
                size = os.path.getsize(path)
                # 檔名一樣，而且（修改時間一樣 或 大小一樣）就當沒變。G 槽（Google 雲端硬碟）回報的修改時間偶爾會跳，
                # 2026-10-24 只靠修改時間時，台電契約／細協被整批重傳。
                if old and old.get("filename") == fn and (old.get("mtime") == mt or old.get("size_kb") == round(size / 1024)):
                    skip += 1
                    continue
                data_bytes = None
                if size > TRIM_BYTES and not args.dry_run:
                    try:
                        data_bytes = first_pages(path)
                    except Exception as e:
                        log(f"  ✗ {case_no} {kind}：{fn} 切前 6 頁失敗：{e}")
                    if data_bytes is None and size > MAX_BYTES:
                        too_big.append((case_no, kind, fn, round(size / 1048576, 1)))
                        continue
                if args.dry_run:
                    log(f"  ＋ {case_no} {kind}：{fn}（{round(size / 1024)}KB）")
                    up += 1
                    continue
                if data_bytes is None:
                    with open(path, "rb") as f:
                        data_bytes = f.read()
                data = base64.b64encode(data_bytes).decode()
                extra = {}
                if kind in CONTRACT_KINDS:    # 契約：文字在本機辨識，主控台只算容量／電價
                    if have_pdf_lib():
                        text, why = read_text(data_bytes, kind)
                        extra = {"text": text[:12000]} if text.strip() else {"text_failed": why or "沒有文字"}
                    else:
                        extra = {"text_failed": "上傳的電腦沒有 PDF 套件（py -m pip install pypdf）"}
                try:
                    for attempt in (1, 2, 3, 4):   # 主控台重開／部署時會 502 → 等 60 秒再試，最多 4 次
                        try:
                            r = api("POST", "/api/procurement/drawings/sync", timeout=300, json={
                                "case_no": case_no, "kind": kind, "filename": fn, "doc_date": doc_date, "src_path": path, "mtime": mt,
                                "orig_size": size, "trimmed": len(data_bytes) < size, "data": data, **extra})
                            if r.status_code >= 400:
                                raise Exception(f"HTTP {r.status_code} {r.text[:200]}")
                            break
                        except Exception:
                            if attempt == 4:
                                raise
                            log(f"    （主控台沒回應，60 秒後重試第 {attempt + 1} 次）")
                            time.sleep(60)
                    j = r.json()
                    info = ("（本機已讀文字）" if j.get("local_read") else "（容量／電價主控台背景讀取中）" if j.get("parsing") else "") + (j.get("note") or "")
                    log(f"  ✓ {case_no} {kind}：{fn}{info}")
                    up += 1
                except Exception as e:
                    log(f"  ✗ {case_no} {kind}：{fn} 上傳失敗：{e}")
                    failed.append((case_no, kind, fn, str(e)[:120]))
                    fail += 1
    log(f"\n完成：上傳 {up}、沒變略過 {skip}、失敗 {fail}")
    if not args.dry_run and not args.case:
        reparse_unread(args.reparse_limit)
    if failed:
        log(f"\n失敗清單（{len(failed)} 份，再跑一次會重試）：")
        for c, k, fn, why in failed:
            log(f"  {c} {k}：{fn} → {why}")
    if too_big:
        log(f"\n超過 30MB 沒上傳（{len(too_big)} 份；先執行 py -m pip install pypdf 再跑一次，就會自動只傳前 6 頁）：")
        for c, k, fn, mb in too_big:
            log(f"  {c} {k}：{fn}（{mb}MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
