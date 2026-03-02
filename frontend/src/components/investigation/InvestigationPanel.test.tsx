import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Investigation } from "@/api/client";

import "../../i18n";

// Mock the store before importing the component
const mockStore: {
  investigations: Investigation[];
  activeInvestigationId: string | null;
  loading: boolean;
  fetchInvestigations: ReturnType<typeof vi.fn>;
  createInvestigation: ReturnType<typeof vi.fn>;
  setActiveInvestigation: ReturnType<typeof vi.fn>;
} = {
  investigations: [],
  activeInvestigationId: null,
  loading: false,
  fetchInvestigations: vi.fn(),
  createInvestigation: vi.fn(),
  setActiveInvestigation: vi.fn(),
};

vi.mock("@/stores/investigation", () => ({
  useInvestigationStore: () => mockStore,
}));

import { InvestigationPanel } from "./InvestigationPanel";

describe("InvestigationPanel", () => {
  it("renders 'New Investigation' button", () => {
    render(<InvestigationPanel />);
    expect(screen.getByText(/Nova investigação/i)).toBeDefined();
  });

  it("renders investigation title when provided", () => {
    mockStore.investigations = [
      {
        id: "inv-1",
        title: "Test Investigation",
        description: "desc",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        entity_ids: ["e1", "e2"],
        share_token: null,
        share_expires_at: null,
      },
    ];

    render(<InvestigationPanel />);
    expect(screen.getByText("Test Investigation")).toBeDefined();
  });

  it("shows empty message when no investigations", () => {
    mockStore.investigations = [];

    render(<InvestigationPanel />);
    expect(screen.getByText(/Nenhuma investigação/i)).toBeDefined();
  });

  it("calls fetchInvestigations on mount", () => {
    render(<InvestigationPanel />);
    expect(mockStore.fetchInvestigations).toHaveBeenCalled();
  });
});
