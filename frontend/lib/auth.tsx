"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type Role = { role: string; kyc_status: string; review_note?: string | null };
export type User = {
  id: number;
  name: string;
  email: string;
  phone: string;
  language: "bn" | "en";
  email_verified: boolean;
  roles: Role[];
  is_admin: boolean;
  balance: number;
  paid_balance: number;
  bonus_balance: number;
};

type AuthState = {
  user: User | null;
  loading: boolean;
  reload: () => Promise<void>;
  setUser: (u: User | null) => void;
  logout: () => Promise<void>;
  hasRole: (role: string) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      setUser(await api<User>("/auth/me"));
    } catch {
      // access token may have expired: try the refresh token once
      try {
        await api("/auth/refresh", { method: "POST" });
        setUser(await api<User>("/auth/me"));
      } catch {
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const logout = useCallback(async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (role: string) => !!user?.roles.some((r) => r.role === role && r.kyc_status === "verified"),
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, loading, reload, setUser, logout, hasRole }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
