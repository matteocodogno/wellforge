---
type: C4 Component
title: Agent owasp-reviewer
status: draft
groma:
  id: agent-owasp-reviewer
  parent: agent-plugin-content
  group: Agents
---

Security specialist that runs an OWASP Top 10 review on changed code before merge. Invoke when a feature is ready for review, a PR is being prepared, or when working on endpoints that handle sensitive data (authentication, file upload, external APIs, PII, financial transactions). Particularly important for projects with regulated data (public sector, regulated industries).
