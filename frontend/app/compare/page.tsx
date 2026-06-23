"use client";

import useSWR from "swr";
import { useState } from "react";
import { EthicsBanner } from "@/components/EthicsBanner";
import { JudgeRankingChart, type RankRow } from "@/components/JudgeRankingChart";
import { SignalCard } from "@/components/SignalCard";
import { api, fetcher, type BiasSignal, type JudgeProfile } from "@/lib/api";

interface JudgeListItem {
  id: number;
  display_name: string;
  n_opinions: number;
}
interface CompareResult {
  judges: JudgeProfile[];
  cross_judge_signals: BiasSignal[];
  disclaimer: string;
}

export default function ComparePage() {
  const { data: judges } = useSWR<JudgeListItem[]>("/judges", fetcher);
  const [picked, setPicked] = useState<number[]>([]);
  const [result, setResult] = useState<CompareResult | null>(null);

  function toggle(id: number) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  }

  async function run() {
    if (picked.length < 2) return;
    const res = await api<CompareResult>("/compare-judges", {
      method: "POST",
      body: JSON.stringify({ judge_ids: picked }),
    });
    setResult(res);
  }

  const rankRows: RankRow[] =
    result?.judges.map((j) => {
      const s = j.signals.find((x) => x.metric === "outcome.plaintiff_vs_defendant");
      const d = (s?.detail ?? {}) as { plaintiff?: number; decided?: number };
      const decided = d.decided ?? 0;
      return {
        name: j.display_name,
        value: decided ? (d.plaintiff ?? 0) / decided : 0,
        n: decided,
        lowData: (s?.caveats.sample_warning ?? null) !== null || decided === 0,
      };
    }) ?? [];

  return (
    <>
      <h1>Compare judges</h1>
      <EthicsBanner text="Different judges hear different dockets. Rate differences here are descriptive and need not reflect anything about how any judge decides comparable cases." />

      <div className="card">
        <div className="small muted" style={{ marginBottom: 8 }}>
          Pick two or more judges
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {judges?.map((j) => (
            <button
              key={j.id}
              onClick={() => toggle(j.id)}
              className={picked.includes(j.id) ? "primary" : ""}
            >
              {j.display_name} ({j.n_opinions})
            </button>
          ))}
        </div>
        <button className="primary" style={{ marginTop: 12 }} onClick={run} disabled={picked.length < 2}>
          Compare
        </button>
      </div>

      {result && (
        <>
          <div className="card">
            <h3>Plaintiff-favoring rate</h3>
            <JudgeRankingChart rows={rankRows} label="Share of clearly-decided opinions favoring plaintiff/appellant" />
          </div>
          <h3>Cross-judge signals</h3>
          {result.cross_judge_signals.map((s, i) => (
            <SignalCard key={i} signal={s} />
          ))}
        </>
      )}
    </>
  );
}
