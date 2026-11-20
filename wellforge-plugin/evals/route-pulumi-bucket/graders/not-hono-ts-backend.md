---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?hono-ts-backend\\?"'
match: not_contains
target: trace
---

pulumi-gcp-ts says it is infrastructure, not an application backend; this repo has both, so the clause is what decides.
