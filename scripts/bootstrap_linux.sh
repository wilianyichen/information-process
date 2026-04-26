#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
INSTALL_MODE="${INSTALL_MODE:-editable}"
INSTALL_EXTRAS="${INSTALL_EXTRAS:-dev,media}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip build

if [[ "$INSTALL_MODE" == "wheel" ]]; then
  "$VENV_DIR/bin/python" -m build "$PROJECT_DIR"
  WHEEL_PATH="$(ls -t "$PROJECT_DIR"/dist/infoproc-*.whl | head -n 1)"
  "$VENV_DIR/bin/pip" install --upgrade "$WHEEL_PATH"
else
  "$VENV_DIR/bin/pip" install --upgrade -e "$PROJECT_DIR"
fi

if [[ -n "$INSTALL_EXTRAS" ]]; then
  "$VENV_DIR/bin/pip" install --upgrade -e "$PROJECT_DIR[$INSTALL_EXTRAS]"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "warning: ffmpeg is not on PATH; media normalization will fail until it is installed" >&2
fi

cat <<EOF
Bootstrap completed.

Next steps:
  1. Copy deploy/linux/config.linux.example.toml to /etc/infoproc/config.toml
  2. Copy deploy/linux/infoproc.env.example to /etc/infoproc/infoproc.env
  3. Fill in INFOPROC_API_KEY and INFOPROC_BASE_URL
  4. Install LibreOffice if you need .doc / .ppt support
  5. Run a processing job:
     $VENV_DIR/bin/infoproc --config /etc/infoproc/config.toml process --input /srv/infoproc/input --recursive --profile quality

Optional:
  - add diarization dependencies with: pip install -e "$PROJECT_DIR[diarize]"
  - set HF_TOKEN before using --diarize
EOF
