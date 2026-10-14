---
type: C4 Component
title: release-cli script
status: draft
groma:
  id: release-cli-script
  parent: repo-release-and-ci
  group: Release path
---

scripts/release-cli.sh cuts a cli-v tag: plans by default, then bumps the version constant, the formula URL and the docs together, and restores the tree if it stops.
