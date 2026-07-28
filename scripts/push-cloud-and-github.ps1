# Push to GitHub then deploy CODE-ONLY to cloud (never overwrite cloud business data).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\push-cloud-and-github.ps1
# Optional passthrough: -Message "CL-0201: ..."  -PushOnly  -PackOnly

param(
    [string]$Message = "",
    [string]$Version = "",
    [switch]$PushOnly,
    [switch]$PackOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Write-Host ""
Write-Host "=== WKT: GitHub + Cloud (CODE ONLY) ===" -ForegroundColor Cyan
Write-Host "Cloud production data/ is NEVER overwritten by this script." -ForegroundColor Green
Write-Host "See docs/change/PRODUCTION-SAFETY.md" -ForegroundColor DarkGray
Write-Host ""

$gitArgs = @()
if ($Message) { $gitArgs += "-Message"; $gitArgs += $Message }
if ($Version) { $gitArgs += "-Version"; $gitArgs += $Version }
if ($PushOnly) { $gitArgs += "-PushOnly" }

Write-Host "--- Step 1/2: GitHub ---" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "git-push.ps1") @gitArgs
if ($LASTEXITCODE -ne 0) { throw "git-push.ps1 failed" }

if ($PushOnly) {
    Write-Host "PushOnly: skip cloud deploy." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "--- Step 2/2: Cloud deploy (code + feishu_config only) ---" -ForegroundColor Cyan
$syncArgs = @()
if ($PackOnly) { $syncArgs += "-PackOnly" }
& (Join-Path $PSScriptRoot "sync-to-cloud.ps1") @syncArgs
if ($LASTEXITCODE -ne 0) { throw "sync-to-cloud.ps1 failed" }

Write-Host ""
Write-Host "All done: GitHub pushed + cloud code updated." -ForegroundColor Green
