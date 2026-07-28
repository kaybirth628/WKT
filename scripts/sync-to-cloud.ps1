# One-click sync local CODE to cloud (test_impl + scripts).
# Default: code-only — cloud data/ is NOT overwritten (cloud is source of truth).
# -WithMasterData: also push local JSON master data (legacy; overwrites cloud JSON).
# -FullData: entire data/ including wkt_orders.db (requires YES confirm).
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\sync-to-cloud.ps1
# Config: copy config\deploy.local.example.json -> config\deploy.local.json

param(
    [switch]$PackOnly,
    [switch]$FullData,
    [switch]$WithMasterData
)

if ($FullData) {
    throw @"
FullData cloud sync is DISABLED (cloud = production).
Do not upload local data/ to overwrite cloud.
Use '一键下载云端数据覆盖本地.bat' to pull cloud -> local instead.
See docs/change/PRODUCTION-SAFETY.md
"@
}
if ($WithMasterData) {
    throw @"
WithMasterData cloud sync is DISABLED (cloud master JSON = production).
Use code-only sync via '一键推送云端和GitHub.bat'.
See docs/change/PRODUCTION-SAFETY.md
"@
}

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$configPath = Join-Path $root "config\deploy.local.json"
$examplePath = Join-Path $root "config\deploy.local.example.json"

function Ensure-PoshSsh {
    if (Get-Module -ListAvailable -Name Posh-SSH) { return }
    Write-Host "Installing Posh-SSH (first time only)..." -ForegroundColor Yellow
    Install-Module Posh-SSH -Scope CurrentUser -Force -AllowClobber
}

function Load-Config {
    if (!(Test-Path $configPath)) {
        if (!(Test-Path $examplePath)) {
            throw "Missing config\deploy.local.example.json"
        }
        Copy-Item $examplePath $configPath
        Write-Host "Created config\deploy.local.json — please edit SSH password, then run again." -ForegroundColor Yellow
        notepad $configPath
        throw "Configure deploy.local.json first."
    }
    $raw = Get-Content $configPath -Raw -Encoding UTF8
    return ($raw | ConvertFrom-Json)
}

function Build-Staging {
    param([string]$StagingDir, [switch]$FullData, [switch]$WithMasterData)
    if (Test-Path $StagingDir) { Remove-Item $StagingDir -Recurse -Force }
    New-Item -ItemType Directory -Path $StagingDir | Out-Null

    $srcImpl = Join-Path $root "test_impl"
    if (!(Test-Path $srcImpl)) { throw "Missing test_impl" }

    Write-Host "Pack test_impl ..." -ForegroundColor Cyan
    & robocopy $srcImpl (Join-Path $StagingDir "test_impl") /MIR /XD __pycache__ .pytest_cache .mypy_cache /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /nc /ns /np
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed: $LASTEXITCODE" }

    $srcScripts = Join-Path $root "scripts"
    if (Test-Path $srcScripts) {
        Write-Host "Pack scripts ..." -ForegroundColor Cyan
        & robocopy $srcScripts (Join-Path $StagingDir "scripts") /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
        if ($LASTEXITCODE -ge 8) { throw "robocopy scripts failed" }
    }

    . (Join-Path $PSScriptRoot "data-sync-rules.ps1")
    Copy-WktDataForSync -SourceRoot $root -DestDir $StagingDir -FullData:$FullData -WithMasterData:$WithMasterData
    if (-not $FullData -and -not $WithMasterData) {
        Copy-WktFeishuConfigForSync -SourceRoot $root -DestDir $StagingDir
    }

    $deployInfo = Join-Path $StagingDir "deploy-info"
    New-Item -ItemType Directory -Path $deployInfo -Force | Out-Null
    $verSrc = Join-Path $root "docs\VERSION.md"
    $clSrc = Join-Path $root "docs\change\CHANGELOG.md"
    if (Test-Path $verSrc) {
        Copy-Item $verSrc (Join-Path $deployInfo "VERSION.md")
        Write-Host "Pack deploy-info/VERSION.md ..." -ForegroundColor DarkGray
    }
    if (Test-Path $clSrc) {
        Copy-Item $clSrc (Join-Path $deployInfo "CHANGELOG.md")
        Write-Host "Pack deploy-info/CHANGELOG.md ..." -ForegroundColor DarkGray
    }
}

function New-Archive {
    param([string]$StagingDir, [string]$ArchivePath)
    $releaseDir = Split-Path $ArchivePath -Parent
    if (!(Test-Path $releaseDir)) { New-Item -ItemType Directory -Path $releaseDir | Out-Null }
    if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }

    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if ($tar) {
        Push-Location $StagingDir
        try {
            $items = @("test_impl")
            if (Test-Path "scripts") { $items += "scripts" }
            if (Test-Path "data") { $items += "data" }
            if (Test-Path "deploy-info") { $items += "deploy-info" }
            & tar -caf $ArchivePath @items
            if ($LASTEXITCODE -ne 0) {
                & tar -caf $ArchivePath test_impl
            }
        } finally {
            Pop-Location
        }
    } else {
        Compress-Archive -Path (Join-Path $StagingDir "*") -DestinationPath $ArchivePath -Force
    }
    Write-Host "Archive: $ArchivePath" -ForegroundColor Green
}

