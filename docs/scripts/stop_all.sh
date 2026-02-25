#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="${ROOT_DIR}/runtime/pids"

stop_one() {
  local name="$1"
  local pidfile="${PID_DIR}/${name}.pid"
  if [[ ! -f "${pidfile}" ]]; then
    echo "[stop_all] ${name}: no pidfile"
    return 0
  fi
  local pid
  pid="$(cat "${pidfile}" || true)"
  if [[ -z "${pid}" ]]; then
    echo "[stop_all] ${name}: empty pidfile"
    rm -f "${pidfile}"
    return 0
  fi
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    echo "[stop_all] ${name}: not running (pid=${pid})"
    rm -f "${pidfile}"
    return 0
  fi

  echo "[stop_all] stopping ${name} (pid=${pid}) ..."
  # kill process group first (setsid creates a new session)
  kill -TERM "-${pid}" >/dev/null 2>&1 || kill -TERM "${pid}" >/dev/null 2>&1 || true

  for _ in {1..30}; do
    if ! kill -0 "${pid}" >/dev/null 2>&1; then
      echo "[stop_all] ${name}: stopped"
      rm -f "${pidfile}"
      return 0
    fi
    sleep 1
  done

  echo "[stop_all] ${name}: force kill (pid=${pid})"
  kill -KILL "-${pid}" >/dev/null 2>&1 || kill -KILL "${pid}" >/dev/null 2>&1 || true
  rm -f "${pidfile}"
}

stop_one "frontend"
stop_one "backend"

