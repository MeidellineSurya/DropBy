import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import { api, restoreAccessToken, setAccessToken } from "./services/api";
import type { UserProfile } from "./types";

interface SessionValue {
  initializing: boolean;
  token: string | null;
  user: UserProfile | null;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string, displayName: string): Promise<void>;
  finishOnboarding(
    displayName: string,
    preferences: string[],
    permission: "denied" | "while_using" | "always",
  ): Promise<void>;
  logout(): Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: React.PropsWithChildren) {
  const [initializing, setInitializing] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    void (async () => {
      const stored = await restoreAccessToken();
      if (stored) {
        try {
          setUser(await api.me());
          setToken(stored);
        } catch {
          await setAccessToken(null);
        }
      }
      setInitializing(false);
    })();
  }, []);

  const value = useMemo<SessionValue>(
    () => ({
      initializing,
      token,
      user,
      async login(email, password) {
        const response = await api.login(email.trim().toLowerCase(), password);
        await setAccessToken(response.access_token);
        setToken(response.access_token);
        setUser(response.user);
      },
      async register(email, password, displayName) {
        const response = await api.register(
          email.trim().toLowerCase(),
          password,
          displayName.trim(),
        );
        await setAccessToken(response.access_token);
        setToken(response.access_token);
        setUser(response.user);
      },
      async finishOnboarding(displayName, preferences, permission) {
        const updated = await api.onboarding(
          displayName.trim(),
          preferences,
          permission,
        );
        setUser(updated);
      },
      async logout() {
        await setAccessToken(null);
        setToken(null);
        setUser(null);
      },
    }),
    [initializing, token, user],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
