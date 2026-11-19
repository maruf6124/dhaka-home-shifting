const BN_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];

export function digits(value: string | number, locale: string): string {
  const s = String(value);
  return locale === "bn" ? s.replace(/\d/g, (d) => BN_DIGITS[Number(d)]) : s;
}

export function money(value: number, locale: string): string {
  return "৳" + digits(value.toLocaleString("en-IN"), locale);
}

export function num(value: number, locale: string): string {
  return digits(value.toLocaleString("en-IN"), locale);
}

export function timeAgo(iso: string, locale: string): string {
  const then = new Date(iso.endsWith("Z") ? iso : iso + "Z").getTime();
  const sec = Math.max(1, Math.round((Date.now() - then) / 1000));
  const rtf = new Intl.RelativeTimeFormat(locale === "bn" ? "bn" : "en", { numeric: "auto" });
  if (sec < 60) return rtf.format(-sec, "second");
  if (sec < 3600) return rtf.format(-Math.round(sec / 60), "minute");
  if (sec < 86400) return rtf.format(-Math.round(sec / 3600), "hour");
  return rtf.format(-Math.round(sec / 86400), "day");
}

export function dateText(iso: string, locale: string): string {
  const d = new Date(iso.endsWith("Z") || iso.length <= 10 ? iso : iso + "Z");
  return d.toLocaleDateString(locale === "bn" ? "bn-BD" : "en-GB", { day: "numeric", month: "short", year: "numeric" });
}
