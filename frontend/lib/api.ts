export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export class ApiError extends Error {}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const fetcher = <T>(path: string) => api<T>(path);

// ---- Shared types (mirror backend schemas) ----
export interface Caveats {
  confidence: number;
  sample_size: number;
  sample_warning: string | null;
  limitations: string;
  interpretation: string;
}

export interface BiasSignal {
  metric: string;
  description: string;
  effect_size: number | null;
  p_value: number | null;
  p_value_adjusted: number | null;
  detail: Record<string, unknown>;
  caveats: Caveats;
}

export interface JudgeProfile {
  judge_id: number;
  display_name: string;
  n_opinions: number;
  signals: BiasSignal[];
  disclaimer: string;
}

export interface SimilarCase {
  opinion_id: number;
  case_name: string;
  judge: string | null;
  court: string | null;
  outcome: string | null;
  similarity: number;
}

export interface SimilarCasesResult {
  query_summary: string;
  results: SimilarCase[];
  outcome_comparison: BiasSignal | null;
  disclaimer: string;
}
