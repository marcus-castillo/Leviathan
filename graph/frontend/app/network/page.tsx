"use client";

import useSWR from "swr";
import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { GraphCanvas } from "@/components/GraphCanvas";
import { Legend } from "@/components/Legend";
import { api, fetcher, type GraphPayload } from "@/lib/api";

export default function NetworkPage() {
  const [topic, setTopic] = useState("");
  const [focus, setFocus] = useState<GraphPayload | null>(null);
  const [focusName, setFocusName] = useState<string | null>(null);

  const key = `/graph/network${topic ? `?topic=${encodeURIComponent(topic)}` : ""}`;
  const { data: network, error } = useSWR<GraphPayload>(key, fetcher);

  async function selectNode(id: string, label: string) {
    if (label !== "Case") return;
    const ego = await api<GraphPayload>(`/graph/case/${encodeURIComponent(id)}`);
    setFocus(ego);
    setFocusName(ego.nodes.find((n) => n.id === id)?.name ?? id);
  }

  const data = focus ?? network;

  return (
    <>
      <h1>Citation network</h1>
      <EthicsBanner />

      <div className="card" style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <label className="small muted">Topic filter</label>
        <select value={topic} onChange={(e) => { setTopic(e.target.value); setFocus(null); }}>
          <option value="">all topics</option>
          {["immigration", "criminal-procedure", "civil-rights", "tax", "habeas", "employment", "administrative"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        {focus && (
          <button onClick={() => setFocus(null)}>← back to full network</button>
        )}
        <span className="small muted" style={{ marginLeft: "auto" }}>
          {focus ? `Ego network: ${focusName}` : "Click any node to focus its ego network"}
        </span>
      </div>

      <Legend />

      {error && <div className="card" style={{ color: "var(--warn)" }}>Graph API unreachable. Is it running and loaded?</div>}
      {!data && !error && <div className="card muted">Loading graph…</div>}
      {data && data.nodes.length === 0 && (
        <div className="card muted">No nodes. Load the example graph (see Overview).</div>
      )}
      {data && data.nodes.length > 0 && (
        <GraphCanvas data={data} onSelect={selectNode} />
      )}
    </>
  );
}
