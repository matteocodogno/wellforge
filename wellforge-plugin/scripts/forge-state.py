#!/usr/bin/env python3
"""WellForge feature state — deterministic, machine-readable, one pass over specs/.

  forge-state.py [--specs-dir specs] [--runs-dir .forge/runs] [--feature NNN-slug] [--json]

WHY THIS EXISTS
/wellforge:status, :triage, :done and :promote each used to have the MODEL read every
spec's frontmatter, count checkboxes in tasks.md, and call run-report.py to find verdicts —
four re-derivations of the same state, on every heartbeat. That is slow, costs tokens for
work a loop does better, cannot be unit-tested, and silently tolerates `status: doen`
(a typo the model reads as "done-ish" and a schema rejects outright). The heartbeat skill
already draws the line this script implements: discovery is deterministic, only judgment
is agentic.

Everything here is mechanical. Nothing in this file decides whether work is GOOD — it
reports what is on disk: statuses, counts, dates, verdicts, and whether the tier's done
gate is met. The prose, the triage narrative and every judgment stay with the model.

Pure stdlib except pyyaml for frontmatter (optional, like run-report.py — without it the
script still runs and says which features it could not parse, rather than guessing).
Run-trace loading is imported from run-report.py, never reimplemented.
"""
import argparse
import datetime
import glob
import importlib.util
import json
import os
import re
import subprocess
import sys

SCHEMA_VERSION = "forge-state/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)


