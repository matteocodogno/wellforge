---
type: C4 Component
title: Run report
status: stable
groma:
  id: run-report
  parent: plugin-runtime-scripts
  code:
    - scanner: python
      file: wellforge-plugin/scripts/run-report.py
  technology: Python
description: Summarizes agent run traces with cost estimates
---

Reads the semantic traces in .forge/runs/, joins best-effort token events by each run's time window, and prints per-run agents, verdicts, drift and an estimated cost. Who, what and verdict are exact; token cost is an estimate.
