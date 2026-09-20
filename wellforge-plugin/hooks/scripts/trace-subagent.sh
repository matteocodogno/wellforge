#!/bin/bash
# SubagentStop hook — best-effort token/latency telemetry for WellForge observability.
# Appends one JSON line per subagent completion to .forge/runs/.events.jsonl, which
# run-report.py joins with the semantic run traces the commands write.
#
# Deliberately defensive: only acts in a WellForge-managed project, captures usage ONLY
# when the harness exposes it in the transcript, and ALWAYS exits 0 (telemetry must never
# break a session). See skills/observability.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Scope: only WellForge-managed projects (has specs/ or .forge/), else no-op — don't
# litter .forge/ into unrelated repos.
{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0
command -v jq >/dev/null 2>&1 || exit 0

TS=$(date -u +%FT%TZ 2>/dev/null) || exit 0

# WHO the event belongs to. Without this an event can only be attributed by TIME, and two
# parallel runs then double-count each other's tokens — which is exactly the shape
# /wellforge:implement produces on every ≥2 batch. Recent Claude Code versions put the agent
# identity on the SubagentStop payload; older ones don't, so every field is optional and the
# consumer degrades to the time window when they are absent.
read_identity() {
  local atype aid sid
  atype=$(echo "$INPUT" | jq -r '(.agent_type // .subagent.agent_type // .subagent_type // empty)' 2>/dev/null)
  aid=$(echo "$INPUT"   | jq -r '(.agent_id // .subagent.agent_id // .subagent_id // empty)' 2>/dev/null)
  sid=$(echo "$INPUT"   | jq -r '(.session_id // empty)' 2>/dev/null)
  printf '%s\t%s\t%s' "${atype:-}" "${aid:-}" "${sid:-}"
}

# The harness may expose usage either inline on the hook payload or in the subagent
# transcript's final assistant message. Try inline first, then the transcript tail.
read_usage() {
  local in out model
  in=$(echo "$INPUT"  | jq -r '(.usage.input_tokens // .subagent.usage.input_tokens // empty)' 2>/dev/null)
  out=$(echo "$INPUT" | jq -r '(.usage.output_tokens // .subagent.usage.output_tokens // empty)' 2>/dev/null)
  model=$(echo "$INPUT" | jq -r '(.model // .subagent.model // empty)' 2>/dev/null)
  if [ -z "$in" ] && [ -z "$out" ]; then
    local tp
    tp=$(echo "$INPUT" | jq -r '(.transcript_path // empty)' 2>/dev/null)
    if [ -n "$tp" ] && [ -f "$tp" ]; then
      # last line carrying a usage object
      local last
      last=$(grep -F '"usage"' "$tp" 2>/dev/null | tail -1)
      if [ -n "$last" ]; then
        in=$(echo "$last"  | jq -r '(.. | objects | select(has("input_tokens")).input_tokens) // empty' 2>/dev/null | tail -1)
        out=$(echo "$last" | jq -r '(.. | objects | select(has("output_tokens")).output_tokens) // empty' 2>/dev/null | tail -1)
        model=$(echo "$last" | jq -r '(.message.model // .model // empty)' 2>/dev/null)
      fi
    fi
  fi
  printf '%s\t%s\t%s' "${in:-}" "${out:-}" "${model:-}"
}

IFS=$'\t' read -r IN OUT MODEL < <(read_usage)
IFS=$'\t' read -r ATYPE AID SID < <(read_identity)

RUNS_DIR="$PROJECT_DIR/.forge/runs"
mkdir -p "$RUNS_DIR" 2>/dev/null || exit 0
jq -cn --arg ts "$TS" --arg model "$MODEL" \
  --arg atype "$ATYPE" --arg aid "$AID" --arg sid "$SID" \
  --argjson in "${IN:-null}" --argjson out "${OUT:-null}" \
  '{ts:$ts, event:"subagent_stop", model:($model|select(.!="")),
    agent_type:($atype|select(.!="")), agent_id:($aid|select(.!="")),
    session_id:($sid|select(.!="")),
    input_tokens:$in, output_tokens:$out}' \
  >> "$RUNS_DIR/.events.jsonl" 2>/dev/null

exit 0
