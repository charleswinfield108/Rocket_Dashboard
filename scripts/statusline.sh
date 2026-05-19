#!/usr/bin/env bash
# Reads Claude Code status JSON from stdin and outputs a single-line status bar.
input=$(cat)

model=$(echo "$input"        | jq -r '.model.id // .model // "unknown"')
ctx_pct=$(echo "$input"      | jq -r '.context_window.used_percentage // 0')
cost=$(echo "$input"         | jq -r '.cost.total_cost_usd // 0')
input_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
output_tokens=$(echo "$input"| jq -r '.context_window.total_output_tokens // 0')
cache_read=$(echo "$input"   | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')
cache_write=$(echo "$input"  | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')

ctx_fmt=$(printf "%.1f" "$ctx_pct")
cost_fmt=$(printf "%.4f" "$cost")

echo "model:${model} | ctx:${ctx_fmt}% | cost:\$${cost_fmt} | in:${input_tokens} out:${output_tokens} | cache_read:${cache_read} cache_write:${cache_write}"
