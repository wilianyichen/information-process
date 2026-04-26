#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

load_infoproc_env
require_venv

CACHE_DIR="${1:-}"
if [[ -n "$CACHE_DIR" ]]; then
  CACHE_DIR="$("$VENV_BIN/python" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser())' "$CACHE_DIR")"
fi

ARGS=(--config "$CONFIG_FILE" download-model --profile quality)
if [[ -n "$CACHE_DIR" ]]; then
  ARGS+=(--cache-dir "$CACHE_DIR")
fi

exec "$VENV_BIN/infoproc" "${ARGS[@]}"
