export const API_BASE =
  process.env.NEXT_PUBLIC_GRAPH_API_BASE || "http://localhost:8001";

export async function api<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const fetcher = <T>(path: string) => api<T>(path);

export interface GNode {
  id: string;
  label: string;
  name: string | null;
  attrs?: Record<string, unknown>;
}
export interface GEdge {
  source: string;
  target: string;
  rel: string;
}
export interface GraphPayload {
  nodes: GNode[];
  edges: GEdge[];
  disclaimer: string;
  influence?: Record<string, unknown> | null;
  paths?: string[][];
}
export interface ClusterResult {
  communities: {
    membership: Record<string, number>;
    communities: { community: number; size: number; exemplar_name: string | null; members: string[] }[];
    modularity?: number;
  };
  statistical_grouping: {
    groups: { group: string; size: number; defining_topics: string[]; members: { judge_id: string; name: string }[] }[];
    disclaimer: string;
    note?: string;
  };
  disclaimer: string;
}
