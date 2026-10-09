<#
陽光主控台「PDF 公文更名」— LINE 收件資料夾背景程式
=====================================================
跑在每位 PM 自己的電腦上（Windows 內建 PowerShell，不用另外安裝）：
  每分鐘到主控台讀「這位 PM 的 LINE 收件資料夾」設定，資料夾（含子資料夾）裡有新的 PDF、
  照片（JPG/PNG，主控台會轉成 PDF）、Word／Excel（.docx／.xlsx），
  就送到主控台的辨識佇列；同一份內容重複下載不會重複辨識（後端比對檔案雜湊）。
  若主控台指定這台電腦負責「自動歸檔」，也會把「已確認」的檔案用確認檔名放進
  「案場資料夾 → 03/04/06/07」，同名檔案不覆蓋；資料夾裡已經有同類型的檔案（例如已有
  桃1_20250106_併聯審查.pdf）會先停下來，到主控台選「仍要歸檔」或「不歸檔」。
  電腦關機期間下載的檔案，下次開機會自動補送。每分鐘回報一次狀態，主控台看得到。

安裝（只要一次，會設定成開機自動在背景執行，不會跳視窗）：
  powershell -ExecutionPolicy Bypass -File pdf_watcher.ps1 -Install
移除：
  powershell -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\SunnyPdfWatcher\pdf_watcher.ps1" -Uninstall
記錄檔：%LOCALAPPDATA%\SunnyPdfWatcher\watcher.log
#>
param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Once,
    [string]$Pm = ""
)

$ErrorActionPreference = "Stop"
$Version = "1.5"
$Backend = "https://epc-backend-4aj2.onrender.com"
if ($env:SUNNY_BACKEND) { $Backend = $env:SUNNY_BACKEND }   # 測試用
if ($env:LOCALAPPDATA) { $AppDir = Join-Path $env:LOCALAPPDATA "SunnyPdfWatcher" }
else { $AppDir = Join-Path $HOME ".sunny_pdf_watcher" }   # 非 Windows（測試用）
$ConfigPath = Join-Path $AppDir "config.json"
$SeenPath = Join-Path $AppDir "seen.json"
$LogPath = Join-Path $AppDir "watcher.log"
$InstalledScript = Join-Path $AppDir "pdf_watcher.ps1"
$Utf8 = New-Object System.Text.UTF8Encoding $false
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

if (-not (Test-Path -LiteralPath $AppDir)) { New-Item -ItemType Directory -Path $AppDir | Out-Null }

function Write-Log([string]$msg) {
    $line = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss") + "  " + $msg
    try {
        if ((Test-Path -LiteralPath $LogPath) -and ((Get-Item -LiteralPath $LogPath).Length -gt 1MB)) {
            Move-Item -LiteralPath $LogPath -Destination ($LogPath + ".old") -Force
        }
        [IO.File]::AppendAllText($LogPath, $line + [Environment]::NewLine, $Utf8)
    } catch { }
    Write-Host $line
}

