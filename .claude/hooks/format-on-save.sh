#!/usr/bin/env bash
# PostToolUse: run gofmt on .go files after any Edit/Write/MultiEdit.
# Reads the edited path from stdin JSON; no-ops on non-.go extensions.
# Always exits 0 — PostToolUse cannot block, so failures must be silent.

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ -z "$file_path" ]] && exit 0

case "${file_path##*.}" in
    go)
        /usr/local/go/bin/gofmt -w "$file_path" 2>/dev/null || true
        ;;
esac

exit 0
