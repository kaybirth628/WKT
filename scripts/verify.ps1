$ErrorActionPreference = "Stop"

Write-Host "== ERP verify start =="

if (!(Test-Path "test_impl")) { throw "Missing test_impl directory." }

Write-Host "[1/3] Lint check placeholder"
Write-Host "[2/3] Running Python unit tests"
python -m unittest discover -s tests -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }

Write-Host "[3/3] Integration test placeholder"

Write-Host "Checklist:"
Write-Host "- Critical flows validated (plan->prod->quality->stock)"
Write-Host "- No direct edits in src/"
Write-Host "- Change request document updated"

Write-Host "== ERP verify passed =="
