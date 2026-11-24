import { useEffect, useState } from "react";
import { loadSession, saveSession, type Session } from "@/lib/api";
import type { User } from "@/lib/types";

export function useSession() {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  useEffect(() => {
    const sync = () => setSession(loadSession());
    window.addEventListener("atelier-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("atelier-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  return {
    session,
    user: session?.user ?? null,
    setUser(user: User) {
      if (!session) return;
      saveSession({ ...session, user });
    },
  };
}
