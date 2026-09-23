#!/usr/bin/env bash
# check-evals-fresh.sh — refuse a plugin-v tag whose prompt layer has moved since the last
# recorded eval run.
#
# The prompt evals are the only tests `commands/`, `agents/` and `skills/` have. They are
# OPTIONAL IN CI on purpose: they need an ANTHROPIC_API_KEY this repo does not have and no
# fork should need. Optional in CI plus nothing else watching equals not tested at all, and
# the plugin IS its prompts — so the freshness check lives on the release path instead, where
# it costs nothing on an ordinary push and is unavoidable at a tag.
#
# "Fresh" means: the recorded SHA is the last commit that touched the prompt layer, or a
# descendant of it. Editing a command and tagging without re-running is exactly the case this
# refuses.
#
#   scripts/check-evals-fresh.sh                 # check
#   scripts/check-evals-fresh.sh --record <sha>  # record a run (check-all does this for you)
#   scripts/check-evals-fresh.sh --skip-evals    # override, with a banner
#
# WELLFORGE_SKIP_EVALS=1 is the same as --skip-evals, for the pre-push hook, which has no
# way to pass a flag.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RECORD="$ROOT/wellforge-plugin/evals/LAST-RUN"
PROMPT_DIRS=(wellforge-plugin/commands wellforge-plugin/agents wellforge-plugin/skills)

SKIP="${WELLFORGE_SKIP_EVALS:-}"
MODE="check"; NEW_SHA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-evals) SKIP=1; shift ;;
    --record) MODE="record"; NEW_SHA="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

banner() {
  cat <<BANNER

╭───────────────────────────────────────────────────────────────────────────╮
│  ⚠  --skip-evals: THE PROMPT EVALS WERE NOT CONFIRMED FOR THIS RELEASE.   │
│                                                                           │
│  commands/, agents/ and skills/ have no other test. You are tagging a     │
│  plugin whose prompt layer changed since the last recorded eval run.      │
│  Say so in the release notes.                                             │
╰───────────────────────────────────────────────────────────────────────────╯

BANNER
}

fail() {
  echo ""
  echo "EVALS STALE — refusing to tag."
  echo "  last recorded eval : ${recorded:-(none ever recorded)}"
  echo "  last prompt change : $last_change"
  echo "                       $(git -C "$ROOT" log -1 --format='%s' "$last_change" 2>/dev/null)"
  echo ""
  echo "  Run them, then record the result:"
  echo "    scripts/check-all.sh --with-evals        # uses your own Claude Code login"
  echo "  ...or run the 'ci' workflow manually with eval_runs=3 and record the SHA it prints:"
  echo "    scripts/check-evals-fresh.sh --record <sha>"
  echo ""
  echo "  Deliberately shipping without them: --skip-evals (or WELLFORGE_SKIP_EVALS=1)."
  echo ""
  [ -n "$SKIP" ] && { banner; exit 0; }
  exit 1
}

[ -n "$recorded" ] || fail

if ! git -C "$ROOT" cat-file -e "${recorded}^{commit}" 2>/dev/null; then
  echo "evals: the recorded SHA $recorded is not a commit in this repository"
  echo "  (rebased or force-pushed away). Re-run the evals and record again."
  [ -n "$SKIP" ] && { banner; exit 0; }
  exit 1
fi

# Fresh when the recorded run is AT or AFTER the last prompt change.
if git -C "$ROOT" merge-base --is-ancestor "$last_change" "$recorded" 2>/dev/null; then
  echo "evals: fresh — last run $recorded covers the prompt layer as of $last_change"
  exit 0
fi

fail