# ── loaders shared with run-report.py (one implementation, not two) ──────────────
def _run_report():
    spec = importlib.util.spec_from_file_location("run_report", os.path.join(HERE, "run-report.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_schema():
    p = os.path.join(PLUGIN, "config", "spec-frontmatter.schema.json")
    try:
        return json.load(open(p))
    except Exception:  # noqa: BLE001 — a missing schema disables validation, never the report
        return None


# ── frontmatter ──────────────────────────────────────────────────────────────────
def read_frontmatter(path):
    """Return (dict, error). Missing file → (None, None): absence is not an error here."""
    if not os.path.exists(path):
        return None, None
    text = open(path, encoding="utf-8", errors="replace").read()
    if not text.startswith("---"):
        return {}, "no frontmatter block"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, "unterminated frontmatter block"
    try:
        import yaml
    except ImportError:
        return {}, "pyyaml unavailable — frontmatter not parsed"
    try:
        data = yaml.safe_load(parts[1]) or {}
    except Exception as e:  # noqa: BLE001
        return {}, f"unparseable YAML ({e})"
    if not isinstance(data, dict):
        return {}, "frontmatter is not a mapping"
    # YAML turns 2026-06-04 into a date and 003 into an int; normalise for comparison.
    return {k: (v.isoformat() if isinstance(v, (datetime.date, datetime.datetime)) else v)
            for k, v in data.items()}, None


def validate(fm, artifact, schema):
    """Minimal JSON-Schema subset — enums, required, patterns, the three conditionals.

    Deliberately not a full validator and deliberately not a dependency: the schema file is
    small and fixed, and a `pip install jsonschema` between an agent and its own status
    command is a worse trade than 40 lines.
    """
    problems = []
    if not schema or fm is None:
        return problems
    spec = schema.get("artifacts", {}).get(artifact)
    if not spec:
        return problems
    defs = schema.get("$defs", {})

    def resolve(node):
        ref = node.get("$ref")
        if ref and ref.startswith("#/$defs/"):
            return defs.get(ref.split("/")[-1], {})
        return node

    for key in spec.get("required", []):
        if key not in fm:
            problems.append(f"{artifact}: missing required `{key}`")
    for key, raw in spec.get("properties", {}).items():
        if key not in fm:
            continue
        rule = resolve(raw)
        val = fm[key]
        if "enum" in rule and val not in rule["enum"]:
            problems.append(f"{artifact}: `{key}: {val}` is not one of {rule['enum']}")
        if "const" in rule and val != rule["const"]:
            problems.append(f"{artifact}: `{key}` must be `{rule['const']}`, got `{val}`")
        if "pattern" in rule and isinstance(val, str) and not re.match(rule["pattern"], val):
            problems.append(f"{artifact}: `{key}: {val}` does not match {rule['pattern']}")
        if rule.get("minLength") and isinstance(val, str) and len(val) < rule["minLength"]:
            problems.append(f"{artifact}: `{key}` is empty")
    for cond in spec.get("allOf", []):
        want = cond.get("if", {}).get("properties", {})
        if all(fm.get(k) == v.get("const") for k, v in want.items()):
            for key in cond.get("then", {}).get("required", []):
                if key not in fm:
                    problems.append(f"{artifact}: `status: {list(want.values())[0]['const']}` "
                                    f"requires `{key}` ({cond.get('description','')})".rstrip())
    return problems


# ── tasks ────────────────────────────────────────────────────────────────────────
TASK_LINE = re.compile(r"^\s*-\s*\[( |x|X)\]\s")


def count_tasks(path):
    if not os.path.exists(path):
        return {"total": 0, "checked": 0, "present": False}
    total = checked = 0
    body = open(path, encoding="utf-8", errors="replace").read()
    # Skip the frontmatter so an `- [ ]` inside it is never a task.
    if body.startswith("---"):
        body = body.split("---", 2)[-1]
    for line in body.splitlines():
        m = TASK_LINE.match(line)
        if m:
            total += 1
            if m.group(1).lower() == "x":
                checked += 1
    return {"total": total, "checked": checked, "present": True}


# ── drift ────────────────────────────────────────────────────────────────────────
def last_change(path, repo):
    """(display date, clock) for the last change to a path. git first, mtime as fallback.

    git is the honest clock: a fresh checkout gives every file the same mtime, so mtime
    alone reports either everything drifted or nothing.
    """
    try:
        out = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%cI", "--", path],
                             capture_output=True, text=True, timeout=10)
        stamp = out.stdout.strip()
        if stamp:
            return stamp[:19].replace("T", " "), "git"
    except Exception:  # noqa: BLE001
        pass
    if os.path.exists(path):
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"), "mtime"
    return None, None


def _commit_order(repo):
    """{commit sha: index}, 0 = newest. Commit ORDER, not commit date, decides recency.

    Dates are second-granular, so two commits made in the same second tie — and a tie reads
    as "not drifted", which is the wrong way to be wrong. Order is exact and is what the
    history actually means. Same-commit changes still tie, correctly: amending a spec and
    re-syncing its tasks together is not drift.
    """
    try:
        out = subprocess.run(["git", "-C", repo, "rev-list", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return {sha: i for i, sha in enumerate(out.stdout.split())}
    except Exception:  # noqa: BLE001
        return {}


def _last_commit(path, repo):
    try:
        out = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%H", "--", path],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def _newer(a_path, b_path, repo, order):
    """Is a_path's last change strictly newer than b_path's? None when undecidable."""
    a, b = _last_commit(a_path, repo), _last_commit(b_path, repo)
    if a and b and a in order and b in order:
        if a == b:
            return False                      # same commit → changed together, not drift
        return order[a] < order[b]            # smaller index = newer
    # Uncommitted or non-git: fall back to mtime, which is all there is.
    if os.path.exists(a_path) and os.path.exists(b_path):
        return os.path.getmtime(a_path) > os.path.getmtime(b_path)
    return None


def compute_drift(d, repo):
    """spec.md or plan.md newer than tasks.md → the task list no longer reflects the spec."""
    tasks = os.path.join(d, "tasks.md")
    if not os.path.exists(tasks):
        return {"drifted": False, "reason": None, "sources": []}
    t_when, t_src = last_change(tasks, repo)
    order = _commit_order(repo)
    sources = []
    for name in ("spec.md", "plan.md"):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            continue
        if _newer(p, tasks, repo, order):
            w, src = last_change(p, repo)
            sources.append({"artifact": name, "changed": w, "clock": src})
    return {
        "drifted": bool(sources),
        "reason": ("newer than tasks.md: " + ", ".join(s["artifact"] for s in sources)) if sources else None,
        "tasks_synced": t_when, "clock": t_src, "sources": sources,
    }


# ── verdicts ─────────────────────────────────────────────────────────────────────
def latest_verdicts(runs, rr):
    """Newest QE and eval verdict for a feature, from its run traces."""
    out = {"qe": {"verdict": None, "at": None, "run_id": None},
           "security": {"verdict": None, "at": None, "run_id": None},
           "eval": {"verdict": None, "at": None, "run_id": None, "score": None}}
    for r in sorted(runs, key=lambda r: r.get("finished") or r.get("started") or ""):
        v = r.get("verdicts") or {}
        when = r.get("finished") or r.get("started")
        if v.get("qe"):
            out["qe"] = {"verdict": v["qe"], "at": when, "run_id": r.get("run_id")}
        if v.get("security"):
            out["security"] = {"verdict": v["security"], "at": when, "run_id": r.get("run_id")}
        if v.get("eval"):
            score = next((a.get("score") for a in r.get("agents", []) if a.get("score") is not None), None)
            out["eval"] = {"verdict": v["eval"], "at": when, "run_id": r.get("run_id"), "score": score}
    return out


# ── tier + gate ──────────────────────────────────────────────────────────────────
def project_default_tier(root):
    for name in ("manifest.json", "adoption.json"):
        p = os.path.join(root, ".forge", name)
        if os.path.exists(p):
            try:
                t = json.load(open(p)).get("rigor")
                if t:
                    return t, f".forge/{name}"
            except Exception:  # noqa: BLE001
                pass
    return "production", "default"


def resolve_tier(fm, root):
    """Precedence per the rigor-tiers skill, minus --mode (a per-run flag, not state)."""
    if fm and fm.get("rigor"):
        return fm["rigor"], "frontmatter"
    return project_default_tier(root)


def done_gate(kind, tier, tasks, verdicts, has_eval_report, eval_fm, drift):
    """The tier-aware gate from /wellforge:done, computed once so four commands agree."""
    failing = []
    if kind == "spike":
        # A spike closes on its brief's findings; nothing here can verify prose, so the
        # gate reports what it CAN check and leaves the judgement to the human.
        return {"tier": "spike", "passes": None, "failing": [],
                "note": "spike closes on brief.md `## Findings` — not machine-checkable"}
    if not tasks["present"]:
        failing.append("no tasks.md")
    elif tasks["checked"] < tasks["total"]:
        failing.append(f"{tasks['total'] - tasks['checked']} of {tasks['total']} tasks unchecked")
    if tasks["present"] and tasks["total"] == 0:
        failing.append("tasks.md has no tasks")
    if verdicts["qe"]["verdict"] != "PASS":
        failing.append(f"QE verdict is {verdicts['qe']['verdict'] or 'absent'} (needs PASS)")
    if tier == "production":
        # Every production batch is reviewed (config/security-triggers.yml always_at_tier),
        # so an ABSENT security verdict here means the review never ran — not that it was
        # unnecessary. A feature can pass every test and still ship an unreviewed auth change.
        if verdicts["security"]["verdict"] != "PASS":
            failing.append(f"security review is "
                           f"{verdicts['security']['verdict'] or 'absent'} (needs PASS at production)")
        if not has_eval_report:
            failing.append("no eval-report.md (needs a PASS)")
        elif (eval_fm or {}).get("verdict") != "PASS":
            failing.append(f"eval-report.md verdict is {(eval_fm or {}).get('verdict') or 'absent'} (needs PASS)")
    if drift.get("drifted"):
        failing.append(f"drift: {drift['reason']} — re-sync with /wellforge:tasks")
    return {"tier": tier, "passes": not failing, "failing": failing}


# ── main ─────────────────────────────────────────────────────────────────────────
def build(specs_dir, runs_dir, feature_filter, root):
    rr = _run_report()
    schema = load_schema()
    all_runs = rr.load_runs(runs_dir, "") if os.path.isdir(runs_dir) else []
    features = []

    for d in sorted(glob.glob(os.path.join(specs_dir, "*/"))):
        slug = os.path.basename(d.rstrip("/"))
        if feature_filter and feature_filter not in slug:
            continue
        spec_fm, spec_err = read_frontmatter(os.path.join(d, "spec.md"))
        brief_fm, brief_err = read_frontmatter(os.path.join(d, "brief.md"))
        if spec_fm is None and brief_fm is None:
            continue                                  # not a feature directory; ignore silently
        kind = "feature" if spec_fm is not None else "spike"
        fm = spec_fm if kind == "feature" else brief_fm
        artifact = "spec.md" if kind == "feature" else "brief.md"

        problems = [f"{artifact}: {e}" for e in ([spec_err] if spec_err else []) + ([brief_err] if brief_err else [])]
        problems += validate(fm, artifact, schema)

        plan_fm, plan_err = read_frontmatter(os.path.join(d, "plan.md"))
        design_fm, design_err = read_frontmatter(os.path.join(d, "design.md"))
        tasks_fm, tasks_err = read_frontmatter(os.path.join(d, "tasks.md"))
        eval_fm, eval_err = read_frontmatter(os.path.join(d, "eval-report.md"))
        for name, sub_fm, err in (("plan.md", plan_fm, plan_err), ("design.md", design_fm, design_err),
                                  ("tasks.md", tasks_fm, tasks_err), ("eval-report.md", eval_fm, eval_err)):
            if err:
                problems.append(f"{name}: {err}")
            problems += validate(sub_fm, name, schema)

        tier, tier_from = resolve_tier(fm, root)
        tasks = count_tasks(os.path.join(d, "tasks.md"))
        drift = compute_drift(d, root)
        runs = [r for r in all_runs if (r.get("feature") or "") == slug]
        verdicts = latest_verdicts(runs, rr)
        status = (fm or {}).get("status")

        features.append({
            "slug": slug, "kind": kind, "status": status,
            "rigor": tier, "rigor_from": tier_from,
            "terminal": status in ("done", "superseded", "archived"),
            "artifacts": {
                "spec": spec_fm is not None, "brief": brief_fm is not None,
                "plan": plan_fm is not None, "plan_status": (plan_fm or {}).get("status"),
                "design": design_fm is not None, "tasks": tasks["present"],
                "eval_report": eval_fm is not None,
            },
            "tasks": {"total": tasks["total"], "checked": tasks["checked"]},
            "drift": drift,
            "verdicts": verdicts,
            "done_gate": done_gate(kind, tier, tasks, verdicts, eval_fm is not None, eval_fm, drift),
            "superseded_by": (fm or {}).get("superseded_by"),
            "archive_reason": (fm or {}).get("archive_reason"),
            "created": (fm or {}).get("created"),
            "last_activity": last_change(d, root)[0],
            "runs": len(runs),
            "problems": problems,
        })
    return {"version": SCHEMA_VERSION,
            "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "specs_dir": specs_dir, "runs_dir": runs_dir,
            "runs_available": os.path.isdir(runs_dir),
            "features": features}


def render(env):
    feats = env["features"]
    if not feats:
        print(f"No features found in {env['specs_dir']}/")
        return
    print(f"{'FEATURE':30} {'KIND':8} {'STATUS':12} {'TIER':11} {'TASKS':>8}  {'QE':6} {'EVAL':6} GATE")
    for f in feats:
        t = f["tasks"]
        tasks = f"{t['checked']}/{t['total']}" if t["total"] else "—"
        g = f["done_gate"]
        gate = "n/a" if g["passes"] is None else ("PASS" if g["passes"] else "blocked")
        print(f"{f['slug']:30} {f['kind']:8} {str(f['status']):12} {f['rigor']:11} {tasks:>8}  "
              f"{str(f['verdicts']['qe']['verdict'] or '—'):6} {str(f['verdicts']['eval']['verdict'] or '—'):6} {gate}")
        if f["drift"]["drifted"]:
            print(f"{'':30} ⚠ drift: {f['drift']['reason']}")
        for p in f["problems"]:
            print(f"{'':30} ✗ {p}")
        if not g["passes"] and g["passes"] is not None and f["status"] not in ("done", "superseded", "archived"):
            for reason in g["failing"]:
                print(f"{'':30} · gate: {reason}")
    if not env["runs_available"]:
        print(f"\nnote: {env['runs_dir']} not found — QE/eval verdicts unavailable (not the same as FAIL)")
    bad = sum(len(f["problems"]) for f in feats)
    if bad:
        print(f"\n{bad} schema problem(s) — frontmatter does not match "
              f"config/spec-frontmatter.schema.json (the spec-driven skill is the authority)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs-dir", default="specs")
    ap.add_argument("--runs-dir", default=os.path.join(".forge", "runs"))
    ap.add_argument("--feature", default=None)
    ap.add_argument("--root", default=".", help="project root (for .forge/ and git dates)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    env = build(args.specs_dir, args.runs_dir, args.feature, args.root)
    if args.json:
        print(json.dumps(env, indent=2))
    else:
        render(env)
    # Exit 0 always: this reports state, it does not gate. A non-zero here would make every
    # consumer treat "a spec has a typo" as "the tool failed".
    return 0


if __name__ == "__main__":
    sys.exit(main())
