# Restore web UI to satisfied baseline snapshot (2026-05-30 conversation)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\restore-ui-baseline.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$snap = Join-Path $root "snapshots\ui-baseline-20260530"

if (-not (Test-Path $snap)) {
  Write-Error "Snapshot folder not found: $snap"
}

Write-Host "Restoring UI from snapshot ..."
Copy-Item (Join-Path $snap "templates\*") (Join-Path $root "test_impl\web\templates\") -Force
Copy-Item (Join-Path $snap "static\*") (Join-Path $root "test_impl\web\static\") -Force

Write-Host "Done. Restart web service and hard-refresh browser (Ctrl+F5)."
