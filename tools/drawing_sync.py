# -*- coding: utf-8 -*-
"""
把 G 槽各案場的「審訖圖」（06 政府函文及相關文件）和「系統送審圖」（04 電廠設計圖）同步到主控台，
讓「採購專區 → 訂單查詢」點進案件時可以直接對照圖面。
2026-10-22 起也同步 06 裡的「台電契約」「細部協商」：主控台上傳時讀出總裝置容量，給「掛表資訊確認」的容量確認用。

  py drawing_sync.py "G:\\共用雲端硬碟\\永續電力處\\02 專案\\01 已上架電廠"            # 掃全部
  py drawing_sync.py "<root>" --case 工程宜蘭9號                                       # 只同步一案
  py drawing_sync.py "<root>" --dry-run                                                # 只列出會上傳什麼
  py drawing_sync.py "<root>\\06 潤特綠能" "<root>\\07 陽光工程" --contracts-only           # 只同步台電契約／細部協商（全部案場，檔案小）

規則：每案每種類型只留「檔名日期最新」的一份 PDF；超過 5MB（Airtable 上限）的會列在最後面請人工處理；
已經上傳過且檔名、修改時間都沒變的不重傳。需要環境變數 EPC_SERVICE_KEY（主控台有開登入保護時用）。
"""
import argparse
import base64
import datetime
import os
import re
import sys

import requests

BACKEND = "https://epc-backend-4aj2.onrender.com"
MAX_BYTES = 5 * 1024 * 1024
CASE_RE = re.compile(r"^\d*\s*((?:工程|潤特)[^\d_\s]+\d+號)")
CAT_RE = re.compile(r"^0?([46])\s*[\.、_ -]?\s*(電廠設計圖|政府函文)")
DATE_RE = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
# (類型, 該類型要找的分類資料夾 04/06, 檔名關鍵字（任一）, 檔名不能有的字)
# 沒指定資料夾時用這兩個（台電契約／細協都放這裡；排程用 sunny_contract_sync.bat，不用在 .bat 裡寫中文路徑）
DEFAULT_ROOTS = [r"G:\共用雲端硬碟\永續電力處\02 專案\01 已上架電廠\06 潤特綠能",
                 r"G:\共用雲端硬碟\永續電力處\02 專案\01 已上架電廠\07 陽光工程"]
KINDS = [("審訖圖", "6", ("審訖圖",), ()), ("系統送審圖", "4", ("系統送審圖",), ()),
         # 台電契約／細部協商：整個案場資料夾（含子資料夾）都找，不限 06（cat=None）
         ("台電契約", None, ("台電契約", "購售契約", "購售電契約"), ("契約函", "契約函文", "租約", "修約")),
         ("細部協商", None, ("細部協商", "細協"), ("補件",))]


try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def log(msg):
    print(msg, flush=True)


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


def pick_latest(case_dir, cat, keywords, excludes=()):
    """案場資料夾底下的某分類資料夾裡，檔名含 keywords 其中之一（且不含 excludes）的 PDF，選檔名日期（沒有就用修改時間）最新的一份。"""
    cands = []
    if cat is None:
        folders = [dp for dp, _, _ in os.walk(case_dir)]
    else:
        folders = []
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
    ap.add_argument("--contracts-only", action="store_true", help="只同步台電契約／細部協商（掛表資訊確認的容量用）")
    args = ap.parse_args()
    args.root = args.root or DEFAULT_ROOTS
    log(datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + " 開始同步")
    kinds = [k for k in KINDS if k[0] in ("台電契約", "細部協商")] if args.contracts_only else KINDS

    try:
        idx = {i["key"]: i for i in api("GET", "/api/procurement/drawings/index").json().get("items", [])}
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
    too_big = []
    for root in args.root:
        cases = find_cases(root)
        log(f"{root}：找到 {len(cases)} 個案場資料夾")
        for case_no, case_dir in cases:
            if args.case and args.case != case_no:
                continue
            if args.open_orders and case_no not in only:
                continue
            for kind, cat, kw, ex in kinds:
                try:
                    best = pick_latest(case_dir, cat, kw, ex)
                except OSError as e:
                    log(f"  ✗ {case_no} {kind} 讀資料夾失敗：{e}")
                    fail += 1
                    continue
                if not best:
                    continue
                doc_date, mtime, path, fn = best
                mt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                old = idx.get(f"{case_no}|{kind}")
                if old and old.get("filename") == fn and old.get("mtime") == mt:
                    skip += 1
                    continue
                size = os.path.getsize(path)
                if size > MAX_BYTES:
                    too_big.append((case_no, kind, fn, round(size / 1048576, 1)))
                    continue
                if args.dry_run:
                    log(f"  ＋ {case_no} {kind}：{fn}（{round(size / 1024)}KB）")
                    up += 1
                    continue
                with open(path, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                try:
                    r = api("POST", "/api/procurement/drawings/sync", timeout=180, json={
                        "case_no": case_no, "kind": kind, "filename": fn, "doc_date": doc_date, "src_path": path, "mtime": mt, "data": data})
                    if r.status_code >= 400:
                        raise Exception(r.text[:200])
                    cap = r.json().get("capacity") if kind in ("台電契約", "細部協商") else None
                    log(f"  ✓ {case_no} {kind}：{fn}" + (f"（容量 {cap} kW）" if cap else (f"（{r.json().get('capacity_src')}）" if kind in ("台電契約", "細部協商") else "")))
                    up += 1
                except Exception as e:
                    log(f"  ✗ {case_no} {kind}：{fn} 上傳失敗：{e}")
                    fail += 1
    log(f"\n完成：上傳 {up}、沒變略過 {skip}、失敗 {fail}")
    if too_big:
        log(f"\n超過 5MB 沒上傳（{len(too_big)} 份）：")
        for c, k, fn, mb in too_big:
            log(f"  {c} {k}：{fn}（{mb}MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
