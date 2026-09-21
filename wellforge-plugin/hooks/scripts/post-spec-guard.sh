#!/bin/bash
# PostToolUse guard — the lifecycle rules that were only ever prompt promises.
#
# Every command was rewritten so that ONLY /wellforge:done writes `status: done` and ONLY
# /wellforge:promote raises `rigor:`. Nothing enforced it: one Edit to a spec's frontmatter
# flips either field, and the "single guarded place" stops being single the first time
# anyone (model or human) takes the shortcut. stop-verify.sh already enforces the drift rule
# mechanically; this is the same move for the other two.
#
# WHAT THIS HOOK CAN AND CANNOT DO — read before trusting it.
# PostToolUse fires AFTER the write. It cannot prevent the edit; it can only refuse to let
# the turn proceed and tell Claude to put the file back. So the message always names the
# revert explicitly. A PreToolUse hook could block first, but it would have to parse the
# proposed content out of the tool input for three different tools (Write/Edit/MultiEdit)
# and reason about a patch it cannot apply — far more ways to be wrong, on a rule whose
# violation is cheap to undo. Detect-and-revert is the honest trade.
#
# Exit 2 + stderr everywhere, like the other four hooks. JSON `decision: block` output would
# render marginally nicer for the multi-line gate list, but a hook that speaks two failure
# protocols is one more thing to get wrong, and uniformity is worth more than prettiness.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

{ [ -d "$PROJECT_DIR/specs" ] || [ -d "$PROJECT_DIR/.forge" ]; } || exit 0
if ! command -v jq >/dev/null 2>&1; then
  echo "post-spec-guard: jq unavailable — lifecycle guard skipped (advisory)" >&2
  exit 0
fi

# NotebookEdit sends `notebook_path`; without it this hook matches the tool and then
# reads nothing, which is a matcher that only looks like coverage.
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')
[ -z "$FILE" ] && exit 0

# Only a spec's or a brief's own frontmatter carries these fields.
case "$FILE" in
  */specs/*/spec.md|specs/*/spec.md|*/specs/*/brief.md|specs/*/brief.md) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

REL="${FILE#"$PROJECT_DIR"/}"
SLUG=$(basename "$(dirname "$FILE")")

# ── frontmatter field extraction (the two scalars, no YAML parser needed) ───────
field() {  # field <name> <text>
  printf '%s' "$2" | awk -v key="$1" '
    BEGIN { infm = 0 }
    /^---[[:space:]]*$/ { infm++; if (infm > 1) exit; next }
    infm == 1 && $1 == key":" { $1 = ""; sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+#.*$/, ""); print; exit }'
}

AFTER=$(cat "$FILE")
# Untracked file → "before" is empty, which is how a brand-new spec reads as a creation
# rather than a transition. git show is quiet about a path that does not exist at HEAD.
BEFORE=$(git -C "$PROJECT_DIR" show "HEAD:$REL" 2>/dev/null || true)

OLD_STATUS=$(field status "$BEFORE"); NEW_STATUS=$(field status "$AFTER")
OLD_RIGOR=$(field rigor "$BEFORE");   NEW_RIGOR=$(field rigor "$AFTER")
[ "$OLD_STATUS" = "$NEW_STATUS" ] && [ "$OLD_RIGOR" = "$NEW_RIGOR" ] && exit 0   # nothing we police changed

refuse() {
  echo "BLOCKED by post-spec-guard: $1" >&2
  shift
  for line in "$@"; do echo "  $line" >&2; done
  echo "  The edit is already written — PostToolUse runs after the tool. REVERT it:" >&2
  echo "      git -C \"$PROJECT_DIR\" checkout -- \"$REL\"    (or restore the previous frontmatter by hand)" >&2
  exit 2
}

tier_rank() { case "$1" in spike) echo 1 ;; mvp) echo 2 ;; production|"") echo 3 ;; *) echo 0 ;; esac; }

# ── 1. rigor may only ever go UP ────────────────────────────────────────────────
if [ -n "$OLD_RIGOR" ] && [ -n "$NEW_RIGOR" ] && [ "$OLD_RIGOR" != "$NEW_RIGOR" ]; then
  if [ "$(tier_rank "$NEW_RIGOR")" -lt "$(tier_rank "$OLD_RIGOR")" ]; then
    refuse "rigor lowered ($OLD_RIGOR -> $NEW_RIGOR) in $REL" \
      "Lower rigor is deferred DEBT, not a setting: the tier records what this feature was held to." \
      "  - for one cheaper run:  /wellforge:implement $SLUG --mode $NEW_RIGOR   (announced, recorded, does not change rigor:)" \
      "  - for genuinely smaller work:  a new feature at that tier" \
      "  - promote is raise-only:  /wellforge:promote $SLUG --to <higher>"
  fi
fi

# ── 2. leaving `done` ───────────────────────────────────────────────────────────
if [ "$OLD_STATUS" = "done" ] && [ "$NEW_STATUS" != "done" ]; then
  case "$NEW_STATUS" in
    superseded|archived) ;;   # the two sanctioned retirements of already-closed work
    *) refuse "status moved backwards from done to '$NEW_STATUS' in $REL" \
         "A closed feature does not reopen by editing its status — that erases the record that it shipped." \
         "  - replaced by other work:  /wellforge:done $SLUG --superseded-by <NNN-slug>" \
         "  - stopped deliberately:    /wellforge:done $SLUG --archive \"<why>\"" \
         "  - closed by mistake:       git revert the commit that closed it, so the history says so" ;;
  esac
fi