function Read-JsonFile([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    $raw = [IO.File]::ReadAllText($path)
    if (-not $raw.Trim()) { return $null }
    return ($raw | ConvertFrom-Json)
}

function Write-JsonFile([string]$path, $obj) {
    [IO.File]::WriteAllText($path, ($obj | ConvertTo-Json -Depth 5), $Utf8)
}

function Get-ErrorText($err) {
    # 後端回 4xx/5xx 時，把 JSON 裡的 error 取出來
    $msg = $err.Exception.Message
    if ($err.ErrorDetails -and $err.ErrorDetails.Message) {
        try { $j = $err.ErrorDetails.Message | ConvertFrom-Json; if ($j.error) { return [string]$j.error } } catch { }
        return [string]$err.ErrorDetails.Message
    }
    return [string]$msg
}

function Invoke-Api([string]$method, [string]$path, $body = $null) {
    $uri = $Backend + $path
    if ($method -eq "GET") {
        return Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 150
    }
    $json = $body | ConvertTo-Json -Depth 5 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    return Invoke-RestMethod -Method Post -Uri $uri -Body $bytes -ContentType "application/json; charset=utf-8" -TimeoutSec 300
}

# ---------------- 安裝／移除 ----------------

function Get-StartupLauncher {
    return Join-Path ([Environment]::GetFolderPath("Startup")) "SunnyPdfWatcher.vbs"
}

function Stop-OtherWatchers {
    try {
        Get-CimInstance Win32_Process -Filter "Name like 'powershell%'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -like "*pdf_watcher.ps1*" -and $_.ProcessId -ne $PID } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    } catch { }
}

if ($Uninstall) {
    Stop-OtherWatchers
    $launcher = Get-StartupLauncher
    if (Test-Path -LiteralPath $launcher) { Remove-Item -LiteralPath $launcher -Force }
    Write-Host "已移除開機自動執行，背景程式已停止。（記錄檔仍保留在 $AppDir）"
    exit 0
}

if ($Install) {
    Write-Host "=== 安裝 LINE 收件資料夾背景程式 ==="
    if (-not $Pm) {
        $pms = @()
        try { $pms = @((Invoke-Api "GET" "/api/pdf-rename/watcher-config").pms) } catch {
            Write-Host "連不到主控台（可能剛醒來，等 1 分鐘再試）：$(Get-ErrorText $_)"
        }
        if ($pms.Count -gt 0) {
            Write-Host "主控台已設定的 PM："
            for ($i = 0; $i -lt $pms.Count; $i++) { Write-Host ("  " + ($i + 1) + ". " + $pms[$i]) }
            $ans = Read-Host "請輸入你的編號（或直接輸入名字）"
            $n = 0
            if ([int]::TryParse($ans, [ref]$n) -and $n -ge 1 -and $n -le $pms.Count) { $Pm = $pms[$n - 1] } else { $Pm = $ans.Trim() }
        } else {
            $Pm = (Read-Host "請輸入你的名字（要跟主控台「LINE 收件資料夾」設定的 PM 名字一樣）").Trim()
        }
    }
    if (-not $Pm) { Write-Host "沒有輸入名字，取消安裝。"; exit 1 }
    try {
        $cfg = Invoke-Api "GET" ("/api/pdf-rename/watcher-config?pm=" + [uri]::EscapeDataString($Pm))
        if ($cfg.folder) {
            Write-Host "主控台設定的 LINE 收件資料夾：$($cfg.folder)"
            if (-not (Test-Path -LiteralPath $cfg.folder)) { Write-Host "⚠ 這台電腦找不到這個資料夾，請到主控台確認路徑（之後改網站設定就好，不用重裝）" }
        } else {
            Write-Host "沒有設定 LINE 收件資料夾：這台電腦只負責自動歸檔"
        }
        if ($cfg.archive -and $cfg.archive.enabled) {
            $found = @(@($cfg.archive.roots) | Where-Object { $_ -and (Test-Path -LiteralPath $_) })
            if ($found.Count -gt 0) { Write-Host "✓ 找得到案場資料夾根目錄：$($found -join '、')" }
            else { Write-Host "⚠ 這台電腦找不到案場資料夾根目錄（$(@($cfg.archive.roots) -join '、')）。請確認已安裝 Google 雲端硬碟並登入公司帳號、看得到「共用雲端硬碟」；磁碟代號不是 G 的話，到主控台把路徑加一行" }
        }
    } catch {
        Write-Host "⚠ $(Get-ErrorText $_)（先到主控台設定好資料夾，之後會自動套用，不用重裝）"
    }
    Write-JsonFile $ConfigPath @{ pm = $Pm }
    if ($PSCommandPath -and ($PSCommandPath -ne $InstalledScript)) {
        Copy-Item -LiteralPath $PSCommandPath -Destination $InstalledScript -Force
    }
    # 用 VBS 啟動才能完全不跳出黑色視窗；存成 Unicode 才能支援中文使用者名稱的路徑
    $cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""' + $InstalledScript + '""'
    $vbs = 'CreateObject("Wscript.Shell").Run "' + $cmd + '", 0, False'
    [IO.File]::WriteAllText((Get-StartupLauncher), $vbs, [Text.Encoding]::Unicode)
    Stop-OtherWatchers
    Start-Process -FilePath "wscript.exe" -ArgumentList ('"' + (Get-StartupLauncher) + '"')
    Write-Host ""
    Write-Host "✓ 安裝完成！已經在背景開始執行，之後每次開機會自動執行。"
    Write-Host "  PM：$Pm"
    Write-Host "  到主控台「PDF 公文更名 → ⚙ 設定 → LINE 收件資料夾」可以看到這台電腦的狀態。"
    Write-Host "  記錄檔：$LogPath"
    exit 0
}

# ---------------- 背景監看 ----------------

$local = Read-JsonFile $ConfigPath
if (-not $Pm -and $local -and $local.pm) { $Pm = [string]$local.pm }
if (-not $Pm) { Write-Log "還沒設定 PM 名字，請先執行：powershell -ExecutionPolicy Bypass -File pdf_watcher.ps1 -Install"; exit 1 }

$mutex = New-Object System.Threading.Mutex($false, "SunnyPdfWatcher")
if (-not $Once -and -not $mutex.WaitOne(0)) { exit 0 }   # 已經有一個在跑

# 已處理過的檔案：路徑|大小|修改時間 → 結果
$seen = @{}
$firstRun = -not (Test-Path -LiteralPath $SeenPath)
$saved = Read-JsonFile $SeenPath
if ($saved) { foreach ($p in $saved.PSObject.Properties) { $seen[$p.Name] = [string]$p.Value } }

$stats = @{ uploaded_total = 0; skipped = 0; last_error = ""; last_upload = "";
            archived_total = 0; last_archive = ""; archive_error = ""; case_folders = 0 }

# ---------------- 自動歸檔 ----------------
$caseIndex = @{}          # 案號 → 案場資料夾完整路徑
$caseIndexAt = [datetime]::MinValue
$archiveFailedAt = @{}    # 記錄 id → 上次失敗時間（失敗的 30 分鐘後再試）
$WatchExts = @(".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".docx", ".xlsx")

function Find-CaseDir($it) {
    # 收購的案場：Airtable 案號是「桃園千塘82號」、G 槽資料夾是「潤特桃園17號」，主控台會給所有可能的案號
    $keys = @($it.folder_keys)
    if ($keys.Count -eq 0) { $keys = @([string]$it.case_no) }
    foreach ($k in $keys) { if ($k -and $script:caseIndex.ContainsKey([string]$k)) { return $script:caseIndex[[string]$k] } }
    return $null
}

function Get-SameTypeFiles($dir, $it) {
    # 同簡稱、同類型、但檔名不同的檔案（例如 桃1_20240105_併聯審查.pdf；類型後面接副檔名、括號或結尾才算）
    if (-not $it.check_same -or -not $it.short) { return @() }
    $alts = (@($it.type_names) | Where-Object { $_ } | ForEach-Object { [regex]::Escape([string]$_) }) -join "|"
    if (-not $alts) { return @() }
    $pat = '^' + [regex]::Escape([string]$it.short) + '_\d{8}_(' + $alts + ')(\.|\s|\(|（|_|-|$)'
    return @(Get-ChildItem -LiteralPath $dir -File -ErrorAction SilentlyContinue |
             Where-Object { $_.Name -match $pat -and $_.Name -ne [string]$it.final_name } | ForEach-Object { $_.Name })
}

function Update-CaseIndex([string[]]$roots) {
    # 根目錄往下最多 4 層找「001 潤特桃園1號_…」這種案場資料夾（名稱開頭是編號＋案號）
    $idx = @{}
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $queue = New-Object System.Collections.Queue
        $queue.Enqueue(@($root, 0))
        while ($queue.Count -gt 0) {
            $item = $queue.Dequeue(); $dir = $item[0]; $depth = $item[1]
            $subs = @(Get-ChildItem -LiteralPath $dir -Directory -ErrorAction SilentlyContinue)
            foreach ($d in $subs) {
                if ($d.Name -match '^\s*\d+\s*[-_.、 ]?\s*([^\s_（(]+?號)') {
                    if (-not $idx.ContainsKey($Matches[1])) { $idx[$Matches[1]] = $d.FullName }
                } elseif ($depth -lt 3) {
                    $queue.Enqueue(@($d.FullName, ($depth + 1)))
                }
            }
        }
    }
    return $idx
}

function Invoke-Archive($arc) {
    $roots = @($arc.roots)
    if ($roots.Count -eq 0) { $stats.archive_error = "主控台還沒設定案場資料夾根目錄"; return }
    if (((Get-Date) - $script:caseIndexAt).TotalMinutes -gt 30 -or $script:caseIndex.Count -eq 0) {
        $script:caseIndex = Update-CaseIndex $roots
        $script:caseIndexAt = Get-Date
        $stats.case_folders = $script:caseIndex.Count
        Write-Log "案場資料夾索引：找到 $($script:caseIndex.Count) 個案場"
    }
    $items = @((Invoke-Api "GET" "/api/pdf-rename/confirmed").items)
    $stats.archive_error = ""
    foreach ($it in $items) {
        if ($script:archiveFailedAt.ContainsKey($it.id) -and ((Get-Date) - $script:archiveFailedAt[$it.id]).TotalMinutes -lt 30) { continue }
        $fail = ""
        $target = ""
        $caseDir = Find-CaseDir $it
        if (-not $it.case_no) { $fail = "沒有案號" }
        elseif (-not $caseDir) {
            # 可能是新案場，重新整理一次索引再找
            $script:caseIndex = Update-CaseIndex $roots; $script:caseIndexAt = Get-Date
            $caseDir = Find-CaseDir $it
            if (-not $caseDir) { $fail = "在根目錄底下找不到案場資料夾「$((@($it.folder_keys) + @($it.case_no) | Select-Object -Unique) -join '／')」" }
        }
        if (-not $fail) {
            $cat = [string]$it.category
            if (-not $cat) { $fail = "文件類型「$($it.doc_type)」沒有設定要放哪個分類資料夾（03/04/06/07）" }
            else {
                $n = [int]$cat
                $sub = @(Get-ChildItem -LiteralPath $caseDir -Directory -ErrorAction SilentlyContinue |
                         Where-Object { $_.Name -match ('^\s*0?' + $n + '(\D|$)') }) | Select-Object -First 1
                if (-not $sub) { $fail = "案場資料夾裡找不到「$cat」開頭的分類資料夾：$caseDir" }
                else { $target = Join-Path $sub.FullName ([string]$it.final_name) }
            }
        }
        if (-not $fail) {
            $same = @(Get-SameTypeFiles (Split-Path -Parent $target) $it)
            if ($same.Count -gt 0) {
                # 已經有同類型的檔案：可能是重複或新版，先不放，讓人在主控台決定
                try { Invoke-Api "POST" ("/api/pdf-rename/" + $it.id + "/archived") @{ ok = $false; conflict = $true; existing = @($same) } | Out-Null } catch { }
                Write-Log "暫停歸檔（資料夾已有同類型檔案 $($same -join '、')）：$($it.final_name)"
                continue
            }
        }
        if (-not $fail) {
            # 大家共用同一個雲端，任何開著的電腦都可能在歸檔：先領取，別台已經在處理就跳過
            try { Invoke-Api "POST" ("/api/pdf-rename/" + $it.id + "/archive-claim") @{ pm = $Pm } | Out-Null }
            catch { continue }
            $tmp = Join-Path $AppDir ("dl_" + $it.id + [IO.Path]::GetExtension([string]$it.final_name))
            try {
                Invoke-WebRequest -Uri ($Backend + "/api/pdf-rename/" + $it.id + "/file") -OutFile $tmp -TimeoutSec 300 -UseBasicParsing
                if (Test-Path -LiteralPath $target) {
                    $same = (Get-FileHash -LiteralPath $tmp -Algorithm SHA1).Hash -eq (Get-FileHash -LiteralPath $target -Algorithm SHA1).Hash
                    Remove-Item -LiteralPath $tmp -Force
                    if (-not $same) { throw "資料夾裡已經有同名但內容不同的檔案（不覆蓋，請手動處理）：$target" }
                } else {
                    [IO.File]::Move($tmp, $target)   # 不用 Move-Item：檔名有 [ ] 會被當成萬用字元
                }
                Invoke-Api "POST" ("/api/pdf-rename/" + $it.id + "/archived") @{ ok = $true; result = "已放到 $target（$env:COMPUTERNAME）" } | Out-Null
                $stats.archived_total++
                $stats.last_archive = $target
                Write-Log "已歸檔：$target"
            } catch {
                $fail = Get-ErrorText $_
                if ($fail -notlike "*同名*") { $fail = "下載或搬移失敗：" + $fail }
                if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
            }
        }
        if ($fail) {
            $script:archiveFailedAt[$it.id] = Get-Date
            $stats.archive_error = $fail
            Write-Log "歸檔失敗（$($it.final_name)）：$fail"
            try { Invoke-Api "POST" ("/api/pdf-rename/" + $it.id + "/archived") @{ ok = $false; result = $fail } | Out-Null } catch { }
        }
    }
}
Write-Log "背景程式啟動（v$Version，PM：$Pm）"

while ($true) {
    $folder = ""
    $folderOk = $false
    try {
        $cfg = Invoke-Api "GET" ("/api/pdf-rename/watcher-config?pm=" + [uri]::EscapeDataString($Pm))
        $folder = [string]$cfg.folder
        $maxBytes = [int64]$cfg.max_mb * 1MB
        $imageMaxBytes = $maxBytes
        if ($cfg.image_max_mb) { $imageMaxBytes = [int64]$cfg.image_max_mb * 1MB }
        if (-not $cfg.enabled) {
            $stats.last_error = "主控台設定為停用"
        } elseif (-not $folder) {
            # 沒設定 LINE 收件資料夾：這台電腦只負責把確認過的檔案歸檔到 G 槽（例如家裡的電腦）
            $stats.last_error = ""
        } elseif (-not (Test-Path -LiteralPath $folder)) {
            $stats.last_error = "這台電腦找不到資料夾：$folder"
        } else {
            $folderOk = $true
            $files = @(Get-ChildItem -LiteralPath $folder -Recurse -File -ErrorAction SilentlyContinue |
                       Where-Object { ($WatchExts -contains $_.Extension.ToLower()) -and -not $_.Name.StartsWith("~$") } |
                       Sort-Object LastWriteTimeUtc)
            $now = (Get-Date).ToUniversalTime()
            if ($firstRun) {
                # 第一次執行：一天以前的舊檔當作已處理，只送最近 24 小時內的（避免一次塞爆佇列）
                $old = 0
                foreach ($f in $files) {
                    if (($now - $f.LastWriteTimeUtc).TotalHours -gt 24) {
                        $seen[$f.FullName + "|" + $f.Length + "|" + $f.LastWriteTimeUtc.Ticks] = "baseline"
                        $old++
                    }
                }
                Write-JsonFile $SeenPath $seen
                Write-Log "第一次執行：資料夾裡 $old 份一天以前的舊檔略過，之後只處理新下載的"
                $firstRun = $false
            }
            $errorThisRound = ""
            foreach ($f in $files) {
                $key = $f.FullName + "|" + $f.Length + "|" + $f.LastWriteTimeUtc.Ticks
                if ($seen.ContainsKey($key)) { continue }
                if (($now - $f.LastWriteTimeUtc).TotalSeconds -lt 30) { continue }   # 可能還在下載
                $isImage = @(".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp") -contains $f.Extension.ToLower()
                $limit = $maxBytes
                if ($isImage) { $limit = $imageMaxBytes }
                if ($f.Length -gt $limit) {
                    $seen[$key] = "too_big"; $stats.skipped++
                    Write-Log "略過（超過 $([int]($limit / 1MB))MB，請到主控台手動上傳）：$($f.FullName)"
                    Write-JsonFile $SeenPath $seen
                    continue
                }
                try {
                    $data = [Convert]::ToBase64String([IO.File]::ReadAllBytes($f.FullName))
                    $res = Invoke-Api "POST" "/api/pdf-rename/watcher-upload" @{ pm = $Pm; filename = $f.Name; path = $f.FullName; data = $data; received_at = $f.LastWriteTime.ToString("yyyy-MM-dd'T'HH:mm:sszzz") }
                    if ($res.duplicate) {
                        $seen[$key] = "duplicate"
                        Write-Log "已經在佇列裡（重複檔案）：$($f.Name)"
                    } else {
                        $seen[$key] = "uploaded"
                        $stats.uploaded_total++
                        $stats.last_upload = $f.Name
                        Write-Log "已送出辨識：$($f.Name)"
                    }
                    Write-JsonFile $SeenPath $seen
                } catch {
                    $msg = Get-ErrorText $_
                    if ($msg -like "*不是 PDF*" -or $msg -like "*不支援*" -or $msg -like "*不是有效*" -or $msg -like "*無法轉成*") {
                        $seen[$key] = "not_pdf"; $stats.skipped++
                        Write-JsonFile $SeenPath $seen
                    } else {
                        $errorThisRound = "送出失敗（下次重試）：$($f.Name)：$msg"
                        Write-Log $errorThisRound
                    }
                }
            }
            $stats.last_error = $errorThisRound
        }
        if ($cfg.archive -and $cfg.archive.enabled) {
            try { Invoke-Archive $cfg.archive } catch {
                $stats.archive_error = "歸檔時發生錯誤：" + (Get-ErrorText $_)
                Write-Log $stats.archive_error
            }
        }
    } catch {
        $stats.last_error = "連不到主控台：" + (Get-ErrorText $_)
        Write-Log $stats.last_error
    }
    try {
        Invoke-Api "POST" "/api/pdf-rename/watcher-heartbeat" @{
            pm = $Pm; host = $env:COMPUTERNAME; folder = $folder; folder_ok = $folderOk; version = $Version
            archive_only = (-not $folder)
            uploaded_total = $stats.uploaded_total; skipped = $stats.skipped
            last_error = $stats.last_error; last_upload = $stats.last_upload
            archived_total = $stats.archived_total; last_archive = $stats.last_archive
            archive_error = $stats.archive_error; case_folders = $stats.case_folders
        } | Out-Null
    } catch { }
    if ($Once) { break }
    Start-Sleep -Seconds 60
}
