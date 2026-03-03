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

import { Login } from "./Login";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

describe("Login", () => {
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

  it("renders login form", () => {
    renderLogin();

    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /entrar/i }),
    ).toBeInTheDocument();
  });

  it("has link to register page", () => {
    renderLogin();
    const link = screen.getByText(/registre-se/i);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/register");
  });

  it("submits login and calls store.login", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/e-mail/i), "test@example.com");
    await user.type(screen.getByLabelText(/senha/i), "password123");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
  });

  it("shows validation errors when submitting empty form", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(mockLogin).not.toHaveBeenCalled();
    expect(
      screen.getByText(/e-mail é obrigatório/i),
    ).toBeInTheDocument();
  });

  it("shows error from store", () => {
    mockStoreState.error = "auth.invalidCredentials";
    renderLogin();

    expect(
      screen.getByText(/e-mail ou senha incorretos/i),
    ).toBeInTheDocument();
  });

  it("disables submit button during loading", () => {
    mockStoreState.loading = true;
    renderLogin();

    const submitBtn = screen.getByRole("button", { name: /carregando/i });
    expect(submitBtn).toBeDisabled();
  });

  it("navigates to /app on success", async () => {
    const user = userEvent.setup();

    mockLogin.mockImplementation(() => {
      mockStoreState.token = "jwt-123";
      return Promise.resolve();
    });

    renderLogin();

    await user.type(screen.getByLabelText(/e-mail/i), "test@example.com");
    await user.type(screen.getByLabelText(/senha/i), "password123");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(mockNavigate).toHaveBeenCalledWith("/app");
  });
});
