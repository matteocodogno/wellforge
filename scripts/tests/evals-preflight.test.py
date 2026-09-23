#!/usr/bin/env python3
"""ci.yml's `evals-preflight` step script, run against controlled git histories.

WHY THIS EXISTS. This job decides whether the optional prompt-eval job runs, and the FIRST
time it ran in CI it failed outright:

    ##[error]Unable to process file command 'output' successfully.
    ##[error]Invalid format 'expected state for forks and for anyone without a key, …'

$GITHUB_OUTPUT is a file of single-line `key=value` pairs. A value containing a newline is
not a longer value, it is a syntax error — and I had written a four-line explanation into
one. Nothing local caught it because nothing local ran the script; `actionlint` checks
shell syntax, and the shell was fine.

So the script is EXTRACTED from the workflow, not restated, and driven here the way GitHub
drives it: real environment variables, a real $GITHUB_OUTPUT file, a real git repository
with known commits. The decision logic is tested at the same time, because a job that
decides whether a costly job runs is worth being sure about.

Run: scripts/tests/evals-preflight.test.py     (needs pyyaml)
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"

wf = yaml.safe_load(CI.read_text())
job = wf["jobs"]["evals-preflight"]
step = next(s for s in job["steps"] if s.get("id") == "decide")
SCRIPT = step["run"]

passed = failed = 0
OUT_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def _ok(name):
    global passed
    passed += 1
    print(f"  ok    {name}")


def _bad(name, detail):
    global failed
    failed += 1
    print(f"  FAIL  {name}\n          {detail}")


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                           "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main",
                           *args], cwd=cwd, capture_output=True, text=True)


def make_repo(tmp):
    """A repo with three commits: seed, a PROMPT change, then a docs-only change."""
    git(tmp, "init", "-q", ".")
    (tmp / "README.md").write_text("seed\n")
    git(tmp, "add", "-A"); git(tmp, "commit", "-qm", "seed")
    seed = git(tmp, "rev-parse", "HEAD").stdout.strip()

    d = tmp / "wellforge-plugin" / "commands"
    d.mkdir(parents=True)
    (d / "status.md").write_text("# status\n")
    git(tmp, "add", "-A"); git(tmp, "commit", "-qm", "prompt change")
    prompt = git(tmp, "rev-parse", "HEAD").stdout.strip()

    (tmp / "README.md").write_text("seed\nmore docs\n")
    git(tmp, "add", "-A"); git(tmp, "commit", "-qm", "docs only")
    docs = git(tmp, "rev-parse", "HEAD").stdout.strip()
    return seed, prompt, docs


def run(name, cwd, env_extra, want_should_run):
    with tempfile.NamedTemporaryFile("w+", delete=False) as f:
        out_path = f.name
    env = dict(os.environ)
    env.update(GITHUB_OUTPUT=out_path, HAS_KEY="false", EVENT="push",
               BEFORE="", PR_BASE="", SHA="")
    env.update(env_extra)
    p = subprocess.run(["bash", "-c", SCRIPT], cwd=cwd, env=env,
                       capture_output=True, text=True)
    body = pathlib.Path(out_path).read_text()
    os.unlink(out_path)

    if p.returncode != 0:
        _bad(name, f"the step exited {p.returncode}: {(p.stderr or p.stdout).strip()[:200]}")
        return

    # THE regression: every line must be a single-line key=value. A multi-line value is
    # what GitHub rejects, and it rejects the whole step.
    bad_lines = [ln for ln in body.splitlines() if ln and not OUT_LINE.match(ln)]
    if bad_lines:
        _bad(name, f"$GITHUB_OUTPUT holds a line GitHub cannot parse: {bad_lines[0]!r} "
                   f"(a value with a newline in it fails the whole step)")
        return

    got = dict(ln.split("=", 1) for ln in body.splitlines() if ln)
    if "should_run" not in got or "reason" not in got:
        _bad(name, f"expected should_run and reason, got {sorted(got)}")
        return
    if got["should_run"] != want_should_run:
        _bad(name, f"should_run={got['should_run']!r}, wanted {want_should_run!r} "
                   f"(reason: {got['reason'][:120]})")
        return
    _ok(f"{name}  → should_run={got['should_run']}")


print("\nevals-preflight\n")

with tempfile.TemporaryDirectory() as td:
    tmp = pathlib.Path(td)
    seed, prompt, docs = make_repo(tmp)

    # No key: the whole point. Optional means skip, and the step must still SUCCEED.
    run("no ANTHROPIC_API_KEY", tmp, {"HAS_KEY": "false"}, "false")
    # …and with a long prose reason, which is the shape that broke it.
    run("no key, prose reason stays one line", tmp, {"HAS_KEY": "false"}, "false")

    # A manual run is a deliberate request and always runs.
    run("workflow_dispatch", tmp,
        {"HAS_KEY": "true", "EVENT": "workflow_dispatch"}, "true")

    # Push ranges.
    run("push touching commands/", tmp,
        {"HAS_KEY": "true", "EVENT": "push", "BEFORE": seed, "SHA": prompt}, "true")
    run("push touching only docs", tmp,
        {"HAS_KEY": "true", "EVENT": "push", "BEFORE": prompt, "SHA": docs}, "false")
    run("pull_request touching commands/", tmp,
        {"HAS_KEY": "true", "EVENT": "pull_request", "PR_BASE": seed, "SHA": prompt}, "true")

    # A new branch pushes the zero sha; an unknown base is not a reason to silently skip.
    run("new branch (zero base) runs rather than skips", tmp,
        {"HAS_KEY": "true", "EVENT": "push",
         "BEFORE": "0" * 40, "SHA": docs}, "true")
    run("unknown base sha runs rather than skips", tmp,
        {"HAS_KEY": "true", "EVENT": "push", "BEFORE": "d" * 40, "SHA": docs}, "true")

print(f"\nevals-preflight: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
