# -*- coding: utf-8 -*-
"""太陽能電廠工程變更協議書產生器（2026-11-20）。

依使用者提供的協議書範本（assets/agreement_template.docx，編號 聚曜／工程苗栗6號 那一份）：
容量／電價／單價／總價 下修後，產出甲方（綠點能創）與乙方（施工廠商）的變更協議書 docx。
只用標準函式庫（zipfile + 正規表示式改 word/document.xml），不需要 python-docx。

做法：先把「付款期程」七列、容量表的列用範本的列複製出來（各列固定格式），再依序改文字。
"""
import io
import os
import re
import zipfile
from xml.sax.saxutils import escape

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "agreement_template.docx")

NODES = ("簽約款", "同意備案款", "材料訂購款", "工班進場款", "掛錶驗收款", "設備登記款", "正式售電款")

JIA = {"name": "綠點能創股份有限公司", "rep": "馮嘯儒", "tax": "54854026", "addr": "台北市南港區重陽路267號10樓"}

# 乙方（施工廠商）資料：取自各廠商合約範本的簽署頁（contract_gen.inspect_template）
VENDORS = {
    "三創": {"name": "三創能源有限公司", "addr": "新竹縣新豐鄉自立街17巷9號", "rep": "曾宏傑", "tax": "42966356"},
    "光鼎": {"name": "光鼎能源科技有限公司", "addr": "嘉義縣民雄鄉福樂村埤角66號之35一樓", "rep": "劉兆耕", "tax": "42955816"},
    "全富": {"name": "全富能源有限公司", "addr": "新竹縣新豐鄉埔頂38號一樓", "rep": "楊傅強", "tax": "83754779"},
    "凰太竹": {"name": "凰太竹金屬企業有限公司", "addr": "臺中市神岡區神洲路716巷71號1樓", "rep": "林紋瑄", "tax": "53283225"},
    "國欽": {"name": "國欽有限公司", "addr": "高雄市前鎮區保泰路19之2號", "rep": "李宥鋮", "tax": "90685340"},
    "大昇": {"name": "大昇科技有限公司", "addr": "高雄市仁武區澄仁西街183號", "rep": "李禎益", "tax": "54617896"},
    "宇陽達": {"name": "宇陽達有限公司", "addr": "臺中市清水區楊厝里頂三庄路163巷12號", "rep": "曾浤維", "tax": "82860463"},
    "尚展": {"name": "尚展能源科技有限公司", "addr": "苗栗縣造橋鄉朝陽路73之3號", "rep": "葉小溱", "tax": "83754665"},
    "弦華": {"name": "弦華科技企業有限公司", "addr": "高雄市鳳山區高鳳一路77巷6號1樓", "rep": "李驊融", "tax": "83088826"},
    "振庭": {"name": "振庭科技有限公司", "addr": "高雄市大寮區會富街70號", "rep": "李洊有", "tax": "90279379"},
    "日力": {"name": "日力能源有限公司", "addr": "臺中市龍井區西濱路三段53之1號", "rep": "施俊毅", "tax": "60627512"},
    "曙光": {"name": "曙光能創有限公司", "addr": "新北市土城區青雲路49巷12號", "rep": "李汪杰", "tax": "83047993"},
    "聚曜": {"name": "聚曜能源科技有限公司", "addr": "彰化縣田中鎮中山街111號", "rep": "洪伶招", "tax": "42971941"},
    "展亦": {"name": "展亦有限公司", "addr": "高雄市鼓山區鼓山二路37號一樓", "rep": "侯清祥", "tax": "90461094"},
    "昶勛": {"name": "昶勛科技有限公司", "addr": "嘉義市西區南京東街126巷29號", "rep": "蕭旭原", "tax": "54233337"},
    "禾勻": {"name": "禾勻科技有限公司", "addr": "桃園市平鎮區南東路52號4樓之3", "rep": "張文輝", "tax": "90509055"},
}

_T_RE = re.compile(r'(<w:t(?: [^>]*)?>)([^<]*)(</w:t>)')
_TR_RE = re.compile(r'<w:tr[ >].*?</w:tr>', re.S)


def fmt_kw(v):
    s = ('%.2f' % float(v)).rstrip('0').rstrip('.')
    return s or '0'


def money(v):
    return '$' + format(int(round(float(v))), ',')


