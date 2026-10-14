---
type: C4 Component
title: Feature state
status: stable
groma:
  id: forge-state
  parent: plugin-runtime-scripts
  code:
    - scanner: python
      file: wellforge-plugin/scripts/forge-state.py
  technology: Python
description: Reports where every feature is in its lifecycle
---

One deterministic pass over specs/ that reads spec frontmatter, counts task checkboxes and joins run-trace verdicts. /wellforge:status, :triage, :done and :promote call it instead of letting the model re-derive state, and it rejects a typo such as `status: doen` outright.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [wellforge-plugin/scripts/forge-state.py](../../../../../../wellforge-plugin/scripts/forge-state.py) | [wellforge-plugin/scripts/run-report.py](../../../../../../wellforge-plugin/scripts/run-report.py) | Loads run traces from | importlib |
