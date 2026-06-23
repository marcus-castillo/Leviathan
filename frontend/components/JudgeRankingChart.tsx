"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface RankRow {
  name: string;
  value: number; // e.g. plaintiff-favoring rate
  n: number;
  lowData: boolean;
}

/**
 * Judge ranking chart. Cautionary by design: low-data judges are visually de-emphasized and the
 * axis is labeled to avoid implying a "bias ranking".
 */
export function JudgeRankingChart({ rows, label }: { rows: RankRow[]; label: string }) {
  return (
    <div>
      <div className="small muted" style={{ marginBottom: 8 }}>
        {label} — bars with hatching have too little data to interpret (n &lt; threshold).
      </div>
      <ResponsiveContainer width="100%" height={Math.max(160, rows.length * 42)}>
        <BarChart data={rows} layout="vertical" margin={{ left: 40, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#dddddd" />
          <XAxis type="number" stroke="#555555" domain={[0, 1]} />
          <YAxis type="category" dataKey="name" stroke="#555555" width={140} />
          <Tooltip
            contentStyle={{ background: "#ffffff", border: "1px solid #cccccc", color: "#000000" }}
            formatter={(v: number, _n, p: any) =>
              [`${(v * 100).toFixed(0)}% (n=${p.payload.n})`, "rate"]
            }
          />
          <Bar dataKey="value">
            {rows.map((r, i) => (
              <Cell key={i} fill={r.lowData ? "#bbbbbb" : "#000000"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
