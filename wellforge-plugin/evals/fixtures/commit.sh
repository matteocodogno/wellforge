#!/usr/bin/env bash
# Commit the scaffolded fixture into a throwaway git repository. Called LAST by every case's
# scaffold.sh, after the case has made its own edits.
#
# WHY: forge-state.py decides drift from git, and falls back to file mtimes only when there
# is no repository. A fixture copied with `cp -R` gets its mtimes in copy order, so outside
# git `003-order-history` read as "spec.md and plan.md newer than tasks.md" — drifted — and
# its done gate was blocked for a reason no case intended. `done-mvp-passes` could not pass
# whatever the agent did; it scored 0.00 on the first full run of this suite (2026-10-05).
#
# A real WellForge project is always a git repository, so this also makes the fixture look
# like what the commands are written for. Everything lands in ONE commit, which the state
# layer reads as "changed together, not drift".
set -euo pipefail
git init -q .
git add -A
git -c user.name="wellforge-evals" -c user.email="evals@wellforge.invalid" \
    -c commit.gpgsign=false commit -q --no-verify -m "chore: fixture project"
