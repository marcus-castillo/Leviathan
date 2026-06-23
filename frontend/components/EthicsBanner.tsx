"use client";

export function EthicsBanner({ text }: { text?: string }) {
  return (
    <div className="banner" role="note">
      <strong>Note — interpretation guardrail.</strong>{" "}
      {text ??
        "Leviathan reports statistical disparities only. It does NOT measure judicial intent, bias, or prejudice, and cannot establish causation. Disparities may reflect caseload composition, the governing law, selection effects, or sampling noise. Treat every figure as a hypothesis for qualified human review."}
    </div>
  );
}
