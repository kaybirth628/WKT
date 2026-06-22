# WKT - restart web service and open browser
# UTF-8 with BOM for Windows PowerShell 5.1
$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$port = 5000
$url = "http://127.0.0.1:$port"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  WKT - restart web" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Check Python deps..." -ForegroundColor Yellow
python -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installing Flask..."
    python -m pip install flask -q
}
python -c "import openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installing openpyxl..."
    python -m pip install openpyxl -q
}
python -c "import rapidocr_onnxruntime" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installing OCR deps (optional)..."
    python -m pip install -r test_impl/web/requirements.txt -q
}

Write-Host "[2/4] Stop old process on port $port ..." -ForegroundColor Yellow
$conns = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
if ($conns.Count -gt 0) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host ("      Stopped PID=" + $procId)
    }
    Start-Sleep -Milliseconds 800
} else {
    Write-Host "      Port $port is free"
}

Write-Host "[3/4] Start Flask..." -ForegroundColor Yellow
$env:WKT_PORT = "$port"
$env:FLASK_DEBUG = "1"
$startCmd = "Set-Location '$root'; `$env:WKT_PORT='$port'; `$env:FLASK_DEBUG='1'; python test_impl/web/app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $startCmd

Write-Host "[4/4] Wait for service..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 24; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
        # not ready yet
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "  OK: $url" -ForegroundColor Green
    Write-Host "  Opening browser..." -ForegroundColor Green
    Start-Process $url
    Write-Host ""
    Write-Host "  Service runs in the new PowerShell window. Close it to stop." -ForegroundColor DarkGray
} else {
    Write-Host ""
    Write-Host "  Timeout. Open manually: $url" -ForegroundColor Red
    Write-Host "  Check the new window for errors." -ForegroundColor Red
}

Write-Host ""
