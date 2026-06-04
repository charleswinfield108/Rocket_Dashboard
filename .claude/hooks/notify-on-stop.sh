#!/usr/bin/env bash
# Stop: send a desktop notification when Claude finishes a turn.
#
# MUST exit 0. Exiting 2 from a Stop hook forces Claude to keep working —
# that would create an infinite loop for a notification hook. notify-send
# is tried first; failure is swallowed so the hook never blocks the session.
#
# The stop_hook_active guard is a belt-and-suspenders safeguard: if a Stop
# hook is already running (e.g. due to the hook itself triggering another
# stop event), exit immediately rather than sending a duplicate notification.

input=$(cat)

if echo "$input" | jq -e '.stop_hook_active == true' >/dev/null 2>&1; then
    exit 0
fi

notify-send "Claude Code" "Task complete." 2>/dev/null || true

exit 0
