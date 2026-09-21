#!/usr/bin/env bash
# Regression matrix for trace-subagent.sh (SubagentStop telemetry).
#
# It drives the REAL hook — JSON on stdin, a temp project on disk, the written
# .forge/runs/.events.jsonl inspected afterwards — rather than re-stating its jq. The bug
# this exists for could not have been caught any other way: the hook always exits 0 (by
# design, telemetry must never break a session) and sends jq's stderr to /dev/null, so the
# ONLY observable difference between "worked" and "silently wrote nothing" is the file.
#
# The bug: keys were built as `model:($model|select(.!=""))`, and a jq object literal whose
# key expression yields no output yields no object. A payload missing any one of model /
# agent_type / agent_id therefore wrote NOTHING, instead of degrading to the time-window
# attribution the observability skill documents.
#
# Run: wellforge-plugin/hooks/scripts/tests/trace-subagent.test.sh
set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/trace-subagent.sh"
[ -x "$HOOK" ] || { echo "hook not executable: $HOOK"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

pass=0 fail=0
TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT

# Run the hook against a throwaway WellForge-shaped project and echo the single event line.
# Returns empty when the hook wrote nothing — which is the failure this file is about.
emit() {  # emit <payload-json>
  local dir
  dir=$(mktemp -d "$TMPROOT/proj.XXXXXX")
  mkdir -p "$dir/.forge"
  printf '%s' "$1" | CLAUDE_PROJECT_DIR="$dir" bash "$HOOK" >/dev/null 2>&1
  cat "$dir/.forge/runs/.events.jsonl" 2>/dev/null
}

check() {  # check <name> <payload> <jq-assertion>
  local name="$1" payload="$2" assertion="$3" line
  line=$(emit "$payload")
  if [ -z "$line" ]; then
    fail=$((fail + 1)); printf '  FAIL  %s: no event written\n' "$name"; return
  fi
  if [ "$(printf '%s' "$line" | jq -r "$assertion" 2>/dev/null)" = "true" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL  %s: assertion false\n        line: %s\n' "$name" "$line"
  fi
}

# ── 1. full identity — the case that always worked ────────────────────────────
check "full identity" \
  '{"agent_type":"backend-dev","agent_id":"a1","session_id":"s1","model":"claude-opus-5","usage":{"input_tokens":120,"output_tokens":45}}' \
  '.event=="subagent_stop" and .agent_type=="backend-dev" and .agent_id=="a1"
   and .model=="claude-opus-5" and .input_tokens==120 and .output_tokens==45
   and (.ts|type=="string")'

# ── 2. NO identity — the regression ───────────────────────────────────────────
# Usage and model present, agent identity absent: the old hook wrote nothing at all.
# The event must still land so run-report.py can attribute it by time window.
check "no identity (usage + model only)" \
  '{"model":"claude-opus-5","usage":{"input_tokens":10,"output_tokens":20}}' \
  '.event=="subagent_stop" and .input_tokens==10 and .output_tokens==20
   and (has("agent_type")|not) and (has("agent_id")|not)'

# Nothing but a session id: still an event, still no invented keys.
check "no identity, no model, no usage" \
  '{"session_id":"s9"}' \
  '.event=="subagent_stop" and .session_id=="s9"
   and (has("model")|not) and (has("input_tokens")|not) and (has("output_tokens")|not)'

# ── 3. no usage — identity alone is still worth recording ─────────────────────
check "no usage" \
  '{"agent_type":"architect","agent_id":"a2","session_id":"s2"}' \
  '.agent_type=="architect" and (has("input_tokens")|not) and (has("output_tokens")|not)'

# ── 4. transcript-path fallback ───────────────────────────────────────────────
# No inline usage; the hook reads the last transcript line carrying a usage object.
TRANSCRIPT="$TMPROOT/transcript.jsonl"
{
  printf '%s\n' '{"type":"assistant","message":{"model":"claude-sonnet-5","usage":{"input_tokens":1,"output_tokens":2}}}'
  printf '%s\n' '{"type":"assistant","message":{"model":"claude-opus-5","usage":{"input_tokens":700,"output_tokens":800}}}'
} > "$TRANSCRIPT"
check "transcript-path fallback" \
  "$(jq -cn --arg tp "$TRANSCRIPT" '{agent_type:"qe", transcript_path:$tp}')" \
  '.agent_type=="qe" and .input_tokens==700 and .output_tokens==800'

# The path is named but does not exist — must not crash, must still write the event.
check "transcript-path missing file" \
  '{"agent_type":"qe","transcript_path":"/nonexistent/nope.jsonl"}' \
  '.agent_type=="qe" and (has("input_tokens")|not)'

# ── 5. non-numeric tokens must not crash ──────────────────────────────────────
# `--argjson in "n/a"` aborted the whole jq invocation, and with stderr discarded the event
# vanished silently. The count degrades to an absent key; everything else survives.
check "non-numeric tokens" \
  '{"agent_type":"devops","model":"m","usage":{"input_tokens":"n/a","output_tokens":"lots"}}' \
  '.agent_type=="devops" and .model=="m"
   and (has("input_tokens")|not) and (has("output_tokens")|not)'

check "one token numeric, one not" \
  '{"agent_type":"devops","usage":{"input_tokens":5,"output_tokens":"oops"}}' \
  '.input_tokens==5 and (has("output_tokens")|not)'

# ── 6. the hook must stay invisible outside a WellForge project ───────────────
NONWF=$(mktemp -d "$TMPROOT/plain.XXXXXX")
printf '%s' '{"agent_type":"x","usage":{"input_tokens":1,"output_tokens":1}}' \
  | CLAUDE_PROJECT_DIR="$NONWF" bash "$HOOK" >/dev/null 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ ! -e "$NONWF/.forge" ]; then
  pass=$((pass + 1))
else
  fail=$((fail + 1)); printf '  FAIL  non-wellforge project: rc=%s, .forge created=%s\n' \
    "$rc" "$([ -e "$NONWF/.forge" ] && echo yes || echo no)"
fi

# ── 7. always exit 0, even on junk ────────────────────────────────────────────
for junk in '' 'not json at all' '{"usage":'; do
  if printf '%s' "$junk" | CLAUDE_PROJECT_DIR="$TMPROOT" bash "$HOOK" >/dev/null 2>&1; then
    pass=$((pass + 1)); else
    fail=$((fail + 1)); printf '  FAIL  junk payload changed the exit code: %s\n' "$junk"; fi
done

printf '\ntrace-subagent: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
