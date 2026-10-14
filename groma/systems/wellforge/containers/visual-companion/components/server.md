---
type: C4 Component
title: Companion server
status: stable
groma:
  id: server
  parent: visual-companion
  code:
    - scanner: javascript
      file: wellforge-plugin/skills/visual-companion/scripts/server.cjs
  technology: Node.js
description: Serves mockups and relays the user's clicks
---

An HTTP server with an RFC 6455 WebSocket implementation that serves the screens the designer writes and appends each browser event to an events file the session reads. Injects helper.js into every served page.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [wellforge-plugin/skills/visual-companion/scripts/server.cjs](../../../../../../wellforge-plugin/skills/visual-companion/scripts/server.cjs) | [wellforge-plugin/skills/visual-companion/scripts/helper.js](../../../../../../wellforge-plugin/skills/visual-companion/scripts/helper.js) | Injects into every page | fs.readFileSync |
