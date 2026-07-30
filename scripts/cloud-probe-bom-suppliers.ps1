# 仅查看云端 BOM 供应商现状（不写库）
param([switch]$Apply)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
if (-not (Get-Module -ListAvailable -Name Posh-SSH)) {
    Install-Module Posh-SSH -Scope CurrentUser -Force -AllowClobber
}
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$appDir = [string]$cfg.remote_app_dir
$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey
try {
    if ($Apply) {
        & (Join-Path $PSScriptRoot "cloud-backfill-bom-suppliers.ps1")
        return
    }
    $cmd = @"
cd '$appDir'
python3 - <<'PY'
import json, sqlite3, sys
from collections import Counter
sys.path.insert(0, ".")
from test_impl.order_management.supplier_profile.store import list_profile_suppliers, resolve_supplier_name
profiles = list_profile_suppliers()
profile_set = {p.casefold() for p in profiles}
print("profiles", len(profiles))
conn = sqlite3.connect("data/wkt_orders.db")
full = resolvable = unmatched = Counter()
for (raw,) in conn.execute("SELECT process_prices_json FROM cost_records"):
    pp = json.loads(raw or "{}")
    for k, v in pp.items():
        if k == "__order__" or not isinstance(v, dict):
            continue
        for s in [v.get("supplier")] + (v.get("suppliers") or []):
            s = str(s or "").strip()
            if not s or s == "场内自制":
                continue
            if s.casefold() in profile_set:
                full["ok"] += 1
            else:
                r, _ = resolve_supplier_name(s)
                if r.casefold() in profile_set and r != s:
                    resolvable[s] += 1
                else:
                    unmatched[s] += 1
print("full_in_db", full["ok"])
print("short_but_resolvable", sum(resolvable.values()))
for a,b in resolvable.most_common(10):
    r,_ = resolve_supplier_name(a)
    print(f"  {a!r} -> {r!r} x{b}")
print("unmatched", sum(unmatched.values()))
for a,b in unmatched.most_common(10):
    print(f"  {a!r} x{b}")
PY
"@
    $r = Invoke-SSHCommand -SessionId $session.SessionId -Command $cmd -TimeOut 120
    Write-Host $r.Output
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
