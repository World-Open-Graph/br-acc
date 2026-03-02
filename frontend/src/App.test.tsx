import { act, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import "./i18n";

// Mock auth store — unauthenticated by default
vi.mock("./stores/auth", () => ({
  useAuthStore: Object.assign(
    (selector?: (state: Record<string, unknown>) => unknown) => {
      const state = {
        token: null,
        user: null,
        restored: true,
        restore: () => Promise.resolve(),
      };
      return selector ? selector(state) : state;
    },
    {
      getState: () => ({ token: null, restored: true }),
    },
  ),
}));

// Keep App route test deterministic without Landing async effects.
vi.mock("./pages/Landing", () => ({
  Landing: () => <div>BR-ACC</div>,
}));

import { App } from "./App";

describe("App", () => {
  it("renders the landing page with title", async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <App />
        </MemoryRouter>,
      );
    });
    await waitFor(() => {
      expect(screen.getAllByText("BR-ACC").length).toBeGreaterThan(0);
    });
  });

  it("renders login page at /login", async () => {
    await act(async () => {
      render(
        <MemoryRouter initialEntries={["/login"]}>
          <App />
        </MemoryRouter>,
      );
    });
    await waitFor(() => {
      expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument();
    });
  });
});
