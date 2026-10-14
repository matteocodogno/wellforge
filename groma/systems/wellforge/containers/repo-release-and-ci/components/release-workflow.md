---
type: C4 Component
title: Release workflow
status: draft
groma:
  id: release-workflow
  parent: repo-release-and-ci
  group: Release path
---

.github/workflows/release.yml publishes a GitHub Release when a template tag is pushed and prepares the Homebrew formula bump as a separate follow-up branch, never writing to main.
