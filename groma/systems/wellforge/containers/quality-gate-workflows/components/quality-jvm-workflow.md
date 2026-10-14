---
type: C4 Component
title: quality-jvm workflow
status: draft
groma:
  id: quality-jvm-workflow
  parent: quality-gate-workflows
  group: Stack gates
---

Reusable gate for Spring Boot Kotlin Maven modules: ktlint, tests with JaCoCo at 80% lines enforced by check-jacoco.py, osv-scanner for known vulnerabilities and semgrep SAST.
