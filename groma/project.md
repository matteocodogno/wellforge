---
type: Groma Project
title: WellForge
groma:
  profile: architecture
description: 'Reproducible, AI-assisted project setup: a Claude Code plugin, a Copier template and central quality gates'
---

WellForge turns hours of repetitive AI-infrastructure setup into minutes and keeps the result upgradeable. Three layers: a Claude Code plugin (spec-driven workflow, subagents, orchestrator), a Copier monorepo template for scaffolding and `copier update`, and reusable CI gates with central thresholds.

**Scope of this map.** Solid elements are what a scanner can read: the Python behind the plugin's scripts, the adapters and the gates. Everything else is a dashed draft container, because no scanner reads Markdown, shell, workflow YAML or templated text: the plugin's commands, agents, skills, hooks, config and evals; the template engine and its three presets; the reusable quality-gate workflows with their configs and git hooks; the CLI and fleet scripts; and the repo's own release and CI. Those are listed one by one, described from their own files, and carry no relationships between them. Not shown: the presentation site (site/) and the docs.
