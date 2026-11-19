"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import { CheckIcon, Diamond, MailIcon } from "@/components/icons";
import { Alert, Field, btn, card, input } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useAuth, type User } from "@/lib/auth";

type Mode = "login" | "signup" | "forgot";
type Step = "form" | "otp" | "done";

function LoginInner() {
  const t = useTranslations("auth");
  const locale = useLocale();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const { setUser, user } = useAuth();

  const [mode, setMode] = useState<Mode>(params.get("mode") === "signup" ? "signup" : "login");
  const [step, setStep] = useState<Step>("form");
  const [purpose, setPurpose] = useState<"signup" | "login" | "reset">("login");
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", agree: true });
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [bonus, setBonus] = useState(false);

  useEffect(() => {
    if (user && step === "form") router.replace(next);
  }, [user, step, next, router]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: k === "agree" ? e.target.checked : e.target.value }));

  const run = async (fn: () => Promise<void>) => {
    setError("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("networkError"));
    } finally {
      setBusy(false);
    }
  };

  const goOtp = (p: typeof purpose) => {
    setPurpose(p);
    setCode("");
    setStep("otp");
    setCooldown(60);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      if (mode === "signup") {
        if (!form.agree) throw new ApiError(400, "agree", t("mustAgree"));
        await api("/auth/register", { method: "POST", body: { ...form, language: locale } });
        goOtp("signup");
      } else if (mode === "login") {
        const r = await api<{ status: string; user?: User }>("/auth/login", { method: "POST", body: { email: form.email, password: form.password } });
        if (r.status === "ok" && r.user) {
          setUser(r.user);
          router.replace(next);
        } else if (r.status === "verify_email") goOtp("signup");
        else goOtp("login");
      } else {
        await api("/auth/forgot-password", { method: "POST", body: { email: form.email } });
        goOtp("reset");
      }
    });
  };

  const verify = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      if (purpose === "reset") {
        await api("/auth/reset-password", { method: "POST", body: { email: form.email, code, new_password: newPassword } });
        setStep("done");
        return;
      }
      const path = purpose === "signup" ? "/auth/verify-email" : "/auth/login/verify";
      const r = await api<{ user: User }>(path, { method: "POST", body: { email: form.email, code } });
      setUser(r.user);
      setBonus(purpose === "signup");
      setStep("done");
    });
  };

  const resend = () =>
    run(async () => {
      await api("/auth/resend-otp", { method: "POST", body: { email: form.email, purpose } });
      setCooldown(60);
    });

  const switchMode = (m: Mode) => {
    setMode(m);
    setStep("form");
    setError("");
  };

  return (
    <div className="mx-auto grid min-h-[calc(100vh-72px)] max-w-6xl lg:grid-cols-2">
      <section className="hidden flex-col justify-center gap-6 bg-slate-900 p-12 text-white lg:flex">
        <h1 className="text-4xl font-bold leading-tight">{t("hero")}</h1>
        <ul className="flex flex-col gap-4 text-[17px] text-slate-300">
          {(["b1", "b2", "b3"] as const).map((k) => (
            <li key={k} className="flex gap-3"><span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-teal-900 text-teal-300"><CheckIcon size={16} /></span>{t(k)}</li>
          ))}
        </ul>
        <p className="text-sm text-slate-400">{t("privacy")}</p>
      </section>

      <section className="flex flex-col items-center gap-5 px-4 py-8">
        <div className={`${card} flex w-full max-w-md flex-col gap-4 p-6 sm:p-8`}>
          {step === "form" && mode !== "forgot" && (
            <div role="tablist" className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
              {(["login", "signup"] as const).map((m) => (
                <button key={m} role="tab" aria-selected={mode === m} onClick={() => switchMode(m)}
                  className={`min-h-[44px] rounded-lg font-bold ${mode === m ? "bg-white shadow-sm" : "text-slate-600"}`}>
                  {t(`tab.${m}`)}
                </button>
              ))}
            </div>
          )}

          {error && <Alert>{error}</Alert>}

          {step === "form" && (
            <form onSubmit={submit} className="flex flex-col gap-4">
              <div>
                <h2 className="text-2xl font-bold">{t(`${mode}.title`)}</h2>
                <p className="text-[15px] text-slate-600">{t(`${mode}.subtitle`)}</p>
              </div>
              {mode === "forgot" && (
                <button type="button" onClick={() => switchMode("login")} className="-mt-2 self-start text-sm font-semibold text-teal-700">← {t("backToLogin")}</button>
              )}
              {mode === "signup" && (
                <Field label={t("name")}><input required minLength={2} value={form.name} onChange={set("name")} className={input} autoComplete="name" /></Field>
              )}
              <Field label={t("email")}><input required type="email" value={form.email} onChange={set("email")} className={input} autoComplete="email" placeholder="name@gmail.com" /></Field>
              {mode === "signup" && (
                <Field label={t("phone")} hint={t("phoneHint")}><input required value={form.phone} onChange={set("phone")} className={input} autoComplete="tel" inputMode="tel" placeholder="01XXXXXXXXX" /></Field>
              )}
              {mode !== "forgot" && (
                <Field label={t("password")} hint={mode === "signup" ? t("passwordHint") : undefined}>
                  <input required type="password" minLength={mode === "signup" ? 8 : 1} value={form.password} onChange={set("password")} className={input}
                    autoComplete={mode === "signup" ? "new-password" : "current-password"} />
                </Field>
              )}
              {mode === "login" && (
                <button type="button" onClick={() => switchMode("forgot")} className="-mt-2 self-end text-sm font-semibold text-teal-700">{t("forgotLink")}</button>
              )}
              {mode === "signup" && (
                <label className="flex items-start gap-2.5 text-sm leading-relaxed text-slate-700">
                  <input type="checkbox" checked={form.agree} onChange={set("agree")} className="mt-1 h-[18px] w-[18px] accent-teal-700" />
                  {t("agree")}
                </label>
              )}
              <button disabled={busy} className={btn.primary}>{busy ? t("wait") : t(`${mode}.submit`)}</button>
            </form>
          )}

          {step === "otp" && (
            <form onSubmit={verify} className="flex flex-col gap-4">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-100 text-teal-700"><MailIcon size={28} /></span>
              <div>
                <h2 className="text-2xl font-bold">{t(`otp.${purpose}`)}</h2>
                <p className="text-[15px] leading-relaxed text-slate-600">{t("otpSent", { email: form.email })}</p>
              </div>
              <Field label={t("code")}>
                <input required value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" placeholder="••••••"
                  className={`${input} text-center text-2xl font-bold tracking-[0.5em]`} />
              </Field>
              {purpose === "reset" && (
                <Field label={t("newPassword")} hint={t("passwordHint")}>
                  <input required type="password" minLength={8} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={input} autoComplete="new-password" />
                </Field>
              )}
              {purpose === "signup" && (
                <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><Diamond size={26} />{t("bonusHint")}</div>
              )}
              <button disabled={busy || code.length !== 6} className={btn.primary}>{purpose === "reset" ? t("savePassword") : t("verify")}</button>
              <div className="flex items-center justify-between text-sm text-slate-600">
                <button type="button" onClick={() => setStep("form")} className="font-semibold text-teal-700">← {t("changeEmail")}</button>
                <button type="button" disabled={cooldown > 0 || busy} onClick={resend} className="min-h-[40px] font-semibold text-teal-700 disabled:text-slate-400">
                  {cooldown > 0 ? t("resendIn", { s: cooldown }) : t("resend")}
                </button>
              </div>
              <p className="text-center text-xs text-slate-500">{t("lockout")}</p>
            </form>
          )}

          {step === "done" && (
            <div className="flex flex-col items-center gap-4 text-center">
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-green-700"><CheckIcon size={32} /></span>
              <h2 className="text-2xl font-bold">{t(`done.${purpose}`)}</h2>
              {bonus && <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-left text-sm text-amber-900"><Diamond size={28} />{t("bonusAdded")}</div>}
              {purpose === "reset" ? (
                <button onClick={() => switchMode("login")} className={`${btn.primary} w-full`}>{t("goLogin")}</button>
              ) : (
                <button onClick={() => router.replace(next)} className={`${btn.primary} w-full`}>{t("continue")}</button>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginInner />
    </Suspense>
  );
}
