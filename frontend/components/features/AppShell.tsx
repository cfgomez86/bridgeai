"use client"

import { usePathname } from "next/navigation"
import { Sidebar } from "@/components/features/Sidebar"
import { Topbar } from "@/components/features/Topbar"

const AUTH_PATHS = ["/sign-in", "/sign-up", "/login"]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuth = AUTH_PATHS.some((p) => pathname.startsWith(p))

  if (isAuth) {
    return <>{children}</>
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <Topbar />
        <main style={{ flex: 1, background: "var(--bg)" }}>{children}</main>
      </div>
    </div>
  )
}
