---
type: C4 Component
title: Headless eval gate
status: stable
groma:
  id: run-eval
  parent: gate-scripts
  code:
    - scanner: python
      file: gates/scripts/run-eval.py
  technology: Python
description: Scores a feature against the rubric in CI
---

Calls the Anthropic API as an LM judge against gates/configs/eval-rubric.yml and fails when the weighted total is under the pass score or any dimension is under its floor. A canned judge response lets the gating logic be tested offline.
