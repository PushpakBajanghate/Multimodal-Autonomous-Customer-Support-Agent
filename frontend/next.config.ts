import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL;

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendUrl) {
      return [];
    }
    return [
      {
        source: "/api/backend/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
      {
        source: "/api/backend/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;


