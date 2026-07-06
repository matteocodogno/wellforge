#!/usr/bin/env bash
# fleet-triage.sh — the FLEET HEARTBEAT's data-gathering step (WellForge Phase 14b).
#
# Extends fleet-status.sh: for every WellForge-generated repo in an org it reports BOTH
#   (1) template drift  — recorded manifest version vs the latest vX.Y.Z template release, and
#   (2) gate health     — the conclusion of the latest completed CI run on the default branch.
# Output is a triage report grouped by what needs attention, plus a one-line summary — meant to
# be run on a schedule and posted (surface, never auto-ship: it changes nothing, it only reports).
#
# Usage: scripts/fleet-triage.sh <github-org> [--repo-list file]
#   --repo-list: check the listed repos (one owner/repo per line) instead of a code search.
#
# Needs: gh (authenticated — GITHUB_TOKEN works in headless/cron), jq. Degrades per-repo:
# an unreadable manifest or unavailable CI is reported as such, never aborts the sweep.
set -euo pipefail

ORG="${1:?usage: fleet-triage.sh <github-org> [--repo-list file]}"
shift || true
REPO_LIST=""
[ "${1:-}" = "--repo-list" ] && REPO_LIST="${2:?--repo-list needs a file}"

command -v gh >/dev/null || { echo "needs gh CLI (authenticated)"; exit 1; }
command -v jq >/dev/null || { echo "needs jq"; exit 1; }

LATEST=$(git -C "$(dirname "$0")/.." tag -l 'v[0-9]*' --sort=-v:refname | head -1)
LATEST="${LATEST:-none}"
LATEST_NUM="${LATEST#v}"

if [ -n "$REPO_LIST" ]; then
  REPOS=$(grep -v '^[[:space:]]*\(#\|$\)' "$REPO_LIST")
else
  REPOS=$(gh search code --owner "$ORG" --filename manifest.json --path .forge \
            --json repository --jq '.[].repository.nameWithOwner' | sort -u)
fi
[ -z "$REPOS" ] && { echo "no WellForge projects found in $ORG"; exit 0; }

# behind_count <current> — how many vX.Y.Z releases newer than <current> (version-aware).
behind_count() {
  local current="$1" n=0 v newer
  [ "$LATEST" = "none" ] && { echo 0; return; }
  while IFS= read -r v; do
    [ -z "$v" ] && continue
    [ "$v" = "$current" ] && continue
    newer=$(printf '%s\n%s\n' "$current" "$v" | sort -V | tail -1)
    [ "$newer" = "$v" ] && n=$((n + 1))
  done < <(git -C "$(dirname "$0")/.." tag -l 'v[0-9]*' | sed 's/^v//' | sort -Vu)
  echo "$n"
}

behind=""; failing=""; unknown=""; healthy=0; total=0

while IFS= read -r repo; do
  [ -z "$repo" ] && continue
  total=$((total + 1))

  manifest=$(gh api "repos/$repo/contents/.forge/manifest.json" --jq '.content' 2>/dev/null \
               | base64 -d 2>/dev/null) || { unknown+="  $repo  (manifest unreadable)"$'\n'; continue; }
  version=$(jq -r '.version // "?"' <<<"$manifest")

  # (1) drift
  n=$(behind_count "$version")
  if [ "$n" -gt 0 ]; then
    behind+="  $(printf '%-40s %s → %s (%d behind)' "$repo" "$version" "$LATEST_NUM" "$n")"$'\n'
  fi

  # (2) gate health — latest completed run on the default branch
  default=$(gh api "repos/$repo" --jq '.default_branch' 2>/dev/null || echo "")
  concl=$(gh api "repos/$repo/actions/runs?branch=${default}&status=completed&per_page=1" \
            --jq '.workflow_runs[0].conclusion // "none"' 2>/dev/null || echo "unavailable")
  url=$(gh api "repos/$repo/actions/runs?branch=${default}&status=completed&per_page=1" \
            --jq '.workflow_runs[0].html_url // ""' 2>/dev/null || echo "")
  case "$concl" in
    success|none) : ;;                                   # green (or no CI yet) — fine
    unavailable)  unknown+="  $repo  (CI unavailable)"$'\n' ;;
    *)            failing+="  $(printf '%-40s CI %s  %s' "$repo" "$concl" "$url")"$'\n' ;;
  esac

  { [ "$n" -eq 0 ] && { [ "$concl" = "success" ] || [ "$concl" = "none" ]; }; } && healthy=$((healthy + 1))
done <<<"$REPOS"

echo "WellForge fleet triage — $ORG   (latest template: ${LATEST})"
echo
[ -n "$behind" ]  && { echo "⬆ Behind template (run /wellforge:upgrade)"; printf '%s' "$behind"; echo; }
[ -n "$failing" ] && { echo "✗ Failing gates (latest CI on default branch)"; printf '%s' "$failing"; echo; }
[ -n "$unknown" ] && { echo "? Unknown"; printf '%s' "$unknown"; echo; }
b=$(printf '%s' "$behind"  | grep -c . || true)
f=$(printf '%s' "$failing" | grep -c . || true)
echo "Summary: ${total} projects · ${healthy} healthy · ${b} behind · ${f} failing"
[ "$b" -eq 0 ] && [ "$f" -eq 0 ] && echo "Fleet healthy — nothing needs attention."
