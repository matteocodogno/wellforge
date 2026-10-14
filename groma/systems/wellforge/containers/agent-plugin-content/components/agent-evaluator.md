---
type: C4 Component
title: Agent evaluator
status: draft
groma:
  id: agent-evaluator
  parent: agent-plugin-content
  group: Agents
---

LM-judge for the WellForge spec-driven workflow. Scores a feature against the central rubric (gates/configs/eval-rubric.yml) — the non-deterministic half tests and CI gates cannot cover: spec fidelity, test quality, code conventions, trajectory. Produces a scored, evidence-cited eval-report.md verdict. Distinct from the quality-engineer (which runs deterministic gates and writes tests);
