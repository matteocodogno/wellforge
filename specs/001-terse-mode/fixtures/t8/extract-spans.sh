#!/bin/bash
# T8 fixture — AC-1.2 byte-identical invariant check.
#
# Extracts the "payload spans" (fenced code/shell/error blocks + inline
# backtick paths) from the canonical (non-terse) and terse-rendered fixtures
# in this directory, then diffs each extracted set. A clean diff (empty
# output, exit 0) proves the terse rendering reproduced those spans
# byte-for-byte, even though the surrounding prose was compressed.
#
# Usage: ./extract-spans.sh
set -u
cd "$(dirname "$0")"

status=0

echo "== Fenced code/shell/error blocks =="
awk '/^```/{f=!f; next} f' canonical.md      > /tmp/t8-canonical-fenced.txt
awk '/^```/{f=!f; next} f' terse-rendered.md > /tmp/t8-terse-fenced.txt
if diff -u /tmp/t8-canonical-fenced.txt /tmp/t8-terse-fenced.txt; then
  echo "PASS: fenced spans (python code block, bash command, error message) are byte-identical"
else
  echo "FAIL: fenced spans differ"
  status=1
fi

echo
echo "== Inline backtick spans (file paths) =="
grep -o '`[^`]*`' canonical.md      > /tmp/t8-canonical-inline.txt
grep -o '`[^`]*`' terse-rendered.md > /tmp/t8-terse-inline.txt
if diff -u /tmp/t8-canonical-inline.txt /tmp/t8-terse-inline.txt; then
  echo "PASS: inline path spans are byte-identical"
else
  echo "FAIL: inline path spans differ"
  status=1
fi

exit $status
