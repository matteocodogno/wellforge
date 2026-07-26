#!/usr/bin/env python3
"""T12 fixture — durable AC-5.1 pairing test for run-report.py.

Promotes T7's scratchpad dry-run into a committed, deterministic test (spec.md AC-5.1 /
plan.md Test strategy AC-5.1 row: "Assert a terse orchestrate/implement run writes
terse:true; run-report.py computes output-token delta vs. the paired control run").

Fixtures (this directory, `runs/`):
  - control-run.json  — a non-terse `implement` run of feature `001-terse-mode`.
  - terse-run.json    — a terse `implement` run of the SAME feature+command, paired to the
                         control via an explicit `control_run_id` (the producer-set pairing
                         path in `find_control()`, run-report.py:119-170).
  - orphan-run.json   — a terse run of a DIFFERENT feature (`999-orphan-feature`) with no
                         `control_run_id` and no same-feature/command sibling in this fixture
                         set at all — `find_control()` must return None for it.
  - .events.jsonl     — per-run output-token events, one block per run's [started, finished]
                         window, plus one stray event far outside every window (proves the
                         window join doesn't leak tokens across runs).

Hand math (see .events.jsonl):
  control window [10:00:00Z, 10:10:00Z) -> output_tokens = 5000 + 3000 = 8000
  terse   window [11:00:00Z, 11:10:00Z) -> output_tokens = 4000
  output_tokens_saved = 8000 - 4000 = 4000
  pct_saved            = round((8000 - 4000) / 8000 * 100, 1) = 50.0

Invokes the REAL `run-report.py` (subprocess, stdlib only, no network) against this fixture
runs-dir with `--json`, then asserts:
  (a) the terse+control pair yields output_tokens_saved == 4000 and pct_saved == 50.0,
      paired to the expected control_run_id;
  (b) the orphan run's report entry OMITS output_tokens_saved/pct_saved/control_run_id
      entirely (no control resolves for it).

Exit 0 if every assertion passes, exit 1 (with a diagnostic) otherwise.

Usage: python3 test_run_report_pairing.py
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]  # t12 -> fixtures -> 001-terse-mode -> specs -> <repo root>
RUN_REPORT = REPO_ROOT / "wellforge-plugin" / "scripts" / "run-report.py"
RUNS_DIR = HERE / "runs"

CONTROL_RUN_ID = "2026-07-20T10-00-00Z-implement-001-terse-mode"
TERSE_RUN_ID = "2026-07-20T11-00-00Z-implement-001-terse-mode"
ORPHAN_RUN_ID = "2026-07-20T12-00-00Z-implement-999-orphan-feature"

EXPECTED_OUTPUT_TOKENS_SAVED = 4000
EXPECTED_PCT_SAVED = 50.0

failures = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(label)


def main():
    if not RUN_REPORT.exists():
        print(f"FATAL: run-report.py not found at {RUN_REPORT}", file=sys.stderr)
        return 1
    if not RUNS_DIR.is_dir():
        print(f"FATAL: fixture runs-dir not found at {RUNS_DIR}", file=sys.stderr)
        return 1

    proc = subprocess.run(
        [sys.executable, str(RUN_REPORT), "--runs-dir", str(RUNS_DIR), "--json"],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        print("FATAL: run-report.py exited non-zero", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        return 1

    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"FATAL: --json output was not valid JSON ({e})", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        return 1

    by_id = {entry.get("run_id"): entry for entry in report}

    check("report contains control-run entry", CONTROL_RUN_ID in by_id)
    check("report contains terse-run entry", TERSE_RUN_ID in by_id)
    check("report contains orphan-run entry", ORPHAN_RUN_ID in by_id)
    if failures:
        # Can't check field contents on missing entries — bail with what we have.
        print(f"\n{len(failures)} check(s) failed (missing entries).", file=sys.stderr)
        return 1

    control = by_id[CONTROL_RUN_ID]
    terse = by_id[TERSE_RUN_ID]
    orphan = by_id[ORPHAN_RUN_ID]

    # --- sanity on the raw window token totals feeding the hand math ---
    check(
        "control run's own output_tokens == 8000 (5000+3000 in its window)",
        control.get("output_tokens") == 8000,
        f"got {control.get('output_tokens')!r}",
    )
    check(
        "terse run's own output_tokens == 4000 (its window)",
        terse.get("output_tokens") == 4000,
        f"got {terse.get('output_tokens')!r}",
    )

    # --- (a) terse+control pair: delta + pct against hand math ---
    check("terse entry terse == True", terse.get("terse") is True, f"got {terse.get('terse')!r}")
    check(
        "terse entry paired to expected control_run_id",
        terse.get("control_run_id") == CONTROL_RUN_ID,
        f"got {terse.get('control_run_id')!r}",
    )
    check(
        "terse entry output_tokens_saved == 4000 (hand math: 8000-4000)",
        terse.get("output_tokens_saved") == EXPECTED_OUTPUT_TOKENS_SAVED,
        f"got {terse.get('output_tokens_saved')!r}",
    )
    check(
        "terse entry pct_saved == 50.0 (hand math: (8000-4000)/8000*100)",
        terse.get("pct_saved") == EXPECTED_PCT_SAVED,
        f"got {terse.get('pct_saved')!r}",
    )

    # --- (b) orphan run: omit case ---
    check("orphan entry terse == True", orphan.get("terse") is True, f"got {orphan.get('terse')!r}")
    check(
        "orphan entry OMITS output_tokens_saved (no control resolved)",
        "output_tokens_saved" not in orphan,
        f"unexpectedly present: {orphan.get('output_tokens_saved')!r}",
    )
    check(
        "orphan entry OMITS pct_saved (no control resolved)",
        "pct_saved" not in orphan,
        f"unexpectedly present: {orphan.get('pct_saved')!r}",
    )
    check(
        "orphan entry OMITS control_run_id (no control resolved)",
        "control_run_id" not in orphan,
        f"unexpectedly present: {orphan.get('control_run_id')!r}",
    )

    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"All checks PASSED ({len(report)} run entries; AC-5.1 pairing + omit case verified).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
