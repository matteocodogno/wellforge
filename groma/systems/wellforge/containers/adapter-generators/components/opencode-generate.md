---
type: C4 Component
title: OpenCode generator
status: stable
groma:
  id: opencode-generate
  parent: adapter-generators
  code:
    - scanner: python
      file: adapters/opencode/generate.py
  technology: Python
description: Projects the plugin onto OpenCode
---

Emits .opencode/ and opencode.json for the chosen provider from the plugin's agents, commands, skills and model routing. Hooks are not generated; enforcement comes from the OpenCode plugin and CI gates.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [adapters/opencode/generate.py](../../../../../../adapters/opencode/generate.py) | [adapters/deterministic.py](../../../../../../adapters/deterministic.py) | Reuses repointing and shipping | Python import |
