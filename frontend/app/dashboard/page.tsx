"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { BuildingIcon, Diamond, PlusIcon } from "@/components/icons";
import { Alert, Badge, Empty, Spinner, btn, card } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { dateText, digits, money } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";

type MyListing = { id: number; type: string; title: string; rent: number; area_bn: string; area_en: string; status: string; expired: boolean; expires_at: string; image: string | null };
type MyUnlock = { id: number; listing_id: number; title: string; room_id: number; refunded: boolean; refund_reason: string | null; created_at: string; link: string };
type OwnerReport = { id: number; listing_id: number; title: string; reason: string; note: string | null; created_at: string };

const statusTone: Record<string, "green" | "slate" | "amber" | "red"> = { active: "green", rented: "slate", expired: "amber", hidden: "red", removed: "red" };

export default function DashboardPage() {
  const t = useTranslations("dash");
  const tc = useTranslations("common");
  const locale = useLocale();
  const { user, reload } = useRequireUser();
  const [tab, setTab] = useState<"posts" | "unlocks" | "reports">("posts");
  const [posts, setPosts] = useState<MyListing[] | null>(null);
  const [unlocks, setUnlocks] = useState<MyUnlock[]>([]);
  const [reports, setReports] = useState<OwnerReport[]>([]);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(() => {
    api<MyListing[]>("/users/me/listings").then(setPosts).catch(() => setPosts([]));
    api<MyUnlock[]>("/unlocks/mine").then(setUnlocks).catch(() => undefined);
    api<OwnerReport[]>("/reports/on-my-listings").then(setReports).catch(() => undefined);
  }, []);
  useEffect(() => { if (user) load(); }, [user, load]);

  if (!user || posts === null) return <Spinner />;

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMsg(null);
    try {
      await fn();
      setMsg({ kind: "ok", text: ok });
      load();
      reload();
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : tc("error") });
    }
  };

  const roles = user.roles.filter((r) => r.role !== "client");

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5 px-4 py-6">
      <section className="flex flex-col gap-4 rounded-3xl bg-slate-900 p-6 text-white">
        <div className="flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-400 text-2xl font-bold text-teal-950">{user.name.slice(0, 1)}</span>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-xl font-bold">{user.name}</h1>
            <p className="truncate text-sm text-slate-300">{user.email} · {digits(user.phone, locale)}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="slate">{t("client")}</Badge>
          {roles.map((r) => <Badge key={r.role} tone={r.kyc_status === "verified" ? "green" : r.kyc_status === "pending" ? "amber" : "red"}>{t(`role.${r.role}`)} · {t(`kyc.${r.kyc_status}`)}</Badge>)}
          <Link href="/become-provider" className="rounded-full border border-dashed border-slate-500 px-2.5 py-0.5 text-xs font-bold text-slate-200">+ {t("addRole")}</Link>
        </div>
        <Link href="/wallet" className="flex items-center gap-2 self-start rounded-xl bg-slate-800 px-4 py-2 font-bold"><Diamond />{t("balance", { n: digits(user.balance, locale) })}</Link>
      </section>

      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      {reports.length > 0 && <Alert kind="warn">{t("reportsWaiting", { n: digits(reports.length, locale) })}</Alert>}

      <div role="tablist" className="flex gap-1 rounded-xl bg-slate-200 p-1 sm:self-start">
        {(["posts", "unlocks", "reports"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`min-h-[42px] flex-1 rounded-lg px-4 font-semibold sm:flex-none ${tab === k ? "bg-white shadow-sm" : "text-slate-600"}`}>{t(`tab.${k}`)}</button>
        ))}
      </div>

      {tab === "posts" && (
        posts.length === 0 ? (
          <Empty title={t("noPosts")}><Link href="/post" className={btn.primary}><PlusIcon />{t("newPost")}</Link></Empty>
        ) : (
          <div className="flex flex-col gap-3">
            <Link href="/post" className={`${btn.outline} self-start`}><PlusIcon />{t("newPost")}</Link>
            {posts.map((p) => {
              const status = p.expired && p.status === "active" ? "expired" : p.status;
              return (
                <article key={p.id} className={`${card} flex flex-wrap items-center gap-4 p-4`}>
                  <span className="flex h-16 w-16 flex-none items-center justify-center overflow-hidden rounded-xl bg-teal-700 text-teal-100">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    {p.image ? <img src={p.image} alt="" className="h-full w-full object-cover" /> : <BuildingIcon />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <Link href={`/rent/${p.id}`} className="font-bold hover:text-teal-700">{p.title}</Link>
                    <p className="text-sm text-slate-600">{money(p.rent, locale)} · {locale === "en" ? p.area_en : p.area_bn} · {t("expires", { d: dateText(p.expires_at, locale) })}</p>
                  </div>
                  <Badge tone={statusTone[status] || "slate"}>{t(`status.${status}`)}</Badge>
                  <div className="flex gap-2">
                    {status === "active" && <button className={btn.outline} onClick={() => act(() => api(`/rent/${p.id}/status`, { method: "POST", body: { status: "rented" } }), t("updated"))}>{t("markRented")}</button>}
                    {status === "rented" && <button className={btn.ghost} onClick={() => act(() => api(`/rent/${p.id}/status`, { method: "POST", body: { status: "active" } }), t("updated"))}>{t("reactivate")}</button>}
                    {status === "expired" && <button className={btn.outline} onClick={() => act(() => api(`/rent/${p.id}/renew`, { method: "POST" }), t("renewed"))}>{t("renew")}</button>}
                    <Link href={`/post?edit=${p.id}`} className={btn.ghost}>{t("edit")}</Link>
                  </div>
                </article>
              );
            })}
          </div>
        )
      )}

      {tab === "unlocks" && (
        unlocks.length === 0 ? <Empty title={t("noUnlocks")}><Link href="/rent" className={btn.outline}>{t("browse")}</Link></Empty> : (
          <ul className="flex flex-col gap-3">
            {unlocks.map((u) => {
              const old = Date.now() - new Date(u.created_at + "Z").getTime() > 48 * 3600 * 1000;
              return (
                <li key={u.id} className={`${card} flex flex-wrap items-center gap-3 p-4`}>
                  <div className="min-w-0 flex-1">
                    <Link href={u.link} className="font-bold hover:text-teal-700">{u.title}</Link>
                    <p className="text-sm text-slate-600">{dateText(u.created_at, locale)}{u.refunded && <> · <span className="font-semibold text-amber-800">{t("refunded")}</span></>}</p>
                  </div>
                  {!u.refunded && <Link href={`/messages?room=${u.room_id}`} className={btn.outline}>{t("chat")}</Link>}
                  {!u.refunded && old && (
                    <button className={btn.ghost} onClick={() => act(() => api(`/unlocks/${u.id}/claim-refund`, { method: "POST" }), t("refundOk"))}>{t("claimRefund")}</button>
                  )}
                </li>
              );
            })}
          </ul>
        )
      )}

      {tab === "reports" && (
        reports.length === 0 ? <Empty title={t("noReports")} /> : (
          <ul className="flex flex-col gap-3">
            {reports.map((r) => (
              <li key={r.id} className={`${card} flex flex-col gap-2 p-4`}>
                <b>{r.title}</b>
                <p className="text-sm text-slate-700">{t(`reason.${r.reason}`)}{r.note && <> — “{r.note}”</>}</p>
                {r.reason === "already_rented" && (
                  <button className={`${btn.outline} self-start`} onClick={() => act(() => api(`/reports/${r.id}/owner-confirm-rented`, { method: "POST" }), t("confirmedRented"))}>
                    {t("confirmRented")}
                  </button>
                )}
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  );
}
