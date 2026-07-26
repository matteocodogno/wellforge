<!--
T11 fixture — NEGATIVE CONTROL for AC-4.1.
Identical to compressed.md except fact F4 (the local gate-check command) is
corrupted: `--min 0.40` has been silently changed to `--min 0.4`, which is a
different, non-byte-identical string. This is not a claim about real
terse-compress output — it exists only to prove check-facts.py actually
detects a dropped/altered fact rather than passing vacuously. Expected: FAIL.
-->

# Terse Mode — Working Memory

Operational facts for terse-mode work.

- Target: 40% output-token reduction target (spec AC-5.3).
- OFF by default in mvp and production unless --terse is passed; ON only in spike.
- Default auto-on tier: TERSE_MODE_DEFAULT_TIER=spike (read by the orchestrator).
- Local gate check: `mise run terse:check -- --min 0.4`.
- Invariant + exemption list: `wellforge-plugin/skills/terse/SKILL.md`.
- Authoritative AC: AC-4.1 in `specs/001-terse-mode/spec.md`.
