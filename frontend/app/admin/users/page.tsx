"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Badge, Spinner, btn, card, input } from "@/components/ui";
import { api } from "@/lib/api";
import { dateText } from "@/lib/format";

type U = { id: number; name: string; email: string; phone: string; verified: boolean; banned: boolean; warnings: number; balance: number; roles: { role: string; kyc_status: string }[]; created_at: string };

export default function AdminUsers() {
  const t = useTranslations("admin");
  const locale = useLocale();
  const [q, setQ] = useState("");
  const [users, setUsers] = useState<U[] | null>(null);
  const load = useCallback((query: string) => api<U[]>(`/admin/users?q=${encodeURIComponent(query)}`).then(setUsers).catch(() => setUsers([])), []);
  useEffect(() => { load(""); }, [load]);

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t("nav.users")}</h1>
      <form onSubmit={(e) => { e.preventDefault(); load(q); }} className="flex max-w-lg gap-2">
        <label className="flex-1"><span className="sr-only">{t("users.search")}</span><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("users.search")} className={input} /></label>
        <button className={btn.primary}>{t("users.find")}</button>
      </form>
      {!users ? <Spinner /> : (
        <div className={`${card} overflow-x-auto`}>
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-slate-50 text-left text-slate-600"><tr>{["name", "roles", "balance", "joined", ""].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h && t(`users.col.${h}`)}</th>)}</tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-3"><b>{u.name}</b> {u.banned && <Badge tone="red">{t("users.banned")}</Badge>}<br /><span className="text-slate-500">{u.email} · {u.phone}</span></td>
                  <td className="px-4 py-3">{u.roles.map((r) => <span key={r.role} className="mr-1 inline-block">{r.role}{r.kyc_status !== "verified" ? ` (${r.kyc_status})` : ""}</span>)}{u.warnings > 0 && <Badge tone="amber">⚠ {u.warnings}</Badge>}</td>
                  <td className="px-4 py-3">{u.balance} ◆</td>
                  <td className="px-4 py-3 text-slate-500">{dateText(u.created_at, locale)}</td>
                  <td className="px-4 py-3 text-right">
                    <button className={u.banned ? btn.ghost : btn.danger}
                      onClick={() => api(`/admin/users/${u.id}/ban?banned=${!u.banned}`, { method: "POST" }).then(() => load(q))}>
                      {u.banned ? t("users.unban") : t("users.ban")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
