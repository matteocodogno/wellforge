#!/usr/bin/env python3
"""Validate a commit message against Conventional Commits.

  check-commit-msg.py <path-to-COMMIT_EDITMSG>     # git commit-msg hook
  echo "feat: x" | check-commit-msg.py -           # stdin

Exits 0 if the subject line matches `type(scope)!: description`, non-zero with a helpful
message otherwise. Merge/revert/fixup/squash commits are exempt (git generates them).
Shared by the local commit-msg hook (gates/hooks/commit-msg) and the CI gate.
"""
import re
import sys

TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test",
         "build", "ci", "chore", "revert"]
# type, optional (scope), optional !, ": ", non-empty description
SUBJECT = re.compile(rf"^({'|'.join(TYPES)})(\([\w .,/-]+\))?(!)?: .+")
EXEMPT = re.compile(r"^(Merge |Revert |fixup!|squash!|amend!)")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check-commit-msg.py <file|->")
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    # first non-comment, non-blank line is the subject
    subject = ""
    for line in raw.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            subject = line
            break

    if EXEMPT.match(subject):
        return 0
    if SUBJECT.match(subject):
        return 0

    print("✗ commit message is not Conventional Commits:")
    print(f"    {subject!r}")
    print("  expected:  <type>[(scope)][!]: <description>")
    print(f"  types:     {', '.join(TYPES)}")
    print("  examples:  feat(opencode): add provider choice")
    print("             fix(cli): doctor mislabeled gh auth")
    print("             refactor(commands)!: rename dispatch refs")
    print("  (merge/revert/fixup commits are exempt)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
