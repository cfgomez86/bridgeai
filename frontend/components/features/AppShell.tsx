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
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768)
    check()
    window.addEventListener("resize", check)
    return () => window.removeEventListener("resize", check)
  }, [])

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
    <div
      className="grid-sidebar-layout"
      style={{
        display: "grid",
        gridTemplateColumns: isMobile ? "1fr" : "240px 1fr",
        minHeight: "100vh",
      }}
    >
      {sidebarOpen && isMobile && (
        <div
          className="sidebar-overlay"
          style={{
            display: "block",
            position: "fixed",
            inset: 0,
            background: "oklch(0 0 0 / 0.45)",
            zIndex: 39,
            backdropFilter: "blur(1px)",
          }}
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} isMobile={isMobile} />
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", minWidth: 0, overflow: "clip" }}>
        <Topbar onMenuToggle={() => setSidebarOpen(true)} isMobile={isMobile} />
        <main style={{ flex: 1, background: "var(--bg)" }}>{children}</main>
      </div>
    </div>
  )
}
