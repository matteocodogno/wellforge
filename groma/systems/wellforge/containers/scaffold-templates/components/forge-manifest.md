---
type: C4 Component
title: Forge manifest
status: draft
groma:
  id: forge-manifest
  parent: scaffold-templates
  group: Generated in every project
---

.forge/manifest.json records which template and version produced the project, plus the recorded answers. It is the upgrade contract: /wellforge:upgrade reads it to re-run `copier update`, and nothing may edit it by hand.
