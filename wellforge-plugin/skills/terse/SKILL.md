---
name: terse
description: >
  WellForge terse mode — the token-efficient conversational output cue, orthogonal to rigor
  tier. Use whenever running /wellforge:spike (terse by default), when /wellforge:orchestrate
  or /wellforge:implement is given --terse/--no-terse, when the main-loop /wellforge:terse toggle is
  invoked, or when deciding whether a piece of output should be compressed. Authoritative
  reference for the terse cue directive text, the byte-identical invariant, which artifacts
  are exempt, the activation matrix, and /wellforge:terse session semantics.
---

# Terse mode — token-efficient conversational output

Conversational output, orchestration/handoff narration, and status recaps are pure overhead:
they cost output tokens without adding substance. **Terse mode** is a plain-text directive,
modelled one-to-one on the existing effort cue (`skills/rigor-tiers/SKILL.md`), that
dispatching commands prepend to each agent's task prompt — or that the spike main loop
self-applies. It is **orthogonal to rigor tier**: any tier may run terse, and terse never
changes which gates, agents, or approvals run.

## Terse cue

The injected directive (verbatim — do not paraphrase when prepending it to a task prompt):

```
TERSE MODE — output tokens are the cost. Drop filler, preamble, and restating the
question. Prefer fragments over sentences. Substance only.
INVARIANT: never alter code blocks, shell commands, file paths, identifiers, or error
messages — reproduce them byte-for-byte.
EXEMPT: when writing spec.md / plan.md / tasks.md / design.md / an ADR / eval*.md, ignore
terse mode entirely and follow the full format contract.
```

Prepend this cue next to the effort cue (if the rigor-tiers skill is also in play) whenever
terse is resolved on. For the spike main loop, the loop applies the cue to itself — there is
no subagent task prompt to prepend to.

## Byte-identical invariant

**Terseness MUST NOT alter code blocks, shell commands, file paths, identifiers, or error
messages.** These are reproduced byte-for-byte identical to their non-terse form.

This is a **correctness and safety invariant, not a style preference**. Terse compression
targets prose — filler, preamble, restated context, narration — never the literal payload a
human or a downstream tool will copy, paste, or execute. A terse transform that silently
edited a shell command or a file path would not just read worse, it would cause real damage
(wrong command run, wrong file touched, a masked error message). Treat any drift between a
terse rendering and the canonical content of a code span, command, path, identifier, or
error message as a bug to fix, not a tradeoff to accept.

## Artifact exemption

Terse mode **NEVER applies** when writing any of the spec-driven or governance artifacts:

- `spec.md`
- `plan.md`
- `tasks.md`
- `design.md`
- an ADR
- `eval.md` / `eval-report.md`

These artifacts follow their **full format contract** regardless of whether terse mode is
active for the surrounding conversation. The commands that write them (`spec`, `plan`,
`design`, `tasks`, `adr-writer`, `eval`) load the spec-driven skill's format mandate, which
takes precedence — terse is a conversational-output cue, not a document-generation mode, and
must not leak into a contracted artifact. This is backstopped by the existing drift/format
checks and by the evaluator, which would surface any fidelity regression in these files as a
score drop (US-3, AC-3.1/AC-3.2).

## Activation matrix

Terse is resolved as a boolean per run/session, independent of rigor tier:

| Surface | Activation | Notes |
|---|---|---|
| `/wellforge:spike` | **ON by default** | main loop self-applies the cue; `--no-terse` opts out |
| `/wellforge:orchestrate` | `--terse` flag (**OFF by default**) | parsed/stripped in Step 0 — Resolve, alongside `--mode`; prepended per dispatched agent |
| `/wellforge:implement` | `--terse` flag (**OFF by default**) | same Step 0 handling as orchestrate |
| main loop | **`/wellforge:terse` toggle** command | session-level directive, independent of any command flag |
| `mvp` / `production` (no flag) | **OFF** | terse is never implied by tier alone outside spike |

`--terse` / `--no-terse` is a separate axis from `--mode`/rigor tier — any tier can be run
terse; spike merely defaults it on. A `--no-terse` flag on `/wellforge:spike` restores normal
verbosity for that run.

## /wellforge:terse semantics

`/wellforge:terse` is a main-loop session toggle, not a one-shot flag — it has no arguments and flips
state on each invocation:

```
/wellforge:terse            → "Terse mode: ON until you run /wellforge:terse again."
/wellforge:terse  (again)   → "Terse mode: OFF."
```

Because the plugin has no persistent main-loop state store, "session state" is realized the
WellForge way: as a stated directive the command emits, which governs subsequent
conversational output for the rest of the session (or until toggled off again) — the same
pattern the effort cue uses, just re-triggerable. The artifact exemption above still applies
in full while the toggle is ON: writing a spec-driven artifact mid-session ignores the active
terse state.
