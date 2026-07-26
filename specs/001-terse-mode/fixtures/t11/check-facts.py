#!/usr/bin/env python3
"""
T11 fixture — AC-4.1 deterministic fact-preservation checker.

Given an explicit fact list (one atomic fact string per line, '#'-comments
and blank lines ignored) and a target file, asserts every fact is still
recoverable as a byte-identical substring of the target. This is the
deterministic half of the AC-4.1 gate described in plan.md's test-strategy
table ("assert fact-set(compressed) ⊇ fact-set(original)") and mirrors what
/wellforge:terse-compress's Step 3 (re-extract and assert no fact was lost)
checks mechanically for facts that are literal spans (thresholds, commands,
paths, identifiers) rather than paraphrasable prose.

Deterministic, stdlib-only, no network calls, no external dependencies.

Usage:
    ./check-facts.py <facts-file> <target-file>

Exit codes:
    0  every fact in <facts-file> is present verbatim in <target-file>
    1  at least one fact is missing (dropped or altered) — prints which
    2  usage/IO error
"""
import sys


def load_facts(path):
    facts = []
    with open(path, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            facts.append(line)
    return facts


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} <facts-file> <target-file>", file=sys.stderr)
        return 2

    facts_path, target_path = argv[1], argv[2]

    try:
        facts = load_facts(facts_path)
    except OSError as exc:
        print(f"FAIL: could not read facts file {facts_path}: {exc}", file=sys.stderr)
        return 2

    if not facts:
        print(f"FAIL: no facts loaded from {facts_path}", file=sys.stderr)
        return 2

    try:
        with open(target_path, encoding="utf-8") as fh:
            target_text = fh.read()
    except OSError as exc:
        print(f"FAIL: could not read target file {target_path}: {exc}", file=sys.stderr)
        return 2

    missing = []
    print(f"Checking {len(facts)} fact(s) against {target_path}:")
    for fact in facts:
        if fact in target_text:
            print(f"  [present] {fact}")
        else:
            print(f"  [MISSING] {fact}")
            missing.append(fact)

    if missing:
        print(
            f"\nFAIL: {len(missing)}/{len(facts)} fact(s) not recoverable "
            f"verbatim in {target_path}"
        )
        return 1

    print(f"\nPASS: all {len(facts)} fact(s) recoverable verbatim in {target_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
