"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Alert, Empty, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { timeAgo } from "@/lib/format";

type Item = {
  user: { id: number; name: string; email: string; phone: string };
  role: string; status: string; note: string | null; submitted_at: string;
  documents: { id: number; doc_type: string; content_type: string }[];
};

export default function AdminKyc() {
  const t = useTranslations("admin");
  const tk = useTranslations("kyc");
  const locale = useLocale();
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState<Item[] | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");

  const load = useCallback(() => api<Item[]>(`/admin/kyc?status=${status}`).then(setItems).catch(() => setItems([])), [status]);
  useEffect(() => { setItems(null); load(); }, [load]);

  const openDoc = async (id: number) => {
    const { url } = await api<{ url: string }>(`/admin/kyc/documents/${id}/url`);
    window.open(url.startsWith("/") ? `/api${url}` : url, "_blank", "noopener");
  };

  const decide = async (it: Item, ok: boolean) => {
    const key = `${it.user.id}-${it.role}`;
    try {
      await api(`/admin/kyc/${it.user.id}/${it.role}/${ok ? "approve" : "reject"}`, { method: "POST", body: { note: notes[key] || null } });
      setMsg(ok ? t("kyc.approved") : t("kyc.rejected"));
      load();
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Error");
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.kyc")}</h1>
        <div className="flex rounded-xl bg-slate-200 p-1">
          {["pending", "verified", "rejected"].map((s) => (
            <button key={s} aria-pressed={status === s} onClick={() => setStatus(s)} className={`min-h-[40px] rounded-lg px-4 text-sm font-semibold ${status === s ? "bg-white" : "text-slate-600"}`}>{tk(`status.${s}`)}</button>
          ))}
        </div>
      </div>
      {msg && <Alert kind="ok">{msg}</Alert>}
      {!items ? <Spinner /> : items.length === 0 ? <Empty title={t("kyc.empty")} /> : items.map((it) => {
        const key = `${it.user.id}-${it.role}`;
        return (
          <article key={key} className={`${card} flex flex-col gap-3 p-5`}>
            <div className="flex flex-wrap justify-between gap-2">
              <div><b className="text-lg">{it.user.name}</b> · {tk(`role.${it.role}`)}<p className="text-sm text-slate-600">{it.user.email} · {it.user.phone}</p></div>
              <span className="text-sm text-slate-500">{timeAgo(it.submitted_at, locale)}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {it.documents.map((d) => <button key={d.id} onClick={() => openDoc(d.id)} className={btn.ghost}>{tk(`doc.${d.doc_type}`)} ↗</button>)}
            </div>
            <p className="text-xs text-slate-500">{t("kyc.checklist")}</p>
            {status === "pending" && (
              <>
                <input value={notes[key] || ""} onChange={(e) => setNotes((n) => ({ ...n, [key]: e.target.value }))} placeholder={t("kyc.notePh")} className={input} />
                <div className="flex gap-2">
                  <button className={btn.danger} onClick={() => decide(it, false)}>{t("reject")}</button>
                  <button className={btn.primary} onClick={() => decide(it, true)}>{t("kyc.approve")}</button>
                </div>
              </>
            )}
            {it.note && <p className="text-sm text-slate-600">{t("note")}: {it.note}</p>}
          </article>
        );
      })}
    </div>
  );
}
