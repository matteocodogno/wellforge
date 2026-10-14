---
type: C4 Component
title: Hook pre-file-guard
status: draft
groma:
  id: hook-pre-file-guard
  parent: agent-plugin-content
  group: Hooks
---

PreToolUse hook on Read|Write|Edit|MultiEdit|NotebookEdit|Grep. PreToolUse guard for the FILE tools (Read/Write/Edit/MultiEdit/NotebookEdit). WHY THIS EXISTS SEPARATELY FROM pre-bash-guard.sh The bash guard inspects COMMAND TEXT, so it only ever covered Bash. Write and Edit could create a dotenv or secrets file freely and Read could read one — the protection was real for `cat` and absent for the tool an agent actually reaches for.
