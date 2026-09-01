<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<!-- 2026-09-01 新增：沒有這個標籤時，手機瀏覽器預設會用「桌面寬度（約980px）」
     去渲染整個頁面、再整頁縮小塞進螢幕，導致所有 @media (max-width:...) 的
     手機版 CSS 規則永遠判斷不到「這是手機」而不會生效（DevTools 的手機模擬
     模式因為會強制用實際裝置寬度渲染，所以不受影響，才會出現「模擬器正常、
     真手機不正常」的落差）。加上這行以後，瀏覽器才會照手機螢幕的實際寬度
     渲染，前面寫的手機版 RWD 樣式才會真的生效。-->
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
  .vendor-yyd{background:#F1ECFE;color:#7C3AED;}
  .vendor-jy{background:#E0F7FA;color:#00838F;}
  .vendor-cp{background:#FCE4EC;color:#C2185B;}
  .vendor-ds{background:#EFEBE9;color:#6D4C41;}
  .vendor-zy{background:#E8EAF6;color:#3F51B5;}
  .vendor-htz{background:#F1F8E9;color:#689F38;}
  .vendor-gq{background:#FFF8E1;color:#F57F17;}
  .vendor-zt{background:#ECEFF1;color:#455A64;}
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

  /* ---------- 手機版響應式（2026-09-01 新增）---------- */
  .mobile-topbar{
    display:none;align-items:center;gap:12px;padding:12px 16px;
    background:var(--surface);border-bottom:1px solid var(--border);
    position:sticky;top:0;z-index:150;
  }
  .mobile-hamburger{
    width:36px;height:36px;flex-shrink:0;border-radius:10px;border:1px solid var(--border);
    background:var(--surface);font-size:18px;color:var(--text);cursor:pointer;
  }
  .mobile-topbar-brand{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14px;}
  .sidebar-overlay{
    display:none;position:fixed;inset:0;background:rgba(20,25,40,.45);z-index:190;
  }
  .sidebar-overlay.show{display:block;}

  @media (max-width: 860px){
    body{flex-direction:column;}
    .mobile-topbar{display:flex;}
    .sidebar{
      position:fixed;top:0;left:0;bottom:0;width:250px;z-index:200;
      transform:translateX(-100%);transition:transform .22s ease;
      box-shadow:10px 0 30px rgba(20,30,60,.18);
    }
    .sidebar.open{transform:translateX(0);}
    .main{padding:16px 14px 32px;}
    .page-title{font-size:19px;}
    .grid{grid-template-columns:1fr;}
    .tabs{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;}
    .tabs .tab{flex-shrink:0;white-space:nowrap;}
    .panel{padding:14px;}
    .panel, .modal-body{overflow-x:auto;-webkit-overflow-scrolling:touch;}
    .panel table, .modal-body table{min-width:640px;}
    .modal-box{max-width:100%;border-radius:0;min-height:100%;}
    .modal-overlay{padding:0;align-items:stretch;}
    .modal-body{max-height:calc(100vh - 60px);}
    .cal-cell{min-height:60px;padding:4px;}
    .chip{font-size:9px;padding:1px 4px;}
    .cal-month{font-size:14px;min-width:auto;}
    .note-add-row, .note-add-row-wide, .pending-toolbar{flex-wrap:wrap;}
    .note-add-row-wide input:first-child{flex:1 1 100%;}
    /* iOS Safari 會在 input font-size 小於 16px 時自動放大畫面，統一調成 16px 避免這個狀況 */
    .quick-mark-input, select, textarea, input[type="date"], input[type="text"], input[type="number"]{
      font-size:16px;
    }
    .stat-value{font-size:22px;}
    .module-card{padding:16px 18px;flex-direction:column;align-items:flex-start;gap:10px;}
    .module-desc{max-width:100%;}
  }
</style>
</head>
<body>

  <div class="toast" id="toastBanner"></div>

  <div class="mobile-topbar">
    <button class="mobile-hamburger" onclick="toggleSidebar()" aria-label="開啟選單">☰</button>
    <div class="mobile-topbar-brand">
      <div class="brand-mark" style="width:26px;height:26px;font-size:12px;">陽</div>
      <span>陽光管理主控台</span>
    </div>
  </div>
  <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

  <aside class="sidebar" id="sidebar">
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
        <div class="nav-item" data-view="pdf" onclick="toggleNavSection('pdf')">
          <span class="nav-icon">📄</span> PDF 公文更名
        </div>
        <div class="nav-sub" id="navSub-pdf">
          <div class="nav-sub-item" data-sub="pdf-rename" onclick="showPdfTab('pdf-rename')">公文更名</div>
          <div class="nav-sub-item" data-sub="pdf-line" onclick="showPdfTab('pdf-line')">LINE 收件紀錄</div>
        </div>
        <div class="nav-item" data-view="epc" onclick="toggleNavSection('epc')">
          <span class="nav-icon">🚚</span> EPC 出貨／進場排程
        </div>
        <div class="nav-sub" id="navSub-epc">
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
        <div style="position:relative;flex-shrink:0;">
          <button class="btn btn-ghost" style="padding:7px 14px;font-size:12.5px;white-space:nowrap;" onclick="toggleGlobalVendorDropdown(event)">
            🏭 廠商<span id="globalVendorFilterLabel"></span> ▾
          </button>
          <div class="vendor-dropdown" id="globalVendorDropdown" style="right:0;left:auto;min-width:150px;"></div>
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
            🔗 這裡只顯示未來 7 天內的所有排程項目,跨廠商彙整,方便快速掌握近期要出貨/進場的案件,不用逐日翻日曆。要篩選廠商請用右上角的「🏭 廠商」按鈕,所有頁面共用同一份篩選設定。
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
            <button class="btn btn-ghost notes-trigger-btn" onclick="openNotebookModal()">📓 筆記本</button>
          </div>

          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="pendingSearchInput" placeholder="搜尋案號或別名…" oninput="renderPendingTable()" style="max-width:260px;">
          </div>

          <table>
            <thead>
              <tr>
                <th class="sortable-th" onclick="sortPendingBy('case')">案號／別名 <span id="pendingSortIcon_case">↕</span></th>
                <th>廠商</th>
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
            🔗 資料每天 00:00／06:00／12:00／18:00 自動整批更新一次(伺服器背景排程),平常開啟頁面是直接讀取這份快取,不會每次都重新查 Airtable。點「排定日期」寫入成功後,會立刻觸發一次重新整理,清單會馬上反映最新狀態。標示「⚠ 尚未填寫規格」的案件仍會列在清單中提醒你安排出貨,只是模組/逆變器資訊還沒填。點欄位標題（案號／別名、觸發依據、模組、逆變器）可切換排序,輸入框可用案號、別名、模組、逆變器內容篩選,點廠商 chip 可篩選特定廠商。點「🪛」植筋按鈕可以安排植筋日期,或勾選「跟進場一起」;植筋日期一旦過了當天,隔天會自動視為完成,不用手動標記。「🏠」屋主資訊按鈕可以先在這個階段填寫屋主聯絡人／電話／備註,跟「案件進場安排」共用同一份資料,不用等到進場階段才能填,也不用重複輸入。
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
              <th>廠商</th>
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
            🔗 案件在「待安排出貨&植筋」完成排定出貨時間後,會自動移入這裡等待安排進場日期;進場日期排定後,狀態會變成「已安排」,案件仍會留在這裡,直到你按下「完工」填好完工日期,案件就會移入「掛表安排」,依「細部協商」「台電購售契約」是否都已取得,自動分類到「待安排掛表」或「待函文取得」（會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到）。點「案號」「模組／逆變器」欄位標題可排序,點「廠商」可篩選特定廠商,輸入框可用案號、地址、模組、逆變器內容搜尋。
          </div>
        </div>
      </div>

      <!-- 掛表安排 -->
      <div class="subview" id="tab-epc-meter">
        <div class="panel">
          <div class="panel-title">
            待安排掛表 <span class="module-tag tag-cloud" style="margin-left:6px;" id="meterReadyCountTag">共 0 筆</span>
          </div>
          <div class="pending-toolbar">
            <input type="text" class="quick-mark-input" id="meterFilterInput" placeholder="搜尋案號、地址、模組、逆變器…" oninput="tableSearchInput('meter')" style="max-width:280px;">
          </div>
          <table>
            <thead><tr>
              <th class="sortable-th" onclick="sortTableBy('meter','case')">案號 <span id="meterSortIcon_case">↕</span></th>
              <th>廠商</th>
              <th>案場地址</th>
              <th class="sortable-th" onclick="sortTableBy('meter','module')">模組／逆變器 <span id="meterSortIcon_module">↕</span></th>
              <th>細部協商</th>
              <th>台電購售契約</th>
              <th>預計掛表日期</th>
              <th>操作</th>
            </tr></thead>
            <tbody id="meterRows">
              <tr>
                <td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 這裡只列出已完工、已排定預計掛表日期，而且「細部協商」跟「台電購售契約」都已取得的案件——這兩份函文都到齊，代表真的可以安排掛表了。點預計日期可以修正；按「完成掛表」會跳出確認,寫入後案件會移入「歷史紀錄」。點「案號」「模組／逆變器」欄位標題可排序,輸入框可用案號、地址、模組、逆變器內容搜尋。地址下方會顯示屋主聯絡人／電話（在「案件進場安排」填過的資料）,點一下可以查看完整備註或修改。
          </div>
        </div>

        <div class="panel" style="margin-top:16px;">
          <div class="panel-title">
            待函文取得 <span class="module-tag tag-cloud" style="margin-left:6px;" id="meterWaitingCountTag">共 0 筆</span>
          </div>
          <table>
            <thead><tr>
              <th>案號</th>
              <th>廠商</th>
              <th>案場地址</th>
              <th>模組／逆變器</th>
              <th>細部協商</th>
              <th>台電購售契約</th>
              <th>掛表安排</th>
            </tr></thead>
            <tbody id="meterWaitingRows">
              <tr>
                <td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">載入中…</td>
              </tr>
            </tbody>
          </table>
          <div class="login-note">
            🔗 這裡列出已完工、但「細部協商」跟「台電購售契約」還沒有全部取得的案件——這兩份函文的目前狀態直接顯示在這裡（跟 Airtable「進度管理」表同步，每 6 小時自動更新一次，或點「待安排出貨&植筋」的「手動更新」立即重查）。「掛表安排」按鈕在函文還沒到齊時是灰色、按不動的；等兩份都取得日期後，案件會自動移到上方「待安排掛表」，才能真的排掛表日期。
          </div>
        </div>
      </div>

      <!-- 異常案件（已完工但目前卡住無法安排/完成掛表） -->
      <div class="subview" id="tab-epc-issue">
        <div class="panel">
          <div class="panel-title">
            異常案件
            <button class="btn btn-ghost notes-trigger-btn" onclick="recheckAllDocStatus()">🔄 重新檢查函文進度</button>
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
              <th>廠商</th>
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
            🔗 這份清單會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到。在上方輸入案號即可加入；按「已排除異常」會移出此清單,案件依原本階段繼續正常顯示在對應頁面;按「撤案」會移到「撤案清單」（點上方按鈕查看）。「待取得函文」是選填功能,標記異常時可以順便選案件是卡在等哪份函文（免雜／細部協商／台電購售契約）,只有第一次看到會即時查 Airtable「進度管理」表的實際進度,之後重繪畫面（包含背景自動同步）都用快取結果顯示,不會一直重查;想看最新狀態可以點上方「🔄 重新檢查函文進度」,或在「待安排出貨&植筋」按「手動更新」（會一併刷新這裡）。一旦偵測到函文已取得,案件會自動排除異常、回到「待安排出貨&植筋」清單,「觸發依據」欄位也會自動改顯示這份函文的日期。點「案號」欄位標題可排序,點「廠商」可篩選特定廠商,下方搜尋框可用案號、地址內容篩選。
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
              <th>廠商</th>
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
              已整理「案件進場安排」裡所有案件的出貨資訊,複製後可直接貼到 Slack 通知採購。可篩選特定廠商,也可設定模組出貨日期區間,留空/選「全部廠商」代表不篩選（顯示全部）。
            </div>
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px;flex-wrap:wrap;">
              <select class="quick-mark-input" id="notifyVendorFilter" style="max-width:150px;" onchange="openNotifyModal()">
                <option value="all">全部廠商</option>
                <option value="三創">三創</option>
                <option value="尚展">尚展</option>
                <option value="曙光">曙光</option>
                <option value="光鼎">光鼎</option>
                <option value="宇陽達">宇陽達</option>
                <option value="聚曜">聚曜</option>
                <option value="澄品">澄品</option>
                <option value="大昇">大昇</option>
                <option value="展亦">展亦</option>
                <option value="凰太竹">凰太竹</option>
                <option value="國欽">國欽</option>
                <option value="振庭">振庭</option>
              </select>
              <input type="date" class="quick-mark-input" id="notifyDateFrom" style="flex:1;min-width:130px;" onchange="openNotifyModal()">
              <span style="color:var(--text-muted);font-size:13px;">至</span>
              <input type="date" class="quick-mark-input" id="notifyDateTo" style="flex:1;min-width:130px;" onchange="openNotifyModal()">
              <button class="btn btn-ghost" style="white-space:nowrap;padding:9px 14px;" onclick="document.getElementById('notifyDateFrom').value='';document.getElementById('notifyDateTo').value='';document.getElementById('notifyVendorFilter').value='all';openNotifyModal();">清除篩選</button>
            </div>
            <textarea id="notifyTextarea" readonly style="width:100%;min-height:260px;border:1px solid var(--border);border-radius:10px;padding:14px;font-size:12.5px;font-family:ui-monospace,monospace;line-height:1.7;color:var(--text);background:var(--surface-2);resize:vertical;"></textarea>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;margin-top:12px;" onclick="copyNotifyText()">📎 複製訊息</button>
          </div>
        </div>
      </div>

      <!-- 筆記本 modal -->
      <div class="modal-overlay" id="notebookModalOverlay" onclick="if(event.target===this) closeNotebookModal()">
        <div class="modal-box" style="max-width:640px;">
          <div class="modal-header">
            <div class="modal-title">📓 筆記本</div>
            <button class="modal-close" onclick="closeNotebookModal()">✕</button>
          </div>
          <div class="modal-body">
            <div class="tabs" style="margin-bottom:16px;">
              <div class="tab active" data-notebook-tab="local" onclick="showNotebookTab('local')">本地紀錄（只存這台電腦）</div>
              <div class="tab" data-notebook-tab="online" onclick="showNotebookTab('online')">線上紀錄（同事都能看到）</div>
            </div>

            <div class="panel" style="margin-bottom:16px;">
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">案場（可輸入案號、地址關鍵字、或屋主姓名的一部分來模糊搜尋，選填）</label>
              <div class="quick-mark" style="margin-bottom:10px;">
                <div class="quick-mark-input-wrap">
                  <input type="text" class="quick-mark-input" id="notebookCaseInput" placeholder="例如：桃園81號、龍潭中正、張榮煌…" autocomplete="off" oninput="onNotebookCaseInput()">
                  <div class="quick-mark-results" id="notebookSearchResults"></div>
                </div>
              </div>
              <div id="notebookCaseSummary" style="display:none;background:var(--surface-2);border-radius:10px;padding:10px 12px;margin-bottom:10px;font-size:12px;line-height:1.7;"></div>
              <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">紀錄內容</label>
              <textarea class="quick-mark-input" id="notebookContentInput" rows="3" style="width:100%;font-family:inherit;resize:vertical;margin-bottom:10px;" placeholder="例如：已電話跟廠商約 9/5 出貨，待確認金額"></textarea>
              <button class="btn btn-primary" id="notebookAddBtn" onclick="addNotebookEntry()">＋ 加入本地紀錄</button>
            </div>

            <div class="subview active" id="notebook-tab-local">
              <table>
                <thead><tr><th>案號</th><th>內容</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="notebookLocalRows">
                  <tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有本地紀錄</td></tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 本地紀錄只存在「這台電腦、這個瀏覽器」裡，換電腦或清掉瀏覽器資料就會不見，同事在別台電腦也看不到——適合先隨手記下來、還不確定要不要讓大家知道的內容。想讓同事一起看到，點「⬆ 上傳」把這筆移到線上紀錄（上傳後這台電腦的本地紀錄會被移除，改成存在線上）。
              </div>
            </div>

            <div class="subview" id="notebook-tab-online">
              <table>
                <thead><tr><th>案號</th><th>內容</th><th>記錄日期</th><th>操作</th></tr></thead>
                <tbody id="notebookOnlineRows">
                  <tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有線上紀錄</td></tr>
                </tbody>
              </table>
              <div class="login-note">
                🔗 線上紀錄會寫回 Airtable「APP資料」表，不同電腦／同事都能同步看到，適合已經確認、需要跟團隊共享的內容。
              </div>
            </div>
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
            <div class="modal-title">✓ 標記完工</div>
            <button class="modal-close" onclick="closeCompleteMeterModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="completeMeterCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="completeMeterCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">完工日期</label>
            <input type="date" class="quick-mark-input" id="completeMeterCompletedDate" style="margin-bottom:6px;">
            <div style="font-size:11.5px;color:var(--text-muted);margin-bottom:18px;">會寫回 Airtable「APP資料」表,不同電腦/同事都能同步看到;送出後案件會移入「掛表安排」，依「細部協商」「台電購售契約」是否都已取得，自動分類到「待安排掛表」或「待函文取得」。掛表日期不用在這裡先填，等函文都到齊、案件進到「待安排掛表」後再另外安排。</div>
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

      <!-- 填寫模組／逆變器規格 modal -->
      <div class="modal-overlay" id="caseSpecModalOverlay" onclick="if(event.target===this) closeCaseSpecModal()">
        <div class="modal-box" style="max-width:520px;">
          <div class="modal-header">
            <div class="modal-title">🔧 填寫模組／逆變器規格</div>
            <div style="display:flex;align-items:center;gap:10px;">
              <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openModelManageModal()">🗂 管理型號清單</button>
              <button class="modal-close" onclick="closeCaseSpecModal()">✕</button>
            </div>
          </div>
          <div class="modal-body">
            <div style="margin-bottom:14px;">
              <div style="font-weight:700;font-size:14px;" id="caseSpecCaseTitle">—</div>
              <div style="font-size:12px;color:var(--text-muted);margin-top:2px;" id="caseSpecCaseAddr">—</div>
            </div>
            <label style="font-size:12px;font-weight:600;display:block;margin-bottom:6px;">模組型號</label>
            <div style="display:flex;gap:8px;margin-bottom:6px;">
              <select class="quick-mark-input" id="caseSpecModuleModel" style="flex:1;"></select>
              <input type="text" class="quick-mark-input" id="caseSpecModuleModelText" style="flex:1;display:none;" placeholder="例如：500W_TS60-CMH-500 H6QT">
              <input type="text" class="quick-mark-input" id="caseSpecModuleQty" style="width:90px;background:var(--surface-2);color:var(--text-muted);" disabled placeholder="片數">
            </div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:16px;">片數由 Airtable 自動計算，這裡僅顯示目前數值，無法在此修改。</div>
            <label style="font-size:12px;font-weight:700;display:block;margin-bottom:8px;">逆變器（可加多筆,型號可直接輸入關鍵字快速篩選,但仍必須從 Airtable 現有清單裡選一個,不能自己亂打字；數量填「這個型號總共要幾顆」,儲存時系統會自動幫你在 Airtable「採購-逆變器」表建立/比對對應筆數的記錄,不用自己手動一筆一筆新增）</label>
            <div id="caseSpecInverterRows" style="display:flex;flex-direction:column;gap:8px;margin-bottom:10px;"></div>
            <datalist id="inverterOptionsDatalist"></datalist>
            <button class="btn btn-ghost" style="margin-bottom:18px;" onclick="addCaseSpecInverterRow()">＋ 新增逆變器</button>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:14px;">這裡填寫的內容會直接寫回 Airtable「專案細節」表,不用再回 Airtable 手動填。</div>
            <button class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmCaseSpec()">儲存</button>
          </div>
        </div>
      </div>

      <!-- 管理模組／逆變器型號清單 modal -->
      <div class="modal-overlay" id="modelManageModalOverlay" onclick="if(event.target===this) closeModelManageModal()">
        <div class="modal-box" style="max-width:500px;">
          <div class="modal-header">
            <div class="modal-title">🗂 管理型號清單</div>
            <button class="modal-close" onclick="closeModelManageModal()">✕</button>
          </div>
          <div class="modal-body">
            <div style="font-weight:700;font-size:13.5px;margin-bottom:10px;">模組型號</div>
            <div style="display:flex;gap:8px;margin-bottom:10px;">
              <input type="text" class="quick-mark-input" id="newModuleModelInput" placeholder="輸入新的模組型號" style="flex:1;">
              <button class="btn btn-primary" onclick="addNewModuleModel()">＋ 新增</button>
            </div>
            <div id="moduleModelListArea" style="max-height:140px;overflow-y:auto;font-size:12.5px;color:var(--text-muted);margin-bottom:20px;border:1px solid var(--border);border-radius:10px;padding:10px 12px;">載入中…</div>

            <div style="font-weight:700;font-size:13.5px;margin-bottom:10px;">逆變器型號</div>
            <div style="display:flex;gap:8px;margin-bottom:10px;">
              <input type="text" class="quick-mark-input" id="newInverterModelInput" placeholder="輸入新的逆變器型號" style="flex:1;">
              <button class="btn btn-primary" onclick="addNewInverterModel()">＋ 新增</button>
            </div>
            <div id="inverterModelListArea" style="max-height:140px;overflow-y:auto;font-size:12.5px;color:var(--text-muted);border:1px solid var(--border);border-radius:10px;padding:10px 12px;">載入中…</div>

            <div style="font-weight:700;font-size:13.5px;margin:20px 0 10px;">已隱藏的型號</div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:10px;">被隱藏的型號不會出現在「填寫規格」的下拉選單中,但不會動到 Airtable 裡任何舊案件已經填過的資料,隨時可以按「恢復」找回來。</div>
            <div id="hiddenModelListArea" style="max-height:160px;overflow-y:auto;font-size:12.5px;color:var(--text-muted);border:1px solid var(--border);border-radius:10px;padding:10px 12px;">載入中…</div>
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
                <th>廠商</th>
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
              <input type="checkbox" id="materialUseRemoveOriginal">
              從「未使用料件」清單移除這筆
            </label>
            <div style="font-size:11px;color:var(--m-rebar);margin-top:-10px;margin-bottom:18px;">⚠ 勾選後會把上面「原料件內容」整筆刪除（包含模組和逆變器），不會只刪掉這次用到的部分。如果原本的料件只用掉一部分（例如模組用了 25 片、還剩 4 片，或逆變器完全沒用到），請不要勾選，改成到「未使用料件」清單裡自己把內容改成剩餘數量。</div>
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
            <div class="legend-item"><span style="color:#D64545;font-weight:700;">●</span>國定假日</div>
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

const VENDOR_CLASS = {
  '三創':'vendor-sc','尚展':'vendor-sz','曙光':'vendor-sg','光鼎':'vendor-gd',
  '宇陽達':'vendor-yyd','聚曜':'vendor-jy','澄品':'vendor-cp','大昇':'vendor-ds',
  '展亦':'vendor-zy','凰太竹':'vendor-htz','國欽':'vendor-gq','振庭':'vendor-zt',
};

let PENDING_CASES = [];
let ENTRY_CASES = [];
let COMPLETED_CASES = [];
let pendingSortKey = 'case';
let pendingSortAsc = true;

// ===================================================================
// 廠商篩選（2026-08-31 改成全站共用單一設定）：原本每個頁面／頁籤各自有一份
// 篩選狀態，使用者要在每個分頁重新勾選一次很麻煩。現在改成只有一份
// GLOBAL_VENDOR_SCOPE，存在瀏覽器 localStorage，右上角「🏭 廠商」按鈕勾選
// 完，待安排出貨&植筋／案件進場安排／掛表安排／異常案件／撤案清單／
// 歷史紀錄／排程日曆／近一週安排，全部同步套用同一份篩選結果。
// Set 是空的代表「沒有篩選、全部廠商都顯示」；非空則只顯示 Set 裡有的廠商。
// ===================================================================
const ALL_VENDOR_NAMES = ['三創','尚展','曙光','光鼎','宇陽達','聚曜','澄品','大昇','展亦','凰太竹','國欽','振庭'];
const GLOBAL_VENDOR_SCOPE_STORAGE_KEY = 'epc_global_vendor_scope';

function loadGlobalVendorScope(){
  try{
    const raw = localStorage.getItem(GLOBAL_VENDOR_SCOPE_STORAGE_KEY);
    if(!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr.filter(v => ALL_VENDOR_NAMES.includes(v)) : []);
  }catch(e){
    return new Set();
  }
}
function saveGlobalVendorScope(){
  try{
    localStorage.setItem(GLOBAL_VENDOR_SCOPE_STORAGE_KEY, JSON.stringify(Array.from(GLOBAL_VENDOR_SCOPE)));
  }catch(e){}
}
let GLOBAL_VENDOR_SCOPE = loadGlobalVendorScope();
function matchesGlobalVendorScope(vendor){
  return GLOBAL_VENDOR_SCOPE.size === 0 || GLOBAL_VENDOR_SCOPE.has(vendor);
}

function toggleGlobalVendorDropdown(e){
  e.stopPropagation();
  const dd = document.getElementById('globalVendorDropdown');
  if(!dd) return;
  if(!dd.dataset.built){
    dd.innerHTML = '<div class="vendor-dropdown-item active" data-vendor="all" onclick="toggleGlobalVendorItem(\'all\',event)"><input type="checkbox" class="vendor-checkbox" data-vendor="all" style="margin-right:6px;pointer-events:none;">全部廠商</div>'
      + ALL_VENDOR_NAMES.map(v => `<div class="vendor-dropdown-item" data-vendor="${v}" onclick="toggleGlobalVendorItem('${v}',event)"><input type="checkbox" class="vendor-checkbox" data-vendor="${v}" style="margin-right:6px;pointer-events:none;">${v}</div>`).join('');
    dd.dataset.built = '1';
    updateGlobalVendorUI();
  }
  dd.classList.toggle('show');
}
// 勾選/取消勾選其中一個廠商（複選，不會關閉下拉選單，方便一次勾多個）；
// 點「全部廠商」等於清空選取，回到「不篩選」狀態。選取變動後，所有頁面／
// 頁籤全部重新畫一次，確保同步反映最新篩選結果。
function toggleGlobalVendorItem(vendor, e){
  if(e) e.stopPropagation();
  if(vendor === 'all'){
    GLOBAL_VENDOR_SCOPE.clear();
  } else {
    if(GLOBAL_VENDOR_SCOPE.has(vendor)) GLOBAL_VENDOR_SCOPE.delete(vendor); else GLOBAL_VENDOR_SCOPE.add(vendor);
  }
  saveGlobalVendorScope();
  updateGlobalVendorUI();
  refreshAllVendorFilteredViews();
}
function updateGlobalVendorUI(){
  const dd = document.getElementById('globalVendorDropdown');
  if(dd){
    dd.querySelectorAll('.vendor-checkbox').forEach(cb => {
      const v = cb.dataset.vendor;
      cb.checked = v === 'all' ? GLOBAL_VENDOR_SCOPE.size === 0 : GLOBAL_VENDOR_SCOPE.has(v);
    });
    dd.querySelectorAll('.vendor-dropdown-item').forEach(item => {
      const v = item.dataset.vendor;
      const checked = v === 'all' ? GLOBAL_VENDOR_SCOPE.size === 0 : GLOBAL_VENDOR_SCOPE.has(v);
      item.classList.toggle('active', checked);
    });
  }
  const label = document.getElementById('globalVendorFilterLabel');
  if(label) label.textContent = GLOBAL_VENDOR_SCOPE.size === 0 ? '' : '（' + Array.from(GLOBAL_VENDOR_SCOPE).join('、') + '）';
}
// 點選單以外的地方，下拉勾選框收起來
document.addEventListener('click', function(){
  const dd = document.getElementById('globalVendorDropdown');
  if(dd) dd.classList.remove('show');
});
// 篩選條件變動後，把目前畫面上會用到廠商篩選的所有地方都重新畫一次；
// 用 typeof 檢查是因為這幾個 render 函式定義在檔案後段，開機時（呼叫
// updateGlobalVendorUI 那次）它們可能都還沒定義好。
function refreshAllVendorFilteredViews(){
  if(typeof renderPendingTable === 'function') renderPendingTable();
  if(typeof renderEntryTable === 'function') renderEntryTable();
  if(typeof renderMeterTable === 'function') renderMeterTable();
  if(typeof renderIssueTable === 'function') renderIssueTable();
  if(typeof renderArchiveTable === 'function') renderArchiveTable();
  if(typeof renderWithdrawnTable === 'function') renderWithdrawnTable();
  if(typeof renderCalendar === 'function') renderCalendar();
  if(typeof renderWeekList === 'function') renderWeekList();
}

// ===================================================================
// 台灣國定假日（2026-08-30 新增，2026-08-31 依行政院人事行政總處官方公告
// 全面查證更新）：直接查證行政院人事行政總處公告的 115年（2026年）「附表3」
// ／116年（2027年）政府行政機關辦公日曆表，把先前漏掉的補假日（和平紀念日、
// 兒童節、清明節、國慶日、台灣光復節、勞動節、行憲紀念日這幾個逢週六／週日
// 需要補假的情況）一次補齊，之後年度需要時要記得同樣去查官方公告，不要用
// 「推算」的（很容易漏算補假規則：逢六補前一天，逢日補後一天）。
// ===================================================================
const TW_HOLIDAYS = {
  // ---- 2026 年（115年）----
  '2026-01-01': '元旦',
  '2026-02-15': '小年夜',
  '2026-02-16': '除夕',
  '2026-02-17': '春節',
  '2026-02-18': '春節',
  '2026-02-19': '春節',
  '2026-02-20': '小年夜補假',
  '2026-02-27': '和平紀念日補假',  // 2/28 適逢週六，於前一日 2/27（五）補假
  '2026-02-28': '和平紀念日',
  '2026-04-03': '兒童節補假',      // 4/4 適逢週六，於前一日 4/3（五）補假
  '2026-04-04': '兒童節',
  '2026-04-05': '清明節',
  '2026-04-06': '清明節補假',      // 4/5 適逢週日，於次一日 4/6（一）補假
  '2026-05-01': '勞動節',
  '2026-06-19': '端午節',
  '2026-09-25': '中秋節',
  '2026-09-28': '教師節',
  '2026-10-09': '國慶日補假',      // 10/10 適逢週六，於前一日 10/9（五）補假
  '2026-10-10': '國慶日',
  '2026-10-25': '台灣光復節',
  '2026-10-26': '台灣光復節補假',  // 10/25 適逢週日，於次一日 10/26（一）補假
  '2026-12-25': '行憲紀念日',
  // ---- 2027 年（116年）----
  '2027-01-01': '元旦',
  '2027-02-04': '小年夜',
  '2027-02-05': '除夕',
  '2027-02-06': '春節',
  '2027-02-07': '春節',
  '2027-02-08': '春節',
  '2027-02-09': '春節補假',
  '2027-02-10': '春節補假',
  '2027-02-28': '和平紀念日',
  '2027-03-01': '和平紀念日補假',  // 2/28 適逢週日，於次一日 3/1（一）補假
  '2027-04-04': '兒童節',
  '2027-04-05': '清明節',
  '2027-04-06': '兒童節補假',      // 4/4 適逢週日，於清明節次日 4/6（二）補假
  '2027-04-30': '勞動節補假',      // 5/1 適逢週六，於前一日 4/30（五）補假
  '2027-05-01': '勞動節',
  '2027-06-09': '端午節',
  '2027-09-15': '中秋節',
  '2027-09-28': '教師節',
  '2027-10-10': '國慶日',
  '2027-10-11': '國慶日補假',      // 10/10 適逢週日，於次一日 10/11（一）補假
  '2027-10-25': '台灣光復節',
  '2027-12-24': '行憲紀念日補假',  // 12/25 適逢週六，於前一日 12/24（五）補假
  '2027-12-25': '行憲紀念日',
  '2027-12-31': '元旦補假',        // 117年(2028)1/1 適逢週六，於前一日 12/31（五）補假
};

// ===================================================================
// 連假偵測（2026-08-31 新增）：把「週六、週日、國定假日」視為休息日，找出
// 3 天以上連續的休息日區間，日曆上會在整段區間淡淡標色，並在第一天顯示
// 「🎉共N天連假」。只計算實際的國定假日／週末，不含使用者自行請假延長的部分。
// ===================================================================
function computeConsecutiveOffRanges(startDateStr, endDateStr){
  const isOff = (ds) => {
    const dow = new Date(ds + 'T00:00:00').getDay();
    return dow === 0 || dow === 6 || !!TW_HOLIDAYS[ds];
  };
  const ranges = [];
  let cur = new Date(startDateStr + 'T00:00:00');
  const end = new Date(endDateStr + 'T00:00:00');
  let runStart = null;
  while(cur <= end){
    const ds = fmtISODate(cur.getFullYear(), cur.getMonth(), cur.getDate());
    if(isOff(ds)){
      if(!runStart) runStart = ds;
    } else if(runStart){
      const prev = new Date(cur);
      prev.setDate(prev.getDate() - 1);
      ranges.push({start: runStart, end: fmtISODate(prev.getFullYear(), prev.getMonth(), prev.getDate())});
      runStart = null;
    }
    cur.setDate(cur.getDate() + 1);
  }
  if(runStart){
    ranges.push({start: runStart, end: fmtISODate(end.getFullYear(), end.getMonth(), end.getDate())});
  }
  return ranges
    .map(r => ({...r, days: Math.round((new Date(r.end + 'T00:00:00') - new Date(r.start + 'T00:00:00')) / 86400000) + 1}))
    .filter(r => r.days >= 3);
}
// 開機時算好整段範圍（涵蓋目前收錄的 2026～2027），之後查詢直接查表，不用每次重算。
const HOLIDAY_RANGES = computeConsecutiveOffRanges('2026-01-01', '2027-12-31');
function getHolidayRangeForDate(dateStr){
  return HOLIDAY_RANGES.find(r => dateStr >= r.start && dateStr <= r.end) || null;
}

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
  document.getElementById('completeMeterModalOverlay').classList.add('show');
}
function closeCompleteMeterModal(){
  document.getElementById('completeMeterModalOverlay').classList.remove('show');
}
async function confirmCompleteMeter(){
  const completedVal = document.getElementById('completeMeterCompletedDate').value;
  if(!completedVal){ showToast('請選擇完工日期'); return; }
  const recordId = completeMeterTargetRecordId;
  const found = COMPLETED_CASES.find(c => c.record_id === recordId);
  const cs = getCaseStatus(recordId);
  const caseNo = (found && found.case) || (cs && cs.case_no) || '';
  const btn = document.querySelector('#completeMeterModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    await saveCaseStatusField(recordId, caseNo, {completed_date: completedVal});
    closeCompleteMeterModal();
    renderEntryTable();
    renderMeterTable();
    showToast('已記錄完工日期，移入「掛表安排」');
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
  if(cs && cs.completed_date) return '掛表安排';
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
      sales_person: (found && found.sales_person) || '',
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
      <td><div class="case-id">${it.case}</div><div class="case-alias">${it.alias||''}</div>${salesLineHtml(it.sales_person)}</td>
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
// 2026-08-31 新增：在案號／別名下方顯示這筆案件的負責業務（綠點業務），
// 所有案件列表（待安排出貨&植筋／案件進場安排／掛表安排／異常案件／
// 撤案清單／歷史紀錄）共用同一個小函式，樣式統一。沒有業務資料（例如
// Airtable 那邊「綠點業務」欄位還沒設定，或這筆案件沒填）就不顯示這行。
function salesLineHtml(salesPerson){
  return salesPerson ? `<div class="case-alias" style="color:var(--primary-dark);">業務：${salesPerson}</div>` : '';
}
// 2026-09-01 新增：如果這個案件曾經在「料件使用清單」（未使用料件的挪用紀錄）
// 裡出現過（也就是這個案場用的模組/逆變器不是全新出貨，而是挪用其他撤案案件
// 剩下的料件），在案號下方額外顯示一行提醒，方便一眼看出這個案場的料件來源
// 不是原本規劃的出貨，避免誤會/漏看。比對方式是用案號字串完全相符
// APP_NOTES 裡類型是「料件使用」的「使用於案號/案場」欄位。
function materialReuseNoteHtml(caseNo){
  if(!caseNo || !APP_NOTES) return '';
  const matches = APP_NOTES.filter(n => n.type === '料件使用' && n.case_text === caseNo);
  if(matches.length === 0) return '';
  return matches.map(n =>
    `<div class="case-alias" style="color:var(--m-rebar);">♻️ ${n.content}</div>`
  ).join('');
}
// 2026-08-31 新增：「屋主資訊」小按鈕，點下去開啟既有的屋主資訊視窗
// （openOwnerInfoModal，跟「案件進場安排」共用同一套資料，寫在 APP資料 表的
// owner_contact_* 欄位）。已經填過的話直接顯示聯絡人／電話，方便一眼看到，
// 不用點進去才知道有沒有資料；「待安排出貨&植筋」「掛表安排」都可以用這個
// 按鈕先填/查看，不用等到案件進場安排階段才能填。
function ownerInfoButtonHtml(recordId){
  const cs = getCaseStatus(recordId);
  const hasContact = cs && (cs.owner_contact_name || cs.owner_contact_phone || cs.owner_contact_note);
  let label;
  if(hasContact){
    const parts = [cs.owner_contact_name, cs.owner_contact_phone].filter(Boolean);
    label = parts.length ? parts.join('　') : '已填寫備註';
  } else {
    label = '尚未填寫';
  }
  return `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openOwnerInfoModal('${recordId}')">🏠 ${label}</button>`;
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
    renderNotebookOnlineList();
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
// ---- 填寫模組／逆變器規格（直接寫回 Airtable「專案細節」表）----
let INVERTER_OPTIONS = null;
async function loadInverterOptionsIfNeeded(force){
  if(INVERTER_OPTIONS && !force){
    renderInverterDatalist();
    return INVERTER_OPTIONS;
  }
  try{
    const res = await fetch(API_BASE + '/api/inverter-options', {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    INVERTER_OPTIONS = data.options || [];
  }catch(err){
    INVERTER_OPTIONS = INVERTER_OPTIONS || [];
    showToast('讀取逆變器型號清單失敗：' + err.message);
  }
  renderInverterDatalist();
  return INVERTER_OPTIONS;
}
// 逆變器輸入框改用 <input list="..."> 搭配 <datalist>，讓使用者可以打字篩選、
// 但選出來的值仍必須完全對應清單裡的一個名稱，才會被視為有效選擇（見
// addCaseSpecInverterRow 裡 input 的 change 事件，用完整比對名稱找回 record_id；
// 找不到就代表使用者亂打字，儲存時會被擋下來）。每次型號清單重新整理都要
// 同步刷新這份 datalist，不然使用者打字時看到的建議會是舊清單。
function renderInverterDatalist(){
  const dl = document.getElementById('inverterOptionsDatalist');
  if(!dl) return;
  dl.innerHTML = (INVERTER_OPTIONS || []).map(o => {
    const escaped = (o.name || '').replace(/"/g, '&quot;');
    return `<option value="${escaped}"></option>`;
  }).join('');
}
// 模組型號是 Single select 固定選項欄位；如果後端讀不到（例如 Token 沒有
// schema.bases:read 權限），moduleOptionsAvailable 會是 false，改用一般文字輸入框，
// 不會整個卡住讓使用者填不了規格。
let MODULE_OPTIONS = null;
let moduleOptionsAvailable = true;
async function loadModuleOptionsIfNeeded(force){
  if(MODULE_OPTIONS && !force) return MODULE_OPTIONS;
  try{
    const res = await fetch(API_BASE + '/api/module-options', {cache: 'no-store'});
    const data = await res.json();
    if(!res.ok || data.error || !Array.isArray(data.options)){
      moduleOptionsAvailable = false;
      MODULE_OPTIONS = [];
    } else {
      moduleOptionsAvailable = true;
      MODULE_OPTIONS = data.options;
    }
  }catch(err){
    moduleOptionsAvailable = false;
    MODULE_OPTIONS = MODULE_OPTIONS || [];
  }
  return MODULE_OPTIONS;
}
let caseSpecTargetRecordId = null;
async function openCaseSpecModal(recordId){
  caseSpecTargetRecordId = recordId;
  const found = findCaseAnywhere(recordId);
  document.getElementById('caseSpecCaseTitle').textContent = (found && found.case) || '—';
  document.getElementById('caseSpecCaseAddr').textContent = found ? (found.address + '　' + found.vendor) : '';

  // 既有模組字串格式是「型號 ×數量」，解析回結構化欄位方便編輯
  let moduleModel = '', moduleQty = '';
  if(found && found.module){
    const m = found.module.match(/^(.*)\s×([\d.]+)\s*$/);
    if(m){ moduleModel = m[1]; moduleQty = m[2]; } else { moduleModel = found.module; }
  }
  document.getElementById('caseSpecModuleQty').value = moduleQty;

  // 兩份選項清單改成同時抓，不用一個做完才做下一個，可以省掉不少等待時間；
  // 而且這兩份資料在頁面載入時就已經在背景偷偷預先抓好一次了，正常情況下這裡
  // 幾乎是秒開（除非使用者真的是頁面才剛打開沒幾秒就立刻點開這個視窗）。
  await Promise.all([loadModuleOptionsIfNeeded(), loadInverterOptionsIfNeeded()]);
  const moduleSelect = document.getElementById('caseSpecModuleModel');
  const moduleText = document.getElementById('caseSpecModuleModelText');
  if(moduleOptionsAvailable){
    const opts = [...MODULE_OPTIONS];
    if(moduleModel && !opts.includes(moduleModel)) opts.unshift(moduleModel); // 保留舊資料，即使不在目前選項清單裡
    moduleSelect.innerHTML = '<option value="">— 選擇模組型號 —</option>' +
      opts.map(o => `<option value="${o}"${o === moduleModel ? ' selected' : ''}>${o}</option>`).join('');
    moduleSelect.style.display = '';
    moduleText.style.display = 'none';
  } else {
    moduleSelect.style.display = 'none';
    moduleText.style.display = '';
    moduleText.value = moduleModel;
  }

  const container = document.getElementById('caseSpecInverterRows');
  container.innerHTML = '';
  // 案件的逆變器欄位背後是「一筆記錄＝一顆實體逆變器」，同型號的多顆逆變器
  // 會是好幾筆各自 ×1 的獨立記錄，字串上會顯示成「CPSPV6600ETL1 ×1、
  // CPSPV6600ETL1 ×1」這種重複型號的樣子。這裡把同名的加總成一行、一個總數量，
  // 這樣使用者看到的、也是儲存時會送出的，都是「型號＋這個型號總共幾顆」，
  // 不用逐筆對照。
  const existingInvertersMap = {};
  if(found && found.inverter){
    found.inverter.split('、').forEach(seg => {
      const m = seg.match(/^(.*)\s×([\d.]+)\s*$/);
      let name, q;
      if(m){ name = m[1].trim(); q = Number(m[2]); }
      else if(seg.trim()){ name = seg.trim(); q = 1; }
      if(name) existingInvertersMap[name] = (existingInvertersMap[name] || 0) + (isNaN(q) ? 1 : q);
    });
  }
  const existingInverterNames = Object.keys(existingInvertersMap);
  if(existingInverterNames.length === 0){
    addCaseSpecInverterRow();
  } else {
    existingInverterNames.forEach(name => {
      addCaseSpecInverterRow(name, existingInvertersMap[name]);
    });
  }

  document.getElementById('caseSpecModalOverlay').classList.add('show');
}
function closeCaseSpecModal(){
  document.getElementById('caseSpecModalOverlay').classList.remove('show');
}
function addCaseSpecInverterRow(existingName, qty){
  const container = document.getElementById('caseSpecInverterRows');
  const row = document.createElement('div');
  row.className = 'case-spec-inverter-row';
  row.style.cssText = 'display:flex;gap:8px;align-items:center;';
  const escapedName = (existingName || '').replace(/"/g, '&quot;');
  row.innerHTML = `
    <input type="text" class="quick-mark-input inverter-input" list="inverterOptionsDatalist" value="${escapedName}" placeholder="輸入關鍵字篩選逆變器型號">
    <input type="number" class="quick-mark-input inverter-qty" style="width:90px;" min="1" value="${qty || 1}" placeholder="數量">
    <button class="btn btn-ghost" style="padding:6px 10px;" onclick="this.closest('.case-spec-inverter-row').remove()">✕</button>
  `;
  container.appendChild(row);
}
async function confirmCaseSpec(){
  const moduleModel = moduleOptionsAvailable
    ? document.getElementById('caseSpecModuleModel').value.trim()
    : document.getElementById('caseSpecModuleModelText').value.trim();
  // 「片數」欄位在 Airtable 是計算欄位（依系統容量自動換算），外部無法寫入，
  // 這裡不讀也不送這個值。逆變器則是送「型號＋這個型號總共要幾顆」，實際
  // 建立/比對記錄的邏輯交給後端 sync_inverter_units_for_case() 處理。
  const rows = document.querySelectorAll('#caseSpecInverterRows .case-spec-inverter-row');
  const knownInverterNames = new Set((INVERTER_OPTIONS || []).map(o => o.name));
  const combined = {};
  let hasInvalidInverter = false;
  rows.forEach(row => {
    const input = row.querySelector('.inverter-input');
    const qtyInput = row.querySelector('.inverter-qty');
    const name = input.value.trim();
    if(!name) return; // 這一列沒填，略過
    if(!knownInverterNames.has(name)){
      hasInvalidInverter = true; // 打的文字沒有對應到清單裡任何一筆，視為不合法
      return;
    }
    const qty = qtyInput.value ? Number(qtyInput.value) : 1;
    if(qty < 1) return;
    // 同一個型號如果被分成好幾列填寫，加總成一個數字再送出，避免後端重複比對。
    combined[name] = (combined[name] || 0) + qty;
  });
  if(hasInvalidInverter){
    showToast('有逆變器型號的輸入內容不在現有清單中，請從輸入時跳出的建議選項裡點選一個');
    return;
  }
  const inverters = Object.keys(combined).map(name => ({name, qty: combined[name]}));
  const btn = document.querySelector('#caseSpecModalOverlay .btn-primary');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    const res = await fetch(API_BASE + '/api/case-spec', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        case_record_id: caseSpecTargetRecordId,
        module_model: moduleModel,
        inverters,
      }),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    closeCaseSpecModal();
    showToast('已寫入 Airtable,規格更新完成');
    await pollForCacheUpdate();
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.textContent = originalText;
    btn.disabled = false;
  }
}

// ---- 管理模組／逆變器型號清單 ----
async function openModelManageModal(){
  document.getElementById('modelManageModalOverlay').classList.add('show');
  await renderModelManageLists();
}
function closeModelManageModal(){
  document.getElementById('modelManageModalOverlay').classList.remove('show');
}
async function renderModelManageLists(){
  const moduleArea = document.getElementById('moduleModelListArea');
  const inverterArea = document.getElementById('inverterModelListArea');
  moduleArea.textContent = '載入中…';
  inverterArea.textContent = '載入中…';

  await loadModuleOptionsIfNeeded(true);
  if(!moduleOptionsAvailable){
    moduleArea.innerHTML = '目前無法讀取模組型號選項（後端 Airtable Token 可能沒有 schema 讀取權限），暫時只能用文字輸入,無法在此新增。';
  } else if(MODULE_OPTIONS.length === 0){
    moduleArea.textContent = '目前沒有任何模組型號選項。';
  } else {
    moduleArea.innerHTML = MODULE_OPTIONS.map(o => {
      const escaped = o.replace(/'/g, "\\'").replace(/"/g, '&quot;');
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;gap:8px;">
        <span>${o}</span>
        <button class="btn btn-ghost" style="padding:2px 8px;font-size:11px;flex-shrink:0;" onclick="hideModuleModel('${escaped}')">隱藏</button>
      </div>`;
    }).join('');
  }

  await loadInverterOptionsIfNeeded(true);
  if((INVERTER_OPTIONS || []).length === 0){
    inverterArea.textContent = '目前沒有任何逆變器型號選項。';
  } else {
    inverterArea.innerHTML = INVERTER_OPTIONS.map(o => {
      const escapedName = (o.name || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
      return `<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;gap:8px;">
        <span>${o.name}</span>
        <button class="btn btn-ghost" style="padding:2px 8px;font-size:11px;flex-shrink:0;" onclick="hideInverterModel('${o.record_id}','${escapedName}')">隱藏</button>
      </div>`;
    }).join('');
  }

  await renderHiddenModelsList();
}

// ---- 隱藏型號清單（軟隱藏，不動 Airtable 原始資料，寫在 APP資料 表）----
async function renderHiddenModelsList(){
  const area = document.getElementById('hiddenModelListArea');
  if(!area) return;
  area.textContent = '載入中…';
  try{
    const res = await fetch(API_BASE + '/api/hidden-models', {cache: 'no-store'});
    if(!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    const list = data.hidden || [];
    if(list.length === 0){
      area.textContent = '目前沒有隱藏任何型號。';
      return;
    }
    area.innerHTML = list.map(h => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:3px 0;gap:8px;">
        <span>${h.name}<span style="color:var(--text-muted);">（${h.category === 'module' ? '模組' : '逆變器'}）</span></span>
        <button class="btn btn-ghost" style="padding:2px 8px;font-size:11px;flex-shrink:0;" onclick="unhideModel('${h.app_record_id}')">恢復</button>
      </div>
    `).join('');
  }catch(err){
    area.textContent = '讀取隱藏清單失敗：' + err.message;
    console.error(err);
  }
}
async function hideModuleModel(name){
  try{
    const res = await fetch(API_BASE + '/api/hidden-models', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: 'module', value: name}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    showToast('已隱藏「' + name + '」，不會再出現在填寫規格的選單中');
    await renderModelManageLists();
  }catch(err){
    showToast('隱藏失敗：' + err.message);
    console.error(err);
  }
}
async function hideInverterModel(recordId, name){
  try{
    const res = await fetch(API_BASE + '/api/hidden-models', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({category: 'inverter', value: recordId + '::' + name}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    showToast('已隱藏「' + name + '」，不會再出現在填寫規格的選單中');
    await renderModelManageLists();
  }catch(err){
    showToast('隱藏失敗：' + err.message);
    console.error(err);
  }
}
async function unhideModel(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/hidden-models/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    showToast('已恢復顯示');
    await renderModelManageLists();
  }catch(err){
    showToast('恢復失敗：' + err.message);
    console.error(err);
  }
}
async function addNewModuleModel(){
  const input = document.getElementById('newModuleModelInput');
  const name = input.value.trim();
  if(!name){ showToast('請輸入型號名稱'); return; }
  try{
    const res = await fetch(API_BASE + '/api/module-options', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    input.value = '';
    showToast('已新增模組型號');
    await renderModelManageLists();
  }catch(err){
    showToast('新增失敗：' + err.message);
    console.error(err);
  }
}
async function addNewInverterModel(){
  const input = document.getElementById('newInverterModelInput');
  const name = input.value.trim();
  if(!name){ showToast('請輸入型號名稱'); return; }
  try{
    const res = await fetch(API_BASE + '/api/inverter-options', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    input.value = '';
    showToast('已新增逆變器型號');
    await renderModelManageLists();
  }catch(err){
    showToast('新增失敗：' + err.message);
    console.error(err);
  }
}
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
  // pollForCacheUpdate 只會刷新出貨/進場/已進場這三份（Airtable 案件池快取）；
  // 這裡另外一併刷新「APP資料」（屋主資訊/植筋/撤案/未使用料件…）跟「異常案件」
  // 裡每一筆「待取得函文」的最新進度，讓「手動更新」真的是一次更新到底，
  // 不用你自己再跑去異常案件分頁另外重查。
  await loadAppData();
  recheckAllDocStatus();
  showToast(ok ? '已更新完成' : '更新時間較長,請稍後再檢查一次');
  btn.disabled = false;
  btn.textContent = '🔄 手動更新';
}
function recheckAllDocStatus(){
  Object.keys(APP_CASE_STATUS).forEach(id => {
    const cs = APP_CASE_STATUS[id];
    if(cs.issue_note && !cs.withdrawn_note && cs.waiting_doc_type){
      delete docStatusCache[id];
      checkDocStatus(id, cs.waiting_doc_type);
    }
  });
}

function renderPendingTable(){
  const q = document.getElementById('pendingSearchInput').value.trim();
  let rows = PENDING_CASES.filter(r => {
    if(!matchesGlobalVendorScope(r.vendor)) return false;
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
      ? `<td>${r.module}<button class="btn btn-ghost" style="padding:1px 6px;font-size:10px;margin-left:4px;" onclick="openCaseSpecModal('${r.record_id}')">✎</button></td><td>${r.inverter || ''}</td>`
      : `<td colspan="2"><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;background:var(--epc-soft);color:var(--epc);border-color:transparent;" onclick="openCaseSpecModal('${r.record_id}')">⚠ 尚未填寫規格,點此填寫</button></td>`;
    const cs = getCaseStatus(r.record_id);
    const triggerPill = (cs && cs.waiting_doc_type && cs.waiting_doc_date)
      ? `<span class="pm-pill" style="background:var(--m-rebar-soft);color:var(--m-rebar);">${cs.waiting_doc_type} ${fmtDate(cs.waiting_doc_date)}</span>`
      : `<span class="pm-pill" style="background:var(--success-soft);color:var(--success);">同意備案 ${r.agree}</span>`;
    return `
      <tr data-record-id="${r.record_id}" data-ship-milestone-id="${r.ship_milestone_record_id || ''}" data-case="${r.case}" data-alias="${r.alias||''}" data-vendor="${r.vendor}" data-vendorclass="${r.vendorClass}" data-addr="${r.address}" data-module="${hasSpec ? r.module : '尚未填寫規格'}" data-inverter="${hasSpec ? (r.inverter||'') : ''}">
        <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div>${salesLineHtml(r.sales_person)}${materialReuseNoteHtml(r.case)}</td>
        <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
        <td>${r.address}
          <div style="margin-top:4px;">${ownerInfoButtonHtml(r.record_id)}</div>
        </td>
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
      return !(cs && cs.completed_date) && !(cs && cs.issue_note);
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
      statusPill = `<span class="pm-pill" style="background:var(--success-soft);color:var(--success);">已安排</span>`;
    }
    const actions = r._status === 'waiting'
      ? `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openScheduleModal(this,'reschedule')">重新安排出貨日期</button>
         <button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;margin-left:6px;" onclick="openEntryModal(this)">排定進場日期</button>${renderRebarBadge(r.record_id)}`
      : `<button class="btn btn-ghost" style="padding:6px 12px;font-size:12px;" onclick="openEntryModal(this,'reschedule')">重新安排進場日期</button>
         <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;margin-left:6px;" onclick="openCompleteMeterModal('${r.record_id}')">✓ 完工</button>`;
    return `
    <tr data-record-id="${r.record_id}" data-ship-milestone-id="${r.ship_milestone_record_id || ''}" data-entry-milestone-id="${r.entry_milestone_record_id || ''}" data-case="${r.case}" data-alias="${r.alias||''}" data-vendor="${r.vendor}" data-vendorclass="${r.vendorClass}" data-addr="${r.address}" data-module="${r.module||''}" data-inverter="${r.inverter||''}" data-shipdate="${fmtDate(r.ship_date)}" data-shipdatefull="${r.ship_date||''}" data-entrydatefull="${r.entry_date||''}">
      <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div>${salesLineHtml(r.sales_person)}${materialReuseNoteHtml(r.case)}</td>
      <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
      <td>${r.address}
        <div style="margin-top:4px;">${ownerInfoButtonHtml(r.record_id)}</div>
      </td>
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
  const waitingTbody = document.getElementById('meterWaitingRows');
  if(!tbody && !waitingTbody) return;
  const baseRows = COMPLETED_CASES.filter(r => {
    const cs = getCaseStatus(r.record_id);
    return cs && cs.completed_date && !cs.meter_confirmed && !cs.issue_note;
  });
  // 2026-08-31 新增：完工不代表可以掛表，還要「細部協商」跟「台電購售契約」
  // 這兩份函文都確認取得（都有實際日期）才算真的能排掛表。兩份都到齊的
  // 進「待安排掛表」，還缺其中一份（或兩份都缺）的進「待函文取得」。
  // 預計掛表日期不再是進入這個頁籤的門檻，改成進到「待安排掛表」之後才安排。
  const readyRows = baseRows.filter(r => r.detail_nego_date && r.contract_date);
  const waitingRows = baseRows.filter(r => !(r.detail_nego_date && r.contract_date));

  const readyCountTag = document.getElementById('meterReadyCountTag');
  if(readyCountTag) readyCountTag.textContent = '共 ' + readyRows.length + ' 筆';
  const waitingCountTag = document.getElementById('meterWaitingCountTag');
  if(waitingCountTag) waitingCountTag.textContent = '共 ' + waitingRows.length + ' 筆';

  // ---- 待安排掛表（沿用既有的搜尋／排序）----
  if(tbody){
    if(readyRows.length === 0){
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有可以安排掛表的案件——細部協商跟台電購售契約都取得後，案件會自動從下方「待函文取得」移過來</td></tr>';
    } else {
      let rows = applyTableFilterSort('meter', readyRows);
      if(!TABLE_STATE.meter.sortKey){
        rows.sort((a,b) => {
          const ca = getCaseStatus(a.record_id), cb = getCaseStatus(b.record_id);
          return (ca.meter_planned_date||'').localeCompare(cb.meter_planned_date||'');
        });
      }
      if(rows.length === 0){
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px 0;">沒有符合篩選條件的案件</td></tr>';
      } else {
        tbody.innerHTML = rows.map(r => {
          const cs = getCaseStatus(r.record_id);
          const plannedLabel = cs.meter_planned_date ? fmtDate(cs.meter_planned_date) : '尚未安排';
          const negoHtml = r.detail_nego_date
            ? `<span style="color:var(--success);font-weight:600;">✓ ${fmtDate(r.detail_nego_date)}</span>`
            : `<span style="color:var(--m-rebar);">尚未取得</span>`;
          const contractHtml = r.contract_date
            ? `<span style="color:var(--success);font-weight:600;">✓ ${fmtDate(r.contract_date)}</span>`
            : `<span style="color:var(--m-rebar);">尚未取得</span>`;
          return `
          <tr>
            <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div>${salesLineHtml(r.sales_person)}${materialReuseNoteHtml(r.case)}</td>
            <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
            <td>${r.address}
              <div style="margin-top:4px;">${ownerInfoButtonHtml(r.record_id)}</div>
            </td>
            <td>${r.module ? `<div>${glueCount(r.module)}</div>${r.inverter ? `<div style="margin-top:2px;">${glueCount(r.inverter)}</div>` : ''}` : '<span style="color:var(--text-muted);font-size:12px;">尚未填寫規格</span>'}</td>
            <td>${negoHtml}</td>
            <td>${contractHtml}</td>
            <td><button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="openPlanMeterModal('${r.record_id}')">${plannedLabel}　✎</button></td>
            <td>
              <button class="btn btn-primary" style="padding:6px 12px;font-size:12px;" onclick="openMeterModal('${r.record_id}')">完成掛表</button>
            </td>
          </tr>
        `;
        }).join('');
      }
    }
  }

  // ---- 待函文取得（顯示細部協商／台電購售契約目前的狀態）----
  if(waitingTbody){
    if(waitingRows.length === 0){
      waitingTbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:30px 0;">目前沒有等待函文的案件</td></tr>';
    } else {
      const sorted = [...waitingRows].sort((a,b) => (a.case||'').localeCompare(b.case||'', 'zh-Hant'));
      waitingTbody.innerHTML = sorted.map(r => {
        const negoHtml = r.detail_nego_date
          ? `<span style="color:var(--success);font-weight:600;">✓ ${fmtDate(r.detail_nego_date)}</span>`
          : `<span style="color:var(--m-rebar);">尚未取得</span>`;
        const contractHtml = r.contract_date
          ? `<span style="color:var(--success);font-weight:600;">✓ ${fmtDate(r.contract_date)}</span>`
          : `<span style="color:var(--m-rebar);">尚未取得</span>`;
        return `
        <tr>
          <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div>${salesLineHtml(r.sales_person)}${materialReuseNoteHtml(r.case)}</td>
          <td><span class="vendor-pill ${r.vendorClass}">${r.vendor}</span></td>
          <td>${r.address}
            <div style="margin-top:4px;">${ownerInfoButtonHtml(r.record_id)}</div>
          </td>
          <td>${r.module ? `<div>${glueCount(r.module)}</div>${r.inverter ? `<div style="margin-top:2px;">${glueCount(r.inverter)}</div>` : ''}` : '<span style="color:var(--text-muted);font-size:12px;">尚未填寫規格</span>'}</td>
          <td>${negoHtml}</td>
          <td>${contractHtml}</td>
          <td><button class="btn btn-ghost" disabled style="padding:6px 12px;font-size:12px;opacity:.45;cursor:not-allowed;" title="細部協商、台電購售契約還沒有全部取得，暫時無法安排掛表">🔌 掛表安排</button></td>
        </tr>
      `;
      }).join('');
    }
  }
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
      sales_person: (found && found.sales_person) || '',
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
      <td><div class="case-id">${it.case}</div><div class="case-alias">${it.alias||''}</div>${salesLineHtml(it.sales_person)}</td>
      <td>${it.vendor ? `<span class="vendor-pill ${it.vendorClass}">${it.vendor}</span>` : ''}</td>
      <td>${it.address}</td>
      <td><span class="pm-pill">${it.stage}</span></td>
      <td style="max-width:260px;white-space:pre-wrap;">${it.issue_note}</td>
      <td>
        ${it.waiting_doc_type ? `
          <div style="font-size:11.5px;color:var(--text-muted);margin-bottom:2px;">${it.waiting_doc_type}</div>
          <div id="docStatus_${it.id}" style="font-size:12px;">${renderDocStatusHtml(docStatusCache[it.id])}</div>
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
      <td><div class="case-id">${r.case}</div><div class="case-alias">${r.alias||''}</div>${salesLineHtml(r.sales_person)}</td>
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
// ---- 通用表格篩選／排序（案件進場安排／已完工／掛表安排／異常案件／歷史紀錄共用）----
// 廠商篩選已改用最上面的全站共用 GLOBAL_VENDOR_SCOPE，這裡的 TABLE_STATE
// 只保留排序跟關鍵字搜尋兩件事。
const TABLE_STATE = {
  entry:   { sortKey: null, sortAsc: true, q: '' },
  meter:   { sortKey: null, sortAsc: true, q: '' },
  issue:   { sortKey: null, sortAsc: true, q: '' },
  archive: { sortKey: null, sortAsc: true, q: '' },
  withdrawn: { sortKey: null, sortAsc: true, q: '' },
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
function tableSearchInput(tab){
  const input = document.getElementById(tab + 'FilterInput');
  TABLE_STATE[tab].q = input ? input.value.trim() : '';
  TABLE_RENDER_FN[tab]();
}
function applyTableFilterSort(tab, rows){
  const st = TABLE_STATE[tab];
  let out = rows.filter(r => matchesGlobalVendorScope(r.vendor));
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
document.addEventListener('DOMContentLoaded', function(){
  updateGlobalVendorUI(); // 讓右上角「🏭 廠商」按鈕的標籤，一開機就反映上次記住的篩選狀態
  loadPendingCases();
  loadEntryCases();
  loadCompletedCases();
  loadAppData();
  startAutoSync();
  // 提早在背景偷偷把「模組型號」「逆變器型號」這兩份選項清單抓好，
  // 之後使用者點開「填寫規格」視窗時大機率已經是現成的，不用現場等。
  loadModuleOptionsIfNeeded();
  loadInverterOptionsIfNeeded();
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

// ===================================================================
// 記住最後停留的頁面（2026-08-31 新增）：存在瀏覽器 localStorage 裡，重新整理
// 網頁時直接回到原本的頁籤，不用每次都從「總覽」重新點過去。只存在這台電腦，
// 換裝置不會同步（純粹是導覽方便性，跟案件資料無關，不需要跨裝置同步）。
// ===================================================================
const NAV_STATE_STORAGE_KEY = 'epc_nav_state';
function saveNavState(state){
  try{ localStorage.setItem(NAV_STATE_STORAGE_KEY, JSON.stringify(state)); }catch(e){}
}
function loadNavState(){
  try{
    const raw = localStorage.getItem(NAV_STATE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  }catch(e){
    return null;
  }
}

// 2026-09-01 新增：手機版側邊欄開關（漢堡選單）。桌面版寬度下這兩個函式
// 存在也不會有作用（.sidebar 在桌面版本來就一直顯示，CSS 只在
// @media (max-width:860px) 內才會套用滑出效果）。
function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('show');
}
function closeSidebar(){
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('show');
}

function showView(name){
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+name).classList.add('active');
  document.querySelectorAll('.nav-item[data-view]').forEach(n=>n.classList.remove('active'));
  document.querySelector('.nav-item[data-view="'+name+'"]').classList.add('active');
  document.querySelectorAll('.nav-sub-item').forEach(n=>n.classList.remove('active'));
  saveNavState({view: name});
  closeSidebar(); // 手機版選了頁面後，選單自動收起來，桌面版沒有影響
}
// 2026-08-31 新增：側邊選單「PDF 公文更名」「EPC 出貨／進場排程」這兩個
// 有子項目的分類，點一下標題可以摺疊/展開底下的子選單（手風琴效果），
// 同時照舊切換到該分類的頁面。每次點擊單純把目前的顯示狀態反過來，
// 跟目前在哪個頁面無關，操作直覺。
function toggleNavSection(name){
  const sub = document.getElementById('navSub-' + name);
  if(sub) sub.style.display = (sub.style.display === 'none') ? 'flex' : 'none';
  showView(name);
}
function openNotifyModal(){
  const vendorVal = document.getElementById('notifyVendorFilter') ? document.getElementById('notifyVendorFilter').value : 'all';
  const fromVal = document.getElementById('notifyDateFrom').value;
  const toVal = document.getElementById('notifyDateTo').value;
  let cases = ENTRY_CASES;
  if(vendorVal !== 'all') cases = cases.filter(r => r.vendor === vendorVal);
  if(fromVal) cases = cases.filter(r => r.ship_date && r.ship_date >= fromVal);
  if(toVal) cases = cases.filter(r => r.ship_date && r.ship_date <= toVal);

  let text;
  if(ENTRY_CASES.length === 0){
    text = '目前「案件進場安排」還沒有案件。';
  } else if(cases.length === 0){
    text = '這個篩選條件下沒有符合的出貨案件。';
  } else {
    const noteParts = [];
    if(vendorVal !== 'all') noteParts.push('廠商：' + vendorVal);
    if(fromVal || toVal) noteParts.push(`出貨日期 ${fromVal ? fmtDate(fromVal) : '最早'} ～ ${toVal ? fmtDate(toVal) : '最晚'}`);
    const rangeNote = noteParts.length ? `（${noteParts.join('，')}）` : '';
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
  document.getElementById('materialUseRemoveOriginal').checked = false;
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
  if(removeOriginal){
    const ok = confirm(`確定要把「${sourceCaseText}」的這筆未使用料件整筆刪除嗎？\n\n原內容：${(sourceNote && sourceNote.content) || ''}\n\n如果這次只用掉其中一部分（不是全部），請按「取消」，改成不勾選那個選項，這筆記錄才不會被整個刪掉。`);
    if(!ok) return;
  }
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

// ===================================================================
// 筆記本（2026-08-31 新增）：跟廠商電話排行程時可以先隨手記錄下來，之後再
// 回頭安排。分「本地紀錄」（只存在這台電腦的瀏覽器 localStorage，換裝置或
// 清瀏覽器資料就會不見，同事看不到）跟「線上紀錄」（寫回 Airtable「APP資料」
// 表，類型是「電話紀錄」，比照其他註記清單，同事在不同電腦都能同步看到）。
// 本地紀錄可以「上傳」變成線上紀錄，上傳後會從本地清單移除、改存在線上。
// 輸入案號時會呼叫後端 /api/case-lookup 即時查 Airtable，自動帶出案件基本
// 資料（案號／別名／地址／廠商／業務／模組／逆變器）跟關鍵進度日期
// （併聯審查／同意備案／細部協商／台電購售契約／免雜），方便講電話當下
// 快速掌握案件現況，不用切去別的分頁對照。
// ===================================================================
const NOTEBOOK_NOTE_TYPE = '電話紀錄';
const NOTEBOOK_LOCAL_STORAGE_KEY = 'epc_notebook_local';
let notebookActiveTab = 'local';
let notebookEditingLocalId = null;
let notebookEditingOnlineId = null;

function loadLocalNotebook(){
  try{
    const raw = localStorage.getItem(NOTEBOOK_LOCAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  }catch(err){
    console.error('讀取本地筆記本失敗：', err);
    return [];
  }
}
function saveLocalNotebook(list){
  try{
    localStorage.setItem(NOTEBOOK_LOCAL_STORAGE_KEY, JSON.stringify(list));
  }catch(err){
    showToast('本地紀錄儲存失敗（瀏覽器儲存空間可能已滿）：' + err.message);
    console.error(err);
  }
}

function openNotebookModal(){
  document.getElementById('notebookCaseInput').value = '';
  document.getElementById('notebookContentInput').value = '';
  document.getElementById('notebookCaseSummary').style.display = 'none';
  hideNotebookSearchResults();
  notebookSelectedCaseRecordId = null;
  notebookEditingLocalId = null;
  notebookEditingOnlineId = null;
  showNotebookTab('local');
  renderNotebookLocalList();
  renderNotebookOnlineList();
  document.getElementById('notebookModalOverlay').classList.add('show');
}
function closeNotebookModal(){
  document.getElementById('notebookModalOverlay').classList.remove('show');
}
function showNotebookTab(tab){
  notebookActiveTab = tab;
  const overlay = document.getElementById('notebookModalOverlay');
  overlay.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  const tabEl = overlay.querySelector(`.tab[data-notebook-tab="${tab}"]`);
  if(tabEl) tabEl.classList.add('active');
  overlay.querySelectorAll('.subview').forEach(v => v.classList.remove('active'));
  const viewEl = document.getElementById('notebook-tab-' + tab);
  if(viewEl) viewEl.classList.add('active');
  const btn = document.getElementById('notebookAddBtn');
  if(btn && !notebookEditingLocalId && !notebookEditingOnlineId){
    btn.textContent = tab === 'local' ? '＋ 加入本地紀錄' : '＋ 加入線上紀錄';
  }
}

// ---- 案場模糊搜尋（案號／地址／別名都可以比對一部分關鍵字）----
let notebookSearchTimer = null;
let notebookSelectedCaseRecordId = null;
function hideNotebookSearchResults(){
  const box = document.getElementById('notebookSearchResults');
  if(box){ box.classList.remove('show'); box.innerHTML = ''; }
}
function onNotebookCaseInput(){
  // 使用者正在打字，代表之前選定的案件（如果有）已經不算數了，
  // 摘要面板先藏起來，等重新選定候選項目後才會再顯示。
  notebookSelectedCaseRecordId = null;
  document.getElementById('notebookCaseSummary').style.display = 'none';
  const q = document.getElementById('notebookCaseInput').value.trim();
  clearTimeout(notebookSearchTimer);
  if(!q){ hideNotebookSearchResults(); return; }
  // 簡單 debounce，等使用者停下來 300 毫秒才真的送出查詢，避免每打一個字就打一次 API。
  notebookSearchTimer = setTimeout(() => runNotebookCaseSearch(q), 300);
}
async function runNotebookCaseSearch(q){
  const box = document.getElementById('notebookSearchResults');
  if(!box) return;
  box.innerHTML = '<div class="qm-empty">搜尋中…</div>';
  box.classList.add('show');
  try{
    const res = await fetch(API_BASE + '/api/case-search?q=' + encodeURIComponent(q), {cache: 'no-store'});
    const data = await res.json();
    if(!res.ok){
      box.innerHTML = `<div class="qm-empty">搜尋失敗：${data.error || ('HTTP ' + res.status)}</div>`;
      return;
    }
    const results = data.results || [];
    if(results.length === 0){
      box.innerHTML = '<div class="qm-empty">找不到符合的案場，可以直接記錄文字內容，不影響儲存。</div>';
      return;
    }
    box.innerHTML = results.map(r => `
      <div class="qm-result" onclick='selectNotebookCase(${JSON.stringify(r).replace(/'/g, "&#39;")})'>
        <div>
          <div class="qm-result-name">${r.case}${r.alias ? '　' + r.alias : ''}</div>
          <div class="qm-result-addr">${r.address || ''}</div>
        </div>
        <span class="vendor-pill ${VENDOR_CLASS[r.vendor] || 'vendor-other'}">${r.vendor || ''}</span>
      </div>
    `).join('');
  }catch(err){
    box.innerHTML = `<div class="qm-empty">搜尋失敗：${err.message}</div>`;
    console.error(err);
  }
}
async function selectNotebookCase(r){
  hideNotebookSearchResults();
  document.getElementById('notebookCaseInput').value = r.case;
  notebookSelectedCaseRecordId = r.record_id;
  await lookupNotebookCaseDetail(r.record_id);
}
// 點選單以外的地方，候選清單自動收起來
document.addEventListener('click', function(e){
  const box = document.getElementById('notebookSearchResults');
  const input = document.getElementById('notebookCaseInput');
  if(!box || !input) return;
  if(e.target !== input && !box.contains(e.target)) hideNotebookSearchResults();
});

async function lookupNotebookCaseDetail(caseRecordId){
  await lookupNotebookCaseByParams('case_record_id=' + encodeURIComponent(caseRecordId));
}
async function lookupNotebookCaseByText(caseText){
  if(!caseText){ document.getElementById('notebookCaseSummary').style.display = 'none'; return; }
  await lookupNotebookCaseByParams('case_no=' + encodeURIComponent(caseText));
}
async function lookupNotebookCaseByParams(qs){
  const summaryEl = document.getElementById('notebookCaseSummary');
  summaryEl.style.display = 'block';
  summaryEl.innerHTML = '查詢中…';
  try{
    const res = await fetch(API_BASE + '/api/case-lookup?' + qs, {cache: 'no-store'});
    const data = await res.json();
    if(!res.ok){
      summaryEl.innerHTML = '<span style="color:var(--text-muted);">查詢失敗：' + (data.error || ('HTTP ' + res.status)) + '</span>';
      return;
    }
    if(!data.found){
      summaryEl.innerHTML = '<span style="color:var(--text-muted);">這筆案件目前查不到資料，仍可直接記錄文字內容，不影響儲存。</span>';
      return;
    }
    const m = data.milestones || {};
    const salesLine = data.sales_field_configured
      ? `<div>業務：${data.sales_person || '（未填寫）'}</div>`
      : `<div style="color:var(--text-muted);">業務：（尚未設定業務欄位，需請開發者確認 Airtable 欄位名稱）</div>`;
    summaryEl.innerHTML = `
      <div style="font-weight:700;margin-bottom:4px;">${data.case}${data.alias ? '　'+data.alias : ''} <span class="vendor-pill ${VENDOR_CLASS[data.vendor]||'vendor-other'}" style="margin-left:4px;">${data.vendor||''}</span></div>
      <div>地址：${data.address || '（未填寫）'}</div>
      ${salesLine}
      <div>模組：${data.module || '（未填寫）'}</div>
      <div>逆變器：${data.inverter || '（未填寫）'}</div>
      <div style="margin-top:6px;font-weight:700;">函文進度</div>
      <div>併聯審查：${m['併聯審查'] ? fmtDate(m['併聯審查']) : '尚未'}</div>
      <div>同意備案：${m['同意備案'] ? fmtDate(m['同意備案']) : '尚未'}</div>
      <div>細部協商：${m['細部協商'] ? fmtDate(m['細部協商']) : '尚未'}</div>
      <div>台電契約：${m['台電購售契約'] ? fmtDate(m['台電購售契約']) : '尚未'}</div>
      <div>免雜：${m['免雜'] ? fmtDate(m['免雜']) : '尚未'}</div>
    `;
  }catch(err){
    summaryEl.innerHTML = '<span style="color:var(--text-muted);">查詢失敗：' + err.message + '</span>';
    console.error(err);
  }
}

async function addNotebookEntry(){
  const caseInput = document.getElementById('notebookCaseInput');
  const contentInput = document.getElementById('notebookContentInput');
  const caseText = caseInput.value.trim();
  const content = contentInput.value.trim();
  if(!content){ showToast('請填寫紀錄內容'); return; }

  if(notebookActiveTab === 'local'){
    const list = loadLocalNotebook();
    if(notebookEditingLocalId){
      const idx = list.findIndex(n => n.id === notebookEditingLocalId);
      if(idx >= 0) list[idx] = {...list[idx], case_text: caseText, content};
      notebookEditingLocalId = null;
    } else {
      list.unshift({
        id: 'local_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
        case_text: caseText,
        content,
        date: todayStr(),
      });
    }
    saveLocalNotebook(list);
    renderNotebookLocalList();
    caseInput.value = '';
    contentInput.value = '';
    document.getElementById('notebookCaseSummary').style.display = 'none';
    document.getElementById('notebookAddBtn').textContent = '＋ 加入本地紀錄';
    showToast('已加入本地紀錄（只存在這台電腦）');
    return;
  }

  const btn = document.getElementById('notebookAddBtn');
  const originalText = btn.textContent;
  btn.textContent = '儲存中…';
  btn.disabled = true;
  try{
    if(notebookEditingOnlineId){
      const res = await fetch(API_BASE + '/api/app-data/note/' + notebookEditingOnlineId, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({case_text: caseText || '（未指定案場）', content}),
      });
      if(!res.ok){
        const err = await res.json().catch(()=>({}));
        throw new Error(err.error || ('HTTP ' + res.status));
      }
      notebookEditingOnlineId = null;
    } else {
      const res = await fetch(API_BASE + '/api/app-data/note', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({type: NOTEBOOK_NOTE_TYPE, case_text: caseText || '（未指定案場）', content}),
      });
      if(!res.ok){
        const err = await res.json().catch(()=>({}));
        throw new Error(err.error || ('HTTP ' + res.status));
      }
    }
    await loadAppData();
    caseInput.value = '';
    contentInput.value = '';
    document.getElementById('notebookCaseSummary').style.display = 'none';
    showToast('已同步到線上紀錄，同事也能看到這筆');
  }catch(err){
    showToast('儲存失敗：' + err.message);
    console.error(err);
  }finally{
    btn.disabled = false;
    btn.textContent = notebookActiveTab === 'local' ? '＋ 加入本地紀錄' : '＋ 加入線上紀錄';
  }
}

function renderNotebookLocalList(){
  const tbody = document.getElementById('notebookLocalRows');
  if(!tbody) return;
  const list = loadLocalNotebook();
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有本地紀錄</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => `
    <tr>
      <td><div class="case-id">${n.case_text || '（未指定案場）'}</div></td>
      <td style="white-space:pre-wrap;">${n.content}</td>
      <td>${fmtDate(n.date)}</td>
      <td>
        <button class="btn btn-primary" style="padding:4px 10px;font-size:11.5px;" onclick="uploadLocalNotebookEntry('${n.id}')">⬆ 上傳</button>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;margin-left:4px;" onclick="editLocalNotebookEntry('${n.id}')">編輯</button>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;margin-left:4px;" onclick="deleteLocalNotebookEntry('${n.id}')">刪除</button>
      </td>
    </tr>
  `).join('');
}
function editLocalNotebookEntry(id){
  const list = loadLocalNotebook();
  const n = list.find(x => x.id === id);
  if(!n) return;
  showNotebookTab('local');
  document.getElementById('notebookCaseInput').value = n.case_text || '';
  document.getElementById('notebookContentInput').value = n.content || '';
  document.getElementById('notebookAddBtn').textContent = '更新本地紀錄';
  notebookEditingLocalId = id;
  notebookEditingOnlineId = null;
  notebookSelectedCaseRecordId = null;
  lookupNotebookCaseByText(n.case_text);
}
function deleteLocalNotebookEntry(id){
  const list = loadLocalNotebook().filter(n => n.id !== id);
  saveLocalNotebook(list);
  renderNotebookLocalList();
}
async function uploadLocalNotebookEntry(id){
  const list = loadLocalNotebook();
  const n = list.find(x => x.id === id);
  if(!n) return;
  try{
    const res = await fetch(API_BASE + '/api/app-data/note', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({type: NOTEBOOK_NOTE_TYPE, case_text: n.case_text || '（未指定案場）', content: n.content}),
    });
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    saveLocalNotebook(list.filter(x => x.id !== id));
    renderNotebookLocalList();
    await loadAppData();
    showToast('已上傳到線上紀錄，同事現在也能看到這筆');
  }catch(err){
    showToast('上傳失敗：' + err.message);
    console.error(err);
  }
}
function renderNotebookOnlineList(){
  const tbody = document.getElementById('notebookOnlineRows');
  if(!tbody) return;
  const list = APP_NOTES.filter(n => n.type === NOTEBOOK_NOTE_TYPE);
  if(list.length === 0){
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:20px 0;">目前沒有線上紀錄</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(n => `
    <tr>
      <td><div class="case-id">${n.case_text}</div></td>
      <td style="white-space:pre-wrap;">${n.content}</td>
      <td>${fmtDate(n.date)}</td>
      <td>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;" onclick="editOnlineNotebookEntry('${n.app_record_id}')">編輯</button>
        <button class="btn btn-ghost" style="padding:4px 10px;font-size:11.5px;margin-left:4px;" onclick="deleteOnlineNotebookEntry('${n.app_record_id}')">刪除</button>
      </td>
    </tr>
  `).join('');
}
function editOnlineNotebookEntry(appRecordId){
  const n = APP_NOTES.find(x => x.app_record_id === appRecordId);
  if(!n) return;
  showNotebookTab('online');
  document.getElementById('notebookCaseInput').value = n.case_text || '';
  document.getElementById('notebookContentInput').value = n.content || '';
  document.getElementById('notebookAddBtn').textContent = '更新線上紀錄';
  notebookEditingOnlineId = appRecordId;
  notebookEditingLocalId = null;
  notebookSelectedCaseRecordId = null;
  lookupNotebookCaseByText(n.case_text);
}
async function deleteOnlineNotebookEntry(appRecordId){
  try{
    const res = await fetch(API_BASE + '/api/app-data/' + appRecordId, {method: 'DELETE'});
    if(!res.ok){
      const err = await res.json().catch(()=>({}));
      throw new Error(err.error || ('HTTP ' + res.status));
    }
    APP_NOTES = APP_NOTES.filter(n => n.app_record_id !== appRecordId);
    renderNotebookOnlineList();
  }catch(err){
    showToast('刪除失敗：' + err.message);
    console.error(err);
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
  saveNavState({view: 'epc', epcTab: tab});
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
  return Array.from(map.values()).filter(e => matchesGlobalVendorScope(e.vendor));
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
  const holidayName = TW_HOLIDAYS[dateStr];
  const holidayRange = getHolidayRangeForDate(dateStr);
  const rangeNote = holidayRange ? `　（${holidayRange.days}天連假 ${fmtDate(holidayRange.start)}～${fmtDate(holidayRange.end)}）` : '';
  title.textContent = p[1] + '/' + p[2] + '（' + weekday + '）當日排程' + (holidayName ? `　🎌 ${holidayName}` : '') + rangeNote;
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
    rowsEl.innerHTML = '<div class="login-note">未來 7 天內目前沒有符合篩選條件的排程。</div>';
    return;
  }
  const weekdayNames = ['日','一','二','三','四','五','六'];
  rowsEl.innerHTML = events.map(e => {
    const p = e.date.split('-');
    const d = new Date(Number(p[0]), Number(p[1])-1, Number(p[2]));
    const holidayName = TW_HOLIDAYS[e.date];
    const dayLabel = p[1] + '/' + p[2] + '（' + weekdayNames[d.getDay()] + '）' + (holidayName ? ` 🎌${holidayName}` : '');
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
      return `<div class="chip ${CAL_TYPE_CHIP[e.type]}" data-vendor="${e.vendorCode}" title="${e.case}　${e.vendor||''}">${e.label} ${CAL_TYPE_LABEL[e.type]}</div>`;
    }).join('');
    const isToday = cellDate === todayIso;
    const selectedClass = cellDate === calSelectedDate ? ' cal-cell-selected' : '';
    const holidayName = TW_HOLIDAYS[cellDate];
    const holidayRange = getHolidayRangeForDate(cellDate);
    const rangeStyle = holidayRange ? 'background:#FFF6EC;' : '';
    cellsHtml += `<div class="cal-cell${muted?' muted':''}${selectedClass}" data-date="${cellDate}" style="${rangeStyle}" onclick="selectCalDay('${cellDate}')">
      <div class="cal-date${isToday?' today':''}" style="${holidayName ? 'color:#D64545;' : ''}">${dayLabel}</div>
      ${holidayName ? `<div style="font-size:9.5px;color:#D64545;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${holidayName}">${holidayName}</div>` : ''}
      ${holidayRange && holidayRange.start === cellDate ? `<div style="font-size:9.5px;color:#E8890C;font-weight:700;white-space:nowrap;">🎉共${holidayRange.days}天連假</div>` : ''}
      ${chipsHtml}
    </div>`;
  }

  grid.innerHTML = `
    <div class="cal-dow">一</div><div class="cal-dow">二</div><div class="cal-dow">三</div>
    <div class="cal-dow">四</div><div class="cal-dow">五</div><div class="cal-dow">六</div><div class="cal-dow">日</div>
    ${cellsHtml}
  `;

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
  saveNavState({view: 'pdf', pdfTab: tab});
}

// 開機時嘗試恢復上次停留的頁面（見上方 saveNavState/loadNavState 說明），
// 讀不到有效紀錄、或紀錄的頁籤已經不存在，就一律退回顯示「總覽」。
(function restoreNavState(){
  const state = loadNavState();
  if(state && state.view === 'epc' && state.epcTab && document.getElementById('tab-' + state.epcTab)){
    showEpcTab(state.epcTab);
  } else if(state && state.view === 'pdf' && state.pdfTab && document.getElementById('tab-' + state.pdfTab)){
    showPdfTab(state.pdfTab);
  } else {
    showView('home');
  }
})();
</script>

</body>
</html>
