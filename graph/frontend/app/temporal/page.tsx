"use client";

import useSWR from "swr";
import { EthicsBanner } from "@/components/EthicsBanner";
import { fetcher } from "@/lib/api";

interface TimelinePoint { year: number; topics: Record<string, number>; total: number; }
interface EraPrecedents { era: string; top_precedents: { name: string; count: number }[]; }
interface TemporalResult {
  timeline: TimelinePoint[];
  top_precedents_by_era: EraPrecedents[];
  note: string;
  disclaimer: string;
}

export default function TemporalPage() {
  const { data, error } = useSWR<TemporalResult>("/graph/temporal", fetcher);
  const maxTotal = data ? Math.max(1, ...data.timeline.map((t) => t.total)) : 1;

  return (
    <>
      <h1>Temporal evolution of reasoning</h1>
      <EthicsBanner text="Year-over-year movement reflects corpus coverage and the law as much as anything else. Absence of data in a year is not absence of activity." />

      {error && <div className="card" style={{ color: "var(--warn)" }}>Graph API unreachable.</div>}
      {!data && !error && <div className="card muted">Loading…</div>}

      {data && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Topical emphasis by year</h3>
            {data.timeline.length === 0 && <div className="muted small">No dated cases.</div>}
            {data.timeline.map((t) => (
              <div key={t.year} style={{ display: "flex", alignItems: "center", gap: 10, margin: "4px 0" }}>
                <span className="small muted" style={{ width: 44 }}>{t.year}</span>
                <div style={{ flex: 1, background: "var(--panel-2)", borderRadius: 6, height: 20, position: "relative" }}>
                  <div style={{ width: `${(t.total / maxTotal) * 100}%`, background: "var(--accent)", height: "100%", borderRadius: 6 }} />
                </div>
                <span className="small muted" style={{ width: 220 }}>
                  {Object.entries(t.topics).map(([k, v]) => `${k}:${v}`).join("  ")}
                </span>
              </div>
            ))}
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>Most-cited precedents per era</h3>
            {data.top_precedents_by_era.map((e) => (
              <div key={e.era} style={{ marginBottom: 10 }}>
                <span className="badge">{e.era}</span>
                <span className="small">
                  {e.top_precedents.map((p) => `${p.name} (${p.count})`).join("  ·  ") || "—"}
                </span>
              </div>
            ))}
          </div>

          <p className="muted small">{data.note}</p>
        </>
      )}
    </>
  );
}
