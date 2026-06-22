# WKT - start web only (no kill port), for quick dev
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$port = if ($env:WKT_PORT) { $env:WKT_PORT } else { "5000" }
$env:WKT_PORT = "$port"
$env:FLASK_DEBUG = "1"
Write-Host "Starting http://127.0.0.1:$port ..."
python test_impl/web/app.py
