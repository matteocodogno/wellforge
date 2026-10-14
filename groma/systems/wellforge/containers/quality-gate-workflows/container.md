---
type: C4 Container
title: Quality gate workflows
status: draft
groma:
  id: quality-gate-workflows
  parent: wellforge
---

The reusable GitHub Actions workflows and their configs that every scaffold references by a gates-v* tag and never copies. Thresholds live here and change only by PR, which is the single point of discretion. GitHub only resolves workflow_call from .github/workflows/, so the files live there while gates/ holds their configs, scripts and hooks. Workflow YAML is not read by a scanner, so this stays a draft.
