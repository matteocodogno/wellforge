---
type: C4 Container
title: Adapter generators
status: stable
groma:
  id: adapter-generators
  parent: wellforge
---

Build-time generators that project the Claude Code plugin onto GitHub Copilot and OpenCode, ship the deterministic layer into their output, and smoke-test it. The Claude Code plugin stays the source of truth.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [adapter-generators](container.md) | [github-copilot](../../../../externals/github-copilot.md) | Generates files for | File output |
| [adapter-generators](container.md) | [opencode](../../../../externals/opencode.md) | Generates files for | File output |
