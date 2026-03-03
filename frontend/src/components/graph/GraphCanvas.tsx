import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D, {
  type ForceGraphMethods,
  type LinkObject,
  type NodeObject,
} from "react-force-graph-2d";
import { useTranslation } from "react-i18next";

import type { GraphData } from "@/api/client";
import { relationshipColors } from "@/styles/tokens";

import { ContextMenu } from "./ContextMenu";
import { EdgeDetail } from "./EdgeDetail";
import { NODE_COLORS } from "./graphConstants";
import { GraphLegend } from "./GraphLegend";
import { GraphMinimap } from "./GraphMinimap";
import { GraphToolbar } from "./GraphToolbar";
import { NodeTooltip } from "./NodeTooltip";
import { renderNode, getNodeSize } from "./nodeRendering";
import { ZoomControls } from "./ZoomControls";
import styles from "./GraphCanvas.module.css";

interface GraphCanvasProps {
  data: GraphData;
  centerId: string;
  enabledTypes: Set<string>;
  enabledRelTypes: Set<string>;
  hiddenNodeIds: Set<string>;
  selectedNodeIds: Set<string>;
  hoveredNodeId: string | null;
  layoutMode: "force" | "hierarchy";
  onNodeClick: (nodeId: string) => void;
  onNodeDeselect: () => void;
  onNodeHover: (nodeId: string | null) => void;
  onNodeRightClick: (x: number, y: number, nodeId: string) => void;
  onLayoutChange: (mode: "force" | "hierarchy") => void;
  onFullscreen: () => void;
  sidebarCollapsed: boolean;
}

interface GraphNodeObject extends NodeObject {
  id: string;
  label: string;
  type: string;
  connectionCount?: number;
  document_id?: string | null;
}

interface GraphLinkObject extends LinkObject {
  type: string;
  confidence?: number;
  value?: number;
  properties: Record<string, unknown>;
}

