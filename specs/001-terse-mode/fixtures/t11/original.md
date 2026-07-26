<!--
T11 fixture — AC-4.1 fact-preservation, ORIGINAL (pre-compression) memory file.
Six atomic facts are embedded in verbose prose below (numbered so the checker's
facts.txt can be cross-referenced by eye). `terse-compress` is allowed to shorten
the prose around them, but every fact string in facts.txt must survive verbatim —
that's the deterministic half of AC-4.1's no-fact-loss gate (plan.md's "unit"
test-strategy row for AC-4.1). See compressed.md (good) and compressed-BAD.md
(negative control, F4 corrupted) alongside this file.
-->

# Terse Mode — Working Memory

This file is scratch memory for terse-mode work carried across sessions. It captures a
handful of operational facts contributors keep re-deriving from the spec and plan, so
nobody has to re-read those documents just to remember the basics.

## Facts to remember

1. The output-token reduction target WellForge is holding this feature to is the
   40% output-token reduction target committed to in the spec's AC-5.3.

2. Terse mode is OFF by default in mvp and production unless --terse is passed on
   the command line — spike is the only tier where it's on without anyone asking.

3. The default rigor tier where terse mode activates automatically is captured by the
   identifier TERSE_MODE_DEFAULT_TIER=spike, which the orchestrator reads at run time.

4. If you want to sanity check the compression gate locally before trusting it in CI,
   the command to run is:

   `mise run terse:check -- --min 0.40`

   It shells out to the same fact-preservation logic the terse-compress command uses.

5. The file that documents the byte-identical invariant and the artifact-exemption list
   in full is `wellforge-plugin/skills/terse/SKILL.md` — read it before touching any
   compression logic.

6. The authoritative acceptance criterion governing all of this is AC-4.1 in `specs/001-terse-mode/spec.md` —
   if in doubt about scope, that's the source of truth.

That's everything worth remembering here; anything else, go re-read the spec and plan
directly rather than trusting a stale paraphrase in this notes file.
