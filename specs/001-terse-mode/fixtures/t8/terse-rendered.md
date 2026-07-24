<!--
T8 fixture — AC-1.2 (byte-identical invariant), TERSE-RENDERED form of the same
output as canonical.md. Prose (preamble/postamble/filler) has been compressed
per the terse cue in wellforge-plugin/skills/terse/SKILL.md. The four payload
spans (code block, shell command, path, error message) are reproduced
byte-for-byte from canonical.md — this is the invariant AC-1.2 requires.
-->

## Result

Coverage gate fix.

```python
def savings_ratio(baseline: int, terse: int) -> float:
    if baseline == 0:
        raise ValueError("baseline token count must be non-zero")
    return (baseline - terse) / baseline
```

Repro:

```bash
python3 gates/scripts/check-jacoco.py --path specs/001-terse-mode/fixtures/t8/coverage.xml --min 0.80
```

File: `wellforge-plugin/scripts/run-report.py`

```
Error: coverage 0.7421 below threshold 0.80 (gates/configs/thresholds.yml)
```
