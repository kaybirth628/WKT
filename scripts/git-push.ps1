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
$DebugLogPath = Join-Path $root "debug-21e439.log"

function Write-AgentDebugLog {
    param(
        [string]$HypothesisId,
        [string]$Location,
        [string]$Message,
        [hashtable]$Data = @{}
    )
    #region agent log
    try {
        $payload = @{
            sessionId    = "21e439"
            hypothesisId = $HypothesisId
            location     = $Location
            message      = $Message
            data         = $Data
            timestamp    = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        ($payload | ConvertTo-Json -Compress -Depth 6) + "`n" | Out-File -FilePath $DebugLogPath -Append -Encoding utf8
    } catch { }
    #endregion
}

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

function Get-LatestChangelogEntry {
    $path = Join-Path $root "docs\change\CHANGELOG.md"
    if (!(Test-Path $path)) { return $null }
    $text = Get-Content $path -Raw -Encoding UTF8
    if ($text -match '(?ms)^### (CL-\d+) · ([^\r\n]+).*?\| 变更内容 \| ([^\|]+) \|') {
        $summary = $Matches[3].Trim()
        if ($summary.Length -gt 72) { $summary = $summary.Substring(0, 69) + "..." }
        return [PSCustomObject]@{
            Cl      = $Matches[1]
            Meta    = $Matches[2].Trim()
            Summary = $summary
        }
    }
    if ($text -match '(?m)^### (CL-(\d+)) · ([^\r\n]+)') {
        return [PSCustomObject]@{
            Cl      = $Matches[1]
            Meta    = $Matches[3].Trim()
            Summary = ""
        }
    }
    return $null
}

function Get-RecommendedCommitMessage {
    $entry = Get-LatestChangelogEntry
    if ($entry) {
        if ($entry.Summary) {
            return "$($entry.Cl): $($entry.Summary)"
        }
        return "$($entry.Cl): $($entry.Meta)"
    }
    $max = 0
    $clPath = Join-Path $root "docs\change\CHANGELOG.md"
    if (Test-Path $clPath) {
        $text = Get-Content $clPath -Raw -Encoding UTF8
        foreach ($m in [regex]::Matches($text, 'CL-(\d+)')) {
            $n = [int]$m.Groups[1].Value
            if ($n -gt $max) { $max = $n }
        }
    }
    $next = $max + 1
    return ("CL-{0:D4}: sync" -f $next)
}

function Read-CommitMessageWithDefault {
    param([string]$Default)
    Write-Host ""
    Write-Host "Recommended commit (from CHANGELOG top entry):" -ForegroundColor Cyan
    Write-Host "  $Default" -ForegroundColor Green
    Write-Host "Press Enter to use it, or type to override." -ForegroundColor DarkGray
    $input = Read-Host "Commit message"
    if (-not $input.Trim()) { return $Default }
    return $input.Trim()
}

function Read-MilestoneTagOptional {
    $docVer = Get-DocVersion
    Write-Host ""
    Write-Host "Milestone git tag: usually skip for daily commits." -ForegroundColor DarkGray
    if ($docVer) { Write-Host "  VERSION.md current: $docVer (only tag on big releases)" -ForegroundColor DarkGray }
    Write-Host "Press Enter to skip, or type e.g. v0.6.1" -ForegroundColor DarkGray
    $input = Read-Host "Milestone tag"
    return $input.Trim()
}

function Show-VersionHelp {
    $docVer = Get-DocVersion
    $gitTag = Get-LatestGitTag
    $rec = Get-RecommendedCommitMessage
    Write-Host ""
    Write-Host "=== Version / CHANGELOG ===" -ForegroundColor Cyan
    Write-Host "  Recommended : $rec" -ForegroundColor Green
    Write-Host "  CL-XXXX     : daily commit (auto from CHANGELOG.md top entry)" -ForegroundColor DarkGray
    Write-Host "  v0.x.x      : optional milestone git tag (usually skip)" -ForegroundColor DarkGray
    if ($docVer) { Write-Host "  VERSION.md  : $docVer" -ForegroundColor DarkGray }
    if ($gitTag) { Write-Host "  Latest tag  : $gitTag" -ForegroundColor DarkGray }
    Write-Host ""
}

function Show-Status {
    Write-Host "=== git status ===" -ForegroundColor Cyan
    git status -sb
    Write-Host ""
}

function Test-IsBlockedGitPath {
    param([string]$Path)
    if ($Path -match '^data\.local\.bak-') { return $true }
    if ($Path -match '(^|/)data/.*\.db(\.|$|-journal$|-wal$|-shm$)') { return $true }
    if ($Path -match '\.db\.bak') { return $true }
    return $false
}

function Reset-StagedBackupPaths {
    $staged = @(git diff --cached --name-only 2>$null)
    if ($LASTEXITCODE -ne 0) { return @() }
    $bak = @($staged | Where-Object { Test-IsBlockedGitPath $_ })
    if ($bak.Count -gt 0) {
        git reset HEAD -- "data.local.bak-*" 2>$null | Out-Null
        $staged = @(git diff --cached --name-only 2>$null)
        $bak = @($staged | Where-Object { Test-IsBlockedGitPath $_ })
        foreach ($p in $bak) {
            git reset HEAD -- $p 2>$null | Out-Null
        }
    }
    Write-AgentDebugLog -HypothesisId "A" -Location "git-push.ps1:Reset-StagedBackupPaths" -Message "unstage blocked paths" -Data @{ count = $bak.Count; sample = @($bak | Select-Object -First 5) }
    return $bak
}

function Invoke-SafeGitStage {
    $resetBefore = Reset-StagedBackupPaths
    git add -A
    if ($LASTEXITCODE -ne 0) { throw "git add failed" }
    $resetAfter = Reset-StagedBackupPaths
    $staged = @(git diff --cached --name-only 2>$null)
    Write-AgentDebugLog -HypothesisId "B" -Location "git-push.ps1:Invoke-SafeGitStage" -Message "after safe stage" -Data @{
        resetBefore = $resetBefore.Count
        resetAfter  = $resetAfter.Count
        stagedCount = $staged.Count
        blockedLeft = @($staged | Where-Object { Test-IsBlockedGitPath $_ }).Count
    }
}

function Assert-NoDatabaseStaged {
    $staged = @(git diff --cached --name-only 2>$null)
    if ($LASTEXITCODE -ne 0) { return }
    $dbFiles = @($staged | Where-Object { Test-IsBlockedGitPath $_ })
    Write-AgentDebugLog -HypothesisId "C" -Location "git-push.ps1:Assert-NoDatabaseStaged" -Message "assert check" -Data @{ blocked = $dbFiles.Count; sample = @($dbFiles | Select-Object -First 5) }
    if ($dbFiles) {
        throw "Refusing to commit database/backup files: $($dbFiles -join ', '). These paths are gitignored (data.local.bak-* / *.db)."
    }
}

function Show-DataCommitPolicy {
    Write-Host ""
    Write-Host "=== Data commit policy ===" -ForegroundColor Cyan
    Write-Host "  Will commit: customer_profiles, delivery_templates, supplier_profiles, feishu_config, ..." -ForegroundColor DarkGray
    Write-Host "  Will NOT commit: *.db, data.local.bak-*, delivery_notes/attachments, secrets" -ForegroundColor DarkGray
    Write-Host ""
}

Show-DataCommitPolicy
Show-VersionHelp
Show-Status

if (-not $PushOnly) {
    $pending = git status --porcelain
    if ($pending) {
        if (-not $Message.Trim()) {
            $defaultMsg = Get-RecommendedCommitMessage
            $Message = Read-CommitMessageWithDefault -Default $defaultMsg
        }
        if (-not $Message.Trim()) {
            throw "Commit message required."
        }
        Invoke-SafeGitStage
        Assert-NoDatabaseStaged
        git commit -m $Message
        Write-Host "Committed: $Message" -ForegroundColor Green
    }
    else {
        Write-Host "No local changes; push only." -ForegroundColor Yellow
    }
}

function Invoke-GitPushWithRetry {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [string]$Label = "git push"
    )
    $max = 3
    for ($i = 1; $i -le $max; $i++) {
        & git @Args
        if ($LASTEXITCODE -eq 0) { return }
        if ($i -lt $max) {
            Write-Host "$Label failed (attempt $i/$max); retry in 5s ..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    Write-Host ""
    Write-Host "GitHub push failed: network cannot reach github.com (443)." -ForegroundColor Red
    Write-Host "Your commit is saved locally. Try:" -ForegroundColor Yellow
    Write-Host "  1) VPN / proxy, then run this script again with -PushOnly" -ForegroundColor DarkGray
    Write-Host "  2) Or: git push origin master" -ForegroundColor DarkGray
    Write-Host "  3) Cloud deploy: 一键推送云端和GitHub.bat (code only; never overwrites cloud data/)" -ForegroundColor DarkGray
    Write-Host ""
    throw "$Label failed."
}

if (-not $Version.Trim()) {
    $Version = Read-MilestoneTagOptional
}
$Version = Normalize-VersionTag $Version

Write-Host "Pushing origin/master ..." -ForegroundColor Cyan
Invoke-GitPushWithRetry -Args @("push", "origin", "master") -Label "git push origin master"

if ($Version) {
    $exists = git tag -l $Version
    if ($exists) {
        Write-Host "Tag $Version exists; pushing tag only." -ForegroundColor Yellow
    }
    else {
        git tag -a $Version -m "Release $Version"
        Write-Host "Created tag $Version" -ForegroundColor Green
    }
    Invoke-GitPushWithRetry -Args @("push", "origin", $Version) -Label "git push tag $Version"
    Write-Host "Pushed tag $Version" -ForegroundColor Green
    Write-Host "Update docs/VERSION.md and CHANGELOG if needed." -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Done: https://github.com/kaybirth628/WKT" -ForegroundColor Green
