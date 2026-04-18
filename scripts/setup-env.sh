#!/usr/bin/env bash
# SCML local development environment bootstrap (bash / WSL / macOS / Linux).
# Creates a conda env at a user-chosen path. Defaults to $HOME/envs/scml on
# Unix; use --prefix to override (Windows convention: D:\envs\scml).
#
# Usage:
#   ./scripts/setup-env.sh                         # default prefix
#   ./scripts/setup-env.sh --prefix D:/envs/scml   # explicit prefix
#   ./scripts/setup-env.sh --force                 # recreate

set -euo pipefail

ENV_PREFIX="${HOME}/envs/scml"
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) ENV_PREFIX="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if ! command -v conda >/dev/null 2>&1; then
  echo "conda not found on PATH. Install Miniconda/Mambaforge first." >&2
  exit 1
fi

if [[ $FORCE -eq 1 && -d "$ENV_PREFIX" ]]; then
  echo "Removing existing env at $ENV_PREFIX ..."
  conda env remove -p "$ENV_PREFIX" -y
fi

if [[ -d "$ENV_PREFIX" ]]; then
  echo "Env already exists at $ENV_PREFIX. Use --force to recreate."
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  echo "Creating conda env at $ENV_PREFIX (5-10 min) ..."
  conda env create -p "$ENV_PREFIX" -f "$SCRIPT_DIR/../environment.yml"
fi

cat <<EOF

Activate with:  conda activate $ENV_PREFIX
Set backend:    export KERAS_BACKEND=torch
Verify with:    python scripts/verify-env.py
EOF
