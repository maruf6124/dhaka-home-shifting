"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { areaName, type Listing } from "@/components/ListingCard";
import { BuildingIcon, ChatIcon, CheckIcon, Diamond, FlagIcon, LockIcon } from "@/components/icons";
import { Alert, Badge, Modal, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { dateText, digits, money, num, timeAgo } from "@/lib/format";

export default function RentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations("detail");
  const tl = useTranslations("listing");
  const tc = useTranslations("common");
  const locale = useLocale();
  const router = useRouter();
  const { user, reload } = useAuth();
  const [item, setItem] = useState<Listing | null>(null);
  const [error, setError] = useState("");
  const [photo, setPhoto] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reason, setReason] = useState("already_rented");
  const [note, setNote] = useState("");
  const [rating, setRating] = useState(0);
  const [flash, setFlash] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Listing>(`/rent/${id}`).then(setItem).catch((e: ApiError) => setError(e.message));
  }, [id]);
  useEffect(load, [load, locale]);

  const act = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      if (ok) setFlash(ok);
      load();
      reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : tc("error"));
    } finally {
      setBusy(false);
    }
  };

  if (error && !item) return <div className="mx-auto max-w-3xl px-4 py-10"><Alert>{error}</Alert></div>;
  if (!item) return <Spinner />;

  const unlockCost = 1;
  const amenities = item.amenities.map((a) => tl(`amenity.${a}`)).join(" · ");

  const unlock = () =>
    act(async () => {
      await api("/unlocks", { method: "POST", body: { listing_type: "rent", listing_id: item.id } });
      setConfirm(false);
    }, t("unlockedFlash"));

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 px-4 py-6">
      <nav className="text-sm text-slate-500"><Link href="/" className="text-teal-700">{tc("home")}</Link> / <Link href="/rent" className="text-teal-700">{tl("rent")}</Link> / {areaName(item.area, locale)}</nav>
      {flash && <Alert kind="ok">{flash}</Alert>}
      {error && <Alert>{error}</Alert>}
      {item.status !== "active" && <Alert kind="warn">{t(`status.${item.status}`)}</Alert>}

      <div className="grid gap-2 md:grid-cols-[2fr_1fr]">
        <div className="flex aspect-[16/10] items-center justify-center overflow-hidden rounded-2xl bg-teal-700 text-teal-200">
          {item.images[photo] ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={item.images[photo]} alt={t("photoAlt", { n: photo + 1 })} className="h-full w-full object-cover" />
          ) : <BuildingIcon size={72} />}
        </div>
        {item.images.length > 1 && (
          <div className="grid grid-cols-4 gap-2 md:grid-cols-2">
            {item.images.slice(0, 8).map((src, i) => (
              <button key={src} onClick={() => setPhoto(i)} aria-label={t("photoAlt", { n: i + 1 })}
                className={`aspect-square overflow-hidden rounded-xl ${i === photo ? "ring-2 ring-teal-700" : ""}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="mb-1 flex flex-wrap gap-2"><Badge tone="teal">{tl(`type.${item.type}`)}</Badge>{item.owner.verified && <Badge tone="green"><CheckIcon size={12} />{t("verifiedLandlord")}</Badge>}</div>
        <h1 className="text-2xl font-bold sm:text-3xl">{item.title}</h1>
        <p className="text-[15px] text-slate-600">
          {areaName(item.area, locale)} · {t("posted", { when: timeAgo(item.created_at, locale) })}
          {item.available_from && <> · {t("availableFrom", { date: dateText(item.available_from, locale) })}</>}
        </p>
      </div>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              [num(item.rooms, locale), tl("rooms")],
              [num(item.baths, locale), tl("baths")],
              [item.size_sqft ? num(item.size_sqft, locale) : "—", tl("sqft")],
              [item.floor !== null ? num(item.floor, locale) : "—", tl("floor")],
            ].map(([v, l]) => (
              <div key={l} className={`${card} p-3`}><div className="text-xl font-bold">{v}</div><div className="text-sm text-slate-600">{l}</div></div>
            ))}
          </div>
          {item.description && (
            <section>
              <h2 className="mb-1 text-lg font-bold">{t("description")}</h2>
              <p className="whitespace-pre-line text-[16px] leading-relaxed text-slate-700">{item.description}</p>
            </section>
          )}
          <dl className={`${card} grid gap-x-6 gap-y-2 p-4 text-[15px] sm:grid-cols-2`}>
            <div className="flex justify-between gap-3"><dt className="text-slate-600">{tl("tenantFor")}</dt><dd className="font-semibold">{tl(`tenant.${item.tenant_type}`)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-slate-600">{tl("serviceCharge")}</dt><dd className="font-semibold">{money(item.service_charge, locale)}</dd></div>
            <div className="flex justify-between gap-3"><dt className="text-slate-600">{tl("advance")}</dt><dd className="font-semibold">{t("months", { n: digits(item.advance_months, locale) })}</dd></div>
            {amenities && <div className="flex justify-between gap-3"><dt className="text-slate-600">{tl("amenities")}</dt><dd className="text-right font-semibold">{amenities}</dd></div>}
          </dl>
          <div className={`${card} flex items-center gap-3 p-4`}>
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-200 font-bold">{t("ownerInitial")}</span>
            <div className="flex-1">
              <p className="font-bold">{item.type === "sublet" ? t("poster") : t("landlord")}</p>
              <p className="text-sm text-slate-600">
                {item.owner.rating?.count ? t("rating", { avg: digits(item.owner.rating.avg ?? 0, locale), n: digits(item.owner.rating.count, locale) }) : t("noReviews")}
              </p>
            </div>
          </div>

          {item.unlocked && !item.is_owner && (
            <section className={`${card} flex flex-col gap-3 p-4`}>
              <h2 className="font-bold">{t("rateTitle")}</h2>
              <div className="flex gap-1" role="radiogroup" aria-label={t("rateTitle")}>
                {[1, 2, 3, 4, 5].map((s) => (
                  <button key={s} role="radio" aria-checked={rating === s} onClick={() => setRating(s)}
                    className={`h-11 w-11 rounded-lg text-2xl ${s <= rating ? "text-amber-500" : "text-slate-300"}`} aria-label={`${s}`}>★</button>
                ))}
              </div>
              <button disabled={!rating || busy} className={`${btn.outline} self-start`}
                onClick={() => act(() => api("/reviews", { method: "POST", body: { listing_type: "rent", listing_id: item.id, rating } }), t("reviewThanks"))}>
                {t("sendReview")}
              </button>
            </section>
          )}
        </div>

        <aside className={`${card} order-first flex flex-col gap-4 p-5 shadow-sm lg:order-none lg:sticky lg:top-24 lg:w-96`}>
          <div className="text-3xl font-bold">{money(item.rent, locale)}<span className="text-base font-normal text-slate-600">{tl("perMonth")}</span></div>
          {item.private ? (
            <div className="flex flex-col gap-1 rounded-xl border border-teal-200 bg-teal-50 p-4">
              <span className="text-sm font-semibold text-teal-800">{item.is_owner ? t("yourPrivate") : t("unlocked")}</span>
              <span className="text-[16px] font-semibold">{t("address", { road: item.private.road_no, house: item.private.house_no, area: areaName(item.area, locale) })}</span>
              <a href={`tel:${item.private.contact_phone}`} className="text-[16px] font-semibold text-teal-800">{digits(item.private.contact_phone, locale)}</a>
            </div>
          ) : (
            <div className="flex flex-col gap-1 rounded-xl border-[1.5px] border-dashed border-amber-400 bg-amber-50 p-4">
              <span className="flex items-center gap-1.5 text-sm font-semibold text-amber-900"><LockIcon size={15} />{t("locked")}</span>
              <span className="blurred text-[16px]">Road 6, House 14/B · 01712-345678</span>
            </div>
          )}

          {item.is_owner ? (
            <div className="flex flex-col gap-2">
              {item.stats && <p className="text-sm text-slate-600">{t("ownerStats", { u: digits(item.stats.unlocks, locale), r: digits(item.stats.open_reports, locale) })}</p>}
              <Link href={`/post?edit=${item.id}`} className={btn.ghost}>{t("edit")}</Link>
              {item.status === "active" && <button disabled={busy} className={btn.outline} onClick={() => act(() => api(`/rent/${item.id}/status`, { method: "POST", body: { status: "rented" } }), t("markedRented"))}>{t("markRented")}</button>}
              {item.status === "rented" && <button disabled={busy} className={btn.outline} onClick={() => act(() => api(`/rent/${item.id}/status`, { method: "POST", body: { status: "active" } }))}>{t("reactivate")}</button>}
              {(item.status === "expired" || item.status === "active") && <button disabled={busy} className={btn.ghost} onClick={() => act(() => api(`/rent/${item.id}/renew`, { method: "POST" }), t("renewed"))}>{t("renew")}</button>}
              <button disabled={busy} className="min-h-[44px] text-sm font-semibold text-red-700"
                onClick={() => window.confirm(t("deleteConfirm")) && act(async () => { await api(`/rent/${item.id}`, { method: "DELETE" }); router.push("/dashboard"); })}>
                {t("delete")}
              </button>
            </div>
          ) : item.unlocked ? (
            <div className="grid grid-cols-2 gap-2">
              <Link href={`/messages?room=${item.room_id}`} className={btn.primary}><ChatIcon />{t("chat")}</Link>
              <a href={`tel:${item.private?.contact_phone}`} className={btn.outline}>{t("call")}</a>
            </div>
          ) : item.status === "active" ? (
            <button className={btn.primary} onClick={() => (user ? setConfirm(true) : router.push(`/login?next=/rent/${item.id}`))}>
              <Diamond size={18} />{t("unlockCta", { n: digits(unlockCost, locale) })}
            </button>
          ) : null}
          {!item.is_owner && <p className="text-[13px] leading-relaxed text-slate-600">{t("refundNote")}</p>}
          {user && !item.is_owner && (
            <button onClick={() => setReportOpen(true)} className="flex min-h-[44px] items-center justify-center gap-1.5 text-sm text-slate-600 underline"><FlagIcon size={15} />{t("report")}</button>
          )}
        </aside>
      </div>

      <Modal open={confirm} onClose={() => setConfirm(false)} title={t("confirmTitle", { n: digits(unlockCost, locale) })} label={tc("close")}>
        <div className="flex flex-col gap-4">
          <p className="text-[15px] text-slate-700">{t("confirmBalance", { from: digits(user?.balance ?? 0, locale), to: digits((user?.balance ?? 0) - unlockCost, locale) })}</p>
          <ul className="list-disc space-y-1 pl-5 text-[15px] text-slate-700"><li>{t("confirm1")}</li><li>{t("confirm2")}</li></ul>
          {(user?.balance ?? 0) < unlockCost ? (
            <Link href="/wallet" className={btn.primary}>{t("buyDiamonds")}</Link>
          ) : (
            <div className="grid grid-cols-[1fr_2fr] gap-2">
              <button className={btn.ghost} onClick={() => setConfirm(false)}>{tc("cancel")}</button>
              <button disabled={busy} className={btn.primary} onClick={unlock}>{t("confirmUnlock")}</button>
            </div>
          )}
        </div>
      </Modal>

      <Modal open={reportOpen} onClose={() => setReportOpen(false)} title={t("reportTitle")} label={tc("close")}>
        <div className="flex flex-col gap-3">
          {["already_rented", "fake", "scam", "no_reply", "abuse", "other"].map((r) => (
            <label key={r} className="flex min-h-[40px] items-center gap-2.5 text-[15px]">
              <input type="radio" name="reason" checked={reason === r} onChange={() => setReason(r)} className="h-[18px] w-[18px] accent-teal-700" />{t(`reason.${r}`)}
            </label>
          ))}
          <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} rows={3} placeholder={t("reportNote")} className={`${input} py-2`} />
          <button disabled={busy} className={btn.danger}
            onClick={() => act(async () => { await api("/reports", { method: "POST", body: { listing_type: "rent", listing_id: item.id, reason, note: note || null } }); setReportOpen(false); }, t("reported"))}>
            {t("sendReport")}
          </button>
        </div>
      </Modal>
    </div>
  );
}
