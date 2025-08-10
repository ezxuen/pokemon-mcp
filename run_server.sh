#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# env
export DATABASE_PATH="$SCRIPT_DIR/data/pokemon.db"
export CSV_CACHE_DIR="$SCRIPT_DIR/data/csv_cache"

# pick python
PYEXE="$SCRIPT_DIR/venv/bin/python3"
if [ ! -x "$PYEXE" ]; then
  if command -v python3 >/dev/null 2>&1; then PYEXE=python3
  elif command -v python >/dev/null 2>&1; then PYEXE=python
  else echo "[launcher] Python not found" >&2; exit 1; fi
fi

# choose entrypoint
if [ -f "$SCRIPT_DIR/server.py" ]; then
  exec "$PYEXE" -m server
else
  echo "[launcher] server.py not found" >&2; exit 1
fi