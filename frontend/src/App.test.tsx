import { render, screen } from "@testing-library/react";
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

import { App } from "./App";

describe("App", () => {
  it("renders the landing page with title", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getAllByText("BRACC").length).toBeGreaterThan(0);
  });

  it("renders login page at /login", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument();
  });
});
