"use client";

export function EthicsBanner({ text }: { text?: string }) {
  return (
    <div className="banner" role="note">
      <strong>Note — interpretation guardrail.</strong>{" "}
      {text ??
        "These are lexical/stylistic statistics of opinion text only. They do NOT measure any justice's beliefs, motives, or the correctness of any opinion. 'Clusters' are writing-style groups with neutral labels — not ideology scores (use external measures like Martin–Quinn for that)."}
    </div>
  );
}
