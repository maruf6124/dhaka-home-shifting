"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import type { Listing } from "@/components/ListingCard";
import { CloseIcon, ImageIcon, LockIcon } from "@/components/icons";
import { Alert, Field, Spinner, btn, card, input } from "@/components/ui";
import { ApiError, api, compressImage } from "@/lib/api";
import { areaOptions, useAreas } from "@/lib/areas";
import { useAuth } from "@/lib/auth";

const AMENITIES = ["lift", "gas", "generator", "parking", "cctv", "guard"] as const;

const empty = {
  type: "entire_flat", area_id: "", title: "", description: "", rent: "", service_charge: "0", advance_months: "2",
  rooms: "2", baths: "1", size_sqft: "", floor: "", tenant_type: "family", amenities: [] as string[], available_from: "",
  road_no: "", house_no: "", contact_phone: "", images: [] as string[],
};

function PostInner() {
  const t = useTranslations("post");
  const tl = useTranslations("listing");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const editId = params.get("edit");
  const { user, loading, hasRole } = useAuth();
  const areas = useAreas();
  const [form, setForm] = useState({ ...empty, type: params.get("type") === "sublet" ? "sublet" : "entire_flat" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loaded, setLoaded] = useState(!editId);

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=/post`);
  }, [loading, user, router]);

  useEffect(() => {
    if (!editId) return;
    api<Listing>(`/rent/${editId}`).then((l) => {
      setForm({
        type: l.type, area_id: String(l.area.id), title: l.title, description: l.description, rent: String(l.rent),
        service_charge: String(l.service_charge), advance_months: String(l.advance_months), rooms: String(l.rooms),
        baths: String(l.baths), size_sqft: l.size_sqft ? String(l.size_sqft) : "", floor: l.floor !== null ? String(l.floor) : "",
        tenant_type: l.tenant_type, amenities: l.amenities, available_from: l.available_from || "",
        road_no: l.private?.road_no || "", house_no: l.private?.house_no || "", contact_phone: l.private?.contact_phone || "", images: l.images,
      });
      setLoaded(true);
    }).catch((e: ApiError) => setError(e.message));
  }, [editId]);

  useEffect(() => {
    if (user && !form.contact_phone && !editId) setForm((f) => ({ ...f, contact_phone: user.phone }));
  }, [user, form.contact_phone, editId]);

  if (loading || !user || !loaded) return <Spinner />;

  const isLandlord = hasRole("landlord");
  const blocked = form.type === "entire_flat" && !isLandlord && !editId;
  const set = (k: keyof typeof empty) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const upload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    setError("");
    try {
      const urls: string[] = [];
      for (const file of Array.from(files).slice(0, 8 - form.images.length)) {
        const fd = new FormData();
        fd.append("file", await compressImage(file));
        urls.push((await api<{ url: string }>("/uploads/image", { method: "POST", body: fd })).url);
      }
      setForm((f) => ({ ...f, images: [...f.images, ...urls] }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("uploadFailed"));
    } finally {
      setUploading(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    const toInt = (v: string) => (v === "" ? null : Number(v));
    const body: Record<string, unknown> = {
      ...form, area_id: Number(form.area_id), rent: Number(form.rent), service_charge: Number(form.service_charge || 0),
      advance_months: Number(form.advance_months || 0), rooms: Number(form.rooms), baths: Number(form.baths),
      size_sqft: toInt(form.size_sqft), floor: toInt(form.floor), available_from: form.available_from || null,
    };
    try {
      if (editId) {
        delete body.type;
        delete body.area_id;
        await api(`/rent/${editId}`, { method: "PATCH", body });
        router.push(`/rent/${editId}`);
      } else {
        const r = await api<{ id: number }>("/rent", { method: "POST", body });
        router.push(`/rent/${r.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("failed"));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-3xl flex-col gap-5 px-4 py-6">
      <div>
        <h1 className="text-3xl font-bold">{editId ? t("editTitle") : t("title")}</h1>
        <p className="text-[15px] text-slate-600">{t("subtitle")}</p>
      </div>
      {error && <Alert>{error}</Alert>}

      {!editId && (
        <fieldset className="grid grid-cols-2 gap-3">
          <legend className="mb-2 text-sm font-semibold">{t("kind")}</legend>
          {(["entire_flat", "sublet"] as const).map((k) => (
            <label key={k} className={`flex cursor-pointer flex-col gap-1 rounded-2xl border-2 p-4 ${form.type === k ? "border-teal-700 bg-teal-50" : "border-slate-200 bg-white"}`}>
              <span className="flex items-center gap-2 font-bold"><input type="radio" name="type" checked={form.type === k} onChange={() => setForm((f) => ({ ...f, type: k }))} className="h-[18px] w-[18px] accent-teal-700" />{tl(`type.${k}`)}</span>
              <span className="text-xs text-slate-600">{t(`kindHint.${k}`)}</span>
            </label>
          ))}
        </fieldset>
      )}

      {blocked ? (
        <Alert kind="warn">
          {t("needLandlord")} <Link href="/become-provider" className="font-bold underline">{t("becomeLandlord")}</Link>
        </Alert>
      ) : (
        <>
          <section className={`${card} grid gap-4 p-5 sm:grid-cols-2`}>
            <h2 className="text-lg font-bold sm:col-span-2">{t("s1")}</h2>
            {!editId && (
              <Field label={t("area")}>
                <select required value={form.area_id} onChange={set("area_id")} className={input}>
                  <option value="">{t("chooseArea")}</option>
                  {areaOptions(areas, locale).map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </Field>
            )}
            <Field label={t("rent")}><input required type="number" min={1} value={form.rent} onChange={set("rent")} className={input} /></Field>
            <Field label={t("serviceCharge")}><input type="number" min={0} value={form.service_charge} onChange={set("service_charge")} className={input} /></Field>
            <Field label={t("advance")}>
              <select value={form.advance_months} onChange={set("advance_months")} className={input}>
                {[0, 1, 2, 3, 6].map((m) => <option key={m} value={m}>{t("months", { n: m })}</option>)}
              </select>
            </Field>
            <Field label={t("availableFrom")}><input type="date" value={form.available_from} onChange={set("available_from")} className={input} /></Field>
          </section>

          <section className={`${card} grid gap-4 p-5 sm:grid-cols-3`}>
            <h2 className="text-lg font-bold sm:col-span-3">{t("s2")}</h2>
            <div className="sm:col-span-3"><Field label={t("titleField")} hint={t("titleHint")}><input required minLength={5} maxLength={150} value={form.title} onChange={set("title")} className={input} /></Field></div>
            <Field label={tl("rooms")}><input required type="number" min={1} max={20} value={form.rooms} onChange={set("rooms")} className={input} /></Field>
            <Field label={tl("baths")}><input required type="number" min={0} max={20} value={form.baths} onChange={set("baths")} className={input} /></Field>
            <Field label={tl("floor")}><input type="number" min={0} max={100} value={form.floor} onChange={set("floor")} className={input} /></Field>
            <Field label={tl("sqft")}><input type="number" min={1} value={form.size_sqft} onChange={set("size_sqft")} className={input} /></Field>
            <div className="sm:col-span-2">
              <Field label={tl("tenantFor")}>
                <select value={form.tenant_type} onChange={set("tenant_type")} className={input}>
                  {["family", "bachelor", "female", "any"].map((k) => <option key={k} value={k}>{tl(`tenant.${k}`)}</option>)}
                </select>
              </Field>
            </div>
            <fieldset className="sm:col-span-3">
              <legend className="mb-2 text-sm font-semibold">{tl("amenities")}</legend>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {AMENITIES.map((a) => (
                  <label key={a} className="flex min-h-[40px] items-center gap-2 text-[15px]">
                    <input type="checkbox" checked={form.amenities.includes(a)} className="h-[18px] w-[18px] accent-teal-700"
                      onChange={(e) => setForm((f) => ({ ...f, amenities: e.target.checked ? [...f.amenities, a] : f.amenities.filter((x) => x !== a) }))} />
                    {tl(`amenity.${a}`)}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="sm:col-span-3">
              <Field label={t("description")} hint={t("contactWarning")}>
                <textarea rows={4} maxLength={3000} value={form.description} onChange={set("description")} className={`${input} py-2.5`} />
              </Field>
            </div>
          </section>

          <section className={`${card} flex flex-col gap-3 p-5`}>
            <h2 className="text-lg font-bold">{t("s3")}</h2>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
              {form.images.map((src) => (
                <div key={src} className="relative aspect-square overflow-hidden rounded-xl bg-slate-100">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt="" className="h-full w-full object-cover" />
                  <button type="button" aria-label={t("removePhoto")} onClick={() => setForm((f) => ({ ...f, images: f.images.filter((x) => x !== src) }))}
                    className="absolute right-1 top-1 flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-slate-800"><CloseIcon size={16} /></button>
                </div>
              ))}
              {form.images.length < 8 && (
                <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-slate-400 bg-slate-50 text-sm text-slate-600">
                  <ImageIcon size={24} />{uploading ? t("uploading") : t("addPhoto")}
                  <input type="file" accept="image/jpeg,image/png,image/webp" multiple className="sr-only" disabled={uploading} onChange={(e) => upload(e.target.files)} />
                </label>
              )}
            </div>
            <p className="text-xs text-slate-500">{t("photoHint")}</p>
          </section>

          <section className="grid gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-5 sm:grid-cols-3">
            <h2 className="flex items-center gap-2 text-lg font-bold text-amber-950 sm:col-span-3"><LockIcon size={18} />{t("s4")}</h2>
            <Field label={t("road")}><input required value={form.road_no} onChange={set("road_no")} className={input} /></Field>
            <Field label={t("house")}><input required value={form.house_no} onChange={set("house_no")} className={input} /></Field>
            <Field label={t("phone")}><input required value={form.contact_phone} onChange={set("contact_phone")} className={input} inputMode="tel" /></Field>
          </section>

          <ul className="space-y-1 text-sm text-slate-600">
            <li>• {t("rule1")}</li><li>• {t("rule2")}</li>
          </ul>
          <button disabled={busy || uploading} className={btn.primary}>{busy ? t("saving") : editId ? t("save") : t("publish")}</button>
        </>
      )}
    </form>
  );
}

export default function PostPage() {
  return <Suspense><PostInner /></Suspense>;
}
