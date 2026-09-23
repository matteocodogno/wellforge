#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# Same feature, one tier lower: the mvp gate does not ask for an eval.
sed -i.bak "s/^rigor: production$/rigor: mvp/" specs/003-order-history/spec.md && rm -f specs/003-order-history/spec.md.bak
