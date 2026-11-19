"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import ListingCard, { type Listing } from "@/components/ListingCard";
import { PlusIcon } from "@/components/icons";
import { Empty, Spinner, btn, card, input } from "@/components/ui";
import { api } from "@/lib/api";
import { areaOptions, useAreas } from "@/lib/areas";
import { num } from "@/lib/format";

function RentInner() {
  const t = useTranslations("rent");
  const tl = useTranslations("listing");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const areas = useAreas();
  const [data, setData] = useState<{ items: Listing[]; total: number; page: number; page_size: number } | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const type = params.get("type") || "entire_flat";
  const query = params.toString();

  useEffect(() => {
    setData(null);
    const q = new URLSearchParams(query);
    if (!q.get("type")) q.set("type", "entire_flat");
    api(`/rent?${q.toString()}`).then(setData).catch(() => setData({ items: [], total: 0, page: 1, page_size: 12 }));
  }, [query, locale]);

  const update = (changes: Record<string, string | null>) => {
    const q = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(changes)) {
      if (v === null || v === "") q.delete(k);
      else q.set(k, v);
    }
    if (!("page" in changes)) q.delete("page");
    router.push(`${pathname}?${q.toString()}`);
  };

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const page = Number(params.get("page") || 1);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">{t("title")}</h1>
          <p className="text-[15px] text-slate-600">{t("subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" className="flex rounded-xl bg-slate-200 p-1">
            {(["entire_flat", "sublet"] as const).map((k) => (
              <button key={k} role="tab" aria-selected={type === k} onClick={() => update({ type: k })}
                className={`min-h-[42px] rounded-lg px-4 font-semibold ${type === k ? "bg-white shadow-sm" : "text-slate-600"}`}>
                {tl(`type.${k}`)}
              </button>
            ))}
          </div>
          <Link href={`/post?type=${type}`} className={btn.primary}><PlusIcon />{t(type === "sublet" ? "postSublet" : "postFlat")}</Link>
        </div>
      </div>

      <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <button onClick={() => setFiltersOpen((o) => !o)} aria-expanded={filtersOpen} className={`${btn.ghost} lg:hidden`}>{t("filters")}</button>
        <aside className={`${card} ${filtersOpen ? "flex" : "hidden"} flex-col gap-4 p-5 lg:flex lg:w-72 lg:flex-none`} aria-label={t("filters")}>
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold">{t("filters")}</span>
            <button onClick={() => router.push(`${pathname}?type=${type}`)} className="text-sm font-semibold text-teal-700">{t("clear")}</button>
          </div>
          <label className="flex flex-col gap-1.5 text-sm font-semibold">
            {t("area")}
            <select value={params.get("area_id") || ""} onChange={(e) => update({ area_id: e.target.value })} className={input}>
              <option value="">{t("allDhaka")}</option>
              {areaOptions(areas, locale).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="flex flex-col gap-1.5 text-sm font-semibold">{t("minRent")}
              <input type="number" min={0} defaultValue={params.get("min_rent") || ""} onBlur={(e) => update({ min_rent: e.target.value })} className={input} />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-semibold">{t("maxRent")}
              <input type="number" min={0} defaultValue={params.get("max_rent") || ""} onBlur={(e) => update({ max_rent: e.target.value })} className={input} />
            </label>
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-sm font-semibold">{t("rooms")}</legend>
            <div className="grid grid-cols-4 gap-1.5">
              {["1", "2", "3", "4"].map((r) => (
                <button key={r} aria-pressed={params.get("rooms") === r} onClick={() => update({ rooms: params.get("rooms") === r ? null : r })}
                  className={`min-h-[42px] rounded-lg border text-sm ${params.get("rooms") === r ? "border-2 border-teal-700 bg-teal-50 font-bold text-teal-900" : "border-slate-300 bg-white"}`}>
                  {num(Number(r), locale)}{r === "4" ? "+" : ""}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="flex flex-col gap-1.5 text-sm font-semibold">
            {t("tenantType")}
            <select value={params.get("tenant_type") || ""} onChange={(e) => update({ tenant_type: e.target.value })} className={input}>
              <option value="">{tl("tenant.any")}</option>
              {["family", "bachelor", "female"].map((k) => <option key={k} value={k}>{tl(`tenant.${k}`)}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2.5 text-[15px]">
            <input type="checkbox" checked={params.get("verified_only") === "true"} onChange={(e) => update({ verified_only: e.target.checked ? "true" : null })} className="h-[18px] w-[18px] accent-teal-700" />
            {t("verifiedOnly")}
          </label>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[15px] text-slate-600">{data ? t("count", { n: num(data.total, locale) }) : ""} · {t("unlockNote")}</span>
            <label className="flex items-center gap-2 text-sm text-slate-600">{t("sort")}
              <select value={params.get("sort") || "newest"} onChange={(e) => update({ sort: e.target.value })} className="min-h-[40px] rounded-lg border border-slate-300 bg-white px-2">
                <option value="newest">{t("newest")}</option>
                <option value="price_asc">{t("priceAsc")}</option>
                <option value="price_desc">{t("priceDesc")}</option>
              </select>
            </label>
          </div>
          {!data ? <Spinner /> : data.items.length === 0 ? (
            <Empty title={t("empty")}><p className="text-sm text-slate-600">{t("emptyHint")}</p></Empty>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {data.items.map((l) => <ListingCard key={l.id} item={l} />)}
            </div>
          )}
          {pages > 1 && (
            <nav aria-label={t("pagination")} className="flex items-center justify-center gap-2">
              <button disabled={page <= 1} onClick={() => update({ page: String(page - 1) })} className={btn.ghost}>{t("prev")}</button>
              <span className="px-2 text-sm">{num(page, locale)} / {num(pages, locale)}</span>
              <button disabled={page >= pages} onClick={() => update({ page: String(page + 1) })} className={btn.ghost}>{t("next")}</button>
            </nav>
          )}
        </section>
      </div>
    </div>
  );
}

export default function RentPage() {
  return <Suspense><RentInner /></Suspense>;
}
