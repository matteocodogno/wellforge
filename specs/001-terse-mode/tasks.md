---
spec: 001
generated: 2026-07-23
---

# Tasks: Terse mode — token-efficient conversational output

- [x] T1: Author the `terse` skill (authoritative definition) — refs: US-1, US-2, US-3, US-4 — deps: none
  - touch: `wellforge-plugin/skills/terse/SKILL.md` (new)
  - contains, mirroring the `rigor-tiers` skill: the **terse cue** directive text; the
    **byte-identical invariant** (never alter code/commands/paths/identifiers/errors); the
    **artifact-exemption list** (spec/plan/tasks/design/ADR/eval never terse); the
    **activation matrix** (spike default-on, `--terse` flag, `/wellforge:terse` toggle, off in
    mvp/production); and `/wellforge:terse` session semantics.
  - done when: SKILL.md exists with a heading for each of {Terse cue, Byte-identical
    invariant, Artifact exemption, Activation matrix, /wellforge:terse semantics} (verifiable by
    heading grep) and the skill is discoverable in Claude Code's skill list.

- [x] T2: Parse `--terse`/`--no-terse` and prepend the terse cue per-agent in orchestrate + implement — refs: US-2 (AC-2.1, AC-2.2) — deps: T1
  - touch: `wellforge-plugin/commands/orchestrate.md`, `wellforge-plugin/commands/implement.md`
  - parse+strip the flag in each "Step 0 — Resolve" block (orthogonal to `--mode`); when
    resolved on, prepend the terse cue to every dispatched agent's task, beside the effort cue;
    update each `argument-hint` frontmatter.
  - done when: a `--terse` dispatch shows the terse cue in dispatched agent prompts and a
    no-flag `mvp`/`production` dispatch does not (AC-2.1, AC-2.2).

- [x] T3: Spike self-applies terse by default (+ `--no-terse` opt-out) — refs: US-1 (AC-1.1) — deps: T1
  - touch: `wellforge-plugin/commands/spike.md`
  - the spike main loop self-applies the terse cue by default; `--no-terse` disables it.
  - done when: `/wellforge:spike` output is terse with no flag, and `--no-terse` restores
    normal verbosity (AC-1.1).

- [x] T4: `/wellforge:terse` main-loop toggle command — refs: US-2 (AC-2.3) — deps: T1
  - touch: `wellforge-plugin/commands/terse.md` (new)
  - toggles session terse state and emits the resolved state ("Terse mode: ON/OFF").
  - done when: running `/wellforge:terse` on→off→on flips the emitted state and governs subsequent
    output; command is discoverable in the command list (AC-2.3).

- [x] T5: `/wellforge:terse-compress` — one-way compression with fact-preservation gate — refs: US-4 (AC-4.1, AC-4.2) — deps: T1
  - touch: `wellforge-plugin/commands/terse-compress.md` (new)
  - accepts a WellForge-owned target (`memory/*.md`, `AGENTS.md`, or our own
    skill/command/agent `description`); runs extract-facts → compress → re-extract →
    assert compressed fact-set ⊇ original → show diff → confirm → overwrite in place
    (one-way). Refuses non-owned targets and files with no VCS backing.
  - done when: a fixture memory file compresses smaller with the fact-set assertion passing
    (no fact lost), a non-owned target is refused, and a fresh run consuming the compressed
    file behaves identically to the uncompressed baseline (AC-4.1, AC-4.2).

- [x] T6: Record terse state in the run trace — refs: US-5 (AC-5.1, record half) — deps: T2, T3
  - touch: `wellforge-plugin/skills/observability/SKILL.md`, `wellforge-plugin/commands/orchestrate.md`,
    `wellforge-plugin/commands/implement.md`, `wellforge-plugin/commands/spike.md`
  - additive `terse: boolean` + `control_run_id: string|null` on the `wellforge-run/v1`
    schema (id unchanged); producers set `terse` when writing their trace.
  - done when: the observability schema documents both fields and a terse
    orchestrate/implement/spike run writes `terse: true` into its `.forge/runs/<id>.json`
    (AC-5.1 record half).

- [x] T7: Compute + surface terse-vs-control savings — refs: US-5 (AC-5.1 compute, AC-5.2) — deps: T6
  - touch: `wellforge-plugin/scripts/run-report.py`, `wellforge-plugin/commands/status.md`
  - `run-report.py --json` pairs a terse run to its non-terse control (output-token totals
    from `.events.jsonl`) and emits `output_tokens_saved` + `pct_saved`; `/wellforge:status`
    prints the savings line when a pair exists and omits it otherwise.
  - done when: `run-report.py --json` reports the saved-token delta for a terse+control pair,
    and `/wellforge:status` shows it (present) / omits it (absent) (AC-5.1, AC-5.2).

- [x] T8: Verify output + artifact integrity under terse (LM-judge/QE) — refs: US-1 (AC-1.2), US-3 (AC-3.1, AC-3.2) — deps: T2, T3
  - touch: `specs/001-terse-mode/` (verification fixture + notes), reuse the spec-driven
    format check + the eval rubric
  - done when: (a) code/command/path spans in terse output are byte-identical to a canonical
    copy (AC-1.2); (b) spec/plan/tasks generated under active terse validate against the
    spec-driven format (AC-3.1); (c) a fixture feature scored terse vs. baseline shows
    spec-fidelity & code-conventions eval scores within rubric variance (AC-3.2).

- [x] T9: Measure the ≥40% reduction on agent-dispatched runs — refs: US-5 (AC-5.3) — deps: T2, T7
  - touch: `specs/001-terse-mode/measurement-t9.md`
  - run a sample of paired agent-dispatched terse/control runs; aggregate the **output-length**
    deltas (authoritative per the 2026-07-25 amendment; run-trace token layer proved unreliable).
  - done when: median output reduction across the sample is **≥ 40%** versus the control
    runs, recorded in the feature's measurement notes (AC-5.3). **Met: median 40.2%** (`measurement-t9.md`).

- [ ] T10: Close the feature — refs: (closing) — deps: T4, T5, T8, T9
  - done when: all gates green (self-CI lint + advisory checks), every task above checked,
    and `/wellforge:done 001-terse-mode` flips spec status → done.
