"use client";

import type { BiasSignal } from "@/lib/api";
import { ConfidencePill } from "./ConfidencePill";

export function SignalCard({ signal }: { signal: BiasSignal }) {
  const p = signal.p_value_adjusted ?? signal.p_value;
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
        <div>
          <div className="small muted">{signal.metric}</div>
          <div style={{ marginTop: 4 }}>{signal.description}</div>
        </div>
        <ConfidencePill caveats={signal.caveats} />
      </div>

      <div className="small muted" style={{ marginTop: 10, display: "flex", gap: 16, flexWrap: "wrap" }}>
        {signal.effect_size != null && <span>effect size: {signal.effect_size}</span>}
        {p != null && (
          <span>
            {signal.p_value_adjusted != null ? "q (FDR)" : "p"}: {p}
          </span>
        )}
      </div>

      {signal.caveats.sample_warning && (
        <div className="small" style={{ color: "var(--danger)", marginTop: 8 }}>
          {signal.caveats.sample_warning}
        </div>
      )}

      <details style={{ marginTop: 10 }}>
        <summary className="small muted" style={{ cursor: "pointer" }}>
          Why this is not proof of bias
        </summary>
        <div className="small muted" style={{ marginTop: 6, lineHeight: 1.5 }}>
          <p style={{ margin: "4px 0" }}>{signal.caveats.interpretation}</p>
          <p style={{ margin: "4px 0" }}>{signal.caveats.limitations}</p>
        </div>
      </details>
    </div>
  );
}
