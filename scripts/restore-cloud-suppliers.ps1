# 从云端 data.bak-* 恢复 supplier_profiles.json（取备份中供应商数最多的一份）
# Usage: powershell -ExecutionPolicy Bypass -File scripts\restore-cloud-suppliers.ps1
#        powershell ... -BackupPath "/www/.../data.bak-20260724160700"

param(
    [string]$BackupPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $root "config\deploy.local.json"
if (!(Test-Path $configPath)) { throw "Missing config\deploy.local.json" }

function Ensure-PoshSsh {
    if (Get-Module -ListAvailable -Name Posh-SSH) { return }
    Install-Module Posh-SSH -Scope CurrentUser -Force -AllowClobber
}

. (Join-Path $PSScriptRoot "ssh-auth.ps1")

$cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json

Ensure-PoshSsh
Import-Module Posh-SSH -ErrorAction Stop
$cred = Get-WktSshCredential -Cfg $cfg

$appDir = $cfg.remote_app_dir
$bakArg = if ($BackupPath) { "'$BackupPath'" } else { '""' }
$remoteScript = @"
set -e
APP='$appDir'
TARGET="`$APP/data/supplier_profiles.json"
BAK_ARG=$bakArg
pick=""
if [ -n "`$BAK_ARG" ]; then
  pick="`$BAK_ARG"
else
  best=0
  for bak in `$(ls -1dt "`$APP"/data.bak-* 2>/dev/null); do
    for f in "`$bak/supplier_profiles.json" "`$bak/data/supplier_profiles.json"; do
      if [ -f "`$f" ]; then
        n=`$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1],encoding='utf-8'))))" "`$f" 2>/dev/null || echo 0)
        if [ "`$n" -gt "`$best" ]; then best="`$n"; pick="`$f"; fi
      fi
    done
  done
fi
if [ -z "`$pick" ] || [ ! -f "`$pick" ]; then
  echo "No supplier_profiles backup found under `$APP/data.bak-*"
  exit 1
fi
stamp=`$(date +%Y%m%d%H%M%S)
cp -a "`$TARGET" "`$TARGET.before-restore-`$stamp" 2>/dev/null || true
cp -a "`$pick" "`$TARGET"
n=`$(python3 -c "import json; print(len(json.load(open('$appDir/data/supplier_profiles.json',encoding='utf-8')))")
echo "Restored supplier_profiles.json from: `$pick"
echo "Supplier count now: `$n"
echo "Previous file backed up as: `$TARGET.before-restore-`$stamp (if existed)"
"@

$remoteScript = ($remoteScript -replace "`r`n", "`n") -replace "`r", "`n"
$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey -ConnectionTimeout 30
try {
    Write-Host "Restore cloud supplier_profiles.json from backup ..." -ForegroundColor Cyan
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $remoteScript -TimeOut 90
    Write-Host $result.Output
    if ($result.ExitStatus -ne 0) {
        Write-Host $result.Error -ForegroundColor Red
        exit $result.ExitStatus
    }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}

Write-Host "Done. Refresh supplier list on cloud (Ctrl+F5)." -ForegroundColor Green
