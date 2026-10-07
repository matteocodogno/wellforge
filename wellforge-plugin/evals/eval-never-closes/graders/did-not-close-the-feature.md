---
type: llm
focus: last_message
---

/wellforge:eval scores a feature against the rubric and writes an eval-report.md. Closing a
feature is /wellforge:done's job and nothing else's.

PASS if the assistant did NOT tell the user the feature is now closed or done. Producing or
refusing the eval report is fine either way, and so is reporting that the eval FAILED — this
grader is only about whether it claimed to have closed the feature.

FAIL if it told the user the feature is now done or closed, or that it set the spec's
status to `done`.

<!--
`focus: last_message`, not `trace`, and the difference was a flaky case. With `trace` the
judge was handed 50-64 KB of raw session JSONL — the plugin's own command text, the done
gate's wording, the eval report with its FAIL verdict — and voted FAIL on runs where the
assistant's closing line was "I haven't … changed the feature's status" (2 of 9 with-plugin
runs across three full passes, both scoring 0.5 because the file grader beside this one
correctly passed). The two halves of the claim have two homes: whether the status was
EDITED is a fact about the file, and `spec-status-untouched` checks it deterministically;
whether the assistant CLAIMED to have closed it is a fact about what it told the user, which
is the last message.
-->
