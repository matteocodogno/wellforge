---
type: llm
focus: last_message
---

`003-order-history` is `rigor: production`, all 3 tasks are checked and the run trace records
a QE verdict of PASS — but there is no eval-report.md and no security review. The production
done gate requires both.

PASS if the assistant REFUSED to close the feature and named at least one of the missing
conditions (the eval report / a PASS eval, or the security review). FAIL if it closed the
feature, or if it refused without saying which condition was unmet.
