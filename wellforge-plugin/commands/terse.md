---
description: Toggle terse mode for the main-loop session — token-efficient conversational output, on this run and off the next
argument-hint: (no arguments — toggles)
---

Toggle the main-loop session's terse state. Load the **terse** skill now — it is the
authoritative definition of the cue, the byte-identical invariant, and the artifact
exemption; this command only resolves and states which side of the toggle the session is on.

$ARGUMENTS

## Procedure

1. **No persistent state store exists for the main loop.** Realize "session state" the
   WellForge way (same precedent as the effort cue): look back at this conversation for the
   most recent `/terse` invocation and the state it declared.
   - No prior `/terse` in this session → resolve to **ON**.
   - Most recent `/terse` declared ON → resolve to **OFF**.
   - Most recent `/terse` declared OFF → resolve to **ON**.

2. **Emit the resolved state as a stated directive** — this line (and only this line, plus
   the note below) IS the mechanism; there is no config file or flag to set:
   - Turning on: `Terse mode: ON — I will keep responses terse until you run /terse again.`
   - Turning off: `Terse mode: OFF.`

3. **From this point forward in the session:**
   - If **ON**: apply the terse skill's cue (drop filler/preamble, fragments over sentences,
     substance only) to every subsequent conversational reply, honoring the **byte-identical
     invariant** (code blocks, shell commands, file paths, identifiers, error messages are
     always reproduced verbatim) and the **artifact exemption** (writing `spec.md`,
     `plan.md`, `tasks.md`, `design.md`, an ADR, or `eval*.md` ignores terse mode entirely —
     full format contract, unaffected).
   - If **OFF**: resume normal verbosity.

## Hard rules

- No arguments are read from `$ARGUMENTS` — `/terse` only toggles; it never takes a mode.
- This governs **main-loop conversational output only** — it has no effect on
  `/wellforge:orchestrate --terse` / `/wellforge:implement --terse` (separate, per-invocation
  flags) or on `/wellforge:spike` (terse-by-default per the activation matrix). Those are
  independent axes; running `/terse` does not flip them, and running them does not flip this.
- Never let the toggle suppress or shorten a spec-driven/governance artifact — the artifact
  exemption in the terse skill always wins.
