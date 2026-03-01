import { create } from "zustand";

import { apiFetch, ApiError } from "@/api/client";

const STORAGE_KEY = "bracc_auth";

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

  isAuthenticated: () => boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
  restore: () => Promise<void>;
}

function loadPersistedToken(): string | null {
  try {
    // Persist tokens only in sessionStorage to limit exposure to XSS
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function persistToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem(STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // sessionStorage unavailable
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: loadPersistedToken(),
  user: null,
  loading: false,
  error: null,

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

      persistToken(res.access_token);
      set({ token: res.access_token, loading: false });

      const user = await apiFetch<AuthUser>("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${res.access_token}` },
      });
      set({ user });
    } catch (err) {
      persistToken(null);
      const message =
        err instanceof ApiError && err.status === 401
          ? "auth.invalidCredentials"
          : "auth.loginError";
      set({ token: null, user: null, loading: false, error: message });
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
    persistToken(null);
    set({ token: null, user: null, error: null });
  },

  restore: async () => {
    const token = get().token;
    if (!token) return;

    try {
      const user = await apiFetch<AuthUser>("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      set({ user });
    } catch {
      // Token expired or invalid
      persistToken(null);
      set({ token: null, user: null });
    }
  },
}));
