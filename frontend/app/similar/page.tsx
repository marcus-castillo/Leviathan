"use client";

import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { SignalCard } from "@/components/SignalCard";
import { api, type SimilarCasesResult } from "@/lib/api";

export default function SimilarPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<SimilarCasesResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (text.trim().length < 20) return;
    setLoading(true);
    try {
      const res = await api<SimilarCasesResult>("/similar-cases", {
        method: "POST",
        body: JSON.stringify({ text, top_k: 10 }),
      });
      setResult(res);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1>Similar case explorer</h1>
      <EthicsBanner text="Embedding similarity captures textual resemblance, not legal equivalence. 'Similar' cases may differ on facts that legitimately change the outcome — do not read divergent outcomes as inconsistency by any judge." />

      <div className="card">
        <label className="small muted">Paste opinion text or a fact pattern</label>
        <textarea
          style={{ display: "block", width: "100%", minHeight: 140, marginTop: 6 }}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Petitioner sought asylum under 8 U.S.C. § 1158 alleging past persecution..."
        />
        <button className="primary" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
          {loading ? "Searching…" : "Find similar cases"}
        </button>
      </div>

      {result && (
        <>
          {result.outcome_comparison && <SignalCard signal={result.outcome_comparison} />}
          <div className="card">
            <h3 style={{ marginTop: 0 }}>{result.query_summary}</h3>
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Judge</th>
                  <th>Court</th>
                  <th>Outcome</th>
                  <th>Similarity</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((r) => (
                  <tr key={r.opinion_id}>
                    <td>{r.case_name}</td>
                    <td>{r.judge ?? "—"}</td>
                    <td>{r.court ?? "—"}</td>
                    <td>{r.outcome ?? "—"}</td>
                    <td>{(r.similarity * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
