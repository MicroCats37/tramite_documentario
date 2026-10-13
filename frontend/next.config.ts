import type { NextConfig } from "next";

const backendHost = process.env.BACKEND_HOST;
if (!backendHost) {
  throw new Error(
    "BACKEND_HOST env var is required (format: host:port, e.g. localhost:8000). " +
      "Set it in frontend/.env.local (dev) or root .env (Docker).",
  );
}

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `http://${backendHost}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
