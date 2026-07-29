# WKT · 校验并确认 .cursor/rules 已就绪（Cursor 打开本项目时自动加载 alwaysApply 规则）
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$rulesDir = Join-Path $root ".cursor\rules"

$requiredAlwaysApply = @(
    "00-wkt-master.mdc",
    "wkt-read-before-edit.mdc",
    "wkt-agent-workflow.mdc",
    "wkt-ui-design.mdc",
    "wkt-change-governance.mdc",
    "wkt-production-safety.mdc",
    "karpathy-guidelines.mdc"
)

if (-not (Test-Path $rulesDir)) {
    Write-Error "Missing $rulesDir"
}

Write-Host "WKT Cursor Rules -> $rulesDir"
Write-Host ""

$fail = 0
foreach ($name in $requiredAlwaysApply) {
    $path = Join-Path $rulesDir $name
    if (-not (Test-Path $path)) {
        Write-Host "  MISSING  $name" -ForegroundColor Red
        $fail++
        continue
    }
    $head = (Get-Content $path -TotalCount 8) -join "`n"
    if ($head -notmatch "alwaysApply:\s*true") {
        Write-Host "  FAIL     $name (alwaysApply: true required)" -ForegroundColor Red
        $fail++
    } else {
        Write-Host "  OK       $name" -ForegroundColor Green
    }
}

$extra = Get-ChildItem $rulesDir -Filter "*.mdc" |
    Where-Object { $requiredAlwaysApply -notcontains $_.Name }
foreach ($f in $extra) {
    Write-Host "  EXTRA    $($f.Name)" -ForegroundColor DarkYellow
}

Write-Host ""
if ($fail -gt 0) {
    Write-Error "$fail required rule(s) missing or misconfigured."
}

Write-Host "All required Cursor rules OK."
Write-Host "Cursor loads these automatically when this folder is the workspace."
Write-Host "If Agent ignores rules: Cursor Settings -> Rules -> confirm Project Rules enabled -> Reload Window."
