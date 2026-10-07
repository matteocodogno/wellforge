---
type: regex
pattern: "subagent_type\\W{1,8}wellforge:product-owner"
target: trace
---

The spec must have come from the product-owner AGENT. That is the whole point of this case:
an agent cannot see the conversation, so the only way the 14 months and the EUR-only rule
reach the spec is the ledger path it was handed.

Matched on the agent call's `subagent_type`, not with a `tool_used` grader, on purpose. The
tool that spawns an agent is listed as `Task` and invoked as `Agent` (measured: a
`tool_used: Task` grader reported "called 0x" on a run that had spawned the agent), so a
grader keyed on the tool's name would track the harness's naming rather than the behaviour.
The bare string `wellforge:product-owner` is not enough either — the orchestrate command's
own text contains it.
