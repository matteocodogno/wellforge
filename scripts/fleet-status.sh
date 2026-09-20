#!/usr/bin/env bash
# fleet-status.sh — list WellForge-generated projects, their template AND plugin versions.
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

# The plugin version this checkout ships. A project can be current on the template and
# stale on the plugin, or the reverse — they move independently, which is the whole reason
# the manifest records both.
PLUGIN_LATEST=$(jq -r '.version // "?"' \
  "$(dirname "$0")/../wellforge-plugin/.claude-plugin/plugin.json" 2>/dev/null || echo "?")

if [ -n "$REPO_LIST" ]; then
  REPOS=$(grep -v '^\s*\(#\|$\)' "$REPO_LIST")
else
  # Code search: repos in the org with a .forge/manifest.json
  REPOS=$(gh search code --owner "$ORG" --filename manifest.json --path .forge \
            --json repository --jq '.[].repository.nameWithOwner' | sort -u)
fi

[ -z "$REPOS" ] && { echo "no WellForge projects found in $ORG"; exit 0; }

printf "%-38s %-20s %-9s %-9s %s\n" "REPO" "TEMPLATE" "VERSION" "PLUGIN" "STATUS (template $LATEST · plugin $PLUGIN_LATEST)"
while IFS= read -r repo; do
  MANIFEST=$(gh api "repos/$repo/contents/.forge/manifest.json" --jq '.content' 2>/dev/null \
               | base64 -d 2>/dev/null) || { printf "%-45s %s\n" "$repo" "manifest unreadable"; continue; }
  TEMPLATE=$(jq -r '.template // "?"' <<<"$MANIFEST")
  VERSION=$(jq -r '.version // "?"' <<<"$MANIFEST")
  # `plugin` is an object since 2.38 and was a bare string in early adoptions; "—" means the
  # project predates the field entirely, which is information, not an error.
  PLUGIN=$(jq -r 'if (.plugin|type) == "object" then .plugin.version
                  elif (.plugin|type) == "string" then .plugin
                  else "—" end' <<<"$MANIFEST")
  if [ "$LATEST" = "none" ]; then STATUS="-"
  elif [ "v$VERSION" = "$LATEST" ] || [ "$VERSION" = "$LATEST" ]; then STATUS="✓ current"
  else STATUS="⬆ template outdated → /wellforge:upgrade"
  fi
  # Plugin staleness is reported alongside, not folded into, template staleness: a project
  # can be current on one and behind on the other, and one upgrade run fixes both.
  if [ "$PLUGIN" = "—" ]; then STATUS="$STATUS · plugin unrecorded (pre-2.38)"
  elif [ "$PLUGIN" != "$PLUGIN_LATEST" ] && [ "$PLUGIN_LATEST" != "?" ]; then
    STATUS="$STATUS · plugin $PLUGIN < $PLUGIN_LATEST"
  fi
  printf "%-38s %-20s %-9s %-9s %s\n" "$repo" "$TEMPLATE" "$VERSION" "$PLUGIN" "$STATUS"
done <<<"$REPOS"
