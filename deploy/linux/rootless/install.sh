#!/usr/bin/env bash
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${INFOPROC_INSTALL_ROOT:-$HOME/.local/opt/infoproc}"
MODEL_CACHE_DIR=""
STORAGE_ROOT=""
WITH_FASTER_WHISPER=1
WITH_WHISPERX=0
PREFETCH_LARGE_V3=0
INSTALL_CODEX_SKILL=0

usage() {
  cat <<EOF
Usage: bash install.sh [options]

Options:
  --root <path>            Install target root. Default: $HOME/.local/opt/infoproc
  --storage-root <path>    Default storage root written into config.toml
  --model-cache-dir <path> Override transcription.model_cache_dir for first install
  --no-faster-whisper      Skip installing faster-whisper
  --with-whisperx          Install whisperx for diarization support
  --prefetch-large-v3      Download the quality model after install
  --install-codex-skill    Copy the bundled skill into \$CODEX_HOME/skills or ~/.codex/skills
  --help                   Show this message

Environment:
  INFOPROC_INSTALL_ROOT    Override install root
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --storage-root)
      STORAGE_ROOT="$2"
      shift 2
      ;;
    --model-cache-dir)
      MODEL_CACHE_DIR="$2"
      shift 2
      ;;
    --no-faster-whisper)
      WITH_FASTER_WHISPER=0
      shift
      ;;
    --with-whisperx)
      WITH_WHISPERX=1
      shift
      ;;
    --prefetch-large-v3)
      PREFETCH_LARGE_V3=1
      shift
      ;;
    --install-codex-skill)
      INSTALL_CODEX_SKILL=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if [[ -z "$MODEL_CACHE_DIR" ]]; then
  MODEL_CACHE_DIR="$INSTALL_ROOT/models"
fi

if [[ -z "$STORAGE_ROOT" ]]; then
  STORAGE_ROOT="$INSTALL_ROOT/storage"
fi

mkdir -p \
  "$INSTALL_ROOT/bin" \
  "$INSTALL_ROOT/codex-skill" \
  "$INSTALL_ROOT/lib" \
  "$INSTALL_ROOT/config" \
  "$INSTALL_ROOT/logs" \
  "$INSTALL_ROOT/state" \
  "$INSTALL_ROOT/models" \
  "$INSTALL_ROOT/storage" \
  "$INSTALL_ROOT/hf_home" \
  "$INSTALL_ROOT/tools/ffmpeg/bin"

mkdir -p "$MODEL_CACHE_DIR" "$STORAGE_ROOT"

python3 -m venv "$INSTALL_ROOT/.venv"
PIP_BIN="$INSTALL_ROOT/.venv/bin/pip"
PYTHON_BIN="$INSTALL_ROOT/.venv/bin/python"

"$PIP_BIN" install --upgrade pip

WHEEL_PATH="$(find "$BUNDLE_DIR/wheels" -maxdepth 1 -type f -name 'infoproc-*.whl' | head -n 1)"
if [[ -z "$WHEEL_PATH" ]]; then
  echo "No infoproc wheel found under $BUNDLE_DIR/wheels" >&2
  exit 1
fi

"$PIP_BIN" install --upgrade "$WHEEL_PATH"

if [[ "$WITH_FASTER_WHISPER" == "1" ]]; then
  "$PIP_BIN" install --upgrade faster-whisper
fi

if [[ "$WITH_WHISPERX" == "1" ]]; then
  "$PIP_BIN" install --upgrade whisperx
fi

cp "$BUNDLE_DIR/bin/"*.sh "$INSTALL_ROOT/bin/"
cp "$BUNDLE_DIR/lib/"*.sh "$INSTALL_ROOT/lib/"
chmod +x "$INSTALL_ROOT/bin/"*.sh "$INSTALL_ROOT/lib/"*.sh
if [[ -d "$BUNDLE_DIR/codex-skill" ]]; then
  cp -R "$BUNDLE_DIR/codex-skill/." "$INSTALL_ROOT/codex-skill/"
fi

CONFIG_FILE="$INSTALL_ROOT/config/config.toml"
ENV_FILE="$INSTALL_ROOT/config/infoproc.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
  "$INSTALL_ROOT/.venv/bin/infoproc" init \
    --config "$CONFIG_FILE" \
    --storage-root "$STORAGE_ROOT" \
    --state-dir "$INSTALL_ROOT/state" \
    --model-cache-dir "$MODEL_CACHE_DIR"
elif [[ "$MODEL_CACHE_DIR" != "$INSTALL_ROOT/models" || "$STORAGE_ROOT" != "$INSTALL_ROOT/storage" ]]; then
  echo "Notice: $CONFIG_FILE already exists, so install-time storage/model overrides were not written." >&2
  echo "If needed, edit $CONFIG_FILE manually or re-run infoproc init with --force." >&2
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$BUNDLE_DIR/templates/infoproc.user.env.example" "$ENV_FILE"
fi

if [[ "$PREFETCH_LARGE_V3" == "1" ]]; then
  "$INSTALL_ROOT/bin/download-quality-model.sh" "$MODEL_CACHE_DIR"
fi

if [[ "$INSTALL_CODEX_SKILL" == "1" ]]; then
  "$INSTALL_ROOT/bin/install-codex-skill.sh"
fi

cat <<EOF
Install completed.

Install root:
  $INSTALL_ROOT

Config files:
  $CONFIG_FILE
  $ENV_FILE

Quick commands:
  $INSTALL_ROOT/bin/download-quality-model.sh "$MODEL_CACHE_DIR"
  $INSTALL_ROOT/bin/install-codex-skill.sh
  $INSTALL_ROOT/bin/process-multimodal-folder.sh
  $INSTALL_ROOT/bin/run-job.sh process --input /path/in

If ffmpeg is not available on PATH, place user-space binaries here:
  $INSTALL_ROOT/tools/ffmpeg/bin

Storage root:
  $STORAGE_ROOT

Model cache dir:
  $MODEL_CACHE_DIR

Python executable:
  $PYTHON_BIN
EOF
