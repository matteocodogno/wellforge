---
type: C4 System
title: Copier
status: stable
groma:
  id: copier
  technology: Python CLI
---

Template engine that renders the scaffold from copier.yml and re-templates it with copier update.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [copier](copier.md) | [scaffold-templates](../systems/wellforge/containers/scaffold-templates/container.md) | Renders and updates | copier copy / update |