function Invoke-RemoteMerge {
    param($Cfg, [string]$RemoteArchive, [string]$StagingDir, [switch]$FullData)

    Ensure-PoshSsh
    Import-Module Posh-SSH -ErrorAction Stop
    . (Join-Path $PSScriptRoot "ssh-auth.ps1")
    $cred = Get-WktSshCredential -Cfg $Cfg

    $session = New-SSHSession -ComputerName $Cfg.ssh_host -Port ([int]$Cfg.ssh_port) -Credential $cred -AcceptKey -ConnectionTimeout 30 -ErrorAction Stop
    try {
        Write-Host "Upload ..." -ForegroundColor Cyan
        Set-SCPItem -ComputerName $Cfg.ssh_host -Port ([int]$Cfg.ssh_port) -Credential $cred -Path $RemoteArchive -Destination "/tmp/" -AcceptKey -ConnectionTimeout 30

        $remoteName = [IO.Path]::GetFileName($RemoteArchive)
        $appDir = $Cfg.remote_app_dir
        $sup = $Cfg.supervisor_name
        $fullFlag = if ($FullData) { "1" } else { "0" }
        $remoteScript = @"
set -e
APP_DIR='$appDir'
STAGING='/tmp/wkt-sync-staging'
ARCH='/tmp/$remoteName'
rm -rf "`$STAGING"
mkdir -p "`$STAGING"
case "`$ARCH" in
  *.tar.gz|*.tgz) tar -xaf "`$ARCH" -C "`$STAGING" ;;
  *.zip) unzip -oq "`$ARCH" -d "`$STAGING" ;;
  *) tar -xaf "`$ARCH" -C "`$STAGING" 2>/dev/null || unzip -oq "`$ARCH" -d "`$STAGING" ;;
esac
export WKT_APP_DIR="`$APP_DIR"
export WKT_SUPERVISOR_NAME='$sup'
export WKT_FULL_DATA_SYNC='$fullFlag'
bash "`$STAGING/scripts/server-merge-update.sh" "`$STAGING"
rm -f "`$ARCH"
rm -rf "`$STAGING"
curl -s '${Cfg.health_url}' || true
"@
        # Windows CRLF breaks bash on Linux (case ... in\r syntax error)
        $remoteScript = ($remoteScript -replace "`r`n", "`n") -replace "`r", "`n"

        if ($FullData) {
            Write-Host "Merge on server (FULL data overwrite) ..." -ForegroundColor Yellow
        } elseif ($WithMasterData) {
            Write-Host "Merge on server (code + master JSON; order DB untouched) ..." -ForegroundColor Yellow
        } else {
            Write-Host "Merge on server (code only; cloud data preserved) ..." -ForegroundColor Green
        }
        $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $remoteScript -TimeOut 120
        Write-Host $result.Output
        if ($result.ExitStatus -ne 0) {
            Write-Host $result.Error
            throw "Remote merge failed (exit $($result.ExitStatus))"
        }
    } finally {
        Remove-SSHSession -SessionId $session.SessionId | Out-Null
    }
}

Write-Host ""
if ($FullData) {
    Write-Host "=== WKT FULL sync to cloud (code + entire data/) ===" -ForegroundColor Yellow
    Write-Host "Will overwrite cloud wkt_orders.db and delivery_notes with local copy." -ForegroundColor Yellow
    Write-Host "Cloud data/ will be backed up to data.bak-timestamp/ on server." -ForegroundColor DarkGray
    if (-not $PackOnly) {
        Write-Host ""
        Write-Host "Edit config\deploy.local.json ssh_password (root SSH) before continue." -ForegroundColor DarkGray
        $confirm = Read-Host "Type YES to overwrite ALL cloud data"
        if ($confirm -ne "YES") {
            Write-Host "Cancelled (must type YES)." -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host "=== WKT sync to cloud (code only) ===" -ForegroundColor Cyan
}
. (Join-Path $PSScriptRoot "data-sync-rules.ps1")
Show-WktDataSyncPolicy -FullData:$FullData -WithMasterData:$WithMasterData
Write-Host "Also sync: test_impl + scripts" -ForegroundColor DarkGray
Write-Host "NOT touched on server: order DB, delivery_notes, customer/supplier JSON (except feishu_config.json)" -ForegroundColor DarkGray
Write-Host ""

$cfg = Load-Config
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$staging = Join-Path $env:TEMP "wkt-sync-$stamp"
$releaseDir = Join-Path $root "release"
$ext = if (Get-Command tar -ErrorAction SilentlyContinue) { "tar.gz" } else { "zip" }
$archive = Join-Path $releaseDir "wkt-sync-$stamp.$ext"

Build-Staging -StagingDir $staging -FullData:$FullData -WithMasterData:$WithMasterData
New-Archive -StagingDir $staging -ArchivePath $archive
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue

if ($PackOnly) {
    Write-Host "Pack only. Upload $archive manually if needed." -ForegroundColor Yellow
    exit 0
}

Invoke-RemoteMerge -Cfg $cfg -RemoteArchive $archive -StagingDir $staging -FullData:$FullData

Write-Host ""
Write-Host "Done. Open http://$($cfg.ssh_host):8088/ and hard-refresh (Ctrl+F5)." -ForegroundColor Green
