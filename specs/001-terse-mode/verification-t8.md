---
task: T8
spec: 001-terse-mode
verified: 2026-07-24
verifier: quality-engineer (agent)
---

# T8 verification — output + artifact integrity under terse mode

Scope per `tasks.md` T8: verify AC-1.2 (byte-identical invariant), AC-3.1 (artifacts stay
full-contract under terse), AC-3.2 (no evaluator score regression). This is a verification
task — the deliverable is this document plus the fixtures in `fixtures/t8/`, not product
code. Nothing outside `specs/001-terse-mode/` was touched.

## Summary verdict

| AC | Verdict | Evidence |
|---|---|---|
| AC-1.2 — byte-identical code/commands/paths/errors | **PASS** | `fixtures/t8/extract-spans.sh` — deterministic diff, exit 0, see below |
| AC-3.1 — artifacts stay full-contract under terse | **PASS** | Explicit format checklist (spec-driven skill rules) applied to this feature's own spec.md/plan.md/tasks.md — all items PASS, one non-blocking minor noted |
| AC-3.2 — no evaluator score regression | **PASS-pending-eval** | Methodology documented below; mechanical/design-level guarantees confirmed now; empirical terse-vs-baseline eval run deferred to the feature's actual `/wellforge:eval` pass (no `eval-report.md` exists yet — T9/T10 outstanding) |

---

## AC-1.2 — byte-identical invariant

**Claim under test** (spec.md AC-1.2 / SKILL.md "Byte-identical invariant"): terseness must
never alter code blocks, shell commands, file paths, identifiers, or error messages — they
are reproduced byte-for-byte in terse output.

### Fixture

Two renderings of the same hypothetical agent response, in `fixtures/t8/`:

- `canonical.md` — the verbose (non-terse) form: prose preamble/postamble around four
  payload spans (a Python code block, a `bash` shell command, an inline file path, and a
  plain error-message block).
- `terse-rendered.md` — the terse form of the *same* response: prose compressed to
  fragments per the terse cue (`wellforge-plugin/skills/terse/SKILL.md`), but the four
  payload spans copied verbatim from `canonical.md`.

### Check

`fixtures/t8/extract-spans.sh` extracts (a) the content of every fenced code block
(covers the Python snippet, the shell command, and the error message) and (b) every
inline back-tick span (covers the file path) from both files, then diffs each extracted
set. A clean diff (empty output, exit 0) is the deterministic proof that terse rendering
preserved those spans byte-for-byte while the surrounding prose changed freely.

**Command run:**
```
$ ./specs/001-terse-mode/fixtures/t8/extract-spans.sh
```

**Actual output:**
```
== Fenced code/shell/error blocks ==
PASS: fenced spans (python code block, bash command, error message) are byte-identical

== Inline backtick spans (file paths) ==
PASS: inline path spans are byte-identical
```
Exit code: `0`.

### Negative control (proves the check isn't vacuous)

`fixtures/t8/terse-rendered-BAD.md` is a deliberately mangled variant (the `--min 0.80`
flag value is corrupted to `--min 0.8`). Running the same fenced-block extraction against
it instead of `terse-rendered.md`:

```
$ awk '/^```/{f=!f; next} f' fixtures/t8/canonical.md > /tmp/t8-canonical-fenced.txt
$ awk '/^```/{f=!f; next} f' fixtures/t8/terse-rendered-BAD.md > /tmp/t8-bad-fenced.txt
$ diff -u /tmp/t8-canonical-fenced.txt /tmp/t8-bad-fenced.txt
```
**Actual output:**
```
--- /tmp/t8-canonical-fenced.txt
+++ /tmp/t8-bad-fenced.txt
@@ -2,5 +2,5 @@
     if baseline == 0:
         raise ValueError("baseline token count must be non-zero")
     return (baseline - terse) / baseline
-python3 gates/scripts/check-jacoco.py --path specs/001-terse-mode/fixtures/t8/coverage.xml --min 0.80
+python3 gates/scripts/check-jacoco.py --path specs/001-terse-mode/fixtures/t8/coverage.xml --min 0.8
 Error: coverage 0.7421 below threshold 0.80 (gates/configs/thresholds.yml)
