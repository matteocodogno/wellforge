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
def _utc(dt):
    """A timezone-aware datetime → `YYYY-MM-DDTHH:MM:SSZ`. One format, one zone.

    Timestamps used to be emitted in whatever zone the machine happened to be in, with no
    marker saying which — so two people comparing the same feature's `last_activity` could
    read times an hour apart and neither could tell. Everything this script prints is UTC
    and says so.
    """
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mtime_utc(path):
    return _utc(datetime.datetime.fromtimestamp(os.path.getmtime(path), datetime.timezone.utc))


_DIRTY_CACHE = {}


def dirty_paths(repo):
    """Repo-relative paths git reports as modified/untracked.

    Cached for the duration of ONE build() — `git status` is called for every path
    comparison otherwise. The cache is cleared at the start of each build rather than
    living for the process, because this module is imported and called repeatedly by the
    test suite and by other tools: a process-lifetime cache answered the second call with
    the first call's working tree, which is exactly the staleness this function exists to
    detect.

    This is the fix for a drift check that could not see the thing most likely to have
    changed: the working tree. `_newer` compared LAST-COMMIT times, so an uncommitted edit
    to spec.md reported no drift (its commit is old), and an uncommitted re-sync of tasks.md
    still reported drift (same reason, other direction). Both wrong, and wrong in the
    direction that says "nothing to do".
    """
    if repo in _DIRTY_CACHE:
        return _DIRTY_CACHE[repo]
    out = set()
    try:
        r = subprocess.run(["git", "-C", repo, "status", "--porcelain", "-z", "--untracked-files=all"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for entry in r.stdout.split("\0"):
                if len(entry) > 3:
                    out.add(entry[3:])
    except Exception:  # noqa: BLE001
        pass
    _DIRTY_CACHE[repo] = out
    return out


def _rel(path, repo):
    """Repo-relative, slash-separated, symlink-resolved on BOTH sides.

    `compute_drift` passes a RELATIVE path (`specs/001-x/spec.md`), so `os.path.abspath`
    resolved it against the process cwd — which the OS reports symlink-resolved — while
    `repo` was whatever string the caller passed, unresolved. On macOS `mktemp -d` returns
    `/var/folders/...`, a symlink to `/private/var/folders/...`, so the two never matched,
    `_is_dirty` returned False for every file, and the entire dirty-drift path was dead.
    Its own test suite passed for that reason, which is why the regression below shipped
    and only the first Linux CI run found it.
    """
    try:
        return os.path.relpath(os.path.realpath(path), os.path.realpath(repo)).replace(os.sep, "/")
    except Exception:  # noqa: BLE001
        return None


def _is_dirty(path, repo):
    """Does git consider this path modified or untracked?"""
    rel = _rel(path, repo)
    return bool(rel) and rel in dirty_paths(repo)


# Frontmatter fields that record where a feature IS in its lifecycle, not what it asks for.
# Editing one of these is bookkeeping — /wellforge:done writes `status` + `done`,
# /wellforge:promote writes `rigor` — and bookkeeping is not a requirement change, so it
# must not read as drift. Anything else in the frontmatter (a changed `title`, say) is a
# change to the spec and is treated exactly like a body change.
LIFECYCLE_FIELDS = frozenset({"status", "done", "approved", "superseded_by",
                              "archive_reason", "rigor", "plugin"})


def _split_frontmatter(text):
    """(frontmatter, body). No frontmatter block → ("", whole text)."""
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    return (parts[1], parts[2]) if len(parts) >= 3 else ("", text)


def _fm_fields(fm_text):
    """Top-level `key: value` pairs. Line-based on purpose: this runs without pyyaml (the
    script degrades to a warning when pyyaml is missing) and must not start needing it."""
    out = {}
    for line in fm_text.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def _head_text(path, repo):
    """The committed version of a path, or None when there is no HEAD version."""
    rel = _rel(path, repo)
    if not rel:
        return None
    try:
        out = subprocess.run(["git", "-C", repo, "show", f"HEAD:{rel}"],
                             capture_output=True, text=True, timeout=10)
    except Exception:  # noqa: BLE001
        return None
    return out.stdout if out.returncode == 0 else None


_CLASS_CACHE = {}


def change_class(path, repo):
    """How has this file changed against HEAD? One of:

      clean       — git sees no change (or only changes that mean nothing here)
      lifecycle   — body identical, and ONLY lifecycle frontmatter fields differ
      content     — the body differs, or a non-lifecycle frontmatter field differs
      untracked   — dirty with no HEAD version to compare against

    Only `content` and `untracked` are drift. `lifecycle` is the fix for the regression
    this function exists for: writing `status: done` into spec.md is the LAST thing
    /wellforge:done does, so under a plain mtime rule spec.md was always newer than
    tasks.md and every close reported drift — the done gate refused the transition it had
    just performed, and post-spec-guard.sh blocked it.
    """
    key = (os.path.realpath(path) if os.path.exists(path) else path, repo)
    if key in _CLASS_CACHE:
        return _CLASS_CACHE[key]
    res = _change_class(path, repo)
    _CLASS_CACHE[key] = res
    return res


def _change_class(path, repo):
    if not _is_dirty(path, repo):
        return "clean"
    head = _head_text(path, repo)
    if head is None:
        # No baseline exists, so "newer than tasks.md" is the only honest answer.
        return "untracked"
    try:
        now = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return "content"
    fm_head, body_head = _split_frontmatter(head)
    fm_now, body_now = _split_frontmatter(now)
    if body_head != body_now:
        return "content"
    a, b = _fm_fields(fm_head), _fm_fields(fm_now)
    changed = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
    if not changed:
        return "clean"
    return "lifecycle" if changed <= LIFECYCLE_FIELDS else "content"


def last_change(path, repo):
    """(UTC timestamp, clock) for the last change to a path. git first, mtime as fallback.

    git is the honest clock for COMMITTED files: a fresh checkout gives every file the same
    mtime, so mtime alone reports either everything drifted or nothing. A file with
    uncommitted CONTENT changes is younger than its last commit, and for that one mtime is
    the only clock that knows.

    A `lifecycle` change deliberately reads from git, not mtime: the committed change time
    is still the last time the spec's requirements moved, which is the question drift asks.
    The clock says which rule answered — `mtime-dirty`, `mtime-untracked` or `git`.
    """
    cls = change_class(path, repo)
    if cls in ("content", "untracked") and os.path.exists(path):
        return _mtime_utc(path), ("mtime-untracked" if cls == "untracked" else "mtime-dirty")
    try:
        out = subprocess.run(["git", "-C", repo, "log", "-1", "--format=%cI", "--", path],
                             capture_output=True, text=True, timeout=10)
        stamp = out.stdout.strip()
        if stamp:
            try:
                return _utc(datetime.datetime.fromisoformat(stamp)), "git"
            except ValueError:
                return stamp[:19] + "Z", "git"
    except Exception:  # noqa: BLE001
        pass
    if os.path.exists(path):
        return _mtime_utc(path), "mtime"
    return None, None


# Directories never worth walking for a "last change" answer.
_SKIP_DIRS = {".git", "node_modules", "target", "dist", "build", ".venv", "venv",
              "__pycache__", ".mypy_cache", ".pytest_cache", ".gradle", ".idea", "coverage"}


def _max_mtime(root, skip_rel=()):  # noqa: C901
    """Newest mtime under `root`, skipping build output and the given relative subtrees.

    A DIRECTORY's mtime only moves when an entry is added or removed, so `getmtime(dir)`
    answers "when was a file last created here", not "when was this feature last touched" —
    editing spec.md in place left last_activity frozen at the day the directory was made.
    """
    newest = None
    skip_abs = {os.path.abspath(os.path.join(root, p)) for p in skip_rel}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in _SKIP_DIRS
                       and os.path.abspath(os.path.join(dirpath, d)) not in skip_abs]
        for fn in filenames:
            try:
                m = os.path.getmtime(os.path.join(dirpath, fn))
            except OSError:
                continue
            if newest is None or m > newest:
                newest = m
    return newest


def last_activity(path, repo):
    """When was this feature last touched? Falls back to the newest FILE mtime, not the
    directory's own — see _max_mtime."""
    when, clock = last_change(path, repo)
    # In a git repo an uncommitted edit inside the directory is not visible from the
    # directory's own log, so take the newer of (directory log, newest dirty file inside).
    newest_dirty = None
    for rel in dirty_paths(repo):
        ap = os.path.abspath(os.path.join(repo, rel))
        if ap.startswith(os.path.abspath(path) + os.sep) and os.path.exists(ap):
            m = os.path.getmtime(ap)
            newest_dirty = m if newest_dirty is None or m > newest_dirty else newest_dirty
    if newest_dirty is not None:
        cand = _utc(datetime.datetime.fromtimestamp(newest_dirty, datetime.timezone.utc))
        if when is None or cand > when:
            return cand, "mtime-dirty"
    if when is not None:
        return when, clock
    m = _max_mtime(path)
    if m is not None:
        return _utc(datetime.datetime.fromtimestamp(m, datetime.timezone.utc)), "mtime"
    return None, None


def last_code_change(repo, specs_dir):
    """(UTC timestamp, clock) of the newest change to CODE — everything outside specs/ and
    .forge/. This is what makes an eval verdict stale: the report judged a tree that has
    since moved on.

    Nothing computed this before, although /wellforge:done listed "eval not stale" as a
    condition — so the condition was documentation only, and an eval-report.md from before
    a rewrite still counted as a PASS.
    """
    rel_specs = os.path.basename(specs_dir.rstrip("/")) or "specs"
    # Dirty files win: an uncommitted code change is the newest thing there is.
    newest_dirty = None
    for rel in dirty_paths(repo):
        top = rel.split("/", 1)[0]
        if top in (rel_specs, ".forge") or top in _SKIP_DIRS:
            continue
        ap = os.path.join(repo, rel)
        if os.path.exists(ap):
            m = os.path.getmtime(ap)
            newest_dirty = m if newest_dirty is None or m > newest_dirty else newest_dirty
    if newest_dirty is not None:
        return _utc(datetime.datetime.fromtimestamp(newest_dirty, datetime.timezone.utc)), "mtime-dirty"
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%cI", "--",
             ".", f":(exclude){rel_specs}", ":(exclude).forge"],
            capture_output=True, text=True, timeout=10)
        stamp = out.stdout.strip()
        if stamp:
            try:
                return _utc(datetime.datetime.fromisoformat(stamp)), "git"
            except ValueError:
                return stamp[:19] + "Z", "git"
    except Exception:  # noqa: BLE001
        pass
    m = _max_mtime(repo, skip_rel=(rel_specs, ".forge"))
    if m is not None:
        return _utc(datetime.datetime.fromtimestamp(m, datetime.timezone.utc)), "mtime"
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
    """Is a_path's last change strictly newer than b_path's? None when undecidable.

    If EITHER file has uncommitted changes, commit order cannot answer the question — the
    dirty file's real age is its mtime and its commit is stale — so both sides fall back to
    mtime. Without this, an uncommitted spec edit reported no drift and an uncommitted
    tasks re-sync still reported drift.
    """
    # Only a REAL change (new content, or a file with no committed baseline) makes mtime
    # the better clock. A lifecycle-only edit leaves commit order in charge, which is what
    # keeps closing a feature from counting as drift against its own task list.
    if change_class(a_path, repo) in ("content", "untracked") \
       or change_class(b_path, repo) in ("content", "untracked"):
        if os.path.exists(a_path) and os.path.exists(b_path):
            return os.path.getmtime(a_path) > os.path.getmtime(b_path)
        return None
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
# The only two values a verdict may hold. The comparison in done_gate is `!= "PASS"`, so
# ANY other string fails the gate — including `"pass"` and the owasp-reviewer's own
# `"PASS WITH NOTES"`, which is a pass in the agent's vocabulary and a blocked close here.
# The mapping belongs to the producer (agents/owasp-reviewer.md); this script's job is to
# make a violation legible instead of letting it surface as an unexplained refusal.
VERDICT_VALUES = ("PASS", "FAIL")


