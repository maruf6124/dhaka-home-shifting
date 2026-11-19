import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

// The browser talks to the API through /api on the same domain, so login
// cookies are first-party (no third-party-cookie problems on Safari/Chrome).
const API_URL = process.env.API_URL || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
  images: { unoptimized: true },
};

export default withNextIntl(nextConfig);
