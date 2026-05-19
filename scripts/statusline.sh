#!/usr/bin/env bash
# Reads Claude Code status JSON from stdin and outputs a single-line status bar.
input=$(cat)

model=$(echo "$input"        | jq -r 'if .model | type == "object" then .model.id else (.model // "unknown") end')
used=$(echo "$input"         | jq -r '.context_window.input_tokens // 0')
available=$(echo "$input"    | jq -r '.context_window.max_tokens // 1')
cost=$(echo "$input"         | jq -r '.costUSD // 0')
input_tokens=$(echo "$input" | jq -r '.usage.input_tokens // 0')
output_tokens=$(echo "$input"| jq -r '.usage.output_tokens // 0')

ctx_pct=$(echo "$used $available" | awk '{printf "%.1f", ($1 / $2) * 100}')
cost_fmt=$(printf "%.4f" "$cost")

echo "model:${model} | ctx:${ctx_pct}% | cost:\$${cost_fmt} | in:${input_tokens} out:${output_tokens}"
