$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$remote = "$($cfg.remote_app_dir)/data/supplier_profiles.json"
$dest = Join-Path $root "data\bom_import_audit\cloud_supplier_profiles.json"
Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $remote -Destination (Split-Path $dest) -AcceptKey -ConnectionTimeout 60 -PathType File
Move-Item -Force (Join-Path (Split-Path $dest) "supplier_profiles.json") $dest -ErrorAction SilentlyContinue
if (Test-Path (Join-Path (Split-Path $dest) "cloud_supplier_profiles.json")) { }
python -c "import json; from pathlib import Path; p=Path(r'$dest'); print('exists',p.exists(), 'count', len(json.loads(p.read_text(encoding='utf-8'))) if p.exists() else 0)"
