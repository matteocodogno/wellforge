---
type: C4 Component
title: Hook trace-subagent
status: draft
groma:
  id: hook-trace-subagent
  parent: agent-plugin-content
  group: Hooks
---

SubagentStop hook. SubagentStop hook — best-effort token/latency telemetry for WellForge observability. Appends one JSON line per subagent completion to .forge/runs/.events.jsonl, which run-report.py joins with the semantic run traces the commands write. Deliberately defensive: only acts in a WellForge-managed project, captures usage ONLY when the harness exposes it in the transcript, and ALWAYS exits 0 (telemetry must never break a session).
