#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.platform"
PID_DIR="${ROOT_DIR}/runtime/pids"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

check_pid() {
  local name="$1"
  local pidfile="${PID_DIR}/${name}.pid"
  if [[ ! -f "${pidfile}" ]]; then
    echo "[status] ${name}: stopped (no pidfile)"
    return 0
  fi
  local pid
  pid="$(cat "${pidfile}" || true)"
  if [[ -z "${pid}" ]]; then
    echo "[status] ${name}: stopped (empty pidfile)"
    return 0
  fi
  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[status] ${name}: running (pid=${pid})"
  else
    echo "[status] ${name}: not running (stale pidfile pid=${pid})"
  fi
}

check_http() {
  local name="$1"
  local url="$2"
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "${url}" || true)"
  echo "[status] ${name}: ${url} -> ${code}"
}

check_pid "backend"
check_pid "frontend"

BACKEND_CHECK_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_CHECK_HOST="${FRONTEND_HOST:-127.0.0.1}"

# 某些环境下 curl 访问 0.0.0.0 会失败；用 127.0.0.1 进行本机健康检查更稳妥
if [[ "${BACKEND_CHECK_HOST}" == "0.0.0.0" || "${BACKEND_CHECK_HOST}" == "::" ]]; then
  BACKEND_CHECK_HOST="127.0.0.1"
fi
if [[ "${FRONTEND_CHECK_HOST}" == "0.0.0.0" || "${FRONTEND_CHECK_HOST}" == "::" ]]; then
  FRONTEND_CHECK_HOST="127.0.0.1"
fi

check_http "backend" "http://${BACKEND_CHECK_HOST}:${BACKEND_PORT:-9999}/openapi.json"
check_http "frontend" "http://${FRONTEND_CHECK_HOST}:${FRONTEND_PORT:-3006}/"

