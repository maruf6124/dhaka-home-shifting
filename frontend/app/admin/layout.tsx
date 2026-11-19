"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { HomeIcon } from "@/components/icons";
import LanguageSwitch from "@/components/LanguageSwitch";
import { Spinner } from "@/components/ui";
import { useRequireUser } from "@/lib/useRequireUser";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("admin");
  const pathname = usePathname();
  const { user } = useRequireUser(true);
  if (!user?.is_admin) return <Spinner />;

  const links = [
    ["/admin", t("nav.dashboard")],
    ["/admin/kyc", t("nav.kyc")],
    ["/admin/payments", t("nav.payments")],
    ["/admin/reports", t("nav.reports")],
    ["/admin/users", t("nav.users")],
    ["/admin/settings", t("nav.settings")],
    ["/admin/audit", t("nav.audit")],
  ];

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <nav aria-label={t("menu")} className="flex flex-col gap-1 bg-slate-900 p-4 text-slate-200 lg:w-60 lg:flex-none">
        <div className="mb-3 flex items-center justify-between gap-2">
          <Link href="/" className="flex items-center gap-2 font-bold text-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700"><HomeIcon size={20} /></span>{t("title")}
          </Link>
        </div>
        <div className="flex flex-wrap gap-1 lg:flex-col">
          {links.map(([href, label]) => (
            <Link key={href} href={href} aria-current={pathname === href ? "page" : undefined}
              className={`flex min-h-[44px] items-center rounded-lg px-3 text-[15px] ${pathname === href ? "bg-slate-800 font-semibold text-white" : "hover:bg-slate-800"}`}>
              {label}
            </Link>
          ))}
        </div>
        <div className="mt-3 lg:mt-auto"><LanguageSwitch compact /></div>
      </nav>
      <main className="min-w-0 flex-1 p-4 sm:p-8">{children}</main>
    </div>
  );
}
