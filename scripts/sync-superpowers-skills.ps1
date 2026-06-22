$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$skills = @(
    "brainstorming", "dispatching-parallel-agents", "executing-plans",
    "finishing-a-development-branch", "receiving-code-review", "requesting-code-review",
    "subagent-driven-development", "systematic-debugging", "test-driven-development",
    "using-git-worktrees", "using-superpowers", "verification-before-completion",
    "writing-plans", "writing-skills"
)

$skillsRoot = Join-Path $root ".cursor\skills"
New-Item -ItemType Directory -Force -Path $skillsRoot | Out-Null

Write-Host "Syncing obra/superpowers skills to $skillsRoot"
foreach ($s in $skills) {
    $dir = Join-Path $skillsRoot $s
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $url = "https://raw.githubusercontent.com/obra/superpowers/main/skills/$s/SKILL.md"
    Invoke-WebRequest -Uri $url -OutFile (Join-Path $dir "SKILL.md") -UseBasicParsing -TimeoutSec 120
    Write-Host "  OK $s"
}
Write-Host "Done. Restart Cursor or open a new Agent session."
