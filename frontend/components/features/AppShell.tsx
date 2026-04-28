"use client"

import { useState, useEffect } from "react"
import { usePathname } from "next/navigation"
import { Sidebar } from "@/components/features/Sidebar"
import { Topbar } from "@/components/features/Topbar"

const AUTH_PATHS = ["/sign-in", "/sign-up", "/login"]

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuth = AUTH_PATHS.some((p) => pathname.startsWith(p))
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Prevent background scroll when sidebar drawer is open on mobile
  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? "hidden" : ""
    return () => { document.body.style.overflow = "" }
  }, [sidebarOpen])

  // Close sidebar on route change (mobile navigation)
  useEffect(() => { setSidebarOpen(false) }, [pathname])

  if (isAuth) {
    return <>{children}</>
  }

  return (
    <div className="grid-sidebar-layout">
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", minWidth: 0, overflow: "hidden" }}>
        <Topbar onMenuToggle={() => setSidebarOpen(true)} />
        <main style={{ flex: 1, background: "var(--bg)" }}>{children}</main>
      </div>
    </div>
  )
}
