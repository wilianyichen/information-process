#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_BIN="$INSTALL_ROOT/.venv/bin"
CONFIG_DIR="${INFOPROC_CONFIG_DIR:-$INSTALL_ROOT/config}"
CONFIG_FILE="${INFOPROC_CONFIG:-$CONFIG_DIR/config.toml}"
ENV_FILE="${INFOPROC_ENV_FILE:-$CONFIG_DIR/infoproc.env}"
LOG_DIR="$INSTALL_ROOT/logs"

load_infoproc_env() {
  mkdir -p "$LOG_DIR"
  if [[ -d "$INSTALL_ROOT/tools/ffmpeg/bin" ]]; then
    export PATH="$INSTALL_ROOT/tools/ffmpeg/bin:$PATH"
  fi
  export PATH="$VENV_BIN:$PATH"
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
  export INFOPROC_CONFIG="$CONFIG_FILE"
}

require_venv() {
  if [[ ! -x "$VENV_BIN/infoproc" ]]; then
    echo "infoproc is not installed in $VENV_BIN" >&2
    echo "Run the bundle install.sh first." >&2
    exit 1
  fi
}
