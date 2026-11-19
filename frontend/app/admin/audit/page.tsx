"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Spinner, card } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";

type Log = { id: number; admin: string; action: string; target_type: string | null; target_id: number | null; details: Record<string, unknown>; created_at: string };

export default function AdminAudit() {
  const t = useTranslations("admin");
  const locale = useLocale();
  const [logs, setLogs] = useState<Log[] | null>(null);
  useEffect(() => { api<Log[]>("/admin/audit-logs").then(setLogs).catch(() => setLogs([])); }, []);
  if (!logs) return <Spinner />;
  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-bold">{t("nav.audit")}</h1>
      <div className={`${card} overflow-x-auto`}>
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-slate-50 text-left text-slate-600"><tr>{["time", "admin", "action", "details"].map((h) => <th key={h} className="px-4 py-3 font-semibold">{t(`audit.${h}`)}</th>)}</tr></thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t border-slate-100 align-top">
                <td className="whitespace-nowrap px-4 py-3 text-slate-500">{timeAgo(l.created_at, locale)}</td>
                <td className="px-4 py-3">{l.admin}</td>
                <td className="px-4 py-3 font-semibold">{l.action}{l.target_type && <span className="font-normal text-slate-500"> · {l.target_type} #{l.target_id}</span>}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{JSON.stringify(l.details)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
