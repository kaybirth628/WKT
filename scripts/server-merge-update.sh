#!/bin/bash
# 服务器端：合并 test_impl / scripts / 白名单主数据，不碰 DB、客户档案、config、venv
set -euo pipefail

APP_DIR="${WKT_APP_DIR:-/www/wwwroot/WKT/wkt-sales-system}"
STAGING="${1:-}"

if [ -z "$STAGING" ] || [ ! -d "$STAGING/test_impl" ]; then
  echo "用法: server-merge-update.sh <staging目录>"
  exit 1
fi

echo "==> 合并代码到: ${APP_DIR}"
echo "    保留不动: *.db、customer_profiles、config/、venv/、orders/、imports/"

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

if [ -f "${STAGING}/data/supplier_profiles.json" ]; then
  mkdir -p "${APP_DIR}/data"
  if [ -f "${APP_DIR}/data/supplier_profiles.json" ]; then
    bak="${APP_DIR}/data/supplier_profiles.json.bak-$(date +%Y%m%d%H%M%S)"
    cp -a "${APP_DIR}/data/supplier_profiles.json" "${bak}"
    echo "    已备份旧供应商档案: ${bak}"
  fi
  cp -a "${STAGING}/data/supplier_profiles.json" "${APP_DIR}/data/supplier_profiles.json"
  echo "    已更新: data/supplier_profiles.json"
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
