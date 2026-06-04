#!/usr/bin/env bash
# PreToolUse: block Write/Edit/MultiEdit to existing source files in data/.
#
# Consequence-if-violated justification (from claude_md_audit.md, Rule 2):
# Three systems load from data/ at startup — the Python Flask server, the Go API
# (platform/api/), and the ML pipeline. Modifying an existing source file corrupts
# all three silently; advisory text in CLAUDE.md cannot prevent a Write tool call.
#
# Exception: NEW files (e.g. data/predictions.csv, which does not yet exist) are
# allowed. The -f test blocks only when the target file is already present on disk.
#
# Blocking mechanism: exit 0 with permissionDecision "deny" in hookSpecificOutput,
# which produces a structured user-facing message rather than a raw stderr dump.

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ -z "$file_path" ]] && exit 0

# Resolve to absolute path so relative paths from any working directory match.
if [[ "$file_path" = /* ]]; then
    abs_path="$file_path"
else
    abs_path="${CLAUDE_PROJECT_DIR}/${file_path}"
fi

data_dir="${CLAUDE_PROJECT_DIR}/data"

# Block only if the file already exists inside data/
if [[ "$abs_path" == "$data_dir/"* ]] && [[ -f "$abs_path" ]]; then
    jq -n --arg path "$abs_path" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: ("READ-ONLY: \($path) is a source dataset. It is loaded at startup by the Flask server, Go API, and ML pipeline — modifying it corrupts all three. To add derived data, create a new file (e.g. data/predictions.csv does not yet exist and may be created freely).")
        }
    }'
    exit 0
fi

exit 0
