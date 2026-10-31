#!/bin/bash
# macOS banner when Claude Code finishes a turn, fails, or needs your input.
#
# Wired in ~/.claude/settings.json (installed by install.py):
#   Stop          → notify.sh finished
#   StopFailure   → notify.sh failed
#   Notification  → notify.sh attention
#
# Reads the hook JSON on stdin, takes the "message" field when there is one.
# Never blocks anything: always exits 0.

label="${1:-event}"
message=$(python3 -I -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print((d.get("message") or d.get("notification_type") or "")[:200])' 2>/dev/null)

case "$label" in
  finished)  title="Claude Code: finished";  body="${message:-Turn complete, your move.}" ;;
  failed)    title="Claude Code: failed";    body="${message:-The last turn ended with an error.}" ;;
  attention) title="Claude Code: needs you"; body="${message:-Approval or input needed.}" ;;
  *)         title="Claude Code";            body="${message:-$label}" ;;
esac

body=${body//\"/\'}
osascript -e "display notification \"$body\" with title \"$title\"" >/dev/null 2>&1
exit 0
