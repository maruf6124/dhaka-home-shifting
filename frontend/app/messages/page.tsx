"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { BackIcon, SendIcon } from "@/components/icons";
import { Alert, Empty, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api, wsUrl } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useRequireUser } from "@/lib/useRequireUser";

type Room = {
  id: number; listing_type: string; listing_id: number; listing_title: string; i_am_owner: boolean;
  other: { id: number; name: string } | null; last_message: Msg | null; unread: number;
  blocked: boolean; blocked_by_other: boolean; updated_at: string;
};
type Msg = { id: number; room_id: number; sender_id: number; body: string; created_at: string };

function MessagesInner() {
  const t = useTranslations("chat");
  const tc = useTranslations("common");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const activeId = Number(params.get("room")) || null;
  const { user } = useRequireUser();
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<"online" | "connecting" | "offline">("connecting");
  const [error, setError] = useState("");
  const ws = useRef<WebSocket | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const loadRooms = useCallback(() => api<Room[]>("/chat/rooms").then(setRooms).catch(() => setRooms([])), []);
  useEffect(() => { if (user) loadRooms(); }, [user, loadRooms]);

  const loadHistory = useCallback(async (roomId: number) => {
    const list = await api<Msg[]>(`/chat/rooms/${roomId}/messages`);
    setMsgs(list);
    api(`/chat/rooms/${roomId}/read`, { method: "POST" }).catch(() => undefined);
  }, []);

  // Live connection with automatic reconnect (the free server may be asleep).
  useEffect(() => {
    if (!user || !activeId) return;
    let closed = false;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout>;
    let ping: ReturnType<typeof setInterval>;
    const connect = async () => {
      setStatus("connecting");
      try {
        await loadHistory(activeId);
        const { token } = await api<{ token: string }>("/auth/ws-token");
        if (closed) return;
        const sock = new WebSocket(wsUrl(`/ws/chat/${activeId}?token=${token}`));
        ws.current = sock;
        sock.onopen = () => { retry = 0; setStatus("online"); ping = setInterval(() => sock.readyState === 1 && sock.send(JSON.stringify({ type: "ping" })), 25000); };
        sock.onmessage = (ev) => {
          const data = JSON.parse(ev.data);
          if (data.type === "message") setMsgs((m) => (m.some((x) => x.id === data.message.id) ? m : [...m, data.message]));
          if (data.type === "error") setError(data.code);
        };
        sock.onclose = () => {
          clearInterval(ping);
          if (closed) return;
          setStatus("offline");
          timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++));
        };
      } catch {
        if (!closed) { setStatus("offline"); timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** retry++)); }
      }
    };
    connect();
    return () => { closed = true; clearTimeout(timer); clearInterval(ping); ws.current?.close(); };
  }, [user, activeId, loadHistory]);

  useEffect(() => { bottom.current?.scrollIntoView({ block: "end" }); }, [msgs]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body || !activeId) return;
    setDraft("");
    setError("");
    try {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "message", body }));
      } else {
        const m = await api<Msg>(`/chat/rooms/${activeId}/messages`, { method: "POST", body: { body } });
        setMsgs((list) => [...list, m]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : tc("error"));
      setDraft(body);
    }
  };

  if (!user || rooms === null) return <Spinner />;
  const active = rooms.find((r) => r.id === activeId) || null;

  const toggleBlock = async () => {
    if (!active) return;
    await api(`/chat/rooms/${active.id}/block?blocked=${!active.blocked}`, { method: "POST" });
    loadRooms();
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-150px)] max-w-6xl gap-4 px-4 py-4 lg:h-[calc(100vh-90px)]">
      <section aria-label={t("conversations")} className={`${card} ${active ? "hidden md:flex" : "flex"} w-full flex-col overflow-hidden md:w-80 md:flex-none`}>
        <h1 className="border-b border-slate-100 px-4 py-3 text-xl font-bold">{t("title")}</h1>
        {rooms.length === 0 ? (
          <div className="p-4"><Empty title={t("empty")}><p className="text-sm text-slate-600">{t("emptyHint")}</p><Link href="/rent" className={btn.outline}>{t("browse")}</Link></Empty></div>
        ) : (
          <ul className="overflow-y-auto">
            {rooms.map((r) => (
              <li key={r.id}>
                <button onClick={() => router.push(`/messages?room=${r.id}`)} aria-current={r.id === activeId}
                  className={`flex w-full gap-3 border-b border-slate-100 px-4 py-3 text-left ${r.id === activeId ? "bg-teal-50 shadow-[inset_3px_0_0_#0F766E]" : "hover:bg-slate-50"}`}>
                  <span className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-teal-700 font-bold text-white">{r.other?.name.slice(0, 1)}</span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span className="flex justify-between gap-2"><b className="truncate">{r.other?.name}</b><span className="flex-none text-xs text-slate-500">{timeAgo(r.updated_at, locale)}</span></span>
                    <span className="truncate text-xs font-semibold text-teal-700">{r.listing_title}</span>
                    <span className="truncate text-sm text-slate-600">{r.last_message?.body || t("noMessages")}</span>
                  </span>
                  {r.unread > 0 && r.id !== activeId && <span className="flex h-6 min-w-6 flex-none items-center justify-center self-center rounded-full bg-teal-700 px-1.5 text-xs font-bold text-white">{r.unread}</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {active ? (
        <section aria-label={t("chat")} className={`${card} flex min-w-0 flex-1 flex-col overflow-hidden`}>
          <div className="flex items-center gap-3 border-b border-slate-100 px-3 py-2.5">
            <button onClick={() => router.push("/messages")} aria-label={tc("back")} className="flex h-11 w-11 items-center justify-center md:hidden"><BackIcon /></button>
            <div className="flex min-w-0 flex-1 flex-col">
              <b className="truncate">{active.other?.name}</b>
              <Link href={`/rent/${active.listing_id}`} className="truncate text-xs font-semibold text-teal-700">{active.listing_title}</Link>
            </div>
            <span className={`text-xs ${status === "online" ? "text-green-700" : "text-amber-700"}`}>{t(`status.${status}`)}</span>
            <button onClick={toggleBlock} className="min-h-[40px] rounded-lg px-2 text-sm text-red-700 hover:bg-red-50">{active.blocked ? t("unblock") : t("block")}</button>
          </div>
          <div className="flex flex-1 flex-col gap-2 overflow-y-auto bg-slate-50 p-4">
            <p className="self-center rounded-full bg-slate-200 px-3 py-0.5 text-xs text-slate-600">{t("opened")}</p>
            {msgs.map((m) => {
              const mine = m.sender_id === user.id;
              return (
                <div key={m.id} className={`max-w-[75%] rounded-2xl px-3.5 py-2 text-[15px] leading-relaxed ${mine ? "self-end rounded-br-md bg-teal-700 text-white" : "self-start rounded-bl-md border border-slate-200 bg-white"}`}>
                  <p className="whitespace-pre-wrap break-words">{m.body}</p>
                  <p className={`text-right text-[11px] ${mine ? "text-teal-100" : "text-slate-500"}`}>{timeAgo(m.created_at, locale)}</p>
                </div>
              );
            })}
            <div ref={bottom} />
          </div>
          {error && <div className="px-3 pt-2"><Alert>{error === "blocked" ? t("blockedMsg") : error}</Alert></div>}
          {active.blocked || active.blocked_by_other ? (
            <p className="border-t border-slate-100 p-4 text-center text-sm text-slate-600">{t("blockedMsg")}</p>
          ) : (
            <form onSubmit={send} className="flex gap-2 border-t border-slate-100 p-3">
              <label className="flex-1"><span className="sr-only">{t("message")}</span>
                <input value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={2000} placeholder={t("placeholder")} className={input} />
              </label>
              <button aria-label={t("send")} className="flex h-12 w-12 flex-none items-center justify-center rounded-xl bg-teal-700 text-white"><SendIcon /></button>
            </form>
          )}
        </section>
      ) : (
        <section className={`${card} hidden flex-1 items-center justify-center text-slate-500 md:flex`}>{t("pick")}</section>
      )}
    </div>
  );
}

export default function MessagesPage() {
  return <Suspense><MessagesInner /></Suspense>;
}
