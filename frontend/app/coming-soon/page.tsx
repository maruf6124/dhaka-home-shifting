"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense } from "react";
import { SofaIcon, SparkleIcon, TruckIcon } from "@/components/icons";
import { btn } from "@/components/ui";

function Inner() {
  const t = useTranslations("soon");
  const s = useSearchParams().get("s");
  const key = s === "goods" || s === "cleaning" ? s : "shifting";
  const icon = { shifting: <TruckIcon size={36} />, goods: <SofaIcon size={36} />, cleaning: <SparkleIcon size={36} /> }[key];
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center gap-4 px-4 py-16 text-center">
      <span className="flex h-20 w-20 items-center justify-center rounded-3xl bg-teal-100 text-teal-700">{icon}</span>
      <h1 className="text-3xl font-bold">{t(`${key}.title`)}</h1>
      <p className="text-[16px] leading-relaxed text-slate-600">{t(`${key}.desc`)}</p>
      <p className="rounded-full bg-amber-100 px-4 py-1 text-sm font-semibold text-amber-900">{t("badge")}</p>
      <Link href="/rent" className={btn.primary}>{t("cta")}</Link>
    </div>
  );
}

export default function ComingSoonPage() {
  return <Suspense><Inner /></Suspense>;
}
