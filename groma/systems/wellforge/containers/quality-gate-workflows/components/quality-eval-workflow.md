---
type: C4 Component
title: quality-eval workflow
status: draft
groma:
  id: quality-eval-workflow
  parent: quality-gate-workflows
  group: Opt-in and scheduled
---

Opt-in LM-judge gate that scores a feature against the central rubric. It covers what tests and coverage cannot (spec fidelity, test quality, conventions), and costs API tokens, so it is wired only on agent-facing or high-stakes changes.
