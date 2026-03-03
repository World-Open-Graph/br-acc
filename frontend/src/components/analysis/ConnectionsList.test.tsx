import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import "@/i18n";

import type { GraphNode } from "@/api/client";

import { ConnectionsList } from "./ConnectionsList";

const nodes: GraphNode[] = [
  { id: "center", label: "Center", type: "person", properties: {}, sources: [{ database: "TSE" }] },
  { id: "n1", label: "Company A", type: "company", properties: {}, sources: [{ database: "CNPJ" }] },
  { id: "n2", label: "Company B", type: "company", properties: {}, sources: [{ database: "CNPJ" }] },
  { id: "n3", label: "Person B", type: "person", properties: {}, sources: [{ database: "TSE" }] },
];

describe("ConnectionsList", () => {
  it("renders grouped connections excluding center", () => {
    render(
      <ConnectionsList
        nodes={nodes}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );
    expect(screen.getByText("Company A")).toBeInTheDocument();
    expect(screen.getByText("Company B")).toBeInTheDocument();
    expect(screen.getByText("Person B")).toBeInTheDocument();
    expect(screen.queryByText("Center")).not.toBeInTheDocument();
  });

  it("displays total connection count", () => {
    render(
      <ConnectionsList
        nodes={nodes}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("calls onSelectNode when item clicked", () => {
    const onSelect = vi.fn();
    render(
      <ConnectionsList
        nodes={nodes}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Company A"));
    expect(onSelect).toHaveBeenCalledWith("n1");
  });

  it("marks selected node", () => {
    render(
      <ConnectionsList
        nodes={nodes}
        centerId="center"
        selectedNodeId="n1"
        onSelectNode={vi.fn()}
      />,
    );
    const item = screen.getByText("Company A").closest("[role=option]");
    expect(item?.getAttribute("aria-selected")).toBe("true");
  });

  it("renders group headers with counts", () => {
    render(
      <ConnectionsList
        nodes={nodes}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );
    // company group has 2 nodes
    expect(screen.getByText("2")).toBeInTheDocument();
    // person group has 1 node
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("falls back to document id when label is empty", () => {
    const withBlankLabel: GraphNode[] = [
      ...nodes,
      {
        id: "n4",
        label: "   ",
        type: "contract",
        document_id: "CTR-001",
        properties: {},
        sources: [],
      },
    ];

    render(
      <ConnectionsList
        nodes={withBlankLabel}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );

    expect(screen.getByText("CTR-001")).toBeInTheDocument();
  });

  it("falls back to type and id when label and document id are empty", () => {
    const withNoName: GraphNode[] = [
      ...nodes,
      {
        id: "graph:node:42",
        label: "",
        type: "contract",
        properties: {},
        sources: [],
      },
    ];

    render(
      <ConnectionsList
        nodes={withNoName}
        centerId="center"
        selectedNodeId={null}
        onSelectNode={vi.fn()}
      />,
    );

    expect(screen.getByText(/#42$/)).toBeInTheDocument();
  });
});
