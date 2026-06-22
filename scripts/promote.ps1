param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [string]$ChangeId
)

$ErrorActionPreference = "Stop"

if (!(Test-Path "test_impl")) { throw "Missing test_impl directory." }
if (!(Test-Path "src")) { New-Item -ItemType Directory -Path "src" | Out-Null }

$testPath = Join-Path "test_impl" $Path
$srcPath = Join-Path "src" $Path

if (!(Test-Path $testPath)) { throw "Test path not found: $testPath" }

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path "release_backup" "$timestamp-$ChangeId"
$backupPath = Join-Path $backupRoot $Path

New-Item -ItemType Directory -Path (Split-Path -Parent $backupPath) -Force | Out-Null
if (Test-Path $srcPath) {
    Copy-Item -Path $srcPath -Destination $backupPath -Recurse -Force
}

New-Item -ItemType Directory -Path (Split-Path -Parent $srcPath) -Force | Out-Null
Copy-Item -Path $testPath -Destination $srcPath -Recurse -Force

$reportPath = Join-Path $backupRoot "promote-report.txt"
"change_id=$ChangeId" | Out-File $reportPath -Encoding utf8
"path=$Path" | Out-File $reportPath -Encoding utf8 -Append
"backup=$backupPath" | Out-File $reportPath -Encoding utf8 -Append
"time=$timestamp" | Out-File $reportPath -Encoding utf8 -Append

Write-Host "Promoted:" $Path
Write-Host "Backup:" $backupPath
Write-Host "Report:" $reportPath
