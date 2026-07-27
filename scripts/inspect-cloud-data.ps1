# 查询云端 data/ 概况（供应商数、备份目录、订单库大小等）
# Usage: powershell -ExecutionPolicy Bypass -File scripts\inspect-cloud-data.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
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

$appDir = $cfg.remote_app_dir
$remoteScript = @"
APP='$appDir'
echo "=== WKT cloud data inspect ==="
echo "APP_DIR: `$APP"
echo ""
count_suppliers() {
  python3 -c "import json,sys; p=sys.argv[1]; d=json.load(open(p,encoding='utf-8')); print(len(d))" "`$1" 2>/dev/null || echo "?"
}
if [ -f "`$APP/data/supplier_profiles.json" ]; then
  n=`$(count_suppliers "`$APP/data/supplier_profiles.json")
  echo "CURRENT supplier_profiles.json: `$n suppliers"
  python3 -c "
import json
d=json.load(open('$appDir/data/supplier_profiles.json',encoding='utf-8'))
for name in sorted(d.keys())[-20:]:
    print('  -', name)
" 2>/dev/null || true
else
  echo "CURRENT supplier_profiles.json: MISSING"
fi
echo ""
if [ -f "`$APP/data/customer_profiles.json" ]; then
  n=`$(count_suppliers "`$APP/data/customer_profiles.json")
  echo "CURRENT customer_profiles.json: `$n customers"
fi
if [ -f "`$APP/data/wkt_orders.db" ]; then
  ls -lh "`$APP/data/wkt_orders.db" | awk '{print "wkt_orders.db:", $5}'
fi
echo ""
echo "=== data.bak-* (newest 10, supplier count) ==="
ls -1dt "`$APP"/data.bak-* 2>/dev/null | head -10 | while read bak; do
  f=""
  if [ -f "`$bak/supplier_profiles.json" ]; then f="`$bak/supplier_profiles.json"; fi
  if [ -f "`$bak/data/supplier_profiles.json" ]; then f="`$bak/data/supplier_profiles.json"; fi
  if [ -n "`$f" ]; then
    n=`$(count_suppliers "`$f")
    echo "  `$bak -> `$n suppliers (`$f)"
  else
    echo "  `$bak -> (no supplier_profiles.json)"
  fi
done
echo ""
curl -s '${cfg.health_url}' 2>/dev/null | head -c 240 || true
echo ""
"@

$remoteScript = ($remoteScript -replace "`r`n", "`n") -replace "`r", "`n"
$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey -ConnectionTimeout 30
try {
    $result = Invoke-SSHCommand -SessionId $session.SessionId -Command $remoteScript -TimeOut 90
    Write-Host $result.Output
    if ($result.ExitStatus -ne 0) {
        Write-Host $result.Error -ForegroundColor Red
        exit $result.ExitStatus
    }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
