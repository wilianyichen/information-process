#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_ROOT="${1:-${CODEX_HOME:-$HOME/.codex}/skills}"
SOURCE_ROOT="$INSTALL_ROOT/codex-skill"

mkdir -p "$TARGET_ROOT"

if [[ ! -d "$SOURCE_ROOT" ]]; then
  echo "Bundled skill directory not found: $SOURCE_ROOT" >&2
  exit 1
fi

installed_any=0
for SOURCE_DIR in "$SOURCE_ROOT"/*; do
  if [[ ! -d "$SOURCE_DIR" || ! -f "$SOURCE_DIR/SKILL.md" ]]; then
    continue
  fi
  SKILL_NAME="$(basename "$SOURCE_DIR")"
  TARGET_DIR="$TARGET_ROOT/$SKILL_NAME"
  rm -rf "$TARGET_DIR"
  cp -R "$SOURCE_DIR" "$TARGET_DIR"
  echo "Codex skill installed:"
  echo "  $TARGET_DIR"
  installed_any=1
done

if [[ "$installed_any" != "1" ]]; then
  echo "No bundled skills found under $SOURCE_ROOT" >&2
  exit 1
fi
