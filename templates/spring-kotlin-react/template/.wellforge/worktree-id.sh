#!/usr/bin/env sh
# Derive this checkout's isolation identity — see docs/adr/0002-per-worktree-databases.md.
#
# A git worktree isolates the CHECKOUT and nothing else: two worktrees resolve a database
# name, a host port and a compose project to the same object. This script turns the one
# thing that IS unique per checkout — its absolute path — into names that are not shared.
#
#   suffix  ""              (primary tree)  | "_wt<hash8>"  (linked worktree)
#   id      "main"                          | "wt<hash8>"
#   port    $WF_DB_BASE_PORT (default 5432) | base + (hash mod 1000)
#   linked  "no" | "yes"
#
# The primary tree keeps the plain name and base port on purpose: upgrading an existing
# project must not orphan the dev database someone already has data in.
set -eu

top=$(git rev-parse --show-toplevel 2>/dev/null) || top=""
base_port=${WF_DB_BASE_PORT:-5432}

if [ -z "$top" ]; then
  # Not a git tree (a tarball, a Docker build context). No worktrees exist here, so there
  # is nothing to isolate from: behave exactly like the primary tree.
  case "${1:-id}" in
    suffix) printf '' ;; id) printf 'main' ;; port) printf '%s' "$base_port" ;; linked) printf 'no' ;;
    *) echo "usage: worktree-id.sh [suffix|id|port|linked]" >&2; exit 2 ;;
  esac
  exit 0
fi

# A linked worktree is the only case where .git-dir and .git-common-dir diverge.
if [ "$(git rev-parse --git-dir)" != "$(git rev-parse --git-common-dir)" ]; then
  linked=yes
else
  linked=no
fi

hash=$(printf %s "$top" | { command -v sha256sum >/dev/null 2>&1 && sha256sum || shasum -a 256; } | cut -c1-8)

case "${1:-id}" in
  linked) printf '%s' "$linked" ;;
  suffix) [ "$linked" = yes ] && printf '_wt%s' "$hash" || printf '' ;;
  id)     [ "$linked" = yes ] && printf 'wt%s' "$hash" || printf 'main' ;;
  port)
    if [ "$linked" = no ]; then printf '%s' "$base_port"; exit 0; fi
    # Hex -> decimal in awk: `$((16#..))` is not POSIX and dash rejects it.
    off=$(awk -v h="$hash" 'BEGIN{n=0;for(i=1;i<=length(h);i++){n=(n*16+index("0123456789abcdef",substr(h,i,1))-1)%1000}print n}')
    printf '%s' "$((base_port + off))" ;;
  *) echo "usage: worktree-id.sh [suffix|id|port|linked]" >&2; exit 2 ;;
esac
