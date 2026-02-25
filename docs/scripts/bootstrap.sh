#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[bootstrap] docs dir: ${ROOT_DIR}"

if ! command -v conda >/dev/null 2>&1; then
  echo "[bootstrap] ERROR: conda not found in PATH"
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[bootstrap] WARN: node not found in PATH (frontend may not start)"
else
  echo "[bootstrap] node: $(node -v)"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[bootstrap] WARN: pnpm not found in PATH (frontend may not start)"
else
  echo "[bootstrap] pnpm: $(pnpm -v)"
fi

echo "[bootstrap] conda base: $(conda info --base 2>/dev/null || true)"

echo
echo "[bootstrap] Next steps:"
echo "  1) cp ${ROOT_DIR}/.env.platform.example ${ROOT_DIR}/.env.platform"
echo "  2) edit ${ROOT_DIR}/.env.platform"
echo "  3) ./scripts/start_all.sh"

