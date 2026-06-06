#!/usr/bin/env bash
# PostToolUse: run go build ./... in platform/api after any .go edit.
#
# Why a hook rather than a CLAUDE.md rule:
#   A CLAUDE.md rule can be skipped — especially during multi-step implementations
#   where edits are intentionally in-progress and the build is "meant to be fixed
#   later." A hook fires on every save, so breakage is surfaced at the exact edit
#   that introduced it, not at commit time after several files have changed.
#
# Why a hook rather than a skill:
#   A skill is invoked (user-triggered or Claude-decided). A PostToolUse hook fires
#   automatically after each Write/Edit without a deliberate invocation. When three
#   files in the same package (main.go, data.go, handlers.go) are being edited in
#   sequence, the hook catches cross-file type errors at the edit that breaks
#   compilation, not only when someone explicitly asks for a build check.
#
# Exit codes:
#   0 — build passed or file is not in platform/api/ (silent, no output)
#   1 — build failed; stderr is shown to Claude in the transcript
#   (PostToolUse is non-blocking; exit 2 is not needed)

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ -z "$file_path" ]] && exit 0

# Resolve to absolute path
if [[ "$file_path" = /* ]]; then
    abs_path="$file_path"
else
    abs_path="${CLAUDE_PROJECT_DIR}/${file_path}"
fi

api_dir="${CLAUDE_PROJECT_DIR}/platform/api"

# Only run for .go files inside the platform/api module
[[ "$abs_path" == "$api_dir/"*.go ]] || exit 0

# Build from the module root; surface any errors to Claude via stderr
output=$(cd "$api_dir" && /usr/local/go/bin/go build ./... 2>&1)
if [[ -n "$output" ]]; then
    echo "go build ./... failed after editing ${abs_path##"$CLAUDE_PROJECT_DIR/"}:" >&2
    echo "$output" >&2
    exit 1
fi

exit 0
