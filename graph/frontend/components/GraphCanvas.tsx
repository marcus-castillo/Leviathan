"use client";

import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import type { GraphPayload } from "@/lib/api";

// Monochrome encoding: treatment is carried by grayscale shade + line style, not color.
const REL_COLOR: Record<string, string> = {
  CITES: "#999999",
  FOLLOWS: "#000000",
  OVERRULES: "#000000",
  DISTINGUISHES: "#777777",
  AUTHORED_BY: "#bbbbbb",
};
const REL_LSTYLE: Record<string, string> = {
  CITES: "solid",
  FOLLOWS: "solid",
  OVERRULES: "dashed",
  DISTINGUISHES: "dotted",
  AUTHORED_BY: "dotted",
};

/**
 * Zoomable citation network. Node size scales with PageRank (authority); edge treatment is encoded
 * in grayscale + line style (solid/dashed/dotted) for a clean monochrome look. Clicking a case node
 * calls `onSelect` so the page can re-center the ego network.
 */
export function GraphCanvas({
  data,
  highlightPaths,
  onSelect,
}: {
  data: GraphPayload;
  highlightPaths?: string[][];
  onSelect?: (id: string, label: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!ref.current) return;

    const pathNodes = new Set((highlightPaths ?? []).flat());
    const pathEdges = new Set<string>();
    (highlightPaths ?? []).forEach((p) => {
      for (let i = 0; i < p.length - 1; i++) pathEdges.add(`${p[i]}->${p[i + 1]}`);
    });

    const elements: ElementDefinition[] = [
      ...data.nodes.map((n) => {
        const pr = Number((n.attrs?.pagerank as number) ?? 0);
        return {
          data: {
            id: n.id,
            label: n.name ?? n.id,
            type: n.label,
            size: 18 + Math.min(46, pr * 600),
            onpath: pathNodes.has(n.id) ? 1 : 0,
          },
        };
      }),
      ...data.edges.map((e) => ({
        data: {
          id: `${e.source}->${e.target}:${e.rel}`,
          source: e.source,
          target: e.target,
          rel: e.rel,
          color: REL_COLOR[e.rel] ?? "#999999",
          lstyle: REL_LSTYLE[e.rel] ?? "solid",
          onpath: pathEdges.has(`${e.source}->${e.target}`) ? 1 : 0,
        },
      })),
    ];

    const cy = cytoscape({
      container: ref.current,
      elements,
      wheelSensitivity: 0.2,
      // Styling uses selectors + data() string-mappers only (no function mappers / ambiguous
      // layout options), so it type-checks cleanly against @types/cytoscape.
      style: [
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            "background-color": "#ffffff",
            "border-width": 1,
            "border-color": "#000000",
            label: "data(label)",
            color: "#000000",
            "font-family": "Times New Roman, Times, serif",
            "font-size": "9px",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "text-valign": "bottom",
            "text-margin-y": 3,
          },
        },
        { selector: 'node[type = "Judge"]', style: { "background-color": "#dddddd" } },
        { selector: "node[onpath = 1]", style: { "border-width": 3 } },
        {
          selector: "edge",
          style: {
            width: 1.2,
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.7,
          },
        },
        { selector: 'edge[lstyle = "dashed"]', style: { "line-style": "dashed" } },
        { selector: 'edge[lstyle = "dotted"]', style: { "line-style": "dotted" } },
        { selector: "edge[onpath = 1]", style: { width: 3, opacity: 1 } },
      ],
      layout: { name: "cose", animate: false, padding: 30 },
    });

    cy.on("tap", "node", (evt) => {
      const d = evt.target.data();
      onSelect?.(d.id, d.type);
    });

    cyRef.current = cy;
    return () => cy.destroy();
  }, [data, highlightPaths, onSelect]);

  return <div id="cy" ref={ref} />;
}
