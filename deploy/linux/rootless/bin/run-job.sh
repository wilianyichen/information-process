#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

load_infoproc_env
require_venv

if [[ $# -eq 0 ]]; then
  echo "Usage: $(basename "$0") <infoproc arguments>" >&2
  echo "Example: $(basename "$0") process --input /path/in" >&2
  exit 1
fi

exec "$VENV_BIN/infoproc" --config "$CONFIG_FILE" "$@"
