---
type: C4 Component
title: template-drift workflow
status: draft
groma:
  id: template-drift-workflow
  parent: quality-gate-workflows
  group: Opt-in and scheduled
---

Reusable scheduled check that a generated project has not fallen behind its template: reads .forge/manifest.json, compares with the latest release and files one issue pointing at /wellforge:upgrade. Reports only; never upgrades.
