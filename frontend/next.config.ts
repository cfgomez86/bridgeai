import type { NextConfig } from "next"
import * as fs from "fs"
import * as path from "path"

// ── Environment overlay loading ────────────────────────────────────────────────
// Mirrors backend config.py pattern: base .env is loaded by Next.js automatically;
// this loads .env.{APP_ENV} on top, same as pydantic-settings does server-side.
//
// Usage:
//   APP_ENV=local   (default) → loads frontend/.env.local
//   APP_ENV=prod              → loads frontend/.env.prod

function loadEnvOverlay(appEnv: string): void {
  const filePath = path.join(process.cwd(), `.env.${appEnv}`)
  if (!fs.existsSync(filePath)) return
  const content = fs.readFileSync(filePath, "utf-8")
  for (const line of content.split("\n")) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith("#")) continue
    const eq = trimmed.indexOf("=")
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    const value = trimmed.slice(eq + 1).trim()
    process.env[key] = value
  }
}

const APP_ENV = process.env.APP_ENV ?? "local"
loadEnvOverlay(APP_ENV)

// ── Derived values (available after overlay is applied) ───────────────────────

// Backend URL for the server-side proxy — never sent to the browser.
const API_URL = process.env.API_URL ?? "http://localhost:8000"

// Frontend origin — needed so Next.js trusts Server Actions requests coming
// through a tunnel or reverse proxy (CSRF origin check).
const extraOrigins: string[] = []
if (process.env.APP_URL) {
  try {
    extraOrigins.push(new URL(process.env.APP_URL).host)
  } catch {}
}

// ── Next.js config ────────────────────────────────────────────────────────────

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:3000", ...extraOrigins],
    },
    proxyTimeout: 120_000,
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
