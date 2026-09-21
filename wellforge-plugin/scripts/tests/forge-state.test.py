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
import time
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
    run = {"schema": kw.get("schema", "wellforge-run/v2"), "run_id": kw.get("run_id", f"r-{slug}"),
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
trace(r, "001-prod", verdicts={"qe": "PASS", "security": "PASS", "eval": "PASS"},
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

check("security verdict joined from the trace",
      one(env, "001-prod")["verdicts"]["security"]["verdict"], "PASS")

# Security review at production: every batch is reviewed, so ABSENT means it never ran.
# An unreviewed auth change passes every test — that is the gap this condition closes.
feature(r, "005-nosec", {"id": "005", "slug": "nosec", "status": "in-progress", "rigor": "production"},
        tasks=[True], eval_fm={"spec": "005", "verdict": "PASS"})
trace(r, "005-nosec", run_id="r-nosec", verdicts={"qe": "PASS", "eval": "PASS"})
commit(r, "chore: add nosec fixture")
env = state(r)
check("production without a security verdict is blocked",
      any("security review is absent" in f for f in one(env, "005-nosec")["done_gate"]["failing"]), True)
check("...and mvp is not asked for one",
      any("security" in f for f in one(env, "002-mvp")["done_gate"]["failing"]), False)

feature(r, "006-secfail", {"id": "006", "slug": "secfail", "status": "in-progress", "rigor": "production"},
        tasks=[True], eval_fm={"spec": "006", "verdict": "PASS"})
trace(r, "006-secfail", run_id="r-secfail",
      verdicts={"qe": "PASS", "security": "FAIL", "eval": "PASS"})
commit(r, "chore: add secfail fixture")
env = state(r)
check("a FAIL security verdict blocks too",
      any("security review is FAIL" in f for f in one(env, "006-secfail")["done_gate"]["failing"]), True)

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
check("verdicts carry all three kinds",
      sorted(one(env, "001-prod")["verdicts"]), ["eval", "qe", "security"])
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

# ── a v1 trace still counts (schema bumped to v2 in plugin 2.39) ────────────────
# Traces outlive the plugin that wrote them, and forge-state reads them through
# run-report's loader — so the loader accepting both versions has to hold end to end here,
# not just in run-report's own tests.
r_v1 = repo()
feature(r_v1, "001-old", {"id": "001", "slug": "old", "status": "in-progress", "rigor": "mvp"},
        tasks=[True])
trace(r_v1, "001-old", run_id="r-v1", schema="wellforge-run/v1", verdicts={"qe": "PASS"})
commit(r_v1)
env_v1 = state(r_v1)
check("a v1 trace still yields its QE verdict",
      one(env_v1, "001-old")["verdicts"]["qe"]["verdict"], "PASS")
check("...and an mvp gate built on it passes",
      one(env_v1, "001-old")["done_gate"]["passes"], True)

# ── malformed traces must not take the whole report down ─────────────────────
# One bad file in .forge/runs/ raised AttributeError and exited 1, contradicting the
# "Exit 0 always" contract — and post-spec-guard.sh read the empty result as "could not
# evaluate the done gate", so it ALLOWED a `status: done` edit unverified. A single
# unparseable file silently switched the gate off.
for label, body in (
    ("a JSON list",        "[1]"),
    ("a bare string",      '"hello"'),
    ("null",               "null"),
    ("agents as a string", '{"schema":"wellforge-run/v3","feature":"001-bad","agents":"x"}'),
    ("a null in agents",   '{"schema":"wellforge-run/v3","feature":"001-bad","agents":[null]}'),
    ("verdicts as string", '{"schema":"wellforge-run/v3","feature":"001-bad","verdicts":"PASS"}'),
    ("unknown schema",     '{"schema":"wellforge-run/v9","feature":"001-bad"}'),
    ("truncated JSON",     '{"schema":'),
):
    r = repo()
    feature(r, "001-bad", spec_fm={"id": 1, "slug": "bad", "status": "in-progress",
                                   "rigor": "mvp"}, tasks=[True])
    rd = os.path.join(r, ".forge", "runs")
    os.makedirs(rd, exist_ok=True)
    open(os.path.join(rd, "bad.json"), "w").write(body)
    try:
        env = state(r)
        ok = True
    except Exception as e:  # noqa: BLE001
        ok = False
        env = None
        print(f"    raised: {type(e).__name__}: {e}")
    check(f"{label} does not raise", ok, True)
    if env is not None:
        check(f"{label} is reported under top-level problems[]",
              any("bad.json" in p for p in env.get("problems", [])), True)
    shutil.rmtree(r, ignore_errors=True)

# A malformed trace beside a GOOD one must not cost the good one's verdicts.
r = repo()
feature(r, "001-mix", spec_fm={"id": 1, "slug": "mix", "status": "in-progress",
                               "rigor": "mvp"}, tasks=[True])
trace(r, "001-mix", verdicts={"qe": "PASS"})
open(os.path.join(r, ".forge", "runs", "bad.json"), "w").write("[1]")
env = state(r)
check("a good trace beside a malformed one still yields its verdict",
      one(env, "001-mix")["verdicts"]["qe"]["verdict"], "PASS")
check("...and the malformed one is still reported",
      any("bad.json" in p for p in env.get("problems", [])), True)
shutil.rmtree(r, ignore_errors=True)

# ── drift must see the WORKING TREE, not only the last commit ────────────────
# _newer compared commit times, so an uncommitted spec edit reported no drift (its
# commit is old) and an uncommitted tasks re-sync still reported drift. Both wrong, and
# both wrong in the direction that says "nothing to do".
import time

r = repo()
feature(r, "001-d", spec_fm={"id": 1, "slug": "d", "status": "in-progress", "rigor": "mvp"},
        tasks=[True])
commit(r)
check("committed together → no drift", one(state(r), "001-d")["drift"]["drifted"], False)
time.sleep(1.1)
open(os.path.join(r, "specs", "001-d", "spec.md"), "a").write("\nan uncommitted edit\n")
check("UNCOMMITTED spec edit is drift",
      one(state(r), "001-d")["drift"]["drifted"], True)
# ...and re-syncing tasks (also uncommitted) clears it again.
time.sleep(1.1)
open(os.path.join(r, "specs", "001-d", "tasks.md"), "a").write("\n- [x] T2: resynced\n")
check("UNCOMMITTED tasks re-sync clears the drift",
      one(state(r), "001-d")["drift"]["drifted"], False)
shutil.rmtree(r, ignore_errors=True)

# ── drift is about CONTENT, not about the file having been touched ──────────
# The regression this guards: /wellforge:done writes `status: done` into spec.md's
# frontmatter as its LAST action, so under a plain mtime rule spec.md was always newer
# than tasks.md, the production gate reported drift, and post-spec-guard.sh blocked the
# transition /wellforge:done had just performed.
#
# These ran green on macOS before the fix for a second reason worth knowing: _is_dirty
# compared abspath(path) against abspath(repo) while compute_drift passes a RELATIVE
# path, so on a symlinked /var/folders temp dir nothing was ever dirty and the whole
# code path was dead. Both halves are fixed; these cells fail against either bug.
SPEC_BODY = "\n\n# X\n\nThe requirement.\n"


def spec_text(status="in-progress", extra="", title="Thing", body=SPEC_BODY):
    fm = f"id: 001\nslug: x\nstatus: {status}\nrigor: production\ntitle: {title}"
    return f"---\n{fm}{extra}\n---{body}"


def drift_fixture():
    r = repo()
    d = os.path.join(r, "specs", "001-x")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "spec.md"), "w").write(spec_text())
    open(os.path.join(d, "tasks.md"), "w").write("---\nspec: 001\nsynced: 2026-09-01\n---\n\n- [x] T1\n")
    commit(r)
    time.sleep(1.05)
    return r, d


