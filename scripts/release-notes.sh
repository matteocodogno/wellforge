#!/usr/bin/env bash
# Render release notes for a tag from its Conventional Commits.
#
#   scripts/release-notes.sh <tag> [previous-tag]
#
# Previous tag defaults to the nearest earlier vX.Y.Z (gates-v* tags are a separate series
# and are skipped). Output is markdown on stdout — used by .github/workflows/release.yml and
# by the one-off backfill of historical releases, so both read identically.
set -euo pipefail

tag="${1:?usage: release-notes.sh <tag> [previous-tag]}"
prev="${2:-}"

if [ -z "$prev" ]; then
  # version-sorted list of template tags; take the one right before $tag
  prev=$(git tag -l 'v*' --sort=v:refname | grep -v '^gates-' | awk -v t="$tag" '$0==t{print p; exit} {p=$0}')
fi

range="${prev:+$prev..}$tag"
count=$(git rev-list --count "$range")

section() {           # section <heading> <type-regex>
  local heading="$1" types="$2" body
  body=$(git log "$range" --no-merges --format='%s|%h' \
    | awk -F'|' -v re="^($types)(\\(.+\\))?!?: " '$1 ~ re {print}' \
    | sed -E 's/^([a-z]+)(\(([^)]+)\))?!?: (.*)\|(.*)$/- \3: \4 (`\5`)/; s/^- : /- /')
  [ -n "$body" ] && printf '### %s\n%s\n\n' "$heading" "$body"
  return 0
}

printf '%s — %s commit(s)%s\n\n' "$tag" "$count" "${prev:+ since $prev}"

breaking=$(git log "$range" --no-merges --format='%s|%h' | grep -E '^[a-z]+(\([^)]+\))?!: ' || true)
if [ -n "$breaking" ]; then
  printf '### ⚠️ Breaking changes\n%s\n\n' \
    "$(printf '%s' "$breaking" | sed -E 's/^([a-z]+)(\(([^)]+)\))?!: (.*)\|(.*)$/- \3: \4 (`\5`)/; s/^- : /- /')"
fi

section 'Features'       'feat'
section 'Fixes'          'fix'
section 'Performance'    'perf'
section 'Refactoring'    'refactor'
section 'Documentation'  'docs'
section 'Maintenance'    'chore|ci|build|test|style|revert'

printf '**Full diff:** %s\n' "${prev:+\`$prev...$tag\`}"
