"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useLanguage } from "@/lib/i18n"

interface NavItem {
  href: string
  label: string
  icon: React.ReactNode
}

function IconWand() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2l1 1-7 7-1-1 7-7z" />
      <path d="M14 6l-1-1" />
      <path d="M2 10l-1 1" />
      <path d="M13 1l1 1" />
      <path d="M1 13l1 1" />
      <path d="M3 3l1 1" />
      <path d="M12 12l1 1" />
    </svg>
  )
}

function IconDatabase() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="8" cy="4" rx="5.5" ry="1.5" />
      <path d="M13.5 4v3c0 .83-2.46 1.5-5.5 1.5S2.5 7.83 2.5 7V4" />
      <path d="M13.5 7v3c0 .83-2.46 1.5-5.5 1.5S2.5 10.83 2.5 10V7" />
      <path d="M13.5 10v2c0 .83-2.46 1.5-5.5 1.5S2.5 12.83 2.5 12v-2" />
    </svg>
  )
}

function IconPlug() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 1v4M6.5 1v4" />
      <path d="M4 5h8a1 1 0 0 1 1 1v1a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V6a1 1 0 0 1 1-1z" />
      <path d="M8 11v4" />
    </svg>
  )
}

function IconSettings() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5v1M8 13.5v1M1.5 8h1M13.5 8h1M3.4 3.4l.7.7M11.9 11.9l.7.7M3.4 12.6l.7-.7M11.9 4.1l.7-.7" />
    </svg>
  )
}

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname()
  const { t } = useLanguage()

  const prefix = ""

  const NAV_ITEMS: NavItem[] = [
    { href: `${prefix}/workflow`, label: t.nav.workflow, icon: <IconWand /> },
    { href: `${prefix}/indexing`, label: t.nav.indexing, icon: <IconDatabase /> },
    { href: `${prefix}/connections`, label: t.nav.connections, icon: <IconPlug /> },
    { href: `${prefix}/settings`, label: t.nav.settings, icon: <IconSettings /> },
  ]

  function navItemStyle(isActive: boolean): React.CSSProperties {
    return {
      display: "flex",
      alignItems: "center",
      gap: "8px",
      padding: "6px 10px",
      borderRadius: "5px",
      color: isActive ? "var(--accent-strong)" : "var(--fg-2)",
      background: isActive ? "var(--accent-soft)" : "transparent",
      fontWeight: isActive ? 500 : 400,
      fontSize: "13px",
      textDecoration: "none",
      cursor: "pointer",
      transition: "background 0.1s, color 0.1s",
    }
  }

  return (
    <aside
      className={`sidebar-mobile${isOpen ? " is-open" : ""}`}
      style={{
        background: "var(--surface-2)",
        borderRight: "1px solid var(--border)",
        padding: "14px 10px",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        position: "sticky",
        top: 0,
        overflow: "hidden",
        gap: "0",
      }}
    >
      {/* Close button — mobile only */}
      <button
        onClick={onClose}
        className="sidebar-close-btn"
        aria-label="Cerrar menú"
        style={{
          position: "absolute",
          top: "10px",
          right: "10px",
          width: "28px",
          height: "28px",
          border: "none",
          background: "transparent",
          color: "var(--muted)",
          cursor: "pointer",
          borderRadius: "4px",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          lineHeight: 1,
          padding: 0,
        }}
      >
        ×
      </button>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "2px 6px", marginBottom: "12px" }}>
        <div style={{
          width: "22px",
          height: "22px",
          borderRadius: "5px",
          background: "linear-gradient(135deg, var(--accent) 0%, oklch(0.62 0.18 300) 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontSize: "11px",
          fontWeight: 700,
          fontFamily: "var(--font-display)",
          flexShrink: 0,
        }}>B</div>
        <span style={{ fontSize: "13.5px", fontWeight: 600, fontFamily: "var(--font-display)", color: "var(--fg)" }}>
          BridgeAI <span style={{ color: "var(--muted-2)", fontWeight: 400 }}>·</span>
        </span>
      </div>

      {/* Navigation */}
      <nav style={{ display: "flex", flexDirection: "column", gap: "1px", flex: 1 }}>
        {NAV_ITEMS.map(({ href, label, icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/")
          return (
            <Link key={href} href={href} style={navItemStyle(isActive)} className="group">
              <span style={{ flexShrink: 0, color: isActive ? "var(--accent)" : "var(--muted)" }}>
                {icon}
              </span>
              <span style={{ flex: 1 }}>{label}</span>
            </Link>
          )
        })}
      </nav>

      <style>{`
        .group:hover { background: var(--surface-3) !important; }
      `}</style>
    </aside>
  )
}
