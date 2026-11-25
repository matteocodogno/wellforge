#!/bin/bash
# PostToolUse guard — a red test is never silenced (systematic-debugging, "Never make the
# symptom disappear"). The skill says it in prose: don't `.skip` / `@Disabled` a red test.
# Prose is what an agent skips when green will not come, so the part a regex can recognize
# lives here.
#
# What it catches: an edit to a TEST file that ADDS a skip / disable / focus marker —
#   JS/TS     it.skip  describe.only  test.todo  xit(  xdescribe(  .skipIf(  { skip: true }
#   JVM       @Disabled  @Ignore  enabled = false (Kotest)
#   Python    @pytest.mark.skip / skipif / xfail  pytest.skip(  @unittest.skip
#   Go        t.Skip(
# `.only` is here too: focusing one test silences every other one just as surely.
#
# ADDS, not CONTAINS: the markers are counted before and after the edit, and only a rise
# blocks. A file that already carries a skip someone else put there, or an edit that touches
# a line near one, is not this agent silencing anything.
#   Edit / MultiEdit  before = old_string(s), after = new_string(s)
#   Write             before = the file at HEAD (empty when untracked), after = content
#
# What it deliberately does NOT try: deciding whether a timeout was "raised to settle a
# flaky test". A number going up is not a regex question, and a clever guard that fires on
# legitimate edits gets disabled — which loses the part it gets right.
#
# PostToolUse fires AFTER the write, so — like post-spec-guard — the message names the revert.
# Exit 2 + stderr, the protocol every WellForge hook speaks.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0
command -v jq >/dev/null 2>&1 || exit 0

FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FILE" ] && exit 0

case "$FILE" in
  *.test.*|*.spec.*|*_test.*|*/test_*.py|test_*.py|*Test.kt|*Test.java|*Tests.kt|*Tests.java|\
  */test/*|*/tests/*|*/__tests__/*) ;;
  *) exit 0 ;;
esac

# One alternation per language family; grep -oE counts every occurrence, not every line.
MARKERS='\b(it|test|describe|context|suite)\.(skip|only|todo|skipIf)\b|\b(xit|xtest|xdescribe|fit|fdescribe)\(|\bskip[[:space:]]*:[[:space:]]*(true|"|'"'"')|\bt\.(skip|todo)\(|@Disabled\b|@Ignore\b|\benabled[[:space:]]*=[[:space:]]*false\b|@pytest\.mark\.(skip|skipif|xfail)\b|\bpytest\.skip\(|@unittest\.skip|\bt\.Skip(f|Now)?\('

count() { grep -oE "$MARKERS" | wc -l | tr -d ' '; }

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
REL="${FILE#"$PROJECT_DIR"/}"
# Codex's runner (adapters/codex) turns one apply_patch into one payload PER FILE carrying
# only `file_path` — no old_string, no content. The edit has already landed, so compare the
# file on disk with HEAD. Without this the hook would read two empty strings and never fire.
if ! printf '%s' "$INPUT" | jq -e '.tool_input | has("old_string") or has("content") or has("edits")' >/dev/null 2>&1; then
  TOOL="disk"
fi
case "$TOOL" in
  disk)
    [ -f "$FILE" ] || exit 0
    AFTER=$(count < "$FILE")
    BEFORE=$(git -C "$PROJECT_DIR" show "HEAD:$REL" 2>/dev/null | count)
    ;;
  Write)
    AFTER=$(printf '%s' "$INPUT" | jq -r '.tool_input.content // empty' | count)
    BEFORE=$(git -C "$PROJECT_DIR" show "HEAD:$REL" 2>/dev/null | count)
    ;;
  Edit|MultiEdit)
    BEFORE=$(printf '%s' "$INPUT" | jq -r '[.tool_input.old_string // empty, (.tool_input.edits[]?.old_string // empty)] | join("\n")' | count)
    AFTER=$(printf '%s' "$INPUT"  | jq -r '[.tool_input.new_string // empty, (.tool_input.edits[]?.new_string // empty)] | join("\n")' | count)
    ;;
  *) exit 0 ;;
esac

[ "${AFTER:-0}" -gt "${BEFORE:-0}" ] || exit 0

if [ "$TOOL" = "disk" ]; then
  ADDED=$(grep -oE "$MARKERS" "$FILE" | sort -u | head -3 | paste -sd ',' - | sed 's/,/, /g')
else
  ADDED=$(printf '%s' "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // ([.tool_input.edits[]?.new_string] | join("\n")) // empty' \
    | grep -oE "$MARKERS" | sort -u | head -3 | paste -sd ',' - | sed 's/,/, /g')
fi
cat >&2 <<EOF
BLOCKED: this edit adds a test silencer (${ADDED:-skip/disable/only}) to ${FILE#"$PROJECT_DIR"/}.
Revert that part of the edit now.

A red test is evidence. Skipping, disabling or focusing it destroys the evidence and hides
the bug (systematic-debugging, "Never make the symptom disappear"). Instead:
- find the root cause (Phase 1 of that skill), or
- if the failure is the ENVIRONMENT (missing variable, shared resource), report
  ENV-FAULT and stop, or
- if the test itself is wrong, that is a spec/plan question: route it in your report,
  don't delete or skip it.
If the user explicitly asked for this skip, say the guard refused it and let them make it.
EOF
exit 2
