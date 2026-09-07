import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backendUrl =
      process.env.INTERNAL_API_URL ||
      (process.env.NODE_ENV === "production" ? "http://api:8000" : "http://localhost:8000");
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
