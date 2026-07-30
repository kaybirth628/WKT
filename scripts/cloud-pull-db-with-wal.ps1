# 拉取云端 wkt_orders.db（含 WAL 附属文件，若有）
param([string]$DestDir = "")

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path $root "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$remoteDir = "$($cfg.remote_app_dir)/data"
$dest = if ($DestDir) { $DestDir } else { Join-Path $root "data\bom_import_audit\cloud_db_work" }
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$session = New-SSHSession -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -AcceptKey
try {
    foreach ($name in @("wkt_orders.db", "wkt_orders.db-wal", "wkt_orders.db-shm")) {
        $remote = "$remoteDir/$name"
        $check = Invoke-SSHCommand -SessionId $session.SessionId -Command "test -f '$remote' && echo yes || echo no"
        if (($check.Output -join "").Trim() -ne "yes") {
            Write-Host "Skip missing $name"
            continue
        }
        Write-Host "Download $name ..."
        Get-SCPItem -ComputerName $cfg.ssh_host -Port ([int]$cfg.ssh_port) -Credential $cred -Path $remote -Destination $dest -AcceptKey -ConnectionTimeout 180 -PathType File
    }
} finally {
    Remove-SSHSession -SessionId $session.SessionId | Out-Null
}
Write-Host "Saved to $dest"
