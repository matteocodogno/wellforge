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
#
# These set globals rather than packing fields into a tab-separated line for `read` to split.
# That packing silently mis-assigned every value when a LEADING field was empty: tab is an
# IFS *whitespace* character, so bash collapses runs of it and strips leading ones, and
# `printf '%s\t%s\t%s' "" "" "s9"` read back as atype="s9", aid="", sid="". A payload with
# only a session_id recorded it as the agent type — a wrong attribution, which is worse than
# the missing one it was trying to avoid. Assigning directly cannot express that bug.
read_identity() {
  ATYPE=$(echo "$INPUT" | jq -r '(.agent_type // .subagent.agent_type // .subagent_type // empty)' 2>/dev/null)
  AID=$(echo "$INPUT"   | jq -r '(.agent_id // .subagent.agent_id // .subagent_id // empty)' 2>/dev/null)
  SID=$(echo "$INPUT"   | jq -r '(.session_id // empty)' 2>/dev/null)
}

# The harness may expose usage either inline on the hook payload or in the subagent
# transcript's final assistant message. Try inline first, then the transcript tail.
# Sets IN / OUT / MODEL as globals, for the same reason as read_identity above.
read_usage() {
  IN=$(echo "$INPUT"  | jq -r '(.usage.input_tokens // .subagent.usage.input_tokens // empty)' 2>/dev/null)
  OUT=$(echo "$INPUT" | jq -r '(.usage.output_tokens // .subagent.usage.output_tokens // empty)' 2>/dev/null)
  MODEL=$(echo "$INPUT" | jq -r '(.model // .subagent.model // empty)' 2>/dev/null)
  if [ -z "$IN" ] && [ -z "$OUT" ]; then
    local tp last
    tp=$(echo "$INPUT" | jq -r '(.transcript_path // empty)' 2>/dev/null)
    if [ -n "$tp" ] && [ -f "$tp" ]; then
      # last line carrying a usage object
      last=$(grep -F '"usage"' "$tp" 2>/dev/null | tail -1)
      if [ -n "$last" ]; then
        IN=$(echo "$last"  | jq -r '(.. | objects | select(has("input_tokens")).input_tokens) // empty' 2>/dev/null | tail -1)
        OUT=$(echo "$last" | jq -r '(.. | objects | select(has("output_tokens")).output_tokens) // empty' 2>/dev/null | tail -1)
        MODEL=$(echo "$last" | jq -r '(.message.model // .model // empty)' 2>/dev/null)
      fi
    fi
  fi
}

IN=""; OUT=""; MODEL=""; ATYPE=""; AID=""; SID=""
read_usage
read_identity

RUNS_DIR="$PROJECT_DIR/.forge/runs"
mkdir -p "$RUNS_DIR" 2>/dev/null || exit 0
# Build the object so that a MISSING field drops its key, and never suppresses the event.
#
# The previous version wrote `model:($model|select(.!=""))`, and an object literal whose key
# expression produces NO output produces no object at all — so a payload missing any one of
# model / agent_type / agent_id wrote nothing whatsoever. Verified: a payload carrying usage
# and model but no agent identity left .events.jsonl empty; only a fully-populated payload
# produced a line. That inverts what the observability skill promises — identity fields are
# documented as optional, with the consumer degrading to the time window when they are
# absent — and it silently loses telemetry from exactly the older harnesses the optionality
# exists for.
#
# Tokens go in as STRINGS and are converted inside jq. `--argjson in "$IN"` aborts the whole
# invocation when the value is not JSON ("jq: invalid JSON text passed to --argjson"), which
# with the 2>/dev/null below is an event lost without a trace. `tonumber? // null` degrades a
# non-numeric count to an absent key and keeps the rest of the event.
#
# run-report.py reads these with .get(...) and `or 0`, so an absent key is already its
# documented "no token data" path.
jq -cn --arg ts "$TS" --arg model "$MODEL" \
  --arg atype "$ATYPE" --arg aid "$AID" --arg sid "$SID" \
  --arg in "${IN:-}" --arg out "${OUT:-}" \
  'def nz: if . == "" then null else . end;
   def num: if . == "" then null else (tonumber? // null) end;
   {ts:$ts, event:"subagent_stop",
    model:($model|nz), agent_type:($atype|nz), agent_id:($aid|nz), session_id:($sid|nz),
    input_tokens:($in|num), output_tokens:($out|num)}
   | with_entries(select(.value != null))' \
  >> "$RUNS_DIR/.events.jsonl" 2>/dev/null

exit 0
