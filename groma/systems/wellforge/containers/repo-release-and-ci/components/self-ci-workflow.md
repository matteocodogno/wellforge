---
type: C4 Component
title: Self CI workflow
status: draft
groma:
  id: self-ci-workflow
  parent: repo-release-and-ci
  group: Self-verification
---

.github/workflows/ci.yml, the one workflow with real triggers: lints this repo's own commits, keeps history linear, guards drift and smoke-tests all three presets by scaffolding each. The reusable gates only ever run from generated projects.
