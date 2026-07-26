<!--
T11 fixture — AC-4.1 fact-preservation, GOOD compressed form of original.md.
Prose is genuinely shorter (filler and restated context dropped, per the
terse-compress command's Step 2), but all six atomic facts from original.md
are still recoverable verbatim, including the shell command, the file path,
and the TERSE_MODE_DEFAULT_TIER identifier — the byte-identical invariant the
command holds even under compression. Checked by check-facts.py against
facts.txt: expected PASS.
-->

# Terse Mode — Working Memory

Operational facts for terse-mode work.

- Target: 40% output-token reduction target (spec AC-5.3).
- OFF by default in mvp and production unless --terse is passed; ON only in spike.
- Default auto-on tier: TERSE_MODE_DEFAULT_TIER=spike (read by the orchestrator).
- Local gate check: `mise run terse:check -- --min 0.40`.
- Invariant + exemption list: `wellforge-plugin/skills/terse/SKILL.md`.
- Authoritative AC: AC-4.1 in `specs/001-terse-mode/spec.md`.
