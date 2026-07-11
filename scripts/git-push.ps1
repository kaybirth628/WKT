# 一键：提交并推送到 GitHub（master），可选打里程碑版本标签
# 用法：
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -Message "CL-0104: 简述"
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -PushOnly
#   powershell -ExecutionPolicy Bypass -File scripts\git-push.ps1 -Version "v0.5.2"

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
    if ($text -match '\|\s*\*\*版本号\*\*\s*\|\s*\*\*(v[\d.]+)\*\*') {
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
        throw "版本号格式应为 v0.5.2 这类（三位数字），当前: $raw"
    }
    return $v
}

function Show-VersionHelp {
    $docVer = Get-DocVersion
    $gitTag = Get-LatestGitTag
    Write-Host ""
    Write-Host "=== 版本与变更（推送前）===" -ForegroundColor Cyan
    Write-Host "  CL-XXXX  ：每次改动的变更编号（写在提交说明 / CHANGELOG，日常推送用这个）"
    Write-Host "  v0.5.x   ：里程碑大版本（Git 标签，方便回退；不必每次推送都打）"
    if ($docVer) { Write-Host "  VERSION.md 当前版本: $docVer" -ForegroundColor DarkGray }
    if ($gitTag) { Write-Host "  Git 最新标签:       $gitTag" -ForegroundColor DarkGray }
    Write-Host ""
}

function Show-Status {
    Write-Host "=== git status ===" -ForegroundColor Cyan
    git status -sb
    Write-Host ""
}

Show-VersionHelp
Show-Status

if (-not $PushOnly) {
    $pending = git status --porcelain
    if ($pending) {
        if (-not $Message.Trim()) {
            $Message = Read-Host "【变更记录】提交说明（建议 CL-0104: 简述）"
        }
        if (-not $Message.Trim()) {
            throw "未输入提交说明，已取消。"
        }

        git add -A
        git commit -m $Message
        Write-Host "已提交: $Message" -ForegroundColor Green
    } else {
        Write-Host "没有未提交的改动，仅推送。" -ForegroundColor Yellow
    }
}

if (-not $Version.Trim()) {
    $Version = Read-Host "【里程碑版本】要打 Git 标签吗？留空=只推代码；输入如 v0.5.2=打标签并推送"
}
$Version = Normalize-VersionTag $Version

Write-Host "推送到 origin/master ..." -ForegroundColor Cyan
git push origin master

if ($Version) {
    $exists = git tag -l $Version
    if ($exists) {
        Write-Host "标签 $Version 已存在，跳过创建，仅推送标签。" -ForegroundColor Yellow
    } else {
        git tag -a $Version -m "Release $Version"
        Write-Host "已创建标签 $Version" -ForegroundColor Green
    }
    git push origin $Version
    Write-Host "已推送标签 $Version" -ForegroundColor Green
    Write-Host "提示: 请同步更新 docs/VERSION.md 与 CHANGELOG「当前发布版本」。" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "完成。仓库: https://github.com/kaybirth628/WKT" -ForegroundColor Green
