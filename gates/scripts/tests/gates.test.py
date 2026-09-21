#!/usr/bin/env python3
"""Regression matrix for the gate scripts — run-eval.py and check-jacoco.py.

`gates/README.md` has claimed "tested: pass/fail/floor" for check-jacoco.py since it was
written, and there was no test file anywhere in the repository. The two scripts here decide
whether work ships: one turns a judge's JSON into a PASS/FAIL, the other turns a coverage
report into one. Both had ways to say PASS that nothing could have caught.

The bug that prompted this: run-eval.py never clamped a judge score, so a judge answering
9 on every 1-5 dimension printed `TOTAL 180.0/100 ... verdict: PASS` — a verdict
arithmetically incapable of failing, rendered in the same format as a real one.

Run: uv run --with pyyaml python gates/scripts/tests/gates.test.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GATES))
RUBRIC = os.path.join(GATES, "..", "configs", "eval-rubric.yml")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ev = _load("run_eval", os.path.join(GATES, "run-eval.py"))

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want!r}\n        got  {got!r}")


rubric, by_key = ev.load_rubric(RUBRIC)
SCALE = rubric["scale"]
ALL = list(by_key)


def scores(**kw):
    """Every dimension at `default`, overridden per key."""
    default = kw.pop("default", SCALE)
    return [{"key": k, "score": kw.get(k, default), "evidence": "x"} for k in ALL]


print("gates matrix")
print(f"  rubric: scale 1-{SCALE}, pass ≥ {rubric['pass_score']}, {len(ALL)} dimensions")

# ── 1. the happy path ───────────────────────────────────────────────────────────
DESIGN = {"spec.md", "plan.md", "tasks.md", "design.md"}
NODESIGN = {"spec.md", "plan.md", "tasks.md"}

v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(), DESIGN)
check("top marks pass", v, "PASS")
check("...with a total of exactly 100", total, 100.0)
check("...and no errors", errors, [])

# ── 2. below the pass score, every floor met ────────────────────────────────────
v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(default=3), DESIGN)
check("mid scores fall under the pass score", v, "FAIL")
check("...without tripping a floor", [f for f in floors if f != "ac_satisfaction"], [])

# ── 3. a floor bites even when the total is high ────────────────────────────────
# ac_satisfaction has floor 4: a 3 there fails regardless of everything else being 5.
v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(ac_satisfaction=3), DESIGN)
check("a single sub-floor dimension fails the run", v, "FAIL")
check("...and names the dimension", floors, ["ac_satisfaction"])
check("...even though the total is above the pass score", total >= rubric["pass_score"], True)

# ── 4. OUT OF RANGE — the bug ───────────────────────────────────────────────────
v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(default=9), DESIGN)
check("a score above the scale fails the run", v, "FAIL")
check("...and the total is clamped to at most 100", total <= 100.0, True)
check("...and every excursion is reported", len(errors), len(ALL))
check("...naming the scale", "outside the 1-5 scale" in errors[0], True)

v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(default=0), DESIGN)
check("a score below the scale also fails", v, "FAIL")
check("...clamped up to 1, not left at 0", total > 0, True)

v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(trajectory=-5), DESIGN)
check("one bad dimension is enough to fail", v, "FAIL")
check("...and only it is reported", len(errors), 1)

v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(trajectory="four"), DESIGN)
check("a non-integer score is a judge error", v, "FAIL")
check("...reported as such", "not an integer" in errors[0], True)

# ── 5. applicability comes from DISK, not from what the judge returned ──────────
# design.md present, judge omitted the dimension: it applies and scores worst.
partial = [s for s in scores() if s["key"] != "design_fidelity"]
v, total, rows, floors, errors = ev.gate(rubric, by_key, partial, DESIGN)
check("design.md present + unscored → the dimension applies", v, "FAIL")
check("...and fails its floor rather than vanishing", floors, ["design_fidelity"])

# design.md absent, judge omitted it: genuinely N/A, and the rest re-normalises to 100.
v, total, rows, floors, errors = ev.gate(rubric, by_key, partial, NODESIGN)
check("design.md absent + unscored → not applicable", v, "PASS")
check("...and the total re-normalises over the rest", total, 100.0)

# design.md absent but the judge scored it anyway: ignored, and flagged.
v, total, rows, floors, errors = ev.gate(rubric, by_key, scores(), NODESIGN)
check("design.md absent + scored → the score is ignored", v, "FAIL")
check("...and reported as a judge error", "does not apply" in errors[0], True)

# The pre-fix fallback survives for a caller that cannot say what is on disk.
v, total, rows, floors, errors = ev.gate(rubric, by_key, partial, None)
check("with presence unknown, absence of a score still means N/A", v, "PASS")

# ── 6. gather_present reads the directory ───────────────────────────────────────
d = tempfile.mkdtemp()
open(os.path.join(d, "spec.md"), "w").write("# s\n")
check("gather_present finds what exists", ev.gather_present(d), {"spec.md"})
open(os.path.join(d, "design.md"), "w").write("# d\n")
check("...and notices design.md", "design.md" in ev.gather_present(d), True)

# ── 7. end to end, because the exit code is what CI reads ───────────────────────
jr = os.path.join(d, "judge.json")
json.dump({"scores": scores(default=9)}, open(jr, "w"))
out = subprocess.run([sys.executable, os.path.join(GATES, "run-eval.py"),
                      "--rubric", RUBRIC, "--judge-response", jr, "--spec-dir", d],
                     capture_output=True, text=True)
check("an over-range judge exits non-zero", out.returncode, 1)
check("...and says why", "outside the 1-5 scale" in out.stdout, True)
check("...and never prints a total above 100",
      all(not l.startswith("TOTAL") or float(l.split()[1].split("/")[0]) <= 100.0
          for l in out.stdout.splitlines()), True)

json.dump({"scores": scores()}, open(jr, "w"))
out = subprocess.run([sys.executable, os.path.join(GATES, "run-eval.py"),
                      "--rubric", RUBRIC, "--judge-response", jr, "--spec-dir", d],
                     capture_output=True, text=True)
check("a clean judge exits 0", out.returncode, 0)

# ── 8. check-jacoco.py — the "tested: pass/fail/floor" the README promised ──────
JACOCO = os.path.join(GATES, "check-jacoco.py")


def report(line_missed, line_covered, branch=None):
    p = os.path.join(d, f"jacoco-{line_missed}-{line_covered}-{branch}.xml")
    b = (f'<counter type="BRANCH" missed="{branch[0]}" covered="{branch[1]}"/>'
         if branch else "")
    open(p, "w").write(
        '<?xml version="1.0"?><report name="t">'
        f'<counter type="LINE" missed="{line_missed}" covered="{line_covered}"/>{b}</report>')
    return p


def jacoco(path, *args):
    return subprocess.run([sys.executable, JACOCO, path, *args],
                          capture_output=True, text=True)


r = jacoco(report(10, 90), "--min-line", "80")
check("90% line coverage passes an 80% gate", r.returncode, 0)

r = jacoco(report(30, 70), "--min-line", "80")
check("70% fails an 80% gate", r.returncode, 1)
check("...with an actionable error", "below the WellForge gate" in r.stdout, True)

# The floor: a scaffold-sized module is not held to the threshold.
r = jacoco(report(40, 5), "--min-line", "80", "--floor-lines", "50")
check("a module under the line floor is exempt", r.returncode, 0)
check("...and says so rather than passing silently", "enforcement skipped" in r.stdout, True)
r = jacoco(report(40, 5), "--min-line", "80", "--floor-lines", "10")
check("...and is NOT exempt once it is big enough", r.returncode, 1)

# Branch coverage is reported-only at 0 and enforced above it.
r = jacoco(report(10, 90, branch=(50, 50)), "--min-line", "80")
check("branch coverage is reported, not enforced, at --min-branch 0", r.returncode, 0)
check("...and labelled as such", "reported only" in r.stdout, True)
r = jacoco(report(10, 90, branch=(50, 50)), "--min-line", "80", "--min-branch", "70")
check("...and enforced when a threshold is set", r.returncode, 1)

# Inputs that are not reports must fail loudly, not read as 100%.
r = jacoco(os.path.join(d, "nope.xml"), "--min-line", "80")
check("a missing report fails", r.returncode, 1)
open(os.path.join(d, "bad.xml"), "w").write("not xml at all")
r = jacoco(os.path.join(d, "bad.xml"), "--min-line", "80")
check("unparseable XML fails", r.returncode, 1)
open(os.path.join(d, "empty.xml"), "w").write('<?xml version="1.0"?><report name="t"/>')
r = jacoco(os.path.join(d, "empty.xml"), "--min-line", "80")
check("a report with no LINE counter fails (did tests run?)", r.returncode, 1)

print(f"\ngates: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
