---
type: C4 Component
title: Model routing guard
status: stable
groma:
  id: check-routing
  parent: plugin-drift-guards
  code:
    - scanner: python
      file: wellforge-plugin/scripts/check-routing.py
  technology: Python
description: Checks agent models match the routing policy
---

Verifies each agent's frontmatter model equals tiers[tool][routing tier], for the Claude plugin and, with a glob, for generated adapter agents. Exits non-zero on any mismatch.
