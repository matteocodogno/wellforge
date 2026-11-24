#!/usr/bin/env bash
# Regression matrix for session-start.sh — the measured-cost half (skills/observability,
# "Measured cost"). Drives the real hook with a SessionStart payload on stdin.
#
#   - opted out (no WF_OTEL_SINK=1): no .events.jsonl line, no sink — the default for everyone;
#   - opted in: one `session_start` marker with the session id, and a sink that answers;
#   - outside a WellForge project: nothing at all, opted in or not;
#   - the context block still prints, and the hook exits 0 either way.
#
# Run: wellforge-plugin/hooks/scripts/tests/session-start.test.sh
set -uo pipefail

HOOK="$(cd "$(dirname "$0")/.." && pwd)/session-start.sh"
SINK="$(cd "$(dirname "$0")/../../.." && pwd)/scripts/otel-sink.py"
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }

pass=0 fail=0
TMPROOT=$(mktemp -d)
trap 'rm -rf "$TMPROOT"' EXIT
PROJ="$TMPROOT/proj"; mkdir -p "$PROJ/specs"
BARE="$TMPROOT/bare"; mkdir -p "$BARE"
SPOOL="$TMPROOT/spool"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
EVENTS="$PROJ/.forge/runs/.events.jsonl"

ok() {  # ok <name> <condition-exit-code>
  if [ "$2" = 0 ]; then pass=$((pass + 1)); else fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; fi
}

hook() {  # hook <dir> <opt-in 0|1>  → stdout in $TMPROOT/out, exit code in $RC
  local optin=""
  [ "$2" = 1 ] && optin=1
  printf '{"session_id":"sess-abc","hook_event_name":"SessionStart","source":"startup"}' |
    CLAUDE_PROJECT_DIR="$1" WF_OTEL_SINK="$optin" WF_OTEL_PORT="$PORT" WF_OTEL_SPOOL="$SPOOL" \
    WF_OTEL_IDLE_EXIT=3 bash "$HOOK" >"$TMPROOT/out" 2>&1
  RC=$?
}

answers() { python3 -I "$SINK" status --port "$PORT"; }

check() {  # check <name> <command…>: passes when the command succeeds
  local name="$1"; shift
  if "$@"; then pass=$((pass + 1)); else fail=$((fail + 1)); printf '  FAIL  %s\n' "$name"; fi
}
not() { ! "$@"; }
marker_is() { [ "$(jq -r 'select(.event=="session_start") | .session_id' "$EVENTS" 2>/dev/null)" = "$1" ]; }
marker_count_is() { [ "$(grep -c session_start "$EVENTS")" = "$1" ]; }
bare_untouched() { [ ! -s "$TMPROOT/out" ] && [ ! -e "$BARE/.forge" ]; }

# 1. Opted out: context printed, nothing recorded, no sink.
hook "$PROJ" 0
ok "opted out exits 0" "$RC"
check "opted out still prints context" grep -q 'SESSION CONTEXT' "$TMPROOT/out"
check "opted out writes no marker" not test -e "$EVENTS"
sleep 0.5; check "opted out starts no sink" not answers

# 2. Opted in: one marker, a sink that answers.
hook "$PROJ" 1
ok "opted in exits 0" "$RC"
check "opted in still prints context" grep -q 'SESSION CONTEXT' "$TMPROOT/out"
check "opted in records the session id" marker_is sess-abc
up=1; for _ in $(seq 1 30); do answers && { up=0; break; }; sleep 0.2; done
ok "opted in starts the sink" "$up"

# 3. Opted in again: a second marker, still exactly one sink (ensure is a no-op).
hook "$PROJ" 1
check "each session start is recorded" marker_count_is 2
check "sink still answers" answers

# 4. Outside a WellForge project: nothing, even opted in.
hook "$BARE" 1
ok "bare project exits 0" "$RC"
check "bare project: no output, no .forge" bare_untouched

# 5. The sink idle-exits (WF_OTEL_IDLE_EXIT=3) — a test must not leave a process behind.
gone=1; for _ in $(seq 1 30); do answers || { gone=0; break; }; sleep 0.5; done
ok "sink idle-exits" "$gone"

printf 'session-start: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
