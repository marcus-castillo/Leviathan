import Link from "next/link";
import { EthicsBanner } from "@/components/EthicsBanner";

export default function Home() {
  return (
    <>
      <h1>Supreme Court Opinion NLP</h1>
      <EthicsBanner />
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Explore</h3>
        <ul className="muted small" style={{ lineHeight: 1.7 }}>
          <li><Link href="/justices">Justices</Link> — style-similarity map, stylistic clustering, and per-justice distinctive framing vocabulary.</li>
          <li><Link href="/divergence">Divergence</Link> — words most distinctive of the majority vs. the dissent in a case (weighted log-odds / Fightin&apos; Words).</li>
          <li><Link href="/evolution">Evolution</Link> — how constitutional themes shift across SCOTUS terms.</li>
        </ul>
      </div>
      <div className="card small muted">
        Empty? Load + embed the example corpus:{" "}
        <code>docker compose exec scotus-api python -m scripts.load_example_corpus</code> then{" "}
        <code>python -m scripts.build_justice_embeddings</code>.
      </div>
    </>
  );
}