def verdict_problems(verdicts):
    """Verdict values that are neither PASS, FAIL, nor absent."""
    out = []
    for name, v in verdicts.items():
        got = v.get("verdict")
        if got is None or got in VERDICT_VALUES:
            continue
        out.append(f"verdicts.{name} is {got!r} in run {v.get('run_id')} — the trace field "
                   f"holds {' or '.join(VERDICT_VALUES)} (case-sensitive) and anything else "
                   f"fails the gate. See agents/owasp-reviewer.md for the mapping.")
    return out


def latest_verdicts(runs, rr):
    """Newest QE and eval verdict for a feature, from its run traces.

    `null` and an absent key are treated identically on purpose: `implement.md` used to
    prescribe `null` for "not dispatched" while the observability skill prescribed absence,
    and this falsy test is why nobody noticed for so long. Absence is now the documented
    rule; this keeps reading old traces that wrote `null`.
    """
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


# THE done gate. Four documents used to state it and no two agreed: this function checked
# tasks + QE + security + eval + drift; commands/done.md added "eval not stale" that nothing
# computed; the spec-driven skill listed tasks + QE + fresh eval with no security and no
# drift; rigor-tiers never mentioned security at all; and commands/status.md omitted
# verdicts.security from its envelope, so status printed "→ /wellforge:done" for a feature
# that /wellforge:done then refused on "security review is absent".
#
# This function is now the single definition, and `--explain-gate` prints it so the prose can
# quote the implementation instead of paraphrasing it. If you change a condition here, re-run
# `--explain-gate` and paste the table into the docs that reference it.
GATE_CONDITIONS = [
    ("tasks.md exists",            "every tier", "a feature with no task list has nothing to have finished"),
    ("every task checked",         "every tier", "unchecked tasks are unfinished work, not optimism"),
    ("tasks.md has >0 tasks",      "every tier", "an empty list passes 'all checked' vacuously"),
    ("verdicts.qe == PASS",        "every tier", "from the run trace — independent verification, not self-report"),
    ("verdicts.security == PASS",  "production", "every production batch is reviewed, so ABSENT means it never ran"),
    ("eval-report.md exists",      "production", "the LM-judge half of verification"),
    ("eval-report.md verdict PASS", "production", "a FAIL or absent verdict is not a pass"),
    ("eval is not stale",          "production", "an eval that predates the last code change judged a different tree"),
    ("no drift",                   "every tier", "spec/plan BODY newer than tasks.md; lifecycle frontmatter edits are not drift"),
]


