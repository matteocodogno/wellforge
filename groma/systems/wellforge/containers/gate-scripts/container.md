---
type: C4 Container
title: Quality gate scripts
status: stable
groma:
  id: gate-scripts
  parent: wellforge
---

Python helpers behind the central quality gates: Conventional Commits validation, JaCoCo coverage thresholds and the headless LM-judge eval. Shared by the committed git hooks and the reusable CI workflows.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [gate-scripts](container.md) | [anthropic-api](../../../../externals/anthropic-api.md) | Calls as judge | HTTPS |
