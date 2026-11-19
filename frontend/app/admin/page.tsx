"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Spinner, card } from "@/components/ui";
import { api } from "@/lib/api";
import { digits, money } from "@/lib/format";

type Stats = {
  users: number; verified_providers: number; active_listings: number; pending_kyc: number; pending_payments: number;
  pending_free: number; open_reports: number; revenue_30d: number; diamonds_by_day: { date: string; diamonds: number }[];
};

export default function AdminDashboard() {
  const t = useTranslations("admin");
  const locale = useLocale();
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => { api<Stats>("/admin/stats").then(setS).catch(() => undefined); }, []);
  if (!s) return <Spinner />;
  const max = Math.max(1, ...s.diamonds_by_day.map((d) => d.diamonds));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">{t("nav.dashboard")}</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          [t("stat.users"), digits(s.users, locale)],
          [t("stat.providers"), digits(s.verified_providers, locale)],
          [t("stat.listings"), digits(s.active_listings, locale)],
          [t("stat.revenue"), money(s.revenue_30d, locale)],
        ].map(([l, v]) => (
          <div key={l} className={`${card} p-4`}><p className="text-sm text-slate-600">{l}</p><p className="text-2xl font-bold">{v}</p></div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-[3fr_2fr]">
        <section className={`${card} flex flex-col gap-3 p-5`}>
          <h2 className="font-bold">{t("chart")}</h2>
          <div role="img" aria-label={t("chartAlt")} className="flex h-48 items-end gap-1.5 border-b border-slate-200">
            {s.diamonds_by_day.map((d, i) => (
              <div key={d.date} title={`${d.date}: ${d.diamonds}`} className={`flex-1 rounded-t ${i === s.diamonds_by_day.length - 1 ? "bg-teal-700" : "bg-teal-200"}`}
                style={{ height: `${Math.max(2, (d.diamonds / max) * 100)}%` }} />
            ))}
          </div>
          <div className="flex justify-between text-xs text-slate-500"><span>{s.diamonds_by_day[0]?.date}</span><span>{t("today")}</span></div>
        </section>
        <section className="flex flex-col gap-3">
          {[
            ["/admin/kyc", t("q.kyc"), s.pending_kyc],
            ["/admin/payments", t("q.payments"), s.pending_payments + s.pending_free],
            ["/admin/reports", t("q.reports"), s.open_reports],
          ].map(([href, label, n]) => (
            <Link key={href as string} href={href as string} className={`${card} flex items-center justify-between p-4 hover:border-teal-600`}>
              <b>{label}</b><span className="text-2xl font-bold">{digits(n as number, locale)}</span>
            </Link>
          ))}
        </section>
      </div>
    </div>
  );
}
