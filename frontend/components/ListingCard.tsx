"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { money, num } from "@/lib/format";
import { BuildingIcon, CheckIcon, LockIcon } from "./icons";

export type Listing = {
  id: number;
  type: "entire_flat" | "sublet";
  area: { id: number; name: string; name_bn: string; name_en: string };
  title: string;
  description: string;
  rent: number;
  service_charge: number;
  advance_months: number;
  rooms: number;
  baths: number;
  size_sqft: number | null;
  floor: number | null;
  tenant_type: string;
  amenities: string[];
  available_from: string | null;
  images: string[];
  status: string;
  expires_at: string;
  created_at: string;
  owner: { id: number; verified: boolean; rating: { avg: number | null; count: number } | null };
  unlocked: boolean;
  is_owner: boolean;
  room_id?: number | null;
  private: { road_no: string; house_no: string; contact_phone: string } | null;
  stats?: { unlocks: number; open_reports: number };
};

export function areaName(a: Listing["area"], locale: string) {
  return locale === "en" ? a.name_en : a.name_bn;
}

export default function ListingCard({ item }: { item: Listing }) {
  const t = useTranslations("listing");
  const locale = useLocale();
  return (
    <Link href={`/rent/${item.id}`} className="group flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white hover:border-teal-600">
      <div className="relative flex h-40 items-center justify-center bg-teal-700 text-teal-100">
        {item.images[0] ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={item.images[0]} alt="" className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <BuildingIcon size={44} />
        )}
        {item.owner.verified && (
          <span className="absolute left-2.5 top-2.5 inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-bold text-green-800">
            <CheckIcon size={12} />{t("verified")}
          </span>
        )}
        <span className="absolute right-2.5 top-2.5 rounded-full bg-white/90 px-2 py-0.5 text-xs font-bold text-slate-800">
          {t(`type.${item.type}`)}
        </span>
      </div>
      <div className="flex flex-col gap-0.5 p-4">
        <span className="text-xl font-bold">
          {money(item.rent, locale)}<span className="text-[13px] font-normal text-slate-600">{t("perMonth")}</span>
        </span>
        <span className="line-clamp-1 text-[15px] font-semibold">{item.title}</span>
        <span className="text-sm text-slate-600">
          {t("roomsBaths", { rooms: num(item.rooms, locale), baths: num(item.baths, locale) })} · {t(`tenant.${item.tenant_type}`)}
        </span>
        <span className="mt-2 flex items-center gap-1.5 border-t border-slate-100 pt-2 text-[13px] text-slate-500">
          <LockIcon size={14} /><span className="blurred">Road 6, House 14</span> · {areaName(item.area, locale)}
        </span>
      </div>
    </Link>
  );
}
