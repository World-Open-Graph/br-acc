import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";

// Mock heavy graph components
vi.mock("@/components/graph/GraphCanvas", () => ({
  GraphCanvas: () => <div data-testid="graph-canvas" />,
}));

vi.mock("@/components/graph/ControlsSidebar", () => ({
  ControlsSidebar: () => <div data-testid="controls-sidebar" />,
}));

vi.mock("@/components/entity/EntityDetail", () => ({
  EntityDetail: () => <div data-testid="entity-detail" />,
}));

// Mock react-resizable-panels (depends on DOM APIs not present in jsdom)
vi.mock("react-resizable-panels", () => ({
  Group: ({ children }: { children: React.ReactNode }) => <div data-testid="panel-group">{children}</div>,
  Panel: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Separator: () => <div />,
}));

// Mock useGraphData
const mockUseGraphData = vi.fn();
vi.mock("@/hooks/useGraphData", () => ({
  useGraphData: (...args: unknown[]) => mockUseGraphData(...args),
}));

// Mock graphExplorer store
vi.mock("@/stores/graphExplorer", () => ({
  useGraphExplorerStore: () => ({
    depth: 1,
    enabledTypes: new Set<string>(),
    enabledRelTypes: new Set<string>(),
    selectedNodeIds: new Set<string>(),
    sidebarCollapsed: false,
    detailPanelOpen: false,
    hoveredNodeId: null,
    hiddenNodeIds: new Set<string>(),
    layoutMode: "force" as const,
    reset: vi.fn(),
    toggleSidebar: vi.fn(),
    setDepth: vi.fn(),
    toggleType: vi.fn(),
    toggleRelType: vi.fn(),
    selectNode: vi.fn(),
    setHoveredNode: vi.fn(),
    setContextMenu: vi.fn(),
    setLayoutMode: vi.fn(),
    toggleFullscreen: vi.fn(),
  }),
}));

import { GraphExplorer } from "./GraphExplorer";

function renderGraphExplorer(path = "/graph") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/graph" element={<GraphExplorer />} />
        <Route path="/graph/:entityId" element={<GraphExplorer />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("GraphExplorer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing and shows no-data message", () => {
    mockUseGraphData.mockReturnValue({ data: null, loading: false, error: null });
    renderGraphExplorer();

    expect(screen.getByText("Nenhum dado de grafo dispon\u00EDvel.")).toBeInTheDocument();
  });

  it("shows graph canvas when data is available", () => {
    mockUseGraphData.mockReturnValue({
      data: {
        nodes: [{ id: "n1", label: "Test", type: "person", properties: {}, sources: [] }],
        edges: [],
      },
      loading: false,
      error: null,
    });

    renderGraphExplorer("/graph/entity-123");

    expect(screen.getByTestId("graph-canvas")).toBeInTheDocument();
  });
});
