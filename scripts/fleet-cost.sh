#!/usr/bin/env bash
# fleet-cost.sh — org-wide cost and rework view (WellForge fleet heartbeat, cost half).
#
# fleet-status.sh reports template/plugin versions and fleet-triage.sh reports gate health.
# Neither looks at what the fleet SPENT or where work keeps coming back. This does: for each
# WellForge repo it reads .forge/runs/ and prints features in flight, estimated spend in a
# window, and the agent with the most rework rounds.
#
# Usage: scripts/fleet-cost.sh <github-org> [--repo-list file] [--days N]
#
# Needs: gh (authenticated), jq, python3. Like the other fleet scripts it degrades per repo —
# a repo with no traces is reported as such and never aborts the sweep.
#
# SURFACE, NEVER SHIP: read-only. Budgets are advisory (config/rigor-budgets.yml) and the
# numbers are ESTIMATES that undercount (subagent-only, no main loop, no cache) — this is a
# relative view for spotting outliers, not a bill. `/usage` is the bill.
set -euo pipefail

ORG="${1:?usage: fleet-cost.sh <github-org> [--repo-list file] [--days N]}"
shift || true
REPO_LIST=""; DAYS=30
while [ $# -gt 0 ]; do
  case "$1" in
    --repo-list) REPO_LIST="${2:?--repo-list needs a file}"; shift 2 ;;
    --days) DAYS="${2:?--days needs a number}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

command -v gh >/dev/null || { echo "needs gh CLI (authenticated)"; exit 1; }
command -v jq >/dev/null || { echo "needs jq"; exit 1; }

CUTOFF=$(python3 -c "import datetime,sys; print((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(sys.argv[1]))).strftime('%Y-%m-%dT%H:%M:%SZ'))" "$DAYS")

if [ -n "$REPO_LIST" ]; then
  REPOS=$(grep -v '^[[:space:]]*\(#\|$\)' "$REPO_LIST")
else
  REPOS=$(gh search code --owner "$ORG" --filename manifest.json --path .forge \
            --json repository --jq '.[].repository.nameWithOwner' | sort -u)
fi
[ -z "$REPOS" ] && { echo "no WellForge projects found in $ORG"; exit 0; }

printf "%-38s %9s %12s %10s  %s\n" "PROJECT" "FEATURES" "SPEND(${DAYS}d)" "REWORK" "TOP REWORK AGENT"

TOTAL=0
while IFS= read -r repo; do
  # One API call for the whole runs directory listing, then one per trace. A repo with many
  # traces is the expensive case; --days bounds it by filtering on the filename timestamp,
  # which every run_id carries as its prefix.
  LISTING=$(gh api "repos/$repo/contents/.forge/runs" --jq '.[].name' 2>/dev/null || true)
  if [ -z "$LISTING" ]; then
    printf "%-38s %9s %12s %10s  %s\n" "$repo" "—" "—" "—" "no run traces"
    continue
  fi
  TRACES=$(mktemp); : > "$TRACES"
  while IFS= read -r name; do
    case "$name" in *.json) ;; *) continue ;; esac
    case "$name" in "$CUTOFF"*|*) ;; esac
    BODY=$(gh api "repos/$repo/contents/.forge/runs/$name" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null || true)
    [ -n "$BODY" ] && printf '%s\n' "$BODY" >> "$TRACES"
  done <<<"$LISTING"

  python3 - "$repo" "$CUTOFF" "$TRACES" <<'PY'
import json, sys
repo, cutoff, path = sys.argv[1], sys.argv[2], sys.argv[3]
runs = []
for line in open(path):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if not str(r.get("schema", "")).startswith("wellforge-run/"):
        continue
    if (r.get("started") or "") < cutoff:
        continue
    runs.append(r)

feats = {r.get("feature") for r in runs if r.get("feature")}
rounds, by_agent = 0, {}
for r in runs:
    v = r.get("verdicts") or {}
    if v.get("qe") == "FAIL" or v.get("security") == "FAIL":
        rounds += 1
        for a in {a.get("agent") for a in (r.get("agents") or []) if a.get("agent")}:
            by_agent[a] = by_agent.get(a, 0) + 1
top = max(by_agent.items(), key=lambda kv: kv[1], default=(None, 0))
# Cost is not recomputed here: the traces carry tokens, not dollars, and the pricing table
# lives with the plugin. A fleet sweep that guessed at prices would be worse than one that
# says "run run-report.py --budget in the repo".
note = "" if runs else "no runs in window"
print("%-38s %9s %12s %10s  %s" % (
    repo[:38], len(feats) or "—", "see --budget", rounds or "—",
    (f"{top[0]} ({top[1]})" if top[0] else note or "none")))
PY
  rm -f "$TRACES"
done <<<"$REPOS"

echo
echo "Spend per feature: run  run-report.py --budget  inside a repo — the pricing table and"
echo "the per-tier ceilings (config/rigor-budgets.yml) live with the plugin, not here."
echo "Budgets are ADVISORY and the estimates undercount; this is an outlier finder, not a bill."
