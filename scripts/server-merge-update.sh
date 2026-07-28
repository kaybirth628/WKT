#!/bin/bash
# 服务器端：合并 test_impl / scripts / data
# 默认不含订单库；WKT_FULL_DATA_SYNC=1 时整包覆盖 data/（含 *.db、delivery_notes）
set -euo pipefail

APP_DIR="${WKT_APP_DIR:-/www/wwwroot/WKT/wkt-sales-system}"
STAGING="${1:-}"
FULL_DATA="${WKT_FULL_DATA_SYNC:-0}"
SUP="${WKT_SUPERVISOR_NAME:-wkt-sales-system}"

if [ -z "$STAGING" ] || [ ! -d "$STAGING/test_impl" ]; then
  echo "用法: server-merge-update.sh <staging目录>"
  exit 1
fi

echo "==> 合并代码到: ${APP_DIR}"
if [ "$FULL_DATA" = "1" ]; then
  echo "    【全量】覆盖 data/（含订单库 wkt_orders.db、delivery_notes）"
  echo "    云端旧 data 会先备份到 data.bak-时间戳/"
else
  echo "    【仅代码】不更新订单库/客商 JSON；若包内含 data/feishu_config.json 则覆盖云端飞书配置"
  echo "    保留不动: *.db、delivery_notes/、customer_profiles、supplier_profiles 等"
fi

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

  stop_wkt() {
    if command -v supervisorctl >/dev/null 2>&1; then
      supervisorctl stop "${SUP}" 2>/dev/null || true
    fi
    if pgrep -f "gunicorn.*app:app" >/dev/null 2>&1; then
      pkill -TERM -f "gunicorn.*app:app" 2>/dev/null || true
      sleep 2
    fi
  }

  start_wkt() {
    if command -v supervisorctl >/dev/null 2>&1; then
      supervisorctl start "${SUP}" 2>/dev/null || supervisorctl restart "${SUP}" 2>/dev/null || true
    fi
    if pgrep -f "gunicorn.*app:app" >/dev/null 2>&1; then
      pkill -HUP -f "gunicorn.*app:app" 2>/dev/null || true
    fi
  }

  if [ "$FULL_DATA" = "1" ]; then
    stop_wkt
    if [ -d "${APP_DIR}/data" ]; then
      echo "    备份整包 data/ 到: ${bak_root}"
      cp -a "${APP_DIR}/data" "${bak_root}"
    fi
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "${STAGING}/data/" "${APP_DIR}/data/"
    else
      rm -rf "${APP_DIR}/data"
      cp -a "${STAGING}/data" "${APP_DIR}/"
    fi
    echo "    已全量覆盖: data/（含订单库）"
    start_wkt
  else
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
    if [ -f "${STAGING}/data/feishu_config.json" ]; then
      echo "    已同步: data/feishu_config.json（飞书 Webhook 通知配置）"
    fi
  fi
fi

if [ -d "${STAGING}/deploy-info" ]; then
  mkdir -p "${APP_DIR}/deploy-info"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "${STAGING}/deploy-info/" "${APP_DIR}/deploy-info/"
  else
    rm -rf "${APP_DIR}/deploy-info"
    cp -a "${STAGING}/deploy-info" "${APP_DIR}/"
  fi
  echo "    已更新: deploy-info/（版本与 CHANGELOG 摘要供飞书部署通知）"
fi

find "${APP_DIR}/test_impl" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

PIP=""
if [ -x "${APP_DIR}/venv/bin/pip" ]; then
  PIP="${APP_DIR}/venv/bin/pip"
elif [ -x "${APP_DIR}/.venv/bin/pip" ]; then
  PIP="${APP_DIR}/.venv/bin/pip"
fi
if [ -n "${PIP}" ] && [ -f "${APP_DIR}/test_impl/web/requirements.txt" ]; then
  echo "==> 安装/更新 Python 依赖 ..."
  "${PIP}" install -r "${APP_DIR}/test_impl/web/requirements.txt" -q || true
fi

if [ "$FULL_DATA" != "1" ]; then
  if command -v supervisorctl >/dev/null 2>&1; then
    supervisorctl restart "${SUP}" 2>/dev/null || true
  fi
  if pgrep -f "gunicorn.*app:app" >/dev/null 2>&1; then
    pkill -HUP -f "gunicorn.*app:app" 2>/dev/null || true
  fi
fi

PY=""
if [ -x "${APP_DIR}/venv/bin/python" ]; then
  PY="${APP_DIR}/venv/bin/python"
elif [ -x "${APP_DIR}/.venv/bin/python" ]; then
  PY="${APP_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
fi
if [ -n "${PY}" ] && [ -f "${APP_DIR}/scripts/notify-feishu-deploy.py" ]; then
  echo "==> 飞书部署通知 ..."
  (cd "${APP_DIR}" && "${PY}" scripts/notify-feishu-deploy.py --app-dir "${APP_DIR}" --host-label "云端") || true
fi

echo "==> 完成。请访问外网 8088 端口并 Ctrl+F5 刷新。"
