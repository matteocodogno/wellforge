---
type: C4 Component
title: Hook pre-bash-guard
status: draft
groma:
  id: hook-pre-bash-guard
  parent: agent-plugin-content
  group: Hooks
---

PreToolUse hook on Bash. Block deleting /, /*, ~, ~/, ~/*, bare * — NOT legitimate paths like /tmp/foo (the original unanchored "rm -rf /" matched every absolute-path deletion).
