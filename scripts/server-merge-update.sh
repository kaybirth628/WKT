#!/bin/bash
# 服务器端：仅合并 test_impl / scripts，不碰 data、config、venv
set -euo pipefail

APP_DIR="${WKT_APP_DIR:-/www/wwwroot/WKT/wkt-sales-system}"
STAGING="${1:-}"

if [ -z "$STAGING" ] || [ ! -d "$STAGING/test_impl" ]; then
  echo "用法: server-merge-update.sh <staging目录>"
  exit 1
fi

echo "==> 合并代码到: ${APP_DIR}"
echo "    保留不动: data/ config/ venv/ orders/ imports/"

mkdir -p "${APP_DIR}"

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${STAGING}/test_impl/" "${APP_DIR}/test_impl/"
  if [ -d "${STAGING}/scripts" ]; then
    rsync -a "${STAGING}/scripts/" "${APP_DIR}/scripts/"
  fi
else
  rm -rf "${APP_DIR}/test_impl"
  cp -a "${STAGING}/test_impl" "${APP_DIR}/"
  if [ -d "${STAGING}/scripts" ]; then
    rm -rf "${APP_DIR}/scripts"
    cp -a "${STAGING}/scripts" "${APP_DIR}/"
  fi
fi

find "${APP_DIR}/test_impl" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

SUP="${WKT_SUPERVISOR_NAME:-wkt-sales-system}"
if command -v supervisorctl >/dev/null 2>&1; then
  supervisorctl restart "${SUP}" 2>/dev/null || true
fi
if pgrep -f "gunicorn.*app:app" >/dev/null 2>&1; then
  pkill -HUP -f "gunicorn.*app:app" 2>/dev/null || true
fi

echo "==> 完成。请访问外网 8088 端口并 Ctrl+F5 刷新。"
