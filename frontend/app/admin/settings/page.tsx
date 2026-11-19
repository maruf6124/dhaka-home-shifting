"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Alert, Field, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

type Pkg = { key: string; diamonds: number; price: number; active: boolean };
type S = {
  packages: Pkg[]; costs: Record<string, number>; welcome_bonus: number; free_bonus_max: number; free_bonus_cooldown_days: number;
  report_hide_threshold: number; rent_expiry_days: number; other_expiry_days: number; no_reply_refund_hours: number;
  delete_refund_hours: number; warnings_before_ban: number; payment_numbers: { bkash: string; nagad: string };
};
const NUMBERS = ["welcome_bonus", "free_bonus_max", "free_bonus_cooldown_days", "report_hide_threshold", "rent_expiry_days", "no_reply_refund_hours", "delete_refund_hours", "warnings_before_ban"] as const;

export default function AdminSettings() {
  const t = useTranslations("admin");
  const [s, setS] = useState<S | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  useEffect(() => { api<S>("/admin/settings").then(setS).catch(() => undefined); }, []);
  if (!s) return <Spinner />;

  const save = async () => {
    setMsg(null);
    try {
      setS(await api<S>("/admin/settings", { method: "PUT", body: { values: s } }));
      setMsg({ kind: "ok", text: t("set.saved") });
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : "Error" });
    }
  };

  const setPkg = (i: number, k: keyof Pkg, v: string | boolean) =>
    setS({ ...s, packages: s.packages.map((p, j) => (j === i ? { ...p, [k]: typeof v === "boolean" ? v : Number(v) } : p)) });

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">{t("nav.settings")}</h1><p className="text-sm text-slate-600">{t("set.hint")}</p></div>
        <button onClick={save} className={btn.primary}>{t("set.save")}</button>
      </div>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <div className="grid gap-4 xl:grid-cols-2">
        <section className={`${card} p-5`}>
          <h2 className="mb-3 font-bold">{t("set.packages")}</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-slate-600"><tr><th className="py-2">{t("set.name")}</th><th>{t("set.diamonds")}</th><th>{t("set.price")}</th><th>{t("set.active")}</th></tr></thead>
            <tbody>
              {s.packages.map((p, i) => (
                <tr key={p.key} className="border-t border-slate-100">
                  <td className="py-2">{p.key}</td>
                  <td><input aria-label={`${p.key} ${t("set.diamonds")}`} type="number" min={1} value={p.diamonds} onChange={(e) => setPkg(i, "diamonds", e.target.value)} className={`${input} w-24`} /></td>
                  <td><input aria-label={`${p.key} ${t("set.price")}`} type="number" min={1} value={p.price} onChange={(e) => setPkg(i, "price", e.target.value)} className={`${input} w-24`} /></td>
                  <td><input aria-label={`${p.key} ${t("set.active")}`} type="checkbox" checked={p.active} onChange={(e) => setPkg(i, "active", e.target.checked)} className="h-5 w-5 accent-teal-700" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section className={`${card} grid grid-cols-2 gap-3 p-5`}>
          <h2 className="col-span-2 font-bold">{t("set.costs")}</h2>
          {Object.entries(s.costs).map(([k, v]) => (
            <Field key={k} label={t(`set.cost.${k}`)}><input type="number" min={0} value={v} onChange={(e) => setS({ ...s, costs: { ...s.costs, [k]: Number(e.target.value) } })} className={input} /></Field>
          ))}
        </section>
        <section className={`${card} grid grid-cols-2 gap-3 p-5`}>
          <h2 className="col-span-2 font-bold">{t("set.rules")}</h2>
          {NUMBERS.map((k) => (
            <Field key={k} label={t(`set.${k}`)}><input type="number" min={0} value={s[k]} onChange={(e) => setS({ ...s, [k]: Number(e.target.value) })} className={input} /></Field>
          ))}
        </section>
        <section className={`${card} grid gap-3 p-5`}>
          <h2 className="font-bold">{t("set.numbers")}</h2>
          {(["bkash", "nagad"] as const).map((k) => (
            <Field key={k} label={k}><input value={s.payment_numbers[k]} onChange={(e) => setS({ ...s, payment_numbers: { ...s.payment_numbers, [k]: e.target.value } })} className={input} /></Field>
          ))}
        </section>
      </div>
    </div>
  );
}
