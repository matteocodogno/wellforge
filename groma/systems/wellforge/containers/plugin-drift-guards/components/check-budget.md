---
type: C4 Component
title: Session budget guard
status: stable
groma:
  id: check-budget
  parent: plugin-drift-guards
  code:
    - scanner: python
      file: wellforge-plugin/scripts/check-budget.py
  technology: Python
description: Caps what the plugin costs before the user types
---

Estimates the token weight of every skill, command and agent description loaded into each session, prints the worst offenders and fails past the ceiling in config/budget.yml so the number can only fall by a deliberate decision.
