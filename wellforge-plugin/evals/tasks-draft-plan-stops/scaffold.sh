#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# 001's plan is approved in the fixture; this case needs it in draft.
sed -i.bak "s/^status: approved$/status: draft/" specs/001-checkout-flow/plan.md && rm -f specs/001-checkout-flow/plan.md.bak