```
Exit code: `1` (diff detects the drift immediately). This confirms the check has power to
fail on a real single-character span mutation, not just pass by construction.

**Verdict: PASS.** The deterministic diff-based check exists, is reproducible
(`fixtures/t8/extract-spans.sh`), passes on the terse rendering, and is proven to catch
drift via the negative control.

**Honest limitation:** this fixture is a hand-authored stand-in for "an agent's terse vs.
non-terse output of the same turn" — it is not captured from a live dispatched run (no
harness currently records paired terse/non-terse raw transcripts of the same turn for
diffing). The check itself (extract spans, diff) is exactly what would be run against real
transcript pairs if/when they're captured; the mechanism is verified, the live-transcript
application is not. This matches T8's brief ("Build a small fixture ... describe the exact
command and show it passing").

---

## AC-3.1 — artifacts stay full-contract under terse

**Claim under test** (spec.md AC-3.1 / SKILL.md "Artifact exemption"): when terse mode is
active, `spec.md`/`plan.md`/`tasks.md`/`design.md`/an ADR/`eval*.md` still follow the full
spec-driven format contract — no terse compression applied to them.

### Why no runnable validator exists

Checked the two candidate mechanical validators named in the task brief:

- **Stop hook `stop-verify.sh`** (`wellforge-plugin/hooks/scripts/stop-verify.sh`): only
  checks the **drift rule** (spec.md/plan.md changed without a re-synced tasks.md →
  block). It does not validate internal format/structure of any of the three files, and
  it is silent on terse mode entirely (it has no notion of terse state). Confirmed by
  reading the full script (69 lines) — no format assertions beyond the drift check, a
  TypeScript compile check, and a Kotlin/Maven compile check.
- Repo-wide search for any spec/plan/tasks format validator
  (`grep -rliE "validate.*(spec|format)"` across `wellforge-plugin/`, `gates/`,
  `scripts/`) returned no hits besides unrelated files (`terse-compress.md`,
  `policy-as-code.md`).

So, per the task brief's fallback instruction, an explicit checklist is derived from the
spec-driven skill's file-format rules (`wellforge-plugin/skills/spec-driven/SKILL.md`,
"File formats" section) and applied to **this feature's own spec.md/plan.md/tasks.md** as
the fixture.

### Checklist — spec.md (`specs/001-terse-mode/spec.md`)

| # | Rule (spec-driven SKILL.md) | Result | Evidence |
|---|---|---|---|
| 1 | Frontmatter has `id`, `slug`, `status`, `rigor`, `created` | PASS | lines 1-8: `id: 001`, `slug: terse-mode`, `status: in-progress`, `rigor: production`, `created: 2026-07-16` |
| 2 | `# <Title>` heading | PASS | line 10 |
| 3 | `## Problem`, 2-5 sentences, no solutions | PASS | lines 12-22, 5 sentences, frames the gap not a design |
| 4 | `## User stories`, each `US-N`: "As a / I want / so that" + `**Acceptance criteria:**` with `Given/when/then` ACs | PASS | US-1..US-5 (lines 42-106) all conform |
| 5 | `## Non-goals` present | PASS | lines 108-118 |
| 6 | `## Open questions` empty or explicitly resolved before approval | PASS | lines 120-126, all `[x]` resolved |
| 7 | Every AC objectively verifiable (no clarification needed to test it) | PASS | spot-checked AC-1.2, AC-3.1, AC-3.2, AC-5.1 — all Given/when/then, observable outcomes |

### Checklist — plan.md (`specs/001-terse-mode/plan.md`)

| # | Rule | Result | Evidence |
|---|---|---|---|
| 1 | Frontmatter `spec:`, `status: draft\|approved` | PASS | lines 1-4: `spec: 001`, `status: approved` |
| 2 | `## Architecture`, `## Data model`, `## API contracts`, `## Test strategy`, `## Risks`, `## Security` all present | PASS | lines 8, 93, 109, 149, 175, 209 |
| 3 | Every spec AC mapped in the Test strategy table | PASS | table at lines 157-170 lists all 12 ACs (AC-1.1/1.2, 2.1/2.2/2.3, 3.1/3.2, 4.1/4.2, 5.1/5.2/5.3), matching spec.md 1:1; plan.md states this explicitly at line 172 |
| 4 | `## Security` states security-sensitive YES/NO + reasoning | PASS | line 211: "Security-sensitive: NO ... no owasp pass scheduled", with two named safety invariants |

