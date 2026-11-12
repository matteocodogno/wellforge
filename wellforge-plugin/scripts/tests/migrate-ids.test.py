#!/usr/bin/env python3
"""Regression matrix for migrate-ids.py — legacy NNN-/NNNN- ids renamed to date ids.

Run: uv run --with pyyaml python wellforge-plugin/scripts/tests/migrate-ids.test.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "migrate-ids.py")
spec = importlib.util.spec_from_file_location("forge_state", os.path.join(HERE, "..", "forge-state.py"))
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


def w(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(text)


def r(root, rel):
    return open(os.path.join(root, rel)).read()


def g(root, *args, date=None):
    env = dict(os.environ)
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    return subprocess.run(["git", "-C", root, *args], check=True, capture_output=True, text=True, env=env)


def repo():
    d = tempfile.mkdtemp()
    g(d, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@t"), ("user.name", "T"), ("commit.gpgsign", "false")):
        g(d, "config", k, v)
    return d


def commit(root, msg="chore: fixture", date=None):
    g(root, "add", "-A")
    g(root, "commit", "-qm", msg, date=date)


def run(root, *args):
    out = subprocess.run([sys.executable, SCRIPT, "--root", root, "--json", *args],
                         capture_output=True, text=True)
    return out.returncode, (json.loads(out.stdout) if out.stdout.strip() else {}), out.stderr


def spec_md(id_, slug, status, extra=""):
    return f"---\nid: {id_}\nslug: {slug}\nstatus: {status}\ncreated: {{c}}\n{extra}---\n\n# {slug}\n"


def project():
    d = repo()
    w(d, "specs/001-login/spec.md",
      "---\nid: 001\nslug: login\nstatus: superseded\nsuperseded_by: 002-login-sso\n"
      "created: 2026-09-01\nsuperseded: 2026-09-05\n---\n\n# login\n")
    w(d, "specs/002-login-sso/spec.md",
      "---\nid: 002\nslug: login-sso\nstatus: done\ncreated: 2026-09-05\ndone: 2026-09-10\n---\n\n"
      "# login-sso\nReplaces 001-login. See docs/adr/0001-jwt-sessions.md.\n")
    w(d, "specs/002-login-sso/tasks.md", "---\nspec: 002\n---\n\n- [x] T1: task\n")
    w(d, "specs/003-csv/brief.md",
      "---\nid: 3\nslug: csv\nrigor: spike\nstatus: in-progress\ncreated: 2026-10-01\n---\n\n# csv\n")
    w(d, "specs/README.md", "Features live here; 001-login was the first.\n")
    w(d, "docs/adr/0001-jwt-sessions.md",
      "# 0001 — JWT sessions\n\n**Date:** 2026-09-03  \n**Status:** Accepted\n")
    w(d, "docs/adr/0002-no-date.md", "# 0002 — No date line\n\nSupersedes ADR 0001.\n")
    w(d, "AGENTS.md", "## Architecture decisions\n\n"
      "- [0001] JWT sessions — rule (see docs/adr/0001-jwt-sessions.md)\n"
      "- [0002] No date — rule (see docs/adr/0002-no-date.md)\n"
      "Port 0001 is unrelated.\n")
    w(d, "src/notes.md", "Done in specs/002 (T1). Not 0010-other, not 001-login-extra.\n")
    commit(d, date="2026-09-20T10:00:00Z")
    # A run trace — untracked on purpose (some projects ignore .forge/runs/).
    w(d, ".git/info/exclude", ".forge/runs/\n")
    w(d, ".forge/runs/r1.json", json.dumps({
        "schema": "wellforge-run/v2", "run_id": "r1", "command": "implement",
        "feature": "002-login-sso", "rigor": "production", "started": "2026-09-08T10:00:00Z",
        "finished": "2026-09-08T10:30:00Z", "agents": [], "drift_events": [], "verdicts": {}}))
    return d


print("migrate-ids matrix")

# ── dry run changes nothing ─────────────────────────────────────────────────────
d = project()
code, res, _ = run(d)
check("dry run exits 0", code, 0)
check("dry run plans features",
      [(f["old"], f["new"]) for f in res["features"]],
      [("001-login", "20260901-login"), ("002-login-sso", "20260905-login-sso"), ("003-csv", "20261001-csv")])
check("ADR date from **Date:**, else from git",
      [(a["old"], a["new"], a["date_from"]) for a in res["adrs"]],
      [("0001-jwt-sessions", "20260903-jwt-sessions", "**Date:**"),
       ("0002-no-date", "20260920-no-date", "git (first commit)")])
check("dry run touches nothing", os.path.isdir(os.path.join(d, "specs/001-login")), True)
check("dry run is not applied", res["applied"], False)

# ── apply ───────────────────────────────────────────────────────────────────────
code, res, err = run(d, "--apply")
check("apply exits 0", code, 0)
check("apply reports applied", res.get("applied"), True)
check("old dir gone", os.path.exists(os.path.join(d, "specs/001-login")), False)
check("new dir present", os.path.isdir(os.path.join(d, "specs/20260901-login")), True)
st = g(d, "status", "--porcelain").stdout
check("renames are staged as renames, rewrites staged too",
      "R  specs/001-login/spec.md -> specs/20260901-login/spec.md" in st, True)
check("nothing left unstaged in tracked files", [l for l in st.splitlines() if l[1] not in " ?"], [])
s = r(d, "specs/20260901-login/spec.md")
check("superseded_by rewritten", "superseded_by: 20260905-login-sso" in s, True)
check("own id rewritten", "\nid: 20260901\n" in s, True)
check("tasks.md spec: rewritten", "spec: 20260905" in r(d, "specs/20260905-login-sso/tasks.md"), True)
check("unpadded id: 3 rewritten", "\nid: 20261001\n" in r(d, "specs/20261001-csv/brief.md"), True)
check("cross-ref to feature + ADR path rewritten",
      "Replaces 20260901-login. See docs/adr/20260903-jwt-sessions.md." in
      r(d, "specs/20260905-login-sso/spec.md"), True)
check("non-feature file under specs/ rewritten", "20260901-login was the first" in r(d, "specs/README.md"), True)
check("specs/NNN short form rewritten, look-alikes left alone",
      r(d, "src/notes.md"), "Done in specs/20260905-login-sso (T1). Not 0010-other, not 001-login-extra.\n")
a = r(d, "AGENTS.md")
check("AGENTS.md decision tag + path rewritten",
      "- [20260903] JWT sessions — rule (see docs/adr/20260903-jwt-sessions.md)" in a, True)
check("unrelated 0001 left alone", "Port 0001 is unrelated." in a, True)
check("ADR heading rewritten", r(d, "docs/adr/20260903-jwt-sessions.md").startswith("# 20260903 — JWT"), True)
check("ADR N reference rewritten", "Supersedes ADR 20260903-jwt-sessions." in
      r(d, "docs/adr/20260920-no-date.md"), True)
check("untracked run trace rewritten",
      json.loads(r(d, ".forge/runs/r1.json"))["feature"], "20260905-login-sso")
m = json.loads(r(d, ".forge/id-migration.json"))
check("map records features", m["features"]["003-csv"], "20261001-csv")
check("map records ADRs", m["adrs"]["0002-no-date"], "20260920-no-date")
env = fs.build(os.path.join(d, "specs"), os.path.join(d, ".forge", "runs"), None, d)
check("forge-state: no problems after migration", sum(len(f["problems"]) for f in env["features"]), 0)
check("forge-state: run still attributed", next(f for f in env["features"]
                                                if f["slug"] == "20260905-login-sso")["runs"], 1)

# ── idempotent ──────────────────────────────────────────────────────────────────
commit(d, "refactor: date-based ids")
code, res, _ = run(d, "--apply")
check("second run: nothing to do", (code, res["features"], res["adrs"], res["applied"]), (0, [], [], False))

# ── refusals ────────────────────────────────────────────────────────────────────
d = project()
w(d, "dirty.txt", "x")
code, res, _ = run(d, "--apply")
check("dirty tree refused", code, 1)
check("...and nothing renamed", os.path.isdir(os.path.join(d, "specs/001-login")), True)

d = repo()
w(d, "specs/001-auth/spec.md", spec_md("001", "auth", "done").replace("{c}", "2026-09-01"))
w(d, "specs/004-auth/spec.md", spec_md("004", "auth", "draft").replace("{c}", "2026-09-01"))
commit(d)
code, res, _ = run(d, "--apply")
check("same date + slug refused", (code, any("both map to" in e for e in res["errors"])), (1, True))

d = repo()
w(d, "specs/001-x/spec.md", spec_md("001", "x", "draft").replace("{c}", "2026-09-01"))
w(d, "specs/20260901-x/spec.md", spec_md("20260901", "x", "draft").replace("{c}", "2026-09-01"))
commit(d)
code, res, _ = run(d)
check("existing target refused", (code, any("already exists" in e for e in res["errors"])), (1, True))

# drift on an in-progress feature: the rename would hide it
d = repo()
w(d, "specs/001-feat/spec.md", spec_md("001", "feat", "in-progress").replace("{c}", "2026-09-01"))
w(d, "specs/001-feat/tasks.md", "---\nspec: 001\n---\n\n- [ ] T1: task\n")
commit(d, "chore: tasks")
open(os.path.join(d, "specs/001-feat/spec.md"), "a").write("\namended\n")
commit(d, "docs: amend spec")
code, res, _ = run(d, "--apply")
check("drift on a live feature refused", (code, any("drift" in e for e in res["errors"])), (1, True))
check("...nothing renamed", os.path.isdir(os.path.join(d, "specs/001-feat")), True)
code, res, _ = run(d, "--apply", "--force")
check("--force applies anyway", (code, res.get("applied")), (0, True))

print(f"\nmigrate-ids: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
