# 云端 SQLite WAL checkpoint（不改动业务数据，仅合并 WAL 到主库）
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$appDir = [string]$cfg.remote_app_dir
$sup = [string]$cfg.supervisor_name

$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey
try {
    $cmd = @"
set -e
APP='$appDir'
DB="`$APP/data/wkt_orders.db"
supervisorctl stop '$sup' 2>/dev/null || true
sleep 1
PY=""
for c in python3 python; do command -v "`$c" >/dev/null 2>&1 && PY="`$c" && break; done
cd "`$APP"
"`$PY" -c "import sqlite3; c=sqlite3.connect('data/wkt_orders.db'); c.execute('PRAGMA wal_checkpoint(FULL)'); print('checkpoint', c.execute('PRAGMA wal_checkpoint(FULL)').fetchone()); c.close()"
ls -la data/wkt_orders.db data/wkt_orders.db-wal 2>/dev/null || true
supervisorctl start '$sup'
supervisorctl status '$sup' || true
"@
    $cmd = ($cmd -replace "`r`n", "`n") -replace "`r", "`n"
    $r = Invoke-SSHCommand -SessionId $session.SessionId -Command $cmd -TimeOut 120
    Write-Host ($r.Output -join "`n")
    if ($r.ExitStatus -ne 0) { throw "checkpoint failed" }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
Write-Host "WAL checkpoint done." -ForegroundColor Green
