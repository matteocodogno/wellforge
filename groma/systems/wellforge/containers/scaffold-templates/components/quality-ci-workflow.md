---
type: C4 Component
title: Quality CI workflow
status: draft
groma:
  id: quality-ci-workflow
  parent: scaffold-templates
  group: Generated in every project
---

.github/workflows/quality.yml. References, never copies, the central gates pinned by `gates_ref`: linear history, Conventional Commits, the secrets security floor and the stack gate (quality-jvm or quality-node). Strictness follows the project's rigor tier.
