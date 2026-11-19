"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { digits } from "@/lib/format";
import LanguageSwitch from "./LanguageSwitch";
import { BellIcon, ChatIcon, Diamond, HomeIcon, PlusIcon, SearchIcon, UserIcon } from "./icons";

export default function Header() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [unread, setUnread] = useState(0);
  const [menu, setMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    const load = () => api<{ unread: number }>("/notifications").then((r) => setUnread(r.unread)).catch(() => undefined);
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [user, pathname]);

  useEffect(() => {
    const close = (e: MouseEvent) => menuRef.current && !menuRef.current.contains(e.target as Node) && setMenu(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  if (pathname.startsWith("/admin")) return null;

  const nav = [
    { href: "/rent", label: t("rent") },
    { href: "/coming-soon?s=shifting", label: t("shifting") },
    { href: "/coming-soon?s=goods", label: t("goods") },
    { href: "/coming-soon?s=cleaning", label: t("cleaning") },
  ];

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/" className="flex items-center gap-2.5 text-slate-900">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-700 text-white"><HomeIcon size={22} /></span>
            <span className="hidden text-[17px] font-bold sm:inline">{t("brand")}</span>
          </Link>
          <nav aria-label={t("services")} className="hidden flex-1 flex-wrap gap-1 lg:flex">
            {nav.map((n) => (
              <Link key={n.href} href={n.href}
                className={`flex min-h-[44px] items-center px-3 text-[15px] ${pathname === n.href ? "font-bold text-teal-700 shadow-[inset_0_-3px_0_#0F766E]" : "text-slate-700 hover:text-teal-700"}`}>
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <LanguageSwitch compact />
            {user ? (
              <>
                <Link href="/wallet" aria-label={t("balance", { n: user.balance })}
                  className="flex h-10 items-center gap-1.5 rounded-full bg-amber-100 px-3 font-bold text-amber-900">
                  <Diamond />{digits(user.balance, locale)}
                </Link>
                <Link href="/messages" aria-label={t("messages")} className="hidden h-11 w-11 items-center justify-center rounded-xl border border-slate-200 sm:flex"><ChatIcon /></Link>
                <Link href="/notifications" aria-label={t("notifications")} className="relative flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200">
                  <BellIcon />
                  {unread > 0 && <span className="absolute right-2 top-2 h-2.5 w-2.5 rounded-full bg-red-600" />}
                </Link>
                <div className="relative" ref={menuRef}>
                  <button onClick={() => setMenu((m) => !m)} aria-expanded={menu} aria-label={t("account")}
                    className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-100 font-bold text-teal-900">
                    {user.name.slice(0, 1)}
                  </button>
                  {menu && (
                    <div className="absolute right-0 top-12 w-56 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-xl">
                      <p className="truncate px-3 py-2 text-sm text-slate-500">{user.email}</p>
                      {[
                        ["/dashboard", t("dashboard")],
                        ["/wallet", t("wallet")],
                        ["/messages", t("messages")],
                        ["/become-provider", t("becomeProvider")],
                        ...(user.is_admin ? [["/admin", t("admin")]] : []),
                      ].map(([href, label]) => (
                        <Link key={href} href={href} onClick={() => setMenu(false)} className="flex min-h-[44px] items-center rounded-xl px-3 text-[15px] hover:bg-slate-50">{label}</Link>
                      ))}
                      <button onClick={async () => { setMenu(false); await logout(); router.push("/"); }}
                        className="flex min-h-[44px] w-full items-center rounded-xl px-3 text-left text-[15px] text-red-700 hover:bg-red-50">{t("logout")}</button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <Link href="/login" className="flex min-h-[44px] items-center rounded-xl border border-slate-300 px-4 font-semibold">{t("login")}</Link>
            )}
          </div>
        </div>
      </header>

      {/* Mobile bottom navigation */}
      <nav aria-label={t("mobileNav")} className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 items-center border-t border-slate-200 bg-white px-2 pb-2 pt-1 lg:hidden">
        {[
          { href: "/", label: t("home"), icon: <HomeIcon size={22} /> },
          { href: "/rent", label: t("search"), icon: <SearchIcon size={22} /> },
          { href: "/post", label: t("post"), icon: <PlusIcon size={24} />, main: true },
          { href: "/messages", label: t("messages"), icon: <ChatIcon size={22} /> },
          { href: user ? "/dashboard" : "/login", label: t("profile"), icon: <UserIcon size={22} /> },
        ].map((n) =>
          n.main ? (
            <Link key={n.href} href={n.href} aria-label={n.label} className="-mt-5 flex h-[52px] w-[52px] items-center justify-center justify-self-center rounded-2xl bg-teal-700 text-white shadow-lg shadow-teal-700/30">{n.icon}</Link>
          ) : (
            <Link key={n.href} href={n.href} className={`flex min-h-[48px] flex-col items-center justify-center gap-0.5 text-xs ${pathname === n.href ? "font-semibold text-teal-700" : "text-slate-500"}`}>
              {n.icon}{n.label}
            </Link>
          ),
        )}
      </nav>
    </>
  );
}
