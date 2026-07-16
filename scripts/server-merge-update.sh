#!/bin/bash
# 服务器端：合并 test_impl / scripts / data 主数据（不含订单库）
set -euo pipefail

APP_DIR="${WKT_APP_DIR:-/www/wwwroot/WKT/wkt-sales-system}"
STAGING="${1:-}"

if [ -z "$STAGING" ] || [ ! -d "$STAGING/test_impl" ]; then
  echo "用法: server-merge-update.sh <staging目录>"
  exit 1
fi

echo "==> 合并代码到: ${APP_DIR}"
echo "    覆盖 data/ 主数据（客户/送货单模板/供应商/飞书等）"
echo "    保留不动: *.db、delivery_notes/、config/、venv/、orders/、imports/"

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

if [ -d "${STAGING}/data" ]; then
  mkdir -p "${APP_DIR}/data"
  bak_root="${APP_DIR}/data.bak-$(date +%Y%m%d%H%M%S)"
  if [ -d "${APP_DIR}/data" ]; then
    mkdir -p "${bak_root}"
    for f in customer_profiles.json supplier_profiles.json feishu_config.json reconciliation_config.json; do
      if [ -f "${APP_DIR}/data/${f}" ]; then
        cp -a "${APP_DIR}/data/${f}" "${bak_root}/${f}"
      fi
    done
    if [ -d "${APP_DIR}/data/delivery_templates" ]; then
      mkdir -p "${bak_root}/delivery_templates"
      cp -a "${APP_DIR}/data/delivery_templates/." "${bak_root}/delivery_templates/" 2>/dev/null || true
    fi
    echo "    已备份关键 data 到: ${bak_root}"
  fi

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude='*.db' \
      --exclude='*.db-journal' \
      --exclude='*.db-wal' \
      --exclude='*.db-shm' \
      --exclude='*.db.bak*' \
      --exclude='delivery_notes/' \
      "${STAGING}/data/" "${APP_DIR}/data/"
  else
    find "${STAGING}/data" -type f \
      ! -path '*/delivery_notes/*' \
      ! -name '*.db' \
      ! -name '*.db-journal' \
      ! -name '*.db-wal' \
      ! -name '*.db-shm' \
      ! -name '*.db.bak*' | while IFS= read -r src; do
      rel="${src#${STAGING}/data/}"
      dest="${APP_DIR}/data/${rel}"
      mkdir -p "$(dirname "${dest}")"
      cp -a "${src}" "${dest}"
    done
  fi
  echo "    已更新: data/（不含订单库与 delivery_notes）"
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
