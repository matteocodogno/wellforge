---
type: C4 Container
title: Plugin drift guards
status: stable
groma:
  id: plugin-drift-guards
  parent: wellforge
---

Self-checks that fail the repo's CI when the plugin's docs, model routing or session-injection budget drift from what ships. Run by mise run check, never by users of the plugin.
