#!/usr/bin/env python3
"""Enforce coverage thresholds from a JaCoCo XML report.

Usage: check-jacoco.py <jacoco.xml> --min-line 80 [--min-branch 0] [--floor-lines 50]

--min-branch 0 means branch coverage is reported but not enforced.
--floor-lines: if the module has fewer total lines than this, enforcement is
skipped (fresh scaffolds shouldn't fail their own gate) — a notice is printed.
"""
import argparse
import sys
import xml.etree.ElementTree as ET


def pct(counter):
    missed, covered = int(counter.get("missed")), int(counter.get("covered"))
    total = missed + covered
    return (100.0 * covered / total if total else 100.0), total


def main():
    p = argparse.ArgumentParser()
    p.add_argument("report")
    p.add_argument("--min-line", type=float, required=True)
    p.add_argument("--min-branch", type=float, default=0)
    p.add_argument("--floor-lines", type=int, default=50)
    args = p.parse_args()

    try:
        root = ET.parse(args.report).getroot()
    except (OSError, ET.ParseError) as e:
        print(f"::error::cannot read JaCoCo report {args.report}: {e}")
        return 1

    # Report-level counters are the last direct children of <report>
    counters = {c.get("type"): c for c in root.findall("counter")}
    if "LINE" not in counters:
        print(f"::error::no LINE counter in {args.report} — did tests run?")
        return 1

    line_pct, line_total = pct(counters["LINE"])
    branch_pct = None
    if "BRANCH" in counters:
        branch_pct, _ = pct(counters["BRANCH"])

    print(f"line coverage:   {line_pct:.1f}% ({line_total} lines, threshold {args.min_line}%)")
    if branch_pct is not None:
        enforced = f"threshold {args.min_branch}%" if args.min_branch else "reported only"
        print(f"branch coverage: {branch_pct:.1f}% ({enforced})")

    if line_total < args.floor_lines:
        print(f"::notice::module has {line_total} lines (< floor {args.floor_lines}) — "
              "coverage enforcement skipped (scaffold-sized module)")
        return 0

    failed = False
    if line_pct < args.min_line:
        print(f"::error::line coverage {line_pct:.1f}% is below the welld gate ({args.min_line}%)")
        failed = True
    if args.min_branch and branch_pct is not None and branch_pct < args.min_branch:
        print(f"::error::branch coverage {branch_pct:.1f}% is below the welld gate ({args.min_branch}%)")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