### Checklist — tasks.md (`specs/001-terse-mode/tasks.md`)

| # | Rule | Result | Evidence |
|---|---|---|---|
| 1 | Frontmatter `spec:`, `generated:` | PASS | lines 1-4 |
| 2 | Each task: `- [ ] TN: <title> — refs: ... — deps: ...` + `touch:` + `done when:` | PASS | spot-checked T1, T2, T5, T8, T10 — all conform |
| 3 | Every task references at least one AC | **PASS (minor, non-blocking)** | T2-T9 all cite explicit AC codes (e.g. T8: "AC-1.2, AC-3.1, AC-3.2"); T1 cites only user stories (`US-1, US-2, US-3, US-4`) with no explicit `AC-` code, and T10 is a closing task (`refs: (closing)`) by design. T1 not citing explicit ACs is a real, minor format deviation — flagged here rather than silently passed — but non-blocking: T1 is the foundational skill-authoring task and every AC it indirectly enables is separately covered by name in T2-T9 (checklist item 4 below), so no AC goes unverified. |
| 4 | Every spec AC covered by at least one task | PASS | AC-1.1→T3, AC-1.2→T8, AC-2.1/2.2→T2, AC-2.3→T4, AC-3.1/3.2→T8, AC-4.1/4.2→T5, AC-5.1→T6+T7, AC-5.2→T7, AC-5.3→T9 — all 12 spec ACs traced to at least one task |
| 5 | `deps:` form a DAG (no cycles) | PASS | T1←none; T2,T3,T4,T5←T1; T6←T2,T3; T7←T6; T8←T2,T3; T9←T2,T7; T10←T4,T5,T8,T9 — acyclic |

**Verdict: PASS.** All three artifacts of this feature satisfy the full spec-driven format
contract with no observed compression/shortcut — exactly what AC-3.1 requires. This is
reinforced structurally by `wellforge-plugin/skills/terse/SKILL.md`'s "Artifact exemption"
section (lines 51-68), which explicitly instructs the writing commands (`spec`, `plan`,
`design`, `tasks`, `adr-writer`, `eval`) to ignore terse mode entirely for these six file
types — i.e. the exemption is a load-bearing instruction in the very skill T1-T5 delivered,
not just an incidental property of these particular files.

