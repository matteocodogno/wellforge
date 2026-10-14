---
type: C4 Component
title: Copier entry point
status: draft
groma:
  id: copier-entry-point
  parent: scaffold-templates
  group: Template engine
---

The single root copier.yml that serves every preset: a `preset` question picks the stack and a templated `_subdirectory` selects its file tree. It must be the repo root, versioned by repo-wide vX.Y.Z tags, because that is what makes `copier update` work. Holds the common questions (name, slug, CI, rigor tier, gates repo and ref, heartbeat) and the migration hooks run when an upgrade crosses a version.
