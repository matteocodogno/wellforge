#!/bin/bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Scope: only WellForge-managed projects (has specs/ or .forge/), else no-op. Enabled at
# user scope the plugin's hooks fire in EVERY repo, and a WellForge hook has no business
# writing files or printing WellForge context into someone's unrelated checkout.
# trace-subagent.sh has always done this; these two did not.
{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0

# Measured cost (skills/observability, "Measured cost"). Only when the developer opted in
# with WF_OTEL_SINK=1 in the same user-scope env block that turns on Claude Code's OTel
# export — the hook cannot see the OTEL_* variables themselves, Claude Code withholds them.
#  1. Record this session id in .events.jsonl (already gitignored): run-report.py reads
#     measured cost for THIS project's sessions only.
#  2. Start the local sink unless one already answers. Detached and silenced, so a session
#     never waits on it or sees its output; a failure here only means "no measured cost".
if [ "${WF_OTEL_SINK:-}" = "1" ]; then
  INPUT=$(cat 2>/dev/null)
  SID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
  if [ -n "$SID" ] && mkdir -p "$PROJECT_DIR/.forge/runs" 2>/dev/null; then
    jq -cn --arg ts "$(date -u +%FT%TZ)" --arg sid "$SID" \
      '{ts:$ts, event:"session_start", session_id:$sid}' \
      >> "$PROJECT_DIR/.forge/runs/.events.jsonl" 2>/dev/null
  fi
  SINK="$(cd "$(dirname "$0")/../.." && pwd)/scripts/otel-sink.py"
  if command -v python3 >/dev/null 2>&1 && [ -f "$SINK" ]; then
    (python3 -I "$SINK" ensure </dev/null >/dev/null 2>&1 &)
  fi
fi

echo "=== SESSION CONTEXT ==="
echo "## Git status"
git -C "$PROJECT_DIR" status --short 2>/dev/null || echo "(not a git repo)"
echo ""
echo "## Recent commits"
git -C "$PROJECT_DIR" log --oneline -5 2>/dev/null || echo "(no commits)"
echo ""
echo "## Branch"
git -C "$PROJECT_DIR" branch --show-current 2>/dev/null
echo ""
if [ -f "$PROJECT_DIR/.claude/context/glossary.md" ]; then
  echo "## Domain glossary"
  cat "$PROJECT_DIR/.claude/context/glossary.md"
  echo ""
fi
echo "## Monorepo services"
for dir in "$PROJECT_DIR"/*/; do
  name=$(basename "$dir")
  if [ -f "$dir/pom.xml" ]; then echo "- $name (Kotlin/Spring Boot)"
  elif [ -f "$dir/package.json" ]; then echo "- $name (Node/TypeScript)"
  fi
done
echo "======================="
