#!/usr/bin/env bash
# Install the viz_results skill for CLI agents.
#
#   ./install.sh              # user-level: Claude Code (~/.claude/skills) + Codex (~/.codex/skills)
#   ./install.sh --project DIR  # also into DIR/.claude/skills and DIR/.codex/skills
#   ./install.sh --claude-only | --codex-only
#   ./install.sh --package    # also build dist/viz_results.skill (zip)
#
# Skills are plain directories with a SKILL.md; both CLIs discover them by
# scanning these folders, so "install" is just a copy. Re-run to update.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="$(basename "$SRC")"
DO_CLAUDE=1; DO_CODEX=1; PROJECT=""; PACKAGE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-only) DO_CODEX=0 ;;
    --codex-only)  DO_CLAUDE=0 ;;
    --project) PROJECT="$2"; shift ;;
    --package) PACKAGE=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown flag $1" >&2; exit 1 ;;
  esac; shift
done

copy_to() {
  local dst="$1"
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  # exclude workspace/eval junk; keep everything the skill needs
  rsync -a --exclude '__pycache__' --exclude '*-workspace' --exclude 'evals' --exclude '.git' --exclude 'dist' "$SRC/" "$dst/"
  echo "installed -> $dst"
}

targets=()
[[ $DO_CLAUDE == 1 ]] && targets+=("$HOME/.claude/skills/$NAME")
[[ $DO_CODEX  == 1 ]] && targets+=("$HOME/.codex/skills/$NAME")
if [[ -n "$PROJECT" ]]; then
  [[ $DO_CLAUDE == 1 ]] && targets+=("$PROJECT/.claude/skills/$NAME")
  [[ $DO_CODEX  == 1 ]] && targets+=("$PROJECT/.codex/skills/$NAME")
fi
for t in "${targets[@]}"; do
  [[ "$t" == "$SRC" ]] && { echo "skip (source) $t"; continue; }
  copy_to "$t"
done

if [[ $PACKAGE == 1 ]]; then
  mkdir -p "$SRC/dist"
  (cd "$SRC/.." && rm -f "$SRC/dist/$NAME.skill" && zip -qr "$SRC/dist/$NAME.skill" "$NAME" -x '*/__pycache__/*' '*-workspace/*' '*/.git/*' '*/dist/*' '*/.DS_Store')
  echo "packaged -> $SRC/dist/$NAME.skill"
fi

echo
echo "Use it with:   claude  ->  /$NAME        codex  ->  \$$NAME  (or just describe the task)"
echo "Prepare libs:  python3 \"$SRC/scripts/setup_env.py\""
echo "Open the GUI:  python3 \"$SRC/scripts/gui.py\" --project /path/to/your/study"
