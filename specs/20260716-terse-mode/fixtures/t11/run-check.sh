#!/bin/bash
# T11 fixture — AC-4.1 fact-preservation, single entry point (mirrors T8's
# extract-spans.sh pattern: one runnable, deterministic, no-args checker).
#
# Runs check-facts.py against all three fixtures in this directory:
#   1. original.md       — sanity check, must PASS (facts.txt is derived from it)
#   2. compressed.md      — the GOOD compression, must PASS (AC-4.1 done-when)
#   3. compressed-BAD.md  — the negative control, must FAIL (proves the check
#                            has real power rather than passing vacuously)
#
# Exit code: 0 if all three outcomes match expectation, 1 otherwise.
#
# Usage: ./run-check.sh
set -u
cd "$(dirname "$0")"

overall=0

run_case () {
  local label="$1" file="$2" expect="$3"  # expect: pass | fail
  echo "== $label ($file), expect $expect =="
  python3 check-facts.py facts.txt "$file"
  local rc=$?
  echo "(exit code: $rc)"
  if [ "$expect" = "pass" ] && [ "$rc" -ne 0 ]; then
    echo "UNEXPECTED: $label was expected to PASS but exited $rc"
    overall=1
  elif [ "$expect" = "fail" ] && [ "$rc" -eq 0 ]; then
    echo "UNEXPECTED: $label was expected to FAIL but exited 0"
    overall=1
  else
    echo "OK: $label behaved as expected"
  fi
  echo
}

run_case "original"          original.md        pass
run_case "good compression"  compressed.md       pass
run_case "BAD negative control" compressed-BAD.md fail

if [ "$overall" -eq 0 ]; then
  echo "PASS: check-facts.py exits 0 on the good pair and non-zero on the fact-dropping control (AC-4.1)"
else
  echo "FAIL: checker did not behave as expected — see UNEXPECTED lines above"
fi

exit $overall