# ── 3. arriving at `done` — the gate, not a promise ─────────────────────────────
# CARVE-OUT: a file with no version at HEAD is being CREATED, and creation is not a
# transition. Writing a retro spec that documents already-shipped work (the brownfield
# /wellforge:adopt shape, or back-filling history) can never satisfy a gate about tasks and
# QE runs that predate the spec, and blocking it would mean the only way to record history
# is to switch the guard off. Loud, because it is also the shape a bypass would take.
if [ "$NEW_STATUS" = "done" ] && [ -z "$BEFORE" ]; then
  echo "post-spec-guard: $REL is NEW and already \`status: done\` — allowed as a record of" >&2
  echo "  work that predates this spec, not as a lifecycle transition. The done gate was NOT" >&2
  echo "  evaluated. If this is a live feature, close it with /wellforge:done $SLUG instead." >&2
  exit 0
fi
if [ "$NEW_STATUS" = "done" ] && [ "$OLD_STATUS" != "done" ]; then
  STATE_SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/forge-state.py"
  if [ ! -f "$STATE_SCRIPT" ]; then
    echo "post-spec-guard: forge-state.py not found — done gate not verified (advisory)" >&2
    exit 0
  fi
  # forge-state needs pyyaml to read frontmatter. The system python3 usually lacks it, and
  # a guard that falls open on most machines is not a guard — so fall back to uv, which the
  # plugin already requires for the copier flow and which caches the env after the first run.
  RUNNER=""
  if python3 -c "import yaml" >/dev/null 2>&1; then
    RUNNER="python3"
  elif command -v uv >/dev/null 2>&1; then
    RUNNER="uv run --quiet --with pyyaml python"
  fi
  if [ -z "$RUNNER" ]; then
    echo "post-spec-guard: no python with pyyaml (and no uv) — done gate not verified (advisory)" >&2
    exit 0
  fi
  GATE=$(cd "$PROJECT_DIR" && $RUNNER "$STATE_SCRIPT" --json --feature "$SLUG" --root "$PROJECT_DIR" 2>/dev/null)
  if [ -z "$GATE" ]; then
    # pyyaml missing, or the script could not run: fail OPEN and say so. A guard that blocks
    # when it cannot evaluate teaches people to disable it.
    echo "post-spec-guard: could not evaluate the done gate (forge-state.py unavailable) — allowed, unverified" >&2
    exit 0
  fi
  VERDICT=$(printf '%s' "$GATE" | python3 -c '
import json, sys
try:
    env = json.load(sys.stdin)
except Exception:
    print("SKIP|"); raise SystemExit
fs = [f for f in env.get("features", []) if f.get("slug") == sys.argv[1]]
if not fs:
    print("SKIP|"); raise SystemExit
f = fs[0]
g = f.get("done_gate", {})
problems = f.get("problems", [])
# A parser that could not run is not a verdict. forge-state reports the absence of pyyaml
# as a problem so a human sees it; here it means UNVERIFIABLE, and a guard that blocks when
# it cannot evaluate is a guard people switch off.
if any("pyyaml unavailable" in p or "not parsed" in p for p in problems):
    print("SKIP|pyyaml unavailable"); raise SystemExit
if problems:
    print("PROBLEMS|" + " ; ".join(problems)); raise SystemExit
p = g.get("passes")
if p is True:
    print("PASS|")
elif p is None:
    print("UNCHECKABLE|" + (g.get("note") or ""))
else:
    print("FAIL|" + " ; ".join(g.get("failing", [])))
' "$SLUG")
  KIND="${VERDICT%%|*}"; DETAIL="${VERDICT#*|}"
  case "$KIND" in
    PASS) ;;
    UNCHECKABLE)
      # The spike tier closes on prose in brief.md; no script can read whether a finding
      # answers a question. Allowing it is the carve-out, not an oversight.
      echo "post-spec-guard: $SLUG closes at the spike tier — gate is not machine-checkable, allowed" >&2 ;;
    PROBLEMS)
      refuse "frontmatter in $REL does not validate, so a done status cannot be trusted" \
        "$DETAIL" "Fix the frontmatter first (config/spec-frontmatter.schema.json mirrors the spec-driven skill)." ;;
    SKIP)
      echo "post-spec-guard: $SLUG not found in forge-state output — gate unverified (advisory)" >&2 ;;
    *)
      OLD_IFS="$IFS"; IFS=';'
      set -- $DETAIL
      IFS="$OLD_IFS"
      ARGS=()
      for f in "$@"; do
        trimmed=$(printf '%s' "$f" | sed 's/^ *//; s/ *$//')
        [ -n "$trimmed" ] && ARGS+=("· $trimmed")
      done
      ARGS+=("Run /wellforge:done $SLUG instead: it checks this gate and refuses for the same reasons.")
      refuse "the done gate is not met for $SLUG — status: done was written anyway" "${ARGS[@]}" ;;
  esac
fi

# ── 4. any frontmatter that fails the schema ────────────────────────────────────
# Cheap re-check for the transitions that are otherwise legal (e.g. draft -> approved):
# a typo'd status is invisible to every rule above, because it matches none of them.
if [ -n "$NEW_STATUS" ]; then
  case "$NEW_STATUS" in
    draft|approved|in-progress|done|superseded|archived) ;;
    *) refuse "'$NEW_STATUS' is not a status in the lifecycle ($REL)" \
         "Valid: draft, approved, in-progress, done, superseded, archived." \
         "A status outside the enum is read as 'approximately right' by a model and rejected by every script." ;;
  esac
fi
if [ -n "$NEW_RIGOR" ]; then
  case "$NEW_RIGOR" in
    spike|mvp|production) ;;
    *) refuse "'$NEW_RIGOR' is not a rigor tier ($REL)" "Valid: spike, mvp, production." ;;
  esac
fi

exit 0
