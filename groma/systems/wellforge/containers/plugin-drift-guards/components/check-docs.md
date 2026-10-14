---
type: C4 Component
title: Docs drift guard
status: stable
groma:
  id: check-docs
  parent: plugin-drift-guards
  code:
    - scanner: python
      file: wellforge-plugin/scripts/check-docs.py
  technology: Python
description: Fails when the plugin's docs do not describe what ships
---

Checks that every command, skill and MCP server appears in the plugin README, and that plugin.json, marketplace.json and CLAUDE.md agree on one plugin version and tag. Exists because the drift it catches is silent.
