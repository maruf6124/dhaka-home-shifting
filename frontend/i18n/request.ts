import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export const LOCALES = ["bn", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_COOKIE = "NEXT_LOCALE";

// One language setting for the whole site: stored in a cookie (and in the
// user's profile when logged in), read here on every request.
export default getRequestConfig(async () => {
  const fromCookie = cookies().get(LOCALE_COOKIE)?.value;
  let locale: Locale = "bn";
  if (fromCookie === "en" || fromCookie === "bn") {
    locale = fromCookie;
  } else if ((headers().get("accept-language") || "").toLowerCase().startsWith("en")) {
    locale = "en";
  }
  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
    timeZone: "Asia/Dhaka",
  };
});
