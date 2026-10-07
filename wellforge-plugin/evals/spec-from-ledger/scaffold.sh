#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# A decision ledger as /wellforge:grill-me leaves it for a free-form idea. The decisions are
# deliberately ones nobody would guess (14 months, EUR only, a 12-character code), so a spec
# that carries them got them from this file and from nowhere else.
mkdir -p .forge/grill
cp "$here/../fixtures/ledger-gift-cards.md" .forge/grill/gift-cards.md

# Last: one commit, so the state layer reads drift from git, not from copy-order mtimes.
bash "$here/../fixtures/commit.sh"
