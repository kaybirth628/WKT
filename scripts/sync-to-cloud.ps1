# One-click sync local code to cloud (test_impl + scripts + whitelisted master data).
# Server DB, customer profiles, config, venv are NOT overwritten.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\sync-to-cloud.ps1
# Config: copy config\deploy.local.example.json -> config\deploy.local.json

param(
    [switch]$PackOnly
)

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
    param([string]$StagingDir)
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

    # Master data only — never sync DB or customer profiles here.
    $dataWhitelist = @(
        "data\supplier_profiles.json"
    )
    foreach ($rel in $dataWhitelist) {
        $src = Join-Path $root $rel
        if (!(Test-Path $src)) { continue }
        $dest = Join-Path $StagingDir $rel
        $destDir = Split-Path $dest -Parent
        if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
        Copy-Item $src $dest -Force
        Write-Host "Pack $rel ..." -ForegroundColor Cyan
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
    param($Cfg, [string]$RemoteArchive, [string]$StagingDir)

    Ensure-PoshSsh
    Import-Module Posh-SSH -ErrorAction Stop

    $pass = $Cfg.ssh_password
    if (-not $pass) {
        $sec = Read-Host "SSH password (root)" -AsSecureString
        $pass = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        )
    }

    $cred = New-Object System.Management.Automation.PSCredential($Cfg.ssh_user, (
            ConvertTo-SecureString $pass -AsPlainText -Force
        ))

    $session = New-SSHSession -ComputerName $Cfg.ssh_host -Port ([int]$Cfg.ssh_port) -Credential $cred -AcceptKey -ErrorAction Stop
    try {
        Write-Host "Upload ..." -ForegroundColor Cyan
        Set-SCPItem -ComputerName $Cfg.ssh_host -Port ([int]$Cfg.ssh_port) -Credential $cred -Path $RemoteArchive -Destination "/tmp/" -AcceptKey

        $remoteName = [IO.Path]::GetFileName($RemoteArchive)
        $appDir = $Cfg.remote_app_dir
        $sup = $Cfg.supervisor_name
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
bash "`$STAGING/scripts/server-merge-update.sh" "`$STAGING"
rm -f "`$ARCH"
rm -rf "`$STAGING"
curl -s '${Cfg.health_url}' || true
"@

        Write-Host "Merge on server (DB/customer/config/venv untouched) ..." -ForegroundColor Cyan
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
Write-Host "=== WKT sync to cloud ===" -ForegroundColor Cyan
Write-Host "Sync: test_impl + scripts + supplier_profiles.json" -ForegroundColor DarkGray
Write-Host "NOT touched: DB, customer_profiles, config, venv" -ForegroundColor DarkGray
Write-Host ""

$cfg = Load-Config
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$staging = Join-Path $env:TEMP "wkt-sync-$stamp"
$releaseDir = Join-Path $root "release"
$ext = if (Get-Command tar -ErrorAction SilentlyContinue) { "tar.gz" } else { "zip" }
$archive = Join-Path $releaseDir "wkt-sync-$stamp.$ext"

Build-Staging -StagingDir $staging
New-Archive -StagingDir $staging -ArchivePath $archive
Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue

if ($PackOnly) {
    Write-Host "Pack only. Upload $archive manually if needed." -ForegroundColor Yellow
    exit 0
}

Invoke-RemoteMerge -Cfg $cfg -RemoteArchive $archive -StagingDir $staging

Write-Host ""
Write-Host "Done. Open http://$($cfg.ssh_host):8088/ and hard-refresh (Ctrl+F5)." -ForegroundColor Green
