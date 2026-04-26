#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../lib/common.sh"

load_infoproc_env
require_venv

if ! "$VENV_BIN/python" -c "import whisperx" >/dev/null 2>&1; then
  echo "whisperx is not installed in $VENV_BIN" >&2
  echo "Re-run install with --with-whisperx, or install it into the venv manually." >&2
  exit 1
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "HF_TOKEN is not set. whisperx diarization requires it." >&2
  echo "Set HF_TOKEN in $ENV_FILE and retry." >&2
  exit 1
fi

expand_path() {
  "$VENV_BIN/python" -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).expanduser())' "$1"
}

echo "Interactive multimodal batch processing"
echo "This script uses the configured storage root and creates one run directory per execution."
echo

read -r -p "Input folder path: " INPUT_DIR_RAW
if [[ -z "$INPUT_DIR_RAW" ]]; then
  echo "Input folder is required." >&2
  exit 1
fi

INPUT_DIR="$(expand_path "$INPUT_DIR_RAW")"
if [[ ! -d "$INPUT_DIR" ]]; then
  echo "Input folder does not exist: $INPUT_DIR" >&2
  exit 1
fi

read -r -p "Run name [default: auto timestamp]: " RUN_NAME_RAW
RUN_NAME="${RUN_NAME_RAW:-}"

read -r -p "Glob pattern [default: *]: " PATTERN_RAW
PATTERN="${PATTERN_RAW:-*}"

echo
echo "Current config:"
echo "  config file   : $CONFIG_FILE"
echo "  input folder  : $INPUT_DIR"
echo "  run name      : ${RUN_NAME:-<auto>}"
echo "  pattern       : $PATTERN"
echo "  profile       : quality"
echo "  diarize       : true (whisperx)"
echo "  distill mode  : both"
echo "  recursive     : true"
echo

read -r -p "Continue? [Y/n]: " CONFIRM_RAW
CONFIRM="${CONFIRM_RAW:-Y}"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "Cancelled."
  exit 0
fi

ARGS=(
  process
  --input "$INPUT_DIR"
  --recursive
  --pattern "$PATTERN"
  --profile quality
  --diarize
  --distill both
)

if [[ -n "$RUN_NAME" ]]; then
  ARGS+=(--run-name "$RUN_NAME")
fi

exec "$SCRIPT_DIR/run-job.sh" "${ARGS[@]}"
