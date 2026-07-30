# 拉取云端 backfill 前 DB 备份到本地做对比（可选）
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$remote = "$($cfg.remote_app_dir)/data/wkt_orders.db.bak-supplier-20260730-100937"
$dest = Join-Path $root "data\bom_import_audit"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $remote -Destination $dest -AcceptKey -ConnectionTimeout 120 -PathType File
Write-Host "Downloaded to $dest"
