# Reset WKT order SQLite database (empty, no demo data)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$db = Join-Path $root "data\wkt_orders.db"

Write-Host ""
Write-Host "Reset order database: $db" -ForegroundColor Yellow

if (Test-Path $db) {
    Remove-Item -Force $db
    Write-Host "  Deleted old database." -ForegroundColor Green
} else {
    Write-Host "  No database file (already empty)." -ForegroundColor DarkGray
}

Set-Location $root
python -c "from test_impl.order_management.order_entry.line_store import LineStore; s=LineStore(); print('  Created empty database, lines:', s.count_lines()); s.close()"

Write-Host ""
Write-Host "Done. Restart web service and re-import Excel." -ForegroundColor Cyan
Write-Host ""
