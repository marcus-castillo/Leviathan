import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Leviathan — Judicial Opinion Disparity Explorer",
  description:
    "Research tool for statistical disparities in judicial opinions. Not a measure of intent or bias.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <span className="brand">Leviathan</span>
          <Link href="/">Overview</Link>
          <Link href="/judges">Judges</Link>
          <Link href="/compare">Compare</Link>
          <Link href="/similar">Similar Cases</Link>
          <Link href="/trends">Trends</Link>
          <span className="small muted" style={{ marginLeft: "auto" }}>
            research preview — not legal advice
          </span>
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
