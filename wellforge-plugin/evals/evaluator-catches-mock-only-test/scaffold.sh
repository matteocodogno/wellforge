#!/usr/bin/env bash
# Copy the frozen fixture project into this run's working directory. Every case does this:
# the run starts in an EMPTY throwaway directory, so without it there is no project to act on.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/../fixtures/project/." .

# The artefact under judgement: a test that asserts a mock and nothing else.
mkdir -p src
cat > src/orderHistory.test.ts <<'TS'
import { describe, it, expect, vi } from "vitest";
import { getOrderHistory } from "./orderHistory";

describe("getOrderHistory", () => {
  it("calls the repository", async () => {
    const repo = { findByCustomer: vi.fn().mockResolvedValue([]) };
    await getOrderHistory(repo as never, "cust-1");
    expect(repo.findByCustomer).toHaveBeenCalled();
  });
});
TS
cat > src/orderHistory.ts <<'TS'
export async function getOrderHistory(repo: { findByCustomer: (id: string) => Promise<unknown[]> }, customerId: string) {
  const rows = await repo.findByCustomer(customerId);
  return [...rows].reverse();
}
TS
