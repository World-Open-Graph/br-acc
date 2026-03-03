import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
  initReactI18next: {
    type: "3rdParty",
    init: vi.fn(),
  },
}));

import type { GraphData } from "@/api/client";

// Polyfill for jsdom
if (typeof Element.prototype.requestFullscreen === "undefined") {
  Element.prototype.requestFullscreen = vi.fn().mockResolvedValue(undefined);
}
if (typeof document.exitFullscreen === "undefined") {
  document.exitFullscreen = vi.fn().mockResolvedValue(undefined);
}

let capturedProps: Record<string, unknown> = {};

vi.mock("react-force-graph-2d", () => ({
  __esModule: true,
  default: vi.fn((props: Record<string, unknown>) => {
    capturedProps = props;
    return <div data-testid="force-graph" />;
  }),
}));

import { GraphCanvas } from "./GraphCanvas";

const sampleData: GraphData = {
  nodes: [
    { id: "n1", label: "Node 1", type: "person", properties: {}, sources: [] },
    { id: "n2", label: "Node 2", type: "company", properties: {}, sources: [] },
    { id: "n3", label: "Node 3", type: "sanction", properties: {}, sources: [] },
  ],
  edges: [
    { id: "r1", source: "n1", target: "n2", type: "PARTNER", properties: {}, confidence: 1.0, sources: [] },
    { id: "r2", source: "n2", target: "n3", type: "SANCTIONED", properties: {}, confidence: 0.8, sources: [] },
  ],
};

const defaultProps = {
  data: sampleData,
  centerId: "n1",
  enabledTypes: new Set(["person", "company", "sanction"]),
  enabledRelTypes: new Set(["PARTNER", "SANCTIONED"]),
  hiddenNodeIds: new Set<string>(),
  selectedNodeIds: new Set<string>(),
  hoveredNodeId: null,
  layoutMode: "force" as const,
  onNodeClick: vi.fn(),
  onNodeDeselect: vi.fn(),
  onNodeHover: vi.fn(),
  onNodeRightClick: vi.fn(),
  onLayoutChange: vi.fn(),
  onFullscreen: vi.fn(),
  sidebarCollapsed: false,
};

describe("GraphCanvas", () => {
  it("renders ForceGraph2D component", () => {
    render(<GraphCanvas {...defaultProps} />);
    expect(screen.getByTestId("force-graph")).toBeInTheDocument();
  });

  it("passes graphData with correct nodes and links", () => {
    render(<GraphCanvas {...defaultProps} />);
    const graphData = capturedProps.graphData as { nodes: unknown[]; links: unknown[] };
    expect(graphData.nodes).toHaveLength(3);
    expect(graphData.links).toHaveLength(2);
  });

  it("uses nodeVisibility to filter by enabledTypes", () => {
    render(
      <GraphCanvas
        {...defaultProps}
        enabledTypes={new Set(["person", "company"])}
      />,
    );

    // graphData still contains all nodes (simulation stability)
    const graphData = capturedProps.graphData as { nodes: { id: string }[]; links: unknown[] };
    expect(graphData.nodes).toHaveLength(3);
    expect(graphData.links).toHaveLength(2);

    // nodeVisibility callback hides disabled types
    const nodeVis = capturedProps.nodeVisibility as (node: { id: string; type: string }) => boolean;
    expect(nodeVis({ id: "n1", type: "person" })).toBe(true);
    expect(nodeVis({ id: "n2", type: "company" })).toBe(true);
    expect(nodeVis({ id: "n3", type: "sanction" })).toBe(false);
  });

  it("invokes onNodeClick when node is clicked", () => {
    const onNodeClick = vi.fn();
    render(<GraphCanvas {...defaultProps} onNodeClick={onNodeClick} />);

    const handler = capturedProps.onNodeClick as (node: { id: string }) => void;
    handler({ id: "n2" });
    expect(onNodeClick).toHaveBeenCalledWith("n2");
  });

  it("invokes onFullscreen when toolbar fullscreen button is clicked", () => {
    const onFullscreen = vi.fn();
    render(<GraphCanvas {...defaultProps} onFullscreen={onFullscreen} />);
    
    // The GraphToolbar's onFullscreen is connected to handleFullscreenToggle
    // We can find the button by its title from i18n
    const fullscreenBtn = screen.getByTitle("graph.fullscreen");
    fullscreenBtn.click();
    
    expect(onFullscreen).toHaveBeenCalled();
  });
});
