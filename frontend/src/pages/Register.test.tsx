import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "@/i18n";

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock auth store
const mockLogin = vi.fn();
const mockRegister = vi.fn();
let mockStoreState = {
  login: mockLogin,
  register: mockRegister,
  loading: false,
  error: null as string | null,
  token: null as string | null,
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: Object.assign(
    (selector?: (state: typeof mockStoreState) => unknown) =>
      selector ? selector(mockStoreState) : mockStoreState,
    {
      getState: () => mockStoreState,
    },
  ),
}));

import { Register } from "./Register";

function renderRegister() {
  return render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>,
  );
}

describe("Register", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStoreState = {
      login: mockLogin,
      register: mockRegister,
      loading: false,
      error: null,
      token: null,
    };
  });

  it("renders registration form with all fields", () => {
    renderRegister();

    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^senha$/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/confirmar senha/i),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/c\u00F3digo de convite/i)).toBeInTheDocument();
  });

  it("shows email and password inputs with correct types", () => {
    renderRegister();

    const emailInput = screen.getByLabelText(/e-mail/i);
    const passwordInput = screen.getByLabelText(/^senha$/i);

    expect(emailInput).toHaveAttribute("type", "email");
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("has submit button that calls register", async () => {
    const user = userEvent.setup();
    renderRegister();

    const submitBtn = screen.getByRole("button", { name: /registrar/i });
    expect(submitBtn).toBeInTheDocument();

    await user.type(screen.getByLabelText(/e-mail/i), "test@example.com");
    await user.type(screen.getByLabelText(/^senha$/i), "password123");
    await user.type(
      screen.getByLabelText(/confirmar senha/i),
      "password123",
    );
    await user.type(screen.getByLabelText(/c\u00F3digo de convite/i), "INV-123");
    await user.click(submitBtn);

    expect(mockRegister).toHaveBeenCalledWith(
      "test@example.com",
      "password123",
      "INV-123",
    );
  });

  it("shows validation errors when submitting empty form", async () => {
    const user = userEvent.setup();
    renderRegister();

    await user.click(screen.getByRole("button", { name: /registrar/i }));

    expect(mockRegister).not.toHaveBeenCalled();
    expect(
      screen.getByText(/e-mail é obrigatório/i),
    ).toBeInTheDocument();
  });

  it("shows error from store", () => {
    mockStoreState.error = "auth.invalidInvite";
    renderRegister();

    expect(screen.getByText(/c\u00F3digo de convite inv\u00E1lido/i)).toBeInTheDocument();
  });

  it("disables submit button during loading", () => {
    mockStoreState.loading = true;
    renderRegister();

    const submitBtn = screen.getByRole("button", { name: /carregando/i });
    expect(submitBtn).toBeDisabled();
  });

  it("has link to login page", () => {
    renderRegister();
    const link = screen.getByText(/j\u00E1 tem conta\? entre/i);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/login");
  });
});
