---
type: regex
pattern: "001-checkout-flow[^\\n]*production[^\\n]*tasks[\\s\\S]*002-search-filters[^\\n]*mvp[^\\n]*tasks[\\s\\S]*003-order-history[^\\n]*production[^\\n]*(eval|in-progress)[^\\n]*3/3[\\s\\S]*004-cache-spike[^\\n]*spike[\\s\\S]*005-legacy-payments[^\\n]*(superseded|retired)[\\s\\S]*006-wishlists[^\\n]*draft"
target: last_message
---

Deterministic on purpose. This was an `llm` grader, and on 2026-10-06 the judge voted
FAIL FAIL FAIL on two answers and PASS PASS PASS on a third that differed from them by one
word in a column that is not a state ("approved" / "spec approved"). A claim a regex can
check should not be put to a vote.

Each feature's own row must carry its tier and phase, in order:

- `001-checkout-flow` — production, at tasks (approved plan, no task list yet)
- `002-search-filters` — mvp, at tasks
- `003-order-history` — production, at eval (or in-progress), 3/3 tasks
- `004-cache-spike` — a spike
- `005-legacy-payments` — superseded / retired
- `006-wishlists` — draft

It fails the degraded output too: with frontmatter unreadable every tier falls back to the
project default, so 002 reads `production` and 006 has no `draft`.
