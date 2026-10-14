---
type: C4 Component
title: Copilot generator
status: stable
groma:
  id: copilot-generate
  parent: adapter-generators
  code:
    - scanner: python
      file: adapters/copilot/generate.py
  technology: Python
description: Projects the plugin onto GitHub Copilot
---

Maps commands to .github/prompts, agents to chat modes and stack skills to instructions files, with models from the routing and tier config, and a .vscode/mcp.json.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [adapters/copilot/generate.py](../../../../../../adapters/copilot/generate.py) | [adapters/deterministic.py](../../../../../../adapters/deterministic.py) | Reuses repointing and shipping | Python import |
