---
type: C4 System
title: Claude Code
status: stable
groma:
  id: claude-code
  technology: Anthropic CLI / IDE
---

The host runtime the plugin lives in: loads its commands, subagents, skills and hooks into a session.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [claude-code](claude-code.md) | [agent-plugin-content](../systems/wellforge/containers/agent-plugin-content/container.md) | Loads and runs | Plugin API |
