export const API_BASE =
  process.env.NEXT_PUBLIC_SCOTUS_API_BASE || "http://localhost:8002";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const fetcher = <T>(path: string) => api<T>(path);

export interface SimilarityMap {
  justices: string[];
  matrix: number[][];
  clusters: { cluster: string; justices: string[] }[];
  disclaimer: string;
}
export interface JusticeProfile {
  slug: string;
  name: string;
  n_segments: number;
  distinctive_terms: [string, number][];
  nearest: { justice: string; similarity: number }[];
  disclaimer: string;
}
export interface DivergenceResult {
  case_id: number;
  case_name: string;
  majority_terms: [string, number][];
  dissent_terms: [string, number][];
  note?: string | null;
  disclaimer: string;
}
export interface EvolutionResult {
  by_term: { term: number; themes: Record<string, number>; total: number }[];
  disclaimer: string;
}
