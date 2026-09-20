#!/usr/bin/env python3
"""Regression matrix for forge-state.py — the deterministic half of feature state.

Every case here is state four commands used to re-derive with the model. The point of the
script is that these answers are now testable at all; the point of this file is that they
stay answered the same way.

Run: uv run --with pyyaml python wellforge-plugin/scripts/tests/forge-state.test.py
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "forge-state.py")
spec = importlib.util.spec_from_file_location("forge_state", SCRIPT)
fs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fs)

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want!r}\n        got  {got!r}")


def repo():
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", "-b", "main", d], check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "T"), ("commit.gpgsign", "false")):
        subprocess.run(["git", "-C", d, "config", k, v], check=True)
    os.makedirs(os.path.join(d, "specs"))
    return d


def feature(root, slug, spec_fm=None, brief_fm=None, tasks=None, tasks_fm=None,
            plan_fm=None, eval_fm=None):
    p = os.path.join(root, "specs", slug)
    os.makedirs(p, exist_ok=True)
    def write(name, fm, body=""):
        if fm is None:
            return
        lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
        open(os.path.join(p, name), "w").write(f"---\n{lines}\n---\n\n# {slug}\n{body}")
    write("spec.md", spec_fm)
    write("brief.md", brief_fm)
    write("plan.md", plan_fm)
    write("eval-report.md", eval_fm)
    if tasks is not None:
        body = "\n".join(f"- [{'x' if done else ' '}] T{i+1}: task" for i, done in enumerate(tasks))
        write("tasks.md", tasks_fm or {"spec": "001"}, "\n" + body + "\n")
    return p


def trace(root, slug, **kw):
    rd = os.path.join(root, ".forge", "runs")
    os.makedirs(rd, exist_ok=True)
    run = {"schema": "wellforge-run/v1", "run_id": kw.get("run_id", f"r-{slug}"),
           "command": "implement", "feature": slug, "rigor": kw.get("rigor", "production"),
           "started": kw.get("at", "2026-09-01T10:00:00Z"),
           "finished": kw.get("at", "2026-09-01T10:30:00Z"),
           "agents": kw.get("agents", []), "drift_events": [],
           "verdicts": kw.get("verdicts", {})}
    json.dump(run, open(os.path.join(rd, run["run_id"] + ".json"), "w"))


def commit(root, msg="chore: fixture"):
    subprocess.run(["git", "-C", root, "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", root, "commit", "-qm", msg], check=True, capture_output=True)


def state(root, **kw):
    return fs.build(os.path.join(root, "specs"), os.path.join(root, ".forge", "runs"),
                    kw.get("feature"), root)


def one(env, slug):
    return next(f for f in env["features"] if f["slug"] == slug)


print("forge-state matrix")

# ── every status ────────────────────────────────────────────────────────────────
r = repo()
feature(r, "001-draft", {"id": "001", "slug": "draft", "status": "draft"})
feature(r, "002-approved", {"id": "002", "slug": "approved", "status": "approved", "approved": "2026-09-01"})
feature(r, "003-inprog", {"id": "003", "slug": "inprog", "status": "in-progress"}, tasks=[True, False])
feature(r, "004-done", {"id": "004", "slug": "done", "status": "done", "done": "2026-09-02"}, tasks=[True])
feature(r, "005-superseded", {"id": "005", "slug": "superseded", "status": "superseded",
                              "superseded_by": "004-done"})
feature(r, "006-archived", {"id": "006", "slug": "archived", "status": "archived",
                            "archive_reason": "approach rejected"})
commit(r)
env = state(r)
for slug, st in [("001-draft", "draft"), ("002-approved", "approved"), ("003-inprog", "in-progress"),
                 ("004-done", "done"), ("005-superseded", "superseded"), ("006-archived", "archived")]:
    check(f"status {st}", one(env, slug)["status"], st)
check("terminal flag: done", one(env, "004-done")["terminal"], True)
check("terminal flag: superseded", one(env, "005-superseded")["terminal"], True)
check("terminal flag: archived", one(env, "006-archived")["terminal"], True)
check("terminal flag: in-progress is not", one(env, "003-inprog")["terminal"], False)
check("superseded_by surfaced", one(env, "005-superseded")["superseded_by"], "004-done")
check("archive_reason surfaced", one(env, "006-archived")["archive_reason"], "approach rejected")
check("no false problems on valid fixtures", sum(len(f["problems"]) for f in env["features"]), 0)
check("task counts", one(env, "003-inprog")["tasks"], {"total": 2, "checked": 1})

# ── every tier, and the precedence ──────────────────────────────────────────────
r = repo()
feature(r, "001-prod", {"id": "001", "slug": "prod", "status": "in-progress", "rigor": "production"})
feature(r, "002-mvp", {"id": "002", "slug": "mvp", "status": "in-progress", "rigor": "mvp"})
feature(r, "003-spike", brief_fm={"id": "003", "slug": "spike", "status": "in-progress", "rigor": "spike"})
feature(r, "004-unset", {"id": "004", "slug": "unset", "status": "in-progress"})
commit(r)
env = state(r)
check("tier production", one(env, "001-prod")["rigor"], "production")
check("tier mvp", one(env, "002-mvp")["rigor"], "mvp")
check("tier spike", one(env, "003-spike")["rigor"], "spike")
check("unset tier defaults to production", one(env, "004-unset")["rigor"], "production")
check("unset tier says where it came from", one(env, "004-unset")["rigor_from"], "default")
check("a brief-only feature is a spike", one(env, "003-spike")["kind"], "spike")
check("spike gate is not machine-checkable", one(env, "003-spike")["done_gate"]["passes"], None)

# project default overrides the absent frontmatter value
os.makedirs(os.path.join(r, ".forge"), exist_ok=True)
json.dump({"rigor": "mvp"}, open(os.path.join(r, ".forge", "manifest.json"), "w"))
env = state(r)
check("project default applies when frontmatter is silent", one(env, "004-unset")["rigor"], "mvp")
check("...and says so", one(env, "004-unset")["rigor_from"], ".forge/manifest.json")
check("frontmatter still wins over the project default", one(env, "001-prod")["rigor"], "production")

# ── drift present / absent ──────────────────────────────────────────────────────
r = repo()
feature(r, "001-clean", {"id": "001", "slug": "clean", "status": "in-progress"}, tasks=[True])
commit(r, "chore: clean feature")
env = state(r)
check("no drift when tasks.md is newest", one(env, "001-clean")["drift"]["drifted"], False)

p = os.path.join(r, "specs", "001-clean", "spec.md")
open(p, "a").write("\nan amendment\n")
commit(r, "docs: amend the spec after tasks")
env = state(r)
d = one(env, "001-clean")["drift"]
check("drift when spec.md is newer than tasks.md", d["drifted"], True)
check("drift names the artifact", [s["artifact"] for s in d["sources"]], ["spec.md"])
check("drift blocks the done gate", "drift" in " ".join(one(env, "001-clean")["done_gate"]["failing"]), True)

# ── schema violations ───────────────────────────────────────────────────────────
r = repo()
feature(r, "001-typo", {"id": "001", "slug": "typo", "status": "doen"})            # the typo case
feature(r, "002-badtier", {"id": "002", "slug": "badtier", "status": "draft", "rigor": "prod"})
feature(r, "003-nopointer", {"id": "003", "slug": "nopointer", "status": "superseded"})
feature(r, "004-noreason", {"id": "004", "slug": "noreason", "status": "archived"})
feature(r, "005-nodate", {"id": "005", "slug": "nodate", "status": "done"})
commit(r)
env = state(r)
check("`status: doen` is rejected", any("doen" in p for p in one(env, "001-typo")["problems"]), True)
check("bad tier is rejected", any("prod" in p for p in one(env, "002-badtier")["problems"]), True)
check("superseded without a pointer is rejected",
      any("superseded_by" in p for p in one(env, "003-nopointer")["problems"]), True)
check("archived without a reason is rejected",
      any("archive_reason" in p for p in one(env, "004-noreason")["problems"]), True)
check("done without a date is rejected", any("`done`" in p for p in one(env, "005-nodate")["problems"]), True)
check("a schema violation does not crash the report", len(env["features"]), 5)

# ── missing .forge/runs/ ────────────────────────────────────────────────────────
r = repo()
feature(r, "001-x", {"id": "001", "slug": "x", "status": "in-progress"}, tasks=[True])
commit(r)
env = state(r)
check("missing runs dir is reported, not crashed", env["runs_available"], False)
check("absent QE verdict is None, not FAIL", one(env, "001-x")["verdicts"]["qe"]["verdict"], None)
check("absent verdict blocks the gate", one(env, "001-x")["done_gate"]["passes"], False)
check("...and says the verdict is absent",
      any("absent" in f for f in one(env, "001-x")["done_gate"]["failing"]), True)

# ── both verdict kinds, and the gate per tier ───────────────────────────────────
r = repo()
feature(r, "001-prod", {"id": "001", "slug": "prod", "status": "in-progress", "rigor": "production"},
        tasks=[True, True], eval_fm={"spec": "001", "verdict": "PASS", "score": 88})
trace(r, "001-prod", verdicts={"qe": "PASS", "eval": "PASS"},
      agents=[{"agent": "evaluator", "outcome": "PASS", "score": 88}])
feature(r, "002-mvp", {"id": "002", "slug": "mvp", "status": "in-progress", "rigor": "mvp"}, tasks=[True])
trace(r, "002-mvp", run_id="r-mvp", verdicts={"qe": "PASS"})
feature(r, "003-qefail", {"id": "003", "slug": "qefail", "status": "in-progress"}, tasks=[True])
trace(r, "003-qefail", run_id="r-qefail", verdicts={"qe": "FAIL"})
commit(r)
env = state(r)
check("QE verdict joined from the trace", one(env, "001-prod")["verdicts"]["qe"]["verdict"], "PASS")
check("eval verdict joined from the trace", one(env, "001-prod")["verdicts"]["eval"]["verdict"], "PASS")
check("eval score joined", one(env, "001-prod")["verdicts"]["eval"]["score"], 88)
check("verdict carries its timestamp", one(env, "001-prod")["verdicts"]["qe"]["at"] is not None, True)
check("production gate passes with tasks + QE + eval", one(env, "001-prod")["done_gate"]["passes"], True)
check("mvp gate passes without an eval", one(env, "002-mvp")["done_gate"]["passes"], True)
check("mvp gate does not ask for an eval",
      any("eval" in f for f in one(env, "002-mvp")["done_gate"]["failing"]), False)
check("QE FAIL blocks the gate", one(env, "003-qefail")["done_gate"]["passes"], False)

# production with QE PASS but no eval → blocked on the eval specifically
feature(r, "004-noeval", {"id": "004", "slug": "noeval", "status": "in-progress", "rigor": "production"},
        tasks=[True])
trace(r, "004-noeval", run_id="r-noeval", verdicts={"qe": "PASS"})
commit(r, "chore: add noeval fixture")
env = state(r)
check("production without an eval is blocked",
      any("eval-report" in f for f in one(env, "004-noeval")["done_gate"]["failing"]), True)

# ── the envelope itself ─────────────────────────────────────────────────────────
check("envelope version", env["version"], "forge-state/v1")
for key in ("generated", "features", "runs_available", "specs_dir", "runs_dir"):
    check(f"envelope carries `{key}`", key in env, True)
for key in ("slug", "kind", "status", "rigor", "artifacts", "tasks", "drift", "verdicts",
            "done_gate", "problems"):
    check(f"feature carries `{key}`", key in one(env, "001-prod"), True)

# ── the CLI, end to end ─────────────────────────────────────────────────────────
out = subprocess.run([sys.executable, SCRIPT, "--specs-dir", os.path.join(r, "specs"),
                      "--runs-dir", os.path.join(r, ".forge", "runs"), "--root", r, "--json"],
                     capture_output=True, text=True)
check("--json exits 0", out.returncode, 0)
try:
    parsed = json.loads(out.stdout)
    check("--json emits the envelope", parsed["version"], "forge-state/v1")
except json.JSONDecodeError as e:
    check(f"--json is valid JSON ({e})", False, True)
out2 = subprocess.run([sys.executable, SCRIPT, "--specs-dir", os.path.join(r, "specs"),
                       "--runs-dir", os.path.join(r, ".forge", "runs"), "--root", r],
                      capture_output=True, text=True)
check("human table exits 0", out2.returncode, 0)
check("human table has a header", "FEATURE" in out2.stdout, True)
check("--feature filters", len(state(r, feature="001-prod")["features"]), 1)

print(f"\nforge-state: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
