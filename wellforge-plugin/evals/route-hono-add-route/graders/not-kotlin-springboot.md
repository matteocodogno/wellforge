---
type: regex
pattern: '\\?"skill\\?"\s*:\s*\\?"(wellforge:)?kotlin-springboot\\?"'
match: not_contains
target: trace
---

A Hono repo must not pull in the Spring skill.
