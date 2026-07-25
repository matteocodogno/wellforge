---
spec: 001
status: approved
---

# Plan: Terse mode — token-efficient conversational output

## Architecture

Terse mode is an **orthogonal behavioral axis**, not a rigor tier. It is modelled
one-to-one on the existing **effort cue** (`skills/rigor-tiers/SKILL.md:47-70`): a
plain-text directive, derived from the resolved mode, that commands prepend to each
dispatched agent's task prompt (and that the spike main loop self-applies). Tool-portable,
zero new config — the same precedent that already ships.

**Components**

1. **`skills/terse/SKILL.md` (new)** — the authoritative definition, mirroring the
   `rigor-tiers` skill structure. It defines:
   - The **terse cue** (the directive text): drop filler, prefer fragments, no preamble/
     postamble — *substance only*.
   - The **byte-identical invariant**: terseness MUST NOT alter code blocks, shell
     commands, file paths, identifiers, or error messages — those are reproduced verbatim.
     This is a correctness/safety invariant, not a style preference.
   - The **artifact-protection list** (US-3): terse mode NEVER applies when writing a
     spec-driven artifact (`spec.md`, `plan.md`, `tasks.md`, `design.md`), an ADR, `eval.md`,
     or `eval-report.md`. These follow their full format contract regardless of terse state.
     (Backstopped by the drift/format checks and the evaluator — see Test strategy AC-3.)
   - The **activation matrix** (below) and the `/wellforge:terse` session semantics.
   Referenced by name ("Load the **terse** skill") from the commands, exactly like the
   `rigor-tiers` and `observability` skills are today.

2. **Activation — three entry points, one directive.** Terse is resolved as a boolean,
   orthogonal to tier:

   | Surface | Activation | Injection point (mirrors effort cue) |
   |---|---|---|
   | `/wellforge:spike` | **ON by default** | spike main loop self-applies (`spike.md:13-22`) |
   | `/wellforge:orchestrate` | `--terse` flag (off by default) | prepend terse cue per-agent (`orchestrate.md:45-47`) |
   | `/wellforge:implement` | `--terse` flag (off by default) | prepend terse cue per-agent (`implement.md:54-57`) |
   | main loop | **`/wellforge:terse` toggle** command (new) | session-level directive until toggled off |
   | mvp / production (no flag) | OFF | — |

   `--terse` is parsed in the existing **"Step 0 — Resolve"** prose of orchestrate/implement
   (same place `--mode` is parsed and stripped): read the token out of `$ARGUMENTS`, set the
   terse boolean, strip the token before using the rest as the goal. It is a **separate axis
   from `--mode`** — any tier may be flagged terse; spike defaults it on but `--no-terse`
   turns it off.

