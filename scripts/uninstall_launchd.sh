#!/usr/bin/env bash
set -euo pipefail

DEST="$HOME/Library/LaunchAgents/com.web3_ai_daily_brief.plist"
LABEL="com.web3_ai_daily_brief"
DOMAIN="gui/$(id -u)"

if [[ -f "$DEST" ]]; then
  if launchctl help bootout >/dev/null 2>&1; then
    launchctl bootout "$DOMAIN" "$DEST" >/dev/null 2>&1 || true
    launchctl disable "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
  else
    launchctl unload "$DEST" >/dev/null 2>&1 || true
  fi
  rm -f "$DEST"
  echo "Unloaded and removed: $DEST"
else
  echo "Not found: $DEST"
fi
