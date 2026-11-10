#!/usr/bin/env bash
# Regression matrix for subagent-decisions-guard.sh (SubagentStop: dev/devops reports must
# carry a DECISIONS block). Drives the real hook with JSON on stdin against a temp project.
#
# Run: wellforge-plugin/hooks/scripts/tests/subagent-decisions-guard.test.sh
set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/subagent-decisions-guard.sh"
[ -x "$HOOK" ] || { echo "hook not executable: $HOOK"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

pass=0 fail=0
TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT
PROJ="$TMPROOT/proj"; mkdir -p "$PROJ/specs"
BARE="$TMPROOT/bare"; mkdir -p "$BARE"

# expect <name> <want-exit> <payload-json> [project-dir]
expect() {
  local name="$1" want="$2" payload="$3" dir="${4:-$PROJ}" got
  printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$dir" bash "$HOOK" >/dev/null 2>"$TMPROOT/err"
  got=$?
  if [ "$got" = "$want" ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf '  FAIL  %s: exit %s, want %s\n' "$name" "$got" "$want"
    sed 's/^/        /' "$TMPROOT/err"
  fi
}

# payload <agent_type> <last_assistant_message> [stop_hook_active]
payload() {
  jq -cn --arg a "$1" --arg m "$2" --argjson s "${3:-false}" \
    '{agent_type:$a, last_assistant_message:$m, stop_hook_active:$s}'
}

REPORT_OK=$'T3 done. Tests 14/14.\n\nDECISIONS:\n- default: page size 50 — why: spec silent — where: T3'
REPORT_NONE=$'T3 done.\nDECISIONS: none — the task named every value'
REPORT_BOLD=$'T3 done.\n\n**DECISIONS:**\n- assumption: UTC timestamps — why: … — where: export.ts'
REPORT_HEADING=$'T3 done.\n\n## Decisions\n- scope: no CSV escaping of formulas — why: … — where: T3'
REPORT_MISSING=$'T3 done. Tests 14/14. Self-critique: tightened one name.'
REPORT_PROSE=$'T3 done. Decisions were all in the plan, nothing to add.'

# ── 1. the block is there ───────────────────────────────────────────────────────────────
expect "plain DECISIONS:"            0 "$(payload wellforge:backend-dev "$REPORT_OK")"
expect "DECISIONS: none — reason"    0 "$(payload wellforge:backend-dev "$REPORT_NONE")"
expect "bold **DECISIONS:**"         0 "$(payload wellforge:frontend-dev "$REPORT_BOLD")"
expect "markdown heading ## Decisions" 0 "$(payload wellforge:devops "$REPORT_HEADING")"

# ── 2. the block is missing → sent back (exit 2) ────────────────────────────────────────
expect "backend-dev without block"   2 "$(payload wellforge:backend-dev "$REPORT_MISSING")"
expect "frontend-dev without block"  2 "$(payload wellforge:frontend-dev "$REPORT_MISSING")"
expect "devops without block"        2 "$(payload wellforge:devops "$REPORT_MISSING")"
expect "Codex name wf-backend-dev"   2 "$(payload wf-backend-dev "$REPORT_MISSING")"
# The word in prose is not the block: it has to start a line and end with ':' or the line.
expect "'Decisions' in prose only"   2 "$(payload wellforge:backend-dev "$REPORT_PROSE")"

# ── 3. never loops: already sent back once ──────────────────────────────────────────────
expect "stop_hook_active → let go"   0 "$(payload wellforge:backend-dev "$REPORT_MISSING" true)"

# ── 4. out of scope → fails open ────────────────────────────────────────────────────────
expect "quality-engineer not covered" 0 "$(payload wellforge:quality-engineer "$REPORT_MISSING")"
expect "architect not covered"        0 "$(payload wellforge:architect "$REPORT_MISSING")"
expect "no agent_type"                0 "$(jq -cn --arg m "$REPORT_MISSING" '{last_assistant_message:$m}')"
expect "not a WellForge project"      0 "$(payload wellforge:backend-dev "$REPORT_MISSING")" "$BARE"
expect "no message, no transcript"    0 '{"agent_type":"wellforge:backend-dev"}'

# ── 5. message read from the subagent transcript when not inline ────────────────────────
TP_OK="$TMPROOT/ok.jsonl"; TP_BAD="$TMPROOT/bad.jsonl"
jq -cn '{type:"user",message:{content:"go"}}' > "$TP_OK"
jq -cn --arg t "first pass" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}' >> "$TP_OK"
jq -cn --arg t "$REPORT_OK" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}' >> "$TP_OK"
jq -cn '{type:"user",message:{content:"go"}}' > "$TP_BAD"
jq -cn --arg t "$REPORT_OK" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}' >> "$TP_BAD"
jq -cn --arg t "$REPORT_MISSING" '{type:"assistant",message:{content:[{type:"text",text:$t}]}}' >> "$TP_BAD"
expect "transcript: last message has block" 0 \
  "$(jq -cn --arg p "$TP_OK" '{agent_type:"wellforge:backend-dev",agent_transcript_path:$p}')"
# Only the FINAL message counts: an earlier draft with the block does not excuse the report.
expect "transcript: block only in an earlier message" 2 \
  "$(jq -cn --arg p "$TP_BAD" '{agent_type:"wellforge:backend-dev",agent_transcript_path:$p}')"

printf 'subagent-decisions-guard: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
