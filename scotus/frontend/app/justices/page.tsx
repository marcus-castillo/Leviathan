"use client";

import useSWR from "swr";
import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { fetcher, type JusticeProfile, type SimilarityMap } from "@/lib/api";

function heat(v: number): string {
  // map cosine [-1,1] -> grayscale; higher similarity = darker cell (kept light enough for black text)
  const t = Math.max(0, Math.min(1, (v + 1) / 2));
  const lightness = Math.round(100 - t * 30); // 70%..100%
  return `hsl(0, 0%, ${lightness}%)`;
}

export default function JusticesPage() {
  const { data: map } = useSWR<SimilarityMap>("/justice/similarity", fetcher);
  const [slug, setSlug] = useState<string | null>(null);
  const { data: profile } = useSWR<JusticeProfile>(slug ? `/justice/${slug}` : null, fetcher);

  return (
    <>
      <h1>Justices — style similarity</h1>
      <EthicsBanner />

      {!map && <div className="card muted">Loading… (run embeddings if empty)</div>}

      {map && map.justices.length > 0 && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Pairwise style-similarity (cosine)</h3>
            <table>
              <thead>
                <tr>
                  <th></th>
                  {map.justices.map((j) => <th key={j}>{j.split("-").pop()}</th>)}
                </tr>
              </thead>
              <tbody>
                {map.matrix.map((row, i) => (
                  <tr key={map.justices[i]}>
                    <td>
                      <a href="#" onClick={(e) => { e.preventDefault(); setSlug(map.justices[i]); }}>
                        {map.justices[i]}
                      </a>
                    </td>
                    {row.map((v, j) => (
                      <td key={j} style={{ background: heat(v), color: "#000000", fontWeight: 600 }}>
                        {v.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>Stylistic clusters</h3>
            <p className="small" style={{ color: "var(--warn)" }}>
              Neutral labels — these are writing-style groups, NOT ideology.
            </p>
            {map.clusters.map((c) => (
              <div key={c.cluster} style={{ marginBottom: 8 }}>
                <span className="badge">{c.cluster}</span>
                {c.justices.map((j) => <span key={j} className="chip">{j}</span>)}
              </div>
            ))}
          </div>
        </>
      )}

      {profile && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>{profile.name} <span className="muted small">({profile.n_segments} segments)</span></h3>
          <div className="small muted">Distinctive framing vocabulary (vs. peers):</div>
          <div style={{ margin: "6px 0" }}>
            {profile.distinctive_terms.map(([w, z]) => (
              <span key={w} className="chip" title={`z=${z}`}>{w}</span>
            ))}
          </div>
          <div className="small muted">Nearest by style:</div>
          <div>{profile.nearest.map((n) => (
            <span key={n.justice} className="chip">{n.justice} · {n.similarity.toFixed(2)}</span>
          ))}</div>
        </div>
      )}
    </>
  );
}
