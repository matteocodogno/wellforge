---
type: C4 Component
title: Adapter smoke test
status: stable
groma:
  id: smoke-test
  parent: adapter-generators
  code:
    - scanner: python
      file: adapters/smoke-test.py
  technology: Python
description: Proves an adapter's output is shippable
---

Generates an adapter into a temp dir and asserts that no file is empty, the deterministic layer's references resolve and its scripts run, and routing matches. Each assertion guards a failure the generators' own summaries would not show.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [adapters/smoke-test.py](../../../../../../adapters/smoke-test.py) | [adapters/opencode/generate.py](../../../../../../adapters/opencode/generate.py) | Runs to produce output | subprocess |
| [adapters/smoke-test.py](../../../../../../adapters/smoke-test.py) | [adapters/copilot/generate.py](../../../../../../adapters/copilot/generate.py) | Runs to produce output | subprocess |
| [adapters/smoke-test.py](../../../../../../adapters/smoke-test.py) | [wellforge-plugin/scripts/check-routing.py](../../../../../../wellforge-plugin/scripts/check-routing.py) | Verifies generated routing with | subprocess |
