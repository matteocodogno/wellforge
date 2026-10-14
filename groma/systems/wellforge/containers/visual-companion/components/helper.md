---
type: C4 Component
title: Companion page helper
status: stable
groma:
  id: helper
  parent: visual-companion
  code:
    - scanner: javascript
      file: wellforge-plugin/skills/visual-companion/scripts/helper.js
  technology: JavaScript (browser)
description: Reports clicks and reconnects from the browser
---

Runs inside each served mockup: sends the user's selections to the server over the WebSocket, reconnects with capped exponential backoff and shows a paused overlay when the session is gone.