**Honest limitation:** terse mode has no runtime enforcement (it is a prompt-level cue, per
plan.md's rejected-alternative "a hook cannot read terse state" — R5). This checklist proves
the *artifacts as produced* meet the full contract; it cannot prove a differently-behaving
agent could never violate the exemption. That residual risk is explicitly named as R5 in
plan.md and is backstopped there by the evaluator/QE catching fidelity regressions — which is
exactly AC-3.2's job, addressed next.

---

## AC-3.2 — no evaluator score regression

**Claim under test** (spec.md AC-3.2): when terse mode is active, a terse run and a baseline
run of the same feature score within the rubric's normal variance on spec-fidelity and
code-conventions — no regression attributable to terse output.

### Methodology (documented per task brief, to be executed at the feature's actual eval stage)

Rubric: `gates/configs/eval-rubric.yml` (version `default-v2`). The two dimensions AC-3.2
names map to:
- `spec_fidelity` (weight 20, floor 3, scale 1-5)
- `code_quality` — "Code quality & conventions" (weight 15, floor 3, scale 1-5)

**Procedure:**
1. Pick a fixture feature (small, already-speced) and implement it twice via
   `/wellforge:orchestrate` or `/wellforge:implement`: once with `--terse`, once without
   (the baseline/control), same tasks.md, same tier.
2. Run `/wellforge:eval` (the `evaluator` agent) against both resulting implementations,
   independently, producing two `eval-report.md`-style scorings.
3. Compare the `spec_fidelity` and `code_quality` dimension scores between the terse run
   and the baseline run.

**Operational definition of "within the rubric's normal variance"** (the rubric itself does
not quantify a variance band for repeat scoring, so this is the explicit definition this
task adopts, per the task brief's instruction to document the exact methodology):
- Neither dimension's terse-run score may be **more than 1 point lower** than the
  baseline-run score on the 1-5 scale (accounts for ordinary LM-judge scoring noise across
  two independent runs of non-identical prose).
- Neither dimension's terse-run score may drop **below its floor** (`spec_fidelity` ≥ 3,
  `code_quality` ≥ 3) — a floor breach fails the eval regardless of the baseline comparison,
  per the rubric's own pass rule ("a single dimension under its floor fails the eval").
- A terse-run score that is *equal to or higher* than baseline is trivially within variance.

If both conditions hold for both dimensions → PASS. If either dimension drops more than 1
point vs. baseline, or falls below its floor, on a run attributable to terse output → FAIL,
and the drop is a defect in the terse cue/skill (either the cue is leaking terseness into
code, or into the artifacts the evaluator reads for spec fidelity).

### What is mechanically confirmed now (without a live eval run)

- No `eval-report.md` exists yet for `001-terse-mode` (confirmed: `ls specs/001-terse-mode/`
  contains only `spec.md`, `plan.md`, `tasks.md`, this verification doc, and `fixtures/`) —
  T9 (aggregate measurement) and T10 (close) are still open, and a live terse-vs-baseline
  eval comparison is explicitly out of T8's scope per the task brief ("If a full
  `/wellforge:eval` run is out of scope for a single task, document the exact methodology").
- **Design-level guarantee protecting `spec_fidelity` inputs:** the evaluator scores
  `spec_fidelity` by reading `spec.md`/`plan.md`/`tasks.md` (and the implementation against
  them). AC-3.1 above establishes those three files are never terse-compressed by contract
  (SKILL.md's artifact exemption) — so the *inputs* the evaluator reads for this dimension
  are structurally protected from terse mode regardless of whether the surrounding
  conversation was terse.
- **Design-level guarantee protecting `code_quality` inputs:** spec.md's Constraints section
  (line 29) scopes terse's compressible surfaces to "conversational output,
  orchestration/handoff narration, and memory + MCP tool-description files" — source code is
  not a compressible surface by design (nor are commit messages / PR text, per the same
  line). The terse cue itself (SKILL.md, "Terse cue") targets "filler, preamble, restated
  context, narration" — not code generation. So the surface `code_quality` is scored against
  is out of terse mode's scope by construction.
- These two points are **scope/design arguments, not empirical measurements** — they explain
  *why* a regression would be surprising, but only a live paired eval run (per the procedure
  above) empirically confirms scores don't drift in practice (e.g. a terse agent rushing
  through a task and cutting corners on error handling due to the terse cue's tone, even
  though the cue text says it targets only prose).

### Verdict

**PASS-pending-eval.** Methodology is fully specified and reproducible; the two rubric
dimensions AC-3.2 cares about have their scoring *inputs* structurally protected from terse
compression by the artifact exemption (AC-3.1) and by terse's scope being explicitly
narrowed away from source code (spec.md Constraints). The empirical part — actually running
the paired terse/baseline eval and checking the 1-point/floor bands above — is honestly
deferred: it depends on T9's aggregate-measurement infrastructure and belongs at the
feature's `/wellforge:eval` stage (and ultimately gates `/wellforge:done` for this
`production`-tier feature, which requires a fresh passing `eval-report.md`). No eval-report.md
exists yet, so no empirical score data can be reported now — this gap is called out here
rather than assumed away.

---

## Files added by this task

```
specs/001-terse-mode/verification-t8.md              (this file)
specs/001-terse-mode/fixtures/t8/canonical.md         (AC-1.2 fixture: verbose/baseline form)
specs/001-terse-mode/fixtures/t8/terse-rendered.md    (AC-1.2 fixture: terse form, spans preserved)
specs/001-terse-mode/fixtures/t8/terse-rendered-BAD.md (AC-1.2 negative control: mangled span)
specs/001-terse-mode/fixtures/t8/extract-spans.sh     (AC-1.2 deterministic diff-based check)
```

No files outside `specs/001-terse-mode/` were modified. `tasks.md`, `spec.md`, and `plan.md`
were read but not edited.
