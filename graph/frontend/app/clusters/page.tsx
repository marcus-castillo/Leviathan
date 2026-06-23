"use client";

import useSWR from "swr";
import { EthicsBanner } from "@/components/EthicsBanner";
import { fetcher, type ClusterResult } from "@/lib/api";

export default function ClustersPage() {
  const { data, error } = useSWR<ClusterResult>("/graph/cluster", fetcher);

  return (
    <>
      <h1>Clusters & statistical grouping</h1>
      <EthicsBanner text="Communities and judge 'groups' are unsupervised statistical artifacts of citation/topic patterns. Group labels (Group 1, Group 2…) are neutral and carry NO ideological meaning or ordering." />

      {error && <div className="card" style={{ color: "var(--warn)" }}>Graph API unreachable.</div>}
      {!data && !error && <div className="card muted">Computing…</div>}

      {data && (
        <>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>
              Case communities{" "}
              <span className="small muted">
                (Louvain · modularity {data.communities.modularity ?? "—"})
              </span>
            </h3>
            {data.communities.communities.map((c) => (
              <div key={c.community} style={{ marginBottom: 10 }}>
                <span className="badge">community {c.community}</span>
                <strong>{c.size} cases</strong>{" "}
                <span className="muted small">· exemplar: {c.exemplar_name ?? "—"}</span>
              </div>
            ))}
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>Judge statistical grouping</h3>
            <p className="small" style={{ color: "var(--warn)" }}>
              {data.statistical_grouping.disclaimer}
            </p>
            {data.statistical_grouping.note && (
              <p className="muted small">{data.statistical_grouping.note}</p>
            )}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 14 }}>
              {data.statistical_grouping.groups.map((g) => (
                <div key={g.group} className="card" style={{ margin: 0 }}>
                  <strong>{g.group}</strong> <span className="muted small">({g.size} judges)</span>
                  <div className="small muted" style={{ margin: "6px 0" }}>
                    defining topics: {g.defining_topics.join(", ") || "—"}
                  </div>
                  <ul className="small" style={{ paddingLeft: 16, margin: 0 }}>
                    {g.members.map((m) => <li key={m.judge_id}>{m.name}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </>
  );
}
