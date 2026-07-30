$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "ssh-auth.ps1")
$cfg = Get-Content (Join-Path (Split-Path $PSScriptRoot -Parent) "config\deploy.local.json") -Raw | ConvertFrom-Json
Import-Module Posh-SSH
$cred = Get-WktSshCredential -Cfg $cfg
$s = New-SSHSession -ComputerName $cfg.ssh_host -Port $cfg.ssh_port -Credential $cred -AcceptKey
$r = Invoke-SSHCommand -SessionId $s.SessionId -Command "supervisorctl start $($cfg.supervisor_name); supervisorctl status $($cfg.supervisor_name); curl -s $($cfg.health_url)"
Write-Host $r.Output
Remove-SSHSession $s.SessionId
