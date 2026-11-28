// A designed screen: on-grid spacing, quiet chrome, plain copy. It must scan clean — every
// line here is a near miss for some sign, which is what keeps the catalogue honest.
import { Receipt } from "lucide-react";

export function Invoices({ unlockAccount }: { unlockAccount: () => void }) {
  const total = 48210;
  return (
    <section className="p-6 gap-4 mt-[28px] px-[2px]">
      <h1 className="text-2xl font-medium tracking-tight">October 2026</h1>
      <p className="text-sm text-neutral-500">+12% vs last month</p>
      <Receipt size={16} strokeWidth={1.5} aria-hidden />
      <button className="transition-colors hover:bg-neutral-100" onClick={() => unlockAccount()}>
        Unlock account
      </button>
      <input placeholder="Search" />
      <span className="animate-pulse h-4 w-24 rounded bg-neutral-200" /> {/* slop-ok: loading skeleton */}
      <p>{total > 0 ? "Paid" : "Due"} ✓</p>
    </section>
  );
}