def explain_gate():
    """Print the gate's conditions. The docs quote THIS, verbatim."""
    print("The /wellforge:done gate — the single definition, from "
          "wellforge-plugin/scripts/forge-state.py `done_gate()`.")
    print()
    print(f"| {'Condition':30} | {'Applies at':11} | Why |")
    print(f"|{'-' * 32}|{'-' * 13}|{'-' * 60}|")
    for cond, tier, why in GATE_CONDITIONS:
        print(f"| {cond:30} | {tier:11} | {why} |")
    print()
    print("`spike` is exempt: a spike closes on prose in brief.md `## Findings`, which no")
    print("script can judge. The gate reports passes=null there, never a false PASS.")
    return 0


def done_gate(kind, tier, tasks, verdicts, has_eval_report, eval_fm, drift, eval_stale=None):
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
        elif eval_stale and eval_stale.get("stale"):
            # done.md has listed this condition for as long as it has existed, and nothing
            # computed it — so a PASS from before a rewrite counted as a PASS.
            failing.append(
                f"eval is stale: eval-report.md ({eval_stale.get('eval_at')}) predates the last "
                f"code change ({eval_stale.get('code_at')}) — re-run /wellforge:eval")
    if drift.get("drifted"):
        failing.append(f"drift: {drift['reason']} — re-sync with /wellforge:tasks")
    return {"tier": tier, "passes": not failing, "failing": failing,
            "eval_stale": eval_stale}


