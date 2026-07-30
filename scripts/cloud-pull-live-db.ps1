$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$remote = "$($cfg.remote_app_dir)/data/wkt_orders.db"
$dest = Join-Path $root "data\bom_import_audit\cloud_wkt_orders_live.db"
New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $remote -Destination (Split-Path $dest) -AcceptKey -ConnectionTimeout 180 -PathType File
Move-Item -Force (Join-Path (Split-Path $dest) "wkt_orders.db") $dest
Write-Host "Saved $dest"
