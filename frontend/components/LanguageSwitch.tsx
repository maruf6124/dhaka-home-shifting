"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** One switch for the whole site: saves the cookie (and the profile when logged in). */
export default function LanguageSwitch({ compact = false }: { compact?: boolean }) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations("common");
  const { user, setUser } = useAuth();
  const [pending, start] = useTransition();

  const choose = (lang: "bn" | "en") => {
    if (lang === locale) return;
    document.cookie = `NEXT_LOCALE=${lang}; path=/; max-age=31536000; samesite=lax`;
    document.documentElement.lang = lang;
    if (user) {
      api("/users/me", { method: "PATCH", body: { language: lang } }).then(setUser).catch(() => undefined);
    }
    start(() => router.refresh());
  };

  const item = (lang: "bn" | "en", label: string) => (
    <button
      type="button"
      onClick={() => choose(lang)}
      aria-pressed={locale === lang}
      className={`min-h-[34px] rounded-full px-3 text-[13px] font-bold transition ${
        locale === lang ? "bg-slate-900 text-white" : "text-slate-600 hover:text-slate-900"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div role="group" aria-label={t("language")} className={`flex rounded-full bg-slate-200 p-[3px] ${pending ? "opacity-60" : ""}`}>
      {item("bn", compact ? "বাং" : "বাংলা")}
      {item("en", compact ? "EN" : "English")}
    </div>
  );
}
