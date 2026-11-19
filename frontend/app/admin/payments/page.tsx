"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert, Empty, Field, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { money, timeAgo } from "@/lib/format";

type Pay = { id: number; user: { name: string; email: string }; method: string; package_key: string; diamonds: number; amount_bdt: number; trx_id: string; sender_number: string; created_at: string };
type Free = { id: number; user: { name: string; email: string }; reason: string; balance: number; last_approved_at: string | null; created_at: string };

export default function AdminPayments() {
  const t = useTranslations("admin");
  const locale = useLocale();
  const [tab, setTab] = useState<"pay" | "free" | "gift">("pay");
  const [pays, setPays] = useState<Pay[] | null>(null);
  const [free, setFree] = useState<{ max_amount: number; items: Free[] } | null>(null);
  const [amounts, setAmounts] = useState<Record<number, number>>({});
  const [gift, setGift] = useState({ user: "", amount: "5", reason: "" });
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(() => {
    api<Pay[]>("/admin/payments").then(setPays).catch(() => setPays([]));
    api<{ max_amount: number; items: Free[] }>("/admin/free-requests").then(setFree).catch(() => undefined);
  }, []);
  useEffect(load, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setMsg(null);
    try { await fn(); setMsg({ kind: "ok", text: ok }); load(); } catch (e) { setMsg({ kind: "error", text: e instanceof ApiError ? e.message : "Error" }); }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">{t("nav.payments")}</h1><p className="text-sm text-slate-600">{t("pay.hint")}</p></div>
        <div className="flex rounded-xl bg-slate-200 p-1">
          {(["pay", "free", "gift"] as const).map((k) => (
            <button key={k} aria-pressed={tab === k} onClick={() => setTab(k)} className={`min-h-[40px] rounded-lg px-4 text-sm font-semibold ${tab === k ? "bg-white" : "text-slate-600"}`}>
              {t(`pay.tab.${k}`)}{k === "pay" && pays ? ` (${pays.length})` : k === "free" && free ? ` (${free.items.length})` : ""}
            </button>
          ))}
        </div>
      </div>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}

      {tab === "pay" && (!pays ? <Spinner /> : pays.length === 0 ? <Empty title={t("pay.empty")} /> : (
        <div className={`${card} overflow-x-auto`}>
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-slate-50 text-left text-slate-600"><tr>{["user", "package", "method", "trx", "time", ""].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h && t(`pay.col.${h}`)}</th>)}</tr></thead>
            <tbody>
              {pays.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-4 py-3"><b>{p.user.name}</b><br /><span className="text-slate-500">{p.user.email}</span></td>
                  <td className="px-4 py-3">{p.diamonds} ◆<br /><b>{money(p.amount_bdt, locale)}</b></td>
                  <td className="px-4 py-3">{p.method}</td>
                  <td className="px-4 py-3 font-mono">{p.trx_id}<br /><span className="font-sans text-slate-500">{p.sender_number}</span></td>
                  <td className="px-4 py-3 text-slate-500">{timeAgo(p.created_at, locale)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    <button className={btn.ghost} onClick={() => act(() => api(`/admin/payments/${p.id}/reject`, { method: "POST", body: {} }), t("pay.rejected"))}>{t("reject")}</button>{" "}
                    <button className={btn.primary} onClick={() => act(() => api(`/admin/payments/${p.id}/approve`, { method: "POST" }), t("pay.approved"))}>{t("approve")}</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {tab === "free" && (!free ? <Spinner /> : free.items.length === 0 ? <Empty title={t("pay.emptyFree")} /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {free.items.map((r) => (
            <article key={r.id} className={`${card} flex flex-col gap-2 p-4`}>
              <div className="flex justify-between"><b>{r.user.name}</b><span className="text-sm text-slate-500">{timeAgo(r.created_at, locale)}</span></div>
              <p className="text-sm">“{r.reason}”</p>
              <p className="text-xs text-slate-500">{t("pay.lastBonus")}: {r.last_approved_at ? timeAgo(r.last_approved_at, locale) : t("never")}</p>
              <div className="flex items-end gap-2">
                <Field label={t("pay.amount", { max: free.max_amount })}>
                  <input type="number" min={1} max={free.max_amount} value={amounts[r.id] ?? free.max_amount} onChange={(e) => setAmounts((a) => ({ ...a, [r.id]: Number(e.target.value) }))} className={`${input} w-24`} />
                </Field>
                <button className={btn.ghost} onClick={() => act(() => api(`/admin/free-requests/${r.id}/reject`, { method: "POST", body: {} }), t("pay.rejected"))}>{t("reject")}</button>
                <button className={btn.primary} onClick={() => act(() => api(`/admin/free-requests/${r.id}/approve`, { method: "POST", body: { amount: amounts[r.id] ?? free.max_amount } }), t("pay.approved"))}>{t("approve")}</button>
              </div>
            </article>
          ))}
        </div>
      ))}

      {tab === "gift" && (
        <form className={`${card} flex max-w-lg flex-col gap-3 p-5`}
          onSubmit={(e) => { e.preventDefault(); act(() => api("/admin/gift", { method: "POST", body: { ...gift, amount: Number(gift.amount) } }), t("pay.gifted")); }}>
          <Field label={t("pay.giftUser")}><input required value={gift.user} onChange={(e) => setGift({ ...gift, user: e.target.value })} className={input} /></Field>
          <Field label={t("pay.giftAmount")}><input required type="number" min={1} max={1000} value={gift.amount} onChange={(e) => setGift({ ...gift, amount: e.target.value })} className={input} /></Field>
          <Field label={t("pay.giftReason")}><input required minLength={3} value={gift.reason} onChange={(e) => setGift({ ...gift, reason: e.target.value })} className={input} /></Field>
          <button className={`${btn.primary} self-start`}>{t("pay.giftSend")}</button>
        </form>
      )}
    </div>
  );
}
