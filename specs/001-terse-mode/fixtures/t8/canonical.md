<!--
T8 fixture — AC-1.2 (byte-identical invariant), CANONICAL (non-terse) form.
This is the baseline: verbose conversational prose wrapping four payload spans
(a code block, a shell command, a file path, an error message). The payload
spans are what must survive terse rendering byte-for-byte; the prose around
them is exactly what terse mode is allowed to compress.
-->

## Result

I looked into why the coverage gate was failing and put together a small fix.
Let me first walk through the context before getting into the specific change,
since it might not be obvious why this particular approach was chosen and
there are a couple of tradeoffs worth spelling out for future readers.

Here is the function that computes the token savings ratio:

```python
def savings_ratio(baseline: int, terse: int) -> float:
    if baseline == 0:
        raise ValueError("baseline token count must be non-zero")
    return (baseline - terse) / baseline
```

To reproduce locally, run this from the repo root:

```bash
python3 gates/scripts/check-jacoco.py --path specs/001-terse-mode/fixtures/t8/coverage.xml --min 0.80
```

The relevant file lives at `wellforge-plugin/scripts/run-report.py`, and if the
threshold is missed you will see an error that looks like this:

```
Error: coverage 0.7421 below threshold 0.80 (gates/configs/thresholds.yml)
```

I hope this clears things up — let me know if you'd like me to walk through
any of the surrounding logic again, or if there's anything else you want me
to double check before we move on.
