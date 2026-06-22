param(
    [Parameter(Mandatory = $false)]
    [string]$Path = "."
)

$ErrorActionPreference = "Stop"

if (!(Test-Path "src")) { throw "Missing src directory." }
if (!(Test-Path "test_impl")) { New-Item -ItemType Directory -Path "test_impl" | Out-Null }

$srcPath = Join-Path "src" $Path
$dstPath = Join-Path "test_impl" $Path

if (!(Test-Path $srcPath)) { throw "Source path not found: $srcPath" }

New-Item -ItemType Directory -Path (Split-Path -Parent $dstPath) -Force | Out-Null
Copy-Item -Path $srcPath -Destination $dstPath -Recurse -Force

Write-Host "Synced to test_impl:" $Path
