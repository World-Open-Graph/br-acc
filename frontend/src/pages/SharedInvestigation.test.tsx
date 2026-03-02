import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";

vi.mock("@/api/client", () => ({
  getSharedInvestigation: vi.fn(),
}));

import { getSharedInvestigation } from "@/api/client";
import { SharedInvestigation } from "./SharedInvestigation";

const mockGetSharedInvestigation = vi.mocked(getSharedInvestigation);

function renderSharedInvestigation(token = "abc-123") {
  return render(
    <MemoryRouter initialEntries={[`/shared/${token}`]}>
      <Routes>
        <Route path="/shared/:token" element={<SharedInvestigation />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SharedInvestigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockGetSharedInvestigation.mockReturnValue(new Promise(() => {}));
    renderSharedInvestigation();

    expect(screen.getByText("Carregando...")).toBeInTheDocument();
  });

  it("shows investigation data after successful fetch", async () => {
    mockGetSharedInvestigation.mockResolvedValue({
      id: "inv-1",
      title: "Investiga\u00E7\u00E3o Teste",
      description: "Uma descri\u00E7\u00E3o",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      entity_ids: ["e1", "e2"],
      share_token: "abc-123",
      share_expires_at: "2026-01-08T00:00:00Z",
    });

    renderSharedInvestigation();

    await waitFor(() => {
      expect(screen.getByText("Investiga\u00E7\u00E3o Teste")).toBeInTheDocument();
    });

    expect(screen.getByText("Uma descri\u00E7\u00E3o")).toBeInTheDocument();
    expect(screen.getByText("e1")).toBeInTheDocument();
    expect(screen.getByText("e2")).toBeInTheDocument();
  });

  it("shows error message when fetch fails", async () => {
    mockGetSharedInvestigation.mockRejectedValue(new Error("Not found"));

    renderSharedInvestigation();

    await waitFor(() => {
      expect(
        screen.getByText("Investiga\u00E7\u00E3o compartilhada n\u00E3o encontrada."),
      ).toBeInTheDocument();
    });
  });
});
