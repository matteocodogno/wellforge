#!/bin/bash
# T13 fixture — single reproducible entry point for every terse-mode regression test.
#
# Runs, in order:
#   1. t8/extract-spans.sh              (AC-1.2 — byte-identical payload spans)
#   2. t11/run-check.sh                 (AC-4.1 — fact-preservation checker behavior)
#   3. t12/test_run_report_pairing.py   (AC-5.1 — run-report.py delta + omit pairing)
#
# Exits 0 only if all three pass; non-zero if ANY fails. Path-independent: resolves its
# own directory so it can be invoked from any cwd (`./run-all.sh`, `bash run-all.sh`,
# an absolute path from CI, etc.) rather than assuming the caller's cwd.
#
# stdlib/bash + python3 only, no network.
#
# Usage: ./run-all.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

overall=0
declare -a results=()

run_one () {
  local label="$1"; shift
  echo "############################################################"
  echo "## $label"
  echo "############################################################"
  if "$@"; then
    echo "--- PASS: $label"
    results+=("PASS  $label")
  else
    echo "--- FAIL: $label"
    results+=("FAIL  $label")
    overall=1
  fi
  echo
}

run_one "T8  extract-spans.sh   (AC-1.2)" "$HERE/t8/extract-spans.sh"
run_one "T11 run-check.sh       (AC-4.1)" "$HERE/t11/run-check.sh"
run_one "T12 test_run_report_pairing.py (AC-5.1)" python3 "$HERE/t12/test_run_report_pairing.py"

echo "============================================================"
echo "Summary:"
for r in "${results[@]}"; do
  echo "  $r"
done
if [ "$overall" -eq 0 ]; then
  echo "ALL PASS"
else
  echo "SOME FAILED"
fi

exit $overall
