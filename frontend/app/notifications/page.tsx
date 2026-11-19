"use client";

import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Empty, Spinner, card } from "@/components/ui";
import { api } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";

type N = { id: number; type: string; title: string; body: string; link: string | null; is_read: boolean; created_at: string };

export default function NotificationsPage() {
  const t = useTranslations("notif");
  const locale = useLocale();
  const { user } = useRequireUser();
  const [items, setItems] = useState<N[] | null>(null);

  useEffect(() => {
    if (!user) return;
    api<{ items: N[] }>("/notifications").then((r) => setItems(r.items)).catch(() => setItems([]));
  }, [user]);

  if (!items) return <Spinner />;

  const readAll = async () => {
    await api("/notifications/read-all", { method: "POST" });
    setItems((list) => list?.map((n) => ({ ...n, is_read: true })) ?? null);
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        {items.some((n) => !n.is_read) && <button onClick={readAll} className="min-h-[44px] font-semibold text-teal-700">{t("readAll")}</button>}
      </div>
      {items.length === 0 ? <Empty title={t("empty")} /> : (
        <ul className={`${card} overflow-hidden`}>
          {items.map((n) => {
            const inner = (
              <>
                <span className="flex-1">
                  <b className="block text-[15px]">{n.title}</b>
                  {n.body && <span className="block text-sm text-slate-600">{n.body}</span>}
                  <span className="text-xs text-slate-500">{timeAgo(n.created_at, locale)}</span>
                </span>
                {!n.is_read && <span className="mt-1.5 h-2.5 w-2.5 flex-none rounded-full bg-teal-700" aria-label={t("unread")} />}
              </>
            );
            const cls = `flex gap-3 border-b border-slate-100 px-4 py-3 ${n.is_read ? "" : "bg-teal-50"}`;
            return <li key={n.id}>{n.link ? <Link href={n.link} className={cls}>{inner}</Link> : <div className={cls}>{inner}</div>}</li>;
          })}
        </ul>
      )}
    </div>
  );
}