function GraphCanvasInner({
  data,
  centerId,
  enabledTypes,
  enabledRelTypes,
  hiddenNodeIds,
  selectedNodeIds,
  hoveredNodeId,
  layoutMode,
  onNodeClick,
  onNodeDeselect,
  onNodeHover,
  onNodeRightClick,
  onLayoutChange,
  onFullscreen,
  sidebarCollapsed,
}: GraphCanvasProps) {
  const { t } = useTranslation();
  const fgRef = useRef<ForceGraphMethods<GraphNodeObject, GraphLinkObject> | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [selectedEdge, setSelectedEdge] = useState<GraphLinkObject | null>(null);
  const [, setSearchQuery] = useState("");
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null);
  const zoomRef = useRef(1);

  // Track container dimensions via ResizeObserver
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width, height });
        }
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Tooltip state
  const [tooltip, setTooltip] = useState<{ node: GraphNodeObject; x: number; y: number } | null>(null);
  const tooltipTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Visible node IDs (for link visibility check)
  const visibleNodeIds = useMemo(
    () => new Set(
      data.nodes
        .filter((n) => enabledTypes.has(n.type) && !hiddenNodeIds.has(n.id))
        .map((n) => n.id),
    ),
    [data.nodes, enabledTypes, hiddenNodeIds],
  );

  // Connection counts based on visible edges, stored in ref to avoid destabilizing graphData.
  // Using useEffect to keep the ref in sync without causing graphData to change on filter toggles.
  const connectionCountsRef = useRef(new Map<string, number>());
  useEffect(() => {
    const counts = new Map<string, number>();
    for (const edge of data.edges) {
      if (
        visibleNodeIds.has(edge.source) &&
        visibleNodeIds.has(edge.target) &&
        enabledRelTypes.has(edge.type)
      ) {
        counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
        counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
      }
    }
    connectionCountsRef.current = counts;
  }, [data.edges, visibleNodeIds, enabledRelTypes]);

  // Stable graphData — only changes when underlying data changes, not on filter toggles.
  // This prevents d3-force simulation restarts when toggling type filters.
  const graphData = useMemo(
    () => ({
      nodes: data.nodes.map((n) => ({
        ...n,
        connectionCount: 0, // Updated via ref at render time
      })),
      links: data.edges.map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type,
        confidence: e.confidence,
        value: (e.properties as Record<string, unknown>)?.value as number | undefined,
        properties: e.properties,
      })),
    }),
    [data.nodes, data.edges],
  );

  // Visibility callbacks — hide/show without recreating the graph data
  const nodeVisibility = useCallback(
    (node: GraphNodeObject) =>
      enabledTypes.has(node.type) && !hiddenNodeIds.has(node.id),
    [enabledTypes, hiddenNodeIds],
  );

  const linkVisibility = useCallback(
    (link: GraphLinkObject) => {
      const src = typeof link.source === "object" ? (link.source as GraphNodeObject).id : (link.source as string);
      const tgt = typeof link.target === "object" ? (link.target as GraphNodeObject).id : (link.target as string);
      return (
        enabledRelTypes.has(link.type) &&
        visibleNodeIds.has(src) &&
        visibleNodeIds.has(tgt)
      );
    },
    [enabledRelTypes, visibleNodeIds],
  );

  // Configure d3 forces for better layout — only reheat when underlying data changes
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    const charge = fg.d3Force("charge") as { strength?: (s: number) => void } | undefined;
    charge?.strength?.(-200);
    const link = fg.d3Force("link") as { distance?: (d: number | ((l: unknown) => number)) => void } | undefined;
    link?.distance?.(100);
    fg.d3ReheatSimulation();
  }, [data]);

  // Adjacency set for hover dimming (use all edges, check visibility at render time)
  const adjacentToHovered = useMemo(() => {
    if (!hoveredNodeId) return null;
    const adj = new Set<string>([hoveredNodeId]);
    for (const edge of data.edges) {
      if (
        visibleNodeIds.has(edge.source) &&
        visibleNodeIds.has(edge.target) &&
        enabledRelTypes.has(edge.type)
      ) {
        if (edge.source === hoveredNodeId) adj.add(edge.target);
        if (edge.target === hoveredNodeId) adj.add(edge.source);
      }
    }
    return adj;
  }, [hoveredNodeId, data.edges, visibleNodeIds, enabledRelTypes]);

  // Minimap nodes — x/y are added at runtime by ForceGraph2D layout engine
  const minimapNodes = useMemo(
    () =>
      (graphData.nodes as (typeof graphData.nodes[number] & { x?: number; y?: number })[])
        .filter((n): n is typeof n & { x: number; y: number } =>
          n.x != null && n.y != null && visibleNodeIds.has(n.id),
        )
        .map((n) => ({ x: n.x, y: n.y, type: n.type })),
    [graphData, visibleNodeIds],
  );

  const nodeColor = useCallback((node: GraphNodeObject) => {
    return NODE_COLORS[node.type as keyof typeof NODE_COLORS] ?? "#5a6b60";
  }, []);

  const nodeSize = useCallback(
    (node: GraphNodeObject) => {
      const count = connectionCountsRef.current.get(node.id) ?? 0;
      return getNodeSize(count, node.id === centerId);
    },
    [centerId],
  );

  const linkColor = useCallback(
    (link: GraphLinkObject) => {
      if (adjacentToHovered) {
        const src = typeof link.source === "object" ? (link.source as GraphNodeObject).id : link.source;
        const tgt = typeof link.target === "object" ? (link.target as GraphNodeObject).id : link.target;
        if (!adjacentToHovered.has(src as string) && !adjacentToHovered.has(tgt as string)) {
          return "rgba(255, 255, 255, 0.03)";
        }
      }
      // Use relationship-type color with visible alpha
      const typeColor = relationshipColors[link.type];
      if (typeColor) {
        // Convert hex to rgba with 0.5 alpha
        const hex = typeColor.replace("#", "");
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, 0.7)`;
      }
      return "rgba(148, 163, 154, 0.5)";
    },
    [adjacentToHovered],
  );

  const linkWidth = useCallback((link: GraphLinkObject) => {
    const value = link.value ?? 0;
    const confidence = link.confidence ?? 1;
    const baseWidth = confidence >= 0.9 ? 2 : 1;
    return value > 0 ? baseWidth + Math.min(4, Math.log10(value + 1) * 0.6) : baseWidth;
  }, []);

  const linkLineDash = useCallback((link: GraphLinkObject) => {
    return (link.confidence ?? 1) < 0.9 ? [4, 2] : null;
  }, []);

  const handleNodeClick = useCallback(
    (node: GraphNodeObject) => {
      onNodeClick(node.id);
      setContextMenu(null);
    },
    [onNodeClick],
  );

  const handleNodeHover = useCallback(
    (node: GraphNodeObject | null) => {
      onNodeHover(node?.id ?? null);

      if (tooltipTimer.current) clearTimeout(tooltipTimer.current);

      if (node && node.x != null && node.y != null) {
        tooltipTimer.current = setTimeout(() => {
          // Convert graph coords to screen coords
          const screen = fgRef.current?.graph2ScreenCoords(node.x!, node.y!);
          if (screen) {
            const rect = containerRef.current?.getBoundingClientRect();
            const ox = rect?.left ?? 0;
            const oy = rect?.top ?? 0;
            setTooltip({ node, x: screen.x - ox + 12, y: screen.y - oy - 8 });
          }
        }, 200);
      } else {
        setTooltip(null);
      }
    },
    [onNodeHover],
  );

  const handleNodeRightClick = useCallback(
    (node: GraphNodeObject, event: MouseEvent) => {
      event.preventDefault();
      onNodeRightClick(event.clientX, event.clientY, node.id);
      setContextMenu({ x: event.clientX, y: event.clientY, nodeId: node.id });
    },
    [onNodeRightClick],
  );

  const handleBackgroundClick = useCallback(() => {
    onNodeDeselect();
    setContextMenu(null);
    setSelectedEdge(null);
  }, [onNodeDeselect]);

  const handleLinkClick = useCallback((link: GraphLinkObject) => {
    setSelectedEdge(link);
  }, []);

  const handleZoom = useCallback((transform: { k: number }) => {
    zoomRef.current = transform.k;
  }, []);

  const fittedRef = useRef(false);

  // Auto-fit once after initial layout
  useEffect(() => {
    fittedRef.current = false;
  }, [data]);

  const handleEngineStop = useCallback(() => {
    if (!fittedRef.current) {
      fittedRef.current = true;
      setTimeout(() => {
        fgRef.current?.zoomToFit(300, 50);
        // Defer pause until after zoomToFit animation completes
        setTimeout(() => fgRef.current?.pauseAnimation(), 350);
      }, 200);
    } else {
      fgRef.current?.pauseAnimation();
    }
  }, []);

  // Cleanup: pause animation on unmount to stop RAF loop surviving navigation
  useEffect(() => {
    const fg = fgRef.current;
    return () => { fg?.pauseAnimation(); };
  }, []);

  // Stable canvas render callback — avoids ForceGraph2D re-initializing render pipeline
  const nodeCanvasObjectMode = useCallback(() => "replace" as const, []);

  const nodeCanvasObject = useCallback(
    (node: GraphNodeObject, ctx: CanvasRenderingContext2D) => {
      if (node.x == null || node.y == null) return;
      const isDimmed = adjacentToHovered !== null && !adjacentToHovered.has(node.id);
      renderNode(ctx, {
        x: node.x,
        y: node.y,
        type: node.type,
        label: node.label,
        connectionCount: connectionCountsRef.current.get(node.id) ?? 0,
        isCenter: node.id === centerId,
        isSelected: selectedNodeIds.has(node.id),
        isHovered: hoveredNodeId === node.id,
        isDimmed,
        isPep: false,
        zoom: zoomRef.current,
      });
    },
    [adjacentToHovered, centerId, selectedNodeIds, hoveredNodeId],
  );

  const handleZoomIn = useCallback(() => fgRef.current?.zoom(zoomRef.current * 1.5, 300), []);
  const handleZoomOut = useCallback(() => fgRef.current?.zoom(zoomRef.current / 1.5, 300), []);
  const handleFitView = useCallback(() => fgRef.current?.zoomToFit(300, 40), []);
  const handleResetZoom = useCallback(() => fgRef.current?.zoom(1, 300), []);

  const handleExportPng = useCallback(() => {
    try {
      const canvas = containerRef.current?.querySelector("canvas") || wrapperRef.current?.querySelector("canvas");
      if (!canvas) return;

      const exportCanvas = document.createElement("canvas");
      exportCanvas.width = canvas.width;
      exportCanvas.height = canvas.height;
      const ctx = exportCanvas.getContext("2d");
      if (!ctx) return;

      // Draw background (matching the UI's dark background)
      ctx.fillStyle = "#060a07";
      ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

      // Draw the graph canvas on top
      ctx.drawImage(canvas, 0, 0);

      const link = document.createElement("a");
      link.download = `world-graph-export-${new Date().toISOString().split("T")[0]}.png`;
      link.href = exportCanvas.toDataURL("image/png");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch {
      // Silently fail or handle as needed
    }
  }, []);

  const handleFullscreenToggle = useCallback(() => {
    const elem = wrapperRef.current;
    if (!elem) return;

    if (!document.fullscreenElement) {
      elem.requestFullscreen().catch(() => {});
    } else if (document.exitFullscreen) {
      document.exitFullscreen().catch(() => {});
    }
    
    onFullscreen();
  }, [onFullscreen]);

  return (
    <div className={styles.canvas} ref={wrapperRef}>
      <GraphToolbar
        onSearch={setSearchQuery}
        layoutMode={layoutMode}
        onLayoutChange={onLayoutChange}
        onFullscreen={handleFullscreenToggle}
        onExportPng={handleExportPng}
      />

      <div ref={containerRef} className={styles.graphContainer}>
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          nodeVisibility={nodeVisibility}
          linkVisibility={linkVisibility}
          nodeColor={nodeColor}
          nodeVal={nodeSize}
          nodeLabel=""
          linkColor={linkColor}
          linkWidth={linkWidth}
          linkLineDash={linkLineDash}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={0.85}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onNodeRightClick={handleNodeRightClick}
          onBackgroundClick={handleBackgroundClick}
          onLinkClick={handleLinkClick}
          onZoom={handleZoom}
          backgroundColor="rgba(0,0,0,0)"
          linkDirectionalParticles={0}
          cooldownTime={4000}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.5}
          warmupTicks={30}
          onEngineStop={handleEngineStop}
          dagMode={layoutMode === "hierarchy" ? "td" : undefined}
          nodeCanvasObjectMode={nodeCanvasObjectMode}
          nodeCanvasObject={nodeCanvasObject}
        />

        <GraphLegend visible={sidebarCollapsed} />
        <GraphMinimap nodes={minimapNodes} />
        <ZoomControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onFitView={handleFitView}
          onResetZoom={handleResetZoom}
        />

        {tooltip && (
          <NodeTooltip
            node={{
              id: tooltip.node.id,
              label: tooltip.node.label,
              type: tooltip.node.type,
              connectionCount: tooltip.node.connectionCount ?? 0,
              document_id: tooltip.node.document_id ?? undefined,
            }}
            x={tooltip.x}
            y={tooltip.y}
          />
        )}

        {contextMenu && (
          <ContextMenu
            x={contextMenu.x}
            y={contextMenu.y}
            nodeId={contextMenu.nodeId}
            onClose={() => setContextMenu(null)}
            actions={[
              { id: "expand", label: t("graph.expand"), handler: () => setContextMenu(null) },
              { id: "hide", label: t("graph.hide"), handler: () => { setContextMenu(null); } },
              { id: "detail", label: t("graph.viewDetail"), handler: () => { onNodeClick(contextMenu.nodeId); setContextMenu(null); } },
            ]}
          />
        )}
      </div>

      {selectedEdge && (
        <EdgeDetail edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
      )}
    </div>
  );
}

export const GraphCanvas = memo(GraphCanvasInner);
