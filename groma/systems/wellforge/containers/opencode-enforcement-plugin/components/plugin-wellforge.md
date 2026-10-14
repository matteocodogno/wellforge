---
type: C4 Component
title: OpenCode guard plugin
status: stable
groma:
  id: plugin-wellforge
  parent: opencode-enforcement-plugin
  code:
    - scanner: javascript
      file: adapters/opencode/plugin/wellforge.js
      symbol: WellForge
  technology: JavaScript (OpenCode plugin)
description: Ports the Claude Code guard hooks to OpenCode
---

Denies dangerous shell commands and protected file edits, and treats spec edits as drift unless they only touch lifecycle frontmatter. Its lifecycle-field list is kept equal to forge-state's by a drift test.
