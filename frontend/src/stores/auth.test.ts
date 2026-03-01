import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const { mockApiFetch } = vi.hoisted(() => ({
  mockApiFetch: vi.fn(),
}));

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>(
    "@/api/client",
  );
  return { ...actual, apiFetch: mockApiFetch };
});

import { useAuthStore } from "./auth";

function resetStore() {
  useAuthStore.setState({
    token: null,
    user: null,
    loading: false,
    error: null,
    restored: false,
  });
}

describe("useAuthStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStore();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("login success sets token and user", async () => {
    const tokenRes = { access_token: "jwt-123", token_type: "bearer" };
    const userRes = {
      id: "u1",
      email: "test@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };

    mockApiFetch
      .mockResolvedValueOnce(tokenRes)
      .mockResolvedValueOnce(userRes);

    await useAuthStore.getState().login("test@example.com", "password123");

    const state = useAuthStore.getState();
    expect(state.token).toBe("jwt-123");
    expect(state.user).toEqual(userRes);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.restored).toBe(true);
  });

  it("login 401 sets auth.invalidCredentials error", async () => {
    mockApiFetch.mockRejectedValueOnce(new ApiError(401, "Unauthorized"));

    await useAuthStore.getState().login("bad@example.com", "wrong");

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBe("auth.invalidCredentials");
    expect(state.restored).toBe(true);
  });

  it("register success auto-calls login and sets token", async () => {
    const tokenRes = { access_token: "jwt-reg", token_type: "bearer" };
    const userRes = {
      id: "u2",
      email: "new@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };

    mockApiFetch
      .mockResolvedValueOnce(undefined)
      .mockResolvedValueOnce(tokenRes)
      .mockResolvedValueOnce(userRes);

    await useAuthStore
      .getState()
      .register("new@example.com", "password123", "invite-abc");

    const state = useAuthStore.getState();
    expect(state.token).toBe("jwt-reg");
    expect(state.user).toEqual(userRes);
    expect(state.restored).toBe(true);
  });

  it("logout clears token and user and calls API logout", () => {
    useAuthStore.setState({
      token: "jwt-123",
      user: {
        id: "u1",
        email: "test@example.com",
        created_at: "2026-01-01T00:00:00Z",
      },
      restored: true,
    });

    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.error).toBeNull();
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/auth/logout", { method: "POST" });
  });

  it("restore success sets user and cookie-session token when empty", async () => {
    const userRes = {
      id: "u1",
      email: "test@example.com",
      created_at: "2026-01-01T00:00:00Z",
    };
    mockApiFetch.mockResolvedValueOnce(userRes);

    await useAuthStore.getState().restore();

    const state = useAuthStore.getState();
    expect(state.user).toEqual(userRes);
    expect(state.token).toBe("cookie-session");
    expect(state.restored).toBe(true);
    expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/auth/me");
  });

  it("restore failure clears token and user", async () => {
    useAuthStore.setState({ token: "expired-jwt" });
    mockApiFetch.mockRejectedValueOnce(new ApiError(401, "Unauthorized"));

    await useAuthStore.getState().restore();

    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.restored).toBe(true);
  });

  it("isAuthenticated returns true when token present, false otherwise", () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);

    useAuthStore.setState({ token: "jwt-123" });
    expect(useAuthStore.getState().isAuthenticated()).toBe(true);

    useAuthStore.setState({ token: null });
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
  });
});
