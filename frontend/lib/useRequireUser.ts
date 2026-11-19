"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./auth";

/** Sends logged-out visitors to /login and brings them back afterwards. */
export function useRequireUser(admin = false) {
  const auth = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (auth.loading) return;
    if (!auth.user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (admin && !auth.user.is_admin) router.replace("/");
  }, [auth.loading, auth.user, admin, router, pathname]);
  return auth;
}
