# WKT 主数据同步规则（一键云端 / GitHub 参考）
# 订单库 *.db 与出货附件 delivery_notes 不同步；其余 data/ 覆盖上传。

function Get-WktDataSyncExcludeDirs {
    return @(
        "delivery_notes"
    )
}

function Test-WktDataSyncExcludedFile {
    param([string]$FileName)
    $name = [IO.Path]::GetFileName($FileName)
    if ($name -match '\.db$') { return $true }
    if ($name -match '\.db-(journal|wal|shm)$') { return $true }
    if ($name -like '*.db.bak*') { return $true }
    return $false
}

function Copy-WktDataForSync {
    param(
        [Parameter(Mandatory = $true)][string]$SourceRoot,
        [Parameter(Mandatory = $true)][string]$DestDir
    )

    $srcData = Join-Path $SourceRoot "data"
    if (!(Test-Path $srcData)) {
        Write-Host "No data/ directory; skip." -ForegroundColor DarkGray
        return
    }

    $destData = Join-Path $DestDir "data"
    New-Item -ItemType Directory -Path $destData -Force | Out-Null
    $excludeDirs = Get-WktDataSyncExcludeDirs

    Write-Host "Pack data/ (exclude order DB + delivery_notes attachments) ..." -ForegroundColor Cyan
    $count = 0
    Get-ChildItem -Path $srcData -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($srcData.Length).TrimStart('\', '/')
        $top = ($rel -split '[\\/]', 2)[0]
        if ($excludeDirs -contains $top) { return }
        if (Test-WktDataSyncExcludedFile $_.Name) { return }

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

function Show-WktDataSyncPolicy {
    Write-Host "Sync data/: customer_profiles, delivery_templates, supplier_profiles, feishu_config, ..." -ForegroundColor DarkGray
    Write-Host "NOT sync: *.db (order DB), delivery_notes/ (shipment attachments)" -ForegroundColor DarkGray
}
