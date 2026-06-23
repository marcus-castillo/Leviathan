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
const REL_DASH: Record<string, number[]> = {
  CITES: [1, 0],
  FOLLOWS: [1, 0],
  OVERRULES: [6, 3],
  DISTINGUISHES: [2, 3],
  AUTHORED_BY: [2, 3],
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
          dash: REL_DASH[e.rel] ?? [1, 0],
          onpath: pathEdges.has(`${e.source}->${e.target}`) ? 1 : 0,
        },
      })),
    ];

    const cy = cytoscape({
      container: ref.current,
      elements,
      wheelSensitivity: 0.2,
      style: [
        {
          selector: "node",
          style: {
            width: "data(size)",
            height: "data(size)",
            "background-color": (ele) => (ele.data("type") === "Judge" ? "#dddddd" : "#ffffff"),
            "border-width": (ele) => (ele.data("onpath") ? 3 : 1),
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
        {
          selector: "edge",
          style: {
            width: (ele) => (ele.data("onpath") ? 3 : 1.2),
            "line-color": "data(color)",
            "line-style": (ele) => (ele.data("dash")[1] ? "dashed" : "solid"),
            "line-dash-pattern": (ele) => ele.data("dash"),
            "target-arrow-color": "data(color)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: (ele) => (ele.data("onpath") ? 1 : 0.7),
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 30, nodeRepulsion: () => 12000 },
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
