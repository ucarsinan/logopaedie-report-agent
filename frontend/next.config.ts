import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    if (process.env.VERCEL_ENV !== "preview") return [];
    return [
      {
        source: "/(.*)",
        headers: [{ key: "X-Robots-Tag", value: "noindex" }],
      },
    ];
  },
};

export default nextConfig;
