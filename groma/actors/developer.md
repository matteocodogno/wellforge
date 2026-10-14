---
type: C4 Actor
title: Developer
status: stable
groma:
  id: developer
---

A person on a product team who sets up and builds a project with AI assistance. Runs the /wellforge commands inside Claude Code, approves each spec and plan, and merges the result.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [developer](developer.md) | [agent-plugin-content](../systems/wellforge/containers/agent-plugin-content/container.md) | Drives the workflow | Slash commands |
| [developer](developer.md) | [scaffold-templates](../systems/wellforge/containers/scaffold-templates/container.md) | Scaffolds projects from | /wellforge:new |
| [developer](developer.md) | [gate-scripts](../systems/wellforge/containers/gate-scripts/container.md) | Commits through | git hooks |
| [developer](developer.md) | [visual-companion](../systems/wellforge/containers/visual-companion/container.md) | Clicks mockups in | Browser, WebSocket |
| [developer](developer.md) | [cli-and-fleet-tooling](../systems/wellforge/containers/cli-and-fleet-tooling/container.md) | Sets up with | Homebrew, shell |
