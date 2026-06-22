param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFolder
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $BackupFolder)) { throw "Backup folder not found: $BackupFolder" }

$items = Get-ChildItem -Path $BackupFolder -Recurse -File | Where-Object {
    $_.Name -ne "promote-report.txt"
}

foreach ($item in $items) {
    $relative = $item.FullName.Substring((Resolve-Path $BackupFolder).Path.Length).TrimStart('\')
    $target = Join-Path "src" $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -Path $item.FullName -Destination $target -Force
}

Write-Host "Rollback complete from:" $BackupFolder
