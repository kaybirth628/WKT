# WKT 主数据同步规则
# 【生产阶段】默认 CodeOnly：不同步任何 data/，云端 data 为权威。
# -FullData / -WithMasterData 已在 sync-to-cloud.ps1 入口禁用。
# 见 docs/change/PRODUCTION-SAFETY.md

function Get-WktDataSyncExcludeDirs {
    param([switch]$FullData)
    if ($FullData) { return @() }
    return @(
        "delivery_notes"
    )
}

function Test-WktDataSyncExcludedFile {
    param(
        [string]$FileName,
        [switch]$FullData
    )
    if ($FullData) { return $false }
    $name = [IO.Path]::GetFileName($FileName)
    if ($name -match '\.db$') { return $true }
    if ($name -match '\.db-(journal|wal|shm)$') { return $true }
    if ($name -like '*.db.bak*') { return $true }
    return $false
}

function Copy-WktDataForSync {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$DestDir,
        [switch]$FullData,
        [switch]$WithMasterData
    )

    if (-not $FullData -and -not $WithMasterData) {
        Write-Host "Skip data/ (code-only sync; cloud data preserved)." -ForegroundColor Green
        return
    }

    $srcData = Join-Path $SourceRoot "data"
    if (!(Test-Path $srcData)) {
        Write-Host "No data/ directory; skip." -ForegroundColor DarkGray
        return
    }

    $destData = Join-Path $DestDir "data"
    New-Item -ItemType Directory -Path $destData -Force | Out-Null
    $excludeDirs = Get-WktDataSyncExcludeDirs -FullData:$FullData

    if ($FullData) {
        Write-Host "Pack data/ FULL (order DB + delivery_notes included) ..." -ForegroundColor Yellow
    } else {
        Write-Host "Pack data/ master JSON only (exclude order DB + delivery_notes) ..." -ForegroundColor Cyan
    }
    $count = 0
    Get-ChildItem -Path $srcData -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($srcData.Length).TrimStart('\', '/')
        $top = ($rel -split '[\\/]', 2)[0]
        if ($excludeDirs -contains $top) { return }
        if (Test-WktDataSyncExcludedFile $_.Name -FullData:$FullData) { return }

        $target = Join-Path $destData $rel
        $targetDir = Split-Path $target -Parent
        if (!(Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item $_.FullName $target -Force
        $count++
    }
    Write-Host "  Packed $count data files." -ForegroundColor DarkGray
}

function Copy-WktFeishuConfigForSync {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$DestDir
    )
    $srcFeishu = Join-Path $SourceRoot "data\feishu_config.json"
    if (!(Test-Path $srcFeishu)) {
        Write-Host "No data/feishu_config.json; skip Feishu notify sync." -ForegroundColor DarkGray
        return
    }
    $destData = Join-Path $DestDir "data"
    New-Item -ItemType Directory -Path $destData -Force | Out-Null
    Copy-Item $srcFeishu (Join-Path $destData "feishu_config.json") -Force
    Write-Host "Pack data/feishu_config.json (always push Feishu webhooks to cloud)." -ForegroundColor Cyan
}

function Show-WktDataSyncPolicy {
    param(
        [switch]$FullData,
        [switch]$WithMasterData
    )
    if ($FullData) {
        Write-Host "FULL data sync: entire data/ including wkt_orders.db + delivery_notes/" -ForegroundColor Yellow
        Write-Host "Cloud order DB will be REPLACED by local copy." -ForegroundColor Yellow
        return
    }
    if ($WithMasterData) {
        Write-Host "Master data sync: customer_profiles, supplier_profiles, delivery_templates, feishu_config, ..." -ForegroundColor Yellow
        Write-Host "NOT sync: *.db (order DB), delivery_notes/" -ForegroundColor DarkGray
        Write-Host "WARNING: cloud JSON master data will be OVERWREN by local files." -ForegroundColor Yellow
        return
    }
    Write-Host "Code-only sync: test_impl + scripts ONLY" -ForegroundColor Green
    Write-Host "Cloud data/ is NOT touched (orders, suppliers, customers stay on server)." -ForegroundColor Green
    Write-Host "Exception: data/feishu_config.json is ALWAYS synced (Feishu notify webhooks)." -ForegroundColor Cyan
}
