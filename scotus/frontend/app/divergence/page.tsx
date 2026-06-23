"use client";

import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { api, type DivergenceResult } from "@/lib/api";

export default function DivergencePage() {
  const [caseId, setCaseId] = useState("1");
  const [data, setData] = useState<DivergenceResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setErr(null);
    try {
      setData(await api<DivergenceResult>(`/analysis/divergence?case_id=${encodeURIComponent(caseId)}`));
    } catch (e) {
      setErr(String(e));
      setData(null);
    }
  }

  return (
    <>
      <h1>Majority vs. dissent — lexical divergence</h1>
      <EthicsBanner text="Distinctive words are a statistical property of the text (weighted log-odds). They do not capture legal merit or who is 'right'." />

      <div className="card" style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <label className="small muted">Case ID</label>
        <input value={caseId} onChange={(e) => setCaseId(e.target.value)} style={{ width: 90 }} />
        <button onClick={run}>Analyze</button>
        <span className="small muted">(IDs are sequential from the loaded corpus)</span>
      </div>

      {err && <div className="card" style={{ color: "var(--warn)" }}>{err}</div>}

      {data && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{data.case_name}</h3>
          {data.note && <p className="muted small">{data.note}</p>}
          <div className="cols">
            <div>
              <div className="badge" style={{ color: "var(--maj)", borderColor: "var(--maj)" }}>
                distinctive of MAJORITY
              </div>
              <div style={{ marginTop: 8 }}>
                {data.majority_terms.map(([w, z]) => (
                  <span key={w} className="chip" title={`z=${z}`}>{w}</span>
                ))}
              </div>
            </div>
            <div>
              <div className="badge" style={{ color: "var(--dis)", borderColor: "var(--dis)" }}>
                distinctive of DISSENT
              </div>
              <div style={{ marginTop: 8 }}>
                {data.dissent_terms.map(([w, z]) => (
                  <span key={w} className="chip" title={`z=${z}`}>{w}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
