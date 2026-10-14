---
type: C4 System
title: GitHub Actions
status: stable
groma:
  id: github-actions
  technology: GitHub
---

Runs the reusable quality-gate workflows and the repository's own CI, which call the gate scripts.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [github-actions](github-actions.md) | [gate-scripts](../systems/wellforge/containers/gate-scripts/container.md) | Runs | Reusable workflows |
| [github-actions](github-actions.md) | [quality-gate-workflows](../systems/wellforge/containers/quality-gate-workflows/container.md) | Runs | Reusable workflows |
| [github-actions](github-actions.md) | [repo-release-and-ci](../systems/wellforge/containers/repo-release-and-ci/container.md) | Runs | Workflow triggers |
