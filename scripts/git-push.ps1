# WKT: commit and push to GitHub (master), optional milestone tag
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -Message "CL-0104: summary"
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -PushOnly
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -Version "v0.6.0"

param(
    [string]$Message = "",
    [string]$Version = "",
    [switch]$PushOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Get-DocVersion {
    $path = Join-Path $root "docs\VERSION.md"
    if (!(Test-Path $path)) { return "" }
    $text = Get-Content $path -Raw -Encoding UTF8
    if ($text -match '\*\*(v\d+\.\d+\.\d+)\*\*') {
        return $Matches[1]
    }
    return ""
}

function Get-LatestGitTag {
    $tag = git describe --tags --abbrev=0 2>$null
    if ($LASTEXITCODE -ne 0) { return "" }
    return $tag.Trim()
}

function Normalize-VersionTag([string]$raw) {
    $v = $raw.Trim()
    if (-not $v) { return "" }
    if ($v -notmatch '^v') { $v = "v$v" }
    if ($v -notmatch '^v\d+\.\d+\.\d+$') {
        throw "Invalid version tag (use v0.6.0): $raw"
    }
    return $v
}

function Show-VersionHelp {
    $docVer = Get-DocVersion
    $gitTag = Get-LatestGitTag
    Write-Host ""
    Write-Host "=== Version / CHANGELOG ===" -ForegroundColor Cyan
    Write-Host "  CL-XXXX  : daily commit message"
    Write-Host "  v0.x.x   : optional milestone git tag"
    if ($docVer) { Write-Host "  VERSION.md: $docVer" -ForegroundColor DarkGray }
    if ($gitTag) { Write-Host "  Latest tag: $gitTag" -ForegroundColor DarkGray }
    Write-Host ""
}

function Show-Status {
    Write-Host "=== git status ===" -ForegroundColor Cyan
    git status -sb
    Write-Host ""
}

function Assert-NoDatabaseStaged {
    $staged = @(git diff --cached --name-only 2>$null)
    if ($LASTEXITCODE -ne 0) { return }
    $dbFiles = $staged | Where-Object {
        $_ -match '(^|/)data/.*\.db(\.|$|-journal$|-wal$|-shm$)' -or $_ -match '\.db\.bak'
    }
    if ($dbFiles) {
        throw "Refusing to commit order database files: $($dbFiles -join ', ')"
    }
}

function Show-DataCommitPolicy {
    Write-Host ""
    Write-Host "=== Data commit policy ===" -ForegroundColor Cyan
    Write-Host "  Will commit: customer_profiles, delivery_templates, supplier_profiles, feishu_config, ..." -ForegroundColor DarkGray
    Write-Host "  Will NOT commit: *.db, delivery_notes/attachments, secrets, deploy.local.json" -ForegroundColor DarkGray
    Write-Host ""
}

Show-DataCommitPolicy
Show-VersionHelp
Show-Status

if (-not $PushOnly) {
    $pending = git status --porcelain
    if ($pending) {
        if (-not $Message.Trim()) {
            $Message = Read-Host "Commit message (e.g. CL-0108: summary)"
        }
        if (-not $Message.Trim()) {
            throw "Commit message required."
        }
        git add -A
        Assert-NoDatabaseStaged
        git commit -m $Message
        Write-Host "Committed: $Message" -ForegroundColor Green
    }
    else {
        Write-Host "No local changes; push only." -ForegroundColor Yellow
    }
}

if (-not $Version.Trim()) {
    $Version = Read-Host "Milestone tag? empty=skip, e.g. v0.6.0"
}
$Version = Normalize-VersionTag $Version

Write-Host "Pushing origin/master ..." -ForegroundColor Cyan
git push origin master
if ($LASTEXITCODE -ne 0) {
    throw "git push failed."
}

if ($Version) {
    $exists = git tag -l $Version
    if ($exists) {
        Write-Host "Tag $Version exists; pushing tag only." -ForegroundColor Yellow
    }
    else {
        git tag -a $Version -m "Release $Version"
        Write-Host "Created tag $Version" -ForegroundColor Green
    }
    git push origin $Version
    if ($LASTEXITCODE -ne 0) {
        throw "git push tag failed."
    }
    Write-Host "Pushed tag $Version" -ForegroundColor Green
    Write-Host "Update docs/VERSION.md and CHANGELOG if needed." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Done: https://github.com/kaybirth628/WKT" -ForegroundColor Green
