#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# Last: one commit, so the state layer reads drift from git, not from copy-order mtimes.
bash "$here/../fixtures/commit.sh"
