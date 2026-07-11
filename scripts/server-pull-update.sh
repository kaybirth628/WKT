#!/bin/bash
# 阿里云 / 宝塔：从 GitHub 拉取最新代码并重启 WKT（与 AI Factory 隔离，端口 5001/8088）
set -euo pipefail

APP_DIR="${WKT_APP_DIR:-/www/wwwroot/WKT/wkt-sales-system}"
BRANCH="${WKT_GIT_BRANCH:-master}"

if [ ! -d "${APP_DIR}/.git" ] && [ -d "/www/wwwroot/wkt-sales-system/wkt-sales-system/.git" ]; then
  APP_DIR="/www/wwwroot/wkt-sales-system/wkt-sales-system"
fi

echo "==> WKT pull update: ${APP_DIR}"
cd "${APP_DIR}"

git fetch origin
git checkout "${BRANCH}"
git pull origin "${BRANCH}"

if [ -d venv ]; then
  source venv/bin/activate
  pip install -r requirements.txt -q || pip install -r test_impl/web/requirements.txt -q || true
fi

if command -v supervisorctl >/dev/null 2>&1; then
  supervisorctl restart wkt-sales-system || true
fi

if pgrep -f "gunicorn.*app:app" >/dev/null 2>&1; then
  pkill -HUP -f "gunicorn.*app:app" || true
fi

echo "==> Done. Check: curl -s http://127.0.0.1:5001/api/health"
