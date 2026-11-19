"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Diamond } from "@/components/icons";
import { Alert, Field, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { dateText, digits, money } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";

type Pkg = { key: string; diamonds: number; price: number };
type WalletInfo = {
  balance: number; paid_balance: number; bonus_balance: number; packages: Pkg[];
  payment_numbers: { bkash: string; nagad: string };
  free_bonus: { cooldown_days: number; last_request: { status: string; created_at: string } | null };
  pending_topups: { id: number; trx_id: string; diamonds: number; amount_bdt: number; created_at: string }[];
};
type Tx = { id: number; amount: number; kind: string; note: string | null; created_at: string };

export default function WalletPage() {
  const t = useTranslations("wallet");
  const tc = useTranslations("common");
  const locale = useLocale();
  const { user, reload } = useRequireUser();
  const [info, setInfo] = useState<WalletInfo | null>(null);
  const [tx, setTx] = useState<Tx[]>([]);
  const [pkg, setPkg] = useState("popular");
  const [method, setMethod] = useState<"bkash" | "nagad">("bkash");
  const [trx, setTrx] = useState("");
  const [sender, setSender] = useState("");
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<WalletInfo>("/wallet").then(setInfo).catch(() => undefined);
    api<Tx[]>("/wallet/transactions").then(setTx).catch(() => undefined);
  }, []);
  useEffect(() => { if (user) load(); }, [user, load]);

  if (!user || !info) return <Spinner />;
  const chosen = info.packages.find((p) => p.key === pkg) || info.packages[0];

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ kind: "ok", text: ok });
      load();
      reload();
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : tc("error") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6 lg:flex-row lg:items-start">
      <section className="flex min-w-0 flex-1 flex-col gap-5">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-slate-900 p-6 text-white">
          <div>
            <p className="text-sm text-slate-300">{t("total")}</p>
            <p className="flex items-center gap-2 text-4xl font-bold"><Diamond size={32} />{digits(info.balance, locale)}</p>
          </div>
          <div className="flex gap-6 text-[15px]">
            <div><span className="text-slate-300">{t("paid")}</span><b className="block text-2xl">{digits(info.paid_balance, locale)}</b></div>
            <div><span className="text-slate-300">{t("bonus")}</span><b className="block text-2xl">{digits(info.bonus_balance, locale)}</b></div>
          </div>
          <p className="w-full text-xs text-slate-400">{t("bonusFirst")}</p>
        </div>

        <div className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">{t("choose")}</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {info.packages.map((p) => (
              <button key={p.key} type="button" aria-pressed={pkg === p.key} onClick={() => setPkg(p.key)}
                className={`flex flex-col rounded-2xl border-2 p-4 text-left ${pkg === p.key ? "border-teal-700 bg-teal-50" : "border-slate-200 bg-white"}`}>
                <span className="text-sm text-slate-600">{t(`pkg.${p.key}`)}</span>
                <span className="text-xl font-bold">{t("diamonds", { n: digits(p.diamonds, locale) })}</span>
                <span className="font-bold text-teal-700">{money(p.price, locale)}</span>
                <span className="text-xs text-slate-500">{t("per", { v: digits((p.price / p.diamonds).toFixed(1), locale) })}</span>
              </button>
            ))}
          </div>
        </div>

        <form className={`${card} flex flex-col gap-4 p-5`}
          onSubmit={(e) => { e.preventDefault(); run(() => api("/wallet/topup", { method: "POST", body: { method, package_key: chosen.key, trx_id: trx, sender_number: sender } }).then(() => { setTrx(""); }), t("submitted")); }}>
          <div role="tablist" className="flex self-start rounded-xl bg-slate-100 p-1">
            {(["bkash", "nagad"] as const).map((m) => (
              <button key={m} type="button" role="tab" aria-selected={method === m} onClick={() => setMethod(m)}
                className={`min-h-[40px] rounded-lg px-5 font-semibold ${method === m ? "bg-white shadow-sm" : "text-slate-600"}`}>{t(m)}</button>
            ))}
          </div>
          <p className="text-[15px] leading-relaxed text-slate-700">
            {t.rich("howTo", { amount: money(chosen.price, locale), number: digits(info.payment_numbers[method], locale), b: (c) => <b>{c}</b> })}
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t("trx")}><input required minLength={6} maxLength={40} value={trx} onChange={(e) => setTrx(e.target.value)} className={`${input} uppercase`} placeholder="9GH7K2LQ1P" /></Field>
            <Field label={t("sender")}><input required value={sender} onChange={(e) => setSender(e.target.value)} className={input} inputMode="tel" placeholder="01XXXXXXXXX" /></Field>
          </div>
          <button disabled={busy} className={`${btn.primary} self-start`}>{t("send")}</button>
          {info.pending_topups.length > 0 && (
            <ul className="text-sm text-slate-600">
              {info.pending_topups.map((p) => <li key={p.id}>⏳ {t("pending", { trx: p.trx_id, n: digits(p.diamonds, locale) })}</li>)}
            </ul>
          )}
        </form>
      </section>

      <aside className="flex flex-col gap-4 lg:w-96 lg:pt-14">
        <div className={`${card} p-4`}>
          <h2 className="mb-2 text-lg font-bold">{t("history")}</h2>
          {tx.length === 0 ? <p className="text-sm text-slate-500">{t("noHistory")}</p> : (
            <ul>
              {tx.map((x) => (
                <li key={x.id} className="flex justify-between gap-3 border-t border-slate-100 py-2.5 first:border-0">
                  <span className="flex flex-col"><span className="text-[15px]">{t(`kind.${x.kind}`)}</span><span className="text-xs text-slate-500">{dateText(x.created_at, locale)}</span></span>
                  <b className={x.amount > 0 ? "text-green-700" : "text-red-700"}>{x.amount > 0 ? "+" : "−"}{digits(Math.abs(x.amount), locale)}</b>
                </li>
              ))}
            </ul>
          )}
        </div>
        <form className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4"
          onSubmit={(e) => { e.preventDefault(); run(() => api("/wallet/free-request", { method: "POST", body: { reason } }).then(() => setReason("")), t("freeSent")); }}>
          <h2 className="font-bold text-amber-950">{t("freeTitle")}</h2>
          <p className="text-sm text-amber-900">{t("freeRule", { d: digits(info.free_bonus.cooldown_days, locale) })}</p>
          {info.balance === 0 ? (
            <>
              <textarea required minLength={3} maxLength={300} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder={t("freeReason")} className={`${input} py-2`} />
              <button disabled={busy} className={btn.outline}>{t("freeSend")}</button>
            </>
          ) : <p className="text-sm font-semibold text-amber-900">{t("freeNotNow")}</p>}
        </form>
      </aside>
    </div>
  );
}
