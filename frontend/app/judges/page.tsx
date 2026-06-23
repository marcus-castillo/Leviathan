"use client";

import useSWR from "swr";
import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { SignalCard } from "@/components/SignalCard";
import { fetcher, type JudgeProfile } from "@/lib/api";

interface JudgeListItem {
  id: number;
  display_name: string;
  n_opinions: number;
}

export default function JudgesPage() {
  const { data: judges } = useSWR<JudgeListItem[]>("/judges", fetcher);
  const [selected, setSelected] = useState<number | null>(null);
  const { data: profile } = useSWR<JudgeProfile>(
    selected ? `/judge-profile/${selected}` : null,
    fetcher
  );

  return (
    <>
      <h1>Judge profiles</h1>
      <EthicsBanner />

      <div className="card">
        <label className="small muted">Select a judge</label>
        <select
          style={{ display: "block", marginTop: 6, width: "100%" }}
          value={selected ?? ""}
          onChange={(e) => setSelected(Number(e.target.value) || null)}
        >
          <option value="">— choose —</option>
          {judges?.map((j) => (
            <option key={j.id} value={j.id}>
              {j.display_name} (n={j.n_opinions})
            </option>
          ))}
        </select>
      </div>

      {profile && (
        <>
          <div className="card">
            <h3 style={{ margin: 0 }}>{profile.display_name}</h3>
            <div className="small muted">{profile.n_opinions} analyzed opinions</div>
            <p className="small" style={{ color: "var(--warn)", marginBottom: 0 }}>
              {profile.disclaimer}
            </p>
          </div>

          {profile.signals.length === 0 && (
            <div className="card muted">No signals — insufficient analyzed data for this judge.</div>
          )}
          {profile.signals.map((s, i) => (
            <SignalCard key={i} signal={s} />
          ))}
        </>
      )}
    </>
  );
}
