---
type: C4 Component
title: Security triggers
status: stable
groma:
  id: security-triggers
  parent: plugin-runtime-scripts
  code:
    - scanner: python
      file: wellforge-plugin/scripts/security-triggers.py
  technology: Python
description: Decides whether a batch needs an OWASP review
---

Answers one question deterministically: dispatch an owasp-reviewer or not, and why, from the batch's touched files and rigor tier. Called by implement and orchestrate between integration and QE so the security floor does not depend on the orchestrator remembering.
