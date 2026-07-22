import cytoscape, { type Core } from "cytoscape";
import { Focus, Maximize2, Minus, Plus, RotateCcw } from "lucide-react";
import { useEffect, useRef } from "react";
import type { GraphNode, Projection } from "../api";

type Props = {
  projection: Projection | null;
  selectedId: string | null;
  onSelect: (node: GraphNode | null) => void;
};

const colors: Record<string, string> = {
  event_handler: "#b9f778",
  function: "#62d8f5",
  method: "#68a8ff",
  class: "#d8a7ff",
  struct: "#f0a96b",
  enum: "#ffd66b",
  file: "#73827d",
  runtime: "#ff7d68",
  external_function: "#87938f",
};

export function GraphWorkspace({ projection, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current || !projection) return;
    cyRef.current?.destroy();
    const nodeMap = new Map(projection.nodes.map((node) => [node.id, node]));
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...projection.nodes.map((node) => ({
          data: {
            id: node.id,
            label: node.name,
            qualifiedName: node.qualified_name,
            kind: node.kind,
            color: colors[node.kind] ?? "#8aa09a",
          },
        })),
        ...projection.edges.map((edge) => ({
          data: {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            relationship: edge.relationship,
            origin: edge.origin,
            confidence: edge.confidence,
          },
        })),
      ],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            "border-color": "#07110f",
            "border-width": 2,
            width: 17,
            height: 17,
            label: "",
            "overlay-opacity": 0,
          },
        },
        {
          selector: "node:selected",
          style: {
            width: 28,
            height: 28,
            "border-color": "#f6fff2",
            "border-width": 3,
            label: "data(label)",
            color: "#f5fff1",
            "font-size": 10,
            "font-weight": 700,
            "text-background-color": "#07110f",
            "text-background-opacity": 0.92,
            "text-background-padding": "4px",
            "text-valign": "bottom",
            "text-margin-y": 10,
          },
        },
        {
          selector: "edge",
          style: {
            width: "mapData(confidence, 0, 1, 0.5, 1.8)",
            "line-color": "#36504a",
            "target-arrow-color": "#52776e",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.62,
            "arrow-scale": 0.65,
          },
        },
        {
          selector: 'edge[origin = "runtime"]',
          style: { "line-color": "#df835f", "target-arrow-color": "#df835f", "line-style": "dashed" },
        },
        {
          selector: "edge:selected",
          style: { width: 3, "line-color": "#b9f778", "target-arrow-color": "#b9f778", opacity: 1 },
        },
      ],
      minZoom: 0.08,
      maxZoom: 4,
    });
    cy.on("tap", "node", (event) => onSelect(nodeMap.get(event.target.id()) ?? null));
    cy.on("tap", (event) => {
      if (event.target === cy) onSelect(null);
    });
    cy.layout({
      name: projection.nodes.length > 420 ? "grid" : "cose",
      animate: false,
      fit: true,
      padding: 42,
      nodeRepulsion: () => 9000,
      idealEdgeLength: () => 72,
      gravity: 0.32,
    }).run();
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [projection, onSelect]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !selectedId) return;
    const node = cy.getElementById(selectedId);
    if (!node.empty()) {
      cy.$(":selected").unselect();
      node.select();
      cy.animate({ center: { eles: node }, zoom: Math.max(cy.zoom(), 1.1) }, { duration: 280 });
    }
  }, [selectedId]);

  const action = (kind: "in" | "out" | "fit" | "reset") => {
    const cy = cyRef.current;
    if (!cy) return;
    if (kind === "in") cy.zoom({ level: cy.zoom() * 1.25, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    if (kind === "out") cy.zoom({ level: cy.zoom() / 1.25, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
    if (kind === "fit") cy.fit(undefined, 42);
    if (kind === "reset") {
      cy.$(":selected").unselect();
      cy.fit(undefined, 42);
      onSelect(null);
    }
  };

  return (
    <section className="graph-stage" aria-label="Interactive code graph">
      <div className="graph-canvas" ref={containerRef} />
      {!projection?.nodes.length && (
        <div className="graph-empty">
          <Focus size={34} />
          <strong>No graph projection</strong>
          <span>Analyze a repository or loosen the current filters.</span>
        </div>
      )}
      <div className="graph-controls" aria-label="Graph controls">
        <button onClick={() => action("in")} aria-label="Zoom in"><Plus size={16} /></button>
        <button onClick={() => action("out")} aria-label="Zoom out"><Minus size={16} /></button>
        <button onClick={() => action("fit")} aria-label="Fit graph"><Maximize2 size={16} /></button>
        <button onClick={() => action("reset")} aria-label="Reset graph"><RotateCcw size={16} /></button>
      </div>
      {projection?.truncated && (
        <div className="projection-notice">Projection capped at {projection.visible_nodes.toLocaleString()} nodes</div>
      )}
    </section>
  );
}
