"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert, Empty, Spinner, btn, card } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { timeAgo } from "@/lib/format";

type Group = {
  listing_type: string; listing_id: number; title: string; status: string; link: string;
  owner: { id: number; name: string; warnings: number }; unlockers: number;
  reports: { id: number; reason: string; note: string | null; created_at: string }[];
};

export default function AdminReports() {
  const t = useTranslations("admin");
  const td = useTranslations("detail");
  const locale = useLocale();
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const load = useCallback(() => api<Group[]>("/admin/reports").then(setGroups).catch(() => setGroups([])), []);
  useEffect(() => { load(); }, [load]);

  const act = async (g: Group, action: "confirm" | "dismiss") => {
    setMsg(null);
    try {
      const r = await api<{ refunded?: number }>(`/admin/reports/${g.listing_type}/${g.listing_id}/${action}`, { method: "POST", body: {} });
      setMsg({ kind: "ok", text: action === "confirm" ? t("rep.confirmed", { n: r.refunded ?? 0 }) : t("rep.dismissed") });
      load();
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : "Error" });
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div><h1 className="text-2xl font-bold">{t("nav.reports")}</h1><p className="text-sm text-slate-600">{t("rep.hint")}</p></div>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      {!groups ? <Spinner /> : groups.length === 0 ? <Empty title={t("rep.empty")} /> : groups.map((g) => (
        <article key={`${g.listing_type}-${g.listing_id}`} className={`${card} flex flex-col gap-3 p-5`}>
          <div className="flex flex-wrap justify-between gap-2">
            <div>
              <Link href={g.link} className="text-lg font-bold text-teal-800 underline">{g.title}</Link>
              <p className="text-sm text-slate-600">{t("rep.owner", { name: g.owner.name, w: g.owner.warnings })} · {t("rep.unlockers", { n: g.unlockers })} · {g.status}</p>
            </div>
            <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-bold text-red-800">{t("rep.count", { n: g.reports.length })}</span>
          </div>
          <ul className="flex flex-col gap-1.5">
            {g.reports.map((r) => (
              <li key={r.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm"><b className="text-red-700">{td(`reason.${r.reason}`)}</b>{r.note && <> — “{r.note}”</>} <span className="text-slate-500">· {timeAgo(r.created_at, locale)}</span></li>
            ))}
          </ul>
          <Alert kind="warn">{t("rep.effect", { n: g.unlockers })}</Alert>
          <div className="flex flex-wrap gap-2">
            <button className={btn.ghost} onClick={() => act(g, "dismiss")}>{t("rep.dismiss")}</button>
            <button className={btn.danger} onClick={() => act(g, "confirm")}>{t("rep.confirm")}</button>
          </div>
        </article>
      ))}
    </div>
  );
}
