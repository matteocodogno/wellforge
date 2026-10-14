---
type: C4 Component
title: Git policy setup
status: draft
groma:
  id: git-policy-setup
  parent: repo-release-and-ci
  group: Release path
---

scripts/setup-git-policy.sh applies linear history and Conventional Commits config to a clone, idempotently, and installs the committed hooks.