# ── main ─────────────────────────────────────────────────────────────────────────
def _eval_staleness(d, root, specs_dir, has_eval_report):
    """Is eval-report.md older than the newest code change?"""
    if not has_eval_report:
        return None
    eval_at, eval_clock = last_change(os.path.join(d, "eval-report.md"), root)
    code_at, code_clock = last_code_change(root, specs_dir)
    if not eval_at or not code_at:
        return {"stale": None, "eval_at": eval_at, "code_at": code_at,
                "clock": eval_clock or code_clock,
                "note": "undecidable — no clock for one side"}
    return {"stale": code_at > eval_at, "eval_at": eval_at, "code_at": code_at,
            "clock": f"{eval_clock}/{code_clock}"}


def build(specs_dir, runs_dir, feature_filter, root):
    _DIRTY_CACHE.clear()          # see dirty_paths: cached per build, never per process
    _CLASS_CACHE.clear()
    rr = _run_report()
    schema = load_schema()
    # A trace that will not load is reported ONCE, at the top level, not silently dropped:
    # a run that does not load looks exactly like a run that never happened, and its
    # verdicts then read as absent — which is how one malformed file turned into "QE
    # verdict is absent" on a feature that had passed QE.
    rejected = []
    all_runs = rr.load_runs(runs_dir, "", rejected) if os.path.isdir(runs_dir) else []
    problems_global = [f".forge/runs/{w}" for w in rejected]

    # pyyaml is an ENVIRONMENT fact, not a property of any feature. Reported per-feature it
    # put a problem on every one of them, and promote.md refuses on a non-empty problems[] —
    # so a machine without system pyyaml could never promote anything. It is a warning.
    warnings = []
    try:
        import yaml  # noqa: F401
        have_yaml = True
    except ImportError:
        have_yaml = False
        warnings.append("pyyaml unavailable — frontmatter not parsed, so status/rigor/verdict "
                        "fields are unknown (not absent). Re-run with: "
                        "uv run --with pyyaml python <this script>")
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
        # See `warnings` above: the absence of a parser is not a defect in these files.
        if not have_yaml:
            problems = [p for p in problems if "pyyaml unavailable" not in p]

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
            "done_gate": done_gate(kind, tier, tasks, verdicts, eval_fm is not None, eval_fm, drift,
                                   _eval_staleness(d, root, specs_dir, eval_fm is not None)),
            "superseded_by": (fm or {}).get("superseded_by"),
            "archive_reason": (fm or {}).get("archive_reason"),
            "created": (fm or {}).get("created"),
            "last_activity": last_activity(d, root)[0],
            "runs": len(runs),
            "problems": problems + verdict_problems(verdicts),
        })
    return {"version": SCHEMA_VERSION,
            "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "specs_dir": specs_dir, "runs_dir": runs_dir,
            "runs_available": os.path.isdir(runs_dir),
            "problems": problems_global,
            "warnings": warnings,
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
    for p in env.get("problems", []):
        print(f"\n✗ unreadable run trace: {p}")
        print("  Its verdicts are NOT counted, so a gate may read PASS as absent. Fix or delete it.")
    for w in env.get("warnings", []):
        print(f"\n⚠ {w}")
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
    ap.add_argument("--explain-gate", action="store_true",
                    help="print the done-gate conditions (the docs quote this verbatim)")
    args = ap.parse_args()
    if args.explain_gate:
        return explain_gate()
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
