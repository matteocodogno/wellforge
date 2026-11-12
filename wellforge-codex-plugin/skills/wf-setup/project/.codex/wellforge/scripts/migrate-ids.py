#!/usr/bin/env python3
"""Rename legacy sequential ids to date ids — specs/NNN-slug/ and docs/adr/NNNN-title.md.

  migrate-ids.py [--root .] [--specs-dir specs] [--adr-dir docs/adr] [--apply] [--force] [--json]

Dry run by default: prints the plan and changes nothing. `--apply` performs it on a clean
working tree and leaves the result STAGED, not committed, for the caller to review
(`git diff --cached -M`) and commit as one commit of its own
(`refactor: date-based ids for features and ADRs`).

Why a migration exists at all: a sequential NNN collides whenever two people create a feature
(or an ADR) on parallel branches off the same main. New ids are the creation date
(`YYYYMMDD`); see the spec-driven skill. Projects started before 2.62.0 opt into this rename.

What --apply does, in order:
  1. `git mv` every legacy feature dir and ADR to its date id. The date comes from the
     artifact itself (`created:` in spec.md / brief.md, `**Date:**` in an ADR), else from
     the commit that first added it. No date → that item is an error, nothing is applied.
  2. Rewrites references in every tracked text file plus everything under .forge/ (run
     traces are often untracked): the full `NNN-slug` / `NNNN-title` token, the short
     `specs/NNN` commit-convention form, `ADR NNNN`, the `[NNNN]` tag on an AGENTS.md
     decision line, the ADR's own `# NNNN —` heading, and `id:` / `spec:` frontmatter
     inside the feature's own directory.
  3. Records old → new in .forge/id-migration.json — commit messages keep the old ids
     forever, and this is how they are read back.

Refusals (exit 1, nothing changed):
  - two items mapping to the same target, or a target that already exists;
  - --apply on a dirty working tree (the rename must be its own reviewable commit);
  - --apply while a NON-terminal feature has drift or a stale eval, unless --force. The
    rename commit becomes the last change of every artifact it moves, so git can no longer
    tell that spec.md was newer than tasks.md, or that the eval predates the code: the
    migration would silently clear exactly the signals the done gate depends on. Resolve
    them first (re-sync tasks.md, re-run /wellforge:eval), then migrate.

Exit: 0 = planned / applied / nothing to do, 1 = refused.
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys

FEATURE_RE = re.compile(r"^(\d{3})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
ADR_RE = re.compile(r"^(\d{4})-(.+)\.md$")
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
MAP_FILE = os.path.join(".forge", "id-migration.json")
MAX_BYTES = 2 * 1024 * 1024


def git(root, *args):
    out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return out.returncode, out.stdout


def compact(iso):
    m = ISO_DATE.search(str(iso or ""))
    if not m:
        return None
    try:
        datetime.date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None
    return m[1] + m[2] + m[3]


def frontmatter_field(path, key):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    block = text[3:end if end != -1 else len(text)]
    m = re.search(rf"^{re.escape(key)}:\s*['\"]?([^'\"\n#]+)", block, re.M)
    return m[1].strip() if m else None


def first_added(root, rel):
    code, out = git(root, "log", "--reverse", "--format=%cs", "--", rel)
    lines = out.split()
    return compact(lines[0]) if code == 0 and lines else None


# ── plan ─────────────────────────────────────────────────────────────────────────
def plan(root, specs_dir, adr_dir):
    features, adrs, errors = [], [], []
    sd = os.path.join(root, specs_dir)
    if os.path.isdir(sd):
        for name in sorted(os.listdir(sd)):
            m = FEATURE_RE.match(name)
            if not m or not os.path.isdir(os.path.join(sd, name)):
                continue
            rel = os.path.join(specs_dir, name)
            date, src = None, None
            for art in ("spec.md", "brief.md"):
                date = compact(frontmatter_field(os.path.join(sd, name, art), "created"))
                if date:
                    src = f"{art} created:"
                    break
            if not date:
                date, src = first_added(root, rel), "git (first commit)"
            if not date:
                errors.append(f"{rel}: no date — no `created:` in spec.md/brief.md and no commit "
                              f"adds it; add `created: YYYY-MM-DD` to its frontmatter and re-run")
                continue
            features.append({"old": name, "new": f"{date}-{m[2]}", "num": m[1],
                             "id": date, "date_from": src})
    ad = os.path.join(root, adr_dir)
    if os.path.isdir(ad):
        for name in sorted(os.listdir(ad)):
            m = ADR_RE.match(name)
            if not m:
                continue
            path = os.path.join(ad, name)
            rel = os.path.join(adr_dir, name)
            date, src = None, None
            try:
                dm = re.search(r"^\**Date:?\**:?\s*(\d{4}-\d{2}-\d{2})",
                               open(path, encoding="utf-8").read(), re.M | re.I)
            except OSError:
                dm = None
            if dm:
                date, src = compact(dm[1]), "**Date:**"
            if not date:
                date, src = first_added(root, rel), "git (first commit)"
            if not date:
                errors.append(f"{rel}: no date — no `**Date:**` line and no commit adds it")
                continue
            adrs.append({"old": name[:-3], "new": f"{date}-{m[2]}", "num": m[1],
                         "id": date, "date_from": src})

    for kind, items, base in (("feature", features, sd), ("ADR", adrs, ad)):
        seen = {}
        for it in items:
            if it["new"] in seen:
                errors.append(f"{kind} {it['old']} and {seen[it['new']]} both map to {it['new']} — "
                              f"rename one slug by hand first (same date, same name)")
            seen[it["new"]] = it["old"]
            target = os.path.join(base, it["new"] + ("" if kind == "feature" else ".md"))
            if os.path.exists(target):
                errors.append(f"{kind} {it['old']} → {it['new']}: target already exists")
    return features, adrs, errors


# ── preflight ────────────────────────────────────────────────────────────────────
def gate_signals(root, specs_dir):
    """Non-terminal features whose drift / eval staleness the rename would erase."""
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("forge_state", os.path.join(here, "forge-state.py"))
    fs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fs)
    env = fs.build(os.path.join(root, specs_dir), os.path.join(root, ".forge", "runs"), None, root)
    out = []
    for f in env["features"]:
        if f["terminal"] or not FEATURE_RE.match(f["slug"]):
            continue
        why = []
        if (f.get("drift") or {}).get("drifted"):
            why.append("drift (" + f["drift"]["reason"] + ")")
        if ((f.get("done_gate") or {}).get("eval_stale") or {}).get("stale"):
            why.append("stale eval")
        if why:
            out.append(f"{f['slug']}: " + ", ".join(why))
    return out


# ── apply ────────────────────────────────────────────────────────────────────────
def text_files(root):
    code, out = git(root, "ls-files", "-z")
    files = set(out.split("\0")) if code == 0 else set()
    fd = os.path.join(root, ".forge")
    for dp, _, names in os.walk(fd):
        for n in names:
            files.add(os.path.relpath(os.path.join(dp, n), root))
    for rel in sorted(f for f in files if f):
        p = os.path.join(root, rel)
        if not os.path.isfile(p) or os.path.islink(p) or os.path.getsize(p) > MAX_BYTES:
            continue
        try:
            raw = open(p, "rb").read()
            if b"\0" in raw:
                continue
            yield rel, raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def rewrite(text, features, adrs):
    tok = lambda s: rf"(?<![\w-]){re.escape(s)}(?![\w-])"
    for f in features:
        text = re.sub(tok(f["old"]), f["new"], text)
        text = re.sub(rf"(?<![\w-])specs/{f['num']}(?![\w-])", f"specs/{f['new']}", text)
    for a in adrs:
        text = re.sub(tok(a["old"]), a["new"], text)
        text = re.sub(rf"\bADR[ -]{a['num']}\b(?!-)", f"ADR {a['new']}", text)
        # The [NNNN] tag on the AGENTS.md decision line — only on a line that names this ADR.
        text = "\n".join(l.replace(f"[{a['num']}]", f"[{a['id']}]") if a["new"] in l else l
                         for l in text.split("\n"))
    return text


def rewrite_feature_frontmatter(path, f):
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    head, rest = text[:end], text[end:]
    new = re.sub(rf"^(id|spec):[ \t]*['\"]?0*{int(f['num'])}['\"]?[ \t]*$",
                 lambda m: f"{m[1]}: {f['id']}", head, flags=re.M)
    if new != head:
        open(path, "w", encoding="utf-8").write(new + rest)
        return True
    return False


def apply(root, specs_dir, adr_dir, features, adrs):
    for f in features:
        git(root, "mv", os.path.join(specs_dir, f["old"]), os.path.join(specs_dir, f["new"]))
    for a in adrs:
        git(root, "mv", os.path.join(adr_dir, a["old"] + ".md"), os.path.join(adr_dir, a["new"] + ".md"))
    changed = []
    for f in features:
        d = os.path.join(root, specs_dir, f["new"])
        for n in sorted(os.listdir(d)):
            if n.endswith(".md") and rewrite_feature_frontmatter(os.path.join(d, n), f):
                changed.append(os.path.join(specs_dir, f["new"], n))
    for a in adrs:
        p = os.path.join(root, adr_dir, a["new"] + ".md")
        text = open(p, encoding="utf-8").read()
        new = re.sub(rf"^(#\s*){a['num']}\b", rf"\g<1>{a['id']}", text, count=1, flags=re.M)
        if new != text:
            open(p, "w", encoding="utf-8").write(new)
            changed.append(os.path.join(adr_dir, a["new"] + ".md"))
    for rel, text in text_files(root):
        new = rewrite(text, features, adrs)
        if new != text:
            open(os.path.join(root, rel), "w", encoding="utf-8").write(new)
            changed.append(rel)
    mp = os.path.join(root, MAP_FILE)
    record = {"version": 1, "features": {}, "adrs": {}}
    if os.path.exists(mp):
        try:
            record.update(json.load(open(mp)))
        except (OSError, ValueError):
            pass
    record["features"].update({f["old"]: f["new"] for f in features})
    record["adrs"].update({a["old"]: a["new"] for a in adrs})
    record["migrated"] = datetime.date.today().isoformat()
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    with open(mp, "w") as fh:
        json.dump(record, fh, indent=2, sort_keys=True)
        fh.write("\n")
    # Stage the whole migration so `git diff --cached -M` reviews it as one change. Untracked
    # files (an ignored .forge/runs/) are rewritten in place but stay untracked.
    _, tracked = git(root, "ls-files", "-z")
    tracked = set(tracked.split("\0"))
    git(root, "add", "-A", "--", specs_dir, adr_dir, *[c for c in set(changed) if c in tracked])
    git(root, "add", "--", MAP_FILE)  # fails quietly when .forge/ is ignored — that is fine
    return sorted(set(changed))


def leftovers(root, adrs):
    """Bare ADR numbers still in prose — not rewritten, because `0001` alone is ambiguous."""
    out = []
    for rel, text in text_files(root):
        for i, line in enumerate(text.split("\n"), 1):
            for a in adrs:
                if re.search(rf"(?<![\w-]){a['num']}(?![\w-])", line) and re.search(r"adr|decision", line, re.I):
                    out.append(f"{rel}:{i}: {line.strip()[:120]}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--specs-dir", default="specs")
    ap.add_argument("--adr-dir", default=os.path.join("docs", "adr"))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="apply even though a non-terminal feature has drift or a stale eval")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.root)

    features, adrs, errors = plan(root, a.specs_dir, a.adr_dir)
    result = {"features": features, "adrs": adrs, "errors": errors, "applied": False}
    if not errors and a.apply and (features or adrs):
        code, out = git(root, "status", "--porcelain")
        if code != 0:
            errors.append("not a git repository — the rename needs git mv")
        elif out.strip():
            errors.append("working tree is dirty — commit or stash first; the rename must be "
                          "a commit of its own")
        else:
            signals = gate_signals(root, a.specs_dir)
            result["gate_signals"] = signals
            if signals and not a.force:
                errors.append("the rename would erase these done-gate signals (git dates move "
                              "to the rename commit) — resolve them first or pass --force: "
                              + "; ".join(signals))
    if not errors and a.apply and (features or adrs):
        result["changed"] = apply(root, a.specs_dir, a.adr_dir, features, adrs)
        result["leftovers"] = leftovers(root, adrs)
        result["applied"] = True

    if a.json:
        print(json.dumps(result, indent=2))
    else:
        if not features and not adrs and not errors:
            print("nothing to migrate — no legacy NNN- features or NNNN- ADRs")
        for kind, items in (("feature", features), ("ADR", adrs)):
            for it in items:
                print(f"{kind:8} {it['old']}  →  {it['new']}   (date from {it['date_from']})")
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        if result["applied"]:
            print(f"\napplied: {len(features)} feature(s), {len(adrs)} ADR(s); "
                  f"{len(result['changed'])} file(s) rewritten; map in {MAP_FILE}. Not committed.")
            for l in result["leftovers"]:
                print(f"  check by hand (bare ADR number): {l}")
        elif (features or adrs) and not errors:
            print("\ndry run — nothing changed. Re-run with --apply on a clean tree.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
