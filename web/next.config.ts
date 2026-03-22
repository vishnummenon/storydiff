import type { NextConfig } from "next";

const backend =
  process.env.BACKEND_URL || process.env.API_BASE_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
  /** Proxy Core Read API so the browser can use same-origin `/api/v1/*` (no CORS). SSR uses API_BASE_URL direct to FastAPI by default. */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
  async redirects() {
    return [{ source: "/feed", destination: "/", permanent: true }];
  },
};

export default nextConfig;
