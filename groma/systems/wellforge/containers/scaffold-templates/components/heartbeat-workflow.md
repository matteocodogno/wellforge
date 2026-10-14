---
type: C4 Component
title: Heartbeat workflow
status: draft
groma:
  id: heartbeat-workflow
  parent: scaffold-templates
  group: Generated in every project
---

Scheduled workflow, generated only for CI on GitHub and a rigor above spike, that re-runs the stack gate on a cron to catch CVEs and rule updates that arrive without a commit. Findings go into one deduplicated issue.
