#!/usr/bin/env python3
"""Session-injection budget — what the plugin costs before the user types a word.

Claude Code loads every skill, command and agent DESCRIPTION into the session prompt so it
can decide what to invoke. Bodies are read on demand; descriptions are not. With 21 skills,
20 commands and 10 agents, that is a fixed toll paid in every project where the plugin is
enabled — including repos that have nothing to do with WellForge.

Nobody had measured it. This script does, prints the worst offenders, and fails when the
total crosses the ceiling in config/budget.yml so the number can only go down without a
deliberate decision.

TOKENS ARE ESTIMATED at chars/4 — the standard rough ratio for English prose, stated rather
than implied. The real count depends on the tokenizer (and Claude 4.7+ uses a different one
than earlier models). Treat the number as an order of magnitude and the CHARACTER count,
which is exact, as the thing being governed.

Run: uv run --with pyyaml python wellforge-plugin/scripts/check-budget.py [--json]
"""
import argparse
import glob
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
CHARS_PER_TOKEN = 4
HARD_PER_ITEM = 1024          # the loader's own per-description limit


def _description_textually(fm_text):
    """Pull `description:` out of frontmatter that strict YAML rejects.

    Handles both the inline form and the `>`/`|` block form, which is what the longer
    skill descriptions use.
    """
    lines = fm_text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line[len("description:"):].strip()
        if rest and rest not in (">", "|", ">-", "|-"):
            return rest
        out = []
        for cont in lines[i + 1:]:
            if cont.strip() and not cont.startswith((" ", "\t")):
                break
            out.append(cont.strip())
        return " ".join(out)
    return ""


def descriptions():
    out = []
    for kind, pattern, namer in (
        ("skill", f"{PLUGIN}/skills/*/SKILL.md", lambda p: os.path.basename(os.path.dirname(p))),
        ("command", f"{PLUGIN}/commands/*.md", lambda p: os.path.basename(p)[:-3]),
        ("agent", f"{PLUGIN}/agents/*.md", lambda p: os.path.basename(p)[:-3]),
    ):
        for path in sorted(glob.glob(pattern)):
            body = open(path, encoding="utf-8").read()
            if not body.startswith("---"):
                continue
            fm_text = body.split("---", 2)[1]
            try:
                fm = yaml.safe_load(fm_text) or {}
                desc = fm.get("description") or ""
            except Exception:  # noqa: BLE001
                # Command frontmatter is NOT strict YAML — `argument-hint: [feature] [--flag]`
                # is a valid Claude Code hint and an invalid YAML flow sequence, and the
                # loader is lenient about it. Parsing strictly here silently skipped 14 of
                # 20 commands and under-counted the budget by a third, which is the wrong
                # way for a measurement to fail. Fall back to reading the field textually,
                # the way the thing being measured does.
                desc = _description_textually(fm_text)
            desc = " ".join(str(desc).split())
            out.append({"kind": kind, "name": namer(path), "path": os.path.relpath(path, PLUGIN),
                        "chars": len(desc), "tokens": round(len(desc) / CHARS_PER_TOKEN)})
    return out


def load_budget():
    p = os.path.join(PLUGIN, "config", "budget.yml")
    if not os.path.exists(p):
        return None
    return yaml.safe_load(open(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=12, help="rows to print (0 = all)")
    args = ap.parse_args()

    items = sorted(descriptions(), key=lambda d: -d["chars"])
    total_chars = sum(d["chars"] for d in items)
    total_tokens = round(total_chars / CHARS_PER_TOKEN)
    budget = load_budget()
    ceiling = (budget or {}).get("session_injection", {}).get("max_chars")

    if args.json:
        print(json.dumps({"total_chars": total_chars, "total_tokens_est": total_tokens,
                          "ceiling_chars": ceiling, "chars_per_token": CHARS_PER_TOKEN,
                          "items": items}, indent=2))
    else:
        shown = items if args.top == 0 else items[:args.top]
        print(f"{'KIND':9} {'NAME':24} {'CHARS':>6} {'~TOK':>6}")
        for d in shown:
            flag = "  ← over 1024" if d["chars"] > HARD_PER_ITEM else ""
            print(f"{d['kind']:9} {d['name']:24} {d['chars']:>6} {d['tokens']:>6}{flag}")
        if args.top and len(items) > args.top:
            print(f"{'…':9} {len(items) - args.top} more")
        by_kind = {}
        for d in items:
            by_kind.setdefault(d["kind"], [0, 0])
            by_kind[d["kind"]][0] += 1
            by_kind[d["kind"]][1] += d["chars"]
        print()
        for kind, (n, c) in sorted(by_kind.items()):
            print(f"  {kind + 's':10} {n:>3} items  {c:>6} chars  ~{round(c / CHARS_PER_TOKEN):>5} tokens")
        print(f"  {'TOTAL':10} {len(items):>3} items  {total_chars:>6} chars  ~{total_tokens:>5} tokens"
              f"  (injected into EVERY session, every project)")
        if ceiling:
            pct = round(total_chars / ceiling * 100)
            print(f"  {'CEILING':10}              {ceiling:>6} chars  ({pct}% used)")

    fail = []
    for d in items:
        if d["chars"] > HARD_PER_ITEM:
            fail.append(f"{d['kind']} `{d['name']}` description is {d['chars']} chars (limit {HARD_PER_ITEM})")
    if ceiling and total_chars > ceiling:
        fail.append(f"session injection is {total_chars} chars, over the {ceiling}-char ceiling "
                    f"in config/budget.yml by {total_chars - ceiling}. Shrink a description "
                    f"(/wellforge:terse-compress) or raise the ceiling deliberately, in its own commit.")
    if ceiling is None:
        print("\nnote: config/budget.yml has no session_injection.max_chars — nothing enforced", file=sys.stderr)

    if fail:
        print("\n✗ budget:", file=sys.stderr)
        for f in fail:
            print(f"    {f}", file=sys.stderr)
        return 1
    if not args.json:
        print("\n✓ within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
