import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";

vi.mock("@/api/client", () => ({
  getStats: vi.fn(),
}));

// Stub heavy visual components that depend on canvas/animation
vi.mock("@/components/landing/NetworkAnimation", () => ({
  NetworkAnimation: () => <div data-testid="network-animation" />,
}));

vi.mock("@/components/landing/HeroGraph", () => ({
  HeroGraph: () => <div data-testid="hero-graph" />,
}));

vi.mock("@/components/landing/StatsBar", () => ({
  StatsBar: () => <div data-testid="stats-bar" />,
}));

import { getStats } from "@/api/client";
import { Landing } from "./Landing";

const mockGetStats = vi.mocked(getStats);

function renderLanding() {
  return render(
    <MemoryRouter>
      <Landing />
    </MemoryRouter>,
  );
}

describe("Landing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStats.mockResolvedValue({
      total_nodes: 87_000_000,
      total_relationships: 53_000_000,
      person_count: 2_450_000,
      company_count: 58_500_000,
      health_count: 602_000,
      finance_count: 24_000_000,
      contract_count: 1_080_000,
      sanction_count: 69_000,
      election_count: 17_000,
      amendment_count: 98_000,
      embargo_count: 79_000,
      education_count: 224_000,
      convenio_count: 67_000,
      laborstats_count: 29_500,
      data_sources: 13,
    });
  });

  it("renders without crashing", async () => {
    await act(async () => {
      renderLanding();
    });
    // Hero heading should be rendered
    expect(screen.getByText("Siga o dinheiro p\u00FAblico")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("58.5M")).toBeInTheDocument();
    });
  });

  it("shows key heading text and CTA", async () => {
    await act(async () => {
      renderLanding();
    });
    expect(screen.getByText("Siga o dinheiro p\u00FAblico")).toBeInTheDocument();
    expect(screen.getByText("Explorar o grafo")).toBeInTheDocument();
    expect(screen.getByText("BR-ACC \u00B7 Dados abertos")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("58.5M")).toBeInTheDocument();
    });
  });

  it("shows all 13 data sources", async () => {
    await act(async () => {
      renderLanding();
    });

    await waitFor(() => {
      expect(screen.getByText("CNPJ")).toBeInTheDocument();
    });

    const sourceNames = [
      "CNPJ", "TSE", "Transpar\u00EAncia", "CEIS/CNEP", "DATASUS",
      "BNDES", "PGFN", "IBAMA", "ComprasNet", "TCU",
      "TransfereGov", "RAIS", "INEP",
    ];

    for (const name of sourceNames) {
      expect(screen.getByText(name)).toBeInTheDocument();
    }
  });
});
