# 从云端拉取 data/ 到本地（云端为主；本地 data 先备份）
# Usage: powershell -ExecutionPolicy Bypass -File scripts\pull-data-from-cloud.ps1
# Optional: -IncludeDeliveryNotes  同时拉 delivery_notes/

param(
    [switch]$IncludeDeliveryNotes
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

$configPath = Join-Path $root "config\deploy.local.json"
if (!(Test-Path $configPath)) {
    throw "Missing config\deploy.local.json"
}

function Ensure-PoshSsh {
    if (Get-Module -ListAvailable -Name Posh-SSH) { return }
    Install-Module Posh-SSH -Scope CurrentUser -Force -AllowClobber
}

. (Join-Path $PSScriptRoot "ssh-auth.ps1")

$cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

Ensure-PoshSsh
Import-Module Posh-SSH -ErrorAction Stop
$cred = Get-WktSshCredential -Cfg $cfg

$localData = Join-Path $root "data"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$localBackup = Join-Path $root "data.local.bak-$stamp"
if (Test-Path $localData) {
    Write-Host "Backup local data/ -> $localBackup" -ForegroundColor Cyan
    Copy-Item $localData $localBackup -Recurse -Force
}

$appDir = $cfg.remote_app_dir
$remoteArchive = "/tmp/wkt-data-pull-$stamp.tar.gz"
$includeFlag = if ($IncludeDeliveryNotes) { "1" } else { "0" }
$remoteScript = @"
set -e
APP='$appDir'
ARCH='$remoteArchive'
cd "`$APP"
if [ '$includeFlag' = '1' ]; then
  tar -czf "`$ARCH" --exclude='delivery_templates/files' data
else
  tar -czf "`$ARCH" --exclude='delivery_notes' --exclude='delivery_templates/files' data
fi
ls -lh "`$ARCH"
"@

$remoteScript = ($remoteScript -replace "`r`n", "`n") -replace "`r", "`n"
$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey -ConnectionTimeout 30
try {
    Write-Host "Pack cloud data on server ..." -ForegroundColor Cyan
    $pack = Invoke-SSHCommand -SessionId $session.SessionId -Command $remoteScript -TimeOut 180
    Write-Host $pack.Output
    if ($pack.ExitStatus -ne 0) { throw "Remote pack failed: $($pack.Error)" }

    $localTar = Join-Path $env:TEMP "wkt-data-pull-$stamp.tar.gz"
    $localTarDir = Split-Path $localTar -Parent
    Write-Host "Download $remoteArchive ..." -ForegroundColor Cyan
    Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $remoteArchive -Destination $localTarDir -AcceptKey -ConnectionTimeout 120 -PathType File

    $downloaded = Join-Path $localTarDir ([IO.Path]::GetFileName($remoteArchive))
    if (!(Test-Path $downloaded)) {
        throw "Download failed: $downloaded not found"
    }

    New-Item -ItemType Directory -Path $localData -Force | Out-Null
    $extractPy = Join-Path $PSScriptRoot "extract-data-tar.py"
    if (!(Test-Path $extractPy)) {
        throw "Missing $extractPy"
    }
    Write-Host "Extract to $root (Python UTF-8) ..." -ForegroundColor Cyan
    & python $extractPy $downloaded $root
    if ($LASTEXITCODE -ne 0) {
        throw "Extract failed (python exit $LASTEXITCODE)"
    }

    $suppliersPath = Join-Path $localData "supplier_profiles.json"
    if (Test-Path $suppliersPath) {
        try {
            $n = (& python -c "import json; print(len(json.load(open(r'$suppliersPath',encoding='utf-8'))))")
            Write-Host "Local supplier_profiles.json: $n suppliers" -ForegroundColor Green
        } catch {
            Write-Host "Local supplier_profiles.json updated." -ForegroundColor Green
        }
    }

    Remove-Item $downloaded -Force -ErrorAction SilentlyContinue
    Invoke-SSHCommand -SessionId $session.SessionId -Command "rm -f '$remoteArchive'" -TimeOut 30 | Out-Null
    Write-Host ""
    Write-Host "Done. Local data/ updated from cloud." -ForegroundColor Green
    Write-Host "Local backup: $localBackup" -ForegroundColor DarkGray
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