3. **`/wellforge:terse` toggle (new command, `commands/terse.md`)** — a main-loop session toggle
   (AC-2.3). Running `/wellforge:terse` turns terse on; running it again turns it off. Because the
   plugin has no persistent main-loop state store, "session state" is realized the WellForge
   way — as a stated directive the command emits ("Terse mode: ON — I will keep responses
   terse until you run `/wellforge:terse` again"), which governs subsequent output for the session.
   No config file, consistent with the effort-cue precedent.

4. **One-way memory / description compression (new command, `commands/terse-compress.md`,
   US-4)** — `/wellforge:terse-compress <path>` rewrites a target file to a shorter form
   in place. Scope of valid targets: **WellForge-authored files we own** — `memory/*.md`,
   `AGENTS.md`, and the `description:` frontmatter of our own skills/commands/agents.
   It is **one-way** (irreversible; no decompress ships). Safety for AC-4.1's no-fact-loss
   property is a **two-pass fact-preservation check** (see Risks): the command extracts the
   atomic fact set from the original, produces the compressed version, re-extracts facts
   from it, and refuses to overwrite unless every original fact is still recoverable; the
   diff is shown for confirmation before the in-place write. See Risk R2 on why third-party
   MCP tool descriptions are **out of reach** and how the spec's "tool-description" clause is
   interpreted.

5. **Measurement (US-5)** — reuses the observability run-trace. Additive schema change:
   a `terse: boolean` field on the `wellforge-run/v1` trace so consumers can identify a
   terse run and pair it with its control. `scripts/run-report.py` gains a
   terse-vs-control comparison (join a terse run to a non-terse control run of the same
   feature by output-token totals from `.events.jsonl`), and `/wellforge:status` surfaces
   the saved-token readout beside its existing (honestly-hedged) cost line. **Critical
   limitation, see Risk R1:** the token layer only sees *subagent* output, not the main
   loop — so the ≥40% measurement is only mechanically verifiable on the **agent-dispatched
   surfaces** (`orchestrate`/`implement --terse`). Spike and `/wellforge:terse` savings are real but
   observable only via `/usage`.

**Rejected alternatives**
- *Vendor caveman / global installer* — rejected in the spec (non-reproducible, namespace
  collision). Confirmed: no shared flag parser or middleware layer exists to hang it on.
- *Make terse a new rigor tier* — rejected: tiers tune pipeline depth/gates/models; terse is
  orthogonal (any tier can be terse). Adding a tier would wrongly couple verbosity to
  ceremony. The effort-cue pattern (a cross-cutting cue, not a tier) is the right analog.
- *A config field / runtime engine to flip terse* — rejected: everything behavioral in
  WellForge is prompt text; `config/*.yml` is consumed by prose or `run-report.py`, never a
  runtime engine. Terse adds zero new config, matching the effort cue.
- *Enforce artifact protection with a hook* — rejected: hooks are file/tool-keyed and
  tier-blind; they cannot read terse state. Protection is a skill rule, backstopped by the
  existing format/drift checks and the evaluator.

## Data model

No database. Two artifact-schema changes:

1. **Run-trace `wellforge-run/v1`** (`skills/observability/SKILL.md:37-64`) — **additive**:
   ```
   terse: boolean        # was this run dispatched with terse mode active
   control_run_id: string | null   # optional: the non-terse run this one is compared against
   ```
   Additive, non-breaking (existing readers ignore unknown fields); schema id stays
   `wellforge-run/v1`. Producers (`orchestrate`, `implement`, `spike`) set `terse`.

2. **`.forge/runs/.events.jsonl`** — unchanged. Existing per-subagent
   `{ts, event:"subagent_stop", model, input_tokens, output_tokens}` lines already carry the
   output-token signal the comparison needs. No new event type.

## API contracts

No HTTP API. The "contracts" are the command/directive interfaces:

**The terse cue (injected directive — the core contract)**
```
TERSE MODE — output tokens are the cost. Drop filler, preamble, and restating the
question. Prefer fragments over sentences. Substance only.
INVARIANT: never alter code blocks, shell commands, file paths, identifiers, or error
messages — reproduce them byte-for-byte.
EXEMPT: when writing spec.md / plan.md / tasks.md / design.md / an ADR / eval*.md, ignore
terse mode entirely and follow the full format contract.
```

**`/wellforge:orchestrate` / `/wellforge:implement`** — argument-hint gains `[--terse]`
(and `[--no-terse]` to force off under spike). Parsed and stripped in Step 0 alongside
`--mode`. When resolved on, the terse cue is prepended to every dispatched agent's task,
next to the effort cue.

**`/wellforge:terse`** (new) — no arguments. Toggles session terse state; emits the resolved state.
```
/wellforge:terse            → "Terse mode: ON until you run /wellforge:terse again."
/wellforge:terse  (again)   → "Terse mode: OFF."
```

**`/wellforge:terse-compress <path>`** (new)
```
in:   a path to a WellForge-owned file (memory/*.md | AGENTS.md | our own skill/command/
      agent description frontmatter)
steps: extract fact-set(original) → compress → extract fact-set(compressed) →
       assert fact-set(compressed) ⊇ fact-set(original) → show diff → confirm → overwrite
out:  the file, compressed in place (one-way). Refuses + reports if any fact is dropped or
      the target is not a WellForge-owned file.
```

**`run-report.py` / `status`** — `--json` output per run gains `terse` and, when a control
pairing exists, `output_tokens_saved` + `pct_saved`. `/wellforge:status` prints the savings
line only when a terse run has a paired control (else nothing, matching its existing
omit-when-empty behavior).

## Test strategy

Terse output is prose, so ACs split into **deterministic checks** (flag parsing, skill/
command presence, format validation, trace field, byte-identical passthrough, fact-set
preservation) and **LM-judge/QE checks** (terseness quality, no-fact-loss judgement, score
non-regression, the ≥40% aggregate). This split is native to WellForge (QE + evaluator own
the non-deterministic half).

| AC | Level | Check |
|---|---|---|
| AC-1.1 terse-by-default in spike | integration | Run `/wellforge:spike`; assert the terse cue is self-applied (present in the loop directive) and output is terse (LM-judge/QE) |
| AC-1.2 byte-identical code/commands | unit + integration | Fixture: output containing a code block + shell command + path; assert those spans are reproduced verbatim vs. a canonical copy |
| AC-2.1 `--terse` enables on orchestrate/implement | integration | Dispatch with `--terse`; assert terse cue is prepended to each agent task prompt |
| AC-2.2 off by default in mvp/production | integration | Dispatch without flag at `mvp`/`production`; assert no terse cue present |
| AC-2.3 `/wellforge:terse` toggle | integration | Run `/wellforge:terse` on→off→on; assert emitted state flips and governs subsequent output |
| AC-3.1 artifacts stay full-contract | integration | Under active terse, generate spec/plan/tasks; validate against spec-driven format (same validation the drift/format checks use) |
| AC-3.2 no evaluator score regression | eval | Run a fixture feature terse vs. baseline; assert spec-fidelity & code-conventions scores within rubric variance |
| AC-4.1 compression, no fact loss | unit + eval | `terse-compress` on a fixture memory file; assert fact-set(compressed) ⊇ fact-set(original) (deterministic set-check + LM-judge confirmation) |
| AC-4.2 compressed file behaves identically | integration | Consume the compressed fixture in a fresh run; assert downstream behavior matches the uncompressed baseline |
| AC-5.1 run-trace records terse-vs-control | unit | Assert a terse `orchestrate`/`implement` run writes `terse:true`; `run-report.py` computes output-token delta vs. the paired control run |
| AC-5.2 status surfaces savings | integration | With a terse+control pair present, assert `/wellforge:status` prints the savings line; absent → line omitted |
| AC-5.3 aggregate reduction ≥ 40% | measurement/eval | Across a sample of paired agent-dispatched terse/control runs, assert median output-token reduction ≥ 40% (see Risk R1 — main-loop surfaces excluded from the mechanical measure) |

Every spec AC is mapped. AC-5.1/5.3 carry the R1 caveat (measurement scoped to
agent-dispatched surfaces).

## Risks

- **R1 — the token telemetry cannot see the main loop.** The observability layer captures
  only *subagent* output tokens (`SKILL.md:108-116` honest-limits: a ~10-20× under-count,
  "audit trail, not a cost meter"). Terse mode's biggest surfaces — spike and `/wellforge:terse` — are
  **main-loop** output, which the trace can't measure. So AC-5.1/5.3's mechanical ≥40% check
  is only verifiable on `orchestrate`/`implement --terse` (subagent output IS captured).
  *Mitigation / decision needed:* scope the measured guarantee to agent-dispatched runs and
  document that main-loop terse savings are observable only via `/usage`. **This is a
  potential spec refinement (drift) — flagged for the review below**, since spec AC-5.1 reads
  "a terse run" generically. Early check: confirm subagent output-token deltas are large
  enough that a ≥40% target is realistic on agent-dispatched runs before committing the
  number. **Resolved (T9, 2026-07-25):** the SubagentStop token layer proved a ~10–20×
  undercount live (under-counted 4/6 sample runs, prompt-cache effects). Per accepted spec
  amendment, the **authoritative** measure is **output length / `/usage`**; the run-trace
  `terse`/`pct_saved` fields (T6/T7) are indicative-only. Median reduction = **40.2%** on the
  output-length basis — see `measurement-t9.md`.
- **R2 — third-party MCP tool descriptions are not editable.** The spec's US-4 names "MCP
  tool-description files," but MCP servers own their tool descriptions; WellForge cannot
  rewrite them from a file (there is no middleware layer, and adding a `caveman-shrink`-style
  runtime interceptor is a much larger, fragile lift). *Interpretation adopted:*
  `terse-compress` targets **WellForge-owned descriptions** (our skill/command/agent
  frontmatter) + memory files — the input-token savings that are actually within our
  control. If genuine third-party MCP-description shrinking is required, that is a separate,
  larger feature. **Also flagged for review** (mild scope narrowing of US-4).
- **R3 — terse mangling a command/path is a correctness bug, not a cosmetic one.** A terse
  transform that edited a shell command or path could cause real damage. Mitigated by the
  byte-identical invariant (AC-1.2) being a hard rule in the skill and a deterministic
  passthrough test, not a soft style note.
- **R4 — one-way compression could silently drop a security-relevant fact** from a memory
  file (e.g. a security-floor rule). Mitigated by the two-pass fact-preservation gate (AC-4.1)
  and the show-diff-before-overwrite confirmation. Given it is one-way, `terse-compress`
  should also refuse to run on a file with no VCS backing (so git history is the de-facto undo).
- **R5 — artifact protection is prose, not mechanically enforced.** A misbehaving agent could
  in principle terse-compress a spec. Mitigated by: the exemption being explicit in the skill,
  the writing commands loading the spec-driven skill (full-format mandate), and the evaluator/
  QE catching any fidelity regression (AC-3.2) as the backstop.

## Security

**Security-sensitive: NO** in the auth/PII/upload/payments/regulated-data sense — no owasp
pass scheduled. Two safety invariants are called out instead and covered by tests:
(1) the **byte-identical invariant** for code/commands/paths/errors (R3, AC-1.2) — a
correctness-and-safety guarantee; (2) **no security-relevant fact loss** in one-way
compression (R4, AC-4.1). The security floor and all quality/approval gates are explicitly
untouched by terse mode (spec non-goal).

## ADR

One decision here will constrain future work and deserves an ADR:
**"Terse mode as an orthogonal plain-text cue (effort-cue pattern), not a rigor tier, with
zero new config; one-way memory/own-description compression; measurement scoped to
agent-dispatched runs."** Offer to invoke the **adr-writer** agent after plan approval.
