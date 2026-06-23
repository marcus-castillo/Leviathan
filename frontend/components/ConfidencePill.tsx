"use client";

import type { Caveats } from "@/lib/api";

export function ConfidencePill({ caveats }: { caveats: Caveats }) {
  const pct = Math.round(caveats.confidence * 100);
  const cls = caveats.sample_warning ? "badge low" : pct >= 70 ? "badge" : "badge warn";
  return (
    <span className={cls} title={caveats.limitations}>
      conf {pct}% · n={caveats.sample_size}
      {caveats.sample_warning ? " · low-data" : ""}
    </span>
  );
}
