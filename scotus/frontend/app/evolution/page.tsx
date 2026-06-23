"use client";

import useSWR from "swr";
import { EthicsBanner } from "@/components/EthicsBanner";
import { fetcher, type EvolutionResult } from "@/lib/api";

const COLORS = ["#000000", "#3a3a3a", "#5a5a5a", "#777777", "#949494", "#b0b0b0", "#c8c8c8", "#e0e0e0"];

export default function EvolutionPage() {
  const { data } = useSWR<EvolutionResult>("/analysis/evolution", fetcher);
  const allThemes = data
    ? Array.from(new Set(data.by_term.flatMap((t) => Object.keys(t.themes)))).sort()
    : [];

  return (
    <>
      <h1>Theme evolution across terms</h1>
      <EthicsBanner text="Counts reflect corpus coverage as much as any real trend; sparse terms are noisy." />

      {!data && <div className="card muted">Loading…</div>}
      {data && data.by_term.length === 0 && (
        <div className="card muted">No dated cases loaded.</div>
      )}

      {data && data.by_term.length > 0 && (
        <>
          <div className="card">
            <div className="small muted" style={{ marginBottom: 10 }}>
              {allThemes.map((t, i) => (
                <span key={t} className="badge" style={{ color: COLORS[i % COLORS.length], borderColor: COLORS[i % COLORS.length] }}>{t}</span>
              ))}
            </div>
            {data.by_term.map((row) => (
              <div key={row.term} style={{ display: "flex", alignItems: "center", gap: 8, margin: "4px 0" }}>
                <span className="small muted" style={{ width: 52 }}>{row.term}</span>
                <div style={{ display: "flex", flex: 1, height: 22, borderRadius: 5, overflow: "hidden", background: "var(--panel-2)" }}>
                  {allThemes.map((t, i) => {
                    const v = row.themes[t] || 0;
                    if (!v) return null;
                    return (
                      <div key={t} title={`${t}: ${v}`}
                        style={{ width: `${(v / row.total) * 100}%`, background: COLORS[i % COLORS.length] }} />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <p className="muted small">{data.disclaimer}</p>
        </>
      )}
    </>
  );
}
