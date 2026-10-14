---
type: C4 Component
title: Coverage threshold check
status: stable
groma:
  id: check-jacoco
  parent: gate-scripts
  code:
    - scanner: python
      file: gates/scripts/check-jacoco.py
  technology: Python
description: Enforces minimum coverage from a JaCoCo report
---

Reads a JaCoCo XML report and fails below the configured line (and optional branch) minimum. Skips enforcement for modules under a floor of total lines so a fresh scaffold does not fail its own gate.
