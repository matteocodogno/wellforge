#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# The shared fixture's 001 has a plan and NO tasks.md (status-rows asserts exactly that).
# /wellforge:implement stops at a missing tasks.md, and a run that stops there never reaches
# the behaviour this case is about — one of three runs did precisely that and said nothing
# about the tier. So this case gives its own copy a task list, per the README: a case that
# needs a different state edits its own copy, never the shared fixture.
cat > specs/001-checkout-flow/tasks.md <<'TASKS'
---
spec: 001-checkout-flow
generated: 2026-09-23
---

# Tasks — checkout flow

- [ ] T1 — payments module and PSP adapter  <!-- agent: backend-dev -->
  - ACs: AC-1, AC-2
  - deps: none
  - touch: backend/src/payments/**
  - done when: the payments integration test passes for a valid and a declined card
- [ ] T2 — checkout screen  <!-- agent: frontend-dev -->
  - ACs: AC-1, AC-2
  - deps: T1
  - touch: frontend/src/checkout/**
  - done when: the checkout component test shows the issuer's reason on a declined card
TASKS

# Last: one commit, so the state layer reads drift from git, not from copy-order mtimes.
bash "$here/../fixtures/commit.sh"
