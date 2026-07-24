<!--
T8 fixture — NEGATIVE CONTROL for AC-1.2.
Deliberately mangles the shell command's --min value (0.80 -> 0.8) to prove
extract-spans.sh actually detects drift rather than passing vacuously. This
file is not a claim about real terse output — it exists only to validate the
check itself. See verification-t8.md, AC-1.2, "Negative control".
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
python3 gates/scripts/check-jacoco.py --path specs/001-terse-mode/fixtures/t8/coverage.xml --min 0.8
```

File: `wellforge-plugin/scripts/run-report.py`

```
Error: coverage 0.7421 below threshold 0.80 (gates/configs/thresholds.yml)
```
