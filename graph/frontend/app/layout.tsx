import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Leviathan Graph — Citation Network Explorer",
  description: "Citation-graph influence analysis. Not a measure of intent or ideology.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <span className="brand">Leviathan Graph</span>
          <Link href="/">Overview</Link>
          <Link href="/network">Network</Link>
          <Link href="/clusters">Clusters</Link>
          <Link href="/temporal">Temporal</Link>
          <span className="small muted" style={{ marginLeft: "auto" }}>
            research preview — statistical grouping only
          </span>
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