def drifted(r, d):
    # getattr, so this file can also be run against an OLDER forge-state.py (the mutation
    # check) and report clean FAILs instead of an AttributeError.
    fs._DIRTY_CACHE.clear()
    getattr(fs, "_CLASS_CACHE", {}).clear()
    return fs.compute_drift(d, r)


# cell 1 — spec dirty, BODY changed: drift, on the mtime clock
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "w").write(spec_text(body="\n\n# X\n\nA DIFFERENT requirement.\n"))
res = drifted(r, d)
check("spec dirty / body changed is drift", res["drifted"], True)
check("...on the mtime-dirty clock", res["sources"][0]["clock"], "mtime-dirty")
shutil.rmtree(r, ignore_errors=True)

# cell 2 — spec dirty, LIFECYCLE frontmatter only: NOT drift. This is the close.
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "w").write(spec_text(status="done", extra="\ndone: 2026-09-20"))
check("spec dirty / lifecycle frontmatter only is NOT drift", drifted(r, d)["drifted"], False)
shutil.rmtree(r, ignore_errors=True)

# ...but a non-lifecycle frontmatter field is a spec change like any other.
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "w").write(spec_text(title="Something Else"))
check("spec dirty / `title` changed IS drift (not a lifecycle field)",
      drifted(r, d)["drifted"], True)
shutil.rmtree(r, ignore_errors=True)

# cell 3 — tasks dirty: an uncommitted re-sync clears drift left by a committed spec move
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "w").write(spec_text(body="\n\n# X\n\nNEW requirement.\n"))
commit(r)
check("committed spec body change, tasks not re-synced → drift", drifted(r, d)["drifted"], True)
time.sleep(1.05)
open(os.path.join(d, "tasks.md"), "a").write("- [x] T2: resynced\n")
check("tasks dirty / uncommitted re-sync clears drift", drifted(r, d)["drifted"], False)
shutil.rmtree(r, ignore_errors=True)

# cell 4 — BOTH dirty. Order decides, and it must decide the same way round both ways.
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "w").write(spec_text(body="\n\n# X\n\nNEW requirement.\n"))
time.sleep(1.05)
open(os.path.join(d, "tasks.md"), "a").write("- [x] T2: resynced\n")
check("both dirty / tasks re-synced last → no drift", drifted(r, d)["drifted"], False)
shutil.rmtree(r, ignore_errors=True)

