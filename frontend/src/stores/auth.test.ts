import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

// Must use vi.hoisted so the ref exists when vi.mock factory runs (hoisted)
const { mockApiFetch } = vi.hoisted(() => ({
  mockApiFetch: vi.fn(),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return { ...actual, apiFetch: mockApiFetch };
});

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(globalThis, "sessionStorage", {
  value: sessionStorageMock,
});

import { useAuthStore } from "./auth";

const STORAGE_KEY = "bracc_auth";

function resetStore() {
  useAuthStore.setState({
    token: null,
    user: null,
    loading: false,
    error: null,
  });
}

describe("useAuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorageMock.clear();
    resetStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("login success sets token and user, persists to sessionStorage", async () => {
    const tokenRes = { access_token: "jwt-123", token_type: "bearer" };
    const userRes = {
      id: "u1",
      email: "test@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };

    mockApiFetch
      .mockResolvedValueOnce(tokenRes) // login
      .mockResolvedValueOnce(userRes); // /auth/me

    await useAuthStore.getState().login("test@example.com", "password123");

    const state = useAuthStore.getState();
    expect(state.token).toBe("jwt-123");
    expect(state.user).toEqual(userRes);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
    expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
      STORAGE_KEY,
      "jwt-123",
    );
  });

  it("login 401 sets auth.invalidCredentials error", async () => {
    mockApiFetch.mockRejectedValueOnce(new ApiError(401, "Unauthorized"));

    await useAuthStore.getState().login("bad@example.com", "wrong");

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBe("auth.invalidCredentials");
  });

  it("login other error sets auth.loginError", async () => {
    mockApiFetch.mockRejectedValueOnce(
      new ApiError(500, "Internal Server Error"),
    );

    await useAuthStore.getState().login("test@example.com", "password123");

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.error).toBe("auth.loginError");
  });

  it("register success auto-calls login and sets token", async () => {
    const tokenRes = { access_token: "jwt-reg", token_type: "bearer" };
    const userRes = {
      id: "u2",
      email: "new@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };

    mockApiFetch
      .mockResolvedValueOnce(undefined) // register
      .mockResolvedValueOnce(tokenRes) // login
      .mockResolvedValueOnce(userRes); // /auth/me

    await useAuthStore
      .getState()
      .register("new@example.com", "password123", "invite-abc");

    const state = useAuthStore.getState();
    expect(state.token).toBe("jwt-reg");
    expect(state.user).toEqual(userRes);

    // First call was register
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: "new@example.com",
        password: "password123",
        invite_code: "invite-abc",
      }),
    });
  });

  it("register 403 sets auth.invalidInvite error", async () => {
    mockApiFetch.mockRejectedValueOnce(new ApiError(403, "Forbidden"));

    await useAuthStore
      .getState()
      .register("new@example.com", "password123", "bad-invite");

    const state = useAuthStore.getState();
    expect(state.loading).toBe(false);
    expect(state.error).toBe("auth.invalidInvite");
  });

  it("register other error sets auth.registerError", async () => {
    mockApiFetch.mockRejectedValueOnce(
      new ApiError(500, "Internal Server Error"),
    );

    await useAuthStore
      .getState()
      .register("new@example.com", "password123", "invite-abc");

    const state = useAuthStore.getState();
    expect(state.error).toBe("auth.registerError");
  });

  it("logout clears token, user, and sessionStorage", () => {
    useAuthStore.setState({
      token: "jwt-123",
      user: {
        id: "u1",
        email: "test@example.com",
        created_at: "2026-01-01T00:00:00Z",
      },
    });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.error).toBeNull();
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(STORAGE_KEY);
  });

  it("restore success validates cached token and sets user", async () => {
    const userRes = {
      id: "u1",
      email: "test@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };

    useAuthStore.setState({ token: "cached-jwt" });
    mockApiFetch.mockResolvedValueOnce(userRes);

    await useAuthStore.getState().restore();

    const state = useAuthStore.getState();
    expect(state.user).toEqual(userRes);
    expect(state.token).toBe("cached-jwt");
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/auth/me", {
      headers: { Authorization: "Bearer cached-jwt" },
    });
  });

  it("restore failure clears token and user", async () => {
    useAuthStore.setState({ token: "expired-jwt" });
    mockApiFetch.mockRejectedValueOnce(new ApiError(401, "Unauthorized"));

    await useAuthStore.getState().restore();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(STORAGE_KEY);
  });

  it("isAuthenticated returns true when token present, false otherwise", () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);

    useAuthStore.setState({ token: "jwt-123" });
    expect(useAuthStore.getState().isAuthenticated()).toBe(true);

    useAuthStore.setState({ token: null });
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
  });
});
