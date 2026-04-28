"use client"

import { usePathname } from "next/navigation"
import { useLanguage } from "@/lib/i18n"
import { useUser } from "@auth0/nextjs-auth0/client"

interface TopbarProps {
  onMenuToggle?: () => void
  isMobile?: boolean
}

export function Topbar({ onMenuToggle, isMobile = false }: TopbarProps) {
  const pathname = usePathname()
  const { t } = useLanguage()
  const { user } = useUser()

  const segments = pathname.split("/").filter(Boolean)

  const ROUTE_LABELS: Record<string, string> = {
    workflow: t.nav.workflow,
    indexing: t.nav.indexing,
    connections: t.nav.connections,
    settings: t.nav.settings,
  }

  const crumbs: { label: string; href: string }[] = [{ label: "BridgeAI", href: "/" }]
  let cumulative = ""
  for (const seg of segments) {
    cumulative += "/" + seg
    const label = ROUTE_LABELS[seg]
    if (label) crumbs.push({ label, href: cumulative })
  }

  return (
    <header style={{
      height: "48px",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 20px",
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      backdropFilter: "blur(8px)",
      position: "sticky",
      top: 0,
      zIndex: 20,
      flexShrink: 0,
    }}>
      {/* Hamburger — visible only on mobile */}
      <button
        onClick={onMenuToggle}
        className="hamburger-btn"
        aria-label="Abrir menú"
        style={{
          display: isMobile ? "flex" : "none",
          alignItems: "center",
          justifyContent: "center",
          width: "36px",
          height: "36px",
          padding: 0,
          border: "none",
          background: "transparent",
          color: "var(--fg)",
          cursor: "pointer",
          borderRadius: "var(--radius)",
          flexShrink: 0,
          marginRight: "4px",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <line x1="2" y1="4.5" x2="16" y2="4.5" />
          <line x1="2" y1="9" x2="16" y2="9" />
          <line x1="2" y1="13.5" x2="16" y2="13.5" />
        </svg>
      </button>

      {/* Breadcrumbs */}
      <nav style={{ display: "flex", alignItems: "center", gap: "4px", overflow: "hidden", flex: 1, minWidth: 0 }}>
        {crumbs.map((crumb, i) => (
          <span key={crumb.href} style={{ display: "flex", alignItems: "center", gap: "4px", flexShrink: i === crumbs.length - 1 ? 1 : 0, minWidth: 0 }}>
            {i > 0 && (
              <span style={{ color: "var(--muted-2)", fontSize: "13px" }}>/</span>
            )}
            <span style={{
              fontSize: "13px",
              color: i === crumbs.length - 1 ? "var(--fg)" : "var(--muted)",
              fontWeight: i === crumbs.length - 1 ? 500 : 400,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {crumb.label}
            </span>
          </span>
        ))}
      </nav>

      {/* User menu */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexShrink: 0, paddingLeft: "12px" }}>
        {user && (
          <span className="topbar-email" style={{ fontSize: "13px", color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "200px" }}>
            {user.email}
          </span>
        )}
        <a
          href="/api/auth/logout"
          style={{
            fontSize: "13px",
            color: "var(--muted)",
            textDecoration: "none",
            padding: "4px 10px",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          Salir
        </a>
      </div>
    </header>
  )
}
