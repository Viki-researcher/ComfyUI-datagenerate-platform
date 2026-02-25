#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.platform"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[start_all] ERROR: missing ${ENV_FILE}"
  echo "[start_all] Hint: cp ${ROOT_DIR}/.env.platform.example ${ENV_FILE}"
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

RUNTIME_DIR="${ROOT_DIR}/runtime"
LOG_DIR="${RUNTIME_DIR}/logs"
PID_DIR="${RUNTIME_DIR}/pids"
mkdir -p "${LOG_DIR}" "${PID_DIR}"

resolve_py() {
  local py="$1"
  local env_name="$2"
  if [[ -x "${py}" ]]; then
    echo "${py}"
    return 0
  fi
  if command -v conda >/dev/null 2>&1; then
    local base
    base="$(conda info --base 2>/dev/null || true)"
    if [[ -n "${base}" && -x "${base}/envs/${env_name}/bin/python" ]]; then
      echo "${base}/envs/${env_name}/bin/python"
      return 0
    fi
  fi
  echo ""
}

BACKEND_PY="$(resolve_py "${BACKEND_PY:-}" "datagen-backend")"
COMFYUI_PYTHON="$(resolve_py "${COMFYUI_PYTHON:-}" "datagen-comfyui")"

if [[ -z "${BACKEND_PY}" ]]; then
  echo "[start_all] ERROR: BACKEND_PY not found; please set it in ${ENV_FILE}"
  exit 1
fi
if [[ -z "${COMFYUI_PYTHON}" ]]; then
  echo "[start_all] ERROR: COMFYUI_PYTHON not found; please set it in ${ENV_FILE}"
  exit 1
fi

start_proc() {
  local name="$1"
  local pidfile="${PID_DIR}/${name}.pid"
  local logfile="${LOG_DIR}/${name}.log"

  if [[ -f "${pidfile}" ]]; then
    local pid
    pid="$(cat "${pidfile}" || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      echo "[start_all] ${name} already running (pid=${pid})"
      return 0
    fi
  fi

  echo "[start_all] starting ${name} ..."
  setsid bash -lc "$2" >"${logfile}" 2>&1 &
  echo "$!" >"${pidfile}"
  echo "[start_all] ${name} pid=$! log=${logfile}"
}

BACKEND_CMD=$(cat <<'EOF'
cd "${BACKEND_DIR}"
export DB_DEFAULT_CONNECTION="${DB_DEFAULT_CONNECTION:-sqlite}"
export COMFYUI_REPO_PATH="${COMFYUI_REPO_PATH}"
export COMFYUI_PYTHON="${COMFYUI_PYTHON}"
export COMFYUI_LISTEN="${COMFYUI_LISTEN:-127.0.0.1}"
export COMFYUI_INTERNAL_HOST="${COMFYUI_INTERNAL_HOST:-}"
export COMFYUI_PUBLIC_BASE_URL="${COMFYUI_PUBLIC_BASE_URL:-}"
export COMFYUI_PORT_RANGE="${COMFYUI_PORT_RANGE:-8200-8299}"
export COMFYUI_INSTANCE_BASE_DIR="${COMFYUI_INSTANCE_BASE_DIR:-runtime/comfy_instances}"
export COMFYUI_LOG_DIR="${COMFYUI_LOG_DIR:-runtime/comfy_logs}"
export COMFYUI_STARTUP_TIMEOUT_SECONDS="${COMFYUI_STARTUP_TIMEOUT_SECONDS:-240}"
export COMFYUI_HEARTBEAT_INTERVAL_SECONDS="${COMFYUI_HEARTBEAT_INTERVAL_SECONDS:-30}"
export COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS="${COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS:-10}"
export COMFYUI_FORCE_CPU="${COMFYUI_FORCE_CPU:-false}"
export PLATFORM_INTERNAL_SECRET="${PLATFORM_INTERNAL_SECRET:-}"
export PLATFORM_CALLBACK_URL="${PLATFORM_CALLBACK_URL:-http://127.0.0.1:9999/api/internal/comfy/callback}"
export PYTHONUNBUFFERED=1
# 后端日志加时间戳
exec > >(while IFS= read -r line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done)
exec 2>&1
"${BACKEND_PY}" -m uvicorn app:app --host "${BACKEND_HOST:-0.0.0.0}" --port "${BACKEND_PORT:-9999}"
EOF
)

FRONTEND_CMD=$(cat <<'EOF'
cd "${ART_FRONTEND_DIR}"
export VITE_API_PROXY_URL="${VITE_API_PROXY_URL:-http://127.0.0.1:9999}"
export VITE_DISABLE_DRAG_VERIFY="${VITE_DISABLE_DRAG_VERIFY:-true}"
# 前端日志加时间戳
exec > >(while IFS= read -r line; do echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"; done)
exec 2>&1
pnpm dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3006}" --open false
EOF
)

start_proc "backend" "${BACKEND_CMD}"
start_proc "frontend" "${FRONTEND_CMD}"

echo
echo "[start_all] URLs:"
HOST_IPS=()
if command -v hostname >/dev/null 2>&1; then
  read -r -a HOST_IPS <<<"$(hostname -I 2>/dev/null || true)"
fi
PRIMARY_IP="${HOST_IPS[0]:-127.0.0.1}"

FRONTEND_BIND_HOST="${FRONTEND_HOST:-0.0.0.0}"
BACKEND_BIND_HOST="${BACKEND_HOST:-0.0.0.0}"
FRONTEND_SHOW_HOST="${FRONTEND_BIND_HOST}"
BACKEND_SHOW_HOST="${BACKEND_BIND_HOST}"

if [[ "${FRONTEND_BIND_HOST}" == "0.0.0.0" || "${FRONTEND_BIND_HOST}" == "::" ]]; then
  FRONTEND_SHOW_HOST="${PRIMARY_IP}"
fi
if [[ "${BACKEND_BIND_HOST}" == "0.0.0.0" || "${BACKEND_BIND_HOST}" == "::" ]]; then
  BACKEND_SHOW_HOST="${PRIMARY_IP}"
fi

echo "  - frontend: http://${FRONTEND_SHOW_HOST}:${FRONTEND_PORT:-3006}"
echo "  - backend:  http://${BACKEND_SHOW_HOST}:${BACKEND_PORT:-9999}"
echo "  - backend api docs: http://${BACKEND_SHOW_HOST}:${BACKEND_PORT:-9999}/docs"

