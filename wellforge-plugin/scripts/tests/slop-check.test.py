#!/usr/bin/env python3
"""Fixture matrix for slop-check.py — the advisory UI-slop catalogue.

Two failure modes matter, and they pull in opposite directions. A sign that stops firing is
invisible (a clean report looks exactly like a clean screen). A sign that fires on designed
code trains everyone to ignore the check. So: every sign must fire on the sloppy fixture,
nothing may fire on the clean one — which is built from near misses — and the advisory exit
contract is pinned, because a gate that turns red on a judgement call stops being advisory.

Run: uv run --with pyyaml python wellforge-plugin/scripts/tests/slop-check.test.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sc", os.path.join(HERE, "..", "slop-check.py"))
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
SIGNS = sc.load_config()
FIX = os.path.join(HERE, "fixtures", "slop")

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want!r}\n        got  {got!r}")


def ids(text, name):
    return {f["id"] for f in sc.scan_text(text, name, SIGNS)}


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sc.main(argv)
    return rc, buf.getvalue()


print("slop-check matrix")
print(f"  catalogue: {len(SIGNS)} signs")

# ── the catalogue itself ─────────────────────────────────────────────────────────────
all_ids = [s["id"] for s in SIGNS]
check("sign ids are unique", len(all_ids), len(set(all_ids)))
for s in SIGNS:
    check(f"{s['id']}: group is a known pass", s["group"] in sc.GROUP_ORDER, True)
    check(f"{s['id']}: names a sign and a fix", bool(s.get("sign")) and bool(s.get("fix")), True)

# ── every sign fires on the sloppy fixtures (a sign that never fires is dead weight) ──
sloppy = sc.scan(sc.collect([os.path.join(FIX, "sloppy")], [], None, ".")[0], SIGNS)
fired = {f["id"] for f in sloppy}
for sid in all_ids:
    check(f"fires on the sloppy fixtures: {sid}", sid in fired, True)

# ── nothing fires on the clean fixture: on-grid arbitrary values, an identifier that
#    contains a hype word, a check mark, tight tracking on LARGE text, a skeleton marked
#    slop-ok. Each of these is a false positive some earlier draft produced. ──────────
clean = sc.scan(sc.collect([os.path.join(FIX, "clean")], [], None, ".")[0], SIGNS)
check("clean fixture scans clean", [(f["id"], f["line"]) for f in clean], [])

# ── individual near misses, line by line ────────────────────────────────────────────
for line, name, want in [
    ('<div className="mt-[13px]">', "a.tsx", {"off-grid-spacing"}),
    ('<div className="mt-[12px] px-[2px] gap-[0px]">', "a.tsx", set()),
    ('<div className="mt-[12.5px]">', "a.tsx", {"off-grid-spacing"}),
    ("  padding: 8px 13px;", "a.css", set()),              # first value decides; 8 is on grid
    ("  margin-top: 10px;", "a.css", {"off-grid-spacing-css"}),
    ("  width: 13px;", "a.css", set()),                     # not spacing
    ("<p>Unlock your potential</p>", "a.tsx", {"hype-copy"}),
    ("onClick={() => unlock()}", "a.tsx", set()),
    ("const unlockAccount = 1", "a.tsx", set()),
    ('title="Seamless sync"', "a.tsx", {"hype-copy"}),
    ("<p>Saved</p>", "a.tsx", set()),
    ("<p>Saved!</p>", "a.tsx", {"exclamation-copy"}),
    ("if (!ready) return <p>Wait</p>", "a.tsx", set()),     # negation is not copy
    ('className="uppercase"', "a.tsx", set()),              # uppercase alone is fine
    ('className="uppercase tracking-wider"', "a.tsx", {"tracked-uppercase"}),
    ('className="text-4xl tracking-tight"', "a.tsx", set()),
    ('className="font-semibold"', "a.tsx", set()),
    ("<Title fw={500}>", "a.tsx", set()),
    ("<span>✓ Paid</span>", "a.tsx", set()),
    ("<span>⚠️ Overdue</span>", "a.tsx", {"emoji-icon"}),
    ("<span>🔥 Hot</span>", "a.tsx", {"emoji-icon"}),
    ('<span className="animate-spin" />', "a.tsx", set()),  # a spinner is not idle motion
    ('<span className="animate-ping" /> {/* slop-ok: live */}', "a.tsx", set()),
    ('className="backdrop-blur-sm"', "a.tsx", set()),       # blur alone (a scrim) is fine
    ('className="hover:scale-95"', "a.tsx", set()),         # press-down is the allowed form
    ('className="transition-colors"', "a.tsx", set()),
    ("  font-weight: 500;", "a.css", set()),
    # a rule is scoped to its file kind: CSS syntax in TSX is not a style finding …
    ("  font-weight: 900;", "a.tsx", set()),
    # … but HTML/Vue/Svelte carry their own <style>, so style rules apply there
    ("  font-weight: 900;", "a.html", {"heavy-weight-css"}),
    ("  font-weight: 900;", "a.vue", {"heavy-weight-css"}),
    # a Copier template is judged as the file it renders to
    ('<div className="mt-[13px]">', "App.tsx.jinja", {"off-grid-spacing"}),
    ('<div className="mt-[13px]">', "notes.md", set()),
]:
    check(f"{name}: {line!r}", ids(line, name), want)

# ── which files are looked at ───────────────────────────────────────────────────────
for p, want in [
    ("src/App.tsx", True), ("src/App.tsx.jinja", True), ("public/index.html", True),
    ("src/theme.css", True), ("src/App.test.tsx", False), ("src/App.spec.tsx", False),
    ("node_modules/x/a.tsx", False), ("dist/index.html", False), ("src/app.min.css", False),
    ("src/__tests__/a.tsx", False), ("src/api.ts", False), ("README.md", False),
    (".wellforge-gates/wellforge-plugin/scripts/tests/fixtures/slop/sloppy/Dashboard.tsx", False),
]:
    check(f"scannable({p})", sc.scannable(p), want)

# ── output order follows the passes: spacing before color before … motion ──────────
order = [f["group"] for f in sloppy]
ranks = [sc.GROUP_ORDER.index(g) for g in order]
check("findings are ordered by pass", ranks, sorted(ranks))

# ── the advisory exit contract ──────────────────────────────────────────────────────
rc, out = run([os.path.join(FIX, "sloppy")])
check("findings exit 0 by default (advisory)", rc, 0)
check("text output ends on the headline", out.strip().splitlines()[-1].startswith("ui-slop:"), True)
rc, _ = run([os.path.join(FIX, "sloppy"), "--strict"])
check("--strict exits 1 on findings", rc, 1)
rc, _ = run([os.path.join(FIX, "clean"), "--strict"])
check("--strict exits 0 when clean", rc, 0)
rc, out = run([os.path.join(FIX, "sloppy"), "--json"])
doc = json.loads(out)
check("json: summary.level is heavy for the sloppy fixtures", doc["summary"]["level"], "heavy")
check("json: one record per finding", doc["summary"]["findings"], len(doc["findings"]))
check("json: findings carry path/line/id/fix",
      all({"path", "line", "id", "fix"} <= set(f) for f in doc["findings"]), True)
rc, out = run([os.path.join(FIX, "sloppy"), "--format", "github"])
check("github: one ::warning per finding",
      sum(1 for l in out.splitlines() if l.startswith("::warning file=")), len(doc["findings"]))
check("github: never ::error (advisory)", "::error" in out, False)
rc, out = run([os.path.join(FIX, "sloppy"), "--format", "markdown"])
check("markdown: a table row per finding", out.count("\n| ") - 1, len(doc["findings"]))

summary = sc.summarize([], 3)
check("triage: nothing found → none", summary["level"], "none")
light = [{"group": "copy", "path": "a"}, {"group": "copy", "path": "a"}]
check("triage: few signs in few passes → light", sc.summarize(light, 1)["level"], "light")

# ── a broken catalogue or git failure is exit 2, never a clean report ───────────────
with tempfile.TemporaryDirectory() as d:
    bad = os.path.join(d, "bad.yml")
    open(bad, "w").write("signs:\n  - id: x\n    group: copy\n    pattern: '(unclosed'\n    sign: s\n    fix: f\n")
    rc, _ = run([FIX, "--config", bad])
    check("invalid regex in the catalogue → exit 2", rc, 2)
    rc, _ = run([FIX, "--config", os.path.join(d, "missing.yml")])
    check("missing catalogue → exit 2", rc, 2)

    # --diff-base: only changed, still-present UI files are scanned
    def git(*a):
        subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)
    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    open(os.path.join(d, "Old.tsx"), "w").write('<p className="mt-[13px]">x</p>\n')
    git("add", ".")
    git("commit", "-q", "-m", "base")
    open(os.path.join(d, "New.tsx"), "w").write("<p>Go!</p>\n")
    git("add", ".")
    git("commit", "-q", "-m", "change")
    rc, out = run(["--repo", d, "--diff-base", "HEAD~1", "--json"])
    got = sorted({os.path.basename(f["path"]) for f in json.loads(out)["findings"]})
    check("--diff-base scans only the changed file", got, ["New.tsx"])
    os.makedirs(os.path.join(d, "web"))
    open(os.path.join(d, "web", "Hero.tsx"), "w").write("<p>Hi!</p>\n")
    git("add", ".")
    git("commit", "-q", "-m", "web")
    rc, out = run([os.path.join(d, "web"), "--repo", d, "--diff-base", "HEAD~2", "--json"])
    got = sorted({os.path.basename(f["path"]) for f in json.loads(out)["findings"]})
    check("--diff-base + PATH → changed files under PATH only", got, ["Hero.tsx"])
    rc, _ = run(["--repo", d, "--diff-base", "no-such-ref"])
    check("--diff-base on an unknown ref → exit 2", rc, 2)
    rc, out = run(["--repo", d, "--json"])
    check("no paths → every tracked UI file", json.loads(out)["summary"]["scanned"], 3)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
