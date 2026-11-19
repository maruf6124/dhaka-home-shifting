"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import ListingCard, { type Listing } from "@/components/ListingCard";
import { BuildingIcon, SearchIcon, SofaIcon, SparkleIcon, TruckIcon } from "@/components/icons";
import { btn } from "@/components/ui";
import { api } from "@/lib/api";
import { areaOptions, useAreas } from "@/lib/areas";
import { digits } from "@/lib/format";

export default function HomePage() {
  const t = useTranslations("home");
  const locale = useLocale();
  const router = useRouter();
  const areas = useAreas();
  const [latest, setLatest] = useState<Listing[]>([]);
  const [area, setArea] = useState("");
  const [budget, setBudget] = useState("");
  const [type, setType] = useState("");

  useEffect(() => {
    api<{ items: Listing[] }>("/rent?page_size=4").then((r) => setLatest(r.items)).catch(() => undefined);
  }, [locale]);

  const search = (e: React.FormEvent) => {
    e.preventDefault();
    const q = new URLSearchParams();
    if (area) q.set("area_id", area);
    if (type) q.set("type", type);
    if (budget) q.set("max_rent", budget);
    router.push(`/rent?${q.toString()}`);
  };

  const services = [
    { href: "/rent", icon: <BuildingIcon size={26} />, color: "bg-teal-100 text-teal-700", key: "rent" },
    { href: "/coming-soon?s=shifting", icon: <TruckIcon size={26} />, color: "bg-blue-100 text-blue-700", key: "shifting" },
    { href: "/coming-soon?s=goods", icon: <SofaIcon size={26} />, color: "bg-pink-100 text-pink-700", key: "goods" },
    { href: "/coming-soon?s=cleaning", icon: <SparkleIcon size={26} />, color: "bg-violet-100 text-violet-700", key: "cleaning" },
  ];

  return (
    <div>
      <section className="mx-auto grid max-w-6xl gap-8 px-4 pb-8 pt-10 lg:grid-cols-[3fr_2fr] lg:items-center lg:pt-14">
        <div className="flex flex-col gap-5">
          <span className="self-start rounded-full bg-teal-100 px-3 py-1 text-sm font-semibold text-teal-900">{t("badge")}</span>
          <h1 className="text-3xl font-bold leading-tight sm:text-[44px]">{t("title")}</h1>
          <p className="max-w-xl text-lg leading-relaxed text-slate-600">{t("subtitle")}</p>
          <form onSubmit={search} className="grid gap-2 rounded-2xl border border-slate-200 bg-white p-2.5 shadow-sm sm:grid-cols-[1fr_1fr_1fr_auto]">
            <label className="flex flex-col px-2 text-xs font-semibold text-slate-500">
              {t("type")}
              <select value={type} onChange={(e) => setType(e.target.value)} className="h-9 bg-transparent text-base text-slate-900 focus:outline-none">
                <option value="">{t("any")}</option>
                <option value="entire_flat">{t("entireFlat")}</option>
                <option value="sublet">{t("sublet")}</option>
              </select>
            </label>
            <label className="flex flex-col px-2 text-xs font-semibold text-slate-500 sm:border-l sm:border-slate-200">
              {t("area")}
              <select value={area} onChange={(e) => setArea(e.target.value)} className="h-9 bg-transparent text-base text-slate-900 focus:outline-none">
                <option value="">{t("allDhaka")}</option>
                {areaOptions(areas, locale).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
              </select>
            </label>
            <label className="flex flex-col px-2 text-xs font-semibold text-slate-500 sm:border-l sm:border-slate-200">
              {t("budget")}
              <select value={budget} onChange={(e) => setBudget(e.target.value)} className="h-9 bg-transparent text-base text-slate-900 focus:outline-none">
                <option value="">{t("any")}</option>
                {[10000, 15000, 25000, 40000].map((b) => <option key={b} value={b}>{t("upTo", { n: digits(b.toLocaleString("en-IN"), locale) })}</option>)}
              </select>
            </label>
            <button className={btn.primary}><SearchIcon />{t("search")}</button>
          </form>
        </div>
        <aside className="flex flex-col gap-4 rounded-3xl bg-slate-900 p-6 text-white">
          <h2 className="text-lg font-bold">{t("journeyTitle")}</h2>
          <ol className="flex flex-col gap-3">
            {(["j1", "j2", "j3", "j4"] as const).map((k, i) => (
              <li key={k} className="flex items-center gap-3 text-[15px] text-slate-200">
                <span className="flex h-8 w-8 flex-none items-center justify-center rounded-full border-2 border-teal-400 font-bold text-teal-300">{digits(i + 1, locale)}</span>
                {t(k)}
              </li>
            ))}
          </ol>
          <Link href="/rent" className="flex min-h-[48px] items-center justify-center rounded-xl bg-teal-400 font-bold text-teal-950">{t("startRent")}</Link>
        </aside>
      </section>

      <section className="mx-auto grid max-w-6xl grid-cols-2 gap-3 px-4 pb-8 lg:grid-cols-4">
        {services.map((s) => (
          <Link key={s.key} href={s.href} className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-5 hover:border-teal-600">
            <span className={`flex h-12 w-12 items-center justify-center rounded-xl ${s.color}`}>{s.icon}</span>
            <span className="text-lg font-bold">{t(`svc.${s.key}.title`)}</span>
            <span className="text-sm leading-relaxed text-slate-600">{t(`svc.${s.key}.desc`)}</span>
          </Link>
        ))}
      </section>

      {latest.length > 0 && (
        <section className="mx-auto max-w-6xl px-4 pb-10">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-2xl font-bold">{t("latest")}</h2>
            <Link href="/rent" className="font-semibold text-teal-700">{t("seeAll")}</Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {latest.map((l) => <ListingCard key={l.id} item={l} />)}
          </div>
        </section>
      )}

      <section className="border-y border-slate-200 bg-white">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 md:grid-cols-3">
          <h2 className="text-2xl font-bold md:col-span-3">{t("howTitle")}</h2>
          {(["h1", "h2", "h3"] as const).map((k, i) => (
            <div key={k} className="flex gap-3.5">
              <span className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl font-bold ${i === 1 ? "bg-amber-100 text-amber-900" : "bg-slate-100 text-teal-700"}`}>{digits(i + 1, locale)}</span>
              <div>
                <p className="text-[17px] font-bold">{t(`${k}.title`)}</p>
                <p className="text-[15px] leading-relaxed text-slate-600">{t(`${k}.desc`)}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
      <footer className="mx-auto flex max-w-6xl flex-wrap justify-between gap-3 px-4 py-6 text-sm text-slate-600">
        <span>{t("footer")}</span>
        <span>{t("footerNote")}</span>
      </footer>
    </div>
  );
}
