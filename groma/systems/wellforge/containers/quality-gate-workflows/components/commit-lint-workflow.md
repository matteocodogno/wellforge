---
type: C4 Component
title: commit-lint workflow
status: draft
groma:
  id: commit-lint-workflow
  parent: quality-gate-workflows
  group: Policy gates
---

Reusable CI enforcement of Conventional Commits on PRs. The local commit-msg hook can be skipped with --no-verify, so CI is the enforcement point.