def contract_date_from_no(no):
    """合約編號 <縣市字母><民國年3><月2><日2><序號1>C → (民國年, 月, 日)；格式不對回 None。"""
    m = re.match(r'^[A-Z](\d{3})(\d{2})(\d{2})\d', (no or '').strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def plan_payments(orig, paid, new_total):
    """orig: {節點: 原含稅金額}；paid: {節點: {...}}（已開發票的節點，金額不動）；new_total: 新的含稅總價。
    已開發票的期別維持原金額，其餘期別依原本比例分攤「新總價 − 已開發票金額」，最後一期補尾差。
    回傳 ({節點: 本協議金額}, 差額須退款金額)。"""
    new = {}
    fixed = {n: float(orig.get(n) or 0) for n in NODES if n in paid}
    new.update(fixed)
    free = [n for n in NODES if n not in paid]
    pool = float(new_total) - sum(fixed.values())
    refund = 0
    if free:
        if pool < 0:
            refund, pool = int(round(-pool)), 0
        base = sum(float(orig.get(n) or 0) for n in free) or 1
        acc = 0
        for i, n in enumerate(free):
            if i == len(free) - 1:
                v = int(round(pool)) - acc
            else:
                v = int(round(pool * float(orig.get(n) or 0) / base))
                acc += v
            new[n] = v
    else:
        refund = max(0, int(round(sum(fixed.values()) - float(new_total))))
    return new, refund


# ---------------------------------------------------------------- 低階：改 document.xml

def _tokens(xml):
    return list(_T_RE.finditer(xml))


def _set_tokens(xml, edits):
    """edits: {token 序號: 新文字}。由後往前取代，序號不會跑掉。"""
    toks = _tokens(xml)
    for idx in sorted(edits, reverse=True):
        m = toks[idx]
        txt = edits[idx]
        xml = xml[:m.start()] + '<w:t xml:space="preserve">' + escape(txt) + m.group(3) + xml[m.end():]
    return xml


def _row_texts(row):
    return [m.group(2) for m in _tokens(row)]


def _row_set(row, mapping):
    return _set_tokens(row, mapping)


def _find_rows(xml):
    return [(m.start(), m.end(), m.group(0)) for m in _TR_RE.finditer(xml)]


def _find_row_with_first(xml, first_text):
    for s, e, r in _find_rows(xml):
        t = _row_texts(r)
        if t and t[0] == first_text:
            return s, e, r
    raise ValueError('範本裡找不到「%s」那一列，範本格式跟預期不同' % first_text)


def _fill_range_row(row, label, orig_rng, orig_text, new_rng, new_text):
    """一列：第 0 格標題、orig_rng 範圍合成 orig_text、new_rng 範圍合成 new_text（其餘 token 清空）。"""
    mp = {0: label}
    for i in range(orig_rng[0], orig_rng[1] + 1):
        mp[i] = orig_text if i == orig_rng[0] else ''
    for i in range(new_rng[0], new_rng[1] + 1):
        mp[i] = new_text if i == new_rng[0] else ''
    return _row_set(row, mp)


def _replace_all_static(xml, old, new):
    """把 <w:t> 內容剛好等於 old 的文字換成 new。"""
    def _r(m):
        return m.group(1) + (escape(new) if m.group(2) == old else m.group(2)) + m.group(3)
    return _T_RE.sub(_r, xml)


# ---------------------------------------------------------------- 產生

def build_docx(d):
    """d（皆為字串／數字，前端可編輯後送回）：
      vendor_name, vendor_rep, vendor_tax, vendor_addr   乙方
      case_name（工程宜蘭1號）, addr_cell（範本「地址」欄，預設放別名）, contract_no
      sign_y, sign_m, sign_d    原合約簽訂日（民國）
      items: ['容量','電價']      本次變動項目；direction: 'down'|'up'|'mixed'
      cap_from, cap_to, price_from, price_to（電價，可空）
      unit_from, unit_to（工程單價 未稅元/kWp）, total_from, total_to（含稅）
      payments: [{node, orig, new, invoice, date}] 七期
      refund（差額須退款，含稅，可為 0）
      date_y, date_m, date_d    本協議日期（民國）
    回傳 docx bytes。"""
    with zipfile.ZipFile(TEMPLATE_PATH) as zf:
        xml = zf.read('word/document.xml').decode('utf-8')
        parts = {n: zf.read(n) for n in zf.namelist()}
        infos = {i.filename: i for i in zf.infolist()}

    # ---- 1. 付款期程：七列都用「簽約款」那一列當樣板複製（含發票號碼／支付日期兩格）
    s0, e0, proto = _find_row_with_first(xml, '簽約款')
    # 範本的七列是連續的 <w:tr>，找到各列的範圍後整段換掉
    spans = []
    for n in NODES:
        try:
            s, e, _ = _find_row_with_first(xml, n if n != '掛錶驗收款' else '掛錶驗收款')
        except ValueError:
            s, e, _ = _find_row_with_first(xml, '掛表驗收款')
        spans.append((s, e))
    new_rows = []
    pays = {p['node']: p for p in d['payments']}
    for n in NODES:
        p = pays.get(n, {})
        mp = {0: n, 1: money(p.get('orig', 0)), 2: '', 3: '', 4: money(p.get('new', 0)), 5: '', 6: '',
              7: p.get('invoice', '') or '', 8: p.get('date', '') or ''}
        new_rows.append(_row_set(proto, mp))
    # 由後往前換
    first_start, last_end = spans[0][0], spans[-1][1]
    xml = xml[:first_start] + ''.join(new_rows) + xml[last_end:]

    # ---- 2. 容量表（容量／工程單價／工程總價 三列；電價有變動就多一列）
    s, e, cap_row = _find_row_with_first(xml, '容量')
    # 第一個「容量」第 0 格的列有可能是表頭上方的段落，這裡只取表格列
    cap_new = _fill_range_row(cap_row, '容量', (1, 1), fmt_kw(d['cap_from']), (2, 6), fmt_kw(d['cap_to']))
    price_row_xml = ''
    s_u, e_u, unit_row = _find_row_with_first(xml, '工程單價')
    if '電價' in d.get('items', []) and d.get('price_from') not in (None, '') and d.get('price_to') not in (None, ''):
        price_row_xml = _fill_range_row(unit_row, '躉購電價', (1, 6), '%s元/度' % _num4(d['price_from']),
                                        (7, 12), '%s元/度' % _num4(d['price_to']))
    unit_new = _fill_range_row(unit_row, '工程單價', (1, 6), money(d['unit_from']) + '/kWp(未稅)',
                               (7, 12), money(d['unit_to']) + '/kWp(未稅)')
    s_t, e_t, total_row = _find_row_with_first(xml, '工程總價')
    total_new = _fill_range_row(total_row, '工程總價', (1, 6), money(d['total_from']) + '(含稅)',
                                (7, 11), money(d['total_to']) + '(含稅)')
    # 由後往前換（總價 → 單價 → 容量），位置不會跑掉
    xml = xml[:s_t] + total_new + xml[e_t:]
    xml = xml[:s_u] + unit_new + xml[e_u:]
    if price_row_xml:
        # 插在容量列後面、單價列前面：同位置先放電價列
        s_u2, e_u2, _ = _find_row_with_first(xml, '工程單價')
        xml = xml[:s_u2] + price_row_xml + xml[s_u2:]
    s, e, _r = _find_row_with_first(xml, '容量')
    xml = xml[:s] + cap_new + xml[e:]

    # ---- 3. 其他文字（用 token 序列定位，不寫死序號）
    toks = _tokens(xml)
    texts = [m.group(2) for m in toks]

    def find(txt, start=0):
        for i in range(start, len(texts)):
            if texts[i] == txt:
                return i
        raise ValueError('範本裡找不到「%s」，範本格式跟預期不同' % txt)

    edits = {}
    # 抬頭：乙方
    j = find('乙方：')
    edits[j + 2] = d['vendor_name']
    # 底線靠兩側底線空白撐（範本 10 個字的公司名＋兩側各 5 格）：名稱每差 1 個字，兩側各差 1 格，底線長度才跟甲方那行一致
    pad = ' ' * max(0, 5 + (10 - len(d['vendor_name'])))
    edits[j + 1] = pad
    edits[j + 3] = pad
    # 前言：容量(、電價)下修，…中華民國(下同)114年12月16日簽訂…
    items = [x for x in d.get('items', []) if x] or ['容量']
    dir_word = {'down': '下修', 'up': '上調'}.get(d.get('direction'), '調整')
    i0 = find('容量')
    edits[i0] = '、'.join(items)
    edits[i0 + 1] = dir_word + '，因故原雙方於中華民國(下同)'
    edits[i0 + 2] = str(d['sign_y'])
    edits[i0 + 4] = str(d['sign_m'])
    edits[i0 + 6] = str(d['sign_d'])
    # 名稱／地址／合約編號
    k = find('合約編號')
    edits[k + 1] = d['case_name']
    edits[k + 2] = ''
    edits[k + 3] = d.get('addr_cell', '')
    edits[k + 4] = d.get('contract_no', '')
    # 付款段落
    p = find('因工程單價調整，工程合約價金亦')
    edits[p] = '因工程%s調整，工程合約價金亦' % ('、'.join(items))
    # 備註（退款）
    q = find('本協議書一式兩份，由甲、乙雙方各持正本一份為憑。')
    refund = int(d.get('refund') or 0)
    if refund > 0:
        edits[q] = '差額須退款金額：%s(含稅)。本協議書一式兩份，由甲、乙雙方各持正本一份為憑。' % money(refund)
    # 簽署頁乙方
    ks = len(texts) - 1 - texts[::-1].index('乙方：')
    edits[ks + 2] = d['vendor_name']
    edits[ks + 5] = d['vendor_rep']
    edits[ks + 7] = d['vendor_tax']
    a0 = ks + 8
    if texts[a0] != '地址：':
        raise ValueError('範本簽署頁乙方地址格式跟預期不同')
    edits[a0 + 2] = d['vendor_addr']
    for t in (a0 + 3, a0 + 4, a0 + 5):
        edits[t] = ''
    # 協議日期
    z = len(texts) - 1 - texts[::-1].index('中華民國')
    edits[z + 1] = str(d['date_y'])
    edits[z + 3] = str(d['date_m'])
    edits[z + 5] = str(d['date_d'])
    xml = _set_tokens(xml, edits)

    # ---- 4. 寫回 docx
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zo:
        for name, data in parts.items():
            if name == 'word/document.xml':
                data = xml.encode('utf-8')
            zo.writestr(infos[name], data)
    return out.getvalue()


def _num4(v):
    s = ('%.4f' % float(v)).rstrip('0').rstrip('.')
    return s
