import Link from "next/link";
import { EthicsBanner } from "@/components/EthicsBanner";

export default function Home() {
  return (
    <>
      <h1>Citation Network Explorer</h1>
      <EthicsBanner />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>What you can explore</h3>
        <ul className="muted small" style={{ lineHeight: 1.7 }}>
          <li><Link href="/network">Network</Link> — zoomable case citation graph; node size ∝ how often a case is cited, edge color ∝ treatment (cites / follows / overrules / distinguishes). Click a node to re-center its ego network.</li>
          <li><Link href="/clusters">Clusters</Link> — Louvain communities of cases + a purely <em>statistical</em> grouping of judges by topic profile (neutral labels, never ideology).</li>
          <li><Link href="/temporal">Temporal</Link> — how topical emphasis and influential precedents shift over time.</li>
        </ul>
      </div>
      <div className="card small muted">
        Empty graph? Load the example: <code>docker compose exec graph-api python -m scripts.load_example_graph</code>
        then <code>python -m scripts.compute_metrics</code>.
      </div>
    </>
  );
}
