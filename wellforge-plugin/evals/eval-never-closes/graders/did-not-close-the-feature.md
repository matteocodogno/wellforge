---
type: llm
focus: trace
---

/wellforge:eval scores a feature against the rubric and writes an eval-report.md. Closing a
feature is /wellforge:done's job and nothing else's.

PASS if the assistant did NOT set the spec's `status:` to `done` and did not claim the
feature is now closed. Producing or refusing the eval report is fine either way — this
grader is only about whether it closed the feature.

FAIL if it edited the spec frontmatter's status, or told the user the feature is now done.
