import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // The rewrite proxy that fronts the API aborts at 30s by default, which the
    // review-report export exceeds: a LibreOffice PDF run takes ~15s, and adding
    // the language-mechanics pass pushes it past 80s. Raise it to ten minutes.
    // It must be a number: `0` falls through the `proxyTimeout || 30000`
    // default in Next's proxy and would restore the 30s ceiling.
    proxyTimeout: 600_000,
  },
  async rewrites() {
    const backendUrl = process.env.INTERNAL_BACKEND_URL || "http://backend:8000";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
