"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { CheckIcon, ShieldIcon } from "@/components/icons";
import { Alert, Badge, Spinner, btn, card } from "@/components/ui";
import { ApiError, api, compressImage } from "@/lib/api";
import { useRequireUser } from "@/lib/useRequireUser";

type RoleKey = "landlord" | "driver" | "cleaner";
type Kyc = Record<RoleKey, { status: string; note: string | null; required: string[]; uploaded: string[] }>;

export default function BecomeProviderPage() {
  const t = useTranslations("kyc");
  const tc = useTranslations("common");
  const { user, reload } = useRequireUser();
  const [kyc, setKyc] = useState<Kyc | null>(null);
  const [role, setRole] = useState<RoleKey>("landlord");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const load = useCallback(() => api<Kyc>("/kyc").then(setKyc).catch(() => undefined), []);
  useEffect(() => { if (user) load(); }, [user, load]);

  if (!user || !kyc) return <Spinner />;
  const info = kyc[role];
  const locked = info.status === "pending" || info.status === "verified";
  const ready = info.required.every((d) => info.uploaded.includes(d));

  const upload = async (doc: string, file?: File) => {
    if (!file) return;
    setBusy(doc);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("role", role);
      fd.append("doc_type", doc);
      fd.append("file", file.type === "application/pdf" ? file : await compressImage(file, 2000, 0.9));
      await api("/kyc/documents", { method: "POST", body: fd });
      await load();
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : tc("error") });
    } finally {
      setBusy(null);
    }
  };

  const submit = async () => {
    setBusy("submit");
    setMsg(null);
    try {
      await api(`/kyc/${role}/submit`, { method: "POST" });
      setMsg({ kind: "ok", text: t("submitted") });
      await load();
      reload();
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : tc("error") });
    } finally {
      setBusy(null);
    }
  };

  const tone = { none: "slate", pending: "amber", verified: "green", rejected: "red" } as const;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 px-4 py-6">
      <div>
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="text-[15px] text-slate-600">{t("subtitle")}</p>
      </div>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}

      <fieldset className="grid grid-cols-3 gap-2">
        <legend className="mb-2 text-sm font-semibold">{t("whichRole")}</legend>
        {(["landlord", "driver", "cleaner"] as const).map((r) => (
          <button key={r} aria-pressed={role === r} onClick={() => setRole(r)}
            className={`flex min-h-[88px] flex-col items-center justify-center gap-1.5 rounded-2xl border-2 p-2 font-semibold ${role === r ? "border-teal-700 bg-teal-50" : "border-slate-200 bg-white"}`}>
            {t(`role.${r}`)}
            <Badge tone={tone[kyc[r].status as keyof typeof tone] || "slate"}>{t(`status.${kyc[r].status}`)}</Badge>
          </button>
        ))}
      </fieldset>
      {role !== "landlord" && <Alert kind="info">{t("comingNote")}</Alert>}
      {info.status === "rejected" && info.note && <Alert>{t("rejectedNote", { note: info.note })}</Alert>}

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold">{t("docs")}</h2>
        {info.required.map((doc) => {
          const done = info.uploaded.includes(doc);
          return (
            <div key={doc} className={`${card} flex items-center gap-3 p-3`}>
              <span className={`flex h-10 w-10 flex-none items-center justify-center rounded-xl ${done ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>{done ? <CheckIcon /> : "•"}</span>
              <span className="flex-1"><b className="block text-[15px]">{t(`doc.${doc}`)}</b><span className="text-xs text-slate-500">{t("fileHint")}</span></span>
              {!locked && (
                <label className={`${btn.outline} cursor-pointer text-sm`}>
                  {busy === doc ? t("uploading") : done ? t("replace") : t("upload")}
                  <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" className="sr-only" disabled={!!busy}
                    onChange={(e) => upload(doc, e.target.files?.[0])} />
                </label>
              )}
            </div>
          );
        })}
      </section>

      <div className="flex gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm leading-relaxed text-blue-900">
        <ShieldIcon size={20} />{t("privacy")}
      </div>
      {!locked && <button disabled={!ready || !!busy} onClick={submit} className={btn.primary}>{ready ? t("submit") : t("uploadAll")}</button>}
      {info.status === "pending" && <Alert kind="info">{t("pendingNote")}</Alert>}
      {info.status === "verified" && <Alert kind="ok">{t("verifiedNote")}</Alert>}
    </div>
  );
}
