import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Leviathan SCOTUS — Opinion NLP",
  description: "NLP research on Supreme Court opinions. Lexical/stylistic statistics, not ideology.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <span className="brand">Leviathan SCOTUS</span>
          <Link href="/">Overview</Link>
          <Link href="/justices">Justices</Link>
          <Link href="/divergence">Divergence</Link>
          <Link href="/evolution">Evolution</Link>
          <span className="small muted" style={{ marginLeft: "auto" }}>
            research preview — stylistic statistics only
          </span>
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
