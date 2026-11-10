#!/usr/bin/env bash
# check-evals-fresh.sh — say whether the prompt layer has moved since the last recorded eval
# run. ADVISORY: it warns and exits 0. `--strict` makes a stale record exit 1.
#
# The prompt evals are the only tests `commands/`, `agents/` and `skills/` have, so a release
# should know whether they ran. It used to REFUSE a plugin-v tag instead, and that did not
# hold: a full pass took ~56 min and ~$17, the suite did not cover what had changed, and the
# first time the refusal met a release everyone needed (plugin-v2.58.0, 2026-11-10) it was
# overridden. A gate that is walked past whenever it matters protects nothing; a warning
# that names the stale commit at least keeps the fact visible.
#
# "Fresh" means: the recorded SHA is the last commit that touched the prompt layer, or a
# descendant of it.
#
#   scripts/check-evals-fresh.sh                 # check — warns if stale, exit 0
#   scripts/check-evals-fresh.sh --strict        # check — exit 1 if stale
#   scripts/check-evals-fresh.sh --record <sha>  # record a run (check-all does this for you)
#
# --skip-evals / WELLFORGE_SKIP_EVALS=1 are still accepted and do nothing: the check no
# longer refuses, so there is nothing to override.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RECORD="$ROOT/wellforge-plugin/evals/LAST-RUN"
PROMPT_DIRS=(wellforge-plugin/commands wellforge-plugin/agents wellforge-plugin/skills)

STRICT=""
MODE="check"; NEW_SHA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --skip-evals) shift ;;   # accepted for old scripts; nothing to override any more
    --record) MODE="record"; NEW_SHA="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [ "$MODE" = "record" ]; then
  [ -n "$NEW_SHA" ] || { echo "--record needs a commit sha" >&2; exit 2; }
  mkdir -p "$(dirname "$RECORD")"
  {
    echo "# Written by scripts/check-evals-fresh.sh --record. The SHA is the tree the prompt"
    echo "# evals last PASSED against; see wellforge-plugin/evals/README.md."
    echo "sha: $NEW_SHA"
    echo "date: $(date -u +%Y-%m-%d)"
    echo "where: ${WELLFORGE_EVAL_SOURCE:-local}"
  } > "$RECORD"
  echo "recorded eval run at $NEW_SHA"
  exit 0
fi

# Last commit that touched anything the evals actually measure.
last_change="$(git -C "$ROOT" log -1 --format=%H -- "${PROMPT_DIRS[@]}" 2>/dev/null)"
if [ -z "$last_change" ]; then
  echo "evals: no commit has touched the prompt layer — nothing to be stale against."
  exit 0
fi

recorded=""
[ -f "$RECORD" ] && recorded="$(sed -n 's/^sha:[[:space:]]*//p' "$RECORD" | head -1)"

stale() {
  echo ""
  echo "evals: STALE (advisory) — the prompt layer changed since the last recorded run."
  echo "  last recorded eval : ${recorded:-(none ever recorded)}"
  echo "  last prompt change : $last_change"
  echo "                       $(git -C "$ROOT" log -1 --format='%s' "$last_change" 2>/dev/null)"
  echo ""
  echo "  Run them (records the result):  mise run check -- --with-evals"
  echo ""
  [ -n "$STRICT" ] && exit 1
  exit 0
}

[ -n "$recorded" ] || stale

if ! git -C "$ROOT" cat-file -e "${recorded}^{commit}" 2>/dev/null; then
  echo "evals: the recorded SHA $recorded is not a commit in this repository"
  echo "  (rebased or force-pushed away). Re-run the evals and record again."
  stale
fi

# Fresh when the recorded run is AT or AFTER the last prompt change.
if git -C "$ROOT" merge-base --is-ancestor "$last_change" "$recorded" 2>/dev/null; then
  echo "evals: fresh — last run $recorded covers the prompt layer as of $last_change"
  exit 0
fi

stale
