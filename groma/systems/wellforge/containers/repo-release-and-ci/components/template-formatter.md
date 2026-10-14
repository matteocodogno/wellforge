---
type: C4 Component
title: Template formatter
status: draft
groma:
  id: template-formatter
  parent: repo-release-and-ci
  group: Self-verification
---

scripts/format-templates.sh runs each preset's own formatter over its rendered output and writes the result back into the template, so a fresh scaffold lints clean.
