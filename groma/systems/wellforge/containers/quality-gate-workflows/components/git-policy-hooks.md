---
type: C4 Component
title: Git policy hooks
status: draft
groma:
  id: git-policy-hooks
  parent: quality-gate-workflows
  group: Configs and git hooks
---

Committed hooks in gates/hooks: commit-msg (Conventional Commits), pre-merge-commit (refuses merge commits) and pre-push (refuses to push a release tag from a tree whose self-tests are red). Installed by setup-git-policy.sh.
