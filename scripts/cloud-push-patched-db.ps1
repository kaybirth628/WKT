# 上传已回写供应商全称的 wkt_orders.db 到云端（仅替换订单库文件，不动其它 JSON）
param(
    [string]$LocalDb = "",
    [switch]$SkipSupervisorRestart
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg

$localPath = if ($LocalDb) { $LocalDb } else { Join-Path $root "data\bom_import_audit\cloud_db_work\wkt_orders.db" }
if (!(Test-Path $localPath)) {
    throw "Local DB not found: $localPath"
}

$appDir = [string]$cfg.remote_app_dir
$sup = [string]$cfg.supervisor_name
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteData = "$appDir/data"
$remoteDb = "$remoteData/wkt_orders.db"

$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey
try {
    Write-Host "Stop supervisor $sup ..." -ForegroundColor Cyan
    $stop = Invoke-SSHCommand -SessionId $session.SessionId -Command "supervisorctl stop $sup 2>/dev/null || true; sleep 1"
    Write-Host ($stop.Output -join "`n")

    Write-Host "Backup cloud DB ..." -ForegroundColor Cyan
    $backup = Invoke-SSHCommand -SessionId $session.SessionId -Command @"
set -e
cd '$remoteData'
cp -f wkt_orders.db wkt_orders.db.bak-supplier-push-$stamp
rm -f wkt_orders.db-wal wkt_orders.db-shm
echo backup=wkt_orders.db.bak-supplier-push-$stamp
"@
    Write-Host ($backup.Output -join "`n")

    Write-Host "Upload patched DB ..." -ForegroundColor Cyan
    Set-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $localPath -Destination "/root/" -AcceptKey -ConnectionTimeout 180
    $install = Invoke-SSHCommand -SessionId $session.SessionId -Command @"
set -e
cp -f /root/wkt_orders.db '$remoteDb'
chmod 666 '$remoteDb' || true
rm -f '$remoteData/wkt_orders.db-wal' '$remoteData/wkt_orders.db-shm'
cd '$appDir'
PY=""
for c in python3 python; do command -v "`$c" >/dev/null 2>&1 && PY="`$c" && break; done
"`$PY" scripts/backfill_bom_supplier_names.py --db data/wkt_orders.db > /root/cloud_push_verify.txt || true
cat /root/cloud_push_verify.txt
"@
    Write-Host ($install.Output -join "`n")

    if (-not $SkipSupervisorRestart) {
        Write-Host "Start supervisor $sup ..." -ForegroundColor Cyan
        $start = Invoke-SSHCommand -SessionId $session.SessionId -Command "supervisorctl start $sup; sleep 1; supervisorctl status $sup"
        Write-Host ($start.Output -join "`n")
    }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
Write-Host "Cloud DB supplier backfill upload done." -ForegroundColor Green