r, d = drift_fixture()
open(os.path.join(d, "tasks.md"), "a").write("- [x] T2\n")
time.sleep(1.05)
open(os.path.join(d, "spec.md"), "w").write(spec_text(body="\n\n# X\n\nNEW requirement.\n"))
check("both dirty / spec changed last → drift", drifted(r, d)["drifted"], True)
shutil.rmtree(r, ignore_errors=True)

# UNTRACKED: no HEAD version, so there is no baseline and mtime is the only honest answer.
r, d = drift_fixture()
open(os.path.join(d, "plan.md"), "w").write("---\nstatus: approved\n---\n\n# plan\n")
res = drifted(r, d)
check("an untracked plan.md is drift", res["drifted"], True)
check("...and says which clock answered", res["sources"][0]["clock"], "mtime-untracked")
shutil.rmtree(r, ignore_errors=True)

# The path bug itself, asserted directly: compute_drift passes a RELATIVE path.
r, d = drift_fixture()
open(os.path.join(d, "spec.md"), "a").write("edited\n")
_prev = os.getcwd()
os.chdir(r)
fs._DIRTY_CACHE.clear()
check("_is_dirty works on a RELATIVE path (what compute_drift passes)",
      fs._is_dirty(os.path.join("specs", "001-x", "spec.md"), r), True)
os.chdir(_prev)
shutil.rmtree(r, ignore_errors=True)

# The close, end to end through the gate — the shape post-spec-guard evaluates.
r = repo()
p = feature(r, "001-close",
            spec_fm={"id": 1, "slug": "close", "status": "in-progress", "rigor": "production"},
            tasks=[True], eval_fm={"spec": "001", "verdict": "PASS", "score": 90})
trace(r, "001-close", verdicts={"qe": "PASS", "security": "PASS", "eval": "PASS"})
commit(r)
time.sleep(1.05)
# Derive the new frontmatter from the old one, touching ONLY the lifecycle fields — that
# is exactly what /wellforge:done does. (A first draft of this fixture also retyped
# `id: 1` as `id: 001`; the gate correctly called that a spec change, because `id` is not
# a lifecycle field. The fixture was wrong, not the rule.)
_orig = open(os.path.join(p, "spec.md")).read()
_fm, _body = _orig.split("---", 2)[1], _orig.split("---", 2)[2]
_fm = _fm.replace("status: in-progress", "status: done\ndone: 2026-09-20")
open(os.path.join(p, "spec.md"), "w").write("---" + _fm + "---" + _body)
check("closing a production feature leaves the gate passing",
      one(state(r), "001-close")["done_gate"]["passes"], True)
shutil.rmtree(r, ignore_errors=True)

# ── last_activity: a directory mtime does not move when a file is edited ─────
r = repo()
p = feature(r, "001-act", spec_fm={"id": 1, "slug": "act", "status": "draft", "rigor": "mvp"})
commit(r)
before = one(state(r), "001-act")["last_activity"]
time.sleep(1.1)
open(os.path.join(p, "spec.md"), "a").write("\nedited\n")
after = one(state(r), "001-act")["last_activity"]
check("editing a file inside the feature moves last_activity", after > before, True)
check("last_activity is UTC with a Z", after.endswith("Z"), True)
shutil.rmtree(r, ignore_errors=True)

# ── eval staleness: done.md promised this condition and nothing computed it ──
r = repo()
feature(r, "001-stale",
        spec_fm={"id": 1, "slug": "stale", "status": "in-progress", "rigor": "production"},
        tasks=[True],
        eval_fm={"spec": "001", "verdict": "PASS", "score": 90})
trace(r, "001-stale", verdicts={"qe": "PASS", "security": "PASS", "eval": "PASS"})
os.makedirs(os.path.join(r, "src"), exist_ok=True)
open(os.path.join(r, "src", "app.py"), "w").write("x = 1\n")
commit(r)
check("a fresh eval passes the gate", one(state(r), "001-stale")["done_gate"]["passes"], True)
time.sleep(1.1)
open(os.path.join(r, "src", "app.py"), "a").write("y = 2\n")   # code moved on
g = one(state(r), "001-stale")["done_gate"]
check("a code change AFTER the eval makes it stale", g["passes"], False)
check("...and the reason says so", any("stale" in f for f in g["failing"]), True)
shutil.rmtree(r, ignore_errors=True)

# ── --explain-gate is the single definition the docs quote ───────────────────
out = subprocess.run([sys.executable, SCRIPT, "--explain-gate"],
                     capture_output=True, text=True)
check("--explain-gate exits 0", out.returncode, 0)
for needed in ("verdicts.qe == PASS", "verdicts.security == PASS", "eval is not stale",
               "no drift", "tasks.md exists"):
    check(f"--explain-gate lists `{needed}`", needed in out.stdout, True)

print(f"\nforge-state: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
