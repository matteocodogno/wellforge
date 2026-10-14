---
type: C4 Component
title: Commit message check
status: stable
groma:
  id: check-commit-msg
  parent: gate-scripts
  code:
    - scanner: python
      file: gates/scripts/check-commit-msg.py
      symbol: main
  technology: Python
description: Enforces Conventional Commits on a commit message
---

Validates the subject line against type(scope)!: description and exits non-zero with a helpful message. One script shared by the local commit-msg hook and the commit-lint CI gate; merge, revert, fixup and squash commits are exempt.
