---
type: C4 Component
title: Deterministic layer shipper
status: stable
groma:
  id: deterministic
  parent: adapter-generators
  code:
    - scanner: python
      file: adapters/deterministic.py
  technology: Python
description: Ships the scripts and configs into an adapter's output
---

Copies forge-state, run-report, security-triggers and their YAML configs into the adapter's tree and repoints the generated prompts at them, so instructions that name those files no longer point at nothing.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [adapters/deterministic.py](../../../../../../adapters/deterministic.py) | [wellforge-plugin/scripts/forge-state.py](../../../../../../wellforge-plugin/scripts/forge-state.py) | Ships into adapter output | File copy |
| [adapters/deterministic.py](../../../../../../adapters/deterministic.py) | [wellforge-plugin/scripts/run-report.py](../../../../../../wellforge-plugin/scripts/run-report.py) | Ships into adapter output | File copy |
| [adapters/deterministic.py](../../../../../../adapters/deterministic.py) | [wellforge-plugin/scripts/security-triggers.py](../../../../../../wellforge-plugin/scripts/security-triggers.py) | Ships into adapter output | File copy |
