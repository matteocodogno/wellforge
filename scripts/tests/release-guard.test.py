#!/usr/bin/env python3
"""release-guard's step script, run against synthetic `needs` payloads.

WHY THIS EXISTS. `release-guard` is the one check in ci.yml that only ever fires on a
release tag, which makes it the one check nobody can exercise without minting a public tag.
It was wrong for its whole life and nothing said so: it had no `if: always()`, so a job that
FAILED did not satisfy `needs:` and the guard was SKIPPED rather than red — and a skipped
required check satisfies branch protection under the default settings. The guard that exists
to stop a red tag was silent on exactly the run it was built for.

So it is tested here, from the outside, the same contract as every other suite in this repo:
the script is EXTRACTED from .github/workflows/ci.yml rather than restated, and only the
`${{ }}` expressions GitHub itself would substitute are substituted. A guard whose logic is
only ever proven by cutting a real tag is not proven.

Run: scripts/tests/release-guard.test.py   (needs pyyaml; `uv run --with pyyaml` works)
"""
import json
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"

wf = yaml.safe_load(CI.read_text())
guard = wf["jobs"]["release-guard"]
NEEDS_LIST = list(guard["needs"])
SCRIPT = guard["steps"][0]["run"]

passed = failed = 0


def _bad(name, detail):
    global failed
    failed += 1
    print(f"  FAIL  {name}\n          {detail}")


def _ok(name):
    global passed
    passed += 1
    print(f"  ok    {name}")


def needs(**overrides):
    """Every job green, then apply overrides (underscores become hyphens)."""
    n = {j: {"result": "success"} for j in NEEDS_LIST}
    for k, v in overrides.items():
        key = k.replace("_", "-")
        assert key in n, f"{key} is not in release-guard's needs:"
        n[key] = {"result": v}
    return json.dumps(n)


def run(name, needs_json, want_fail, ref_name="cli-v9.9.9", simulated="false"):
    body = SCRIPT.replace("${{ github.ref_name }}", ref_name)
    leftover = body.replace("${{ github.event_name == 'workflow_dispatch' }}", "")
    if "${{" in leftover:
        _bad(name, "the step still holds an unsubstituted ${{ }} expression — this test "
                   "would be proving nothing")
        return
    env = dict(os.environ, NEEDS=needs_json, OPTIONAL_JOBS="", SIMULATED=simulated)
    p = subprocess.run(["bash", "-c", body], env=env, capture_output=True, text=True)
    if (p.returncode != 0) == want_fail:
        _ok(name)
    else:
        want = "non-zero" if want_fail else "zero"
        out = (p.stdout + p.stderr).strip().splitlines()
        _bad(name, f"rc={p.returncode}, wanted {want}\n          "
                   + "\n          ".join(out[-3:]))


print("\nrelease-guard\n")

# ── the job's own wiring, before its logic ────────────────────────────────────
# Without always(), a failed dependency SKIPS this job instead of failing it. This is the
# original bug, and it is a property of the `if:`, not of the script.
if "always()" in str(guard.get("if", "")):
    _ok("the job runs even when a dependency failed (if: always())")
else:
    _bad("the job runs even when a dependency failed (if: always())",
         "release-guard has no always() — a red dependency will SKIP it, and a skipped "
         "required check reads as green")

# Jobs a release tag deliberately does NOT require. Every name here is a decision someone
# made on purpose, and writing it down is the point: an omission from `needs:` then reads as
# a mistake rather than as "probably intentional".
#
#   plugin-evals — the prompt-layer eval suite. It is an LLM judge, which is a noisy
#   instrument, and it costs money per run. A gate that fails for reasons nobody can
#   reproduce teaches people to ignore gates, so it reports and a human reads it. Promote it
#   into `needs:` (and delete this line) once its scores have been stable for a while.
NOT_REQUIRED = {"plugin-evals"}

expected = set(wf["jobs"]) - {"release-guard"} - NOT_REQUIRED
missing = sorted(expected - set(NEEDS_LIST))
unexpected = sorted(set(NEEDS_LIST) - expected - NOT_REQUIRED)
if not missing and not unexpected:
    _ok(f"needs: lists every job a tag requires ({len(NEEDS_LIST)}; "
        f"{len(NOT_REQUIRED)} deliberately excluded)")
else:
    detail = []
    if missing:
        detail.append(f"not in release-guard's needs: {missing} — the guard cannot require "
                      f"a job it does not depend on. If that is deliberate, add it to "
                      f"NOT_REQUIRED here with the reason.")
    if unexpected:
        detail.append(f"in needs: but not a job in the workflow: {unexpected}")
    _bad("needs: lists every job a tag requires", " ".join(detail))

# ── the script's logic ────────────────────────────────────────────────────────
run("all green on a release tag", needs(), want_fail=False)
run("a FAILED job fails the guard", needs(cli="failure"), want_fail=True)
run("a SKIPPED job fails the guard", needs(cli="skipped"), want_fail=True)
run("a CANCELLED job fails the guard", needs(cli="cancelled"), want_fail=True)
# `formula` is continue-on-error, so `needs:` reports it satisfied even when it failed.
run("a failed continue-on-error job fails the guard", needs(formula="failure"),
    want_fail=True)
run("several red jobs still fail", needs(cli="failure", scaffold="skipped"), want_fail=True)
# A guard that checks nothing must not pass: an empty context is a failure, not a sweep.
run("an empty needs context fails", "{}", want_fail=True)
run("a truncated needs context fails", json.dumps({"cli": {"result": "success"}}),
    want_fail=True)
run("a tag outside the documented series fails", needs(), want_fail=True, ref_name="banana")
run("workflow_dispatch does not check the ref name", needs(), want_fail=False,
    ref_name="guard-proof", simulated="true")
run("workflow_dispatch does NOT excuse a red job", needs(cli="failure"), want_fail=True,
    ref_name="guard-proof", simulated="true")

print(f"\nrelease-guard: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
