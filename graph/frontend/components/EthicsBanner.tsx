"use client";

export function EthicsBanner({ text }: { text?: string }) {
  return (
    <div className="banner" role="note">
      <strong>Note — interpretation guardrail.</strong>{" "}
      {text ??
        "This graph describes citation structure and statistical groupings only. It does NOT measure judicial intent, ideology, or bias and cannot establish causation. Communities and metrics are sensitive to corpus coverage, time window, and algorithm parameters."}
    </div>
  );
}
