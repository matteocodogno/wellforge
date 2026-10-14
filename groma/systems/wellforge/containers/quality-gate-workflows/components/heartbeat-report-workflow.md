---
type: C4 Component
title: heartbeat-report workflow
status: draft
groma:
  id: heartbeat-report-workflow
  parent: quality-gate-workflows
  group: Opt-in and scheduled
---

Reusable reporter that opens, updates and closes one deduplicated tracking issue for scheduled gate findings, because a scheduled run has no PR to annotate.
