"use client";

import useSWR from "swr";
import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EthicsBanner } from "@/components/EthicsBanner";
import { fetcher } from "@/lib/api";

interface JudgeListItem {
  id: number;
  display_name: string;
  n_opinions: number;
}
interface TrendPoint {
  year: number;
  n: number;
  plaintiff_rate: number;
}

export default function TrendsPage() {
  const { data: judges } = useSWR<JudgeListItem[]>("/judges", fetcher);
  const [judgeId, setJudgeId] = useState<number | null>(null);
  const key = `/trends/plaintiff-rate${judgeId ? `?judge_id=${judgeId}` : ""}`;
  const { data } = useSWR<TrendPoint[]>(key, fetcher);

  return (
    <>
      <h1>Temporal trends</h1>
      <EthicsBanner text="Year-over-year movement can reflect changes in the docket, the law, or sampling — not a shift in any judge's disposition. Small yearly counts are especially noisy." />

      <div className="card">
        <label className="small muted">Scope</label>
        <select
          style={{ display: "block", marginTop: 6 }}
          value={judgeId ?? ""}
          onChange={(e) => setJudgeId(Number(e.target.value) || null)}
        >
          <option value="">Whole corpus</option>
          {judges?.map((j) => (
            <option key={j.id} value={j.id}>
              {j.display_name}
            </option>
          ))}
        </select>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Plaintiff-favoring rate by year</h3>
        {!data || data.length === 0 ? (
          <div className="muted small">No dated, decided opinions for this scope.</div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dddddd" />
              <XAxis dataKey="year" stroke="#555555" />
              <YAxis domain={[0, 1]} stroke="#555555" />
              <Tooltip
                contentStyle={{ background: "#ffffff", border: "1px solid #cccccc", color: "#000000" }}
                formatter={(v: number, _n, p: any) => [
                  `${(v * 100).toFixed(0)}% (n=${p.payload.n})`,
                  "plaintiff rate",
                ]}
              />
              <Line type="monotone" dataKey="plaintiff_rate" stroke="#000000" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </>
  );
}
