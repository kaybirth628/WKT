# 云端 BOM 工序供应商简称 -> 全称（仅 cost_records.process_prices_json）
# Usage: powershell -ExecutionPolicy Bypass -File scripts\cloud-backfill-bom-suppliers.ps1
param([switch]$SkipBackup)

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

$appDir = [string]$cfg.remote_app_dir
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$localScript = Join-Path $root "scripts\backfill_bom_supplier_names.py"
if (!(Test-Path $localScript)) {
    throw "Missing scripts/backfill_bom_supplier_names.py"
}

$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey -ConnectionTimeout 30 -ErrorAction Stop
try {
    Write-Host "Upload backfill script ..." -ForegroundColor Cyan
    Set-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $localScript -Destination "/root/" -AcceptKey -ConnectionTimeout 60

$skipBackupFlag = if ($SkipBackup) { "1" } else { "0" }
    $remoteScript = @"
set -e
APP='$appDir'
DB="`$APP/data/wkt_orders.db"
STAMP='$stamp'
SKIP_BACKUP='$skipBackupFlag'
PY=""
for c in python3 python; do
  if command -v "`$c" >/dev/null 2>&1; then PY="`$c"; break; fi
done
if [ -z "`$PY" ]; then echo "python not found"; exit 1; fi
if [ ! -f "`$DB" ]; then echo "DB missing: `$DB"; exit 1; fi
if [ "`$SKIP_BACKUP" != "1" ]; then
  cp "`$DB" "`$DB.bak-supplier-`$STAMP"
  echo "Backup: `$DB.bak-supplier-`$STAMP"
fi
mkdir -p "`$APP/scripts"
cp /root/backfill_bom_supplier_names.py "`$APP/scripts/backfill_bom_supplier_names.py"
cd "`$APP"
echo "=== ENV CHECK ==="
"`$PY" -c "import sys; sys.path.insert(0,'.'); from test_impl.order_management.supplier_profile.store import list_profile_suppliers, resolve_supplier_name; print('profiles', len(list_profile_suppliers())); s='\\u9ea6\\u51ef\\u826f'; r,n=resolve_supplier_name(s); print('sample', s, '->', r)"
ls -la scripts/backfill_bom_supplier_names.py data/wkt_orders.db data/supplier_profiles.json
echo "=== DRY-RUN ==="
PYTHONPATH="`$APP" "`$PY" "`$APP/scripts/backfill_bom_supplier_names.py" --db "`$APP/data/wkt_orders.db"
echo "=== APPLY ==="
PYTHONPATH="`$APP" "`$PY" "`$APP/scripts/backfill_bom_supplier_names.py" --db "`$APP/data/wkt_orders.db" --apply
echo "=== POST CHECK ==="
PYTHONPATH="`$APP" "`$PY" "`$APP/scripts/backfill_bom_supplier_names.py" --db "`$APP/data/wkt_orders.db" > /root/cloud_supplier_backfill_post.txt
cat /root/cloud_supplier_backfill_post.txt
"@
    $remoteScript = ($remoteScript -replace "`r`n", "`n") -replace "`r", "`n"
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $remoteScript -TimeOut 180
    Write-Host $result.Output
    $reportLocal = Join-Path $root "data\bom_import_audit\cloud_supplier_backfill_post.txt"
    New-Item -ItemType Directory -Force -Path (Split-Path $reportLocal) | Out-Null
    Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path "/root/cloud_supplier_backfill_post.txt" -Destination (Split-Path $reportLocal) -AcceptKey -ConnectionTimeout 60 -PathType File
    if (Test-Path (Join-Path (Split-Path $reportLocal) "cloud_supplier_backfill_post.txt")) {
        Move-Item -Force (Join-Path (Split-Path $reportLocal) "cloud_supplier_backfill_post.txt") $reportLocal
        Write-Host "Report saved: $reportLocal" -ForegroundColor DarkGray
    }
    if ($result.ExitStatus -ne 0) {
        if ($result.Error) { Write-Host $result.Error -ForegroundColor Red }
        throw "Remote backfill failed (exit $($result.ExitStatus))"
    }
    Write-Host "Cloud BOM supplier backfill done." -ForegroundColor Green
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
