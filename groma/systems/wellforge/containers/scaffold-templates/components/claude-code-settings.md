---
type: C4 Component
title: Claude Code settings
status: draft
groma:
  id: claude-code-settings
  parent: scaffold-templates
  group: Generated in every project
---

.claude/settings.json pre-enables the wellforge plugin from the marketplace and allow-lists the commands the workflow runs (mise, plus mvn for the Spring preset and pnpm for the others; the Pulumi preset adds read-only pulumi preview, config and stack), so a fresh clone is ready for /wellforge commands.
