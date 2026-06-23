#!/usr/bin/env bash
# fleet-status.sh — list WellForge-generated projects and their template versions.
#
# Finds repos in a GitHub org containing .forge/manifest.json, reads template+version,
# and compares against the latest template release tag in this repo.
#
# Usage: scripts/fleet-status.sh <github-org> [--repo-list file]
#   --repo-list: skip the code search (needs no search scope) and check the listed
#                repos (one owner/repo per line) instead.
set -euo pipefail

ORG="${1:?usage: fleet-status.sh <github-org> [--repo-list file]}"
shift || true
REPO_LIST=""
[ "${1:-}" = "--repo-list" ] && REPO_LIST="${2:?--repo-list needs a file}"

command -v gh >/dev/null || { echo "needs gh CLI (authenticated)"; exit 1; }
command -v jq >/dev/null || { echo "needs jq"; exit 1; }

# Latest template release tag in this repo (vX.Y.Z only — gates-v* are not template tags)
LATEST=$(git -C "$(dirname "$0")/.." tag -l 'v[0-9]*' --sort=-v:refname | head -1)
LATEST="${LATEST:-none}"

if [ -n "$REPO_LIST" ]; then
  REPOS=$(grep -v '^\s*\(#\|$\)' "$REPO_LIST")
else
  # Code search: repos in the org with a .forge/manifest.json
  REPOS=$(gh search code --owner "$ORG" --filename manifest.json --path .forge \
            --json repository --jq '.[].repository.nameWithOwner' | sort -u)
fi

[ -z "$REPOS" ] && { echo "no WellForge projects found in $ORG"; exit 0; }

printf "%-45s %-22s %-10s %s\n" "REPO" "TEMPLATE" "VERSION" "STATUS (latest: $LATEST)"
while IFS= read -r repo; do
  MANIFEST=$(gh api "repos/$repo/contents/.forge/manifest.json" --jq '.content' 2>/dev/null \
               | base64 -d 2>/dev/null) || { printf "%-45s %s\n" "$repo" "manifest unreadable"; continue; }
  TEMPLATE=$(jq -r '.template // "?"' <<<"$MANIFEST")
  VERSION=$(jq -r '.version // "?"' <<<"$MANIFEST")
  if [ "$LATEST" = "none" ]; then STATUS="-"
  elif [ "v$VERSION" = "$LATEST" ] || [ "$VERSION" = "$LATEST" ]; then STATUS="✓ current"
  else STATUS="⬆ outdated → run /wellforge:upgrade"
  fi
  printf "%-45s %-22s %-10s %s\n" "$repo" "$TEMPLATE" "$VERSION" "$STATUS"
done <<<"$REPOS"
