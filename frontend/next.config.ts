import type { NextConfig } from "next"

// Backend URL used only by the Next.js server for proxying.
// Never exposed to the browser (no NEXT_PUBLIC_ prefix).
const API_URL = process.env.API_URL ?? "http://localhost:8000"

const nextConfig: NextConfig = {
  turbopack: {
    resolveExtensions: [".ts", ".tsx", ".js", ".jsx"],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_URL}/api/v1/:path*`,
      },
    ]
  },
}

export default nextConfig
