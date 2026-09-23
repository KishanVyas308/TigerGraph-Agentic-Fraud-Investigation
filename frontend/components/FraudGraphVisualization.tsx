"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import cytoscape, { Core, EventObject } from "cytoscape";
import {
  GraphVisualizationResponse,
  EvidenceListResponse,
  CytoscapeElementData,
} from "@/types/api";
import {
  Network,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Layers,
  X,
  ShieldAlert,
  FileText,
  Activity,
  Info,
} from "lucide-react";

interface FraudGraphVisualizationProps {
  graphData: GraphVisualizationResponse | null;
  evidenceData?: EvidenceListResponse | null;
  caseId: string;
}

type LayoutType = "cose" | "concentric" | "circle" | "breadthfirst";

export const FraudGraphVisualization: React.FC<FraudGraphVisualizationProps> = ({
  graphData,
  evidenceData,
  caseId,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [currentLayout, setCurrentLayout] = useState<LayoutType>("cose");
  const [selectedEntity, setSelectedEntity] = useState<{
    type: "node" | "edge";
    data: CytoscapeElementData;
    connectedDegree?: number;
    matchingEvidence?: Array<{
      evidence_id: string;
      category: string;
      fact: string;
    }>;
  } | null>(null);

  // Initialize and update Cytoscape instance
  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    // Destroy prior instance if existing
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    const elements = [
      ...(graphData.nodes || []).map((n) => ({
        group: "nodes" as const,
        data: n.data,
        classes: n.classes || `${(n.data.type || "unknown").toLowerCase()}-node`,
      })),
      ...(graphData.edges || []).map((e) => ({
        group: "edges" as const,
        data: e.data,
        classes: e.classes || "default-edge",
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      boxSelectionEnabled: false,
      autounselectify: false,
      minZoom: 0.2,
      maxZoom: 3.5,
      style: [
        // Base Node Style
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: "#F8FAFC",
            "font-size": "10px",
            "font-family": "monospace",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-background-opacity": 0.85,
            "text-background-color": "#060913",
            "text-background-padding": "2px",
            "text-background-shape": "roundrectangle",
            "border-width": 2,
            "border-color": "#334155",
            "background-color": "#1E293B",
            width: 36,
            height: 36,
          },
        },
        // Entity Type Specific Node Styles
        {
          selector: 'node[type = "CASE"], .case-node',
          style: {
            "background-color": "#F97316",
            "border-color": "#FB923C",
            "border-width": 3,
            shape: "round-rectangle",
            width: 46,
            height: 46,
            "font-weight": "bold",
          },
        },
        {
          selector: 'node[type = "CUSTOMER"], .customer-node',
          style: {
            "background-color": "#0284C7",
            "border-color": "#38BDF8",
            shape: "ellipse",
            width: 40,
            height: 40,
          },
        },
        {
          selector: 'node[type = "ACCOUNT"], .account-node',
          style: {
            "background-color": "#6366F1",
            "border-color": "#818CF8",
            shape: "round-rectangle",
            width: 38,
            height: 38,
          },
        },
        {
          selector: 'node[type = "TRANSACTION"], .transaction-node',
          style: {
            "background-color": "#F59E0B",
            "border-color": "#FCD34D",
            shape: "diamond",
            width: 42,
            height: 42,
          },
        },
        {
          selector: 'node[type = "DEVICE"], .device-node',
          style: {
            "background-color": "#10B981",
            "border-color": "#34D399",
            shape: "hexagon",
            width: 38,
            height: 38,
          },
        },
        {
          selector: 'node[type = "IP"], .ip-node',
          style: {
            "background-color": "#A855F7",
            "border-color": "#C084FC",
            shape: "octagon",
            width: 36,
            height: 36,
          },
        },
        {
          selector: 'node[type = "HISTORICAL_CASE"], .fraud-case-node',
          style: {
            "background-color": "#EF4444",
            "border-color": "#F87171",
            shape: "star",
            width: 44,
            height: 44,
          },
        },
        // Base Edge Style
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#475569",
            "line-color": "#334155",
            width: 1.5,
            label: "data(label)",
            "font-size": "8px",
            "font-family": "monospace",
            color: "#94A3B8",
            "text-rotation": "autorotate",
            "text-background-opacity": 0.85,
            "text-background-color": "#0B1120",
            "text-background-padding": "2px",
          },
        },
        // Interactive Selection & Focus States
        {
          selector: ".selected",
          style: {
            "border-color": "#06B6D4",
            "border-width": 4,
            "line-color": "#06B6D4",
            "target-arrow-color": "#06B6D4",
            width: 3,
          },
        },
        {
          selector: ".connected",
          style: {
            opacity: 1.0,
            "line-color": "#38BDF8",
            "target-arrow-color": "#38BDF8",
            width: 2.5,
          },
        },
        {
          selector: ".dimmed",
          style: {
            opacity: 0.15,
          },
        },
      ],
      layout: getLayoutConfig(currentLayout),
    });

    // Handle Node Click
    cy.on("tap", "node", (evt: EventObject) => {
      const node = evt.target;
      const data: CytoscapeElementData = node.data();

      // Highlight 1-hop connected neighborhood
      cy.elements().removeClass("selected connected dimmed");
      node.addClass("selected");
      const connectedEdges = node.connectedEdges();
      connectedEdges.addClass("connected");
      const connectedNeighbors = connectedEdges.connectedNodes();
      connectedNeighbors.addClass("connected");
      cy.elements().not(node).not(connectedEdges).not(connectedNeighbors).addClass("dimmed");

      // Match evidence items mentioning this entity ID or properties
      const idSearch = data.id.replace(/^(CASE_|CUST_|ACC_|TX_|DEV_|IP_)/, "");
      const matchingEv = (evidenceData?.evidence || []).filter((ev) => {
        const fact = (ev.fact || "").toLowerCase();
        const ref = (ev.source_reference || "").toLowerCase();
        const search = idSearch.toLowerCase();
        return fact.includes(search) || ref.includes(search);
      });

      setSelectedEntity({
        type: "node",
        data,
        connectedDegree: node.degree(),
        matchingEvidence: matchingEv.map((e) => ({
          evidence_id: e.evidence_id,
          category: e.category,
          fact: e.fact,
        })),
      });
    });

    // Handle Edge Click
    cy.on("tap", "edge", (evt: EventObject) => {
      const edge = evt.target;
      const data: CytoscapeElementData = edge.data();

      cy.elements().removeClass("selected connected dimmed");
      edge.addClass("selected");
      const source = edge.source();
      const target = edge.target();
      source.addClass("connected");
      target.addClass("connected");
      cy.elements().not(edge).not(source).not(target).addClass("dimmed");

      setSelectedEntity({
        type: "edge",
        data,
      });
    });

    // Handle Background Click (Reset Selection)
    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        cy.elements().removeClass("selected connected dimmed");
        setSelectedEntity(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
  }, [graphData, evidenceData, currentLayout]);

  function getLayoutConfig(layout: LayoutType) {
    switch (layout) {
      case "concentric":
        return {
          name: "concentric",
          concentric: (node: any) => (node.data("type") === "CASE" ? 10 : 2),
          levelWidth: () => 1,
          padding: 30,
        };
      case "circle":
        return { name: "circle", padding: 30 };
      case "breadthfirst":
        return { name: "breadthfirst", directed: true, padding: 30 };
      case "cose":
      default:
        return {
          name: "cose",
          idealEdgeLength: () => 80,
          nodeOverlap: 20,
          refresh: 20,
          fit: true,
          padding: 30,
          randomize: false,
          componentSpacing: 100,
          nodeRepulsion: () => 400000,
          edgeElasticity: () => 100,
          nestingFactor: 5,
        };
    }
  }

  // Interactive controls
  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.25);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() * 0.8);
  const handleFit = () => cyRef.current?.fit(undefined, 30);
  const handleReset = () => {
    if (cyRef.current) {
      cyRef.current.reset();
      cyRef.current.fit(undefined, 30);
      cyRef.current.elements().removeClass("selected connected dimmed");
      setSelectedEntity(null);
    }
  };

  const handleLayoutChange = (l: LayoutType) => {
    setCurrentLayout(l);
    if (cyRef.current) {
      const layout = cyRef.current.layout(getLayoutConfig(l));
      layout.run();
    }
  };

  return (
    <div className="relative w-full h-full min-h-[500px] flex flex-col bg-brand-950 rounded-xl overflow-hidden border border-brand-700/60 glass-panel">
      {/* Top Toolbar */}
      <div className="p-3 border-b border-brand-700/60 bg-brand-900/60 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 z-10">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-orange-400" />
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            TigerGraph Fraud Network Subgraph
          </h4>
          <span className="text-[10px] font-mono text-slate-400">
            Case: {caseId}
          </span>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-2">
          {/* Layout Selector */}
          <div className="flex items-center gap-1.5 bg-brand-950 px-2 py-1 rounded-lg border border-brand-700 text-xs">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={currentLayout}
              onChange={(e) => handleLayoutChange(e.target.value as LayoutType)}
              className="bg-transparent text-slate-300 text-[11px] font-mono focus:outline-none cursor-pointer"
            >
              <option value="cose" className="bg-brand-900">cose (Force-Directed)</option>
              <option value="concentric" className="bg-brand-900">concentric (Focal Center)</option>
              <option value="breadthfirst" className="bg-brand-900">breadthfirst (Tree)</option>
              <option value="circle" className="bg-brand-900">circle (Radial)</option>
            </select>
          </div>

          {/* Zoom & Fit Actions */}
          <div className="flex items-center gap-1 bg-brand-950 p-0.5 rounded-lg border border-brand-700">
            <button
              onClick={handleZoomIn}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-brand-800 transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-brand-800 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleFit}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-brand-800 transition-colors"
              title="Fit to Screen"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleReset}
              className="p-1 text-slate-400 hover:text-white rounded hover:bg-brand-800 transition-colors"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Counts */}
          {graphData && (
            <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
              <span className="px-2 py-0.5 rounded bg-brand-800 border border-brand-700">
                Nodes: {graphData.nodes?.length ?? 0}
              </span>
              <span className="px-2 py-0.5 rounded bg-brand-800 border border-brand-700">
                Edges: {graphData.edges?.length ?? 0}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Cytoscape Canvas Container */}
      <div className="relative flex-1 w-full h-full min-h-[460px]">
        <div ref={containerRef} className="absolute inset-0 w-full h-full" />

        {/* Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-brand-950/85 backdrop-blur-md border border-brand-700/60 rounded-lg p-2.5 space-y-1.5 text-[10px] font-mono z-10 pointer-events-none select-none">
          <div className="text-[11px] font-bold text-slate-300 font-sans mb-1">
            Entity Legend
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-orange-500 shadow-sm" />
            <span className="text-slate-300">Case Investigation (Focal)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500 shadow-sm" />
            <span className="text-slate-300">Customer</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-indigo-500 shadow-sm" />
            <span className="text-slate-300">Account / Card</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rotate-45 bg-amber-500 shadow-sm" />
            <span className="text-slate-300">Trigger Transaction</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 shadow-sm" />
            <span className="text-slate-300">Device Fingerprint</span>
          </div>
        </div>

        {/* Selected Entity Inspection Drawer */}
        {selectedEntity && (
          <div className="absolute top-3 right-3 bottom-3 w-80 bg-brand-900/95 backdrop-blur-md border border-brand-700 rounded-xl shadow-2xl p-4 flex flex-col gap-3 overflow-y-auto z-20 animate-fade-in">
            <div className="flex items-center justify-between pb-2 border-b border-brand-700/60">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-cyan-400" />
                <h5 className="text-xs font-bold text-white uppercase tracking-wider">
                  Entity Inspector
                </h5>
              </div>
              <button
                onClick={() => {
                  setSelectedEntity(null);
                  cyRef.current?.elements().removeClass("selected connected dimmed");
                }}
                className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-brand-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Entity Badge & ID */}
            <div className="space-y-1">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-brand-800 text-cyan-300 border border-brand-700">
                {selectedEntity.data.type || "ENTITY"}
              </span>
              <p className="text-sm font-bold font-mono text-white mt-1 break-all">
                {selectedEntity.data.label || selectedEntity.data.id}
              </p>
              <p className="text-[11px] font-mono text-slate-400">
                ID: {selectedEntity.data.id}
              </p>
            </div>

            {/* Degree / Connections */}
            {selectedEntity.connectedDegree !== undefined && (
              <div className="p-2.5 rounded-lg bg-brand-950/70 border border-brand-800 flex items-center justify-between text-xs">
                <span className="text-slate-400">Connected Relationships:</span>
                <span className="font-mono font-bold text-cyan-400">
                  {selectedEntity.connectedDegree}
                </span>
              </div>
            )}

            {/* Properties Table */}
            {selectedEntity.data.properties &&
              Object.keys(selectedEntity.data.properties).length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Node Attributes
                  </span>
                  <div className="p-2.5 rounded-lg bg-brand-950/70 border border-brand-800 space-y-1 text-xs">
                    {Object.entries(selectedEntity.data.properties).map(([k, v]) => (
                      <div
                        key={k}
                        className="flex items-center justify-between text-[11px] font-mono"
                      >
                        <span className="text-slate-400">{k}:</span>
                        <span className="text-slate-200 font-semibold">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Matching Grounded Evidence */}
            {selectedEntity.matchingEvidence &&
              selectedEntity.matchingEvidence.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold text-orange-400 uppercase tracking-wider">
                    <FileText className="w-3.5 h-3.5" />
                    <span>Grounded Evidence ({selectedEntity.matchingEvidence.length})</span>
                  </div>
                  <div className="space-y-1.5">
                    {selectedEntity.matchingEvidence.map((ev) => (
                      <div
                        key={ev.evidence_id}
                        className="p-2.5 rounded-lg bg-orange-950/20 border border-orange-500/30 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px] font-mono">
                          <span className="text-orange-400 font-bold">{ev.evidence_id}</span>
                          <span className="text-slate-400">{ev.category}</span>
                        </div>
                        <p className="text-[11px] text-slate-200">{ev.fact}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>
        )}
      </div>
    </div>
  );
};
