import { create } from "zustand";

import { apiFetch, ApiError } from "@/api/client";

interface AuthUser {
  id: string;
  email: string;
  created_at: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  restored: boolean;

  isAuthenticated: () => boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
  restore: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  loading: false,
  error: null,
  restored: false,

  isAuthenticated: () => get().token !== null,

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const params = new URLSearchParams();
      params.set("username", email);
      params.set("password", password);

      const res = await apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: params.toString(),
      });

      set({ token: res.access_token, loading: false, restored: true });

      const user = await apiFetch<AuthUser>("/api/v1/auth/me");
      set({ user });
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 401
          ? "auth.invalidCredentials"
          : "auth.loginError";
      set({ token: null, user: null, loading: false, error: message, restored: true });
    }
  },

  register: async (email, password, inviteCode) => {
    set({ loading: true, error: null });
    try {
      await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          invite_code: inviteCode,
        }),
      });

      // Auto-login after registration
      await get().login(email, password);
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 403
          ? "auth.invalidInvite"
          : "auth.registerError";
      set({ loading: false, error: message });
    }
  },

  logout: () => {
    void Promise.resolve(
      apiFetch<void>("/api/v1/auth/logout", { method: "POST" }),
    ).catch(() => undefined);
    set({ token: null, user: null, error: null, restored: true });
  },

  restore: async () => {
    try {
      const user = await apiFetch<AuthUser>("/api/v1/auth/me");
      set((state) => ({ user, token: state.token ?? "cookie-session", restored: true }));
    } catch {
      set({ token: null, user: null, restored: true });
    }
  },
}));
