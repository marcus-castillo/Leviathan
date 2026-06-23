"use client";

const ITEMS: { label: string; color: string; style: string }[] = [
  { label: "cites", color: "#999999", style: "solid" },
  { label: "follows", color: "#000000", style: "solid" },
  { label: "overrules", color: "#000000", style: "dashed" },
  { label: "distinguishes", color: "#777777", style: "dotted" },
];

export function Legend() {
  return (
    <div className="legend card" style={{ padding: "10px 14px" }}>
      {ITEMS.map((it) => (
        <span key={it.label}>
          <span
            className="dot"
            style={{ borderTopColor: it.color, borderTopStyle: it.style as "solid" }}
          />
          {it.label}
        </span>
      ))}
      <span className="muted">node size proportional to times cited (PageRank)</span>
    </div>
  );
}
