#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TPL="$ROOT_DIR/launchd/com.web3_ai_daily_brief.plist.template"
DEST_DIR="$HOME/Library/LaunchAgents"
DEST="$DEST_DIR/com.web3_ai_daily_brief.plist"

mkdir -p "$DEST_DIR"

if [[ ! -f "$TPL" ]]; then
  echo "Missing template: $TPL" >&2
  exit 1
fi

sed "s#__REPO_PATH__#$ROOT_DIR#g" "$TPL" > "$DEST"
echo "Wrote: $DEST"

launchctl unload "$DEST" >/dev/null 2>&1 || true
LABEL="com.web3_ai_daily_brief"
DOMAIN="gui/$(id -u)"

# Prefer modern launchctl subcommands. Fall back to legacy load/unload if needed.
if launchctl help bootstrap >/dev/null 2>&1; then
  launchctl bootout "$DOMAIN" "$DEST" >/dev/null 2>&1 || true
  launchctl bootstrap "$DOMAIN" "$DEST"
  launchctl enable "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
else
  launchctl load "$DEST"
fi
echo "Loaded launchd job: $LABEL"

echo
echo "Next run: daily at 09:00 (local time)."
echo "Logs:"
echo "  $ROOT_DIR/outputs/launchd_stdout.log"
echo "  $ROOT_DIR/outputs/launchd_stderr.log"
