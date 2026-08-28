<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<title>陽光管理主控台</title>
<style>
  :root{
    --bg:#F3F5FA;
    --surface:#FFFFFF;
    --surface-2:#F8F9FD;
    --primary:#2B5FF6;
    --primary-dark:#1E46C4;
    --primary-soft:#E8EEFF;
    --epc:#E8890C;
    --epc-soft:#FDF1DF;
    --text:#1B2333;
    --text-muted:#6B7280;
    --border:#E4E8F1;
    --success:#16A34A;
    --success-soft:#E7F7EE;
    --radius:14px;

    /* milestone colors */
    --m-ship:#E8890C;    --m-ship-soft:#FDF1DF;
    --m-rebar:#8B5CF6;   --m-rebar-soft:#F1ECFE;
    --m-enter:#2B5FF6;   --m-enter-soft:#E8EEFF;
    --m-meter:#16A34A;   --m-meter-soft:#E7F7EE;
  }
  *{box-sizing:border-box;}
  body{
    margin:0;
    font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,-apple-system,sans-serif;
    background:var(--bg);
    color:var(--text);
    display:flex;
    min-height:100vh;
  }

  /* ---------- Sidebar ---------- */
  .sidebar{
    width:236px;flex-shrink:0;background:var(--surface);
    border-right:1px solid var(--border);padding:24px 16px;
    display:flex;flex-direction:column;gap:22px;
  }
  .brand{display:flex;align-items:center;gap:10px;padding:0 8px;}
  .brand-mark{
    width:34px;height:34px;border-radius:10px;
    background:linear-gradient(135deg,var(--primary),#6FA1FF);
    display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:15px;
  }
  .brand-name{font-weight:700;font-size:15px;letter-spacing:.02em;}
  .brand-sub{font-size:11px;color:var(--text-muted);margin-top:1px;}
  .nav-group-label{font-size:11px;color:var(--text-muted);padding:0 10px;margin-bottom:6px;letter-spacing:.06em;}
  .nav{display:flex;flex-direction:column;gap:3px;}
  .nav-item{
    display:flex;align-items:center;gap:10px;padding:10px 10px;border-radius:10px;
    font-size:13.5px;color:var(--text);cursor:pointer;border:1px solid transparent;
    transition:background .15s ease;
  }
  .nav-item:hover{background:var(--surface-2);}
  .nav-item.active{background:var(--primary-soft);color:var(--primary-dark);font-weight:600;}
  .nav-icon{width:20px;height:20px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}
  .nav-sub{padding-left:30px;display:flex;flex-direction:column;gap:2px;margin-top:2px;}
  .nav-sub-item{
    font-size:12px;color:var(--text-muted);padding:6px 8px;border-radius:8px;cursor:pointer;
  }
  .nav-sub-item:hover{background:var(--surface-2);}
  .nav-sub-item.active{background:var(--primary-soft);color:var(--primary-dark);font-weight:600;}
  .sidebar-footer{margin-top:auto;padding:12px 10px;border-top:1px solid var(--border);font-size:11px;color:var(--text-muted);}

  /* ---------- Main ---------- */
  .main{flex:1;min-width:0;padding:28px 34px 40px;}
  .topbar{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:22px;gap:16px;flex-wrap:wrap;}
  .crumb{font-size:12px;color:var(--text-muted);margin-bottom:4px;}
  .page-title{font-size:22px;font-weight:700;margin:0;}
  .page-sub{font-size:13px;color:var(--text-muted);margin-top:4px;}

  .pipeline{
    display:flex;align-items:stretch;background:var(--surface);border:1px solid var(--border);
    border-radius:var(--radius);padding:16px 20px;margin-bottom:24px;overflow-x:auto;
  }
  .pipe-step{display:flex;align-items:center;gap:12px;flex:1;min-width:150px;}
  .pipe-num{
    width:26px;height:26px;border-radius:50%;background:var(--surface-2);border:1px solid var(--border);
    display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:var(--text-muted);flex-shrink:0;
  }
  .pipe-step.done .pipe-num{background:var(--success);border-color:var(--success);color:#fff;}
  .pipe-step.active .pipe-num{background:var(--primary);border-color:var(--primary);color:#fff;}
  .pipe-label{font-size:12.5px;font-weight:600;}
  .pipe-desc{font-size:11px;color:var(--text-muted);margin-top:1px;}
  .pipe-arrow{width:28px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#C7CCDA;font-size:14px;}

  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:26px;}
  .stat-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px 20px;}
  .stat-label{font-size:12px;color:var(--text-muted);}
  .stat-value{font-size:26px;font-weight:700;margin-top:6px;}
  .stat-sub{font-size:11.5px;color:var(--text-muted);margin-top:2px;}

  .module-card{
    background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
    padding:22px 24px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;
    cursor:pointer;transition:border-color .15s ease, box-shadow .15s ease;
  }
  .module-card:hover{border-color:#C9D5FB;box-shadow:0 2px 10px rgba(43,95,246,.08);}
  .module-left{display:flex;gap:16px;align-items:flex-start;}
  .module-icon{width:44px;height:44px;border-radius:12px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:20px;}
  .module-icon.pdf{background:var(--primary-soft);color:var(--primary-dark);}
  .module-icon.epc{background:var(--epc-soft);color:var(--epc);}
  .module-title{font-size:15.5px;font-weight:700;}
  .module-desc{font-size:12.5px;color:var(--text-muted);margin-top:3px;max-width:440px;line-height:1.5;}
  .module-tag{font-size:10.5px;padding:2px 8px;border-radius:20px;margin-left:8px;font-weight:600;}
  .tag-local{background:#EEF0F5;color:#6B7280;}
  .tag-cloud{background:var(--success-soft);color:var(--success);}
  .chevron{color:#C7CCDA;font-size:18px;}

  .view{display:none;}
  .view.active{display:block;}

  .btn{
    border:none;border-radius:10px;padding:9px 16px;font-size:13px;font-weight:600;
    cursor:pointer;display:inline-flex;align-items:center;gap:6px;
  }
  .btn-primary{background:var(--primary);color:#fff;}
  .btn-primary:hover{background:var(--primary-dark);}
  .btn-ghost{background:var(--surface);border:1px solid var(--border);color:var(--text);}
  .btn-danger{background:#E5484D;color:#fff;}
  .btn-danger:hover{background:#C9383D;}

  .panel{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px;}
  .panel-title{font-size:14px;font-weight:700;margin:0 0 14px;display:flex;align-items:center;gap:8px;}

  /* ---- PDF module tabs (公文更名 / LINE收件紀錄) ---- */
  .tabs{display:flex;gap:4px;border-bottom:1px solid var(--border);margin-bottom:18px;}
  .tab{
    padding:10px 16px;font-size:13px;font-weight:600;color:var(--text-muted);
    cursor:pointer;border-bottom:2px solid transparent;
  }
  .tab.active{color:var(--primary-dark);border-bottom-color:var(--primary);}
  .subview{display:none;}
  .subview.active{display:block;}
  table{width:100%;border-collapse:collapse;font-size:12.5px;}
  th{text-align:left;color:var(--text-muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--border);font-size:11.5px;}
  td{padding:10px 10px;border-bottom:1px solid var(--border);vertical-align:top;}
  tr:last-child td{border-bottom:none;}
  .pm-pill{font-size:10.5px;padding:2px 8px;border-radius:20px;background:var(--surface-2);color:var(--text-muted);font-weight:600;}

  /* ---------- EPC Calendar ---------- */
  .cal-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:12px;}
  .cal-nav{display:flex;align-items:center;gap:10px;}
  .cal-month{font-size:16px;font-weight:700;min-width:110px;text-align:center;}
  .icon-btn{
    width:30px;height:30px;border-radius:8px;border:1px solid var(--border);background:var(--surface);
    cursor:pointer;font-size:13px;color:var(--text-muted);
  }
  .legend{display:flex;gap:14px;flex-wrap:wrap;}
  .legend-item{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--text-muted);}
  .dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;}
  .dot-ship{background:var(--m-ship);}
  .dot-rebar{background:var(--m-rebar);}
  .dot-enter{background:var(--m-enter);}
  .dot-meter{background:var(--m-meter);}

  .cal-grid{
    display:grid;grid-template-columns:repeat(7,1fr);
    border:1px solid var(--border);border-radius:12px;overflow:hidden;
  }
  .cal-dow{
    background:var(--surface-2);color:var(--text-muted);font-size:11px;font-weight:600;
    text-align:center;padding:8px 0;border-bottom:1px solid var(--border);
  }
  .cal-cell{
    min-height:96px;border-right:1px solid var(--border);border-bottom:1px solid var(--border);
    padding:6px;background:var(--surface);display:flex;flex-direction:column;gap:3px;cursor:pointer;
  }
  .cal-cell:hover{background:var(--surface-2);}
  .cal-cell.cal-cell-selected{background:var(--primary-soft);box-shadow:inset 0 0 0 2px var(--primary);}
  .cal-cell:nth-child(7n){border-right:none;}
  .cal-cell.muted{background:var(--surface-2);}
  .cal-date{font-size:11px;color:var(--text-muted);margin-bottom:2px;}
  .cal-date.today{
    color:#fff;background:var(--primary);width:20px;height:20px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;font-weight:700;
  }
  .chip{
    font-size:10px;padding:2px 6px;border-radius:6px;font-weight:600;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  }
  .chip-ship{background:var(--m-ship-soft);color:var(--m-ship);}
  .chip-rebar{background:var(--m-rebar-soft);color:var(--m-rebar);}
  .chip-enter{background:var(--m-enter-soft);color:var(--m-enter);}
  .chip-meter{background:var(--m-meter-soft);color:var(--m-meter);}

  .epc-bottom{display:block;margin-top:16px;}
  .day-detail-row{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid var(--border);font-size:12.5px;}
  .day-detail-row:last-child{border-bottom:none;}
  .dd-left{display:flex;align-items:center;gap:8px;}
  .case-id{font-weight:700;font-family:ui-monospace,monospace;font-size:12px;white-space:nowrap;}

  .phone-wrap{display:flex;flex-direction:column;align-items:center;}
  .phone{width:210px;border-radius:30px;background:#0F1420;padding:11px;box-shadow:0 12px 30px rgba(20,30,60,.18);}
  .phone-screen{background:var(--bg);border-radius:20px;overflow:hidden;height:330px;display:flex;flex-direction:column;}
  .phone-bar{background:var(--primary);color:#fff;padding:12px 12px 10px;}
  .phone-bar-title{font-size:12.5px;font-weight:700;}
  .phone-bar-sub{font-size:10px;opacity:.85;margin-top:2px;}
  .phone-body{padding:10px;display:flex;flex-direction:column;gap:8px;overflow-y:auto;}
  .phone-card{background:var(--surface);border-radius:11px;padding:9px 10px;border:1px solid var(--border);}
  .phone-case{font-size:11px;font-weight:700;font-family:ui-monospace,monospace;}
  .phone-addr{font-size:10px;color:var(--text-muted);margin-top:2px;line-height:1.4;}
  .phone-row{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;}
  .phone-caption{font-size:10.5px;color:var(--text-muted);margin-top:10px;text-align:center;max-width:200px;line-height:1.5;}

  .vendor-pill{
    font-size:10.5px;padding:3px 9px;border-radius:20px;font-weight:700;white-space:nowrap;
  }
  .vendor-sc{background:#FDECEC;color:#D64545;}
  .vendor-sz{background:#E9F3FF;color:#1E70C8;}
  .vendor-sg{background:#FFF3D9;color:#B37A00;}
  .vendor-gd{background:#EAF7EE;color:#1E8A4C;}
  .vendor-other{background:var(--surface-2);color:var(--text-muted);}

  .vendor-filter{display:flex;gap:8px;margin:10px 0 16px;flex-wrap:wrap;}
  .vendor-chip{
    font-size:12px;font-weight:600;padding:7px 14px;border-radius:20px;
    border:1px solid var(--border);background:var(--surface);color:var(--text-muted);
    cursor:pointer;transition:all .15s ease;
  }
  .vendor-chip:hover{border-color:#C9D5FB;}
  .vendor-chip.active{background:var(--text);color:#fff;border-color:var(--text);}
  .vendor-chip.vendor-sc.active{background:#D64545;border-color:#D64545;}
  .vendor-chip.vendor-sz.active{background:#1E70C8;border-color:#1E70C8;}
  .vendor-chip.vendor-sg.active{background:#B37A00;border-color:#B37A00;}
  .vendor-chip.vendor-gd.active{background:#1E8A4C;border-color:#1E8A4C;}
  .chip.chip-dim{opacity:.15;}

  .quick-mark{position:relative;}
  .quick-mark-input-wrap{position:relative;}
  .quick-mark-input{
    width:100%;border:1px solid var(--border);border-radius:10px;padding:11px 14px;
    font-size:13px;font-family:inherit;color:var(--text);background:var(--surface-2);
  }
  .quick-mark-input:focus{outline:none;border-color:var(--primary);background:var(--surface);}
  .note-add-row{display:flex;gap:10px;}
  .note-add-row .quick-mark-input{flex:1;}
  .note-add-row-wide input:first-child{flex:0 0 200px;}
  .note-add-row-wide input:nth-child(2){flex:1;}

  .notes-trigger-btn{margin-left:auto;padding:7px 14px;font-size:12.5px;}
  .notes-trigger-btn + .notes-trigger-btn{margin-left:8px;}

  .pending-toolbar{display:flex;justify-content:flex-start;align-items:center;gap:12px;margin:14px 0;flex-wrap:wrap;}
  .sortable-th{cursor:pointer;user-select:none;}
  .sortable-th:hover{color:var(--primary-dark);}
  .case-alias{font-size:11px;color:var(--text-muted);margin-top:1px;}

  .filter-th{position:relative;cursor:pointer;user-select:none;}
  .filter-th:hover{color:var(--primary-dark);}
  #vendorFilterLabel{color:var(--primary-dark);font-weight:700;}
  .vendor-dropdown{
    display:none;position:absolute;top:calc(100% + 6px);left:0;
    background:var(--surface);border:1px solid var(--border);border-radius:10px;
    box-shadow:0 10px 26px rgba(20,30,60,.14);z-index:10;min-width:130px;overflow:hidden;
    font-weight:400;text-transform:none;
  }
  .vendor-dropdown.show{display:block;}
  .vendor-dropdown-item{
    padding:9px 14px;font-size:12.5px;color:var(--text);cursor:pointer;white-space:nowrap;
  }
  .vendor-dropdown-item:hover{background:var(--surface-2);}
  .vendor-dropdown-item.active{color:var(--primary-dark);font-weight:700;background:var(--primary-soft);}

  .modal-overlay{
    display:none;position:fixed;inset:0;background:rgba(20,25,40,.45);
    z-index:50;align-items:flex-start;justify-content:center;padding:6vh 20px;
    overflow-y:auto;
  }
  .modal-overlay.show{display:flex;}
  .modal-box{
    background:var(--bg);border-radius:16px;max-width:720px;width:100%;
    box-shadow:0 20px 60px rgba(20,30,60,.25);overflow:hidden;
  }
  .modal-header{
    display:flex;align-items:center;justify-content:space-between;
    padding:16px 20px;background:var(--surface);border-bottom:1px solid var(--border);
  }
  .modal-title{font-size:15px;font-weight:700;}
  .modal-close{
    width:28px;height:28px;border-radius:8px;border:none;background:var(--surface-2);
    color:var(--text-muted);font-size:13px;cursor:pointer;
  }
  .modal-close:hover{background:var(--border);}
  .modal-body{padding:18px 20px;max-height:70vh;overflow-y:auto;}

  .toast{
    position:fixed;top:24px;left:50%;transform:translateX(-50%) translateY(-16px);
    background:#B8720A;color:#fff;padding:13px 22px;border-radius:10px;
    font-size:13px;font-weight:600;box-shadow:0 10px 28px rgba(0,0,0,.22);
    z-index:100;opacity:0;pointer-events:none;transition:all .2s ease;max-width:90vw;text-align:center;
  }
  .toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
  .quick-mark-results{
    position:absolute;left:0;right:0;top:calc(100% + 6px);background:var(--surface);
    border:1px solid var(--border);border-radius:10px;box-shadow:0 8px 24px rgba(20,30,60,.10);
    z-index:5;overflow:hidden;display:none;
  }
  .quick-mark-results.show{display:block;}
  .qm-result{
    display:flex;justify-content:space-between;align-items:center;padding:11px 14px;
    cursor:pointer;border-bottom:1px solid var(--border);
  }
  .qm-result:last-child{border-bottom:none;}
  .qm-result:hover{background:var(--surface-2);}
  .qm-result-name{font-size:13px;font-weight:600;}
  .qm-result-addr{font-size:11px;color:var(--text-muted);margin-top:2px;}
  .qm-mark-btn{
    font-size:11.5px;font-weight:700;color:#fff;background:var(--epc);
    border:none;border-radius:8px;padding:6px 12px;cursor:pointer;flex-shrink:0;
  }
  .qm-empty{padding:12px 14px;font-size:12px;color:var(--text-muted);}
  .qm-confirmed{
    display:none;align-items:center;gap:8px;margin-top:10px;padding:10px 12px;
    background:var(--success-soft);color:var(--success);border-radius:10px;font-size:12.5px;font-weight:600;
  }
  .qm-confirmed.show{display:flex;}

  .warn-pill{
    display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;
    padding:3px 9px;border-radius:20px;background:#FFF0D6;color:#B8720A;
  }

  .login-note{
    display:flex;gap:10px;align-items:flex-start;background:var(--surface-2);border:1px dashed var(--border);
    border-radius:10px;padding:12px 14px;margin-top:14px;font-size:11.5px;color:var(--text-muted);line-height:1.6;
  }
</style>
</head>
<body>

  <div class="toast" id="toastBanner"></div>

  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">陽</div>
      <div>
        <div class="brand-name">陽光管理主控台</div>
        <div class="brand-sub">Sunny Ops Console</div>
      </div>
    </div>

    <div>
      <div class="nav-group-label">功能模組</div>
      <div class="nav">
        <div class="nav-item" data-view="home" onclick="showView('home')">
          <span class="nav-icon">🏠</span> 總覽
        </div>
        <div class="nav-item" data-view="pdf" onclick="showView('pdf')">
          <span class="nav-icon">📄</span> PDF 公文更名
        </div>
        <div class="nav-sub">
          <div class="nav-sub-item" data-sub="pdf-rename" onclick="showPdfTab('pdf-rename')">公文更名</div>
          <div class="nav-sub-item" data-sub="pdf-line" onclick="showPdfTab('pdf-line')">LINE 收件紀錄</div>
        </div>
        <div class="nav-item" data-view="epc" onclick="showView('epc')">
          <span class="nav-icon">🚚</span> EPC 出貨／進場排程
        </div>
        <div class="nav-sub">
          <div class="nav-sub-item" data-sub="epc-week" onclick="showEpcTab('epc-week')">近一週安排</div>
          <div class="nav-sub-item" data-sub="epc-calendar" onclick="showEpcTab('epc-calendar')">排程日曆</div>
          <div class="nav-sub-item" data-sub="epc-pending" onclick="showEpcTab('epc-pending')">待安排出貨&植筋</div>
          <div class="nav-sub-item" data-sub="epc-entry" onclick="showEpcTab('epc-entry')">案件進場安排</div>
          <div class="nav-sub-item" data-sub="epc-meter" onclick="showEpcTab('epc-meter')">掛表安排</div>
          <div class="nav-sub-item" data-sub="epc-issue" onclick="showEpcTab('epc-issue')">異常案件</div>
          <div class="nav-sub-item" data-sub="epc-archive" onclick="showEpcTab('epc-archive')">歷史紀錄</div>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      本機模組與雲端模組並存<br>V0.2 介面原型
    </div>
  </aside>

  <main class="main">

    <!-- ============ HOME ============ -->
    <section class="view" id="view-home">
      <div class="topbar">
        <div>
          <div class="crumb">總覽</div>
          <h1 class="page-title">今日狀態</h1>
          <div class="page-sub">整合本機工具與雲端 EPC 排程,一個入口管理所有案件流程</div>
        </div>
      </div>

      <div class="pipeline">
        <div class="pipe-step done">
          <div class="pipe-num">✓</div>
          <div><div class="pipe-label">LINE 收件</div><div class="pipe-desc">自動分類,併入 PDF 更名模組</div></div>
        </div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-step active">
          <div class="pipe-num">2</div>
          <div><div class="pipe-label">PDF 更名</div><div class="pipe-desc">本機 OCR 辨識</div></div>
        </div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-step">
          <div class="pipe-num">3</div>
          <div><div class="pipe-label">EPC 排程</div><div class="pipe-desc">出貨／植筋／進場／掛表</div></div>
        </div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-step">
          <div class="pipe-num">4</div>
          <div><div class="pipe-label">案件完成</div><div class="pipe-desc">回填 Airtable</div></div>
        </div>
      </div>

      <div class="grid">
        <div class="stat-card">
          <div class="stat-label">待處理 PDF</div>
          <div class="stat-value">1 份</div>
          <div class="stat-sub">來自本機資料夾</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">本週排程項目</div>
          <div class="stat-value">7 件</div>
          <div class="stat-sub">出貨/植筋/進場/掛表 合計</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">今日待辦</div>
          <div class="stat-value">2 件</div>
          <div class="stat-sub">EPC 排程模組</div>
        </div>
      </div>

      <div class="module-card" onclick="showView('pdf')">
        <div class="module-left">
          <div class="module-icon pdf">📄</div>
          <div>
            <div class="module-title">PDF 公文更名 <span class="module-tag tag-local">本機執行</span></div>
            <div class="module-desc">掃描待處理資料夾中的 PDF,自動辨識案號、日期與函文類型;內含 LINE 收件紀錄子頁籤。</div>
          </div>
        </div>
        <div class="chevron">›</div>
      </div>

      <div class="module-card" onclick="showView('epc')">
        <div class="module-left">
          <div class="module-icon epc">🚚</div>
          <div>
            <div class="module-title">EPC 出貨／進場排程 <span class="module-tag tag-cloud">雲端・手機可看</span></div>
            <div class="module-desc">日曆檢視出貨、植筋、進場、掛表四種日期安排;EPC 廠商可用手機登入查看自己的案件。</div>
          </div>
        </div>
        <div class="chevron">›</div>
      </div>
    </section>

    <!-- ============ PDF MODULE (with LINE收件紀錄 sub-tab) ============ -->
    <section class="view" id="view-pdf">
      <div class="topbar">
        <div>
          <div class="crumb">功能模組 / PDF 公文更名</div>
          <h1 class="page-title">PDF 公文更名</h1>
          <div class="page-sub">本機執行；LINE 收件紀錄併入此模組,方便對照來源檔案</div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab active" data-tab="pdf-rename" onclick="showPdfTab('pdf-rename')">公文更名</div>
        <div class="tab" data-tab="pdf-line" onclick="showPdfTab('pdf-line')">LINE 收件紀錄</div>
      </div>

      <div class="subview active" id="tab-pdf-rename">
        <div class="panel" style="text-align:center;padding:60px 20px;color:var(--text-muted);">
          <div style="font-size:32px;margin-bottom:10px;">📄</div>
          原本機 PDF 更名工具介面會嵌在這裡（沿用現有 V2.15 畫面）
        </div>
      </div>

      <div class="subview" id="tab-pdf-line">
        <div class="panel">
          <div class="panel-title">陽光機器人 · 最近收件</div>
          <table>
            <thead><tr><th>時間</th><th>LINE 群組</th><th>檔案</th><th>分派 PM</th><th>狀態</th></tr></thead>
            <tbody>
              <tr>
                <td>08/20 09:14</td><td>陽光伏特家&曙光能創</td><td>電費單_115年8月.pdf</td>
                <td><span class="pm-pill">PM-家豪</span></td><td><span class="pm-pill" style="color:var(--success);background:var(--success-soft);">已同步</span></td>
              </tr>
              <tr>
                <td>08/20 08:52</td><td>文件測試</td><td>竣工報告.pdf</td>
                <td><span class="pm-pill">PM-家豪 / PM-敏萱</span></td><td><span class="pm-pill" style="color:var(--success);background:var(--success-soft);">已同步</span></td>
              </tr>
              <tr>
                <td>08/19 17:03</td><td>三創</td><td>併聯掛表申請.pdf</td>
                <td><span class="pm-pill">PM-家豪</span></td><td><span class="pm-pill" style="color:var(--success);background:var(--success-soft);">已同步</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ============ EPC MODULE — CALENDAR ============ -->
    <section class="view" id="view-epc">
      <div class="topbar">
        <div>
          <div class="crumb">功能模組 / EPC 出貨／進場排程</div>
          <h1 class="page-title">EPC 出貨／進場排程</h1>
          <div class="page-sub">依廠商線檢視所有案件的關鍵日期,新增排程自動查 Google Sheet,儲存後回填 Airtable</div>
        </div>
      </div>

      <div class="tabs">
        <div class="tab active" data-tab="epc-week" onclick="showEpcTab('epc-week')">近一週安排</div>
        <div class="tab" data-tab="epc-calendar" onclick="showEpcTab('epc-calendar')">排程日曆</div>
        <div class="tab" data-tab="epc-pending" onclick="showEpcTab('epc-pending')">待安排出貨&植筋</div>
        <div class="tab" data-tab="epc-entry" onclick="showEpcTab('epc-entry')">案件進場安排</div>
        <div class="tab" data-tab="epc-meter" onclick="showEpcTab('epc-meter')">掛表安排</div>
        <div class="tab" data-tab="epc-issue" onclick="showEpcTab('epc-issue')">異常案件</div>
        <div class="tab" data-tab="epc-archive" onclick="showEpcTab('epc-archive')">歷史紀錄</div>
      </div>

      <!-- 近一週安排 -->
      <div class="subview active" id="tab-epc-week">
        <div class="panel">
          <div class="panel-title" id="weekRangeTitle">近一週安排</div>
          <div id="weekRows">
            <div class="login-note">載入中…</div>
          </div>
          <div class="login-note">
            🔗 這裡只顯示未來 7 天內的所有排程項目,跨廠商彙整,方便快速掌握近期要出貨/進場的案件,不用逐日翻日曆。
          </div>
        </div>
      </div>

      <!-- 待安排出貨&植筋 -->
      <div class="subview" id="tab-epc-pending">
        <div class="panel">
          <div class="panel-title">
            待安排出貨&植筋
            <span class="module-tag tag-cloud" style="margin-left:6px;" id="pendingCountTag">共 0 筆</span>
            <span id="pendingUpdatedAt" style="margin-left:8px;font-size:11px;color:var(--text-muted);font-weight:400;"></span>
            <button class="btn btn-ghost notes-trigger-btn" id="manualRefreshBtn" onclick="triggerManualRefresh()">🔄 手動更新</button>
            <button class="btn btn-ghost notes-trigger-btn" onclick="openNotesModal()">📝 註記清單</button>
            <button class="btn btn-ghost notes-trigger-btn" onclick="openMaterialModal()">📦 未使用料件</button>
            <button class="btn btn-ghost notes-trigger-btn" onclick="openNotifyModal()">📋 產出通知訊息</button>
          </div>

          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="pendingSearchInput" placeholder="搜尋案號或別名…" oninput="renderPendingTable()" style="max-width:260px;">
          </div>

          <table>
            <thead>
              <tr>
                <th class="sortable-th" onclick="sortPendingBy('case')">案號／別名 <span id="pendingSortIcon_case">↕</span></th>
                <th class="filter-th" onclick="toggleVendorDropdown(event)">
                  廠商<span id="vendorFilterLabel"></span> ▾
                  <div class="vendor-dropdown" id="vendorDropdown">
                    <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectPendingVendor(event,'all')">全部廠商</div>
                    <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectPendingVendor(event,'三創')">三創</div>
                    <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectPendingVendor(event,'尚展')">尚展</div>
                    <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectPendingVendor(event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectPendingVendor(event,'光鼎')">光鼎</div>
                  </div>
                </th>
                <th>案場地址</th>
                <th class="sortable-th" onclick="sortPendingBy('agree_date')">觸發依據 <span id="pendingSortIcon_agree_date">↕</span></th>
                <th class="sortable-th" onclick="sortPendingBy('module')">模組 <span id="pendingSortIcon_module">↕</span></th>
                <th class="sortable-th" onclick="sortPendingBy('inverter')">逆變器 <span id="pendingSortIcon_inverter">↕</span></th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody id="pendingRows"></tbody>
          </table>
          <div class="login-note" id="pendingLoginNote">
            🔗 資料每天 00:00／06:00／12:00／18:00 自動整批更新一次(伺服器背景排程),平常開啟頁面是直接讀取這份快取,不會每次都重新查 Airtable。點「排定日期」寫入成功後,會立刻觸發一次重新整理,清單會馬上反映最新狀態。標示「⚠ 尚未填寫規格」的案件仍會列在清單中提醒你安排出貨,只是模組/逆變器資訊還沒填。點欄位標題（案號／別名、觸發依據、模組、逆變器）可切換排序,輸入框可用案號、別名、模組、逆變器內容篩選,點廠商 chip 可篩選特定廠商。點「🪛」植筋按鈕可以安排植筋日期,或勾選「跟進場一起」;植筋日期一旦過了當天,隔天會自動視為完成,不用手動標記。
          </div>
        </div>
      </div>

      <!-- 案件進場安排 -->
      <div class="subview" id="tab-epc-entry">
        <div class="panel">
          <div class="panel-title">
            案件進場安排
          </div>
          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="entryFilterInput" placeholder="搜尋案號、地址、模組、逆變器…" oninput="tableSearchInput('entry')" style="max-width:280px;">
          </div>
          <table>
            <thead><tr>
              <th class="sortable-th" onclick="sortTableBy('entry','case')">案號 <span id="entrySortIcon_case">↕</span></th>
              <th class="filter-th" onclick="toggleTableVendorDropdown('entry',event)">
                廠商<span id="entryVendorFilterLabel"></span> ▾
                <div class="vendor-dropdown" id="entryVendorDropdown">
                  <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectTableVendor('entry',event,'all')">全部廠商</div>
                  <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectTableVendor('entry',event,'三創')">三創</div>
                  <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectTableVendor('entry',event,'尚展')">尚展</div>
                  <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectTableVendor('entry',event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectTableVendor('entry',event,'光鼎')">光鼎</div>
                </div>
              </th>
              <th>案場地址</th>
              <th class="sortable-th" colspan="2" onclick="sortTableBy('entry','module')">模組／逆變器 <span id="entrySortIcon_module">↕</span></th>
              <th>時程安排</th>
              <th>狀態</th>
              <th>操作</th>
            </tr></thead>
            <tbody id="entryRows">
              <tr>
                <td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 案件在「待安排出貨&植筋」完成排定出貨時間後,會自動移入這裡等待安排進場日期;進場日期排定後,狀態會變成「已安排」,案件仍會留在這裡,直到你按下「完工&掛表」一次填好完工日期跟預計掛表日期,案件就會直接移入「掛表安排」（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）。點「案號」「模組／逆變器」欄位標題可排序,點「廠商」可篩選特定廠商,輸入框可用案號、地址、模組、逆變器內容搜尋。
          </div>
        </div>
      </div>

      <!-- 掛表安排 -->
      <div class="subview" id="tab-epc-meter">
        <div class="panel">
          <div class="panel-title">
            掛表安排
          </div>
          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="meterFilterInput" placeholder="搜尋案號、地址、模組、逆變器…" oninput="tableSearchInput('meter')" style="max-width:280px;">
          </div>
          <table>
            <thead><tr>
              <th class="sortable-th" onclick="sortTableBy('meter','case')">案號 <span id="meterSortIcon_case">↕</span></th>
              <th class="filter-th" onclick="toggleTableVendorDropdown('meter',event)">
                廠商<span id="meterVendorFilterLabel"></span> ▾
                <div class="vendor-dropdown" id="meterVendorDropdown">
                  <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectTableVendor('meter',event,'all')">全部廠商</div>
                  <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectTableVendor('meter',event,'三創')">三創</div>
                  <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectTableVendor('meter',event,'尚展')">尚展</div>
                  <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectTableVendor('meter',event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectTableVendor('meter',event,'光鼎')">光鼎</div>
                </div>
              </th>
              <th>案場地址</th>
              <th class="sortable-th" onclick="sortTableBy('meter','module')">模組／逆變器 <span id="meterSortIcon_module">↕</span></th>
              <th>預計掛表日期</th>
              <th>操作</th>
            </tr></thead>
            <tbody id="meterRows">
              <tr>
                <td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 這裡列出已完工且已排定預計掛表日期的案件（在「案件進場安排」按「完工&掛表」後會直接出現在這裡）。點預計日期可以修正；按「完成掛表」會跳出確認,寫入後案件會移入「歷史紀錄」。點「案號」「模組／逆變器」欄位標題可排序,點「廠商」可篩選特定廠商,輸入框可用案號、地址、模組、逆變器內容搜尋。
          </div>
        </div>
      </div>

      <!-- 異常案件（已完工但目前卡住無法安排/完成掛表） -->
      <div class="subview" id="tab-epc-issue">
        <div class="panel">
          <div class="panel-title">
            異常案件
            <button class="btn btn-ghost notes-trigger-btn" onclick="openWithdrawnModal()">🚫 撤案清單 <span class="module-tag tag-cloud" style="margin-left:4px;" id="withdrawnCountTag">共 0 筆</span></button>
          </div>
          <div style="display:flex;gap:8px;margin-bottom:16px;">
            <input type="text" class="quick-mark-input" id="issueSearchInput" placeholder="輸入案號,例如：工程新竹6號" style="flex:1;" onkeydown="if(event.key==='Enter') addIssueByCaseNumber()">
            <button class="btn btn-primary" style="white-space:nowrap;" onclick="addIssueByCaseNumber()">＋ 加入異常案件</button>
          </div>
          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="issueFilterInput" placeholder="篩選案號或地址…" oninput="tableSearchInput('issue')" style="max-width:260px;">
          </div>
          <table>
            <thead><tr>
              <th class="sortable-th" onclick="sortTableBy('issue','case')">案號 <span id="issueSortIcon_case">↕</span></th>
              <th class="filter-th" onclick="toggleTableVendorDropdown('issue',event)">
                廠商<span id="issueVendorFilterLabel"></span> ▾
                <div class="vendor-dropdown" id="issueVendorDropdown">
                  <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectTableVendor('issue',event,'all')">全部廠商</div>
                  <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectTableVendor('issue',event,'三創')">三創</div>
                  <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectTableVendor('issue',event,'尚展')">尚展</div>
                  <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectTableVendor('issue',event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectTableVendor('issue',event,'光鼎')">光鼎</div>
                </div>
              </th>
              <th>案場地址</th>
              <th>目前階段</th>
              <th>異常狀況</th>
              <th>待取得函文</th>
              <th>記錄日期</th>
              <th>操作</th>
            </tr></thead>
            <tbody id="issueRows">
              <tr>
                <td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 這份清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。在上方輸入案號即可加入；按「已排除異常」會移出此清單,案件依原本階段繼續正常顯示在對應頁面;按「撤案」會移到「撤案清單」（點上方按鈕查看）。「待取得函文」是選填功能,標記異常時可以順便選案件是卡在等哪份函文（免雜／細部協商／台電購售契約）,系統會即時查 Airtable「進度管理」表目前的實際進度;一旦偵測到函文已取得,案件會自動排除異常、回到「待安排出貨&植筋」清單,「觸發依據」欄位也會自動改顯示這份函文的日期。點「案號」欄位標題可排序,點「廠商」可篩選特定廠商,下方搜尋框可用案號、地址內容篩選。
          </div>
        </div>
      </div>

      <!-- 歷史紀錄（最終封存，掛表已完成） -->
      <div class="subview" id="tab-epc-archive">
        <div class="panel">
          <div class="panel-title">
            歷史紀錄
          </div>
          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="archiveFilterInput" placeholder="搜尋案號、地址、模組、逆變器…" oninput="tableSearchInput('archive')" style="max-width:280px;">
          </div>
          <table>
            <thead><tr>
              <th class="sortable-th" onclick="sortTableBy('archive','case')">案號 <span id="archiveSortIcon_case">↕</span></th>
              <th class="filter-th" onclick="toggleTableVendorDropdown('archive',event)">
                廠商<span id="archiveVendorFilterLabel"></span> ▾
                <div class="vendor-dropdown" id="archiveVendorDropdown">
                  <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectTableVendor('archive',event,'all')">全部廠商</div>
                  <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectTableVendor('archive',event,'三創')">三創</div>
                  <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectTableVendor('archive',event,'尚展')">尚展</div>
                  <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectTableVendor('archive',event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectTableVendor('archive',event,'光鼎')">光鼎</div>
                </div>
              </th>
              <th>案場地址</th>
              <th class="sortable-th" onclick="sortTableBy('archive','module')">模組／逆變器 <span id="archiveSortIcon_module">↕</span></th>
              <th>出貨時間</th>
              <th>進場時間</th>
              <th>掛表時間</th>
            </tr></thead>
            <tbody id="archiveRows">
              <tr>
                <td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 此清單也會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。案件在「掛表安排」實際排定掛表日期並成功寫入 Airtable 後,會移到這裡。點「案號」「模組／逆變器」欄位標題可排序,點「廠商」可篩選特定廠商,輸入框可用案號、地址、模組、逆變器內容搜尋。
          </div>
        </div>
      </div>

      <!-- 排定日期 modal -->
      <div class="modal-overlay" id="scheduleModalOverlay" onclick="if(event.target===this) closeScheduleModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">📦 排定出貨時間</div>
            <button class="modal-close" onclick="closeScheduleModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="scheduleCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="scheduleCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">模組出貨時間（寫入 Airtable「大料出貨時間」）</label>
            <input type="date" class="quick-mark-input" id="scheduleShipDate" style="margin-bottom:14px;">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">變流器出貨時間（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）</label>
            <input type="date" class="quick-mark-input" id="scheduleInverterDate" style="margin-bottom:18px;">
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmSchedule()">確認排定，移入案件進場安排</button>
          </div>
        </div>
      </div>

      <!-- 產出通知訊息 modal -->
      <div class="modal-overlay" id="notifyModalOverlay" onclick="if(event.target===this) closeNotifyModal()">
        <div class="modal-box" style="max-width:560px;">
          <div class="modal-header">
            <div class="modal-title">📋 出貨通知訊息</div>
            <button class="modal-close" onclick="closeNotifyModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="login-note" style="margin-top:0;margin-bottom:12px;">
              已整理「案件進場安排」裡所有案件的出貨資訊,複製後可直接貼到 Slack 通知採購。可設定模組出貨日期區間篩選,留空代表不篩選（顯示全部）。
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px;">
              <input type="date" class="quick-mark-input" id="notifyDateFrom" style="flex:1;" onchange="openNotifyModal()">
              <span style="color:var(--text-muted);font-size:13px;">至</span>
              <input type="date" class="quick-mark-input" id="notifyDateTo" style="flex:1;" onchange="openNotifyModal()">
              <button class="btn btn-ghost" style="white-space:nowrap;padding:9px 14px;" onclick="document.getElementById('notifyDateFrom').value='';document.getElementById('notifyDateTo').value='';openNotifyModal();">清除篩選</button>
            </div>
            <textarea id="notifyTextarea" readonly style="width:100%;min-height:260px;border:1px solid var(--border);border-radius:10px;padding:14px;font-size:12.5px;font-family:ui-monospace,monospace;line-height:1.7;color:var(--text);background:var(--surface-2);resize:vertical;"></textarea>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;margin-top:12px;" onclick="copyNotifyText()">📎 複製訊息</button>
          </div>
        </div>
      </div>

      <!-- 排定進場日期 modal -->
      <div class="modal-overlay" id="entryModalOverlay" onclick="if(event.target===this) closeEntryModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🚚 排定進場日期</div>
            <button class="modal-close" onclick="closeEntryModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="entryCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="entryCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">進場日期</label>
            <input type="date" class="quick-mark-input" id="entryDate" style="margin-bottom:18px;">
            <div style="border-top:1px solid var(--border);padding-top:14px;margin-bottom:14px;">
              <label style="font-size:12px;font-weight:700;display:block;margin-bottom:10px;">屋主聯絡資訊（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）</label>
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">聯絡人</label>
              <input type="text" class="quick-mark-input" id="entryContactName" style="margin-bottom:12px;" placeholder="例如：王先生">
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">聯絡電話</label>
              <input type="text" class="quick-mark-input" id="entryContactPhone" style="margin-bottom:12px;" placeholder="例如：0912-345-678">
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">備註</label>
              <textarea class="quick-mark-input" id="entryContactNote" rows="3" style="width:100%;font-family:inherit;resize:vertical;" placeholder="例如：平日不在家,建議約假日"></textarea>
            </div>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmEntry()">確認排定，同步到排程日曆</button>
          </div>
        </div>
      </div>

      <!-- 完工日期 modal（只記錄在本機，不寫回 Airtable） -->
      <div class="modal-overlay" id="completeMeterModalOverlay" onclick="if(event.target===this) closeCompleteMeterModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">✓ 完工&掛表</div>
            <button class="modal-close" onclick="closeCompleteMeterModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="completeMeterCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="completeMeterCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">完工日期</label>
            <input type="date" class="quick-mark-input" id="completeMeterCompletedDate" style="margin-bottom:14px;">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">預計掛表日期</label>
            <input type="date" class="quick-mark-input" id="completeMeterPlannedDate" style="margin-bottom:6px;">
            <div style="font-size:11.5px;color:var(--text-muted);margin-bottom:18px;">兩個日期會一起寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到;送出後案件會直接移入「掛表安排」。</div>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmCompleteMeter()">確認，移入掛表安排</button>
          </div>
        </div>
      </div>

      <!-- 預計掛表日期 modal（掛表安排頁修正日期用，寫回 Airtable「APP資料」表） -->
      <div class="modal-overlay" id="planMeterModalOverlay" onclick="if(event.target===this) closePlanMeterModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🔌 安排掛表日期</div>
            <button class="modal-close" onclick="closePlanMeterModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="planMeterCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="planMeterCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">預計掛表日期（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到)</label>
            <input type="date" class="quick-mark-input" id="planMeterDate" style="margin-bottom:18px;">
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmPlanMeter()">確認</button>
          </div>
        </div>
      </div>

      <!-- 完成掛表 modal（確認/調整日期後才寫回 Airtable「掛表」里程碑） -->
      <div class="modal-overlay" id="meterModalOverlay" onclick="if(event.target===this) closeMeterModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🔌 完成掛表</div>
            <button class="modal-close" onclick="closeMeterModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="meterCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="meterCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;" id="meterConfirmLabel">掛表日是否為之前預定的日期？如需改期,調整下方日期即可（將寫入 Airtable「掛表」里程碑）</label>
            <input type="date" class="quick-mark-input" id="meterConfirmDate" style="margin-bottom:18px;">
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmMeter()">確認完成掛表，寫入 Airtable</button>
          </div>
        </div>
      </div>

      <!-- 標記異常 modal（只記錄在本機，不寫回 Airtable） -->
      <div class="modal-overlay" id="issueModalOverlay" onclick="if(event.target===this) closeIssueModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">⚠ 標記異常</div>
            <button class="modal-close" onclick="closeIssueModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="issueCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="issueCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">異常狀況說明（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）</label>
            <textarea class="quick-mark-input" id="issueNote" rows="4" style="margin-bottom:18px;width:100%;font-family:inherit;resize:vertical;" placeholder="例如：屋主要求延後掛表、電力公司文件缺件…"></textarea>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">待取得函文再進場（選填,會即時查詢 Airtable「進度管理」表的實際進度）</label>
            <select class="quick-mark-input" id="issueWaitingDocType" style="margin-bottom:18px;">
              <option value="">不適用</option>
              <option value="免雜">免雜</option>
              <option value="細部協商">細部協商</option>
              <option value="台電購售契約">台電購售契約（台電契約）</option>
            </select>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmIssue()">確認標記</button>
          </div>
        </div>
      </div>

      <!-- 撤案 modal（只記錄在本機，不寫回 Airtable） -->
      <div class="modal-overlay" id="withdrawModalOverlay" onclick="if(event.target===this) closeWithdrawModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🚫 撤案</div>
            <button class="modal-close" onclick="closeWithdrawModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="withdrawCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="withdrawCaseAddr">—</div>
            </div>
            <div style="background:#FDF1F1;color:#C9383D;font-size:12.5px;padding:10px 12px;border-radius:10px;margin-bottom:14px;">
              確認撤案後,此案件會從「異常案件」清單移到下方「撤案清單」,不會再出現在待出貨/進場/完工等一般流程中。
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">撤案原因（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）</label>
            <textarea class="quick-mark-input" id="withdrawNote" rows="4" style="margin-bottom:18px;width:100%;font-family:inherit;resize:vertical;" placeholder="例如：屋主取消合作、案場條件不符…"></textarea>
            <button class="btn btn-danger" style="width:100%;justify-content:center;padding:11px;" onclick="confirmWithdraw()">確認撤案</button>
          </div>
        </div>
      </div>

      <!-- 屋主資訊 modal（只記錄在本機，不寫回 Airtable） -->
      <div class="modal-overlay" id="ownerInfoModalOverlay" onclick="if(event.target===this) closeOwnerInfoModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🏠 屋主資訊</div>
            <button class="modal-close" onclick="closeOwnerInfoModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="ownerInfoCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="ownerInfoCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">聯絡人</label>
            <input type="text" class="quick-mark-input" id="ownerInfoName" style="margin-bottom:12px;" placeholder="例如：王先生">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">聯絡電話</label>
            <input type="text" class="quick-mark-input" id="ownerInfoPhone" style="margin-bottom:12px;" placeholder="例如：0912-345-678">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">備註（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）</label>
            <textarea class="quick-mark-input" id="ownerInfoNote" rows="3" style="margin-bottom:18px;width:100%;font-family:inherit;resize:vertical;" placeholder="例如：平日不在家,建議約假日"></textarea>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmOwnerInfo()">儲存</button>
          </div>
        </div>
      </div>

      <!-- 植筋安排 modal -->
      <div class="modal-overlay" id="rebarModalOverlay" onclick="if(event.target===this) closeRebarModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">🪛 植筋安排</div>
            <button class="modal-close" onclick="closeRebarModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="rebarCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="rebarCaseAddr">—</div>
            </div>
            <label style="display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:16px;cursor:pointer;">
              <input type="checkbox" id="rebarWithEntry" onchange="toggleRebarWithEntry()">
              植筋跟進場一起，不用另外安排
            </label>
            <div id="rebarDateFields">
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">植筋日期</label>
              <input type="date" class="quick-mark-input" id="rebarPlannedDate" style="margin-bottom:6px;">
              <div style="font-size:11.5px;color:var(--text-muted);margin-bottom:18px;">植筋通常一天內完成,過了這天的隔天會自動視為已完成,不用另外標記。</div>
            </div>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmRebar()">儲存</button>
          </div>
        </div>
      </div>

      <!-- 撤案清單 modal -->
      <div class="modal-overlay" id="withdrawnModalOverlay" onclick="if(event.target===this) closeWithdrawnModal()">
        <div class="modal-box" style="max-width:900px;">
          <div class="modal-header">
            <div class="modal-title">🚫 撤案清單</div>
            <button class="modal-close" onclick="closeWithdrawnModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="pending-toolbar">
              <input type="text" class="quick-mark-input" id="withdrawnFilterInput" placeholder="篩選案號或地址…" oninput="tableSearchInput('withdrawn')" style="max-width:260px;">
            </div>
            <table>
              <thead><tr>
                <th class="sortable-th" onclick="sortTableBy('withdrawn','case')">案號 <span id="withdrawnSortIcon_case">↕</span></th>
                <th class="filter-th" onclick="toggleTableVendorDropdown('withdrawn',event)">
                  廠商<span id="withdrawnVendorFilterLabel"></span> ▾
                  <div class="vendor-dropdown" id="withdrawnVendorDropdown">
                    <div class="vendor-dropdown-item active" data-vendor="all" onclick="selectTableVendor('withdrawn',event,'all')">全部廠商</div>
                    <div class="vendor-dropdown-item" data-vendor="三創" onclick="selectTableVendor('withdrawn',event,'三創')">三創</div>
                    <div class="vendor-dropdown-item" data-vendor="尚展" onclick="selectTableVendor('withdrawn',event,'尚展')">尚展</div>
                    <div class="vendor-dropdown-item" data-vendor="曙光" onclick="selectTableVendor('withdrawn',event,'曙光')">曙光</div>
                  <div class="vendor-dropdown-item" data-vendor="光鼎" onclick="selectTableVendor('withdrawn',event,'光鼎')">光鼎</div>
                  </div>
                </th>
                <th>案場地址</th>
                <th>撤案原因</th>
                <th>撤案日期</th>
                <th>操作</th>
              </tr></thead>
              <tbody id="withdrawnRows">
                <tr>
                  <td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有撤案案件</td>
                </tr>
              </tbody>
            </table>
            <div class="login-note">
              🔗 這份清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。在「異常案件」按下「撤案」的案件會移到這裡；按「取消撤案」可以移回「異常案件」清單。
            </div>
          </div>
        </div>
      </div>


      <!-- 註記清單 modal (triggered from 待安排出貨案件 button) -->
      <div class="modal-overlay" id="notesModalOverlay" onclick="if(event.target===this) closeNotesModal()">
        <div class="modal-box">
          <div class="modal-header">
            <div class="modal-title">📝 註記清單</div>
            <button class="modal-close" onclick="closeNotesModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="panel" style="margin-bottom:16px;">
              <div class="panel-title">
                併聯取得時備貨
                <span class="module-tag" style="background:var(--epc-soft);color:var(--epc);margin-left:6px;">併聯審查一到就提早進待安排</span>
              </div>
              <div class="note-add-row note-add-row-wide">
                <input type="text" class="quick-mark-input" id="earlyNoteInput" placeholder="輸入案號或案場別名,例如：潤特桃園80號">
                <input type="text" class="quick-mark-input" id="earlyNoteReasonInput" placeholder="原因,例如：特殊規格模組需提早備貨">
                <button class="btn btn-primary" onclick="addEarlyNote()">＋ 加入名單</button>
              </div>
              <table style="margin-top:14px;">
                <thead><tr><th>案號／案場</th><th>原因</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="earlyNoteRows">
                  <tr>
                    <td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有名單</td>
                  </tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 名單中的案件,一旦 Airtable 的「併聯審查」欄位填入日期,就會自動進入「待安排出貨&植筋」並標示特殊規格,不用等同意備案。此清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。
              </div>
            </div>

            <div class="panel">
              <div class="panel-title">其他狀況備住</div>
              <div class="note-add-row note-add-row-wide">
                <input type="text" class="quick-mark-input" id="parkedCaseInput" placeholder="輸入案號或案場別名">
                <input type="text" class="quick-mark-input" id="parkedNoteInput" placeholder="備住的狀況/注意事項,例如：屋主要求延後進場">
                <button class="btn btn-primary" onclick="addParkedNote()">＋ 加入備住</button>
              </div>
              <table style="margin-top:14px;">
                <thead><tr><th>案號／案場</th><th>備住內容</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="parkedNoteRows">
                  <tr>
                    <td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有備住項目</td>
                  </tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 這裡先記錄還用不到的注意事項;等該案件的「同意備案」填入日期、進入待安排出貨清單時,備住的內容會一併顯示出來提醒你。此清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 未使用料件 modal -->
      <div class="modal-overlay" id="materialModalOverlay" onclick="if(event.target===this) closeMaterialModal()">
        <div class="modal-box">
          <div class="modal-header">
            <div class="modal-title">📦 未使用料件</div>
            <div style="display:flex;align-items:center;gap:10px;">
              <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openMaterialUseListModal()">🔧 料件使用清單</button>
              <button class="modal-close" onclick="closeMaterialModal()">✕</button>
            </div>
          </div>
          <div class="modal-body">
            <div class="panel">
              <div class="note-add-row note-add-row-wide" style="align-items:flex-start;">
                <div style="display:flex;flex-direction:column;gap:2px;width:190px;flex:0 0 auto;">
                  <input type="text" class="quick-mark-input" id="materialCaseInput" style="flex:none;width:100%;" placeholder="案號或案場（可留空）" onblur="autofillMaterialFromCase()">
                  <span id="materialCaseHint" style="font-size:10.5px;color:var(--m-rebar);min-height:14px;"></span>
                </div>
                <textarea class="quick-mark-input" id="materialContentInput" rows="3" style="flex:1;font-family:inherit;resize:vertical;" placeholder="料件內容,例如：CPSPV6000ETLA ×2、未使用退回"></textarea>
                <div style="display:flex;flex-direction:column;gap:2px;width:150px;flex:0 0 auto;">
                  <input type="date" class="quick-mark-input" id="materialShipDateInput" style="flex:none;width:100%;">
                  <span style="font-size:10.5px;color:var(--text-muted);">出貨日期（填案號後自動帶入,可自行修改）</span>
                </div>
                <button class="btn btn-primary" onclick="addMaterialNote()">＋ 加入清單</button>
              </div>
              <table style="margin-top:14px;">
                <thead><tr><th>案號／案場</th><th>廠商</th><th>料件內容</th><th>出貨日期</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="materialRows">
                  <tr>
                    <td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有未使用料件</td>
                  </tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 這裡記錄目前尚未使用、可以留到下次案場使用的料件。此清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。填案號後如果比對到系統裡現有的案件,會自動帶入模組/逆變器內容、出貨日期,並顯示廠商；找不到對應案件的話,案號可以留空或自己輸入,料件內容也自己填寫就好。在「異常案件」按下「撤案」時,如果該案已經出貨,系統會另外跳出提示,問你要不要把料件自動加進這裡。點「編輯」可以修正案號、料件內容,或補填/修改出貨日期。點「使用」可以把這筆料件登記成用在其他案場,會一併記錄到「料件使用清單」。
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 未使用料件 編輯 modal -->
      <div class="modal-overlay" id="materialEditModalOverlay" onclick="if(event.target===this) closeMaterialEditModal()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">✎ 編輯未使用料件</div>
            <button class="modal-close" onclick="closeMaterialEditModal()">✕</button>
          </div>
          <div class="modal-body">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">案號／案場</label>
            <input type="text" class="quick-mark-input" id="materialEditCase" style="margin-bottom:14px;">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">料件內容</label>
            <textarea class="quick-mark-input" id="materialEditContent" rows="3" style="margin-bottom:14px;width:100%;font-family:inherit;resize:vertical;"></textarea>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">出貨日期</label>
            <input type="date" class="quick-mark-input" id="materialEditShipDate" style="margin-bottom:6px;">
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:18px;">如果原本沒有紀錄,這裡會是空白,可以自行補填；清空後儲存會變回「無出貨日期」。</div>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmMaterialEdit()">儲存</button>
          </div>
        </div>
      </div>

      <!-- 料件使用 modal -->
      <div class="modal-overlay" id="materialUseModalOverlay" onclick="if(event.target===this) closeMaterialUseModal()">
        <div class="modal-box" style="max-width:460px;">
          <div class="modal-header">
            <div class="modal-title">🔧 料件使用</div>
            <button class="modal-close" onclick="closeMaterialUseModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;background:var(--surface-2);border-radius:10px;padding:10px 12px;">
              <div style="font-size:11px;color:var(--text-muted);margin-bottom:2px;">原案號／案場</div>
              <div style="font-weight:700;font-size:13.5px;" id="materialUseSourceCase">—</div>
              <div style="font-size:11px;color:var(--text-muted);margin-top:8px;margin-bottom:2px;">原料件內容</div>
              <div style="font-size:12.5px;white-space:pre-wrap;" id="materialUseSourceContent">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">使用於案號／案場</label>
            <input type="text" class="quick-mark-input" id="materialUseTargetCase" style="margin-bottom:14px;" placeholder="例如：工程桃園20號">
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">使用內容說明（可修改,例如只用了其中 1 台）</label>
            <textarea class="quick-mark-input" id="materialUseContent" rows="3" style="margin-bottom:14px;width:100%;font-family:inherit;resize:vertical;"></textarea>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">使用日期</label>
            <input type="date" class="quick-mark-input" id="materialUseDate" style="margin-bottom:14px;">
            <label style="display:flex;align-items:center;gap:8px;font-size:12.5px;margin-bottom:18px;cursor:pointer;">
              <input type="checkbox" id="materialUseRemoveOriginal" checked>
              從「未使用料件」清單移除這筆（全部用完了才勾；只用掉一部分的話取消勾選,自己去清單裡把內容改成剩餘數量）
            </label>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmMaterialUse()">確認登記使用</button>
          </div>
        </div>
      </div>

      <!-- 料件使用清單 modal -->
      <div class="modal-overlay" id="materialUseListModalOverlay" onclick="if(event.target===this) closeMaterialUseListModal()">
        <div class="modal-box">
          <div class="modal-header">
            <div class="modal-title">🔧 料件使用清單</div>
            <button class="modal-close" onclick="closeMaterialUseListModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="panel">
              <table>
                <thead><tr><th>使用於案號／案場</th><th>使用內容</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="materialUseRows">
                  <tr>
                    <td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有料件使用紀錄</td>
                  </tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 這裡記錄從「未使用料件」清單挪去別的案場用掉的料件,在「未使用料件」清單點「使用」就會自動加進這裡。此清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 撤案後詢問是否加入未使用料件 modal -->
      <div class="modal-overlay" id="withdrawMaterialPromptOverlay" onclick="if(event.target===this) closeWithdrawMaterialPrompt()">
        <div class="modal-box" style="max-width:440px;">
          <div class="modal-header">
            <div class="modal-title">📦 加入未使用料件？</div>
            <button class="modal-close" onclick="closeWithdrawMaterialPrompt()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="withdrawMaterialCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">這筆案件已經出貨,撤案後這些料件可能會用不到,要不要先記到「未使用料件」清單？</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">料件內容（可修改後再加入）</label>
            <textarea class="quick-mark-input" id="withdrawMaterialContent" rows="3" style="margin-bottom:18px;width:100%;font-family:inherit;resize:vertical;"></textarea>
            <div style="display:flex;gap:10px;">
              <button class="btn btn-ghost" style="flex:1;justify-content:center;padding:11px;" onclick="closeWithdrawMaterialPrompt()">不用，謝謝</button>
              <button class="btn btn-primary" style="flex:1;justify-content:center;padding:11px;" onclick="confirmWithdrawMaterial()">加入未使用料件清單</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 排程日曆 -->
      <div class="subview" id="tab-epc-calendar">
      <div class="panel">
        <div class="panel-title" style="margin-bottom:4px;">排程日曆</div>
        <div class="vendor-filter">
          <div class="vendor-chip active" data-vendor="all" onclick="filterVendor('all')">全部廠商線</div>
          <div class="vendor-chip vendor-sc" data-vendor="sc" onclick="filterVendor('sc')">三創</div>
          <div class="vendor-chip vendor-sz" data-vendor="sz" onclick="filterVendor('sz')">尚展</div>
          <div class="vendor-chip vendor-sg" data-vendor="sg" onclick="filterVendor('sg')">曙光</div>
          <div class="vendor-chip vendor-gd" data-vendor="gd" onclick="filterVendor('gd')">光鼎</div>
        </div>
        <div class="cal-header">
          <div class="cal-nav">
            <button class="icon-btn" onclick="changeCalMonth(-1)">‹</button>
            <div class="cal-month" id="calMonthLabel">2026年8月</div>
            <button class="icon-btn" onclick="changeCalMonth(1)">›</button>
          </div>
          <div class="legend">
            <div class="legend-item"><span class="dot dot-ship"></span>模組/變流器出貨</div>
            <div class="legend-item"><span class="dot dot-rebar"></span>植筋</div>
            <div class="legend-item"><span class="dot dot-enter"></span>進場</div>
            <div class="legend-item"><span class="dot dot-meter"></span>掛表</div>
          </div>
        </div>

        <div class="cal-grid" id="calGrid">
          <div class="cal-dow">一</div><div class="cal-dow">二</div><div class="cal-dow">三</div>
          <div class="cal-dow">四</div><div class="cal-dow">五</div><div class="cal-dow">六</div><div class="cal-dow">日</div>
        </div>
      </div>

      <div class="epc-bottom">
        <div class="panel">
          <div class="panel-title" id="dayDetailTitle">選擇日期查看當日排程</div>
          <div id="dayDetailRows">
            <div class="login-note">點選上方日曆中的任一天,就會在這裡列出當天所有的出貨/進場/掛表排程。</div>
          </div>
          <div class="login-note">
            🔗 這裡的日期直接讀取「案件進場安排」「掛表安排」「歷史紀錄」裡的即時資料,不需要另外輸入;掛表日期若尚未實際完成掛表,會顯示為「預計」。
          </div>
        </div>
      </div>
      </div>
    </section>

  </main>

<script>
const API_BASE = 'https://epc-backend-4aj2.onrender.com';

const VENDOR_CLASS = {'三創':'vendor-sc','尚展':'vendor-sz','曙光':'vendor-sg','光鼎':'vendor-gd'};

let PENDING_CASES = [];
let ENTRY_CASES = [];
let COMPLETED_CASES = [];
let pendingSortKey = 'case';
let pendingSortAsc = true;
let pendingVendorFilter = 'all';

function todayStr(){
  const d = new Date();
  return d.getFullYear() + '-' + (d.getMonth()+1).toString().padStart(2,'0') + '-' + d.getDate().toString().padStart(2,'0');
}

// ---- 完工＆掛表 modal ----
let completeMeterTargetRecordId = null;
function openCompleteMeterModal(recordId){
  completeMeterTargetRecordId = recordId;
  const cs = getCaseStatus(recordId);
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  if(!found && !cs){ showToast('找不到這筆案件的資料，請重新整理頁面再試一次'); return; }
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const addr = (found && found.address) || '';
  const vendor = (found && found.vendor) || '';
  document.getElementById('completeMeterCaseTitle').textContent = caseNo;
  document.getElementById('completeMeterCaseAddr').textContent = addr + '　' + vendor;
  document.getElementById('completeMeterCompletedDate').value = (cs && cs.completed_date) || todayStr();
  document.getElementById('completeMeterPlannedDate').value = (cs && cs.meter_planned_date) || todayStr();
  document.getElementById('completeMeterModalOverlay').classList.add('show');
}
function closeCompleteMeterModal(){
  document.getElementById('completeMeterModalOverlay').classList.remove('show');
}
async function confirmCompleteMeter(){
  const completedVal = document.getElementById('completeMeterCompletedDate').value;
  const plannedVal = document.getElementById('completeMeterPlannedDate').value;
  if(!completedVal){ showToast('請選擇完工日期'); return; }
  if(!plannedVal){ showToast('請選擇預計掛表日期'); return; }
  const recordId = completeMeterTargetRecordId;
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  const cs = getCaseStatus(recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const btn = document.querySelector('#completeMeterModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(recordId, caseNo, {completed_date: completedVal, meter_planned_date: plannedVal});
    closeCompleteMeterModal();
    renderEntryTable();
    renderMeterTable();
    showToast('已記錄完工＆掛表日期，移入「掛表安排」');
    showEpcTab('epc-meter');
    loadAppData();  // 背景重新對齊一次，確保跟其他人同步
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 預計掛表日期 modal（已完工頁用，寫入 APP資料 表，跨裝置共用；還沒真的寫入 Airtable「掛表」里程碑）----
let planMeterTargetRecordId = null;
function openPlanMeterModal(recordId){
  planMeterTargetRecordId = recordId;
  const cs = getCaseStatus(recordId);
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  if(!found && !cs){ showToast('找不到這筆案件的資料，請重新整理頁面再試一次'); return; }
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const addr = (found && found.address) || '';
  const vendor = (found && found.vendor) || '';
  document.getElementById('planMeterCaseTitle').textContent = caseNo;
  document.getElementById('planMeterCaseAddr').textContent = addr + '　' + vendor;
  document.getElementById('planMeterDate').value = (cs && cs.meter_planned_date) || todayStr();
  document.getElementById('planMeterModalOverlay').classList.add('show');
}
function closePlanMeterModal(){
  document.getElementById('planMeterModalOverlay').classList.remove('show');
}
async function confirmPlanMeter(){
  const dateVal = document.getElementById('planMeterDate').value;
  if(!dateVal){ showToast('請選擇預計掛表日期'); return; }
  const recordId = planMeterTargetRecordId;
  const cs = getCaseStatus(recordId);
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const btn = document.querySelector('#planMeterModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(recordId, caseNo, {meter_planned_date: dateVal});
    closePlanMeterModal();
    renderMeterTable();
    showToast('已排定掛表日期，移入「掛表安排」');
    showEpcTab('epc-meter');
    loadAppData();
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 完成掛表 modal（確認/調整日期後，寫回 Airtable「掛表」里程碑，並同步標記 APP資料 表）----
let meterTargetRecordId = null;
function openMeterModal(recordId){
  meterTargetRecordId = recordId;
  const cs = getCaseStatus(recordId);
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  if(!found && !cs){ showToast('找不到這筆案件的資料，請重新整理頁面再試一次'); return; }
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const addr = (found && found.address) || '';
  const vendor = (found && found.vendor) || '';
  document.getElementById('meterCaseTitle').textContent = caseNo;
  document.getElementById('meterCaseAddr').textContent = addr + '　' + vendor;
  const planned = cs && cs.meter_planned_date;
  document.getElementById('meterConfirmLabel').textContent = planned
    ? `掛表日是否為 ${fmtDate(planned)}？如需改期,調整下方日期即可（將寫入 Airtable「掛表」里程碑）`
    : '掛表日期（將寫入 Airtable「掛表」里程碑）';
  document.getElementById('meterConfirmDate').value = planned || todayStr();
  document.getElementById('meterModalOverlay').classList.add('show');
}
function closeMeterModal(){
  document.getElementById('meterModalOverlay').classList.remove('show');
}
async function confirmMeter(){
  const dateVal = document.getElementById('meterConfirmDate').value;
  if(!dateVal){ showToast('請選擇掛表日期'); return; }
  const recordId = meterTargetRecordId;
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  const btn = document.querySelector('#meterModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '寫入中…';
  btn.disabled = true;
  try{
    const res = await fetch(API_BASE + '/api/hang-meter-date', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        case_record_id: recordId,
        milestone_record_id: (found && found.meter_milestone_record_id) || undefined,
        hang_meter_date: dateVal,
      }),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    closeMeterModal();
    showToast('已寫入 Airtable「掛表」，移入歷史紀錄');
    await Promise.all([loadCompletedCases(), loadAppData()]);
  }catch(err){
    showToast('寫入失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 標記異常 modal（寫入 APP資料 表，跨裝置共用）----
// 可以標記任何階段的案件（待安排出貨／案件進場安排／已完工／掛表安排），
// 所以顯示資料要依序在 PENDING_CASES / ENTRY_CASES / COMPLETED_CASES 裡找。
function findCaseAnywhere(recordId){
  return PENDING_CASES.find(c => c.record_id === recordId)
    || ENTRY_CASES.find(c => c.record_id === recordId)
    || COMPLETED_CASES.find(c => c.record_id === recordId)
    || null;
}
// 判斷案件「目前」卡在哪個階段——每次都即時判斷，不是存死的，
// 這樣即使案件在被標記異常之後又繼續往下走了幾步，階段顯示還是準的。
function deriveStageLabel(recordId){
  const cs = getCaseStatus(recordId);
  if(cs && cs.meter_confirmed) return '歷史紀錄（掛表已完成）';
  if(cs && cs.meter_planned_date) return '掛表安排';
  if(cs && cs.completed_date) return '已完工';
  if(COMPLETED_CASES.find(c => c.record_id === recordId)) return '案件進場安排（已安排）';
  if(ENTRY_CASES.find(c => c.record_id === recordId)) return '案件進場安排（待進場）';
  if(PENDING_CASES.find(c => c.record_id === recordId)) return '待安排出貨&植筋';
  return '找不到目前階段（可能已離開排程池）';
}

let issueTargetRecordId = null;
function openIssueModal(recordId){
  issueTargetRecordId = recordId;
  const cs = getCaseStatus(recordId);
  const found = findCaseAnywhere(recordId);
  if(!found && !cs){ showToast('找不到這筆案件的資料，請重新整理頁面再試一次'); return; }
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const addr = (found && found.address) || '';
  const vendor = (found && found.vendor) || '';
  document.getElementById('issueCaseTitle').textContent = caseNo;
  document.getElementById('issueCaseAddr').textContent = addr + '　' + vendor;
  document.getElementById('issueNote').value = (cs && cs.issue_note) || '';
  document.getElementById('issueWaitingDocType').value = (cs && cs.waiting_doc_type) || '';
  document.getElementById('issueModalOverlay').classList.add('show');
}
function closeIssueModal(){
  document.getElementById('issueModalOverlay').classList.remove('show');
}
async function confirmIssue(){
  const note = document.getElementById('issueNote').value.trim();
  const waitingDocType = document.getElementById('issueWaitingDocType').value;
  if(!note){ showToast('請填寫異常狀況說明'); return; }
  const recordId = issueTargetRecordId;
  const cs = getCaseStatus(recordId);
  const found = findCaseAnywhere(recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const btn = document.querySelector('#issueModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(recordId, caseNo, {issue_note: note, issue_date: todayStr(), waiting_doc_type: waitingDocType || null});
    delete docStatusCache[recordId]; // 函文種類可能被改過，清掉快取讓它重新查一次
    closeIssueModal();
    renderPendingTable();
    renderEntryTable();
    renderMeterTable();
    renderIssueTable();
    renderWithdrawnTable();
    showToast('已標記異常，移入「異常案件」');
    showEpcTab('epc-issue');
    loadAppData();
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}
async function resolveIssue(recordId){
  const cs = getCaseStatus(recordId);
  const caseNo = (cs && cs.case_no) || '';
  try{
    await saveCaseStatusField(recordId, caseNo, {issue_note: null, issue_date: null});
    delete docStatusCache[recordId];
    renderPendingTable();
    renderEntryTable();
    renderMeterTable();
    renderIssueTable();
    renderWithdrawnTable();
    showToast('已排除異常');
  }catch(err){
    showToast('操作失敗：' + err.message);
    console.error(err);
  }
}

let withdrawTargetRecordId = null;
function openWithdrawModal(recordId){
  withdrawTargetRecordId = recordId;
  const cs = getCaseStatus(recordId);
  const found = findCaseAnywhere(recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '（找不到案號）';
  const addr = (found && found.address) || '（找不到即時資料，可能已離開排程池）';
  const vendor = (found && found.vendor) || '';
  document.getElementById('withdrawCaseTitle').textContent = caseNo;
  document.getElementById('withdrawCaseAddr').textContent = addr + (vendor ? '　' + vendor : '');
  document.getElementById('withdrawNote').value = (cs && cs.withdrawn_note) || '';
  document.getElementById('withdrawModalOverlay').classList.add('show');
}
function closeWithdrawModal(){
  document.getElementById('withdrawModalOverlay').classList.remove('show');
}
async function confirmWithdraw(){
  const note = document.getElementById('withdrawNote').value.trim();
  if(!note){ showToast('請填寫撤案原因'); return; }
  const recordId = withdrawTargetRecordId;
  const cs = getCaseStatus(recordId);
  const found = findCaseAnywhere(recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const btn = document.querySelector('#withdrawModalOverlay .btn-danger');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(recordId, caseNo, {withdrawn_note: note, withdrawn_date: todayStr()});
    closeWithdrawModal();
    renderIssueTable();
    renderWithdrawnTable();
    showToast('已撤案，移入「撤案清單」');
    maybePromptWithdrawMaterial(recordId, found);
  }catch(err){
    showToast('撤案失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}
async function unwithdrawCase(recordId){
  const cs = getCaseStatus(recordId);
  const caseNo = (cs && cs.case_no) || '';
  try{
    await saveCaseStatusField(recordId, caseNo, {withdrawn_note: null, withdrawn_date: null});
    renderIssueTable();
    renderWithdrawnTable();
    showToast('已取消撤案，移回「異常案件」');
  }catch(err){
    showToast('操作失敗：' + err.message);
    console.error(err);
  }
}

let ownerInfoTargetRecordId = null;
let ownerInfoTargetCaseNo = '';
function openOwnerInfoModal(recordId){
  ownerInfoTargetRecordId = recordId;
  const found = findCaseAnywhere(recordId);
  ownerInfoTargetCaseNo = (found && found.case) || '';
  const cs = getCaseStatus(recordId);
  document.getElementById('ownerInfoCaseTitle').textContent = ownerInfoTargetCaseNo || '—';
  document.getElementById('ownerInfoCaseAddr').textContent = found ? (found.address + '　' + found.vendor) : '';
  document.getElementById('ownerInfoName').value = (cs && cs.owner_contact_name) || '';
  document.getElementById('ownerInfoPhone').value = (cs && cs.owner_contact_phone) || '';
  document.getElementById('ownerInfoNote').value = (cs && cs.owner_contact_note) || '';
  document.getElementById('ownerInfoModalOverlay').classList.add('show');
}
function closeOwnerInfoModal(){
  document.getElementById('ownerInfoModalOverlay').classList.remove('show');
}
async function confirmOwnerInfo(){
  const name = document.getElementById('ownerInfoName').value.trim();
  const phone = document.getElementById('ownerInfoPhone').value.trim();
  const note = document.getElementById('ownerInfoNote').value.trim();
  const btn = document.querySelector('#ownerInfoModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(ownerInfoTargetRecordId, ownerInfoTargetCaseNo, {
      owner_contact_name: name || null,
      owner_contact_phone: phone || null,
      owner_contact_note: note || null,
    });
    closeOwnerInfoModal();
    renderEntryTable();
    showToast('已更新屋主資訊');
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 植筋安排 ----
// ---- 植筋 ----
// 判斷植筋是否「已完成」：不用另外標記完成日期，只要植筋日期已經過了（不含當天），
// 隔天起就自動視為完成。植筋跟進場一起（rebar_with_entry）的案件不適用這個判斷。
function isRebarDone(cs){
  if(!cs || !cs.rebar_planned_date || cs.rebar_with_entry) return false;
  return cs.rebar_planned_date < todayStr();
}
function renderRebarBadge(recordId){
  const cs = getCaseStatus(recordId);
  const btnStyle = 'padding:6px 12px;font-size:12px;white-space:nowrap;';
  if(cs && cs.rebar_with_entry){
    return `<div style="margin-top:6px;"><button class="btn btn-ghost" style="${btnStyle}background:var(--m-rebar-soft);color:var(--m-rebar);border-color:transparent;" onclick="openRebarModal('${recordId}')">🪛 植筋與進場一起</button></div>`;
  }
  if(cs && cs.rebar_planned_date){
    const done = isRebarDone(cs);
    const bg = done ? 'var(--success-soft)' : 'var(--m-rebar-soft)';
    const fg = done ? 'var(--success)' : 'var(--m-rebar)';
    return `<div style="margin-top:6px;"><button class="btn btn-ghost" style="${btnStyle}background:${bg};color:${fg};border-color:transparent;" onclick="openRebarModal('${recordId}')">🪛 植筋 ${fmtDate(cs.rebar_planned_date)}</button></div>`;
  }
  return `<div style="margin-top:6px;"><button class="btn btn-ghost" style="${btnStyle}" onclick="openRebarModal('${recordId}')">🪛 安排植筋</button></div>`;
}
let rebarTargetRecordId = null;
let rebarTargetCaseNo = '';
function openRebarModal(recordId){
  rebarTargetRecordId = recordId;
  const found = findCaseAnywhere(recordId);
  rebarTargetCaseNo = (found && found.case) || '';
  const cs = getCaseStatus(recordId);
  document.getElementById('rebarCaseTitle').textContent = rebarTargetCaseNo || '—';
  document.getElementById('rebarCaseAddr').textContent = found ? (found.address + '　' + found.vendor) : '';
  const withEntry = !!(cs && cs.rebar_with_entry);
  document.getElementById('rebarWithEntry').checked = withEntry;
  document.getElementById('rebarPlannedDate').value = (cs && cs.rebar_planned_date) || '';
  document.getElementById('rebarDateFields').style.display = withEntry ? 'none' : 'block';
  document.getElementById('rebarModalOverlay').classList.add('show');
}
function closeRebarModal(){
  document.getElementById('rebarModalOverlay').classList.remove('show');
}
function toggleRebarWithEntry(){
  const checked = document.getElementById('rebarWithEntry').checked;
  document.getElementById('rebarDateFields').style.display = checked ? 'none' : 'block';
}
async function confirmRebar(){
  const withEntry = document.getElementById('rebarWithEntry').checked;
  const planned = document.getElementById('rebarPlannedDate').value;
  const btn = document.querySelector('#rebarModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(rebarTargetRecordId, rebarTargetCaseNo, {
      rebar_with_entry: withEntry,
      rebar_planned_date: withEntry ? null : (planned || null),
    });
    closeRebarModal();
    renderPendingTable();
    renderEntryTable();
    renderCalendar();
    renderWeekList();
    showToast('已更新植筋安排');
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

function openWithdrawnModal(){
  renderWithdrawnTable();
  document.getElementById('withdrawnModalOverlay').classList.add('show');
}
function closeWithdrawnModal(){
  document.getElementById('withdrawnModalOverlay').classList.remove('show');
}
function renderWithdrawnTable(){
  const tbody = document.getElementById('withdrawnRows');
  const countTag = document.getElementById('withdrawnCountTag');
  if(!tbody) return;
  const ids = Object.keys(APP_CASE_STATUS).filter(id => APP_CASE_STATUS[id].withdrawn_note);
  if(countTag) countTag.textContent = '共 ' + ids.length + ' 筆';
  if(ids.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有撤案案件</td></tr>';
    return;
  }
  const baseItems = ids.map(id => {
    const cs = APP_CASE_STATUS[id];
    const found = findCaseAnywhere(id);
    return {
      id,
      case: (found && found.case) || cs.case_no || '（找不到案號）',
      alias: (found && found.alias) || '',
      vendor: (found && found.vendor) || '',
      vendorClass: (found && (VENDOR_CLASS[found.vendor] || 'vendor-other')) || 'vendor-other',
      address: (found && found.address) || '（找不到即時資料，可能已離開排程池）',
      withdrawn_note: cs.withdrawn_note,
      withdrawn_date: cs.withdrawn_date,
    };
  });
  let items = applyTableFilterSort('withdrawn', baseItems);
  if(!TABLE_STATE.withdrawn.sortKey){
    items.sort((a,b) => (b.withdrawn_date||'').localeCompare(a.withdrawn_date||''));
  }
  if(items.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = items.map(it => {
    return `
    <tr>
      <td><div class="case-id">${it.case}</div><div class="case-alias">${it.alias||''}</div></td>
      <td>${it.vendor ? `<span class="vendor-pill ${it.vendorClass}">${it.vendor}</span>` : ''}</td>
      <td>${it.address}</td>
      <td style="max-width:260px;white-space:pre-wrap;">${it.withdrawn_note}</td>
      <td>${fmtDate(it.withdrawn_date)}</td>
      <td>
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="unwithdrawCase('${it.id}')">取消撤案</button>
      </td>
    </tr>
  `;
  }).join('');
}
function addIssueByCaseNumber(){
  const input = document.getElementById('issueSearchInput');
  const q = input.value.trim();
  if(!q){ showToast('請輸入案號'); return; }
  const found = PENDING_CASES.find(c => c.case === q)
    || ENTRY_CASES.find(c => c.case === q)
    || COMPLETED_CASES.find(c => c.case === q);
  if(!found){ showToast('找不到案號「' + q + '」，請確認輸入是否正確（區分全形/半形、完整案號）'); return; }
  input.value = '';
  openIssueModal(found.record_id);
}

function fmtDate(iso){
  // "YYYY-MM-DD" -> "MM/DD"
  if(!iso) return '';
  const p = iso.split('-');
  return p.length === 3 ? p[1]+'/'+p[2] : iso;
}
// 型號規格文字裡「型號 ×片數」之間如果被空白斷開換行,把最後那個空白換成不換行空白,
// 避免像「H6QT」跟「×26」被拆到不同行。
function glueCount(str){
  if(!str) return str;
  return str.replace(/[ \t]+(×[\d.]+)/g, '\u00A0$1');
}

// ===================================================================
// APP資料（已完工／掛表安排／異常案件／變流器日期／註記清單）
// 2026-08-25 改成寫回 Airtable 的 APP資料 表，讓不同電腦/同事都能同步看到，
// 取代原本只存在瀏覽器本機的 localStorage 版本。
// ===================================================================
let APP_CASE_STATUS = {};  // { [case_record_id]: {app_record_id, completed_date, meter_planned_date, meter_confirmed, issue_note, issue_date, inverter_ship_date} }
let APP_NOTES = [];        // [{app_record_id, type, case_text, content, date}]
let APP_ARCHIVED = [];     // 已封存（掛表已確認）案件，含完整顯示快照

async function loadAppData(includeArchived){
  if(includeArchived === undefined) includeArchived = true;
  try{
    const url = API_BASE + '/api/app-data' + (includeArchived ? '' : '?include_archived=false');
    const res = await fetch(url, {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    APP_CASE_STATUS = {};
    (data.case_status || []).forEach(cs => { APP_CASE_STATUS[cs.case_record_id] = cs; });
    APP_NOTES = data.notes || [];
    if(data.archived !== undefined){
      // 快速輪詢帶 include_archived=false 時後端不會回傳這個欄位，
      // 這種情況下沿用目前記憶體裡既有的 APP_ARCHIVED，不要清空。
      APP_ARCHIVED = (data.archived || []).map(a => ({...a, vendorClass: VENDOR_CLASS[a.vendor] || 'vendor-other'}));
    }
    renderPendingTable();
    renderEntryTable();
    renderMeterTable();
    renderIssueTable();
    renderWithdrawnTable();
    renderArchiveTable();
    renderEarlyNoteList();
    renderParkedNoteList();
    renderMaterialList();
    renderMaterialUseList();
    renderCalendar();
    renderWeekList();
  }catch(err){
    console.error(err);
  }
}
function getCaseStatus(recordId){
  return APP_CASE_STATUS[recordId] || null;
}
async function saveCaseStatusField(recordId, caseNo, fieldsPatch){
  const res = await fetch(API_BASE + '/api/app-data/case-status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({case_record_id: recordId, case_no: caseNo, fields: fieldsPatch}),
  });
  if(!res.ok){
    const err = await res.json().catch(()=>({}));
    throw new Error(err.error || ('HTTP ' + res.status));
  }
  const existing = APP_CASE_STATUS[recordId] || {case_record_id: recordId, case_no: caseNo};
  APP_CASE_STATUS[recordId] = {...existing, ...fieldsPatch};  // 樂觀更新，畫面先反應，之後 loadAppData() 會再對齊一次
}
function getInverterDate(recordId){
  const cs = getCaseStatus(recordId);
  return (cs && cs.inverter_ship_date) || '';
}

function fmtUpdatedAt(iso){
  if(!iso) return '尚未完成初次整理,請稍候片刻再重新整理頁面';
  const d = new Date(iso);
  const p2 = n => n.toString().padStart(2,'0');
  return `${p2(d.getMonth()+1)}/${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}`;
}

async function loadPendingCases(){
  const tbody = document.getElementById('pendingRows');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td></tr>';
  try{
    const res = await fetch(API_BASE + '/api/pending-cases', {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    PENDING_CASES = (data.cases || []).map(c => ({
      ...c,
      vendorClass: VENDOR_CLASS[c.vendor] || 'vendor-other',
      agree: fmtDate(c.agree_date),
    }));
    renderPendingTable();
    renderIssueTable();
    renderWithdrawnTable();
    if(data.updated_at) lastKnownUpdatedAt = data.updated_at;
    const label = document.getElementById('pendingUpdatedAt');
    if(label){
      if(data.last_error){
        label.textContent = '⚠ 上次背景更新失敗：' + data.last_error;
        label.style.color = '#D64545';
      } else if(data.updated_at){
        label.textContent = (data.refreshing ? '更新中… 顯示的是 ' : '資料更新於 ') + fmtUpdatedAt(data.updated_at);
        label.style.color = '';
      } else {
        label.textContent = data.refreshing ? '首次整理進行中,請稍候…' : '資料尚未準備好,請點「手動更新」';
        label.style.color = '';
      }
    }
  }catch(err){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">連不上後端服務,請確認 Render 服務是否正常運作</td></tr>';
    console.error(err);
  }
}

async function loadEntryCases(){
  const tbody = document.getElementById('entryRows');
  tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td></tr>';
  try{
    const res = await fetch(API_BASE + '/api/entry-cases', {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    ENTRY_CASES = (data.cases || []).map(c => ({
      ...c,
      vendorClass: VENDOR_CLASS[c.vendor] || 'vendor-other',
    }));
    renderEntryTable();
    renderIssueTable();
    renderWithdrawnTable();
    renderCalendar();
    renderWeekList();
  }catch(err){
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">連不上後端服務,請確認 Render 服務是否正常運作</td></tr>';
    console.error(err);
  }
}

async function loadCompletedCases(){
  try{
    const res = await fetch(API_BASE + '/api/completed-cases', {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    COMPLETED_CASES = (data.cases || []).map(c => ({
      ...c,
      vendorClass: VENDOR_CLASS[c.vendor] || 'vendor-other',
    }));
    renderEntryTable();
    renderMeterTable();
    renderIssueTable();
    renderWithdrawnTable();
    renderCalendar();
    renderWeekList();
  }catch(err){
    console.error(err);
  }
}

let lastKnownUpdatedAt = null;
function pollForCacheUpdate(){
  return new Promise((resolve) => {
    let tries = 0;
    const maxTries = 24;
    const poll = setInterval(async () => {
      tries++;
      try{
        const res = await fetch(API_BASE + '/api/pending-cases', {cache: 'no-store'});
        const data = await res.json();
        if(data.updated_at && data.updated_at !== lastKnownUpdatedAt){
          clearInterval(poll);
          lastKnownUpdatedAt = data.updated_at;
          await Promise.all([loadPendingCases(), loadEntryCases(), loadCompletedCases(), loadAppData()]);
          resolve(true);
        } else if(tries >= maxTries){
          clearInterval(poll);
          resolve(false);
        }
      }catch(err){
        // 忽略單次輪詢失敗，繼續等下一次
      }
    }, 5000);
  });
}
async function triggerManualRefresh(){
  const btn = document.getElementById('manualRefreshBtn');
  btn.disabled = true;
  btn.textContent = '🔄 更新中…';
  showToast('已在背景開始重新整理,通常 30-60 秒完成,完成後畫面會自動更新');

  try{
    await fetch(API_BASE + '/api/refresh', {method: 'POST'});
  }catch(err){
    showToast('觸發更新失敗：' + err.message);
    btn.disabled = false;
    btn.textContent = '🔄 手動更新';
    return;
  }

  const ok = await pollForCacheUpdate();
  showToast(ok ? '已更新完成' : '更新時間較長,請稍後再檢查一次');
  btn.disabled = false;
  btn.textContent = '🔄 手動更新';
}

function renderPendingTable(){
  const q = document.getElementById('pendingSearchInput').value.trim();
  let rows = PENDING_CASES.filter(r => {
    if(pendingVendorFilter !== 'all' && r.vendor !== pendingVendorFilter) return false;
    if(q && !((r.case||'').includes(q) || (r.alias||'').includes(q)
              || (r.module||'').includes(q) || (r.inverter||'').includes(q))) return false;
    const cs = APP_CASE_STATUS[r.record_id];
    if(cs && cs.issue_note) return false; // 已標記異常的案件不再顯示在「待安排出貨案件」
    return true;
  });
  rows.sort((a,b) => {
    let av, bv;
    if(pendingSortKey === 'agree_date'){ av = a.agree_date || ''; bv = b.agree_date || ''; }
    else { av = a[pendingSortKey] || ''; bv = b[pendingSortKey] || ''; }
    const cmp = ('' + av).localeCompare('' + bv, 'zh-Hant');
    return pendingSortAsc ? cmp : -cmp;
  });

  document.getElementById('pendingCountTag').textContent = '共 ' + rows.length + ' 筆';

  const tbody = document.getElementById('pendingRows');
  if(rows.length === 0){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const hasSpec = !!r.module;
    const specCell = hasSpec
      ? `<td>${r.module}</td><td>${r.inverter || ''}</td>`
      : `<td colspan="2"><span class="warn-pill">⚠ 尚未填寫規格</span></td>`;
    const cs = getCaseStatus(r.record_id);
    const triggerPill = (cs && cs.waiting_doc_type && cs.waiting_doc_date)
      ? `<span class="pm-pill" style="background:var(--m-rebar-soft);color:var(--m-rebar);">${cs.waiting_doc_type} ${fmtDate(cs.waiting_doc_date)}</span>`
      : `<span class="pm-pill" style="background:var(--success-soft);color:var(--success);">同意備案 ${r.agree}</span>`;
    return `
      <tr data-record-id="${r.record_id}" data-ship-milestone-id="${r.ship_milestone_record_id || ''}" data-case="${r.case}" data-alias="${r.alias||''}" data-vendor="${r.vendor}" data-vendorclass="${r.vendorClass}" data-addr="${r.address}" data-module="${hasSpec ? r.module : '尚未填寫規格'}" data-inverter="${hasSpec ? (r.inverter||'') : ''}">
        <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div></td>
        <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
        <td>${r.address}</td>
        <td>${triggerPill}</td>
        ${specCell}
        <td><button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openScheduleModal(this)">📅 排定日期</button>${renderRebarBadge(r.record_id)}</td>
      </tr>
    `;
  }).join('');
}

function renderEntryTable(){
  const tbody = document.getElementById('entryRows');
  const waitingRows = ENTRY_CASES
    .filter(r => !(getCaseStatus(r.record_id) && getCaseStatus(r.record_id).issue_note))
    .map(r => ({...r, _status: 'waiting'}));
  const doneRows = COMPLETED_CASES
    .filter(r => {
      const cs = getCaseStatus(r.record_id);
      return !(cs && cs.meter_planned_date) && !(cs && cs.issue_note);
    })
    .map(r => ({...r, _status: 'scheduled'}));
  const allRows = [...waitingRows, ...doneRows];
  const rows = applyTableFilterSort('entry', allRows);

  if(allRows.length === 0){
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有案件——在「待安排出貨&植筋」排定出貨日期後,案件會自動出現在這裡</td></tr>';
    return;
  }
  if(rows.length === 0){
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const invDate = getInverterDate(r.record_id);
    const chips = [`<span class="chip chip-ship">模組 ${fmtDate(r.ship_date)}</span>`];
    if(invDate) chips.push(`<span class="chip chip-ship">變流器 ${fmtDate(invDate)}</span>`);
    if(r._status === 'scheduled' && r.entry_date) chips.push(`<span class="chip chip-enter">進場 ${fmtDate(r.entry_date)}</span>`);
    const scheduleChips = `<div style="display:flex;flex-direction:column;gap:3px;align-items:flex-start;">${chips.join('')}</div>`;
    let statusPill;
    if(r._status === 'waiting'){
      statusPill = `<span class="pm-pill">待進場</span>`;
    } else {
      const cs = getCaseStatus(r.record_id);
      const hasContact = cs && (cs.owner_contact_name || cs.owner_contact_phone || cs.owner_contact_note);
      statusPill = `<span class="pm-pill" style="background:var(--success-soft);color:var(--success);">已安排</span>
        <div style="margin-top:5px;">
          <span class="pm-pill" style="cursor:pointer;background:var(--surface-2);color:var(--text);" onclick="openOwnerInfoModal('${r.record_id}')">🏠 屋主資訊</span>
        </div>
        ${hasContact ? '' : '<div style="margin-top:3px;font-size:11px;color:var(--text-muted);">（尚未填寫）</div>'}`;
    }
    const actions = r._status === 'waiting'
      ? `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openScheduleModal(this,'reschedule')">重新安排出貨日期</button>
         <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;margin-left:6px;" onclick="openEntryModal(this)">排定進場日期</button>${renderRebarBadge(r.record_id)}`
      : `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openEntryModal(this,'reschedule')">重新安排進場日期</button>
         <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;margin-left:6px;" onclick="openCompleteMeterModal('${r.record_id}')">✓ 完工&掛表</button>`;
    return `
    <tr data-record-id="${r.record_id}" data-ship-milestone-id="${r.ship_milestone_record_id || ''}" data-entry-milestone-id="${r.entry_milestone_record_id || ''}" data-case="${r.case}" data-alias="${r.alias||''}" data-vendor="${r.vendor}" data-vendorclass="${r.vendorClass}" data-addr="${r.address}" data-module="${r.module||''}" data-inverter="${r.inverter||''}" data-shipdate="${fmtDate(r.ship_date)}" data-shipdatefull="${r.ship_date||''}" data-entrydatefull="${r.entry_date||''}">
      <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div></td>
      <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
      <td>${r.address}</td>
      <td colspan="2">${r.module ? `<div>${glueCount(r.module)}</div>${r.inverter ? `<div style="margin-top:2px;">${glueCount(r.inverter)}</div>` : ''}` : '<span style="color:var(--text-muted);font-size:12px;">尚未填寫規格</span>'}</td>
      <td>${scheduleChips}</td>
      <td>${statusPill}</td>
      <td>${actions}</td>
    </tr>
  `;
  }).join('');
}

// ---- 已完工（尚未排掛表）----
// ---- 掛表安排（已排定預計掛表日期，等待確認寫回 Airtable）----
function renderMeterTable(){
  const tbody = document.getElementById('meterRows');
  if(!tbody) return;
  const baseRows = COMPLETED_CASES.filter(r => {
    const cs = getCaseStatus(r.record_id);
    return cs && cs.meter_planned_date && !cs.meter_confirmed && !cs.issue_note;
  });
  if(baseRows.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有等待完成掛表的案件——在「案件進場安排」按下「完工&掛表」後,案件會出現在這裡</td></tr>';
    return;
  }
  let rows = applyTableFilterSort('meter', baseRows);
  if(!TABLE_STATE.meter.sortKey){
    rows.sort((a,b) => {
      const ca = getCaseStatus(a.record_id), cb = getCaseStatus(b.record_id);
      return (ca.meter_planned_date||'').localeCompare(cb.meter_planned_date||'');
    });
  }
  if(rows.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const cs = getCaseStatus(r.record_id);
    return `
    <tr>
      <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div></td>
      <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
      <td>${r.address}</td>
      <td>${r.module ? `<div>${glueCount(r.module)}</div>${r.inverter ? `<div style="margin-top:2px;">${glueCount(r.inverter)}</div>` : ''}` : '<span style="color:var(--text-muted);font-size:12px;">尚未填寫規格</span>'}</td>
      <td><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="openPlanMeterModal('${r.record_id}')">${fmtDate(cs.meter_planned_date)}　✎</button></td>
      <td>
        <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;" onclick="openMeterModal('${r.record_id}')">完成掛表</button>
      </td>
    </tr>
  `;
  }).join('');
}

// ---- 異常案件 ----
function renderIssueTable(){
  const tbody = document.getElementById('issueRows');
  if(!tbody) return;
  const ids = Object.keys(APP_CASE_STATUS).filter(id => APP_CASE_STATUS[id].issue_note && !APP_CASE_STATUS[id].withdrawn_note);
  if(ids.length === 0){
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有異常案件</td></tr>';
    return;
  }
  const baseItems = ids.map(id => {
    const cs = APP_CASE_STATUS[id];
    const found = findCaseAnywhere(id);
    return {
      id,
      case: (found && found.case) || cs.case_no || '（找不到案號）',
      alias: (found && found.alias) || '',
      vendor: (found && found.vendor) || '',
      vendorClass: (found && (VENDOR_CLASS[found.vendor] || 'vendor-other')) || 'vendor-other',
      address: (found && found.address) || '（找不到即時資料，可能已離開排程池）',
      stage: deriveStageLabel(id),
      issue_note: cs.issue_note,
      issue_date: cs.issue_date,
      waiting_doc_type: cs.waiting_doc_type || '',
    };
  });
  let items = applyTableFilterSort('issue', baseItems);
  if(!TABLE_STATE.issue.sortKey){
    items.sort((a,b) => (b.issue_date||'').localeCompare(a.issue_date||''));
  }
  if(items.length === 0){
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = items.map(it => {
    return `
    <tr>
      <td><div class="case-id">${it.case}</div><div class="case-alias">${it.alias||''}</div></td>
      <td>${it.vendor ? `<span class="vendor-pill ${it.vendorClass}">${it.vendor}</span>` : ''}</td>
      <td>${it.address}</td>
      <td><span class="pm-pill">${it.stage}</span></td>
      <td style="max-width:260px;white-space:pre-wrap;">${it.issue_note}</td>
      <td>
        ${it.waiting_doc_type ? `
          <div style="font-size:11.5px;color:var(--text-muted);margin-bottom:2px;">${it.waiting_doc_type}</div>
          <div id="docStatus_${it.id}" style="font-size:12px;">${renderDocStatusHtml(docStatusCache[it.id])}</div>
          <button class="btn btn-ghost" style="padding:2px 8px;font-size:10.5px;margin-top:3px;" onclick="checkDocStatus('${it.id}','${it.waiting_doc_type}')">🔄 重新檢查</button>
        ` : '<span style="color:var(--text-muted);">—</span>'}
      </td>
      <td>${fmtDate(it.issue_date)}</td>
      <td>
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openIssueModal('${it.id}')">編輯</button>
        <div style="margin-top:6px;">
          <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;" onclick="resolveIssue('${it.id}')">已排除異常</button>
          <button class="btn btn-danger" style="padding:6px 12px;font-size:12px;margin-left:6px;" onclick="openWithdrawModal('${it.id}')">撤案</button>
        </div>
      </td>
    </tr>
  `;
  }).join('');
  // 只在「第一次看到這個案件」時才主動查一次 Airtable，之後重繪表格（包含每 6 秒一次的
  // 背景自動同步）都直接用快取結果顯示，不會每次都重新查詢。要看最新狀態就按「重新檢查」。
  items.forEach(it => {
    if(it.waiting_doc_type && !docStatusCache[it.id]) checkDocStatus(it.id, it.waiting_doc_type);
  });
}
let docStatusCache = {};
function renderDocStatusHtml(status){
  if(!status) return '查詢中…';
  if(status.completed) return `<span style="color:var(--success);font-weight:600;">✓ 已取得 ${fmtDate(status.actual_date)}</span>`;
  if(status.found_milestone === false) return `<span style="color:var(--m-rebar);">尚未取得函文</span>`;
  return `<span style="color:var(--m-rebar);">尚未取得</span>`;
}
async function checkDocStatus(recordId, docType){
  const el = document.getElementById('docStatus_' + recordId);
  if(el) el.innerHTML = '查詢中…';
  try{
    const res = await fetch(API_BASE + '/api/milestone-status?case_record_id=' + encodeURIComponent(recordId) + '&type=' + encodeURIComponent(docType), {cache: 'no-store'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    const data = await res.json();
    if(data.completed){
      // 已取得，自動排除異常，讓案件回到「待安排出貨&植筋」，並保留函文日期做為新的觸發依據
      delete docStatusCache[recordId];
      await autoResolveByDocument(recordId, docType, data.actual_date);
      return;
    }
    docStatusCache[recordId] = data;
    const elAfter = document.getElementById('docStatus_' + recordId);
    if(elAfter) elAfter.innerHTML = renderDocStatusHtml(data);
  }catch(err){
    const elErr = document.getElementById('docStatus_' + recordId);
    if(elErr) elErr.innerHTML = '<span style="color:var(--text-muted);">查詢失敗</span>';
    console.error(err);
  }
}
async function autoResolveByDocument(recordId, docType, actualDate){
  const cs = getCaseStatus(recordId);
  const caseNo = (cs && cs.case_no) || '';
  try{
    await saveCaseStatusField(recordId, caseNo, {
      issue_note: null,
      issue_date: null,
      waiting_doc_date: actualDate || todayStr(),
    });
    renderPendingTable();
    renderEntryTable();
    renderMeterTable();
    renderIssueTable();
    renderWithdrawnTable();
    showToast(`已取得「${docType}」，案件已自動移回「待安排出貨&植筋」`);
  }catch(err){
    showToast('自動排除異常失敗：' + err.message);
    console.error(err);
  }
}

// ---- 歷史紀錄（最終封存，掛表已完成）----
function renderArchiveTable(){
  const tbody = document.getElementById('archiveRows');
  if(!tbody) return;
  const baseRows = APP_ARCHIVED;
  if(baseRows.length === 0){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有已封存的案件——在「掛表安排」排定掛表日期後,案件會出現在這裡</td></tr>';
    return;
  }
  let sorted = applyTableFilterSort('archive', baseRows);
  if(!TABLE_STATE.archive.sortKey){
    sorted.sort((a,b) => (b.meter_date||'').localeCompare(a.meter_date||''));
  }
  if(sorted.length === 0){
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
    return;
  }
  tbody.innerHTML = sorted.map(r => {
    const invDate = getInverterDate(r.case_record_id);
    const shipText = fmtDate(r.ship_date) + (invDate ? `（變流器 ${fmtDate(invDate)}）` : '');
    return `
    <tr>
      <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div></td>
      <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
      <td>${r.address}</td>
      <td>${r.module ? `<div>${glueCount(r.module)}</div>${r.inverter ? `<div style="margin-top:2px;">${glueCount(r.inverter)}</div>` : ''}` : '<span style="color:var(--text-muted);font-size:12px;">尚未填寫規格</span>'}</td>
      <td>${shipText}</td>
      <td>${fmtDate(r.entry_date)}</td>
      <td>${fmtDate(r.meter_date)}</td>
    </tr>
  `;
  }).join('');
}

function sortPendingBy(key){
  if(pendingSortKey === key){
    pendingSortAsc = !pendingSortAsc;
  } else {
    pendingSortKey = key;
    pendingSortAsc = true;
  }
  ['case','agree_date','module','inverter'].forEach(k => {
    const icon = document.getElementById('pendingSortIcon_' + k);
    if(!icon) return;
    icon.textContent = (k === pendingSortKey) ? (pendingSortAsc ? '↑' : '↓') : '↕';
  });
  renderPendingTable();
}
function toggleVendorDropdown(e){
  e.stopPropagation();
  document.getElementById('vendorDropdown').classList.toggle('show');
}
function selectPendingVendor(e, v){
  e.stopPropagation();
  pendingVendorFilter = v;
  document.querySelectorAll('.vendor-dropdown-item').forEach(i => i.classList.remove('active'));
  document.querySelector(`.vendor-dropdown-item[data-vendor="${v}"]`).classList.add('active');
  document.getElementById('vendorFilterLabel').textContent = v === 'all' ? '' : '（' + v + '）';
  document.getElementById('vendorDropdown').classList.remove('show');
  renderPendingTable();
}
document.addEventListener('click', function(){
  const dd = document.getElementById('vendorDropdown');
  if(dd) dd.classList.remove('show');
});

// ---- 通用表格篩選／排序（案件進場安排／已完工／掛表安排／異常案件／歷史紀錄共用）----
const TABLE_STATE = {
  entry:   { sortKey: null, sortAsc: true, vendor: 'all', q: '' },
  meter:   { sortKey: null, sortAsc: true, vendor: 'all', q: '' },
  issue:   { sortKey: null, sortAsc: true, vendor: 'all', q: '' },
  archive: { sortKey: null, sortAsc: true, vendor: 'all', q: '' },
  withdrawn: { sortKey: null, sortAsc: true, vendor: 'all', q: '' },
};
const TABLE_SORT_FIELDS = {
  entry: ['case','module'],
  meter: ['case','module'],
  issue: ['case'],
  archive: ['case','module'],
  withdrawn: ['case'],
};
const TABLE_RENDER_FN = {
  entry: () => renderEntryTable(),
  meter: () => renderMeterTable(),
  issue: () => renderIssueTable(),
  archive: () => renderArchiveTable(),
  withdrawn: () => renderWithdrawnTable(),
};
function sortTableBy(tab, key){
  const st = TABLE_STATE[tab];
  if(st.sortKey === key){ st.sortAsc = !st.sortAsc; } else { st.sortKey = key; st.sortAsc = true; }
  (TABLE_SORT_FIELDS[tab] || []).forEach(k => {
    const icon = document.getElementById(tab + 'SortIcon_' + k);
    if(!icon) return;
    icon.textContent = (k === st.sortKey) ? (st.sortAsc ? '↑' : '↓') : '↕';
  });
  TABLE_RENDER_FN[tab]();
}
function toggleTableVendorDropdown(tab, e){
  e.stopPropagation();
  const dd = document.getElementById(tab + 'VendorDropdown');
  if(dd) dd.classList.toggle('show');
}
function selectTableVendor(tab, e, v){
  e.stopPropagation();
  TABLE_STATE[tab].vendor = v;
  const dd = document.getElementById(tab + 'VendorDropdown');
  if(dd){
    dd.querySelectorAll('.vendor-dropdown-item').forEach(i => i.classList.remove('active'));
    const item = dd.querySelector(`.vendor-dropdown-item[data-vendor="${v}"]`);
    if(item) item.classList.add('active');
    dd.classList.remove('show');
  }
  const label = document.getElementById(tab + 'VendorFilterLabel');
  if(label) label.textContent = v === 'all' ? '' : '（' + v + '）';
  TABLE_RENDER_FN[tab]();
}
function tableSearchInput(tab){
  const input = document.getElementById(tab + 'FilterInput');
  TABLE_STATE[tab].q = input ? input.value.trim() : '';
  TABLE_RENDER_FN[tab]();
}
function applyTableFilterSort(tab, rows){
  const st = TABLE_STATE[tab];
  let out = rows;
  if(st.vendor !== 'all') out = out.filter(r => r.vendor === st.vendor);
  if(st.q){
    const q = st.q;
    out = out.filter(r => (r.case||'').includes(q) || (r.address||'').includes(q)
                        || (r.module||'').includes(q) || (r.inverter||'').includes(q));
  }
  if(st.sortKey){
    out = [...out].sort((a,b) => {
      const av = '' + (a[st.sortKey] || '');
      const bv = '' + (b[st.sortKey] || '');
      const cmp = av.localeCompare(bv, 'zh-Hant');
      return st.sortAsc ? cmp : -cmp;
    });
  }
  return out;
}
document.addEventListener('click', function(){
  ['entry','meter','issue','archive','withdrawn'].forEach(tab => {
    const dd = document.getElementById(tab + 'VendorDropdown');
    if(dd) dd.classList.remove('show');
  });
});
document.addEventListener('DOMContentLoaded', function(){
  loadPendingCases();
  loadEntryCases();
  loadCompletedCases();
  loadAppData();
  startAutoSync();
});

// ---- 多人協作背景自動同步 ----
// 每 6 秒偷偷檢查一次是否有其他人更新過資料，有的話就悄悄重新抓取、重新畫面，
// 不用整頁重新整理，也不會打斷使用者正在填寫的表單（modal 是獨立元素，不受影響）。
// pending/entry/completed 這三份走「快取版本比對」（updated_at 沒變就不重抓，省流量）；
// APP資料裡「案件狀態／註記」這種輕量資料每輪都重抓；「歷史紀錄」因為每一筆都要額外
// 查 1-2 次 Airtable、案件一多會逼近 Airtable 每秒 5 次請求的限制，所以只每 5 輪
// （約 30 秒）才連同歷史紀錄一起做一次完整刷新。
let autoSyncTimer = null;
let autoSyncInFlight = false;
let autoSyncTick = 0;
const AUTO_SYNC_INTERVAL_MS = 6000;
const AUTO_SYNC_ARCHIVE_EVERY_N_TICKS = 5;
function startAutoSync(){
  if(autoSyncTimer) return;
  autoSyncTimer = setInterval(async () => {
    if(autoSyncInFlight) return; // 避免上一輪還沒跑完又疊一輪
    autoSyncInFlight = true;
    autoSyncTick++;
    try{
      const res = await fetch(API_BASE + '/api/pending-cases', {cache: 'no-store'});
      const data = await res.json();
      if(data.updated_at && data.updated_at !== lastKnownUpdatedAt){
        lastKnownUpdatedAt = data.updated_at;
        await Promise.all([loadPendingCases(), loadEntryCases(), loadCompletedCases()]);
      }
      const includeArchived = (autoSyncTick % AUTO_SYNC_ARCHIVE_EVERY_N_TICKS === 0);
      await loadAppData(includeArchived);
    }catch(err){
      // 忽略單次輪詢失敗，等下一輪繼續
    }finally{
      autoSyncInFlight = false;
    }
  }, AUTO_SYNC_INTERVAL_MS);
}

function showView(name){
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+name).classList.add('active');
  document.querySelectorAll('.nav-item[data-view]').forEach(n=>n.classList.remove('active'));
  document.querySelector('.nav-item[data-view="'+name+'"]').classList.add('active');
  document.querySelectorAll('.nav-sub-item').forEach(n=>n.classList.remove('active'));
}
function openNotifyModal(){
  const fromVal = document.getElementById('notifyDateFrom').value;
  const toVal = document.getElementById('notifyDateTo').value;
  let cases = ENTRY_CASES;
  if(fromVal) cases = cases.filter(r => r.ship_date && r.ship_date >= fromVal);
  if(toVal) cases = cases.filter(r => r.ship_date && r.ship_date <= toVal);

  let text;
  if(ENTRY_CASES.length === 0){
    text = '目前「案件進場安排」還沒有案件。';
  } else if(cases.length === 0){
    text = '這個日期區間內沒有符合條件的出貨案件。';
  } else {
    const rangeNote = (fromVal || toVal) ? `（出貨日期 ${fromVal ? fmtDate(fromVal) : '最早'} ～ ${toVal ? fmtDate(toVal) : '最晚'}）` : '';
    const lines = [`【EPC 模組／變流器出貨通知】共 ${cases.length} 件${rangeNote}`, ''];
    cases.forEach((r, i) => {
      const invDate = getInverterDate(r.record_id);
      lines.push(`${i+1}. ${r.case}（${r.vendor}）`);
      lines.push(`　模組出貨時間：${fmtDate(r.ship_date)}`);
      lines.push(`　變流器出貨時間：${invDate ? fmtDate(invDate) : '（未填寫）'}`);
      lines.push(`　地址：${r.address}`);
      lines.push(`　模組：${r.module || '（尚未填寫）'}`);
      lines.push(`　逆變器：${r.inverter || '（尚未填寫）'}`);
      lines.push('');
    });
    text = lines.join('\n');
  }
  document.getElementById('notifyTextarea').value = text;
  document.getElementById('notifyModalOverlay').classList.add('show');
}
function closeNotifyModal(){
  document.getElementById('notifyModalOverlay').classList.remove('show');
}
function copyNotifyText(){
  const ta = document.getElementById('notifyTextarea');
  ta.select();
  try{ document.execCommand('copy'); }catch(e){}
  const btn = event.target;
  const original = btn.textContent;
  btn.textContent = '✓ 已複製';
  setTimeout(()=>{ btn.textContent = original; }, 1500);
}
let toastTimer = null;
function showToast(msg){
  const t = document.getElementById('toastBanner');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>t.classList.remove('show'), 4000);
}
let scheduleTargetRow = null;
let scheduleMode = 'new';
function openScheduleModal(btn, mode){
  mode = mode || 'new';
  const row = btn.closest('tr');
  if(mode === 'new' && row.dataset.module === '尚未填寫規格'){
    showToast('這筆案件尚未填寫模組／變流器資訊，請先至 Airtable 輸入模組／變流器資訊後再排定出貨時間。');
    return;
  }
  scheduleTargetRow = row;
  scheduleMode = mode;
  document.getElementById('scheduleCaseTitle').textContent = row.dataset.case;
  document.getElementById('scheduleCaseAddr').textContent = row.dataset.addr + '　' + row.dataset.vendor;
  document.getElementById('scheduleShipDate').value = mode === 'reschedule' ? (row.dataset.shipdatefull || '') : '';
  document.getElementById('scheduleInverterDate').value = getInverterDate(row.dataset.recordId);
  document.getElementById('scheduleModalOverlay').classList.add('show');
}
function closeScheduleModal(){
  document.getElementById('scheduleModalOverlay').classList.remove('show');
}
async function confirmSchedule(){
  const shipDate = document.getElementById('scheduleShipDate').value;
  const inverterDate = document.getElementById('scheduleInverterDate').value;
  if(!shipDate){ showToast('請填寫模組出貨時間'); return; }

  const milestoneId = scheduleTargetRow.dataset.shipMilestoneId;
  const recordId = scheduleTargetRow.dataset.recordId;
  const btn = document.querySelector('#scheduleModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '寫入中…';
  btn.disabled = true;

  try{
    const res = await fetch(API_BASE + '/api/schedule', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({milestone_record_id: milestoneId || undefined, case_record_id: recordId, ship_date: shipDate}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    // 變流器出貨日期存進 APP資料 表（跨裝置共用），不影響 Airtable 官方的「大料出貨時間」欄位
    try{
      await saveCaseStatusField(recordId, scheduleTargetRow.dataset.case, {inverter_ship_date: inverterDate || null});
    }catch(e){ console.error('儲存變流器出貨日期失敗：', e); }
    closeScheduleModal();
    showToast('已寫入 Airtable「大料出貨時間」');
    // 先做一次立即刷新（可能還沒反映後端最新快取），並在背景繼續輪詢，
    // 等後端這次的 refresh_cache 真的跑完後自動再刷新一次，不用使用者手動整頁重新整理，
    // 也不強制切換分頁，維持使用者原本停留的頁面。
    await Promise.all([loadPendingCases(), loadEntryCases(), loadCompletedCases(), loadAppData()]);
    pollForCacheUpdate();
  }catch(err){
    showToast('寫入失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

let entryTargetRow = null;
function openEntryModal(btn, mode){
  mode = mode || 'new';
  const row = btn.closest('tr');
  entryTargetRow = row;
  document.getElementById('entryCaseTitle').textContent = row.dataset.case;
  document.getElementById('entryCaseAddr').textContent = row.dataset.addr + '　' + row.dataset.vendor;
  document.getElementById('entryDate').value = mode === 'reschedule' ? (row.dataset.entrydatefull || '') : '';
  const cs = getCaseStatus(row.dataset.recordId);
  document.getElementById('entryContactName').value = (cs && cs.owner_contact_name) || '';
  document.getElementById('entryContactPhone').value = (cs && cs.owner_contact_phone) || '';
  document.getElementById('entryContactNote').value = (cs && cs.owner_contact_note) || '';
  document.getElementById('entryModalOverlay').classList.add('show');
}
function closeEntryModal(){
  document.getElementById('entryModalOverlay').classList.remove('show');
}
async function confirmEntry(){
  const entryDate = document.getElementById('entryDate').value;
  if(!entryDate){ showToast('請填寫進場日期'); return; }

  const milestoneId = entryTargetRow.dataset.entryMilestoneId;
  const recordId = entryTargetRow.dataset.recordId;
  const caseNo = entryTargetRow.dataset.case;
  const contactName = document.getElementById('entryContactName').value.trim();
  const contactPhone = document.getElementById('entryContactPhone').value.trim();
  const contactNote = document.getElementById('entryContactNote').value.trim();
  const btn = document.querySelector('#entryModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '寫入中…';
  btn.disabled = true;

  try{
    const res = await fetch(API_BASE + '/api/entry-date', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({milestone_record_id: milestoneId || undefined, case_record_id: recordId, entry_date: entryDate}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    if(recordId){
      await saveCaseStatusField(recordId, caseNo, {
        owner_contact_name: contactName || null,
        owner_contact_phone: contactPhone || null,
        owner_contact_note: contactNote || null,
      });
    }
    closeEntryModal();
    showToast('已寫入 Airtable「進場屋主預約」，狀態變更為「已安排」');
    await Promise.all([loadEntryCases(), loadCompletedCases(), loadAppData()]);  // 這筆案件會從「待進場」變成「已安排」
  }catch(err){
    showToast('寫入失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

function openNotesModal(){
  renderEarlyNoteList();
  renderParkedNoteList();
  document.getElementById('notesModalOverlay').classList.add('show');
}
function closeNotesModal(){
  document.getElementById('notesModalOverlay').classList.remove('show');
}

// ---- 併聯取得時備貨 / 其他狀況備住 名單（寫入 APP資料 表，跨裝置共用）----
async function addEarlyNote(){
  const input = document.getElementById('earlyNoteInput');
  const reasonInput = document.getElementById('earlyNoteReasonInput');
  const name = input.value.trim();
  const reason = reasonInput.value.trim();
  if(!name){ showToast('請輸入案號或案場別名'); return; }
  if(!reason){ showToast('請填寫原因'); return; }
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: '併聯取得時備貨', case_text: name, content: reason}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    input.value = '';
    reasonInput.value = '';
    await loadAppData();
  }catch(err){
    showToast('新增失敗：' + err.message);
    console.error(err);
  }
}
async function deleteEarlyNote(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/app-data/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== appRecordId);
    renderEarlyNoteList();
  }catch(err){
    showToast('刪除失敗：' + err.message);
    console.error(err);
  }
}
function renderEarlyNoteList(){
  const tbody = document.getElementById('earlyNoteRows');
  if(!tbody) return;
  const list = APP_NOTES.filter(n => n.type === '併聯取得時備貨');
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有名單</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => `
    <tr>
      <td><div class="case-id">${n.case_text}</div></td>
      <td>${n.content}</td>
      <td>${fmtDate(n.date)}</td>
      <td><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="deleteEarlyNote('${n.app_record_id}')">刪除</button></td>
    </tr>
  `).join('');
}

async function addParkedNote(){
  const caseInput = document.getElementById('parkedCaseInput');
  const noteInput = document.getElementById('parkedNoteInput');
  const name = caseInput.value.trim();
  const note = noteInput.value.trim();
  if(!name){ showToast('請輸入案號或案場別名'); return; }
  if(!note){ showToast('請填寫備住的狀況/注意事項'); return; }
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: '其他狀況備住', case_text: name, content: note}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    caseInput.value = '';
    noteInput.value = '';
    await loadAppData();
  }catch(err){
    showToast('新增失敗：' + err.message);
    console.error(err);
  }
}
async function deleteParkedNote(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/app-data/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== appRecordId);
    renderParkedNoteList();
  }catch(err){
    showToast('刪除失敗：' + err.message);
    console.error(err);
  }
}
function renderParkedNoteList(){
  const tbody = document.getElementById('parkedNoteRows');
  if(!tbody) return;
  const list = APP_NOTES.filter(n => n.type === '其他狀況備住');
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有備住項目</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => `
    <tr>
      <td><div class="case-id">${n.case_text}</div></td>
      <td>${n.content}</td>
      <td>${fmtDate(n.date)}</td>
      <td><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="deleteParkedNote('${n.app_record_id}')">刪除</button></td>
    </tr>
  `).join('');
}

function openMaterialModal(){
  renderMaterialList();
  document.getElementById('materialModalOverlay').classList.add('show');
}
function closeMaterialModal(){
  document.getElementById('materialModalOverlay').classList.remove('show');
}
async function addMaterialNote(){
  const caseInput = document.getElementById('materialCaseInput');
  const contentInput = document.getElementById('materialContentInput');
  const shipDateInput = document.getElementById('materialShipDateInput');
  const caseText = caseInput.value.trim();
  const content = contentInput.value.trim();
  const shipDate = shipDateInput.value;
  if(!content){ showToast('請填寫料件內容'); return; }
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: '未使用料件', case_text: caseText || '（未指定案場）', content, ship_date: shipDate || undefined}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    caseInput.value = '';
    contentInput.value = '';
    shipDateInput.value = '';
    const hintEl = document.getElementById('materialCaseHint');
    if(hintEl) hintEl.textContent = '';
    await loadAppData();
    renderMaterialList();
    showToast('已加入「未使用料件」清單');
  }catch(err){
    showToast('新增失敗：' + err.message);
    console.error(err);
  }
}
async function deleteMaterialNote(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/app-data/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== appRecordId);
    renderMaterialList();
  }catch(err){
    showToast('刪除失敗：' + err.message);
    console.error(err);
  }
}
function renderMaterialList(){
  const tbody = document.getElementById('materialRows');
  if(!tbody) return;
  const list = APP_NOTES.filter(n => n.type === '未使用料件');
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有未使用料件</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => {
    const found = findCaseByCaseNo(n.case_text);
    const vendorCell = found
      ? `<span class="vendor-pill ${VENDOR_CLASS[found.vendor] || 'vendor-other'}">${found.vendor}</span>`
      : '<span style="color:var(--text-muted);">—</span>';
    return `
    <tr>
      <td><div class="case-id">${n.case_text}</div></td>
      <td>${vendorCell}</td>
      <td style="white-space:pre-wrap;">${n.content}</td>
      <td>${n.ship_date ? fmtDate(n.ship_date) : '<span style="color:var(--text-muted);">無出貨日期</span>'}</td>
      <td>${fmtDate(n.date)}</td>
      <td>
        <button class="btn btn-primary" style="padding:4px 10px;font-size:11.5px;" onclick="openMaterialUseModal('${n.app_record_id}')">使用</button>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;margin-left:4px;" onclick="openMaterialEditModal('${n.app_record_id}')">編輯</button>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;margin-left:4px;" onclick="deleteMaterialNote('${n.app_record_id}')">刪除</button>
      </td>
    </tr>
  `;
  }).join('');
}
// 依「案號」在系統現有案件裡（待安排出貨/案件進場安排/已進場/歷史紀錄）找完全相符的一筆，
// 找不到就回傳 null（表示是自由輸入的案場，沒有對應的即時資料）。
function findCaseByCaseNo(caseNo){
  if(!caseNo) return null;
  const all = [
    ...PENDING_CASES,
    ...ENTRY_CASES,
    ...COMPLETED_CASES,
    ...APP_ARCHIVED.map(a => ({...a, record_id: a.case_record_id})),
  ];
  return all.find(c => c.case === caseNo) || null;
}
// 未使用料件新增時，如果填的案號跟系統裡現有的案件完全一致，自動帶出這個案件的
// 模組/逆變器料件內容、出貨日期，並在案號下方顯示廠商；使用者已經自己填過的欄位
// 不會被覆蓋。找不到對應案件時清空提示文字，讓使用者自己輸入。
function autofillMaterialFromCase(){
  const caseInput = document.getElementById('materialCaseInput');
  const contentInput = document.getElementById('materialContentInput');
  const shipDateInput = document.getElementById('materialShipDateInput');
  const hintEl = document.getElementById('materialCaseHint');
  if(!caseInput) return;
  const caseNo = caseInput.value.trim();
  const found = findCaseByCaseNo(caseNo);
  if(!found){
    if(hintEl) hintEl.textContent = caseNo ? '找不到對應案件,可自行輸入料件內容' : '';
    return;
  }
  if(shipDateInput && !shipDateInput.value){
    const shipDate = found.ship_date || getInverterDate(found.record_id) || '';
    if(shipDate) shipDateInput.value = shipDate;
  }
  if(contentInput && !contentInput.value.trim()){
    const parts = [];
    if(found.module) parts.push('模組：' + found.module);
    if(found.inverter) parts.push('逆變器：' + found.inverter);
    if(parts.length) contentInput.value = parts.join('\n');
  }
  if(hintEl) hintEl.textContent = found.vendor ? `已比對到案件（${found.vendor}）` : '已比對到案件';
}

// ---- 未使用料件：編輯案號／內容／出貨日期 ----
let materialEditTargetId = null;
function openMaterialEditModal(appRecordId){
  const note = APP_NOTES.find(n => n.app_record_id === appRecordId);
  if(!note){ showToast('找不到這筆料件資料，請重新整理頁面再試一次'); return; }
  materialEditTargetId = appRecordId;
  document.getElementById('materialEditCase').value = note.case_text || '';
  document.getElementById('materialEditContent').value = note.content || '';
  document.getElementById('materialEditShipDate').value = note.ship_date || '';
  document.getElementById('materialEditModalOverlay').classList.add('show');
}
function closeMaterialEditModal(){
  document.getElementById('materialEditModalOverlay').classList.remove('show');
}
async function confirmMaterialEdit(){
  const caseText = document.getElementById('materialEditCase').value.trim();
  const content = document.getElementById('materialEditContent').value.trim();
  const shipDate = document.getElementById('materialEditShipDate').value;
  if(!caseText){ showToast('請填寫案號或案場'); return; }
  if(!content){ showToast('請填寫料件內容'); return; }
  const btn = document.querySelector('#materialEditModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    const res = await fetch(API_BASE + '/api/app-data/note/' + materialEditTargetId, {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({case_text: caseText, content, ship_date: shipDate}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    closeMaterialEditModal();
    await loadAppData();
    renderMaterialList();
    showToast('已更新');
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 料件使用：把「未使用料件」清單裡的某一筆，登記成用在別的案場 ----
let materialUseSourceId = null;
function openMaterialUseModal(appRecordId){
  const note = APP_NOTES.find(n => n.app_record_id === appRecordId);
  if(!note){ showToast('找不到這筆料件資料，請重新整理頁面再試一次'); return; }
  materialUseSourceId = appRecordId;
  document.getElementById('materialUseSourceCase').textContent = note.case_text || '（未指定案場）';
  document.getElementById('materialUseSourceContent').textContent = note.content || '';
  document.getElementById('materialUseTargetCase').value = '';
  document.getElementById('materialUseContent').value = note.content || '';
  document.getElementById('materialUseDate').value = todayStr();
  document.getElementById('materialUseRemoveOriginal').checked = true;
  document.getElementById('materialUseModalOverlay').classList.add('show');
}
function closeMaterialUseModal(){
  document.getElementById('materialUseModalOverlay').classList.remove('show');
}
async function confirmMaterialUse(){
  const targetCase = document.getElementById('materialUseTargetCase').value.trim();
  const content = document.getElementById('materialUseContent').value.trim();
  const useDate = document.getElementById('materialUseDate').value;
  const removeOriginal = document.getElementById('materialUseRemoveOriginal').checked;
  if(!targetCase){ showToast('請填寫使用於哪個案號／案場'); return; }
  if(!content){ showToast('請填寫使用內容說明'); return; }
  const sourceNote = APP_NOTES.find(n => n.app_record_id === materialUseSourceId);
  const sourceCaseText = (sourceNote && sourceNote.case_text) || '（未指定案場）';
  const btn = document.querySelector('#materialUseModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        type: '料件使用',
        case_text: targetCase,
        content: `從「${sourceCaseText}」挪用：${content}`,
      }),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    if(removeOriginal && materialUseSourceId){
      await fetch(API_BASE + '/api/app-data/' + materialUseSourceId, {method: 'DELETE'});
      APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== materialUseSourceId);
    }
    closeMaterialUseModal();
    await loadAppData();
    renderMaterialList();
    renderMaterialUseList();
    showToast('已登記料件使用，記錄到「料件使用清單」');
  }catch(err){
    showToast('登記失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}
function openMaterialUseListModal(){
  renderMaterialUseList();
  document.getElementById('materialUseListModalOverlay').classList.add('show');
}
function closeMaterialUseListModal(){
  document.getElementById('materialUseListModalOverlay').classList.remove('show');
}
async function deleteMaterialUseNote(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/app-data/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== appRecordId);
    renderMaterialUseList();
  }catch(err){
    showToast('刪除失敗：' + err.message);
    console.error(err);
  }
}
function renderMaterialUseList(){
  const tbody = document.getElementById('materialUseRows');
  if(!tbody) return;
  const list = APP_NOTES.filter(n => n.type === '料件使用');
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有料件使用紀錄</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => `
    <tr>
      <td><div class="case-id">${n.case_text}</div></td>
      <td style="white-space:pre-wrap;">${n.content}</td>
      <td>${fmtDate(n.date)}</td>
      <td><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="deleteMaterialUseNote('${n.app_record_id}')">刪除</button></td>
    </tr>
  `).join('');
}

// ---- 撤案時，若案件已出貨，詢問是否把料件加入「未使用料件」清單 ----
let withdrawMaterialCaseText = '';
let withdrawMaterialShipDate = '';
function maybePromptWithdrawMaterial(recordId, found){
  if(!found || !found.ship_date) return; // 還沒出貨，不用問
  withdrawMaterialCaseText = found.case;
  withdrawMaterialShipDate = found.ship_date || '';
  document.getElementById('withdrawMaterialCaseTitle').textContent = found.case + (found.alias ? '　'+found.alias : '');
  const parts = [];
  if(found.module) parts.push('模組：' + found.module);
  if(found.inverter) parts.push('逆變器：' + found.inverter);
  document.getElementById('withdrawMaterialContent').value = parts.join('\n');
  document.getElementById('withdrawMaterialPromptOverlay').classList.add('show');
}
function closeWithdrawMaterialPrompt(){
  document.getElementById('withdrawMaterialPromptOverlay').classList.remove('show');
}
async function confirmWithdrawMaterial(){
  const content = document.getElementById('withdrawMaterialContent').value.trim();
  if(!content){ showToast('請填寫料件內容'); return; }
  const btn = document.querySelector('#withdrawMaterialPromptOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '加入中…';
  btn.disabled = true;
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: '未使用料件', case_text: withdrawMaterialCaseText, content, ship_date: withdrawMaterialShipDate || undefined}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    closeWithdrawMaterialPrompt();
    await loadAppData();
    showToast('已加入「未使用料件」清單');
  }catch(err){
    showToast('加入失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

function showEpcTab(tab){
  showView('epc');
  document.querySelectorAll('#view-epc .subview').forEach(v=>v.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  document.querySelectorAll('#view-epc .tab').forEach(t=>t.classList.remove('active'));
  document.querySelector('#view-epc .tab[data-tab="'+tab+'"]').classList.add('active');
  document.querySelectorAll('.nav-sub-item').forEach(n=>n.classList.remove('active'));
  document.querySelector('.nav-sub-item[data-sub="'+tab+'"]').classList.add('active');
  if(tab === 'epc-calendar') renderCalendar();
  if(tab === 'epc-week') renderWeekList();
}
function filterVendor(v){
  calVendorFilter = v;
  document.querySelectorAll('.vendor-chip').forEach(c=>c.classList.remove('active'));
  document.querySelector('.vendor-chip[data-vendor="'+v+'"]').classList.add('active');
  document.querySelectorAll('.cal-grid .chip').forEach(chip=>{
    if(v==='all' || chip.getAttribute('data-vendor')===v){
      chip.classList.remove('chip-dim');
      chip.style.display='';
    } else {
      chip.style.display='none';
    }
  });
}
function changeCalMonth(delta){
  calMonth += delta;
  if(calMonth < 0){ calMonth = 11; calYear -= 1; }
  if(calMonth > 11){ calMonth = 0; calYear += 1; }
  renderCalendar();
}
function fmtISODate(y, m, d){
  // m 為 0-based 月份
  return y + '-' + String(m+1).padStart(2,'0') + '-' + String(d).padStart(2,'0');
}
const VENDOR_CODE = {'三創':'sc','尚展':'sz','曙光':'sg','光鼎':'gd'};
// 案號前綴（原始案場公司）對應的簡稱，依「原始案號」欄位比對
const CASE_PREFIX_MAP = {
  '潤特新北':'新', '潤特桃園':'桃', '潤特新竹':'竹', '潤特苗栗':'苗', '潤特臺中':'中', '潤特台中':'中',
  '潤特南投':'投', '潤特彰化':'彰', '潤特雲林':'雲', '潤特嘉義':'嘉', '潤特臺南':'南', '潤特台南':'南',
  '潤特高雄':'高', '潤特屏東':'屏', '潤特宜蘭':'宜',
  '工程新北':'工新', '工程桃園':'工桃', '工程新竹':'工竹', '工程苗栗':'工苗', '工程臺中':'工中', '工程台中':'工中',
  '工程南投':'工投', '工程彰化':'工彰', '工程雲林':'工雲', '工程嘉義':'工嘉', '工程臺南':'工南', '工程台南':'工南',
  '工程高雄':'工高', '工程屏東':'工屏', '工程宜蘭':'工宜',
};
const CASE_PREFIX_KEYS = Object.keys(CASE_PREFIX_MAP).sort((a,b) => b.length - a.length);
function caseAbbrCode(caseStr){
  if(!caseStr) return '';
  for(const k of CASE_PREFIX_KEYS){
    if(caseStr.startsWith(k)) return CASE_PREFIX_MAP[k];
  }
  return caseStr[0] || ''; // 找不到對應前綴時，退回取案號第一個字，避免完全沒有標示
}
function calShortLabel(caseStr, vendor){
  const digits = (caseStr||'').match(/\d+/);
  const code = caseAbbrCode(caseStr);
  return (vendor || '') + ' ' + code + (digits ? digits[0] : '');
}
function collectCalendarEvents(){
  const map = new Map();
  function add(date, type, r, recordId){
    if(!date) return;
    const key = date + '|' + type + '|' + (recordId || r.case);
    if(map.has(key)) return;
    map.set(key, {
      date, type,
      record_id: recordId || r.record_id,
      case: r.case,
      alias: r.alias || '',
      label: calShortLabel(r.case, r.vendor),
      vendor: r.vendor,
      vendorCode: VENDOR_CODE[r.vendor] || 'other',
      address: r.address,
      module: r.module || '',
      inverter: r.inverter || '',
    });
  }
  // 模組出貨與變流器出貨：同一天到貨就合併成一筆「模組&變流器」事件,不同天則各自獨立顯示
  function addShipEvents(r, recordId){
    const moduleDate = r.ship_date;
    const invDate = getInverterDate(recordId || r.record_id);
    if(moduleDate && invDate && moduleDate === invDate){
      add(moduleDate, 'ship-both', r, recordId);
    } else {
      if(moduleDate) add(moduleDate, 'ship-module', r, recordId);
      if(invDate) add(invDate, 'ship-inverter', r, recordId);
    }
  }
  [...ENTRY_CASES, ...COMPLETED_CASES].forEach(r => {
    addShipEvents(r, r.record_id);
  });
  COMPLETED_CASES.forEach(r => {
    if(r.entry_date) add(r.entry_date, 'enter', r, r.record_id);
    const cs = getCaseStatus(r.record_id);
    if(cs && cs.meter_planned_date && !cs.meter_confirmed) add(cs.meter_planned_date, 'meter-planned', r, r.record_id);
  });
  // 植筋：跟進場一起（rebar_with_entry）的案件不另外顯示植筋事件，已經算在進場事件裡了
  [...PENDING_CASES, ...ENTRY_CASES, ...COMPLETED_CASES].forEach(r => {
    const cs = getCaseStatus(r.record_id);
    if(!cs || cs.rebar_with_entry || !cs.rebar_planned_date) return;
    add(cs.rebar_planned_date, 'rebar', r, r.record_id);
  });
  APP_ARCHIVED.forEach(r => {
    const rid = r.case_record_id;
    addShipEvents(r, rid);
    if(r.entry_date) add(r.entry_date, 'enter', r, rid);
    if(r.meter_date) add(r.meter_date, 'meter', r, rid);
  });
  return Array.from(map.values());
}
const CAL_TYPE_LABEL = {
  'ship-module': '模組出貨', 'ship-inverter': '變流器出貨', 'ship-both': '模組&變流器出貨',
  enter: '進場', meter: '掛表', 'meter-planned': '預計掛表',
  rebar: '植筋',
};
const CAL_TYPE_DOT = {
  'ship-module': 'dot-ship', 'ship-inverter': 'dot-ship', 'ship-both': 'dot-ship',
  enter: 'dot-enter', meter: 'dot-meter', 'meter-planned': 'dot-meter',
  rebar: 'dot-rebar',
};
const CAL_TYPE_CHIP = {
  'ship-module': 'chip-ship', 'ship-inverter': 'chip-ship', 'ship-both': 'chip-ship',
  enter: 'chip-enter', meter: 'chip-meter', 'meter-planned': 'chip-meter',
  rebar: 'chip-rebar',
};
let calYear = new Date().getFullYear();
let calMonth = new Date().getMonth();
let calVendorFilter = 'all';
let calSelectedDate = null;
function selectCalDay(dateStr){
  calSelectedDate = dateStr;
  document.querySelectorAll('#calGrid .cal-cell').forEach(c => c.classList.remove('cal-cell-selected'));
  const cell = document.querySelector(`#calGrid .cal-cell[data-date="${dateStr}"]`);
  if(cell) cell.classList.add('cal-cell-selected');
  renderDayDetail(dateStr);
}
function renderDayDetail(dateStr){
  const title = document.getElementById('dayDetailTitle');
  const rows = document.getElementById('dayDetailRows');
  if(!title || !rows) return;
  if(!dateStr){
    title.textContent = '選擇日期查看當日排程';
    rows.innerHTML = '<div class="login-note">點選上方日曆中的任一天,就會在這裡列出當天所有的出貨/進場/掛表排程。</div>';
    return;
  }
  const p = dateStr.split('-');
  const d = new Date(Number(p[0]), Number(p[1])-1, Number(p[2]));
  const weekday = ['日','一','二','三','四','五','六'][d.getDay()];
  title.textContent = p[1] + '/' + p[2] + '（' + weekday + '）當日排程';
  const events = collectCalendarEvents().filter(e => e.date === dateStr);
  if(events.length === 0){
    rows.innerHTML = '<div class="login-note">這天目前沒有排程。</div>';
    return;
  }
  rows.innerHTML = events.map(e => {
    let specLine = '';
    if(e.type === 'ship-module' && e.module){
      specLine = `<div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">模組：${glueCount(e.module)}</div>`;
    } else if(e.type === 'ship-inverter' && e.inverter){
      specLine = `<div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">變流器：${glueCount(e.inverter)}</div>`;
    } else if(e.type === 'ship-both'){
      const parts = [];
      if(e.module) parts.push('模組：' + glueCount(e.module));
      if(e.inverter) parts.push('變流器：' + glueCount(e.inverter));
      if(parts.length) specLine = `<div style="font-size:11.5px;color:var(--text-muted);margin-top:2px;">${parts.join('　')}</div>`;
    }
    return `
    <div class="day-detail-row" style="align-items:flex-start;">
      <div class="dd-left" style="flex-direction:column;align-items:flex-start;gap:2px;">
        <div style="display:flex;align-items:center;gap:8px;"><span class="dot ${CAL_TYPE_DOT[e.type]}"></span><span class="case-id">${e.case}</span>${e.alias ? `<span style="font-size:11px;color:var(--text-muted);">${e.alias}</span>` : ''} ${CAL_TYPE_LABEL[e.type]}</div>
        ${specLine}
      </div>
      <span class="vendor-pill ${VENDOR_CLASS[e.vendor] || 'vendor-other'}">${e.vendor||''}</span>
    </div>
  `;
  }).join('');
}
function renderWeekList(){
  const titleEl = document.getElementById('weekRangeTitle');
  const rowsEl = document.getElementById('weekRows');
  if(!titleEl || !rowsEl) return;

  const today = new Date();
  today.setHours(0,0,0,0);
  const end = new Date(today);
  end.setDate(end.getDate() + 6);
  const fmtMD = (d) => (d.getMonth()+1).toString().padStart(2,'0') + '/' + d.getDate().toString().padStart(2,'0');
  titleEl.textContent = `近一週安排（${fmtMD(today)} － ${fmtMD(end)}）`;

  const startIso = fmtISODate(today.getFullYear(), today.getMonth(), today.getDate());
  const endIso = fmtISODate(end.getFullYear(), end.getMonth(), end.getDate());
  const events = collectCalendarEvents()
    .filter(e => e.date >= startIso && e.date <= endIso)
    .sort((a,b) => a.date < b.date ? -1 : (a.date > b.date ? 1 : 0));

  if(events.length === 0){
    rowsEl.innerHTML = '<div class="login-note">未來 7 天內目前沒有排程。</div>';
    return;
  }
  const weekdayNames = ['日','一','二','三','四','五','六'];
  rowsEl.innerHTML = events.map(e => {
    const p = e.date.split('-');
    const d = new Date(Number(p[0]), Number(p[1])-1, Number(p[2]));
    const dayLabel = p[1] + '/' + p[2] + '（' + weekdayNames[d.getDay()] + '）';
    return `
    <div class="day-detail-row">
      <div class="dd-left"><span class="pm-pill" style="background:var(--surface-2);">${dayLabel}</span><span class="dot ${CAL_TYPE_DOT[e.type]}"></span><span class="case-id">${e.case}</span>${e.alias ? `<span style="font-size:11px;color:var(--text-muted);">${e.alias}</span>` : ''} ${CAL_TYPE_LABEL[e.type]}</div>
      <span class="vendor-pill ${VENDOR_CLASS[e.vendor] || 'vendor-other'}">${e.vendor||''}</span>
    </div>
  `;
  }).join('');
}
function renderCalendar(){
  const grid = document.getElementById('calGrid');
  const label = document.getElementById('calMonthLabel');
  if(!grid || !label) return;
  label.textContent = calYear + '年' + (calMonth+1) + '月';

  const events = collectCalendarEvents();
  const eventsByDate = {};
  events.forEach(e => { (eventsByDate[e.date] = eventsByDate[e.date] || []).push(e); });

  const firstOfMonth = new Date(calYear, calMonth, 1);
  const startWeekday = (firstOfMonth.getDay() + 6) % 7; // 週一為 0
  const daysInMonth = new Date(calYear, calMonth+1, 0).getDate();
  const daysInPrevMonth = new Date(calYear, calMonth, 0).getDate();
  const todayIso = todayStr();
  const totalCells = Math.ceil((startWeekday + daysInMonth) / 7) * 7;

  let cellsHtml = '';
  for(let i=0;i<totalCells;i++){
    const dayNum = i - startWeekday + 1;
    let cellDate, dayLabel, muted = false;
    if(dayNum < 1){
      dayLabel = daysInPrevMonth + dayNum;
      const pm = calMonth === 0 ? 11 : calMonth - 1;
      const py = calMonth === 0 ? calYear - 1 : calYear;
      cellDate = fmtISODate(py, pm, dayLabel);
      muted = true;
    } else if(dayNum > daysInMonth){
      dayLabel = dayNum - daysInMonth;
      const nm = calMonth === 11 ? 0 : calMonth + 1;
      const ny = calMonth === 11 ? calYear + 1 : calYear;
      cellDate = fmtISODate(ny, nm, dayLabel);
      muted = true;
    } else {
      dayLabel = dayNum;
      cellDate = fmtISODate(calYear, calMonth, dayNum);
    }
    const dayEvents = eventsByDate[cellDate] || [];
    const chipsHtml = dayEvents.map(e => {
      const dim = (calVendorFilter !== 'all' && e.vendorCode !== calVendorFilter) ? ' chip-dim' : '';
      return `<div class="chip ${CAL_TYPE_CHIP[e.type]}${dim}" data-vendor="${e.vendorCode}" title="${e.case}　${e.vendor||''}">${e.label} ${CAL_TYPE_LABEL[e.type]}</div>`;
    }).join('');
    const isToday = cellDate === todayIso;
    const selectedClass = cellDate === calSelectedDate ? ' cal-cell-selected' : '';
    cellsHtml += `<div class="cal-cell${muted?' muted':''}${selectedClass}" data-date="${cellDate}" onclick="selectCalDay('${cellDate}')">
      <div class="cal-date${isToday?' today':''}">${dayLabel}</div>
      ${chipsHtml}
    </div>`;
  }

  grid.innerHTML = `
    <div class="cal-dow">一</div><div class="cal-dow">二</div><div class="cal-dow">三</div>
    <div class="cal-dow">四</div><div class="cal-dow">五</div><div class="cal-dow">六</div><div class="cal-dow">日</div>
    ${cellsHtml}
  `;

  if(calVendorFilter !== 'all') filterVendor(calVendorFilter);

  // 預設選取：若今天落在目前顯示的月份就選今天，否則選當月 1 號
  if(!calSelectedDate || calSelectedDate.slice(0,7) !== fmtISODate(calYear, calMonth, 1).slice(0,7)){
    const todayInThisMonth = todayIso.slice(0,7) === fmtISODate(calYear, calMonth, 1).slice(0,7);
    calSelectedDate = todayInThisMonth ? todayIso : fmtISODate(calYear, calMonth, 1);
    const cell = document.querySelector(`#calGrid .cal-cell[data-date="${calSelectedDate}"]`);
    if(cell) cell.classList.add('cal-cell-selected');
  }
  renderDayDetail(calSelectedDate);
}
function showPdfTab(tab){
  showView('pdf');
  document.querySelectorAll('.subview').forEach(v=>v.classList.remove('active'));
  document.getElementById('tab-'+tab).classList.add('active');
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelector('.tab[data-tab="'+tab+'"]').classList.add('active');
  document.querySelectorAll('.nav-sub-item').forEach(n=>n.classList.remove('active'));
  document.querySelector('.nav-sub-item[data-sub="'+tab+'"]').classList.add('active');
}
showView('home');
</script>

</body>
</html>
