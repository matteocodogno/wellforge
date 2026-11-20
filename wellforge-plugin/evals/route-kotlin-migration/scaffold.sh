#!/usr/bin/env bash
# Routing case: copy a stack fixture, not the spec-workflow project — what is being tested is
# which skill the request selects, and that depends on what the repository is built with.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/stacks/jvm-monorepo/." .
bash "$here/../fixtures/commit.sh"
