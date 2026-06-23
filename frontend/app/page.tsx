import { EthicsBanner } from "@/components/EthicsBanner";
import { API_BASE } from "@/lib/api";

async function getStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function Home() {
  const stats = await getStats();
  return (
    <>
      <h1>Judicial Opinion Disparity Explorer</h1>
      <EthicsBanner />

      <div className="grid">
        <Stat label="Opinions" value={stats?.opinions ?? "—"} />
        <Stat label="Analyzed" value={stats?.analyzed ?? "—"} />
        <Stat label="Judges" value={stats?.judges ?? "—"} />
        <Stat label="Courts" value={stats?.courts ?? "—"} />
      </div>

      <div className="card">
        <h3>What this is — and isn&apos;t</h3>
        <p className="muted small" style={{ lineHeight: 1.6 }}>
          Leviathan surfaces <strong>statistical patterns</strong> in opinion text and outcomes to help
          researchers decide <em>where to look</em>. Every figure ships with a confidence score, a
          sample-size warning, and a limitations note. It deliberately uses the term{" "}
          <strong>&ldquo;tone analysis&rdquo;</strong> for language metrics, never claims intent, and
          refuses to rank judges on thin data. Disparities are hypotheses, not findings.
        </p>
        {!stats && (
          <p className="small" style={{ color: "var(--warn)" }}>
            Backend not reachable. Start it and load data:{" "}
            <code>docker compose exec backend python -m scripts.load_example_dataset</code>
          </p>
        )}
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="card">
      <div className="small muted">{label}</div>
      <div style={{ fontSize: 30, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
