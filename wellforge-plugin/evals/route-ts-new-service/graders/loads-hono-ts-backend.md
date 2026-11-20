---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?hono-ts-backend\\?"'
target: trace
---

"scaffold a service" in a TypeScript monorepo. The `hono-ts-backend` skill must be invoked. Matched on the Skill call's input, not on the bare
name, which the session's skill listing and other skills' bodies also contain.
