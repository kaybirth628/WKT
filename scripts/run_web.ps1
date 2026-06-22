$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "检查 Flask..."
python -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安装 Flask..."
    python -m pip install flask -q
}

$port = 5000
$inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    Write-Host "警告: 端口 $port 已被占用，将改用 5050"
    $env:WKT_PORT = "5050"
    $port = 5050
} else {
    $env:WKT_PORT = "5000"
}

Write-Host ""
Write-Host "=========================================="
Write-Host "  启动后请在浏览器打开:"
Write-Host "  http://127.0.0.1:$port"
Write-Host "  不要关闭此终端窗口"
Write-Host "=========================================="
Write-Host ""

python test_impl/web/app.py
